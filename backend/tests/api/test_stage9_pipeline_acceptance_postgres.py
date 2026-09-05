from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest import IsolatedAsyncioTestCase

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.interviews import (
    install_interview_exception_handlers,
    router as interview_router,
)
from app.api.offers import install_offer_exception_handlers, router as offer_router
from app.api.recruitment_statistics import router as statistics_router
from app.api.screening_center import router as screening_center_router
from app.core.config import Settings
from app.core.database import get_db
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview_record import InterviewRecord
from app.models.job import Job
from app.models.offer_record import OfferRecord
from app.models.resume import Resume
from app.models.stage_history import StageHistory


UTC = timezone.utc
NOW = datetime(2026, 9, 5, 8, 0, tzinfo=UTC)
COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    StageHistory,
    InterviewRecord,
    OfferRecord,
    ActivityLog,
)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class Stage9PipelineAcceptancePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            settings.async_database_url,
            poolclass=NullPool,
        )
        async with AsyncSession(self.engine) as outside:
            self.before = await counts(outside)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        job = Job(title="阶段 9F 虚构端到端岗位", status="open")
        candidate = Candidate(
            name="阶段 9F 虚构候选人",
            phone="13800009090",
            email="stage9f@example.test",
            source="hr_screening",
            status="screening",
        )
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="stage9f-fictional.txt",
            file_path="tests/stage9f-fictional.txt",
            file_type="text/plain",
            file_size=20,
            raw_text="阶段 9F 虚构简历正文，不应出现在统计或时间线。",
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
            applied_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        self.db.add(application)
        await self.db.flush()
        self.db.add(
            StageHistory(
                application_id=application.id,
                from_lifecycle_status=None,
                to_lifecycle_status="active",
                from_recruitment_stage=None,
                to_recruitment_stage="screening_passed",
                from_hr_decision=None,
                to_hr_decision="passed",
                from_final_outcome=None,
                to_final_outcome=None,
                reason_code="application_created_hr_direct",
                actor_type="hr",
                actor_id="stage9f",
                actor_label="阶段 9F 虚构 HR",
                created_at=NOW,
            )
        )
        await self.db.commit()
        self.application_id = application.id
        self.job_id = job.id

        self.app = FastAPI()
        install_interview_exception_handlers(self.app)
        install_offer_exception_handlers(self.app)
        self.app.include_router(interview_router, prefix="/api/v2")
        self.app.include_router(offer_router, prefix="/api/v2")
        self.app.include_router(statistics_router, prefix="/api/v2")
        self.app.include_router(screening_center_router, prefix="/api/v2")

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
            after = await counts(outside)
        await self.engine.dispose()
        self.assertEqual(after, self.before)

    @staticmethod
    def schedule(round_number: int, start: datetime) -> dict:
        return {
            "round_number": round_number,
            "interview_type": "video",
            "scheduled_start_at": start.isoformat(),
            "duration_minutes": 60,
            "timezone": "Asia/Shanghai",
            "interviewer_names": [f"阶段 9F 虚构面试官 {round_number}"],
            "meeting_link": f"https://meet.example.test/stage9f-round-{round_number}",
        }

    @staticmethod
    def feedback(decision: str, reason_code: str) -> dict:
        return {
            "expected_version": 1,
            "feedback_summary": f"阶段 9F 虚构反馈：{decision}",
            "strengths": ["虚构工程实践证据"],
            "concerns": [],
            "follow_up_questions": [],
            "decision": decision,
            "reason_code": reason_code,
        }

    @staticmethod
    def confirmed(version: int, reason_code: str, detail: str) -> dict:
        return {
            "expected_version": version,
            "reason_code": reason_code,
            "reason_detail": detail,
            "confirmed": True,
        }

    async def test_two_interviews_offer_accept_admit_hire_and_statistics(self) -> None:
        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/interviews",
            json=self.schedule(1, NOW + timedelta(days=1)),
        )
        self.assertEqual(response.status_code, 201)
        first_id = response.json()["id"]

        response = await self.client.post(
            f"/api/v2/interviews/{first_id}/feedback",
            json=self.feedback("next_round", "interview_next_round"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "next_round")

        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/interviews",
            json=self.schedule(2, NOW + timedelta(days=2)),
        )
        self.assertEqual(response.status_code, 201)
        second_id = response.json()["id"]

        response = await self.client.post(
            f"/api/v2/interviews/{second_id}/feedback",
            json=self.feedback("proceed_offer", "interview_proceed_offer"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "proceed_offer")

        valid_until = date.today() + timedelta(days=30)
        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/offers",
            json={
                "position_title": "阶段 9F 虚构工程师",
                "currency": "CNY",
                "salary_period": "monthly",
                "base_salary_amount": "18888.80",
                "salary_months": "13.0",
                "bonus_note": "阶段 9F 虚构奖金",
                "benefits_note": "阶段 9F 虚构福利",
                "valid_until": valid_until.isoformat(),
                "expected_start_date": (valid_until + timedelta(days=15)).isoformat(),
                "note": "阶段 9F 虚构内部说明",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["base_salary_amount"], "18888.80")
        offer_id = response.json()["id"]

        response = await self.client.post(
            f"/api/v2/offers/{offer_id}/send",
            json=self.confirmed(1, "offer_sent", "已通过虚构线下渠道发送"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")
        response = await self.client.post(
            f"/api/v2/offers/{offer_id}/accept",
            json=self.confirmed(2, "offer_accepted", "候选人明确接受虚构 Offer"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")

        accepted_stats = await self.client.get(
            "/api/v2/recruitment-statistics", params={"job_id": self.job_id}
        )
        self.assertEqual(accepted_stats.status_code, 200)
        accepted_funnel = {
            item["key"]: item["count"] for item in accepted_stats.json()["funnel"]
        }
        self.assertEqual(accepted_funnel["offer_accepted"], 1)
        self.assertEqual(accepted_funnel["admitted"], 0)
        self.assertEqual(accepted_funnel["hired"], 0)
        self.assertEqual(accepted_stats.json()["todos"]["accepted_offers"], 1)

        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/confirm-admission",
            json=self.confirmed(3, "application_admitted", "HR 独立确认虚构录取"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitment_stage"], "admitted")
        self.assertIsNone(response.json()["final_outcome"])
        self.assertEqual(response.json()["hr_decision"], "passed")

        admitted_stats = await self.client.get(
            "/api/v2/recruitment-statistics", params={"job_id": self.job_id}
        )
        self.assertEqual(admitted_stats.json()["todos"]["accepted_offers"], 0)
        self.assertEqual(admitted_stats.json()["todos"]["admitted_applications"], 1)

        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/confirm-hire",
            json=self.confirmed(3, "application_hired", "HR 独立确认虚构正式到岗"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lifecycle_status"], "ended")
        self.assertEqual(response.json()["recruitment_stage"], "hired")
        self.assertEqual(response.json()["final_outcome"], "hired")
        self.assertEqual(response.json()["hr_decision"], "passed")

        final_stats = await self.client.get(
            "/api/v2/recruitment-statistics", params={"job_id": self.job_id}
        )
        self.assertEqual(final_stats.status_code, 200)
        self.assertEqual(
            [item["count"] for item in final_stats.json()["funnel"]],
            [1, 1, 1, 1, 1, 1, 1, 1],
        )
        self.assertEqual(final_stats.json()["todos"]["total"], 0)
        self.assertNotIn("salary", final_stats.text.lower())
        self.assertNotIn("18888.80", final_stats.text)

        timeline = await self.client.get(
            f"/api/v2/applications/{self.application_id}/timeline"
        )
        self.assertEqual(timeline.status_code, 200)
        reason_codes = {item["reason_code"] for item in timeline.json()}
        for reason_code in (
            "interview_scheduled",
            "interview_next_round",
            "interview_proceed_offer",
            "offer_sent",
            "offer_accepted",
            "application_admitted",
            "application_hired",
        ):
            self.assertIn(reason_code, reason_codes)
        self.assertNotIn("18888.80", timeline.text)
        self.assertNotIn("meeting_link", timeline.text)
        self.assertNotIn("feedback_summary", timeline.text)

        screening = await self.client.get(
            "/api/v2/screening-center/applications",
            params={"job_id": self.job_id, "view": "candidate"},
        )
        self.assertEqual(screening.status_code, 200)
        self.assertEqual(screening.json()["total"], 1)
        self.assertEqual(screening.json()["items"][0]["recruitment_stage"], "hired")
        self.assertNotIn("salary", screening.text.lower())
        self.assertNotIn("18888.80", screening.text)

        offers = await self.client.get(
            f"/api/v2/applications/{self.application_id}/offers"
        )
        self.assertEqual(offers.status_code, 200)
        self.assertEqual(offers.json()[0]["base_salary_amount"], "18888.80")

        application = await self.db.get(Application, self.application_id)
        await self.db.refresh(application)
        self.assertEqual(
            (
                application.lifecycle_status,
                application.recruitment_stage,
                application.hr_decision,
                application.final_outcome,
            ),
            ("ended", "hired", "passed", "hired"),
        )
        stage_values = list(
            await self.db.scalars(
                select(StageHistory.to_recruitment_stage)
                .where(StageHistory.application_id == self.application_id)
                .order_by(StageHistory.id)
            )
        )
        for stage in (
            "screening_passed",
            "interview",
            "offer",
            "offer_accepted",
            "admitted",
            "hired",
        ):
            self.assertIn(stage, stage_values)
        activities = list(
            await self.db.scalars(
                select(ActivityLog).where(
                    ActivityLog.target_id.in_([first_id, second_id, offer_id, self.application_id])
                )
            )
        )
        self.assertNotIn("18888.80", repr([item.detail for item in activities]))
