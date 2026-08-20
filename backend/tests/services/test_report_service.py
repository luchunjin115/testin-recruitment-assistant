from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate
from app.services.report_service import (
    ReportDependencyNotFoundError,
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
        ]
        report = await self.service.create_report(
            self.db,
            ReportCreate(
                candidate_id=10,
                job_id=3,
                title="通用报告",
                content="# 报告内容",
                report_metadata={"version": 1},
            ),
        )

        self.assertEqual(report.candidate_id, 10)
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

    async def test_get_and_filtered_list(self) -> None:
        expected = Report(id=7, candidate_id=10, job_id=3, content="报告")
        self.db.get.return_value = expected
        self.assertIs(await self.service.get_report(self.db, 7), expected)

        scalar_result = Mock()
        scalar_result.all.return_value = [expected]
        self.db.scalars.return_value = scalar_result
        listed = await self.service.list_reports(
            self.db, candidate_id=10, job_id=3
        )
        self.assertEqual(listed, [expected])
        statement = str(self.db.scalars.await_args.args[0])
        self.assertIn("reports.candidate_id", statement)
        self.assertIn("reports.job_id", statement)

    async def test_update_changes_public_fields(self) -> None:
        existing = Report(
            id=4,
            candidate_id=10,
            job_id=3,
            title="旧标题",
            content="旧内容",
        )
        self.db.get.return_value = existing
        report = await self.service.update_report(
            self.db,
            4,
            ReportUpdate(title="新标题", content="新内容"),
        )

        self.assertIs(report, existing)
        self.assertEqual(existing.title, "新标题")
        self.db.commit.assert_awaited_once()

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
