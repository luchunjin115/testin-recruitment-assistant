from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.applications import install_application_exception_handlers, router
from app.core.database import get_db
from app.models.application import Application
from app.models.screening_result import ScreeningResult
from app.schemas.application import CandidateResolution
from app.services.application_intake_service import (
    ApplicationContactIdentityConflictError,
    ApplicationIntakeResult,
    ApplicationJobNotOpenError,
    ApplicationResumeNotFoundError,
    ApplicationResumeOwnershipConflictError,
    application_intake_service,
)
from app.services.application_service import application_service
from app.services.screening_result_service import screening_result_service
from app.services.screening_service import (
    ScreeningAlreadyRunningError,
    ScreeningApplicationNotFoundError,
    ScreeningJobNotOpenError,
    ScreeningNotAllowedError,
    ScreeningResumeRequiredError,
    ScreeningRubricInvalidError,
    ScreeningRubricStaleError,
    ScreeningRunOutcome,
    screening_service,
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


def make_screening_result(result_id: int = 8) -> ScreeningResult:
    return ScreeningResult(
        id=result_id,
        candidate_id=2,
        job_id=3,
        application_id=1,
        resume_id=4,
        attempt_number=2,
        execution_status="completed",
        input_fingerprint="a" * 64,
        overall_score=86,
        hard_pass=True,
        recommendation="strong_recommend",
        evidence_coverage_rate=Decimal("0.9000"),
        strengths=["项目证据充分"],
        risks=[],
        hard_requirement_checks=[],
        dimension_scores={},
        pending_questions=[],
        resume_evidence=[],
        job_evidence=[],
        candidate_input_snapshot={"application_ref": "application-1"},
        resume_snapshot={"resume_id": 4},
        job_requirements_snapshot={"schema_version": "1.0"},
        rubric_snapshot={"version": 1},
        force_rerun=False,
        is_outdated=False,
        started_at=TEST_TIME,
        finished_at=TEST_TIME,
        duration_ms=1200,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


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

    def test_list_and_detail_use_application_query_service(self) -> None:
        list_mock = AsyncMock(return_value=[make_application()])
        get_mock = AsyncMock(side_effect=[make_application(), None])
        with (
            patch.object(application_service, "list_applications", list_mock),
            patch.object(application_service, "get_application", get_mock),
        ):
            listed = self.client.get(
                "/applications?job_id=3&recruitment_stage=applied"
                "&ai_status=not_started&hr_decision=pending"
                "&lifecycle_status=active"
            )
            found = self.client.get("/applications/1")
            missing = self.client.get("/applications/999")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["id"], 1)
        list_mock.assert_awaited_once_with(
            self.db,
            job_id=3,
            recruitment_stage="applied",
            ai_status="not_started",
            hr_decision="pending",
            lifecycle_status="active",
        )
        self.assertEqual(found.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"]["code"], "APPLICATION_NOT_FOUND")

    def test_invalid_list_filter_is_rejected_before_service(self) -> None:
        list_mock = AsyncMock()
        with patch.object(application_service, "list_applications", list_mock):
            response = self.client.get("/applications?ai_status=queued")

        self.assertEqual(response.status_code, 422)
        list_mock.assert_not_awaited()

    def test_single_screening_returns_result_and_execution_metadata(self) -> None:
        run_mock = AsyncMock(
            return_value=ScreeningRunOutcome(
                result=make_screening_result(),
                reused=False,
                model_called=True,
            )
        )
        with patch.object(screening_service, "run", run_mock):
            response = self.client.post("/applications/1/screenings", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["attempt_number"], 2)
        self.assertEqual(response.json()["result"]["overall_score"], 86)
        self.assertTrue(response.json()["model_called"])
        passed_db, passed_application_id, passed_request = run_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_application_id, 1)
        self.assertFalse(passed_request.force)
        self.assertEqual(run_mock.await_args.kwargs["actor_type"], "hr")

    def test_single_screening_errors_have_stable_safe_codes(self) -> None:
        cases = (
            (ScreeningApplicationNotFoundError("private"), 404, "APPLICATION_NOT_FOUND"),
            (ScreeningAlreadyRunningError("private"), 409, "SCREENING_ALREADY_RUNNING"),
            (ScreeningResumeRequiredError("private"), 422, "APPLICATION_RESUME_REQUIRED"),
            (ScreeningJobNotOpenError("private"), 409, "JOB_NOT_OPEN_FOR_SCREENING"),
            (ScreeningRubricInvalidError("private"), 422, "RUBRIC_CRITERIA_INVALID"),
            (ScreeningRubricStaleError("private"), 409, "RUBRIC_DRAFT_STALE"),
            (ScreeningNotAllowedError("private"), 409, "SCREENING_NOT_ALLOWED"),
            (RuntimeError("postgresql://private"), 500, "SCREENING_OPERATION_FAILED"),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(code=expected_code), patch.object(
                screening_service,
                "run",
                AsyncMock(side_effect=error),
            ):
                response = self.client.post("/applications/1/screenings", json={})

            self.assertEqual(response.status_code, expected_status)
            self.assertEqual(response.json()["detail"]["code"], expected_code)
            self.assertNotIn("private", response.text)

    def test_screening_history_is_scoped_to_existing_application(self) -> None:
        get_mock = AsyncMock(side_effect=[make_application(), None])
        history_mock = AsyncMock(return_value=[make_screening_result()])
        with (
            patch.object(application_service, "get_application", get_mock),
            patch.object(
                screening_result_service,
                "list_screening_results",
                history_mock,
            ),
        ):
            found = self.client.get("/applications/1/screenings")
            missing = self.client.get("/applications/999/screenings")

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()[0]["execution_status"], "completed")
        self.assertEqual(found.json()[0]["evidence_coverage_rate"], "0.9000")
        history_mock.assert_awaited_once_with(self.db, application_id=1)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"]["code"], "APPLICATION_NOT_FOUND")
