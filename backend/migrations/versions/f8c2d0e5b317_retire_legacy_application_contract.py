"""Retire legacy Application and ScreeningResult compatibility.

Revision ID: f8c2d0e5b317
Revises: e7b1c9d4a206
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f8c2d0e5b317"
down_revision: str | None = "e7b1c9d4a206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM applications
                    WHERE current_resume_id IS NULL OR source = 'legacy_migration'
                ) THEN
                    RAISE EXCEPTION 'legacy Application rows must be removed before f8c2d0e5b317';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM screening_results
                    WHERE application_id IS NULL OR resume_id IS NULL
                ) THEN
                    RAISE EXCEPTION 'legacy ScreeningResult rows must be removed before f8c2d0e5b317';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM job_screening_rubrics
                    WHERE source = 'legacy_migration'
                ) THEN
                    RAISE EXCEPTION 'legacy Rubric rows must be removed before f8c2d0e5b317';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM stage_histories
                    WHERE actor_type = 'migration'
                ) THEN
                    RAISE EXCEPTION 'legacy StageHistory rows must be removed before f8c2d0e5b317';
                END IF;
            END $$;
            """
        )
    )

    op.drop_constraint(
        "ck_applications_resume_required_unless_legacy",
        "applications",
        type_="check",
    )
    op.drop_constraint(
        "ck_applications_source_allowed",
        "applications",
        type_="check",
    )
    op.alter_column(
        "applications",
        "current_resume_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("applications", "legacy_stage")
    op.create_check_constraint(
        "ck_applications_source_allowed",
        "applications",
        "source IN ('hr_direct', 'hr_screening', 'public_apply')",
    )

    op.drop_index(
        "uq_screening_results_running_application",
        table_name="screening_results",
    )
    op.alter_column(
        "screening_results",
        "application_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "screening_results",
        "resume_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_index(
        "uq_screening_results_running_application",
        "screening_results",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("execution_status = 'screening'"),
    )

    op.drop_constraint(
        "ck_job_screening_rubrics_source_allowed",
        "job_screening_rubrics",
        type_="check",
    )
    op.create_check_constraint(
        "ck_job_screening_rubrics_source_allowed",
        "job_screening_rubrics",
        "source IN ('standard_template', 'technical_template', "
        "'non_technical_template', 'ai_generated', 'hr_manual')",
    )

    op.drop_constraint(
        "ck_stage_histories_actor_type_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_actor_type_allowed",
        "stage_histories",
        "actor_type IN ('hr', 'system')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_stage_histories_actor_type_allowed",
        "stage_histories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_stage_histories_actor_type_allowed",
        "stage_histories",
        "actor_type IN ('hr', 'system', 'migration')",
    )

    op.drop_constraint(
        "ck_job_screening_rubrics_source_allowed",
        "job_screening_rubrics",
        type_="check",
    )
    op.create_check_constraint(
        "ck_job_screening_rubrics_source_allowed",
        "job_screening_rubrics",
        "source IN ('standard_template', 'technical_template', "
        "'non_technical_template', 'ai_generated', 'hr_manual', "
        "'legacy_migration')",
    )

    op.drop_index(
        "uq_screening_results_running_application",
        table_name="screening_results",
    )
    op.alter_column(
        "screening_results",
        "resume_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "screening_results",
        "application_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_index(
        "uq_screening_results_running_application",
        "screening_results",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text(
            "execution_status = 'screening' AND application_id IS NOT NULL"
        ),
    )

    op.drop_constraint(
        "ck_applications_source_allowed",
        "applications",
        type_="check",
    )
    op.add_column(
        "applications",
        sa.Column("legacy_stage", sa.String(length=100), nullable=True),
    )
    op.alter_column(
        "applications",
        "current_resume_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_applications_source_allowed",
        "applications",
        "source IN ('hr_direct', 'hr_screening', 'public_apply', 'legacy_migration')",
    )
    op.create_check_constraint(
        "ck_applications_resume_required_unless_legacy",
        "applications",
        "source = 'legacy_migration' OR current_resume_id IS NOT NULL",
    )
