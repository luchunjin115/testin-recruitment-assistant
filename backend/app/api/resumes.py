from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeRead, ResumeUpdate
from app.services.rebuilt.resume_service import resume_service


router = APIRouter(prefix="/resumes", tags=["resumes"])
RESUME_NOT_FOUND = "简历不存在"


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(
    data: ResumeCreate,
    db: AsyncSession = Depends(get_db),
) -> Resume:
    return await resume_service.create_resume(db, data)


@router.get("", response_model=list[ResumeRead])
async def list_resumes(db: AsyncSession = Depends(get_db)) -> list[Resume]:
    return await resume_service.list_resumes(db)


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
    deleted = await resume_service.delete_resume(db, resume_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RESUME_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
