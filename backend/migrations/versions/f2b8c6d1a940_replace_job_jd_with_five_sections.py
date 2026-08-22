"""Replace the legacy Job JD fields with five plain-text sections.

Revision ID: f2b8c6d1a940
Revises: e4c7a1b9d632
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f2b8c6d1a940"
down_revision: str | None = "e4c7a1b9d632"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_empty_jobs_table(connection) -> None:
    job_count = connection.execute(sa.text("SELECT COUNT(*) FROM jobs")).scalar_one()
    if job_count:
        raise RuntimeError(
            "STAGE6_FIVE_SECTION_JD_REQUIRES_EMPTY_JOBS: "
            "jobs 表非空，禁止自动删除、覆盖或转换旧 JD"
        )


def upgrade() -> None:
    _require_empty_jobs_table(op.get_bind())

    op.add_column("jobs", sa.Column("job_background", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("job_responsibilities", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("candidate_requirements", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("preferred_qualifications", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("public_notes", sa.Text(), nullable=True))
    op.drop_column("jobs", "description")
    op.drop_column("jobs", "requirements")
    op.drop_column("jobs", "legacy_requirements")


def downgrade() -> None:
    _require_empty_jobs_table(op.get_bind())

    op.add_column("jobs", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column(
            "requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "legacy_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.drop_column("jobs", "job_background")
    op.drop_column("jobs", "job_responsibilities")
    op.drop_column("jobs", "candidate_requirements")
    op.drop_column("jobs", "preferred_qualifications")
    op.drop_column("jobs", "public_notes")
