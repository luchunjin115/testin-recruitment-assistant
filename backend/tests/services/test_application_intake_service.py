from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.application import ApplicationIntakeRequest, CandidateResolution
from app.services.application_intake_service import (
    ApplicationContactIdentityConflictError,
    ApplicationIntakeService,
    ApplicationJobNotOpenError,
    ApplicationResumeOwnershipConflictError,
)


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_job(job_id: int = 1, status: str = "open") -> Job:
    return Job(
        id=job_id,
        title="后端开发工程师",
        department="研发部",
        location="上海",
        employment_type="full_time",
        headcount=1,
        description="负责后端开发",
        requirements={},
        status=status,
    )


def make_resume(
    resume_id: int = 2,
    *,
    candidate_id: int | None = None,
) -> Resume:
    return Resume(
        id=resume_id,
        candidate_id=candidate_id,
        job_id=None,
        filename="candidate.pdf",
        file_path="2026/candidate.pdf",
        file_type="application/pdf",
        file_size=128,
        raw_text="Python developer",
        parsed_snapshot={"skills": ["Python"]},
        parse_status="parsed",
        structure_status="succeeded",
    )


def make_candidate(
    candidate_id: int = 3,
    *,
    phone: str = "13800138000",
    email: str = "candidate@example.com",
) -> Candidate:
    return Candidate(
        id=candidate_id,
        name="张三",
        phone=phone,
        email=email,
        status="new",
    )


def make_application(application_id: int = 4) -> Application:
    return Application(
        id=application_id,
        candidate_id=3,
        job_id=1,
        current_resume_id=2,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage="applied",
        ai_status="not_started",
        hr_decision="pending",
        current_screening_result_id=None,
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def make_request(**overrides) -> ApplicationIntakeRequest:
    payload = {
        "name": "张三",
        "phone": "13800138000",
        "email": "candidate@example.com",
        "job_id": 1,
        "current_resume_id": 2,
        "source": "hr_screening",
    }
    payload.update(overrides)
    return ApplicationIntakeRequest.model_validate(payload)


def scalar_rows(items: list) -> Mock:
    result = Mock()
    result.unique.return_value.all.return_value = items
    result.all.return_value = items
    return result


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class ApplicationIntakeServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ApplicationIntakeService()
        self.db = make_session()

    async def test_new_screening_candidate_resume_application_and_history_commit_once(self) -> None:
        job = make_job()
        resume = make_resume()
        self.db.scalar.side_effect = [job, resume, None]
        self.db.scalars.side_effect = [scalar_rows([]), scalar_rows([9])]

        next_ids = {Candidate: 3, Application: 4}

        async def assign_ids() -> None:
            for call in self.db.add.call_args_list:
                item = call.args[0]
                if type(item) in next_ids and item.id is None:
                    item.id = next_ids[type(item)]
            for call in self.db.add.call_args_list:
                item = call.args[0]
                if isinstance(item, Application):
                    item.applied_at = TEST_TIME
                    item.created_at = TEST_TIME
                    item.updated_at = TEST_TIME

        self.db.flush.side_effect = assign_ids

        result = await self.service.intake(self.db, make_request())

        self.assertIs(result.candidate_resolution, CandidateResolution.CREATED)
        self.assertFalse(result.existing_application_reused)
        self.assertEqual(result.suspected_duplicate_candidate_ids, (9,))
        self.assertEqual(result.application.recruitment_stage, "applied")
        self.assertEqual(result.application.hr_decision, "pending")
        self.assertEqual(resume.candidate_id, 3)
        added = [call.args[0] for call in self.db.add.call_args_list]
        candidate = next(item for item in added if isinstance(item, Candidate))
        history = next(item for item in added if isinstance(item, StageHistory))
        self.assertIsNone(candidate.resume_text)
        self.assertIsNone(candidate.parsed_data)
        self.assertIsNone(candidate.applied_job_id)
        self.assertEqual(history.reason_code, "application_created")
        self.db.commit.assert_awaited_once()
        self.db.rollback.assert_not_awaited()

    async def test_hr_direct_uses_passed_state_and_direct_entry_history(self) -> None:
        job = make_job()
        candidate = make_candidate()
        resume = make_resume(candidate_id=candidate.id)
        self.db.scalar.side_effect = [job, resume, None]
        self.db.scalars.return_value = scalar_rows([candidate])

        async def assign_application_id() -> None:
            for call in self.db.add.call_args_list:
                item = call.args[0]
                if isinstance(item, Application) and item.id is None:
                    item.id = 4
                    item.applied_at = TEST_TIME
                    item.created_at = TEST_TIME
                    item.updated_at = TEST_TIME

        self.db.flush.side_effect = assign_application_id
        request = make_request(source="hr_direct", confirm_hr_pass=True)

        result = await self.service.intake(self.db, request)

        self.assertEqual(result.application.recruitment_stage, "screening_passed")
        self.assertEqual(result.application.hr_decision, "passed")
        added = [call.args[0] for call in self.db.add.call_args_list]
        history = next(item for item in added if isinstance(item, StageHistory))
        self.assertEqual(history.reason_code, "hr_direct_entry")

    async def test_new_resume_profile_is_saved_without_creating_global_career_profile(self) -> None:
        job = make_job()
        resume = make_resume()
        self.db.scalar.side_effect = [job, resume, None]
        self.db.scalars.side_effect = [scalar_rows([]), scalar_rows([])]

        next_ids = {Candidate: 3, Application: 4}

        async def assign_ids() -> None:
            for call in self.db.add.call_args_list:
                item = call.args[0]
                if type(item) in next_ids and item.id is None:
                    item.id = next_ids[type(item)]
                if isinstance(item, Application):
                    item.applied_at = TEST_TIME
                    item.created_at = TEST_TIME
                    item.updated_at = TEST_TIME

        self.db.flush.side_effect = assign_ids
        request = make_request(
            source="hr_direct",
            confirm_hr_pass=True,
            resume_profile={
                "current_company": "示例科技",
                "current_title": "后端工程师",
                "skills": ["Python", "FastAPI"],
                "education_records": [{"school": "示例大学", "degree": "本科"}],
                "work_experiences": [{"company": "示例科技", "title": "后端工程师"}],
                "project_experiences": [{"project_name": "招聘助手", "role": "开发"}],
            },
        )

        result = await self.service.intake(self.db, request)

        added = [call.args[0] for call in self.db.add.call_args_list]
        candidate = next(item for item in added if isinstance(item, Candidate))
        self.assertIsNone(candidate.current_company)
        self.assertIsNone(candidate.tags)
        self.assertEqual(candidate.education_records, [])
        self.assertEqual(candidate.work_experiences, [])
        self.assertEqual(candidate.project_experiences, [])
        confirmed = resume.parsed_snapshot["confirmed_profile"]
        self.assertEqual(confirmed["current_company"], "示例科技")
        self.assertEqual(confirmed["skills"], ["Python", "FastAPI"])
        self.assertEqual(confirmed["education_records"][0]["school"], "示例大学")
        self.assertEqual(result.application.hr_decision, "passed")
        self.db.commit.assert_awaited_once()

    async def test_reused_candidate_keeps_global_profile_and_new_resume_gets_its_own_profile(self) -> None:
        candidate = make_candidate()
        candidate.current_company = "历史公司"
        resume = make_resume(candidate_id=candidate.id)
        self.db.scalar.side_effect = [make_job(), resume, None]
        self.db.scalars.return_value = scalar_rows([candidate])

        await self.service.intake(
            self.db,
            make_request(resume_profile={"current_company": "简历中的新公司"}),
        )

        self.assertEqual(candidate.current_company, "历史公司")
        self.assertEqual(
            resume.parsed_snapshot["confirmed_profile"]["current_company"],
            "简历中的新公司",
        )

    async def test_matching_phone_and_email_reuse_candidate_and_existing_application(self) -> None:
        job = make_job()
        candidate = make_candidate()
        resume = make_resume(candidate_id=candidate.id)
        existing = make_application()
        self.db.scalar.side_effect = [job, resume, existing]
        self.db.scalars.return_value = scalar_rows([candidate])

        original_snapshot = dict(resume.parsed_snapshot)
        result = await self.service.intake(
            self.db,
            make_request(resume_profile={"current_company": "不应写入"}),
        )

        self.assertIs(result.application, existing)
        self.assertIs(result.candidate_resolution, CandidateResolution.REUSED)
        self.assertTrue(result.existing_application_reused)
        self.assertEqual(resume.parsed_snapshot, original_snapshot)
        self.db.add.assert_not_called()
        self.db.commit.assert_awaited_once()

    async def test_hr_direct_reused_pending_application_becomes_passed_with_history(self) -> None:
        candidate = make_candidate()
        resume = make_resume(candidate_id=candidate.id)
        existing = make_application()
        self.db.scalar.side_effect = [make_job(), resume, existing]
        self.db.scalars.return_value = scalar_rows([candidate])

        result = await self.service.intake(
            self.db,
            make_request(source="hr_direct", confirm_hr_pass=True),
        )

        self.assertTrue(result.existing_application_reused)
        self.assertEqual(existing.recruitment_stage, "screening_passed")
        self.assertEqual(existing.hr_decision, "passed")
        history = self.db.add.call_args.args[0]
        self.assertIsInstance(history, StageHistory)
        self.assertEqual(history.from_hr_decision, "pending")
        self.assertEqual(history.reason_code, "hr_direct_entry")
        self.db.commit.assert_awaited_once()

    async def test_one_sided_or_split_contact_match_is_a_conflict(self) -> None:
        cases = (
            [make_candidate(email="other@example.com")],
            [
                make_candidate(3, email="other@example.com"),
                make_candidate(4, phone="13900139000"),
            ],
        )
        for candidates in cases:
            with self.subTest(candidate_ids=[item.id for item in candidates]):
                db = make_session()
                db.scalar.side_effect = [make_job(), make_resume()]
                db.scalars.return_value = scalar_rows(candidates)

                with self.assertRaises(ApplicationContactIdentityConflictError):
                    await self.service.intake(db, make_request())

                db.rollback.assert_awaited_once()
                db.commit.assert_not_awaited()

    async def test_resume_bound_to_another_candidate_rolls_back(self) -> None:
        candidate = make_candidate()
        self.db.scalar.side_effect = [make_job(), make_resume(candidate_id=99)]
        self.db.scalars.return_value = scalar_rows([candidate])

        with self.assertRaises(ApplicationResumeOwnershipConflictError):
            await self.service.intake(self.db, make_request())

        self.db.rollback.assert_awaited_once()
        self.db.commit.assert_not_awaited()

    async def test_closed_or_missing_job_rolls_back_before_candidate_changes(self) -> None:
        self.db.scalar.return_value = None

        with self.assertRaises(ApplicationJobNotOpenError):
            await self.service.intake(self.db, make_request())

        self.db.add.assert_not_called()
        self.db.rollback.assert_awaited_once()

    async def test_unexpected_write_failure_rolls_back_entire_intake(self) -> None:
        self.db.scalar.side_effect = [make_job(), make_resume()]
        self.db.scalars.side_effect = [scalar_rows([]), scalar_rows([])]
        self.db.flush.side_effect = RuntimeError("database write failed")

        with self.assertRaises(RuntimeError):
            await self.service.intake(self.db, make_request())

        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_contact_advisory_locks_are_acquired_in_stable_order(self) -> None:
        self.db.scalar.return_value = None

        with self.assertRaises(ApplicationJobNotOpenError):
            await self.service.intake(self.db, make_request())

        self.assertEqual(self.db.execute.await_count, 2)
        compiled = [str(call.args[0]) for call in self.db.execute.await_args_list]
        self.assertTrue(all("pg_advisory_xact_lock" in value for value in compiled))
