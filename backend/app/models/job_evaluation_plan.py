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
            "status IN ("
            "'generating', 'pending_confirmation', 'ready', 'failed', 'outdated'"
            ")",
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
            "source_review_summary IS NULL "
            "OR jsonb_typeof(source_review_summary) = 'object'",
            name="ck_job_evaluation_plans_source_review_summary_object",
        ),
        CheckConstraint(
            "schema_version IN ('1.0', '2.0', '3.0', '4.0')",
            name="ck_job_evaluation_plans_schema_version_allowed",
        ),
        CheckConstraint(
            "schema_version <> '2.0' OR status <> 'ready' "
            "OR free_text_coverage IS NOT NULL",
            name="ck_job_evaluation_plans_v2_ready_has_free_text_coverage",
        ),
        CheckConstraint(
            "schema_version <> '3.0' OR status <> 'ready' "
            "OR source_review_summary IS NOT NULL",
            name="ck_job_evaluation_plans_v3_ready_has_source_review_summary",
        ),
        CheckConstraint(
            "schema_version <> '3.0' OR "
            "(structured_coverage IS NULL AND free_text_coverage IS NULL)",
            name="ck_job_evaluation_plans_v3_has_no_legacy_coverage",
        ),
        CheckConstraint(
            "requirement_facts IS NULL "
            "OR jsonb_typeof(requirement_facts) = 'array'",
            name="ck_job_evaluation_plans_requirement_facts_array",
        ),
        CheckConstraint(
            "evaluation_criteria IS NULL "
            "OR jsonb_typeof(evaluation_criteria) = 'array'",
            name="ck_job_evaluation_plans_evaluation_criteria_array",
        ),
        CheckConstraint(
            "coverage_review_summary IS NULL "
            "OR jsonb_typeof(coverage_review_summary) = 'object'",
            name="ck_job_evaluation_plans_coverage_review_summary_object",
        ),
        CheckConstraint(
            "generation_audit IS NULL "
            "OR jsonb_typeof(generation_audit) = 'object'",
            name="ck_job_evaluation_plans_generation_audit_object",
        ),
        CheckConstraint(
            "schema_version = '4.0' OR "
            "(requirement_facts IS NULL "
            "AND evaluation_criteria IS NULL "
            "AND coverage_review_summary IS NULL "
            "AND generation_audit IS NULL)",
            name="ck_job_evaluation_plans_legacy_has_no_v4_payload",
        ),
        CheckConstraint(
            "schema_version <> '4.0' OR "
            "(items IS NULL "
            "AND structured_coverage IS NULL "
            "AND free_text_coverage IS NULL)",
            name="ck_job_evaluation_plans_v4_has_no_legacy_payload",
        ),
        CheckConstraint(
            "schema_version <> '4.0' "
            "OR status NOT IN ('pending_confirmation', 'ready') "
            "OR (requirement_facts IS NOT NULL "
            "AND jsonb_array_length(requirement_facts) > 0 "
            "AND evaluation_criteria IS NOT NULL "
            "AND jsonb_array_length(evaluation_criteria) > 0 "
            "AND source_review_summary IS NOT NULL "
            "AND coverage_review_summary IS NOT NULL "
            "AND generation_audit IS NOT NULL)",
            name="ck_job_evaluation_plans_v4_complete_payload",
        ),
        CheckConstraint(
            "schema_version <> '4.0' "
            "OR status NOT IN ('generating', 'failed') "
            "OR (requirement_facts IS NULL "
            "AND evaluation_criteria IS NULL "
            "AND source_review_summary IS NULL "
            "AND coverage_review_summary IS NULL "
            "AND generation_audit IS NULL)",
            name="ck_job_evaluation_plans_v4_no_partial_failed_payload",
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
    items: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    structured_coverage: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    free_text_coverage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_review_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requirement_facts: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    evaluation_criteria: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    coverage_review_summary: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    generation_audit: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[str | dict]] = mapped_column(
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
