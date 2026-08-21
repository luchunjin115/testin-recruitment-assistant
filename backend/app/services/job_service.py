from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.application import Application
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.report import Report
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.schemas.job import (
    JobCreate,
    JobRequirementsV1,
    JobStatus,
    JobUpdate,
)


class JobServiceError(Exception):
    """Base class for expected Job business errors."""


class JobOpenValidationError(JobServiceError):
    def __init__(self, fields: tuple[str, ...]) -> None:
        self.fields = fields
        super().__init__("岗位信息不完整，暂时不能开放")


class InvalidJobStatusTransitionError(JobServiceError):
    def __init__(self, *, action: str, current_status: str) -> None:
        self.action = action
        self.current_status = current_status
        super().__init__(f"岗位当前状态 {current_status!r} 不允许执行 {action!r}")


class JobMustBeClosedBeforeDeleteError(JobServiceError):
    def __init__(self) -> None:
        super().__init__("开放岗位必须先关闭才能删除")


@dataclass(frozen=True)
class JobReferenceCounts:
    candidates: int
    resumes: int
    applications: int
    evaluation_plans: int
    reports: int
    screening_reports: int
    screening_runs: int

    @property
    def total(self) -> int:
        return (
            self.candidates
            + self.resumes
            + self.applications
            + self.evaluation_plans
            + self.reports
            + self.screening_reports
            + self.screening_runs
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "candidates": self.candidates,
            "resumes": self.resumes,
            "applications": self.applications,
            "evaluation_plans": self.evaluation_plans,
            "reports": self.reports,
            "screening_reports": self.screening_reports,
            "screening_runs": self.screening_runs,
        }


class JobHasReferencesError(JobServiceError):
    def __init__(self, references: JobReferenceCounts) -> None:
        self.references = references
        super().__init__("岗位已有历史业务数据，不能删除")


class JobService:
    _EDITABLE_FIELDS = (
        "title",
        "department",
        "location",
        "employment_type",
        "headcount",
        "description",
        "requirements",
    )
    _EMPLOYMENT_TYPES = {"full_time", "part_time", "internship", "contract"}

    async def create_job(self, db: AsyncSession, data: JobCreate) -> Job:
        payload = data.model_dump(mode="json")
        try:
            if payload["status"] == JobStatus.OPEN.value:
                self._ensure_open_valid(payload)

            job = Job(**payload)
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return job
        except Exception:
            await db.rollback()
            raise

    async def get_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await db.get(Job, job_id)

    async def list_jobs(
        self,
        db: AsyncSession,
        status: JobStatus | str | None = None,
    ) -> list[Job]:
        statement = select(Job)
        if status is not None:
            status_value = status.value if isinstance(status, JobStatus) else status
            statement = statement.where(Job.status == status_value)
        statement = statement.order_by(Job.updated_at.desc(), Job.id.desc())
        result = await db.scalars(statement)
        return list(result.all())

    async def update_job(
        self,
        db: AsyncSession,
        job_id: int,
        data: JobUpdate,
    ) -> Job | None:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                return None

            changes = data.model_dump(exclude_unset=True, mode="json")
            current_values = self._job_values(job)
            prospective = dict(current_values)
            prospective.update(changes)
            if self._status_value(job.status) == JobStatus.OPEN.value:
                self._ensure_open_valid(prospective)

            for field, value in changes.items():
                setattr(job, field, value)

            await db.commit()
            await db.refresh(job)
            return job
        except Exception:
            await db.rollback()
            raise

    async def open_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await self._transition_job(
            db,
            job_id,
            action="open",
            expected_status=JobStatus.DRAFT,
            target_status=JobStatus.OPEN,
            validate_open=True,
        )

    async def close_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await self._transition_job(
            db,
            job_id,
            action="close",
            expected_status=JobStatus.OPEN,
            target_status=JobStatus.CLOSED,
            validate_open=False,
        )

    async def reopen_job(self, db: AsyncSession, job_id: int) -> Job | None:
        return await self._transition_job(
            db,
            job_id,
            action="reopen",
            expected_status=JobStatus.CLOSED,
            target_status=JobStatus.OPEN,
            validate_open=True,
        )

    async def get_reference_counts(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobReferenceCounts:
        statement = select(
            select(func.count(Candidate.id))
            .where(Candidate.applied_job_id == job_id)
            .scalar_subquery()
            .label("candidates"),
            select(func.count(Resume.id))
            .where(Resume.job_id == job_id)
            .scalar_subquery()
            .label("resumes"),
            select(func.count(Application.id))
            .where(Application.job_id == job_id)
            .scalar_subquery()
            .label("applications"),
            select(func.count(JobEvaluationPlan.id))
            .where(JobEvaluationPlan.job_id == job_id)
            .scalar_subquery()
            .label("evaluation_plans"),
            select(func.count(Report.id))
            .where(Report.job_id == job_id)
            .scalar_subquery()
            .label("reports"),
            select(func.count(ScreeningReport.id))
            .where(ScreeningReport.job_id == job_id)
            .scalar_subquery()
            .label("screening_reports"),
            select(func.count(ScreeningRun.id))
            .where(ScreeningRun.job_id == job_id)
            .scalar_subquery()
            .label("screening_runs"),
        )
        row = (await db.execute(statement)).one()
        return JobReferenceCounts(
            candidates=int(row.candidates or 0),
            resumes=int(row.resumes or 0),
            applications=int(row.applications or 0),
            evaluation_plans=int(row.evaluation_plans or 0),
            reports=int(row.reports or 0),
            screening_reports=int(row.screening_reports or 0),
            screening_runs=int(row.screening_runs or 0),
        )

    async def delete_job(self, db: AsyncSession, job_id: int) -> bool:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                return False

            if self._status_value(job.status) not in {
                JobStatus.DRAFT.value,
                JobStatus.CLOSED.value,
            }:
                raise JobMustBeClosedBeforeDeleteError()

            references = await self.get_reference_counts(db, job_id)
            if references.total:
                raise JobHasReferencesError(references)

            await db.delete(job)
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise

    def validate_open_job(self, values: Mapping[str, Any]) -> tuple[str, ...]:
        missing: list[str] = []

        for field in ("title", "department", "location"):
            if not self._is_nonempty_text(values.get(field)):
                missing.append(field)

        employment_type = values.get("employment_type")
        employment_value = getattr(employment_type, "value", employment_type)
        if employment_value not in self._EMPLOYMENT_TYPES:
            missing.append("employment_type")

        headcount = values.get("headcount")
        if (
            isinstance(headcount, bool)
            or not isinstance(headcount, int)
            or not 1 <= headcount <= 999
        ):
            missing.append("headcount")

        if not self._is_nonempty_text(values.get("description")):
            missing.append("description")

        requirements_value = values.get("requirements")
        if isinstance(requirements_value, JobRequirementsV1):
            requirements = requirements_value
        else:
            try:
                requirements = JobRequirementsV1.model_validate(requirements_value)
            except ValidationError:
                missing.append("requirements")
                return tuple(missing)

        if not requirements.responsibilities:
            missing.append("requirements.responsibilities")
        if not requirements.required_skills:
            missing.append("requirements.required_skills")
        if requirements.minimum_work_years is None:
            missing.append("requirements.minimum_work_years")
        if requirements.education_requirement is None:
            missing.append("requirements.education_requirement")

        return tuple(missing)

    async def _transition_job(
        self,
        db: AsyncSession,
        job_id: int,
        *,
        action: str,
        expected_status: JobStatus,
        target_status: JobStatus,
        validate_open: bool,
    ) -> Job | None:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                return None

            current_status = self._status_value(job.status)
            if current_status != expected_status.value:
                raise InvalidJobStatusTransitionError(
                    action=action,
                    current_status=current_status,
                )
            if validate_open:
                self._ensure_open_valid(self._job_values(job))

            job.status = target_status.value
            await db.commit()
            await db.refresh(job)
            return job
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def _get_job_for_update(db: AsyncSession, job_id: int) -> Job | None:
        statement = select(Job).where(Job.id == job_id).with_for_update()
        return await db.scalar(statement)

    def _ensure_open_valid(self, values: Mapping[str, Any]) -> None:
        fields = self.validate_open_job(values)
        if fields:
            raise JobOpenValidationError(fields)

    def _job_values(self, job: Job) -> dict[str, Any]:
        return {field: getattr(job, field) for field in self._EDITABLE_FIELDS}

    @staticmethod
    def _is_nonempty_text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _status_value(value: Any) -> str:
        return str(getattr(value, "value", value))


job_service = JobService()
