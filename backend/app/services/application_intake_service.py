from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.application import (
    ApplicationIntakeRequest,
    ApplicationSource,
    CandidateResolution,
    normalize_application_email,
    normalize_application_phone,
)
from app.schemas.stage_history import StageHistoryReasonCode


LOCAL_HR_ACTOR_LABEL = "本地 HR（未认证）"
ACTIVE_APPLICATION_UNIQUE_CONSTRAINT = "uq_applications_active_candidate_job"


class ApplicationIntakeError(ValueError):
    pass


class ApplicationCandidateNotFoundError(ApplicationIntakeError):
    pass


class ApplicationContactIdentityConflictError(ApplicationIntakeError):
    def __init__(self, candidate_ids: tuple[int, ...]) -> None:
        super().__init__("手机号和邮箱无法安全识别为同一个 Candidate")
        self.candidate_ids = candidate_ids


class ApplicationJobNotOpenError(ApplicationIntakeError):
    pass


class ApplicationResumeNotFoundError(ApplicationIntakeError):
    pass


class ApplicationResumeOwnershipConflictError(ApplicationIntakeError):
    pass


@dataclass(frozen=True)
class ApplicationIntakeResult:
    application: Application
    candidate_resolution: CandidateResolution
    existing_application_reused: bool
    suspected_duplicate_candidate_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class _CandidateResolutionResult:
    candidate: Candidate
    resolution: CandidateResolution
    suspected_duplicate_candidate_ids: tuple[int, ...]


class ApplicationIntakeService:
    async def intake(
        self,
        db: AsyncSession,
        data: ApplicationIntakeRequest,
    ) -> ApplicationIntakeResult:
        candidate_id: int | None = None
        candidate_resolution = CandidateResolution.REUSED
        suspected_duplicate_candidate_ids: tuple[int, ...] = ()

        try:
            await self._lock_contact_identity(db, data.phone, data.email)
            job = await self._get_open_job_for_update(db, data.job_id)
            if job is None:
                raise ApplicationJobNotOpenError("岗位不存在或当前不是 open 状态")

            resume = await self._get_resume_for_update(db, data.current_resume_id)
            if resume is None:
                raise ApplicationResumeNotFoundError("当前简历不存在")

            resolved = await self._resolve_candidate(db, data, resume)
            candidate = resolved.candidate
            candidate_resolution = resolved.resolution
            suspected_duplicate_candidate_ids = resolved.suspected_duplicate_candidate_ids
            candidate_id = candidate.id

            if resume.candidate_id not in {None, candidate.id}:
                raise ApplicationResumeOwnershipConflictError(
                    "当前简历已绑定其他 Candidate"
                )

            existing = await self._get_active_application_for_update(
                db,
                candidate.id,
                job.id,
            )
            if existing is not None:
                await db.commit()
                return ApplicationIntakeResult(
                    application=existing,
                    candidate_resolution=candidate_resolution,
                    existing_application_reused=True,
                    suspected_duplicate_candidate_ids=suspected_duplicate_candidate_ids,
                )

            if resume.candidate_id is None:
                resume.candidate_id = candidate.id

            application = self._build_application(data, candidate.id)
            db.add(application)
            await db.flush()
            db.add(self._build_initial_history(application, data.source))
            await db.flush()
            await db.commit()
            await db.refresh(application)
            return ApplicationIntakeResult(
                application=application,
                candidate_resolution=candidate_resolution,
                existing_application_reused=False,
                suspected_duplicate_candidate_ids=suspected_duplicate_candidate_ids,
            )
        except IntegrityError as exc:
            await db.rollback()
            if (
                candidate_id is not None
                and self._constraint_name(exc) == ACTIVE_APPLICATION_UNIQUE_CONSTRAINT
            ):
                existing = await self._get_active_application_for_update(
                    db,
                    candidate_id,
                    data.job_id,
                )
                if existing is not None:
                    await db.commit()
                    return ApplicationIntakeResult(
                        application=existing,
                        candidate_resolution=candidate_resolution,
                        existing_application_reused=True,
                        suspected_duplicate_candidate_ids=suspected_duplicate_candidate_ids,
                    )
            raise
        except Exception:
            await db.rollback()
            raise

    async def _resolve_candidate(
        self,
        db: AsyncSession,
        data: ApplicationIntakeRequest,
        resume: Resume,
    ) -> _CandidateResolutionResult:
        matching_candidates = await self._find_contact_matches(db, data.phone, data.email)
        matching_ids = tuple(sorted({candidate.id for candidate in matching_candidates}))

        if data.candidate_id is not None:
            candidate = await self._get_candidate_for_update(db, data.candidate_id)
            if candidate is None:
                raise ApplicationCandidateNotFoundError("指定的 Candidate 不存在")
            if not self._candidate_contacts_match(candidate, data.phone, data.email):
                conflict_ids = tuple(sorted({*matching_ids, candidate.id}))
                raise ApplicationContactIdentityConflictError(conflict_ids)
            if any(item.id != candidate.id for item in matching_candidates):
                raise ApplicationContactIdentityConflictError(matching_ids)
            return _CandidateResolutionResult(
                candidate=candidate,
                resolution=CandidateResolution.REUSED,
                suspected_duplicate_candidate_ids=(),
            )

        phone_matches = {
            candidate.id
            for candidate in matching_candidates
            if self._normalized_stored_phone(candidate.phone) == data.phone
        }
        email_matches = {
            candidate.id
            for candidate in matching_candidates
            if self._normalized_stored_email(candidate.email) == data.email
        }
        if len(phone_matches) == 1 and phone_matches == email_matches:
            matched_id = next(iter(phone_matches))
            candidate = next(item for item in matching_candidates if item.id == matched_id)
            return _CandidateResolutionResult(
                candidate=candidate,
                resolution=CandidateResolution.REUSED,
                suspected_duplicate_candidate_ids=(),
            )
        if phone_matches or email_matches:
            raise ApplicationContactIdentityConflictError(matching_ids)

        suspected_ids = await self._find_same_name_candidate_ids(db, data.name)
        candidate = Candidate(
            name=data.name,
            phone=data.phone,
            email=data.email,
            source=data.source.value,
            status=("passed" if data.source is ApplicationSource.HR_DIRECT else "new"),
            applied_job_id=data.job_id,
            resume_file_path=resume.file_path,
            resume_text=resume.raw_text,
            parsed_data=resume.parsed_snapshot,
        )
        db.add(candidate)
        await db.flush()
        return _CandidateResolutionResult(
            candidate=candidate,
            resolution=CandidateResolution.CREATED,
            suspected_duplicate_candidate_ids=suspected_ids,
        )

    @staticmethod
    async def _lock_contact_identity(
        db: AsyncSession,
        phone: str,
        email: str,
    ) -> None:
        for lock_key in sorted({f"email:{email}", f"phone:{phone}"}):
            statement = select(
                func.pg_advisory_xact_lock(func.hashtextextended(lock_key, 0))
            )
            await db.execute(statement)

    @staticmethod
    async def _get_open_job_for_update(db: AsyncSession, job_id: int) -> Job | None:
        statement = (
            select(Job)
            .where(Job.id == job_id, Job.status == "open")
            .with_for_update()
        )
        return await db.scalar(statement)

    @staticmethod
    async def _get_resume_for_update(db: AsyncSession, resume_id: int) -> Resume | None:
        statement = select(Resume).where(Resume.id == resume_id).with_for_update()
        return await db.scalar(statement)

    @staticmethod
    async def _get_candidate_for_update(
        db: AsyncSession,
        candidate_id: int,
    ) -> Candidate | None:
        statement = select(Candidate).where(Candidate.id == candidate_id).with_for_update()
        return await db.scalar(statement)

    async def _find_contact_matches(
        self,
        db: AsyncSession,
        phone: str,
        email: str,
    ) -> list[Candidate]:
        normalized_phone = func.regexp_replace(
            func.coalesce(Candidate.phone, ""),
            r"[\s()\-]",
            "",
            "g",
        )
        normalized_email = func.lower(func.btrim(func.coalesce(Candidate.email, "")))
        statement = (
            select(Candidate)
            .where(or_(normalized_phone == phone, normalized_email == email))
            .order_by(Candidate.id)
            .with_for_update()
        )
        result = await db.scalars(statement)
        return list(result.unique().all())

    @staticmethod
    async def _find_same_name_candidate_ids(
        db: AsyncSession,
        name: str,
    ) -> tuple[int, ...]:
        statement = (
            select(Candidate.id)
            .where(func.btrim(Candidate.name) == name)
            .order_by(Candidate.id)
        )
        result = await db.scalars(statement)
        return tuple(result.all())

    @staticmethod
    async def _get_active_application_for_update(
        db: AsyncSession,
        candidate_id: int,
        job_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(
                Application.candidate_id == candidate_id,
                Application.job_id == job_id,
                Application.lifecycle_status == "active",
            )
            .with_for_update()
        )
        return await db.scalar(statement)

    @staticmethod
    def _build_application(
        data: ApplicationIntakeRequest,
        candidate_id: int,
    ) -> Application:
        if data.source is ApplicationSource.HR_DIRECT:
            recruitment_stage = "screening_passed"
            hr_decision = "passed"
        else:
            recruitment_stage = "applied"
            hr_decision = "pending"
        return Application(
            candidate_id=candidate_id,
            job_id=data.job_id,
            current_resume_id=data.current_resume_id,
            source=data.source.value,
            lifecycle_status="active",
            recruitment_stage=recruitment_stage,
            ai_status="not_started",
            hr_decision=hr_decision,
        )

    @staticmethod
    def _build_initial_history(
        application: Application,
        source: ApplicationSource,
    ) -> StageHistory:
        reason_code = (
            StageHistoryReasonCode.HR_DIRECT_ENTRY.value
            if source is ApplicationSource.HR_DIRECT
            else StageHistoryReasonCode.APPLICATION_CREATED.value
        )
        return StageHistory(
            application_id=application.id,
            from_recruitment_stage=None,
            to_recruitment_stage=application.recruitment_stage,
            from_hr_decision=None,
            to_hr_decision=application.hr_decision,
            reason_code=reason_code,
            actor_type="hr",
            actor_id=None,
            actor_label=LOCAL_HR_ACTOR_LABEL,
            screening_result_id=None,
            overrides_ai_recommendation=False,
        )

    @staticmethod
    def _normalized_stored_phone(value: Any) -> str | None:
        try:
            normalized = normalize_application_phone(value)
        except ValueError:
            return None
        return normalized if isinstance(normalized, str) else None

    @staticmethod
    def _normalized_stored_email(value: Any) -> str | None:
        try:
            normalized = normalize_application_email(value)
        except ValueError:
            return None
        return normalized if isinstance(normalized, str) else None

    @staticmethod
    def _candidate_contacts_match(
        candidate: Candidate,
        phone: str,
        email: str,
    ) -> bool:
        return (
            ApplicationIntakeService._normalized_stored_phone(candidate.phone) == phone
            and ApplicationIntakeService._normalized_stored_email(candidate.email) == email
        )

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        original = getattr(exc, "orig", None)
        direct_name = getattr(original, "constraint_name", None)
        if isinstance(direct_name, str):
            return direct_name
        diagnostic = getattr(original, "diag", None)
        name = getattr(diagnostic, "constraint_name", None)
        return name if isinstance(name, str) else None


application_intake_service = ApplicationIntakeService()
