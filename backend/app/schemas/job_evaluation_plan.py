from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


JOB_EVALUATION_PLAN_SCHEMA_VERSION = "2.0"
JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION = "2.0"
JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION = "jd_extraction_v2"
JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION = "jd_source_units_v1"
JOB_EVALUATION_PLAN_MAX_ITEMS = 30
JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS = 100


class LegacyEvaluationPlanEducationRequirement(str, Enum):
    NONE = "none"
    ASSOCIATE_OR_ABOVE = "associate_or_above"
    BACHELOR_OR_ABOVE = "bachelor_or_above"
    MASTER_OR_ABOVE = "master_or_above"
    DOCTORATE = "doctorate"


LegacyShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
LegacyLongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
LegacyMinimumWorkYears = Annotated[StrictInt, Field(ge=0, le=80)]


class LegacyEvaluationPlanRequirements(BaseModel):
    """Frozen Stage 7 read model; it is not accepted by the Job API."""

    schema_version: Literal["1.0"]
    responsibilities: list[LegacyLongText] = Field(max_length=50)
    required_skills: list[LegacyShortText] = Field(max_length=100)
    preferred_skills: list[LegacyShortText] = Field(max_length=100)
    minimum_work_years: LegacyMinimumWorkYears | None
    education_requirement: LegacyEvaluationPlanEducationRequirement | None
    required_experiences: list[LegacyLongText] = Field(max_length=50)
    preferred_experiences: list[LegacyLongText] = Field(max_length=50)
    keywords: list[LegacyShortText] = Field(max_length=100)
    additional_requirements: list[LegacyLongText] = Field(max_length=50)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "responsibilities",
        "required_skills",
        "preferred_skills",
        "required_experiences",
        "preferred_experiences",
        "keywords",
        "additional_requirements",
        mode="before",
    )
    @classmethod
    def normalize_text_lists(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        normalized: list[Any] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                normalized.append(item)
                continue
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized


class JobEvaluationPlanStatus(str, Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    OUTDATED = "outdated"


class EvaluationItemCategory(str, Enum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    RESPONSIBILITY = "responsibility"
    EDUCATION = "education"
    OTHER = "other"


class EvaluationItemPriority(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    GENERAL = "general"


class EvaluationItemSourceType(str, Enum):
    STRUCTURED = "structured"
    AI_EXTRACTED = "ai_extracted"


class JobEvaluationPlanWarning(str, Enum):
    LIMITED_BASIS = "limited_basis"


ItemKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=160,
        pattern=r"^[a-z0-9][a-z0-9:_-]*$",
    ),
]
ItemTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
SourceField = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=160,
        pattern=r"^[a-z][a-z0-9_.]*$",
    ),
]
SourceQuote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]
VersionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Fingerprint = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]
ErrorCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    ),
]
SafeErrorMessage = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
SourceId = Annotated[
    str,
    StringConstraints(pattern=r"^description:\d{4}$"),
]


class JobEvaluationItem(BaseModel):
    key: ItemKey
    title: ItemTitle
    category: EvaluationItemCategory
    priority: EvaluationItemPriority
    source_type: EvaluationItemSourceType
    source_field: SourceField | None = None
    source_quote: SourceQuote | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_source_trace(self) -> JobEvaluationItem:
        if self.source_type is EvaluationItemSourceType.STRUCTURED:
            if self.source_field is None:
                raise ValueError("结构化评价事项必须包含 source_field")
        elif self.source_quote is None:
            raise ValueError("AI 拆解评价事项必须包含 source_quote")
        return self


class StructuredFieldCoverage(BaseModel):
    source_field: SourceField
    source_value_count: int = Field(ge=0, le=500)
    item_keys: list[ItemKey] = Field(max_length=500)

    model_config = ConfigDict(extra="forbid")


class StructuredCoverageResult(BaseModel):
    source_schema_version: VersionText
    fields: list[StructuredFieldCoverage] = Field(max_length=20)
    all_covered: bool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_coverage_counts(self) -> StructuredCoverageResult:
        for field in self.fields:
            if len(field.item_keys) != field.source_value_count:
                raise ValueError("结构化字段覆盖数量与事项映射数量不一致")
        expected = all(
            len(field.item_keys) == field.source_value_count for field in self.fields
        )
        if self.all_covered is not expected:
            raise ValueError("all_covered 与字段覆盖结果不一致")
        return self


class JobEvaluationPlanFreeTextCoverageUnit(BaseModel):
    source_id: SourceId
    disposition: Literal["requirements", "non_requirement"]
    item_keys: list[ItemKey] = Field(max_length=JOB_EVALUATION_PLAN_MAX_ITEMS)
    equivalent_structured_item_keys: list[ItemKey] = Field(
        max_length=JOB_EVALUATION_PLAN_MAX_ITEMS
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_item_keys(self) -> JobEvaluationPlanFreeTextCoverageUnit:
        if len(self.item_keys) != len(set(self.item_keys)):
            raise ValueError("自由文本覆盖事项 key 不能重复")
        if len(self.equivalent_structured_item_keys) != len(
            set(self.equivalent_structured_item_keys)
        ):
            raise ValueError("自由文本结构化等价 key 不能重复")
        if not set(self.equivalent_structured_item_keys).issubset(self.item_keys):
            raise ValueError("结构化等价 key 必须同时出现在片段覆盖事项中")
        if self.disposition == "requirements" and not self.item_keys:
            raise ValueError("requirements 覆盖片段必须映射至少一个最终事项")
        if self.disposition == "non_requirement" and self.item_keys:
            raise ValueError("non_requirement 覆盖片段不能映射评价事项")
        return self


class JobEvaluationPlanFreeTextCoverage(BaseModel):
    rule_version: Literal["jd_source_units_v1"]
    all_reviewed: Literal[True]
    units: list[JobEvaluationPlanFreeTextCoverageUnit] = Field(
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_source_ids(self) -> JobEvaluationPlanFreeTextCoverage:
        source_ids = [unit.source_id for unit in self.units]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("自由文本覆盖 source ID 不能重复")
        return self


class JobEvaluationPlanInputSnapshot(BaseModel):
    job_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20_000)
    requirements: LegacyEvaluationPlanRequirements

    model_config = ConfigDict(extra="forbid")


class JobEvaluationPlanRead(BaseModel):
    id: int
    job_id: int
    jd_fingerprint: Fingerprint
    status: JobEvaluationPlanStatus
    is_current: bool
    items: list[JobEvaluationItem] = Field(max_length=JOB_EVALUATION_PLAN_MAX_ITEMS)
    structured_coverage: StructuredCoverageResult
    warnings: list[JobEvaluationPlanWarning] = Field(max_length=5)
    prompt_version: VersionText
    model_version: VersionText
    schema_version: Literal["1.0", "2.0"]
    input_fingerprint: Fingerprint
    input_snapshot: JobEvaluationPlanInputSnapshot
    contract_outdated: bool = False
    error_code: ErrorCode | None
    error_message: SafeErrorMessage | None
    created_at: datetime
    completed_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        protected_namespaces=(),
    )

    @model_validator(mode="after")
    def validate_status_payload(self) -> JobEvaluationPlanRead:
        if self.status is JobEvaluationPlanStatus.GENERATING:
            if self.completed_at is not None or self.error_code or self.error_message:
                raise ValueError("generating 计划不能包含完成时间或错误信息")
        elif self.status is JobEvaluationPlanStatus.READY:
            if self.completed_at is None or self.error_code or self.error_message:
                raise ValueError("ready 计划必须已完成且不能包含错误信息")
            if not self.items:
                raise ValueError("ready 计划必须包含评价事项")
        elif self.status is JobEvaluationPlanStatus.FAILED:
            if self.completed_at is None or not self.error_code or not self.error_message:
                raise ValueError("failed 计划必须包含完成时间和安全错误信息")
        if self.status is JobEvaluationPlanStatus.OUTDATED and self.is_current:
            raise ValueError("outdated 计划不能是当前计划")
        return self


class JobEvaluationPlanAISourceUnit(BaseModel):
    source_id: SourceId
    source_field: Literal["description"]
    source_text: str = Field(min_length=1, max_length=20_000)

    model_config = ConfigDict(extra="forbid")


class JobEvaluationPlanAIStructuredCandidate(BaseModel):
    key: ItemKey
    title: ItemTitle
    category: EvaluationItemCategory
    priority: EvaluationItemPriority
    source_field: SourceField

    model_config = ConfigDict(extra="forbid")


class JobEvaluationPlanAIInput(BaseModel):
    input_snapshot: JobEvaluationPlanInputSnapshot
    source_units: list[JobEvaluationPlanAISourceUnit] = Field(
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )
    structured_candidates: list[JobEvaluationPlanAIStructuredCandidate] = Field(
        max_length=500
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_input_keys(self) -> JobEvaluationPlanAIInput:
        source_ids = [unit.source_id for unit in self.source_units]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source unit ID 不能重复")
        candidate_keys = [candidate.key for candidate in self.structured_candidates]
        if len(candidate_keys) != len(set(candidate_keys)):
            raise ValueError("结构化候选事项 key 不能重复")
        return self


class AIExtractedEvaluationItem(BaseModel):
    title: ItemTitle
    category: EvaluationItemCategory
    priority: EvaluationItemPriority
    source_quote: SourceQuote

    model_config = ConfigDict(extra="forbid")


class LegacyAIExtractedEvaluationPlanV1(BaseModel):
    schema_version: Literal["1.0"]
    items: list[AIExtractedEvaluationItem] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid")


class AIExtractedSourceReviewItem(BaseModel):
    title: ItemTitle
    category: EvaluationItemCategory
    equivalent_structured_item_key: ItemKey | None

    model_config = ConfigDict(extra="forbid")


class AIExtractedSourceReview(BaseModel):
    source_id: SourceId
    disposition: Literal["requirements", "non_requirement"]
    non_requirement_reason: Literal[
        "company_info",
        "benefit",
        "promotion",
        "context",
    ] | None
    items: list[AIExtractedSourceReviewItem] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_disposition_payload(self) -> AIExtractedSourceReview:
        if self.disposition == "requirements":
            if not self.items or self.non_requirement_reason is not None:
                raise ValueError("requirements 审阅必须有事项且不能包含非要求原因")
        elif self.items or self.non_requirement_reason is None:
            raise ValueError("non_requirement 审阅必须无事项且包含受控原因")
        return self


class AIExtractedEvaluationPlanV2(BaseModel):
    schema_version: Literal["2.0"]
    source_reviews: list[AIExtractedSourceReview] = Field(
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    model_config = ConfigDict(extra="forbid")


class AIExtractedEvaluationPlan:
    """Temporary staged parser; production Adapter accepts only the V2 result."""

    @classmethod
    def model_validate(
        cls,
        value: object,
    ) -> LegacyAIExtractedEvaluationPlanV1 | AIExtractedEvaluationPlanV2:
        if isinstance(value, dict) and value.get("schema_version") == "2.0":
            return AIExtractedEvaluationPlanV2.model_validate(value)
        return LegacyAIExtractedEvaluationPlanV1.model_validate(value)
