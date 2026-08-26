"""Add JobEvaluationPlan 5.0 lightweight criteria persistence.

Revision ID: a3b5c7d9e101
Revises: d6f4a2b8e913
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a3b5c7d9e101"
down_revision: str | None = "d6f4a2b8e913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_known_pre_v5_history(connection) -> None:
    unknown_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version IS NULL
               OR schema_version NOT IN ('1.0', '2.0', '3.0', '4.0')
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if unknown_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V5_UNKNOWN_HISTORY: "
            f"评价计划 #{unknown_plan_id} 不符合已知 1.0—4.0 历史合同"
        )


def _require_v5_free_downgrade(connection) -> None:
    incompatible_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version = '5.0'
               OR v5_criteria IS NOT NULL
               OR edit_version IS NOT NULL
               OR confirmed_at IS NOT NULL
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if incompatible_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V5_DOWNGRADE_BLOCKED: "
            f"评价计划 #{incompatible_plan_id} 需要 5.0 持久化合同"
        )


def upgrade() -> None:
    _require_known_pre_v5_history(op.get_bind())

    op.drop_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v4_payload",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_v4_has_no_legacy_payload",
        "job_evaluation_plans",
        type_="check",
    )

    op.add_column(
        "job_evaluation_plans",
        sa.Column(
            "v5_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "job_evaluation_plans",
        sa.Column("edit_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_evaluation_plans",
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        "schema_version IN ('1.0', '2.0', '3.0', '4.0', '5.0')",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v4_payload",
        "job_evaluation_plans",
        "schema_version IN ('4.0', '5.0') OR "
        "(requirement_facts IS NULL "
        "AND evaluation_criteria IS NULL "
        "AND coverage_review_summary IS NULL "
        "AND generation_audit IS NULL)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v4_has_no_legacy_payload",
        "job_evaluation_plans",
        "schema_version NOT IN ('4.0', '5.0') OR "
        "(items IS NULL "
        "AND structured_coverage IS NULL "
        "AND free_text_coverage IS NULL)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v5_criteria_array",
        "job_evaluation_plans",
        "v5_criteria IS NULL "
        "OR jsonb_typeof(v5_criteria) = 'array'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "job_evaluation_plans",
        "schema_version = '5.0' OR v5_criteria IS NULL",
    )


def downgrade() -> None:
    _require_v5_free_downgrade(op.get_bind())

    for constraint_name in (
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "ck_job_evaluation_plans_v5_criteria_array",
        "ck_job_evaluation_plans_v4_has_no_legacy_payload",
        "ck_job_evaluation_plans_legacy_has_no_v4_payload",
        "ck_job_evaluation_plans_schema_version_allowed",
    ):
        op.drop_constraint(
            constraint_name,
            "job_evaluation_plans",
            type_="check",
        )

    for column_name in ("confirmed_at", "edit_version", "v5_criteria"):
        op.drop_column("job_evaluation_plans", column_name)

    op.create_check_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        "schema_version IN ('1.0', '2.0', '3.0', '4.0')",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v4_payload",
        "job_evaluation_plans",
        "schema_version = '4.0' OR "
        "(requirement_facts IS NULL "
        "AND evaluation_criteria IS NULL "
        "AND coverage_review_summary IS NULL "
        "AND generation_audit IS NULL)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v4_has_no_legacy_payload",
        "job_evaluation_plans",
        "schema_version <> '4.0' OR "
        "(items IS NULL "
        "AND structured_coverage IS NULL "
        "AND free_text_coverage IS NULL)",
    )
