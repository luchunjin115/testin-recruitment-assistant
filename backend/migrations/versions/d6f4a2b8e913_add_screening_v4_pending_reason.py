"""add screening v4 pending-confirmation waiting reason

Revision ID: d6f4a2b8e913
Revises: c7d9e2f4a681
Create Date: 2026-08-24 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d6f4a2b8e913"
down_revision: str | Sequence[str] | None = "c7d9e2f4a681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CONSTRAINT = "ck_screening_runs_waiting_reason_matches_status"
_V3_EXPRESSION = (
    "waiting_reason IS NULL OR "
    "(status = 'waiting_plan' AND waiting_reason IN "
    "('plan_missing', 'plan_generating', 'plan_failed', "
    "'plan_outdated', 'plan_contract_outdated')) OR "
    "(status = 'paused' AND waiting_reason = 'job_closed')"
)
_V4_EXPRESSION = (
    "waiting_reason IS NULL OR "
    "(status = 'waiting_plan' AND waiting_reason IN "
    "('plan_missing', 'plan_generating', 'plan_pending_confirmation', "
    "'plan_failed', 'plan_outdated', 'plan_contract_outdated')) OR "
    "(status = 'paused' AND waiting_reason = 'job_closed')"
)


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "screening_runs", type_="check")
    op.create_check_constraint(_CONSTRAINT, "screening_runs", _V4_EXPRESSION)


def downgrade() -> None:
    bind = op.get_bind()
    has_v4_reason = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM screening_runs "
            "WHERE waiting_reason = 'plan_pending_confirmation'"
            ")"
        )
    ).scalar_one()
    if has_v4_reason:
        raise RuntimeError("STAGE7_SCREENING_V4_DOWNGRADE_BLOCKED")
    op.drop_constraint(_CONSTRAINT, "screening_runs", type_="check")
    op.create_check_constraint(_CONSTRAINT, "screening_runs", _V3_EXPRESSION)
