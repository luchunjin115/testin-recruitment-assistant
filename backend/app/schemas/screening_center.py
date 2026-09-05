from __future__ import annotations

from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt

from app.schemas.application import (
    ApplicationLifecycleStatus,
    ApplicationSource,
    FinalOutcome,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.job import JobStatus
from app.schemas.job_evaluation_plan import EvaluationItemPriority
from app.schemas.public_application import (
    ApplicationProcessingStatus,
    ApplicationProcessingStep,
)
from app.schemas.screening import ScreeningRunStatus, ScreeningWaitingReason


class ScreeningCenterSort(str, Enum):
    APPLIED_DESC = "applied_desc"
    UPDATED_DESC = "updated_desc"
    SCORE_DESC = "score_desc"
    SCORE_ASC = "score_asc"


class ScreeningCenterView(str, Enum):
    SCREENING = "screening"
    CANDIDATE = "candidate"
    ALL = "all"


class ScreeningCenterProcessingPool(str, Enum):
    ALL = "all"
    INTERNAL = "internal"
    NORMAL = "normal"
    EXCEPTION = "exception"


class ScreeningCenterReportStatus(str, Enum):
    NOT_STARTED = "not_started"
    WAITING_RESUME = "waiting_resume"
    WAITING_PLAN = "waiting_plan"
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    PAUSED = "paused"
    OUTDATED = "outdated"
    OLD_REPORT_RETAINED = "old_report_retained"


class ScreeningCenterDisplayLabel(str, Enum):
    WEAK = "关联较弱"
    CLEAR_GAP = "存在明显差距"
    PARTIAL = "部分匹配"
    MATCHED = "整体较匹配"
    HIGH = "高度匹配"


class ScreeningCenterAllowedAction(str, Enum):
    VIEW_DETAIL = "view_detail"
    START_SCREENING = "start_screening"
    REASSESS_SCREENING = "reassess_screening"
    PASS = "pass"
    BACKUP = "backup"
    REJECT = "reject"
    UNDO_REJECTION = "undo_rejection"
    SCHEDULE_INTERVIEW = "schedule_interview"
    CREATE_OFFER = "create_offer"
    EDIT_OFFER = "edit_offer"
    SEND_OFFER = "send_offer"
    ACCEPT_OFFER = "accept_offer"
    DECLINE_OFFER = "decline_offer"
    WITHDRAW_OFFER = "withdraw_offer"
    EXPIRE_OFFER = "expire_offer"
    CONFIRM_ADMISSION = "confirm_admission"
    CONFIRM_HIRE = "confirm_hire"
    WITHDRAW_APPLICATION = "withdraw_application"
    CANCEL_PROCESS = "cancel_process"
    REOPEN_STAGE9 = "reopen_stage9"


class ScreeningAbilityTag(BaseModel):
    criterion_id: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=200)
    score: StrictInt = Field(ge=1, le=10)
    importance: EvaluationItemPriority
    evidence_count: StrictInt = Field(ge=1, le=10)
    is_outdated: StrictBool

    model_config = ConfigDict(extra="forbid")


class ScreeningCenterApplicationSummary(BaseModel):
    application_id: StrictInt = Field(ge=1)
    candidate_id: StrictInt = Field(ge=1)
    job_id: StrictInt = Field(ge=1)
    resume_id: StrictInt = Field(ge=1)
    candidate_name: str = Field(min_length=1, max_length=100)
    masked_phone: str | None = Field(default=None, max_length=20)
    current_company: str | None = Field(default=None, max_length=200)
    current_title: str | None = Field(default=None, max_length=200)
    work_years: StrictInt | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, max_length=50)
    job_title: str = Field(min_length=1, max_length=200)
    job_status: JobStatus
    source: ApplicationSource
    submission_id: StrictInt | None = Field(default=None, ge=1)
    submission_reference: str | None = Field(default=None, max_length=27)
    lifecycle_status: ApplicationLifecycleStatus
    recruitment_stage: RecruitmentStage
    hr_decision: HRDecision
    final_outcome: FinalOutcome | None
    processing_pool: ScreeningCenterProcessingPool
    processing_status: ApplicationProcessingStatus | None
    processing_step: ApplicationProcessingStep | None
    processing_warning_codes: list[str] = Field(default_factory=list, max_length=5)
    screening_status: ScreeningCenterReportStatus
    screening_run_status: ScreeningRunStatus | None
    screening_waiting_reason: ScreeningWaitingReason | None
    screening_error_message: str | None = Field(default=None, max_length=500)
    score: StrictInt | None = Field(default=None, ge=0, le=100)
    display_label: str | None = Field(default=None, max_length=30)
    report_id: StrictInt | None = Field(default=None, ge=1)
    report_is_outdated: StrictBool = False
    ability_tags: list[ScreeningAbilityTag] = Field(default_factory=list, max_length=4)
    overall_summary: str | None = Field(default=None, max_length=360)
    strengths: list[str] = Field(default_factory=list, max_length=2)
    gaps_or_risks: list[str] = Field(default_factory=list, max_length=2)
    applied_at: AwareDatetime
    business_updated_at: AwareDatetime
    allowed_actions: list[ScreeningCenterAllowedAction]

    model_config = ConfigDict(extra="forbid")


class ScreeningCenterApplicationPage(BaseModel):
    items: list[ScreeningCenterApplicationSummary]
    page: StrictInt = Field(ge=1)
    page_size: StrictInt = Field(ge=1, le=100)
    total: StrictInt = Field(ge=0)
    total_pages: StrictInt = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


__all__ = [name for name in globals() if name.startswith("Screening")]
