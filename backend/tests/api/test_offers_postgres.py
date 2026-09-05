from __future__ import annotations

from datetime import date, timedelta
from unittest import IsolatedAsyncioTestCase

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.offers import install_offer_exception_handlers, router
from app.core.config import Settings
from app.core.database import get_db
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.offer_record import OfferRecord
from app.models.resume import Resume
from app.models.stage_history import StageHistory


COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    OfferRecord,
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


class OfferApiPostgresTest(IsolatedAsyncioTestCase):
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
            title="阶段 9D API 虚构岗位",
            department="自动化测试部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="仅用于 API 事务测试。",
            job_responsibilities="验证 Offer API。",
            candidate_requirements="使用虚构资料。",
            preferred_qualifications="无。",
            public_notes="测试后回滚。",
            status="open",
        )
        candidate = Candidate(
            name="阶段 9D API 虚构候选人",
            phone="13800009994",
            email="stage9d-api@example.test",
            source="hr_screening",
            status="new",
        )
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="stage9d-api-fictional.txt",
            file_path="tests/stage9d-api-fictional.txt",
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
            recruitment_stage="offer",
            hr_decision="passed",
            final_outcome=None,
        )
        self.db.add(application)
        await self.db.commit()
        self.application_id = application.id

        self.app = FastAPI()
        install_offer_exception_handlers(self.app)
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

    def details(self) -> dict:
        valid_until = date.today() + timedelta(days=30)
        return {
            "position_title": "阶段 9D API 虚构工程师",
            "currency": "CNY",
            "salary_period": "monthly",
            "base_salary_amount": "18888.80",
            "salary_months": "13.0",
            "bonus_note": "虚构奖金",
            "benefits_note": "虚构福利",
            "valid_until": valid_until.isoformat(),
            "expected_start_date": (valid_until + timedelta(days=15)).isoformat(),
            "note": "虚构内部备注",
        }

    def action(self, version: int, reason_code: str, detail: str) -> dict:
        return {
            "expected_version": version,
            "reason_code": reason_code,
            "reason_detail": detail,
            "confirmed": True,
        }

    async def test_real_api_offer_to_hired_keeps_exact_salary_and_hr_pass(self) -> None:
        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/offers",
            json=self.details(),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["base_salary_amount"], "18888.80")
        offer_id = response.json()["id"]

        response = await self.client.put(
            f"/api/v2/offers/{offer_id}",
            json={**self.details(), "expected_version": 99},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "OFFER_VERSION_CONFLICT")
        self.assertNotIn("18888.80", response.text)

        response = await self.client.post(
            f"/api/v2/offers/{offer_id}/send",
            json=self.action(1, "offer_sent", "已通过线下渠道发送"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")

        response = await self.client.post(
            f"/api/v2/offers/{offer_id}/accept",
            json=self.action(2, "offer_accepted", "候选人明确接受"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")

        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/confirm-admission",
            json=self.action(3, "application_admitted", "HR 已确认录取"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitment_stage"], "admitted")
        self.assertIsNone(response.json()["final_outcome"])

        response = await self.client.post(
            f"/api/v2/applications/{self.application_id}/confirm-hire",
            json=self.action(3, "application_hired", "HR 已确认正式到岗"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitment_stage"], "hired")
        self.assertEqual(response.json()["final_outcome"], "hired")
        self.assertEqual(response.json()["hr_decision"], "passed")

        response = await self.client.get(
            f"/api/v2/applications/{self.application_id}/offers"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["base_salary_amount"], "18888.80")

        histories = list(
            (
                await self.db.scalars(
                    select(StageHistory).where(
                        StageHistory.application_id == self.application_id
                    )
                )
            ).all()
        )
        self.assertEqual(
            [item.to_recruitment_stage for item in histories],
            ["offer_accepted", "admitted", "hired"],
        )
        self.assertTrue(all(item.to_hr_decision == "passed" for item in histories))

        activities = list(
            (
                await self.db.scalars(
                    select(ActivityLog).where(
                        ActivityLog.target_id.in_([offer_id, self.application_id])
                    )
                )
            ).all()
        )
        self.assertNotIn("18888.80", repr([item.detail for item in activities]))
