from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, case, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from app.adapters.resume_structure import (
    ResumeStructureAdapterError,
    ResumeStructureRateLimitError,
    ResumeStructureServiceUnavailableError,
    ResumeStructureTimeoutError,
)
from app.core.config import Settings, get_settings
from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.activity_log import ActivityLog
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.screening_run import ScreeningRun
from app.schemas.public_application import (
    ApplicationProcessingStatus,
    ApplicationProcessingStep,
    ApplicationProcessingTriggerType,
    ApplicationProcessingWaitingReason,
    ApplicationProcessingWarningCode,
)
from app.schemas.screening import ScreeningRunStatus, ScreeningRunTriggerType
from app.services.resume_service import (
    ResumeTextExtractionConflictError,
    ResumeTextExtractionFailedError,
    UnsupportedResumeTextExtractionError,
    resume_service,
)
from app.services.resume_structure_service import (
    ResumeStructureConflictError,
    ResumeStructureServiceError,
    resume_structure_service,
)
from app.services.application_intake_service import LOCAL_HR_ACTOR_LABEL
from app.services.screening_service import (
    ScreeningJobClosedError,
    ScreeningServiceError,
    screening_service,
)


logger = logging.getLogger(__name__)
_ACTIVE_STATUSES = (
    ApplicationProcessingStatus.QUEUED.value,
    ApplicationProcessingStatus.RUNNING.value,
    ApplicationProcessingStatus.WAITING_SCREENING.value,
)
_SUCCESS_STATUSES = {
    ApplicationProcessingStatus.SUCCEEDED.value,
    ApplicationProcessingStatus.SUCCEEDED_WITH_WARNINGS.value,
}
_SCREENING_WAITING_STATUSES = {
    ScreeningRunStatus.WAITING_RESUME.value,
    ScreeningRunStatus.WAITING_PLAN.value,
    ScreeningRunStatus.QUEUED.value,
    ScreeningRunStatus.RUNNING.value,
}
_STRUCTURE_RETRYABLE_ERRORS = (
    ResumeStructureConflictError,
    ResumeStructureRateLimitError,
    ResumeStructureServiceUnavailableError,
    ResumeStructureTimeoutError,
)


class ApplicationProcessingServiceError(RuntimeError):
    pass


class ApplicationProcessingRunNotFoundError(ApplicationProcessingServiceError):
    pass


class ApplicationProcessingLeaseLostError(ApplicationProcessingServiceError):
    pass


class ApplicationProcessingRetryNotAllowedError(ApplicationProcessingServiceError):
    pass


class ApplicationProcessingPauseNotRecoveredError(
    ApplicationProcessingRetryNotAllowedError
):
    pass


class ApplicationProcessingActiveRunError(ApplicationProcessingServiceError):
    pass


@dataclass(frozen=True, slots=True)
class ApplicationProcessingExecutionResult:
    run: ApplicationProcessingRun
    progressed: bool


@dataclass(frozen=True, slots=True)
class _OwnedRunContext:
    id: int
    application_id: int
    resume_id: int
    current_step: str


class ApplicationProcessingService:
    async def claim_next_run(
        self,
        db: AsyncSession,
        *,
        worker_id: str,
        lease_seconds: int,
        max_attempts: int,
        clock: Callable[[], datetime] | None = None,
    ) -> ApplicationProcessingRun | None:
        now = self._now(clock)
        other = aliased(ApplicationProcessingRun)
        other_active = exists(
            select(other.id).where(
                other.submission_id == ApplicationProcessingRun.submission_id,
                other.id != ApplicationProcessingRun.id,
                other.status.in_(_ACTIVE_STATUSES),
            )
        )
        resumable_pause = and_(
            ApplicationProcessingRun.status
            == ApplicationProcessingStatus.PAUSED.value,
            ~other_active,
            or_(
                and_(
                    ApplicationProcessingRun.waiting_reason
                    == ApplicationProcessingWaitingReason.JOB_CLOSED.value,
                    Job.status == "open",
                ),
                and_(
                    ApplicationProcessingRun.waiting_reason
                    == ApplicationProcessingWaitingReason.EXISTING_APPLICATION_RESUME_CHOICE.value,
                    Application.current_resume_id
                    == ApplicationProcessingRun.resume_id,
                ),
            ),
        )

        try:
            await self._recover_expired_runs(db, now, max_attempts)
            run = await db.scalar(
                select(ApplicationProcessingRun)
                .join(
                    Application,
                    Application.id == ApplicationProcessingRun.application_id,
                )
                .join(Job, Job.id == Application.job_id)
                .where(
                    or_(
                        and_(
                            ApplicationProcessingRun.status
                            == ApplicationProcessingStatus.QUEUED.value,
                            ApplicationProcessingRun.attempt_count < max_attempts,
                        ),
                        ApplicationProcessingRun.status
                        == ApplicationProcessingStatus.WAITING_SCREENING.value,
                        resumable_pause,
                    )
                )
                .order_by(
                    case(
                        (
                            ApplicationProcessingRun.status
                            == ApplicationProcessingStatus.QUEUED.value,
                            0,
                        ),
                        (
                            ApplicationProcessingRun.status
                            == ApplicationProcessingStatus.PAUSED.value,
                            1,
                        ),
                        else_=2,
                    ),
                    ApplicationProcessingRun.created_at,
                    ApplicationProcessingRun.id,
                )
                .with_for_update(of=ApplicationProcessingRun, skip_locked=True)
                .limit(1)
            )
            if run is None:
                await db.commit()
                return None

            was_queued = run.status == ApplicationProcessingStatus.QUEUED.value
            run.status = ApplicationProcessingStatus.RUNNING.value
            run.waiting_reason = None
            run.error_code = None
            run.error_message = None
            run.completed_at = None
            run.started_at = run.started_at or now
            if was_queued:
                run.attempt_count += 1
            run.lease_owner = worker_id
            run.lease_expires_at = now + timedelta(seconds=lease_seconds)
            await db.commit()
            await db.refresh(run)
            return run
        except Exception:
            await db.rollback()
            raise

    async def execute_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        settings: Settings | None = None,
        structure_adapter=None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> ApplicationProcessingExecutionResult:
        resolved = settings or get_settings()
        progressed = False
        for _ in range(5):
            context = await self._renew_and_read(
                db,
                run_id,
                worker_id=worker_id,
                lease_seconds=resolved.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
                clock=clock,
            )
            step = context.current_step
            if step == ApplicationProcessingStep.EXTRACT_TEXT.value:
                terminal = await self._execute_extract_text(
                    db,
                    context,
                    worker_id=worker_id,
                    settings=resolved,
                    clock=clock,
                )
            elif step == ApplicationProcessingStep.STRUCTURE_RESUME.value:
                terminal = await self._execute_structure_resume(
                    db,
                    context,
                    worker_id=worker_id,
                    settings=resolved,
                    structure_adapter=structure_adapter,
                    clock=clock,
                    sleeper=sleeper,
                )
            elif step == ApplicationProcessingStep.TRIGGER_SCREENING.value:
                terminal = await self._execute_trigger_screening(
                    db,
                    context,
                    worker_id=worker_id,
                    settings=resolved,
                    clock=clock,
                )
            elif step == ApplicationProcessingStep.AWAIT_SCREENING.value:
                terminal = await self._execute_await_screening(
                    db,
                    context,
                    worker_id=worker_id,
                    settings=resolved,
                    clock=clock,
                )
            else:
                terminal = await self._fail_owned_run(
                    db,
                    run_id,
                    worker_id=worker_id,
                    code="APPLICATION_PROCESSING_STEP_INVALID",
                    message="处理任务当前步骤无效，无法继续",
                    clock=clock,
                )
            progressed = True
            if terminal:
                run = await db.get(ApplicationProcessingRun, run_id)
                assert run is not None
                return ApplicationProcessingExecutionResult(run=run, progressed=progressed)

        run = await self._fail_owned_run(
            db,
            run_id,
            worker_id=worker_id,
            code="APPLICATION_PROCESSING_STEP_LIMIT_EXCEEDED",
            message="处理任务步骤推进超过安全上限",
            clock=clock,
        )
        return ApplicationProcessingExecutionResult(run=run, progressed=progressed)

    async def release_for_retry(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        max_attempts: int,
        clock: Callable[[], datetime] | None = None,
    ) -> ApplicationProcessingRun | None:
        now = self._now(clock)
        try:
            run = await db.scalar(
                select(ApplicationProcessingRun)
                .where(ApplicationProcessingRun.id == run_id)
                .with_for_update()
            )
            if run is None:
                await db.rollback()
                return None
            if (
                run.status != ApplicationProcessingStatus.RUNNING.value
                or run.lease_owner != worker_id
            ):
                await db.rollback()
                return run
            if run.current_step == ApplicationProcessingStep.AWAIT_SCREENING.value:
                run.status = ApplicationProcessingStatus.WAITING_SCREENING.value
            elif run.attempt_count < max_attempts:
                run.status = ApplicationProcessingStatus.QUEUED.value
            else:
                self._set_failed(
                    run,
                    code="APPLICATION_PROCESSING_ATTEMPTS_EXHAUSTED",
                    message="处理任务已达到自动尝试上限，请由招聘团队人工重试",
                    completed_at=now,
                )
            run.lease_owner = None
            run.lease_expires_at = None
            await db.commit()
            await db.refresh(run)
            return run
        except Exception:
            await db.rollback()
            raise

    async def create_manual_retry(
        self,
        db: AsyncSession,
        submission_id: int,
    ) -> ApplicationProcessingRun:
        try:
            submission = await db.scalar(
                select(PublicApplicationSubmission)
                .where(PublicApplicationSubmission.id == submission_id)
                .with_for_update()
            )
            if submission is None:
                raise ApplicationProcessingRunNotFoundError("公开提交不存在")
            active = await db.scalar(
                select(ApplicationProcessingRun.id).where(
                    ApplicationProcessingRun.submission_id == submission_id,
                    ApplicationProcessingRun.status.in_(_ACTIVE_STATUSES),
                )
            )
            if active is not None:
                raise ApplicationProcessingActiveRunError("当前已有非终态处理任务")
            previous = await db.scalar(
                select(ApplicationProcessingRun)
                .where(ApplicationProcessingRun.submission_id == submission_id)
                .order_by(
                    ApplicationProcessingRun.created_at.desc(),
                    ApplicationProcessingRun.id.desc(),
                )
                .with_for_update()
                .limit(1)
            )
            if previous is None or previous.status not in {
                ApplicationProcessingStatus.FAILED.value,
                ApplicationProcessingStatus.PAUSED.value,
            }:
                raise ApplicationProcessingRetryNotAllowedError(
                    "只有失败或恢复条件已满足的暂停任务可以人工重试"
                )
            if previous.status == ApplicationProcessingStatus.PAUSED.value:
                await self._validate_pause_recovered(db, previous)

            retry_step = previous.current_step
            if (
                previous.status == ApplicationProcessingStatus.FAILED.value
                and retry_step == ApplicationProcessingStep.AWAIT_SCREENING.value
            ):
                retry_step = ApplicationProcessingStep.TRIGGER_SCREENING.value
            run = ApplicationProcessingRun(
                submission_id=submission.id,
                application_id=submission.application_id,
                resume_id=submission.resume_id,
                trigger_type=ApplicationProcessingTriggerType.MANUAL_RETRY.value,
                status=ApplicationProcessingStatus.QUEUED.value,
                current_step=retry_step,
                attempt_count=0,
                warning_codes=list(previous.warning_codes or []),
            )
            db.add(run)
            await db.flush()
            db.add(
                ActivityLog(
                    user_id=None,
                    action="public_application_manual_retry",
                    target_type="public_application_submission",
                    target_id=submission.id,
                    detail={
                        "previous_run_id": previous.id,
                        "new_run_id": run.id,
                        "resume_from_step": retry_step,
                        "actor_type": "hr",
                        "actor_label": LOCAL_HR_ACTOR_LABEL,
                    },
                )
            )
            await db.commit()
            await db.refresh(run)
            return run
        except IntegrityError as exc:
            await db.rollback()
            raise ApplicationProcessingActiveRunError(
                "当前已有非终态处理任务"
            ) from exc
        except Exception:
            await db.rollback()
            raise

    async def _execute_extract_text(
        self,
        db: AsyncSession,
        context: _OwnedRunContext,
        *,
        worker_id: str,
        settings: Settings,
        clock: Callable[[], datetime] | None,
    ) -> bool:
        try:
            resume = await resume_service.extract_text(
                db,
                context.resume_id,
                Path(settings.STORAGE_DIR),
            )
        except (
            ResumeTextExtractionFailedError,
            UnsupportedResumeTextExtractionError,
        ):
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code="RESUME_TEXT_EXTRACTION_FAILED",
                message="简历原文提取失败，请检查原文件后人工重试",
                clock=clock,
            )
            return True
        except ResumeTextExtractionConflictError:
            raise
        if resume is None:
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code="RESUME_NOT_FOUND",
                message="处理任务对应的 Resume 不存在",
                clock=clock,
            )
            return True
        await self._advance_owned_run(
            db,
            context.id,
            worker_id=worker_id,
            expected_step=ApplicationProcessingStep.EXTRACT_TEXT.value,
            next_step=ApplicationProcessingStep.STRUCTURE_RESUME.value,
            lease_seconds=settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
            clock=clock,
        )
        return False

    async def _execute_structure_resume(
        self,
        db: AsyncSession,
        context: _OwnedRunContext,
        *,
        worker_id: str,
        settings: Settings,
        structure_adapter,
        clock: Callable[[], datetime] | None,
        sleeper: Callable[[float], Awaitable[None]],
    ) -> bool:
        failed = False
        max_retries = settings.APPLICATION_PROCESSING_STEP_INFRASTRUCTURE_RETRIES
        for retry_index in range(max_retries + 1):
            await self._renew_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                lease_seconds=settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
                clock=clock,
            )
            try:
                await resume_structure_service.structure_resume(
                    db,
                    context.resume_id,
                    adapter=structure_adapter,
                    settings=settings,
                )
                break
            except _STRUCTURE_RETRYABLE_ERRORS:
                if retry_index >= max_retries:
                    failed = True
                    break
                delay = settings.APPLICATION_PROCESSING_RETRY_BACKOFF_SECONDS * (
                    2**retry_index
                )
                await sleeper(delay)
            except (ResumeStructureServiceError, ResumeStructureAdapterError):
                failed = True
                break

        await self._advance_owned_run(
            db,
            context.id,
            worker_id=worker_id,
            expected_step=ApplicationProcessingStep.STRUCTURE_RESUME.value,
            next_step=ApplicationProcessingStep.TRIGGER_SCREENING.value,
            lease_seconds=settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
            add_warning=(
                ApplicationProcessingWarningCode.RESUME_STRUCTURE_FAILED.value
                if failed
                else None
            ),
            clock=clock,
        )
        return False

    async def _execute_trigger_screening(
        self,
        db: AsyncSession,
        context: _OwnedRunContext,
        *,
        worker_id: str,
        settings: Settings,
        clock: Callable[[], datetime] | None,
    ) -> bool:
        application = await db.get(Application, context.application_id)
        job = await db.get(Job, application.job_id) if application is not None else None
        current_resume_id = (
            application.current_resume_id if application is not None else None
        )
        job_status = job.status if job is not None else None
        await db.rollback()
        if application is None or job is None:
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code="APPLICATION_CONTEXT_NOT_FOUND",
                message="处理任务对应的 Application 或 Job 不存在",
                clock=clock,
            )
            return True
        if current_resume_id != context.resume_id:
            await self._pause_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                reason=(
                    ApplicationProcessingWaitingReason.EXISTING_APPLICATION_RESUME_CHOICE.value
                ),
                clock=clock,
            )
            return True
        if job_status != "open":
            await self._pause_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                reason=ApplicationProcessingWaitingReason.JOB_CLOSED.value,
                clock=clock,
            )
            return True

        try:
            result = await screening_service.trigger(
                db,
                context.application_id,
                trigger_type=ScreeningRunTriggerType.AUTOMATIC,
                settings=settings,
            )
        except ScreeningJobClosedError:
            await self._pause_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                reason=ApplicationProcessingWaitingReason.JOB_CLOSED.value,
                clock=clock,
            )
            return True
        except ScreeningServiceError as exc:
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code=exc.code,
                message="阶段 7 初筛任务无法创建，请由招聘团队人工重试",
                clock=clock,
            )
            return True

        if result.reused_report or (
            result.run is None and result.report is not None
        ):
            await self._succeed_owned_run(db, context.id, worker_id=worker_id, clock=clock)
            return True
        if result.run is None:
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code="SCREENING_STATE_UNAVAILABLE",
                message="阶段 7 初筛任务状态不可用，请由招聘团队人工重试",
                clock=clock,
            )
            return True
        return await self._map_screening_run(
            db,
            context,
            result.run,
            worker_id=worker_id,
            clock=clock,
        )

    async def _execute_await_screening(
        self,
        db: AsyncSession,
        context: _OwnedRunContext,
        *,
        worker_id: str,
        settings: Settings,
        clock: Callable[[], datetime] | None,
    ) -> bool:
        application = await db.get(Application, context.application_id)
        if application is None:
            await db.rollback()
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code="APPLICATION_NOT_FOUND",
                message="处理任务对应的 Application 不存在",
                clock=clock,
            )
            return True
        if application.current_resume_id != context.resume_id:
            await db.rollback()
            await self._pause_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                reason=(
                    ApplicationProcessingWaitingReason.EXISTING_APPLICATION_RESUME_CHOICE.value
                ),
                clock=clock,
            )
            return True
        await db.rollback()
        state = await screening_service.get_state(db, context.application_id)
        latest = state.latest_run
        if latest is None:
            if state.report is not None and state.report.is_current and not state.report.is_outdated:
                await self._succeed_owned_run(
                    db,
                    context.id,
                    worker_id=worker_id,
                    clock=clock,
                )
                return True
            await self._advance_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                expected_step=ApplicationProcessingStep.AWAIT_SCREENING.value,
                next_step=ApplicationProcessingStep.TRIGGER_SCREENING.value,
                lease_seconds=settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
                clock=clock,
            )
            return False
        return await self._map_screening_run(
            db,
            context,
            latest,
            worker_id=worker_id,
            clock=clock,
        )

    async def _map_screening_run(
        self,
        db: AsyncSession,
        context: _OwnedRunContext,
        screening_run: ScreeningRun,
        *,
        worker_id: str,
        clock: Callable[[], datetime] | None,
    ) -> bool:
        if screening_run.status == ScreeningRunStatus.SUCCEEDED.value:
            await self._succeed_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                clock=clock,
            )
            return True
        if screening_run.status == ScreeningRunStatus.FAILED.value:
            await self._fail_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                code=screening_run.error_code or "SCREENING_FAILED",
                message=screening_run.error_message or "阶段 7 初筛失败，请人工重试",
                clock=clock,
            )
            return True
        if screening_run.status == ScreeningRunStatus.PAUSED.value:
            await self._pause_owned_run(
                db,
                context.id,
                worker_id=worker_id,
                reason=ApplicationProcessingWaitingReason.JOB_CLOSED.value,
                clock=clock,
            )
            return True
        if screening_run.status in _SCREENING_WAITING_STATUSES:
            await self._wait_for_screening(
                db,
                context.id,
                worker_id=worker_id,
                clock=clock,
            )
            return True
        await self._fail_owned_run(
            db,
            context.id,
            worker_id=worker_id,
            code="SCREENING_STATE_INVALID",
            message="阶段 7 初筛返回了无法识别的状态",
            clock=clock,
        )
        return True

    async def _recover_expired_runs(
        self,
        db: AsyncSession,
        now: datetime,
        max_attempts: int,
    ) -> None:
        expired = and_(
            ApplicationProcessingRun.status
            == ApplicationProcessingStatus.RUNNING.value,
            ApplicationProcessingRun.lease_expires_at.is_not(None),
            ApplicationProcessingRun.lease_expires_at < now,
        )
        await db.execute(
            update(ApplicationProcessingRun)
            .where(
                expired,
                ApplicationProcessingRun.current_step
                == ApplicationProcessingStep.AWAIT_SCREENING.value,
            )
            .values(
                status=ApplicationProcessingStatus.WAITING_SCREENING.value,
                lease_owner=None,
                lease_expires_at=None,
            )
        )
        await db.execute(
            update(ApplicationProcessingRun)
            .where(
                expired,
                ApplicationProcessingRun.current_step
                != ApplicationProcessingStep.AWAIT_SCREENING.value,
                ApplicationProcessingRun.attempt_count >= max_attempts,
            )
            .values(
                status=ApplicationProcessingStatus.FAILED.value,
                completed_at=now,
                error_code="APPLICATION_PROCESSING_ATTEMPTS_EXHAUSTED",
                error_message="处理任务已达到自动尝试上限，请由招聘团队人工重试",
                lease_owner=None,
                lease_expires_at=None,
            )
        )
        await db.execute(
            update(ApplicationProcessingRun)
            .where(
                expired,
                ApplicationProcessingRun.current_step
                != ApplicationProcessingStep.AWAIT_SCREENING.value,
                ApplicationProcessingRun.attempt_count < max_attempts,
            )
            .values(
                status=ApplicationProcessingStatus.QUEUED.value,
                error_code=None,
                error_message=None,
                completed_at=None,
                lease_owner=None,
                lease_expires_at=None,
            )
        )
        await db.execute(
            update(ApplicationProcessingRun)
            .where(
                ApplicationProcessingRun.status
                == ApplicationProcessingStatus.QUEUED.value,
                ApplicationProcessingRun.attempt_count >= max_attempts,
            )
            .values(
                status=ApplicationProcessingStatus.FAILED.value,
                completed_at=now,
                error_code="APPLICATION_PROCESSING_ATTEMPTS_EXHAUSTED",
                error_message="处理任务已达到自动尝试上限，请由招聘团队人工重试",
                lease_owner=None,
                lease_expires_at=None,
            )
        )

    async def _renew_and_read(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        lease_seconds: int,
        clock: Callable[[], datetime] | None,
    ) -> _OwnedRunContext:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        run.lease_expires_at = self._now(clock) + timedelta(seconds=lease_seconds)
        context = _OwnedRunContext(
            id=run.id,
            application_id=run.application_id,
            resume_id=run.resume_id,
            current_step=run.current_step,
        )
        await db.commit()
        return context

    async def _renew_owned_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        lease_seconds: int,
        clock: Callable[[], datetime] | None,
    ) -> None:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        run.lease_expires_at = self._now(clock) + timedelta(seconds=lease_seconds)
        await db.commit()

    async def _advance_owned_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        expected_step: str,
        next_step: str,
        lease_seconds: int,
        add_warning: str | None = None,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        if run.current_step != expected_step:
            raise ApplicationProcessingLeaseLostError(
                "处理任务步骤已被其他 Worker 推进"
            )
        run.current_step = next_step
        if add_warning is not None:
            warnings = list(run.warning_codes or [])
            if add_warning not in warnings:
                warnings.append(add_warning)
            run.warning_codes = warnings
        run.lease_expires_at = self._now(clock) + timedelta(seconds=lease_seconds)
        await db.commit()
        await db.refresh(run)
        return run

    async def _wait_for_screening(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        run.current_step = ApplicationProcessingStep.AWAIT_SCREENING.value
        run.status = ApplicationProcessingStatus.WAITING_SCREENING.value
        run.waiting_reason = None
        run.lease_owner = None
        run.lease_expires_at = None
        await db.commit()
        await db.refresh(run)
        return run

    async def _pause_owned_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        reason: str,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        run.status = ApplicationProcessingStatus.PAUSED.value
        run.waiting_reason = reason
        run.lease_owner = None
        run.lease_expires_at = None
        await db.commit()
        await db.refresh(run)
        return run

    async def _succeed_owned_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        run.current_step = ApplicationProcessingStep.COMPLETED.value
        run.status = (
            ApplicationProcessingStatus.SUCCEEDED_WITH_WARNINGS.value
            if run.warning_codes
            else ApplicationProcessingStatus.SUCCEEDED.value
        )
        run.waiting_reason = None
        run.completed_at = self._now(clock)
        run.error_code = None
        run.error_message = None
        run.lease_owner = None
        run.lease_expires_at = None
        await db.commit()
        await db.refresh(run)
        return run

    async def _fail_owned_run(
        self,
        db: AsyncSession,
        run_id: int,
        *,
        worker_id: str,
        code: str,
        message: str,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await self._owned_run_for_update(db, run_id, worker_id, clock)
        self._set_failed(
            run,
            code=code,
            message=message,
            completed_at=self._now(clock),
        )
        await db.commit()
        await db.refresh(run)
        return run

    async def _owned_run_for_update(
        self,
        db: AsyncSession,
        run_id: int,
        worker_id: str,
        clock: Callable[[], datetime] | None,
    ) -> ApplicationProcessingRun:
        run = await db.scalar(
            select(ApplicationProcessingRun)
            .where(ApplicationProcessingRun.id == run_id)
            .with_for_update()
        )
        if run is None:
            raise ApplicationProcessingRunNotFoundError("处理任务不存在")
        now = self._now(clock)
        if (
            run.status != ApplicationProcessingStatus.RUNNING.value
            or run.lease_owner != worker_id
            or run.lease_expires_at is None
            or run.lease_expires_at < now
        ):
            raise ApplicationProcessingLeaseLostError("处理任务租约已失效")
        return run

    @staticmethod
    def _set_failed(
        run: ApplicationProcessingRun,
        *,
        code: str,
        message: str,
        completed_at: datetime,
    ) -> None:
        run.status = ApplicationProcessingStatus.FAILED.value
        run.waiting_reason = None
        run.completed_at = completed_at
        run.error_code = ApplicationProcessingService._safe_code(code)
        run.error_message = message[:500]
        run.lease_owner = None
        run.lease_expires_at = None

    async def _validate_pause_recovered(
        self,
        db: AsyncSession,
        run: ApplicationProcessingRun,
    ) -> None:
        application = await db.get(Application, run.application_id)
        job = await db.get(Job, application.job_id) if application is not None else None
        recovered = False
        if run.waiting_reason == ApplicationProcessingWaitingReason.JOB_CLOSED.value:
            recovered = job is not None and job.status == "open"
        elif (
            run.waiting_reason
            == ApplicationProcessingWaitingReason.EXISTING_APPLICATION_RESUME_CHOICE.value
        ):
            recovered = (
                application is not None
                and application.current_resume_id == run.resume_id
            )
        if not recovered:
            raise ApplicationProcessingPauseNotRecoveredError(
                "暂停任务的恢复条件尚未满足"
            )

    @staticmethod
    def _safe_code(value: str) -> str:
        normalized = "".join(
            character if character.isascii() and (character.isupper() or character.isdigit())
            else "_"
            for character in value.upper()
        )
        normalized = normalized.strip("_") or "APPLICATION_PROCESSING_FAILED"
        if not normalized[0].isalpha():
            normalized = f"APPLICATION_PROCESSING_{normalized}"
        return normalized[:100]

    @staticmethod
    def _now(clock: Callable[[], datetime] | None) -> datetime:
        value = (clock or (lambda: datetime.now(timezone.utc)))()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Worker 时间必须包含时区")
        return value


application_processing_service = ApplicationProcessingService()


async def run_application_processing_worker_loop(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    interval_seconds: float,
    lease_seconds: int,
    batch_size: int,
    max_attempts: int,
) -> None:
    """Poll PostgreSQL processing runs; the process holds no authoritative queue."""
    worker_id = f"application-processing-worker-{uuid.uuid4()}"
    while True:
        try:
            for _ in range(batch_size):
                async with session_factory() as db:
                    run = await application_processing_service.claim_next_run(
                        db,
                        worker_id=worker_id,
                        lease_seconds=lease_seconds,
                        max_attempts=max_attempts,
                    )
                if run is None:
                    break
                try:
                    async with session_factory() as db:
                        await application_processing_service.execute_run(
                            db,
                            run.id,
                            worker_id=worker_id,
                        )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Application processing run failed unexpectedly (run_id=%s)",
                        run.id,
                    )
                    try:
                        async with session_factory() as recovery_db:
                            await application_processing_service.release_for_retry(
                                recovery_db,
                                run.id,
                                worker_id=worker_id,
                                max_attempts=max_attempts,
                            )
                    except Exception:
                        logger.exception(
                            "Application processing recovery failed (run_id=%s)",
                            run.id,
                        )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Application processing worker polling failed")
        await asyncio.sleep(interval_seconds)


__all__ = [
    "ApplicationProcessingActiveRunError",
    "ApplicationProcessingExecutionResult",
    "ApplicationProcessingLeaseLostError",
    "ApplicationProcessingPauseNotRecoveredError",
    "ApplicationProcessingRetryNotAllowedError",
    "ApplicationProcessingRunNotFoundError",
    "ApplicationProcessingService",
    "application_processing_service",
    "run_application_processing_worker_loop",
]
