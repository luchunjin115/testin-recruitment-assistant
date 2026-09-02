"""add public application submission and processing contract

Revision ID: a8d4f2c7e901
Revises: e7f9a1b3c545
Create Date: 2026-09-02 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a8d4f2c7e901"
down_revision: str | Sequence[str] | None = "e7f9a1b3c545"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _assert_candidate_emails_fit_legacy_limit() -> None:
    oversized = op.get_bind().execute(
        sa.text("SELECT 1 FROM candidates WHERE length(email) > 100 LIMIT 1")
    ).first()
    if oversized is not None:
        raise RuntimeError("STAGE8_CANDIDATE_EMAIL_DOWNGRADE_BLOCKED")


def upgrade() -> None:
    op.alter_column(
        "candidates",
        "email",
        existing_type=sa.String(length=100),
        type_=sa.String(length=254),
        existing_nullable=True,
    )

    op.create_table(
        "public_application_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("submission_reference", sa.String(length=27), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("consent_version", sa.String(length=100), nullable=False),
        sa.Column(
            "consented_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "identity_review_status",
            sa.String(length=20),
            server_default="clear",
            nullable=False,
        ),
        sa.Column(
            "identity_review_reasons",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "submission_reference ~ '^AP-[A-Z0-9]{8,24}$'",
            name="ck_public_application_submissions_reference_format",
        ),
        sa.CheckConstraint(
            "idempotency_key_hash ~ '^[0-9a-f]{64}$'",
            name="ck_public_application_submissions_idempotency_hash_format",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_public_application_submissions_request_fingerprint_format",
        ),
        sa.CheckConstraint(
            "btrim(consent_version) <> ''",
            name="ck_public_application_submissions_consent_version_nonempty",
        ),
        sa.CheckConstraint(
            "identity_review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_public_application_submissions_identity_status_allowed",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(identity_review_reasons) = 'array'",
            name="ck_public_application_submissions_identity_reasons_array",
        ),
        sa.CheckConstraint(
            "identity_review_reasons <@ "
            "'[\"same_name\", \"contact_conflict\"]'::jsonb",
            name="ck_public_application_submissions_identity_reasons_allowed",
        ),
        sa.CheckConstraint(
            "(identity_review_status = 'clear' AND "
            "jsonb_array_length(identity_review_reasons) = 0) OR "
            "(identity_review_status IN ('needs_review', 'reviewed') AND "
            "jsonb_array_length(identity_review_reasons) > 0)",
            name="ck_public_application_submissions_identity_review_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name="fk_public_application_submissions_application_id_applications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_public_application_submissions_resume_id_resumes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            name="uq_public_application_submissions_application_id",
        ),
        sa.UniqueConstraint(
            "resume_id",
            name="uq_public_application_submissions_resume_id",
        ),
        sa.UniqueConstraint(
            "submission_reference",
            name="uq_public_application_submissions_reference",
        ),
        sa.UniqueConstraint(
            "idempotency_key_hash",
            name="uq_public_application_submissions_idempotency_hash",
        ),
        sa.UniqueConstraint(
            "id",
            "application_id",
            "resume_id",
            name="uq_public_application_submissions_frozen_identity",
        ),
    )
    op.create_index(
        "ix_public_application_submissions_identity_review_status",
        "public_application_submissions",
        ["identity_review_status"],
        unique=False,
    )
    op.create_index(
        "ix_public_application_submissions_created_at",
        "public_application_submissions",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "application_processing_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "current_step",
            sa.String(length=30),
            server_default="extract_text",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("waiting_reason", sa.String(length=50), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "warning_codes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
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
            "trigger_type IN ('automatic', 'manual_retry')",
            name="ck_application_processing_runs_trigger_type_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'waiting_screening', 'succeeded', "
            "'succeeded_with_warnings', 'failed', 'paused')",
            name="ck_application_processing_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "current_step IN ('extract_text', 'structure_resume', "
            "'trigger_screening', 'await_screening', 'completed')",
            name="ck_application_processing_runs_current_step_allowed",
        ),
        sa.CheckConstraint(
            "attempt_count BETWEEN 0 AND 3",
            name="ck_application_processing_runs_attempt_count_range",
        ),
        sa.CheckConstraint(
            "(status = 'paused' AND waiting_reason IN "
            "('job_closed', 'existing_application_resume_choice')) OR "
            "(status <> 'paused' AND waiting_reason IS NULL)",
            name="ck_application_processing_runs_waiting_reason_matches_status",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND completed_at IS NOT NULL AND "
            "error_code IS NOT NULL AND error_message IS NOT NULL) OR "
            "(status <> 'failed' AND error_code IS NULL AND error_message IS NULL)",
            name="ck_application_processing_runs_failed_has_safe_error",
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]*$'",
            name="ck_application_processing_runs_error_code_format",
        ),
        sa.CheckConstraint(
            "error_message IS NULL OR btrim(error_message) <> ''",
            name="ck_application_processing_runs_error_message_nonempty",
        ),
        sa.CheckConstraint(
            "status NOT IN ('succeeded', 'succeeded_with_warnings') OR "
            "(current_step = 'completed' AND completed_at IS NOT NULL)",
            name="ck_application_processing_runs_success_completed",
        ),
        sa.CheckConstraint(
            "current_step <> 'completed' OR "
            "status IN ('succeeded', 'succeeded_with_warnings')",
            name="ck_application_processing_runs_completed_step_matches_status",
        ),
        sa.CheckConstraint(
            "status <> 'waiting_screening' OR current_step = 'await_screening'",
            name="ck_application_processing_runs_waiting_screening_step",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(warning_codes) = 'array'",
            name="ck_application_processing_runs_warning_codes_array",
        ),
        sa.CheckConstraint(
            "warning_codes <@ '[\"RESUME_STRUCTURE_FAILED\"]'::jsonb",
            name="ck_application_processing_runs_warning_codes_allowed",
        ),
        sa.CheckConstraint(
            "status <> 'succeeded' OR jsonb_array_length(warning_codes) = 0",
            name="ck_application_processing_runs_succeeded_without_warnings",
        ),
        sa.CheckConstraint(
            "status <> 'succeeded_with_warnings' OR "
            "jsonb_array_length(warning_codes) > 0",
            name="ck_application_processing_runs_warning_status_consistent",
        ),
        sa.CheckConstraint(
            "(lease_owner IS NULL AND lease_expires_at IS NULL) OR "
            "(status = 'running' AND lease_owner IS NOT NULL AND "
            "lease_expires_at IS NOT NULL)",
            name="ck_application_processing_runs_lease_consistent",
        ),
        sa.CheckConstraint(
            "status <> 'running' OR started_at IS NOT NULL",
            name="ck_application_processing_runs_running_has_started_at",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name="fk_application_processing_runs_application_id_applications",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_application_processing_runs_resume_id_resumes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id", "application_id", "resume_id"],
            [
                "public_application_submissions.id",
                "public_application_submissions.application_id",
                "public_application_submissions.resume_id",
            ],
            name="fk_application_processing_runs_frozen_submission_identity",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_processing_runs_submission_id",
        "application_processing_runs",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        "ix_application_processing_runs_application_id",
        "application_processing_runs",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_application_processing_runs_resume_id",
        "application_processing_runs",
        ["resume_id"],
        unique=False,
    )
    op.create_index(
        "ix_application_processing_runs_current_step",
        "application_processing_runs",
        ["current_step"],
        unique=False,
    )
    op.create_index(
        "ix_application_processing_runs_created_at",
        "application_processing_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_application_processing_runs_claim",
        "application_processing_runs",
        ["status", "lease_expires_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_application_processing_runs_active_submission",
        "application_processing_runs",
        ["submission_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('queued', 'running', 'waiting_screening')"
        ),
    )


def downgrade() -> None:
    _assert_candidate_emails_fit_legacy_limit()
    op.drop_table("application_processing_runs")
    op.drop_table("public_application_submissions")
    op.alter_column(
        "candidates",
        "email",
        existing_type=sa.String(length=254),
        type_=sa.String(length=100),
        existing_nullable=True,
    )
