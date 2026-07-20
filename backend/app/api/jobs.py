from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate, JobRead
from app.services.rebuilt.job_service import job_service


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await job_service.create_job(db, data)
