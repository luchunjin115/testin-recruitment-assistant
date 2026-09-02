from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.resume_structure import (
    ResumeStructureAdapterResult,
    ResumeStructureResponseInterruptedError,
    ResumeStructureTimeoutError,
)
from app.core.config import Settings
from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.models.screening_run import ScreeningRun
from app.models.stage_history import StageHistory
from app.schemas.public_application import PublicApplicationForm
from app.services.application_processing_service import ApplicationProcessingService
from app.services.public_application_service import PublicApplicationService
from app.services.resume_service import resume_service
from app.services.resume_storage import ResumeFileStorage
from app.services.resume_structure_service import resume_structure_service
from app.services.screening_service import screening_service


NOW = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    StageHistory,
    PublicApplicationSubmission,
    ApplicationProcessingRun,
    ScreeningRun,
)


def draft_payload() -> dict:
    return {
        "schema_version": "1.0",
        "basic_info": {
            "name": "虚构处理候选人",
            "phone": None,
            "email": None,
            "gender": None,
            "age": None,
            "location": "长沙",
            "current_company": None,
            "current_title": "后端工程师",
            "work_years": None,
            "education_level": None,
        },
        "education_records": [],
        "work_experiences": [],
        "project_experiences": [],
        "skills": ["Python"],
        "certifications": [],
        "self_evaluation": None,
        "warnings": [],
        "missing_fields": [],
    }


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class ApplicationProcessingServicePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        base_settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            base_settings.async_database_url,
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
        self.settings = Settings(
            _env_file=None,
            STORAGE_DIR=str(self.root),
            APPLICATION_PROCESSING_RETRY_BACKOFF_SECONDS=0,
        )
        self.storage = ResumeFileStorage()
        self.intake = PublicApplicationService()
        self.processing = ApplicationProcessingService()
        self.job = Job(
            title="阶段 8C 虚构岗位",
            department="演示研发部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="仅用于自动化测试。",
            job_responsibilities="验证持久任务处理。",
            candidate_requirements="具备 Python 项目经验。",
            preferred_qualifications="有 PostgreSQL 经验优先。",
            public_notes="所有记录在测试后回滚。",
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

    def form(
        self,
        *,
        key: str = "c1111111-1111-4111-8111-111111111111",
        phone: str = "13800008001",
        email: str = "stage8c-a@example.com",
    ) -> PublicApplicationForm:
        return PublicApplicationForm(
            name="虚构处理候选人",
            phone=phone,
            email=email,
            job_id=self.job.id,
            privacy_consent=True,
            consent_version="2026-09-02",
            idempotency_key=UUID(key),
        )

    async def submit(self, data: PublicApplicationForm | None = None):
        prepared = await self.storage.prepare(
            UploadFile(
                filename="resume.txt",
                file=BytesIO("虚构候选人 Python 项目经历".encode("utf-8")),
            ),
            self.root,
            1024,
        )
        result = await self.intake.accept(
            self.db,
            data or self.form(),
            prepared,
            storage=self.storage,
        )
        submission = await self.db.scalar(
            select(PublicApplicationSubmission).where(
                PublicApplicationSubmission.submission_reference
                == result.submission_reference
            )
        )
        run = await self.db.scalar(
            select(ApplicationProcessingRun).where(
                ApplicationProcessingRun.submission_id == submission.id
            )
        )
        return submission, run

    @staticmethod
    def adapter(*side_effects: Exception) -> Mock:
        adapter = Mock()
        success = ResumeStructureAdapterResult(
            content=json.dumps(draft_payload(), ensure_ascii=False),
            model="fake-stage8c-structure",
            finish_reason="stop",
            input_tokens=12,
            output_tokens=34,
        )
        effects = [*side_effects, success] if side_effects else None
        adapter.extract = AsyncMock(
            return_value=success,
            side_effect=effects,
        )
        return adapter

    async def claim(self, worker: str = "worker-a", *, clock=NOW):
        return await self.processing.claim_next_run(
            self.db,
            worker_id=worker,
            lease_seconds=self.settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
            max_attempts=self.settings.APPLICATION_PROCESSING_MAX_ATTEMPTS,
            clock=lambda: clock,
        )

    async def execute(self, run_id: int, adapter: Mock, worker: str = "worker-a"):
        return await self.processing.execute_run(
            self.db,
            run_id,
            worker_id=worker,
            settings=self.settings,
            structure_adapter=adapter,
            clock=lambda: NOW,
            sleeper=AsyncMock(),
        )

    async def test_full_non_ai_chain_extracts_structures_and_waits_for_stage7(self) -> None:
        submission, queued = await self.submit()
        resume_id = submission.resume_id
        application_id = submission.application_id
        claimed = await self.claim()
        self.assertEqual(claimed.id, queued.id)
        self.assertEqual(claimed.status, "running")
        self.assertEqual(claimed.attempt_count, 1)
        structure_adapter = self.adapter()

        result = await self.execute(claimed.id, structure_adapter)

        self.assertEqual(result.run.status, "waiting_screening")
        self.assertEqual(result.run.current_step, "await_screening")
        resume = await self.db.get(Resume, resume_id)
        self.assertEqual(resume.parse_status, "parsed")
        self.assertIn("Python", resume.raw_text)
        self.assertEqual(resume.structure_status, "succeeded")
        self.assertEqual(resume.parsed_snapshot["metadata"]["model"], "fake-stage8c-structure")
        stage7_run = await self.db.scalar(
            select(ScreeningRun).where(
                ScreeningRun.application_id == application_id
            )
        )
        self.assertEqual(stage7_run.status, "waiting_plan")
        structure_adapter.extract.assert_awaited_once()

    async def test_waiting_screening_reconciles_to_success_without_model_call(self) -> None:
        submission, queued = await self.submit()
        application_id = submission.application_id
        claimed = await self.claim()
        await self.execute(claimed.id, self.adapter())
        stage7_run = await self.db.scalar(
            select(ScreeningRun)
            .where(ScreeningRun.application_id == application_id)
            .with_for_update()
        )
        stage7_run.status = "succeeded"
        stage7_run.waiting_reason = None
        stage7_run.completed_at = NOW
        await self.db.commit()

        waiting_claim = await self.claim(worker="worker-b")
        result = await self.execute(
            waiting_claim.id,
            self.adapter(),
            worker="worker-b",
        )

        self.assertEqual(waiting_claim.id, queued.id)
        self.assertEqual(result.run.status, "succeeded")
        self.assertEqual(result.run.current_step, "completed")
        self.assertIsNotNone(result.run.completed_at)

    async def test_waiting_screening_reconciles_stage7_failure_safely(self) -> None:
        submission, _ = await self.submit(
            self.form(
                key="c2222222-2222-4222-8222-222222222222",
                phone="13800008002",
                email="stage8c-failed@example.com",
            )
        )
        application_id = submission.application_id
        claimed = await self.claim()
        await self.execute(claimed.id, self.adapter())
        stage7_run = await self.db.scalar(
            select(ScreeningRun)
            .where(ScreeningRun.application_id == application_id)
            .with_for_update()
        )
        stage7_run.status = "failed"
        stage7_run.waiting_reason = None
        stage7_run.error_code = "SCREENING_TEST_FAILURE"
        stage7_run.error_message = "虚构初筛失败"
        stage7_run.completed_at = NOW
        await self.db.commit()

        waiting_claim = await self.claim(worker="worker-b")
        result = await self.execute(
            waiting_claim.id,
            self.adapter(),
            worker="worker-b",
        )

        self.assertEqual(result.run.status, "failed")
        self.assertEqual(result.run.current_step, "await_screening")
        self.assertEqual(result.run.error_code, "SCREENING_TEST_FAILURE")
        self.assertEqual(result.run.error_message, "虚构初筛失败")

    async def test_structure_content_failure_adds_warning_and_still_triggers_screening(self) -> None:
        submission, queued = await self.submit()
        application_id = submission.application_id
        claimed = await self.claim()
        adapter = self.adapter(
            ResumeStructureResponseInterruptedError("虚构的确定性内容错误")
        )

        result = await self.execute(claimed.id, adapter)

        self.assertEqual(result.run.status, "waiting_screening")
        self.assertEqual(result.run.warning_codes, ["RESUME_STRUCTURE_FAILED"])
        resume = await self.db.get(Resume, queued.resume_id)
        self.assertEqual(resume.structure_status, "failed")
        adapter.extract.assert_awaited_once()

        stage7_run = await self.db.scalar(
            select(ScreeningRun)
            .where(ScreeningRun.application_id == application_id)
            .with_for_update()
        )
        stage7_run.status = "succeeded"
        stage7_run.waiting_reason = None
        stage7_run.completed_at = NOW
        await self.db.commit()
        waiting_claim = await self.claim(worker="worker-b")
        completed = await self.execute(
            waiting_claim.id,
            self.adapter(),
            worker="worker-b",
        )
        self.assertEqual(completed.run.status, "succeeded_with_warnings")

    async def test_existing_successful_resume_steps_are_skipped(self) -> None:
        submission, _ = await self.submit(
            self.form(
                key="c3333333-3333-4333-8333-333333333333",
                phone="13800008003",
                email="stage8c-skip@example.com",
            )
        )
        await resume_service.extract_text(
            self.db,
            submission.resume_id,
            self.root,
        )
        first_adapter = self.adapter()
        await resume_structure_service.structure_resume(
            self.db,
            submission.resume_id,
            adapter=first_adapter,
            settings=self.settings,
        )
        first_adapter.extract.assert_awaited_once()
        cached_adapter = self.adapter()

        claimed = await self.claim()
        result = await self.execute(claimed.id, cached_adapter)

        self.assertEqual(result.run.status, "waiting_screening")
        cached_adapter.extract.assert_not_awaited()

    async def test_structure_infrastructure_failure_retries_twice_then_succeeds(self) -> None:
        _, _ = await self.submit()
        claimed = await self.claim()
        adapter = self.adapter(
            ResumeStructureTimeoutError("虚构超时一"),
            ResumeStructureTimeoutError("虚构超时二"),
        )
        sleeper = AsyncMock()

        result = await self.processing.execute_run(
            self.db,
            claimed.id,
            worker_id="worker-a",
            settings=self.settings,
            structure_adapter=adapter,
            clock=lambda: NOW,
            sleeper=sleeper,
        )

        self.assertEqual(result.run.status, "waiting_screening")
        self.assertEqual(result.run.warning_codes, [])
        self.assertEqual(adapter.extract.await_count, 3)
        self.assertEqual(sleeper.await_count, 2)

    async def test_closed_job_pauses_after_local_steps_and_reopen_resumes(self) -> None:
        _, queued = await self.submit()
        self.job.status = "closed"
        await self.db.commit()
        claimed = await self.claim()

        paused = await self.execute(claimed.id, self.adapter())

        self.assertEqual(paused.run.status, "paused")
        self.assertEqual(paused.run.current_step, "trigger_screening")
        self.assertEqual(paused.run.waiting_reason, "job_closed")
        resume = await self.db.get(Resume, queued.resume_id)
        self.assertEqual(resume.parse_status, "parsed")
        self.assertEqual(resume.structure_status, "succeeded")

        self.job.status = "open"
        await self.db.commit()
        resumed = await self.claim(worker="worker-b")
        result = await self.execute(resumed.id, self.adapter(), worker="worker-b")
        self.assertEqual(result.run.status, "waiting_screening")

    async def test_expired_lease_recovers_and_attempt_limit_is_terminal(self) -> None:
        _, queued = await self.submit()
        first = await self.claim(worker="worker-a", clock=NOW)
        second = await self.claim(
            worker="worker-b",
            clock=NOW + timedelta(seconds=301),
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.attempt_count, 2)
        third = await self.claim(
            worker="worker-c",
            clock=NOW + timedelta(seconds=602),
        )
        self.assertEqual(third.attempt_count, 3)

        exhausted = await self.claim(
            worker="worker-d",
            clock=NOW + timedelta(seconds=903),
        )
        self.assertIsNone(exhausted)
        run = await self.db.get(ApplicationProcessingRun, queued.id)
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.error_code, "APPLICATION_PROCESSING_ATTEMPTS_EXHAUSTED")

    async def test_manual_retry_creates_new_history_and_keeps_failed_run(self) -> None:
        submission, queued = await self.submit()
        claimed = await self.claim()
        resume = await self.db.get(Resume, submission.resume_id)
        (self.root / resume.file_path).unlink()
        failed = await self.execute(claimed.id, self.adapter())
        self.assertEqual(failed.run.status, "failed")
        self.assertEqual(failed.run.current_step, "extract_text")

        retry = await self.processing.create_manual_retry(self.db, submission.id)

        self.assertEqual(retry.trigger_type, "manual_retry")
        self.assertEqual(retry.status, "queued")
        self.assertEqual(retry.current_step, "extract_text")
        runs = list(
            (
                await self.db.scalars(
                    select(ApplicationProcessingRun)
                    .where(ApplicationProcessingRun.submission_id == submission.id)
                    .order_by(ApplicationProcessingRun.id)
                )
            ).all()
        )
        self.assertEqual([run.id for run in runs], [queued.id, retry.id])
        self.assertEqual(runs[0].status, "failed")

    async def test_existing_internal_application_waits_for_resume_choice_then_resumes(self) -> None:
        candidate = Candidate(
            name="内部虚构候选人",
            phone="13800008009",
            email="stage8c-internal@example.com",
            source="hr_screening",
            status="new",
        )
        self.db.add(candidate)
        await self.db.flush()
        old_resume = Resume(
            candidate_id=candidate.id,
            job_id=self.job.id,
            filename="old.txt",
            file_path="v2/resumes/old.txt",
            file_type="text/plain",
            file_size=3,
            raw_text="旧虚构简历",
            parse_status="parsed",
        )
        self.db.add(old_resume)
        await self.db.flush()
        application = Application(
            candidate_id=candidate.id,
            job_id=self.job.id,
            current_resume_id=old_resume.id,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="applied",
            hr_decision="pending",
        )
        self.db.add(application)
        await self.db.commit()
        submission, queued = await self.submit(
            self.form(
                key="c9999999-9999-4999-8999-999999999999",
                phone=candidate.phone,
                email=candidate.email,
            )
        )
        claimed = await self.claim()

        paused = await self.execute(claimed.id, self.adapter())

        self.assertEqual(paused.run.status, "paused")
        self.assertEqual(
            paused.run.waiting_reason,
            "existing_application_resume_choice",
        )
        await self.db.refresh(application)
        self.assertEqual(application.current_resume_id, old_resume.id)
        self.assertEqual(queued.application_id, application.id)

        await screening_service.switch_current_resume(
            self.db,
            application.id,
            submission.resume_id,
        )
        resumed = await self.claim(worker="worker-b")
        result = await self.execute(resumed.id, self.adapter(), worker="worker-b")
        self.assertEqual(result.run.status, "waiting_screening")
