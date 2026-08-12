from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.rebuilt.candidate import Candidate
    from app.models.rebuilt.job import Job


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidates.id"),
        index=True,
    )
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(Integer)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(
        String(30),
        default="uploaded",
        server_default="uploaded",
        index=True,
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    parsed_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    structure_status: Mapped[str] = mapped_column(
        String(30),
        default="not_started",
        server_default="not_started",
        index=True,
    )
    structure_error: Mapped[str | None] = mapped_column(Text)
    structure_attempt_id: Mapped[str | None] = mapped_column(String(36))
    structure_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    structured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    structure_schema_version: Mapped[str | None] = mapped_column(String(20))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidate: Mapped["Candidate | None"] = relationship(back_populates="resumes")
    job: Mapped["Job | None"] = relationship(back_populates="resumes")
