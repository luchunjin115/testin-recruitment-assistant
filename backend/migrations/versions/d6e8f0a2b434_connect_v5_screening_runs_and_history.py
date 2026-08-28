"""connect 5.0 screening runs and stage history

Revision ID: d6e8f0a2b434
Revises: c5d7e9f1a323
Create Date: 2026-08-27 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d6e8f0a2b434"
down_revision: str | Sequence[str] | None = "c5d7e9f1a323"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _assert_no_duplicate_nonterminal_runs() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            "SELECT application_id FROM screening_runs "
            "WHERE status IN ('waiting_resume', 'waiting_plan', 'queued', "
            "'running', 'paused') GROUP BY application_id HAVING COUNT(*) > 1 "
            "LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError("STAGE7_V5_NONTERMINAL_RUN_CONFLICT")


def _assert_no_report_history_links() -> None:
    linked = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM stage_histories WHERE report_id IS NOT NULL LIMIT 1"
        )
    ).first()
    if linked is not None:
        raise RuntimeError("STAGE7_V5_HISTORY_DOWNGRADE_BLOCKED")


def _assert_no_report_history_rows() -> None:
    history = op.get_bind().execute(
        sa.text(
            "SELECT application_id FROM screening_reports "
            "GROUP BY application_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if history is not None:
        raise RuntimeError("STAGE7_V5_REPORT_HISTORY_DOWNGRADE_BLOCKED")


def upgrade() -> None:
    _assert_no_duplicate_nonterminal_runs()
    op.drop_index("uq_screening_runs_active_input", table_name="screening_runs")
    op.create_index(
        "uq_screening_runs_active_application",
        "screening_runs",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('waiting_resume', 'waiting_plan', 'queued', "
            "'running', 'paused')"
        ),
    )
    op.add_column(
        "screening_reports",
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.drop_constraint(
        "uq_screening_reports_application_id",
        "screening_reports",
        type_="unique",
    )
    op.create_index(
        "uq_screening_reports_current_application",
        "screening_reports",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.add_column(
        "stage_histories",
        sa.Column("report_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_stage_histories_report_id",
        "stage_histories",
        ["report_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_stage_histories_report_id_screening_reports",
        "stage_histories",
        "screening_reports",
        ["report_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    _assert_no_report_history_links()
    _assert_no_report_history_rows()
    op.drop_constraint(
        "fk_stage_histories_report_id_screening_reports",
        "stage_histories",
        type_="foreignkey",
    )
    op.drop_index("ix_stage_histories_report_id", table_name="stage_histories")
    op.drop_column("stage_histories", "report_id")
    op.drop_index(
        "uq_screening_reports_current_application",
        table_name="screening_reports",
    )
    op.create_unique_constraint(
        "uq_screening_reports_application_id",
        "screening_reports",
        ["application_id"],
    )
    op.drop_column("screening_reports", "is_current")
    op.drop_index(
        "uq_screening_runs_active_application",
        table_name="screening_runs",
    )
    op.create_index(
        "uq_screening_runs_active_input",
        "screening_runs",
        ["application_id", "input_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
