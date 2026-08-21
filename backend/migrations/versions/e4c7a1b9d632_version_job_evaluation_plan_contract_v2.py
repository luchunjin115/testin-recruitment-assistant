"""Version JobEvaluationPlan persistence for extraction contract v2.

Revision ID: e4c7a1b9d632
Revises: d9a1f4c7e820
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e4c7a1b9d632"
down_revision: str | None = "d9a1f4c7e820"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_evaluation_plans",
        sa.Column(
            "free_text_coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "uq_job_evaluation_plans_job_jd_fingerprint",
        "job_evaluation_plans",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        ["job_id", "input_fingerprint"],
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_free_text_coverage_object",
        "job_evaluation_plans",
        "free_text_coverage IS NULL "
        "OR jsonb_typeof(free_text_coverage) = 'object'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v2_ready_has_free_text_coverage",
        "job_evaluation_plans",
        "schema_version <> '2.0' OR status <> 'ready' "
        "OR free_text_coverage IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_job_evaluation_plans_v2_ready_has_free_text_coverage",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_free_text_coverage_object",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_job_evaluation_plans_job_jd_fingerprint",
        "job_evaluation_plans",
        ["job_id", "jd_fingerprint"],
    )
    op.drop_column("job_evaluation_plans", "free_text_coverage")
