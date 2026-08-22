from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.job import JobCreate, JobRead, JobStatus, JobUpdate


FIVE_SECTION_FIELDS = (
    "job_background",
    "job_responsibilities",
    "candidate_requirements",
    "preferred_qualifications",
    "public_notes",
)
FIELD_LIMITS = {
    "job_background": 5_000,
    "job_responsibilities": 10_000,
    "candidate_requirements": 10_000,
    "preferred_qualifications": 5_000,
    "public_notes": 5_000,
}


def validate_or_fail(test: TestCase, schema, payload: dict):
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        test.fail(f"五段式合法输入不应被拒绝：{exc}")


class JobFiveSectionSchemaContractTest(TestCase):
    def test_draft_requires_only_title_and_defaults_all_sections_to_null(self) -> None:
        draft = validate_or_fail(self, JobCreate, {"title": "  AI 应用工程师  "})
        payload = draft.model_dump(mode="json")

        self.assertEqual(draft.title, "AI 应用工程师")
        self.assertIs(draft.status, JobStatus.DRAFT)
        self.assertTrue(set(FIVE_SECTION_FIELDS).issubset(payload))
        self.assertEqual(
            {field: payload[field] for field in FIVE_SECTION_FIELDS},
            {field: None for field in FIVE_SECTION_FIELDS},
        )

    def test_five_sections_trim_outer_whitespace_and_preserve_internal_format(self) -> None:
        formatted = "  1. 负责 API 设计\n\n- 保留项目符号\n  "
        payload = {
            "title": "后端工程师",
            **{field: formatted for field in FIVE_SECTION_FIELDS},
        }

        created = validate_or_fail(self, JobCreate, payload)

        for field in FIVE_SECTION_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(
                    getattr(created, field),
                    "1. 负责 API 设计\n\n- 保留项目符号",
                )

    def test_null_and_whitespace_only_sections_normalize_to_null(self) -> None:
        payload = {
            "title": "测试工程师",
            "job_background": None,
            "job_responsibilities": "  \n\t ",
            "candidate_requirements": "\n",
            "preferred_qualifications": "   ",
            "public_notes": None,
        }

        created = validate_or_fail(self, JobCreate, payload)

        for field in FIVE_SECTION_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(created, field))

    def test_each_section_accepts_its_maximum_and_rejects_one_character_more(self) -> None:
        for field, limit in FIELD_LIMITS.items():
            with self.subTest(field=field, boundary="maximum"):
                created = validate_or_fail(
                    self,
                    JobCreate,
                    {"title": "边界岗位", field: "字" * limit},
                )
                self.assertEqual(len(getattr(created, field)), limit)

            with self.subTest(field=field, boundary="too_long"):
                with self.assertRaises(ValidationError):
                    JobCreate.model_validate(
                        {"title": "边界岗位", field: "字" * (limit + 1)}
                    )

    def test_update_accepts_partial_null_and_formatted_section_values(self) -> None:
        update = validate_or_fail(
            self,
            JobUpdate,
            {
                "job_background": None,
                "job_responsibilities": "  1. 编写服务\n- 维护测试  ",
            },
        )

        self.assertEqual(
            update.model_dump(exclude_unset=True, mode="json"),
            {
                "job_background": None,
                "job_responsibilities": "1. 编写服务\n- 维护测试",
            },
        )

    def test_old_and_unknown_request_fields_are_rejected(self) -> None:
        old_requirements = {
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
        }
        for field, value in (
            ("description", "旧岗位描述"),
            ("requirements", old_requirements),
            ("legacy_requirements", {"summary": "旧要求"}),
            ("unknown_field", True),
        ):
            with self.subTest(schema="create", field=field):
                with self.assertRaises(ValidationError):
                    JobCreate.model_validate({"title": "拒绝旧字段", field: value})
            with self.subTest(schema="update", field=field):
                with self.assertRaises(ValidationError):
                    JobUpdate.model_validate({field: value})

    def test_job_read_uses_only_five_section_jd_fields(self) -> None:
        payload = {
            "id": 1,
            "title": "AI 应用工程师",
            "department": "研发部",
            "location": "长沙",
            "employment_type": "full_time",
            "headcount": 2,
            "job_background": "建设 AI 应用平台",
            "job_responsibilities": "负责应用设计与交付",
            "candidate_requirements": "具备后端开发经验",
            "preferred_qualifications": "有 RAG 项目经验",
            "public_notes": "候选人可提前准备项目介绍",
            "status": "open",
            "created_at": datetime(2026, 8, 21, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 8, 21, tzinfo=timezone.utc),
        }
        read = validate_or_fail(self, JobRead, payload)

        self.assertEqual(set(read.model_dump(mode="json")), set(payload))
        self.assertFalse(
            {"description", "requirements", "legacy_requirements"}
            & set(read.model_dump(mode="json"))
        )
