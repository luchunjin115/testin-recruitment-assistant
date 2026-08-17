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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.rebuilt.job import Job


class JobScreeningRubric(Base):
    __tablename__ = "job_screening_rubrics"
    __table_args__ = (
        UniqueConstraint("job_id", "version", name="uq_job_screening_rubrics_job_version"),
        CheckConstraint("version >= 1", name="ck_job_screening_rubrics_version_positive"),
        CheckConstraint(
            "must_have_requirements_weight BETWEEN 30 AND 50",
            name="ck_job_screening_rubrics_must_have_weight_range",
        ),
        CheckConstraint(
            "work_experience_relevance_weight BETWEEN 15 AND 35",
            name="ck_job_screening_rubrics_work_weight_range",
        ),
        CheckConstraint(
            "projects_and_capability_weight BETWEEN 10 AND 30",
            name="ck_job_screening_rubrics_project_weight_range",
        ),
        CheckConstraint(
            "preferred_qualifications_weight BETWEEN 0 AND 20",
            name="ck_job_screening_rubrics_preferred_weight_range",
        ),
        CheckConstraint(
            "keywords_and_additional_weight BETWEEN 0 AND 10",
            name="ck_job_screening_rubrics_additional_weight_range",
        ),
        CheckConstraint(
            "must_have_requirements_weight + work_experience_relevance_weight + "
            "projects_and_capability_weight + preferred_qualifications_weight + "
            "keywords_and_additional_weight = 100",
            name="ck_job_screening_rubrics_weight_total",
        ),
        Index(
            "uq_job_screening_rubrics_current_job",
            "job_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    must_have_requirements_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=40,
        server_default="40",
    )
    work_experience_relevance_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
        server_default="25",
    )
    projects_and_capability_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
        server_default="20",
    )
    preferred_qualifications_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )
    keywords_and_additional_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )
    schema_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
        server_default="1.0",
    )
    subcriteria_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
        server_default="1.0",
    )
    recommendation_thresholds_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
        server_default="1.0",
    )
    fairness_rules_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
        server_default="1.0",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )
    change_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    change_detail: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped["Job"] = relationship(back_populates="screening_rubrics")

    @property
    def weights(self) -> dict[str, int]:
        return {
            "must_have_requirements": self.must_have_requirements_weight,
            "work_experience_relevance": self.work_experience_relevance_weight,
            "projects_and_capability": self.projects_and_capability_weight,
            "preferred_qualifications": self.preferred_qualifications_weight,
            "keywords_and_additional": self.keywords_and_additional_weight,
        }
