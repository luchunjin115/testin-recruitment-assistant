from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.public_application import ApplicationProcessingStatus
from app.schemas.public_application_workbench import (
    HRActionConfirmation,
    PublicApplicationPool,
    PublicApplicationProcessingRunSummary,
    PublicApplicationWorkbenchDetail,
    PublicApplicationWorkbenchSummary,
)
from app.services.application_processing_service import (
    ApplicationProcessingActiveRunError,
    ApplicationProcessingPauseNotRecoveredError,
    ApplicationProcessingRetryNotAllowedError,
    ApplicationProcessingRunNotFoundError,
)
from app.services.public_application_workbench_service import (
    PublicApplicationIdentityReviewNotRequiredError,
    PublicApplicationWorkbenchSubmissionNotFoundError,
    public_application_workbench_service,
)


router = APIRouter(
    prefix="/public-application-submissions",
    tags=["public-application-workbench"],
)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            PublicApplicationWorkbenchSubmissionNotFoundError,
            ApplicationProcessingRunNotFoundError,
        ),
    ):
        return _error(
            status.HTTP_404_NOT_FOUND,
            "PUBLIC_APPLICATION_SUBMISSION_NOT_FOUND",
            "公开投递不存在",
        )
    if isinstance(exc, PublicApplicationIdentityReviewNotRequiredError):
        return _error(
            status.HTTP_409_CONFLICT,
            "PUBLIC_APPLICATION_IDENTITY_REVIEW_NOT_REQUIRED",
            "当前投递不需要身份核对",
        )
    if isinstance(exc, ApplicationProcessingActiveRunError):
        return _error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_PROCESSING_ACTIVE_RUN",
            "当前已有正在处理的任务，请等待完成后再操作",
        )
    if isinstance(exc, ApplicationProcessingPauseNotRecoveredError):
        return _error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_PROCESSING_PAUSE_NOT_RECOVERED",
            "暂停原因尚未解除，请先完成页面提示的处理",
        )
    if isinstance(exc, ApplicationProcessingRetryNotAllowedError):
        return _error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_PROCESSING_RETRY_NOT_ALLOWED",
            "当前任务不能人工重试",
        )
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "PUBLIC_APPLICATION_WORKBENCH_OPERATION_FAILED",
        "公开投递工作台操作失败，请稍后重试",
    )


def _require_confirmation(data: HRActionConfirmation) -> None:
    if not data.confirmed:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "HR_ACTION_CONFIRMATION_REQUIRED",
            "该操作需要 HR 二次确认",
        )


@router.get("", response_model=list[PublicApplicationWorkbenchSummary])
async def list_public_application_submissions(
    pool: PublicApplicationPool = PublicApplicationPool.ALL,
    job_id: int | None = Query(default=None, ge=1),
    processing_status: ApplicationProcessingStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PublicApplicationWorkbenchSummary]:
    try:
        return await public_application_workbench_service.list_submissions(
            db,
            pool=pool,
            job_id=job_id,
            processing_status=processing_status,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get(
    "/{submission_id}",
    response_model=PublicApplicationWorkbenchDetail,
)
async def get_public_application_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
) -> PublicApplicationWorkbenchDetail:
    try:
        return await public_application_workbench_service.get_submission(
            db,
            submission_id,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{submission_id}/identity-review",
    response_model=PublicApplicationWorkbenchDetail,
)
async def mark_public_application_identity_reviewed(
    submission_id: int,
    data: HRActionConfirmation,
    db: AsyncSession = Depends(get_db),
) -> PublicApplicationWorkbenchDetail:
    _require_confirmation(data)
    try:
        return await public_application_workbench_service.mark_identity_reviewed(
            db,
            submission_id,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{submission_id}/retry",
    response_model=PublicApplicationProcessingRunSummary,
    status_code=status.HTTP_201_CREATED,
)
async def retry_public_application_processing(
    submission_id: int,
    data: HRActionConfirmation,
    db: AsyncSession = Depends(get_db),
) -> PublicApplicationProcessingRunSummary:
    _require_confirmation(data)
    try:
        return await public_application_workbench_service.create_manual_retry(
            db,
            submission_id,
        )
    except Exception as exc:
        raise _map_error(exc) from exc
