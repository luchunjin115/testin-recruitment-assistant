"""add stage 7 application foundation

Revision ID: e7b1c9d4a206
Revises: c8e1a6f4d205
Create Date: 2026-08-17 16:00:00
"""

from __future__ import annotations

import json

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

DEFAULT_STANDARD_SEMANTIC_ITEMS = [
    {
        "key": "responsibility_alignment",
        "name": "岗位职责相关性",
        "description": "评价候选人既往实际职责与当前岗位核心职责的相关程度。",
        "dimension": "work_experience_relevance",
        "max_score": 10,
        "suggested_share": 50,
        "high_score_anchor": "有多段直接相关经历，并清楚说明本人承担的核心职责。",
        "mid_score_anchor": "有部分相关职责，但覆盖范围、持续时间或本人角色不够完整。",
        "low_score_anchor": "经历与岗位职责关联较弱，或只有笼统表述而缺少本人职责证据。",
        "source": "template",
    },
    {
        "key": "experience_depth",
        "name": "相关经验深度",
        "description": "评价候选人是否在岗位相关场景中承担过有实质深度的工作。",
        "dimension": "work_experience_relevance",
        "max_score": 10,
        "suggested_share": 50,
        "high_score_anchor": "长期承担关键工作，能够说明复杂场景、决策和实际结果。",
        "mid_score_anchor": "具备相关实践，但复杂度、独立性或结果证据有限。",
        "low_score_anchor": "仅接触基础任务，或无法证明真实参与深度。",
        "source": "template",
    },
    {
        "key": "project_impact",
        "name": "项目成果与影响",
        "description": "评价候选人项目成果是否具体、可核对并与岗位目标相关。",
        "dimension": "projects_and_capability",
        "max_score": 10,
        "suggested_share": 50,
        "high_score_anchor": "成果具体且可核对，能说明本人贡献和对业务或交付的明确影响。",
        "mid_score_anchor": "有项目成果，但量化程度、本人贡献或岗位相关性不完整。",
        "low_score_anchor": "只有项目名称或职责罗列，没有可核对的结果证据。",
        "source": "template",
    },
    {
        "key": "problem_solving_depth",
        "name": "问题解决能力",
        "description": "评价候选人识别、分析和解决岗位相关复杂问题的实际证据。",
        "dimension": "projects_and_capability",
        "max_score": 10,
        "suggested_share": 50,
        "high_score_anchor": "能够说明复杂问题、分析过程、关键决策、解决方案和最终结果。",
        "mid_score_anchor": "参与过问题处理，但分析深度、独立性或结果证据有限。",
        "low_score_anchor": "只有一般性能力描述，没有具体问题和解决过程。",
        "source": "template",
    },
    {
        "key": "role_specific_context",
        "name": "岗位补充场景匹配",
        "description": "评价岗位补充说明中需要理解上下文的工作场景是否有简历证据支持。",
        "dimension": "keywords_and_additional",
        "max_score": 10,
        "suggested_share": 100,
        "high_score_anchor": "有直接、完整且可核对的相关场景证据。",
        "mid_score_anchor": "存在部分相关场景，但范围或结果证据不足。",
        "low_score_anchor": "没有直接相关场景，或只能依靠宽泛描述推测。",
        "source": "template",
    },
]


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
        sa.Column("schema_version", sa.String(length=20), server_default="2.0", nullable=False),
        sa.Column(
            "subcriteria_version",
            sa.String(length=20),
            server_default="2.0",
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
        sa.Column(
            "source",
            sa.String(length=30),
            server_default="standard_template",
            nullable=False,
        ),
        sa.Column(
            "template_key",
            sa.String(length=30),
            server_default="standard",
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "semantic_items",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column("job_fingerprint", sa.String(length=64), nullable=True),
        sa.Column(
            "is_stale",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("generation_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("change_reason", sa.String(length=50), nullable=False),
        sa.Column("change_detail", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("confirmed_by", sa.String(length=100), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "source IN ('standard_template', 'technical_template', "
            "'non_technical_template', 'ai_generated', 'hr_manual', "
            "'legacy_migration')",
            name="ck_job_screening_rubrics_source_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'abandoned')",
            name="ck_job_screening_rubrics_status_allowed",
        ),
        sa.CheckConstraint(
            "template_key IS NULL OR template_key IN "
            "('standard', 'technical', 'non_technical')",
            name="ck_job_screening_rubrics_template_allowed",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(semantic_items) = 'array'",
            name="ck_job_screening_rubrics_semantic_items_array",
        ),
        sa.CheckConstraint(
            "status NOT IN ('active', 'archived') OR "
            "jsonb_array_length(semantic_items) BETWEEN 4 AND 10",
            name="ck_job_screening_rubrics_published_item_count",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND is_current = true) OR "
            "(status <> 'active' AND is_current = false)",
            name="ck_job_screening_rubrics_current_status_consistent",
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
        "ix_job_screening_rubrics_job_fingerprint",
        "job_screening_rubrics",
        ["job_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_job_screening_rubrics_is_stale",
        "job_screening_rubrics",
        ["is_stale"],
        unique=False,
    )
    op.create_index(
        "ix_job_screening_rubrics_status",
        "job_screening_rubrics",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_job_screening_rubrics_current_job",
        "job_screening_rubrics",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "uq_job_screening_rubrics_draft_job",
        "job_screening_rubrics",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    semantic_items_json = json.dumps(
        DEFAULT_STANDARD_SEMANTIC_ITEMS,
        ensure_ascii=False,
        separators=(",", ":"),
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
                source,
                template_key,
                status,
                semantic_items,
                change_reason,
                change_detail,
                created_by,
                confirmed_by,
                confirmed_at
            )
            SELECT
                id,
                1,
                40,
                25,
                20,
                10,
                5,
                '2.0',
                '2.0',
                '1.0',
                '1.0',
                true,
                'standard_template',
                'standard',
                'active',
                CAST(:semantic_items AS jsonb),
                'initial_default',
                '阶段 7 migration 为既有岗位创建默认 Rubric',
                'migration',
                'migration',
                now()
            FROM jobs
            ORDER BY id
            """
        ).bindparams(semantic_items=semantic_items_json)
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
        "uq_job_screening_rubrics_draft_job",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "uq_job_screening_rubrics_current_job",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "ix_job_screening_rubrics_status",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "ix_job_screening_rubrics_is_stale",
        table_name="job_screening_rubrics",
    )
    op.drop_index(
        "ix_job_screening_rubrics_job_fingerprint",
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
