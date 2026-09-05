from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)

from app.schemas.application import PositiveId
from app.schemas.stage_history import OptionalReasonDetail, RequiredReasonDetail


class InterviewType(str, Enum):
    ONSITE = "onsite"
    VIDEO = "video"
    PHONE = "phone"


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELED = "canceled"
    NO_SHOW = "no_show"


class InterviewDecision(str, Enum):
    PENDING = "pending"
    NEXT_ROUND = "next_round"
    PROCEED_OFFER = "proceed_offer"
    REJECTED = "rejected"
    CANDIDATE_WITHDREW = "candidate_withdrew"


class InterviewFeedbackReasonCode(str, Enum):
    ROUND_COMPLETED = "interview_round_completed"
    NEXT_ROUND = "interview_next_round"
    PROCEED_OFFER = "interview_proceed_offer"
    REJECTED = "interview_rejected"
    CANDIDATE_WITHDREW = "candidate_withdrew"


class InterviewCancelReasonCode(str, Enum):
    CANCELED = "interview_canceled"


class InterviewNoShowReasonCode(str, Enum):
    NO_SHOW = "interview_no_show"


class InterviewCorrectionReasonCode(str, Enum):
    CORRECTION = "stage9_correction"


def _validate_iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("必须使用有效 IANA 时区") from exc
    return value


InterviewerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
InterviewListItem = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=500),
]
InterviewTimezone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=3,
        max_length=100,
        pattern=r"^(?:UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+.-]+)+)$",
    ),
    AfterValidator(_validate_iana_timezone),
]
OptionalLocation = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=500),
]
OptionalScheduleNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=2_000),
]
OptionalFeedbackSummary = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=5_000),
]
FeedbackActorLabel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]


class InterviewScheduleFields(BaseModel):
    interview_type: InterviewType
    scheduled_start_at: AwareDatetime
    duration_minutes: Annotated[StrictInt, Field(ge=15, le=480)]
    timezone: InterviewTimezone = "Asia/Shanghai"
    interviewer_names: list[InterviewerName] = Field(min_length=1, max_length=10)
    location: OptionalLocation | None = None
    meeting_link: AnyHttpUrl | None = None
    schedule_note: OptionalScheduleNote | None = None

    model_config = ConfigDict(extra="forbid")


class InterviewScheduleCreate(InterviewScheduleFields):
    round_number: Annotated[StrictInt, Field(ge=1)]


class InterviewScheduleUpdate(InterviewScheduleFields):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    reason_detail: OptionalReasonDetail | None = None


class InterviewCancelRequest(BaseModel):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    reason_code: InterviewCancelReasonCode
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


class InterviewNoShowRequest(BaseModel):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    reason_code: InterviewNoShowReasonCode
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool
    end_application: StrictBool = False

    model_config = ConfigDict(extra="forbid")


class InterviewFeedbackContent(BaseModel):
    feedback_summary: OptionalFeedbackSummary
    strengths: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    concerns: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    follow_up_questions: list[InterviewListItem] = Field(
        default_factory=list,
        max_length=20,
    )
    decision: InterviewDecision

    model_config = ConfigDict(extra="forbid")


class InterviewFeedbackSubmitRequest(InterviewFeedbackContent):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    reason_code: InterviewFeedbackReasonCode
    reason_detail: OptionalReasonDetail | None = None
    confirmed: StrictBool = False


class InterviewFeedbackUpdateRequest(InterviewFeedbackContent):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    reason_code: InterviewCorrectionReasonCode
    correction_reason: RequiredReasonDetail
    confirmed: StrictBool


class InterviewRecordCreate(BaseModel):
    application_id: PositiveId
    round_number: Annotated[StrictInt, Field(ge=1)]
    interview_type: InterviewType
    status: InterviewStatus = InterviewStatus.SCHEDULED
    scheduled_start_at: AwareDatetime
    duration_minutes: Annotated[StrictInt, Field(ge=15, le=480)]
    timezone: InterviewTimezone = "Asia/Shanghai"
    interviewer_names: list[InterviewerName] = Field(min_length=1, max_length=10)
    location: OptionalLocation | None = None
    meeting_link: AnyHttpUrl | None = None
    schedule_note: OptionalScheduleNote | None = None
    decision: InterviewDecision = InterviewDecision.PENDING
    feedback_summary: OptionalFeedbackSummary | None = None
    strengths: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    concerns: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    follow_up_questions: list[InterviewListItem] = Field(
        default_factory=list,
        max_length=20,
    )
    feedback_submitted_by_label: FeedbackActorLabel | None = None
    feedback_submitted_at: AwareDatetime | None = None
    version: Annotated[StrictInt, Field(ge=1)] = 1

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_feedback_state(self) -> InterviewRecordCreate:
        has_feedback_content = bool(
            self.feedback_summary
            or self.strengths
            or self.concerns
            or self.follow_up_questions
        )
        has_feedback_audit = bool(
            self.feedback_submitted_by_label or self.feedback_submitted_at
        )
        has_feedback = has_feedback_content or has_feedback_audit

        if has_feedback:
            if self.status is not InterviewStatus.COMPLETED:
                raise ValueError("只有已完成面试可以保存反馈")
            if (
                self.feedback_summary is None
                or self.feedback_submitted_by_label is None
                or self.feedback_submitted_at is None
            ):
                raise ValueError("面试反馈必须同时包含总结、提交人和提交时间")

        if self.decision is not InterviewDecision.PENDING and not has_feedback:
            raise ValueError("非待决定结果必须来自已提交反馈")

        if self.status in {InterviewStatus.CANCELED, InterviewStatus.NO_SHOW}:
            if self.decision is not InterviewDecision.PENDING:
                raise ValueError("取消或未到场记录不能直接写面试决定")
        return self


class InterviewRecordRead(InterviewRecordCreate):
    id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class InterviewRecordListItem(BaseModel):
    id: PositiveId
    application_id: PositiveId
    round_number: Annotated[StrictInt, Field(ge=1)]
    interview_type: InterviewType
    status: InterviewStatus
    scheduled_start_at: AwareDatetime
    duration_minutes: Annotated[StrictInt, Field(ge=15, le=480)]
    timezone: InterviewTimezone
    interviewer_names: list[InterviewerName] = Field(min_length=1, max_length=10)
    location: OptionalLocation | None = None
    decision: InterviewDecision
    feedback_summary: OptionalFeedbackSummary | None = None
    strengths: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    concerns: list[InterviewListItem] = Field(default_factory=list, max_length=20)
    follow_up_questions: list[InterviewListItem] = Field(
        default_factory=list,
        max_length=20,
    )
    feedback_submitted_by_label: FeedbackActorLabel | None = None
    feedback_submitted_at: AwareDatetime | None = None
    version: Annotated[StrictInt, Field(ge=1)]
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


__all__ = [
    "InterviewCancelReasonCode",
    "InterviewCancelRequest",
    "InterviewCorrectionReasonCode",
    "InterviewDecision",
    "InterviewFeedbackReasonCode",
    "InterviewFeedbackSubmitRequest",
    "InterviewFeedbackUpdateRequest",
    "InterviewNoShowReasonCode",
    "InterviewNoShowRequest",
    "InterviewRecordCreate",
    "InterviewRecordListItem",
    "InterviewRecordRead",
    "InterviewScheduleCreate",
    "InterviewScheduleUpdate",
    "InterviewStatus",
    "InterviewType",
]
