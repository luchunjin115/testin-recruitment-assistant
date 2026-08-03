from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.job import Job
from app.models.rebuilt.report import Report
from app.models.rebuilt.screening_result import ScreeningResult
from app.schemas.rebuilt.report import ReportCreate, ReportUpdate
from app.services.rebuilt.report_service import (
    ReportDependencyNotFoundError,
    ReportScreeningMismatchError,
    ReportService,
)


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.scalars = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class ReportServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ReportService()
        self.db = make_session()

    async def test_create_validates_all_dependencies_and_commits(self) -> None:
        self.db.get.side_effect = [
            Candidate(id=10, name="候选人"),
            Job(id=3, title="岗位"),
            ScreeningResult(id=5, candidate_id=10, job_id=3),
        ]
        report = await self.service.create_report(
            self.db,
            ReportCreate(
                candidate_id=10,
                job_id=3,
                screening_id=5,
                title="初筛报告",
                content="# 报告内容",
                report_metadata={"version": 1},
            ),
        )

        self.assertEqual(report.candidate_id, 10)
        self.assertEqual(report.screening_id, 5)
        self.assertEqual(report.format, "markdown")
        self.db.add.assert_called_once_with(report)
        self.db.commit.assert_awaited_once()

    async def test_create_reports_missing_dependencies(self) -> None:
        self.db.get.return_value = None
        with self.assertRaises(ReportDependencyNotFoundError) as candidate_error:
            await self.service.create_report(
                self.db, ReportCreate(candidate_id=999, job_id=3, content="报告")
            )
        self.assertEqual(candidate_error.exception.resource, "candidate")

        self.db.get.reset_mock()
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), None]
        with self.assertRaises(ReportDependencyNotFoundError) as job_error:
            await self.service.create_report(
                self.db, ReportCreate(candidate_id=10, job_id=999, content="报告")
            )
        self.assertEqual(job_error.exception.resource, "job")

    async def test_create_rejects_missing_or_mismatched_screening(self) -> None:
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), Job(id=3, title="岗位"), None]
        with self.assertRaises(ReportDependencyNotFoundError) as missing_error:
            await self.service.create_report(
                self.db,
                ReportCreate(candidate_id=10, job_id=3, screening_id=999, content="报告"),
            )
        self.assertEqual(missing_error.exception.resource, "screening_result")

        self.db.get.side_effect = [
            Candidate(id=10, name="候选人"),
            Job(id=3, title="岗位"),
            ScreeningResult(id=5, candidate_id=11, job_id=3),
        ]
        with self.assertRaises(ReportScreeningMismatchError):
            await self.service.create_report(
                self.db,
                ReportCreate(candidate_id=10, job_id=3, screening_id=5, content="报告"),
            )
        self.db.add.assert_not_called()

    async def test_get_and_filtered_list(self) -> None:
        expected = Report(id=7, candidate_id=10, job_id=3, content="报告")
        self.db.get.return_value = expected
        self.assertIs(await self.service.get_report(self.db, 7), expected)

        scalar_result = Mock()
        scalar_result.all.return_value = [expected]
        self.db.scalars.return_value = scalar_result
        listed = await self.service.list_reports(
            self.db, candidate_id=10, job_id=3, screening_id=5
        )
        self.assertEqual(listed, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("reports.candidate_id", statement)
        self.assertIn("reports.job_id", statement)
        self.assertIn("reports.screening_id", statement)

    async def test_update_validates_new_screening_and_updates_fields(self) -> None:
        existing = Report(
            id=4,
            candidate_id=10,
            job_id=3,
            screening_id=None,
            title="旧标题",
            content="旧内容",
        )
        self.db.get.side_effect = [
            existing,
            ScreeningResult(id=5, candidate_id=10, job_id=3),
        ]
        report = await self.service.update_report(
            self.db,
            4,
            ReportUpdate(screening_id=5, title="新标题", content="新内容"),
        )

        self.assertIs(report, existing)
        self.assertEqual(existing.screening_id, 5)
        self.assertEqual(existing.title, "新标题")
        self.db.commit.assert_awaited_once()

    async def test_update_can_unlink_screening_without_lookup(self) -> None:
        existing = Report(id=4, candidate_id=10, job_id=3, screening_id=5, content="报告")
        self.db.get.return_value = existing
        report = await self.service.update_report(
            self.db, 4, ReportUpdate(screening_id=None)
        )
        self.assertIsNone(report.screening_id)
        self.db.get.assert_awaited_once_with(Report, 4)

    async def test_update_and_delete_not_found(self) -> None:
        self.db.get.return_value = None
        self.assertIsNone(
            await self.service.update_report(self.db, 999, ReportUpdate(title="新标题"))
        )
        self.assertFalse(await self.service.delete_report(self.db, 999))
        self.db.commit.assert_not_awaited()

    async def test_delete_commits_when_found(self) -> None:
        existing = Report(id=6, candidate_id=10, job_id=3, content="报告")
        self.db.get.return_value = existing
        self.assertTrue(await self.service.delete_report(self.db, 6))
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_write_failure_rolls_back(self) -> None:
        self.db.get.side_effect = [Candidate(id=10, name="候选人"), Job(id=3, title="岗位")]
        self.db.commit.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_report(
                self.db, ReportCreate(candidate_id=10, job_id=3, content="报告")
            )
        self.db.rollback.assert_awaited_once()
