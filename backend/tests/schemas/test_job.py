from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas import EmploymentType, JobCreate, JobRead, JobStatus, JobUpdate


class JobRequestSchemaTest(TestCase):
    def test_minimal_create_defaults_to_draft_and_empty_sections(self) -> None:
        data = JobCreate(title="  后端开发工程师  ")

        self.assertEqual(data.title, "后端开发工程师")
        self.assertIs(data.status, JobStatus.DRAFT)
        self.assertIsNone(data.job_background)
        self.assertIsNone(data.job_responsibilities)
        self.assertIsNone(data.candidate_requirements)
        self.assertIsNone(data.preferred_qualifications)
        self.assertIsNone(data.public_notes)

    def test_complete_create_normalizes_text_and_enums(self) -> None:
        data = JobCreate(
            title="后端开发工程师",
            department=" 研发部 ",
            location=" 上海 ",
            employment_type="full_time",
            headcount=2,
            job_background="  平台建设\n背景  ",
            job_responsibilities="  1. 开发\n2. 维护  ",
            candidate_requirements="  熟悉 Python  ",
            status="open",
        )

        self.assertEqual(data.department, "研发部")
        self.assertEqual(data.location, "上海")
        self.assertEqual(data.job_background, "平台建设\n背景")
        self.assertEqual(data.job_responsibilities, "1. 开发\n2. 维护")
        self.assertIs(data.employment_type, EmploymentType.FULL_TIME)
        self.assertIs(data.status, JobStatus.OPEN)

    def test_blank_title_closed_initial_status_and_bad_headcount_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobCreate(title="   ")
        with self.assertRaises(ValidationError):
            JobCreate(title="测试工程师", status="closed")
        for invalid_value in ("2", 0, 1_000):
            with self.subTest(value=invalid_value), self.assertRaises(ValidationError):
                JobCreate(title="测试工程师", headcount=invalid_value)

    def test_partial_update_and_strict_extra_fields(self) -> None:
        update = JobUpdate(department=None, job_background=" 新背景 ")
        self.assertEqual(
            update.model_dump(exclude_unset=True),
            {"department": None, "job_background": "新背景"},
        )
        invalid_payloads = (
            {},
            {"title": None},
            {"status": "closed"},
            {"description": "旧值"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                JobUpdate.model_validate(payload)

    def test_package_exports_stable_job_enums(self) -> None:
        self.assertEqual(JobStatus.CLOSED.value, "closed")
        self.assertEqual(EmploymentType.INTERNSHIP.value, "internship")


class JobReadTest(TestCase):
    def test_read_uses_five_section_contract(self) -> None:
        read = JobRead(
            id=1,
            title="后端开发工程师",
            department="研发部",
            location="上海",
            employment_type="full_time",
            headcount=2,
            job_background="岗位背景",
            job_responsibilities="岗位职责",
            candidate_requirements="任职要求",
            preferred_qualifications=None,
            public_notes=None,
            status="open",
            created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )

        self.assertEqual(read.job_responsibilities, "岗位职责")
        self.assertNotIn("description", JobRead.model_fields)
        self.assertNotIn("requirements", JobRead.model_fields)
