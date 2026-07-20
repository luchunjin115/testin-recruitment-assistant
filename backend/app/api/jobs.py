from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate, JobRead, JobUpdate
from app.services.rebuilt.job_service import job_service


router = APIRouter(prefix="/jobs", tags=["jobs"])
JOB_NOT_FOUND = "岗位不存在"


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await job_service.create_job(db, data)


@router.get("", response_model=list[JobRead])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[Job]:
    return await job_service.list_jobs(db)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Job:
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=JOB_NOT_FOUND,
        )
    return job


@router.put("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: int,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
) -> Job:
    job = await job_service.update_job(db, job_id, data)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=JOB_NOT_FOUND,
        )
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await job_service.delete_job(db, job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=JOB_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
