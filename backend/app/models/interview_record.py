from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.stage_history import StageHistory


class InterviewRecord(Base):
    __tablename__ = "interview_records"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "round_number",
            name="uq_interview_records_application_round",
        ),
        CheckConstraint(
            "round_number >= 1",
            name="ck_interview_records_round_positive",
        ),
        CheckConstraint(
            "interview_type IN ('onsite', 'video', 'phone')",
            name="ck_interview_records_type_allowed",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'canceled', 'no_show')",
            name="ck_interview_records_status_allowed",
        ),
        CheckConstraint(
            "decision IN ('pending', 'next_round', 'proceed_offer', "
            "'rejected', 'candidate_withdrew')",
            name="ck_interview_records_decision_allowed",
        ),
        CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_interview_records_duration_range",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_interview_records_version_positive",
        ),
        CheckConstraint(
            "jsonb_typeof(interviewer_names) = 'array' AND "
            "jsonb_array_length(interviewer_names) BETWEEN 1 AND 10",
            name="ck_interview_records_interviewers_array",
        ),
        CheckConstraint(
            "jsonb_typeof(strengths) = 'array' AND "
            "jsonb_array_length(strengths) <= 20",
            name="ck_interview_records_strengths_array",
        ),
        CheckConstraint(
            "jsonb_typeof(concerns) = 'array' AND "
            "jsonb_array_length(concerns) <= 20",
            name="ck_interview_records_concerns_array",
        ),
        CheckConstraint(
            "jsonb_typeof(follow_up_questions) = 'array' AND "
            "jsonb_array_length(follow_up_questions) <= 20",
            name="ck_interview_records_follow_ups_array",
        ),
        CheckConstraint(
            "(feedback_submitted_at IS NULL AND "
            "feedback_submitted_by_label IS NULL AND feedback_summary IS NULL "
            "AND decision = 'pending' AND jsonb_array_length(strengths) = 0 "
            "AND jsonb_array_length(concerns) = 0 "
            "AND jsonb_array_length(follow_up_questions) = 0) OR "
            "(feedback_submitted_at IS NOT NULL AND "
            "feedback_submitted_by_label IS NOT NULL AND "
            "feedback_summary IS NOT NULL AND status = 'completed')",
            name="ck_interview_records_feedback_consistent",
        ),
        CheckConstraint(
            "status NOT IN ('canceled', 'no_show') OR decision = 'pending'",
            name="ck_interview_records_closed_status_pending_decision",
        ),
        CheckConstraint(
            "feedback_submitted_at IS NULL OR feedback_submitted_at >= created_at",
            name="ck_interview_records_feedback_time_consistent",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_interview_records_update_time_consistent",
        ),
        Index(
            "uq_interview_records_one_scheduled_per_application",
            "application_id",
            unique=True,
            postgresql_where=text("status = 'scheduled'"),
        ),
        Index(
            "ix_interview_records_application_status_scheduled_start",
            "application_id",
            "status",
            "scheduled_start_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey(
            "applications.id",
            name="fk_interview_records_application_id_applications",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    interview_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", server_default="scheduled"
    )
    scheduled_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Asia/Shanghai",
        server_default="Asia/Shanghai",
    )
    interviewer_names: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    location: Mapped[str | None] = mapped_column(String(500))
    meeting_link: Mapped[str | None] = mapped_column(String(2_048))
    schedule_note: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending"
    )
    feedback_summary: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    concerns: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    follow_up_questions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    feedback_submitted_by_label: Mapped[str | None] = mapped_column(String(100))
    feedback_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    application: Mapped["Application"] = relationship(
        back_populates="interview_records"
    )
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        back_populates="interview_record",
        passive_deletes=True,
    )
