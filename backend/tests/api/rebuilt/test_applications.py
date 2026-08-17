from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.applications import install_application_exception_handlers, router
from app.core.database import get_db
from app.models.rebuilt.application import Application
from app.schemas.rebuilt.application import CandidateResolution
from app.services.rebuilt.application_intake_service import (
    ApplicationContactIdentityConflictError,
    ApplicationIntakeResult,
    ApplicationJobNotOpenError,
    ApplicationResumeNotFoundError,
    ApplicationResumeOwnershipConflictError,
    application_intake_service,
)


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
        ai_status="not_started",
        hr_decision="pending",
        current_screening_result_id=None,
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
        legacy_stage=None,
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

    def test_new_application_returns_201_and_strict_response(self) -> None:
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
        self.assertEqual(response.json()["application"]["ai_status"], "not_started")
        self.assertEqual(response.json()["candidate_resolution"], "created")
        self.assertEqual(response.json()["suspected_duplicate_candidate_ids"], [9])
        passed_db, passed_data = intake_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_data.email, "candidate@example.com")

    def test_existing_active_application_returns_200_without_duplicate(self) -> None:
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

    def test_business_errors_have_stable_safe_codes(self) -> None:
        cases = (
            (ApplicationResumeNotFoundError("private"), 404, "RESUME_NOT_FOUND"),
            (
                ApplicationContactIdentityConflictError((2, 3)),
                409,
                "CONTACT_IDENTITY_CONFLICT",
            ),
            (
                ApplicationJobNotOpenError("private"),
                409,
                "JOB_NOT_OPEN_FOR_SCREENING",
            ),
            (
                ApplicationResumeOwnershipConflictError("private"),
                409,
                "RESUME_OWNERSHIP_CONFLICT",
            ),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(code=expected_code):
                with patch.object(
                    application_intake_service,
                    "intake",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/applications/intake",
                        json=valid_payload(),
                    )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_contact_and_resume_validation_have_stable_422_codes(self) -> None:
        for field, expected_code in (
            ("phone", "APPLICATION_CONTACT_REQUIRED"),
            ("email", "APPLICATION_CONTACT_REQUIRED"),
            ("current_resume_id", "APPLICATION_RESUME_REQUIRED"),
        ):
            payload = valid_payload()
            payload.pop(field)
            with self.subTest(field=field):
                response = self.client.post("/applications/intake", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"]["code"], expected_code)

    def test_unknown_failure_is_sanitized(self) -> None:
        with patch.object(
            application_intake_service,
            "intake",
            AsyncMock(side_effect=RuntimeError("postgresql://private candidate@example.com")),
        ):
            response = self.client.post("/applications/intake", json=valid_payload())

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "APPLICATION_OPERATION_FAILED",
        )
        self.assertNotIn("postgresql", response.text)
        self.assertNotIn("candidate@example.com", response.text)

    def test_openapi_registers_intake_once(self) -> None:
        operation = self.app.openapi()["paths"]["/applications/intake"]["post"]
        self.assertEqual(operation["tags"], ["applications"])
        self.assertEqual(
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ApplicationIntakeRequest",
        )
        matching_routes = [
            route
            for route in self.app.routes
            if getattr(route, "path", None) == "/applications/intake"
            and "POST" in getattr(route, "methods", set())
        ]
        self.assertEqual(len(matching_routes), 1)

