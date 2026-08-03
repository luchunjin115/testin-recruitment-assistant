from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.education import Education
from app.schemas.rebuilt.education import EducationCreate, EducationRead, EducationUpdate
from app.services.rebuilt.education_service import education_service


router = APIRouter(prefix="/education", tags=["education"])
CANDIDATE_NOT_FOUND = "候选人不存在"
EDUCATION_NOT_FOUND = "教育经历不存在"


@router.post("", response_model=EducationRead, status_code=status.HTTP_201_CREATED)
async def create_education(
    data: EducationCreate,
    candidate_id: int = Query(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Education:
    education = await education_service.create_education(db, candidate_id, data)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CANDIDATE_NOT_FOUND,
        )
    return education


@router.get("", response_model=list[EducationRead])
async def list_education(
    candidate_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[Education]:
    return await education_service.list_education(db, candidate_id)


@router.get("/{education_id}", response_model=EducationRead)
async def get_education(
    education_id: int,
    db: AsyncSession = Depends(get_db),
) -> Education:
    education = await education_service.get_education(db, education_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EDUCATION_NOT_FOUND,
        )
    return education


@router.put("/{education_id}", response_model=EducationRead)
async def update_education(
    education_id: int,
    data: EducationUpdate,
    db: AsyncSession = Depends(get_db),
) -> Education:
    education = await education_service.update_education(db, education_id, data)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EDUCATION_NOT_FOUND,
        )
    return education


@router.delete(
    "/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_education(
    education_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await education_service.delete_education(db, education_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EDUCATION_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
