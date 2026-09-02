from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.stage_history import StageHistory


class OfferRecord(Base):
    __tablename__ = "offer_records"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "version_number",
            name="uq_offer_records_application_version",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_offer_records_version_number_positive",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_offer_records_version_positive",
        ),
        CheckConstraint(
            "status IN ('draft', 'sent', 'accepted', 'declined', "
            "'withdrawn', 'expired')",
            name="ck_offer_records_status_allowed",
        ),
        CheckConstraint(
            "salary_period IN ('monthly', 'annual')",
            name="ck_offer_records_salary_period_allowed",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_offer_records_currency_format",
        ),
        CheckConstraint(
            "base_salary_amount > 0",
            name="ck_offer_records_base_salary_positive",
        ),
        CheckConstraint(
            "(salary_period = 'monthly' AND salary_months BETWEEN 1 AND 24) OR "
            "(salary_period = 'annual' AND salary_months IS NULL)",
            name="ck_offer_records_salary_months_consistent",
        ),
        CheckConstraint(
            "expected_start_date >= valid_until",
            name="ck_offer_records_dates_consistent",
        ),
        CheckConstraint(
            "(status = 'draft' AND sent_at IS NULL AND responded_at IS NULL "
            "AND closed_at IS NULL) OR "
            "(status = 'sent' AND sent_at IS NOT NULL AND responded_at IS NULL "
            "AND closed_at IS NULL) OR "
            "(status IN ('accepted', 'declined') AND sent_at IS NOT NULL "
            "AND responded_at IS NOT NULL AND closed_at IS NULL) OR "
            "(status IN ('withdrawn', 'expired') AND sent_at IS NOT NULL "
            "AND responded_at IS NULL AND closed_at IS NOT NULL)",
            name="ck_offer_records_status_timestamps_consistent",
        ),
        CheckConstraint(
            "responded_at IS NULL OR responded_at >= sent_at",
            name="ck_offer_records_response_time_consistent",
        ),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= sent_at",
            name="ck_offer_records_close_time_consistent",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_offer_records_update_time_consistent",
        ),
        Index(
            "uq_offer_records_one_active_per_application",
            "application_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'sent', 'accepted')"),
        ),
        Index(
            "ix_offer_records_application_status_valid_until",
            "application_id",
            "status",
            "valid_until",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey(
            "applications.id",
            name="fk_offer_records_application_id_applications",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    position_title: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    salary_period: Mapped[str] = mapped_column(String(20), nullable=False)
    base_salary_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )
    salary_months: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=4, scale=1)
    )
    bonus_note: Mapped[str | None] = mapped_column(Text)
    benefits_note: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    expected_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    application: Mapped["Application"] = relationship(back_populates="offer_records")
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        back_populates="offer_record",
        passive_deletes=True,
    )
