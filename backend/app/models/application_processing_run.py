from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.public_application_submission import PublicApplicationSubmission
    from app.models.resume import Resume


class ApplicationProcessingRun(Base):
    __tablename__ = "application_processing_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('automatic', 'manual_retry')",
            name="ck_application_processing_runs_trigger_type_allowed",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'waiting_screening', 'succeeded', "
            "'succeeded_with_warnings', 'failed', 'paused')",
            name="ck_application_processing_runs_status_allowed",
        ),
        CheckConstraint(
            "current_step IN ('extract_text', 'structure_resume', "
            "'trigger_screening', 'await_screening', 'completed')",
            name="ck_application_processing_runs_current_step_allowed",
        ),
        CheckConstraint(
            "attempt_count BETWEEN 0 AND 3",
            name="ck_application_processing_runs_attempt_count_range",
        ),
        CheckConstraint(
            "(status = 'paused' AND waiting_reason IN "
            "('job_closed', 'existing_application_resume_choice')) OR "
            "(status <> 'paused' AND waiting_reason IS NULL)",
            name="ck_application_processing_runs_waiting_reason_matches_status",
        ),
        CheckConstraint(
            "(status = 'failed' AND completed_at IS NOT NULL AND "
            "error_code IS NOT NULL AND error_message IS NOT NULL) OR "
            "(status <> 'failed' AND error_code IS NULL AND error_message IS NULL)",
            name="ck_application_processing_runs_failed_has_safe_error",
        ),
        CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]*$'",
            name="ck_application_processing_runs_error_code_format",
        ),
        CheckConstraint(
            "error_message IS NULL OR btrim(error_message) <> ''",
            name="ck_application_processing_runs_error_message_nonempty",
        ),
        CheckConstraint(
            "status NOT IN ('succeeded', 'succeeded_with_warnings') OR "
            "(current_step = 'completed' AND completed_at IS NOT NULL)",
            name="ck_application_processing_runs_success_completed",
        ),
        CheckConstraint(
            "current_step <> 'completed' OR "
            "status IN ('succeeded', 'succeeded_with_warnings')",
            name="ck_application_processing_runs_completed_step_matches_status",
        ),
        CheckConstraint(
            "status <> 'waiting_screening' OR current_step = 'await_screening'",
            name="ck_application_processing_runs_waiting_screening_step",
        ),
        CheckConstraint(
            "jsonb_typeof(warning_codes) = 'array'",
            name="ck_application_processing_runs_warning_codes_array",
        ),
        CheckConstraint(
            "warning_codes <@ '[\"RESUME_STRUCTURE_FAILED\"]'::jsonb",
            name="ck_application_processing_runs_warning_codes_allowed",
        ),
        CheckConstraint(
            "status <> 'succeeded' OR jsonb_array_length(warning_codes) = 0",
            name="ck_application_processing_runs_succeeded_without_warnings",
        ),
        CheckConstraint(
            "status <> 'succeeded_with_warnings' OR "
            "jsonb_array_length(warning_codes) > 0",
            name="ck_application_processing_runs_warning_status_consistent",
        ),
        CheckConstraint(
            "(lease_owner IS NULL AND lease_expires_at IS NULL) OR "
            "(status = 'running' AND lease_owner IS NOT NULL AND "
            "lease_expires_at IS NOT NULL)",
            name="ck_application_processing_runs_lease_consistent",
        ),
        CheckConstraint(
            "status <> 'running' OR started_at IS NOT NULL",
            name="ck_application_processing_runs_running_has_started_at",
        ),
        ForeignKeyConstraint(
            ["submission_id", "application_id", "resume_id"],
            [
                "public_application_submissions.id",
                "public_application_submissions.application_id",
                "public_application_submissions.resume_id",
            ],
            name="fk_application_processing_runs_frozen_submission_identity",
            ondelete="RESTRICT",
        ),
        Index("ix_application_processing_runs_submission_id", "submission_id"),
        Index("ix_application_processing_runs_application_id", "application_id"),
        Index("ix_application_processing_runs_resume_id", "resume_id"),
        Index("ix_application_processing_runs_current_step", "current_step"),
        Index("ix_application_processing_runs_created_at", "created_at"),
        Index(
            "ix_application_processing_runs_claim",
            "status",
            "lease_expires_at",
            "created_at",
        ),
        Index(
            "uq_application_processing_runs_active_submission",
            "submission_id",
            unique=True,
            postgresql_where=text(
                "status IN ('queued', 'running', 'waiting_screening')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(nullable=False)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="queued",
        server_default="queued",
    )
    current_step: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="extract_text",
        server_default="extract_text",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    waiting_reason: Mapped[str | None] = mapped_column(String(50))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    warning_codes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(100))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    submission: Mapped["PublicApplicationSubmission"] = relationship(
        back_populates="processing_runs",
        viewonly=True,
    )
    application: Mapped["Application"] = relationship(
        back_populates="application_processing_runs",
        foreign_keys=[application_id],
    )
    resume: Mapped["Resume"] = relationship(
        back_populates="application_processing_runs",
        foreign_keys=[resume_id],
    )
