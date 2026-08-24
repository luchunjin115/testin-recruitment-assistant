"""Add persistence contract for five-section JobEvaluationPlan 3.0.

Revision ID: a9e7d3c5b821
Revises: f2b8c6d1a940
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a9e7d3c5b821"
down_revision: str | None = "f2b8c6d1a940"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_known_legacy_history(connection) -> None:
    unknown_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version IS NULL
               OR schema_version NOT IN ('1.0', '2.0')
               OR jsonb_typeof(items) <> 'array'
               OR jsonb_typeof(warnings) <> 'array'
               OR jsonb_typeof(input_snapshot) <> 'object'
               OR jsonb_typeof(structured_coverage) <> 'object'
               OR (
                    free_text_coverage IS NOT NULL
                    AND jsonb_typeof(free_text_coverage) <> 'object'
               )
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if unknown_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V3_UNKNOWN_LEGACY_HISTORY: "
            f"评价计划 #{unknown_plan_id} 不符合已知 1.0/2.0 历史合同"
        )


def _require_v3_free_downgrade(connection) -> None:
    incompatible_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version = '3.0'
               OR structured_coverage IS NULL
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if incompatible_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V3_DOWNGRADE_BLOCKED: "
            f"评价计划 #{incompatible_plan_id} 需要 3.0 持久化合同"
        )


def upgrade() -> None:
    _require_known_legacy_history(op.get_bind())

    op.add_column(
        "job_evaluation_plans",
        sa.Column(
            "source_review_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.alter_column(
        "job_evaluation_plans",
        "structured_coverage",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=None,
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_source_review_summary_object",
        "job_evaluation_plans",
        "source_review_summary IS NULL "
        "OR jsonb_typeof(source_review_summary) = 'object'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        "schema_version IN ('1.0', '2.0', '3.0')",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v3_ready_has_source_review_summary",
        "job_evaluation_plans",
        "schema_version <> '3.0' OR status <> 'ready' "
        "OR source_review_summary IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v3_has_no_legacy_coverage",
        "job_evaluation_plans",
        "schema_version <> '3.0' OR "
        "(structured_coverage IS NULL AND free_text_coverage IS NULL)",
    )


def downgrade() -> None:
    _require_v3_free_downgrade(op.get_bind())

    op.drop_constraint(
        "ck_job_evaluation_plans_v3_has_no_legacy_coverage",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_v3_ready_has_source_review_summary",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_source_review_summary_object",
        "job_evaluation_plans",
        type_="check",
    )
    op.alter_column(
        "job_evaluation_plans",
        "structured_coverage",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    op.drop_column("job_evaluation_plans", "source_review_summary")
