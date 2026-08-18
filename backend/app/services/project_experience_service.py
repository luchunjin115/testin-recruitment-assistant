from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.project_experience import ProjectExperience
from app.schemas.project_experience import (
    ProjectExperienceCreate,
    ProjectExperienceUpdate,
)


class ProjectExperienceService:
    async def create_project_experience(
        self,
        db: AsyncSession,
        candidate_id: int,
        data: ProjectExperienceCreate,
    ) -> ProjectExperience | None:
        if await db.get(Candidate, candidate_id) is None:
            return None

        experience = ProjectExperience(candidate_id=candidate_id, **data.model_dump())
        db.add(experience)
        await self._commit_and_refresh(db, experience)
        return experience

    async def get_project_experience(
        self,
        db: AsyncSession,
        experience_id: int,
    ) -> ProjectExperience | None:
        return await db.get(ProjectExperience, experience_id)

    async def list_project_experiences(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
    ) -> list[ProjectExperience]:
        statement = select(ProjectExperience)
        if candidate_id is not None:
            statement = statement.where(ProjectExperience.candidate_id == candidate_id)
        statement = statement.order_by(
            ProjectExperience.updated_at.desc(),
            ProjectExperience.id.desc(),
        )
        result = await db.scalars(statement)
        return list(result.all())

    async def update_project_experience(
        self,
        db: AsyncSession,
        experience_id: int,
        data: ProjectExperienceUpdate,
    ) -> ProjectExperience | None:
        experience = await self.get_project_experience(db, experience_id)
        if experience is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(experience, field, value)

        await self._commit_and_refresh(db, experience)
        return experience

    async def delete_project_experience(
        self,
        db: AsyncSession,
        experience_id: int,
    ) -> bool:
        experience = await self.get_project_experience(db, experience_id)
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
        experience: ProjectExperience,
    ) -> None:
        try:
            await db.commit()
            await db.refresh(experience)
        except Exception:
            await db.rollback()
            raise


project_experience_service = ProjectExperienceService()
