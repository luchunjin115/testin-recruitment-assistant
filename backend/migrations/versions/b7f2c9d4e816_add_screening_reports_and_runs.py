"""Add the durable current screening report and run log.

Revision ID: b7f2c9d4e816
Revises: a6d4e8f2c713
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7f2c9d4e816"
down_revision: str | None = "a6d4e8f2c713"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "screening_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("job_evaluation_plan_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("display_label", sa.String(length=30), nullable=False),
        sa.Column("overall_summary", sa.Text(), nullable=False),
        sa.Column("requirement_assessments", postgresql.JSONB(), nullable=False),
        sa.Column("bonus_highlights", postgresql.JSONB(), nullable=False),
        sa.Column("tradeoff_reason", sa.Text(), nullable=True),
        sa.Column("interview_questions", postgresql.JSONB(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("jd_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("plan_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("resume_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("redaction_version", sa.String(length=100), nullable=False),
        sa.Column(
            "is_outdated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "outdated_reasons",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("outdated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_at",
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
            "overall_score BETWEEN 0 AND 100",
            name="ck_screening_reports_overall_score_range",
        ),
        sa.CheckConstraint(
            "display_label IN ('关联较弱', '存在明显差距', '部分匹配', "
            "'整体较匹配', '高度匹配')",
            name="ck_screening_reports_display_label_allowed",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(requirement_assessments) = 'array'",
            name="ck_screening_reports_requirements_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(bonus_highlights) = 'array'",
            name="ck_screening_reports_bonuses_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(interview_questions) = 'array'",
            name="ck_screening_reports_questions_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(outdated_reasons) = 'array'",
            name="ck_screening_reports_outdated_reasons_array",
        ),
        sa.CheckConstraint(
            "(is_outdated AND jsonb_array_length(outdated_reasons) > 0 "
            "AND outdated_at IS NOT NULL) OR "
            "(NOT is_outdated AND jsonb_array_length(outdated_reasons) = 0 "
            "AND outdated_at IS NULL)",
            name="ck_screening_reports_outdated_state_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name="fk_screening_reports_application_id_applications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_screening_reports_job_id_jobs", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_screening_reports_resume_id_resumes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_evaluation_plan_id"],
            ["job_evaluation_plans.id"],
            name="fk_screening_reports_plan_id_job_evaluation_plans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_screening_reports"),
        sa.UniqueConstraint(
            "application_id", name="uq_screening_reports_application_id"
        ),
    )
    op.create_index("ix_screening_reports_job_id", "screening_reports", ["job_id"])
    op.create_index("ix_screening_reports_resume_id", "screening_reports", ["resume_id"])
    op.create_index("ix_screening_reports_plan_id", "screening_reports", ["job_evaluation_plan_id"])
    op.create_index("ix_screening_reports_is_outdated", "screening_reports", ["is_outdated"])
    op.create_index("ix_screening_reports_input_fingerprint", "screening_reports", ["input_fingerprint"])

    op.create_table(
        "screening_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("job_evaluation_plan_id", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("redaction_version", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
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
            "trigger_type IN ('automatic', 'single_reassessment', 'batch_reassessment')",
            name="ck_screening_runs_trigger_type_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('waiting_resume', 'waiting_plan', 'queued', 'running', "
            "'succeeded', 'failed', 'paused')",
            name="ck_screening_runs_status_allowed",
        ),
        sa.CheckConstraint("attempt_count BETWEEN 0 AND 2", name="ck_screening_runs_attempt_count_range"),
        sa.CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="ck_screening_runs_input_tokens_nonnegative"),
        sa.CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="ck_screening_runs_output_tokens_nonnegative"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_screening_runs_duration_nonnegative"),
        sa.CheckConstraint(
            "status <> 'failed' OR (completed_at IS NOT NULL AND error_code IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_screening_runs_failed_has_safe_error",
        ),
        sa.CheckConstraint(
            "status <> 'succeeded' OR (completed_at IS NOT NULL AND error_code IS NULL AND error_message IS NULL)",
            name="ck_screening_runs_succeeded_is_clean",
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_screening_runs_application_id_applications", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_screening_runs_job_id_jobs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], name="fk_screening_runs_resume_id_resumes", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_evaluation_plan_id"], ["job_evaluation_plans.id"], name="fk_screening_runs_plan_id_job_evaluation_plans", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_screening_runs"),
    )
    op.create_index("ix_screening_runs_application_id", "screening_runs", ["application_id"])
    op.create_index("ix_screening_runs_job_id", "screening_runs", ["job_id"])
    op.create_index("ix_screening_runs_status", "screening_runs", ["status"])
    op.create_index("ix_screening_runs_created_at", "screening_runs", ["created_at"])
    op.create_index(
        "uq_screening_runs_active_input",
        "screening_runs",
        ["application_id", "input_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_screening_runs_active_input", table_name="screening_runs", postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.drop_index("ix_screening_runs_created_at", table_name="screening_runs")
    op.drop_index("ix_screening_runs_status", table_name="screening_runs")
    op.drop_index("ix_screening_runs_job_id", table_name="screening_runs")
    op.drop_index("ix_screening_runs_application_id", table_name="screening_runs")
    op.drop_table("screening_runs")
    op.drop_index("ix_screening_reports_input_fingerprint", table_name="screening_reports")
    op.drop_index("ix_screening_reports_is_outdated", table_name="screening_reports")
    op.drop_index("ix_screening_reports_plan_id", table_name="screening_reports")
    op.drop_index("ix_screening_reports_resume_id", table_name="screening_reports")
    op.drop_index("ix_screening_reports_job_id", table_name="screening_reports")
    op.drop_table("screening_reports")
