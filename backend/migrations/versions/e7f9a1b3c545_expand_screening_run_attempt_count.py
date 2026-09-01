"""expand screening run attempt count for one controlled content repair

Revision ID: e7f9a1b3c545
Revises: d6e8f0a2b434
Create Date: 2026-09-01 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e7f9a1b3c545"
down_revision: str | Sequence[str] | None = "d6e8f0a2b434"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_NAME = "ck_screening_runs_attempt_count_range"


def _replace_attempt_constraint(clause: str) -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        "screening_runs",
        type_="check",
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "screening_runs",
        clause,
    )


def upgrade() -> None:
    _replace_attempt_constraint("attempt_count BETWEEN 0 AND 3")


def downgrade() -> None:
    row = op.get_bind().execute(
        sa.text("SELECT 1 FROM screening_runs WHERE attempt_count > 2 LIMIT 1")
    ).first()
    if row is not None:
        raise RuntimeError("SCREENING_RUN_ATTEMPT_COUNT_DOWNGRADE_BLOCKED")
    _replace_attempt_constraint("attempt_count BETWEEN 0 AND 2")
