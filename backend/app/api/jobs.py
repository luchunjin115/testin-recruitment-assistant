from __future__ import annotations

import re
from inspect import isawaitable
from collections.abc import Awaitable, Callable

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate, JobRead, JobStatus, JobUpdate
from app.services.job_service import (
    InvalidJobStatusTransitionError,
    JobHasReferencesError,
    JobMustBeClosedBeforeDeleteError,
    JobOpenValidationError,
    job_service,
)
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from app.services.screening_service import screening_service


router = APIRouter(prefix="/jobs", tags=["jobs"])

JOB_NOT_FOUND = {"code": "JOB_NOT_FOUND", "message": "岗位不存在"}
JOB_OPERATION_FAILED = {
    "code": "JOB_OPERATION_FAILED",
    "message": "岗位操作失败，请稍后重试",
}
JOB_UPDATE_EMPTY = {
    "code": "JOB_UPDATE_EMPTY",
    "message": "岗位更新内容不能为空",
}
_JOB_UPDATE_PATH = re.compile(r"^(?:/api/v2)?/jobs/-?\d+/?$")
_StatusAction = Callable[[AsyncSession, int], Awaitable[Job | None]]


def install_job_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _job_request_validation_handler)


async def _job_request_validation_handler(
    request: Request,
    exc: RequestValidationError,
):
    if (
        request.method == "PUT"
        and _JOB_UPDATE_PATH.fullmatch(request.url.path)
        and exc.body in ({}, None)
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": JOB_UPDATE_EMPTY},
        )
    return await request_validation_exception_handler(request, exc)


def _job_http_exception(
    status_code: int,
    code: str,
    message: str,
    **extra,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, **extra},
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=JOB_NOT_FOUND)


def _operation_failed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=JOB_OPERATION_FAILED,
    )


def _open_validation_failed(exc: JobOpenValidationError) -> HTTPException:
    return _job_http_exception(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "JOB_OPEN_VALIDATION_FAILED",
        "岗位信息不完整，暂时不能开放",
        fields=list(exc.fields),
    )


async def _generate_plan_after_job_commit(
    db: AsyncSession,
    job: Job,
) -> None:
    """Best-effort post-commit hook; plan failure never rolls back the Job."""
    if job.status != "open":
        return
    try:
        plan = await job_evaluation_plan_service.generate_for_job(db, job.id)
        await screening_service.after_plan_changed(
            db,
            job.id,
            plan_ready=plan.status == "ready" and plan.is_current,
        )
    except Exception:
        try:
            rollback_result = db.rollback()
            if isawaitable(rollback_result):
                await rollback_result
        except Exception:
            pass


async def _run_status_action(
    action: _StatusAction,
    db: AsyncSession,
    job_id: int,
) -> Job:
    try:
        job = await action(db, job_id)
    except JobOpenValidationError as exc:
        raise _open_validation_failed(exc) from exc
    except InvalidJobStatusTransitionError as exc:
        raise _job_http_exception(
            status.HTTP_409_CONFLICT,
            "INVALID_JOB_STATUS_TRANSITION",
            "岗位当前状态不允许执行该操作",
        ) from exc
    except Exception as exc:
        raise _operation_failed() from exc
    if job is None:
        raise _not_found()
    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(data: JobCreate, db: AsyncSession = Depends(get_db)) -> Job:
    try:
        job = await job_service.create_job(db, data)
    except JobOpenValidationError as exc:
        raise _open_validation_failed(exc) from exc
    except Exception as exc:
        raise _operation_failed() from exc
    await _generate_plan_after_job_commit(db, job)
    return job


@router.get("", response_model=list[JobRead])
async def list_jobs(
    job_status: JobStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[Job]:
    try:
        return await job_service.list_jobs(db, status=job_status)
    except Exception as exc:
        raise _operation_failed() from exc


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Job:
    try:
        job = await job_service.get_job(db, job_id)
    except Exception as exc:
        raise _operation_failed() from exc
    if job is None:
        raise _not_found()
    return job


@router.put("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: int,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
) -> Job:
    try:
        job = await job_service.update_job(db, job_id, data)
    except JobOpenValidationError as exc:
        raise _open_validation_failed(exc) from exc
    except Exception as exc:
        raise _operation_failed() from exc
    if job is None:
        raise _not_found()
    await _generate_plan_after_job_commit(db, job)
    return job


@router.post("/{job_id}/open", response_model=JobRead)
async def open_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Job:
    job = await _run_status_action(job_service.open_job, db, job_id)
    await _generate_plan_after_job_commit(db, job)
    return job


@router.post("/{job_id}/close", response_model=JobRead)
async def close_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Job:
    job = await _run_status_action(job_service.close_job, db, job_id)
    try:
        await screening_service.after_job_closed(db, job.id)
    except Exception:
        pass
    return job


@router.post("/{job_id}/reopen", response_model=JobRead)
async def reopen_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Job:
    job = await _run_status_action(job_service.reopen_job, db, job_id)
    await _generate_plan_after_job_commit(db, job)
    try:
        await screening_service.after_job_reopened(db, job.id)
    except Exception:
        pass
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    try:
        deleted = await job_service.delete_job(db, job_id)
    except JobMustBeClosedBeforeDeleteError as exc:
        raise _job_http_exception(
            status.HTTP_409_CONFLICT,
            "JOB_MUST_BE_CLOSED_BEFORE_DELETE",
            "开放岗位必须先关闭才能删除",
        ) from exc
    except JobHasReferencesError as exc:
        raise _job_http_exception(
            status.HTTP_409_CONFLICT,
            "JOB_HAS_REFERENCES",
            "岗位已有历史业务数据，不能删除",
            references=exc.references.as_dict(),
        ) from exc
    except Exception as exc:
        raise _operation_failed() from exc
    if not deleted:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
