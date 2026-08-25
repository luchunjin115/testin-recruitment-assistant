"""Add JobEvaluationPlan 4.0 fact and criterion persistence.

Revision ID: c7d9e2f4a681
Revises: b4e8c2d7f913
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c7d9e2f4a681"
down_revision: str | None = "b4e8c2d7f913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_known_pre_v4_history(connection) -> None:
    unknown_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version IS NULL
               OR schema_version NOT IN ('1.0', '2.0', '3.0')
               OR jsonb_typeof(items) <> 'array'
               OR jsonb_typeof(warnings) <> 'array'
               OR jsonb_typeof(input_snapshot) <> 'object'
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if unknown_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V4_UNKNOWN_HISTORY: "
            f"评价计划 #{unknown_plan_id} 不符合已知 1.0—3.0 历史合同"
        )


def _require_v4_free_downgrade(connection) -> None:
    incompatible_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version = '4.0'
               OR items IS NULL
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if incompatible_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V4_DOWNGRADE_BLOCKED: "
            f"评价计划 #{incompatible_plan_id} 需要 4.0 持久化合同"
        )


def upgrade() -> None:
    _require_known_pre_v4_history(op.get_bind())

    op.drop_constraint(
        "ck_job_evaluation_plans_status_allowed",
        "job_evaluation_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        type_="check",
    )
    op.alter_column(
        "job_evaluation_plans",
        "items",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        existing_server_default=sa.text("'[]'::jsonb"),
    )

    for column_name in (
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
    ):
        op.add_column(
            "job_evaluation_plans",
            sa.Column(
                column_name,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )

    op.create_check_constraint(
        "ck_job_evaluation_plans_status_allowed",
        "job_evaluation_plans",
        "status IN ("
        "'generating', 'pending_confirmation', 'ready', 'failed', 'outdated'"
        ")",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        "schema_version IN ('1.0', '2.0', '3.0', '4.0')",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_requirement_facts_array",
        "job_evaluation_plans",
        "requirement_facts IS NULL "
        "OR jsonb_typeof(requirement_facts) = 'array'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_evaluation_criteria_array",
        "job_evaluation_plans",
        "evaluation_criteria IS NULL "
        "OR jsonb_typeof(evaluation_criteria) = 'array'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_coverage_review_summary_object",
        "job_evaluation_plans",
        "coverage_review_summary IS NULL "
        "OR jsonb_typeof(coverage_review_summary) = 'object'",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_generation_audit_object",
        "job_evaluation_plans",
        "generation_audit IS NULL "
        "OR jsonb_typeof(generation_audit) = 'object'",
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
    op.create_check_constraint(
        "ck_job_evaluation_plans_v4_complete_payload",
        "job_evaluation_plans",
        "schema_version <> '4.0' "
        "OR status NOT IN ('pending_confirmation', 'ready') "
        "OR (requirement_facts IS NOT NULL "
        "AND jsonb_array_length(requirement_facts) > 0 "
        "AND evaluation_criteria IS NOT NULL "
        "AND jsonb_array_length(evaluation_criteria) > 0 "
        "AND source_review_summary IS NOT NULL "
        "AND coverage_review_summary IS NOT NULL "
        "AND generation_audit IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v4_no_partial_failed_payload",
        "job_evaluation_plans",
        "schema_version <> '4.0' "
        "OR status NOT IN ('generating', 'failed') "
        "OR (requirement_facts IS NULL "
        "AND evaluation_criteria IS NULL "
        "AND source_review_summary IS NULL "
        "AND coverage_review_summary IS NULL "
        "AND generation_audit IS NULL)",
    )


def downgrade() -> None:
    _require_v4_free_downgrade(op.get_bind())

    for constraint_name in (
        "ck_job_evaluation_plans_v4_no_partial_failed_payload",
        "ck_job_evaluation_plans_v4_complete_payload",
        "ck_job_evaluation_plans_v4_has_no_legacy_payload",
        "ck_job_evaluation_plans_legacy_has_no_v4_payload",
        "ck_job_evaluation_plans_generation_audit_object",
        "ck_job_evaluation_plans_coverage_review_summary_object",
        "ck_job_evaluation_plans_evaluation_criteria_array",
        "ck_job_evaluation_plans_requirement_facts_array",
        "ck_job_evaluation_plans_schema_version_allowed",
        "ck_job_evaluation_plans_status_allowed",
    ):
        op.drop_constraint(
            constraint_name,
            "job_evaluation_plans",
            type_="check",
        )

    op.create_check_constraint(
        "ck_job_evaluation_plans_status_allowed",
        "job_evaluation_plans",
        "status IN ('generating', 'ready', 'failed', 'outdated')",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_schema_version_allowed",
        "job_evaluation_plans",
        "schema_version IN ('1.0', '2.0', '3.0')",
    )

    for column_name in (
        "generation_audit",
        "coverage_review_summary",
        "evaluation_criteria",
        "requirement_facts",
    ):
        op.drop_column("job_evaluation_plans", column_name)

    op.alter_column(
        "job_evaluation_plans",
        "items",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        existing_server_default=sa.text("'[]'::jsonb"),
    )
