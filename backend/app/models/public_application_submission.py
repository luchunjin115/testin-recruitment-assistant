from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.application_processing_run import ApplicationProcessingRun
    from app.models.resume import Resume


class PublicApplicationSubmission(Base):
    __tablename__ = "public_application_submissions"
    __table_args__ = (
        CheckConstraint(
            "submission_reference ~ '^AP-[A-Z0-9]{8,24}$'",
            name="ck_public_application_submissions_reference_format",
        ),
        CheckConstraint(
            "idempotency_key_hash ~ '^[0-9a-f]{64}$'",
            name="ck_public_application_submissions_idempotency_hash_format",
        ),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_public_application_submissions_request_fingerprint_format",
        ),
        CheckConstraint(
            "btrim(consent_version) <> ''",
            name="ck_public_application_submissions_consent_version_nonempty",
        ),
        CheckConstraint(
            "identity_review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_public_application_submissions_identity_status_allowed",
        ),
        CheckConstraint(
            "jsonb_typeof(identity_review_reasons) = 'array'",
            name="ck_public_application_submissions_identity_reasons_array",
        ),
        CheckConstraint(
            "identity_review_reasons <@ '[\"same_name\", \"contact_conflict\"]'::jsonb",
            name="ck_public_application_submissions_identity_reasons_allowed",
        ),
        CheckConstraint(
            "(identity_review_status = 'clear' AND "
            "jsonb_array_length(identity_review_reasons) = 0) OR "
            "(identity_review_status IN ('needs_review', 'reviewed') AND "
            "jsonb_array_length(identity_review_reasons) > 0)",
            name="ck_public_application_submissions_identity_review_consistent",
        ),
        UniqueConstraint(
            "application_id",
            name="uq_public_application_submissions_application_id",
        ),
        UniqueConstraint(
            "resume_id",
            name="uq_public_application_submissions_resume_id",
        ),
        UniqueConstraint(
            "submission_reference",
            name="uq_public_application_submissions_reference",
        ),
        UniqueConstraint(
            "idempotency_key_hash",
            name="uq_public_application_submissions_idempotency_hash",
        ),
        UniqueConstraint(
            "id",
            "application_id",
            "resume_id",
            name="uq_public_application_submissions_frozen_identity",
        ),
        Index(
            "ix_public_application_submissions_identity_review_status",
            "identity_review_status",
        ),
        Index(
            "ix_public_application_submissions_created_at",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submission_reference: Mapped[str] = mapped_column(String(27), nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(100), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    identity_review_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="clear",
        server_default="clear",
    )
    identity_review_reasons: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    application: Mapped["Application"] = relationship(back_populates="public_submission")
    resume: Mapped["Resume"] = relationship(back_populates="public_submission")
    processing_runs: Mapped[list["ApplicationProcessingRun"]] = relationship(
        back_populates="submission",
        order_by="ApplicationProcessingRun.created_at",
        viewonly=True,
    )
