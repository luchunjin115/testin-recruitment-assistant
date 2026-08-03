from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeUpdate


class ResumeService:
    async def create_resume(self, db: AsyncSession, data: ResumeCreate) -> Resume:
        resume = Resume(**data.model_dump())
        db.add(resume)
        await self._commit_and_refresh(db, resume)
        return resume

    async def get_resume(self, db: AsyncSession, resume_id: int) -> Resume | None:
        return await db.get(Resume, resume_id)

    async def list_resumes(self, db: AsyncSession) -> list[Resume]:
        statement = select(Resume).order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        result = await db.scalars(statement)
        return list(result.all())

    async def update_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        data: ResumeUpdate,
    ) -> Resume | None:
        resume = await self.get_resume(db, resume_id)
        if resume is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(resume, field, value)

        await self._commit_and_refresh(db, resume)
        return resume

    async def delete_resume(self, db: AsyncSession, resume_id: int) -> bool:
        resume = await self.get_resume(db, resume_id)
        if resume is None:
            return False

        try:
            await db.delete(resume)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, resume: Resume) -> None:
        try:
            await db.commit()
            await db.refresh(resume)
        except Exception:
            await db.rollback()
            raise


resume_service = ResumeService()
