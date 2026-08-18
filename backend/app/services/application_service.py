from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application


class ApplicationService:
    """Read Application records for the stage 7 HR workspace."""

    async def get_application(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> Application | None:
        return await db.get(Application, application_id)

    async def list_applications(
        self,
        db: AsyncSession,
        *,
        job_id: int | None = None,
        recruitment_stage: str | None = None,
        ai_status: str | None = None,
        hr_decision: str | None = None,
        lifecycle_status: str | None = None,
    ) -> list[Application]:
        statement = select(Application)
        if job_id is not None:
            statement = statement.where(Application.job_id == job_id)
        if recruitment_stage is not None:
            statement = statement.where(
                Application.recruitment_stage == recruitment_stage
            )
        if ai_status is not None:
            statement = statement.where(Application.ai_status == ai_status)
        if hr_decision is not None:
            statement = statement.where(Application.hr_decision == hr_decision)
        if lifecycle_status is not None:
            statement = statement.where(
                Application.lifecycle_status == lifecycle_status
            )
        statement = statement.order_by(
            Application.applied_at.desc(),
            Application.id.desc(),
        )
        result = await db.scalars(statement)
        return list(result.all())


application_service = ApplicationService()


__all__ = ["ApplicationService", "application_service"]
