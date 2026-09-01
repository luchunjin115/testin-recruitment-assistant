from __future__ import annotations

from datetime import datetime
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

from app.schemas.screening_evaluation import (
    BonusHighlight,
    RequirementAssessment,
    ScreeningEvaluationV5ReportPayload,
)
from app.schemas.experience_period import ExperiencePeriodFactsSnapshot


class ScreeningRunTriggerType(str, Enum):
    AUTOMATIC = "automatic"
    SINGLE_REASSESSMENT = "single_reassessment"
    BATCH_REASSESSMENT = "batch_reassessment"


class ScreeningRunStatus(str, Enum):
    WAITING_RESUME = "waiting_resume"
    WAITING_PLAN = "waiting_plan"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PAUSED = "paused"


class ScreeningWaitingReason(str, Enum):
    JOB_CLOSED = "job_closed"
    PLAN_MISSING = "plan_missing"
    PLAN_GENERATING = "plan_generating"
    PLAN_PENDING_CONFIRMATION = "plan_pending_confirmation"
    PLAN_FAILED = "plan_failed"
    PLAN_OUTDATED = "plan_outdated"
    PLAN_CONTRACT_OUTDATED = "plan_contract_outdated"


class ScreeningOutdatedReason(str, Enum):
    RESUME_CHANGED = "resume_changed"
    JD_CHANGED = "jd_changed"
    JOB_EVALUATION_INPUT_CHANGED = "job_evaluation_input_changed"
    EVALUATION_PLAN_CHANGED = "evaluation_plan_changed"


Fingerprint = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
VersionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
SafeErrorCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=100),
]
SafeErrorMessage = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
PositiveId = Annotated[StrictInt, Field(ge=1)]


class ScreeningReportRead(BaseModel):
    id: PositiveId
    application_id: PositiveId
    job_id: PositiveId
    resume_id: PositiveId
    job_evaluation_plan_id: PositiveId
    overall_score: int = Field(strict=True, ge=0, le=100)
    display_label: str = Field(min_length=1, max_length=30)
    overall_summary: str = Field(min_length=1, max_length=3_000)
    requirement_assessments: list[RequirementAssessment] = Field(max_length=512)
    bonus_highlights: list[BonusHighlight] = Field(max_length=5)
    tradeoff_reason: str | None = Field(default=None, min_length=1, max_length=2_000)
    interview_questions: list[str] = Field(max_length=5)
    input_fingerprint: Fingerprint
    jd_fingerprint: Fingerprint
    plan_fingerprint: Fingerprint
    resume_fingerprint: Fingerprint
    prompt_version: VersionText
    model_version: VersionText
    schema_version: VersionText
    redaction_version: VersionText
    evaluation_reference_at: datetime | None = None
    evaluation_timezone: VersionText | None = None
    experience_period_facts_rule_version: VersionText | None = None
    experience_period_facts: ExperiencePeriodFactsSnapshot | None = Field(
        default=None,
        exclude=True,
    )
    v5_report: ScreeningEvaluationV5ReportPayload | None = None
    is_current: bool
    is_outdated: bool
    outdated_reasons: list[ScreeningOutdatedReason] = Field(max_length=3)
    outdated_at: datetime | None
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        protected_namespaces=(),
    )

    @model_validator(mode="after")
    def validate_outdated_state(self) -> ScreeningReportRead:
        if self.is_outdated != bool(self.outdated_reasons):
            raise ValueError("报告过期状态与原因不一致")
        if self.is_outdated != (self.outdated_at is not None):
            raise ValueError("报告过期状态与时间不一致")
        if self.schema_version == "5.0":
            if self.v5_report is None:
                raise ValueError("5.0 报告必须包含完整 v5_report")
            if (
                self.v5_report.overall_score != self.overall_score
                or self.v5_report.display_label != self.display_label
                or self.v5_report.overall_summary != self.overall_summary
            ):
                raise ValueError("5.0 JSONB 报告与索引列不一致")
        elif self.v5_report is not None:
            raise ValueError("旧报告不得伪装为 5.0 report payload")
        return self


class ScreeningRunRead(BaseModel):
    id: PositiveId
    application_id: PositiveId
    job_id: PositiveId
    resume_id: PositiveId
    job_evaluation_plan_id: PositiveId | None
    trigger_type: ScreeningRunTriggerType
    status: ScreeningRunStatus
    waiting_reason: ScreeningWaitingReason | None = None
    input_fingerprint: Fingerprint
    prompt_version: VersionText
    model_version: VersionText
    schema_version: VersionText
    redaction_version: VersionText
    evaluation_reference_at: datetime | None = None
    evaluation_timezone: VersionText | None = None
    experience_period_facts_rule_version: VersionText | None = None
    experience_period_facts_fingerprint: Fingerprint | None = None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: SafeErrorCode | None
    error_message: SafeErrorMessage | None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    attempt_count: int = Field(ge=0, le=3)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        protected_namespaces=(),
    )

    @model_validator(mode="after")
    def validate_waiting_reason(self) -> ScreeningRunRead:
        plan_reasons = {
            ScreeningWaitingReason.PLAN_MISSING,
            ScreeningWaitingReason.PLAN_GENERATING,
            ScreeningWaitingReason.PLAN_PENDING_CONFIRMATION,
            ScreeningWaitingReason.PLAN_FAILED,
            ScreeningWaitingReason.PLAN_OUTDATED,
            ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED,
        }
        if self.waiting_reason in plan_reasons:
            if self.status is not ScreeningRunStatus.WAITING_PLAN:
                raise ValueError("评价计划等待原因只能用于 waiting_plan")
        elif self.waiting_reason is ScreeningWaitingReason.JOB_CLOSED:
            if self.status is not ScreeningRunStatus.PAUSED:
                raise ValueError("job_closed 只能用于 paused")
        elif self.status in {
            ScreeningRunStatus.WAITING_PLAN,
            ScreeningRunStatus.PAUSED,
        }:
            # Historical rows created before 7R-D may not have a reason.
            return self
        return self


class ScreeningStateRead(BaseModel):
    application_id: PositiveId
    report: ScreeningReportRead | None
    latest_run: ScreeningRunRead | None

    model_config = ConfigDict(extra="forbid")


class ScreeningTriggerRead(BaseModel):
    application_id: PositiveId
    run: ScreeningRunRead | None
    report: ScreeningReportRead | None
    reused_report: bool = False
    reused_run: bool = False

    model_config = ConfigDict(extra="forbid")


class ScreeningReassessmentRequest(BaseModel):
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value: bool) -> bool:
        if not value:
            raise ValueError("重新评估必须由 HR 二次确认")
        return value


class ScreeningBatchReassessmentRequest(BaseModel):
    application_ids: list[PositiveId] = Field(min_length=1, max_length=5)
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_applications(self) -> ScreeningBatchReassessmentRequest:
        if len(self.application_ids) != len(set(self.application_ids)):
            raise ValueError("批量重新评估不能包含重复 Application")
        return self

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value: bool) -> bool:
        if not value:
            raise ValueError("批量重新评估必须由 HR 二次确认")
        return value


class ScreeningBatchFailureRead(BaseModel):
    application_id: PositiveId
    error_code: SafeErrorCode
    error_message: SafeErrorMessage
    retryable: bool

    model_config = ConfigDict(extra="forbid")


class ScreeningBatchReassessmentRead(BaseModel):
    job_id: PositiveId
    total_count: int = Field(strict=True, ge=1, le=5)
    reused_count: int = Field(strict=True, ge=0, le=5)
    queued_count: int = Field(strict=True, ge=0, le=5)
    failed_count: int = Field(strict=True, ge=0, le=5)
    results: list[ScreeningTriggerRead] = Field(max_length=5)
    failures: list[ScreeningBatchFailureRead] = Field(max_length=5)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_batch_totals(self) -> ScreeningBatchReassessmentRead:
        if self.total_count != len(self.results) + len(self.failures):
            raise ValueError("批量结果总数与逐项结果不一致")
        if self.failed_count != len(self.failures):
            raise ValueError("批量失败计数与逐项失败不一致")
        if self.reused_count + self.queued_count != len(self.results):
            raise ValueError("批量复用/排队计数与成功提交结果不一致")
        return self


class ApplicationResumeSwitchRequest(BaseModel):
    resume_id: PositiveId

    model_config = ConfigDict(extra="forbid")
