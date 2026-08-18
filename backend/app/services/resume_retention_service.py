from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.resume import Resume
from app.services.resume_file_cleanup import (
    ResumeFileCleanup,
    resume_file_cleanup,
)
from app.services.resume_service import ResumeService, resume_service


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResumeRetentionReport:
    cutoff: datetime
    scanned: int = 0
    deleted: int = 0
    skipped: int = 0
    failed: int = 0
    trash_purged: int = 0
    trash_retained: int = 0
    trash_failed: int = 0


class ResumeRetentionService:
    async def run_once(
        self,
        db: AsyncSession,
        storage_root: Path,
        retention_hours: int,
        batch_size: int,
        processing_lease_seconds: int = 180,
        *,
        now: datetime | None = None,
        resumes: ResumeService = resume_service,
        files: ResumeFileCleanup = resume_file_cleanup,
    ) -> ResumeRetentionReport:
        if retention_hours <= 0:
            raise ValueError("retention_hours must be positive")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if processing_lease_seconds <= 0:
            raise ValueError("processing_lease_seconds must be positive")

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        cutoff = current_time - timedelta(hours=retention_hours)
        processing_cutoff = current_time - timedelta(seconds=processing_lease_seconds)

        result = await db.scalars(
            select(Resume.id)
            .where(
                Resume.candidate_id.is_(None),
                Resume.uploaded_at <= cutoff,
                or_(
                    Resume.structure_status != "processing",
                    Resume.structure_started_at.is_(None),
                    Resume.structure_started_at <= processing_cutoff,
                ),
            )
            .order_by(Resume.uploaded_at.asc(), Resume.id.asc())
            .limit(batch_size)
        )
        resume_ids = list(result.all())
        deleted = 0
        skipped = 0
        failed = 0
        for resume_id in resume_ids:
            try:
                was_deleted = await resumes.delete_expired_resume(
                    db=db,
                    resume_id=resume_id,
                    cutoff=cutoff,
                    storage_root=storage_root,
                    processing_cutoff=processing_cutoff,
                    cleanup=files,
                )
            except Exception:
                failed += 1
                await db.rollback()
                logger.exception("Expired resume cleanup failed for resume %s", resume_id)
                continue
            if was_deleted:
                deleted += 1
            else:
                skipped += 1

        trash_purged = 0
        trash_retained = 0
        trash_failed = 0
        try:
            trash_files = files.list_trash_files(storage_root, limit=batch_size)
        except Exception:
            trash_files = []
            trash_failed += 1
            logger.exception("Resume trash directory scan failed")

        for trash_file in trash_files:
            try:
                resume = await db.get(Resume, trash_file.resume_id)
                if resume is not None:
                    trash_retained += 1
                    continue
                files.purge_trash_file(storage_root, trash_file)
                trash_purged += 1
            except Exception:
                trash_failed += 1
                await db.rollback()
                logger.exception(
                    "Resume trash reconciliation failed for resume %s",
                    trash_file.resume_id,
                )

        return ResumeRetentionReport(
            cutoff=cutoff,
            scanned=len(resume_ids),
            deleted=deleted,
            skipped=skipped,
            failed=failed,
            trash_purged=trash_purged,
            trash_retained=trash_retained,
            trash_failed=trash_failed,
        )


async def run_resume_retention_loop(
    session_factory: async_sessionmaker[AsyncSession],
    storage_root: Path,
    retention_hours: int,
    interval_seconds: int,
    batch_size: int,
    processing_lease_seconds: int = 180,
    *,
    service: ResumeRetentionService | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    retention_service = service or resume_retention_service

    while True:
        await sleep(interval_seconds)
        try:
            async with session_factory() as db:
                report = await retention_service.run_once(
                    db=db,
                    storage_root=storage_root,
                    retention_hours=retention_hours,
                    batch_size=batch_size,
                    processing_lease_seconds=processing_lease_seconds,
                )
            logger.info(
                "Resume retention cleanup completed: scanned=%s deleted=%s "
                "skipped=%s failed=%s trash_purged=%s trash_retained=%s "
                "trash_failed=%s",
                report.scanned,
                report.deleted,
                report.skipped,
                report.failed,
                report.trash_purged,
                report.trash_retained,
                report.trash_failed,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Resume retention cleanup cycle failed")


resume_retention_service = ResumeRetentionService()
