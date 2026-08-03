from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.work_experience import (
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)
from app.services.rebuilt.work_experience_service import work_experience_service


router = APIRouter(prefix="/work-experiences", tags=["work-experiences"])
CANDIDATE_NOT_FOUND = "候选人不存在"
WORK_EXPERIENCE_NOT_FOUND = "工作经历不存在"


@router.post("", response_model=WorkExperienceRead, status_code=status.HTTP_201_CREATED)
async def create_work_experience(
    data: WorkExperienceCreate,
    candidate_id: int = Query(ge=1),
    db: AsyncSession = Depends(get_db),
) -> WorkExperience:
    experience = await work_experience_service.create_work_experience(
        db,
        candidate_id,
        data,
    )
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CANDIDATE_NOT_FOUND,
        )
    return experience


@router.get("", response_model=list[WorkExperienceRead])
async def list_work_experiences(
    candidate_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[WorkExperience]:
    return await work_experience_service.list_work_experiences(db, candidate_id)


@router.get("/{experience_id}", response_model=WorkExperienceRead)
async def get_work_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
) -> WorkExperience:
    experience = await work_experience_service.get_work_experience(db, experience_id)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORK_EXPERIENCE_NOT_FOUND,
        )
    return experience


@router.put("/{experience_id}", response_model=WorkExperienceRead)
async def update_work_experience(
    experience_id: int,
    data: WorkExperienceUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkExperience:
    experience = await work_experience_service.update_work_experience(
        db,
        experience_id,
        data,
    )
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORK_EXPERIENCE_NOT_FOUND,
        )
    return experience


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_work_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await work_experience_service.delete_work_experience(db, experience_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORK_EXPERIENCE_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
