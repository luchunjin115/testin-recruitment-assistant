from __future__ import annotations

from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictFloat, StrictInt


class RecruitmentFunnelKey(str, Enum):
    APPLICATIONS = "applications"
    SCREENING_PASSED = "screening_passed"
    INTERVIEW_ENTERED = "interview_entered"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    ADMITTED = "admitted"
    HIRED = "hired"


class RecruitmentDurationKey(str, Enum):
    APPLICATION_TO_SCREENING_PASSED = "application_to_screening_passed"
    SCREENING_PASSED_TO_FIRST_INTERVIEW = "screening_passed_to_first_interview"
    FIRST_INTERVIEW_TO_LAST_COMPLETED = "first_interview_to_last_completed"
    OFFER_ENTERED_TO_SENT = "offer_entered_to_sent"
    OFFER_SENT_TO_RESPONSE = "offer_sent_to_response"
    OFFER_ACCEPTED_TO_ADMITTED = "offer_accepted_to_admitted"
    ADMITTED_TO_HIRED = "admitted_to_hired"


class RecruitmentStatisticsCohort(BaseModel):
    job_id: StrictInt | None = Field(default=None, ge=1)
    applied_from: AwareDatetime | None = None
    applied_to: AwareDatetime | None = None

    model_config = ConfigDict(extra="forbid")


class RecruitmentFunnelStep(BaseModel):
    key: RecruitmentFunnelKey
    count: StrictInt = Field(ge=0)
    conversion_rate: StrictFloat | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class RecruitmentDurationMetric(BaseModel):
    key: RecruitmentDurationKey
    average_hours: StrictFloat | None = Field(default=None, ge=0)
    sample_count: StrictInt = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class RecruitmentTodoSnapshot(BaseModel):
    scheduled_interviews: StrictInt = Field(ge=0)
    pending_interview_decisions: StrictInt = Field(ge=0)
    next_round_not_scheduled: StrictInt = Field(ge=0)
    draft_offers: StrictInt = Field(ge=0)
    sent_offers: StrictInt = Field(ge=0)
    accepted_offers: StrictInt = Field(ge=0)
    admitted_applications: StrictInt = Field(ge=0)
    total: StrictInt = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class RecruitmentStatisticsRead(BaseModel):
    cohort: RecruitmentStatisticsCohort
    funnel: list[RecruitmentFunnelStep] = Field(min_length=8, max_length=8)
    durations: list[RecruitmentDurationMetric] = Field(min_length=7, max_length=7)
    todos: RecruitmentTodoSnapshot
    generated_at: AwareDatetime

    model_config = ConfigDict(extra="forbid")


__all__ = [name for name in globals() if name.startswith("Recruitment")]
