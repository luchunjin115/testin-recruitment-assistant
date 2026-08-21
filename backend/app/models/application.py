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
    from app.models.candidate import Candidate
    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.stage_history import StageHistory
    from app.models.screening_report import ScreeningReport
    from app.models.screening_run import ScreeningRun


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "source IN ('hr_direct', 'hr_screening', 'public_apply')",
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
            "hr_decision IN ('pending', 'passed', 'backup', 'rejected')",
            name="ck_applications_hr_decision_allowed",
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
    current_resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id"),
        nullable=False,
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
    hr_decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
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

    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    current_resume: Mapped["Resume"] = relationship(
        back_populates="current_applications",
        foreign_keys=[current_resume_id],
    )
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        back_populates="application",
        order_by="StageHistory.created_at",
    )
    screening_report: Mapped["ScreeningReport | None"] = relationship(
        back_populates="application",
        uselist=False,
        passive_deletes=True,
    )
    screening_runs: Mapped[list["ScreeningRun"]] = relationship(
        back_populates="application",
        order_by="ScreeningRun.created_at",
        passive_deletes=True,
    )
