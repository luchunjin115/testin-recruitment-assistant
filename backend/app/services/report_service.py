from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.report import Report
from app.models.screening_result import ScreeningResult
from app.schemas.report import ReportCreate, ReportUpdate


class ReportDependencyNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(resource)


class ReportScreeningMismatchError(Exception):
    pass


class ReportService:
    async def create_report(self, db: AsyncSession, data: ReportCreate) -> Report:
        await self._validate_dependencies(
            db,
            candidate_id=data.candidate_id,
            job_id=data.job_id,
            screening_id=data.screening_id,
        )
        report = Report(**data.model_dump())
        db.add(report)
        await self._commit_and_refresh(db, report)
        return report

    async def get_report(self, db: AsyncSession, report_id: int) -> Report | None:
        return await db.get(Report, report_id)

    async def list_reports(
        self,
        db: AsyncSession,
        candidate_id: int | None = None,
        job_id: int | None = None,
        screening_id: int | None = None,
    ) -> list[Report]:
        statement = select(Report)
        if candidate_id is not None:
            statement = statement.where(Report.candidate_id == candidate_id)
        if job_id is not None:
            statement = statement.where(Report.job_id == job_id)
        if screening_id is not None:
            statement = statement.where(Report.screening_id == screening_id)
        statement = statement.order_by(Report.updated_at.desc(), Report.id.desc())
        result = await db.scalars(statement)
        return list(result.all())

    async def update_report(
        self,
        db: AsyncSession,
        report_id: int,
        data: ReportUpdate,
    ) -> Report | None:
        report = await self.get_report(db, report_id)
        if report is None:
            return None

        if "screening_id" in data.model_fields_set and data.screening_id is not None:
            await self._validate_screening(
                db,
                screening_id=data.screening_id,
                candidate_id=report.candidate_id,
                job_id=report.job_id,
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(report, field, value)

        await self._commit_and_refresh(db, report)
        return report

    async def delete_report(self, db: AsyncSession, report_id: int) -> bool:
        report = await self.get_report(db, report_id)
        if report is None:
            return False

        try:
            await db.delete(report)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return True

    async def _validate_dependencies(
        self,
        db: AsyncSession,
        candidate_id: int,
        job_id: int,
        screening_id: int | None,
    ) -> None:
        if await db.get(Candidate, candidate_id) is None:
            raise ReportDependencyNotFoundError("candidate")
        if await db.get(Job, job_id) is None:
            raise ReportDependencyNotFoundError("job")
        if screening_id is not None:
            await self._validate_screening(db, screening_id, candidate_id, job_id)

    @staticmethod
    async def _validate_screening(
        db: AsyncSession,
        screening_id: int,
        candidate_id: int,
        job_id: int,
    ) -> None:
        screening_result = await db.get(ScreeningResult, screening_id)
        if screening_result is None:
            raise ReportDependencyNotFoundError("screening_result")
        if (
            screening_result.candidate_id != candidate_id
            or screening_result.job_id != job_id
        ):
            raise ReportScreeningMismatchError

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, report: Report) -> None:
        try:
            await db.commit()
            await db.refresh(report)
        except Exception:
            await db.rollback()
            raise


report_service = ReportService()
