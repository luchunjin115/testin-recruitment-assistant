from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.applications import install_application_exception_handlers, router
from app.core.database import get_db
from app.models.application import Application
from app.schemas.application import CandidateResolution
from app.services.application_intake_service import (
    ApplicationContactIdentityConflictError,
    ApplicationIntakeResult,
    ApplicationResumeNotFoundError,
    application_intake_service,
)
from app.services.application_service import application_service


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_application(application_id: int = 1) -> Application:
    return Application(
        id=application_id,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage="applied",
        hr_decision="pending",
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def valid_payload() -> dict:
    return {
        "name": "张三",
        "phone": "13800138000",
        "email": "candidate@example.com",
        "job_id": 3,
        "current_resume_id": 4,
        "source": "hr_screening",
    }


class ApplicationApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_application_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_intake_returns_application_without_legacy_ai_fields(self) -> None:
        intake_mock = AsyncMock(
            return_value=ApplicationIntakeResult(
                application=make_application(),
                candidate_resolution=CandidateResolution.CREATED,
                existing_application_reused=False,
                suspected_duplicate_candidate_ids=(9,),
            )
        )
        with patch.object(application_intake_service, "intake", intake_mock):
            response = self.client.post("/applications/intake", json=valid_payload())

        self.assertEqual(response.status_code, 201)
        application = response.json()["application"]
        self.assertNotIn("ai_status", application)
        self.assertNotIn("current_screening_result_id", application)
        self.assertEqual(response.json()["candidate_resolution"], "created")
        self.assertEqual(response.json()["suspected_duplicate_candidate_ids"], [9])

    def test_existing_active_application_returns_200(self) -> None:
        intake_mock = AsyncMock(
            return_value=ApplicationIntakeResult(
                application=make_application(),
                candidate_resolution=CandidateResolution.REUSED,
                existing_application_reused=True,
            )
        )
        with patch.object(application_intake_service, "intake", intake_mock):
            response = self.client.post("/applications/intake", json=valid_payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["existing_application_reused"])

    def test_intake_errors_have_stable_safe_codes(self) -> None:
        cases = (
            (ApplicationResumeNotFoundError("private"), 404, "RESUME_NOT_FOUND"),
            (ApplicationContactIdentityConflictError((2, 3)), 409, "CONTACT_IDENTITY_CONFLICT"),
        )
        for error, status_code, code in cases:
            with self.subTest(code=code), patch.object(
                application_intake_service,
                "intake",
                AsyncMock(side_effect=error),
            ):
                response = self.client.post("/applications/intake", json=valid_payload())
                self.assertEqual(response.status_code, status_code)
                self.assertEqual(response.json()["detail"]["code"], code)
                self.assertNotIn("private", response.text)

    def test_list_uses_public_filters_without_ai_status(self) -> None:
        list_mock = AsyncMock(return_value=[make_application()])
        with patch.object(application_service, "list_applications", list_mock):
            response = self.client.get(
                "/applications?job_id=3&hr_decision=pending&lifecycle_status=active"
            )
        self.assertEqual(response.status_code, 200)
        list_mock.assert_awaited_once_with(
            self.db,
            job_id=3,
            recruitment_stage=None,
            hr_decision="pending",
            lifecycle_status="active",
        )
        ignored_filter_mock = AsyncMock(return_value=[])
        with patch.object(
            application_service,
            "list_applications",
            ignored_filter_mock,
        ):
            invalid = self.client.get("/applications?ai_status=screening")
        self.assertEqual(invalid.status_code, 200)
        ignored_filter_mock.assert_awaited_once_with(
            self.db,
            job_id=None,
            recruitment_stage=None,
            hr_decision=None,
            lifecycle_status=None,
        )

    def test_get_and_removed_screening_routes(self) -> None:
        with patch.object(
            application_service,
            "get_application",
            AsyncMock(side_effect=[make_application(), None]),
        ):
            found = self.client.get("/applications/1")
            missing = self.client.get("/applications/999")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.client.post("/applications/1/screenings", json={}).status_code, 404)
        self.assertEqual(self.client.get("/applications/1/screenings").status_code, 404)
