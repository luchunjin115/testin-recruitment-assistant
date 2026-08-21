"""Add the frozen application-time context to screening audit records.

Revision ID: d9a1f4c7e820
Revises: b7f2c9d4e816
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d9a1f4c7e820"
down_revision: str | None = "b7f2c9d4e816"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "screening_reports",
        sa.Column("evaluation_reference_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "screening_reports",
        sa.Column("evaluation_timezone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "screening_reports",
        sa.Column(
            "experience_period_facts_rule_version",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "screening_reports",
        sa.Column("experience_period_facts", postgresql.JSONB(), nullable=True),
    )
    op.create_check_constraint(
        "ck_screening_reports_experience_facts_object",
        "screening_reports",
        "experience_period_facts IS NULL OR "
        "jsonb_typeof(experience_period_facts) = 'object'",
    )

    op.add_column(
        "screening_runs",
        sa.Column("evaluation_reference_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "screening_runs",
        sa.Column("evaluation_timezone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "screening_runs",
        sa.Column(
            "experience_period_facts_rule_version",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "screening_runs",
        sa.Column(
            "experience_period_facts_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )

    # The only historical value that can be reconstructed honestly is the
    # Application's immutable applied_at.  Timezone, rule version, snapshots,
    # and fingerprints remain NULL for legacy rows because they were not used
    # by those evaluations.
    op.execute(
        sa.text(
            "UPDATE screening_reports AS report "
            "SET evaluation_reference_at = application.applied_at "
            "FROM applications AS application "
            "WHERE application.id = report.application_id "
            "AND report.evaluation_reference_at IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE screening_runs AS run "
            "SET evaluation_reference_at = application.applied_at "
            "FROM applications AS application "
            "WHERE application.id = run.application_id "
            "AND run.evaluation_reference_at IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("screening_runs", "experience_period_facts_fingerprint")
    op.drop_column("screening_runs", "experience_period_facts_rule_version")
    op.drop_column("screening_runs", "evaluation_timezone")
    op.drop_column("screening_runs", "evaluation_reference_at")
    op.drop_constraint(
        "ck_screening_reports_experience_facts_object",
        "screening_reports",
        type_="check",
    )
    op.drop_column("screening_reports", "experience_period_facts")
    op.drop_column("screening_reports", "experience_period_facts_rule_version")
    op.drop_column("screening_reports", "evaluation_timezone")
    op.drop_column("screening_reports", "evaluation_reference_at")
