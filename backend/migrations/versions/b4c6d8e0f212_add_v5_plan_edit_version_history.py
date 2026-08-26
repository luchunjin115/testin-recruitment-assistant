"""Add 5.0 plan edit-version history and confirmation constraints.

Revision ID: b4c6d8e0f212
Revises: a3b5c7d9e101
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b4c6d8e0f212"
down_revision: str | None = "a3b5c7d9e101"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_valid_existing_v5_rows(connection) -> None:
    invalid_plan_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM job_evaluation_plans
            WHERE schema_version = '5.0'
              AND (
                edit_version IS NULL
                OR edit_version <= 0
                OR (status IN ('pending_confirmation', 'ready')
                    AND (v5_criteria IS NULL
                         OR jsonb_array_length(v5_criteria) = 0))
                OR (status IN ('generating', 'failed')
                    AND v5_criteria IS NOT NULL)
                OR (status = 'ready' AND confirmed_at IS NULL)
                OR (status <> 'ready' AND confirmed_at IS NOT NULL)
              )
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if invalid_plan_id is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V5_EDIT_CONTRACT_INVALID_HISTORY: "
            f"评价计划 #{invalid_plan_id} 不符合 7R5-D 版本合同"
        )


def _require_downgrade_unique_inputs(connection) -> None:
    duplicate = connection.execute(
        sa.text(
            """
            SELECT job_id, input_fingerprint
            FROM job_evaluation_plans
            GROUP BY job_id, input_fingerprint
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "STAGE7_PLAN_V5_EDIT_DOWNGRADE_BLOCKED: "
            "同一岗位和 JD 输入已经存在多个计划版本"
        )


def upgrade() -> None:
    _require_valid_existing_v5_rows(op.get_bind())

    op.drop_constraint(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        type_="unique",
    )
    op.create_index(
        "uq_job_evaluation_plans_legacy_job_input",
        "job_evaluation_plans",
        ["job_id", "input_fingerprint"],
        unique=True,
        postgresql_where=sa.text("schema_version <> '5.0'"),
    )
    op.create_index(
        "uq_job_evaluation_plans_v5_job_input_edit_version",
        "job_evaluation_plans",
        ["job_id", "input_fingerprint", "edit_version"],
        unique=True,
        postgresql_where=sa.text("schema_version = '5.0'"),
    )

    op.drop_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "job_evaluation_plans",
        type_="check",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "job_evaluation_plans",
        "schema_version = '5.0' OR "
        "(v5_criteria IS NULL AND edit_version IS NULL "
        "AND confirmed_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v5_positive_edit_version",
        "job_evaluation_plans",
        "schema_version <> '5.0' OR "
        "(edit_version IS NOT NULL AND edit_version > 0)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v5_complete_payload",
        "job_evaluation_plans",
        "schema_version <> '5.0' "
        "OR status NOT IN ('pending_confirmation', 'ready') "
        "OR (v5_criteria IS NOT NULL "
        "AND jsonb_array_length(v5_criteria) > 0)",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v5_no_partial_failed_payload",
        "job_evaluation_plans",
        "schema_version <> '5.0' "
        "OR status NOT IN ('generating', 'failed') "
        "OR v5_criteria IS NULL",
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_v5_confirmation_timestamp",
        "job_evaluation_plans",
        "schema_version <> '5.0' OR "
        "((status = 'ready' AND confirmed_at IS NOT NULL) "
        "OR (status <> 'ready' AND confirmed_at IS NULL))",
    )


def downgrade() -> None:
    _require_downgrade_unique_inputs(op.get_bind())

    for constraint_name in (
        "ck_job_evaluation_plans_v5_confirmation_timestamp",
        "ck_job_evaluation_plans_v5_no_partial_failed_payload",
        "ck_job_evaluation_plans_v5_complete_payload",
        "ck_job_evaluation_plans_v5_positive_edit_version",
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
    ):
        op.drop_constraint(
            constraint_name,
            "job_evaluation_plans",
            type_="check",
        )

    op.drop_index(
        "uq_job_evaluation_plans_v5_job_input_edit_version",
        table_name="job_evaluation_plans",
    )
    op.drop_index(
        "uq_job_evaluation_plans_legacy_job_input",
        table_name="job_evaluation_plans",
    )
    op.create_unique_constraint(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        ["job_id", "input_fingerprint"],
    )
    op.create_check_constraint(
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "job_evaluation_plans",
        "schema_version = '5.0' OR v5_criteria IS NULL",
    )
