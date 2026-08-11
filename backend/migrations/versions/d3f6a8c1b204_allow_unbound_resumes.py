"""allow resumes before candidate confirmation

Revision ID: d3f6a8c1b204
Revises: 8a9c4d2e1f01
Create Date: 2026-08-09 16:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "d3f6a8c1b204"
down_revision = "8a9c4d2e1f01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "resumes",
        "candidate_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "resumes",
        "candidate_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
