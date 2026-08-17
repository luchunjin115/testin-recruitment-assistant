from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)

from app.schemas.rebuilt.application import PositiveId


SCREENING_RUBRIC_SCHEMA_VERSION = "1.0"
RUBRIC_SUBCRITERIA_VERSION = "1.0"
RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION = "1.0"
RUBRIC_FAIRNESS_RULES_VERSION = "1.0"


class RubricChangeReasonCode(str, Enum):
    INITIAL_DEFAULT = "initial_default"
    HR_ADJUSTMENT = "hr_adjustment"
    RESTORE_DEFAULT = "restore_default"
    LEGACY_MIGRATION = "legacy_migration"


MustHaveWeight = Annotated[StrictInt, Field(ge=30, le=50)]
WorkExperienceWeight = Annotated[StrictInt, Field(ge=15, le=35)]
ProjectsCapabilityWeight = Annotated[StrictInt, Field(ge=10, le=30)]
PreferredQualificationsWeight = Annotated[StrictInt, Field(ge=0, le=20)]
AdditionalMatchWeight = Annotated[StrictInt, Field(ge=0, le=10)]
ChangeDetail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]


class ScreeningRubricWeights(BaseModel):
    must_have_requirements: MustHaveWeight = 40
    work_experience_relevance: WorkExperienceWeight = 25
    projects_and_capability: ProjectsCapabilityWeight = 20
    preferred_qualifications: PreferredQualificationsWeight = 10
    keywords_and_additional: AdditionalMatchWeight = 5

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_total_weight(self) -> ScreeningRubricWeights:
        total = sum(
            (
                self.must_have_requirements,
                self.work_experience_relevance,
                self.projects_and_capability,
                self.preferred_qualifications,
                self.keywords_and_additional,
            )
        )
        if total != 100:
            raise ValueError("Rubric 五个维度的权重总和必须为 100")
        return self


def default_screening_rubric_weights() -> ScreeningRubricWeights:
    return ScreeningRubricWeights()


class JobScreeningRubricCreate(BaseModel):
    job_id: PositiveId
    weights: ScreeningRubricWeights = Field(default_factory=default_screening_rubric_weights)
    schema_version: Literal["1.0"] = SCREENING_RUBRIC_SCHEMA_VERSION
    subcriteria_version: Literal["1.0"] = RUBRIC_SUBCRITERIA_VERSION
    recommendation_thresholds_version: Literal["1.0"] = (
        RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION
    )
    fairness_rules_version: Literal["1.0"] = RUBRIC_FAIRNESS_RULES_VERSION
    change_reason: RubricChangeReasonCode = RubricChangeReasonCode.INITIAL_DEFAULT
    change_detail: ChangeDetail | None = None
    created_by: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_change_reason(self) -> JobScreeningRubricCreate:
        if (
            self.change_reason is RubricChangeReasonCode.HR_ADJUSTMENT
            and self.change_detail is None
        ):
            raise ValueError("HR 调整 Rubric 时必须填写变更说明")
        return self


class ScreeningRubricUpdateRequest(BaseModel):
    weights: ScreeningRubricWeights | None = None
    restore_defaults: StrictBool = False
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_update_mode(self) -> ScreeningRubricUpdateRequest:
        if self.restore_defaults == (self.weights is not None):
            raise ValueError("必须且只能选择提交新权重或恢复默认权重")
        return self

    def resolved_weights(self) -> ScreeningRubricWeights:
        if self.restore_defaults:
            return default_screening_rubric_weights()
        if self.weights is None:  # pragma: no cover - 已由模型校验保证
            raise ValueError("缺少 Rubric 权重")
        return self.weights


class JobScreeningRubricRead(BaseModel):
    id: PositiveId
    job_id: PositiveId
    version: PositiveId
    weights: ScreeningRubricWeights
    schema_version: Literal["1.0"]
    subcriteria_version: Literal["1.0"]
    recommendation_thresholds_version: Literal["1.0"]
    fairness_rules_version: Literal["1.0"]
    is_current: StrictBool
    change_reason: RubricChangeReasonCode
    change_detail: str | None
    created_by: str | None
    created_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


__all__ = [
    "JobScreeningRubricCreate",
    "JobScreeningRubricRead",
    "RUBRIC_FAIRNESS_RULES_VERSION",
    "RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION",
    "RUBRIC_SUBCRITERIA_VERSION",
    "RubricChangeReasonCode",
    "SCREENING_RUBRIC_SCHEMA_VERSION",
    "ScreeningRubricUpdateRequest",
    "ScreeningRubricWeights",
    "default_screening_rubric_weights",
]
