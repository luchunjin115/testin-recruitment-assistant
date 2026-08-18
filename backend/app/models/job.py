from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'open', 'closed')",
            name="ck_jobs_status_allowed",
        ),
        CheckConstraint(
            "headcount IS NULL OR headcount BETWEEN 1 AND 999",
            name="ck_jobs_headcount_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(100))
    employment_type: Mapped[str | None] = mapped_column(String(30))
    headcount: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    legacy_requirements: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSONB(none_as_null=True),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="applied_job")
    resumes: Mapped[list["Resume"]] = relationship(back_populates="job")
    screening_results: Mapped[list["ScreeningResult"]] = relationship(back_populates="job")
    reports: Mapped[list["Report"]] = relationship(back_populates="job")
    applications: Mapped[list["Application"]] = relationship(back_populates="job")
    screening_rubrics: Mapped[list["JobScreeningRubric"]] = relationship(
        back_populates="job",
        order_by="JobScreeningRubric.version",
    )
