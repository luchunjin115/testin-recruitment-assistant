from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.schemas.public_application import PublicApplicationForm
from app.schemas.public_application_workbench import PublicApplicationPool
from app.services.public_application_service import PublicApplicationService
from app.services.public_application_workbench_service import (
    PublicApplicationWorkbenchService,
)
from app.services.resume_storage import ResumeFileStorage
from app.services.screening_service import screening_service


NOW = datetime(2026, 9, 2, 15, 30, tzinfo=timezone.utc)
COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    PublicApplicationSubmission,
    ApplicationProcessingRun,
    ActivityLog,
)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class PublicApplicationWorkbenchServicePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            settings.async_database_url,
            poolclass=NullPool,
        )
        async with AsyncSession(self.engine) as outside:
            self.counts_before = await counts(outside)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage = ResumeFileStorage()
        self.intake = PublicApplicationService()
        self.workbench = PublicApplicationWorkbenchService()
        self.job = Job(
            title="阶段 8E 虚构岗位",
            department="演示研发部",
            location="杭州",
            employment_type="full_time",
            headcount=1,
            job_background="只用于回滚测试。",
            job_responsibilities="验证统一初筛中心。",
            candidate_requirements="具备 Python 项目经验。",
            preferred_qualifications=None,
            public_notes="不使用真实候选人数据。",
            status="open",
        )
        self.db.add(self.job)
        await self.db.commit()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            counts_after = await counts(outside)
        await self.engine.dispose()
        self.temp_dir.cleanup()
        self.assertEqual(counts_after, self.counts_before)

    def form(self, *, key: str, phone: str, email: str) -> PublicApplicationForm:
        return PublicApplicationForm(
            name="阶段八虚构候选人",
            phone=phone,
            email=email,
            job_id=self.job.id,
            privacy_consent=True,
            consent_version="2026-09-02",
            idempotency_key=UUID(key),
        )

    async def submit(
        self,
        *,
        key: str = "e1111111-1111-4111-8111-111111111111",
        phone: str = "13800008101",
        email: str = "stage8e@example.com",
    ) -> tuple[PublicApplicationSubmission, ApplicationProcessingRun]:
        prepared = await self.storage.prepare(
            UploadFile(
                filename="stage8e-resume.txt",
                file=BytesIO("虚构 Python 简历".encode("utf-8")),
            ),
            self.root,
            1024,
        )
        accepted = await self.intake.accept(
            self.db,
            self.form(key=key, phone=phone, email=email),
            prepared,
            storage=self.storage,
        )
        submission = await self.db.scalar(
            select(PublicApplicationSubmission).where(
                PublicApplicationSubmission.submission_reference
                == accepted.submission_reference
            )
        )
        run = await self.db.scalar(
            select(ApplicationProcessingRun).where(
                ApplicationProcessingRun.submission_id == submission.id
            )
        )
        return submission, run

    async def test_unified_queue_summary_detail_and_pool_filters(self) -> None:
        submission, run = await self.submit()

        normal = await self.workbench.list_submissions(
            self.db,
            pool=PublicApplicationPool.NORMAL,
            job_id=self.job.id,
        )
        self.assertEqual(len(normal), 1)
        self.assertEqual(normal[0].application_id, submission.application_id)
        self.assertEqual(normal[0].latest_run.id, run.id)
        serialized = normal[0].model_dump()
        self.assertNotIn("idempotency_key_hash", serialized)
        self.assertNotIn("lease_owner", serialized["latest_run"])

        detail = await self.workbench.get_submission(self.db, submission.id)
        self.assertEqual([item.id for item in detail.processing_runs], [run.id])
        self.assertEqual(detail.identity_candidates, [])
        exceptions = await self.workbench.list_submissions(
            self.db,
            pool=PublicApplicationPool.EXCEPTION,
            job_id=self.job.id,
        )
        self.assertEqual(exceptions, [])

    async def test_identity_review_keeps_candidates_and_writes_activity_log(self) -> None:
        existing = Candidate(
            name="阶段八虚构候选人",
            phone="13800008102",
            email="existing-stage8e@example.com",
            source="hr_screening",
            status="new",
        )
        self.db.add(existing)
        await self.db.commit()
        submission, _ = await self.submit(
            key="e2222222-2222-4222-8222-222222222222",
            phone="13800008103",
            email="new-stage8e@example.com",
        )
        before_candidates = int(
            await self.db.scalar(select(func.count()).select_from(Candidate)) or 0
        )

        detail = await self.workbench.get_submission(self.db, submission.id)
        self.assertEqual(detail.identity_review_status.value, "needs_review")
        self.assertGreaterEqual(len(detail.identity_candidates), 2)
        reviewed = await self.workbench.mark_identity_reviewed(self.db, submission.id)

        self.assertEqual(reviewed.identity_review_status.value, "reviewed")
        self.assertEqual(
            int(await self.db.scalar(select(func.count()).select_from(Candidate)) or 0),
            before_candidates,
        )
        log = await self.db.scalar(
            select(ActivityLog).where(
                ActivityLog.action == "public_application_identity_reviewed",
                ActivityLog.target_id == submission.id,
            )
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.detail["identity_review_reasons"], ["same_name"])

    async def test_manual_retry_and_resume_switch_write_audit_without_deleting_history(self) -> None:
        submission, failed = await self.submit()
        failed.status = "failed"
        failed.completed_at = NOW
        failed.error_code = "RESUME_TEXT_EXTRACTION_FAILED"
        failed.error_message = "无法读取简历原文，请检查文件后人工重试"
        await self.db.commit()

        retry = await self.workbench.create_manual_retry(self.db, submission.id)
        self.assertEqual(retry.trigger_type.value, "manual_retry")
        runs = list(
            (
                await self.db.scalars(
                    select(ApplicationProcessingRun)
                    .where(ApplicationProcessingRun.submission_id == submission.id)
                    .order_by(ApplicationProcessingRun.id)
                )
            ).all()
        )
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0].status, "failed")
        retry_log = await self.db.scalar(
            select(ActivityLog).where(
                ActivityLog.action == "public_application_manual_retry",
                ActivityLog.target_id == submission.id,
            )
        )
        self.assertEqual(retry_log.detail["new_run_id"], retry.id)

        application = await self.db.get(Application, submission.application_id)
        alternate = Resume(
            candidate_id=application.candidate_id,
            job_id=application.job_id,
            filename="alternate.txt",
            file_path="v2/resumes/alternate.txt",
            file_type="text/plain",
            file_size=4,
            raw_text="备用虚构简历",
            parse_status="parsed",
        )
        self.db.add(alternate)
        await self.db.commit()
        await screening_service.switch_current_resume(
            self.db,
            application.id,
            alternate.id,
        )
        switch_log = await self.db.scalar(
            select(ActivityLog).where(
                ActivityLog.action == "application_current_resume_changed",
                ActivityLog.target_id == application.id,
            )
        )
        self.assertEqual(switch_log.detail["previous_resume_id"], submission.resume_id)
        self.assertEqual(switch_log.detail["new_resume_id"], alternate.id)
