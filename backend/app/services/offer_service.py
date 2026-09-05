from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.interview_record import InterviewRecord
from app.models.offer_record import OfferRecord
from app.models.screening_report import ScreeningReport
from app.models.stage_history import StageHistory
from app.schemas.offer import (
    CandidateWithdrawRequest,
    CompanyCancelRequest,
    ConfirmAdmissionRequest,
    ConfirmHireRequest,
    OfferAcceptRequest,
    OfferDeclineRequest,
    OfferDraftCreateRequest,
    OfferExpireRequest,
    OfferSendRequest,
    OfferUpdateRequest,
    OfferWithdrawRequest,
    Stage9ReopenRequest,
)
from app.services.interview_service import (
    ApplicationNotFoundError,
    ApplicationPipelineEndedError,
    HRActionConfirmationRequiredError,
    HRActionReasonRequiredError,
    InterviewVersionConflictError,
    LOCAL_HR_ACTOR_LABEL,
)


OFFER_ACTIVE_UNIQUE_INDEX = "uq_offer_records_one_active_per_application"
OFFER_VERSION_UNIQUE_CONSTRAINT = "uq_offer_records_application_version"
ACTIVE_APPLICATION_UNIQUE_INDEX = "uq_applications_active_candidate_job"
ACTIVE_OFFER_STATUSES = {"draft", "sent", "accepted"}
STAGE9_ACTIVE_STAGES = {
    "screening_passed",
    "interview",
    "offer",
    "offer_accepted",
    "admitted",
}
OFFER_TERMINAL_OUTCOMES = {
    "offer_declined": "declined",
    "offer_withdrawn": "withdrawn",
    "offer_expired": "expired",
}


class OfferPipelineError(ValueError):
    pass


class OfferNotFoundError(OfferPipelineError):
    pass


class OfferActiveConflictError(OfferPipelineError):
    pass


class OfferTransitionInvalidError(OfferPipelineError):
    pass


class OfferVersionConflictError(OfferPipelineError):
    pass


class OfferCompensationInvalidError(OfferPipelineError):
    pass


class ApplicationReopenInvalidError(OfferPipelineError):
    pass


@dataclass(frozen=True)
class _ApplicationState:
    lifecycle_status: str
    recruitment_stage: str
    hr_decision: str
    final_outcome: str | None

    @classmethod
    def from_application(cls, application: Application) -> _ApplicationState:
        return cls(
            application.lifecycle_status,
            application.recruitment_stage,
            application.hr_decision,
            application.final_outcome,
        )


class OfferService:
    async def list_offers(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> list[OfferRecord]:
        application = await db.get(Application, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")
        result = await db.scalars(
            select(OfferRecord)
            .where(OfferRecord.application_id == application_id)
            .order_by(OfferRecord.version_number.desc(), OfferRecord.id.desc())
        )
        return list(result.all())

    async def create_offer(
        self,
        db: AsyncSession,
        application_id: int,
        data: OfferDraftCreateRequest,
    ) -> OfferRecord:
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            self._require_active_offer_stage(application)
            offers = list(
                (
                    await db.scalars(
                        select(OfferRecord)
                        .where(OfferRecord.application_id == application_id)
                        .order_by(OfferRecord.version_number, OfferRecord.id)
                        .with_for_update()
                    )
                ).all()
            )
            active = next(
                (item for item in offers if item.status in ACTIVE_OFFER_STATUSES),
                None,
            )
            if active is not None:
                if active.status == "draft" and self._same_offer_details(active, data):
                    await db.commit()
                    return active
                raise OfferActiveConflictError("已经存在活动 Offer")

            offer = OfferRecord(
                application_id=application_id,
                version_number=max(
                    (item.version_number for item in offers), default=0
                )
                + 1,
                status="draft",
                version=1,
                **self._offer_values(data),
            )
            db.add(offer)
            await db.flush()
            await self._add_offer_activity(
                db,
                offer=offer,
                action="offer_created",
                reason_code="offer_created",
                reason_detail=None,
                changes={
                    "to_status": "draft",
                    "version_number": offer.version_number,
                    "to_version": 1,
                },
            )
            await db.commit()
            await db.refresh(offer)
            return offer
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) in {
                OFFER_ACTIVE_UNIQUE_INDEX,
                OFFER_VERSION_UNIQUE_CONSTRAINT,
            }:
                raise OfferActiveConflictError("已经存在活动 Offer") from exc
            raise
        except Exception:
            await db.rollback()
            raise

    async def update_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferUpdateRequest,
    ) -> OfferRecord:
        try:
            application, offer = await self._get_context_for_update(db, offer_id)
            self._require_active_offer_stage(application)
            if offer.status not in {"draft", "sent"}:
                raise OfferTransitionInvalidError("当前 Offer 状态不能编辑")

            values = self._offer_values(data)
            if offer.version != data.expected_version:
                if self._same_offer_details(offer, data) and await self._latest_offer_update_matches(
                    db,
                    offer,
                    expected_version=data.expected_version,
                    reason_detail=(
                        data.correction_reason if offer.status == "sent" else None
                    ),
                ):
                    await db.commit()
                    return offer
                self._require_version(offer, data.expected_version)
            changed_fields = [
                key for key, value in values.items() if getattr(offer, key) != value
            ]
            if not changed_fields:
                await db.commit()
                return offer
            if offer.status == "sent":
                self._require_confirmation(data.confirmed)
                self._require_reason(data.correction_reason)

            from_version = offer.version
            for key, value in values.items():
                setattr(offer, key, value)
            offer.version += 1
            await self._add_offer_activity(
                db,
                offer=offer,
                action=("stage9_correction" if offer.status == "sent" else "offer_updated"),
                reason_code=("stage9_correction" if offer.status == "sent" else "offer_updated"),
                reason_detail=(data.correction_reason if offer.status == "sent" else None),
                changes={
                    "from_status": offer.status,
                    "to_status": offer.status,
                    "from_version": from_version,
                    "to_version": offer.version,
                    "changed_fields": sorted(changed_fields),
                },
            )
            await db.commit()
            await db.refresh(offer)
            return offer
        except Exception:
            await db.rollback()
            raise

    async def send_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferSendRequest,
    ) -> OfferRecord:
        return await self._transition_offer(
            db,
            offer_id,
            data=data,
            target_status="sent",
            target_application=None,
        )

    async def accept_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferAcceptRequest,
    ) -> OfferRecord:
        return await self._transition_offer(
            db,
            offer_id,
            data=data,
            target_status="accepted",
            target_application=_ApplicationState(
                "active", "offer_accepted", "passed", None
            ),
        )

    async def decline_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferDeclineRequest,
    ) -> OfferRecord:
        return await self._transition_offer(
            db,
            offer_id,
            data=data,
            target_status="declined",
            target_application=_ApplicationState(
                "ended", "offer", "passed", "offer_declined"
            ),
        )

    async def withdraw_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferWithdrawRequest,
    ) -> OfferRecord:
        return await self._transition_offer(
            db,
            offer_id,
            data=data,
            target_status="withdrawn",
            target_application=_ApplicationState(
                "ended", "offer", "passed", "offer_withdrawn"
            ),
        )

    async def expire_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        data: OfferExpireRequest,
    ) -> OfferRecord:
        return await self._transition_offer(
            db,
            offer_id,
            data=data,
            target_status="expired",
            target_application=_ApplicationState(
                "ended", "offer", "passed", "offer_expired"
            ),
        )

    async def confirm_admission(
        self,
        db: AsyncSession,
        application_id: int,
        data: ConfirmAdmissionRequest,
    ) -> Application:
        return await self._confirm_application_milestone(
            db,
            application_id,
            data=data,
            expected_stage="offer_accepted",
            target=_ApplicationState("active", "admitted", "passed", None),
        )

    async def confirm_hire(
        self,
        db: AsyncSession,
        application_id: int,
        data: ConfirmHireRequest,
    ) -> Application:
        return await self._confirm_application_milestone(
            db,
            application_id,
            data=data,
            expected_stage="admitted",
            target=_ApplicationState("ended", "hired", "passed", "hired"),
        )

    async def withdraw_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: CandidateWithdrawRequest,
    ) -> Application:
        return await self._end_application(
            db,
            application_id,
            data=data,
            final_outcome="candidate_withdrew",
        )

    async def cancel_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: CompanyCancelRequest,
    ) -> Application:
        return await self._end_application(
            db,
            application_id,
            data=data,
            final_outcome="company_canceled",
        )

    async def reopen_stage9(
        self,
        db: AsyncSession,
        application_id: int,
        data: Stage9ReopenRequest,
    ) -> Application:
        self._require_confirmation(data.confirmed)
        self._require_reason(data.reason_detail)
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            if await self._latest_application_activity_matches(
                db,
                application,
                action="stage9_reopened",
                reason_detail=data.reason_detail,
                expected_version=data.expected_version,
            ):
                await db.commit()
                return application

            source = _ApplicationState.from_application(application)
            if application.lifecycle_status == "ended":
                other = await self._get_other_active_application_for_update(
                    db, application
                )
                if other is not None:
                    raise ApplicationReopenInvalidError(
                        "同一 Candidate 和 Job 已有其他有效 Application"
                    )

            history = await self._supporting_history_for_reopen(db, application)
            offer: OfferRecord | None = None
            interview: InterviewRecord | None = None
            changes: dict = {"requested_expected_version": data.expected_version}

            if (
                source.lifecycle_status == "active"
                and source.recruitment_stage == "offer_accepted"
                and source.final_outcome is None
            ):
                offer = await self._offer_from_history_for_update(db, history)
                self._require_offer_status(offer, "accepted")
                self._require_optional_version(offer, data.expected_version)
                from_responded_at = offer.responded_at
                from_version = offer.version
                offer.status = "sent"
                offer.responded_at = None
                offer.version += 1
                target = _ApplicationState("active", "offer", "passed", None)
                changes.update(
                    {
                        "offer_record_id": offer.id,
                        "from_offer_status": "accepted",
                        "to_offer_status": "sent",
                        "from_version": from_version,
                        "to_version": offer.version,
                        "from_responded_at": (
                            from_responded_at.isoformat()
                            if from_responded_at is not None
                            else None
                        ),
                    }
                )
            elif (
                source.lifecycle_status == "active"
                and source.recruitment_stage == "admitted"
                and source.final_outcome is None
            ):
                offer = await self._offer_from_history_for_update(db, history)
                self._require_offer_status(offer, "accepted")
                self._require_optional_version(offer, data.expected_version)
                target = _ApplicationState(
                    "active", "offer_accepted", "passed", None
                )
            elif (
                source.lifecycle_status == "ended"
                and source.recruitment_stage == "hired"
                and source.final_outcome == "hired"
            ):
                offer = await self._offer_from_history_for_update(db, history)
                self._require_offer_status(offer, "accepted")
                self._require_optional_version(offer, data.expected_version)
                target = _ApplicationState("active", "admitted", "passed", None)
            elif (
                source.lifecycle_status == "ended"
                and source.final_outcome in OFFER_TERMINAL_OUTCOMES
            ):
                offer = await self._offer_from_history_for_update(db, history)
                self._require_offer_status(
                    offer, OFFER_TERMINAL_OUTCOMES[source.final_outcome]
                )
                self._require_optional_version(offer, data.expected_version)
                target = _ApplicationState("active", "offer", "passed", None)
            elif (
                source.lifecycle_status == "ended"
                and source.final_outcome == "interview_rejected"
            ):
                interview = await self._interview_from_history_for_update(db, history)
                if interview.status != "completed" or interview.decision != "rejected":
                    raise ApplicationReopenInvalidError("面试支撑记录不匹配")
                self._require_optional_interview_version(
                    interview, data.expected_version
                )
                from_version = interview.version
                interview.decision = "pending"
                interview.version += 1
                target = _ApplicationState("active", "interview", "passed", None)
                changes.update(
                    {
                        "interview_record_id": interview.id,
                        "from_interview_decision": "rejected",
                        "to_interview_decision": "pending",
                        "from_version": from_version,
                        "to_version": interview.version,
                    }
                )
            elif (
                source.lifecycle_status == "ended"
                and source.final_outcome == "interview_no_show"
            ):
                interview = await self._interview_from_history_for_update(db, history)
                if interview.status != "no_show":
                    raise ApplicationReopenInvalidError("未到场支撑记录不匹配")
                self._require_optional_interview_version(
                    interview, data.expected_version
                )
                target = _ApplicationState("active", "interview", "passed", None)
            elif (
                source.lifecycle_status == "ended"
                and source.final_outcome
                in {"candidate_withdrew", "company_canceled"}
            ):
                target, offer, interview, restored_changes = (
                    await self._restore_pre_end_stage(
                        db,
                        application,
                        history,
                        expected_version=data.expected_version,
                    )
                )
                changes.update(restored_changes)
            else:
                raise ApplicationReopenInvalidError(
                    "当前结果不允许使用阶段 9 重新打开"
                )

            new_history = await self._transition_application(
                db,
                application,
                target=target,
                reason_code=data.reason_code.value,
                reason_detail=data.reason_detail,
                offer=offer,
                interview=interview,
            )
            await self._add_application_activity(
                db,
                application=application,
                action="stage9_reopened",
                reason_code=data.reason_code.value,
                reason_detail=data.reason_detail,
                history=new_history,
                source=source,
                target=target,
                offer=offer,
                interview=interview,
                changes=changes,
            )
            await db.commit()
            await db.refresh(application)
            return application
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) == ACTIVE_APPLICATION_UNIQUE_INDEX:
                raise ApplicationReopenInvalidError(
                    "同一 Candidate 和 Job 已有其他有效 Application"
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    async def _transition_offer(
        self,
        db: AsyncSession,
        offer_id: int,
        *,
        data: OfferSendRequest
        | OfferAcceptRequest
        | OfferDeclineRequest
        | OfferWithdrawRequest
        | OfferExpireRequest,
        target_status: str,
        target_application: _ApplicationState | None,
    ) -> OfferRecord:
        self._require_confirmation(data.confirmed)
        self._require_reason(data.reason_detail)
        reason_code = data.reason_code.value
        try:
            application, offer = await self._get_context_for_update(db, offer_id)
            if offer.status == target_status:
                if await self._latest_offer_activity_matches(
                    db,
                    offer,
                    action=reason_code,
                    reason_detail=data.reason_detail,
                    expected_version=data.expected_version,
                ):
                    await db.commit()
                    return offer
                self._require_version(offer, data.expected_version)
                raise OfferTransitionInvalidError("Offer 已处于目标状态")

            self._require_active_offer_stage(application)
            self._require_version(offer, data.expected_version)
            expected_source = "draft" if target_status == "sent" else "sent"
            if offer.status != expected_source:
                raise OfferTransitionInvalidError("当前 Offer 状态不允许该转换")
            if target_status in {"sent", "accepted"} and self._is_past_valid_until(
                offer
            ):
                raise OfferTransitionInvalidError(
                    "Offer 已超过有效期，必须由 HR 明确标记过期"
                )
            if target_status == "expired" and not self._is_past_valid_until(offer):
                raise OfferTransitionInvalidError("Offer 尚未超过有效期")

            source = _ApplicationState.from_application(application)
            from_version = offer.version
            offer.status = target_status
            now = datetime.now(timezone.utc)
            if target_status == "sent":
                offer.sent_at = now
            elif target_status in {"accepted", "declined"}:
                offer.responded_at = now
            else:
                offer.closed_at = now
            offer.version += 1

            history: StageHistory | None = None
            if target_application is not None:
                history = await self._transition_application(
                    db,
                    application,
                    target=target_application,
                    reason_code=reason_code,
                    reason_detail=data.reason_detail,
                    offer=offer,
                )
            await self._add_offer_activity(
                db,
                offer=offer,
                action=reason_code,
                reason_code=reason_code,
                reason_detail=data.reason_detail,
                history=history,
                changes={
                    "from_status": expected_source,
                    "to_status": target_status,
                    "from_version": from_version,
                    "to_version": offer.version,
                    "from_recruitment_stage": source.recruitment_stage,
                    "to_recruitment_stage": (
                        target_application.recruitment_stage
                        if target_application is not None
                        else source.recruitment_stage
                    ),
                },
            )
            await db.commit()
            await db.refresh(offer)
            return offer
        except Exception:
            await db.rollback()
            raise

    async def _confirm_application_milestone(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        data: ConfirmAdmissionRequest | ConfirmHireRequest,
        expected_stage: str,
        target: _ApplicationState,
    ) -> Application:
        self._require_confirmation(data.confirmed)
        self._require_reason(data.reason_detail)
        reason_code = data.reason_code.value
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            offer = await self._get_active_offer_for_update(db, application_id)
            if offer is None or offer.status != "accepted":
                raise OfferTransitionInvalidError("缺少已接受 Offer 支撑记录")
            if (
                application.lifecycle_status == target.lifecycle_status
                and application.recruitment_stage == target.recruitment_stage
                and application.final_outcome == target.final_outcome
                and await self._latest_application_activity_matches(
                    db,
                    application,
                    action=reason_code,
                    reason_detail=data.reason_detail,
                    expected_version=data.expected_version,
                )
            ):
                await db.commit()
                return application

            self._require_active_pipeline(application)
            if (
                application.recruitment_stage != expected_stage
                or application.hr_decision != "passed"
                or application.final_outcome is not None
            ):
                raise OfferTransitionInvalidError("当前 Application 阶段不允许该操作")
            self._require_version(offer, data.expected_version)
            source = _ApplicationState.from_application(application)
            history = await self._transition_application(
                db,
                application,
                target=target,
                reason_code=reason_code,
                reason_detail=data.reason_detail,
                offer=offer,
            )
            await self._add_application_activity(
                db,
                application=application,
                action=reason_code,
                reason_code=reason_code,
                reason_detail=data.reason_detail,
                history=history,
                source=source,
                target=target,
                offer=offer,
                changes={"requested_expected_version": data.expected_version},
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    async def _end_application(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        data: CandidateWithdrawRequest | CompanyCancelRequest,
        final_outcome: str,
    ) -> Application:
        self._require_confirmation(data.confirmed)
        self._require_reason(data.reason_detail)
        reason_code = data.reason_code.value
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            if (
                application.lifecycle_status == "ended"
                and application.final_outcome == final_outcome
                and await self._latest_application_activity_matches(
                    db,
                    application,
                    action=reason_code,
                    reason_detail=data.reason_detail,
                    expected_version=data.expected_version,
                )
            ):
                await db.commit()
                return application

            self._require_active_pipeline(application)
            if (
                application.hr_decision != "passed"
                or application.recruitment_stage not in STAGE9_ACTIVE_STAGES
                or application.final_outcome is not None
            ):
                raise OfferTransitionInvalidError("当前 Application 不能结束阶段 9 流程")

            offer = await self._get_active_offer_for_update(db, application_id)
            interview = (
                await self._get_latest_interview_for_update(db, application_id)
                if application.recruitment_stage == "interview"
                else None
            )
            if offer is not None:
                self._require_optional_version(offer, data.expected_version)
            elif interview is not None:
                self._require_optional_interview_version(
                    interview, data.expected_version
                )
            elif data.expected_version is not None:
                raise OfferVersionConflictError("当前没有可匹配的活动 Offer")

            source = _ApplicationState.from_application(application)
            target = _ApplicationState(
                "ended",
                application.recruitment_stage,
                "passed",
                final_outcome,
            )
            history = await self._transition_application(
                db,
                application,
                target=target,
                reason_code=reason_code,
                reason_detail=data.reason_detail,
                offer=offer,
                interview=interview,
            )
            await self._add_application_activity(
                db,
                application=application,
                action=reason_code,
                reason_code=reason_code,
                reason_detail=data.reason_detail,
                history=history,
                source=source,
                target=target,
                offer=offer,
                interview=interview,
                changes={"requested_expected_version": data.expected_version},
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    async def _restore_pre_end_stage(
        self,
        db: AsyncSession,
        application: Application,
        history: StageHistory,
        *,
        expected_version: int | None,
    ) -> tuple[_ApplicationState, OfferRecord | None, InterviewRecord | None, dict]:
        if (
            history.from_lifecycle_status != "active"
            or history.to_lifecycle_status != "ended"
            or history.to_final_outcome != application.final_outcome
            or history.from_recruitment_stage not in STAGE9_ACTIVE_STAGES
        ):
            raise ApplicationReopenInvalidError("结束历史不能支撑重新打开")

        stage = history.from_recruitment_stage
        offer: OfferRecord | None = None
        interview: InterviewRecord | None = None
        changes: dict = {}
        if history.offer_record_id is not None:
            offer = await self._offer_from_history_for_update(db, history)
            self._require_optional_version(offer, expected_version)
            changes["offer_record_id"] = offer.id
        elif stage in {"offer_accepted", "admitted"}:
            offer = await self._get_active_offer_for_update(db, application.id)
            if offer is None or offer.status != "accepted":
                raise ApplicationReopenInvalidError("缺少已接受 Offer 支撑记录")
            self._require_optional_version(offer, expected_version)
            changes["offer_record_id"] = offer.id
        elif history.interview_record_id is not None:
            interview = await self._interview_from_history_for_update(db, history)
            self._require_optional_interview_version(interview, expected_version)
            if (
                application.final_outcome == "candidate_withdrew"
                and interview.status == "completed"
                and interview.decision == "candidate_withdrew"
            ):
                from_version = interview.version
                interview.decision = "pending"
                interview.version += 1
                changes.update(
                    {
                        "interview_record_id": interview.id,
                        "from_interview_decision": "candidate_withdrew",
                        "to_interview_decision": "pending",
                        "from_version": from_version,
                        "to_version": interview.version,
                    }
                )
        elif expected_version is not None:
            raise ApplicationReopenInvalidError("当前重新打开不接受对象版本")

        return (
            _ApplicationState("active", stage, "passed", None),
            offer,
            interview,
            changes,
        )

    async def _supporting_history_for_reopen(
        self,
        db: AsyncSession,
        application: Application,
    ) -> StageHistory:
        conditions = [StageHistory.application_id == application.id]
        if application.lifecycle_status == "ended":
            conditions.extend(
                [
                    StageHistory.to_lifecycle_status == "ended",
                    StageHistory.to_final_outcome == application.final_outcome,
                ]
            )
        elif application.recruitment_stage == "offer_accepted":
            conditions.append(StageHistory.reason_code == "offer_accepted")
        elif application.recruitment_stage == "admitted":
            conditions.append(StageHistory.reason_code == "application_admitted")
        else:
            raise ApplicationReopenInvalidError("当前状态没有可更正历史")
        history = await db.scalar(
            select(StageHistory)
            .where(*conditions)
            .order_by(StageHistory.created_at.desc(), StageHistory.id.desc())
            .limit(1)
        )
        if history is None:
            raise ApplicationReopenInvalidError("缺少重新打开支撑历史")
        return history

    @staticmethod
    async def _transition_application(
        db: AsyncSession,
        application: Application,
        *,
        target: _ApplicationState,
        reason_code: str,
        reason_detail: str | None,
        offer: OfferRecord | None = None,
        interview: InterviewRecord | None = None,
    ) -> StageHistory:
        source = _ApplicationState.from_application(application)
        application.lifecycle_status = target.lifecycle_status
        application.recruitment_stage = target.recruitment_stage
        application.hr_decision = target.hr_decision
        application.final_outcome = target.final_outcome
        report_id = await db.scalar(
            select(ScreeningReport.id).where(
                ScreeningReport.application_id == application.id,
                ScreeningReport.is_current.is_(True),
            )
        )
        history = StageHistory(
            application_id=application.id,
            report_id=report_id,
            interview_record_id=interview.id if interview is not None else None,
            offer_record_id=offer.id if offer is not None else None,
            from_lifecycle_status=source.lifecycle_status,
            to_lifecycle_status=target.lifecycle_status,
            from_recruitment_stage=source.recruitment_stage,
            to_recruitment_stage=target.recruitment_stage,
            from_hr_decision=source.hr_decision,
            to_hr_decision=target.hr_decision,
            from_final_outcome=source.final_outcome,
            to_final_outcome=target.final_outcome,
            reason_code=reason_code,
            reason_detail=reason_detail,
            actor_type="hr",
            actor_id=None,
            actor_label=LOCAL_HR_ACTOR_LABEL,
        )
        db.add(history)
        await db.flush()
        return history

    @staticmethod
    async def _add_offer_activity(
        db: AsyncSession,
        *,
        offer: OfferRecord,
        action: str,
        reason_code: str,
        reason_detail: str | None,
        changes: dict,
        history: StageHistory | None = None,
    ) -> None:
        db.add(
            ActivityLog(
                user_id=None,
                action=action,
                target_type="offer",
                target_id=offer.id,
                detail={
                    "application_id": offer.application_id,
                    "offer_record_id": offer.id,
                    "reason_code": reason_code,
                    "reason_detail": reason_detail,
                    "actor_type": "hr",
                    "actor_label": LOCAL_HR_ACTOR_LABEL,
                    "stage_history_id": history.id if history is not None else None,
                    **changes,
                },
            )
        )
        await db.flush()

    @staticmethod
    async def _add_application_activity(
        db: AsyncSession,
        *,
        application: Application,
        action: str,
        reason_code: str,
        reason_detail: str,
        history: StageHistory,
        source: _ApplicationState,
        target: _ApplicationState,
        changes: dict,
        offer: OfferRecord | None = None,
        interview: InterviewRecord | None = None,
    ) -> None:
        db.add(
            ActivityLog(
                user_id=None,
                action=action,
                target_type="application",
                target_id=application.id,
                detail={
                    "application_id": application.id,
                    "offer_record_id": offer.id if offer is not None else None,
                    "interview_record_id": (
                        interview.id if interview is not None else None
                    ),
                    "reason_code": reason_code,
                    "reason_detail": reason_detail,
                    "actor_type": "hr",
                    "actor_label": LOCAL_HR_ACTOR_LABEL,
                    "stage_history_id": history.id,
                    "from_lifecycle_status": source.lifecycle_status,
                    "to_lifecycle_status": target.lifecycle_status,
                    "from_recruitment_stage": source.recruitment_stage,
                    "to_recruitment_stage": target.recruitment_stage,
                    "from_hr_decision": source.hr_decision,
                    "to_hr_decision": target.hr_decision,
                    "from_final_outcome": source.final_outcome,
                    "to_final_outcome": target.final_outcome,
                    **changes,
                },
            )
        )
        await db.flush()

    async def _latest_offer_activity_matches(
        self,
        db: AsyncSession,
        offer: OfferRecord,
        *,
        action: str,
        reason_detail: str,
        expected_version: int,
    ) -> bool:
        activity = await db.scalar(
            select(ActivityLog)
            .where(
                ActivityLog.target_type == "offer",
                ActivityLog.target_id == offer.id,
                ActivityLog.action == action,
            )
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(1)
        )
        if activity is None or not isinstance(activity.detail, dict):
            return False
        detail = activity.detail
        return (
            detail.get("reason_code") == action
            and detail.get("reason_detail") == reason_detail
            and expected_version
            in {detail.get("from_version"), detail.get("to_version")}
        )

    async def _latest_offer_update_matches(
        self,
        db: AsyncSession,
        offer: OfferRecord,
        *,
        expected_version: int,
        reason_detail: str | None,
    ) -> bool:
        action = "stage9_correction" if offer.status == "sent" else "offer_updated"
        activity = await db.scalar(
            select(ActivityLog)
            .where(
                ActivityLog.target_type == "offer",
                ActivityLog.target_id == offer.id,
                ActivityLog.action == action,
            )
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(1)
        )
        if activity is None or not isinstance(activity.detail, dict):
            return False
        detail = activity.detail
        return (
            detail.get("reason_detail") == reason_detail
            and detail.get("from_version") == expected_version
            and detail.get("to_version") == offer.version
        )

    async def _latest_application_activity_matches(
        self,
        db: AsyncSession,
        application: Application,
        *,
        action: str,
        reason_detail: str,
        expected_version: int | None,
    ) -> bool:
        activity = await db.scalar(
            select(ActivityLog)
            .where(
                ActivityLog.target_type == "application",
                ActivityLog.target_id == application.id,
                ActivityLog.action == action,
            )
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(1)
        )
        if activity is None or not isinstance(activity.detail, dict):
            return False
        detail = activity.detail
        return (
            detail.get("reason_code") == action
            and detail.get("reason_detail") == reason_detail
            and detail.get("requested_expected_version") == expected_version
            and detail.get("to_lifecycle_status") == application.lifecycle_status
            and detail.get("to_recruitment_stage") == application.recruitment_stage
            and detail.get("to_hr_decision") == application.hr_decision
            and detail.get("to_final_outcome") == application.final_outcome
        )

    @staticmethod
    def _offer_values(data: OfferDraftCreateRequest | OfferUpdateRequest) -> dict:
        return {
            "position_title": data.position_title,
            "currency": data.currency,
            "salary_period": data.salary_period.value,
            "base_salary_amount": data.base_salary_amount,
            "salary_months": data.salary_months,
            "bonus_note": data.bonus_note,
            "benefits_note": data.benefits_note,
            "valid_until": data.valid_until,
            "expected_start_date": data.expected_start_date,
            "note": data.note,
        }

    @staticmethod
    def _same_offer_details(
        offer: OfferRecord,
        data: OfferDraftCreateRequest | OfferUpdateRequest,
    ) -> bool:
        return all(
            getattr(offer, key) == value
            for key, value in OfferService._offer_values(data).items()
        )

    @staticmethod
    def _require_active_pipeline(application: Application) -> None:
        if application.lifecycle_status != "active":
            raise ApplicationPipelineEndedError("Application 流程已结束或作废")

    @classmethod
    def _require_active_offer_stage(cls, application: Application) -> None:
        cls._require_active_pipeline(application)
        if (
            application.recruitment_stage != "offer"
            or application.hr_decision != "passed"
            or application.final_outcome is not None
        ):
            raise OfferTransitionInvalidError("当前 Application 不在 Offer 阶段")

    @staticmethod
    def _require_version(offer: OfferRecord, expected_version: int) -> None:
        if offer.version != expected_version:
            raise OfferVersionConflictError("Offer 版本已变化")

    @classmethod
    def _require_optional_version(
        cls,
        offer: OfferRecord,
        expected_version: int | None,
    ) -> None:
        if expected_version is None:
            raise OfferVersionConflictError("缺少 Offer expected_version")
        cls._require_version(offer, expected_version)

    @staticmethod
    def _require_optional_interview_version(
        interview: InterviewRecord,
        expected_version: int | None,
    ) -> None:
        if expected_version is None or interview.version != expected_version:
            raise InterviewVersionConflictError("面试记录版本已变化")

    @staticmethod
    def _require_offer_status(offer: OfferRecord, status: str) -> None:
        if offer.status != status:
            raise ApplicationReopenInvalidError("Offer 支撑记录状态不匹配")

    @staticmethod
    def _require_confirmation(confirmed: bool) -> None:
        if not confirmed:
            raise HRActionConfirmationRequiredError("该操作必须二次确认")

    @staticmethod
    def _require_reason(reason_detail: str | None) -> None:
        if not reason_detail:
            raise HRActionReasonRequiredError("该操作必须填写原因或说明")

    @staticmethod
    def _is_past_valid_until(offer: OfferRecord) -> bool:
        return offer.valid_until < datetime.now(ZoneInfo("Asia/Shanghai")).date()

    @staticmethod
    async def _get_application_for_update(
        db: AsyncSession,
        application_id: int,
    ) -> Application | None:
        return await db.scalar(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
        )

    async def _get_context_for_update(
        self,
        db: AsyncSession,
        offer_id: int,
    ) -> tuple[Application, OfferRecord]:
        application_id = await db.scalar(
            select(OfferRecord.application_id).where(OfferRecord.id == offer_id)
        )
        if application_id is None:
            raise OfferNotFoundError("Offer 不存在")
        application = await self._get_application_for_update(db, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")
        offer = await db.scalar(
            select(OfferRecord)
            .where(OfferRecord.id == offer_id)
            .with_for_update()
        )
        if offer is None:
            raise OfferNotFoundError("Offer 不存在")
        return application, offer

    @staticmethod
    async def _get_active_offer_for_update(
        db: AsyncSession,
        application_id: int,
    ) -> OfferRecord | None:
        return await db.scalar(
            select(OfferRecord)
            .where(
                OfferRecord.application_id == application_id,
                OfferRecord.status.in_(ACTIVE_OFFER_STATUSES),
            )
            .order_by(OfferRecord.version_number.desc(), OfferRecord.id.desc())
            .with_for_update()
            .limit(1)
        )

    @staticmethod
    async def _get_latest_interview_for_update(
        db: AsyncSession,
        application_id: int,
    ) -> InterviewRecord | None:
        return await db.scalar(
            select(InterviewRecord)
            .where(InterviewRecord.application_id == application_id)
            .order_by(InterviewRecord.round_number.desc(), InterviewRecord.id.desc())
            .with_for_update()
            .limit(1)
        )

    @staticmethod
    async def _get_other_active_application_for_update(
        db: AsyncSession,
        application: Application,
    ) -> Application | None:
        return await db.scalar(
            select(Application)
            .where(
                Application.candidate_id == application.candidate_id,
                Application.job_id == application.job_id,
                Application.lifecycle_status == "active",
                Application.id != application.id,
            )
            .with_for_update()
        )

    @staticmethod
    async def _offer_from_history_for_update(
        db: AsyncSession,
        history: StageHistory,
    ) -> OfferRecord:
        if history.offer_record_id is None:
            raise ApplicationReopenInvalidError("缺少 Offer 支撑记录")
        offer = await db.scalar(
            select(OfferRecord)
            .where(OfferRecord.id == history.offer_record_id)
            .with_for_update()
        )
        if offer is None or offer.application_id != history.application_id:
            raise ApplicationReopenInvalidError("Offer 支撑记录不匹配")
        return offer

    @staticmethod
    async def _interview_from_history_for_update(
        db: AsyncSession,
        history: StageHistory,
    ) -> InterviewRecord:
        if history.interview_record_id is None:
            raise ApplicationReopenInvalidError("缺少面试支撑记录")
        interview = await db.scalar(
            select(InterviewRecord)
            .where(InterviewRecord.id == history.interview_record_id)
            .with_for_update()
        )
        if interview is None or interview.application_id != history.application_id:
            raise ApplicationReopenInvalidError("面试支撑记录不匹配")
        return interview

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        original = getattr(exc, "orig", None)
        direct_name = getattr(original, "constraint_name", None)
        if isinstance(direct_name, str):
            return direct_name
        diagnostic = getattr(original, "diag", None)
        name = getattr(diagnostic, "constraint_name", None)
        if isinstance(name, str):
            return name
        message = str(original)
        for expected in (
            OFFER_ACTIVE_UNIQUE_INDEX,
            OFFER_VERSION_UNIQUE_CONSTRAINT,
            ACTIVE_APPLICATION_UNIQUE_INDEX,
        ):
            if expected in message:
                return expected
        return None


offer_service = OfferService()


__all__ = [
    "ApplicationReopenInvalidError",
    "OfferActiveConflictError",
    "OfferCompensationInvalidError",
    "OfferNotFoundError",
    "OfferPipelineError",
    "OfferService",
    "OfferTransitionInvalidError",
    "OfferVersionConflictError",
    "offer_service",
]
