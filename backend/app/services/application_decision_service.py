from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.screening_report import ScreeningReport
from app.models.stage_history import StageHistory
from app.schemas.stage_history import (
    BackupApplicationRequest,
    PassApplicationRequest,
    RejectApplicationRequest,
    ReverseDecisionRequest,
    VoidApplicationRequest,
)


LOCAL_HR_ACTOR_LABEL = "本地 HR（未认证）"
ACTIVE_APPLICATION_UNIQUE_CONSTRAINT = "uq_applications_active_candidate_job"


class ApplicationDecisionError(ValueError):
    pass


class ApplicationNotFoundError(ApplicationDecisionError):
    pass


class InvalidApplicationTransitionError(ApplicationDecisionError):
    pass


class _DecisionAction(str, Enum):
    PASS = "application_passed"
    BACKUP = "application_marked_backup"
    REJECT = "application_rejected"
    UNDO_REJECTION = "application_rejection_undone"
    VOID = "application_voided"


@dataclass(frozen=True)
class _TransitionTarget:
    hr_decision: str
    recruitment_stage: str
    lifecycle_status: str
    final_outcome: str | None


class ApplicationDecisionService:
    async def hr_direct_pass(
        self,
        db: AsyncSession,
        application_id: int,
        data: PassApplicationRequest,
    ) -> Application:
        """Explicit HR override: pass without waiting for an AI outcome."""
        return await self.pass_application(db, application_id, data)

    async def pass_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: PassApplicationRequest,
    ) -> Application:
        return await self._transition(
            db,
            application_id,
            data=data,
            allowed_decisions={"pending", "backup"},
            target=_TransitionTarget("passed", "screening_passed", "active", None),
            action=_DecisionAction.PASS,
        )

    async def backup_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: BackupApplicationRequest,
    ) -> Application:
        return await self._transition(
            db,
            application_id,
            data=data,
            allowed_decisions={"pending", "passed"},
            target=_TransitionTarget("backup", "backup", "active", None),
            action=_DecisionAction.BACKUP,
        )

    async def reject_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: RejectApplicationRequest,
    ) -> Application:
        return await self._transition(
            db,
            application_id,
            data=data,
            allowed_decisions={"pending", "passed", "backup"},
            target=_TransitionTarget(
                "rejected",
                "rejected",
                "ended",
                "screening_rejected",
            ),
            action=_DecisionAction.REJECT,
        )

    async def undo_rejection(
        self,
        db: AsyncSession,
        application_id: int,
        data: ReverseDecisionRequest,
    ) -> Application:
        application: Application | None = None
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            if (
                application.lifecycle_status != "ended"
                or application.hr_decision != "rejected"
                or application.recruitment_stage != "rejected"
                or application.final_outcome != "screening_rejected"
            ):
                raise InvalidApplicationTransitionError("只有已淘汰申请可以撤销淘汰")
            active_application = await self._get_other_active_application_for_update(
                db,
                application,
            )
            if active_application is not None:
                raise InvalidApplicationTransitionError(
                    "同一 Candidate 和 Job 已有其他有效 Application"
                )

            await self._apply_transition(
                db,
                application,
                data=data,
                target=_TransitionTarget("pending", "hr_review", "active", None),
                action=_DecisionAction.UNDO_REJECTION,
            )
            await db.commit()
            await db.refresh(application)
            return application
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) == ACTIVE_APPLICATION_UNIQUE_CONSTRAINT:
                raise InvalidApplicationTransitionError(
                    "同一 Candidate 和 Job 已有其他有效 Application"
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    async def void_application(
        self,
        db: AsyncSession,
        application_id: int,
        data: VoidApplicationRequest,
    ) -> Application:
        application: Application | None = None
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            if application.lifecycle_status == "voided":
                raise InvalidApplicationTransitionError("Application 已经作废")
            await self._apply_transition(
                db,
                application,
                data=data,
                target=_TransitionTarget(
                    application.hr_decision,
                    application.recruitment_stage,
                    "voided",
                    None,
                ),
                action=_DecisionAction.VOID,
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    async def list_history(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> list[StageHistory]:
        application = await db.get(Application, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")
        statement = (
            select(StageHistory)
            .where(StageHistory.application_id == application_id)
            .order_by(StageHistory.created_at, StageHistory.id)
        )
        result = await db.scalars(statement)
        return list(result.all())

    async def advance_to_hr_review_after_screening(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        report_id: int | None,
        succeeded: bool,
    ) -> Application:
        """Advance only untouched applications; never overwrite an HR decision."""
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            await self.append_screening_handoff(
                db,
                application,
                report_id=report_id,
                succeeded=succeeded,
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    async def on_screening_failed(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        report_id: int | None = None,
    ) -> Application:
        """Keep manual HR authority available after an AI failure."""
        return await self.advance_to_hr_review_after_screening(
            db,
            application_id,
            report_id=report_id,
            succeeded=False,
        )

    @staticmethod
    async def append_screening_handoff(
        db: AsyncSession,
        application: Application,
        *,
        report_id: int | None,
        succeeded: bool,
    ) -> bool:
        """Append the system handoff inside the caller's transaction."""
        if (
            application.lifecycle_status != "active"
            or application.hr_decision != "pending"
            or application.recruitment_stage != "applied"
        ):
            return False
        application.recruitment_stage = "hr_review"
        reason_code = (
            "ai_screening_completed" if succeeded else "ai_screening_failed"
        )
        history = StageHistory(
            application_id=application.id,
            report_id=report_id,
            from_lifecycle_status="active",
            to_lifecycle_status="active",
            from_recruitment_stage="applied",
            to_recruitment_stage="hr_review",
            from_hr_decision="pending",
            to_hr_decision="pending",
            from_final_outcome=application.final_outcome,
            to_final_outcome=application.final_outcome,
            reason_code=reason_code,
            reason_detail=None,
            actor_type="system",
            actor_id=None,
            actor_label="AI 初筛系统",
        )
        activity_log = ActivityLog(
            user_id=None,
            action=reason_code,
            target_type="application",
            target_id=application.id,
            detail={
                "from_recruitment_stage": "applied",
                "to_recruitment_stage": "hr_review",
                "from_hr_decision": "pending",
                "to_hr_decision": "pending",
                "report_id": report_id,
                "actor_type": "system",
                "actor_label": "AI 初筛系统",
            },
        )
        db.add_all([history, activity_log])
        await db.flush()
        return True

    async def _transition(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        data: PassApplicationRequest
        | BackupApplicationRequest
        | RejectApplicationRequest,
        allowed_decisions: set[str],
        target: _TransitionTarget,
        action: _DecisionAction,
    ) -> Application:
        application: Application | None = None
        try:
            application = await self._get_application_for_update(db, application_id)
            if application is None:
                raise ApplicationNotFoundError("Application 不存在")
            self._validate_decision_transition(
                application,
                allowed_decisions=allowed_decisions,
            )
            await self._apply_transition(
                db,
                application,
                data=data,
                target=target,
                action=action,
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    def _validate_decision_transition(
        application: Application,
        *,
        allowed_decisions: set[str],
    ) -> None:
        if application.lifecycle_status != "active":
            raise InvalidApplicationTransitionError("只有有效申请可以执行 HR 决策")
        if application.hr_decision not in allowed_decisions:
            raise InvalidApplicationTransitionError("当前 HR 决策不允许执行该操作")

    @staticmethod
    async def _apply_transition(
        db: AsyncSession,
        application: Application,
        *,
        data: PassApplicationRequest
        | BackupApplicationRequest
        | RejectApplicationRequest
        | ReverseDecisionRequest
        | VoidApplicationRequest,
        target: _TransitionTarget,
        action: _DecisionAction,
    ) -> None:
        from_lifecycle_status = application.lifecycle_status
        from_recruitment_stage = application.recruitment_stage
        from_hr_decision = application.hr_decision
        from_final_outcome = application.final_outcome
        reason_code = data.reason_code.value

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
            from_lifecycle_status=from_lifecycle_status,
            to_lifecycle_status=target.lifecycle_status,
            from_recruitment_stage=from_recruitment_stage,
            to_recruitment_stage=target.recruitment_stage,
            from_hr_decision=from_hr_decision,
            to_hr_decision=target.hr_decision,
            from_final_outcome=from_final_outcome,
            to_final_outcome=target.final_outcome,
            reason_code=reason_code,
            reason_detail=data.reason_detail,
            actor_type="hr",
            actor_id=None,
            actor_label=LOCAL_HR_ACTOR_LABEL,
        )
        activity_log = ActivityLog(
            user_id=None,
            action=action.value,
            target_type="application",
            target_id=application.id,
            detail={
                "from_lifecycle_status": from_lifecycle_status,
                "to_lifecycle_status": target.lifecycle_status,
                "from_recruitment_stage": from_recruitment_stage,
                "to_recruitment_stage": target.recruitment_stage,
                "from_hr_decision": from_hr_decision,
                "to_hr_decision": target.hr_decision,
                "from_final_outcome": from_final_outcome,
                "to_final_outcome": target.final_outcome,
                "reason_code": reason_code,
                "reason_detail": data.reason_detail,
                "report_id": report_id,
                "actor_type": "hr",
                "actor_label": LOCAL_HR_ACTOR_LABEL,
            },
        )
        db.add_all([history, activity_log])
        await db.flush()

    @staticmethod
    async def _get_application_for_update(
        db: AsyncSession,
        application_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
        )
        return await db.scalar(statement)

    @staticmethod
    async def _get_other_active_application_for_update(
        db: AsyncSession,
        application: Application,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(
                Application.candidate_id == application.candidate_id,
                Application.job_id == application.job_id,
                Application.lifecycle_status == "active",
                Application.id != application.id,
            )
            .with_for_update()
        )
        return await db.scalar(statement)

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        original = getattr(exc, "orig", None)
        direct_name = getattr(original, "constraint_name", None)
        if isinstance(direct_name, str):
            return direct_name
        diagnostic = getattr(original, "diag", None)
        name = getattr(diagnostic, "constraint_name", None)
        return name if isinstance(name, str) else None


application_decision_service = ApplicationDecisionService()


__all__ = [
    "ApplicationDecisionService",
    "ApplicationNotFoundError",
    "InvalidApplicationTransitionError",
    "application_decision_service",
]
