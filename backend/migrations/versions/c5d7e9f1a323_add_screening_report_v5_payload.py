"""add screening report 5.0 payload contract

Revision ID: c5d7e9f1a323
Revises: b4c6d8e0f212
Create Date: 2026-08-27 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5d7e9f1a323"
down_revision: str | Sequence[str] | None = "b4c6d8e0f212"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CONSTRAINT = "ck_screening_reports_v5_payload_matches_schema"
_EXPRESSION = (
    "(schema_version = '5.0' AND v5_report IS NOT NULL "
    "AND jsonb_typeof(v5_report) = 'object') OR "
    "(schema_version <> '5.0' AND v5_report IS NULL)"
)


def upgrade() -> None:
    op.add_column(
        "screening_reports",
        sa.Column("v5_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_check_constraint(_CONSTRAINT, "screening_reports", _EXPRESSION)


def downgrade() -> None:
    bind = op.get_bind()
    has_v5_report = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM screening_reports "
            "WHERE schema_version = '5.0' OR v5_report IS NOT NULL"
            ")"
        )
    ).scalar_one()
    if has_v5_report:
        raise RuntimeError("STAGE7_SCREENING_V5_DOWNGRADE_BLOCKED")
    op.drop_constraint(_CONSTRAINT, "screening_reports", type_="check")
    op.drop_column("screening_reports", "v5_report")
