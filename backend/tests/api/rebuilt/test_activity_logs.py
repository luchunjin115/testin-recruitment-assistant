from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.activity_logs import router
from app.core.database import get_db
from app.models.rebuilt.activity_log import ActivityLog
from app.schemas.rebuilt.activity_log import ActivityLogCreate
from app.services.rebuilt.activity_log_service import activity_log_service


TEST_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def make_log(log_id: int) -> ActivityLog:
    return ActivityLog(
        id=log_id,
        user_id="hr-001",
        action="report_created",
        target_type="report",
        target_id=7,
        detail={"title": "初筛报告"},
        created_at=TEST_TIME,
    )


class ActivityLogApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_create_returns_201(self) -> None:
        create_mock = AsyncMock(return_value=make_log(1))
        with patch.object(activity_log_service, "create_activity_log", create_mock):
            response = self.client.post(
                "/activity-logs",
                json={
                    "user_id": "hr-001",
                    "action": "report_created",
                    "target_type": "report",
                    "target_id": 7,
                    "detail": {"title": "初筛报告"},
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["detail"], {"title": "初筛报告"})
        self.assertIsInstance(create_mock.await_args.args[1], ActivityLogCreate)

    def test_empty_action_is_rejected_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(activity_log_service, "create_activity_log", create_mock):
            response = self.client.post("/activity-logs", json={"action": ""})
        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_passes_filters_and_limit(self) -> None:
        list_mock = AsyncMock(return_value=[make_log(2)])
        with patch.object(activity_log_service, "list_activity_logs", list_mock):
            response = self.client.get(
                "/activity-logs?target_type=report&target_id=7&action=report_created&user_id=hr-001&limit=20"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(
            self.db, "report", 7, "report_created", "hr-001", 20
        )

    def test_invalid_limit_is_rejected(self) -> None:
        list_mock = AsyncMock()
        with patch.object(activity_log_service, "list_activity_logs", list_mock):
            response = self.client.get("/activity-logs?limit=501")
        self.assertEqual(response.status_code, 422)
        list_mock.assert_not_awaited()

    def test_get_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_log(7), None])
        with patch.object(activity_log_service, "get_activity_log", get_mock):
            found = self.client.get("/activity-logs/7")
            missing = self.client.get("/activity-logs/999")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "操作日志不存在"})

    def test_router_exposes_no_update_or_delete_methods(self) -> None:
        methods = {
            method
            for route in router.routes
            for method in route.methods
            if route.path == "/activity-logs/{activity_log_id}"
        }
        self.assertEqual(methods, {"GET"})
