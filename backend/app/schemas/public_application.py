from __future__ import annotations

from enum import Enum
from typing import Annotated, Any
from uuid import UUID

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

from app.schemas.application import (
    normalize_application_email,
    normalize_application_phone,
)
from app.schemas.job import EmploymentType


class PublicApplicationIdentityReviewStatus(str, Enum):
    CLEAR = "clear"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


class PublicApplicationIdentityReviewReason(str, Enum):
    SAME_NAME = "same_name"
    CONTACT_CONFLICT = "contact_conflict"


class ApplicationProcessingTriggerType(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL_RETRY = "manual_retry"


class ApplicationProcessingStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_SCREENING = "waiting_screening"
    SUCCEEDED = "succeeded"
    SUCCEEDED_WITH_WARNINGS = "succeeded_with_warnings"
    FAILED = "failed"
    PAUSED = "paused"


class ApplicationProcessingStep(str, Enum):
    EXTRACT_TEXT = "extract_text"
    STRUCTURE_RESUME = "structure_resume"
    TRIGGER_SCREENING = "trigger_screening"
    AWAIT_SCREENING = "await_screening"
    COMPLETED = "completed"


class ApplicationProcessingWaitingReason(str, Enum):
    JOB_CLOSED = "job_closed"
    EXISTING_APPLICATION_RESUME_CHOICE = "existing_application_resume_choice"


class ApplicationProcessingWarningCode(str, Enum):
    RESUME_STRUCTURE_FAILED = "RESUME_STRUCTURE_FAILED"


class PublicApplicationErrorCode(str, Enum):
    INVALID = "PUBLIC_APPLICATION_INVALID"
    JOB_NOT_OPEN = "JOB_NOT_OPEN"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    REVIEW_REQUIRED = "PUBLIC_APPLICATION_REVIEW_REQUIRED"
    RESUME_FILE_TOO_LARGE = "RESUME_FILE_TOO_LARGE"
    RESUME_TYPE_UNSUPPORTED = "RESUME_TYPE_UNSUPPORTED"
    VALIDATION_FAILED = "PUBLIC_APPLICATION_VALIDATION_FAILED"
    RATE_LIMITED = "PUBLIC_APPLICATION_RATE_LIMITED"
    SAVE_FAILED = "PUBLIC_APPLICATION_SAVE_FAILED"
    TEMPORARILY_UNAVAILABLE = "PUBLIC_APPLICATION_TEMPORARILY_UNAVAILABLE"


PositiveId = Annotated[StrictInt, Field(ge=1)]
PersonName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
ConsentVersion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
SubmissionReference = Annotated[
    str,
    StringConstraints(pattern=r"^AP-[A-Z0-9]{8,24}$"),
]
Sha256Hex = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]
SafeErrorCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=100),
]
SafeErrorMessage = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=500),
]


class PublicJobRead(BaseModel):
    id: PositiveId
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    employment_type: EmploymentType | None = None
    job_background: str | None = None
    job_responsibilities: str | None = None
    candidate_requirements: str | None = None
    preferred_qualifications: str | None = None
    public_notes: str | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PublicApplicationForm(BaseModel):
    name: PersonName
    phone: str
    email: str
    job_id: PositiveId
    privacy_consent: StrictBool
    consent_version: ConsentVersion
    idempotency_key: UUID

    model_config = ConfigDict(extra="forbid")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Any) -> Any:
        return normalize_application_phone(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return normalize_application_email(value)

    @field_validator("privacy_consent")
    @classmethod
    def require_privacy_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("必须同意当前隐私说明后才能投递")
        return value


class PublicApplicationAcceptedResponse(BaseModel):
    submission_reference: SubmissionReference
    accepted_at: AwareDatetime
    message: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")


class PublicApplicationSubmissionCreate(BaseModel):
    application_id: PositiveId
    resume_id: PositiveId
    submission_reference: SubmissionReference
    idempotency_key_hash: Sha256Hex
    request_fingerprint: Sha256Hex
    consent_version: ConsentVersion
    consented_at: AwareDatetime
    identity_review_status: PublicApplicationIdentityReviewStatus = (
        PublicApplicationIdentityReviewStatus.CLEAR
    )
    identity_review_reasons: list[PublicApplicationIdentityReviewReason] = Field(
        default_factory=list,
        max_length=2,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_identity_review(self) -> PublicApplicationSubmissionCreate:
        if len(self.identity_review_reasons) != len(set(self.identity_review_reasons)):
            raise ValueError("身份核对原因不能重复")
        if self.identity_review_status is PublicApplicationIdentityReviewStatus.CLEAR:
            if self.identity_review_reasons:
                raise ValueError("clear 状态不能包含身份核对原因")
        elif not self.identity_review_reasons:
            raise ValueError("needs_review/reviewed 状态必须保留身份核对原因")
        return self


class PublicApplicationSubmissionRead(PublicApplicationSubmissionCreate):
    id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ApplicationProcessingRunCreate(BaseModel):
    submission_id: PositiveId
    application_id: PositiveId
    resume_id: PositiveId
    trigger_type: ApplicationProcessingTriggerType
    status: ApplicationProcessingStatus = ApplicationProcessingStatus.QUEUED
    current_step: ApplicationProcessingStep = ApplicationProcessingStep.EXTRACT_TEXT
    attempt_count: int = Field(default=0, strict=True, ge=0, le=3)
    waiting_reason: ApplicationProcessingWaitingReason | None = None
    error_code: SafeErrorCode | None = None
    error_message: SafeErrorMessage | None = None
    warning_codes: list[ApplicationProcessingWarningCode] = Field(
        default_factory=list,
        max_length=8,
    )
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    lease_owner: str | None = Field(default=None, min_length=1, max_length=100)
    lease_expires_at: AwareDatetime | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_run_state(self) -> ApplicationProcessingRunCreate:
        if len(self.warning_codes) != len(set(self.warning_codes)):
            raise ValueError("warning code 不能重复")

        if self.status is ApplicationProcessingStatus.PAUSED:
            if self.waiting_reason is None:
                raise ValueError("paused 状态必须包含等待原因")
        elif self.waiting_reason is not None:
            raise ValueError("等待原因只能用于 paused 状态")

        if self.status is ApplicationProcessingStatus.FAILED:
            if self.completed_at is None or self.error_code is None or self.error_message is None:
                raise ValueError("failed 状态必须包含完成时间和安全错误")
        elif self.error_code is not None or self.error_message is not None:
            raise ValueError("安全错误字段只能用于 failed 状态")

        succeeded_statuses = {
            ApplicationProcessingStatus.SUCCEEDED,
            ApplicationProcessingStatus.SUCCEEDED_WITH_WARNINGS,
        }
        if self.status in succeeded_statuses:
            if self.current_step is not ApplicationProcessingStep.COMPLETED:
                raise ValueError("成功状态的当前步骤必须为 completed")
            if self.completed_at is None:
                raise ValueError("成功状态必须包含完成时间")
        elif self.current_step is ApplicationProcessingStep.COMPLETED:
            raise ValueError("completed 步骤只能用于成功状态")

        if (
            self.status is ApplicationProcessingStatus.WAITING_SCREENING
            and self.current_step is not ApplicationProcessingStep.AWAIT_SCREENING
        ):
            raise ValueError("waiting_screening 状态必须停在 await_screening")

        if self.status is ApplicationProcessingStatus.SUCCEEDED and self.warning_codes:
            raise ValueError("succeeded 状态不能包含 warning")
        if (
            self.status is ApplicationProcessingStatus.SUCCEEDED_WITH_WARNINGS
            and not self.warning_codes
        ):
            raise ValueError("succeeded_with_warnings 必须包含 warning")

        has_lease_owner = self.lease_owner is not None
        has_lease_expiry = self.lease_expires_at is not None
        if has_lease_owner != has_lease_expiry:
            raise ValueError("租约 owner 和 expires_at 必须同时存在")
        if has_lease_owner and self.status is not ApplicationProcessingStatus.RUNNING:
            raise ValueError("只有 running 状态可以持有租约")
        if self.status is ApplicationProcessingStatus.RUNNING and self.started_at is None:
            raise ValueError("running 状态必须包含开始时间")
        return self


class ApplicationProcessingRunRead(ApplicationProcessingRunCreate):
    id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


__all__ = [
    "ApplicationProcessingRunCreate",
    "ApplicationProcessingRunRead",
    "ApplicationProcessingStatus",
    "ApplicationProcessingStep",
    "ApplicationProcessingTriggerType",
    "ApplicationProcessingWaitingReason",
    "ApplicationProcessingWarningCode",
    "PublicApplicationAcceptedResponse",
    "PublicApplicationErrorCode",
    "PublicApplicationForm",
    "PublicApplicationIdentityReviewReason",
    "PublicApplicationIdentityReviewStatus",
    "PublicApplicationSubmissionCreate",
    "PublicApplicationSubmissionRead",
    "PublicJobRead",
]
