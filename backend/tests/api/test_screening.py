from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.screening import install_screening_exception_handlers, router
from app.core.database import get_db
from app.main import app as main_app
from app.models.application import Application
from app.models.screening_run import ScreeningRun
from app.services.screening_service import (
    ScreeningApplicationNotFoundError,
    ScreeningBatchFailure,
    ScreeningBatchResult,
    ScreeningBatchJobMismatchError,
    ScreeningStateResult,
    ScreeningTriggerResult,
    screening_service,
)


NOW = datetime(2026, 8, 20, tzinfo=timezone.utc)


def make_run(application_id: int = 1, run_id: int = 10) -> ScreeningRun:
    return ScreeningRun(
        id=run_id,
        application_id=application_id,
        job_id=3,
        resume_id=4,
        job_evaluation_plan_id=5,
        trigger_type="automatic",
        status="queued",
        input_fingerprint="a" * 64,
        prompt_version="screening_evaluation_v3",
        model_version="fake-model",
        schema_version="2.0",
        redaction_version="screening_redaction_v1",
        evaluation_reference_at=NOW,
        evaluation_timezone="Asia/Shanghai",
        experience_period_facts_rule_version="experience_period_facts_v1",
        experience_period_facts_fingerprint="b" * 64,
        attempt_count=0,
        created_at=NOW,
        updated_at=NOW,
    )


def make_application() -> Application:
    return Application(
        id=1,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage="applied",
        hr_decision="pending",
        applied_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


class ScreeningApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_screening_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock()

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_get_state_returns_only_current_report_and_latest_run_contract(self) -> None:
        state = ScreeningStateResult(1, None, make_run())
        with patch.object(screening_service, "get_state", AsyncMock(return_value=state)):
            response = self.client.get("/applications/1/screening")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["latest_run"]["status"], "queued")
        self.assertEqual(
            response.json()["latest_run"]["evaluation_reference_at"],
            "2026-08-20T00:00:00Z",
        )
        self.assertEqual(
            response.json()["latest_run"]["evaluation_timezone"],
            "Asia/Shanghai",
        )
        serialized = response.text.lower()
        self.assertNotIn("raw_response", serialized)
        self.assertNotIn("resume_text", serialized)
        self.assertNotIn("api_key", serialized)

    def test_list_reports_exposes_current_and_history_endpoint(self) -> None:
        with patch.object(
            screening_service,
            "list_reports",
            AsyncMock(return_value=[]),
        ) as service_mock:
            response = self.client.get("/applications/1/screening/reports")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        service_mock.assert_awaited_once_with(self.db, 1)

    def test_normal_and_single_reassessment_return_accepted_run_ids(self) -> None:
        normal = ScreeningTriggerResult(1, make_run(), None)
        reassessed_run = make_run(run_id=11)
        reassessed_run.trigger_type = "single_reassessment"
        reassessed = ScreeningTriggerResult(1, reassessed_run, None)
        with patch.object(
            screening_service,
            "trigger",
            AsyncMock(side_effect=[normal, reassessed]),
        ) as trigger:
            first = self.client.post("/applications/1/screening")
            second = self.client.post(
                "/applications/1/screening/re-evaluate",
                json={"confirmed": True},
            )
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["run"]["id"], 10)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.json()["run"]["trigger_type"], "single_reassessment")
        self.assertEqual(trigger.await_count, 2)

    def test_batch_returns_each_application_run(self) -> None:
        results = ScreeningBatchResult(
            job_id=3,
            total_count=2,
            reused_count=0,
            queued_count=2,
            results=(
                ScreeningTriggerResult(1, make_run(1, 10), None),
                ScreeningTriggerResult(2, make_run(2, 11), None),
            ),
            failures=(),
        )
        with patch.object(
            screening_service,
            "trigger_batch_reassessment",
            AsyncMock(return_value=results),
        ):
            response = self.client.post(
                "/jobs/3/screening/re-evaluate-batch",
                json={"application_ids": [1, 2], "confirmed": True},
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual([item["run"]["id"] for item in response.json()["results"]], [10, 11])

    def test_batch_rejects_more_than_five_before_service(self) -> None:
        service_mock = AsyncMock()
        with patch.object(
            screening_service,
            "trigger_batch_reassessment",
            service_mock,
        ):
            response = self.client.post(
                "/jobs/3/screening/re-evaluate-batch",
                json={"application_ids": list(range(1, 7)), "confirmed": True},
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "SCREENING_BATCH_SIZE_INVALID",
        )
        service_mock.assert_not_awaited()

    def test_batch_returns_stable_partial_failure_counts(self) -> None:
        batch = ScreeningBatchResult(
            job_id=3,
            total_count=2,
            reused_count=0,
            queued_count=1,
            results=(ScreeningTriggerResult(1, make_run(1, 10), None),),
            failures=(
                ScreeningBatchFailure(
                    application_id=2,
                    error_code="SCREENING_APPLICATION_NOT_ELIGIBLE",
                    error_message="该 Application 当前不可重新评估",
                    retryable=False,
                ),
            ),
        )
        with patch.object(
            screening_service,
            "trigger_batch_reassessment",
            AsyncMock(return_value=batch),
        ):
            response = self.client.post(
                "/jobs/3/screening/re-evaluate-batch",
                json={"application_ids": [1, 2], "confirmed": True},
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["total_count"], 2)
        self.assertEqual(response.json()["queued_count"], 1)
        self.assertEqual(response.json()["failed_count"], 1)
        self.assertFalse(response.json()["failures"][0]["retryable"])

    def test_reassessment_requires_explicit_true_confirmation(self) -> None:
        paths = (
            ("/applications/1/screening/re-evaluate", {}),
            ("/applications/1/screening/re-evaluate", {"confirmed": False}),
            (
                "/jobs/3/screening/re-evaluate-batch",
                {"application_ids": [1]},
            ),
            (
                "/jobs/3/screening/re-evaluate-batch",
                {"application_ids": [1], "confirmed": False},
            ),
        )
        for path, payload in paths:
            with self.subTest(path=path, payload=payload):
                response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.json()["detail"]["code"],
                    "SCREENING_REASSESSMENT_CONFIRMATION_REQUIRED",
                )

    def test_errors_are_stable_and_do_not_echo_private_exception(self) -> None:
        cases = (
            (
                "get_state",
                "get",
                "/applications/99/screening",
                ScreeningApplicationNotFoundError("postgresql://secret"),
                404,
                "APPLICATION_NOT_FOUND",
            ),
            (
                "trigger_batch_reassessment",
                "post",
                "/jobs/3/screening/re-evaluate-batch",
                ScreeningBatchJobMismatchError("secret SQL"),
                422,
                "SCREENING_BATCH_JOB_MISMATCH",
            ),
        )
        for method, verb, path, error, expected_status, code in cases:
            with self.subTest(code=code), patch.object(
                screening_service,
                method,
                AsyncMock(side_effect=error),
            ):
                kwargs = (
                    {"json": {"application_ids": [1], "confirmed": True}}
                    if verb == "post"
                    else {}
                )
                response = getattr(self.client, verb)(path, **kwargs)
            self.assertEqual(response.status_code, expected_status)
            self.assertEqual(response.json()["detail"]["code"], code)
            self.assertNotIn("secret", response.text.lower())
            self.assertNotIn("postgresql", response.text.lower())

    def test_resume_switch_uses_internal_application_contract(self) -> None:
        with patch.object(
            screening_service,
            "switch_current_resume",
            AsyncMock(return_value=make_application()),
        ) as service_mock:
            response = self.client.put(
                "/applications/1/current-resume",
                json={"resume_id": 4},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_resume_id"], 4)
        service_mock.assert_awaited_once_with(self.db, 1, 4)

    def test_full_openapi_registers_each_screening_route_once(self) -> None:
        keys = [
            (route.path, method)
            for route in main_app.routes
            for method in getattr(route, "methods", set())
            if "screening" in route.path or "current-resume" in route.path
        ]
        self.assertEqual(len(keys), len(set(keys)))
        schema = main_app.openapi()
        self.assertIn("/api/v2/applications/{application_id}/screening", schema["paths"])
