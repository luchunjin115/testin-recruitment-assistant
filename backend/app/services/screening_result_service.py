from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening_result import ScreeningResult


class ScreeningResultService:
    async def get_screening_result(
        self,
        db: AsyncSession,
        screening_result_id: int,
    ) -> ScreeningResult | None:
        statement = select(ScreeningResult).where(
            ScreeningResult.id == screening_result_id,
            ScreeningResult.application_id.is_not(None),
            ScreeningResult.resume_id.is_not(None),
        )
        return await db.scalar(statement)

    async def list_screening_results(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
        job_id: int | None = None,
        application_id: int | None = None,
    ) -> list[ScreeningResult]:
        statement = select(ScreeningResult).where(
            ScreeningResult.application_id.is_not(None),
            ScreeningResult.resume_id.is_not(None),
        )
        if candidate_id is not None:
            statement = statement.where(ScreeningResult.candidate_id == candidate_id)
        if job_id is not None:
            statement = statement.where(ScreeningResult.job_id == job_id)
        if application_id is not None:
            statement = statement.where(
                ScreeningResult.application_id == application_id
            )
        statement = statement.order_by(
            ScreeningResult.attempt_number.desc()
            if application_id is not None
            else ScreeningResult.updated_at.desc(),
            ScreeningResult.id.desc(),
        )
        result = await db.scalars(statement)
        return list(result.all())


screening_result_service = ScreeningResultService()
