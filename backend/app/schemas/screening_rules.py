from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.screening_rubric import ScreeningRubricWeights


class ScreeningMatchLevel(str, Enum):
    FULL = "full"
    STRONG = "strong"
    PARTIAL = "partial"
    WEAK = "weak"
    NONE = "none"
    UNKNOWN = "unknown"


class HardRequirementStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ScreeningRecommendation(str, Enum):
    STRONG_RECOMMEND = "strong_recommend"
    RECOMMEND = "recommend"
    REVIEW_REQUIRED = "review_required"
    LOW_MATCH = "low_match"


class ScreeningDimension(str, Enum):
    MUST_HAVE_REQUIREMENTS = "must_have_requirements"
    WORK_EXPERIENCE_RELEVANCE = "work_experience_relevance"
    PROJECTS_AND_CAPABILITY = "projects_and_capability"
    PREFERRED_QUALIFICATIONS = "preferred_qualifications"
    KEYWORDS_AND_ADDITIONAL = "keywords_and_additional"


class ScreeningCriterion(str, Enum):
    REQUIRED_SKILLS = "required_skills"
    MINIMUM_WORK_YEARS = "minimum_work_years"
    EDUCATION_REQUIREMENT = "education_requirement"
    REQUIRED_EXPERIENCES = "required_experiences"
    RESPONSIBILITY_RELEVANCE = "responsibility_relevance"
    WORK_EXPERIENCE_QUALITY = "work_experience_quality"
    PROJECT_RELEVANCE = "project_relevance"
    CAPABILITY_DEPTH = "capability_depth"
    VERIFIED_OUTCOMES = "verified_outcomes"
    PREFERRED_SKILLS = "preferred_skills"
    PREFERRED_EXPERIENCES = "preferred_experiences"
    KEYWORDS = "keywords"
    ADDITIONAL_REQUIREMENTS = "additional_requirements"


class RecommendationCapReason(str, Enum):
    HARD_REQUIREMENT_FAILED = "hard_requirement_failed"
    HARD_REQUIREMENT_UNKNOWN = "hard_requirement_unknown"
    LOW_EVIDENCE_COVERAGE = "low_evidence_coverage"


EvidenceText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
RequirementText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
SkillText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
EducationText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]


class RequiredExperienceAssessment(BaseModel):
    requirement: RequirementText
    status: HardRequirementStatus
    evidence: list[EvidenceText] = Field(default_factory=list, max_length=50)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_explicit_evidence(self) -> RequiredExperienceAssessment:
        if self.status is not HardRequirementStatus.UNKNOWN and not self.evidence:
            raise ValueError("必备经历的明确通过或失败必须提供证据")
        return self


class DeterministicCandidateFacts(BaseModel):
    work_years: StrictInt | None = Field(default=None, ge=0, le=80)
    education_level: EducationText | None = None
    skills: list[SkillText] = Field(default_factory=list, max_length=500)
    skills_evidence_complete: StrictBool = False
    required_experiences: list[RequiredExperienceAssessment] = Field(
        default_factory=list,
        max_length=100,
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("skills", mode="after")
    @classmethod
    def deduplicate_skills(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for skill in value:
            key = skill.casefold()
            if key not in seen:
                seen.add(key)
                result.append(skill)
        return result

    @model_validator(mode="after")
    def reject_duplicate_experience_requirements(self) -> DeterministicCandidateFacts:
        normalized = [item.requirement.casefold() for item in self.required_experiences]
        if len(normalized) != len(set(normalized)):
            raise ValueError("必备经历判断不能重复提交同一要求")
        return self


class HardRequirementCheck(BaseModel):
    criterion: ScreeningCriterion
    requirement: RequirementText
    status: HardRequirementStatus
    evidence: list[EvidenceText] = Field(default_factory=list, max_length=50)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_explicit_evidence(self) -> HardRequirementCheck:
        if self.status is not HardRequirementStatus.UNKNOWN and not self.evidence:
            raise ValueError("硬性条件的明确通过或失败必须提供证据")
        return self


class CriterionMatchInput(BaseModel):
    criterion: ScreeningCriterion
    match_level: ScreeningMatchLevel
    evidence: list[EvidenceText] = Field(default_factory=list, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_evidence_for_known_level(self) -> CriterionMatchInput:
        if self.match_level is not ScreeningMatchLevel.UNKNOWN and not self.evidence:
            raise ValueError("非 unknown 评分档位必须提供可核对证据")
        return self


class HardRequirementEvaluation(BaseModel):
    checks: list[HardRequirementCheck]
    criterion_matches: list[CriterionMatchInput]

    model_config = ConfigDict(extra="forbid")


class ScreeningRuleScoreRequest(BaseModel):
    weights: ScreeningRubricWeights = Field(default_factory=ScreeningRubricWeights)
    criterion_matches: list[CriterionMatchInput] = Field(max_length=13)
    hard_requirement_checks: list[HardRequirementCheck] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_duplicate_criteria(self) -> ScreeningRuleScoreRequest:
        criteria = [item.criterion for item in self.criterion_matches]
        if len(criteria) != len(set(criteria)):
            raise ValueError("同一评分子项只能提交一次")
        return self


class CriterionScore(BaseModel):
    criterion: ScreeningCriterion
    match_level: ScreeningMatchLevel
    adjusted_weight: float = Field(ge=0, le=100)
    earned_points: float = Field(ge=0, le=100)
    evidence_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class DimensionScore(BaseModel):
    dimension: ScreeningDimension
    configured_weight: int = Field(ge=0, le=100)
    score_percentage: float = Field(ge=0, le=100)
    evidence_coverage_rate: float = Field(ge=0, le=1)

    model_config = ConfigDict(extra="forbid")


class ScreeningRuleScoreResult(BaseModel):
    blocked: StrictBool
    overall_score: int | None = Field(default=None, ge=0, le=100)
    evidence_coverage_rate: float = Field(ge=0, le=1)
    recommendation: ScreeningRecommendation | None = None
    recommendation_capped: StrictBool
    cap_reasons: list[RecommendationCapReason]
    criterion_scores: list[CriterionScore]
    dimension_scores: list[DimensionScore]

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "CriterionMatchInput",
    "CriterionScore",
    "DeterministicCandidateFacts",
    "DimensionScore",
    "HardRequirementCheck",
    "HardRequirementEvaluation",
    "HardRequirementStatus",
    "RecommendationCapReason",
    "RequiredExperienceAssessment",
    "ScreeningCriterion",
    "ScreeningDimension",
    "ScreeningMatchLevel",
    "ScreeningRecommendation",
    "ScreeningRuleScoreRequest",
    "ScreeningRuleScoreResult",
]
