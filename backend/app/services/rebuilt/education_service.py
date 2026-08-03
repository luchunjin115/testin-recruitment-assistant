from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.schemas.rebuilt.education import EducationCreate, EducationUpdate


class EducationService:
    async def create_education(
        self,
        db: AsyncSession,
        candidate_id: int,
        data: EducationCreate,
    ) -> Education | None:
        if await db.get(Candidate, candidate_id) is None:
            return None

        education = Education(candidate_id=candidate_id, **data.model_dump())
        db.add(education)
        await self._commit_and_refresh(db, education)
        return education

    async def get_education(
        self,
        db: AsyncSession,
        education_id: int,
    ) -> Education | None:
        return await db.get(Education, education_id)

    async def list_education(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
    ) -> list[Education]:
        statement = select(Education)
        if candidate_id is not None:
            statement = statement.where(Education.candidate_id == candidate_id)
        statement = statement.order_by(Education.updated_at.desc(), Education.id.desc())
        result = await db.scalars(statement)
        return list(result.all())

    async def update_education(
        self,
        db: AsyncSession,
        education_id: int,
        data: EducationUpdate,
    ) -> Education | None:
        education = await self.get_education(db, education_id)
        if education is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(education, field, value)

        await self._commit_and_refresh(db, education)
        return education

    async def delete_education(self, db: AsyncSession, education_id: int) -> bool:
        education = await self.get_education(db, education_id)
        if education is None:
            return False

        try:
            await db.delete(education)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, education: Education) -> None:
        try:
            await db.commit()
            await db.refresh(education)
        except Exception:
            await db.rollback()
            raise


education_service = EducationService()
