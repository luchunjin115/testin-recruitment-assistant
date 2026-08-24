"""Persist stable ScreeningRun waiting reasons.

Revision ID: b4e8c2d7f913
Revises: a9e7d3c5b821
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b4e8c2d7f913"
down_revision: str | None = "a9e7d3c5b821"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "screening_runs",
        sa.Column("waiting_reason", sa.String(length=50), nullable=True),
    )
    op.create_check_constraint(
        "ck_screening_runs_waiting_reason_matches_status",
        "screening_runs",
        "waiting_reason IS NULL OR "
        "(status = 'waiting_plan' AND waiting_reason IN "
        "('plan_missing', 'plan_generating', 'plan_failed', "
        "'plan_outdated', 'plan_contract_outdated')) OR "
        "(status = 'paused' AND waiting_reason = 'job_closed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_screening_runs_waiting_reason_matches_status",
        "screening_runs",
        type_="check",
    )
    op.drop_column("screening_runs", "waiting_reason")
