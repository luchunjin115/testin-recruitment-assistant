from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.experience_period import ExperiencePeriodFactKey
from app.schemas.job_evaluation_plan import (
    EvaluationCriterion,
    RequirementFact,
    V5CriterionItem,
)


SCREENING_EVALUATION_SCHEMA_VERSION = "2.0"
SCREENING_EVALUATION_V5_SCHEMA_VERSION = "5.0"
SCREENING_EVALUATION_MAX_REQUIREMENTS = 512
SCREENING_EVALUATION_V5_MAX_CRITERIA = 30
SCREENING_EVALUATION_MAX_BONUSES = 5
SCREENING_EVALUATION_MAX_QUESTIONS = 5


RequirementKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=160,
        pattern=r"^[a-z0-9][a-z0-9:_-]*$",
    ),
]
ReasonText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
EvidenceQuote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]
EvidenceSection = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CalculationNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
BonusTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
SummaryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=3_000),
]
TradeoffText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]
InterviewQuestion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
RequirementScore = Annotated[int, Field(strict=True, ge=0, le=10)]
BonusScore = Annotated[int, Field(strict=True, ge=7, le=10)]
OverallScore = Annotated[int, Field(strict=True, ge=0, le=100)]


class ScreeningEvidence(BaseModel):
    quote: EvidenceQuote
    section: EvidenceSection | None = None

    model_config = ConfigDict(extra="forbid")


class RequirementAssessment(BaseModel):
    requirement_key: RequirementKey
    score: RequirementScore
    reason: ReasonText
    calculation_note: CalculationNote | None = None
    experience_period_fact_keys: list[ExperiencePeriodFactKey] = Field(
        default_factory=list,
        max_length=100,
    )
    evidence: list[ScreeningEvidence] = Field(max_length=10)

    model_config = ConfigDict(extra="forbid")


class ScreeningEvaluationPlanInput(BaseModel):
    """The immutable 4.0 facts and their display-only criterion grouping."""

    schema_version: Annotated[
        str,
        StringConstraints(pattern=r"^[45]\.0$"),
    ]
    requirement_facts: list[RequirementFact] = Field(
        min_length=1,
        max_length=SCREENING_EVALUATION_MAX_REQUIREMENTS,
    )
    evaluation_criteria: list[EvaluationCriterion] = Field(
        min_length=1,
        max_length=SCREENING_EVALUATION_MAX_REQUIREMENTS,
    )

    model_config = ConfigDict(extra="forbid")


class BonusHighlight(BaseModel):
    title: BonusTitle
    score: BonusScore
    reason: ReasonText
    evidence: list[ScreeningEvidence] = Field(min_length=1, max_length=10)

    model_config = ConfigDict(extra="forbid")


class AIScreeningEvaluationOutput(BaseModel):
    """The exact JSON shape accepted from the model; display_label is excluded."""

    overall_score: OverallScore
    overall_summary: SummaryText
    requirement_assessments: list[RequirementAssessment] = Field(
        max_length=SCREENING_EVALUATION_MAX_REQUIREMENTS
    )
    bonus_highlights: list[BonusHighlight] = Field(
        max_length=SCREENING_EVALUATION_MAX_BONUSES
    )
    tradeoff_reason: TradeoffText | None = None
    interview_questions: list[InterviewQuestion] = Field(
        max_length=SCREENING_EVALUATION_MAX_QUESTIONS
    )

    model_config = ConfigDict(extra="forbid")


class ScreeningEvaluationPlanInputV5(BaseModel):
    """The exact confirmed lightweight plan accepted by the 5.0 evaluator."""

    schema_version: Literal["5.0"]
    criteria: list[V5CriterionItem] = Field(
        min_length=1,
        max_length=SCREENING_EVALUATION_V5_MAX_CRITERIA,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_criterion_ids(self) -> ScreeningEvaluationPlanInputV5:
        criterion_ids = [item.criterion_id for item in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("5.0 评价点 criterion_id 不能重复")
        return self


class CriterionAssessment(BaseModel):
    criterion_id: RequirementKey
    score: RequirementScore
    reason: ReasonText
    calculation_note: CalculationNote | None = None
    experience_period_fact_keys: list[ExperiencePeriodFactKey] = Field(
        default_factory=list,
        max_length=100,
    )
    evidence: list[ScreeningEvidence] = Field(max_length=10)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_score_evidence_shape(self) -> CriterionAssessment:
        if self.score > 0 and not self.evidence:
            raise ValueError("5.0 非零分必须至少包含一条简历证据")
        if self.score == 0:
            if self.evidence:
                raise ValueError("5.0 零分不得附带正向简历证据")
            if "当前简历未发现相关证据" not in self.reason:
                raise ValueError("5.0 零分必须说明当前简历未发现相关证据")
        return self


class V5ReportFinding(BaseModel):
    summary: SummaryText
    criterion_ids: list[RequirementKey] = Field(default_factory=list, max_length=30)
    evidence: list[ScreeningEvidence] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_criterion_ids(self) -> V5ReportFinding:
        if len(self.criterion_ids) != len(set(self.criterion_ids)):
            raise ValueError("报告分区引用的 criterion_id 不能重复")
        return self


class AIScreeningEvaluationV5Output(BaseModel):
    """Strict model-owned JSON. Program-owned labels and criterion snapshots are absent."""

    overall_score: OverallScore
    overall_summary: SummaryText
    criterion_assessments: list[CriterionAssessment] = Field(
        min_length=1,
        max_length=SCREENING_EVALUATION_V5_MAX_CRITERIA,
    )
    strengths: list[V5ReportFinding] = Field(max_length=10)
    gaps: list[V5ReportFinding] = Field(min_length=1, max_length=10)
    risks_or_conflicts: list[V5ReportFinding] = Field(max_length=10)
    missing_info: list[V5ReportFinding] = Field(min_length=1, max_length=10)
    hr_follow_up_questions: list[InterviewQuestion] = Field(min_length=1, max_length=5)

    model_config = ConfigDict(extra="forbid")


class PersistedCriterionAssessmentV5(BaseModel):
    """Program-enriched immutable assessment used by a safely persisted report."""

    criterion: V5CriterionItem
    assessment: CriterionAssessment

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_same_criterion(self) -> PersistedCriterionAssessmentV5:
        if self.criterion.criterion_id != self.assessment.criterion_id:
            raise ValueError("评价结果与评价点快照 ID 不一致")
        return self


class ScreeningEvaluationV5ReportPayload(BaseModel):
    """Complete, validated 5.0 report payload safe for JSONB persistence."""

    overall_score: OverallScore
    display_label: str = Field(min_length=1, max_length=30)
    overall_summary: SummaryText
    criterion_assessments: list[PersistedCriterionAssessmentV5] = Field(
        min_length=1,
        max_length=SCREENING_EVALUATION_V5_MAX_CRITERIA,
    )
    strengths: list[V5ReportFinding] = Field(max_length=10)
    gaps: list[V5ReportFinding] = Field(min_length=1, max_length=10)
    risks_or_conflicts: list[V5ReportFinding] = Field(max_length=10)
    missing_info: list[V5ReportFinding] = Field(min_length=1, max_length=10)
    hr_follow_up_questions: list[InterviewQuestion] = Field(min_length=1, max_length=5)

    model_config = ConfigDict(extra="forbid")
