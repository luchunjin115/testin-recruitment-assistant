from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project_experience import ProjectExperience
from app.schemas.project_experience import (
    ProjectExperienceCreate,
    ProjectExperienceRead,
    ProjectExperienceUpdate,
)
from app.services.project_experience_service import project_experience_service


router = APIRouter(prefix="/project-experiences", tags=["project-experiences"])
CANDIDATE_NOT_FOUND = "候选人不存在"
PROJECT_EXPERIENCE_NOT_FOUND = "项目经历不存在"


@router.post("", response_model=ProjectExperienceRead, status_code=status.HTTP_201_CREATED)
async def create_project_experience(
    data: ProjectExperienceCreate,
    candidate_id: int = Query(ge=1),
    db: AsyncSession = Depends(get_db),
) -> ProjectExperience:
    experience = await project_experience_service.create_project_experience(
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


@router.get("", response_model=list[ProjectExperienceRead])
async def list_project_experiences(
    candidate_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectExperience]:
    return await project_experience_service.list_project_experiences(db, candidate_id)


@router.get("/{experience_id}", response_model=ProjectExperienceRead)
async def get_project_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProjectExperience:
    experience = await project_experience_service.get_project_experience(db, experience_id)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROJECT_EXPERIENCE_NOT_FOUND,
        )
    return experience


@router.put("/{experience_id}", response_model=ProjectExperienceRead)
async def update_project_experience(
    experience_id: int,
    data: ProjectExperienceUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectExperience:
    experience = await project_experience_service.update_project_experience(
        db,
        experience_id,
        data,
    )
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROJECT_EXPERIENCE_NOT_FOUND,
        )
    return experience


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_project_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await project_experience_service.delete_project_experience(
        db,
        experience_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROJECT_EXPERIENCE_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
