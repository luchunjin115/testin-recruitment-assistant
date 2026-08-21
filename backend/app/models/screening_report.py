from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.job import Job
    from app.models.job_evaluation_plan import JobEvaluationPlan
    from app.models.resume import Resume


class ScreeningReport(Base):
    """The single current successful AI screening report for an Application."""

    __tablename__ = "screening_reports"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            name="uq_screening_reports_application_id",
        ),
        CheckConstraint(
            "overall_score BETWEEN 0 AND 100",
            name="ck_screening_reports_overall_score_range",
        ),
        CheckConstraint(
            "display_label IN ('关联较弱', '存在明显差距', '部分匹配', "
            "'整体较匹配', '高度匹配')",
            name="ck_screening_reports_display_label_allowed",
        ),
        CheckConstraint(
            "jsonb_typeof(requirement_assessments) = 'array'",
            name="ck_screening_reports_requirements_array",
        ),
        CheckConstraint(
            "jsonb_typeof(bonus_highlights) = 'array'",
            name="ck_screening_reports_bonuses_array",
        ),
        CheckConstraint(
            "jsonb_typeof(interview_questions) = 'array'",
            name="ck_screening_reports_questions_array",
        ),
        CheckConstraint(
            "jsonb_typeof(outdated_reasons) = 'array'",
            name="ck_screening_reports_outdated_reasons_array",
        ),
        CheckConstraint(
            "experience_period_facts IS NULL OR "
            "jsonb_typeof(experience_period_facts) = 'object'",
            name="ck_screening_reports_experience_facts_object",
        ),
        CheckConstraint(
            "(is_outdated AND jsonb_array_length(outdated_reasons) > 0 "
            "AND outdated_at IS NOT NULL) OR "
            "(NOT is_outdated AND jsonb_array_length(outdated_reasons) = 0 "
            "AND outdated_at IS NULL)",
            name="ck_screening_reports_outdated_state_consistent",
        ),
        Index("ix_screening_reports_job_id", "job_id"),
        Index("ix_screening_reports_resume_id", "resume_id"),
        Index("ix_screening_reports_plan_id", "job_evaluation_plan_id"),
        Index("ix_screening_reports_is_outdated", "is_outdated"),
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
    job_evaluation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("job_evaluation_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    display_label: Mapped[str] = mapped_column(String(30), nullable=False)
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_assessments: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    bonus_highlights: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    tradeoff_reason: Mapped[str | None] = mapped_column(Text)
    interview_questions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jd_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
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
    experience_period_facts: Mapped[dict | None] = mapped_column(JSONB)
    is_outdated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    outdated_reasons: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    outdated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime] = mapped_column(
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

    application: Mapped["Application"] = relationship(back_populates="screening_report")
    job: Mapped["Job"] = relationship(back_populates="screening_reports")
    resume: Mapped["Resume"] = relationship(back_populates="screening_reports")
    job_evaluation_plan: Mapped["JobEvaluationPlan"] = relationship(
        back_populates="screening_reports"
    )
