from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.schemas.application import normalize_application_email, normalize_application_phone
from app.schemas.public_application import ApplicationProcessingStatus
from app.schemas.public_application_workbench import (
    PublicApplicationIdentityCandidate,
    PublicApplicationPool,
    PublicApplicationProcessingRunSummary,
    PublicApplicationWorkbenchDetail,
    PublicApplicationWorkbenchSummary,
)
from app.services.application_intake_service import LOCAL_HR_ACTOR_LABEL
from app.services.application_processing_service import application_processing_service


class PublicApplicationWorkbenchError(RuntimeError):
    pass


class PublicApplicationWorkbenchSubmissionNotFoundError(PublicApplicationWorkbenchError):
    pass


class PublicApplicationIdentityReviewNotRequiredError(PublicApplicationWorkbenchError):
    pass


_NORMAL_STATUSES = (
    ApplicationProcessingStatus.QUEUED.value,
    ApplicationProcessingStatus.RUNNING.value,
    ApplicationProcessingStatus.WAITING_SCREENING.value,
    ApplicationProcessingStatus.SUCCEEDED.value,
)
_EXCEPTION_STATUSES = (
    ApplicationProcessingStatus.FAILED.value,
    ApplicationProcessingStatus.PAUSED.value,
    ApplicationProcessingStatus.SUCCEEDED_WITH_WARNINGS.value,
)


class PublicApplicationWorkbenchService:
    async def list_submissions(
        self,
        db: AsyncSession,
        *,
        pool: PublicApplicationPool = PublicApplicationPool.ALL,
        job_id: int | None = None,
        processing_status: ApplicationProcessingStatus | None = None,
    ) -> list[PublicApplicationWorkbenchSummary]:
        statement = self._summary_statement()
        if job_id is not None:
            statement = statement.where(Application.job_id == job_id)
        if processing_status is not None:
            statement = statement.where(
                ApplicationProcessingRun.status == processing_status.value
            )
        if pool is PublicApplicationPool.NORMAL:
            statement = statement.where(
                PublicApplicationSubmission.identity_review_status != "needs_review",
                ApplicationProcessingRun.status.in_(_NORMAL_STATUSES),
            )
        elif pool is PublicApplicationPool.EXCEPTION:
            statement = statement.where(
                or_(
                    PublicApplicationSubmission.identity_review_status == "needs_review",
                    ApplicationProcessingRun.status.in_(_EXCEPTION_STATUSES),
                )
            )
        statement = statement.order_by(
            PublicApplicationSubmission.created_at.desc(),
            PublicApplicationSubmission.id.desc(),
        )
        rows = (await db.execute(statement)).all()
        return [self._summary_from_row(row) for row in rows]

    async def get_submission(
        self,
        db: AsyncSession,
        submission_id: int,
    ) -> PublicApplicationWorkbenchDetail:
        row = (
            await db.execute(
                self._summary_statement().where(
                    PublicApplicationSubmission.id == submission_id
                )
            )
        ).one_or_none()
        if row is None:
            raise PublicApplicationWorkbenchSubmissionNotFoundError(
                "公开投递不存在"
            )
        summary = self._summary_from_row(row)
        runs = list(
            (
                await db.scalars(
                    select(ApplicationProcessingRun)
                    .where(ApplicationProcessingRun.submission_id == submission_id)
                    .order_by(
                        ApplicationProcessingRun.created_at.desc(),
                        ApplicationProcessingRun.id.desc(),
                    )
                )
            ).all()
        )
        candidates = await self._identity_candidates(
            db,
            submission_candidate=row.Candidate,
            reasons=list(row.PublicApplicationSubmission.identity_review_reasons or []),
        )
        return PublicApplicationWorkbenchDetail(
            **summary.model_dump(),
            processing_runs=[self._run_summary(run) for run in runs],
            identity_candidates=candidates,
        )

    async def mark_identity_reviewed(
        self,
        db: AsyncSession,
        submission_id: int,
    ) -> PublicApplicationWorkbenchDetail:
        try:
            submission = await db.scalar(
                select(PublicApplicationSubmission)
                .where(PublicApplicationSubmission.id == submission_id)
                .with_for_update()
            )
            if submission is None:
                raise PublicApplicationWorkbenchSubmissionNotFoundError(
                    "公开投递不存在"
                )
            if submission.identity_review_status == "clear":
                raise PublicApplicationIdentityReviewNotRequiredError(
                    "当前投递不需要身份核对"
                )
            if submission.identity_review_status == "reviewed":
                await db.rollback()
                return await self.get_submission(db, submission_id)

            submission.identity_review_status = "reviewed"
            db.add(
                ActivityLog(
                    user_id=None,
                    action="public_application_identity_reviewed",
                    target_type="public_application_submission",
                    target_id=submission.id,
                    detail={
                        "identity_review_reasons": list(
                            submission.identity_review_reasons or []
                        ),
                        "actor_type": "hr",
                        "actor_label": LOCAL_HR_ACTOR_LABEL,
                    },
                )
            )
            await db.commit()
            return await self.get_submission(db, submission_id)
        except Exception:
            await db.rollback()
            raise

    async def create_manual_retry(
        self,
        db: AsyncSession,
        submission_id: int,
    ) -> PublicApplicationProcessingRunSummary:
        run = await application_processing_service.create_manual_retry(
            db,
            submission_id,
        )
        return self._run_summary(run)

    @staticmethod
    def _summary_statement():
        latest_run_id = (
            select(ApplicationProcessingRun.id)
            .where(
                ApplicationProcessingRun.submission_id
                == PublicApplicationSubmission.id
            )
            .order_by(
                ApplicationProcessingRun.created_at.desc(),
                ApplicationProcessingRun.id.desc(),
            )
            .limit(1)
            .correlate(PublicApplicationSubmission)
            .scalar_subquery()
        )
        return (
            select(
                PublicApplicationSubmission,
                Application,
                Candidate,
                Job,
                Resume,
                ApplicationProcessingRun,
            )
            .join(Application, Application.id == PublicApplicationSubmission.application_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(Job, Job.id == Application.job_id)
            .join(Resume, Resume.id == PublicApplicationSubmission.resume_id)
            .join(ApplicationProcessingRun, ApplicationProcessingRun.id == latest_run_id)
        )

    @classmethod
    def _summary_from_row(cls, row) -> PublicApplicationWorkbenchSummary:
        submission = row.PublicApplicationSubmission
        application = row.Application
        candidate = row.Candidate
        job = row.Job
        resume = row.Resume
        return PublicApplicationWorkbenchSummary(
            submission_id=submission.id,
            submission_reference=submission.submission_reference,
            submitted_at=submission.created_at,
            identity_review_status=submission.identity_review_status,
            identity_review_reasons=list(submission.identity_review_reasons or []),
            application_id=application.id,
            candidate_id=candidate.id,
            resume_id=resume.id,
            job_id=job.id,
            candidate_name=candidate.name,
            job_title=job.title,
            job_status=job.status,
            resume_filename=resume.filename,
            resume_parse_status=resume.parse_status,
            lifecycle_status=application.lifecycle_status,
            recruitment_stage=application.recruitment_stage,
            hr_decision=application.hr_decision,
            latest_run=cls._run_summary(row.ApplicationProcessingRun),
        )

    @staticmethod
    def _run_summary(
        run: ApplicationProcessingRun,
    ) -> PublicApplicationProcessingRunSummary:
        return PublicApplicationProcessingRunSummary(
            id=run.id,
            trigger_type=run.trigger_type,
            status=run.status,
            current_step=run.current_step,
            attempt_count=run.attempt_count,
            waiting_reason=run.waiting_reason,
            error_code=run.error_code,
            error_message=run.error_message,
            warning_codes=list(run.warning_codes or []),
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    async def _identity_candidates(
        self,
        db: AsyncSession,
        *,
        submission_candidate: Candidate,
        reasons: list[str],
    ) -> list[PublicApplicationIdentityCandidate]:
        if not reasons:
            return []
        conditions = [Candidate.id == submission_candidate.id]
        if "same_name" in reasons:
            conditions.append(
                func.btrim(Candidate.name) == submission_candidate.name.strip()
            )
        if "contact_conflict" in reasons:
            phone = self._normalized_phone(submission_candidate.phone)
            email = self._normalized_email(submission_candidate.email)
            contact_conditions = []
            if phone is not None:
                contact_conditions.append(
                    func.regexp_replace(
                        func.coalesce(Candidate.phone, ""),
                        r"[\s()\-]",
                        "",
                        "g",
                    )
                    == phone
                )
            if email is not None:
                contact_conditions.append(
                    func.lower(func.btrim(func.coalesce(Candidate.email, "")))
                    == email
                )
            if contact_conditions:
                conditions.append(or_(*contact_conditions))
        result = await db.scalars(
            select(Candidate)
            .where(or_(*conditions))
            .order_by(Candidate.id)
        )
        return [
            PublicApplicationIdentityCandidate(
                id=candidate.id,
                name=candidate.name,
                phone=candidate.phone,
                email=candidate.email,
                source=candidate.source,
                created_at=candidate.created_at,
                is_submission_candidate=candidate.id == submission_candidate.id,
            )
            for candidate in result.unique().all()
        ]

    @staticmethod
    def _normalized_phone(value: str | None) -> str | None:
        try:
            result = normalize_application_phone(value)
        except ValueError:
            return None
        return result if isinstance(result, str) else None

    @staticmethod
    def _normalized_email(value: str | None) -> str | None:
        try:
            result = normalize_application_email(value)
        except ValueError:
            return None
        return result if isinstance(result, str) else None


public_application_workbench_service = PublicApplicationWorkbenchService()


__all__ = [
    "PublicApplicationIdentityReviewNotRequiredError",
    "PublicApplicationWorkbenchError",
    "PublicApplicationWorkbenchService",
    "PublicApplicationWorkbenchSubmissionNotFoundError",
    "public_application_workbench_service",
]
