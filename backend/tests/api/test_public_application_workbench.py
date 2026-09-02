from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public_application_workbench import router
from app.core.database import get_db
from app.main import app as main_app
from app.schemas.public_application_workbench import (
    PublicApplicationIdentityCandidate,
    PublicApplicationProcessingRunSummary,
    PublicApplicationWorkbenchDetail,
    PublicApplicationWorkbenchSummary,
)
from app.schemas.public_application import ApplicationProcessingTriggerType
from app.schemas.public_application import PublicApplicationIdentityReviewStatus
from app.services.application_processing_service import (
    ApplicationProcessingActiveRunError,
    ApplicationProcessingPauseNotRecoveredError,
)
from app.services.public_application_workbench_service import (
    PublicApplicationIdentityReviewNotRequiredError,
    public_application_workbench_service,
)


NOW = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)


def make_run(
    *, run_id: int = 21, status: str = "queued", step: str = "extract_text"
) -> PublicApplicationProcessingRunSummary:
    return PublicApplicationProcessingRunSummary(
        id=run_id,
        trigger_type="automatic",
        status=status,
        current_step=step,
        attempt_count=0,
        waiting_reason=None,
        error_code=None,
        error_message=None,
        warning_codes=[],
        started_at=None,
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_summary() -> PublicApplicationWorkbenchSummary:
    return PublicApplicationWorkbenchSummary(
        submission_id=10,
        submission_reference="AP-ABCDEFGH1234",
        submitted_at=NOW,
        identity_review_status="needs_review",
        identity_review_reasons=["same_name"],
        application_id=11,
        candidate_id=12,
        resume_id=13,
        job_id=14,
        candidate_name="虚构候选人",
        job_title="后端工程师",
        job_status="open",
        resume_filename="resume.txt",
        resume_parse_status="uploaded",
        lifecycle_status="active",
        recruitment_stage="applied",
        hr_decision="pending",
        latest_run=make_run(),
    )


def make_detail() -> PublicApplicationWorkbenchDetail:
    return PublicApplicationWorkbenchDetail(
        **make_summary().model_dump(),
        processing_runs=[make_run()],
        identity_candidates=[
            PublicApplicationIdentityCandidate(
                id=12,
                name="虚构候选人",
                phone="13800009999",
                email="fake@example.com",
                source="public_apply",
                created_at=NOW,
                is_submission_candidate=True,
            )
        ],
    )


class PublicApplicationWorkbenchApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.db = Mock()

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_list_returns_safe_unified_queue_summary_and_filters(self) -> None:
        service = AsyncMock(return_value=[make_summary()])
        with patch.object(
            public_application_workbench_service, "list_submissions", service
        ):
            response = self.client.get(
                "/public-application-submissions"
                "?pool=exception&job_id=14&processing_status=queued"
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()[0]
        self.assertEqual(body["application_id"], 11)
        self.assertEqual(body["submission_reference"], "AP-ABCDEFGH1234")
        serialized = response.text.lower()
        for forbidden in (
            "idempotency",
            "request_fingerprint",
            "lease_owner",
            "lease_expires_at",
            "file_path",
        ):
            self.assertNotIn(forbidden, serialized)
        kwargs = service.await_args.kwargs
        self.assertEqual(kwargs["pool"].value, "exception")
        self.assertEqual(kwargs["job_id"], 14)
        self.assertEqual(kwargs["processing_status"].value, "queued")

    def test_detail_returns_safe_run_history_and_identity_candidates(self) -> None:
        with patch.object(
            public_application_workbench_service,
            "get_submission",
            AsyncMock(return_value=make_detail()),
        ) as service:
            response = self.client.get("/public-application-submissions/10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["processing_runs"][0]["id"], 21)
        self.assertTrue(
            response.json()["identity_candidates"][0]["is_submission_candidate"]
        )
        service.assert_awaited_once_with(self.db, 10)

    def test_identity_review_and_retry_require_explicit_confirmation(self) -> None:
        paths = (
            "/public-application-submissions/10/identity-review",
            "/public-application-submissions/10/retry",
        )
        for path in paths:
            for payload in ({}, {"confirmed": False}):
                with self.subTest(path=path, payload=payload):
                    response = self.client.post(path, json=payload)
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(
                        response.json()["detail"]["code"],
                        "HR_ACTION_CONFIRMATION_REQUIRED",
                    )

    def test_identity_review_returns_updated_detail(self) -> None:
        detail = make_detail()
        detail.identity_review_status = PublicApplicationIdentityReviewStatus.REVIEWED
        with patch.object(
            public_application_workbench_service,
            "mark_identity_reviewed",
            AsyncMock(return_value=detail),
        ) as service:
            response = self.client.post(
                "/public-application-submissions/10/identity-review",
                json={"confirmed": True},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["identity_review_status"], "reviewed")
        service.assert_awaited_once_with(self.db, 10)

    def test_retry_returns_created_safe_run(self) -> None:
        retry = make_run(run_id=22)
        retry.trigger_type = ApplicationProcessingTriggerType.MANUAL_RETRY
        with patch.object(
            public_application_workbench_service,
            "create_manual_retry",
            AsyncMock(return_value=retry),
        ):
            response = self.client.post(
                "/public-application-submissions/10/retry",
                json={"confirmed": True},
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["trigger_type"], "manual_retry")
        self.assertNotIn("lease_owner", response.text)

    def test_action_errors_are_stable_and_do_not_echo_exception(self) -> None:
        cases = (
            (
                "mark_identity_reviewed",
                "/public-application-submissions/10/identity-review",
                PublicApplicationIdentityReviewNotRequiredError("postgres secret"),
                "PUBLIC_APPLICATION_IDENTITY_REVIEW_NOT_REQUIRED",
            ),
            (
                "create_manual_retry",
                "/public-application-submissions/10/retry",
                ApplicationProcessingActiveRunError("postgres secret"),
                "APPLICATION_PROCESSING_ACTIVE_RUN",
            ),
            (
                "create_manual_retry",
                "/public-application-submissions/10/retry",
                ApplicationProcessingPauseNotRecoveredError("postgres secret"),
                "APPLICATION_PROCESSING_PAUSE_NOT_RECOVERED",
            ),
        )
        for method, path, error, code in cases:
            with self.subTest(code=code), patch.object(
                public_application_workbench_service,
                method,
                AsyncMock(side_effect=error),
            ):
                response = self.client.post(path, json={"confirmed": True})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["detail"]["code"], code)
            self.assertNotIn("secret", response.text.lower())
            self.assertNotIn("postgres", response.text.lower())

    def test_main_app_registers_internal_routes_outside_public_router(self) -> None:
        paths = {route.path for route in main_app.routes}
        self.assertIn("/api/v2/public-application-submissions", paths)
        self.assertIn(
            "/api/v2/public-application-submissions/{submission_id}/retry",
            paths,
        )
        self.assertNotIn("/api/v2/public/public-application-submissions", paths)
