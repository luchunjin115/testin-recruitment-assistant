from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.rebuilt.job import EducationRequirement, JobRequirementsV1
from app.schemas.rebuilt.screening_rules import (
    CriterionMatchInput,
    CriterionScore,
    DeterministicCandidateFacts,
    DimensionScore,
    HardRequirementCheck,
    HardRequirementEvaluation,
    HardRequirementStatus,
    RecommendationCapReason,
    RequiredExperienceAssessment,
    ScreeningCriterion,
    ScreeningDimension,
    ScreeningMatchLevel,
    ScreeningRecommendation,
    ScreeningRuleScoreRequest,
    ScreeningRuleScoreResult,
)


SCREENING_RULES_VERSION = "1.0"

_MATCH_RATIOS = {
    ScreeningMatchLevel.FULL: Decimal("1"),
    ScreeningMatchLevel.STRONG: Decimal("0.8"),
    ScreeningMatchLevel.PARTIAL: Decimal("0.5"),
    ScreeningMatchLevel.WEAK: Decimal("0.2"),
    ScreeningMatchLevel.NONE: Decimal("0"),
    ScreeningMatchLevel.UNKNOWN: Decimal("0"),
}

_CRITERION_CONFIG = {
    ScreeningCriterion.REQUIRED_SKILLS: (
        ScreeningDimension.MUST_HAVE_REQUIREMENTS,
        20,
    ),
    ScreeningCriterion.MINIMUM_WORK_YEARS: (
        ScreeningDimension.MUST_HAVE_REQUIREMENTS,
        8,
    ),
    ScreeningCriterion.EDUCATION_REQUIREMENT: (
        ScreeningDimension.MUST_HAVE_REQUIREMENTS,
        4,
    ),
    ScreeningCriterion.REQUIRED_EXPERIENCES: (
        ScreeningDimension.MUST_HAVE_REQUIREMENTS,
        8,
    ),
    ScreeningCriterion.RESPONSIBILITY_RELEVANCE: (
        ScreeningDimension.WORK_EXPERIENCE_RELEVANCE,
        15,
    ),
    ScreeningCriterion.WORK_EXPERIENCE_QUALITY: (
        ScreeningDimension.WORK_EXPERIENCE_RELEVANCE,
        10,
    ),
    ScreeningCriterion.PROJECT_RELEVANCE: (
        ScreeningDimension.PROJECTS_AND_CAPABILITY,
        10,
    ),
    ScreeningCriterion.CAPABILITY_DEPTH: (
        ScreeningDimension.PROJECTS_AND_CAPABILITY,
        6,
    ),
    ScreeningCriterion.VERIFIED_OUTCOMES: (
        ScreeningDimension.PROJECTS_AND_CAPABILITY,
        4,
    ),
    ScreeningCriterion.PREFERRED_SKILLS: (
        ScreeningDimension.PREFERRED_QUALIFICATIONS,
        5,
    ),
    ScreeningCriterion.PREFERRED_EXPERIENCES: (
        ScreeningDimension.PREFERRED_QUALIFICATIONS,
        5,
    ),
    ScreeningCriterion.KEYWORDS: (
        ScreeningDimension.KEYWORDS_AND_ADDITIONAL,
        2,
    ),
    ScreeningCriterion.ADDITIONAL_REQUIREMENTS: (
        ScreeningDimension.KEYWORDS_AND_ADDITIONAL,
        3,
    ),
}

_HARD_CRITERIA = frozenset(
    {
        ScreeningCriterion.REQUIRED_SKILLS,
        ScreeningCriterion.MINIMUM_WORK_YEARS,
        ScreeningCriterion.EDUCATION_REQUIREMENT,
        ScreeningCriterion.REQUIRED_EXPERIENCES,
    }
)

_SKILL_ALIAS_GROUPS = {
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "nodejs": {"node", "nodejs", "node.js"},
    "react": {"react", "reactjs", "react.js"},
    "vue": {"vue", "vuejs", "vue.js"},
    "postgresql": {"postgres", "postgresql", "pgsql"},
    "kubernetes": {"kubernetes", "k8s"},
    "golang": {"go", "golang"},
    "csharp": {"c#", "csharp", "c sharp"},
    "dotnet": {".net", "dotnet", "dot net"},
}

_EDUCATION_RANKS = {
    EducationRequirement.NONE: 0,
    EducationRequirement.ASSOCIATE_OR_ABOVE: 1,
    EducationRequirement.BACHELOR_OR_ABOVE: 2,
    EducationRequirement.MASTER_OR_ABOVE: 3,
    EducationRequirement.DOCTORATE: 4,
}


def _compact_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[\s._\-/]+", "", normalized)


_SKILL_ALIASES = {
    _compact_text(alias): canonical
    for canonical, aliases in _SKILL_ALIAS_GROUPS.items()
    for alias in aliases
}


class ScreeningRuleService:
    def normalize_skill(self, value: str) -> str:
        compact = _compact_text(value)
        return _SKILL_ALIASES.get(compact, compact)

    def evaluate_hard_requirements(
        self,
        requirements: JobRequirementsV1,
        candidate: DeterministicCandidateFacts,
    ) -> HardRequirementEvaluation:
        checks: list[HardRequirementCheck] = []
        matches: list[CriterionMatchInput] = []

        skill_checks = self._evaluate_required_skills(requirements, candidate)
        self._append_criterion_result(
            checks,
            matches,
            ScreeningCriterion.REQUIRED_SKILLS,
            skill_checks,
        )

        year_checks = self._evaluate_minimum_work_years(requirements, candidate)
        self._append_criterion_result(
            checks,
            matches,
            ScreeningCriterion.MINIMUM_WORK_YEARS,
            year_checks,
        )

        education_checks = self._evaluate_education(requirements, candidate)
        self._append_criterion_result(
            checks,
            matches,
            ScreeningCriterion.EDUCATION_REQUIREMENT,
            education_checks,
        )

        experience_checks = self._evaluate_required_experiences(
            requirements,
            candidate,
        )
        self._append_criterion_result(
            checks,
            matches,
            ScreeningCriterion.REQUIRED_EXPERIENCES,
            experience_checks,
        )
        return HardRequirementEvaluation(
            checks=checks,
            criterion_matches=matches,
        )

    def score(self, data: ScreeningRuleScoreRequest) -> ScreeningRuleScoreResult:
        matches_by_dimension: dict[
            ScreeningDimension,
            list[CriterionMatchInput],
        ] = defaultdict(list)
        for match in data.criterion_matches:
            dimension, _ = _CRITERION_CONFIG[match.criterion]
            matches_by_dimension[dimension].append(match)

        criterion_scores: list[CriterionScore] = []
        dimension_scores: list[DimensionScore] = []
        total_effective_weight = Decimal("0")
        total_earned_points = Decimal("0")
        total_evidence_weight = Decimal("0")

        for dimension in ScreeningDimension:
            matches = matches_by_dimension.get(dimension, [])
            if not matches:
                continue
            configured_weight = Decimal(str(getattr(data.weights, dimension.value)))
            if configured_weight == 0:
                continue
            active_base_weight = Decimal(
                sum(_CRITERION_CONFIG[item.criterion][1] for item in matches)
            )
            dimension_earned = Decimal("0")
            dimension_evidence_weight = Decimal("0")

            for match in matches:
                base_weight = Decimal(str(_CRITERION_CONFIG[match.criterion][1]))
                adjusted_weight = configured_weight * base_weight / active_base_weight
                earned_points = adjusted_weight * _MATCH_RATIOS[match.match_level]
                if match.match_level is not ScreeningMatchLevel.UNKNOWN:
                    dimension_evidence_weight += adjusted_weight
                dimension_earned += earned_points
                criterion_scores.append(
                    CriterionScore(
                        criterion=match.criterion,
                        match_level=match.match_level,
                        adjusted_weight=self._rounded_float(adjusted_weight),
                        earned_points=self._rounded_float(earned_points),
                        evidence_count=len(match.evidence),
                    )
                )

            total_effective_weight += configured_weight
            total_earned_points += dimension_earned
            total_evidence_weight += dimension_evidence_weight
            dimension_scores.append(
                DimensionScore(
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

        if total_effective_weight == 0:
            return self._blocked_result(criterion_scores, dimension_scores, [])

        evidence_coverage = total_evidence_weight / total_effective_weight
        cap_reasons = self._cap_reasons(data, evidence_coverage)
        if total_evidence_weight == 0:
            return self._blocked_result(
                criterion_scores,
                dimension_scores,
                cap_reasons,
            )

        raw_score = total_earned_points / total_effective_weight * Decimal("100")
        overall_score = int(raw_score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        base_recommendation = self._recommendation_for_score(overall_score)
        recommendation = base_recommendation
        if cap_reasons and base_recommendation in {
            ScreeningRecommendation.STRONG_RECOMMEND,
            ScreeningRecommendation.RECOMMEND,
        }:
            recommendation = ScreeningRecommendation.REVIEW_REQUIRED

        return ScreeningRuleScoreResult(
            blocked=False,
            overall_score=overall_score,
            evidence_coverage_rate=self._rounded_float(evidence_coverage),
            recommendation=recommendation,
            recommendation_capped=(recommendation is not base_recommendation),
            cap_reasons=cap_reasons,
            criterion_scores=criterion_scores,
            dimension_scores=dimension_scores,
        )

    def _evaluate_required_skills(
        self,
        requirements: JobRequirementsV1,
        candidate: DeterministicCandidateFacts,
    ) -> list[HardRequirementCheck]:
        candidate_skills = {
            self.normalize_skill(skill): skill for skill in candidate.skills
        }
        checks: list[HardRequirementCheck] = []
        for required_skill in requirements.required_skills:
            normalized = self.normalize_skill(required_skill)
            matched_skill = candidate_skills.get(normalized)
            if matched_skill is not None:
                status = HardRequirementStatus.PASSED
                evidence = [f"已确认技能：{matched_skill}"]
            elif candidate.skills_evidence_complete:
                status = HardRequirementStatus.FAILED
                evidence = ["HR 已确认的完整技能清单中未包含该技能"]
            else:
                status = HardRequirementStatus.UNKNOWN
                evidence = []
            checks.append(
                HardRequirementCheck(
                    criterion=ScreeningCriterion.REQUIRED_SKILLS,
                    requirement=required_skill,
                    status=status,
                    evidence=evidence,
                )
            )
        return checks

    @staticmethod
    def _evaluate_minimum_work_years(
        requirements: JobRequirementsV1,
        candidate: DeterministicCandidateFacts,
    ) -> list[HardRequirementCheck]:
        required_years = requirements.minimum_work_years
        if required_years in {None, 0}:
            return []
        if candidate.work_years is None:
            status = HardRequirementStatus.UNKNOWN
            evidence: list[str] = []
        elif candidate.work_years >= required_years:
            status = HardRequirementStatus.PASSED
            evidence = [f"已确认工作年限：{candidate.work_years} 年"]
        else:
            status = HardRequirementStatus.FAILED
            evidence = [f"已确认工作年限：{candidate.work_years} 年"]
        return [
            HardRequirementCheck(
                criterion=ScreeningCriterion.MINIMUM_WORK_YEARS,
                requirement=f"至少 {required_years} 年工作经验",
                status=status,
                evidence=evidence,
            )
        ]

    def _evaluate_education(
        self,
        requirements: JobRequirementsV1,
        candidate: DeterministicCandidateFacts,
    ) -> list[HardRequirementCheck]:
        requirement = requirements.education_requirement
        if requirement in {None, EducationRequirement.NONE}:
            return []
        candidate_rank = self._education_rank(candidate.education_level)
        required_rank = _EDUCATION_RANKS[requirement]
        if candidate_rank is None:
            status = HardRequirementStatus.UNKNOWN
            evidence: list[str] = []
        elif candidate_rank >= required_rank:
            status = HardRequirementStatus.PASSED
            evidence = [f"已确认学历层级：{candidate.education_level}"]
        else:
            status = HardRequirementStatus.FAILED
            evidence = [f"已确认学历层级：{candidate.education_level}"]
        return [
            HardRequirementCheck(
                criterion=ScreeningCriterion.EDUCATION_REQUIREMENT,
                requirement=requirement.value,
                status=status,
                evidence=evidence,
            )
        ]

    @staticmethod
    def _evaluate_required_experiences(
        requirements: JobRequirementsV1,
        candidate: DeterministicCandidateFacts,
    ) -> list[HardRequirementCheck]:
        normalized_assessments: dict[str, RequiredExperienceAssessment] = {}
        for assessment in candidate.required_experiences:
            key = _compact_text(assessment.requirement)
            if key in normalized_assessments:
                raise ValueError("必备经历判断不能重复提交同一要求")
            normalized_assessments[key] = assessment

        requirement_keys = {
            _compact_text(requirement) for requirement in requirements.required_experiences
        }
        unexpected = set(normalized_assessments) - requirement_keys
        if unexpected:
            raise ValueError("提交了岗位未定义的必备经历判断")

        checks: list[HardRequirementCheck] = []
        for requirement in requirements.required_experiences:
            assessment = normalized_assessments.get(_compact_text(requirement))
            if assessment is None:
                status = HardRequirementStatus.UNKNOWN
                evidence: list[str] = []
            else:
                status = assessment.status
                evidence = assessment.evidence
            checks.append(
                HardRequirementCheck(
                    criterion=ScreeningCriterion.REQUIRED_EXPERIENCES,
                    requirement=requirement,
                    status=status,
                    evidence=evidence,
                )
            )
        return checks

    @staticmethod
    def _append_criterion_result(
        checks: list[HardRequirementCheck],
        matches: list[CriterionMatchInput],
        criterion: ScreeningCriterion,
        new_checks: list[HardRequirementCheck],
    ) -> None:
        if not new_checks:
            return
        checks.extend(new_checks)
        statuses = {item.status for item in new_checks}
        if HardRequirementStatus.FAILED in statuses:
            match_level = ScreeningMatchLevel.NONE
        elif HardRequirementStatus.UNKNOWN in statuses:
            match_level = ScreeningMatchLevel.UNKNOWN
        else:
            match_level = ScreeningMatchLevel.FULL
        matches.append(
            CriterionMatchInput(
                criterion=criterion,
                match_level=match_level,
                evidence=[
                    evidence
                    for check in new_checks
                    for evidence in check.evidence
                ],
            )
        )

    @staticmethod
    def _education_rank(value: str | None) -> int | None:
        if value is None:
            return None
        normalized = unicodedata.normalize("NFKC", value).casefold().strip()
        if any(token in normalized for token in ("博士", "doctor", "phd", "ph.d")):
            return 4
        if any(token in normalized for token in ("硕士", "master", "mba")):
            return 3
        if any(token in normalized for token in ("本科", "学士", "bachelor")):
            return 2
        if any(token in normalized for token in ("大专", "专科", "associate")):
            return 1
        return None

    @staticmethod
    def _cap_reasons(
        data: ScreeningRuleScoreRequest,
        evidence_coverage: Decimal,
    ) -> list[RecommendationCapReason]:
        statuses = {check.status for check in data.hard_requirement_checks}
        hard_matches = {
            match.match_level
            for match in data.criterion_matches
            if match.criterion in _HARD_CRITERIA
        }
        reasons: list[RecommendationCapReason] = []
        if (
            HardRequirementStatus.FAILED in statuses
            or ScreeningMatchLevel.NONE in hard_matches
        ):
            reasons.append(RecommendationCapReason.HARD_REQUIREMENT_FAILED)
        if (
            HardRequirementStatus.UNKNOWN in statuses
            or ScreeningMatchLevel.UNKNOWN in hard_matches
        ):
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

    @staticmethod
    def _blocked_result(
        criterion_scores: list[CriterionScore],
        dimension_scores: list[DimensionScore],
        cap_reasons: list[RecommendationCapReason],
    ) -> ScreeningRuleScoreResult:
        return ScreeningRuleScoreResult(
            blocked=True,
            overall_score=None,
            evidence_coverage_rate=0.0,
            recommendation=None,
            recommendation_capped=False,
            cap_reasons=cap_reasons,
            criterion_scores=criterion_scores,
            dimension_scores=dimension_scores,
        )

    @staticmethod
    def _rounded_float(value: Decimal) -> float:
        return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


screening_rule_service = ScreeningRuleService()


__all__ = [
    "SCREENING_RULES_VERSION",
    "ScreeningRuleService",
    "screening_rule_service",
]
