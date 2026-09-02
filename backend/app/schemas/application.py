from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

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

from app.schemas.education import EducationCreate
from app.schemas.project_experience import ProjectExperienceCreate
from app.schemas.work_experience import WorkExperienceCreate


class ApplicationSource(str, Enum):
    HR_DIRECT = "hr_direct"
    HR_SCREENING = "hr_screening"
    PUBLIC_APPLY = "public_apply"


class ApplicationLifecycleStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    VOIDED = "voided"


class RecruitmentStage(str, Enum):
    APPLIED = "applied"
    HR_REVIEW = "hr_review"
    SCREENING_PASSED = "screening_passed"
    BACKUP = "backup"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"
    OFFER_ACCEPTED = "offer_accepted"
    ADMITTED = "admitted"
    HIRED = "hired"


class HRDecision(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    BACKUP = "backup"
    REJECTED = "rejected"


class FinalOutcome(str, Enum):
    SCREENING_REJECTED = "screening_rejected"
    INTERVIEW_REJECTED = "interview_rejected"
    INTERVIEW_NO_SHOW = "interview_no_show"
    OFFER_DECLINED = "offer_declined"
    OFFER_WITHDRAWN = "offer_withdrawn"
    OFFER_EXPIRED = "offer_expired"
    CANDIDATE_WITHDREW = "candidate_withdrew"
    COMPANY_CANCELED = "company_canceled"
    HIRED = "hired"


class CandidateResolution(str, Enum):
    CREATED = "created"
    REUSED = "reused"


PositiveId = Annotated[StrictInt, Field(ge=1)]
PersonName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
ReasonText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]

_PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9\s()-]+$")
_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def normalize_application_phone(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    raw_value = value.strip()
    if not raw_value or not _PHONE_ALLOWED_PATTERN.fullmatch(raw_value):
        raise ValueError("手机号格式无效")

    has_country_prefix = raw_value.startswith("+")
    digits = re.sub(r"\D", "", raw_value)
    if not 7 <= len(digits) <= 15:
        raise ValueError("手机号必须包含 7 到 15 位数字")
    return f"+{digits}" if has_country_prefix else digits


def normalize_application_email(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower()
    if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("邮箱格式无效")

    local_part, domain = normalized.rsplit("@", 1)
    if len(local_part) > 64 or ".." in local_part or ".." in domain:
        raise ValueError("邮箱格式无效")
    return normalized


class ApplicationResumeProfile(BaseModel):
    gender: str | None = Field(default=None, max_length=10)
    age: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)
    current_company: str | None = Field(default=None, max_length=200)
    current_title: str | None = Field(default=None, max_length=200)
    work_years: int | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=50)
    skills: list[str] | None = None
    education_records: list[EducationCreate] = Field(default_factory=list)
    work_experiences: list[WorkExperienceCreate] = Field(default_factory=list)
    project_experiences: list[ProjectExperienceCreate] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ApplicationIntakeRequest(BaseModel):
    candidate_id: PositiveId | None = None
    name: PersonName
    phone: str
    email: str
    job_id: PositiveId
    current_resume_id: PositiveId
    source: Literal[ApplicationSource.HR_DIRECT, ApplicationSource.HR_SCREENING]
    confirm_hr_pass: StrictBool = False
    resume_profile: ApplicationResumeProfile | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Any) -> Any:
        return normalize_application_phone(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return normalize_application_email(value)

    @model_validator(mode="after")
    def validate_source_confirmation(self) -> ApplicationIntakeRequest:
        if self.source is ApplicationSource.HR_DIRECT and not self.confirm_hr_pass:
            raise ValueError("HR 直接新增必须明确确认人工通过")
        if self.source is ApplicationSource.HR_SCREENING and self.confirm_hr_pass:
            raise ValueError("AI 初筛录入不能声明 HR 已人工通过")
        return self


class ApplicationCreate(BaseModel):
    candidate_id: PositiveId
    job_id: PositiveId
    current_resume_id: PositiveId
    source: ApplicationSource
    lifecycle_status: ApplicationLifecycleStatus = ApplicationLifecycleStatus.ACTIVE
    recruitment_stage: RecruitmentStage
    hr_decision: HRDecision
    final_outcome: FinalOutcome | None = None
    applied_at: AwareDatetime | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_initial_state(self) -> ApplicationCreate:
        if self.final_outcome is not None:
            raise ValueError("新建 Application 不能预设最终结果")

        if self.source is ApplicationSource.HR_DIRECT:
            expected = (
                ApplicationLifecycleStatus.ACTIVE,
                RecruitmentStage.SCREENING_PASSED,
                HRDecision.PASSED,
            )
            actual = (
                self.lifecycle_status,
                self.recruitment_stage,
                self.hr_decision,
            )
            if actual != expected:
                raise ValueError("HR 直接新增的初始状态必须为人工通过且 AI 尚未开始")

        if self.source in {
            ApplicationSource.HR_SCREENING,
            ApplicationSource.PUBLIC_APPLY,
        }:
            expected = (
                ApplicationLifecycleStatus.ACTIVE,
                RecruitmentStage.APPLIED,
                HRDecision.PENDING,
            )
            actual = (
                self.lifecycle_status,
                self.recruitment_stage,
                self.hr_decision,
            )
            if actual != expected:
                raise ValueError("待初筛申请的初始状态必须为 applied/pending/not_started")
        return self


class ApplicationRead(BaseModel):
    id: PositiveId
    candidate_id: PositiveId
    job_id: PositiveId
    current_resume_id: PositiveId
    source: ApplicationSource
    lifecycle_status: ApplicationLifecycleStatus
    recruitment_stage: RecruitmentStage
    hr_decision: HRDecision
    final_outcome: FinalOutcome | None = None
    applied_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ApplicationIntakeResponse(BaseModel):
    application: ApplicationRead
    candidate_resolution: CandidateResolution
    existing_application_reused: StrictBool
    suspected_duplicate_candidate_ids: list[PositiveId] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "ApplicationResumeProfile",
    "ApplicationCreate",
    "ApplicationIntakeRequest",
    "ApplicationIntakeResponse",
    "ApplicationLifecycleStatus",
    "ApplicationRead",
    "ApplicationSource",
    "CandidateResolution",
    "FinalOutcome",
    "HRDecision",
    "PositiveId",
    "ReasonText",
    "RecruitmentStage",
    "normalize_application_email",
    "normalize_application_phone",
]
