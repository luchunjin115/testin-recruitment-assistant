from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.work_experience import WorkExperienceCreate, WorkExperienceUpdate


class WorkExperienceService:
    async def create_work_experience(
        self,
        db: AsyncSession,
        candidate_id: int,
        data: WorkExperienceCreate,
    ) -> WorkExperience | None:
        if await db.get(Candidate, candidate_id) is None:
            return None

        experience = WorkExperience(candidate_id=candidate_id, **data.model_dump())
        db.add(experience)
        await self._commit_and_refresh(db, experience)
        return experience

    async def get_work_experience(
        self,
        db: AsyncSession,
        experience_id: int,
    ) -> WorkExperience | None:
        return await db.get(WorkExperience, experience_id)

    async def list_work_experiences(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
    ) -> list[WorkExperience]:
        statement = select(WorkExperience)
        if candidate_id is not None:
            statement = statement.where(WorkExperience.candidate_id == candidate_id)
        statement = statement.order_by(
            WorkExperience.updated_at.desc(),
            WorkExperience.id.desc(),
        )
        result = await db.scalars(statement)
        return list(result.all())

    async def update_work_experience(
        self,
        db: AsyncSession,
        experience_id: int,
        data: WorkExperienceUpdate,
    ) -> WorkExperience | None:
        experience = await self.get_work_experience(db, experience_id)
        if experience is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(experience, field, value)

        await self._commit_and_refresh(db, experience)
        return experience

    async def delete_work_experience(
        self,
        db: AsyncSession,
        experience_id: int,
    ) -> bool:
        experience = await self.get_work_experience(db, experience_id)
        if experience is None:
            return False

        try:
            await db.delete(experience)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(
        db: AsyncSession,
        experience: WorkExperience,
    ) -> None:
        try:
            await db.commit()
            await db.refresh(experience)
        except Exception:
            await db.rollback()
            raise


work_experience_service = WorkExperienceService()
