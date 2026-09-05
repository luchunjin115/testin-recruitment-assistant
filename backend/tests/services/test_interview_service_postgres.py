from __future__ import annotations

from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
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
from app.schemas.interview import (
    InterviewCancelRequest,
    InterviewFeedbackSubmitRequest,
    InterviewFeedbackUpdateRequest,
    InterviewNoShowRequest,
    InterviewScheduleCreate,
    InterviewScheduleUpdate,
)
from app.schemas.offer import Stage9ReopenRequest
from app.services.interview_service import (
    ApplicationNotReadyForInterviewError,
    InterviewService,
    InterviewVersionConflictError,
)
from app.services.offer_service import OfferService
from app.services.recruitment_timeline_service import RecruitmentTimelineService


TEST_TIME = datetime(2026, 9, 10, 2, 0, tzinfo=timezone.utc)
COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    InterviewRecord,
    StageHistory,
    ActivityLog,
)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class InterviewServicePostgresTest(IsolatedAsyncioTestCase):
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
        self.service = InterviewService()
        self.timeline_service = RecruitmentTimelineService()

        self.job = Job(
            title="阶段 9B 虚构岗位",
            department="自动化测试部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="仅用于事务测试。",
            job_responsibilities="验证面试流程。",
            candidate_requirements="使用虚构资料。",
            preferred_qualifications="无。",
            public_notes="测试后回滚。",
            status="open",
        )
        candidate = Candidate(
            name="阶段 9B 虚构候选人",
            phone="13800009991",
            email="stage9b-test@example.test",
            source="hr_screening",
            status="new",
        )
        self.db.add_all([self.job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=self.job.id,
            filename="stage9b-fictional.txt",
            file_path="tests/stage9b-fictional.txt",
            file_type="text/plain",
            file_size=10,
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
        self.application = Application(
            candidate_id=candidate.id,
            job_id=self.job.id,
            current_resume_id=resume.id,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="screening_passed",
            hr_decision="passed",
            final_outcome=None,
        )
        self.db.add(self.application)
        await self.db.commit()
        self.application_id = self.application.id

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            counts_after = await counts(outside)
        await self.engine.dispose()
        self.assertEqual(counts_after, self.counts_before)

    def schedule(self, round_number: int = 1) -> InterviewScheduleCreate:
        return InterviewScheduleCreate(
            round_number=round_number,
            interview_type="video",
            scheduled_start_at=TEST_TIME,
            duration_minutes=60,
            timezone="Asia/Shanghai",
            interviewer_names=["面试官甲"],
            meeting_link=f"https://meet.example.test/round-{round_number}",
        )

    async def test_multiround_reschedule_cancel_and_timeline_are_consistent(self) -> None:
        first = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "interview")

        first = await self.service.reschedule_interview(
            self.db,
            first.id,
            InterviewScheduleUpdate(
                expected_version=1,
                interview_type="video",
                scheduled_start_at=datetime(
                    2026, 9, 11, 2, 0, tzinfo=timezone.utc
                ),
                duration_minutes=75,
                timezone="Asia/Shanghai",
                interviewer_names=["面试官甲", "面试官乙"],
                meeting_link="https://meet.example.test/round-1-new",
                reason_detail="协调面试官时间",
            ),
        )
        self.assertEqual(first.version, 2)

        first = await self.service.submit_feedback(
            self.db,
            first.id,
            InterviewFeedbackSubmitRequest(
                expected_version=2,
                feedback_summary="面试已完成，等待主管确认下一步。",
                strengths=["能清楚解释事务边界"],
                decision="pending",
                reason_code="interview_round_completed",
            ),
        )
        self.assertEqual(first.status, "completed")
        self.assertEqual(first.version, 3)

        first = await self.service.update_feedback(
            self.db,
            first.id,
            InterviewFeedbackUpdateRequest(
                expected_version=3,
                feedback_summary="主管复核后决定进入下一轮。",
                strengths=["能清楚解释事务边界"],
                decision="next_round",
                reason_code="stage9_correction",
                correction_reason="补充主管复核结论",
                confirmed=True,
            ),
        )
        self.assertEqual(first.decision, "next_round")
        self.assertEqual(first.version, 4)

        second = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule(2)
        )
        second = await self.service.cancel_interview(
            self.db,
            second.id,
            InterviewCancelRequest(
                expected_version=1,
                reason_code="interview_canceled",
                reason_detail="候选人申请重新安排",
                confirmed=True,
            ),
        )
        before_retry = await counts(self.db)
        repeated = await self.service.cancel_interview(
            self.db,
            second.id,
            InterviewCancelRequest(
                expected_version=1,
                reason_code="interview_canceled",
                reason_detail="候选人申请重新安排",
                confirmed=True,
            ),
        )
        self.assertEqual(repeated.version, second.version)
        self.assertEqual(await counts(self.db), before_retry)

        third = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule(3)
        )
        self.assertEqual(third.round_number, 3)

        timeline = await self.timeline_service.list_timeline(
            self.db, self.application_id
        )
        self.assertEqual(timeline[0].reason_code, "interview_scheduled")
        self.assertIn("interview_rescheduled", {item.reason_code for item in timeline})
        self.assertIn("interview_canceled", {item.reason_code for item in timeline})
        self.assertNotIn("meeting_link", timeline[0].model_dump())
        self.assertNotIn("feedback_summary", timeline[0].model_dump())

    async def test_proceed_offer_is_atomic_and_repeated_submission_is_idempotent(self) -> None:
        interview = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        request = InterviewFeedbackSubmitRequest(
            expected_version=1,
            feedback_summary="人工确认通过面试，可以准备 Offer。",
            strengths=["岗位核心能力证据充分"],
            decision="proceed_offer",
            reason_code="interview_proceed_offer",
        )
        interview = await self.service.submit_feedback(self.db, interview.id, request)
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "offer")
        self.assertEqual(self.application.hr_decision, "passed")
        self.assertIsNone(self.application.final_outcome)

        before_retry = await counts(self.db)
        repeated = await self.service.submit_feedback(self.db, interview.id, request)
        self.assertEqual(repeated.id, interview.id)
        self.assertEqual(await counts(self.db), before_retry)
        history = await self.db.scalar(
            select(StageHistory).where(
                StageHistory.application_id == self.application_id,
                StageHistory.reason_code == "interview_proceed_offer",
            )
        )
        self.assertIsNotNone(history)
        self.assertEqual(history.from_hr_decision, "passed")
        self.assertEqual(history.to_hr_decision, "passed")

    async def test_rejection_ends_pipeline_without_rewriting_hr_decision(self) -> None:
        interview = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        await self.service.submit_feedback(
            self.db,
            interview.id,
            InterviewFeedbackSubmitRequest(
                expected_version=1,
                feedback_summary="人工面试证据不足，不进入后续流程。",
                concerns=["关键场景缺少可验证经验"],
                decision="rejected",
                reason_code="interview_rejected",
                reason_detail="面试未达到岗位要求",
                confirmed=True,
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.lifecycle_status, "ended")
        self.assertEqual(self.application.recruitment_stage, "rejected")
        self.assertEqual(self.application.hr_decision, "passed")
        self.assertEqual(self.application.final_outcome, "interview_rejected")

    async def test_no_show_does_not_end_pipeline_but_explicit_withdrawal_does(self) -> None:
        first = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        first = await self.service.mark_no_show(
            self.db,
            first.id,
            InterviewNoShowRequest(
                expected_version=1,
                reason_code="interview_no_show",
                reason_detail="约定时间未到场",
                confirmed=True,
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(first.status, "no_show")
        self.assertEqual(self.application.lifecycle_status, "active")
        self.assertIsNone(self.application.final_outcome)

        second = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule(2)
        )
        await self.service.submit_feedback(
            self.db,
            second.id,
            InterviewFeedbackSubmitRequest(
                expected_version=1,
                feedback_summary="候选人明确表示不再继续招聘流程。",
                decision="candidate_withdrew",
                reason_code="candidate_withdrew",
                reason_detail="候选人主动退出",
                confirmed=True,
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.lifecycle_status, "ended")
        self.assertEqual(self.application.recruitment_stage, "interview")
        self.assertEqual(self.application.hr_decision, "passed")
        self.assertEqual(self.application.final_outcome, "candidate_withdrew")

    async def test_no_show_can_explicitly_end_and_reopen_without_rewriting_history(self) -> None:
        interview = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        request = InterviewNoShowRequest(
            expected_version=1,
            reason_code="interview_no_show",
            reason_detail="HR 核实候选人未到场并明确结束",
            confirmed=True,
            end_application=True,
        )
        interview = await self.service.mark_no_show(self.db, interview.id, request)
        await self.db.refresh(self.application)
        self.assertEqual(interview.status, "no_show")
        self.assertEqual(self.application.lifecycle_status, "ended")
        self.assertEqual(self.application.recruitment_stage, "rejected")
        self.assertEqual(self.application.hr_decision, "passed")
        self.assertEqual(self.application.final_outcome, "interview_no_show")

        before_retry = await counts(self.db)
        repeated = await self.service.mark_no_show(self.db, interview.id, request)
        self.assertEqual(repeated.version, interview.version)
        self.assertEqual(await counts(self.db), before_retry)

        reopened = await OfferService().reopen_stage9(
            self.db,
            self.application_id,
            Stage9ReopenRequest(
                expected_version=interview.version,
                reason_code="stage9_reopened",
                reason_detail="更正未到场结束结果",
                confirmed=True,
            ),
        )
        await self.db.refresh(interview)
        self.assertEqual(reopened.lifecycle_status, "active")
        self.assertEqual(reopened.recruitment_stage, "interview")
        self.assertIsNone(reopened.final_outcome)
        self.assertEqual(interview.status, "no_show")

    async def test_backup_application_and_stale_version_are_rejected(self) -> None:
        self.application.recruitment_stage = "backup"
        self.application.hr_decision = "backup"
        await self.db.commit()
        with self.assertRaises(ApplicationNotReadyForInterviewError):
            await self.service.schedule_interview(
                self.db, self.application_id, self.schedule()
            )
        self.assertEqual(
            await self.db.scalar(
                select(func.count())
                .select_from(InterviewRecord)
                .where(InterviewRecord.application_id == self.application_id)
            ),
            0,
        )

        self.application.recruitment_stage = "screening_passed"
        self.application.hr_decision = "passed"
        await self.db.commit()
        interview = await self.service.schedule_interview(
            self.db, self.application_id, self.schedule()
        )
        with self.assertRaises(InterviewVersionConflictError):
            await self.service.reschedule_interview(
                self.db,
                interview.id,
                InterviewScheduleUpdate(
                    expected_version=99,
                    interview_type="phone",
                    scheduled_start_at=TEST_TIME,
                    duration_minutes=30,
                    timezone="Asia/Shanghai",
                    interviewer_names=["面试官乙"],
                ),
            )
        await self.db.refresh(interview)
        self.assertEqual(interview.version, 1)
        self.assertEqual(interview.interview_type, "video")

    async def test_audit_failure_rolls_back_interview_and_application(self) -> None:
        with patch.object(
            self.service,
            "_add_activity",
            AsyncMock(side_effect=RuntimeError("audit failed")),
        ):
            with self.assertRaises(RuntimeError):
                await self.service.schedule_interview(
                    self.db, self.application_id, self.schedule()
                )

        self.db.expire_all()
        application = await self.db.get(Application, self.application_id)
        self.assertEqual(application.recruitment_stage, "screening_passed")
        self.assertEqual(
            await self.db.scalar(
                select(func.count())
                .select_from(InterviewRecord)
                .where(InterviewRecord.application_id == self.application_id)
            ),
            0,
        )
        self.assertEqual(
            await self.db.scalar(
                select(func.count())
                .select_from(StageHistory)
                .where(StageHistory.application_id == self.application_id)
            ),
            0,
        )
