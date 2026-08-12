"""add independent resume structure state

Revision ID: f5a7c9e2d104
Revises: d3f6a8c1b204
Create Date: 2026-08-12 16:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "f5a7c9e2d104"
down_revision = "d3f6a8c1b204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column(
            "structure_status",
            sa.String(length=30),
            server_default="not_started",
            nullable=False,
        ),
    )
    op.add_column("resumes", sa.Column("structure_error", sa.Text(), nullable=True))
    op.add_column(
        "resumes",
        sa.Column("structure_attempt_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "resumes",
        sa.Column("structure_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resumes",
        sa.Column("structured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resumes",
        sa.Column("structure_schema_version", sa.String(length=20), nullable=True),
    )
    op.create_index(
        op.f("ix_resumes_structure_status"),
        "resumes",
        ["structure_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resumes_structure_status"), table_name="resumes")
    op.drop_column("resumes", "structure_schema_version")
    op.drop_column("resumes", "structured_at")
    op.drop_column("resumes", "structure_started_at")
    op.drop_column("resumes", "structure_attempt_id")
    op.drop_column("resumes", "structure_error")
    op.drop_column("resumes", "structure_status")
