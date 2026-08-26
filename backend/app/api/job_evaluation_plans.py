from __future__ import annotations

import inspect

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.job_evaluation_plan import (
    JobEvaluationPlanRead,
    JobEvaluationPlanV5ConfirmRequest,
    JobEvaluationPlanV5DraftSaveRequest,
    JobEvaluationPlanV5VersionForkRequest,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanConfigurationError,
    JobEvaluationPlanDisabledError,
    JobEvaluationPlanJobNotFoundError,
    JobEvaluationPlanJobNotOpenError,
    JobEvaluationPlanNotFoundError,
    JobEvaluationPlanNotEditableError,
    JobEvaluationPlanNotConfirmableError,
    JobEvaluationPlanNotRegenerableError,
    JobEvaluationPlanContentError,
    PlanEditConflictError,
    job_evaluation_plan_service,
)
from app.services.screening_service import screening_service


router = APIRouter(prefix="/jobs", tags=["job-evaluation-plans"])


async def _notify_screening_plan_changed(
    db: AsyncSession,
    job_id: int,
    *,
    plan_ready: bool,
) -> None:
    try:
        await screening_service.after_plan_changed(
            db,
            job_id,
            plan_ready=plan_ready,
        )
    except Exception:
        rollback_result = db.rollback()
        if inspect.isawaitable(rollback_result):
            await rollback_result


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _map_expected_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobEvaluationPlanJobNotFoundError):
        return _error(status.HTTP_404_NOT_FOUND, exc.code, "岗位不存在")
    if isinstance(exc, JobEvaluationPlanNotFoundError):
        return _error(
            status.HTTP_404_NOT_FOUND,
            exc.code,
            "当前岗位还没有评价计划",
        )
    if isinstance(exc, JobEvaluationPlanJobNotOpenError):
        return _error(
            status.HTTP_409_CONFLICT,
            exc.code,
            "只有开放岗位可以生成评价计划",
        )
    if isinstance(exc, JobEvaluationPlanNotRegenerableError):
        return _error(
            status.HTTP_409_CONFLICT,
            exc.code,
            "只有失败的当前评价计划可以重新生成",
        )
    if isinstance(exc, JobEvaluationPlanNotConfirmableError):
        return _error(
            status.HTTP_409_CONFLICT,
            exc.code,
            "只有当前、未过期且版本匹配的 5.0 待确认计划可以确认",
        )
    if isinstance(exc, JobEvaluationPlanNotEditableError):
        return _error(
            status.HTTP_409_CONFLICT,
            exc.code,
            "只有当前、未过期的 5.0 待确认计划可以编辑",
        )
    if isinstance(exc, PlanEditConflictError):
        return _error(
            status.HTTP_409_CONFLICT,
            exc.code,
            "评价计划已更新，请刷新后重试",
        )
    if isinstance(exc, JobEvaluationPlanContentError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            exc.code,
            "评价计划编辑内容未通过校验",
        )
    if isinstance(exc, JobEvaluationPlanDisabledError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            exc.code,
            "岗位评价计划功能当前未启用",
        )
    if isinstance(exc, JobEvaluationPlanConfigurationError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            exc.code,
            "岗位评价计划服务配置不可用",
        )
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "JOB_EVALUATION_PLAN_OPERATION_FAILED",
        "岗位评价计划操作失败，请稍后重试",
    )


@router.get(
    "/{job_id}/evaluation-plan",
    response_model=JobEvaluationPlanRead,
)
async def get_current_evaluation_plan(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.get_plan_for_display(db, job_id)
    except Exception as exc:
        raise _map_expected_error(exc) from exc
    if plan is None:
        raise _map_expected_error(
            JobEvaluationPlanNotFoundError("当前岗位还没有评价计划")
        )
    return job_evaluation_plan_service.build_read_model(plan)


@router.post(
    "/{job_id}/evaluation-plan/generate",
    response_model=JobEvaluationPlanRead,
)
async def generate_current_evaluation_plan(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.generate_v5_for_job(db, job_id)
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc


@router.post(
    "/{job_id}/evaluation-plan/regenerate",
    response_model=JobEvaluationPlanRead,
)
async def regenerate_failed_evaluation_plan(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.regenerate_failed_v5_plan(
            db,
            job_id,
        )
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc


@router.post(
    "/{job_id}/evaluation-plan/confirm",
    response_model=JobEvaluationPlanRead,
)
async def confirm_current_evaluation_plan(
    job_id: int,
    data: JobEvaluationPlanV5ConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.confirm_current_plan(
            db,
            job_id,
            data.edit_version,
        )
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc


@router.put(
    "/{job_id}/evaluation-plan/draft",
    response_model=JobEvaluationPlanRead,
)
async def save_current_evaluation_plan_draft(
    job_id: int,
    data: JobEvaluationPlanV5DraftSaveRequest,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.save_draft(db, job_id, data)
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc


@router.post(
    "/{job_id}/evaluation-plan/versions",
    response_model=JobEvaluationPlanRead,
)
async def create_evaluation_plan_version(
    job_id: int,
    data: JobEvaluationPlanV5VersionForkRequest,
    db: AsyncSession = Depends(get_db),
) -> JobEvaluationPlanRead:
    try:
        plan = await job_evaluation_plan_service.create_new_version_from_confirmed(
            db,
            job_id,
            data.edit_version,
        )
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc


@router.get(
    "/{job_id}/evaluation-plans",
    response_model=list[JobEvaluationPlanRead],
)
async def list_evaluation_plan_history(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[JobEvaluationPlanRead]:
    try:
        plans = await job_evaluation_plan_service.list_plan_history(db, job_id)
        return [
            job_evaluation_plan_service.build_read_model(plan) for plan in plans
        ]
    except Exception as exc:
        raise _map_expected_error(exc) from exc
