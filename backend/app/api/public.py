from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.schemas.public_application import (
    PublicApplicationAcceptedResponse,
    PublicApplicationErrorCode,
    PublicApplicationForm,
    PublicJobRead,
)
from app.services.public_application_rate_limiter import (
    PublicApplicationRateLimitExceededError,
    PublicApplicationRateLimitUnavailableError,
    public_application_rate_limiter,
)
from app.services.public_application_service import (
    PublicApplicationIdempotencyConflictError,
    PublicApplicationInfrastructureUnavailableError,
    PublicApplicationJobNotOpenError,
    PublicApplicationReviewRequiredError,
    PublicApplicationSaveError,
    public_application_service,
)
from app.services.public_job_service import public_job_service
from app.services.resume_storage import (
    EmptyResumeFileError,
    InvalidResumeContentError,
    InvalidResumeFilenameError,
    ResumeFileTooLargeError,
    ResumeStorageError,
    UnsupportedResumeTypeError,
    resume_file_storage,
)


router = APIRouter(prefix="/public", tags=["public"])
ACCEPTED_MESSAGE = "投递已收到，招聘团队会在审核后与合适的候选人联系。"
_FORM_FIELDS = {
    "name",
    "phone",
    "email",
    "job_id",
    "privacy_consent",
    "consent_version",
    "idempotency_key",
    "resume",
}


class PublicApplicationBodyLimitMiddleware:
    def __init__(self, app, *, max_body_size: int) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send) -> None:
        if not (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"].rstrip("/") == "/api/v2/public/applications"
        ):
            await self.app(scope, receive, send)
            return

        content_length = next(
            (
                value
                for key, value in scope.get("headers", ())
                if key.lower() == b"content-length"
            ),
            None,
        )
        try:
            declared_size = int(content_length) if content_length is not None else None
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > self.max_body_size:
            await self._reject(scope, receive, send)
            return

        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            body.extend(chunk)
            if len(body) > self.max_body_size:
                await self._reject(scope, receive, send)
                return
            more_body = message.get("more_body", False)

        delivered = False

        async def replay_receive():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope, receive, send) -> None:
        response = JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "detail": {
                    "code": PublicApplicationErrorCode.RESUME_FILE_TOO_LARGE.value,
                    "message": "简历文件超过 10 MB 限制",
                }
            },
        )
        await response(scope, receive, send)


@dataclass(frozen=True)
class _ParsedPublicApplication:
    data: PublicApplicationForm


def install_public_exception_handlers(app: FastAPI) -> None:
    previous_handler = app.exception_handlers.get(
        RequestValidationError,
        request_validation_exception_handler,
    )

    async def combined_handler(request: Request, exc: RequestValidationError):
        if request.url.path.rstrip("/") == "/api/v2/public/applications":
            error = _validation_error()
            return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
        return await previous_handler(request, exc)

    app.add_exception_handler(RequestValidationError, combined_handler)


def _public_error(
    status_code: int,
    code: PublicApplicationErrorCode,
    message: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code.value, "message": message},
    )


def _validation_error() -> HTTPException:
    return _public_error(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        PublicApplicationErrorCode.VALIDATION_FAILED,
        "投递信息未通过校验，请检查后重试",
    )


async def get_public_rate_limit_redis() -> AsyncGenerator[Redis, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def _parse_public_application(
    request: Request,
    name: Annotated[str, Form()],
    phone: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_id: Annotated[str, Form()],
    privacy_consent: Annotated[str, Form()],
    consent_version: Annotated[str, Form()],
    idempotency_key: Annotated[str, Form()],
) -> _ParsedPublicApplication:
    form = await request.form()
    if set(form.keys()) - _FORM_FIELDS:
        raise _validation_error()
    if any(len(form.getlist(field)) != 1 for field in _FORM_FIELDS if field in form):
        raise _validation_error()

    try:
        parsed_job_id: object = int(job_id)
    except ValueError:
        parsed_job_id = job_id
    if privacy_consent == "true":
        parsed_consent: object = True
    elif privacy_consent == "false":
        parsed_consent = False
    else:
        parsed_consent = privacy_consent

    try:
        data = PublicApplicationForm.model_validate(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "job_id": parsed_job_id,
                "privacy_consent": parsed_consent,
                "consent_version": consent_version,
                "idempotency_key": idempotency_key,
            }
        )
    except ValidationError as exc:
        raise _validation_error() from exc
    return _ParsedPublicApplication(data=data)


@router.get("/jobs", response_model=list[PublicJobRead])
async def list_public_jobs(db: AsyncSession = Depends(get_db)) -> list[PublicJobRead]:
    jobs = await public_job_service.list_open_jobs(db)
    return [PublicJobRead.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=PublicJobRead)
async def get_public_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> PublicJobRead:
    job = await public_job_service.get_open_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PUBLIC_JOB_NOT_FOUND", "message": "岗位不存在或暂未开放"},
        )
    return PublicJobRead.model_validate(job)


@router.post(
    "/applications",
    response_model=PublicApplicationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_public_application(
    request: Request,
    resume: Annotated[UploadFile, File()],
    parsed: _ParsedPublicApplication = Depends(_parse_public_application),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_public_rate_limit_redis),
) -> PublicApplicationAcceptedResponse:
    settings = get_settings()
    data = parsed.data
    if data.consent_version != settings.PUBLIC_APPLICATION_CONSENT_VERSION:
        raise _public_error(
            status.HTTP_400_BAD_REQUEST,
            PublicApplicationErrorCode.INVALID,
            "隐私说明版本已更新，请刷新页面后重新确认",
        )

    try:
        await public_application_rate_limiter.check(
            redis,
            client_ip=request.client.host if request.client else "unknown",
            phone=data.phone,
            email=data.email,
            window_seconds=settings.PUBLIC_APPLICATION_RATE_LIMIT_WINDOW_SECONDS,
            per_ip=settings.PUBLIC_APPLICATION_RATE_LIMIT_PER_IP,
            per_contact=settings.PUBLIC_APPLICATION_RATE_LIMIT_PER_CONTACT,
        )
    except PublicApplicationRateLimitExceededError as exc:
        error = _public_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            PublicApplicationErrorCode.RATE_LIMITED,
            "提交过于频繁，请稍后重试",
        )
        error.headers = {"Retry-After": str(exc.retry_after)}
        raise error from exc
    except PublicApplicationRateLimitUnavailableError as exc:
        raise _public_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            PublicApplicationErrorCode.TEMPORARILY_UNAVAILABLE,
            "投递服务暂时不可用，请稍后重试",
        ) from exc

    try:
        prepared = await resume_file_storage.prepare(
            resume,
            Path(settings.STORAGE_DIR),
            settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        )
    except ResumeFileTooLargeError as exc:
        raise _public_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            PublicApplicationErrorCode.RESUME_FILE_TOO_LARGE,
            "简历文件超过 10 MB 限制",
        ) from exc
    except UnsupportedResumeTypeError as exc:
        raise _public_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            PublicApplicationErrorCode.RESUME_TYPE_UNSUPPORTED,
            "仅支持 PDF、DOCX 或 TXT 简历",
        ) from exc
    except (InvalidResumeFilenameError, EmptyResumeFileError, InvalidResumeContentError) as exc:
        raise _public_error(
            status.HTTP_400_BAD_REQUEST,
            PublicApplicationErrorCode.INVALID,
            "简历文件无效，请检查后重试",
        ) from exc
    except ResumeStorageError as exc:
        raise _public_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            PublicApplicationErrorCode.SAVE_FAILED,
            "投递保存失败，请稍后重试",
        ) from exc

    try:
        result = await public_application_service.accept(
            db,
            data,
            prepared,
            storage=resume_file_storage,
        )
    except PublicApplicationJobNotOpenError as exc:
        raise _public_error(
            status.HTTP_409_CONFLICT,
            PublicApplicationErrorCode.JOB_NOT_OPEN,
            "岗位不存在或当前未开放",
        ) from exc
    except PublicApplicationIdempotencyConflictError as exc:
        raise _public_error(
            status.HTTP_409_CONFLICT,
            PublicApplicationErrorCode.IDEMPOTENCY_KEY_REUSED,
            "本次提交标识已用于其他内容，请重新发起投递",
        ) from exc
    except PublicApplicationReviewRequiredError as exc:
        raise _public_error(
            status.HTTP_409_CONFLICT,
            PublicApplicationErrorCode.REVIEW_REQUIRED,
            "本次投递需要招聘团队人工核对，请联系招聘团队",
        ) from exc
    except PublicApplicationInfrastructureUnavailableError as exc:
        raise _public_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            PublicApplicationErrorCode.TEMPORARILY_UNAVAILABLE,
            "投递服务暂时不可用，请稍后重试",
        ) from exc
    except PublicApplicationSaveError as exc:
        raise _public_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            PublicApplicationErrorCode.SAVE_FAILED,
            "投递保存失败，请稍后重试",
        ) from exc

    return PublicApplicationAcceptedResponse(
        submission_reference=result.submission_reference,
        accepted_at=result.accepted_at,
        message=ACCEPTED_MESSAGE,
    )


__all__ = [
    "PublicApplicationBodyLimitMiddleware",
    "create_public_application",
    "get_public_job",
    "get_public_rate_limit_redis",
    "install_public_exception_handlers",
    "list_public_jobs",
    "router",
]
