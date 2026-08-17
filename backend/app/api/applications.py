from __future__ import annotations

import re

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.rebuilt.application import (
    ApplicationRead,
    ApplicationIntakeRequest,
    ApplicationIntakeResponse,
)
from app.schemas.rebuilt.stage_history import (
    BackupApplicationRequest,
    PassApplicationRequest,
    RejectApplicationRequest,
    ReverseDecisionRequest,
    StageHistoryRead,
    VoidApplicationRequest,
)
from app.services.rebuilt.application_decision_service import (
    ApplicationNotFoundError,
    InvalidApplicationTransitionError,
    application_decision_service,
)
from app.services.rebuilt.application_intake_service import (
    ApplicationCandidateNotFoundError,
    ApplicationContactIdentityConflictError,
    ApplicationIntakeResult,
    ApplicationJobNotOpenError,
    ApplicationResumeNotFoundError,
    ApplicationResumeOwnershipConflictError,
    application_intake_service,
)


router = APIRouter(prefix="/applications", tags=["applications"])
_APPLICATION_INTAKE_PATH = re.compile(r"^(?:/api/v2)?/applications/intake/?$")


def install_application_exception_handlers(app: FastAPI) -> None:
    previous_handler = app.exception_handlers.get(
        RequestValidationError,
        request_validation_exception_handler,
    )

    async def combined_handler(request: Request, exc: RequestValidationError):
        response = _application_validation_response(request, exc)
        if response is not None:
            return response
        return await previous_handler(request, exc)

    app.add_exception_handler(RequestValidationError, combined_handler)


def _application_validation_response(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse | None:
    if request.method == "POST" and _APPLICATION_INTAKE_PATH.fullmatch(request.url.path):
        invalid_fields = {
            str(error["loc"][-1])
            for error in exc.errors()
            if error.get("loc")
        }
        if invalid_fields.intersection({"phone", "email"}):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": {
                        "code": "APPLICATION_CONTACT_REQUIRED",
                        "message": "必须提供有效手机号和邮箱",
                    }
                },
            )
        if "current_resume_id" in invalid_fields:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": {
                        "code": "APPLICATION_RESUME_REQUIRED",
                        "message": "必须绑定当前简历",
                    }
                },
            )
    return None


def _application_http_exception(
    status_code: int,
    code: str,
    message: str,
    **extra,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, **extra},
    )


def _map_intake_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ApplicationCandidateNotFoundError):
        return _application_http_exception(
            status.HTTP_404_NOT_FOUND,
            "CANDIDATE_NOT_FOUND",
            "指定的 Candidate 不存在",
        )
    if isinstance(exc, ApplicationResumeNotFoundError):
        return _application_http_exception(
            status.HTTP_404_NOT_FOUND,
            "RESUME_NOT_FOUND",
            "当前简历不存在",
        )
    if isinstance(exc, ApplicationContactIdentityConflictError):
        return _application_http_exception(
            status.HTTP_409_CONFLICT,
            "CONTACT_IDENTITY_CONFLICT",
            "手机号和邮箱无法安全识别为同一个 Candidate，请人工核对",
            candidate_ids=list(exc.candidate_ids),
        )
    if isinstance(exc, ApplicationJobNotOpenError):
        return _application_http_exception(
            status.HTTP_409_CONFLICT,
            "JOB_NOT_OPEN_FOR_SCREENING",
            "岗位不存在或当前不是 open 状态",
        )
    if isinstance(exc, ApplicationResumeOwnershipConflictError):
        return _application_http_exception(
            status.HTTP_409_CONFLICT,
            "RESUME_OWNERSHIP_CONFLICT",
            "当前简历已绑定其他 Candidate",
        )
    return _application_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "APPLICATION_OPERATION_FAILED",
        "申请录入失败，已回滚本次操作",
    )


def _map_application_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ApplicationNotFoundError):
        return _application_http_exception(
            status.HTTP_404_NOT_FOUND,
            "APPLICATION_NOT_FOUND",
            "Application 不存在",
        )
    if isinstance(exc, InvalidApplicationTransitionError):
        return _application_http_exception(
            status.HTTP_409_CONFLICT,
            "INVALID_APPLICATION_TRANSITION",
            "当前 Application 状态不允许执行该操作",
        )
    return _application_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "APPLICATION_OPERATION_FAILED",
        "Application 操作失败，已回滚本次操作",
    )


@router.post(
    "/intake",
    response_model=ApplicationIntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def intake_application(
    data: ApplicationIntakeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> ApplicationIntakeResponse:
    try:
        result: ApplicationIntakeResult = await application_intake_service.intake(
            db,
            data,
        )
    except Exception as exc:
        raise _map_intake_error(exc) from exc

    if result.existing_application_reused:
        response.status_code = status.HTTP_200_OK
    return ApplicationIntakeResponse(
        application=result.application,
        candidate_resolution=result.candidate_resolution,
        existing_application_reused=result.existing_application_reused,
        suspected_duplicate_candidate_ids=list(
            result.suspected_duplicate_candidate_ids
        ),
    )


@router.post("/{application_id}/pass", response_model=ApplicationRead)
async def pass_application(
    application_id: int,
    data: PassApplicationRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        return await application_decision_service.pass_application(
            db,
            application_id,
            data,
        )
    except Exception as exc:
        raise _map_application_error(exc) from exc


@router.post("/{application_id}/backup", response_model=ApplicationRead)
async def backup_application(
    application_id: int,
    data: BackupApplicationRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        return await application_decision_service.backup_application(
            db,
            application_id,
            data,
        )
    except Exception as exc:
        raise _map_application_error(exc) from exc


@router.post("/{application_id}/reject", response_model=ApplicationRead)
async def reject_application(
    application_id: int,
    data: RejectApplicationRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        return await application_decision_service.reject_application(
            db,
            application_id,
            data,
        )
    except Exception as exc:
        raise _map_application_error(exc) from exc


@router.post("/{application_id}/undo-rejection", response_model=ApplicationRead)
async def undo_application_rejection(
    application_id: int,
    data: ReverseDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        return await application_decision_service.undo_rejection(
            db,
            application_id,
            data,
        )
    except Exception as exc:
        raise _map_application_error(exc) from exc


@router.post("/{application_id}/void", response_model=ApplicationRead)
async def void_application(
    application_id: int,
    data: VoidApplicationRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    try:
        return await application_decision_service.void_application(
            db,
            application_id,
            data,
        )
    except Exception as exc:
        raise _map_application_error(exc) from exc


@router.get("/{application_id}/history", response_model=list[StageHistoryRead])
async def list_application_history(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[StageHistoryRead]:
    try:
        return await application_decision_service.list_history(db, application_id)
    except Exception as exc:
        raise _map_application_error(exc) from exc
