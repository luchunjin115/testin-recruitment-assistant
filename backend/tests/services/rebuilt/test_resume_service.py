from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeUpdate
from app.services.rebuilt.resume_service import (
    ResumeAlreadyBoundError,
    ResumeAbandonCompensationError,
    ResumeFileUnavailableError,
    ResumeService,
    UnsupportedResumeFileError,
)
from app.services.rebuilt.resume_file_cleanup import ResumeCleanupStorageError


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
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

    async def test_list_resumes_filters_by_candidate_id(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = []
        self.db.scalars.return_value = scalar_result

        await self.service.list_resumes(self.db, candidate_id=64)

        statement = self.db.scalars.await_args.args[0]
        self.assertIn("resumes.candidate_id", str(statement))
        self.assertEqual(statement.compile().params["candidate_id_1"], 64)

    async def test_get_resume_file_returns_validated_private_pdf(self) -> None:
        with TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            path = storage_root / "v2" / "resumes" / "2026" / "08" / "server.pdf"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"%PDF-1.4\nresume")
            self.db.get.return_value = Resume(
                id=32,
                candidate_id=64,
                filename="候选人简历.pdf",
                file_path=path.relative_to(storage_root).as_posix(),
                file_type="application/pdf",
                file_size=path.stat().st_size,
            )

            descriptor = await self.service.get_resume_file(
                self.db,
                32,
                storage_root,
            )

            self.assertIsNotNone(descriptor)
            self.assertEqual(descriptor.path, path.resolve())
            self.assertEqual(descriptor.filename, "候选人简历.pdf")
            self.assertEqual(descriptor.media_type, "application/pdf")
            self.assertTrue(descriptor.supports_inline_preview)

    async def test_get_resume_file_rejects_unknown_mime(self) -> None:
        self.db.get.return_value = Resume(
            id=9,
            candidate_id=64,
            filename="resume.bin",
            file_path="v2/resumes/2026/08/server.bin",
            file_type="application/octet-stream",
            file_size=10,
        )

        with self.assertRaisesRegex(UnsupportedResumeFileError, "不支持"):
            await self.service.get_resume_file(self.db, 9, Path("C:/storage"))

    async def test_get_resume_file_rejects_path_traversal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            outside = storage_root / "outside.pdf"
            outside.write_bytes(b"%PDF-1.4\nresume")
            self.db.get.return_value = Resume(
                id=9,
                candidate_id=64,
                filename="resume.pdf",
                file_path="../outside.pdf",
                file_type="application/pdf",
                file_size=outside.stat().st_size,
            )

            with self.assertRaisesRegex(ResumeFileUnavailableError, "路径无效"):
                await self.service.get_resume_file(self.db, 9, storage_root)

    async def test_get_resume_file_rejects_missing_or_changed_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            path = storage_root / "v2" / "resumes" / "2026" / "08" / "server.txt"
            path.parent.mkdir(parents=True)
            self.db.get.return_value = Resume(
                id=9,
                candidate_id=64,
                filename="resume.txt",
                file_path=path.relative_to(storage_root).as_posix(),
                file_type="text/plain",
                file_size=12,
            )

            with self.assertRaisesRegex(ResumeFileUnavailableError, "文件不存在"):
                await self.service.get_resume_file(self.db, 9, storage_root)

            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ResumeFileUnavailableError, "大小.*不一致"):
                await self.service.get_resume_file(self.db, 9, storage_root)

    async def test_download_filename_removes_path_and_rejects_wrong_suffix(self) -> None:
        self.assertEqual(
            self.service._safe_download_filename("../../中文简历.pdf", 7, ".pdf"),
            "中文简历.pdf",
        )
        self.assertEqual(
            self.service._safe_download_filename("伪装文件.txt", 7, ".pdf"),
            "resume-7.pdf",
        )

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

    async def test_delete_resume_quarantines_unbound_file_before_database_delete(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="delete.pdf",
            file_path="v2/resumes/2026/08/delete.pdf",
            file_type="application/pdf",
            file_size=128,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        cleanup = Mock()
        quarantined = Mock()
        cleanup.quarantine.return_value = quarantined

        deleted = await self.service.delete_resume(
            self.db,
            4,
            Path("C:/storage"),
            cleanup=cleanup,
        )

        self.assertTrue(deleted)
        cleanup.quarantine.assert_called_once_with(
            storage_root=Path("C:/storage"),
            relative_path=existing.file_path,
            file_type=existing.file_type,
            expected_size=existing.file_size,
            resume_id=existing.id,
        )
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()
        cleanup.purge.assert_called_once_with(quarantined)
        cleanup.restore.assert_not_called()

    async def test_delete_resume_returns_false_when_not_found(self) -> None:
        result = Mock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result
        cleanup = Mock()

        deleted = await self.service.delete_resume(
            self.db,
            999,
            Path("C:/storage"),
            cleanup=cleanup,
        )

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()
        cleanup.quarantine.assert_not_called()

    async def test_delete_resume_rejects_bound_resume_before_file_operation(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=10,
            filename="bound.pdf",
            file_path="v2/resumes/2026/08/bound.pdf",
            file_type="application/pdf",
            file_size=128,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        cleanup = Mock()

        with self.assertRaisesRegex(ResumeAlreadyBoundError, "已绑定"):
            await self.service.delete_resume(
                self.db,
                4,
                Path("C:/storage"),
                cleanup=cleanup,
            )

        cleanup.quarantine.assert_not_called()
        self.db.delete.assert_not_awaited()

    async def test_delete_resume_restores_file_when_database_commit_fails(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="delete.txt",
            file_path="v2/resumes/2026/08/delete.txt",
            file_type="text/plain",
            file_size=12,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        self.db.commit.side_effect = RuntimeError("database unavailable")
        cleanup = Mock()
        quarantined = Mock()
        cleanup.quarantine.return_value = quarantined

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.delete_resume(
                self.db,
                4,
                Path("C:/storage"),
                cleanup=cleanup,
            )

        self.db.rollback.assert_awaited_once()
        cleanup.restore.assert_called_once_with(quarantined)
        cleanup.purge.assert_not_called()

    async def test_delete_resume_does_not_touch_database_when_quarantine_fails(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="delete.txt",
            file_path="v2/resumes/2026/08/delete.txt",
            file_type="text/plain",
            file_size=12,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        cleanup = Mock()
        cleanup.quarantine.side_effect = ResumeCleanupStorageError("move failed")

        with self.assertRaisesRegex(ResumeCleanupStorageError, "move failed"):
            await self.service.delete_resume(
                self.db,
                4,
                Path("C:/storage"),
                cleanup=cleanup,
            )

        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_not_awaited()

    async def test_delete_resume_reports_failed_database_compensation(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="delete.txt",
            file_path="v2/resumes/2026/08/delete.txt",
            file_type="text/plain",
            file_size=12,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        self.db.commit.side_effect = RuntimeError("database unavailable")
        cleanup = Mock()
        cleanup.quarantine.return_value = Mock()
        cleanup.restore.side_effect = ResumeCleanupStorageError("restore failed")

        with self.assertRaisesRegex(ResumeAbandonCompensationError, "需要人工检查"):
            await self.service.delete_resume(
                self.db,
                4,
                Path("C:/storage"),
                cleanup=cleanup,
            )

        self.db.rollback.assert_awaited_once()

    async def test_delete_resume_defers_trash_purge_failure_after_commit(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="delete.txt",
            file_path="v2/resumes/2026/08/delete.txt",
            file_type="text/plain",
            file_size=12,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        cleanup = Mock()
        cleanup.quarantine.return_value = Mock()
        cleanup.purge.side_effect = ResumeCleanupStorageError("locked")

        with self.assertLogs(
            "app.services.rebuilt.resume_service",
            level="ERROR",
        ):
            deleted = await self.service.delete_resume(
                self.db,
                4,
                Path("C:/storage"),
                cleanup=cleanup,
            )

        self.assertTrue(deleted)
        self.db.commit.assert_awaited_once()
        cleanup.restore.assert_not_called()

    async def test_delete_expired_resume_rechecks_cutoff_under_row_lock(self) -> None:
        existing = Resume(
            id=4,
            candidate_id=None,
            filename="expired.txt",
            file_path="v2/resumes/2026/08/expired.txt",
            file_type="text/plain",
            file_size=12,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = existing
        self.db.execute.return_value = result
        cleanup = Mock()
        cleanup.quarantine.return_value = Mock()
        cutoff = datetime(2026, 8, 10, tzinfo=timezone.utc)
        processing_cutoff = datetime(2026, 8, 11, 11, 57, tzinfo=timezone.utc)

        deleted = await self.service.delete_expired_resume(
            self.db,
            4,
            cutoff,
            Path("C:/storage"),
            processing_cutoff=processing_cutoff,
            cleanup=cleanup,
        )

        self.assertTrue(deleted)
        statement = self.db.execute.await_args.args[0]
        statement_text = str(statement)
        self.assertIn("resumes.candidate_id IS NULL", statement_text)
        self.assertIn("resumes.uploaded_at <=", statement_text)
        self.assertIn("resumes.structure_status !=", statement_text)
        self.assertIn("resumes.structure_started_at <=", statement_text)
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_delete_expired_resume_skips_fresh_bound_or_locked_record(self) -> None:
        result = Mock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result
        cleanup = Mock()

        deleted = await self.service.delete_expired_resume(
            self.db,
            4,
            datetime(2026, 8, 10, tzinfo=timezone.utc),
            Path("C:/storage"),
            cleanup=cleanup,
        )

        self.assertFalse(deleted)
        cleanup.quarantine.assert_not_called()
        self.db.delete.assert_not_awaited()

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
