from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest import IsolatedAsyncioTestCase

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview_record import InterviewRecord
from app.models.job import Job
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.interview import InterviewScheduleCreate, InterviewScheduleUpdate
from app.services.interview_service import (
    InterviewRoundConflictError,
    InterviewService,
    InterviewVersionConflictError,
)


TEST_TIME = datetime(2026, 9, 12, 2, 0, tzinfo=timezone.utc)


class InterviewServiceConcurrencyPostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            settings.async_database_url,
            poolclass=NullPool,
        )
        self.service = InterviewService()
        async with AsyncSession(self.engine, expire_on_commit=False) as db:
            job = Job(
                title="阶段 9B 并发虚构岗位",
                department="自动化测试部",
                location="长沙",
                employment_type="full_time",
                headcount=1,
                job_background="仅用于并发测试。",
                job_responsibilities="验证行锁和乐观版本。",
                candidate_requirements="使用虚构资料。",
                preferred_qualifications="无。",
                public_notes="测试后精确删除。",
                status="open",
            )
            candidate = Candidate(
                name="阶段 9B 并发虚构候选人",
                phone="13800009992",
                email="stage9b-concurrency@example.test",
                source="hr_screening",
                status="new",
            )
            db.add_all([job, candidate])
            await db.flush()
            resume = Resume(
                candidate_id=candidate.id,
                job_id=job.id,
                filename="stage9b-concurrency.txt",
                file_path="tests/stage9b-concurrency.txt",
                file_type="text/plain",
                file_size=10,
                parse_status="parsed",
            )
            db.add(resume)
            await db.flush()
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id,
                current_resume_id=resume.id,
                source="hr_screening",
                lifecycle_status="active",
                recruitment_stage="screening_passed",
                hr_decision="passed",
                final_outcome=None,
            )
            db.add(application)
            await db.commit()
            self.job_id = job.id
            self.candidate_id = candidate.id
            self.resume_id = resume.id
            self.application_id = application.id

    async def asyncTearDown(self) -> None:
        async with AsyncSession(self.engine) as db:
            interview_ids = list(
                (
                    await db.scalars(
                        select(InterviewRecord.id).where(
                            InterviewRecord.application_id == self.application_id
                        )
                    )
                ).all()
            )
            if interview_ids:
                await db.execute(
                    delete(ActivityLog).where(
                        ActivityLog.target_type == "interview",
                        ActivityLog.target_id.in_(interview_ids),
                    )
                )
            await db.execute(
                delete(StageHistory).where(
                    StageHistory.application_id == self.application_id
                )
            )
            await db.execute(
                delete(InterviewRecord).where(
                    InterviewRecord.application_id == self.application_id
                )
            )
            await db.execute(
                delete(Application).where(Application.id == self.application_id)
            )
            await db.execute(delete(Resume).where(Resume.id == self.resume_id))
            await db.execute(
                delete(Candidate).where(Candidate.id == self.candidate_id)
            )
            await db.execute(delete(Job).where(Job.id == self.job_id))
            await db.commit()
        await self.engine.dispose()

    def schedule(self) -> InterviewScheduleCreate:
        return InterviewScheduleCreate(
            round_number=1,
            interview_type="video",
            scheduled_start_at=TEST_TIME,
            duration_minutes=60,
            timezone="Asia/Shanghai",
            interviewer_names=["面试官甲"],
        )

    async def test_concurrent_first_round_creation_produces_one_record(self) -> None:
        async def create_once():
            async with AsyncSession(self.engine, expire_on_commit=False) as db:
                return await self.service.schedule_interview(
                    db, self.application_id, self.schedule()
                )

        results = await asyncio.gather(
            create_once(),
            create_once(),
            return_exceptions=True,
        )
        self.assertEqual(
            sum(isinstance(result, InterviewRecord) for result in results),
            1,
        )
        self.assertEqual(
            sum(isinstance(result, InterviewRoundConflictError) for result in results),
            1,
        )
        async with AsyncSession(self.engine) as db:
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(InterviewRecord)
                    .where(InterviewRecord.application_id == self.application_id)
                ),
                1,
            )
            application = await db.get(Application, self.application_id)
            self.assertEqual(application.recruitment_stage, "interview")

    async def test_concurrent_reschedule_has_one_winner_and_one_version_conflict(self) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as setup_db:
            interview = await self.service.schedule_interview(
                setup_db, self.application_id, self.schedule()
            )
            interview_id = interview.id

        async def reschedule_once(offset: int):
            async with AsyncSession(self.engine, expire_on_commit=False) as db:
                return await self.service.reschedule_interview(
                    db,
                    interview_id,
                    InterviewScheduleUpdate(
                        expected_version=1,
                        interview_type="video",
                        scheduled_start_at=TEST_TIME + timedelta(hours=offset),
                        duration_minutes=60,
                        timezone="Asia/Shanghai",
                        interviewer_names=["面试官甲"],
                        reason_detail=f"并发改期方案 {offset}",
                    ),
                )

        results = await asyncio.gather(
            reschedule_once(1),
            reschedule_once(2),
            return_exceptions=True,
        )
        self.assertEqual(
            sum(isinstance(result, InterviewRecord) for result in results),
            1,
        )
        self.assertEqual(
            sum(isinstance(result, InterviewVersionConflictError) for result in results),
            1,
        )
        async with AsyncSession(self.engine) as db:
            stored = await db.get(InterviewRecord, interview_id)
            self.assertEqual(stored.version, 2)
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(ActivityLog)
                    .where(
                        ActivityLog.target_type == "interview",
                        ActivityLog.target_id == interview_id,
                        ActivityLog.action == "interview_rescheduled",
                    )
                ),
                1,
            )
