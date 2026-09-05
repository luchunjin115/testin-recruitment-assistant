from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

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

from app.schemas.application import PositiveId
from app.schemas.stage_history import RequiredReasonDetail


class OfferStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class SalaryPeriod(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class OfferSendReasonCode(str, Enum):
    SENT = "offer_sent"


class OfferAcceptReasonCode(str, Enum):
    ACCEPTED = "offer_accepted"


class OfferDeclineReasonCode(str, Enum):
    DECLINED = "offer_declined"


class OfferWithdrawReasonCode(str, Enum):
    WITHDRAWN = "offer_withdrawn"


class OfferExpireReasonCode(str, Enum):
    EXPIRED = "offer_expired"


class AdmissionReasonCode(str, Enum):
    ADMITTED = "application_admitted"


class HireReasonCode(str, Enum):
    HIRED = "application_hired"


class CandidateWithdrawReasonCode(str, Enum):
    WITHDREW = "candidate_withdrew"


class CompanyCancelReasonCode(str, Enum):
    CANCELED = "company_canceled"


class Stage9ReopenReasonCode(str, Enum):
    REOPENED = "stage9_reopened"


PositionTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=200),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        strict=True,
        pattern=r"^[A-Z]{3}$",
    ),
]
OptionalCompensationNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=5_000),
]
OptionalOfferNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=2_000),
]
ExpectedVersion = Annotated[StrictInt, Field(ge=1)]


class OfferDetails(BaseModel):
    position_title: PositionTitle
    currency: CurrencyCode
    salary_period: SalaryPeriod
    base_salary_amount: Decimal = Field(
        gt=Decimal("0"),
        max_digits=14,
        decimal_places=2,
    )
    salary_months: Decimal | None = Field(
        default=None,
        ge=Decimal("1"),
        le=Decimal("24"),
        max_digits=4,
        decimal_places=1,
    )
    bonus_note: OptionalCompensationNote | None = None
    benefits_note: OptionalCompensationNote | None = None
    valid_until: date
    expected_start_date: date
    note: OptionalOfferNote | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("base_salary_amount", "salary_months", mode="before")
    @classmethod
    def reject_binary_float(cls, value: Any) -> Any:
        if isinstance(value, (float, bool)):
            raise ValueError("金额必须使用精确 Decimal 值，不能使用 float")
        return value

    @model_validator(mode="after")
    def validate_compensation_and_dates(self) -> OfferDetails:
        if self.salary_period is SalaryPeriod.MONTHLY and self.salary_months is None:
            raise ValueError("月薪制必须填写 salary_months")
        if self.salary_period is SalaryPeriod.ANNUAL and self.salary_months is not None:
            raise ValueError("年薪制不能填写 salary_months")
        if self.expected_start_date < self.valid_until:
            raise ValueError("预计入职日期不能早于 Offer 有效截止日期")
        return self


class OfferDraftCreateRequest(OfferDetails):
    pass


class OfferUpdateRequest(OfferDetails):
    expected_version: ExpectedVersion
    confirmed: StrictBool = False
    correction_reason: RequiredReasonDetail | None = None


class OfferRecordCreate(OfferDetails):
    application_id: PositiveId
    version_number: ExpectedVersion
    status: OfferStatus = OfferStatus.DRAFT
    sent_at: AwareDatetime | None = None
    responded_at: AwareDatetime | None = None
    closed_at: AwareDatetime | None = None
    version: ExpectedVersion = 1

    @model_validator(mode="after")
    def validate_status_timestamps(self) -> OfferRecordCreate:
        if self.status is OfferStatus.DRAFT:
            if any((self.sent_at, self.responded_at, self.closed_at)):
                raise ValueError("Offer 草稿不能包含发送、回复或关闭时间")
        elif self.status is OfferStatus.SENT:
            if self.sent_at is None or self.responded_at or self.closed_at:
                raise ValueError("已发送 Offer 的时间字段组合无效")
        elif self.status in {OfferStatus.ACCEPTED, OfferStatus.DECLINED}:
            if self.sent_at is None or self.responded_at is None or self.closed_at:
                raise ValueError("已回复 Offer 的时间字段组合无效")
        elif self.status in {OfferStatus.WITHDRAWN, OfferStatus.EXPIRED}:
            if self.sent_at is None or self.closed_at is None or self.responded_at:
                raise ValueError("已关闭 Offer 的时间字段组合无效")

        if self.responded_at and self.sent_at and self.responded_at < self.sent_at:
            raise ValueError("候选人回复时间不能早于发送时间")
        if self.closed_at and self.sent_at and self.closed_at < self.sent_at:
            raise ValueError("Offer 关闭时间不能早于发送时间")
        return self


class OfferRecordRead(OfferRecordCreate):
    id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class OfferSendRequest(BaseModel):
    expected_version: ExpectedVersion
    reason_code: OfferSendReasonCode
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


class _ConfirmedOfferActionRequest(BaseModel):
    expected_version: ExpectedVersion
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


class OfferAcceptRequest(_ConfirmedOfferActionRequest):
    reason_code: OfferAcceptReasonCode


class OfferDeclineRequest(_ConfirmedOfferActionRequest):
    reason_code: OfferDeclineReasonCode


class OfferWithdrawRequest(_ConfirmedOfferActionRequest):
    reason_code: OfferWithdrawReasonCode


class OfferExpireRequest(_ConfirmedOfferActionRequest):
    reason_code: OfferExpireReasonCode


class _ConfirmedApplicationOfferActionRequest(BaseModel):
    expected_version: ExpectedVersion
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


class ConfirmAdmissionRequest(_ConfirmedApplicationOfferActionRequest):
    reason_code: AdmissionReasonCode


class ConfirmHireRequest(_ConfirmedApplicationOfferActionRequest):
    reason_code: HireReasonCode


class _ConfirmedApplicationEndRequest(BaseModel):
    expected_version: ExpectedVersion | None = None
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


class CandidateWithdrawRequest(_ConfirmedApplicationEndRequest):
    reason_code: CandidateWithdrawReasonCode


class CompanyCancelRequest(_ConfirmedApplicationEndRequest):
    reason_code: CompanyCancelReasonCode


class Stage9ReopenRequest(BaseModel):
    expected_version: ExpectedVersion | None = None
    reason_code: Stage9ReopenReasonCode
    reason_detail: RequiredReasonDetail
    confirmed: StrictBool

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "AdmissionReasonCode",
    "CandidateWithdrawReasonCode",
    "CandidateWithdrawRequest",
    "CompanyCancelReasonCode",
    "CompanyCancelRequest",
    "ConfirmAdmissionRequest",
    "ConfirmHireRequest",
    "HireReasonCode",
    "OfferAcceptReasonCode",
    "OfferAcceptRequest",
    "OfferDeclineReasonCode",
    "OfferDeclineRequest",
    "OfferDraftCreateRequest",
    "OfferExpireReasonCode",
    "OfferExpireRequest",
    "OfferRecordCreate",
    "OfferRecordRead",
    "OfferSendReasonCode",
    "OfferSendRequest",
    "OfferStatus",
    "OfferUpdateRequest",
    "OfferWithdrawReasonCode",
    "OfferWithdrawRequest",
    "SalaryPeriod",
    "Stage9ReopenReasonCode",
    "Stage9ReopenRequest",
]
