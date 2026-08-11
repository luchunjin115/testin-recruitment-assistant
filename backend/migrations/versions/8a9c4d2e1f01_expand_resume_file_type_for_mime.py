"""expand resume file type for canonical MIME values

Revision ID: 8a9c4d2e1f01
Revises: bbd627449743
Create Date: 2026-08-09 13:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "8a9c4d2e1f01"
down_revision = "bbd627449743"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "resumes",
        "file_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "resumes",
        "file_type",
        existing_type=sa.String(length=100),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
