from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt

from app.schemas.application import (
    ApplicationLifecycleStatus,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.job import JobStatus
from app.schemas.public_application import (
    ApplicationProcessingStatus,
    ApplicationProcessingStep,
    ApplicationProcessingTriggerType,
    ApplicationProcessingWaitingReason,
    ApplicationProcessingWarningCode,
    PublicApplicationIdentityReviewReason,
    PublicApplicationIdentityReviewStatus,
    SubmissionReference,
)


class PublicApplicationPool(str, Enum):
    ALL = "all"
    NORMAL = "normal"
    EXCEPTION = "exception"


class HRActionConfirmation(BaseModel):
    confirmed: StrictBool = False

    model_config = ConfigDict(extra="forbid")


class PublicApplicationProcessingRunSummary(BaseModel):
    id: StrictInt = Field(ge=1)
    trigger_type: ApplicationProcessingTriggerType
    status: ApplicationProcessingStatus
    current_step: ApplicationProcessingStep
    attempt_count: StrictInt = Field(ge=0, le=3)
    waiting_reason: ApplicationProcessingWaitingReason | None
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)
    warning_codes: list[ApplicationProcessingWarningCode] = Field(default_factory=list)
    started_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(extra="forbid")


class PublicApplicationWorkbenchSummary(BaseModel):
    submission_id: StrictInt = Field(ge=1)
    submission_reference: SubmissionReference
    submitted_at: AwareDatetime
    identity_review_status: PublicApplicationIdentityReviewStatus
    identity_review_reasons: list[PublicApplicationIdentityReviewReason]
    application_id: StrictInt = Field(ge=1)
    candidate_id: StrictInt = Field(ge=1)
    resume_id: StrictInt = Field(ge=1)
    job_id: StrictInt = Field(ge=1)
    candidate_name: str = Field(min_length=1, max_length=100)
    job_title: str = Field(min_length=1, max_length=200)
    job_status: JobStatus
    resume_filename: str = Field(min_length=1, max_length=255)
    resume_parse_status: Literal["uploaded", "parsing", "parsed", "failed"]
    lifecycle_status: ApplicationLifecycleStatus
    recruitment_stage: RecruitmentStage
    hr_decision: HRDecision
    latest_run: PublicApplicationProcessingRunSummary

    model_config = ConfigDict(extra="forbid")


class PublicApplicationIdentityCandidate(BaseModel):
    id: StrictInt = Field(ge=1)
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    source: str | None = Field(default=None, max_length=50)
    created_at: AwareDatetime
    is_submission_candidate: StrictBool

    model_config = ConfigDict(extra="forbid")


class PublicApplicationWorkbenchDetail(PublicApplicationWorkbenchSummary):
    processing_runs: list[PublicApplicationProcessingRunSummary]
    identity_candidates: list[PublicApplicationIdentityCandidate]

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "HRActionConfirmation",
    "PublicApplicationIdentityCandidate",
    "PublicApplicationPool",
    "PublicApplicationProcessingRunSummary",
    "PublicApplicationWorkbenchDetail",
    "PublicApplicationWorkbenchSummary",
]
