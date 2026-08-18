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
    field_validator,
    model_validator,
)

from app.schemas.application import PositiveId


SCREENING_RUBRIC_SCHEMA_VERSION = "2.0"
RUBRIC_SUBCRITERIA_VERSION = "2.0"
RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION = "1.0"
RUBRIC_FAIRNESS_RULES_VERSION = "1.0"
RUBRIC_ITEMS_SCHEMA_VERSION = "2.0"
RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION = "1.0"


FAIRNESS_PROHIBITED_TERMS = (
    "年龄",
    "性别",
    "民族",
    "婚姻",
    "已婚",
    "未婚",
    "婚育",
    "生育",
    "照片",
    "籍贯",
    "985",
    "211",
    "双一流",
    "学校声誉",
    "名校",
    "age",
    "gender",
    "race",
    "ethnicity",
    "marital",
    "married",
    "pregnancy",
    "birthplace",
    "prestigious university",
)


class RubricChangeReasonCode(str, Enum):
    INITIAL_DEFAULT = "initial_default"
    HR_ADJUSTMENT = "hr_adjustment"
    RESTORE_DEFAULT = "restore_default"
    TEMPLATE_DRAFT = "template_draft"
    DRAFT_UPDATED = "draft_updated"
    DRAFT_PUBLISHED = "draft_published"
    DRAFT_ABANDONED = "draft_abandoned"
    JOB_RECONFIRMED = "job_reconfirmed"
    AI_GENERATED_DRAFT = "ai_generated_draft"


class RubricTemplateKey(str, Enum):
    STANDARD = "standard"
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"


class RubricSource(str, Enum):
    STANDARD_TEMPLATE = "standard_template"
    TECHNICAL_TEMPLATE = "technical_template"
    NON_TECHNICAL_TEMPLATE = "non_technical_template"
    AI_GENERATED = "ai_generated"
    HR_MANUAL = "hr_manual"


class RubricLifecycleStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ABANDONED = "abandoned"


class RubricCriterionSource(str, Enum):
    TEMPLATE = "template"
    AI_GENERATED = "ai_generated"
    HR_MANUAL = "hr_manual"


class RubricDimension(str, Enum):
    MUST_HAVE_REQUIREMENTS = "must_have_requirements"
    WORK_EXPERIENCE_RELEVANCE = "work_experience_relevance"
    PROJECTS_AND_CAPABILITY = "projects_and_capability"
    PREFERRED_QUALIFICATIONS = "preferred_qualifications"
    KEYWORDS_AND_ADDITIONAL = "keywords_and_additional"


MustHaveWeight = Annotated[StrictInt, Field(ge=30, le=50)]
WorkExperienceWeight = Annotated[StrictInt, Field(ge=15, le=35)]
ProjectsCapabilityWeight = Annotated[StrictInt, Field(ge=10, le=30)]
PreferredQualificationsWeight = Annotated[StrictInt, Field(ge=0, le=20)]
AdditionalMatchWeight = Annotated[StrictInt, Field(ge=0, le=10)]
ChangeDetail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
CriterionKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]
CriterionName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
CriterionDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
CriterionAnchor = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
SuggestedShare = Annotated[StrictInt, Field(ge=1, le=100)]
JobFingerprint = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    ),
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


def _reject_duplicate_criteria(items: list[SemanticRubricCriterion]) -> None:
    keys = [item.key.casefold() for item in items]
    names = [item.name.casefold() for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("Rubric 语义评分项 key 不能重复")
    if len(names) != len(set(names)):
        raise ValueError("Rubric 语义评分项名称不能重复")


class SemanticRubricCriterion(BaseModel):
    key: CriterionKey
    name: CriterionName
    description: CriterionDescription
    dimension: RubricDimension
    max_score: Literal[10] = 10
    suggested_share: SuggestedShare
    high_score_anchor: CriterionAnchor
    mid_score_anchor: CriterionAnchor
    low_score_anchor: CriterionAnchor
    source: RubricCriterionSource

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "name",
        "description",
        "high_score_anchor",
        "mid_score_anchor",
        "low_score_anchor",
    )
    @classmethod
    def reject_unfair_criteria(cls, value: str) -> str:
        normalized = value.casefold()
        if any(term.casefold() in normalized for term in FAIRNESS_PROHIBITED_TERMS):
            raise ValueError("Rubric 评分项包含公平性禁止内容")
        return value


class ManualSemanticCriterionInput(BaseModel):
    name: CriterionName
    description: CriterionDescription
    dimension: RubricDimension
    suggested_share: SuggestedShare
    high_score_anchor: CriterionAnchor
    mid_score_anchor: CriterionAnchor
    low_score_anchor: CriterionAnchor

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "name",
        "description",
        "high_score_anchor",
        "mid_score_anchor",
        "low_score_anchor",
    )
    @classmethod
    def reject_unfair_criteria(cls, value: str) -> str:
        return SemanticRubricCriterion.reject_unfair_criteria(value)


class ScreeningRubricDraftContent(BaseModel):
    schema_version: Literal["2.0"] = RUBRIC_ITEMS_SCHEMA_VERSION
    source: RubricSource
    template_key: RubricTemplateKey | None = None
    job_fingerprint: JobFingerprint
    weights: ScreeningRubricWeights = Field(default_factory=ScreeningRubricWeights)
    semantic_items: list[SemanticRubricCriterion] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_duplicate_items(self) -> ScreeningRubricDraftContent:
        _reject_duplicate_criteria(self.semantic_items)
        return self


class ScreeningRubricPublishContent(ScreeningRubricDraftContent):
    semantic_items: list[SemanticRubricCriterion] = Field(min_length=4, max_length=10)


class ScreeningRubricTemplateDraftRequest(BaseModel):
    template_key: RubricTemplateKey
    replace_existing: StrictBool = False
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricGenerateRequest(BaseModel):
    template_key: RubricTemplateKey = RubricTemplateKey.STANDARD
    replace_existing: StrictBool = False
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricItemAssistRequest(BaseModel):
    expected_job_fingerprint: JobFingerprint
    item: ManualSemanticCriterionInput

    model_config = ConfigDict(extra="forbid")


class RubricModelMetadata(BaseModel):
    model: Annotated[
        str,
        StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
    ]
    prompt_version: Annotated[
        str,
        StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
    ]
    schema_version: Annotated[
        str,
        StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=20),
    ]
    input_tokens: StrictInt | None = Field(default=None, ge=0)
    output_tokens: StrictInt | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricItemAssistResponse(BaseModel):
    job_fingerprint: JobFingerprint
    suggestion: ManualSemanticCriterionInput
    metadata: RubricModelMetadata

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricDraftUpdateRequest(BaseModel):
    expected_job_fingerprint: JobFingerprint
    weights: ScreeningRubricWeights | None = None
    semantic_items: list[SemanticRubricCriterion] | None = Field(
        default=None,
        max_length=10,
    )
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_content_change(self) -> ScreeningRubricDraftUpdateRequest:
        if self.weights is None and self.semantic_items is None:
            raise ValueError("Rubric 草稿更新必须包含权重或语义评分项")
        if self.semantic_items is not None:
            _reject_duplicate_criteria(self.semantic_items)
        return self


class ScreeningRubricPublishRequest(BaseModel):
    expected_job_fingerprint: JobFingerprint
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricAbandonRequest(BaseModel):
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")


class ScreeningRubricReconfirmRequest(BaseModel):
    expected_job_fingerprint: JobFingerprint
    change_detail: ChangeDetail

    model_config = ConfigDict(extra="forbid")


class RubricGenerationSuggestion(BaseModel):
    schema_version: Literal["1.0"] = RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION
    template_key: RubricTemplateKey
    rationale: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            strict=True,
            min_length=1,
            max_length=2_000,
        ),
    ]
    semantic_items: list[SemanticRubricCriterion] = Field(min_length=4, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @field_validator("semantic_items")
    @classmethod
    def require_ai_generated_source(
        cls,
        value: list[SemanticRubricCriterion],
    ) -> list[SemanticRubricCriterion]:
        if any(item.source is not RubricCriterionSource.AI_GENERATED for item in value):
            raise ValueError("AI 生成结果中的评分项 source 必须为 ai_generated")
        return value

    @model_validator(mode="after")
    def reject_duplicate_items(self) -> RubricGenerationSuggestion:
        _reject_duplicate_criteria(self.semantic_items)
        return self


class JobScreeningRubricCreate(BaseModel):
    job_id: PositiveId
    weights: ScreeningRubricWeights = Field(default_factory=default_screening_rubric_weights)
    schema_version: Literal["2.0"] = SCREENING_RUBRIC_SCHEMA_VERSION
    subcriteria_version: Literal["2.0"] = RUBRIC_SUBCRITERIA_VERSION
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
    schema_version: Literal["2.0"]
    subcriteria_version: Literal["2.0"]
    recommendation_thresholds_version: Literal["1.0"]
    fairness_rules_version: Literal["1.0"]
    is_current: StrictBool
    source: RubricSource
    template_key: RubricTemplateKey | None
    status: RubricLifecycleStatus
    semantic_items: list[SemanticRubricCriterion] = Field(max_length=10)
    job_fingerprint: JobFingerprint | None
    is_stale: StrictBool
    stale_at: AwareDatetime | None
    stale_reason: str | None
    generation_metadata: dict | None
    change_reason: RubricChangeReasonCode
    change_detail: str | None
    created_by: str | None
    confirmed_by: str | None
    confirmed_at: AwareDatetime | None
    abandoned_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


__all__ = [
    "FAIRNESS_PROHIBITED_TERMS",
    "JobScreeningRubricCreate",
    "JobScreeningRubricRead",
    "ManualSemanticCriterionInput",
    "RUBRIC_FAIRNESS_RULES_VERSION",
    "RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION",
    "RUBRIC_ITEMS_SCHEMA_VERSION",
    "RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION",
    "RUBRIC_SUBCRITERIA_VERSION",
    "RubricChangeReasonCode",
    "RubricCriterionSource",
    "RubricDimension",
    "RubricGenerationSuggestion",
    "RubricLifecycleStatus",
    "RubricModelMetadata",
    "RubricSource",
    "RubricTemplateKey",
    "SCREENING_RUBRIC_SCHEMA_VERSION",
    "ScreeningRubricDraftContent",
    "ScreeningRubricDraftUpdateRequest",
    "ScreeningRubricGenerateRequest",
    "ScreeningRubricItemAssistRequest",
    "ScreeningRubricItemAssistResponse",
    "ScreeningRubricAbandonRequest",
    "ScreeningRubricPublishContent",
    "ScreeningRubricPublishRequest",
    "ScreeningRubricReconfirmRequest",
    "ScreeningRubricTemplateDraftRequest",
    "ScreeningRubricUpdateRequest",
    "ScreeningRubricWeights",
    "SemanticRubricCriterion",
    "default_screening_rubric_weights",
]
