from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from sqlalchemy.exc import IntegrityError

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.job import Job
from app.models.rebuilt.screening_result import ScreeningResult
from app.schemas.rebuilt.screening_result import (
    ScreeningResultCreate,
    ScreeningResultUpdate,
)
from app.services.rebuilt.screening_result_service import (
    ScreeningResultAlreadyExistsError,
    ScreeningResultDependencyNotFoundError,
    ScreeningResultService,
)


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class ScreeningResultServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ScreeningResultService()
        self.db = make_session()

    async def test_create_checks_dependencies_and_commits(self) -> None:
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), Job(id=3, title="岗位")]
        self.db.scalar.return_value = None
        result = await self.service.create_screening_result(
            self.db,
            ScreeningResultCreate(
                candidate_id=10,
                job_id=3,
                overall_score=88,
                strengths=["技能匹配"],
            ),
        )

        self.assertEqual(result.candidate_id, 10)
        self.assertEqual(result.job_id, 3)
        self.assertEqual(result.overall_score, 88)
        self.db.add.assert_called_once_with(result)
        self.db.commit.assert_awaited_once()

    async def test_create_reports_missing_candidate_or_job(self) -> None:
        self.db.get.return_value = None
        with self.assertRaises(ScreeningResultDependencyNotFoundError) as candidate_error:
            await self.service.create_screening_result(
                self.db, ScreeningResultCreate(candidate_id=999, job_id=3)
            )
        self.assertEqual(candidate_error.exception.resource, "candidate")

        self.db.get.reset_mock()
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), None]
        with self.assertRaises(ScreeningResultDependencyNotFoundError) as job_error:
            await self.service.create_screening_result(
                self.db, ScreeningResultCreate(candidate_id=10, job_id=999)
            )
        self.assertEqual(job_error.exception.resource, "job")
        self.db.add.assert_not_called()

    async def test_create_rejects_existing_candidate_job_pair(self) -> None:
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), Job(id=3, title="岗位")]
        self.db.scalar.return_value = 7

        with self.assertRaises(ScreeningResultAlreadyExistsError):
            await self.service.create_screening_result(
                self.db, ScreeningResultCreate(candidate_id=10, job_id=3)
            )

        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_integrity_error_rolls_back_and_becomes_duplicate_error(self) -> None:
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), Job(id=3, title="岗位")]
        self.db.scalar.return_value = None
        self.db.commit.side_effect = IntegrityError("insert", {}, Exception("unique"))

        with self.assertRaises(ScreeningResultAlreadyExistsError):
            await self.service.create_screening_result(
                self.db, ScreeningResultCreate(candidate_id=10, job_id=3)
            )

        self.db.rollback.assert_awaited_once()

    async def test_get_and_filtered_list(self) -> None:
        expected = ScreeningResult(id=7, candidate_id=10, job_id=3)
        self.db.get.return_value = expected
        self.assertIs(await self.service.get_screening_result(self.db, 7), expected)

        scalar_result = Mock()
        scalar_result.all.return_value = [expected]
        self.db.scalars.return_value = scalar_result
        listed = await self.service.list_screening_results(self.db, candidate_id=10, job_id=3)
        self.assertEqual(listed, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("screening_results.candidate_id", statement)
        self.assertIn("screening_results.job_id", statement)

    async def test_update_only_changes_requested_fields(self) -> None:
        existing = ScreeningResult(
            id=4,
            candidate_id=10,
            job_id=3,
            overall_score=70,
            recommendation="待定",
        )
        self.db.get.return_value = existing
        result = await self.service.update_screening_result(
            self.db,
            4,
            ScreeningResultUpdate(overall_score=90, recommendation="推荐"),
        )

        self.assertIs(result, existing)
        self.assertEqual(existing.overall_score, 90)
        self.assertEqual(existing.recommendation, "推荐")
        self.assertEqual(existing.job_id, 3)
        self.db.commit.assert_awaited_once()

    async def test_update_and_delete_not_found(self) -> None:
        self.db.get.return_value = None
        self.assertIsNone(
            await self.service.update_screening_result(
                self.db, 999, ScreeningResultUpdate(overall_score=80)
            )
        )
        self.assertFalse(await self.service.delete_screening_result(self.db, 999))
        self.db.commit.assert_not_awaited()

    async def test_delete_commits_when_found(self) -> None:
        existing = ScreeningResult(id=5, candidate_id=10, job_id=3)
        self.db.get.return_value = existing
        self.assertTrue(await self.service.delete_screening_result(self.db, 5))
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()
