from unittest import TestCase

from app.schemas.screening_evaluation import ScreeningSemanticEvaluation
from app.schemas.screening_rules import CriterionMatchInput, HardRequirementCheck
from app.schemas.screening_rubric import (
    RubricCriterionSource,
    ScreeningRubricWeights,
    SemanticRubricCriterion,
)
from app.services.screening_score_service import ScreeningScoreService


def criterion(
    key: str,
    dimension: str,
    *,
    share: int = 10,
) -> SemanticRubricCriterion:
    return SemanticRubricCriterion(
        key=key,
        name=key,
        description=f"评价 {key}",
        dimension=dimension,
        suggested_share=share,
        high_score_anchor="证据充分且表现优秀",
        mid_score_anchor="有部分相关证据",
        low_score_anchor="有明确较弱证据",
        source=RubricCriterionSource.HR_MANUAL,
    )


def semantic_result(
    criteria: list[SemanticRubricCriterion],
    scores: list[int | str],
) -> ScreeningSemanticEvaluation:
    evaluations = []
    for item, score in zip(criteria, scores, strict=True):
        if score == "unknown":
            evaluations.append(
                {
                    "criterion_key": item.key,
                    "score": "unknown",
                    "confidence": "low",
                    "evidence": [],
                    "reason": "材料不足",
                    "strengths": [],
                    "gaps": [f"缺少 {item.key} 证据"],
                }
            )
        else:
            evaluations.append(
                {
                    "criterion_key": item.key,
                    "score": score,
                    "confidence": "high",
                    "evidence": [
                        {
                            "source": "resume_text",
                            "locator": item.key,
                            "quote": f"{item.key} evidence",
                        }
                    ],
                    "reason": "证据与评分锚点一致",
                    "strengths": [f"{item.key} 优势"],
                    "gaps": [],
                }
            )
    return ScreeningSemanticEvaluation(evaluations=evaluations)


class ScreeningScoreServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = ScreeningScoreService()

    def test_combines_deterministic_and_semantic_items_inside_dimension(self) -> None:
        criteria = [
            criterion("delivery", "must_have_requirements", share=20),
            criterion("ownership", "work_experience_relevance"),
            criterion("project_depth", "projects_and_capability"),
            criterion("growth", "preferred_qualifications"),
        ]
        result = self.service.score(
            weights=ScreeningRubricWeights(),
            deterministic_matches=[
                CriterionMatchInput(
                    criterion="required_skills",
                    match_level="full",
                    evidence=["已确认技能：Python"],
                )
            ],
            hard_requirement_checks=[
                HardRequirementCheck(
                    criterion="required_skills",
                    requirement="Python",
                    status="passed",
                    evidence=["已确认技能：Python"],
                )
            ],
            semantic_items=criteria,
            semantic_evaluation=semantic_result(criteria, [10, 8, 6, 10]),
        )

        self.assertFalse(result.blocked)
        self.assertEqual(result.overall_score, 86)
        self.assertEqual(result.evidence_coverage_rate, 1.0)
        self.assertEqual(result.recommendation.value, "strong_recommend")
        must_have = [
            item
            for item in result.criterion_scores
            if item.dimension.value == "must_have_requirements"
        ]
        self.assertEqual([item.adjusted_weight for item in must_have], [20.0, 20.0])

    def test_unknown_lowers_coverage_without_becoming_explicit_failure(self) -> None:
        criteria = [
            criterion("must_context", "must_have_requirements"),
            criterion("ownership", "work_experience_relevance"),
            criterion("project_depth", "projects_and_capability"),
            criterion("growth", "preferred_qualifications"),
        ]
        result = self.service.score(
            weights=ScreeningRubricWeights(),
            deterministic_matches=[],
            hard_requirement_checks=[],
            semantic_items=criteria,
            semantic_evaluation=semantic_result(criteria, [10, 10, "unknown", "unknown"]),
        )

        self.assertFalse(result.blocked)
        self.assertEqual(result.evidence_coverage_rate, 0.6842)
        self.assertEqual(result.overall_score, 68)
        self.assertEqual(result.recommendation.value, "review_required")
        self.assertIn("缺少 project_depth 证据", result.pending_questions)

    def test_hard_unknown_caps_otherwise_strong_result(self) -> None:
        criteria = [
            criterion("must_context", "must_have_requirements"),
            criterion("ownership", "work_experience_relevance"),
            criterion("project_depth", "projects_and_capability"),
            criterion("growth", "preferred_qualifications"),
        ]
        result = self.service.score(
            weights=ScreeningRubricWeights(),
            deterministic_matches=[
                CriterionMatchInput(
                    criterion="required_skills",
                    match_level="unknown",
                    evidence=[],
                )
            ],
            hard_requirement_checks=[
                HardRequirementCheck(
                    criterion="required_skills",
                    requirement="Python",
                    status="unknown",
                    evidence=[],
                )
            ],
            semantic_items=criteria,
            semantic_evaluation=semantic_result(criteria, [10, 10, 10, 10]),
        )

        self.assertEqual(result.recommendation.value, "review_required")
        self.assertTrue(result.recommendation_capped)
        self.assertIn(
            "hard_requirement_unknown",
            [reason.value for reason in result.cap_reasons],
        )

    def test_all_unknown_is_blocked_instead_of_zero_score(self) -> None:
        criteria = [
            criterion("must_context", "must_have_requirements"),
            criterion("ownership", "work_experience_relevance"),
            criterion("project_depth", "projects_and_capability"),
            criterion("growth", "preferred_qualifications"),
        ]
        result = self.service.score(
            weights=ScreeningRubricWeights(),
            deterministic_matches=[],
            hard_requirement_checks=[],
            semantic_items=criteria,
            semantic_evaluation=semantic_result(
                criteria,
                ["unknown", "unknown", "unknown", "unknown"],
            ),
        )

        self.assertTrue(result.blocked)
        self.assertIsNone(result.overall_score)
        self.assertIsNone(result.recommendation)
        self.assertEqual(result.evidence_coverage_rate, 0.0)

    def test_rejects_semantic_result_with_different_rubric_order(self) -> None:
        criteria = [
            criterion("one", "must_have_requirements"),
            criterion("two", "work_experience_relevance"),
            criterion("three", "projects_and_capability"),
            criterion("four", "preferred_qualifications"),
        ]
        reversed_evaluation = semantic_result(list(reversed(criteria)), [10, 10, 10, 10])

        with self.assertRaisesRegex(ValueError, "完整对应"):
            self.service.score(
                weights=ScreeningRubricWeights(),
                deterministic_matches=[],
                hard_requirement_checks=[],
                semantic_items=criteria,
                semantic_evaluation=reversed_evaluation,
            )
