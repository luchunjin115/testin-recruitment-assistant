from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeRead, ResumeUpdate
from app.schemas.rebuilt.resume_structure import (
    ResumeStructureRequest,
    ResumeStructureResponse,
)
from app.adapters.rebuilt.resume_structure import (
    ResumeStructureAdapterError,
    ResumeStructureAuthenticationError,
    ResumeStructureConfigurationError as ResumeStructureAdapterConfigurationError,
    ResumeStructureEmptyResponseError,
    ResumeStructureInputError as ResumeStructureAdapterInputError,
    ResumeStructureQuotaError,
    ResumeStructureRateLimitError,
    ResumeStructureResponseInterruptedError,
    ResumeStructureServiceUnavailableError,
    ResumeStructureTimeoutError,
    ResumeStructureUpstreamError,
)
from app.services.rebuilt.resume_service import (
    ResumeAlreadyBoundError,
    ResumeCandidateNotFoundError,
    ResumeJobNotFoundError,
    ResumeTextExtractionConflictError,
    ResumeTextExtractionFailedError,
    ResumeFileUnavailableError,
    UnsupportedResumeFileError,
    UnsupportedResumeTextExtractionError,
    resume_service,
)
from app.services.rebuilt.resume_structure_service import (
    ResumeStructureConflictError,
    ResumeStructureConfigurationError,
    ResumeStructureDisabledError,
    ResumeStructureInputError,
    ResumeStructureInvalidOutputError,
    ResumeStructureNotFoundError,
    ResumeStructurePrerequisiteError,
    ResumeStructureServiceResult,
    ResumeStructureUnexpectedError,
    resume_structure_service,
)
from app.services.rebuilt.resume_file_cleanup import (
    ResumeCleanupStorageError,
    ResumeCleanupValidationError,
    UnsupportedResumeCleanupError,
)
from app.services.rebuilt.resume_storage import (
    EmptyResumeFileError,
    InvalidResumeContentError,
    InvalidResumeFilenameError,
    ResumeFileTooLargeError,
    ResumeStorageError,
    UnsupportedResumeTypeError,
)


router = APIRouter(prefix="/resumes", tags=["resumes"])
RESUME_NOT_FOUND = "简历不存在"


def _structure_response(result: ResumeStructureServiceResult) -> ResumeStructureResponse:
    return ResumeStructureResponse(
        resume_id=result.resume_id,
        structure_status=result.structure_status,
        structure_error=result.structure_error,
        from_cache=result.from_cache,
        has_previous_draft=result.has_previous_draft,
        draft=result.draft,
    )


async def _raise_structure_http_error(
    *,
    db: AsyncSession,
    resume_id: int,
    force: bool,
    status_code: int,
    detail: str,
) -> None:
    if force:
        try:
            previous = await resume_structure_service.get_current_result(db, resume_id)
        except Exception:
            previous = None
        if previous is not None and previous.structure_status in {"succeeded", "failed"}:
            body = _structure_response(previous).model_dump(mode="json")
            body["detail"] = detail
            raise HTTPException(
                status_code=status_code,
                detail=jsonable_encoder(body),
            )
    raise HTTPException(status_code=status_code, detail=detail)


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: Annotated[UploadFile, File()],
    candidate_id: Annotated[int | None, Form(ge=1)] = None,
    job_id: Annotated[int | None, Form(ge=1)] = None,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    settings = get_settings()
    try:
        return await resume_service.upload_resume(
            db=db,
            upload=file,
            candidate_id=candidate_id,
            job_id=job_id,
            upload_root=Path(settings.V2_STORAGE_DIR),
            max_size_bytes=settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        )
    except ResumeCandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResumeJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedResumeTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ResumeFileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except (
        EmptyResumeFileError,
        InvalidResumeContentError,
        InvalidResumeFilenameError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResumeStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败",
        ) from exc
    finally:
        await file.close()


@router.post("/{resume_id}/extract-text", response_model=ResumeRead)
async def extract_resume_text(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    settings = get_settings()
    try:
        resume = await resume_service.extract_text(
            db=db,
            resume_id=resume_id,
            storage_root=Path(settings.V2_STORAGE_DIR),
        )
    except ResumeTextExtractionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UnsupportedResumeTextExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ResumeTextExtractionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )
    return resume


@router.post(
    "/{resume_id}/structure",
    response_model=ResumeStructureResponse,
)
async def structure_resume(
    resume_id: int,
    data: ResumeStructureRequest,
    db: AsyncSession = Depends(get_db),
) -> ResumeStructureResponse:
    try:
        result = await resume_structure_service.structure_resume(
            db=db,
            resume_id=resume_id,
            force=data.force,
        )
    except ResumeStructureNotFoundError as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except (ResumeStructurePrerequisiteError, ResumeStructureConflictError) as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except (ResumeStructureInputError, ResumeStructureAdapterInputError) as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ResumeStructureRateLimitError as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        )
    except ResumeStructureTimeoutError as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except (
        ResumeStructureDisabledError,
        ResumeStructureConfigurationError,
        ResumeStructureAdapterConfigurationError,
        ResumeStructureAuthenticationError,
        ResumeStructureQuotaError,
        ResumeStructureServiceUnavailableError,
    ) as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except (
        ResumeStructureInvalidOutputError,
        ResumeStructureEmptyResponseError,
        ResumeStructureResponseInterruptedError,
        ResumeStructureUpstreamError,
        ResumeStructureAdapterError,
    ) as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except ResumeStructureUnexpectedError as exc:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception:
        await _raise_structure_http_error(
            db=db,
            resume_id=resume_id,
            force=data.force,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="简历结构化识别发生未预期错误",
        )

    return _structure_response(result)


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(
    data: ResumeCreate,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    return await resume_service.create_resume(db, data)


@router.get("", response_model=list[ResumeRead])
async def list_resumes(
    candidate_id: Annotated[int | None, Query(ge=1)] = None,
    db: AsyncSession = Depends(get_db),
) -> list[Resume]:
    return await resume_service.list_resumes(db, candidate_id=candidate_id)


@router.get("/{resume_id}/file", response_class=FileResponse)
async def get_resume_file(
    resume_id: int,
    download: bool = False,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    settings = get_settings()
    try:
        file_descriptor = await resume_service.get_resume_file(
            db=db,
            resume_id=resume_id,
            storage_root=Path(settings.V2_STORAGE_DIR),
        )
    except UnsupportedResumeFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ResumeFileUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if file_descriptor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )

    disposition = (
        "attachment"
        if download or not file_descriptor.supports_inline_preview
        else "inline"
    )
    return FileResponse(
        path=file_descriptor.path,
        filename=file_descriptor.filename,
        media_type=file_descriptor.media_type,
        content_disposition_type=disposition,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    resume = await resume_service.get_resume(db, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )
    return resume


@router.put("/{resume_id}", response_model=ResumeRead)
async def update_resume(
    resume_id: int,
    data: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    resume = await resume_service.update_resume(db, resume_id, data)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )
    return resume


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    settings = get_settings()
    try:
        deleted = await resume_service.delete_resume(
            db,
            resume_id,
            storage_root=Path(settings.V2_STORAGE_DIR),
        )
    except ResumeAlreadyBoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UnsupportedResumeCleanupError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except ResumeCleanupValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ResumeCleanupStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="简历文件清理失败",
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
