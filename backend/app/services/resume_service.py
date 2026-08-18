import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.core.config import get_settings
from app.schemas.resume import ResumeCreate, ResumeUpdate
from app.services.resume_docx_extractor import (
    ResumeDocxExtractor,
    ResumeDocxExtractorError,
    resume_docx_extractor,
)
from app.services.resume_file_access import (
    ResumeFileAccess,
    ResumeFileAccessError,
    resume_file_access,
)
from app.services.resume_file_cleanup import (
    ResumeCleanupStorageError,
    ResumeFileCleanup,
    resume_file_cleanup,
)
from app.services.resume_pdf_extractor import (
    ResumePdfExtractor,
    ResumePdfExtractorError,
    resume_pdf_extractor,
)
from app.services.resume_storage import ResumeFileStorage, resume_file_storage
from app.services.resume_text_extractor import (
    ResumeTextExtractor,
    ResumeTextExtractorError,
    resume_text_extractor,
)


class ResumeCandidateNotFoundError(ValueError):
    pass


class ResumeJobNotFoundError(ValueError):
    pass


class ResumeTextExtractionConflictError(ValueError):
    pass


class UnsupportedResumeTextExtractionError(ValueError):
    pass


class ResumeTextExtractionFailedError(ValueError):
    pass


class UnsupportedResumeFileError(ValueError):
    pass


class ResumeFileUnavailableError(ValueError):
    pass


class ResumeAlreadyBoundError(ValueError):
    pass


class ResumeAbandonCompensationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResumeFileDescriptor:
    path: Path
    filename: str
    media_type: str
    supports_inline_preview: bool


RESUME_FILE_FORMATS: dict[str, tuple[str, str, bool]] = {
    "application/pdf": (".pdf", "PDF", True),
    "text/plain": (".txt", "TXT", True),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        ".docx",
        "DOCX",
        False,
    ),
}

logger = logging.getLogger(__name__)


class ResumeService:
    async def upload_resume(
        self,
        db: AsyncSession,
        upload: UploadFile,
        candidate_id: int | None,
        job_id: int | None,
        upload_root: Path,
        max_size_bytes: int,
        storage: ResumeFileStorage = resume_file_storage,
    ) -> Resume:
        if candidate_id is not None and await db.get(Candidate, candidate_id) is None:
            raise ResumeCandidateNotFoundError("候选人不存在")
        if job_id is not None and await db.get(Job, job_id) is None:
            raise ResumeJobNotFoundError("岗位不存在")

        prepared = await storage.prepare(upload, upload_root, max_size_bytes)
        try:
            resume = Resume(
                candidate_id=candidate_id,
                job_id=job_id,
                filename=prepared.original_filename,
                file_path=prepared.relative_path,
                file_type=prepared.mime_type,
                file_size=prepared.file_size,
                parse_status="uploaded",
            )
            db.add(resume)
            await db.flush()
            storage.promote(prepared)
            await db.commit()
        except BaseException:
            try:
                await db.rollback()
            finally:
                storage.discard(prepared)
            raise
        finally:
            storage.discard_path(prepared.temp_path)

        return resume

    async def extract_text(
        self,
        db: AsyncSession,
        resume_id: int,
        storage_root: Path,
        text_extractor: ResumeTextExtractor = resume_text_extractor,
        pdf_extractor: ResumePdfExtractor = resume_pdf_extractor,
        docx_extractor: ResumeDocxExtractor = resume_docx_extractor,
    ) -> Resume | None:
        resume = await self.get_resume(db, resume_id)
        if resume is None:
            return None
        if resume.parse_status == "parsed" and resume.raw_text is not None:
            return resume
        if resume.parse_status == "parsing":
            raise ResumeTextExtractionConflictError("简历正在解析中")
        if resume.file_type == "text/plain":
            extractor = text_extractor
        elif resume.file_type == "application/pdf":
            extractor = pdf_extractor
        elif resume.file_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            extractor = docx_extractor
        else:
            raise UnsupportedResumeTextExtractionError(
                "当前步骤只支持 TXT、PDF 和 DOCX 文本提取"
            )

        resume.parse_status = "parsing"
        resume.parse_error = None
        resume.parsed_at = None
        try:
            await db.flush()
            text = await asyncio.to_thread(
                extractor.extract,
                storage_root,
                resume.file_path,
                resume.file_size,
            )
        except (
            ResumeTextExtractorError,
            ResumePdfExtractorError,
            ResumeDocxExtractorError,
        ) as exc:
            resume.raw_text = None
            resume.parse_status = "failed"
            resume.parse_error = str(exc)
            resume.parsed_at = None
            try:
                await db.commit()
            except BaseException:
                await db.rollback()
                raise
            raise ResumeTextExtractionFailedError(str(exc)) from exc
        except BaseException:
            await db.rollback()
            raise

        resume.raw_text = text
        resume.parse_status = "parsed"
        resume.parse_error = None
        resume.parsed_at = datetime.now(timezone.utc)
        try:
            await db.commit()
        except BaseException:
            await db.rollback()
            raise
        return resume

    async def create_resume(self, db: AsyncSession, data: ResumeCreate) -> Resume:
        resume = Resume(**data.model_dump())
        db.add(resume)
        await self._commit_and_refresh(db, resume)
        return resume

    async def get_resume(self, db: AsyncSession, resume_id: int) -> Resume | None:
        return await db.get(Resume, resume_id)

    async def get_resume_file(
        self,
        db: AsyncSession,
        resume_id: int,
        storage_root: Path,
        file_access: ResumeFileAccess = resume_file_access,
    ) -> ResumeFileDescriptor | None:
        resume = await self.get_resume(db, resume_id)
        if resume is None:
            return None

        file_format = RESUME_FILE_FORMATS.get(resume.file_type or "")
        if file_format is None:
            raise UnsupportedResumeFileError("当前文件类型不支持安全查看或下载")
        expected_extension, format_name, supports_inline_preview = file_format
        try:
            target = file_access.resolve(
                storage_root,
                resume.file_path,
                resume.file_size,
                expected_extension=expected_extension,
                format_name=format_name,
            )
        except ResumeFileAccessError as exc:
            raise ResumeFileUnavailableError(str(exc)) from exc

        filename = self._safe_download_filename(
            resume.filename,
            resume.id,
            expected_extension,
        )
        return ResumeFileDescriptor(
            path=target,
            filename=filename,
            media_type=resume.file_type,
            supports_inline_preview=supports_inline_preview,
        )

    async def list_resumes(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
    ) -> list[Resume]:
        statement = select(Resume).order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        if candidate_id is not None:
            statement = statement.where(Resume.candidate_id == candidate_id)
        result = await db.scalars(statement)
        return list(result.all())

    async def update_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        data: ResumeUpdate,
    ) -> Resume | None:
        resume = await self.get_resume(db, resume_id)
        if resume is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(resume, field, value)

        await self._commit_and_refresh(db, resume)
        return resume

    async def delete_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        storage_root: Path,
        cleanup: ResumeFileCleanup = resume_file_cleanup,
    ) -> bool:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id).with_for_update()
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            return False
        if resume.candidate_id is not None:
            raise ResumeAlreadyBoundError("已绑定候选人的简历不能通过放弃接口删除")

        await self._delete_locked_resume(db, resume, storage_root, cleanup)
        return True

    async def delete_expired_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        cutoff: datetime,
        storage_root: Path,
        processing_cutoff: datetime | None = None,
        cleanup: ResumeFileCleanup = resume_file_cleanup,
    ) -> bool:
        processing_cutoff = processing_cutoff or (
            datetime.now(timezone.utc)
            - timedelta(
                seconds=get_settings().RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS
            )
        )
        result = await db.execute(
            select(Resume)
            .where(
                Resume.id == resume_id,
                Resume.candidate_id.is_(None),
                Resume.uploaded_at <= cutoff,
                or_(
                    Resume.structure_status != "processing",
                    Resume.structure_started_at.is_(None),
                    Resume.structure_started_at <= processing_cutoff,
                ),
            )
            .with_for_update(skip_locked=True)
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            return False

        await self._delete_locked_resume(db, resume, storage_root, cleanup)
        return True

    @staticmethod
    async def _delete_locked_resume(
        db: AsyncSession,
        resume: Resume,
        storage_root: Path,
        cleanup: ResumeFileCleanup,
    ) -> None:

        quarantined = cleanup.quarantine(
            storage_root=storage_root,
            relative_path=resume.file_path,
            file_type=resume.file_type,
            expected_size=resume.file_size,
            resume_id=resume.id,
        )

        try:
            await db.delete(resume)
            await db.commit()
        except BaseException as database_error:
            await db.rollback()
            try:
                cleanup.restore(quarantined)
            except ResumeCleanupStorageError as restore_error:
                raise ResumeAbandonCompensationError(
                    "数据库删除失败且简历文件恢复失败，需要人工检查"
                ) from restore_error
            raise database_error

        try:
            cleanup.purge(quarantined)
        except ResumeCleanupStorageError:
            # The live file and database row are already gone. A later trash sweep
            # can safely retry this private, unreachable file without resurrecting data.
            logger.exception("Deferred purge required for quarantined resume file")

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, resume: Resume) -> None:
        try:
            await db.commit()
            await db.refresh(resume)
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    def _safe_download_filename(
        original_filename: str,
        resume_id: int,
        expected_extension: str,
    ) -> str:
        basename = Path(original_filename.replace("\\", "/")).name
        basename = "".join(
            character
            for character in basename
            if ord(character) >= 32 and ord(character) != 127
        ).strip()
        if not basename or Path(basename).suffix.lower() != expected_extension:
            return f"resume-{resume_id}{expected_extension}"
        return basename


resume_service = ResumeService()
