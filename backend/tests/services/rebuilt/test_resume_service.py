from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeUpdate
from app.services.rebuilt.resume_service import ResumeService


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


class ResumeServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ResumeService()
        self.db = make_session()

    async def test_create_resume_commits_and_refreshes(self) -> None:
        data = ResumeCreate(
            candidate_id=10,
            job_id=3,
            filename="zhangsan.pdf",
            file_path="uploads/zhangsan.pdf",
            file_type="pdf",
            file_size=1024,
        )

        resume = await self.service.create_resume(self.db, data)

        self.assertEqual(resume.candidate_id, 10)
        self.assertEqual(resume.job_id, 3)
        self.assertEqual(resume.filename, "zhangsan.pdf")
        self.assertEqual(resume.parse_status, "uploaded")
        self.db.add.assert_called_once_with(resume)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(resume)
        self.db.rollback.assert_not_awaited()

    async def test_get_resume_returns_database_result(self) -> None:
        expected = Resume(id=7, candidate_id=10, filename="resume.pdf", file_path="uploads/resume.pdf")
        self.db.get.return_value = expected

        resume = await self.service.get_resume(self.db, 7)

        self.assertIs(resume, expected)
        self.db.get.assert_awaited_once_with(Resume, 7)

    async def test_list_resumes_returns_scalar_rows(self) -> None:
        resumes = [
            Resume(id=2, candidate_id=10, filename="new.pdf", file_path="uploads/new.pdf"),
            Resume(id=1, candidate_id=10, filename="old.pdf", file_path="uploads/old.pdf"),
        ]
        scalar_result = Mock()
        scalar_result.all.return_value = resumes
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_resumes(self.db)

        self.assertEqual(result, resumes)
        self.db.scalars.assert_awaited_once()

    async def test_update_resume_only_changes_fields_in_request(self) -> None:
        existing = Resume(
            id=3,
            candidate_id=10,
            job_id=4,
            filename="resume.pdf",
            file_path="uploads/resume.pdf",
            parse_status="uploaded",
        )
        self.db.get.return_value = existing
        parsed_at = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)

        resume = await self.service.update_resume(
            self.db,
            3,
            ResumeUpdate(
                job_id=None,
                raw_text="parsed resume text",
                parse_status="parsed",
                parsed_snapshot={"name": "Zhang San"},
                parsed_at=parsed_at,
            ),
        )

        self.assertIs(resume, existing)
        self.assertEqual(existing.candidate_id, 10)
        self.assertIsNone(existing.job_id)
        self.assertEqual(existing.filename, "resume.pdf")
        self.assertEqual(existing.file_path, "uploads/resume.pdf")
        self.assertEqual(existing.parse_status, "parsed")
        self.assertEqual(existing.parsed_snapshot, {"name": "Zhang San"})
        self.assertEqual(existing.parsed_at, parsed_at)
        self.db.commit.assert_awaited_once()

    async def test_update_resume_returns_none_when_not_found(self) -> None:
        self.db.get.return_value = None

        resume = await self.service.update_resume(
            self.db,
            999,
            ResumeUpdate(parse_status="failed", parse_error="parse failed"),
        )

        self.assertIsNone(resume)
        self.db.commit.assert_not_awaited()

    async def test_delete_resume_commits_when_found(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=10,
            filename="delete.pdf",
            file_path="uploads/delete.pdf",
        )
        self.db.get.return_value = existing

        deleted = await self.service.delete_resume(self.db, 4)

        self.assertTrue(deleted)
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_delete_resume_returns_false_when_not_found(self) -> None:
        self.db.get.return_value = None

        deleted = await self.service.delete_resume(self.db, 999)

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_write_failure_rolls_back_transaction(self) -> None:
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_resume(
                self.db,
                ResumeCreate(
                    candidate_id=10,
                    filename="rollback.pdf",
                    file_path="uploads/rollback.pdf",
                ),
            )

        self.db.rollback.assert_awaited_once()
