"""add stage 9 interview, offer, and hiring pipeline contract

Revision ID: b9e2f4a6c801
Revises: a8d4f2c7e901
Create Date: 2026-09-02 20:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b9e2f4a6c801"
down_revision: str | Sequence[str] | None = "a8d4f2c7e901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STAGE_VALUES = (
    "'applied', 'hr_review', 'screening_passed', 'backup', 'rejected', "
    "'interview', 'offer', 'offer_accepted', 'admitted', 'hired'"
)
FINAL_OUTCOME_VALUES = (
    "'screening_rejected', 'interview_rejected', 'interview_no_show', "
    "'offer_declined', 'offer_withdrawn', 'offer_expired', "
    "'candidate_withdrew', 'company_canceled', 'hired'"
)


def _assert_explainable_ended_applications() -> None:
    unexplained = op.get_bind().execute(
        sa.text(
            "SELECT id FROM applications "
            "WHERE lifecycle_status = 'ended' "
            "AND NOT (recruitment_stage = 'rejected' AND hr_decision = 'rejected') "
            "LIMIT 1"
        )
    ).first()
    if unexplained is not None:
        raise RuntimeError("STAGE9_UNEXPLAINED_ENDED_APPLICATIONS")


def _assert_safe_downgrade() -> None:
    bind = op.get_bind()
    stage9_data = bind.execute(
        sa.text(
            "SELECT 1 WHERE EXISTS (SELECT 1 FROM interview_records) "
            "OR EXISTS (SELECT 1 FROM offer_records)"
        )
    ).first()
    if stage9_data is not None:
        raise RuntimeError("STAGE9_PIPELINE_DOWNGRADE_BLOCKED")

    incompatible_application = bind.execute(
        sa.text(
            "SELECT id FROM applications WHERE "
            "recruitment_stage IN ('interview', 'offer', 'offer_accepted', "
            "'admitted', 'hired') OR "
            "final_outcome IS NOT NULL AND final_outcome <> 'screening_rejected' "
            "LIMIT 1"
        )
    ).first()
    if incompatible_application is not None:
        raise RuntimeError("STAGE9_APPLICATION_DOWNGRADE_BLOCKED")

    incompatible_history = bind.execute(
        sa.text(
            "SELECT id FROM stage_histories WHERE "
            "interview_record_id IS NOT NULL OR offer_record_id IS NOT NULL OR "
            "from_recruitment_stage IN ('interview', 'offer', 'offer_accepted', "
            "'admitted', 'hired') OR "
            "to_recruitment_stage IN ('interview', 'offer', 'offer_accepted', "
            "'admitted', 'hired') LIMIT 1"
        )
    ).first()
    if incompatible_history is not None:
        raise RuntimeError("STAGE9_HISTORY_DOWNGRADE_BLOCKED")


def upgrade() -> None:
    _assert_explainable_ended_applications()

    op.add_column(
        "applications",
        sa.Column("final_outcome", sa.String(length=30), nullable=True),
    )
    op.create_index(
        "ix_applications_final_outcome",
        "applications",
        ["final_outcome"],
        unique=False,
    )

    for column in (
        sa.Column("interview_record_id", sa.Integer(), nullable=True),
        sa.Column("offer_record_id", sa.Integer(), nullable=True),
        sa.Column("from_lifecycle_status", sa.String(length=20), nullable=True),
        sa.Column("to_lifecycle_status", sa.String(length=20), nullable=True),
        sa.Column("from_final_outcome", sa.String(length=30), nullable=True),
        sa.Column("to_final_outcome", sa.String(length=30), nullable=True),
    ):
        op.add_column("stage_histories", column)

    op.drop_constraint(
        "ck_applications_recruitment_stage_allowed",
        "applications",
        type_="check",
    )
    op.create_check_constraint(
        "ck_applications_recruitment_stage_allowed",
        "applications",
        f"recruitment_stage IN ({STAGE_VALUES})",
    )
    op.drop_constraint(
        "ck_stage_histories_from_stage_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_from_stage_allowed",
        "stage_histories",
        f"from_recruitment_stage IS NULL OR from_recruitment_stage IN ({STAGE_VALUES})",
    )
    op.drop_constraint(
        "ck_stage_histories_to_stage_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_to_stage_allowed",
        "stage_histories",
        f"to_recruitment_stage IN ({STAGE_VALUES})",
    )

    op.create_table(
        "interview_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("interview_type", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=100),
            server_default="Asia/Shanghai",
            nullable=False,
        ),
        sa.Column("interviewer_names", postgresql.JSONB(), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("meeting_link", sa.String(length=2048), nullable=True),
        sa.Column("schedule_note", sa.Text(), nullable=True),
        sa.Column(
            "decision",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("feedback_summary", sa.Text(), nullable=True),
        sa.Column(
            "strengths",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "concerns",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "follow_up_questions",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("feedback_submitted_by_label", sa.String(length=100), nullable=True),
        sa.Column("feedback_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "round_number >= 1",
            name="ck_interview_records_round_positive",
        ),
        sa.CheckConstraint(
            "interview_type IN ('onsite', 'video', 'phone')",
            name="ck_interview_records_type_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'completed', 'canceled', 'no_show')",
            name="ck_interview_records_status_allowed",
        ),
        sa.CheckConstraint(
            "decision IN ('pending', 'next_round', 'proceed_offer', "
            "'rejected', 'candidate_withdrew')",
            name="ck_interview_records_decision_allowed",
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_interview_records_duration_range",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_interview_records_version_positive",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(interviewer_names) = 'array' AND "
            "jsonb_array_length(interviewer_names) BETWEEN 1 AND 10",
            name="ck_interview_records_interviewers_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(strengths) = 'array' AND jsonb_array_length(strengths) <= 20",
            name="ck_interview_records_strengths_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(concerns) = 'array' AND jsonb_array_length(concerns) <= 20",
            name="ck_interview_records_concerns_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(follow_up_questions) = 'array' AND "
            "jsonb_array_length(follow_up_questions) <= 20",
            name="ck_interview_records_follow_ups_array",
        ),
        sa.CheckConstraint(
            "(feedback_submitted_at IS NULL AND feedback_submitted_by_label IS NULL "
            "AND feedback_summary IS NULL AND decision = 'pending' "
            "AND jsonb_array_length(strengths) = 0 "
            "AND jsonb_array_length(concerns) = 0 "
            "AND jsonb_array_length(follow_up_questions) = 0) OR "
            "(feedback_submitted_at IS NOT NULL AND "
            "feedback_submitted_by_label IS NOT NULL AND "
            "feedback_summary IS NOT NULL AND status = 'completed')",
            name="ck_interview_records_feedback_consistent",
        ),
        sa.CheckConstraint(
            "status NOT IN ('canceled', 'no_show') OR decision = 'pending'",
            name="ck_interview_records_closed_status_pending_decision",
        ),
        sa.CheckConstraint(
            "feedback_submitted_at IS NULL OR feedback_submitted_at >= created_at",
            name="ck_interview_records_feedback_time_consistent",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_interview_records_update_time_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name="fk_interview_records_application_id_applications",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            "round_number",
            name="uq_interview_records_application_round",
        ),
    )
    op.create_index(
        "uq_interview_records_one_scheduled_per_application",
        "interview_records",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("status = 'scheduled'"),
    )
    op.create_index(
        "ix_interview_records_application_status_scheduled_start",
        "interview_records",
        ["application_id", "status", "scheduled_start_at"],
        unique=False,
    )

    op.create_table(
        "offer_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("position_title", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("salary_period", sa.String(length=20), nullable=False),
        sa.Column("base_salary_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("salary_months", sa.Numeric(4, 1), nullable=True),
        sa.Column("bonus_note", sa.Text(), nullable=True),
        sa.Column("benefits_note", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("expected_start_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_offer_records_version_number_positive",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_offer_records_version_positive",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'sent', 'accepted', 'declined', "
            "'withdrawn', 'expired')",
            name="ck_offer_records_status_allowed",
        ),
        sa.CheckConstraint(
            "salary_period IN ('monthly', 'annual')",
            name="ck_offer_records_salary_period_allowed",
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_offer_records_currency_format",
        ),
        sa.CheckConstraint(
            "base_salary_amount > 0",
            name="ck_offer_records_base_salary_positive",
        ),
        sa.CheckConstraint(
            "(salary_period = 'monthly' AND salary_months BETWEEN 1 AND 24) OR "
            "(salary_period = 'annual' AND salary_months IS NULL)",
            name="ck_offer_records_salary_months_consistent",
        ),
        sa.CheckConstraint(
            "expected_start_date >= valid_until",
            name="ck_offer_records_dates_consistent",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "responded_at IS NULL OR responded_at >= sent_at",
            name="ck_offer_records_response_time_consistent",
        ),
        sa.CheckConstraint(
            "closed_at IS NULL OR closed_at >= sent_at",
            name="ck_offer_records_close_time_consistent",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_offer_records_update_time_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name="fk_offer_records_application_id_applications",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            "version_number",
            name="uq_offer_records_application_version",
        ),
    )
    op.create_index(
        "uq_offer_records_one_active_per_application",
        "offer_records",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('draft', 'sent', 'accepted')"),
    )
    op.create_index(
        "ix_offer_records_application_status_valid_until",
        "offer_records",
        ["application_id", "status", "valid_until"],
        unique=False,
    )

    op.create_index(
        "ix_stage_histories_interview_record_id",
        "stage_histories",
        ["interview_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_stage_histories_offer_record_id",
        "stage_histories",
        ["offer_record_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_stage_histories_interview_record_id_interview_records",
        "stage_histories",
        "interview_records",
        ["interview_record_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_stage_histories_offer_record_id_offer_records",
        "stage_histories",
        "offer_records",
        ["offer_record_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_stage_histories_from_lifecycle_allowed",
        "stage_histories",
        "from_lifecycle_status IS NULL OR "
        "from_lifecycle_status IN ('active', 'ended', 'voided')",
    )
    op.create_check_constraint(
        "ck_stage_histories_to_lifecycle_allowed",
        "stage_histories",
        "to_lifecycle_status IS NULL OR "
        "to_lifecycle_status IN ('active', 'ended', 'voided')",
    )
    op.create_check_constraint(
        "ck_stage_histories_from_final_outcome_allowed",
        "stage_histories",
        f"from_final_outcome IS NULL OR from_final_outcome IN ({FINAL_OUTCOME_VALUES})",
    )
    op.create_check_constraint(
        "ck_stage_histories_to_final_outcome_allowed",
        "stage_histories",
        f"to_final_outcome IS NULL OR to_final_outcome IN ({FINAL_OUTCOME_VALUES})",
    )

    op.execute(
        sa.text(
            "UPDATE applications SET final_outcome = 'screening_rejected' "
            "WHERE lifecycle_status = 'ended' "
            "AND recruitment_stage = 'rejected' AND hr_decision = 'rejected'"
        )
    )
    op.create_check_constraint(
        "ck_applications_final_outcome_allowed",
        "applications",
        f"final_outcome IS NULL OR final_outcome IN ({FINAL_OUTCOME_VALUES})",
    )
    op.create_check_constraint(
        "ck_applications_lifecycle_final_outcome_consistent",
        "applications",
        "(lifecycle_status = 'active' AND final_outcome IS NULL) OR "
        "(lifecycle_status = 'ended' AND final_outcome IS NOT NULL) OR "
        "(lifecycle_status = 'voided' AND final_outcome IS NULL)",
    )
    op.create_check_constraint(
        "ck_applications_terminal_outcome_consistent",
        "applications",
        "(final_outcome IS DISTINCT FROM 'hired' OR "
        "(recruitment_stage = 'hired' AND hr_decision = 'passed')) AND "
        "(final_outcome IS DISTINCT FROM 'screening_rejected' OR "
        "(recruitment_stage = 'rejected' AND hr_decision = 'rejected')) AND "
        "(recruitment_stage IS DISTINCT FROM 'hired' OR "
        "(lifecycle_status = 'ended' AND final_outcome = 'hired' "
        "AND hr_decision = 'passed'))",
    )


def downgrade() -> None:
    _assert_safe_downgrade()

    for name in (
        "ck_applications_terminal_outcome_consistent",
        "ck_applications_lifecycle_final_outcome_consistent",
        "ck_applications_final_outcome_allowed",
    ):
        op.drop_constraint(name, "applications", type_="check")

    for name in (
        "ck_stage_histories_to_final_outcome_allowed",
        "ck_stage_histories_from_final_outcome_allowed",
        "ck_stage_histories_to_lifecycle_allowed",
        "ck_stage_histories_from_lifecycle_allowed",
    ):
        op.drop_constraint(name, "stage_histories", type_="check")

    op.drop_constraint(
        "fk_stage_histories_offer_record_id_offer_records",
        "stage_histories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_stage_histories_interview_record_id_interview_records",
        "stage_histories",
        type_="foreignkey",
    )
    op.drop_index("ix_stage_histories_offer_record_id", table_name="stage_histories")
    op.drop_index(
        "ix_stage_histories_interview_record_id",
        table_name="stage_histories",
    )

    op.drop_table("offer_records")
    op.drop_table("interview_records")

    for column_name in (
        "to_final_outcome",
        "from_final_outcome",
        "to_lifecycle_status",
        "from_lifecycle_status",
        "offer_record_id",
        "interview_record_id",
    ):
        op.drop_column("stage_histories", column_name)

    op.drop_index("ix_applications_final_outcome", table_name="applications")
    op.drop_column("applications", "final_outcome")

    op.drop_constraint(
        "ck_stage_histories_to_stage_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_to_stage_allowed",
        "stage_histories",
        "to_recruitment_stage IN "
        "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
    )
    op.drop_constraint(
        "ck_stage_histories_from_stage_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_from_stage_allowed",
        "stage_histories",
        "from_recruitment_stage IS NULL OR from_recruitment_stage IN "
        "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
    )
    op.drop_constraint(
        "ck_applications_recruitment_stage_allowed",
        "applications",
        type_="check",
    )
    op.create_check_constraint(
        "ck_applications_recruitment_stage_allowed",
        "applications",
        "recruitment_stage IN "
        "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
    )
