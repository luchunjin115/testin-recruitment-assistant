from __future__ import annotations

import re

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.application import Application
from app.schemas.application import ApplicationRead
from app.schemas.screening import (
    ApplicationResumeSwitchRequest,
    ScreeningBatchFailureRead,
    ScreeningBatchReassessmentRead,
    ScreeningBatchReassessmentRequest,
    ScreeningReassessmentRequest,
    ScreeningReportRead,
    ScreeningStateRead,
    ScreeningTriggerRead,
    ScreeningRunTriggerType,
)
from app.services.screening_service import (
    ScreeningApplicationNotFoundError,
    ScreeningBatchJobMismatchError,
    ScreeningBatchLimitError,
    ScreeningJobClosedError,
    ScreeningResumeNotFoundError,
    ScreeningResumeOwnershipError,
    ScreeningReassessmentConfirmationRequiredError,
    ScreeningServiceError,
    ScreeningTriggerResult,
    screening_service,
)


router = APIRouter(tags=["screening"])
_BATCH_REASSESSMENT_PATH = re.compile(
    r"^(?:/api/v2)?/jobs/-?\d+/screening/re-evaluate-batch/?$"
)
_SINGLE_REASSESSMENT_PATH = re.compile(
    r"^(?:/api/v2)?/applications/-?\d+/screening/re-evaluate/?$"
)


def install_screening_exception_handlers(app: FastAPI) -> None:
    previous_handler = app.exception_handlers.get(
        RequestValidationError,
        request_validation_exception_handler,
    )

    async def combined_handler(request: Request, exc: RequestValidationError):
        invalid_fields = {
            str(error["loc"][-1]) for error in exc.errors() if error.get("loc")
        }
        if (
            request.method == "POST"
            and (
                _BATCH_REASSESSMENT_PATH.fullmatch(request.url.path)
                or _SINGLE_REASSESSMENT_PATH.fullmatch(request.url.path)
            )
            and "confirmed" in invalid_fields
        ):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": {
                        "code": "SCREENING_REASSESSMENT_CONFIRMATION_REQUIRED",
                        "message": "重新评估必须由 HR 二次确认",
                    }
                },
            )
        if (
            request.method == "POST"
            and _BATCH_REASSESSMENT_PATH.fullmatch(request.url.path)
        ):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": {
                        "code": "SCREENING_BATCH_SIZE_INVALID",
                        "message": "一次只能重新评估 1—5 个不同 Application",
                    }
                },
            )
        return await previous_handler(request, exc)

    app.add_exception_handler(RequestValidationError, combined_handler)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ScreeningApplicationNotFoundError, ScreeningResumeNotFoundError)):
        return _error(status.HTTP_404_NOT_FOUND, exc.code, "Application 或 Resume 不存在")
    if isinstance(exc, ScreeningJobClosedError):
        return _error(status.HTTP_409_CONFLICT, exc.code, "岗位关闭时不能开始初筛或重新评估")
    if isinstance(exc, ScreeningResumeOwnershipError):
        return _error(status.HTTP_409_CONFLICT, exc.code, "Resume 不属于当前 Candidate 或岗位")
    if isinstance(exc, ScreeningBatchLimitError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            exc.code,
            "一次只能重新评估 1—5 个不同 Application",
        )
    if isinstance(exc, ScreeningReassessmentConfirmationRequiredError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            exc.code,
            "重新评估必须由 HR 二次确认",
        )
    if isinstance(exc, ScreeningBatchJobMismatchError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            exc.code,
            "批量重新评估只能包含同一岗位下存在的 Application",
        )
    if isinstance(exc, ScreeningServiceError):
        return _error(status.HTTP_409_CONFLICT, exc.code, "当前状态不允许执行该操作")
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "SCREENING_OPERATION_FAILED",
        "AI 初筛操作失败，请稍后重试",
    )


def _trigger_response(result: ScreeningTriggerResult) -> ScreeningTriggerRead:
    return ScreeningTriggerRead(
        application_id=result.application_id,
        run=result.run,
        report=result.report,
        reused_report=result.reused_report,
        reused_run=result.reused_run,
    )


@router.get(
    "/applications/{application_id}/screening",
    response_model=ScreeningStateRead,
)
async def get_application_screening(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScreeningStateRead:
    try:
        result = await screening_service.get_state(db, application_id)
        return ScreeningStateRead(
            application_id=result.application_id,
            report=result.report,
            latest_run=result.latest_run,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get(
    "/applications/{application_id}/screening/reports",
    response_model=list[ScreeningReportRead],
)
async def list_application_screening_reports(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ScreeningReportRead]:
    try:
        return await screening_service.list_reports(db, application_id)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/applications/{application_id}/screening",
    response_model=ScreeningTriggerRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_application_screening(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScreeningTriggerRead:
    try:
        result = await screening_service.trigger(db, application_id)
        return _trigger_response(result)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/applications/{application_id}/screening/re-evaluate",
    response_model=ScreeningTriggerRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reassess_application_screening(
    application_id: int,
    data: ScreeningReassessmentRequest,
    db: AsyncSession = Depends(get_db),
) -> ScreeningTriggerRead:
    try:
        result = await screening_service.trigger(
            db,
            application_id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            confirmed=data.confirmed,
        )
        return _trigger_response(result)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/jobs/{job_id}/screening/re-evaluate-batch",
    response_model=ScreeningBatchReassessmentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reassess_job_applications(
    job_id: int,
    data: ScreeningBatchReassessmentRequest,
    db: AsyncSession = Depends(get_db),
) -> ScreeningBatchReassessmentRead:
    try:
        results = await screening_service.trigger_batch_reassessment(
            db,
            job_id,
            list(data.application_ids),
            confirmed=data.confirmed,
        )
        return ScreeningBatchReassessmentRead(
            job_id=job_id,
            total_count=results.total_count,
            reused_count=results.reused_count,
            queued_count=results.queued_count,
            failed_count=len(results.failures),
            results=[_trigger_response(result) for result in results.results],
            failures=[
                ScreeningBatchFailureRead(
                    application_id=item.application_id,
                    error_code=item.error_code,
                    error_message=item.error_message,
                    retryable=item.retryable,
                )
                for item in results.failures
            ],
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.put(
    "/applications/{application_id}/current-resume",
    response_model=ApplicationRead,
)
async def switch_application_resume(
    application_id: int,
    data: ApplicationResumeSwitchRequest,
    db: AsyncSession = Depends(get_db),
) -> Application:
    """Internal development boundary; login/RBAC is not implemented yet."""
    try:
        return await screening_service.switch_current_resume(
            db,
            application_id,
            data.resume_id,
        )
    except Exception as exc:
        raise _map_error(exc) from exc
