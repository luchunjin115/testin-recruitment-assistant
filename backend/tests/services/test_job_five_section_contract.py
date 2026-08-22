from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock

from app.schemas.job import EmploymentType, JobCreate, JobStatus, JobUpdate
from app.services.job_service import JobOpenValidationError, JobService


def complete_open_values(**overrides) -> dict:
    values = {
        "title": "AI 应用工程师",
        "department": "研发部",
        "location": "长沙",
        "employment_type": "full_time",
        "headcount": 2,
        "job_background": None,
        "job_responsibilities": "负责 AI 应用设计、开发和上线",
        "candidate_requirements": "具备后端开发经验",
        "preferred_qualifications": None,
        "public_notes": None,
    }
    values.update(overrides)
    return values


def old_requirements() -> dict:
    return {
        "schema_version": "1.0",
        "responsibilities": ["旧职责"],
        "required_skills": ["Python"],
        "preferred_skills": [],
        "minimum_work_years": 1,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": [],
        "additional_requirements": [],
    }


def make_session() -> Mock:
    db = Mock()
    db.add = Mock()
    db.scalar = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


class JobFiveSectionOpenValidationContractTest(TestCase):
    def setUp(self) -> None:
        self.service = JobService()

    def test_complete_open_job_only_requires_confirmed_base_and_two_jd_fields(self) -> None:
        self.assertEqual(self.service.validate_open_job(complete_open_values()), ())

    def test_open_validation_reports_both_required_jd_fields(self) -> None:
        missing = self.service.validate_open_job(
            complete_open_values(
                job_responsibilities="  ",
                candidate_requirements=None,
            )
        )

        self.assertEqual(
            missing,
            ("job_responsibilities", "candidate_requirements"),
        )

    def test_old_jd_fields_are_not_part_of_open_validation(self) -> None:
        values = complete_open_values()
        values.update(
            {
                "description": None,
                "requirements": None,
                "legacy_requirements": None,
            }
        )

        self.assertEqual(self.service.validate_open_job(values), ())


class JobFiveSectionAtomicUpdateContractTest(IsolatedAsyncioTestCase):
    async def test_create_open_requires_both_five_section_required_fields(self) -> None:
        service = JobService()
        db = make_session()
        data = JobCreate.model_construct(
            title="AI 应用工程师",
            department="研发部",
            location="长沙",
            employment_type=EmploymentType.FULL_TIME,
            headcount=2,
            description="旧合同描述",
            requirements=old_requirements(),
            job_responsibilities=None,
            candidate_requirements=None,
            status=JobStatus.OPEN,
        )

        with self.assertRaises(JobOpenValidationError) as raised:
            await service.create_job(db, data)

        self.assertEqual(
            raised.exception.fields,
            ("job_responsibilities", "candidate_requirements"),
        )
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_open_draft_and_reopen_closed_recheck_both_required_fields(self) -> None:
        service = JobService()
        for action, status in (("open_job", "draft"), ("reopen_job", "closed")):
            with self.subTest(action=action):
                job = SimpleNamespace(
                    id=8,
                    status=status,
                    **complete_open_values(
                        job_responsibilities=None,
                        candidate_requirements=None,
                    ),
                    description="旧合同描述",
                    requirements=old_requirements(),
                )
                db = make_session()
                db.scalar.return_value = job

                with self.assertRaises(JobOpenValidationError) as raised:
                    await getattr(service, action)(db, job.id)

                self.assertEqual(
                    raised.exception.fields,
                    ("job_responsibilities", "candidate_requirements"),
                )
                self.assertEqual(job.status, status)
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_open_job_invalid_edit_rolls_back_without_mutating_old_values(self) -> None:
        service = JobService()
        job = SimpleNamespace(
            id=7,
            status="open",
            **complete_open_values(),
            # 旧实现读取这些字段；保留它们只为让红灯准确落在五段式更新能力。
            description="旧合同描述",
            requirements=old_requirements(),
        )
        db = make_session()
        db.scalar.return_value = job
        update = JobUpdate.model_construct(
            candidate_requirements=None,
            _fields_set={"candidate_requirements"},
        )

        with self.assertRaises(JobOpenValidationError) as raised:
            await service.update_job(db, job.id, update)

        self.assertEqual(raised.exception.fields, ("candidate_requirements",))
        self.assertEqual(job.candidate_requirements, "具备后端开发经验")
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()
