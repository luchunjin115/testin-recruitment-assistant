from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate, JobUpdate


class JobService:
    async def create_job(self, db: AsyncSession, data: JobCreate) -> Job:
        job = Job(**data.model_dump())
        db.add(job)
        await self._commit_and_refresh(db, job)
        return job

    async def get_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await db.get(Job, job_id)

    async def list_jobs(self, db: AsyncSession) -> list[Job]:
        statement = select(Job).order_by(Job.updated_at.desc(), Job.id.desc())
        result = await db.scalars(statement)
        return list(result.all())

    async def update_job(
        self,
        db: AsyncSession,
        job_id: int,
        data: JobUpdate,
    ) -> Job | None:
        job = await self.get_job(db, job_id)
        if job is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(job, field, value)

        await self._commit_and_refresh(db, job)
        return job

    async def delete_job(self, db: AsyncSession, job_id: int) -> bool:
        job = await self.get_job(db, job_id)
        if job is None:
            return False

        try:
            await db.delete(job)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, job: Job) -> None:
        try:
            await db.commit()
            await db.refresh(job)
        except Exception:
            await db.rollback()
            raise


job_service = JobService()
