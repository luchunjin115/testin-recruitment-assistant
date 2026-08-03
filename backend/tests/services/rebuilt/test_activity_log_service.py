from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.activity_log import ActivityLog
from app.schemas.rebuilt.activity_log import ActivityLogCreate
from app.services.rebuilt.activity_log_service import ActivityLogService


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.scalars = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class ActivityLogServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ActivityLogService()
        self.db = make_session()

    async def test_create_commits_append_only_record(self) -> None:
        log = await self.service.create_activity_log(
            self.db,
            ActivityLogCreate(
                user_id="hr-001",
                action="report_created",
                target_type="report",
                target_id=7,
                detail={"title": "初筛报告"},
            ),
        )

        self.assertEqual(log.action, "report_created")
        self.assertEqual(log.target_type, "report")
        self.assertEqual(log.detail, {"title": "初筛报告"})
        self.db.add.assert_called_once_with(log)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(log)

    async def test_create_failure_rolls_back(self) -> None:
        self.db.commit.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_activity_log(
                self.db, ActivityLogCreate(action="rollback_test")
            )
        self.db.rollback.assert_awaited_once()

    async def test_get_returns_database_result(self) -> None:
        expected = ActivityLog(id=7, action="candidate_created")
        self.db.get.return_value = expected
        self.assertIs(await self.service.get_activity_log(self.db, 7), expected)
        self.db.get.assert_awaited_once_with(ActivityLog, 7)

    async def test_list_applies_filters_order_and_limit(self) -> None:
        expected = ActivityLog(
            id=8,
            user_id="hr-001",
            action="report_created",
            target_type="report",
            target_id=7,
        )
        scalar_result = Mock()
        scalar_result.all.return_value = [expected]
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_activity_logs(
            self.db,
            target_type="report",
            target_id=7,
            action="report_created",
            user_id="hr-001",
            limit=20,
        )

        self.assertEqual(result, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("activity_logs.target_type", statement)
        self.assertIn("activity_logs.target_id", statement)
        self.assertIn("activity_logs.action", statement)
        self.assertIn("activity_logs.user_id", statement)
        self.assertIn("LIMIT", statement)

    async def test_list_allows_no_filters(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = []
        self.db.scalars.return_value = scalar_result
        self.assertEqual(await self.service.list_activity_logs(self.db), [])
        self.db.scalars.assert_awaited_once()
