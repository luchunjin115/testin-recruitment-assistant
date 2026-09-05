from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.offer_record import OfferRecord
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.offer import (
    CandidateWithdrawRequest,
    ConfirmAdmissionRequest,
    ConfirmHireRequest,
    OfferAcceptRequest,
    OfferDeclineRequest,
    OfferDraftCreateRequest,
    OfferExpireRequest,
    OfferSendRequest,
    OfferUpdateRequest,
    Stage9ReopenRequest,
)
from app.services.offer_service import (
    OfferActiveConflictError,
    OfferService,
    OfferTransitionInvalidError,
    OfferVersionConflictError,
)
from app.services.interview_service import (
    HRActionConfirmationRequiredError,
    HRActionReasonRequiredError,
)
from app.services.recruitment_timeline_service import RecruitmentTimelineService


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


class OfferServicePostgresTest(IsolatedAsyncioTestCase):
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
        self.service = OfferService()
        self.timeline_service = RecruitmentTimelineService()

        job = Job(
            title="阶段 9D 虚构岗位",
            department="自动化测试部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="仅用于 9D 事务测试。",
            job_responsibilities="验证 Offer 流程。",
            candidate_requirements="使用虚构资料。",
            preferred_qualifications="无。",
            public_notes="测试后回滚。",
            status="open",
        )
        candidate = Candidate(
            name="阶段 9D 虚构候选人",
            phone="13800009992",
            email="stage9d-test@example.test",
            source="hr_screening",
            status="new",
        )
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="stage9d-fictional.txt",
            file_path="tests/stage9d-fictional.txt",
            file_type="text/plain",
            file_size=10,
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
        self.application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            current_resume_id=resume.id,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="offer",
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

    def offer_details(self, *, amount: str = "18888.80") -> dict:
        valid_until = date.today() + timedelta(days=30)
        return {
            "position_title": "阶段 9D 虚构工程师",
            "currency": "CNY",
            "salary_period": "monthly",
            "base_salary_amount": amount,
            "salary_months": "13.0",
            "bonus_note": "虚构奖金说明",
            "benefits_note": "虚构福利说明",
            "valid_until": valid_until,
            "expected_start_date": valid_until + timedelta(days=15),
            "note": "仅用于测试",
        }

    def action(self, schema, expected_version: int, reason_code: str, detail: str):
        return schema(
            expected_version=expected_version,
            reason_code=reason_code,
            reason_detail=detail,
            confirmed=True,
        )

    async def test_full_offer_accept_admit_hire_and_reopen_chain(self) -> None:
        create_request = OfferDraftCreateRequest(**self.offer_details())
        offer = await self.service.create_offer(
            self.db, self.application_id, create_request
        )
        self.assertEqual(offer.version_number, 1)
        self.assertEqual(offer.base_salary_amount, Decimal("18888.80"))

        before_duplicate = await counts(self.db)
        duplicate = await self.service.create_offer(
            self.db, self.application_id, create_request
        )
        self.assertEqual(duplicate.id, offer.id)
        self.assertEqual(await counts(self.db), before_duplicate)

        offer = await self.service.update_offer(
            self.db,
            offer.id,
            OfferUpdateRequest(
                **self.offer_details(amount="19999.90"), expected_version=1
            ),
        )
        self.assertEqual(offer.version, 2)
        self.assertEqual(offer.base_salary_amount, Decimal("19999.90"))
        before_duplicate = await counts(self.db)
        duplicate = await self.service.update_offer(
            self.db,
            offer.id,
            OfferUpdateRequest(
                **self.offer_details(amount="19999.90"), expected_version=1
            ),
        )
        self.assertEqual(duplicate.version, 2)
        self.assertEqual(await counts(self.db), before_duplicate)

        offer = await self.service.send_offer(
            self.db,
            offer.id,
            self.action(OfferSendRequest, 2, "offer_sent", "已线下发送"),
        )
        self.assertEqual(offer.status, "sent")
        before_duplicate = await counts(self.db)
        duplicate = await self.service.send_offer(
            self.db,
            offer.id,
            self.action(OfferSendRequest, 2, "offer_sent", "已线下发送"),
        )
        self.assertEqual(duplicate.version, offer.version)
        self.assertEqual(await counts(self.db), before_duplicate)

        offer = await self.service.accept_offer(
            self.db,
            offer.id,
            self.action(
                OfferAcceptRequest, 3, "offer_accepted", "候选人明确接受"
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(offer.status, "accepted")
        self.assertEqual(self.application.recruitment_stage, "offer_accepted")
        self.assertEqual(self.application.hr_decision, "passed")

        await self.service.confirm_admission(
            self.db,
            self.application_id,
            self.action(
                ConfirmAdmissionRequest,
                4,
                "application_admitted",
                "HR 已确认录取，等待入职",
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "admitted")
        self.assertEqual(self.application.lifecycle_status, "active")

        await self.service.confirm_hire(
            self.db,
            self.application_id,
            self.action(
                ConfirmHireRequest,
                4,
                "application_hired",
                "HR 已核实正式到岗",
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "hired")
        self.assertEqual(self.application.lifecycle_status, "ended")
        self.assertEqual(self.application.final_outcome, "hired")
        self.assertEqual(self.application.hr_decision, "passed")

        await self.service.reopen_stage9(
            self.db,
            self.application_id,
            self.action(
                Stage9ReopenRequest,
                4,
                "stage9_reopened",
                "更正误标正式入职",
            ),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "admitted")
        self.assertIsNone(self.application.final_outcome)

        await self.service.reopen_stage9(
            self.db,
            self.application_id,
            self.action(
                Stage9ReopenRequest,
                4,
                "stage9_reopened",
                "更正误标已录取",
            ),
        )
        await self.service.reopen_stage9(
            self.db,
            self.application_id,
            self.action(
                Stage9ReopenRequest,
                4,
                "stage9_reopened",
                "更正误标接受 Offer",
            ),
        )
        await self.db.refresh(self.application)
        await self.db.refresh(offer)
        self.assertEqual(self.application.recruitment_stage, "offer")
        self.assertEqual(offer.status, "sent")
        self.assertIsNone(offer.responded_at)
        self.assertEqual(offer.version, 5)

        offer = await self.service.decline_offer(
            self.db,
            offer.id,
            self.action(
                OfferDeclineRequest, 5, "offer_declined", "候选人明确拒绝"
            ),
        )
        self.assertEqual(offer.status, "declined")
        await self.db.refresh(self.application)
        self.assertEqual(self.application.final_outcome, "offer_declined")

        await self.service.reopen_stage9(
            self.db,
            self.application_id,
            self.action(
                Stage9ReopenRequest,
                6,
                "stage9_reopened",
                "更正候选人拒绝记录",
            ),
        )
        new_offer = await self.service.create_offer(
            self.db,
            self.application_id,
            OfferDraftCreateRequest(**self.offer_details(amount="20000.00")),
        )
        self.assertEqual(new_offer.version_number, 2)

        activities = list(
            (
                await self.db.scalars(
                    select(ActivityLog).where(
                        ActivityLog.detail["application_id"].as_integer()
                        == self.application_id
                    )
                )
            ).all()
        )
        serialized_audit = repr([item.detail for item in activities])
        self.assertNotIn("18888.80", serialized_audit)
        self.assertNotIn("19999.90", serialized_audit)
        self.assertNotIn("20000.00", serialized_audit)

        timeline = await self.timeline_service.list_timeline(
            self.db, self.application_id
        )
        serialized_timeline = repr([item.model_dump() for item in timeline])
        self.assertNotIn("salary", serialized_timeline.lower())
        self.assertNotIn("19999.90", serialized_timeline)
        self.assertIn("offer_accepted", {item.reason_code for item in timeline})
        self.assertIn("application_hired", {item.reason_code for item in timeline})
        self.assertTrue(
            all(
                item.reason_detail is None
                for item in timeline
                if item.offer_record_id is not None
            )
        )

    async def test_illegal_transitions_versions_expiry_and_active_uniqueness(self) -> None:
        offer = await self.service.create_offer(
            self.db,
            self.application_id,
            OfferDraftCreateRequest(**self.offer_details()),
        )
        offer_id = offer.id
        with self.assertRaises(OfferActiveConflictError):
            await self.service.create_offer(
                self.db,
                self.application_id,
                OfferDraftCreateRequest(**self.offer_details(amount="19999.00")),
            )
        with self.assertRaises(OfferTransitionInvalidError):
            await self.service.accept_offer(
                self.db,
                offer_id,
                self.action(
                    OfferAcceptRequest, 1, "offer_accepted", "非法跳过发送"
                ),
            )
        with self.assertRaises(OfferVersionConflictError):
            await self.service.update_offer(
                self.db,
                offer_id,
                OfferUpdateRequest(
                    **self.offer_details(amount="19999.00"), expected_version=99
                ),
            )
        offer = await self.service.send_offer(
            self.db,
            offer_id,
            self.action(OfferSendRequest, 1, "offer_sent", "已线下发送"),
        )
        with self.assertRaises(OfferVersionConflictError):
            await self.service.accept_offer(
                self.db,
                offer_id,
                self.action(
                    OfferAcceptRequest, 1, "offer_accepted", "使用过期页面版本"
                ),
            )
        with self.assertRaises(HRActionConfirmationRequiredError):
            await self.service.update_offer(
                self.db,
                offer_id,
                OfferUpdateRequest(
                    **self.offer_details(amount="19999.00"),
                    expected_version=2,
                    confirmed=False,
                    correction_reason="修正已发送记录",
                ),
            )
        with self.assertRaises(HRActionReasonRequiredError):
            await self.service.update_offer(
                self.db,
                offer_id,
                OfferUpdateRequest(
                    **self.offer_details(amount="19999.00"),
                    expected_version=2,
                    confirmed=True,
                    correction_reason=None,
                ),
            )
        with self.assertRaises(OfferTransitionInvalidError):
            await self.service.expire_offer(
                self.db,
                offer_id,
                self.action(
                    OfferExpireRequest, 2, "offer_expired", "尚未过期"
                ),
            )
        offer = await self.db.get(OfferRecord, offer_id)
        self.assertEqual(offer.status, "sent")
        self.assertEqual(offer.version, 2)
        self.assertEqual(offer.base_salary_amount, Decimal("18888.80"))

    async def test_candidate_withdraw_reopen_preserves_active_offer(self) -> None:
        offer = await self.service.create_offer(
            self.db,
            self.application_id,
            OfferDraftCreateRequest(**self.offer_details()),
        )
        await self.service.withdraw_application(
            self.db,
            self.application_id,
            self.action(
                CandidateWithdrawRequest,
                offer.version,
                "candidate_withdrew",
                "候选人主动退出",
            ),
        )
        await self.service.reopen_stage9(
            self.db,
            self.application_id,
            self.action(
                Stage9ReopenRequest,
                offer.version,
                "stage9_reopened",
                "候选人撤回退出请求",
            ),
        )
        await self.db.refresh(self.application)
        await self.db.refresh(offer)
        self.assertEqual(self.application.recruitment_stage, "offer")
        self.assertEqual(offer.status, "draft")
        with self.assertRaises(OfferActiveConflictError):
            await self.service.create_offer(
                self.db,
                self.application_id,
                OfferDraftCreateRequest(**self.offer_details(amount="19999.00")),
            )

    async def test_audit_failure_rolls_back_application_offer_and_history(self) -> None:
        baseline = await counts(self.db)
        with patch.object(
            self.service,
            "_add_offer_activity",
            AsyncMock(side_effect=RuntimeError("audit failed")),
        ):
            with self.assertRaises(RuntimeError):
                await self.service.create_offer(
                    self.db,
                    self.application_id,
                    OfferDraftCreateRequest(**self.offer_details()),
                )
        self.db.expire_all()
        await self.db.refresh(self.application)
        self.assertEqual(self.application.recruitment_stage, "offer")
        self.assertEqual(await counts(self.db), baseline)
