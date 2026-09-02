from __future__ import annotations

import hashlib
import json
import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.models.stage_history import StageHistory
from app.schemas.application import normalize_application_email, normalize_application_phone
from app.schemas.public_application import (
    PublicApplicationForm,
    PublicApplicationIdentityReviewReason,
)
from app.schemas.stage_history import StageHistoryReasonCode
from app.services.resume_storage import PreparedResumeFile, ResumeFileStorage, ResumeStorageError


logger = logging.getLogger(__name__)
PUBLIC_APPLICATION_ACTOR_LABEL = "候选人公开投递（系统受理）"
REFERENCE_ALPHABET = string.ascii_uppercase + string.digits


class PublicApplicationServiceError(RuntimeError):
    pass


class PublicApplicationIdempotencyConflictError(PublicApplicationServiceError):
    pass


class PublicApplicationJobNotOpenError(PublicApplicationServiceError):
    pass


class PublicApplicationReviewRequiredError(PublicApplicationServiceError):
    pass


class PublicApplicationSaveError(PublicApplicationServiceError):
    pass


class PublicApplicationInfrastructureUnavailableError(PublicApplicationServiceError):
    pass


@dataclass(frozen=True)
class PublicApplicationAcceptance:
    submission_reference: str
    accepted_at: datetime
    reused: bool


@dataclass(frozen=True)
class _CandidateResolution:
    candidate: Candidate
    review_reasons: tuple[PublicApplicationIdentityReviewReason, ...]


class PublicApplicationService:
    async def accept(
        self,
        db: AsyncSession,
        data: PublicApplicationForm,
        prepared: PreparedResumeFile,
        *,
        storage: ResumeFileStorage,
    ) -> PublicApplicationAcceptance:
        idempotency_hash = self._sha256_text(str(data.idempotency_key))
        request_fingerprint = self._request_fingerprint(data, prepared)

        try:
            await self._lock(db, f"public-idempotency:{idempotency_hash}")
            same_key = await self._get_submission_by_idempotency_hash(
                db,
                idempotency_hash,
            )
            if same_key is not None:
                if same_key.request_fingerprint != request_fingerprint:
                    raise PublicApplicationIdempotencyConflictError()
                result = self._acceptance(same_key, reused=True)
                await db.rollback()
                self._discard_safely(storage, prepared)
                return result

            await self._lock_contact_identity(db, data.phone, data.email)
            await self._lock(db, f"name:{data.name}")
            job = await self._get_open_job_for_update(db, data.job_id)
            if job is None:
                raise PublicApplicationJobNotOpenError()

            resolution = await self._resolve_candidate(db, data)
            applications = await self._get_candidate_job_applications_for_update(
                db,
                resolution.candidate.id,
                job.id,
            )
            active_application = next(
                (
                    application
                    for application in applications
                    if application.lifecycle_status == "active"
                ),
                None,
            )
            if any(
                application.lifecycle_status in {"ended", "voided"}
                for application in applications
            ):
                raise PublicApplicationReviewRequiredError()
            if active_application is not None:
                existing_submission = await self._get_submission_for_application(
                    db,
                    active_application.id,
                )
                if existing_submission is not None:
                    result = self._acceptance(existing_submission, reused=True)
                    await db.rollback()
                    self._discard_safely(storage, prepared)
                    return result

            resume = Resume(
                candidate_id=resolution.candidate.id,
                job_id=job.id,
                filename=prepared.original_filename,
                file_path=prepared.relative_path,
                file_type=prepared.mime_type,
                file_size=prepared.file_size,
                parse_status="uploaded",
                structure_status="not_started",
            )
            db.add(resume)
            await db.flush()

            application = active_application
            if application is None:
                application = Application(
                    candidate_id=resolution.candidate.id,
                    job_id=job.id,
                    current_resume_id=resume.id,
                    source="public_apply",
                    lifecycle_status="active",
                    recruitment_stage="applied",
                    hr_decision="pending",
                    final_outcome=None,
                )
                db.add(application)
                await db.flush()
                db.add(
                    StageHistory(
                        application_id=application.id,
                        from_lifecycle_status=None,
                        to_lifecycle_status="active",
                        from_recruitment_stage=None,
                        to_recruitment_stage="applied",
                        from_hr_decision=None,
                        to_hr_decision="pending",
                        from_final_outcome=None,
                        to_final_outcome=None,
                        reason_code=(
                            StageHistoryReasonCode.PUBLIC_APPLICATION_RECEIVED.value
                        ),
                        actor_type="system",
                        actor_id=None,
                        actor_label=PUBLIC_APPLICATION_ACTOR_LABEL,
                    )
                )

            now = datetime.now(timezone.utc)
            review_reasons = [reason.value for reason in resolution.review_reasons]
            submission = PublicApplicationSubmission(
                application_id=application.id,
                resume_id=resume.id,
                submission_reference=self._new_submission_reference(),
                idempotency_key_hash=idempotency_hash,
                request_fingerprint=request_fingerprint,
                consent_version=data.consent_version,
                consented_at=now,
                identity_review_status=("needs_review" if review_reasons else "clear"),
                identity_review_reasons=review_reasons,
            )
            db.add(submission)
            await db.flush()
            db.add(
                ApplicationProcessingRun(
                    submission_id=submission.id,
                    application_id=application.id,
                    resume_id=resume.id,
                    trigger_type="automatic",
                    status="queued",
                    current_step="extract_text",
                    attempt_count=0,
                    warning_codes=[],
                )
            )
            await db.flush()

            storage.promote(prepared)
            await db.commit()
            return PublicApplicationAcceptance(
                submission_reference=submission.submission_reference,
                accepted_at=now,
                reused=False,
            )
        except (
            PublicApplicationIdempotencyConflictError,
            PublicApplicationJobNotOpenError,
            PublicApplicationReviewRequiredError,
        ):
            await db.rollback()
            self._discard_safely(storage, prepared)
            raise
        except OperationalError as exc:
            await db.rollback()
            self._discard_safely(storage, prepared)
            raise PublicApplicationInfrastructureUnavailableError() from exc
        except Exception as exc:
            await db.rollback()
            self._discard_safely(storage, prepared)
            raise PublicApplicationSaveError() from exc

    async def _resolve_candidate(
        self,
        db: AsyncSession,
        data: PublicApplicationForm,
    ) -> _CandidateResolution:
        matches = await self._find_contact_matches(db, data.phone, data.email)
        phone_matches = {
            candidate.id
            for candidate in matches
            if self._normalized_phone(candidate.phone) == data.phone
        }
        email_matches = {
            candidate.id
            for candidate in matches
            if self._normalized_email(candidate.email) == data.email
        }
        exact_matches = phone_matches & email_matches
        if len(exact_matches) == 1:
            candidate_id = next(iter(exact_matches))
            candidate = next(item for item in matches if item.id == candidate_id)
            return _CandidateResolution(candidate=candidate, review_reasons=())

        if phone_matches or email_matches:
            reasons = (PublicApplicationIdentityReviewReason.CONTACT_CONFLICT,)
        else:
            same_name_exists = await self._same_name_exists(db, data.name)
            reasons = (
                (PublicApplicationIdentityReviewReason.SAME_NAME,)
                if same_name_exists
                else ()
            )

        candidate = Candidate(
            name=data.name,
            phone=data.phone,
            email=data.email,
            source="public_apply",
            status="new",
        )
        db.add(candidate)
        await db.flush()
        return _CandidateResolution(candidate=candidate, review_reasons=reasons)

    @staticmethod
    async def _lock(db: AsyncSession, key: str) -> None:
        await db.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(key, 0)))
        )

    async def _lock_contact_identity(
        self,
        db: AsyncSession,
        phone: str,
        email: str,
    ) -> None:
        for key in sorted({f"email:{email}", f"phone:{phone}"}):
            await self._lock(db, key)

    @staticmethod
    async def _get_open_job_for_update(db: AsyncSession, job_id: int) -> Job | None:
        return await db.scalar(
            select(Job)
            .where(Job.id == job_id, Job.status == "open")
            .with_for_update()
        )

    @staticmethod
    async def _get_submission_by_idempotency_hash(
        db: AsyncSession,
        idempotency_hash: str,
    ) -> PublicApplicationSubmission | None:
        return await db.scalar(
            select(PublicApplicationSubmission)
            .where(
                PublicApplicationSubmission.idempotency_key_hash == idempotency_hash
            )
            .with_for_update()
        )

    @staticmethod
    async def _get_submission_for_application(
        db: AsyncSession,
        application_id: int,
    ) -> PublicApplicationSubmission | None:
        return await db.scalar(
            select(PublicApplicationSubmission)
            .where(PublicApplicationSubmission.application_id == application_id)
            .with_for_update()
        )

    @staticmethod
    async def _get_candidate_job_applications_for_update(
        db: AsyncSession,
        candidate_id: int,
        job_id: int,
    ) -> list[Application]:
        result = await db.scalars(
            select(Application)
            .where(
                Application.candidate_id == candidate_id,
                Application.job_id == job_id,
            )
            .order_by(Application.id)
            .with_for_update()
        )
        return list(result.all())

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
        result = await db.scalars(
            select(Candidate)
            .where(or_(normalized_phone == phone, normalized_email == email))
            .order_by(Candidate.id)
            .with_for_update()
        )
        return list(result.unique().all())

    @staticmethod
    async def _same_name_exists(db: AsyncSession, name: str) -> bool:
        candidate_id = await db.scalar(
            select(Candidate.id).where(func.btrim(Candidate.name) == name).limit(1)
        )
        return candidate_id is not None

    @staticmethod
    def _normalized_phone(value: Any) -> str | None:
        try:
            result = normalize_application_phone(value)
        except ValueError:
            return None
        return result if isinstance(result, str) else None

    @staticmethod
    def _normalized_email(value: Any) -> str | None:
        try:
            result = normalize_application_email(value)
        except ValueError:
            return None
        return result if isinstance(result, str) else None

    @classmethod
    def _request_fingerprint(
        cls,
        data: PublicApplicationForm,
        prepared: PreparedResumeFile,
    ) -> str:
        payload = {
            "consent_version": data.consent_version,
            "email": data.email,
            "file_sha256": prepared.sha256,
            "job_id": data.job_id,
            "name": data.name,
            "phone": data.phone,
            "privacy_consent": data.privacy_consent,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return cls._sha256_text(canonical)

    @staticmethod
    def _sha256_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_submission_reference() -> str:
        suffix = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(12))
        return f"AP-{suffix}"

    @staticmethod
    def _acceptance(
        submission: PublicApplicationSubmission,
        *,
        reused: bool,
    ) -> PublicApplicationAcceptance:
        return PublicApplicationAcceptance(
            submission_reference=submission.submission_reference,
            accepted_at=submission.consented_at,
            reused=reused,
        )

    @staticmethod
    def _discard_safely(
        storage: ResumeFileStorage,
        prepared: PreparedResumeFile,
    ) -> None:
        try:
            storage.discard(prepared)
        except ResumeStorageError:
            logger.exception(
                "Public application file cleanup failed (file=%s)",
                prepared.sha256[:12],
            )


public_application_service = PublicApplicationService()
