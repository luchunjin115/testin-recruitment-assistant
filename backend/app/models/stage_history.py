from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.screening_result import ScreeningResult


class StageHistory(Base):
    __tablename__ = "stage_histories"
    __table_args__ = (
        CheckConstraint(
            "from_recruitment_stage IS NULL OR from_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_stage_histories_from_stage_allowed",
        ),
        CheckConstraint(
            "to_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_stage_histories_to_stage_allowed",
        ),
        CheckConstraint(
            "from_hr_decision IS NULL OR from_hr_decision IN "
            "('pending', 'passed', 'backup', 'rejected')",
            name="ck_stage_histories_from_decision_allowed",
        ),
        CheckConstraint(
            "to_hr_decision IN ('pending', 'passed', 'backup', 'rejected')",
            name="ck_stage_histories_to_decision_allowed",
        ),
        CheckConstraint(
            "actor_type IN ('hr', 'system')",
            name="ck_stage_histories_actor_type_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    from_recruitment_stage: Mapped[str | None] = mapped_column(String(30))
    to_recruitment_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    from_hr_decision: Mapped[str | None] = mapped_column(String(20))
    to_hr_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reason_detail: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(100))
    actor_label: Mapped[str] = mapped_column(String(100), nullable=False)
    screening_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("screening_results.id"),
        index=True,
    )
    overrides_ai_recommendation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    application: Mapped["Application"] = relationship(back_populates="stage_histories")
    screening_result: Mapped["ScreeningResult | None"] = relationship(
        back_populates="stage_histories"
    )
