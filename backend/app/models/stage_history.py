from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.interview_record import InterviewRecord
    from app.models.offer_record import OfferRecord
    from app.models.screening_report import ScreeningReport


class StageHistory(Base):
    __tablename__ = "stage_histories"
    __table_args__ = (
        CheckConstraint(
            "from_recruitment_stage IS NULL OR from_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected', "
            "'interview', 'offer', 'offer_accepted', 'admitted', 'hired')",
            name="ck_stage_histories_from_stage_allowed",
        ),
        CheckConstraint(
            "to_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected', "
            "'interview', 'offer', 'offer_accepted', 'admitted', 'hired')",
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
        CheckConstraint(
            "from_lifecycle_status IS NULL OR "
            "from_lifecycle_status IN ('active', 'ended', 'voided')",
            name="ck_stage_histories_from_lifecycle_allowed",
        ),
        CheckConstraint(
            "to_lifecycle_status IS NULL OR "
            "to_lifecycle_status IN ('active', 'ended', 'voided')",
            name="ck_stage_histories_to_lifecycle_allowed",
        ),
        CheckConstraint(
            "from_final_outcome IS NULL OR from_final_outcome IN "
            "('screening_rejected', 'interview_rejected', 'interview_no_show', "
            "'offer_declined', 'offer_withdrawn', 'offer_expired', "
            "'candidate_withdrew', 'company_canceled', 'hired')",
            name="ck_stage_histories_from_final_outcome_allowed",
        ),
        CheckConstraint(
            "to_final_outcome IS NULL OR to_final_outcome IN "
            "('screening_rejected', 'interview_rejected', 'interview_no_show', "
            "'offer_declined', 'offer_withdrawn', 'offer_expired', "
            "'candidate_withdrew', 'company_canceled', 'hired')",
            name="ck_stage_histories_to_final_outcome_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("screening_reports.id", ondelete="SET NULL"),
        index=True,
    )
    interview_record_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "interview_records.id",
            name="fk_stage_histories_interview_record_id_interview_records",
            ondelete="SET NULL",
        ),
        index=True,
    )
    offer_record_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "offer_records.id",
            name="fk_stage_histories_offer_record_id_offer_records",
            ondelete="SET NULL",
        ),
        index=True,
    )
    from_lifecycle_status: Mapped[str | None] = mapped_column(String(20))
    to_lifecycle_status: Mapped[str | None] = mapped_column(String(20))
    from_recruitment_stage: Mapped[str | None] = mapped_column(String(30))
    to_recruitment_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    from_hr_decision: Mapped[str | None] = mapped_column(String(20))
    to_hr_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    from_final_outcome: Mapped[str | None] = mapped_column(String(30))
    to_final_outcome: Mapped[str | None] = mapped_column(String(30))
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reason_detail: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(100))
    actor_label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    application: Mapped["Application"] = relationship(back_populates="stage_histories")
    screening_report: Mapped["ScreeningReport | None"] = relationship(
        back_populates="stage_histories"
    )
    interview_record: Mapped["InterviewRecord | None"] = relationship(
        back_populates="stage_histories"
    )
    offer_record: Mapped["OfferRecord | None"] = relationship(
        back_populates="stage_histories"
    )
