from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.activity_log import ActivityLog
from app.schemas.rebuilt.activity_log import ActivityLogCreate


class ActivityLogService:
    async def create_activity_log(
        self,
        db: AsyncSession,
        data: ActivityLogCreate,
    ) -> ActivityLog:
        activity_log = ActivityLog(**data.model_dump())
        db.add(activity_log)
        try:
            await db.commit()
            await db.refresh(activity_log)
        except Exception:
            await db.rollback()
            raise
        return activity_log

    async def get_activity_log(
        self,
        db: AsyncSession,
        activity_log_id: int,
    ) -> ActivityLog | None:
        return await db.get(ActivityLog, activity_log_id)

    async def list_activity_logs(
        self,
        db: AsyncSession,
        target_type: str | None = None,
        target_id: int | None = None,
        action: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[ActivityLog]:
        statement = select(ActivityLog)
        if target_type is not None:
            statement = statement.where(ActivityLog.target_type == target_type)
        if target_id is not None:
            statement = statement.where(ActivityLog.target_id == target_id)
        if action is not None:
            statement = statement.where(ActivityLog.action == action)
        if user_id is not None:
            statement = statement.where(ActivityLog.user_id == user_id)
        statement = statement.order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        ).limit(limit)
        result = await db.scalars(statement)
        return list(result.all())


activity_log_service = ActivityLogService()
