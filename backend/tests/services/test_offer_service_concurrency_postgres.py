from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.offer_record import OfferRecord
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.offer import OfferDraftCreateRequest, OfferUpdateRequest
from app.services.offer_service import (
    OfferActiveConflictError,
    OfferService,
    OfferVersionConflictError,
)


class OfferServiceConcurrencyPostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            settings.async_database_url,
            poolclass=NullPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            self.offer_count_before = int(
                await db.scalar(select(func.count()).select_from(OfferRecord)) or 0
            )
            job = Job(
                title="阶段 9D 并发虚构岗位",
                department="并发测试部",
                location="长沙",
                employment_type="full_time",
                headcount=1,
                job_background="仅用于并发测试。",
                job_responsibilities="验证行锁。",
                candidate_requirements="虚构资料。",
                preferred_qualifications="无。",
                public_notes="测试后精确清理。",
                status="open",
            )
            candidate = Candidate(
                name="阶段 9D 并发虚构候选人",
                phone="13800009993",
                email="stage9d-concurrency@example.test",
                source="hr_screening",
                status="new",
            )
            db.add_all([job, candidate])
            await db.flush()
            resume = Resume(
                candidate_id=candidate.id,
                job_id=job.id,
                filename="stage9d-concurrency-fictional.txt",
                file_path="tests/stage9d-concurrency-fictional.txt",
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
                recruitment_stage="offer",
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
        async with self.sessions() as db:
            offer_ids = list(
                (
                    await db.scalars(
                        select(OfferRecord.id).where(
                            OfferRecord.application_id == self.application_id
                        )
                    )
                ).all()
            )
            await db.execute(
                delete(ActivityLog).where(
                    (ActivityLog.target_type == "application")
                    & (ActivityLog.target_id == self.application_id)
                    | (ActivityLog.target_type == "offer")
                    & (ActivityLog.target_id.in_(offer_ids or [-1]))
                )
            )
            await db.execute(
                delete(StageHistory).where(
                    StageHistory.application_id == self.application_id
                )
            )
            await db.execute(
                delete(OfferRecord).where(
                    OfferRecord.application_id == self.application_id
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
            count_after = int(
                await db.scalar(select(func.count()).select_from(OfferRecord)) or 0
            )
        await self.engine.dispose()
        self.assertEqual(count_after, self.offer_count_before)

    def request(self, amount: str) -> OfferDraftCreateRequest:
        valid_until = date.today() + timedelta(days=30)
        return OfferDraftCreateRequest(
            position_title="阶段 9D 并发虚构工程师",
            currency="CNY",
            salary_period="monthly",
            base_salary_amount=amount,
            salary_months="13.0",
            valid_until=valid_until,
            expected_start_date=valid_until + timedelta(days=15),
        )

    async def create_in_session(self, amount: str):
        async with self.sessions() as db:
            return await OfferService().create_offer(
                db, self.application_id, self.request(amount)
            )

    async def update_in_session(self, offer_id: int, amount: str):
        details = self.request(amount).model_dump()
        async with self.sessions() as db:
            return await OfferService().update_offer(
                db,
                offer_id,
                OfferUpdateRequest(**details, expected_version=1),
            )

    async def test_two_sessions_create_and_update_allow_only_one_winner(self) -> None:
        create_results = await asyncio.gather(
            self.create_in_session("18888.80"),
            self.create_in_session("19999.90"),
            return_exceptions=True,
        )
        self.assertEqual(
            sum(isinstance(item, OfferRecord) for item in create_results), 1
        )
        self.assertEqual(
            sum(isinstance(item, OfferActiveConflictError) for item in create_results),
            1,
        )
        async with self.sessions() as db:
            offers = list(
                (
                    await db.scalars(
                        select(OfferRecord).where(
                            OfferRecord.application_id == self.application_id
                        )
                    )
                ).all()
            )
        self.assertEqual(len(offers), 1)
        offer_id = offers[0].id

        update_results = await asyncio.gather(
            self.update_in_session(offer_id, "20000.00"),
            self.update_in_session(offer_id, "21000.00"),
            return_exceptions=True,
        )
        self.assertEqual(
            sum(isinstance(item, OfferRecord) for item in update_results), 1
        )
        self.assertEqual(
            sum(isinstance(item, OfferVersionConflictError) for item in update_results),
            1,
        )
        async with self.sessions() as db:
            offer = await db.get(OfferRecord, offer_id)
            self.assertEqual(offer.version, 2)
            self.assertIn(
                offer.base_salary_amount,
                {Decimal("20000.00"), Decimal("21000.00")},
            )
