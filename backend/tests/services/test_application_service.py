from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.application import Application
from app.services.application_service import ApplicationService


TEST_TIME = datetime(2026, 8, 18, tzinfo=timezone.utc)


def make_application(application_id: int = 1) -> Application:
    return Application(
        id=application_id,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage="hr_review",
        hr_decision="pending",
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class ApplicationServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ApplicationService()
        self.db = Mock()
        self.db.get = AsyncMock()
        self.db.scalars = AsyncMock()

    async def test_get_application_uses_primary_key_lookup(self) -> None:
        expected = make_application()
        self.db.get.return_value = expected

        result = await self.service.get_application(self.db, 1)

        self.assertIs(result, expected)
        self.db.get.assert_awaited_once_with(Application, 1)

    async def test_list_applies_all_filters_and_stable_order(self) -> None:
        expected = make_application()
        rows = Mock()
        rows.all.return_value = [expected]
        self.db.scalars.return_value = rows

        result = await self.service.list_applications(
            self.db,
            job_id=3,
            recruitment_stage="hr_review",
            hr_decision="pending",
            lifecycle_status="active",
        )

        self.assertEqual(result, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("applications.job_id", statement)
        self.assertIn("applications.recruitment_stage", statement)
        self.assertIn("applications.hr_decision", statement)
        self.assertIn("applications.lifecycle_status", statement)
        self.assertIn("ORDER BY applications.applied_at DESC", statement)

    async def test_list_without_filters_does_not_add_where_clause(self) -> None:
        rows = Mock()
        rows.all.return_value = []
        self.db.scalars.return_value = rows

        result = await self.service.list_applications(self.db)

        self.assertEqual(result, [])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertNotIn("WHERE", statement)
