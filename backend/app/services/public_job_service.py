from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


class PublicJobService:
    async def list_open_jobs(self, db: AsyncSession) -> list[Job]:
        result = await db.scalars(
            select(Job).where(Job.status == "open").order_by(Job.created_at.desc(), Job.id)
        )
        return list(result.all())

    async def get_open_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await db.scalar(
            select(Job).where(Job.id == job_id, Job.status == "open")
        )


public_job_service = PublicJobService()
