from __future__ import annotations

from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.interviews import install_interview_exception_handlers, router
from app.core.config import Settings
from app.core.database import get_db
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview_record import InterviewRecord
from app.models.job import Job
from app.models.resume import Resume
from app.models.stage_history import StageHistory


TEST_TIME = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
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


class InterviewApiPostgresTest(IsolatedAsyncioTestCase):
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

        job = Job(
            title="阶段 9B API 虚构岗位",
            department="自动化测试部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="仅用于 API 测试。",
            job_responsibilities="验证面试 API。",
            candidate_requirements="使用虚构资料。",
            preferred_qualifications="无。",
            public_notes="测试后回滚。",
            status="open",
        )
        candidate = Candidate(
            name="阶段 9B API 虚构候选人",
            phone="13800009993",
            email="stage9b-api@example.test",
            source="hr_screening",
            status="new",
        )
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="stage9b-api.txt",
            file_path="tests/stage9b-api.txt",
            file_type="text/plain",
            file_size=10,
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
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
        self.db.add(application)
        await self.db.commit()
        self.application_id = application.id

        self.app = FastAPI()
        install_interview_exception_handlers(self.app)
        self.app.include_router(router, prefix="/api/v2")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        self.app.dependency_overrides.clear()
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            counts_after = await counts(outside)
        await self.engine.dispose()
        self.assertEqual(counts_after, self.counts_before)

    def schedule_payload(self) -> dict:
        return {
            "round_number": 1,
            "interview_type": "video",
            "scheduled_start_at": TEST_TIME.isoformat(),
            "duration_minutes": 60,
            "timezone": "Asia/Shanghai",
            "interviewer_names": ["面试官甲"],
            "meeting_link": "https://meet.example.test/api-round-1",
        }

    async def test_real_api_schedule_reschedule_feedback_and_timeline(self) -> None:
        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/interviews",
            json=self.schedule_payload(),
        )
        self.assertEqual(response.status_code, 201)
        interview_id = response.json()["id"]

        response = await self.client.put(
            f"/api/v2/interviews/{interview_id}/schedule",
            json={
                **{key: value for key, value in self.schedule_payload().items() if key != "round_number"},
                "expected_version": 1,
                "duration_minutes": 75,
                "reason_detail": "协调面试官时间",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 2)

        response = await self.client.post(
            f"/api/v2/interviews/{interview_id}/feedback",
            json={
                "expected_version": 2,
                "feedback_summary": "人工面试通过，可以进入 Offer 准备。",
                "strengths": ["核心能力证据充分"],
                "decision": "proceed_offer",
                "reason_code": "interview_proceed_offer",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["decision"], "proceed_offer")

        response = await self.client.get(
            f"/api/v2/applications/{self.application_id}/interviews"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        response = await self.client.get(
            f"/api/v2/applications/{self.application_id}/timeline"
        )
        self.assertEqual(response.status_code, 200)
        reason_codes = {item["reason_code"] for item in response.json()}
        self.assertIn("interview_scheduled", reason_codes)
        self.assertIn("interview_rescheduled", reason_codes)
        self.assertIn("interview_proceed_offer", reason_codes)
        self.assertNotIn("meeting_link", response.text)
        self.assertNotIn("feedback_summary", response.text)

        application = await self.db.get(Application, self.application_id)
        await self.db.refresh(application)
        self.assertEqual(application.recruitment_stage, "offer")
        self.assertEqual(application.hr_decision, "passed")

    async def test_real_api_rejects_missing_confirmation_before_service_write(self) -> None:
        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/interviews",
            json=self.schedule_payload(),
        )
        interview_id = response.json()["id"]
        response = await self.client.post(
            f"/api/v2/interviews/{interview_id}/cancel",
            json={
                "expected_version": 1,
                "reason_code": "interview_canceled",
                "reason_detail": "候选人申请改期",
                "confirmed": False,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "HR_ACTION_CONFIRMATION_REQUIRED",
        )
        interview = await self.db.get(InterviewRecord, interview_id)
        await self.db.refresh(interview)
        self.assertEqual(interview.status, "scheduled")
