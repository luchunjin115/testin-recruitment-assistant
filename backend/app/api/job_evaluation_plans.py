from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.job_evaluation_plan import JobEvaluationPlanRead
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanConfigurationError,
    JobEvaluationPlanDisabledError,
    JobEvaluationPlanJobNotFoundError,
    JobEvaluationPlanJobNotOpenError,
    JobEvaluationPlanNotFoundError,
    JobEvaluationPlanNotRegenerableError,
    job_evaluation_plan_service,
)
from app.services.screening_service import screening_service


router = APIRouter(prefix="/jobs", tags=["job-evaluation-plans"])


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
        plan = await job_evaluation_plan_service.get_current_plan(db, job_id)
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
        plan = await job_evaluation_plan_service.generate_for_job(db, job_id)
        try:
            await screening_service.after_plan_changed(
                db,
                job_id,
                plan_ready=plan.status == "ready" and plan.is_current,
            )
        except Exception:
            pass
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
        plan = await job_evaluation_plan_service.regenerate_failed_plan(db, job_id)
        try:
            await screening_service.after_plan_changed(
                db,
                job_id,
                plan_ready=plan.status == "ready" and plan.is_current,
            )
        except Exception:
            pass
        return job_evaluation_plan_service.build_read_model(plan)
    except Exception as exc:
        raise _map_expected_error(exc) from exc
