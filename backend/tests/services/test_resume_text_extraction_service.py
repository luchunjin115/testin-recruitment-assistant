from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.resume import Resume
from app.services.resume_docx_extractor import (
    ResumeDocxExtractor,
    ResumeDocxExtractorError,
)
from app.services.resume_pdf_extractor import (
    ResumePdfExtractor,
    ResumePdfExtractorError,
)
from app.services.resume_service import (
    ResumeService,
    ResumeTextExtractionConflictError,
    ResumeTextExtractionFailedError,
    UnsupportedResumeTextExtractionError,
)
from app.services.resume_text_extractor import (
    ResumeTextExtractor,
    ResumeTextExtractorError,
)


def make_resume(*, status: str = "uploaded", file_type: str = "text/plain") -> Resume:
    return Resume(
        id=7,
        candidate_id=10,
        filename="resume.txt",
        file_path="v2/resumes/2026/08/server-name.txt",
        file_type=file_type,
        file_size=12,
        raw_text="existing text" if status == "parsed" else None,
        parse_status=status,
        parse_error="previous failure" if status == "failed" else None,
    )


def make_session(resume: Resume | None) -> Mock:
    session = Mock()
    session.get = AsyncMock(return_value=resume)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def make_extractor(result: str = "完整 TXT 简历") -> Mock:
    extractor = Mock(spec=ResumeTextExtractor)
    extractor.extract = Mock(return_value=result)
    return extractor


def make_pdf_extractor(result: str = "Complete PDF resume text") -> Mock:
    extractor = Mock(spec=ResumePdfExtractor)
    extractor.extract = Mock(return_value=result)
    return extractor


def make_docx_extractor(result: str = "完整 DOCX 简历") -> Mock:
    extractor = Mock(spec=ResumeDocxExtractor)
    extractor.extract = Mock(return_value=result)
    return extractor


class ResumeTextExtractionServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ResumeService()
        self.storage_root = Path("C:/private-storage")

    async def test_extract_text_transitions_through_parsing_to_parsed(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        extractor = make_extractor()

        def extract(*args):
            self.assertEqual(resume.parse_status, "parsing")
            return "完整 TXT 简历"

        extractor.extract.side_effect = extract

        result = await self.service.extract_text(db, 7, self.storage_root, extractor)

        self.assertIs(result, resume)
        self.assertEqual(resume.raw_text, "完整 TXT 简历")
        self.assertEqual(resume.parse_status, "parsed")
        self.assertIsNone(resume.parse_error)
        self.assertIsNotNone(resume.parsed_at)
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()
        extractor.extract.assert_called_once_with(
            self.storage_root,
            resume.file_path,
            resume.file_size,
        )

    async def test_extract_text_returns_none_when_resume_does_not_exist(self) -> None:
        db = make_session(None)
        extractor = make_extractor()

        result = await self.service.extract_text(db, 999, self.storage_root, extractor)

        self.assertIsNone(result)
        extractor.extract.assert_not_called()
        db.flush.assert_not_awaited()

    async def test_extract_text_is_idempotent_when_already_parsed(self) -> None:
        resume = make_resume(status="parsed")
        db = make_session(resume)
        extractor = make_extractor("new text")

        result = await self.service.extract_text(db, 7, self.storage_root, extractor)

        self.assertIs(result, resume)
        self.assertEqual(resume.raw_text, "existing text")
        extractor.extract.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_extract_text_rejects_concurrent_parsing_state(self) -> None:
        resume = make_resume(status="parsing")
        db = make_session(resume)

        with self.assertRaises(ResumeTextExtractionConflictError):
            await self.service.extract_text(db, 7, self.storage_root, make_extractor())

        db.flush.assert_not_awaited()

    async def test_extract_text_rejects_unknown_type_without_changing_status(self) -> None:
        resume = make_resume(file_type="application/msword")
        db = make_session(resume)

        with self.assertRaises(UnsupportedResumeTextExtractionError):
            await self.service.extract_text(db, 7, self.storage_root, make_extractor())

        self.assertEqual(resume.parse_status, "uploaded")
        db.flush.assert_not_awaited()

    async def test_extract_text_dispatches_docx_to_docx_extractor(self) -> None:
        resume = make_resume(
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        resume.filename = "resume.docx"
        resume.file_path = "v2/resumes/2026/08/server-name.docx"
        db = make_session(resume)
        text_extractor = make_extractor("wrong TXT extractor")
        pdf_extractor = make_pdf_extractor("wrong PDF extractor")
        docx_extractor = make_docx_extractor()

        result = await self.service.extract_text(
            db,
            7,
            self.storage_root,
            text_extractor,
            pdf_extractor,
            docx_extractor,
        )

        self.assertIs(result, resume)
        self.assertEqual(resume.raw_text, "完整 DOCX 简历")
        text_extractor.extract.assert_not_called()
        pdf_extractor.extract.assert_not_called()
        docx_extractor.extract.assert_called_once_with(
            self.storage_root,
            resume.file_path,
            resume.file_size,
        )

    async def test_docx_extractor_failure_commits_failed_status(self) -> None:
        resume = make_resume(
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        resume.file_path = "v2/resumes/2026/08/server-name.docx"
        db = make_session(resume)
        docx_extractor = make_docx_extractor()
        docx_extractor.extract.side_effect = ResumeDocxExtractorError(
            "DOCX 文件损坏或无法读取"
        )

        with self.assertRaisesRegex(ResumeTextExtractionFailedError, "损坏"):
            await self.service.extract_text(
                db,
                7,
                self.storage_root,
                make_extractor(),
                make_pdf_extractor(),
                docx_extractor,
            )

        self.assertEqual(resume.parse_status, "failed")
        self.assertEqual(resume.parse_error, "DOCX 文件损坏或无法读取")
        db.commit.assert_awaited_once()

    async def test_extract_text_dispatches_pdf_to_pdf_extractor(self) -> None:
        resume = make_resume(file_type="application/pdf")
        resume.filename = "resume.pdf"
        resume.file_path = "v2/resumes/2026/08/server-name.pdf"
        db = make_session(resume)
        text_extractor = make_extractor("wrong extractor")
        pdf_extractor = make_pdf_extractor()

        result = await self.service.extract_text(
            db,
            7,
            self.storage_root,
            text_extractor,
            pdf_extractor,
        )

        self.assertIs(result, resume)
        self.assertEqual(resume.raw_text, "Complete PDF resume text")
        text_extractor.extract.assert_not_called()
        pdf_extractor.extract.assert_called_once_with(
            self.storage_root,
            resume.file_path,
            resume.file_size,
        )

    async def test_pdf_extractor_failure_commits_failed_status(self) -> None:
        resume = make_resume(file_type="application/pdf")
        resume.file_path = "v2/resumes/2026/08/server-name.pdf"
        db = make_session(resume)
        pdf_extractor = make_pdf_extractor()
        pdf_extractor.extract.side_effect = ResumePdfExtractorError(
            "PDF 未检测到可提取文字，可能是扫描件，需要 OCR"
        )

        with self.assertRaisesRegex(ResumeTextExtractionFailedError, "扫描件"):
            await self.service.extract_text(
                db,
                7,
                self.storage_root,
                make_extractor(),
                pdf_extractor,
            )

        self.assertEqual(resume.parse_status, "failed")
        self.assertIn("OCR", resume.parse_error)
        db.commit.assert_awaited_once()

    async def test_extractor_failure_commits_failed_status_and_error(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        extractor = make_extractor()
        extractor.extract.side_effect = ResumeTextExtractorError("原始简历文件不存在")

        with self.assertRaisesRegex(ResumeTextExtractionFailedError, "文件不存在"):
            await self.service.extract_text(db, 7, self.storage_root, extractor)

        self.assertEqual(resume.parse_status, "failed")
        self.assertEqual(resume.parse_error, "原始简历文件不存在")
        self.assertIsNone(resume.raw_text)
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()

    async def test_failed_resume_can_be_retried_successfully(self) -> None:
        resume = make_resume(status="failed")
        db = make_session(resume)

        result = await self.service.extract_text(db, 7, self.storage_root, make_extractor("retry"))

        self.assertIs(result, resume)
        self.assertEqual(resume.parse_status, "parsed")
        self.assertEqual(resume.raw_text, "retry")
        self.assertIsNone(resume.parse_error)

    async def test_database_flush_failure_rolls_back_before_file_read(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        db.flush.side_effect = RuntimeError("flush failed")
        extractor = make_extractor()

        with self.assertRaisesRegex(RuntimeError, "flush failed"):
            await self.service.extract_text(db, 7, self.storage_root, extractor)

        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()
        extractor.extract.assert_not_called()

    async def test_database_commit_failure_rolls_back_parsed_result(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        db.commit.side_effect = RuntimeError("commit failed")

        with self.assertRaisesRegex(RuntimeError, "commit failed"):
            await self.service.extract_text(db, 7, self.storage_root, make_extractor())

        db.rollback.assert_awaited_once()

    async def test_database_failure_while_saving_error_rolls_back(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        db.commit.side_effect = RuntimeError("failed status commit failed")
        extractor = make_extractor()
        extractor.extract.side_effect = ResumeTextExtractorError("read failed")

        with self.assertRaisesRegex(RuntimeError, "failed status commit failed"):
            await self.service.extract_text(db, 7, self.storage_root, extractor)

        db.rollback.assert_awaited_once()
