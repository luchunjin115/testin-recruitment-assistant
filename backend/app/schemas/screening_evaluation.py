from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.experience_period import ExperiencePeriodFactKey


SCREENING_EVALUATION_SCHEMA_VERSION = "2.0"
SCREENING_EVALUATION_MAX_REQUIREMENTS = 30
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
