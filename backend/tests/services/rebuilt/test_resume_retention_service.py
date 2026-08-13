import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.resume import Resume
from app.services.rebuilt.resume_file_cleanup import TrashResumeFile
from app.services.rebuilt.resume_retention_service import (
    ResumeRetentionReport,
    ResumeRetentionService,
    run_resume_retention_loop,
)


class ResumeRetentionServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ResumeRetentionService()
        self.db = Mock()
        self.db.scalars = AsyncMock()
        self.db.get = AsyncMock()
        self.db.rollback = AsyncMock()
        self.now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)

    def scalar_ids(self, ids: list[int]) -> None:
        result = Mock()
        result.all.return_value = ids
        self.db.scalars.return_value = result

    async def test_run_once_deletes_only_ids_that_still_match_under_lock(self) -> None:
        self.scalar_ids([11, 12, 13])
        resumes = Mock()
        resumes.delete_expired_resume = AsyncMock(
            side_effect=[True, False, RuntimeError("database unavailable")]
        )
        files = Mock()
        files.list_trash_files.return_value = []

        with self.assertLogs(
            "app.services.rebuilt.resume_retention_service",
            level="ERROR",
        ):
            report = await self.service.run_once(
                db=self.db,
                storage_root=Path("C:/storage"),
                retention_hours=24,
                batch_size=50,
                now=self.now,
                resumes=resumes,
                files=files,
            )

        self.assertEqual(report.cutoff, self.now - timedelta(hours=24))
        self.assertEqual(report.scanned, 3)
        self.assertEqual(report.deleted, 1)
        self.assertEqual(report.skipped, 1)
        self.assertEqual(report.failed, 1)
        self.db.rollback.assert_awaited_once()
        statement = self.db.scalars.await_args.args[0]
        self.assertIn("resumes.candidate_id IS NULL", str(statement))
        self.assertIn("resumes.structure_status !=", str(statement))
        self.assertIn("resumes.structure_started_at <=", str(statement))
        self.assertEqual(statement.compile().params["param_1"], 50)
        for call_args in resumes.delete_expired_resume.await_args_list:
            self.assertEqual(
                call_args.kwargs["processing_cutoff"],
                self.now - timedelta(seconds=180),
            )

    async def test_trash_is_purged_only_when_resume_row_is_absent(self) -> None:
        self.scalar_ids([])
        absent = TrashResumeFile(
            resume_id=21,
            path=Path("C:/storage/v2/resumes/.trash/resume-21-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.txt"),
        )
        retained = TrashResumeFile(
            resume_id=22,
            path=Path("C:/storage/v2/resumes/.trash/resume-22-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.txt"),
        )
        files = Mock()
        files.list_trash_files.return_value = [absent, retained]
        self.db.get.side_effect = [None, Resume(id=22, filename="resume.txt", file_path="x")]
        resumes = Mock()
        resumes.delete_expired_resume = AsyncMock()

        report = await self.service.run_once(
            db=self.db,
            storage_root=Path("C:/storage"),
            retention_hours=24,
            batch_size=50,
            now=self.now,
            resumes=resumes,
            files=files,
        )

        self.assertEqual(report.trash_purged, 1)
        self.assertEqual(report.trash_retained, 1)
        files.purge_trash_file.assert_called_once_with(Path("C:/storage"), absent)

    async def test_trash_scan_failure_is_reported_without_deleting_rows(self) -> None:
        self.scalar_ids([])
        files = Mock()
        files.list_trash_files.side_effect = OSError("locked")
        resumes = Mock()
        resumes.delete_expired_resume = AsyncMock()

        with self.assertLogs(
            "app.services.rebuilt.resume_retention_service",
            level="ERROR",
        ):
            report = await self.service.run_once(
                db=self.db,
                storage_root=Path("C:/storage"),
                retention_hours=24,
                batch_size=50,
                now=self.now,
                resumes=resumes,
                files=files,
            )

        self.assertEqual(report.trash_failed, 1)
        resumes.delete_expired_resume.assert_not_awaited()

    async def test_run_once_rejects_naive_time_and_invalid_limits(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            await self.service.run_once(
                self.db,
                Path("C:/storage"),
                24,
                50,
                now=datetime(2026, 8, 11, 12, 0),
            )
        with self.assertRaisesRegex(ValueError, "retention_hours"):
            await self.service.run_once(self.db, Path("C:/storage"), 0, 50)
        with self.assertRaisesRegex(ValueError, "batch_size"):
            await self.service.run_once(self.db, Path("C:/storage"), 24, 0)
        with self.assertRaisesRegex(ValueError, "processing_lease_seconds"):
            await self.service.run_once(
                self.db,
                Path("C:/storage"),
                24,
                50,
                processing_lease_seconds=0,
            )

    async def test_loop_waits_before_first_run_and_stops_on_cancellation(self) -> None:
        db = Mock()
        context = AsyncMock()
        context.__aenter__.return_value = db
        session_factory = Mock(return_value=context)
        service = Mock()
        service.run_once = AsyncMock(
            return_value=ResumeRetentionReport(cutoff=self.now)
        )
        sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])

        with self.assertRaises(asyncio.CancelledError):
            await run_resume_retention_loop(
                session_factory=session_factory,
                storage_root=Path("C:/storage"),
                retention_hours=24,
                interval_seconds=3600,
                batch_size=50,
                service=service,
                sleep=sleep,
            )

        self.assertEqual(sleep.await_args_list[0].args, (3600,))
        service.run_once.assert_awaited_once_with(
            db=db,
            storage_root=Path("C:/storage"),
            retention_hours=24,
            batch_size=50,
            processing_lease_seconds=180,
        )
