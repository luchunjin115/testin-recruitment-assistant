from __future__ import annotations

import re

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.interview import (
    InterviewCancelRequest,
    InterviewDecision,
    InterviewFeedbackSubmitRequest,
    InterviewFeedbackUpdateRequest,
    InterviewNoShowRequest,
    InterviewRecordListItem,
    InterviewRecordRead,
    InterviewScheduleCreate,
    InterviewScheduleUpdate,
)
from app.schemas.recruitment_timeline import RecruitmentTimelineItem
from app.services.interview_service import (
    ApplicationNotFoundError,
    ApplicationNotReadyForInterviewError,
    ApplicationPipelineEndedError,
    HRActionConfirmationRequiredError,
    HRActionReasonRequiredError,
    InterviewNotFoundError,
    InterviewRoundConflictError,
    InterviewTransitionInvalidError,
    InterviewVersionConflictError,
    interview_service,
)
from app.services.recruitment_timeline_service import recruitment_timeline_service


router = APIRouter(tags=["interviews"])
_INTERVIEW_ACTION_PATH = re.compile(
    r"^(?:/api/v2)?/interviews/[^/]+/(?:cancel|no-show|feedback)/?$"
)


def install_interview_exception_handlers(app: FastAPI) -> None:
    previous_handler = app.exception_handlers.get(
        RequestValidationError,
        request_validation_exception_handler,
    )

    async def combined_handler(request: Request, exc: RequestValidationError):
        response = _interview_validation_response(request, exc)
        if response is not None:
            return response
        return await previous_handler(request, exc)

    app.add_exception_handler(RequestValidationError, combined_handler)


def _interview_validation_response(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse | None:
    if not _INTERVIEW_ACTION_PATH.fullmatch(request.url.path):
        return None
    invalid_fields = {
        str(error["loc"][-1]) for error in exc.errors() if error.get("loc")
    }
    if "confirmed" in invalid_fields:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "HR_ACTION_CONFIRMATION_REQUIRED",
            "该操作必须明确二次确认",
        )
    if invalid_fields.intersection(
        {"reason_code", "reason_detail", "correction_reason"}
    ):
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "HR_ACTION_REASON_REQUIRED",
            "必须提供合法的受控原因和必要说明",
        )
    return None


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _map_interview_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ApplicationNotFoundError):
        return _http_error(404, "APPLICATION_NOT_FOUND", "Application 不存在")
    if isinstance(exc, InterviewNotFoundError):
        return _http_error(404, "INTERVIEW_NOT_FOUND", "面试记录不存在")
    if isinstance(exc, ApplicationNotReadyForInterviewError):
        return _http_error(
            409,
            "APPLICATION_NOT_READY_FOR_INTERVIEW",
            "当前 Application 尚未达到开始面试的条件",
        )
    if isinstance(exc, ApplicationPipelineEndedError):
        return _http_error(
            409,
            "APPLICATION_PIPELINE_ENDED",
            "Application 流程已经结束或作废",
        )
    if isinstance(exc, InterviewRoundConflictError):
        return _http_error(
            409,
            "INTERVIEW_ROUND_CONFLICT",
            "面试轮次重复或已有待进行面试",
        )
    if isinstance(exc, InterviewTransitionInvalidError):
        return _http_error(
            409,
            "INTERVIEW_TRANSITION_INVALID",
            "当前面试状态不允许执行该操作",
        )
    if isinstance(exc, InterviewVersionConflictError):
        return _http_error(
            409,
            "INTERVIEW_VERSION_CONFLICT",
            "面试记录已被其他操作修改，请刷新后重试",
        )
    if isinstance(exc, HRActionConfirmationRequiredError):
        return _http_error(
            422,
            "HR_ACTION_CONFIRMATION_REQUIRED",
            "该操作必须明确二次确认",
        )
    if isinstance(exc, HRActionReasonRequiredError):
        return _http_error(
            422,
            "HR_ACTION_REASON_REQUIRED",
            "必须提供合法的受控原因和必要说明",
        )
    return _http_error(
        500,
        "RECRUITMENT_PIPELINE_OPERATION_FAILED",
        "招聘流程操作失败，已回滚本次修改",
    )


def _require_confirmation(confirmed: bool) -> None:
    if not confirmed:
        raise _http_error(
            422,
            "HR_ACTION_CONFIRMATION_REQUIRED",
            "该操作必须明确二次确认",
        )


@router.get(
    "/applications/{application_id}/interviews",
    response_model=list[InterviewRecordListItem],
)
async def list_interviews(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[InterviewRecordListItem]:
    try:
        return await interview_service.list_interviews(db, application_id)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.post(
    "/applications/{application_id}/interviews",
    response_model=InterviewRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_interview(
    application_id: int,
    data: InterviewScheduleCreate,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    try:
        return await interview_service.schedule_interview(db, application_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.put(
    "/interviews/{interview_id}/schedule",
    response_model=InterviewRecordRead,
)
async def reschedule_interview(
    interview_id: int,
    data: InterviewScheduleUpdate,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    try:
        return await interview_service.reschedule_interview(db, interview_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.post(
    "/interviews/{interview_id}/cancel",
    response_model=InterviewRecordRead,
)
async def cancel_interview(
    interview_id: int,
    data: InterviewCancelRequest,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await interview_service.cancel_interview(db, interview_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.post(
    "/interviews/{interview_id}/no-show",
    response_model=InterviewRecordRead,
)
async def mark_interview_no_show(
    interview_id: int,
    data: InterviewNoShowRequest,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await interview_service.mark_no_show(db, interview_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.post(
    "/interviews/{interview_id}/feedback",
    response_model=InterviewRecordRead,
)
async def submit_interview_feedback(
    interview_id: int,
    data: InterviewFeedbackSubmitRequest,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    if data.decision in {
        InterviewDecision.REJECTED,
        InterviewDecision.CANDIDATE_WITHDREW,
    }:
        _require_confirmation(data.confirmed)
        if data.reason_detail is None:
            raise _http_error(
                422,
                "HR_ACTION_REASON_REQUIRED",
                "结束招聘流程必须填写原因",
            )
    try:
        return await interview_service.submit_feedback(db, interview_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.put(
    "/interviews/{interview_id}/feedback",
    response_model=InterviewRecordRead,
)
async def update_interview_feedback(
    interview_id: int,
    data: InterviewFeedbackUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await interview_service.update_feedback(db, interview_id, data)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


@router.get(
    "/applications/{application_id}/timeline",
    response_model=list[RecruitmentTimelineItem],
)
async def list_recruitment_timeline(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[RecruitmentTimelineItem]:
    try:
        return await recruitment_timeline_service.list_timeline(db, application_id)
    except Exception as exc:
        raise _map_interview_error(exc) from exc


__all__ = [
    "install_interview_exception_handlers",
    "router",
]
