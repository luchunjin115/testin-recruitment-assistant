from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.models.rebuilt.job import Job
from app.models.rebuilt.project_experience import ProjectExperience
from app.models.rebuilt.resume import Resume
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.candidate import CandidateCreate, CandidateUpdate


EXPERIENCE_FIELDS = (
    "education_records",
    "work_experiences",
    "project_experiences",
)


class CandidateResumeNotFoundError(ValueError):
    pass


class CandidateResumeAlreadyBoundError(ValueError):
    pass


class CandidateResumeJobConflictError(ValueError):
    pass


class CandidateJobNotFoundError(ValueError):
    pass


class CandidateService:
    async def create_candidate(
        self,
        db: AsyncSession,
        data: CandidateCreate,
    ) -> Candidate:
        candidate = self._build_candidate(data)

        db.add(candidate)
        await self._commit_and_refresh(db, candidate)
        return candidate

    async def create_candidate_from_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        data: CandidateCreate,
    ) -> Candidate:
        statement = select(Resume).where(Resume.id == resume_id).with_for_update()
        resume = await db.scalar(statement)
        if resume is None:
            raise CandidateResumeNotFoundError("待绑定简历不存在")
        if resume.candidate_id is not None:
            raise CandidateResumeAlreadyBoundError("简历已绑定候选人")

        if (
            data.applied_job_id is not None
            and resume.job_id is not None
            and data.applied_job_id != resume.job_id
        ):
            raise CandidateResumeJobConflictError("候选人岗位与简历岗位不一致")

        job_id = data.applied_job_id if data.applied_job_id is not None else resume.job_id
        if job_id is not None and await db.get(Job, job_id) is None:
            raise CandidateJobNotFoundError("岗位不存在")

        candidate = self._build_candidate(
            data,
            overrides={
                "applied_job_id": job_id,
                "resume_file_path": resume.file_path,
                "resume_text": resume.raw_text,
                "parsed_data": resume.parsed_snapshot,
            },
        )

        try:
            db.add(candidate)
            await db.flush()
            resume.candidate_id = candidate.id
            resume.job_id = job_id
            await db.flush()
            await self._refresh_candidate(db, candidate)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
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
    def _build_candidate(
        data: CandidateCreate,
        overrides: dict[str, object] | None = None,
    ) -> Candidate:
        candidate_data = data.model_dump(exclude=set(EXPERIENCE_FIELDS))
        if overrides:
            candidate_data.update(overrides)
        return Candidate(
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

    @staticmethod
    async def _refresh_candidate(db: AsyncSession, candidate: Candidate) -> None:
        await db.refresh(candidate)
        await db.refresh(candidate, attribute_names=list(EXPERIENCE_FIELDS))

    @staticmethod
    async def _commit_and_refresh(
        db: AsyncSession,
        candidate: Candidate,
    ) -> None:
        try:
            await db.commit()
            await CandidateService._refresh_candidate(db, candidate)
        except Exception:
            await db.rollback()
            raise


candidate_service = CandidateService()
