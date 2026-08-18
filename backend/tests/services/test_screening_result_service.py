from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.screening_result import ScreeningResult
from app.services.screening_result_service import ScreeningResultService


def make_session() -> Mock:
    session = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


class ScreeningResultServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ScreeningResultService()
        self.db = make_session()

    async def test_get_only_returns_application_results_with_resume(self) -> None:
        expected = ScreeningResult(
            id=7,
            candidate_id=10,
            job_id=3,
            application_id=20,
            resume_id=4,
        )
        self.db.scalar.return_value = expected

        result = await self.service.get_screening_result(self.db, 7)

        self.assertIs(result, expected)
        statement = str(self.db.scalar.await_args.args[0])
        self.assertIn("screening_results.id", statement)
        self.assertIn("screening_results.application_id IS NOT NULL", statement)
        self.assertIn("screening_results.resume_id IS NOT NULL", statement)

    async def test_list_filters_application_results_and_orders_attempts(self) -> None:
        expected = ScreeningResult(
            id=7,
            candidate_id=10,
            job_id=3,
            application_id=20,
            resume_id=4,
            attempt_number=2,
        )
        scalar_result = Mock()
        scalar_result.all.return_value = [expected]
        self.db.scalars.return_value = scalar_result

        listed = await self.service.list_screening_results(
            self.db,
            candidate_id=10,
            job_id=3,
            application_id=20,
        )

        self.assertEqual(listed, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("screening_results.application_id IS NOT NULL", statement)
        self.assertIn("screening_results.resume_id IS NOT NULL", statement)
        self.assertIn("screening_results.candidate_id", statement)
        self.assertIn("screening_results.job_id", statement)
        self.assertIn("screening_results.application_id", statement)
        self.assertIn("screening_results.attempt_number DESC", statement)

    async def test_list_without_application_filter_orders_latest_updates(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = []
        self.db.scalars.return_value = scalar_result

        await self.service.list_screening_results(self.db)

        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("screening_results.updated_at DESC", statement)
