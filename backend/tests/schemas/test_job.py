from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas import (
    JOB_REQUIREMENTS_SCHEMA_VERSION,
    EducationRequirement,
    EmploymentType,
    JobCreate,
    JobRead,
    JobRequirementsV1,
    JobStatus,
    JobUpdate,
    empty_job_requirements_v1,
)


def complete_requirements_payload() -> dict:
    return {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台核心服务设计与开发"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 3,
        "education_requirement": "bachelor_or_above",
        "required_experiences": ["有异步 Web 服务开发经验"],
        "preferred_experiences": ["有招聘系统经验"],
        "keywords": ["后端", "异步服务"],
        "additional_requirements": ["具备良好沟通能力"],
    }


class JobRequirementsV1Test(TestCase):
    def test_complete_requirements_validate_with_stable_enums(self) -> None:
        requirements = JobRequirementsV1.model_validate(complete_requirements_payload())

        self.assertEqual(requirements.schema_version, JOB_REQUIREMENTS_SCHEMA_VERSION)
        self.assertEqual(requirements.minimum_work_years, 3)
        self.assertIs(
            requirements.education_requirement,
            EducationRequirement.BACHELOR_OR_ABOVE,
        )

    def test_empty_factory_contains_every_versioned_field(self) -> None:
        requirements = empty_job_requirements_v1()

        self.assertEqual(
            requirements.model_dump(mode="json"),
            {
                "schema_version": "1.0",
                "responsibilities": [],
                "required_skills": [],
                "preferred_skills": [],
                "minimum_work_years": None,
                "education_requirement": None,
                "required_experiences": [],
                "preferred_experiences": [],
                "keywords": [],
                "additional_requirements": [],
            },
        )

    def test_text_lists_trim_drop_blanks_and_remove_exact_duplicates(self) -> None:
        payload = complete_requirements_payload()
        payload["required_skills"] = [" Python ", "", "Python", "python", "SQL "]

        requirements = JobRequirementsV1.model_validate(payload)

        self.assertEqual(requirements.required_skills, ["Python", "python", "SQL"])

    def test_missing_or_extra_fields_are_rejected(self) -> None:
        missing = complete_requirements_payload()
        missing.pop("keywords")
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(missing)

        extra = complete_requirements_payload()
        extra["unknown"] = True
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(extra)

    def test_wrong_schema_version_is_rejected(self) -> None:
        payload = complete_requirements_payload()
        payload["schema_version"] = "2.0"

        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(payload)

    def test_list_must_be_a_list_and_items_must_be_strings(self) -> None:
        wrong_container = complete_requirements_payload()
        wrong_container["required_skills"] = "Python,PostgreSQL"
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(wrong_container)

        wrong_item = complete_requirements_payload()
        wrong_item["required_skills"] = ["Python", 123]
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(wrong_item)

    def test_minimum_work_years_is_strict_and_bounded(self) -> None:
        for invalid_value in ("3", -1, 81):
            payload = complete_requirements_payload()
            payload["minimum_work_years"] = invalid_value
            with self.subTest(value=invalid_value), self.assertRaises(ValidationError):
                JobRequirementsV1.model_validate(payload)

    def test_list_count_and_item_length_limits_are_enforced(self) -> None:
        too_many = complete_requirements_payload()
        too_many["responsibilities"] = [f"职责 {index}" for index in range(51)]
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(too_many)

        too_long = complete_requirements_payload()
        too_long["required_skills"] = ["技" * 101]
        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(too_long)

    def test_invalid_education_requirement_is_rejected(self) -> None:
        payload = complete_requirements_payload()
        payload["education_requirement"] = "本科"

        with self.assertRaises(ValidationError):
            JobRequirementsV1.model_validate(payload)


class JobRequestSchemaTest(TestCase):
    def test_minimal_create_defaults_to_draft_with_empty_v1(self) -> None:
        data = JobCreate(title="  后端开发工程师  ")

        self.assertEqual(data.title, "后端开发工程师")
        self.assertIs(data.status, JobStatus.DRAFT)
        self.assertEqual(data.requirements, empty_job_requirements_v1())

    def test_complete_create_normalizes_optional_text_and_enums(self) -> None:
        data = JobCreate(
            title="后端开发工程师",
            department=" 研发部 ",
            location=" 上海 ",
            employment_type="full_time",
            headcount=2,
            description=" 负责核心服务 ",
            requirements=complete_requirements_payload(),
            status="open",
        )

        self.assertEqual(data.department, "研发部")
        self.assertEqual(data.location, "上海")
        self.assertEqual(data.description, "负责核心服务")
        self.assertIs(data.employment_type, EmploymentType.FULL_TIME)
        self.assertIs(data.status, JobStatus.OPEN)

    def test_optional_blank_text_becomes_none(self) -> None:
        data = JobCreate(
            title="测试工程师",
            department="   ",
            location="\n",
            description="\t",
        )

        self.assertIsNone(data.department)
        self.assertIsNone(data.location)
        self.assertIsNone(data.description)

    def test_blank_title_and_closed_initial_status_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobCreate(title="   ")
        with self.assertRaises(ValidationError):
            JobCreate(title="测试工程师", status="closed")

    def test_headcount_is_strict_and_bounded(self) -> None:
        for invalid_value in ("2", 0, 1_000):
            with self.subTest(value=invalid_value), self.assertRaises(ValidationError):
                JobCreate(title="测试工程师", headcount=invalid_value)

    def test_unknown_create_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobCreate.model_validate({"title": "测试工程师", "salary": 20_000})

    def test_partial_update_allows_nullable_business_fields(self) -> None:
        update = JobUpdate(department=None, headcount=None, description=" 新描述 ")

        self.assertIsNone(update.department)
        self.assertIsNone(update.headcount)
        self.assertEqual(update.description, "新描述")
        self.assertEqual(
            update.model_dump(exclude_unset=True),
            {"department": None, "headcount": None, "description": "新描述"},
        )

    def test_empty_update_title_null_requirements_null_and_status_are_rejected(self) -> None:
        invalid_payloads = ({}, {"title": None}, {"requirements": None}, {"status": "closed"})

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                JobUpdate.model_validate(payload)

    def test_requirements_update_requires_complete_v1(self) -> None:
        with self.assertRaises(ValidationError):
            JobUpdate(requirements={"required_skills": ["Python"]})

        update = JobUpdate(requirements=complete_requirements_payload())
        self.assertEqual(update.requirements.required_skills, ["Python", "PostgreSQL"])

    def test_json_schema_is_strict_and_lists_all_requirement_keys(self) -> None:
        schema = JobRequirementsV1.model_json_schema()

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "responsibilities",
                "required_skills",
                "preferred_skills",
                "minimum_work_years",
                "education_requirement",
                "required_experiences",
                "preferred_experiences",
                "keywords",
                "additional_requirements",
            },
        )

    def test_schema_package_exports_stage6_job_contract(self) -> None:
        self.assertEqual(JOB_REQUIREMENTS_SCHEMA_VERSION, "1.0")
        self.assertEqual(JobStatus.CLOSED.value, "closed")
        self.assertEqual(EmploymentType.INTERNSHIP.value, "internship")


class JobReadTest(TestCase):
    def test_read_accepts_v1_requirements(self) -> None:
        read = JobRead(
            id=1,
            title="后端开发工程师",
            department="研发部",
            location="上海",
            employment_type="full_time",
            headcount=2,
            description="岗位描述",
            requirements=complete_requirements_payload(),
            status="open",
            created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )

        self.assertIsInstance(read.requirements, JobRequirementsV1)

    def test_read_rejects_legacy_requirements_and_status_after_migration(self) -> None:
        legacy = {"summary": "旧要求", "required_skills": ["Python"]}
        with self.assertRaises(ValidationError):
            JobRead(
                id=2,
                title="旧岗位",
                department=None,
                description="旧描述",
                requirements=legacy,
                status="active",
                created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )
