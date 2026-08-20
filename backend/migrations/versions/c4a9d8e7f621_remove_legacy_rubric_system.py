"""Remove the superseded stage 7 Rubric and scoring system.

Revision ID: c4a9d8e7f621
Revises: f8c2d0e5b317
Create Date: 2026-08-20

The downgrade recreates the retired empty structure for development rollback. It
cannot restore rows removed by the upgrade.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4a9d8e7f621"
down_revision: str | None = "f8c2d0e5b317"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "reports",
        "report_type",
        existing_type=sa.String(length=20),
        server_default="general",
        existing_nullable=False,
    )

    op.drop_constraint(
        "fk_applications_current_screening_result_id_screening_results",
        "applications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_applications_current_screening_result_id",
        "applications",
        type_="unique",
    )
    op.drop_index("ix_applications_ai_status", table_name="applications")
    op.drop_constraint(
        "ck_applications_ai_status_allowed",
        "applications",
        type_="check",
    )
    op.drop_column("applications", "current_screening_result_id")
    op.drop_column("applications", "ai_status")

    op.drop_constraint(
        "stage_histories_screening_result_id_fkey",
        "stage_histories",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_stage_histories_screening_result_id",
        table_name="stage_histories",
    )
    op.drop_column("stage_histories", "screening_result_id")
    op.drop_column("stage_histories", "overrides_ai_recommendation")

    op.drop_constraint(
        "reports_screening_id_fkey",
        "reports",
        type_="foreignkey",
    )
    op.drop_index("ix_reports_screening_id", table_name="reports")
    op.drop_column("reports", "screening_id")

    op.drop_table("screening_results")
    op.drop_table("job_screening_rubrics")


def downgrade() -> None:
    _create_legacy_job_screening_rubrics()
    _create_legacy_screening_results()

    op.add_column(
        "applications",
        sa.Column(
            "ai_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "applications",
        sa.Column("current_screening_result_id", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_applications_ai_status_allowed",
        "applications",
        "ai_status IN ('not_started', 'screening', 'completed', 'failed', 'blocked')",
    )
    op.create_index(
        "ix_applications_ai_status",
        "applications",
        ["ai_status"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_applications_current_screening_result_id",
        "applications",
        ["current_screening_result_id"],
    )
    op.create_foreign_key(
        "fk_applications_current_screening_result_id_screening_results",
        "applications",
        "screening_results",
        ["current_screening_result_id"],
        ["id"],
    )

    op.add_column(
        "stage_histories",
        sa.Column(
            "overrides_ai_recommendation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "stage_histories",
        sa.Column("screening_result_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_stage_histories_screening_result_id",
        "stage_histories",
        ["screening_result_id"],
        unique=False,
    )
    op.create_foreign_key(
        "stage_histories_screening_result_id_fkey",
        "stage_histories",
        "screening_results",
        ["screening_result_id"],
        ["id"],
    )

    op.add_column(
        "reports",
        sa.Column("screening_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_reports_screening_id",
        "reports",
        ["screening_id"],
        unique=False,
    )
    op.create_foreign_key(
        "reports_screening_id_fkey",
        "reports",
        "screening_results",
        ["screening_id"],
        ["id"],
    )
    op.alter_column(
        "reports",
        "report_type",
        existing_type=sa.String(length=20),
        server_default="screening",
        existing_nullable=False,
    )


def _create_legacy_job_screening_rubrics() -> None:
    op.create_table(
        "job_screening_rubrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("must_have_requirements_weight", sa.Integer(), server_default="40", nullable=False),
        sa.Column("work_experience_relevance_weight", sa.Integer(), server_default="25", nullable=False),
        sa.Column("projects_and_capability_weight", sa.Integer(), server_default="20", nullable=False),
        sa.Column("preferred_qualifications_weight", sa.Integer(), server_default="10", nullable=False),
        sa.Column("keywords_and_additional_weight", sa.Integer(), server_default="5", nullable=False),
        sa.Column("schema_version", sa.String(length=20), server_default="2.0", nullable=False),
        sa.Column("subcriteria_version", sa.String(length=20), server_default="2.0", nullable=False),
        sa.Column("recommendation_thresholds_version", sa.String(length=20), server_default="1.0", nullable=False),
        sa.Column("fairness_rules_version", sa.String(length=20), server_default="1.0", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source", sa.String(length=30), server_default="standard_template", nullable=False),
        sa.Column("template_key", sa.String(length=30), server_default="standard", nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("semantic_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("job_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("generation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("change_reason", sa.String(length=50), nullable=False),
        sa.Column("change_detail", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("confirmed_by", sa.String(length=100), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_job_screening_rubrics_version_positive"),
        sa.CheckConstraint("must_have_requirements_weight BETWEEN 30 AND 50", name="ck_job_screening_rubrics_must_have_weight_range"),
        sa.CheckConstraint("work_experience_relevance_weight BETWEEN 15 AND 35", name="ck_job_screening_rubrics_work_weight_range"),
        sa.CheckConstraint("projects_and_capability_weight BETWEEN 10 AND 30", name="ck_job_screening_rubrics_project_weight_range"),
        sa.CheckConstraint("preferred_qualifications_weight BETWEEN 0 AND 20", name="ck_job_screening_rubrics_preferred_weight_range"),
        sa.CheckConstraint("keywords_and_additional_weight BETWEEN 0 AND 10", name="ck_job_screening_rubrics_additional_weight_range"),
        sa.CheckConstraint("must_have_requirements_weight + work_experience_relevance_weight + projects_and_capability_weight + preferred_qualifications_weight + keywords_and_additional_weight = 100", name="ck_job_screening_rubrics_weight_total"),
        sa.CheckConstraint("source IN ('standard_template', 'technical_template', 'non_technical_template', 'ai_generated', 'hr_manual')", name="ck_job_screening_rubrics_source_allowed"),
        sa.CheckConstraint("status IN ('draft', 'active', 'archived', 'abandoned')", name="ck_job_screening_rubrics_status_allowed"),
        sa.CheckConstraint("template_key IS NULL OR template_key IN ('standard', 'technical', 'non_technical')", name="ck_job_screening_rubrics_template_allowed"),
        sa.CheckConstraint("jsonb_typeof(semantic_items) = 'array'", name="ck_job_screening_rubrics_semantic_items_array"),
        sa.CheckConstraint("status NOT IN ('active', 'archived') OR jsonb_array_length(semantic_items) BETWEEN 4 AND 10", name="ck_job_screening_rubrics_published_item_count"),
        sa.CheckConstraint("(status = 'active' AND is_current = true) OR (status <> 'active' AND is_current = false)", name="ck_job_screening_rubrics_current_status_consistent"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "version", name="uq_job_screening_rubrics_job_version"),
    )
    for column_name in ("is_current", "is_stale", "job_fingerprint", "job_id", "status"):
        op.create_index(f"ix_job_screening_rubrics_{column_name}", "job_screening_rubrics", [column_name])
    op.create_index("uq_job_screening_rubrics_current_job", "job_screening_rubrics", ["job_id"], unique=True, postgresql_where=sa.text("is_current = true"))
    op.create_index("uq_job_screening_rubrics_draft_job", "job_screening_rubrics", ["job_id"], unique=True, postgresql_where=sa.text("status = 'draft'"))


def _create_legacy_screening_results() -> None:
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("hard_pass", sa.Boolean(), nullable=True),
        sa.Column("skill_score", sa.Integer(), nullable=True),
        sa.Column("experience_score", sa.Integer(), nullable=True),
        sa.Column("project_score", sa.Integer(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("raw_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("execution_status", sa.String(length=20), server_default="completed", nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("evidence_coverage_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("hard_requirement_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pending_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resume_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("job_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("candidate_input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resume_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("job_requirements_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rubric_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column("force_rerun", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("actor_label", sa.String(length=100), nullable=True),
        sa.Column("is_outdated", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("outdated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number >= 1", name="ck_screening_results_attempt_positive"),
        sa.CheckConstraint("execution_status IN ('screening', 'completed', 'failed', 'blocked')", name="ck_screening_results_execution_status_allowed"),
        sa.CheckConstraint("overall_score IS NULL OR overall_score BETWEEN 0 AND 100", name="ck_screening_results_overall_score_range"),
        sa.CheckConstraint("evidence_coverage_rate IS NULL OR evidence_coverage_rate BETWEEN 0 AND 1", name="ck_screening_results_evidence_coverage_range"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_screening_results_duration_nonnegative"),
        sa.CheckConstraint("prompt_tokens IS NULL OR prompt_tokens >= 0", name="ck_screening_results_prompt_tokens_nonnegative"),
        sa.CheckConstraint("completion_tokens IS NULL OR completion_tokens >= 0", name="ck_screening_results_completion_tokens_nonnegative"),
        sa.CheckConstraint("total_tokens IS NULL OR total_tokens >= 0", name="ck_screening_results_total_tokens_nonnegative"),
        sa.CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0", name="ck_screening_results_estimated_cost_nonnegative"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_screening_results_application_id_applications"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], name="fk_screening_results_resume_id_resumes"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "attempt_number", name="uq_screening_results_application_attempt"),
    )
    for column_name in (
        "application_id", "candidate_id", "error_code", "execution_status",
        "input_fingerprint", "is_outdated", "job_id", "overall_score",
        "recommendation", "resume_id",
    ):
        op.create_index(f"ix_screening_results_{column_name}", "screening_results", [column_name])
    op.create_index("uq_screening_results_running_application", "screening_results", ["application_id"], unique=True, postgresql_where=sa.text("execution_status = 'screening'"))
