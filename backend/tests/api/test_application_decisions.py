from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.applications import install_application_exception_handlers, router
from app.core.database import get_db
from app.models.application import Application
from app.models.stage_history import StageHistory
from app.services.application_decision_service import (
    ApplicationNotFoundError,
    InvalidApplicationTransitionError,
    application_decision_service,
)


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_application(
    *,
    lifecycle_status: str = "active",
    recruitment_stage: str = "hr_review",
    hr_decision: str = "pending",
) -> Application:
    return Application(
        id=1,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status=lifecycle_status,
        recruitment_stage=recruitment_stage,
        hr_decision=hr_decision,
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def make_history() -> StageHistory:
    return StageHistory(
        id=8,
        application_id=1,
        from_recruitment_stage="hr_review",
        to_recruitment_stage="screening_passed",
        from_hr_decision="pending",
        to_hr_decision="passed",
        reason_code="meets_requirements",
        reason_detail=None,
        actor_type="hr",
        actor_id=None,
        actor_label="本地 HR（未认证）",
        created_at=TEST_TIME,
    )


class ApplicationDecisionApiTest(TestCase):
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

    def test_all_five_decision_routes_call_service_and_return_application(self) -> None:
        cases = (
            (
                "/applications/1/pass",
                "hr_direct_pass",
                {"reason_code": "meets_requirements"},
                make_application(
                    recruitment_stage="screening_passed",
                    hr_decision="passed",
                ),
            ),
            (
                "/applications/1/backup",
                "backup_application",
                {
                    "reason_code": "waiting_for_comparison",
                    "reason_detail": "等待同岗位候选人比较",
                },
                make_application(recruitment_stage="backup", hr_decision="backup"),
            ),
            (
                "/applications/1/reject",
                "reject_application",
                {
                    "reason_code": "role_mismatch",
                    "reason_detail": "岗位方向不匹配",
                    "confirmed": True,
                },
                make_application(
                    lifecycle_status="ended",
                    recruitment_stage="rejected",
                    hr_decision="rejected",
                ),
            ),
            (
                "/applications/1/undo-rejection",
                "undo_rejection",
                {
                    "reason_code": "decision_correction",
                    "reason_detail": "修正错误决定",
                },
                make_application(),
            ),
            (
                "/applications/1/void",
                "void_application",
                {"reason_code": "entry_error", "confirmed": True},
                make_application(lifecycle_status="voided"),
            ),
        )
        for path, method_name, payload, application in cases:
            with self.subTest(path=path):
                service_mock = AsyncMock(return_value=application)
                with patch.object(
                    application_decision_service,
                    method_name,
                    service_mock,
                ):
                    response = self.client.post(path, json=payload)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["id"], 1)
                passed_db, application_id, request = service_mock.await_args.args
                self.assertIs(passed_db, self.db)
                self.assertEqual(application_id, 1)
                self.assertEqual(request.reason_code.value, payload["reason_code"])

    def test_history_route_returns_ordered_audit_contract(self) -> None:
        history_mock = AsyncMock(return_value=[make_history()])

        with patch.object(
            application_decision_service,
            "list_history",
            history_mock,
        ):
            response = self.client.get("/applications/1/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["reason_code"], "meets_requirements")
        history_mock.assert_awaited_once_with(self.db, 1)

    def test_not_found_and_invalid_transition_have_stable_codes(self) -> None:
        cases = (
            (ApplicationNotFoundError("private"), 404, "APPLICATION_NOT_FOUND"),
            (
                InvalidApplicationTransitionError("private"),
                409,
                "INVALID_APPLICATION_TRANSITION",
            ),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(code=expected_code):
                with patch.object(
                    application_decision_service,
                    "hr_direct_pass",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/applications/1/pass",
                        json={"reason_code": "meets_requirements"},
                    )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_confirmation_and_reason_contracts_reject_invalid_requests(self) -> None:
        cases = (
            (
                "/applications/1/reject",
                {"reason_code": "role_mismatch", "confirmed": False},
                "reject_application",
            ),
            (
                "/applications/1/void",
                {"reason_code": "entry_error", "confirmed": False},
                "void_application",
            ),
            (
                "/applications/1/undo-rejection",
                {"reason_code": "new_evidence"},
                "undo_rejection",
            ),
            (
                "/applications/1/pass",
                {"reason_code": "role_mismatch"},
                "hr_direct_pass",
            ),
        )
        for path, payload, method_name in cases:
            with self.subTest(path=path):
                service_mock = AsyncMock()
                with patch.object(
                    application_decision_service,
                    method_name,
                    service_mock,
                ):
                    response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 422)
                service_mock.assert_not_awaited()

    def test_unexpected_failure_is_sanitized(self) -> None:
        with patch.object(
            application_decision_service,
            "void_application",
            AsyncMock(side_effect=RuntimeError("postgresql://private")),
        ):
            response = self.client.post(
                "/applications/1/void",
                json={"reason_code": "entry_error", "confirmed": True},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "APPLICATION_OPERATION_FAILED",
        )
        self.assertNotIn("postgresql", response.text)

    def test_openapi_registers_decision_and_history_routes_once(self) -> None:
        expected_routes = {
            ("POST", "/applications/{application_id}/pass"),
            ("POST", "/applications/{application_id}/backup"),
            ("POST", "/applications/{application_id}/reject"),
            ("POST", "/applications/{application_id}/undo-rejection"),
            ("POST", "/applications/{application_id}/void"),
            ("GET", "/applications/{application_id}/history"),
        }
        actual_routes = [
            (method, route.path)
            for route in self.app.routes
            for method in getattr(route, "methods", set())
            if (method, route.path) in expected_routes
        ]
        self.assertEqual(set(actual_routes), expected_routes)
        self.assertEqual(len(actual_routes), len(expected_routes))
