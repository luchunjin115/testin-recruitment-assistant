from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.job import JobRequirementsV1


JOB_EVALUATION_PLAN_SCHEMA_VERSION = "1.0"
JOB_EVALUATION_PLAN_MAX_ITEMS = 30


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


class JobEvaluationPlanInputSnapshot(BaseModel):
    job_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20_000)
    requirements: JobRequirementsV1

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
    schema_version: Literal["1.0"]
    input_fingerprint: Fingerprint
    input_snapshot: JobEvaluationPlanInputSnapshot
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


class AIExtractedEvaluationItem(BaseModel):
    title: ItemTitle
    category: EvaluationItemCategory
    priority: EvaluationItemPriority
    source_quote: SourceQuote

    model_config = ConfigDict(extra="forbid")


class AIExtractedEvaluationPlan(BaseModel):
    schema_version: Literal["1.0"]
    items: list[AIExtractedEvaluationItem] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid")
