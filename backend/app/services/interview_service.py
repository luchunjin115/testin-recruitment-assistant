from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.interview_record import InterviewRecord
from app.models.screening_report import ScreeningReport
from app.models.stage_history import StageHistory
from app.schemas.interview import (
    InterviewCancelRequest,
    InterviewDecision,
    InterviewFeedbackSubmitRequest,
    InterviewFeedbackUpdateRequest,
    InterviewNoShowRequest,
    InterviewScheduleCreate,
    InterviewScheduleUpdate,
)


LOCAL_HR_ACTOR_LABEL = "本地 HR（未认证）"
INTERVIEW_ROUND_UNIQUE_CONSTRAINT = "uq_interview_records_application_round"
INTERVIEW_SCHEDULED_UNIQUE_INDEX = (
    "uq_interview_records_one_scheduled_per_application"
)


class RecruitmentPipelineError(ValueError):
    pass


class ApplicationNotFoundError(RecruitmentPipelineError):
    pass


class InterviewNotFoundError(RecruitmentPipelineError):
    pass


class ApplicationNotReadyForInterviewError(RecruitmentPipelineError):
    pass


class ApplicationPipelineEndedError(RecruitmentPipelineError):
    pass


class InterviewRoundConflictError(RecruitmentPipelineError):
    pass


class InterviewTransitionInvalidError(RecruitmentPipelineError):
    pass


class InterviewVersionConflictError(RecruitmentPipelineError):
    pass


class HRActionConfirmationRequiredError(RecruitmentPipelineError):
    pass


class HRActionReasonRequiredError(RecruitmentPipelineError):
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
            lifecycle_status=application.lifecycle_status,
            recruitment_stage=application.recruitment_stage,
            hr_decision=application.hr_decision,
            final_outcome=application.final_outcome,
        )


_FEEDBACK_REASON_BY_DECISION = {
    "pending": "interview_round_completed",
    "next_round": "interview_next_round",
    "proceed_offer": "interview_proceed_offer",
    "rejected": "interview_rejected",
    "candidate_withdrew": "candidate_withdrew",
}


class InterviewService:
    async def get_interview(
        self,
        db: AsyncSession,
        interview_id: int,
    ) -> InterviewRecord:
        interview = await db.get(InterviewRecord, interview_id)
        if interview is None:
            raise InterviewNotFoundError("面试记录不存在")
        return interview

    async def list_interviews(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> list[InterviewRecord]:
        application = await db.get(Application, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")
        records = await db.scalars(
            select(InterviewRecord)
            .where(InterviewRecord.application_id == application_id)
            .order_by(InterviewRecord.round_number, InterviewRecord.id)
        )
        return list(records.all())

    async def schedule_interview(
        self,
        db: AsyncSession,
        application_id: int,
        data: InterviewScheduleCreate,
    ) -> InterviewRecord:
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            self._require_active_pipeline(application)

            records_result = await db.scalars(
                select(InterviewRecord)
                .where(InterviewRecord.application_id == application_id)
                .order_by(InterviewRecord.round_number, InterviewRecord.id)
                .with_for_update()
            )
            records = list(records_result.all())
            is_first_round = self._validate_new_round(application, records, data)

            interview = InterviewRecord(
                application_id=application_id,
                round_number=data.round_number,
                status="scheduled",
                decision="pending",
                version=1,
                **self._schedule_values(data),
            )
            db.add(interview)
            await db.flush()

            history: StageHistory | None = None
            if is_first_round:
                history = await self._transition_application(
                    db,
                    application,
                    interview=interview,
                    target=_ApplicationState("active", "interview", "passed", None),
                    reason_code="interview_scheduled",
                    reason_detail=None,
                )

            await self._add_activity(
                db,
                interview=interview,
                reason_code="interview_scheduled",
                reason_detail=None,
                history=history,
                changes={
                    "round_number": interview.round_number,
                    "to_status": "scheduled",
                    "to_scheduled_start_at": interview.scheduled_start_at.isoformat(),
                    "to_version": interview.version,
                },
            )
            await db.commit()
            await db.refresh(interview)
            return interview
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) in {
                INTERVIEW_ROUND_UNIQUE_CONSTRAINT,
                INTERVIEW_SCHEDULED_UNIQUE_INDEX,
            }:
                raise InterviewRoundConflictError(
                    "轮次重复或已有待进行面试"
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    async def reschedule_interview(
        self,
        db: AsyncSession,
        interview_id: int,
        data: InterviewScheduleUpdate,
    ) -> InterviewRecord:
        try:
            application, interview = await self._get_context_for_update(
                db, interview_id
            )
            self._require_active_pipeline(application)
            self._require_version(interview, data.expected_version)
            if interview.status != "scheduled":
                raise InterviewTransitionInvalidError("只有待进行面试可以改期")

            new_values = self._schedule_values(data)
            if all(getattr(interview, key) == value for key, value in new_values.items()):
                await db.commit()
                return interview

            from_scheduled_start_at = interview.scheduled_start_at
            from_version = interview.version
            for key, value in new_values.items():
                setattr(interview, key, value)
            interview.version += 1

            await self._add_activity(
                db,
                interview=interview,
                reason_code="interview_rescheduled",
                reason_detail=data.reason_detail,
                changes={
                    "from_scheduled_start_at": from_scheduled_start_at.isoformat(),
                    "to_scheduled_start_at": interview.scheduled_start_at.isoformat(),
                    "from_version": from_version,
                    "to_version": interview.version,
                },
            )
            await db.commit()
            await db.refresh(interview)
            return interview
        except Exception:
            await db.rollback()
            raise

    async def cancel_interview(
        self,
        db: AsyncSession,
        interview_id: int,
        data: InterviewCancelRequest,
    ) -> InterviewRecord:
        return await self._close_scheduled_interview(
            db,
            interview_id,
            expected_version=data.expected_version,
            target_status="canceled",
            reason_code=data.reason_code.value,
            reason_detail=data.reason_detail,
            confirmed=data.confirmed,
        )

    async def mark_no_show(
        self,
        db: AsyncSession,
        interview_id: int,
        data: InterviewNoShowRequest,
    ) -> InterviewRecord:
        return await self._close_scheduled_interview(
            db,
            interview_id,
            expected_version=data.expected_version,
            target_status="no_show",
            reason_code=data.reason_code.value,
            reason_detail=data.reason_detail,
            confirmed=data.confirmed,
            end_application=data.end_application,
        )

    async def submit_feedback(
        self,
        db: AsyncSession,
        interview_id: int,
        data: InterviewFeedbackSubmitRequest,
    ) -> InterviewRecord:
        self._validate_feedback_reason(data.decision.value, data.reason_code.value)
        self._validate_high_risk_feedback(
            data.decision.value,
            confirmed=data.confirmed,
            reason_detail=data.reason_detail,
        )
        try:
            application, interview = await self._get_context_for_update(
                db, interview_id
            )
            if interview.feedback_submitted_at is not None:
                if await self._is_repeated_feedback(
                    db,
                    interview,
                    data,
                    reason_code=data.reason_code.value,
                    reason_detail=data.reason_detail,
                ):
                    await db.commit()
                    return interview
                raise InterviewTransitionInvalidError(
                    "面试反馈已提交，修改时必须使用更正接口"
                )

            self._require_active_pipeline(application)
            self._require_version(interview, data.expected_version)
            if interview.status != "scheduled":
                raise InterviewTransitionInvalidError(
                    "只有待进行面试可以首次提交反馈"
                )

            from_version = interview.version
            interview.status = "completed"
            self._apply_feedback_values(interview, data)
            interview.feedback_submitted_by_label = LOCAL_HR_ACTOR_LABEL
            interview.feedback_submitted_at = datetime.now(timezone.utc)
            interview.version += 1

            history = await self._apply_feedback_transition(
                db,
                application,
                interview,
                decision=data.decision.value,
                reason_code=data.reason_code.value,
                reason_detail=data.reason_detail,
            )
            await self._add_activity(
                db,
                interview=interview,
                reason_code=data.reason_code.value,
                reason_detail=data.reason_detail,
                history=history,
                changes={
                    "from_status": "scheduled",
                    "to_status": "completed",
                    "from_decision": "pending",
                    "to_decision": interview.decision,
                    "from_version": from_version,
                    "to_version": interview.version,
                    **self._feedback_count_changes(interview),
                },
            )
            await db.commit()
            await db.refresh(interview)
            return interview
        except Exception:
            await db.rollback()
            raise

    async def update_feedback(
        self,
        db: AsyncSession,
        interview_id: int,
        data: InterviewFeedbackUpdateRequest,
    ) -> InterviewRecord:
        if not data.confirmed:
            raise HRActionConfirmationRequiredError("修改反馈必须二次确认")
        try:
            application, interview = await self._get_context_for_update(
                db, interview_id
            )
            if interview.feedback_submitted_at is None or interview.status != "completed":
                raise InterviewTransitionInvalidError("面试反馈尚未提交")

            if self._same_feedback(interview, data):
                await db.commit()
                return interview
            self._require_version(interview, data.expected_version)
            if interview.decision != "pending" and (
                data.decision.value != interview.decision
            ):
                raise InterviewTransitionInvalidError(
                    "已生效的面试决定必须通过重新打开流程更正"
                )

            from_decision = interview.decision
            from_version = interview.version
            self._apply_feedback_values(interview, data)
            interview.version += 1

            history: StageHistory | None = None
            transition_reason_code: str | None = None
            if from_decision == "pending" and interview.decision != "pending":
                self._require_active_pipeline(application)
                transition_reason_code = _FEEDBACK_REASON_BY_DECISION[
                    interview.decision
                ]
                history = await self._apply_feedback_transition(
                    db,
                    application,
                    interview,
                    decision=interview.decision,
                    reason_code=transition_reason_code,
                    reason_detail=data.correction_reason,
                )

            await self._add_activity(
                db,
                interview=interview,
                reason_code=data.reason_code.value,
                reason_detail=data.correction_reason,
                history=history,
                changes={
                    "from_status": "completed",
                    "to_status": "completed",
                    "from_decision": from_decision,
                    "to_decision": interview.decision,
                    "from_version": from_version,
                    "to_version": interview.version,
                    "transition_reason_code": transition_reason_code,
                    **self._feedback_count_changes(interview),
                },
            )
            await db.commit()
            await db.refresh(interview)
            return interview
        except Exception:
            await db.rollback()
            raise

    async def _close_scheduled_interview(
        self,
        db: AsyncSession,
        interview_id: int,
        *,
        expected_version: int,
        target_status: str,
        reason_code: str,
        reason_detail: str,
        confirmed: bool,
        end_application: bool = False,
    ) -> InterviewRecord:
        if not confirmed:
            raise HRActionConfirmationRequiredError("该面试动作必须二次确认")
        if not reason_detail:
            raise HRActionReasonRequiredError("该面试动作必须填写原因")
        try:
            application, interview = await self._get_context_for_update(
                db, interview_id
            )
            if interview.status == target_status:
                repeated = await self._latest_activity_matches(
                    db,
                    interview,
                    reason_code=reason_code,
                    reason_detail=reason_detail,
                    expected_version=expected_version,
                    expected_end_application=(
                        end_application if target_status == "no_show" else None
                    ),
                )
                if (
                    target_status == "no_show"
                    and end_application
                    and application.lifecycle_status == "active"
                ):
                    self._require_interview_stage(application)
                    self._require_version(interview, expected_version)
                    history = await self._transition_application(
                        db,
                        application,
                        interview=interview,
                        target=_ApplicationState(
                            "ended", "rejected", "passed", "interview_no_show"
                        ),
                        reason_code=reason_code,
                        reason_detail=reason_detail,
                    )
                    await self._add_activity(
                        db,
                        interview=interview,
                        reason_code=reason_code,
                        reason_detail=reason_detail,
                        history=history,
                        changes={
                            "from_status": "no_show",
                            "to_status": "no_show",
                            "from_decision": "pending",
                            "to_decision": "pending",
                            "from_version": interview.version,
                            "to_version": interview.version,
                            "end_application": True,
                        },
                    )
                    await db.commit()
                    await db.refresh(interview)
                    return interview
                if repeated and (
                    not end_application
                    or (
                        application.lifecycle_status == "ended"
                        and application.final_outcome == "interview_no_show"
                    )
                ):
                    await db.commit()
                    return interview
            self._require_active_pipeline(application)
            if target_status == "no_show" and end_application:
                self._require_interview_stage(application)
            self._require_version(interview, expected_version)
            if interview.status != "scheduled":
                raise InterviewTransitionInvalidError(
                    "当前面试状态不允许执行该动作"
                )

            from_version = interview.version
            interview.status = target_status
            interview.version += 1
            history: StageHistory | None = None
            if target_status == "no_show" and end_application:
                history = await self._transition_application(
                    db,
                    application,
                    interview=interview,
                    target=_ApplicationState(
                        "ended", "rejected", "passed", "interview_no_show"
                    ),
                    reason_code=reason_code,
                    reason_detail=reason_detail,
                )
            await self._add_activity(
                db,
                interview=interview,
                reason_code=reason_code,
                reason_detail=reason_detail,
                history=history,
                changes={
                    "from_status": "scheduled",
                    "to_status": target_status,
                    "from_decision": "pending",
                    "to_decision": "pending",
                    "from_version": from_version,
                    "to_version": interview.version,
                    "end_application": end_application,
                },
            )
            await db.commit()
            await db.refresh(interview)
            return interview
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    def _validate_new_round(
        application: Application,
        records: list[InterviewRecord],
        data: InterviewScheduleCreate,
    ) -> bool:
        if application.hr_decision != "passed":
            raise ApplicationNotReadyForInterviewError(
                "只有 HR 已通过的 Application 可以安排面试"
            )
        if any(record.status == "scheduled" for record in records):
            raise InterviewRoundConflictError("已有待进行面试")

        if application.recruitment_stage == "screening_passed":
            if records or data.round_number != 1:
                raise InterviewRoundConflictError("第一轮面试必须从轮次 1 开始")
            return True
        if application.recruitment_stage != "interview" or not records:
            raise ApplicationNotReadyForInterviewError(
                "当前 Application 阶段不能安排面试"
            )

        latest = max(records, key=lambda item: (item.round_number, item.id))
        if data.round_number != latest.round_number + 1:
            raise InterviewRoundConflictError("新面试必须使用下一连续轮次")
        may_schedule_next = latest.status in {"canceled", "no_show"} or (
            latest.status == "completed" and latest.decision == "next_round"
        )
        if not may_schedule_next:
            raise InterviewTransitionInvalidError(
                "上一轮尚未决定进入下一轮"
            )
        return False

    @staticmethod
    def _require_active_pipeline(application: Application) -> None:
        if application.lifecycle_status != "active":
            raise ApplicationPipelineEndedError("Application 流程已结束或作废")

    @staticmethod
    def _require_interview_stage(application: Application) -> None:
        if (
            application.recruitment_stage != "interview"
            or application.hr_decision != "passed"
            or application.final_outcome is not None
        ):
            raise InterviewTransitionInvalidError(
                "当前 Application 状态不允许因未到场结束流程"
            )

    @staticmethod
    def _require_version(interview: InterviewRecord, expected_version: int) -> None:
        if interview.version != expected_version:
            raise InterviewVersionConflictError("面试记录版本已变化")

    @staticmethod
    def _validate_feedback_reason(decision: str, reason_code: str) -> None:
        if _FEEDBACK_REASON_BY_DECISION[decision] != reason_code:
            raise HRActionReasonRequiredError("面试决定与 reason code 不一致")

    @staticmethod
    def _validate_high_risk_feedback(
        decision: str,
        *,
        confirmed: bool,
        reason_detail: str | None,
    ) -> None:
        if decision not in {"rejected", "candidate_withdrew"}:
            return
        if not confirmed:
            raise HRActionConfirmationRequiredError("结束招聘流程必须二次确认")
        if not reason_detail:
            raise HRActionReasonRequiredError("结束招聘流程必须填写原因")

    async def _apply_feedback_transition(
        self,
        db: AsyncSession,
        application: Application,
        interview: InterviewRecord,
        *,
        decision: str,
        reason_code: str,
        reason_detail: str | None,
    ) -> StageHistory | None:
        if decision in {"pending", "next_round"}:
            return None
        if (
            application.lifecycle_status != "active"
            or application.recruitment_stage != "interview"
            or application.hr_decision != "passed"
        ):
            raise InterviewTransitionInvalidError(
                "当前 Application 状态不允许应用面试决定"
            )

        if decision == "proceed_offer":
            target = _ApplicationState("active", "offer", "passed", None)
        elif decision == "rejected":
            target = _ApplicationState(
                "ended", "rejected", "passed", "interview_rejected"
            )
        else:
            target = _ApplicationState(
                "ended",
                application.recruitment_stage,
                "passed",
                "candidate_withdrew",
            )
        return await self._transition_application(
            db,
            application,
            interview=interview,
            target=target,
            reason_code=reason_code,
            reason_detail=reason_detail,
        )

    @staticmethod
    async def _transition_application(
        db: AsyncSession,
        application: Application,
        *,
        interview: InterviewRecord,
        target: _ApplicationState,
        reason_code: str,
        reason_detail: str | None,
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
            interview_record_id=interview.id,
            offer_record_id=None,
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
    async def _add_activity(
        db: AsyncSession,
        *,
        interview: InterviewRecord,
        reason_code: str,
        reason_detail: str | None,
        changes: dict,
        history: StageHistory | None = None,
    ) -> None:
        detail = {
            "application_id": interview.application_id,
            "interview_record_id": interview.id,
            "reason_code": reason_code,
            "reason_detail": reason_detail,
            "actor_type": "hr",
            "actor_label": LOCAL_HR_ACTOR_LABEL,
            "stage_history_id": history.id if history is not None else None,
            **changes,
        }
        db.add(
            ActivityLog(
                user_id=None,
                action=reason_code,
                target_type="interview",
                target_id=interview.id,
                detail=detail,
            )
        )
        await db.flush()

    async def _latest_activity_matches(
        self,
        db: AsyncSession,
        interview: InterviewRecord,
        *,
        reason_code: str,
        reason_detail: str | None,
        expected_version: int,
        expected_end_application: bool | None = None,
    ) -> bool:
        activity = await db.scalar(
            select(ActivityLog)
            .where(
                ActivityLog.target_type == "interview",
                ActivityLog.target_id == interview.id,
                ActivityLog.action == reason_code,
            )
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(1)
        )
        if activity is None or not isinstance(activity.detail, dict):
            return False
        detail = activity.detail
        matches = (
            detail.get("reason_code") == reason_code
            and detail.get("reason_detail") == reason_detail
            and expected_version
            in {detail.get("from_version"), detail.get("to_version")}
        )
        if expected_end_application is not None:
            matches = matches and (
                detail.get("end_application") is expected_end_application
            )
        return matches

    async def _is_repeated_feedback(
        self,
        db: AsyncSession,
        interview: InterviewRecord,
        data: InterviewFeedbackSubmitRequest,
        *,
        reason_code: str,
        reason_detail: str | None,
    ) -> bool:
        return self._same_feedback(interview, data) and (
            await self._latest_activity_matches(
                db,
                interview,
                reason_code=reason_code,
                reason_detail=reason_detail,
                expected_version=data.expected_version,
            )
        )

    @staticmethod
    def _same_feedback(
        interview: InterviewRecord,
        data: InterviewFeedbackSubmitRequest | InterviewFeedbackUpdateRequest,
    ) -> bool:
        return (
            interview.feedback_summary == data.feedback_summary
            and interview.strengths == list(data.strengths)
            and interview.concerns == list(data.concerns)
            and interview.follow_up_questions == list(data.follow_up_questions)
            and interview.decision == data.decision.value
        )

    @staticmethod
    def _apply_feedback_values(
        interview: InterviewRecord,
        data: InterviewFeedbackSubmitRequest | InterviewFeedbackUpdateRequest,
    ) -> None:
        interview.feedback_summary = data.feedback_summary
        interview.strengths = list(data.strengths)
        interview.concerns = list(data.concerns)
        interview.follow_up_questions = list(data.follow_up_questions)
        interview.decision = data.decision.value

    @staticmethod
    def _feedback_count_changes(interview: InterviewRecord) -> dict[str, int]:
        return {
            "strength_count": len(interview.strengths),
            "concern_count": len(interview.concerns),
            "follow_up_question_count": len(interview.follow_up_questions),
        }

    @staticmethod
    def _schedule_values(
        data: InterviewScheduleCreate | InterviewScheduleUpdate,
    ) -> dict:
        return {
            "interview_type": data.interview_type.value,
            "scheduled_start_at": data.scheduled_start_at,
            "duration_minutes": data.duration_minutes,
            "timezone": data.timezone,
            "interviewer_names": list(data.interviewer_names),
            "location": data.location,
            "meeting_link": (
                str(data.meeting_link) if data.meeting_link is not None else None
            ),
            "schedule_note": data.schedule_note,
        }

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
        interview_id: int,
    ) -> tuple[Application, InterviewRecord]:
        application_id = await db.scalar(
            select(InterviewRecord.application_id).where(
                InterviewRecord.id == interview_id
            )
        )
        if application_id is None:
            raise InterviewNotFoundError("面试记录不存在")
        application = await self._get_application_for_update(db, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")
        interview = await db.scalar(
            select(InterviewRecord)
            .where(InterviewRecord.id == interview_id)
            .with_for_update()
        )
        if interview is None:
            raise InterviewNotFoundError("面试记录不存在")
        return application, interview

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
            INTERVIEW_ROUND_UNIQUE_CONSTRAINT,
            INTERVIEW_SCHEDULED_UNIQUE_INDEX,
        ):
            if expected in message:
                return expected
        return None


interview_service = InterviewService()


__all__ = [
    "ApplicationNotFoundError",
    "ApplicationNotReadyForInterviewError",
    "ApplicationPipelineEndedError",
    "HRActionConfirmationRequiredError",
    "HRActionReasonRequiredError",
    "InterviewNotFoundError",
    "InterviewRoundConflictError",
    "InterviewService",
    "InterviewTransitionInvalidError",
    "InterviewVersionConflictError",
    "RecruitmentPipelineError",
    "interview_service",
]
