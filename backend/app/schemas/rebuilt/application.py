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


class ApplicationSource(str, Enum):
    HR_DIRECT = "hr_direct"
    HR_SCREENING = "hr_screening"
    PUBLIC_APPLY = "public_apply"
    LEGACY_MIGRATION = "legacy_migration"


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


class ApplicationAIStatus(str, Enum):
    NOT_STARTED = "not_started"
    SCREENING = "screening"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class HRDecision(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    BACKUP = "backup"
    REJECTED = "rejected"


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


class ApplicationIntakeRequest(BaseModel):
    candidate_id: PositiveId | None = None
    name: PersonName
    phone: str
    email: str
    job_id: PositiveId
    current_resume_id: PositiveId
    source: Literal[ApplicationSource.HR_DIRECT, ApplicationSource.HR_SCREENING]
    confirm_hr_pass: StrictBool = False

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
    current_resume_id: PositiveId | None
    source: ApplicationSource
    lifecycle_status: ApplicationLifecycleStatus = ApplicationLifecycleStatus.ACTIVE
    recruitment_stage: RecruitmentStage
    ai_status: ApplicationAIStatus = ApplicationAIStatus.NOT_STARTED
    hr_decision: HRDecision
    applied_at: AwareDatetime | None = None
    legacy_stage: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("legacy_stage", mode="before")
    @classmethod
    def normalize_legacy_stage(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_initial_state(self) -> ApplicationCreate:
        if self.source is not ApplicationSource.LEGACY_MIGRATION and self.current_resume_id is None:
            raise ValueError("新 Application 必须绑定当前简历")

        if self.source is ApplicationSource.HR_DIRECT:
            expected = (
                ApplicationLifecycleStatus.ACTIVE,
                RecruitmentStage.SCREENING_PASSED,
                ApplicationAIStatus.NOT_STARTED,
                HRDecision.PASSED,
            )
            actual = (
                self.lifecycle_status,
                self.recruitment_stage,
                self.ai_status,
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
                ApplicationAIStatus.NOT_STARTED,
                HRDecision.PENDING,
            )
            actual = (
                self.lifecycle_status,
                self.recruitment_stage,
                self.ai_status,
                self.hr_decision,
            )
            if actual != expected:
                raise ValueError("待初筛申请的初始状态必须为 applied/pending/not_started")
        return self


class ApplicationRead(BaseModel):
    id: PositiveId
    candidate_id: PositiveId
    job_id: PositiveId
    current_resume_id: PositiveId | None
    source: ApplicationSource
    lifecycle_status: ApplicationLifecycleStatus
    recruitment_stage: RecruitmentStage
    ai_status: ApplicationAIStatus
    hr_decision: HRDecision
    current_screening_result_id: PositiveId | None
    applied_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    legacy_stage: str | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ApplicationIntakeResponse(BaseModel):
    application: ApplicationRead
    candidate_resolution: CandidateResolution
    existing_application_reused: StrictBool
    suspected_duplicate_candidate_ids: list[PositiveId] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ScreeningRunRequest(BaseModel):
    force: StrictBool = False
    confirm_force: StrictBool = False
    reason: ReasonText | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_force_confirmation(self) -> ScreeningRunRequest:
        if self.force and (not self.confirm_force or self.reason is None):
            raise ValueError("强制重跑必须二次确认并填写原因")
        if not self.force and self.confirm_force:
            raise ValueError("普通评分请求不能提交强制重跑确认")
        return self


__all__ = [
    "ApplicationAIStatus",
    "ApplicationCreate",
    "ApplicationIntakeRequest",
    "ApplicationIntakeResponse",
    "ApplicationLifecycleStatus",
    "ApplicationRead",
    "ApplicationSource",
    "CandidateResolution",
    "HRDecision",
    "PositiveId",
    "ReasonText",
    "RecruitmentStage",
    "ScreeningRunRequest",
    "normalize_application_email",
    "normalize_application_phone",
]
