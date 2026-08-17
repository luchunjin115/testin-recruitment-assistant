"""add stage 7 application foundation

Revision ID: e7b1c9d4a206
Revises: c8e1a6f4d205
Create Date: 2026-08-17 16:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e7b1c9d4a206"
down_revision = "c8e1a6f4d205"
branch_labels = None
depends_on = None


DEFAULT_RUBRIC_WEIGHTS = {
    "must_have_requirements_weight": 40,
    "work_experience_relevance_weight": 25,
    "projects_and_capability_weight": 20,
    "preferred_qualifications_weight": 10,
    "keywords_and_additional_weight": 5,
}


def upgrade() -> None:
    op.create_table(
        "job_screening_rubrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "must_have_requirements_weight",
            sa.Integer(),
            server_default="40",
            nullable=False,
        ),
        sa.Column(
            "work_experience_relevance_weight",
            sa.Integer(),
            server_default="25",
            nullable=False,
        ),
        sa.Column(
            "projects_and_capability_weight",
            sa.Integer(),
            server_default="20",
            nullable=False,
        ),
        sa.Column(
            "preferred_qualifications_weight",
            sa.Integer(),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "keywords_and_additional_weight",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=20), server_default="1.0", nullable=False),
        sa.Column(
            "subcriteria_version",
            sa.String(length=20),
            server_default="1.0",
            nullable=False,
        ),
        sa.Column(
            "recommendation_thresholds_version",
            sa.String(length=20),
            server_default="1.0",
            nullable=False,
        ),
        sa.Column(
            "fairness_rules_version",
            sa.String(length=20),
            server_default="1.0",
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("change_reason", sa.String(length=50), nullable=False),
        sa.Column("change_detail", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_job_screening_rubrics_version_positive",
        ),
        sa.CheckConstraint(
            "must_have_requirements_weight BETWEEN 30 AND 50",
            name="ck_job_screening_rubrics_must_have_weight_range",
        ),
        sa.CheckConstraint(
            "work_experience_relevance_weight BETWEEN 15 AND 35",
            name="ck_job_screening_rubrics_work_weight_range",
        ),
        sa.CheckConstraint(
            "projects_and_capability_weight BETWEEN 10 AND 30",
            name="ck_job_screening_rubrics_project_weight_range",
        ),
        sa.CheckConstraint(
            "preferred_qualifications_weight BETWEEN 0 AND 20",
            name="ck_job_screening_rubrics_preferred_weight_range",
        ),
        sa.CheckConstraint(
            "keywords_and_additional_weight BETWEEN 0 AND 10",
            name="ck_job_screening_rubrics_additional_weight_range",
        ),
        sa.CheckConstraint(
            "must_have_requirements_weight + work_experience_relevance_weight + "
            "projects_and_capability_weight + preferred_qualifications_weight + "
            "keywords_and_additional_weight = 100",
            name="ck_job_screening_rubrics_weight_total",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "version",
            name="uq_job_screening_rubrics_job_version",
        ),
    )
    op.create_index(
        "ix_job_screening_rubrics_is_current",
        "job_screening_rubrics",
        ["is_current"],
        unique=False,
    )
    op.create_index(
        "ix_job_screening_rubrics_job_id",
        "job_screening_rubrics",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "uq_job_screening_rubrics_current_job",
        "job_screening_rubrics",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO job_screening_rubrics (
                job_id,
                version,
                must_have_requirements_weight,
                work_experience_relevance_weight,
                projects_and_capability_weight,
                preferred_qualifications_weight,
                keywords_and_additional_weight,
                schema_version,
                subcriteria_version,
                recommendation_thresholds_version,
                fairness_rules_version,
                is_current,
                change_reason,
                change_detail,
                created_by
            )
            SELECT
                id,
                1,
                40,
                25,
                20,
                10,
                5,
                '1.0',
                '1.0',
                '1.0',
                '1.0',
                true,
                'initial_default',
                '阶段 7 migration 为既有岗位创建默认 Rubric',
                'migration'
            FROM jobs
            ORDER BY id
            """
        )
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("current_resume_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column(
            "lifecycle_status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("recruitment_stage", sa.String(length=30), nullable=False),
        sa.Column(
            "ai_status",
            sa.String(length=20),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column("hr_decision", sa.String(length=20), nullable=False),
        sa.Column("current_screening_result_id", sa.Integer(), nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("legacy_stage", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('hr_direct', 'hr_screening', 'public_apply', 'legacy_migration')",
            name="ck_applications_source_allowed",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('active', 'ended', 'voided')",
            name="ck_applications_lifecycle_status_allowed",
        ),
        sa.CheckConstraint(
            "recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_applications_recruitment_stage_allowed",
        ),
        sa.CheckConstraint(
            "ai_status IN ('not_started', 'screening', 'completed', 'failed', 'blocked')",
            name="ck_applications_ai_status_allowed",
        ),
        sa.CheckConstraint(
            "hr_decision IN ('pending', 'passed', 'backup', 'rejected')",
            name="ck_applications_hr_decision_allowed",
        ),
        sa.CheckConstraint(
            "source = 'legacy_migration' OR current_resume_id IS NOT NULL",
            name="ck_applications_resume_required_unless_legacy",
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["current_resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(
            ["current_screening_result_id"],
            ["screening_results.id"],
            name="fk_applications_current_screening_result_id_screening_results",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "current_screening_result_id",
            name="uq_applications_current_screening_result_id",
        ),
    )
    for column_name in (
        "ai_status",
        "applied_at",
        "candidate_id",
        "current_resume_id",
        "hr_decision",
        "job_id",
        "lifecycle_status",
        "recruitment_stage",
        "source",
    ):
        op.create_index(
            f"ix_applications_{column_name}",
            "applications",
            [column_name],
            unique=False,
        )
    op.create_index(
        "uq_applications_active_candidate_job",
        "applications",
        ["candidate_id", "job_id"],
        unique=True,
        postgresql_where=sa.text("lifecycle_status = 'active'"),
    )

    screening_columns = (
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("resume_id", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "execution_status",
            sa.String(length=20),
            server_default="completed",
            nullable=False,
        ),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("evidence_coverage_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("hard_requirement_checks", postgresql.JSONB(), nullable=True),
        sa.Column("dimension_scores", postgresql.JSONB(), nullable=True),
        sa.Column("pending_questions", postgresql.JSONB(), nullable=True),
        sa.Column("resume_evidence", postgresql.JSONB(), nullable=True),
        sa.Column("job_evidence", postgresql.JSONB(), nullable=True),
        sa.Column("candidate_input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("resume_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("job_requirements_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("rubric_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("rules_version", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_config_version", sa.String(length=100), nullable=True),
        sa.Column("job_schema_version", sa.String(length=20), nullable=True),
        sa.Column("resume_schema_version", sa.String(length=20), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("trigger_reason", sa.Text(), nullable=True),
        sa.Column("force_rerun", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("actor_label", sa.String(length=100), nullable=True),
        sa.Column("is_outdated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("outdated_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in screening_columns:
        op.add_column("screening_results", column)

    op.drop_constraint(
        "uq_screening_candidate_job",
        "screening_results",
        type_="unique",
    )
    op.create_foreign_key(
        "fk_screening_results_application_id_applications",
        "screening_results",
        "applications",
        ["application_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_screening_results_resume_id_resumes",
        "screening_results",
        "resumes",
        ["resume_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_screening_results_application_attempt",
        "screening_results",
        ["application_id", "attempt_number"],
    )
    for name, condition in (
        ("ck_screening_results_attempt_positive", "attempt_number >= 1"),
        (
            "ck_screening_results_execution_status_allowed",
            "execution_status IN ('screening', 'completed', 'failed', 'blocked')",
        ),
        (
            "ck_screening_results_overall_score_range",
            "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
        ),
        (
            "ck_screening_results_evidence_coverage_range",
            "evidence_coverage_rate IS NULL OR evidence_coverage_rate BETWEEN 0 AND 1",
        ),
        (
            "ck_screening_results_duration_nonnegative",
            "duration_ms IS NULL OR duration_ms >= 0",
        ),
        (
            "ck_screening_results_prompt_tokens_nonnegative",
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
        ),
        (
            "ck_screening_results_completion_tokens_nonnegative",
            "completion_tokens IS NULL OR completion_tokens >= 0",
        ),
        (
            "ck_screening_results_total_tokens_nonnegative",
            "total_tokens IS NULL OR total_tokens >= 0",
        ),
        (
            "ck_screening_results_estimated_cost_nonnegative",
            "estimated_cost IS NULL OR estimated_cost >= 0",
        ),
    ):
        op.create_check_constraint(name, "screening_results", condition)

    for column_name in (
        "application_id",
        "error_code",
        "execution_status",
        "input_fingerprint",
        "is_outdated",
        "resume_id",
    ):
        op.create_index(
            f"ix_screening_results_{column_name}",
            "screening_results",
            [column_name],
            unique=False,
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

    op.create_table(
        "stage_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("from_recruitment_stage", sa.String(length=30), nullable=True),
        sa.Column("to_recruitment_stage", sa.String(length=30), nullable=False),
        sa.Column("from_hr_decision", sa.String(length=20), nullable=True),
        sa.Column("to_hr_decision", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("actor_label", sa.String(length=100), nullable=False),
        sa.Column("screening_result_id", sa.Integer(), nullable=True),
        sa.Column(
            "overrides_ai_recommendation",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "from_recruitment_stage IS NULL OR from_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_stage_histories_from_stage_allowed",
        ),
        sa.CheckConstraint(
            "to_recruitment_stage IN "
            "('applied', 'hr_review', 'screening_passed', 'backup', 'rejected')",
            name="ck_stage_histories_to_stage_allowed",
        ),
        sa.CheckConstraint(
            "from_hr_decision IS NULL OR from_hr_decision IN "
            "('pending', 'passed', 'backup', 'rejected')",
            name="ck_stage_histories_from_decision_allowed",
        ),
        sa.CheckConstraint(
            "to_hr_decision IN ('pending', 'passed', 'backup', 'rejected')",
            name="ck_stage_histories_to_decision_allowed",
        ),
        sa.CheckConstraint(
            "actor_type IN ('hr', 'system', 'migration')",
            name="ck_stage_histories_actor_type_allowed",
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["screening_result_id"], ["screening_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "actor_type",
        "application_id",
        "created_at",
        "reason_code",
        "screening_result_id",
    ):
        op.create_index(
            f"ix_stage_histories_{column_name}",
            "stage_histories",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "screening_result_id",
        "reason_code",
        "created_at",
        "application_id",
        "actor_type",
    ):
        op.drop_index(
            f"ix_stage_histories_{column_name}",
            table_name="stage_histories",
        )
    op.drop_table("stage_histories")

    op.drop_index(
        "uq_screening_results_running_application",
        table_name="screening_results",
    )
    for column_name in (
        "resume_id",
        "is_outdated",
        "input_fingerprint",
        "execution_status",
        "error_code",
        "application_id",
    ):
        op.drop_index(
            f"ix_screening_results_{column_name}",
            table_name="screening_results",
        )

    for name in (
        "ck_screening_results_estimated_cost_nonnegative",
        "ck_screening_results_total_tokens_nonnegative",
        "ck_screening_results_completion_tokens_nonnegative",
        "ck_screening_results_prompt_tokens_nonnegative",
        "ck_screening_results_duration_nonnegative",
        "ck_screening_results_evidence_coverage_range",
        "ck_screening_results_overall_score_range",
        "ck_screening_results_execution_status_allowed",
        "ck_screening_results_attempt_positive",
    ):
        op.drop_constraint(name, "screening_results", type_="check")
    op.drop_constraint(
        "uq_screening_results_application_attempt",
        "screening_results",
        type_="unique",
    )
    op.drop_constraint(
        "fk_screening_results_resume_id_resumes",
        "screening_results",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_screening_results_application_id_applications",
        "screening_results",
        type_="foreignkey",
    )

    for column_name in (
        "source",
        "recruitment_stage",
        "lifecycle_status",
        "job_id",
        "hr_decision",
        "current_resume_id",
        "candidate_id",
        "applied_at",
        "ai_status",
    ):
        op.drop_index(f"ix_applications_{column_name}", table_name="applications")
    op.drop_index(
        "uq_applications_active_candidate_job",
        table_name="applications",
    )
    op.drop_table("applications")

    for column_name in reversed(
        (
            "application_id",
            "resume_id",
            "attempt_number",
            "execution_status",
            "input_fingerprint",
            "evidence_coverage_rate",
            "hard_requirement_checks",
            "dimension_scores",
            "pending_questions",
            "resume_evidence",
            "job_evidence",
            "candidate_input_snapshot",
            "resume_snapshot",
            "job_requirements_snapshot",
            "rubric_snapshot",
            "rules_version",
            "prompt_version",
            "model_provider",
            "model_name",
            "model_config_version",
            "job_schema_version",
            "resume_schema_version",
            "error_code",
            "error_message",
            "started_at",
            "finished_at",
            "duration_ms",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost",
            "trigger_reason",
            "force_rerun",
            "actor_type",
            "actor_id",
            "actor_label",
            "is_outdated",
            "outdated_at",
        )
    ):
        op.drop_column("screening_results", column_name)
    op.create_unique_constraint(
        "uq_screening_candidate_job",
        "screening_results",
        ["candidate_id", "job_id"],
    )

    op.drop_index(
        "uq_job_screening_rubrics_current_job",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "ix_job_screening_rubrics_job_id",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "ix_job_screening_rubrics_is_current",
        table_name="job_screening_rubrics",
    )
    op.drop_table("job_screening_rubrics")
