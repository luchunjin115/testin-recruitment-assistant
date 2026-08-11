from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from zipfile import ZipFile

from fastapi import UploadFile

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.job import Job
from app.services.rebuilt.resume_service import (
    ResumeCandidateNotFoundError,
    ResumeJobNotFoundError,
    ResumeService,
)
from app.services.rebuilt.resume_storage import (
    EmptyResumeFileError,
    InvalidResumeContentError,
    ResumeFileStorage,
    ResumeFileTooLargeError,
    ResumeStorageError,
    UnsupportedResumeTypeError,
)


def make_upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def make_docx() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")
    return output.getvalue()


def make_session(*, candidate_exists: bool = True, job_exists: bool = True) -> Mock:
    session = Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def get(model, object_id):
        if model is Candidate:
            return Candidate(id=object_id, name="Upload Candidate") if candidate_exists else None
        if model is Job:
            return Job(id=object_id, title="Upload Job") if job_exists else None
        raise AssertionError(f"unexpected model: {model}")

    session.get = AsyncMock(side_effect=get)

    async def flush():
        resume = session.add.call_args.args[0]
        resume.id = 501
        resume.uploaded_at = datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc)

    session.flush.side_effect = flush
    return session


class ResumeUploadServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ResumeService()
        self.storage = ResumeFileStorage()
        self.temp_dir = TemporaryDirectory()
        self.upload_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    async def upload(
        self,
        db: Mock,
        filename: str,
        content: bytes,
        *,
        candidate_id: int | None = 10,
        job_id: int | None = 20,
    ):
        return await self.service.upload_resume(
            db=db,
            upload=make_upload(filename, content),
            candidate_id=candidate_id,
            job_id=job_id,
            upload_root=self.upload_root,
            max_size_bytes=1024,
            storage=self.storage,
        )

    def stored_files(self) -> list[Path]:
        return [path for path in self.upload_root.rglob("*") if path.is_file()]

    async def test_pdf_upload_writes_namespaced_file_and_commits_metadata(self) -> None:
        db = make_session()

        resume = await self.upload(db, "candidate.pdf", b"%PDF-1.4\nresume")

        self.assertEqual(resume.id, 501)
        self.assertEqual(resume.filename, "candidate.pdf")
        self.assertEqual(resume.file_type, "application/pdf")
        self.assertEqual(resume.file_size, 15)
        self.assertEqual(resume.parse_status, "uploaded")
        self.assertTrue(resume.file_path.startswith("v2/resumes/2026/08/"))
        stored_path = self.upload_root / Path(resume.file_path)
        self.assertEqual(stored_path.read_bytes(), b"%PDF-1.4\nresume")
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()

    async def test_upload_without_candidate_creates_unbound_resume(self) -> None:
        db = make_session()

        resume = await self.upload(
            db,
            "candidate.txt",
            "待确认候选人的简历".encode("utf-8"),
            candidate_id=None,
            job_id=None,
        )

        self.assertIsNone(resume.candidate_id)
        self.assertEqual(resume.parse_status, "uploaded")
        self.assertTrue((self.upload_root / Path(resume.file_path)).is_file())
        db.get.assert_not_awaited()
        db.commit.assert_awaited_once()

    async def test_docx_upload_records_full_canonical_mime(self) -> None:
        resume = await self.upload(make_session(), "candidate.DOCX", make_docx())

        self.assertEqual(
            resume.file_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertTrue(resume.file_path.endswith(".docx"))

    async def test_path_components_are_removed_from_original_filename(self) -> None:
        resume = await self.upload(
            make_session(),
            "../../private\\candidate.txt",
            "安全简历".encode("utf-8"),
        )

        self.assertEqual(resume.filename, "candidate.txt")
        self.assertNotIn("..", resume.file_path)
        self.assertEqual((self.upload_root / Path(resume.file_path)).read_text("utf-8"), "安全简历")

    async def test_same_original_filename_never_overwrites_existing_file(self) -> None:
        first = await self.upload(make_session(), "same.txt", b"first", job_id=None)
        second = await self.upload(make_session(), "same.txt", b"second", job_id=None)

        self.assertNotEqual(first.file_path, second.file_path)
        self.assertEqual((self.upload_root / Path(first.file_path)).read_bytes(), b"first")
        self.assertEqual((self.upload_root / Path(second.file_path)).read_bytes(), b"second")

    async def test_unsupported_extension_creates_no_file_or_database_record(self) -> None:
        db = make_session()

        with self.assertRaises(UnsupportedResumeTypeError):
            await self.upload(db, "candidate.exe", b"binary")

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_empty_file_creates_no_file_or_database_record(self) -> None:
        db = make_session()

        with self.assertRaises(EmptyResumeFileError):
            await self.upload(db, "candidate.txt", b"")

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_oversized_file_cleans_staging_and_creates_no_record(self) -> None:
        db = make_session()

        with self.assertRaises(ResumeFileTooLargeError):
            await self.upload(db, "candidate.txt", b"a" * 1025)

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_extension_content_mismatch_cleans_staging(self) -> None:
        db = make_session()

        with self.assertRaises(InvalidResumeContentError):
            await self.upload(db, "candidate.txt", b"%PDF-1.4\nresume")

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()

    async def test_missing_candidate_stops_before_file_write(self) -> None:
        db = make_session(candidate_exists=False)

        with self.assertRaises(ResumeCandidateNotFoundError):
            await self.upload(db, "candidate.txt", b"resume")

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()

    async def test_missing_job_stops_before_file_write(self) -> None:
        db = make_session(job_exists=False)

        with self.assertRaises(ResumeJobNotFoundError):
            await self.upload(db, "candidate.txt", b"resume")

        self.assertEqual(self.stored_files(), [])
        db.add.assert_not_called()

    async def test_file_promotion_failure_rolls_back_and_cleans_files(self) -> None:
        db = make_session()

        with patch.object(self.storage, "promote", side_effect=ResumeStorageError("disk failed")):
            with self.assertRaises(ResumeStorageError):
                await self.upload(
                    db,
                    "candidate.txt",
                    b"resume",
                    candidate_id=None,
                    job_id=None,
                )

        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()
        self.assertEqual(self.stored_files(), [])

    async def test_database_flush_failure_rolls_back_and_cleans_staging(self) -> None:
        db = make_session()
        db.flush.side_effect = RuntimeError("database flush failed")

        with self.assertRaisesRegex(RuntimeError, "database flush failed"):
            await self.upload(
                db,
                "candidate.txt",
                b"resume",
                candidate_id=None,
                job_id=None,
            )

        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()
        self.assertEqual(self.stored_files(), [])

    async def test_database_commit_failure_removes_promoted_file_and_rolls_back(self) -> None:
        db = make_session()
        db.commit.side_effect = RuntimeError("database commit failed")

        with self.assertRaisesRegex(RuntimeError, "database commit failed"):
            await self.upload(
                db,
                "candidate.txt",
                b"resume",
                candidate_id=None,
                job_id=None,
            )

        db.rollback.assert_awaited_once()
        self.assertEqual(self.stored_files(), [])
