from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import (
    PublicApplicationBodyLimitMiddleware,
    get_public_rate_limit_redis,
    install_public_exception_handlers,
    router,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.models.job import Job
from app.services.public_application_rate_limiter import (
    PublicApplicationRateLimitExceededError,
    public_application_rate_limiter,
)
from app.services.public_application_service import (
    PublicApplicationAcceptance,
    PublicApplicationIdempotencyConflictError,
    PublicApplicationJobNotOpenError,
    PublicApplicationReviewRequiredError,
    PublicApplicationSaveError,
    public_application_service,
)
from app.services.public_job_service import public_job_service
from app.services.resume_storage import (
    PreparedResumeFile,
    ResumeFileTooLargeError,
    UnsupportedResumeTypeError,
    resume_file_storage,
)


NOW = datetime(2026, 9, 2, 10, 30, tzinfo=timezone.utc)


def make_job(job_id: int = 1) -> Job:
    return Job(
        id=job_id,
        title="虚构后端工程师",
        department="演示研发部",
        location="长沙",
        employment_type="full_time",
        headcount=99,
        job_background="建设演示系统。",
        job_responsibilities="负责 API 开发。",
        candidate_requirements="具备 Python 经验。",
        preferred_qualifications="有 PostgreSQL 经验优先。",
        public_notes="仅使用虚构数据演示。",
        status="open",
        created_at=NOW,
        updated_at=NOW,
    )


def prepared_file() -> PreparedResumeFile:
    return PreparedResumeFile(
        original_filename="resume.txt",
        extension=".txt",
        mime_type="text/plain",
        file_size=6,
        sha256="a" * 64,
        temp_path=Path("staging.part"),
        final_path=Path("final.txt"),
        relative_path="v2/resumes/2026/09/final.txt",
    )


class PublicApiTest(TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        install_public_exception_handlers(app)
        app.include_router(router, prefix="/api/v2")
        self.db = Mock(name="database")
        self.redis = Mock(name="redis")

        async def override_get_db():
            yield self.db

        async def override_redis():
            yield self.redis

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_public_rate_limit_redis] = override_redis
        self.app = app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    @staticmethod
    def valid_data(**overrides: str) -> dict[str, str]:
        data = {
            "name": "测试候选人",
            "phone": "138 0000 0001",
            "email": "Demo.Candidate@Example.com",
            "job_id": "1",
            "privacy_consent": "true",
            "consent_version": get_settings().PUBLIC_APPLICATION_CONSENT_VERSION,
            "idempotency_key": str(uuid4()),
        }
        data.update(overrides)
        return data

    def post(self, **overrides):
        return self.client.post(
            "/api/v2/public/applications",
            data=self.valid_data(**overrides),
            files={"resume": ("resume.txt", b"resume", "text/plain")},
        )

    def test_public_jobs_only_serialize_candidate_visible_fields(self) -> None:
        with patch.object(
            public_job_service,
            "list_open_jobs",
            AsyncMock(return_value=[make_job()]),
        ):
            response = self.client.get("/api/v2/public/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()[0]),
            {
                "id",
                "title",
                "department",
                "location",
                "employment_type",
                "job_background",
                "job_responsibilities",
                "candidate_requirements",
                "preferred_qualifications",
                "public_notes",
            },
        )
        self.assertNotIn("headcount", response.json()[0])
        self.assertNotIn("status", response.json()[0])

    def test_public_job_detail_hides_closed_draft_and_missing_behind_same_404(self) -> None:
        with patch.object(
            public_job_service,
            "get_open_job",
            AsyncMock(return_value=None),
        ):
            response = self.client.get("/api/v2/public/jobs/7")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "PUBLIC_JOB_NOT_FOUND")

    def test_application_returns_202_public_receipt_and_normalized_schema(self) -> None:
        acceptance = PublicApplicationAcceptance("AP-7K9M2Q4X", NOW, False)
        with (
            patch.object(
                public_application_rate_limiter,
                "check",
                AsyncMock(),
            ) as rate_mock,
            patch.object(
                resume_file_storage,
                "prepare",
                AsyncMock(return_value=prepared_file()),
            ),
            patch.object(
                public_application_service,
                "accept",
                AsyncMock(return_value=acceptance),
            ) as accept_mock,
        ):
            response = self.post()

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["submission_reference"], "AP-7K9M2Q4X")
        self.assertNotIn("candidate_id", response.text)
        passed_data = accept_mock.await_args.args[1]
        self.assertEqual(passed_data.phone, "13800000001")
        self.assertEqual(passed_data.email, "demo.candidate@example.com")
        rate_mock.assert_awaited_once()

    def test_unknown_or_duplicate_form_field_returns_stable_422(self) -> None:
        response = self.client.post(
            "/api/v2/public/applications",
            data={**self.valid_data(), "source": "public_apply"},
            files={"resume": ("resume.txt", b"resume", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "PUBLIC_APPLICATION_VALIDATION_FAILED",
        )

    def test_missing_required_file_returns_stable_422(self) -> None:
        response = self.client.post(
            "/api/v2/public/applications",
            data=self.valid_data(),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "PUBLIC_APPLICATION_VALIDATION_FAILED",
        )

    def test_stale_consent_version_returns_safe_400_before_rate_limit(self) -> None:
        with patch.object(
            public_application_rate_limiter,
            "check",
            AsyncMock(),
        ) as rate_mock:
            response = self.post(consent_version="old-version")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "PUBLIC_APPLICATION_INVALID")
        rate_mock.assert_not_awaited()

    def test_rate_limit_returns_retry_after_and_does_not_write_file(self) -> None:
        with (
            patch.object(
                public_application_rate_limiter,
                "check",
                AsyncMock(side_effect=PublicApplicationRateLimitExceededError(27)),
            ),
            patch.object(resume_file_storage, "prepare", AsyncMock()) as prepare_mock,
        ):
            response = self.post()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "27")
        self.assertEqual(
            response.json()["detail"]["code"],
            "PUBLIC_APPLICATION_RATE_LIMITED",
        )
        prepare_mock.assert_not_awaited()

    def test_body_limit_rejects_request_before_route_dependencies(self) -> None:
        app = FastAPI()
        app.add_middleware(PublicApplicationBodyLimitMiddleware, max_body_size=128)
        app.include_router(router, prefix="/api/v2")
        with TestClient(app) as client:
            response = client.post(
                "/api/v2/public/applications",
                content=b"x" * 129,
                headers={"content-type": "multipart/form-data; boundary=test"},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["detail"]["code"], "RESUME_FILE_TOO_LARGE")

    def test_file_errors_have_stable_public_codes(self) -> None:
        cases = (
            (ResumeFileTooLargeError(), 413, "RESUME_FILE_TOO_LARGE"),
            (UnsupportedResumeTypeError(), 415, "RESUME_TYPE_UNSUPPORTED"),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(expected_code):
                with (
                    patch.object(public_application_rate_limiter, "check", AsyncMock()),
                    patch.object(
                        resume_file_storage,
                        "prepare",
                        AsyncMock(side_effect=error),
                    ),
                ):
                    response = self.post()
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)

    def test_service_errors_are_sanitized(self) -> None:
        cases = (
            (PublicApplicationJobNotOpenError(), 409, "JOB_NOT_OPEN"),
            (
                PublicApplicationIdempotencyConflictError(),
                409,
                "IDEMPOTENCY_KEY_REUSED",
            ),
            (
                PublicApplicationReviewRequiredError(),
                409,
                "PUBLIC_APPLICATION_REVIEW_REQUIRED",
            ),
            (
                PublicApplicationSaveError("postgresql://secret"),
                500,
                "PUBLIC_APPLICATION_SAVE_FAILED",
            ),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(expected_code):
                with (
                    patch.object(public_application_rate_limiter, "check", AsyncMock()),
                    patch.object(
                        resume_file_storage,
                        "prepare",
                        AsyncMock(return_value=prepared_file()),
                    ),
                    patch.object(
                        public_application_service,
                        "accept",
                        AsyncMock(side_effect=error),
                    ),
                ):
                    response = self.post()
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("secret", response.text)
