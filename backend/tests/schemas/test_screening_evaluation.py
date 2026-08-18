from unittest import TestCase

from pydantic import ValidationError

from app.prompts.screening_evaluation import (
    SCREENING_EVALUATION_PROMPT_VERSION,
    ScreeningPromptBuilder,
)
from app.schemas.screening_evaluation import (
    SCREENING_EVALUATION_SCHEMA_VERSION,
    ScreeningCandidateMaterial,
    ScreeningConfidence,
    ScreeningEvidence,
    ScreeningProfileMaterial,
    ScreeningSemanticEvaluation,
    SemanticCriterionEvaluation,
)
from app.schemas.screening_rubric import (
    RubricCriterionSource,
    RubricDimension,
    SemanticRubricCriterion,
)


def make_criteria() -> list[SemanticRubricCriterion]:
    return [
        SemanticRubricCriterion(
            key=f"criterion_{index}",
            name=f"评分项 {index}",
            description="评价岗位相关问题解决能力的真实材料。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            suggested_share=25,
            high_score_anchor="主导复杂问题并取得可核对结果。",
            mid_score_anchor="参与相关问题，但深度或结果有限。",
            low_score_anchor="只有宽泛描述，缺少具体过程。",
            source=RubricCriterionSource.HR_MANUAL,
        )
        for index in range(1, 5)
    ]


def make_material() -> ScreeningCandidateMaterial:
    return ScreeningCandidateMaterial(
        application_ref="application-test-1",
        confirmed_profile=ScreeningProfileMaterial(
            current_title="后端工程师",
            skills=["Python"],
        ),
        resume_text="主导支付系统故障排查，将恢复时间缩短至 10 分钟。",
    )


def make_evaluation(
    key: str,
    *,
    score: int | str = 8,
) -> SemanticCriterionEvaluation:
    if score == "unknown":
        return SemanticCriterionEvaluation(
            criterion_key=key,
            score="unknown",
            confidence=ScreeningConfidence.LOW,
            evidence=[],
            reason="材料不足，无法可靠判断。",
            strengths=[],
            gaps=["缺少能说明本人职责和结果的项目材料。"],
        )
    return SemanticCriterionEvaluation(
        criterion_key=key,
        score=score,
        confidence=ScreeningConfidence.HIGH,
        evidence=[
            ScreeningEvidence(
                source="resume_text",
                locator="项目经历",
                quote="主导支付系统故障排查",
            )
        ],
        reason="材料提供了问题处理和结果证据。",
        strengths=["具有复杂问题处理证据。"],
        gaps=["长期稳定性证据仍有限。"],
    )


class ScreeningSemanticEvaluationSchemaTest(TestCase):
    def test_contract_is_strict_versioned_and_validates_exact_rubric_order(self) -> None:
        criteria = make_criteria()
        result = ScreeningSemanticEvaluation(
            evaluations=[make_evaluation(item.key) for item in criteria]
        )

        self.assertEqual(result.schema_version, SCREENING_EVALUATION_SCHEMA_VERSION)
        self.assertIs(result.validate_against(criteria, make_material()), result)

        reversed_result = ScreeningSemanticEvaluation(
            evaluations=[make_evaluation(item.key) for item in reversed(criteria)]
        )
        with self.assertRaisesRegex(ValueError, "Rubric 顺序"):
            reversed_result.validate_against(criteria, make_material())

    def test_unknown_is_not_low_score_and_must_explain_missing_evidence(self) -> None:
        unknown = make_evaluation("criterion_1", score="unknown")

        self.assertEqual(unknown.score, "unknown")
        self.assertEqual(unknown.evidence, [])
        self.assertTrue(unknown.gaps)

        for changes in (
            {"confidence": "medium"},
            {
                "evidence": [
                    {
                        "source": "resume_text",
                        "locator": "经历",
                        "quote": "主导支付系统故障排查",
                    }
                ]
            },
            {"gaps": []},
        ):
            payload = unknown.model_dump(mode="json")
            payload.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SemanticCriterionEvaluation.model_validate(payload)

    def test_known_score_requires_evidence_and_score_is_strict_integer(self) -> None:
        base = make_evaluation("criterion_1").model_dump(mode="json")
        for changes in (
            {"evidence": []},
            {"score": 11},
            {"score": -1},
            {"score": 8.5},
            {"score": True},
            {"score": "8"},
            {"unexpected": "field"},
        ):
            payload = {**base, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SemanticCriterionEvaluation.model_validate(payload)

    def test_duplicate_missing_extra_and_unlocatable_evidence_are_rejected(self) -> None:
        criteria = make_criteria()
        duplicate = [make_evaluation("criterion_1") for _ in range(4)]
        with self.assertRaises(ValidationError):
            ScreeningSemanticEvaluation(evaluations=duplicate)

        wrong_quote = make_evaluation("criterion_1").model_copy(deep=True)
        wrong_quote.evidence[0].quote = "简历中不存在的结果"
        result = ScreeningSemanticEvaluation(
            evaluations=[wrong_quote, *[make_evaluation(item.key) for item in criteria[1:]]]
        )
        with self.assertRaisesRegex(ValueError, "无法在脱敏候选人材料中定位"):
            result.validate_against(criteria, make_material())

    def test_structured_evidence_matches_one_original_scalar_not_joined_list(self) -> None:
        material = make_material()
        self.assertTrue(
            material.source_contains_quote("confirmed_profile", "Python")
        )
        self.assertFalse(
            material.source_contains_quote(
                "confirmed_profile",
                "后端工程师, Python",
            )
        )

    def test_sensitive_or_unfair_output_is_rejected(self) -> None:
        base = make_evaluation("criterion_1").model_dump(mode="json")
        for field, value in (
            ("reason", "候选人年龄较合适。"),
            ("strengths", ["毕业于 985 学校。"]),
            ("gaps", ["手机号 13800138000 需要确认。"]),
        ):
            payload = {**base, field: value}
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SemanticCriterionEvaluation.model_validate(payload)


class ScreeningPromptBuilderTest(TestCase):
    def test_prompt_injects_all_published_items_and_only_safe_context(self) -> None:
        messages = ScreeningPromptBuilder.build_messages(
            {
                "title": "后端工程师",
                "description": "负责支付系统",
                "requirements": {"responsibilities": ["稳定性建设"]},
                "candidate_phone": "13800138000",
            },
            make_criteria(),
            make_material(),
        )

        self.assertEqual(SCREENING_EVALUATION_PROMPT_VERSION, "screening_evaluation_v3")
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        system = messages[0]["content"]
        user = messages[1]["content"]
        for required in (
            '"unknown"',
            "每项恰好一次",
            "不决定通过、淘汰或录用",
            "confirmed_profile",
            "不能用低分代替 unknown",
            "不得把多个数组元素用逗号合并",
            "score 为数字但 evidence 为空",
        ):
            self.assertIn(required, system)
        for item in make_criteria():
            self.assertIn(item.key, user)
        self.assertIn("不得照抄系统示例中的占位 key", user)
        self.assertIn("主导支付系统故障排查", user)
        self.assertNotIn("13800138000", user)

    def test_prompt_rejects_incomplete_rubric(self) -> None:
        with self.assertRaises(ValueError):
            ScreeningPromptBuilder.build_messages(
                {"title": "测试岗位"},
                make_criteria()[:3],
                make_material(),
            )
