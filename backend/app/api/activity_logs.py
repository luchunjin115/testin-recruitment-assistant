from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.activity_log import ActivityLog
from app.schemas.activity_log import ActivityLogCreate, ActivityLogRead
from app.services.activity_log_service import activity_log_service


router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])
ACTIVITY_LOG_NOT_FOUND = "操作日志不存在"


@router.post("", response_model=ActivityLogRead, status_code=status.HTTP_201_CREATED)
async def create_activity_log(
    data: ActivityLogCreate,
    db: AsyncSession = Depends(get_db),
) -> ActivityLog:
    return await activity_log_service.create_activity_log(db, data)


@router.get("", response_model=list[ActivityLogRead])
async def list_activity_logs(
    target_type: str | None = Query(default=None, max_length=50),
    target_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None, max_length=100),
    user_id: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityLog]:
    return await activity_log_service.list_activity_logs(
        db,
        target_type,
        target_id,
        action,
        user_id,
        limit,
    )


@router.get("/{activity_log_id}", response_model=ActivityLogRead)
async def get_activity_log(
    activity_log_id: int,
    db: AsyncSession = Depends(get_db),
) -> ActivityLog:
    activity_log = await activity_log_service.get_activity_log(db, activity_log_id)
    if activity_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ACTIVITY_LOG_NOT_FOUND,
        )
    return activity_log
