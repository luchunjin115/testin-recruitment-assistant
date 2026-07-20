from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.rebuilt.candidate import Candidate
    from app.models.rebuilt.job import Job
    from app.models.rebuilt.report import Report


class ScreeningResult(Base):
    __tablename__ = "screening_results"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_screening_candidate_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, index=True)
    hard_pass: Mapped[bool | None] = mapped_column(Boolean)
    skill_score: Mapped[int | None] = mapped_column(Integer)
    experience_score: Mapped[int | None] = mapped_column(Integer)
    project_score: Mapped[int | None] = mapped_column(Integer)
    strengths: Mapped[list | None] = mapped_column(JSONB)
    risks: Mapped[list | None] = mapped_column(JSONB)
    recommendation: Mapped[str | None] = mapped_column(String(20), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    raw_result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="screening_results")
    job: Mapped["Job"] = relationship(back_populates="screening_results")
    reports: Mapped[list["Report"]] = relationship(back_populates="screening_result")
