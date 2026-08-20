from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate


class ReportDependencyNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(resource)


class ReportService:
    async def create_report(self, db: AsyncSession, data: ReportCreate) -> Report:
        await self._validate_dependencies(
            db,
            candidate_id=data.candidate_id,
            job_id=data.job_id,
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
    ) -> list[Report]:
        statement = select(Report)
        if candidate_id is not None:
            statement = statement.where(Report.candidate_id == candidate_id)
        if job_id is not None:
            statement = statement.where(Report.job_id == job_id)
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
    ) -> None:
        if await db.get(Candidate, candidate_id) is None:
            raise ReportDependencyNotFoundError("candidate")
        if await db.get(Job, job_id) is None:
            raise ReportDependencyNotFoundError("job")

    @staticmethod
    async def _commit_and_refresh(db: AsyncSession, report: Report) -> None:
        try:
            await db.commit()
            await db.refresh(report)
        except Exception:
            await db.rollback()
            raise


report_service = ReportService()
