from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeRead, ResumeUpdate
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
