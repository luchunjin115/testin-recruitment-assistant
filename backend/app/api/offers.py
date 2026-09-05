from __future__ import annotations

import re

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.application import ApplicationRead
from app.schemas.offer import (
    CandidateWithdrawRequest,
    CompanyCancelRequest,
    ConfirmAdmissionRequest,
    ConfirmHireRequest,
    OfferAcceptRequest,
    OfferDeclineRequest,
    OfferDraftCreateRequest,
    OfferExpireRequest,
    OfferRecordRead,
    OfferSendRequest,
    OfferUpdateRequest,
    OfferWithdrawRequest,
    Stage9ReopenRequest,
)
from app.services.interview_service import (
    ApplicationNotFoundError,
    ApplicationPipelineEndedError,
    HRActionConfirmationRequiredError,
    HRActionReasonRequiredError,
    InterviewVersionConflictError,
)
from app.services.offer_service import (
    ApplicationReopenInvalidError,
    OfferActiveConflictError,
    OfferCompensationInvalidError,
    OfferNotFoundError,
    OfferTransitionInvalidError,
    OfferVersionConflictError,
    offer_service,
)


router = APIRouter(tags=["offers"])
_OFFER_REQUEST_PATH = re.compile(
    r"^(?:/api/v2)?/(?:"
    r"applications/[^/]+/(?:offers|confirm-admission|confirm-hire|withdraw|cancel-process|reopen-stage9)"
    r"|offers/[^/]+(?:/(?:send|accept|decline|withdraw|expire))?"
    r")/?$"
)
_COMPENSATION_FIELDS = {
    "position_title",
    "currency",
    "salary_period",
    "base_salary_amount",
    "salary_months",
    "bonus_note",
    "benefits_note",
    "valid_until",
    "expected_start_date",
    "note",
}


def install_offer_exception_handlers(app: FastAPI) -> None:
    previous_handler = app.exception_handlers.get(
        RequestValidationError,
        request_validation_exception_handler,
    )

    async def combined_handler(request: Request, exc: RequestValidationError):
        response = _offer_validation_response(request, exc)
        if response is not None:
            return response
        return await previous_handler(request, exc)

    app.add_exception_handler(RequestValidationError, combined_handler)


def _offer_validation_response(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse | None:
    if not _OFFER_REQUEST_PATH.fullmatch(request.url.path):
        return None
    invalid_fields = {
        str(error["loc"][-1]) for error in exc.errors() if error.get("loc")
    }
    model_level_compensation_error = any(
        isinstance(error.get("input"), dict)
        and bool(set(error["input"]).intersection(_COMPENSATION_FIELDS))
        for error in exc.errors()
    )
    if "confirmed" in invalid_fields:
        return _error_response(
            422,
            "HR_ACTION_CONFIRMATION_REQUIRED",
            "该操作必须明确二次确认",
        )
    if invalid_fields.intersection(
        {"reason_code", "reason_detail", "correction_reason"}
    ):
        return _error_response(
            422,
            "HR_ACTION_REASON_REQUIRED",
            "必须提供合法的受控原因和必要说明",
        )
    if invalid_fields.intersection(_COMPENSATION_FIELDS) or model_level_compensation_error:
        return _error_response(
            422,
            "OFFER_COMPENSATION_INVALID",
            "Offer 薪资、日期或说明字段无效",
        )
    return _error_response(422, "OFFER_REQUEST_INVALID", "Offer 请求字段无效")


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


def _map_offer_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ApplicationNotFoundError):
        return _http_error(404, "APPLICATION_NOT_FOUND", "Application 不存在")
    if isinstance(exc, OfferNotFoundError):
        return _http_error(404, "OFFER_NOT_FOUND", "Offer 不存在")
    if isinstance(exc, ApplicationPipelineEndedError):
        return _http_error(
            409,
            "APPLICATION_PIPELINE_ENDED",
            "Application 流程已经结束或作废",
        )
    if isinstance(exc, OfferActiveConflictError):
        return _http_error(
            409,
            "OFFER_ACTIVE_CONFLICT",
            "该 Application 已经存在活动 Offer",
        )
    if isinstance(exc, OfferTransitionInvalidError):
        return _http_error(
            409,
            "OFFER_TRANSITION_INVALID",
            "当前 Offer 或 Application 状态不允许执行该操作",
        )
    if isinstance(exc, OfferVersionConflictError):
        return _http_error(
            409,
            "OFFER_VERSION_CONFLICT",
            "Offer 已被其他操作修改，请刷新后重试",
        )
    if isinstance(exc, InterviewVersionConflictError):
        return _http_error(
            409,
            "INTERVIEW_VERSION_CONFLICT",
            "面试记录已被其他操作修改，请刷新后重试",
        )
    if isinstance(exc, ApplicationReopenInvalidError):
        return _http_error(
            409,
            "APPLICATION_REOPEN_INVALID",
            "当前结果或支撑记录不允许重新打开",
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
    if isinstance(exc, OfferCompensationInvalidError):
        return _http_error(
            422,
            "OFFER_COMPENSATION_INVALID",
            "Offer 薪资、日期或说明字段无效",
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
    "/applications/{application_id}/offers",
    response_model=list[OfferRecordRead],
)
async def list_offers(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[OfferRecordRead]:
    try:
        return await offer_service.list_offers(db, application_id)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/offers",
    response_model=OfferRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_offer(
    application_id: int,
    data: OfferDraftCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    try:
        return await offer_service.create_offer(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.put("/offers/{offer_id}", response_model=OfferRecordRead)
async def update_offer(
    offer_id: int,
    data: OfferUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    try:
        return await offer_service.update_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post("/offers/{offer_id}/send", response_model=OfferRecordRead)
async def send_offer(
    offer_id: int,
    data: OfferSendRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.send_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post("/offers/{offer_id}/accept", response_model=OfferRecordRead)
async def accept_offer(
    offer_id: int,
    data: OfferAcceptRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.accept_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post("/offers/{offer_id}/decline", response_model=OfferRecordRead)
async def decline_offer(
    offer_id: int,
    data: OfferDeclineRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.decline_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post("/offers/{offer_id}/withdraw", response_model=OfferRecordRead)
async def withdraw_offer(
    offer_id: int,
    data: OfferWithdrawRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.withdraw_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post("/offers/{offer_id}/expire", response_model=OfferRecordRead)
async def expire_offer(
    offer_id: int,
    data: OfferExpireRequest,
    db: AsyncSession = Depends(get_db),
) -> OfferRecordRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.expire_offer(db, offer_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/confirm-admission",
    response_model=ApplicationRead,
)
async def confirm_admission(
    application_id: int,
    data: ConfirmAdmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.confirm_admission(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/confirm-hire",
    response_model=ApplicationRead,
)
async def confirm_hire(
    application_id: int,
    data: ConfirmHireRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.confirm_hire(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/withdraw",
    response_model=ApplicationRead,
)
async def withdraw_application(
    application_id: int,
    data: CandidateWithdrawRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.withdraw_application(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/cancel-process",
    response_model=ApplicationRead,
)
async def cancel_application_process(
    application_id: int,
    data: CompanyCancelRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.cancel_application(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


@router.post(
    "/applications/{application_id}/reopen-stage9",
    response_model=ApplicationRead,
)
async def reopen_stage9(
    application_id: int,
    data: Stage9ReopenRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    _require_confirmation(data.confirmed)
    try:
        return await offer_service.reopen_stage9(db, application_id, data)
    except Exception as exc:
        raise _map_offer_error(exc) from exc


__all__ = ["install_offer_exception_handlers", "router"]
