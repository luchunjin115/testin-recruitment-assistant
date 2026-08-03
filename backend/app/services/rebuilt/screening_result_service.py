from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.job import Job
from app.models.rebuilt.screening_result import ScreeningResult
from app.schemas.rebuilt.screening_result import (
    ScreeningResultCreate,
    ScreeningResultUpdate,
)


class ScreeningResultDependencyNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(resource)


class ScreeningResultAlreadyExistsError(Exception):
    pass


class ScreeningResultService:
    async def create_screening_result(
        self,
        db: AsyncSession,
        data: ScreeningResultCreate,
    ) -> ScreeningResult:
        if await db.get(Candidate, data.candidate_id) is None:
            raise ScreeningResultDependencyNotFoundError("candidate")
        if await db.get(Job, data.job_id) is None:
            raise ScreeningResultDependencyNotFoundError("job")

        duplicate_statement = select(ScreeningResult.id).where(
            ScreeningResult.candidate_id == data.candidate_id,
            ScreeningResult.job_id == data.job_id,
        )
        if await db.scalar(duplicate_statement) is not None:
            raise ScreeningResultAlreadyExistsError

        screening_result = ScreeningResult(**data.model_dump())
        db.add(screening_result)
        await self._commit_and_refresh(db, screening_result)
        return screening_result

    async def get_screening_result(
        self,
        db: AsyncSession,
        screening_result_id: int,
    ) -> ScreeningResult | None:
        return await db.get(ScreeningResult, screening_result_id)

    async def list_screening_results(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
        job_id: int | None = None,
    ) -> list[ScreeningResult]:
        statement = select(ScreeningResult)
        if candidate_id is not None:
            statement = statement.where(ScreeningResult.candidate_id == candidate_id)
        if job_id is not None:
            statement = statement.where(ScreeningResult.job_id == job_id)
        statement = statement.order_by(
            ScreeningResult.updated_at.desc(),
            ScreeningResult.id.desc(),
        )
        result = await db.scalars(statement)
        return list(result.all())

    async def update_screening_result(
        self,
        db: AsyncSession,
        screening_result_id: int,
        data: ScreeningResultUpdate,
    ) -> ScreeningResult | None:
        screening_result = await self.get_screening_result(db, screening_result_id)
        if screening_result is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(screening_result, field, value)

        await self._commit_and_refresh(db, screening_result)
        return screening_result

    async def delete_screening_result(
        self,
        db: AsyncSession,
        screening_result_id: int,
    ) -> bool:
        screening_result = await self.get_screening_result(db, screening_result_id)
        if screening_result is None:
            return False

        try:
            await db.delete(screening_result)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    @staticmethod
    async def _commit_and_refresh(
        db: AsyncSession,
        screening_result: ScreeningResult,
    ) -> None:
        try:
            await db.commit()
            await db.refresh(screening_result)
        except IntegrityError as exc:
            await db.rollback()
            raise ScreeningResultAlreadyExistsError from exc
        except Exception:
            await db.rollback()
            raise


screening_result_service = ScreeningResultService()
