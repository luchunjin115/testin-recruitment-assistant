from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.database import get_db
from app.api.recruitment_statistics import router
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview_record import InterviewRecord
from app.models.job import Job
from app.models.offer_record import OfferRecord
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.services.recruitment_statistics_service import RecruitmentStatisticsService


UTC = timezone.utc
BASE = datetime(2026, 9, 1, tzinfo=UTC)
MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    StageHistory,
    InterviewRecord,
    OfferRecord,
)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in MODELS
    }


class RecruitmentStatisticsServicePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
        async with AsyncSession(self.engine) as outside:
            self.before = await counts(outside)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        self.service = RecruitmentStatisticsService()
        self.job = Job(title="9E 虚构统计岗位", status="open")
        self.other_job = Job(title="9E 虚构对照岗位", status="open")
        self.db.add_all([self.job, self.other_job])
        await self.db.flush()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            after = await counts(outside)
        await self.engine.dispose()
        self.assertEqual(after, self.before)

    async def _application(
        self,
        name: str,
        *,
        applied_at: datetime,
        stage: str = "interview",
        lifecycle: str = "active",
        final_outcome: str | None = None,
        job: Job | None = None,
    ) -> Application:
        selected_job = job or self.job
        candidate = Candidate(name=name)
        self.db.add(candidate)
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=selected_job.id,
            filename=f"{name}.txt",
            file_path=f"tests/{name}.txt",
            file_type="text/plain",
            file_size=20,
            raw_text="虚构测试简历，不应进入统计响应",
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
        application = Application(
            candidate_id=candidate.id,
            job_id=selected_job.id,
            current_resume_id=resume.id,
            source="hr_screening",
            lifecycle_status=lifecycle,
            recruitment_stage=stage,
            hr_decision="passed",
            final_outcome=final_outcome,
            applied_at=applied_at,
            created_at=applied_at,
            updated_at=applied_at,
        )
        self.db.add(application)
        await self.db.flush()
        return application

    def _history(self, application: Application, stage: str, at: datetime) -> StageHistory:
        return StageHistory(
            application_id=application.id,
            from_lifecycle_status="active",
            to_lifecycle_status="ended" if stage == "hired" else "active",
            from_recruitment_stage="hr_review",
            to_recruitment_stage=stage,
            from_hr_decision="passed",
            to_hr_decision="passed",
            from_final_outcome=None,
            to_final_outcome="hired" if stage == "hired" else None,
            reason_code=f"9e_test_{stage}",
            reason_detail="虚构统计里程碑",
            actor_type="hr",
            actor_id="9e-test",
            actor_label="9E 虚构 HR",
            created_at=at,
        )

    def _interview(
        self,
        application: Application,
        *,
        created_at: datetime,
        status: str,
        decision: str = "pending",
        round_number: int = 1,
        feedback_at: datetime | None = None,
    ) -> InterviewRecord:
        completed = status == "completed"
        return InterviewRecord(
            application_id=application.id,
            round_number=round_number,
            interview_type="video",
            status=status,
            scheduled_start_at=created_at + timedelta(hours=1),
            duration_minutes=60,
            timezone="Asia/Shanghai",
            interviewer_names=["9E 虚构面试官"],
            decision=decision,
            feedback_summary="虚构反馈" if completed else None,
            strengths=["虚构优势"] if completed else [],
            concerns=[],
            follow_up_questions=[],
            feedback_submitted_by_label="9E 虚构 HR" if completed else None,
            feedback_submitted_at=feedback_at if completed else None,
            version=1,
            created_at=created_at,
            updated_at=feedback_at or created_at,
        )

    def _offer(
        self,
        application: Application,
        *,
        status: str,
        sent_at: datetime | None,
        responded_at: datetime | None = None,
        version_number: int = 1,
    ) -> OfferRecord:
        return OfferRecord(
            application_id=application.id,
            version_number=version_number,
            status=status,
            position_title="9E 虚构工程师",
            currency="CNY",
            salary_period="monthly",
            base_salary_amount=Decimal("18888.80"),
            salary_months=Decimal("13.0"),
            bonus_note="虚构薪资仅用于证明统计不会返回它",
            valid_until=date(2026, 10, 10),
            expected_start_date=date(2026, 10, 20),
            sent_at=sent_at,
            responded_at=responded_at,
            closed_at=sent_at if status in {"withdrawn", "expired"} else None,
            version=1,
            created_at=sent_at or BASE,
            updated_at=responded_at or sent_at or BASE,
        )

    async def test_fixed_cohort_historical_funnel_durations_and_realtime_todos(self) -> None:
        hired = await self._application(
            "9E 虚构已入职候选人",
            applied_at=BASE,
            stage="hired",
            lifecycle="ended",
            final_outcome="hired",
        )
        declined = await self._application(
            "9E 虚构拒绝 Offer 候选人",
            applied_at=BASE,
            stage="offer",
            lifecycle="ended",
            final_outcome="offer_declined",
        )
        canceled_only = await self._application(
            "9E 虚构纯取消面试候选人",
            applied_at=BASE + timedelta(days=1),
        )

        self.db.add_all(
            [
                self._history(hired, "screening_passed", BASE + timedelta(hours=12)),
                self._history(hired, "offer", BASE + timedelta(days=2)),
                self._history(hired, "offer_accepted", BASE + timedelta(days=3)),
                self._history(hired, "admitted", BASE + timedelta(days=4)),
                self._history(hired, "hired", BASE + timedelta(days=6)),
                self._history(declined, "screening_passed", BASE + timedelta(days=1)),
                self._history(declined, "offer", BASE + timedelta(days=3)),
                self._interview(
                    hired,
                    created_at=BASE + timedelta(days=1, hours=12),
                    status="completed",
                    decision="proceed_offer",
                    feedback_at=BASE + timedelta(days=1, hours=18),
                ),
                self._interview(
                    declined,
                    created_at=BASE + timedelta(days=2),
                    status="completed",
                    decision="proceed_offer",
                    feedback_at=BASE + timedelta(days=2, hours=12),
                ),
                self._interview(
                    canceled_only,
                    created_at=BASE + timedelta(days=2),
                    status="canceled",
                ),
                self._offer(
                    hired,
                    status="withdrawn",
                    sent_at=BASE + timedelta(days=2, hours=12),
                    version_number=1,
                ),
                self._offer(
                    hired,
                    status="accepted",
                    sent_at=BASE + timedelta(days=2, hours=12),
                    responded_at=BASE + timedelta(days=3),
                    version_number=2,
                ),
                self._offer(
                    declined,
                    status="declined",
                    sent_at=BASE + timedelta(days=3, hours=12),
                    responded_at=BASE + timedelta(days=4, hours=12),
                ),
            ]
        )

        todo_specs = (
            ("待发生面试", "interview"),
            ("待面试决定", "interview"),
            ("待创建下一轮", "interview"),
            ("待发送 Offer", "offer"),
            ("待回应 Offer", "offer"),
            ("待确认录取", "offer_accepted"),
            ("待确认入职", "admitted"),
        )
        todo_apps = {
            name: await self._application(
                f"9E 虚构{name}",
                applied_at=datetime(2026, 10, 2, tzinfo=UTC),
                stage=stage,
            )
            for name, stage in todo_specs
        }
        self.db.add_all(
            [
                self._interview(
                    todo_apps["待发生面试"],
                    created_at=datetime(2026, 10, 2, tzinfo=UTC),
                    status="scheduled",
                ),
                self._interview(
                    todo_apps["待面试决定"],
                    created_at=datetime(2026, 10, 2, tzinfo=UTC),
                    status="completed",
                    feedback_at=datetime(2026, 10, 2, 2, tzinfo=UTC),
                ),
                self._interview(
                    todo_apps["待创建下一轮"],
                    created_at=datetime(2026, 10, 2, tzinfo=UTC),
                    status="completed",
                    decision="next_round",
                    feedback_at=datetime(2026, 10, 2, 2, tzinfo=UTC),
                ),
                self._offer(todo_apps["待发送 Offer"], status="draft", sent_at=None),
                self._offer(
                    todo_apps["待回应 Offer"],
                    status="sent",
                    sent_at=datetime(2026, 10, 2, tzinfo=UTC),
                ),
                self._offer(
                    todo_apps["待确认录取"],
                    status="accepted",
                    sent_at=datetime(2026, 10, 2, tzinfo=UTC),
                    responded_at=datetime(2026, 10, 3, tzinfo=UTC),
                ),
                self._offer(
                    todo_apps["待确认入职"],
                    status="accepted",
                    sent_at=datetime(2026, 10, 1, tzinfo=UTC),
                    responded_at=datetime(2026, 10, 2, tzinfo=UTC),
                ),
            ]
        )
        other_job_app = await self._application(
            "9E 虚构其他岗位待办",
            applied_at=datetime(2026, 10, 2, tzinfo=UTC),
            job=self.other_job,
        )
        self.db.add(
            self._interview(
                other_job_app,
                created_at=datetime(2026, 10, 2, tzinfo=UTC),
                status="scheduled",
            )
        )
        await self.db.commit()

        result = await self.service.get_statistics(
            self.db,
            job_id=self.job.id,
            applied_from=datetime(2026, 9, 1, tzinfo=UTC),
            applied_to=datetime(2026, 9, 30, 23, 59, tzinfo=UTC),
        )

        funnel = {item.key.value: item for item in result.funnel}
        self.assertEqual(
            {key: value.count for key, value in funnel.items()},
            {
                "applications": 3,
                "screening_passed": 2,
                "interview_entered": 2,
                "interview_completed": 2,
                "offer_sent": 2,
                "offer_accepted": 1,
                "admitted": 1,
                "hired": 1,
            },
        )
        self.assertIsNone(funnel["applications"].conversion_rate)
        self.assertEqual(funnel["screening_passed"].conversion_rate, 66.67)
        self.assertEqual(funnel["offer_accepted"].conversion_rate, 50.0)

        durations = {item.key.value: item for item in result.durations}
        expected = {
            "application_to_screening_passed": (18.0, 2),
            "screening_passed_to_first_interview": (24.0, 2),
            "first_interview_to_last_completed": (9.0, 2),
            "offer_entered_to_sent": (12.0, 2),
            "offer_sent_to_response": (18.0, 2),
            "offer_accepted_to_admitted": (24.0, 1),
            "admitted_to_hired": (48.0, 1),
        }
        self.assertEqual(
            {
                key: (value.average_hours, value.sample_count)
                for key, value in durations.items()
            },
            expected,
        )
        self.assertEqual(result.todos.model_dump(), {
            "scheduled_interviews": 1,
            "pending_interview_decisions": 1,
            "next_round_not_scheduled": 1,
            "draft_offers": 1,
            "sent_offers": 1,
            "accepted_offers": 1,
            "admitted_applications": 1,
            "total": 7,
        })
        serialized = repr(result.model_dump())
        self.assertNotIn("salary", serialized.lower())
        self.assertNotIn("18888.80", serialized)

        app = FastAPI()
        app.include_router(router, prefix="/api/v2")

        async def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get(
                "/api/v2/recruitment-statistics",
                params={
                    "job_id": self.job.id,
                    "applied_from": "2026-09-01T00:00:00Z",
                    "applied_to": "2026-09-30T23:59:00Z",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["funnel"][0]["count"], 3)
        self.assertEqual(response.json()["todos"]["total"], 7)
        self.assertNotIn("salary", response.text.lower())
        self.assertNotIn("18888.80", response.text)

    async def test_zero_previous_step_returns_null_rate_and_empty_duration_samples(self) -> None:
        application = await self._application(
            "9E 虚构空漏斗候选人",
            applied_at=BASE,
            stage="hr_review",
        )
        await self.db.commit()
        result = await self.service.get_statistics(
            self.db,
            job_id=application.job_id,
            applied_from=BASE,
            applied_to=BASE,
        )
        funnel = {item.key.value: item for item in result.funnel}
        self.assertEqual(funnel["applications"].count, 1)
        self.assertEqual(funnel["screening_passed"].conversion_rate, 0.0)
        self.assertIsNone(funnel["interview_entered"].conversion_rate)
        self.assertTrue(all(item.average_hours is None for item in result.durations))
        self.assertTrue(all(item.sample_count == 0 for item in result.durations))
