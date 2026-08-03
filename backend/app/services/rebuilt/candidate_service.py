from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.models.rebuilt.project_experience import ProjectExperience
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.candidate import CandidateCreate, CandidateUpdate


EXPERIENCE_FIELDS = (
    "education_records",
    "work_experiences",
    "project_experiences",
)


class CandidateService:
    async def create_candidate(
        self,
        db: AsyncSession,
        data: CandidateCreate,
    ) -> Candidate:
        candidate_data = data.model_dump(exclude=set(EXPERIENCE_FIELDS))
        candidate = Candidate(
            **candidate_data,
            education_records=[
                Education(**record.model_dump()) for record in data.education_records
            ],
            work_experiences=[
                WorkExperience(**record.model_dump()) for record in data.work_experiences
            ],
            project_experiences=[
                ProjectExperience(**record.model_dump())
                for record in data.project_experiences
            ],
        )

        db.add(candidate)
        await self._commit_and_refresh(db, candidate)
        return candidate

    async def get_candidate(
        self,
        db: AsyncSession,
        candidate_id: int,
    ) -> Candidate | None:
        statement = (
            select(Candidate)
            .options(
                selectinload(Candidate.education_records),
                selectinload(Candidate.work_experiences),
                selectinload(Candidate.project_experiences),
            )
            .where(Candidate.id == candidate_id)
        )
        return await db.scalar(statement)

    async def list_candidates(self, db: AsyncSession) -> list[Candidate]:
        statement = (
            select(Candidate)
            .options(
                selectinload(Candidate.education_records),
                selectinload(Candidate.work_experiences),
                selectinload(Candidate.project_experiences),
            )
            .order_by(Candidate.updated_at.desc(), Candidate.id.desc())
        )
        result = await db.scalars(statement)
        return list(result.all())

    async def update_candidate(
        self,
        db: AsyncSession,
        candidate_id: int,
        data: CandidateUpdate,
    ) -> Candidate | None:
        candidate = await self.get_candidate(db, candidate_id)
        if candidate is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(candidate, field, value)

        await self._commit_and_refresh(db, candidate)
        return candidate

    async def delete_candidate(self, db: AsyncSession, candidate_id: int) -> bool:
        candidate = await self.get_candidate(db, candidate_id)
        if candidate is None:
            return False

        try:
            await db.delete(candidate)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(
        db: AsyncSession,
        candidate: Candidate,
    ) -> None:
        try:
            await db.commit()
            await db.refresh(candidate)
            await db.refresh(candidate, attribute_names=list(EXPERIENCE_FIELDS))
        except Exception:
            await db.rollback()
            raise


candidate_service = CandidateService()
