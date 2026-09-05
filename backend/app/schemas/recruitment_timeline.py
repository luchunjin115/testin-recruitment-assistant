from __future__ import annotations

from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.schemas.application import (
    ApplicationLifecycleStatus,
    FinalOutcome,
    HRDecision,
    PositiveId,
    RecruitmentStage,
)
from app.schemas.interview import InterviewDecision, InterviewStatus
from app.schemas.offer import OfferStatus
from app.schemas.stage_history import OptionalReasonDetail, StageHistoryActorType


class RecruitmentTimelineSource(str, Enum):
    STAGE_HISTORY = "stage_history"
    ACTIVITY_LOG = "activity_log"


class RecruitmentTimelineItem(BaseModel):
    source: RecruitmentTimelineSource
    source_id: PositiveId
    event_type: str
    application_id: PositiveId
    interview_record_id: PositiveId | None = None
    offer_record_id: PositiveId | None = None
    from_lifecycle_status: ApplicationLifecycleStatus | None = None
    to_lifecycle_status: ApplicationLifecycleStatus | None = None
    from_recruitment_stage: RecruitmentStage | None = None
    to_recruitment_stage: RecruitmentStage | None = None
    from_hr_decision: HRDecision | None = None
    to_hr_decision: HRDecision | None = None
    from_final_outcome: FinalOutcome | None = None
    to_final_outcome: FinalOutcome | None = None
    from_interview_status: InterviewStatus | None = None
    to_interview_status: InterviewStatus | None = None
    from_interview_decision: InterviewDecision | None = None
    to_interview_decision: InterviewDecision | None = None
    from_offer_status: OfferStatus | None = None
    to_offer_status: OfferStatus | None = None
    from_scheduled_start_at: AwareDatetime | None = None
    to_scheduled_start_at: AwareDatetime | None = None
    from_version: int | None = None
    to_version: int | None = None
    reason_code: str
    reason_detail: OptionalReasonDetail | None = None
    actor_type: StageHistoryActorType
    actor_label: str
    occurred_at: AwareDatetime

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "RecruitmentTimelineItem",
    "RecruitmentTimelineSource",
]
