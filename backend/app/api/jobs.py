from __future__ import annotations

import re
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

from app.adapters.screening_rubric_generation import (
    RubricGenerationAdapterError,
)
from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate, JobRead, JobStatus, JobUpdate
from app.schemas.screening_rubric import (
    JobScreeningRubricRead,
    ScreeningRubricAbandonRequest,
    ScreeningRubricDraftUpdateRequest,
    ScreeningRubricGenerateRequest,
    ScreeningRubricItemAssistRequest,
    ScreeningRubricItemAssistResponse,
    ScreeningRubricPublishRequest,
    ScreeningRubricReconfirmRequest,
    ScreeningRubricShareOptimizationRequest,
    ScreeningRubricShareOptimizationResponse,
    ScreeningRubricTemplateDraftRequest,
)
from app.schemas.screening_batch import (
    ScreeningBatchRunRequest,
    ScreeningBatchRunResponse,
)
from app.services.job_service import (
    InvalidJobStatusTransitionError,
    JobHasReferencesError,
    JobMustBeClosedBeforeDeleteError,
    JobOpenValidationError,
    job_service,
)
from app.services.screening_rubric_service import (
    CurrentScreeningRubricNotFoundError,
    ScreeningRubricDraftAlreadyExistsError,
    ScreeningRubricDraftNotFoundError,
    ScreeningRubricGenerationDisabledError,
    ScreeningRubricGenerationInvalidOutputError,
    ScreeningRubricJobNotFoundError,
    ScreeningRubricPublishValidationError,
    ScreeningRubricStaleError,
    screening_rubric_service,
)
from app.services.screening_batch_service import (
    ScreeningBatchApplicationsNotFoundError,
    ScreeningBatchJobMismatchError,
    ScreeningBatchJobNotFoundError,
    ScreeningBatchJobNotOpenError,
    screening_batch_service,
)


router = APIRouter(prefix="/jobs", tags=["jobs"])

JOB_NOT_FOUND = {
    "code": "JOB_NOT_FOUND",
    "message": "岗位不存在",
}
JOB_OPERATION_FAILED = {
    "code": "JOB_OPERATION_FAILED",
    "message": "岗位操作失败，请稍后重试",
}
JOB_UPDATE_EMPTY = {
    "code": "JOB_UPDATE_EMPTY",
    "message": "岗位更新内容不能为空",
}
_JOB_UPDATE_PATH = re.compile(r"^(?:/api/v2)?/jobs/-?\d+/?$")
_RUBRIC_UPDATE_PATH = re.compile(
    r"^(?:/api/v2)?/jobs/-?\d+/screening-rubric/"
    r"(?:draft(?:/from-template|/assist-item|/optimize-shares|/publish|/abandon)?|generate|reconfirm)/?$"
)
_SCREENING_BATCH_PATH = re.compile(
    r"^(?:/api/v2)?/jobs/-?\d+/screenings/batch/?$"
)
_StatusAction = Callable[[AsyncSession, int], Awaitable[Job | None]]


def install_job_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _job_request_validation_handler)


async def _job_request_validation_handler(
    request: Request,
    exc: RequestValidationError,
):
    if request.method == "POST" and _SCREENING_BATCH_PATH.fullmatch(request.url.path):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "code": "SCREENING_BATCH_INVALID",
                    "message": "批量评分请求不合法，必须选择同岗位的 1—5 个 Application",
                }
            },
        )
    if (
        request.method == "PUT"
        and _JOB_UPDATE_PATH.fullmatch(request.url.path)
        and exc.body in ({}, None)
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": JOB_UPDATE_EMPTY},
        )
    if request.method in {"POST", "PUT"} and _RUBRIC_UPDATE_PATH.fullmatch(
        request.url.path
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "code": "RUBRIC_DRAFT_INVALID",
                    "message": "Rubric 草稿或变更请求不合法",
                }
            },
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
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=JOB_NOT_FOUND,
    )


def _operation_failed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=JOB_OPERATION_FAILED,
    )


def _screening_batch_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ScreeningBatchJobNotFoundError):
        return _not_found()
    if isinstance(exc, ScreeningBatchJobNotOpenError):
        return _job_http_exception(
            status.HTTP_409_CONFLICT,
            "JOB_NOT_OPEN_FOR_SCREENING",
            "岗位当前不是 open 状态，不能启动批量评分",
        )
    if isinstance(exc, ScreeningBatchApplicationsNotFoundError):
        return _job_http_exception(
            status.HTTP_404_NOT_FOUND,
            "BATCH_APPLICATIONS_NOT_FOUND",
            "批次中存在找不到的 Application",
            application_ids=list(exc.application_ids),
        )
    if isinstance(exc, ScreeningBatchJobMismatchError):
        return _job_http_exception(
            status.HTTP_409_CONFLICT,
            "BATCH_APPLICATION_JOB_MISMATCH",
            "批次中的 Application 不属于指定岗位",
            application_ids=list(exc.application_ids),
        )
    return _job_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "SCREENING_BATCH_FAILED",
        "批量评分启动失败，没有影响已独立保存的其他结果",
    )


def _open_validation_failed(exc: JobOpenValidationError) -> HTTPException:
    return _job_http_exception(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "JOB_OPEN_VALIDATION_FAILED",
        "岗位信息不完整，暂时不能开放",
        fields=list(exc.fields),
    )


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
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> Job:
    try:
        return await job_service.create_job(db, data)
    except JobOpenValidationError as exc:
        raise _open_validation_failed(exc) from exc
    except Exception as exc:
        raise _operation_failed() from exc


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
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Job:
    try:
        job = await job_service.get_job(db, job_id)
    except Exception as exc:
        raise _operation_failed() from exc
    if job is None:
        raise _not_found()
    return job


@router.post(
    "/{job_id}/screenings/batch",
    response_model=ScreeningBatchRunResponse,
)
async def run_screening_batch(
    job_id: int,
    data: ScreeningBatchRunRequest,
    db: AsyncSession = Depends(get_db),
) -> ScreeningBatchRunResponse:
    try:
        return await screening_batch_service.run(db, job_id, data)
    except Exception as exc:
        raise _screening_batch_error(exc) from exc


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
    return job


@router.get(
    "/{job_id}/screening-rubric",
    response_model=JobScreeningRubricRead,
)
async def get_screening_rubric(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.get_current_rubric(db, job_id)
    except ScreeningRubricJobNotFoundError as exc:
        raise _not_found() from exc
    except CurrentScreeningRubricNotFoundError as exc:
        raise _job_http_exception(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "RUBRIC_OPERATION_FAILED",
            "岗位评分规则暂时不可用",
        ) from exc
    except Exception as exc:
        raise _job_http_exception(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "RUBRIC_OPERATION_FAILED",
            "岗位评分规则读取失败",
        ) from exc


def _rubric_expected_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ScreeningRubricJobNotFoundError):
        return _not_found()
    if isinstance(exc, ScreeningRubricDraftNotFoundError):
        return _job_http_exception(
            status.HTTP_404_NOT_FOUND,
            "RUBRIC_DRAFT_NOT_FOUND",
            "岗位没有正在编辑的评分标准草稿",
        )
    if isinstance(exc, ScreeningRubricDraftAlreadyExistsError):
        return _job_http_exception(
            status.HTTP_409_CONFLICT,
            "RUBRIC_DRAFT_ALREADY_EXISTS",
            "岗位已有正在编辑的评分标准草稿",
        )
    if isinstance(exc, ScreeningRubricStaleError):
        return _job_http_exception(
            status.HTTP_409_CONFLICT,
            "RUBRIC_DRAFT_STALE",
            "岗位内容已变化，请刷新后重新处理评分标准",
        )
    if isinstance(exc, ScreeningRubricGenerationInvalidOutputError):
        return _job_http_exception(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RUBRIC_CRITERIA_INVALID",
            "AI 返回的评分标准不符合发布和公平性要求",
        )
    if isinstance(
        exc,
        (RubricGenerationAdapterError, ScreeningRubricGenerationDisabledError),
    ):
        return _job_http_exception(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RUBRIC_GENERATION_MODEL_UNAVAILABLE",
            "评分标准生成服务暂时不可用，当前正式版本未受影响",
        )
    if isinstance(exc, ScreeningRubricPublishValidationError):
        return _job_http_exception(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RUBRIC_PUBLISH_INVALID",
            "评分标准草稿尚未达到发布条件",
        )
    if isinstance(exc, CurrentScreeningRubricNotFoundError):
        return _job_http_exception(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "RUBRIC_OPERATION_FAILED",
            "岗位评分规则暂时不可用",
        )
    return _job_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "RUBRIC_OPERATION_FAILED",
        "岗位评分规则操作失败，已回滚本次操作",
    )


@router.get(
    "/{job_id}/screening-rubric/draft",
    response_model=JobScreeningRubricRead,
)
async def get_screening_rubric_draft(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.get_draft_rubric(db, job_id)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/draft/from-template",
    response_model=JobScreeningRubricRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_screening_rubric_template_draft(
    job_id: int,
    data: ScreeningRubricTemplateDraftRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.create_template_draft(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/generate",
    response_model=JobScreeningRubricRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_screening_rubric_draft(
    job_id: int,
    data: ScreeningRubricGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.generate_draft(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/draft/assist-item",
    response_model=ScreeningRubricItemAssistResponse,
)
async def assist_screening_rubric_item(
    job_id: int,
    data: ScreeningRubricItemAssistRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.assist_manual_item(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/draft/optimize-shares",
    response_model=ScreeningRubricShareOptimizationResponse,
)
async def optimize_screening_rubric_shares(
    job_id: int,
    data: ScreeningRubricShareOptimizationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.optimize_draft_shares(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.put(
    "/{job_id}/screening-rubric/draft",
    response_model=JobScreeningRubricRead,
)
async def update_screening_rubric_draft(
    job_id: int,
    data: ScreeningRubricDraftUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.update_draft(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/draft/publish",
    response_model=JobScreeningRubricRead,
)
async def publish_screening_rubric_draft(
    job_id: int,
    data: ScreeningRubricPublishRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.publish_draft(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/draft/abandon",
    response_model=JobScreeningRubricRead,
)
async def abandon_screening_rubric_draft(
    job_id: int,
    data: ScreeningRubricAbandonRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.abandon_draft(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post(
    "/{job_id}/screening-rubric/reconfirm",
    response_model=JobScreeningRubricRead,
)
async def reconfirm_screening_rubric(
    job_id: int,
    data: ScreeningRubricReconfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await screening_rubric_service.reconfirm_current(db, job_id, data)
    except Exception as exc:
        raise _rubric_expected_exception(exc) from exc


@router.post("/{job_id}/open", response_model=JobRead)
async def open_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await _run_status_action(job_service.open_job, db, job_id)


@router.post("/{job_id}/close", response_model=JobRead)
async def close_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await _run_status_action(job_service.close_job, db, job_id)


@router.post("/{job_id}/reopen", response_model=JobRead)
async def reopen_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await _run_status_action(job_service.reopen_job, db, job_id)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
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
