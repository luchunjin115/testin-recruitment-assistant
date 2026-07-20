from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.rebuilt.candidate import Candidate
    from app.models.rebuilt.job import Job
    from app.models.rebuilt.screening_result import ScreeningResult


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    screening_id: Mapped[int | None] = mapped_column(ForeignKey("screening_results.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(20),
        default="screening",
        server_default="screening",
        index=True,
    )
    format: Mapped[str] = mapped_column(
        String(20),
        default="markdown",
        server_default="markdown",
    )
    report_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="reports")
    job: Mapped["Job"] = relationship(back_populates="reports")
    screening_result: Mapped["ScreeningResult | None"] = relationship(back_populates="reports")
