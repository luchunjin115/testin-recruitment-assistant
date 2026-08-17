from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    model_validator,
)

from app.schemas.rebuilt.application import HRDecision, PositiveId, RecruitmentStage


class StageHistoryActorType(str, Enum):
    HR = "hr"
    SYSTEM = "system"
    MIGRATION = "migration"


class StageHistoryReasonCode(str, Enum):
    APPLICATION_CREATED = "application_created"
    HR_DIRECT_ENTRY = "hr_direct_entry"
    MEETS_REQUIREMENTS = "meets_requirements"
    MANUAL_OVERRIDE = "manual_override"
    MINOR_CAPABILITY_GAP = "minor_capability_gap"
    WAITING_FOR_COMPARISON = "waiting_for_comparison"
    LIMITED_HEADCOUNT = "limited_headcount"
    INFORMATION_PENDING = "information_pending"
    COMPENSATION_PENDING = "compensation_pending"
    AVAILABILITY_PENDING = "availability_pending"
    REQUIRED_SKILL_MISSING = "required_skill_missing"
    WORK_EXPERIENCE_INSUFFICIENT = "work_experience_insufficient"
    EDUCATION_REQUIREMENT_NOT_MET = "education_requirement_not_met"
    REQUIRED_EXPERIENCE_MISSING = "required_experience_missing"
    ROLE_MISMATCH = "role_mismatch"
    NEW_EVIDENCE = "new_evidence"
    CANDIDATE_INFORMATION_UPDATED = "candidate_information_updated"
    JOB_REQUIREMENTS_CHANGED = "job_requirements_changed"
    DECISION_CORRECTION = "decision_correction"
    HR_REASSESSMENT = "hr_reassessment"
    DUPLICATE_ENTRY = "duplicate_entry"
    WRONG_JOB = "wrong_job"
    ENTRY_ERROR = "entry_error"
    LEGACY_MIGRATION = "legacy_migration"


class PassReasonCode(str, Enum):
    MEETS_REQUIREMENTS = "meets_requirements"
    MANUAL_OVERRIDE = "manual_override"


class BackupReasonCode(str, Enum):
    MINOR_CAPABILITY_GAP = "minor_capability_gap"
    WAITING_FOR_COMPARISON = "waiting_for_comparison"
    LIMITED_HEADCOUNT = "limited_headcount"
    INFORMATION_PENDING = "information_pending"
    COMPENSATION_PENDING = "compensation_pending"
    AVAILABILITY_PENDING = "availability_pending"


class RejectReasonCode(str, Enum):
    REQUIRED_SKILL_MISSING = "required_skill_missing"
    WORK_EXPERIENCE_INSUFFICIENT = "work_experience_insufficient"
    EDUCATION_REQUIREMENT_NOT_MET = "education_requirement_not_met"
    REQUIRED_EXPERIENCE_MISSING = "required_experience_missing"
    ROLE_MISMATCH = "role_mismatch"


class DecisionReversalReasonCode(str, Enum):
    NEW_EVIDENCE = "new_evidence"
    CANDIDATE_INFORMATION_UPDATED = "candidate_information_updated"
    JOB_REQUIREMENTS_CHANGED = "job_requirements_changed"
    DECISION_CORRECTION = "decision_correction"
    HR_REASSESSMENT = "hr_reassessment"


class VoidReasonCode(str, Enum):
    DUPLICATE_ENTRY = "duplicate_entry"
    WRONG_JOB = "wrong_job"
    ENTRY_ERROR = "entry_error"


RequiredReasonDetail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
OptionalReasonDetail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
ActorLabel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]


class PassApplicationRequest(BaseModel):
    reason_code: PassReasonCode
    reason_detail: OptionalReasonDetail | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_manual_override_detail(self) -> PassApplicationRequest:
        if self.reason_code is PassReasonCode.MANUAL_OVERRIDE and self.reason_detail is None:
            raise ValueError("人工覆盖 AI 建议时必须填写说明")
        return self


class BackupApplicationRequest(BaseModel):
    reason_code: BackupReasonCode
    reason_detail: OptionalReasonDetail | None = None

    model_config = ConfigDict(extra="forbid")


class RejectApplicationRequest(BaseModel):
    reason_code: RejectReasonCode
    reason_detail: OptionalReasonDetail | None = None
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_confirmation(self) -> RejectApplicationRequest:
        if not self.confirmed:
            raise ValueError("淘汰申请必须二次确认")
        return self


class ReverseDecisionRequest(BaseModel):
    reason_code: DecisionReversalReasonCode
    reason_detail: RequiredReasonDetail

    model_config = ConfigDict(extra="forbid")


class VoidApplicationRequest(BaseModel):
    reason_code: VoidReasonCode
    reason_detail: OptionalReasonDetail | None = None
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_confirmation(self) -> VoidApplicationRequest:
        if not self.confirmed:
            raise ValueError("作废申请必须二次确认")
        return self


class StageHistoryCreate(BaseModel):
    application_id: PositiveId
    from_recruitment_stage: RecruitmentStage | None
    to_recruitment_stage: RecruitmentStage
    from_hr_decision: HRDecision | None
    to_hr_decision: HRDecision
    reason_code: StageHistoryReasonCode
    reason_detail: OptionalReasonDetail | None = None
    actor_type: StageHistoryActorType
    actor_id: str | None = Field(default=None, max_length=100)
    actor_label: ActorLabel
    screening_result_id: PositiveId | None = None
    overrides_ai_recommendation: StrictBool = False

    model_config = ConfigDict(extra="forbid")


class StageHistoryRead(StageHistoryCreate):
    id: PositiveId
    created_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


__all__ = [
    "BackupApplicationRequest",
    "BackupReasonCode",
    "DecisionReversalReasonCode",
    "PassApplicationRequest",
    "PassReasonCode",
    "RejectApplicationRequest",
    "RejectReasonCode",
    "ReverseDecisionRequest",
    "StageHistoryActorType",
    "StageHistoryCreate",
    "StageHistoryRead",
    "StageHistoryReasonCode",
    "VoidApplicationRequest",
    "VoidReasonCode",
]
