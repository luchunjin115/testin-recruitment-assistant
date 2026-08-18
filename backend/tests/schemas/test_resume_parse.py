from unittest import TestCase

from pydantic import ValidationError

from app.schemas import (
    RESUME_PARSE_SCHEMA_VERSION,
    ResumeBasicInfoDraft,
    ResumeEducationDraft,
    ResumeParseDraft,
    ResumeProjectExperienceDraft,
    ResumeWorkExperienceDraft,
)


def complete_draft_payload() -> dict:
    return {
        "schema_version": "1.0",
        "basic_info": {
            "name": "张三",
            "phone": "+86 138-0013-8000",
            "email": "zhangsan@example.com",
            "gender": "男",
            "age": 30,
            "location": "上海",
            "current_company": "示例科技有限公司",
            "current_title": "后端开发工程师",
            "work_years": 7,
            "education_level": "本科",
        },
        "education_records": [
            {
                "school": "示例大学",
                "degree": "本科",
                "major": "计算机科学与技术",
                "start_date": "2013-09",
                "end_date": "2017-06",
            }
        ],
        "work_experiences": [
            {
                "company": "示例科技有限公司",
                "title": "后端开发工程师",
                "start_date": "2021-03",
                "end_date": "至今",
                "description": "负责招聘系统后端研发。",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            }
        ],
        "project_experiences": [
            {
                "project_name": "AI 招聘助手",
                "role": "后端开发",
                "start_date": "2025",
                "end_date": "至今",
                "description": "实现简历处理主链路。",
                "tech_stack": ["Python", "Pydantic"],
                "achievements": "建立严格的数据校验边界。",
            }
        ],
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "certifications": ["软件设计师"],
        "self_evaluation": "重视工程质量与数据安全。",
        "warnings": ["手机号包含国际区号，请 HR 核对。"],
        "missing_fields": [],
    }


def nullable_draft_payload() -> dict:
    return {
        "schema_version": "1.0",
        "basic_info": {
            "name": None,
            "phone": None,
            "email": None,
            "gender": None,
            "age": None,
            "location": None,
            "current_company": None,
            "current_title": None,
            "work_years": None,
            "education_level": None,
        },
        "education_records": [],
        "work_experiences": [],
        "project_experiences": [],
        "skills": [],
        "certifications": [],
        "self_evaluation": None,
        "warnings": [],
        "missing_fields": ["basic_info.name", "basic_info.phone"],
    }


class ResumeParseDraftTest(TestCase):
    def test_complete_valid_draft_passes(self) -> None:
        draft = ResumeParseDraft.model_validate(complete_draft_payload())

        self.assertEqual(draft.schema_version, RESUME_PARSE_SCHEMA_VERSION)
        self.assertEqual(draft.basic_info.name, "张三")
        self.assertEqual(draft.education_records[0].school, "示例大学")
        self.assertEqual(draft.work_experiences[0].end_date, "至今")

    def test_many_nullable_fields_and_empty_arrays_are_valid(self) -> None:
        draft = ResumeParseDraft.model_validate(nullable_draft_payload())

        self.assertIsNone(draft.basic_info.name)
        self.assertIsNone(draft.self_evaluation)
        self.assertEqual(draft.education_records, [])
        self.assertEqual(draft.skills, [])

    def test_unknown_schema_version_is_rejected(self) -> None:
        payload = nullable_draft_payload()
        payload["schema_version"] = "2.0"

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_null_is_not_allowed_for_array_fields(self) -> None:
        payload = nullable_draft_payload()
        payload["skills"] = None

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_missing_nullable_key_is_rejected(self) -> None:
        payload = nullable_draft_payload()
        del payload["basic_info"]["email"]

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_extra_fields_are_rejected_at_every_level(self) -> None:
        mutations = (
            lambda payload: payload.update({"unexpected": "value"}),
            lambda payload: payload["basic_info"].update({"target_role": "后端工程师"}),
            lambda payload: payload["education_records"][0].update({"is_985": True}),
        )

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = complete_draft_payload()
                mutation(payload)
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_wrong_field_types_are_rejected_without_coercion(self) -> None:
        mutations = (
            lambda payload: payload["basic_info"].update({"age": "30"}),
            lambda payload: payload["basic_info"].update({"name": 123}),
            lambda payload: payload.update({"skills": "Python"}),
            lambda payload: payload.update({"warnings": [123]}),
        )

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = complete_draft_payload()
                mutation(payload)
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_age_and_work_years_ranges_are_enforced(self) -> None:
        for field, value in (("age", -1), ("age", 121), ("work_years", -1), ("work_years", 81)):
            with self.subTest(field=field, value=value):
                payload = complete_draft_payload()
                payload["basic_info"][field] = value
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_date_format_and_month_range_are_enforced(self) -> None:
        invalid_dates = ("2024/01", "2024-1", "2024-00", "2024-13", "24-01", "现在")
        for invalid_date in invalid_dates:
            with self.subTest(invalid_date=invalid_date):
                payload = complete_draft_payload()
                payload["education_records"][0]["start_date"] = invalid_date
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_start_date_cannot_be_obviously_later_than_end_date(self) -> None:
        for section in ("education_records", "work_experiences", "project_experiences"):
            with self.subTest(section=section):
                payload = complete_draft_payload()
                payload[section][0]["start_date"] = "2025-02"
                payload[section][0]["end_date"] = "2024-12"
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_different_date_precision_is_rejected_only_when_conflict_is_obvious(self) -> None:
        payload = complete_draft_payload()
        payload["education_records"][0]["start_date"] = "2024-12"
        payload["education_records"][0]["end_date"] = "2024"

        draft = ResumeParseDraft.model_validate(payload)
        self.assertEqual(draft.education_records[0].end_date, "2024")

        payload["education_records"][0]["start_date"] = "2025"
        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_present_is_only_allowed_as_end_date(self) -> None:
        payload = complete_draft_payload()
        payload["work_experiences"][0]["start_date"] = "至今"

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

        payload["work_experiences"][0]["start_date"] = "2024"
        payload["work_experiences"][0]["end_date"] = "至今"
        draft = ResumeParseDraft.model_validate(payload)
        self.assertEqual(draft.work_experiences[0].end_date, "至今")

    def test_completely_blank_experience_records_are_rejected(self) -> None:
        blank_records = (
            (
                "education_records",
                {"school": None, "degree": None, "major": None, "start_date": None, "end_date": None},
            ),
            (
                "work_experiences",
                {
                    "company": None,
                    "title": None,
                    "start_date": None,
                    "end_date": None,
                    "description": None,
                    "tech_stack": [],
                },
            ),
            (
                "project_experiences",
                {
                    "project_name": None,
                    "role": None,
                    "start_date": None,
                    "end_date": None,
                    "description": None,
                    "tech_stack": [],
                    "achievements": None,
                },
            ),
        )

        for section, blank_record in blank_records:
            with self.subTest(section=section):
                payload = nullable_draft_payload()
                payload[section] = [blank_record]
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_skills_tech_stacks_and_certifications_are_trimmed_and_deduplicated(self) -> None:
        payload = complete_draft_payload()
        payload["skills"] = [" Python ", "", "Python", "python", " FastAPI ", "   "]
        payload["certifications"] = [" 软件设计师 ", "", "软件设计师", "PMP"]
        payload["work_experiences"][0]["tech_stack"] = [" SQL ", "SQL", "PostgreSQL", ""]
        payload["project_experiences"][0]["tech_stack"] = [" React ", "React", "TypeScript"]

        draft = ResumeParseDraft.model_validate(payload)

        self.assertEqual(draft.skills, ["Python", "python", "FastAPI"])
        self.assertEqual(draft.certifications, ["软件设计师", "PMP"])
        self.assertEqual(draft.work_experiences[0].tech_stack, ["SQL", "PostgreSQL"])
        self.assertEqual(draft.project_experiences[0].tech_stack, ["React", "TypeScript"])

    def test_non_string_list_items_are_rejected_instead_of_coerced(self) -> None:
        payload = complete_draft_payload()
        payload["skills"] = ["Python", 123]

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_overlong_strings_are_rejected(self) -> None:
        mutations = (
            lambda payload: payload["basic_info"].update({"name": "名" * 101}),
            lambda payload: payload["work_experiences"][0].update(
                {"description": "工" * 10_001}
            ),
            lambda payload: payload.update({"self_evaluation": "评" * 5_001}),
            lambda payload: payload.update({"skills": ["技" * 101]}),
        )

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = complete_draft_payload()
                mutation(payload)
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_blank_scalar_strings_must_use_null_instead(self) -> None:
        payload = nullable_draft_payload()
        payload["basic_info"]["name"] = "   "

        with self.assertRaises(ValidationError):
            ResumeParseDraft.model_validate(payload)

    def test_email_and_phone_validation_accepts_reasonable_formats(self) -> None:
        formats = (
            ("+86 138-0013-8000", "candidate@example.com"),
            ("(415) 555-2671", "first.last+hr@example.co.uk"),
        )
        for phone, email in formats:
            with self.subTest(phone=phone, email=email):
                payload = nullable_draft_payload()
                payload["basic_info"]["phone"] = phone
                payload["basic_info"]["email"] = email
                draft = ResumeParseDraft.model_validate(payload)
                self.assertEqual(draft.basic_info.phone, phone)
                self.assertEqual(draft.basic_info.email, email)

    def test_email_and_phone_validation_rejects_unreasonable_values(self) -> None:
        cases = (
            ("12345", None),
            ("13800138000 ext 2", None),
            (None, "not-an-email"),
            (None, ".candidate@example.com"),
        )
        for phone, email in cases:
            with self.subTest(phone=phone, email=email):
                payload = nullable_draft_payload()
                payload["basic_info"]["phone"] = phone
                payload["basic_info"]["email"] = email
                with self.assertRaises(ValidationError):
                    ResumeParseDraft.model_validate(payload)

    def test_education_schema_has_no_model_inferred_school_labels(self) -> None:
        properties = ResumeEducationDraft.model_json_schema()["properties"]

        self.assertEqual(
            set(properties),
            {"school", "degree", "major", "start_date", "end_date"},
        )
        self.assertNotIn("is_985", properties)
        self.assertNotIn("is_211", properties)

    def test_schema_is_exported_for_future_service_and_api_reuse(self) -> None:
        self.assertTrue(issubclass(ResumeParseDraft, object))
        self.assertEqual(RESUME_PARSE_SCHEMA_VERSION, "1.0")

        json_schema = ResumeParseDraft.model_json_schema()
        self.assertEqual(json_schema["properties"]["schema_version"]["const"], "1.0")
        self.assertFalse(json_schema["additionalProperties"])
        self.assertIn("ResumeBasicInfoDraft", json_schema["$defs"])
        self.assertIn("ResumeWorkExperienceDraft", json_schema["$defs"])

    def test_all_five_public_schema_types_can_validate_independently(self) -> None:
        payload = complete_draft_payload()

        self.assertIsInstance(
            ResumeBasicInfoDraft.model_validate(payload["basic_info"]),
            ResumeBasicInfoDraft,
        )
        self.assertIsInstance(
            ResumeEducationDraft.model_validate(payload["education_records"][0]),
            ResumeEducationDraft,
        )
        self.assertIsInstance(
            ResumeWorkExperienceDraft.model_validate(payload["work_experiences"][0]),
            ResumeWorkExperienceDraft,
        )
        self.assertIsInstance(
            ResumeProjectExperienceDraft.model_validate(payload["project_experiences"][0]),
            ResumeProjectExperienceDraft,
        )
        self.assertIsInstance(ResumeParseDraft.model_validate(payload), ResumeParseDraft)
