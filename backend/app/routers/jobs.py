from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.job import JobCreate, JobStatusUpdate, JobUpdate
from ..services.job_service import job_service

router = APIRouter(prefix="/jobs", tags=["岗位管理"])


@router.get("/")
def list_jobs(status: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        jobs = job_service.list_jobs(db, status=status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [job_service.to_read(db, job) for job in jobs]


@router.get("/active")
def list_active_jobs(db: Session = Depends(get_db)):
    jobs = job_service.list_active_jobs(db)
    return [job_service.to_read(db, job) for job in jobs]


@router.post("/")
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    try:
        job = job_service.create_job(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return job_service.to_read(db, job)


@router.put("/{job_id}")
def update_job(job_id: int, data: JobUpdate, db: Session = Depends(get_db)):
    try:
        job = job_service.update_job(db, job_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job_service.to_read(db, job)


@router.patch("/{job_id}/status")
def update_job_status(job_id: int, data: JobStatusUpdate, db: Session = Depends(get_db)):
    try:
        job = job_service.update_status(db, job_id, data.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job_service.to_read(db, job)


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    ok, action = job_service.delete_or_deactivate(db, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="岗位不存在")
    if action == "deactivated":
        return {"message": "该岗位已有候选人，已自动停用以保留历史数据", "action": action}
    return {"message": "岗位已删除", "action": action}
