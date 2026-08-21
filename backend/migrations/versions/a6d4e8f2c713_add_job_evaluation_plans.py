"""Add the JD-bound JobEvaluationPlan data model.

Revision ID: a6d4e8f2c713
Revises: c4a9d8e7f621
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a6d4e8f2c713"
down_revision: str | None = "c4a9d8e7f621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_evaluation_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("jd_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="generating",
            nullable=False,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "items",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "structured_coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "input_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('generating', 'ready', 'failed', 'outdated')",
            name="ck_job_evaluation_plans_status_allowed",
        ),
        sa.CheckConstraint(
            "status <> 'outdated' OR is_current = false",
            name="ck_job_evaluation_plans_outdated_not_current",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_evaluation_plans_job_id_jobs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_evaluation_plans"),
        sa.UniqueConstraint(
            "job_id",
            "jd_fingerprint",
            name="uq_job_evaluation_plans_job_jd_fingerprint",
        ),
    )
    op.create_index(
        "ix_job_evaluation_plans_job_id",
        "job_evaluation_plans",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_evaluation_plans_status",
        "job_evaluation_plans",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_job_evaluation_plans_current_job",
        "job_evaluation_plans",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_job_evaluation_plans_current_job",
        table_name="job_evaluation_plans",
        postgresql_where=sa.text("is_current = true"),
    )
    op.drop_index(
        "ix_job_evaluation_plans_status",
        table_name="job_evaluation_plans",
    )
    op.drop_index(
        "ix_job_evaluation_plans_job_id",
        table_name="job_evaluation_plans",
    )
    op.drop_table("job_evaluation_plans")
