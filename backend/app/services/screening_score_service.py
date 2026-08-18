from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from app.schemas.screening_evaluation import ScreeningSemanticEvaluation
from app.schemas.screening_rules import (
    CriterionMatchInput,
    HardRequirementCheck,
    HardRequirementStatus,
    RecommendationCapReason,
    ScreeningCriterion,
    ScreeningMatchLevel,
    ScreeningRecommendation,
)
from app.schemas.screening_rubric import (
    RubricDimension,
    ScreeningRubricWeights,
    SemanticRubricCriterion,
)
from app.schemas.screening_score import (
    CombinedCriterionScore,
    CombinedDimensionScore,
    CombinedScreeningScoreResult,
    ScreeningScoreSource,
)


SCREENING_SCORE_VERSION = "1.0"

_DETERMINISTIC_CONFIG = {
    ScreeningCriterion.REQUIRED_SKILLS: (
        RubricDimension.MUST_HAVE_REQUIREMENTS,
        20,
    ),
    ScreeningCriterion.MINIMUM_WORK_YEARS: (
        RubricDimension.MUST_HAVE_REQUIREMENTS,
        8,
    ),
    ScreeningCriterion.EDUCATION_REQUIREMENT: (
        RubricDimension.MUST_HAVE_REQUIREMENTS,
        4,
    ),
    ScreeningCriterion.REQUIRED_EXPERIENCES: (
        RubricDimension.MUST_HAVE_REQUIREMENTS,
        8,
    ),
    ScreeningCriterion.PREFERRED_SKILLS: (
        RubricDimension.PREFERRED_QUALIFICATIONS,
        5,
    ),
    ScreeningCriterion.KEYWORDS: (
        RubricDimension.KEYWORDS_AND_ADDITIONAL,
        2,
    ),
}

_MATCH_SCORE = {
    ScreeningMatchLevel.FULL: 10,
    ScreeningMatchLevel.STRONG: 8,
    ScreeningMatchLevel.PARTIAL: 5,
    ScreeningMatchLevel.WEAK: 2,
    ScreeningMatchLevel.NONE: 0,
    ScreeningMatchLevel.UNKNOWN: "unknown",
}


@dataclass(frozen=True, slots=True)
class _ScoreInput:
    criterion_key: str
    dimension: RubricDimension
    source: ScreeningScoreSource
    suggested_share: int
    raw_score: int | str
    evidence_count: int


class ScreeningScoreService:
    """Combine deterministic and semantic items without asking the model for totals."""

    def score(
        self,
        *,
        weights: ScreeningRubricWeights,
        deterministic_matches: Sequence[CriterionMatchInput],
        hard_requirement_checks: Sequence[HardRequirementCheck],
        semantic_items: Sequence[SemanticRubricCriterion],
        semantic_evaluation: ScreeningSemanticEvaluation,
    ) -> CombinedScreeningScoreResult:
        semantic_keys = [item.key for item in semantic_items]
        actual_keys = [item.criterion_key for item in semantic_evaluation.evaluations]
        if actual_keys != semantic_keys:
            raise ValueError("语义评价必须与已发布 Rubric 完整对应")

        deterministic_criteria = [item.criterion for item in deterministic_matches]
        if len(deterministic_criteria) != len(set(deterministic_criteria)):
            raise ValueError("确定性评分项不能重复")

        inputs = self._build_inputs(
            deterministic_matches,
            semantic_items,
            semantic_evaluation,
        )
        by_dimension = {
            dimension: [item for item in inputs if item.dimension is dimension]
            for dimension in RubricDimension
        }

        criterion_scores: list[CombinedCriterionScore] = []
        dimension_scores: list[CombinedDimensionScore] = []
        total_effective_weight = Decimal("0")
        total_earned_points = Decimal("0")
        total_evidence_weight = Decimal("0")

        for dimension in RubricDimension:
            dimension_inputs = by_dimension[dimension]
            if not dimension_inputs:
                continue
            configured_weight = Decimal(str(getattr(weights, dimension.value)))
            if configured_weight == 0:
                continue
            total_share = Decimal(str(sum(item.suggested_share for item in dimension_inputs)))
            dimension_earned = Decimal("0")
            dimension_evidence_weight = Decimal("0")

            for item in dimension_inputs:
                adjusted_weight = (
                    configured_weight
                    * Decimal(str(item.suggested_share))
                    / total_share
                )
                if item.raw_score == "unknown":
                    earned_points = Decimal("0")
                else:
                    earned_points = adjusted_weight * Decimal(str(item.raw_score)) / Decimal("10")
                    dimension_evidence_weight += adjusted_weight
                dimension_earned += earned_points
                criterion_scores.append(
                    CombinedCriterionScore(
                        criterion_key=item.criterion_key,
                        dimension=dimension,
                        source=item.source,
                        raw_score=item.raw_score,
                        adjusted_weight=self._rounded_float(adjusted_weight),
                        earned_points=self._rounded_float(earned_points),
                        evidence_count=item.evidence_count,
                    )
                )

            total_effective_weight += configured_weight
            total_earned_points += dimension_earned
            total_evidence_weight += dimension_evidence_weight
            dimension_scores.append(
                CombinedDimensionScore(
                    dimension=dimension,
                    configured_weight=int(configured_weight),
                    score_percentage=self._rounded_float(
                        dimension_earned / configured_weight * Decimal("100")
                    ),
                    evidence_coverage_rate=self._rounded_float(
                        dimension_evidence_weight / configured_weight
                    ),
                )
            )

        hard_pass = self._hard_pass(hard_requirement_checks)
        if total_effective_weight == 0 or total_evidence_weight == 0:
            return self._blocked_result(
                hard_pass=hard_pass,
                criterion_scores=criterion_scores,
                dimension_scores=dimension_scores,
                semantic_evaluation=semantic_evaluation,
                hard_requirement_checks=hard_requirement_checks,
            )

        evidence_coverage = total_evidence_weight / total_effective_weight
        overall_score = int(
            (total_earned_points / total_effective_weight * Decimal("100")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        cap_reasons = self._cap_reasons(hard_requirement_checks, evidence_coverage)
        base_recommendation = self._recommendation_for_score(overall_score)
        recommendation = base_recommendation
        if cap_reasons and base_recommendation in {
            ScreeningRecommendation.STRONG_RECOMMEND,
            ScreeningRecommendation.RECOMMEND,
        }:
            recommendation = ScreeningRecommendation.REVIEW_REQUIRED

        strengths, risks, questions = self._summaries(
            semantic_evaluation,
            hard_requirement_checks,
        )
        return CombinedScreeningScoreResult(
            blocked=False,
            overall_score=overall_score,
            evidence_coverage_rate=self._rounded_float(evidence_coverage),
            recommendation=recommendation,
            recommendation_capped=recommendation is not base_recommendation,
            cap_reasons=cap_reasons,
            hard_pass=hard_pass,
            criterion_scores=criterion_scores,
            dimension_scores=dimension_scores,
            strengths=strengths,
            risks=risks,
            pending_questions=questions,
        )

    @staticmethod
    def _build_inputs(
        deterministic_matches: Sequence[CriterionMatchInput],
        semantic_items: Sequence[SemanticRubricCriterion],
        semantic_evaluation: ScreeningSemanticEvaluation,
    ) -> list[_ScoreInput]:
        result: list[_ScoreInput] = []
        for match in deterministic_matches:
            config = _DETERMINISTIC_CONFIG.get(match.criterion)
            if config is None:
                raise ValueError("当前确定性评分项不属于新版 Rubric 计算合同")
            dimension, suggested_share = config
            result.append(
                _ScoreInput(
                    criterion_key=match.criterion.value,
                    dimension=dimension,
                    source=ScreeningScoreSource.DETERMINISTIC,
                    suggested_share=suggested_share,
                    raw_score=_MATCH_SCORE[match.match_level],
                    evidence_count=len(match.evidence),
                )
            )
        for rubric_item, evaluation in zip(
            semantic_items,
            semantic_evaluation.evaluations,
            strict=True,
        ):
            result.append(
                _ScoreInput(
                    criterion_key=rubric_item.key,
                    dimension=rubric_item.dimension,
                    source=ScreeningScoreSource.SEMANTIC,
                    suggested_share=rubric_item.suggested_share,
                    raw_score=evaluation.score,
                    evidence_count=len(evaluation.evidence),
                )
            )
        return result

    @staticmethod
    def _hard_pass(checks: Sequence[HardRequirementCheck]) -> bool | None:
        statuses = {item.status for item in checks}
        if HardRequirementStatus.FAILED in statuses:
            return False
        if HardRequirementStatus.UNKNOWN in statuses:
            return None
        return True if statuses else None

    @staticmethod
    def _cap_reasons(
        checks: Sequence[HardRequirementCheck],
        evidence_coverage: Decimal,
    ) -> list[RecommendationCapReason]:
        statuses = {item.status for item in checks}
        reasons: list[RecommendationCapReason] = []
        if HardRequirementStatus.FAILED in statuses:
            reasons.append(RecommendationCapReason.HARD_REQUIREMENT_FAILED)
        if HardRequirementStatus.UNKNOWN in statuses:
            reasons.append(RecommendationCapReason.HARD_REQUIREMENT_UNKNOWN)
        if evidence_coverage < Decimal("0.6"):
            reasons.append(RecommendationCapReason.LOW_EVIDENCE_COVERAGE)
        return reasons

    @staticmethod
    def _recommendation_for_score(score: int) -> ScreeningRecommendation:
        if score >= 85:
            return ScreeningRecommendation.STRONG_RECOMMEND
        if score >= 70:
            return ScreeningRecommendation.RECOMMEND
        if score >= 50:
            return ScreeningRecommendation.REVIEW_REQUIRED
        return ScreeningRecommendation.LOW_MATCH

    def _blocked_result(
        self,
        *,
        hard_pass: bool | None,
        criterion_scores: list[CombinedCriterionScore],
        dimension_scores: list[CombinedDimensionScore],
        semantic_evaluation: ScreeningSemanticEvaluation,
        hard_requirement_checks: Sequence[HardRequirementCheck],
    ) -> CombinedScreeningScoreResult:
        strengths, risks, questions = self._summaries(
            semantic_evaluation,
            hard_requirement_checks,
        )
        return CombinedScreeningScoreResult(
            blocked=True,
            overall_score=None,
            evidence_coverage_rate=0.0,
            recommendation=None,
            recommendation_capped=False,
            cap_reasons=self._cap_reasons(
                hard_requirement_checks,
                Decimal("0"),
            ),
            hard_pass=hard_pass,
            criterion_scores=criterion_scores,
            dimension_scores=dimension_scores,
            strengths=strengths,
            risks=risks,
            pending_questions=questions,
        )

    @staticmethod
    def _summaries(
        evaluation: ScreeningSemanticEvaluation,
        checks: Sequence[HardRequirementCheck],
    ) -> tuple[list[str], list[str], list[str]]:
        strengths = ScreeningScoreService._deduplicate(
            item for score in evaluation.evaluations for item in score.strengths
        )
        risks = ScreeningScoreService._deduplicate(
            item for score in evaluation.evaluations for item in score.gaps
        )
        questions = ScreeningScoreService._deduplicate(
            [
                f"请核对硬性条件：{check.requirement}"
                for check in checks
                if check.status is HardRequirementStatus.UNKNOWN
            ]
            + [
                item
                for score in evaluation.evaluations
                if score.score == "unknown"
                for item in score.gaps
            ]
        )
        return strengths, risks, questions

    @staticmethod
    def _deduplicate(values) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                result.append(value)
        return result

    @staticmethod
    def _rounded_float(value: Decimal) -> float:
        return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


screening_score_service = ScreeningScoreService()


__all__ = [
    "SCREENING_SCORE_VERSION",
    "ScreeningScoreService",
    "screening_score_service",
]
