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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.rebuilt.candidate import Candidate
    from app.models.rebuilt.job import Job
    from app.models.rebuilt.resume import Resume
    from app.models.rebuilt.screening_result import ScreeningResult
    from app.models.rebuilt.stage_history import StageHistory


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "source IN ('hr_direct', 'hr_screening', 'public_apply', 'legacy_migration')",
            name="ck_applications_source_allowed",
        ),
        CheckConstraint(
            "lifecycle_status IN ('active', 'ended', 'voided')",
            name="ck_applications_lifecycle_status_allowed",
        ),
        CheckConstraint(
            "recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_applications_recruitment_stage_allowed",
        ),
        CheckConstraint(
            "ai_status IN ('not_started', 'screening', 'completed', 'failed', 'blocked')",
            name="ck_applications_ai_status_allowed",
        ),
        CheckConstraint(
            "hr_decision IN ('pending', 'passed', 'backup', 'rejected')",
            name="ck_applications_hr_decision_allowed",
        ),
        CheckConstraint(
            "source = 'legacy_migration' OR current_resume_id IS NOT NULL",
            name="ck_applications_resume_required_unless_legacy",
        ),
        UniqueConstraint(
            "current_screening_result_id",
            name="uq_applications_current_screening_result_id",
        ),
        Index(
            "uq_applications_active_candidate_job",
            "candidate_id",
            "job_id",
            unique=True,
            postgresql_where=text("lifecycle_status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
        index=True,
    )
    current_resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id"),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    lifecycle_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    recruitment_stage: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    ai_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
        server_default="not_started",
        index=True,
    )
    hr_decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    current_screening_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "screening_results.id",
            name="fk_applications_current_screening_result_id_screening_results",
            use_alter=True,
        ),
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    legacy_stage: Mapped[str | None] = mapped_column(String(100))
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

    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    current_resume: Mapped["Resume | None"] = relationship(
        back_populates="current_applications",
        foreign_keys=[current_resume_id],
    )
    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="application",
        foreign_keys="ScreeningResult.application_id",
        order_by="ScreeningResult.attempt_number",
    )
    current_screening_result: Mapped["ScreeningResult | None"] = relationship(
        foreign_keys=[current_screening_result_id],
        post_update=True,
    )
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        back_populates="application",
        order_by="StageHistory.created_at",
    )
