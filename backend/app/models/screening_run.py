from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.job import Job
    from app.models.job_evaluation_plan import JobEvaluationPlan
    from app.models.resume import Resume


class ScreeningRun(Base):
    """Minimal durable execution log; it never stores a full model response."""

    __tablename__ = "screening_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('automatic', 'single_reassessment', "
            "'batch_reassessment')",
            name="ck_screening_runs_trigger_type_allowed",
        ),
        CheckConstraint(
            "status IN ('waiting_resume', 'waiting_plan', 'queued', 'running', "
            "'succeeded', 'failed', 'paused')",
            name="ck_screening_runs_status_allowed",
        ),
        CheckConstraint(
            "waiting_reason IS NULL OR "
            "(status = 'waiting_plan' AND waiting_reason IN "
            "('plan_missing', 'plan_generating', 'plan_pending_confirmation', "
            "'plan_failed', "
            "'plan_outdated', 'plan_contract_outdated')) OR "
            "(status = 'paused' AND waiting_reason = 'job_closed')",
            name="ck_screening_runs_waiting_reason_matches_status",
        ),
        CheckConstraint(
            "attempt_count BETWEEN 0 AND 2",
            name="ck_screening_runs_attempt_count_range",
        ),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_screening_runs_input_tokens_nonnegative",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_screening_runs_output_tokens_nonnegative",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_screening_runs_duration_nonnegative",
        ),
        CheckConstraint(
            "status <> 'failed' OR (completed_at IS NOT NULL AND "
            "error_code IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_screening_runs_failed_has_safe_error",
        ),
        CheckConstraint(
            "status <> 'succeeded' OR (completed_at IS NOT NULL AND "
            "error_code IS NULL AND error_message IS NULL)",
            name="ck_screening_runs_succeeded_is_clean",
        ),
        Index("ix_screening_runs_application_id", "application_id"),
        Index("ix_screening_runs_job_id", "job_id"),
        Index("ix_screening_runs_status", "status"),
        Index("ix_screening_runs_created_at", "created_at"),
        Index(
            "uq_screening_runs_active_application",
            "application_id",
            unique=True,
            postgresql_where=text(
                "status IN ('waiting_resume', 'waiting_plan', 'queued', "
                "'running', 'paused')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    job_evaluation_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_evaluation_plans.id", ondelete="RESTRICT")
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    waiting_reason: Mapped[str | None] = mapped_column(String(50))
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    redaction_version: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluation_reference_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    evaluation_timezone: Mapped[str | None] = mapped_column(String(100))
    experience_period_facts_rule_version: Mapped[str | None] = mapped_column(
        String(100)
    )
    experience_period_facts_fingerprint: Mapped[str | None] = mapped_column(
        String(64)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
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

    application: Mapped["Application"] = relationship(back_populates="screening_runs")
    job: Mapped["Job"] = relationship(back_populates="screening_runs")
    resume: Mapped["Resume"] = relationship(back_populates="screening_runs")
    job_evaluation_plan: Mapped["JobEvaluationPlan | None"] = relationship(
        back_populates="screening_runs"
    )
