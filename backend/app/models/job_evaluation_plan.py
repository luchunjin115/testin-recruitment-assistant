from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class JobEvaluationPlan(Base):
    __tablename__ = "job_evaluation_plans"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "input_fingerprint",
            name="uq_job_evaluation_plans_job_input_fingerprint",
        ),
        CheckConstraint(
            "status IN ('generating', 'ready', 'failed', 'outdated')",
            name="ck_job_evaluation_plans_status_allowed",
        ),
        CheckConstraint(
            "status <> 'outdated' OR is_current = false",
            name="ck_job_evaluation_plans_outdated_not_current",
        ),
        CheckConstraint(
            "free_text_coverage IS NULL "
            "OR jsonb_typeof(free_text_coverage) = 'object'",
            name="ck_job_evaluation_plans_free_text_coverage_object",
        ),
        CheckConstraint(
            "schema_version <> '2.0' OR status <> 'ready' "
            "OR free_text_coverage IS NOT NULL",
            name="ck_job_evaluation_plans_v2_ready_has_free_text_coverage",
        ),
        Index("ix_job_evaluation_plans_job_id", "job_id"),
        Index("ix_job_evaluation_plans_status", "status"),
        Index(
            "uq_job_evaluation_plans_current_job",
            "job_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    jd_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="generating",
        server_default="generating",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    items: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    structured_coverage: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    free_text_coverage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job: Mapped["Job"] = relationship(back_populates="evaluation_plans")
    screening_reports: Mapped[list["ScreeningReport"]] = relationship(
        back_populates="job_evaluation_plan",
        passive_deletes=True,
    )
    screening_runs: Mapped[list["ScreeningRun"]] = relationship(
        back_populates="job_evaluation_plan",
        passive_deletes=True,
    )
