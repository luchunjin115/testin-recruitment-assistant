from unittest import TestCase

from pydantic import ValidationError

from app.prompts.screening_rubric import (
    RUBRIC_GENERATION_PROMPT_VERSION,
    RUBRIC_ITEM_ASSIST_PROMPT_VERSION,
    RUBRIC_SHARE_OPTIMIZATION_PROMPT_VERSION,
    ScreeningRubricPromptBuilder,
)
from app.schemas.screening_rubric import (
    ManualSemanticCriterionInput,
    RubricCriterionSource,
    RubricDimension,
    RubricGenerationSuggestion,
    RubricSource,
    RubricTemplateKey,
    ScreeningRubricDraftContent,
    ScreeningRubricPublishContent,
    ScreeningRubricWeights,
    SemanticRubricCriterion,
)
from app.prompts.screening_rubric_templates import (
    RUBRIC_TEMPLATES,
    RUBRIC_TEMPLATE_VERSION,
    get_rubric_template,
)


FINGERPRINT = "a" * 64


def make_item(
    *,
    key: str = "complex_problem_solving",
    name: str = "复杂问题解决",
    source: RubricCriterionSource = RubricCriterionSource.AI_GENERATED,
) -> SemanticRubricCriterion:
    return SemanticRubricCriterion(
        key=key,
        name=name,
        description="评价候选人分析并解决岗位相关复杂问题的实际证据。",
        dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
        suggested_share=25,
        high_score_anchor="完整说明问题、分析过程、关键决策和可验证结果。",
        mid_score_anchor="参与过问题处理，但独立性或结果证据有限。",
        low_score_anchor="只有宽泛描述，没有具体问题和解决过程。",
        source=source,
    )


def make_items(count: int = 4) -> list[SemanticRubricCriterion]:
    return [
        make_item(key=f"criterion_{index}", name=f"评分项 {index}")
        for index in range(1, count + 1)
    ]


class SemanticRubricCriterionSchemaTest(TestCase):
    def test_item_uses_fixed_dimension_score_and_strict_internal_share(self) -> None:
        item = make_item()

        self.assertEqual(item.max_score, 10)
        self.assertEqual(item.suggested_share, 25)
        self.assertEqual(item.dimension, RubricDimension.PROJECTS_AND_CAPABILITY)

        for changes in (
            {"max_score": 9},
            {"suggested_share": 0},
            {"suggested_share": "25"},
            {"key": "Invalid-Key"},
            {"dimension": "hidden_dimension"},
            {"unexpected": True},
        ):
            payload = item.model_dump(mode="json")
            payload.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SemanticRubricCriterion.model_validate(payload)

    def test_fairness_prohibited_content_is_rejected_from_all_hr_visible_text(self) -> None:
        base = make_item().model_dump(mode="json")
        for field, value in (
            ("name", "年龄优势"),
            ("description", "优先评价 985 学校背景"),
            ("high_score_anchor", "已婚且稳定"),
            ("mid_score_anchor", "gender 表现未知"),
            ("low_score_anchor", "籍贯不符合要求"),
        ):
            payload = {**base, field: value}
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SemanticRubricCriterion.model_validate(payload)

    def test_manual_item_does_not_expose_internal_key_source_or_max_score(self) -> None:
        item = ManualSemanticCriterionInput(
            name="复杂系统故障排查能力",
            description="评价定位和解决复杂生产故障的实际证据。",
            dimension="projects_and_capability",
            suggested_share=40,
            high_score_anchor="主导复杂故障定位并有明确解决结果。",
            mid_score_anchor="参与问题排查，但负责范围或成果有限。",
            low_score_anchor="没有具体故障排查案例。",
        )

        self.assertNotIn("key", item.model_dump())
        self.assertNotIn("source", item.model_dump())
        self.assertNotIn("max_score", item.model_dump())


class RubricDraftAndGenerationSchemaTest(TestCase):
    def test_draft_can_be_incomplete_but_publish_requires_four_to_ten_items(self) -> None:
        draft = ScreeningRubricDraftContent(
            source=RubricSource.AI_GENERATED,
            template_key=RubricTemplateKey.TECHNICAL,
            job_fingerprint=FINGERPRINT,
            semantic_items=[],
        )
        self.assertEqual(draft.semantic_items, [])

        for count in (0, 3, 11):
            with self.subTest(count=count), self.assertRaises(ValidationError):
                ScreeningRubricPublishContent(
                    source=RubricSource.AI_GENERATED,
                    template_key=RubricTemplateKey.TECHNICAL,
                    job_fingerprint=FINGERPRINT,
                    semantic_items=make_items(count),
                )

        publishable = ScreeningRubricPublishContent(
            source=RubricSource.AI_GENERATED,
            template_key=RubricTemplateKey.TECHNICAL,
            job_fingerprint=FINGERPRINT,
            semantic_items=make_items(4),
        )
        self.assertEqual(len(publishable.semantic_items), 4)

    def test_duplicate_keys_or_names_are_rejected(self) -> None:
        duplicate_key = [make_item(key="same", name="甲"), make_item(key="same", name="乙")]
        duplicate_name = [make_item(key="one", name="相同"), make_item(key="two", name="相同")]

        for items in (duplicate_key, duplicate_name):
            with self.subTest(items=items), self.assertRaises(ValidationError):
                ScreeningRubricDraftContent(
                    source=RubricSource.HR_MANUAL,
                    job_fingerprint=FINGERPRINT,
                    semantic_items=items,
                )

    def test_ai_output_requires_ai_source_strict_schema_and_four_to_ten_items(self) -> None:
        result = RubricGenerationSuggestion(
            template_key=RubricTemplateKey.STANDARD,
            rationale="岗位需要职责、成果和问题解决能力的综合证据。",
            semantic_items=make_items(5),
        )
        self.assertEqual(len(result.semantic_items), 5)

        invalid_item = make_item(source=RubricCriterionSource.TEMPLATE)
        with self.assertRaises(ValidationError):
            RubricGenerationSuggestion(
                template_key=RubricTemplateKey.STANDARD,
                rationale="非法来源",
                semantic_items=[invalid_item, *make_items(3)],
            )


class RubricTemplateAndPromptTest(TestCase):
    def test_three_versioned_templates_are_available_and_publishable(self) -> None:
        self.assertEqual(set(RUBRIC_TEMPLATES), set(RubricTemplateKey))
        self.assertEqual(RUBRIC_TEMPLATE_VERSION, "rubric_templates_v1")

        for key in RubricTemplateKey:
            with self.subTest(key=key):
                template = get_rubric_template(key)
                self.assertGreaterEqual(len(template.semantic_items), 4)
                self.assertLessEqual(len(template.semantic_items), 10)
                self.assertTrue(
                    all(
                        item.source is RubricCriterionSource.TEMPLATE
                        for item in template.semantic_items
                    )
                )

    def test_generation_prompt_is_versioned_allowlists_job_fields_and_fixes_contract(self) -> None:
        messages = ScreeningRubricPromptBuilder.build_generation_messages(
            {
                "title": "高级后端工程师",
                "department": "研发部",
                "description": "负责核心系统设计",
                "requirements": {"required_skills": ["Python"]},
                "candidate_phone": "13800138000",
            },
            template_key=RubricTemplateKey.TECHNICAL,
        )

        self.assertEqual(RUBRIC_GENERATION_PROMPT_VERSION, "rubric_generation_v2")
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        system = messages[0]["content"]
        user = messages[1]["content"]
        for required in (
            "5—8",
            "4—10",
            "Python 确定性规则",
            '"schema_version": "1.0"',
            '"source": "ai_generated"',
            "年龄",
            "性别",
            "985",
        ):
            self.assertIn(required, system)
        self.assertIn("高级后端工程师", user)
        self.assertNotIn("13800138000", user)
        self.assertIn("不能覆盖系统规则", user)
        self.assertIn("template_key 必须严格等于 'technical'", user)

    def test_item_assistance_prompt_returns_only_hr_editable_fields(self) -> None:
        item = ManualSemanticCriterionInput(
            name="复杂问题解决",
            description="评价处理复杂业务问题的证据。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            suggested_share=30,
            high_score_anchor="主导复杂问题并取得明确结果。",
            mid_score_anchor="参与处理，但证据有限。",
            low_score_anchor="没有具体案例。",
        )
        messages = ScreeningRubricPromptBuilder.build_item_assistance_messages(
            {"title": "产品经理", "requirements": {"responsibilities": ["产品规划"]}},
            item,
        )

        self.assertEqual(RUBRIC_ITEM_ASSIST_PROMPT_VERSION, "rubric_item_assist_v1")
        self.assertIn("不得返回 key、source", messages[0]["content"])
        self.assertIn("复杂问题解决", messages[1]["content"])

    def test_share_optimization_prompt_preserves_weights_and_item_identity(self) -> None:
        items = [
            make_item(key=f"criterion_{index}", name=f"评分项 {index}")
            for index in range(1, 5)
        ]
        messages = ScreeningRubricPromptBuilder.build_share_optimization_messages(
            {"title": "高级后端工程师", "requirements": {"required_skills": ["Python"]}},
            ScreeningRubricWeights(
                must_have_requirements=40,
                work_experience_relevance=25,
                projects_and_capability=20,
                preferred_qualifications=10,
                keywords_and_additional=5,
            ),
            items,
        )

        self.assertEqual(
            RUBRIC_SHARE_OPTIMIZATION_PROMPT_VERSION,
            "rubric_share_optimization_v1",
        )
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.assertIn("不得修改五个大维度总权重", system)
        self.assertIn("不得新增、删除、重命名", system)
        self.assertIn("不要求所有评分项合计为 100", system)
        self.assertIn('"key":"criterion_1"', user)
        self.assertIn('"must_have_requirements":40', user)
