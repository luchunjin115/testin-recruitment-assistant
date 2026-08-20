from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.education import Education
    from app.models.job import Job
    from app.models.project_experience import ProjectExperience
    from app.models.report import Report
    from app.models.resume import Resume
    from app.models.work_experience import WorkExperience


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(100), index=True)
    gender: Mapped[str | None] = mapped_column(String(10))
    age: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(100), index=True)
    current_company: Mapped[str | None] = mapped_column(String(200))
    current_title: Mapped[str | None] = mapped_column(String(200))
    work_years: Mapped[int | None] = mapped_column(Integer, index=True)
    education_level: Mapped[str | None] = mapped_column(String(50), index=True)
    source: Mapped[str | None] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="new",
        server_default="new",
        index=True,
    )
    applied_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    resume_file_path: Mapped[str | None] = mapped_column(String(500))
    resume_text: Mapped[str | None] = mapped_column(Text)
    parsed_data: Mapped[dict | None] = mapped_column(JSONB)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    applied_job: Mapped["Job | None"] = relationship(back_populates="candidates")
    resumes: Mapped[list["Resume"]] = relationship(back_populates="candidate")
    education_records: Mapped[list["Education"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    work_experiences: Mapped[list["WorkExperience"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    project_experiences: Mapped[list["ProjectExperience"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")
    reports: Mapped[list["Report"]] = relationship(back_populates="candidate")
