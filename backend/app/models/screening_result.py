from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.candidate import Candidate
    from app.models.job import Job
    from app.models.report import Report
    from app.models.resume import Resume
    from app.models.stage_history import StageHistory


class ScreeningResult(Base):
    __tablename__ = "screening_results"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "attempt_number",
            name="uq_screening_results_application_attempt",
        ),
        CheckConstraint(
            "attempt_number >= 1",
            name="ck_screening_results_attempt_positive",
        ),
        CheckConstraint(
            "execution_status IN ('screening', 'completed', 'failed', 'blocked')",
            name="ck_screening_results_execution_status_allowed",
        ),
        CheckConstraint(
            "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
            name="ck_screening_results_overall_score_range",
        ),
        CheckConstraint(
            "evidence_coverage_rate IS NULL OR "
            "evidence_coverage_rate BETWEEN 0 AND 1",
            name="ck_screening_results_evidence_coverage_range",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_screening_results_duration_nonnegative",
        ),
        CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_screening_results_prompt_tokens_nonnegative",
        ),
        CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_screening_results_completion_tokens_nonnegative",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_screening_results_total_tokens_nonnegative",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_screening_results_estimated_cost_nonnegative",
        ),
        Index(
            "uq_screening_results_running_application",
            "application_id",
            unique=True,
            postgresql_where=text("execution_status = 'screening'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey(
            "applications.id",
            name="fk_screening_results_application_id_applications",
        ),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey(
            "resumes.id",
            name="fk_screening_results_resume_id_resumes",
        ),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    execution_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        server_default="completed",
        index=True,
    )
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, index=True)
    hard_pass: Mapped[bool | None] = mapped_column(Boolean)
    skill_score: Mapped[int | None] = mapped_column(Integer)
    experience_score: Mapped[int | None] = mapped_column(Integer)
    project_score: Mapped[int | None] = mapped_column(Integer)
    strengths: Mapped[list | None] = mapped_column(JSONB)
    risks: Mapped[list | None] = mapped_column(JSONB)
    recommendation: Mapped[str | None] = mapped_column(String(20), index=True)
    evidence_coverage_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    hard_requirement_checks: Mapped[list | None] = mapped_column(JSONB)
    dimension_scores: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    pending_questions: Mapped[list | None] = mapped_column(JSONB)
    resume_evidence: Mapped[list | None] = mapped_column(JSONB)
    job_evidence: Mapped[list | None] = mapped_column(JSONB)
    candidate_input_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    resume_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    job_requirements_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    rubric_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    rules_version: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    model_provider: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(100))
    model_config_version: Mapped[str | None] = mapped_column(String(100))
    job_schema_version: Mapped[str | None] = mapped_column(String(20))
    resume_schema_version: Mapped[str | None] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(100), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    trigger_reason: Mapped[str | None] = mapped_column(Text)
    force_rerun: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    actor_type: Mapped[str | None] = mapped_column(String(20))
    actor_id: Mapped[str | None] = mapped_column(String(100))
    actor_label: Mapped[str | None] = mapped_column(String(100))
    is_outdated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    outdated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="screening_results")
    job: Mapped["Job"] = relationship(back_populates="screening_results")
    application: Mapped["Application"] = relationship(
        back_populates="screening_results",
        foreign_keys=[application_id],
    )
    resume: Mapped["Resume"] = relationship(back_populates="screening_results")
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        back_populates="screening_result"
    )
    reports: Mapped[list["Report"]] = relationship(back_populates="screening_result")
