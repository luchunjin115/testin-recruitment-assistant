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
    model_serializer,
    model_validator,
)


JOB_EVALUATION_PLAN_SCHEMA_VERSION = "3.0"
JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION = "3.0"
JOB_EVALUATION_PLAN_PROMPT_VERSION = "job_evaluation_plan_v5"
JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION = "five_section_plan_generation_v1"
JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION = "five_section_source_units_v1"
JOB_EVALUATION_PLAN_FINGERPRINT_RULE_VERSION = "job_evaluation_input_v3"
LEGACY_JOB_EVALUATION_PLAN_SCHEMA_VERSION = "2.0"
LEGACY_JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION = "2.0"
LEGACY_JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION = "jd_extraction_v2"
LEGACY_JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION = "jd_source_units_v1"
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


class JobEvaluationPlanWarningCode(str, Enum):
    LIMITED_BASIS = "limited_basis"
    PRIORITY_SIGNAL_CONFLICT = "priority_signal_conflict"
    MISPLACED_NON_EVALUATION_CONTENT = "misplaced_non_evaluation_content"


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
FiveSectionSourceField = Literal[
    "job_responsibilities",
    "candidate_requirements",
    "preferred_qualifications",
]
FiveSectionSourceUnitId = Annotated[
    str,
    StringConstraints(
        pattern=(
            r"^(?:job_responsibilities|candidate_requirements|"
            r"preferred_qualifications):\d{4}$"
        )
    ),
]


class JobEvaluationItemSource(BaseModel):
    source_field: FiveSectionSourceField
    source_unit_id: FiveSectionSourceUnitId
    source_quote: SourceQuote

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_source_identity(self) -> JobEvaluationItemSource:
        if not self.source_unit_id.startswith(f"{self.source_field}:"):
            raise ValueError("source_unit_id 必须属于对应 source_field")
        return self


class JobEvaluationItem(BaseModel):
    key: ItemKey
    title: ItemTitle
    category: EvaluationItemCategory
    priority: EvaluationItemPriority
    source_type: EvaluationItemSourceType | None = None
    source_field: SourceField | None = None
    source_quote: SourceQuote | None = None
    sources: list[JobEvaluationItemSource] | None = Field(
        default=None,
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_source_trace(self) -> JobEvaluationItem:
        if self.sources is not None:
            if any(
                value is not None
                for value in (self.source_type, self.source_field, self.source_quote)
            ):
                raise ValueError("3.0 事项不能包含 legacy source 字段")
            source_identities = [
                (
                    source.source_field,
                    source.source_unit_id,
                    source.source_quote,
                )
                for source in self.sources
            ]
            if len(source_identities) != len(set(source_identities)):
                raise ValueError("3.0 事项来源不能重复")
        elif self.source_type is EvaluationItemSourceType.STRUCTURED:
            if self.source_field is None:
                raise ValueError("结构化评价事项必须包含 source_field")
        elif self.source_type is EvaluationItemSourceType.AI_EXTRACTED:
            if self.source_quote is None:
                raise ValueError("AI 拆解评价事项必须包含 source_quote")
        else:
            raise ValueError("评价事项必须包含 3.0 sources 或 legacy source_type")
        return self

    @model_serializer(mode="wrap")
    def serialize_versioned_item(self, handler):
        payload = handler(self)
        if self.sources is not None:
            payload.pop("source_type", None)
            payload.pop("source_field", None)
            payload.pop("source_quote", None)
        else:
            payload.pop("sources", None)
        return payload


class JobEvaluationPlanWarningDetail(BaseModel):
    code: JobEvaluationPlanWarningCode
    message: SafeErrorMessage
    source_unit_ids: list[FiveSectionSourceUnitId] = Field(
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_source_units(self) -> JobEvaluationPlanWarningDetail:
        if len(self.source_unit_ids) != len(set(self.source_unit_ids)):
            raise ValueError("warning source_unit_ids 不能重复")
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


class JobEvaluationPlanJobContext(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    job_background: str | None = Field(default=None, max_length=5_000)

    model_config = ConfigDict(extra="forbid")


class JobEvaluationPlanEvaluationFields(BaseModel):
    job_responsibilities: str | None = Field(default=None, max_length=10_000)
    candidate_requirements: str | None = Field(default=None, max_length=10_000)
    preferred_qualifications: str | None = Field(default=None, max_length=5_000)

    model_config = ConfigDict(extra="forbid")


class JobEvaluationPlanSourceUnit(BaseModel):
    source_unit_id: FiveSectionSourceUnitId
    source_field: FiveSectionSourceField
    ordinal: int = Field(ge=1, le=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS)
    source_text: str = Field(min_length=1, max_length=10_000)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_stable_identity(self) -> JobEvaluationPlanSourceUnit:
        expected_id = f"{self.source_field}:{self.ordinal:04d}"
        if self.source_unit_id != expected_id:
            raise ValueError("source_unit_id 必须由 source_field 和 ordinal 稳定生成")
        return self


class JobEvaluationPlanInputSnapshot(BaseModel):
    """Versioned input snapshot for current 3.0 plans and legacy history reads."""

    schema_version: Literal["3.0"] | None = None
    job_context: JobEvaluationPlanJobContext | None = None
    evaluation_fields: JobEvaluationPlanEvaluationFields | None = None
    source_units: list[JobEvaluationPlanSourceUnit] | None = Field(
        default=None,
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    job_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20_000)
    requirements: LegacyEvaluationPlanRequirements | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_versioned_shape(self) -> JobEvaluationPlanInputSnapshot:
        legacy_values = (self.job_id, self.title, self.description, self.requirements)
        v3_values = (self.job_context, self.evaluation_fields, self.source_units)
        if self.schema_version == "3.0":
            if any(value is not None for value in legacy_values):
                raise ValueError("3.0 input snapshot 不能包含 legacy Job 字段")
            if any(value is None for value in v3_values):
                raise ValueError("3.0 input snapshot 必须包含上下文、评价字段和 source units")
            source_units = self.source_units or []
            source_ids = [unit.source_unit_id for unit in source_units]
            if len(source_ids) != len(set(source_ids)):
                raise ValueError("3.0 source_unit_id 不能重复")
        else:
            if any(value is not None for value in v3_values):
                raise ValueError("legacy input snapshot 不能包含 3.0 字段")
            if self.job_id is None or self.title is None or self.requirements is None:
                raise ValueError("legacy input snapshot 缺少 Job 历史字段")
        return self

    @model_serializer(mode="wrap")
    def serialize_versioned_snapshot(self, handler):
        payload = handler(self)
        if self.schema_version == "3.0":
            for field in ("job_id", "title", "department", "description", "requirements"):
                payload.pop(field, None)
        else:
            for field in ("schema_version", "job_context", "evaluation_fields", "source_units"):
                payload.pop(field, None)
        return payload


class JobEvaluationPlanSourceReviewUnit(BaseModel):
    source_unit_id: FiveSectionSourceUnitId
    disposition: Literal["evaluation", "non_evaluation"]
    non_evaluation_reason: Literal[
        "company_info",
        "benefit",
        "promotion",
        "recruitment_process",
        "candidate_note",
        "context",
        "other",
    ] | None
    item_keys: list[ItemKey] = Field(max_length=JOB_EVALUATION_PLAN_MAX_ITEMS)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_disposition_payload(self) -> JobEvaluationPlanSourceReviewUnit:
        if len(self.item_keys) != len(set(self.item_keys)):
            raise ValueError("source review item_keys 不能重复")
        if self.disposition == "evaluation":
            if not self.item_keys or self.non_evaluation_reason is not None:
                raise ValueError("evaluation source unit 必须关联事项且不能有排除原因")
        elif self.item_keys or self.non_evaluation_reason is None:
            raise ValueError("non_evaluation source unit 必须有排除原因且不能关联事项")
        return self


class JobEvaluationPlanSourceReviewSummary(BaseModel):
    rule_version: Literal["five_section_source_units_v1"]
    total_units: int = Field(ge=1, le=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS)
    reviewed_units: int = Field(ge=0, le=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS)
    evaluation_units: int = Field(ge=0, le=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS)
    non_evaluation_units: int = Field(ge=0, le=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS)
    all_reviewed: bool
    units: list[JobEvaluationPlanSourceReviewUnit] = Field(
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_review_counts(self) -> JobEvaluationPlanSourceReviewSummary:
        source_ids = [unit.source_unit_id for unit in self.units]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source review summary 不能重复审阅 source unit")
        evaluation_count = sum(
            unit.disposition == "evaluation" for unit in self.units
        )
        non_evaluation_count = len(self.units) - evaluation_count
        if self.reviewed_units != len(self.units):
            raise ValueError("reviewed_units 必须等于已记录审阅单元数")
        if self.evaluation_units != evaluation_count:
            raise ValueError("evaluation_units 与审阅明细不一致")
        if self.non_evaluation_units != non_evaluation_count:
            raise ValueError("non_evaluation_units 与审阅明细不一致")
        if self.all_reviewed is not (self.reviewed_units == self.total_units):
            raise ValueError("all_reviewed 与 total/reviewed 计数不一致")
        return self


class JobEvaluationPlanRead(BaseModel):
    id: int
    job_id: int
    jd_fingerprint: Fingerprint
    status: JobEvaluationPlanStatus
    is_current: bool
    items: list[JobEvaluationItem] = Field(max_length=JOB_EVALUATION_PLAN_MAX_ITEMS)
    structured_coverage: StructuredCoverageResult | None = None
    source_review_summary: JobEvaluationPlanSourceReviewSummary | None = None
    warnings: list[JobEvaluationPlanWarning | JobEvaluationPlanWarningDetail] = Field(
        max_length=5
    )
    prompt_version: VersionText
    model_version: VersionText
    schema_version: Literal["1.0", "2.0", "3.0"]
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
            if self.schema_version == "3.0":
                if (
                    self.source_review_summary is None
                    or not self.source_review_summary.all_reviewed
                ):
                    raise ValueError("3.0 ready 计划必须完整审阅全部 source units")
                if self.structured_coverage is not None:
                    raise ValueError("3.0 计划不能包含 legacy structured coverage")
                if self.input_snapshot.schema_version != "3.0":
                    raise ValueError("3.0 计划必须使用 3.0 input snapshot")
                if any(
                    not isinstance(warning, JobEvaluationPlanWarningDetail)
                    for warning in self.warnings
                ):
                    raise ValueError("3.0 warnings 必须使用受控对象")
        elif self.status is JobEvaluationPlanStatus.FAILED:
            if self.completed_at is None or not self.error_code or not self.error_message:
                raise ValueError("failed 计划必须包含完成时间和安全错误信息")
        if self.status is JobEvaluationPlanStatus.OUTDATED and self.is_current:
            raise ValueError("outdated 计划不能是当前计划")
        return self

    @model_serializer(mode="wrap")
    def serialize_versioned_plan(self, handler):
        payload = handler(self)
        if self.schema_version == "3.0":
            payload.pop("structured_coverage", None)
        else:
            payload.pop("source_review_summary", None)
        return payload


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


class JobEvaluationPlanAIInputV3(BaseModel):
    input_snapshot: JobEvaluationPlanInputSnapshot
    source_units: list[JobEvaluationPlanSourceUnit] = Field(
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_snapshot_units(self) -> JobEvaluationPlanAIInputV3:
        if self.input_snapshot.schema_version != "3.0":
            raise ValueError("当前 AI 输入必须使用 3.0 input snapshot")
        snapshot_units = self.input_snapshot.source_units or []
        if [unit.model_dump(mode="json") for unit in self.source_units] != [
            unit.model_dump(mode="json") for unit in snapshot_units
        ]:
            raise ValueError("AI source_units 必须与 input snapshot 完全一致")
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


class AIExtractedEvaluationItemV3(BaseModel):
    title: ItemTitle
    category: EvaluationItemCategory
    source_quote: SourceQuote

    model_config = ConfigDict(extra="forbid")


class AIExtractedSourceReviewV3(BaseModel):
    source_unit_id: FiveSectionSourceUnitId
    disposition: Literal["evaluation", "non_evaluation"]
    non_evaluation_reason: Literal[
        "company_info",
        "benefit",
        "promotion",
        "recruitment_process",
        "candidate_note",
        "context",
        "other",
    ] | None
    items: list[AIExtractedEvaluationItemV3] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_disposition_payload(self) -> AIExtractedSourceReviewV3:
        if self.disposition == "evaluation":
            if not self.items or self.non_evaluation_reason is not None:
                raise ValueError("evaluation 审阅必须有事项且不能包含排除原因")
        elif self.items or self.non_evaluation_reason is None:
            raise ValueError("non_evaluation 审阅必须无事项且包含受控原因")
        return self


class AIExtractedEvaluationPlanV3(BaseModel):
    schema_version: Literal["3.0"]
    source_reviews: list[AIExtractedSourceReviewV3] = Field(
        min_length=1,
        max_length=JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
    )

    model_config = ConfigDict(extra="forbid")


class AIExtractedEvaluationPlan:
    """Parse current 3.0 output while retaining legacy history test support."""

    @classmethod
    def model_validate(
        cls,
        value: object,
    ) -> (
        LegacyAIExtractedEvaluationPlanV1
        | AIExtractedEvaluationPlanV2
        | AIExtractedEvaluationPlanV3
    ):
        if isinstance(value, dict) and value.get("schema_version") == "3.0":
            return AIExtractedEvaluationPlanV3.model_validate(value)
        if isinstance(value, dict) and value.get("schema_version") == "2.0":
            return AIExtractedEvaluationPlanV2.model_validate(value)
        return LegacyAIExtractedEvaluationPlanV1.model_validate(value)
