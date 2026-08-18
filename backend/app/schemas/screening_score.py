from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from app.schemas.screening_rules import (
    RecommendationCapReason,
    ScreeningRecommendation,
)
from app.schemas.screening_rubric import RubricDimension


CriterionKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=1,
        max_length=100,
    ),
]
CombinedRawScore = Literal["unknown"] | Annotated[StrictInt, Field(ge=0, le=10)]


class ScreeningScoreSource(str, Enum):
    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"


class CombinedCriterionScore(BaseModel):
    criterion_key: CriterionKey
    dimension: RubricDimension
    source: ScreeningScoreSource
    raw_score: CombinedRawScore
    adjusted_weight: float = Field(ge=0, le=100)
    earned_points: float = Field(ge=0, le=100)
    evidence_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class CombinedDimensionScore(BaseModel):
    dimension: RubricDimension
    configured_weight: int = Field(ge=0, le=100)
    score_percentage: float = Field(ge=0, le=100)
    evidence_coverage_rate: float = Field(ge=0, le=1)

    model_config = ConfigDict(extra="forbid")


class CombinedScreeningScoreResult(BaseModel):
    blocked: bool
    overall_score: int | None = Field(default=None, ge=0, le=100)
    evidence_coverage_rate: float = Field(ge=0, le=1)
    recommendation: ScreeningRecommendation | None = None
    recommendation_capped: bool
    cap_reasons: list[RecommendationCapReason]
    hard_pass: bool | None = None
    criterion_scores: list[CombinedCriterionScore]
    dimension_scores: list[CombinedDimensionScore]
    strengths: list[str]
    risks: list[str]
    pending_questions: list[str]

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "CombinedCriterionScore",
    "CombinedDimensionScore",
    "CombinedScreeningScoreResult",
    "ScreeningScoreSource",
]
