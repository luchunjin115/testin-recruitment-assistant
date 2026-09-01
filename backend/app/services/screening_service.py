from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.screening_evaluation import (
    DeepSeekScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
)
from app.core.config import Settings, get_settings
from app.models.application import Application
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.schemas.experience_period import ExperiencePeriodFactsSnapshot
from app.schemas.job_evaluation_plan import JobEvaluationPlanStatus
from app.schemas.screening import (
    ScreeningOutdatedReason,
    ScreeningRunStatus,
    ScreeningRunTriggerType,
    ScreeningWaitingReason,
)
from app.services.application_decision_service import application_decision_service
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from app.services.experience_period_service import experience_period_service
from app.services.screening_evaluation_service import (
    ScreeningEvaluationV5Result,
    screening_evaluation_service,
)


class ScreeningServiceError(RuntimeError):
    code = "SCREENING_OPERATION_FAILED"


class ScreeningApplicationNotFoundError(ScreeningServiceError):
    code = "APPLICATION_NOT_FOUND"


class ScreeningResumeNotFoundError(ScreeningServiceError):
    code = "RESUME_NOT_FOUND"


class ScreeningResumeOwnershipError(ScreeningServiceError):
    code = "RESUME_OWNERSHIP_CONFLICT"


class ScreeningJobClosedError(ScreeningServiceError):
    code = "SCREENING_JOB_NOT_OPEN"


class ScreeningApplicationNotEligibleError(ScreeningServiceError):
    code = "SCREENING_APPLICATION_NOT_ELIGIBLE"


class ScreeningBatchLimitError(ScreeningServiceError):
    code = "SCREENING_BATCH_SIZE_INVALID"


class ScreeningBatchJobMismatchError(ScreeningServiceError):
    code = "SCREENING_BATCH_JOB_MISMATCH"


class ScreeningRunNotFoundError(ScreeningServiceError):
    code = "SCREENING_RUN_NOT_FOUND"


class ScreeningRunStateError(ScreeningServiceError):
    code = "SCREENING_RUN_STATE_INVALID"


class ScreeningReassessmentConfirmationRequiredError(ScreeningServiceError):
    code = "SCREENING_REASSESSMENT_CONFIRMATION_REQUIRED"


class ScreeningAdapter(Protocol):
    async def evaluate_v5(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ): ...

    async def repair_v5(
        self,
        *,
        sanitized_resume: str,
        confirmed_criteria: list[dict[str, Any]],
        original_response: str,
        validation_errors: list[dict[str, str]],
    ): ...


@dataclass(frozen=True, slots=True)
class ScreeningInputContext:
    application_id: int
    job_id: int
    resume_id: int
    plan_id: int | None
    desired_status: ScreeningRunStatus
    waiting_reason: ScreeningWaitingReason | None
    input_fingerprint: str
    jd_fingerprint: str
    plan_fingerprint: str
    resume_fingerprint: str
    evaluation_reference_at: datetime
    evaluation_timezone: str
    experience_period_facts_rule_version: str
    experience_period_facts_fingerprint: str
    experience_period_facts: ExperiencePeriodFactsSnapshot
    job_snapshot: dict[str, Any] | None
    evaluation_plan: dict[str, Any] | None
    sanitized_resume: str | None


@dataclass(frozen=True, slots=True)
class ScreeningTriggerResult:
    application_id: int
    run: ScreeningRun | None
    report: ScreeningReport | None
    reused_report: bool = False
    reused_run: bool = False


@dataclass(frozen=True, slots=True)
class ScreeningStateResult:
    application_id: int
    report: ScreeningReport | None
    latest_run: ScreeningRun | None


@dataclass(frozen=True, slots=True)
class ScreeningBatchFailure:
    application_id: int
    error_code: str
    error_message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class ScreeningBatchResult:
    job_id: int
    total_count: int
    reused_count: int
    queued_count: int
    results: tuple[ScreeningTriggerResult, ...]
    failures: tuple[ScreeningBatchFailure, ...]


class ScreeningService:
    _NONTERMINAL_STATUSES = (
        ScreeningRunStatus.WAITING_RESUME.value,
        ScreeningRunStatus.WAITING_PLAN.value,
        ScreeningRunStatus.QUEUED.value,
        ScreeningRunStatus.RUNNING.value,
        ScreeningRunStatus.PAUSED.value,
    )
    _WAITING_STATUSES = (
        ScreeningRunStatus.WAITING_RESUME.value,
        ScreeningRunStatus.WAITING_PLAN.value,
        ScreeningRunStatus.PAUSED.value,
    )

    async def get_state(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> ScreeningStateResult:
        application = await db.get(Application, application_id)
        if application is None:
            raise ScreeningApplicationNotFoundError("Application 不存在")
        report = await db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id,
                ScreeningReport.is_current.is_(True),
            )
        )
        if report is not None:
            changed = await self._reconcile_report_outdated(db, application, report)
            if changed:
                await db.commit()
                await db.refresh(report)
        latest_run = await db.scalar(
            select(ScreeningRun)
            .where(ScreeningRun.application_id == application_id)
            .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
            .limit(1)
        )
        return ScreeningStateResult(application_id, report, latest_run)

    async def list_reports(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> list[ScreeningReport]:
        application = await db.get(Application, application_id)
        if application is None:
            raise ScreeningApplicationNotFoundError("Application 不存在")
        rows = await db.scalars(
            select(ScreeningReport)
            .where(ScreeningReport.application_id == application_id)
            .order_by(
                ScreeningReport.is_current.desc(),
                ScreeningReport.generated_at.desc(),
                ScreeningReport.id.desc(),
            )
        )
        return list(rows.all())

    async def trigger(
        self,
        db: AsyncSession,
        application_id: int,
        *,
        trigger_type: ScreeningRunTriggerType = ScreeningRunTriggerType.AUTOMATIC,
        force: bool = False,
        confirmed: bool = False,
        settings: Settings | None = None,
        allow_closed_pending: bool = False,
    ) -> ScreeningTriggerResult:
        if force and not confirmed:
            raise ScreeningReassessmentConfirmationRequiredError(
                "重新评估必须由 HR 二次确认"
            )
        resolved = settings or get_settings()
        context: ScreeningInputContext | None = None
        try:
            application = await db.scalar(
                select(Application)
                .where(Application.id == application_id)
                .with_for_update()
            )
            if application is None:
                raise ScreeningApplicationNotFoundError("Application 不存在")
            if application.lifecycle_status != "active":
                raise ScreeningApplicationNotEligibleError(
                    "只有 active Application 可以开始 AI 初筛"
                )
            context = await self._build_context(db, application, resolved)
            if (
                context.desired_status is ScreeningRunStatus.PAUSED
                and not allow_closed_pending
            ):
                raise ScreeningJobClosedError("岗位关闭时不能开始 AI 初筛")

            report = await db.scalar(
                select(ScreeningReport)
                .where(
                    ScreeningReport.application_id == application_id,
                    ScreeningReport.is_current.is_(True),
                )
                .with_for_update()
            )
            if report is not None:
                await self._reconcile_report_outdated(db, application, report)
                if (
                    not force
                    and not report.is_outdated
                    and report.input_fingerprint == context.input_fingerprint
                ):
                    await db.commit()
                    return ScreeningTriggerResult(
                        application_id,
                        None,
                        report,
                        reused_report=True,
                    )

            existing = await self._find_nonterminal_run(
                db,
                application_id,
                context.input_fingerprint,
            )
            if existing is not None:
                await db.commit()
                return ScreeningTriggerResult(
                    application_id,
                    existing,
                    report,
                    reused_run=True,
                )

            run = ScreeningRun(
                application_id=application.id,
                job_id=context.job_id,
                resume_id=context.resume_id,
                job_evaluation_plan_id=context.plan_id,
                trigger_type=trigger_type.value,
                status=context.desired_status.value,
                waiting_reason=(
                    context.waiting_reason.value if context.waiting_reason else None
                ),
                input_fingerprint=context.input_fingerprint,
                prompt_version=resolved.SCREENING_EVALUATION_V5_PROMPT_VERSION,
                model_version=resolved.SCREENING_EVALUATION_MODEL,
                schema_version=resolved.SCREENING_EVALUATION_V5_SCHEMA_VERSION,
                redaction_version=resolved.SCREENING_REDACTION_VERSION,
                evaluation_reference_at=context.evaluation_reference_at,
                evaluation_timezone=context.evaluation_timezone,
                experience_period_facts_rule_version=(
                    context.experience_period_facts_rule_version
                ),
                experience_period_facts_fingerprint=(
                    context.experience_period_facts_fingerprint
                ),
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            return ScreeningTriggerResult(application_id, run, report)
        except IntegrityError:
            await self._safe_rollback(db)
            if context is None:
                raise
            existing = await self._find_nonterminal_run(
                db,
                application_id,
                context.input_fingerprint,
            )
            if existing is None:
                raise
            report = await db.scalar(
                select(ScreeningReport).where(
                    ScreeningReport.application_id == application_id,
                    ScreeningReport.is_current.is_(True),
                )
            )
            return ScreeningTriggerResult(
                application_id,
                existing,
                report,
                reused_run=True,
            )
        except Exception:
            await self._safe_rollback(db)
            raise

    async def trigger_batch_reassessment(
        self,
        db: AsyncSession,
        job_id: int,
        application_ids: list[int],
        *,
        confirmed: bool = False,
        settings: Settings | None = None,
    ) -> ScreeningBatchResult:
        if not confirmed:
            raise ScreeningReassessmentConfirmationRequiredError(
                "批量重新评估必须由 HR 二次确认"
            )
        if not 1 <= len(application_ids) <= 5 or len(application_ids) != len(
            set(application_ids)
        ):
            raise ScreeningBatchLimitError("一次只能重新评估 1—5 个不同 Application")
        job = await db.get(Job, job_id)
        if job is None:
            raise ScreeningBatchJobMismatchError("批量重新评估岗位不存在")
        if job.status != "open":
            raise ScreeningJobClosedError("岗位关闭时不能重新评估")
        rows = await db.scalars(
            select(Application).where(Application.id.in_(application_ids))
        )
        applications = {item.id: item for item in rows.all()}
        if set(applications) != set(application_ids) or any(
            item.job_id != job_id for item in applications.values()
        ):
            raise ScreeningBatchJobMismatchError(
                "批量重新评估只能包含同一岗位下存在的 Application"
            )
        await db.rollback()

        results: list[ScreeningTriggerResult] = []
        failures: list[ScreeningBatchFailure] = []
        for application_id in application_ids:
            try:
                results.append(await self.trigger(
                    db,
                    application_id,
                    trigger_type=ScreeningRunTriggerType.BATCH_REASSESSMENT,
                    force=True,
                    confirmed=True,
                    settings=settings,
                ))
            except ScreeningServiceError as exc:
                failures.append(
                    ScreeningBatchFailure(
                        application_id=application_id,
                        error_code=self._safe_code(exc.code),
                        error_message=self._safe_batch_error(exc),
                        retryable=False,
                    )
                )
            except Exception:
                await self._safe_rollback(db)
                failures.append(
                    ScreeningBatchFailure(
                        application_id=application_id,
                        error_code="SCREENING_OPERATION_FAILED",
                        error_message="该 Application 提交失败，请稍后重试",
                        retryable=True,
                    )
                )
        reused_count = sum(
            1 for item in results if item.reused_report or item.reused_run
        )
        return ScreeningBatchResult(
            job_id=job_id,
            total_count=len(application_ids),
            reused_count=reused_count,
            queued_count=len(results) - reused_count,
            results=tuple(results),
            failures=tuple(failures),
        )

    async def switch_current_resume(
        self,
        db: AsyncSession,
        application_id: int,
        resume_id: int,
    ) -> Application:
        now = datetime.now(timezone.utc)
        try:
            application = await db.scalar(
                select(Application)
                .where(Application.id == application_id)
                .with_for_update()
            )
            if application is None:
                raise ScreeningApplicationNotFoundError("Application 不存在")
            resume = await db.scalar(
                select(Resume).where(Resume.id == resume_id).with_for_update()
            )
            if resume is None:
                raise ScreeningResumeNotFoundError("Resume 不存在")
            if resume.candidate_id != application.candidate_id or resume.job_id not in {
                None,
                application.job_id,
            }:
                raise ScreeningResumeOwnershipError(
                    "Resume 不属于当前 Candidate 或岗位"
                )
            if application.current_resume_id == resume_id:
                await db.rollback()
                return application

            application.current_resume_id = resume_id
            report = await db.scalar(
                select(ScreeningReport)
                .where(
                    ScreeningReport.application_id == application_id,
                    ScreeningReport.is_current.is_(True),
                )
                .with_for_update()
            )
            if report is not None:
                self._add_outdated_reason(
                    report,
                    ScreeningOutdatedReason.RESUME_CHANGED,
                    now,
                )
            await self._supersede_not_started_runs(
                db,
                application_id,
                now,
                "当前 Resume 已变化，旧任务不会继续执行",
            )
            await db.commit()
            await db.refresh(application)
            return application
        except Exception:
            await db.rollback()
            raise

    async def after_application_commit(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> None:
        try:
            await self.trigger(
                db,
                application_id,
                trigger_type=ScreeningRunTriggerType.AUTOMATIC,
                allow_closed_pending=True,
            )
        except Exception:
            await self._safe_rollback(db)

    async def after_resume_ready(self, db: AsyncSession, resume_id: int) -> None:
        application_ids = list(
            (
                await db.scalars(
                    select(Application.id).where(
                        Application.current_resume_id == resume_id
                    )
                )
            ).all()
        )
        await db.rollback()
        for application_id in application_ids:
            await self._reconcile_waiting_run(db, application_id)

    async def after_plan_changed(
        self,
        db: AsyncSession,
        job_id: int,
        *,
        plan_ready: bool,
    ) -> None:
        application_ids = list(
            (await db.scalars(select(Application.id).where(Application.job_id == job_id))).all()
        )
        await db.rollback()
        for application_id in application_ids:
            application = await db.get(Application, application_id)
            if application is None:
                continue
            report = await db.scalar(
                select(ScreeningReport).where(
                    ScreeningReport.application_id == application_id,
                    ScreeningReport.is_current.is_(True),
                )
            )
            if report is not None:
                changed = await self._reconcile_report_outdated(db, application, report)
                if changed:
                    await db.commit()
                else:
                    await db.rollback()
                continue
            await db.rollback()
            await self._reconcile_waiting_run(db, application_id)

    async def after_job_closed(self, db: AsyncSession, job_id: int) -> None:
        try:
            await db.execute(
                update(ScreeningRun)
                .where(
                    ScreeningRun.job_id == job_id,
                    ScreeningRun.status.in_(
                        (
                            ScreeningRunStatus.WAITING_RESUME.value,
                            ScreeningRunStatus.WAITING_PLAN.value,
                            ScreeningRunStatus.QUEUED.value,
                        )
                    ),
                )
                .values(
                    status=ScreeningRunStatus.PAUSED.value,
                    waiting_reason=ScreeningWaitingReason.JOB_CLOSED.value,
                    lease_owner=None,
                    lease_expires_at=None,
                )
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    async def after_job_reopened(self, db: AsyncSession, job_id: int) -> None:
        application_ids = list(
            (
                await db.scalars(
                    select(ScreeningRun.application_id)
                    .where(
                        ScreeningRun.job_id == job_id,
                        ScreeningRun.status == ScreeningRunStatus.PAUSED.value,
                    )
                    .distinct()
                )
            ).all()
        )
        await db.rollback()
        for application_id in application_ids:
            await self._reconcile_waiting_run(db, application_id)

    async def claim_next_run(
        self,
        db: AsyncSession,
        *,
        worker_id: str,
        lease_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> ScreeningRun | None:
        now = (clock or (lambda: datetime.now(timezone.utc)))()
        try:
            await db.execute(
                update(ScreeningRun)
                .where(
                    ScreeningRun.status == ScreeningRunStatus.RUNNING.value,
                    ScreeningRun.lease_expires_at.is_not(None),
                    ScreeningRun.lease_expires_at < now,
                )
                .values(
                    status=ScreeningRunStatus.QUEUED.value,
                    waiting_reason=None,
                    started_at=None,
                    lease_owner=None,
                    lease_expires_at=None,
                    error_code=None,
                    error_message=None,
                    completed_at=None,
                )
            )
            run = await db.scalar(
                select(ScreeningRun)
                .where(ScreeningRun.status == ScreeningRunStatus.QUEUED.value)
                .order_by(ScreeningRun.created_at, ScreeningRun.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if run is None:
                await db.commit()
                return None
            job = await db.get(Job, run.job_id)
            if job is None or job.status != "open":
                run.status = ScreeningRunStatus.PAUSED.value
                run.waiting_reason = ScreeningWaitingReason.JOB_CLOSED.value
                run.lease_owner = None
                run.lease_expires_at = None
                await db.commit()
                return None
            run.status = ScreeningRunStatus.RUNNING.value
            run.waiting_reason = None
            run.started_at = now
            run.completed_at = None
            run.error_code = None
            run.error_message = None
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
        adapter: ScreeningAdapter | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> ScreeningRun:
        resolved = settings or get_settings()
        now_provider = clock or (lambda: datetime.now(timezone.utc))
        run = await db.get(ScreeningRun, run_id)
        if run is None:
            raise ScreeningRunNotFoundError("ScreeningRun 不存在")
        if run.status != ScreeningRunStatus.RUNNING.value:
            raise ScreeningRunStateError("只有 running 任务可以执行")
        application = await db.get(Application, run.application_id)
        if application is None:
            return await self._mark_failed(
                db,
                run_id,
                "APPLICATION_NOT_FOUND",
                "Application 已不存在，任务无法继续",
                now_provider(),
            )
        context = await self._build_context(db, application, resolved, allow_closed=True)
        if (
            context.input_fingerprint != run.input_fingerprint
            or context.desired_status
            in {ScreeningRunStatus.WAITING_PLAN, ScreeningRunStatus.WAITING_RESUME}
        ):
            return await self._mark_failed(
                db,
                run_id,
                "SCREENING_INPUT_OUTDATED_DURING_RUN",
                "任务输入已被新的 Resume、JD 或评价计划取代",
                now_provider(),
            )
        assert context.job_snapshot is not None
        assert context.evaluation_plan is not None
        assert context.sanitized_resume is not None
        await db.rollback()

        started = time.perf_counter()
        attempts = 0
        try:
            resolved_adapter = adapter or DeepSeekScreeningEvaluationAdapter(
                settings=resolved
            )
            result: ScreeningEvaluationV5Result | None = None
            for infrastructure_retry in range(2):
                try:
                    result = await screening_evaluation_service.evaluate_v5(
                        job_snapshot=context.job_snapshot,
                        evaluation_plan=context.evaluation_plan,
                        resume_text=context.sanitized_resume,
                        evaluation_reference_at=context.evaluation_reference_at,
                        evaluation_timezone=context.evaluation_timezone,
                        adapter=resolved_adapter,
                        settings=resolved,
                    )
                    attempts += result.audit.adapter_attempt_count
                    break
                except ScreeningEvaluationAdapterError as exc:
                    attempts += getattr(exc, "adapter_attempt_count", 1)
                    repair_started = getattr(exc, "content_repair_count", 0) > 0
                    if (
                        repair_started
                        or not exc.retryable
                        or infrastructure_retry == 1
                    ):
                        raise
                except Exception as exc:
                    attempts += getattr(exc, "adapter_attempt_count", 1)
                    raise
            assert result is not None
        except ScreeningEvaluationAdapterError as exc:
            audit = getattr(exc, "audit", None)
            message = (
                "模型服务暂时不可用，已自动重试一次，请稍后重新评估"
                if exc.retryable
                else self._safe_evaluation_error(exc.code)
            )
            return await self._mark_failed(
                db,
                run_id,
                exc.code,
                message,
                now_provider(),
                attempts=attempts,
                duration_ms=int((time.perf_counter() - started) * 1000),
                input_tokens=getattr(audit, "input_tokens", None),
                output_tokens=getattr(audit, "output_tokens", None),
            )
        except Exception as exc:
            audit = getattr(exc, "audit", None)
            code = getattr(exc, "code", "SCREENING_EVALUATION_UNEXPECTED_ERROR")
            return await self._mark_failed(
                db,
                run_id,
                code,
                self._safe_evaluation_error(code),
                now_provider(),
                attempts=max(attempts, 1),
                duration_ms=int((time.perf_counter() - started) * 1000),
                input_tokens=getattr(audit, "input_tokens", None),
                output_tokens=getattr(audit, "output_tokens", None),
            )

        try:
            return await self._save_success(
                db,
                run_id,
                context,
                result,
                completed_at=now_provider(),
                attempts=attempts,
                duration_ms=int((time.perf_counter() - started) * 1000),
                settings=resolved,
            )
        except Exception:
            await db.rollback()
            return await self._mark_failed(
                db,
                run_id,
                "SCREENING_DATABASE_COMMIT_FAILED",
                "新报告保存失败，旧成功报告已保留",
                now_provider(),
                attempts=attempts,
                duration_ms=int((time.perf_counter() - started) * 1000),
                input_tokens=result.metadata.input_tokens,
                output_tokens=result.metadata.output_tokens,
            )

    async def _save_success(
        self,
        db: AsyncSession,
        run_id: int,
        original: ScreeningInputContext,
        result: ScreeningEvaluationV5Result,
        *,
        completed_at: datetime,
        attempts: int,
        duration_ms: int,
        settings: Settings,
    ) -> ScreeningRun:
        run = await db.scalar(
            select(ScreeningRun).where(ScreeningRun.id == run_id).with_for_update()
        )
        if run is None:
            raise ScreeningRunNotFoundError("ScreeningRun 不存在")
        application = await db.scalar(
            select(Application)
            .where(Application.id == run.application_id)
            .with_for_update()
        )
        if application is None:
            raise ScreeningApplicationNotFoundError("Application 不存在")
        current = await self._build_context(db, application, settings, allow_closed=True)
        if current.input_fingerprint != original.input_fingerprint:
            return await self._mark_failed(
                db,
                run_id,
                "SCREENING_INPUT_OUTDATED_DURING_RUN",
                "任务输入已被新的 Resume、JD 或评价计划取代",
                completed_at,
                attempts=attempts,
                duration_ms=duration_ms,
            )

        previous_report = await db.scalar(
            select(ScreeningReport)
            .where(
                ScreeningReport.application_id == application.id,
                ScreeningReport.is_current.is_(True),
            )
            .with_for_update()
        )
        if previous_report is not None:
            previous_report.is_current = False
            await db.flush()
        report = ScreeningReport(
            application_id=application.id,
            is_current=True,
        )
        db.add(report)
        payload = result.report
        report.job_id = current.job_id
        report.resume_id = current.resume_id
        assert current.plan_id is not None
        report.job_evaluation_plan_id = current.plan_id
        report.overall_score = payload.overall_score
        report.display_label = payload.display_label
        report.overall_summary = payload.overall_summary
        report.requirement_assessments = []
        report.bonus_highlights = []
        report.tradeoff_reason = None
        report.interview_questions = list(payload.hr_follow_up_questions)
        report.v5_report = payload.model_dump(mode="json")
        report.input_fingerprint = current.input_fingerprint
        report.jd_fingerprint = current.jd_fingerprint
        report.plan_fingerprint = current.plan_fingerprint
        report.resume_fingerprint = current.resume_fingerprint
        report.prompt_version = result.metadata.prompt_version
        report.model_version = result.metadata.model_version
        report.schema_version = result.metadata.schema_version
        report.redaction_version = result.metadata.redaction_version
        report.evaluation_reference_at = current.evaluation_reference_at
        report.evaluation_timezone = current.evaluation_timezone
        report.experience_period_facts_rule_version = (
            current.experience_period_facts_rule_version
        )
        report.experience_period_facts = current.experience_period_facts.model_dump(
            mode="json"
        )
        report.is_outdated = False
        report.outdated_reasons = []
        report.outdated_at = None
        report.generated_at = completed_at

        await db.flush()
        await application_decision_service.append_screening_handoff(
            db,
            application,
            report_id=report.id,
            succeeded=True,
        )

        run.status = ScreeningRunStatus.SUCCEEDED.value
        run.waiting_reason = None
        run.completed_at = completed_at
        run.error_code = None
        run.error_message = None
        run.input_tokens = result.metadata.input_tokens
        run.output_tokens = result.metadata.output_tokens
        run.duration_ms = duration_ms
        run.attempt_count = attempts
        run.model_version = result.metadata.model_version
        run.prompt_version = result.metadata.prompt_version
        run.schema_version = result.metadata.schema_version
        run.evaluation_reference_at = current.evaluation_reference_at
        run.evaluation_timezone = current.evaluation_timezone
        run.experience_period_facts_rule_version = (
            current.experience_period_facts_rule_version
        )
        run.experience_period_facts_fingerprint = (
            current.experience_period_facts_fingerprint
        )
        run.lease_owner = None
        run.lease_expires_at = None
        await db.commit()
        await db.refresh(run)
        return run

    async def _mark_failed(
        self,
        db: AsyncSession,
        run_id: int,
        code: str,
        message: str,
        completed_at: datetime,
        *,
        attempts: int = 0,
        duration_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> ScreeningRun:
        try:
            run = await db.scalar(
                select(ScreeningRun)
                .where(ScreeningRun.id == run_id)
                .with_for_update()
            )
            if run is None:
                raise ScreeningRunNotFoundError("ScreeningRun 不存在")
            run.status = ScreeningRunStatus.FAILED.value
            run.waiting_reason = None
            run.completed_at = completed_at
            run.error_code = self._safe_code(code)
            run.error_message = message[:500]
            run.attempt_count = min(max(attempts, 0), 3)
            run.duration_ms = duration_ms
            run.input_tokens = input_tokens
            run.output_tokens = output_tokens
            run.lease_owner = None
            run.lease_expires_at = None
            application = await db.scalar(
                select(Application)
                .where(Application.id == run.application_id)
                .with_for_update()
            )
            if application is not None:
                report_id = await db.scalar(
                    select(ScreeningReport.id).where(
                        ScreeningReport.application_id == application.id,
                        ScreeningReport.is_current.is_(True),
                    )
                )
                await application_decision_service.append_screening_handoff(
                    db,
                    application,
                    report_id=report_id,
                    succeeded=False,
                )
            await db.commit()
            await db.refresh(run)
            return run
        except Exception:
            await db.rollback()
            raise

    async def _reconcile_waiting_run(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> None:
        try:
            application = await db.scalar(
                select(Application)
                .where(Application.id == application_id)
                .with_for_update()
            )
            if application is None:
                await db.rollback()
                return
            if application.lifecycle_status != "active":
                await db.rollback()
                return
            run = await db.scalar(
                select(ScreeningRun)
                .where(
                    ScreeningRun.application_id == application_id,
                    ScreeningRun.status.in_(self._WAITING_STATUSES),
                )
                .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
                .with_for_update()
                .limit(1)
            )
            if run is None:
                await db.rollback()
                return
            report = await db.scalar(
                select(ScreeningReport).where(
                    ScreeningReport.application_id == application_id,
                    ScreeningReport.is_current.is_(True),
                )
            )
            if (
                report is not None
                and run.trigger_type == ScreeningRunTriggerType.AUTOMATIC.value
            ):
                await db.rollback()
                return
            settings = get_settings()
            context = await self._build_context(db, application, settings)
            duplicate = await self._find_nonterminal_run(
                db,
                application_id,
                context.input_fingerprint,
                exclude_run_id=run.id,
            )
            if duplicate is not None:
                run.status = ScreeningRunStatus.FAILED.value
                run.waiting_reason = None
                run.completed_at = datetime.now(timezone.utc)
                run.error_code = "SCREENING_RUN_SUPERSEDED"
                run.error_message = "已有相同输入的任务，旧等待任务已停止"
            else:
                run.resume_id = context.resume_id
                run.job_evaluation_plan_id = context.plan_id
                run.input_fingerprint = context.input_fingerprint
                run.prompt_version = settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
                run.model_version = settings.SCREENING_EVALUATION_MODEL
                run.schema_version = settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
                run.redaction_version = settings.SCREENING_REDACTION_VERSION
                run.evaluation_reference_at = context.evaluation_reference_at
                run.evaluation_timezone = context.evaluation_timezone
                run.experience_period_facts_rule_version = (
                    context.experience_period_facts_rule_version
                )
                run.experience_period_facts_fingerprint = (
                    context.experience_period_facts_fingerprint
                )
                run.status = context.desired_status.value
                run.waiting_reason = (
                    context.waiting_reason.value if context.waiting_reason else None
                )
                run.error_code = None
                run.error_message = None
                run.completed_at = None
            await db.commit()
        except IntegrityError:
            await db.rollback()
        except Exception:
            await db.rollback()
            raise

    async def _build_context(
        self,
        db: AsyncSession,
        application: Application,
        settings: Settings,
        *,
        allow_closed: bool = False,
    ) -> ScreeningInputContext:
        job = await db.get(Job, application.job_id)
        resume = await db.get(Resume, application.current_resume_id)
        if job is None or resume is None:
            raise ScreeningResumeNotFoundError("Application 的岗位或 Resume 不存在")
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(job)
        jd_fingerprint = job_evaluation_plan_service.fingerprint_snapshot(snapshot)
        plan = await db.scalar(
            select(JobEvaluationPlan).where(
                JobEvaluationPlan.job_id == job.id,
                JobEvaluationPlan.is_current.is_(True),
            )
        )
        latest_plan = plan or await db.scalar(
            select(JobEvaluationPlan)
            .where(JobEvaluationPlan.job_id == job.id)
            .order_by(JobEvaluationPlan.created_at.desc(), JobEvaluationPlan.id.desc())
            .limit(1)
        )
        resume_ready = (
            resume.parse_status == "parsed"
            and isinstance(resume.raw_text, str)
            and bool(resume.raw_text.strip())
        )
        sanitized_resume = (
            screening_evaluation_service.sanitize_resume_text(resume.raw_text or "")
            if resume_ready
            else ""
        )
        resume_ready = resume_ready and bool(sanitized_resume)
        plan_ready, plan_waiting_reason = self._classify_v5_plan(
            snapshot,
            jd_fingerprint,
            plan,
            latest_plan,
        )
        if job.status != "open" and not allow_closed:
            desired = ScreeningRunStatus.PAUSED
            waiting_reason = ScreeningWaitingReason.JOB_CLOSED
        elif not resume_ready:
            desired = ScreeningRunStatus.WAITING_RESUME
            waiting_reason = None
        elif not plan_ready:
            desired = ScreeningRunStatus.WAITING_PLAN
            waiting_reason = plan_waiting_reason
        else:
            desired = ScreeningRunStatus.QUEUED
            waiting_reason = None

        plan_payload = (
            {
                "id": plan.id,
                "jd_fingerprint": plan.jd_fingerprint,
                "input_fingerprint": plan.input_fingerprint,
                "edit_version": plan.edit_version,
                "confirmed_at": (
                    plan.confirmed_at.isoformat() if plan.confirmed_at else None
                ),
                "criteria": plan.v5_criteria,
                "prompt_version": plan.prompt_version,
                "model_version": plan.model_version,
                "schema_version": plan.schema_version,
            }
            if plan_ready and plan is not None
            else {
                "state": "plan_not_ready",
                "plan_id": latest_plan.id if latest_plan is not None else None,
                "plan_status": (
                    latest_plan.status if latest_plan is not None else None
                ),
                "waiting_reason": (
                    plan_waiting_reason.value if plan_waiting_reason else None
                ),
            }
        )
        plan_fingerprint = self._sha256(plan_payload)
        resume_fingerprint = self._sha256(
            {"sanitized_resume": sanitized_resume if resume_ready else "resume_not_ready"}
        )
        if application.applied_at is None:
            raise ScreeningServiceError("Application 投递时间缺失")
        evaluation_reference_at = application.applied_at
        experience_period_facts = experience_period_service.build(
            sanitized_resume if resume_ready else "",
            evaluation_reference_at=evaluation_reference_at,
            evaluation_timezone=settings.SCREENING_EVALUATION_TIMEZONE,
            rule_version=settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION,
        )
        experience_period_facts_fingerprint = experience_period_service.fingerprint(
            experience_period_facts
        )
        fingerprint_payload = {
            "application_id": application.id,
            "job_id": job.id,
            "jd_fingerprint": jd_fingerprint,
            "resume_id": resume.id,
            "resume_fingerprint": resume_fingerprint,
            "plan_id": plan.id if plan_ready and plan is not None else None,
            "plan_fingerprint": plan_fingerprint,
            "prompt_version": settings.SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "model_version": settings.SCREENING_EVALUATION_MODEL,
            "schema_version": settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "redaction_version": settings.SCREENING_REDACTION_VERSION,
            "evaluation_reference_at": evaluation_reference_at.isoformat(),
            "evaluation_timezone": settings.SCREENING_EVALUATION_TIMEZONE,
            "experience_period_facts_rule_version": (
                settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION
            ),
            "experience_period_facts_fingerprint": (
                experience_period_facts_fingerprint
            ),
        }
        return ScreeningInputContext(
            application_id=application.id,
            job_id=job.id,
            resume_id=resume.id,
            plan_id=plan.id if plan is not None else None,
            desired_status=desired,
            waiting_reason=waiting_reason,
            input_fingerprint=self._sha256(fingerprint_payload),
            jd_fingerprint=jd_fingerprint,
            plan_fingerprint=plan_fingerprint,
            resume_fingerprint=resume_fingerprint,
            evaluation_reference_at=evaluation_reference_at,
            evaluation_timezone=settings.SCREENING_EVALUATION_TIMEZONE,
            experience_period_facts_rule_version=(
                settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION
            ),
            experience_period_facts_fingerprint=(
                experience_period_facts_fingerprint
            ),
            experience_period_facts=experience_period_facts,
            job_snapshot=snapshot.model_dump(mode="json") if plan_ready else None,
            evaluation_plan=(
                {
                    "schema_version": "5.0",
                    "criteria": list(plan.v5_criteria or []),
                }
                if plan_ready and plan is not None
                else None
            ),
            sanitized_resume=sanitized_resume if resume_ready else None,
        )

    @staticmethod
    def _classify_v4_plan(
        current_snapshot: Any,
        current_jd_fingerprint: str,
        current: JobEvaluationPlan | None,
        latest: JobEvaluationPlan | None,
    ) -> tuple[bool, ScreeningWaitingReason | None]:
        """Historical 4.0 classifier kept for read-only regression evidence."""
        if current is None:
            return False, (
                ScreeningWaitingReason.PLAN_OUTDATED
                if latest is not None
                else ScreeningWaitingReason.PLAN_MISSING
            )
        if current.schema_version != "4.0":
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        if current.jd_fingerprint != current_jd_fingerprint:
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if job_evaluation_plan_service.is_contract_outdated(current):
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        if current.input_fingerprint != job_evaluation_plan_service.fingerprint_input(
            current_snapshot
        ):
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if current.status == JobEvaluationPlanStatus.GENERATING.value:
            return False, ScreeningWaitingReason.PLAN_GENERATING
        if current.status == "pending_confirmation":
            return False, ScreeningWaitingReason.PLAN_PENDING_CONFIRMATION
        if current.status == JobEvaluationPlanStatus.FAILED.value:
            return False, ScreeningWaitingReason.PLAN_FAILED
        if current.status == JobEvaluationPlanStatus.OUTDATED.value:
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if current.status != JobEvaluationPlanStatus.READY.value or not current.is_current:
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        try:
            read_model = job_evaluation_plan_service.build_read_model(current)
            facts = read_model.requirement_facts or []
            criteria = read_model.evaluation_criteria or []
            fact_ids = {fact.fact_id for fact in facts}
            grouped_fact_ids = [
                fact_id for criterion in criteria for fact_id in criterion.fact_ids
            ]
            shape_ready = (
                read_model.schema_version == "4.0"
                and read_model.input_snapshot.schema_version == "4.0"
                and bool(facts)
                and bool(criteria)
                and len(grouped_fact_ids) == len(fact_ids)
                and set(grouped_fact_ids) == fact_ids
            )
        except (AttributeError, TypeError, ValueError):
            shape_ready = False
        if not shape_ready:
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        return True, None

    @staticmethod
    def _classify_v5_plan(
        current_snapshot: Any,
        current_jd_fingerprint: str,
        current: JobEvaluationPlan | None,
        latest: JobEvaluationPlan | None,
    ) -> tuple[bool, ScreeningWaitingReason | None]:
        if current is None:
            return False, (
                ScreeningWaitingReason.PLAN_OUTDATED
                if latest is not None
                else ScreeningWaitingReason.PLAN_MISSING
            )
        if current.schema_version != "5.0":
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        if current.jd_fingerprint != current_jd_fingerprint:
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if job_evaluation_plan_service.is_contract_outdated(current):
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        if current.input_fingerprint != job_evaluation_plan_service.fingerprint_input(
            current_snapshot
        ):
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if current.status == JobEvaluationPlanStatus.GENERATING.value:
            return False, ScreeningWaitingReason.PLAN_GENERATING
        if current.status == "pending_confirmation":
            return False, ScreeningWaitingReason.PLAN_PENDING_CONFIRMATION
        if current.status == JobEvaluationPlanStatus.FAILED.value:
            return False, ScreeningWaitingReason.PLAN_FAILED
        if current.status == JobEvaluationPlanStatus.OUTDATED.value:
            return False, ScreeningWaitingReason.PLAN_OUTDATED
        if current.status != JobEvaluationPlanStatus.READY.value or not current.is_current:
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        try:
            read_model = job_evaluation_plan_service.build_read_model(current)
            criteria = read_model.v5_criteria or []
            criterion_ids = [item.criterion_id for item in criteria]
            shape_ready = (
                read_model.schema_version == "5.0"
                and read_model.input_snapshot.schema_version == "5.0"
                and bool(criteria)
                and len(criterion_ids) == len(set(criterion_ids))
                and read_model.edit_version is not None
                and read_model.confirmed_at is not None
            )
        except (AttributeError, TypeError, ValueError):
            shape_ready = False
        if not shape_ready:
            return False, ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
        return True, None

    def _build_contract_upgrade_pause_context(
        self,
        application: Application,
        job: Job,
        resume: Resume,
        settings: Settings,
        *,
        allow_closed: bool,
    ) -> ScreeningInputContext:
        """Pause Stage 7 until it has a confirmed five-section input contract."""
        if application.applied_at is None:
            raise ScreeningServiceError("Application 投递时间缺失")
        jd_payload = {
            "job_id": job.id,
            "title": job.title,
            "department": job.department,
            "job_background": job.job_background,
            "job_responsibilities": job.job_responsibilities,
            "candidate_requirements": job.candidate_requirements,
            "preferred_qualifications": job.preferred_qualifications,
        }
        jd_fingerprint = self._sha256(jd_payload)
        resume_fingerprint = self._sha256({"state": "stage7_contract_upgrade"})
        plan_fingerprint = self._sha256({"state": "stage7_contract_upgrade"})
        experience_period_facts = experience_period_service.build(
            "",
            evaluation_reference_at=application.applied_at,
            evaluation_timezone=settings.SCREENING_EVALUATION_TIMEZONE,
            rule_version=settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION,
        )
        facts_fingerprint = experience_period_service.fingerprint(
            experience_period_facts
        )
        desired = (
            ScreeningRunStatus.PAUSED
            if job.status != "open" and not allow_closed
            else ScreeningRunStatus.WAITING_PLAN
        )
        input_fingerprint = self._sha256(
            {
                "application_id": application.id,
                "job_id": job.id,
                "resume_id": resume.id,
                "jd_fingerprint": jd_fingerprint,
                "state": "stage7_contract_upgrade",
            }
        )
        return ScreeningInputContext(
            application_id=application.id,
            job_id=job.id,
            resume_id=resume.id,
            plan_id=None,
            desired_status=desired,
            waiting_reason=(
                ScreeningWaitingReason.JOB_CLOSED
                if desired is ScreeningRunStatus.PAUSED
                else ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
            ),
            input_fingerprint=input_fingerprint,
            jd_fingerprint=jd_fingerprint,
            plan_fingerprint=plan_fingerprint,
            resume_fingerprint=resume_fingerprint,
            evaluation_reference_at=application.applied_at,
            evaluation_timezone=settings.SCREENING_EVALUATION_TIMEZONE,
            experience_period_facts_rule_version=(
                settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION
            ),
            experience_period_facts_fingerprint=facts_fingerprint,
            experience_period_facts=experience_period_facts,
            job_snapshot=None,
            evaluation_plan=None,
            sanitized_resume=None,
        )

    async def _reconcile_report_outdated(
        self,
        db: AsyncSession,
        application: Application,
        report: ScreeningReport,
    ) -> bool:
        changed = False
        now = datetime.now(timezone.utc)
        if report.resume_id != application.current_resume_id:
            changed |= self._add_outdated_reason(
                report, ScreeningOutdatedReason.RESUME_CHANGED, now
            )
        plan = await db.scalar(
            select(JobEvaluationPlan).where(
                JobEvaluationPlan.job_id == application.job_id,
                JobEvaluationPlan.is_current.is_(True),
            )
        )
        current_v5_plan_matches_report = (
            plan is not None
            and plan.schema_version == "5.0"
            and report.job_evaluation_plan_id == plan.id
        )
        if not current_v5_plan_matches_report:
            changed |= self._add_outdated_reason(
                report,
                ScreeningOutdatedReason.EVALUATION_PLAN_CHANGED,
                now,
            )
        else:
            job = await db.get(Job, application.job_id)
            if job is not None:
                snapshot = job_evaluation_plan_service.build_v5_input_snapshot(job)
                current_jd = job_evaluation_plan_service.fingerprint_snapshot(snapshot)
                if report.jd_fingerprint != current_jd:
                    changed |= self._add_outdated_reason(
                        report,
                        ScreeningOutdatedReason.JD_CHANGED,
                        now,
                    )
        return changed

    @staticmethod
    def _add_outdated_reason(
        report: ScreeningReport,
        reason: ScreeningOutdatedReason,
        now: datetime,
    ) -> bool:
        reasons = list(report.outdated_reasons or [])
        if reason.value in reasons:
            return False
        reasons.append(reason.value)
        report.outdated_reasons = reasons
        report.is_outdated = True
        report.outdated_at = report.outdated_at or now
        return True

    @staticmethod
    async def _find_nonterminal_run(
        db: AsyncSession,
        application_id: int,
        _fingerprint: str,
        *,
        exclude_run_id: int | None = None,
    ) -> ScreeningRun | None:
        statement = select(ScreeningRun).where(
            ScreeningRun.application_id == application_id,
            ScreeningRun.status.in_(ScreeningService._NONTERMINAL_STATUSES),
        )
        if exclude_run_id is not None:
            statement = statement.where(ScreeningRun.id != exclude_run_id)
        return await db.scalar(
            statement.order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
        )

    @staticmethod
    async def _supersede_not_started_runs(
        db: AsyncSession,
        application_id: int,
        completed_at: datetime,
        message: str,
    ) -> None:
        await db.execute(
            update(ScreeningRun)
            .where(
                ScreeningRun.application_id == application_id,
                ScreeningRun.status.in_(
                    (
                        ScreeningRunStatus.WAITING_RESUME.value,
                        ScreeningRunStatus.WAITING_PLAN.value,
                        ScreeningRunStatus.QUEUED.value,
                        ScreeningRunStatus.PAUSED.value,
                    )
                ),
            )
            .values(
                status=ScreeningRunStatus.FAILED.value,
                waiting_reason=None,
                completed_at=completed_at,
                error_code="SCREENING_RUN_SUPERSEDED",
                error_message=message,
                lease_owner=None,
                lease_expires_at=None,
            )
        )

    @staticmethod
    def _sha256(payload: Any) -> str:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_code(code: str) -> str:
        normalized = "".join(
            character if character.isupper() or character.isdigit() or character == "_" else "_"
            for character in str(code).upper()
        )
        return (normalized or "SCREENING_OPERATION_FAILED")[:100]

    @staticmethod
    def _safe_evaluation_error(code: str) -> str:
        messages = {
            "SCREENING_EVALUATION_AUTHENTICATION_ERROR": "AI 初筛服务认证不可用，请联系管理员",
            "SCREENING_EVALUATION_QUOTA_ERROR": "AI 初筛服务配额不足，请联系管理员",
            "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT": "AI 初筛结果未通过安全与业务校验",
            "SCREENING_EVALUATION_INPUT_ERROR": "当前初筛输入不满足评价条件",
            "SCREENING_EVALUATION_DISABLED": "AI 初筛功能当前未启用",
            "SCREENING_EVALUATION_CONFIGURATION_ERROR": "AI 初筛服务配置不可用",
        }
        return messages.get(code, "AI 初筛运行失败，旧成功报告未受影响")

    @staticmethod
    def _safe_batch_error(exc: ScreeningServiceError) -> str:
        messages = {
            "SCREENING_APPLICATION_NOT_ELIGIBLE": "该 Application 当前不可重新评估",
            "SCREENING_JOB_NOT_OPEN": "岗位关闭时不能重新评估",
            "SCREENING_REASSESSMENT_CONFIRMATION_REQUIRED": "重新评估缺少 HR 二次确认",
        }
        return messages.get(exc.code, "该 Application 当前无法提交重新评估")

    @staticmethod
    async def _safe_rollback(db: AsyncSession) -> None:
        try:
            result = db.rollback()
            if hasattr(result, "__await__"):
                await result
        except Exception:
            pass


screening_service = ScreeningService()


async def run_screening_worker_loop(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    interval_seconds: float,
    lease_seconds: int,
    batch_size: int,
) -> None:
    """Poll durable PostgreSQL runs; the task itself carries no task state."""
    worker_id = f"screening-worker-{uuid.uuid4()}"
    while True:
        processed = 0
        try:
            for _ in range(batch_size):
                async with session_factory() as db:
                    run = await screening_service.claim_next_run(
                        db,
                        worker_id=worker_id,
                        lease_seconds=lease_seconds,
                    )
                    if run is None:
                        break
                    await screening_service.execute_run(db, run.id)
                    processed += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            # Durable status and leases make the next polling pass recoverable.
            pass
        if processed == 0:
            await asyncio.sleep(interval_seconds)
