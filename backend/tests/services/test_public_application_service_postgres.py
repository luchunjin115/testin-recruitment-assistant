from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import FastAPI, UploadFile
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.database import get_db
from app.api.public import (
    get_public_rate_limit_redis,
    install_public_exception_handlers,
    router as public_router,
)
from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.public_application import PublicApplicationForm
from app.services.public_application_service import (
    PublicApplicationIdempotencyConflictError,
    PublicApplicationJobNotOpenError,
    PublicApplicationReviewRequiredError,
    PublicApplicationSaveError,
    PublicApplicationService,
)
from app.services.resume_storage import ResumeFileStorage, ResumeStorageError


COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    StageHistory,
    PublicApplicationSubmission,
    ApplicationProcessingRun,
)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class PublicApplicationServicePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
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
        self.service = PublicApplicationService()

        self.job = Job(
            title="阶段 8B 虚构岗位",
            department="演示部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="用于自动化验收。",
            job_responsibilities="验证公开投递事务。",
            candidate_requirements="使用虚构资料。",
            preferred_qualifications="无。",
            public_notes="测试完成后回滚。",
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
        key: str = "11111111-1111-4111-8111-111111111111",
        name: str = "虚构候选人甲",
        phone: str = "13800009001",
        email: str = "stage8b-a@example.com",
    ) -> PublicApplicationForm:
        return PublicApplicationForm(
            name=name,
            phone=phone,
            email=email,
            job_id=self.job.id,
            privacy_consent=True,
            consent_version="2026-09-02",
            idempotency_key=UUID(key),
        )

    async def prepare(self, content: bytes = b"fictional resume"):
        return await self.storage.prepare(
            UploadFile(filename="resume.txt", file=BytesIO(content)),
            self.root,
            1024,
        )

    async def accept(self, data: PublicApplicationForm, content: bytes = b"fictional resume"):
        return await self.service.accept(
            self.db,
            data,
            await self.prepare(content),
            storage=self.storage,
        )

    def files(self) -> list[Path]:
        return [path for path in self.root.rglob("*") if path.is_file()]

    async def test_new_submission_creates_complete_graph_and_idempotent_retry_reuses_it(self) -> None:
        data = self.form()
        first = await self.accept(data)

        candidate = await self.db.scalar(
            select(Candidate).where(Candidate.email == data.email)
        )
        application = await self.db.scalar(
            select(Application).where(Application.candidate_id == candidate.id)
        )
        submission = await self.db.scalar(
            select(PublicApplicationSubmission).where(
                PublicApplicationSubmission.application_id == application.id
            )
        )
        run = await self.db.scalar(
            select(ApplicationProcessingRun).where(
                ApplicationProcessingRun.submission_id == submission.id
            )
        )
        history = await self.db.scalar(
            select(StageHistory).where(StageHistory.application_id == application.id)
        )
        resume = await self.db.get(Resume, submission.resume_id)

        self.assertEqual(candidate.source, "public_apply")
        self.assertEqual(application.source, "public_apply")
        self.assertEqual(application.current_resume_id, resume.id)
        self.assertEqual(submission.identity_review_status, "clear")
        self.assertEqual(run.status, "queued")
        self.assertEqual(run.current_step, "extract_text")
        self.assertEqual(history.reason_code, "public_application_received")
        self.assertEqual(history.actor_type, "system")
        self.assertEqual(history.actor_label, "候选人公开投递（系统受理）")
        self.assertTrue((self.root / resume.file_path).is_file())

        before_retry = await counts(self.db)
        retry = await self.accept(data)
        self.assertTrue(retry.reused)
        self.assertEqual(retry.submission_reference, first.submission_reference)
        self.assertEqual(await counts(self.db), before_retry)
        self.assertEqual(len(self.files()), 1)

    async def test_same_idempotency_key_with_different_file_is_rejected_and_cleaned(self) -> None:
        data = self.form()
        await self.accept(data, b"first fictional resume")

        with self.assertRaises(PublicApplicationIdempotencyConflictError):
            await self.accept(data, b"different fictional resume")

        self.assertEqual(len(self.files()), 1)

    async def test_same_public_candidate_and_job_with_new_key_returns_original_receipt(self) -> None:
        original_data = self.form()
        original = await self.accept(original_data)
        before_retry = await counts(self.db)

        retry = await self.accept(
            self.form(key="12121212-1212-4212-8212-121212121212")
        )

        self.assertTrue(retry.reused)
        self.assertEqual(retry.submission_reference, original.submission_reference)
        self.assertEqual(await counts(self.db), before_retry)
        self.assertEqual(len(self.files()), 1)

    async def test_internal_active_application_keeps_current_resume_and_adds_no_fake_history(self) -> None:
        candidate = Candidate(
            name="虚构候选人乙",
            phone="13800009002",
            email="stage8b-b@example.com",
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
            parse_status="parsed",
        )
        self.db.add(old_resume)
        await self.db.flush()
        internal_application = Application(
            candidate_id=candidate.id,
            job_id=self.job.id,
            current_resume_id=old_resume.id,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="applied",
            hr_decision="pending",
        )
        self.db.add(internal_application)
        await self.db.commit()

        await self.accept(
            self.form(
                key="22222222-2222-4222-8222-222222222222",
                name=candidate.name,
                phone=candidate.phone,
                email=candidate.email,
            )
        )

        await self.db.refresh(internal_application)
        submission = await self.db.scalar(
            select(PublicApplicationSubmission).where(
                PublicApplicationSubmission.application_id == internal_application.id
            )
        )
        history_count = await self.db.scalar(
            select(func.count())
            .select_from(StageHistory)
            .where(StageHistory.application_id == internal_application.id)
        )
        self.assertEqual(internal_application.current_resume_id, old_resume.id)
        self.assertNotEqual(submission.resume_id, old_resume.id)
        self.assertEqual(history_count, 0)

    async def test_partial_contact_match_creates_new_candidate_marked_for_review(self) -> None:
        self.db.add(
            Candidate(
                name="已有虚构候选人",
                phone="13800009003",
                email="other@example.com",
                source="hr_screening",
                status="new",
            )
        )
        await self.db.commit()

        await self.accept(
            self.form(
                key="33333333-3333-4333-8333-333333333333",
                name="新虚构候选人",
                phone="13800009003",
                email="new-contact@example.com",
            )
        )

        matching = list(
            (
                await self.db.scalars(
                    select(Candidate).where(Candidate.phone == "13800009003")
                )
            ).all()
        )
        submission = await self.db.scalar(
            select(PublicApplicationSubmission).order_by(
                PublicApplicationSubmission.id.desc()
            )
        )
        self.assertEqual(len(matching), 2)
        self.assertEqual(submission.identity_review_status, "needs_review")
        self.assertEqual(submission.identity_review_reasons, ["contact_conflict"])
        original_reference = submission.submission_reference

        retry = await self.accept(
            self.form(
                key="34343434-3434-4434-8434-343434343434",
                name="新虚构候选人",
                phone="13800009003",
                email="new-contact@example.com",
            )
        )
        self.assertTrue(retry.reused)
        self.assertEqual(retry.submission_reference, original_reference)
        matching_after_retry = list(
            (
                await self.db.scalars(
                    select(Candidate).where(Candidate.phone == "13800009003")
                )
            ).all()
        )
        self.assertEqual(len(matching_after_retry), 2)

    async def test_same_name_only_creates_new_candidate_with_low_risk_review(self) -> None:
        self.db.add(
            Candidate(
                name="同名虚构候选人",
                phone="13800009008",
                email="existing-name@example.com",
                source="hr_screening",
                status="new",
            )
        )
        await self.db.commit()

        await self.accept(
            self.form(
                key="88888888-8888-4888-8888-888888888888",
                name="同名虚构候选人",
                phone="13800009009",
                email="new-name@example.com",
            )
        )

        submission = await self.db.scalar(
            select(PublicApplicationSubmission).order_by(
                PublicApplicationSubmission.id.desc()
            )
        )
        self.assertEqual(submission.identity_review_status, "needs_review")
        self.assertEqual(submission.identity_review_reasons, ["same_name"])

    async def test_closed_job_is_rejected_before_candidate_creation_and_file_is_cleaned(self) -> None:
        self.job.status = "closed"
        await self.db.commit()
        candidates_before = await self.db.scalar(
            select(func.count()).select_from(Candidate)
        )

        with self.assertRaises(PublicApplicationJobNotOpenError):
            await self.accept(
                self.form(key="99999999-9999-4999-8999-999999999999")
            )

        self.assertEqual(self.files(), [])
        self.assertEqual(
            await self.db.scalar(select(func.count()).select_from(Candidate)),
            candidates_before,
        )

    async def test_historical_application_blocks_reapplication_and_removes_temp_file(self) -> None:
        candidate = Candidate(
            name="虚构候选人丙",
            phone="13800009004",
            email="stage8b-c@example.com",
            source="hr_screening",
            status="new",
        )
        self.db.add(candidate)
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=self.job.id,
            filename="history.txt",
            file_path="v2/resumes/history.txt",
            file_type="text/plain",
            file_size=3,
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
        self.db.add(
            Application(
                candidate_id=candidate.id,
                job_id=self.job.id,
                current_resume_id=resume.id,
                source="hr_screening",
                lifecycle_status="ended",
                recruitment_stage="rejected",
                hr_decision="rejected",
                final_outcome="screening_rejected",
            )
        )
        await self.db.commit()

        with self.assertRaises(PublicApplicationReviewRequiredError):
            await self.accept(
                self.form(
                    key="44444444-4444-4444-8444-444444444444",
                    name=candidate.name,
                    phone=candidate.phone,
                    email=candidate.email,
                )
            )

        self.assertEqual(self.files(), [])
        submission_count = await self.db.scalar(
            select(func.count()).select_from(PublicApplicationSubmission)
        )
        self.assertEqual(submission_count, 0)

    async def test_file_promotion_failure_rolls_back_database_and_cleans_staging(self) -> None:
        with patch.object(
            self.storage,
            "promote",
            side_effect=ResumeStorageError("private path must not leak"),
        ):
            with self.assertRaises(PublicApplicationSaveError):
                await self.accept(
                    self.form(key="55555555-5555-4555-8555-555555555555")
                )

        self.assertEqual(self.files(), [])
        self.assertEqual(
            await self.db.scalar(
                select(func.count()).select_from(PublicApplicationSubmission)
            ),
            0,
        )

    async def test_database_commit_failure_removes_promoted_file(self) -> None:
        with patch.object(
            self.db,
            "commit",
            AsyncMock(side_effect=RuntimeError("database commit failed")),
        ):
            with self.assertRaises(PublicApplicationSaveError):
                await self.accept(
                    self.form(key="66666666-6666-4666-8666-666666666666")
                )

        self.assertEqual(self.files(), [])
        self.assertEqual(
            await self.db.scalar(
                select(func.count()).select_from(PublicApplicationSubmission)
            ),
            0,
        )

    async def test_real_multipart_api_postgres_and_storage_chain_returns_only_public_receipt(self) -> None:
        draft_job = Job(title="不应公开的草稿岗位", status="draft")
        self.db.add(draft_job)
        await self.db.commit()
        app = FastAPI()
        install_public_exception_handlers(app)
        app.include_router(public_router, prefix="/api/v2")

        async def override_get_db():
            yield self.db

        async def override_redis():
            yield Mock(name="redis")

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_public_rate_limit_redis] = override_redis
        api_settings = Settings(_env_file=None, STORAGE_DIR=str(self.root))

        with (
            patch("app.api.public.get_settings", return_value=api_settings),
            patch(
                "app.api.public.public_application_rate_limiter.check",
                AsyncMock(),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://stage8b.test",
            ) as client:
                jobs_response = await client.get("/api/v2/public/jobs")
                response = await client.post(
                    "/api/v2/public/applications",
                    data={
                        "name": "虚构 API 候选人",
                        "phone": "13800009007",
                        "email": "stage8b-api@example.com",
                        "job_id": str(self.job.id),
                        "privacy_consent": "true",
                        "consent_version": api_settings.PUBLIC_APPLICATION_CONSENT_VERSION,
                        "idempotency_key": "77777777-7777-4777-8777-777777777777",
                    },
                    files={"resume": ("resume.txt", b"fictional api resume", "text/plain")},
                )

        self.assertEqual(jobs_response.status_code, 200, jobs_response.text)
        self.assertIn(self.job.id, [item["id"] for item in jobs_response.json()])
        self.assertNotIn(draft_job.id, [item["id"] for item in jobs_response.json()])
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(set(response.json()), {"submission_reference", "accepted_at", "message"})
        self.assertNotIn("candidate_id", response.text)
        self.assertEqual(len(self.files()), 1)
