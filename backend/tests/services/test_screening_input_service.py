import json
from unittest import TestCase

from pydantic import ValidationError

from app.services.screening_input_service import ScreeningInputService


class ScreeningInputServiceTest(TestCase):
    def test_builds_separate_safe_sources_and_redacts_raw_resume(self) -> None:
        material = ScreeningInputService.build_candidate_material(
            application_ref="application-101",
            confirmed_profile={
                "name": "张三",
                "phone": "13800138000",
                "email": "zhangsan@example.com",
                "gender": "男",
                "age": 30,
                "current_title": "后端工程师",
                "work_years": 5,
                "skills": ["Python", "Python", "PostgreSQL"],
                "education_records": [
                    {"school": "某大学", "degree": "本科", "major": "计算机"}
                ],
            },
            resume_raw_text=(
                "姓名：张三\n手机：13800138000\n邮箱：zhangsan@example.com\n"
                "性别：男\n地址：北京市某街道\n"
                "张三主导支付系统改造，接口延迟降低 30%。\n"
                "主页：https://github.com/zhangsan"
            ),
            resume_snapshot={
                "draft": {
                    "basic_info": {
                        "name": "张三",
                        "gender": "男",
                        "age": 30,
                        "current_title": "高级开发工程师",
                    },
                    "skills": ["Python"],
                    "education_records": [
                        {"school": "某大学", "degree": "本科", "major": "计算机"}
                    ],
                    "project_experiences": [
                        {
                            "project_name": "支付平台",
                            "role": "核心开发",
                            "description": "负责高并发交易链路",
                            "achievements": "可用性提升至 99.99%",
                            "tech_stack": ["Python", "Redis"],
                        }
                    ],
                },
                "metadata": {
                    "model": "deepseek-v4-flash",
                    "prompt_version": "resume_structure_v1",
                },
            },
        )

        serialized = json.dumps(material.model_dump(mode="json"), ensure_ascii=False)
        for prohibited in (
            "张三",
            "13800138000",
            "zhangsan@example.com",
            "北京市某街道",
            "某大学",
            "github.com/zhangsan",
        ):
            self.assertNotIn(prohibited, serialized)
        self.assertIn("接口延迟降低 30%", material.resume_text or "")
        self.assertEqual(material.confirmed_profile.current_title, "后端工程师")
        self.assertEqual(material.structured_resume.current_title, "高级开发工程师")
        self.assertEqual(material.confirmed_profile.skills, ["Python", "PostgreSQL"])
        self.assertEqual(material.structured_resume.education_records[0].major, "计算机")

    def test_empty_candidate_material_is_blocked_before_model_call(self) -> None:
        cases = (
            "姓名：李四\n电话：13900139000",
            "李四",
        )
        for raw_text in cases:
            with self.subTest(raw_text=raw_text), self.assertRaises(ValidationError):
                ScreeningInputService.build_candidate_material(
                    application_ref="application-empty",
                    confirmed_profile={"name": "李四", "phone": "13900139000"},
                    resume_raw_text=raw_text,
                    resume_snapshot={
                        "basic_info": {"name": "李四"},
                        "education_records": [{"school": "某大学"}],
                    },
                )

    def test_rejects_identity_fields_if_callers_bypass_the_service_schema(self) -> None:
        from app.schemas.screening_evaluation import ScreeningCandidateMaterial

        with self.assertRaises(ValidationError):
            ScreeningCandidateMaterial.model_validate(
                {
                    "application_ref": "application-unsafe",
                    "confirmed_profile": {"name": "王五", "skills": ["Python"]},
                }
            )

    def test_ai_structured_snapshot_alone_cannot_satisfy_minimum_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "材料不足"):
            ScreeningInputService.build_candidate_material(
                application_ref="application-structured-only",
                confirmed_profile=None,
                resume_raw_text=None,
                resume_snapshot={
                    "draft": {
                        "skills": ["Python"],
                        "work_experiences": [
                            {"description": "AI 结构化快照中的经历"}
                        ],
                    }
                },
            )
