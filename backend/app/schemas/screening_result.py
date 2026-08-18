from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.schemas.application import PositiveId


class ScreeningExecutionStatus(str, Enum):
    SCREENING = "screening"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ApplicationScreeningResultSummaryRead(BaseModel):
    id: PositiveId
    candidate_id: PositiveId
    job_id: PositiveId
    application_id: PositiveId
    resume_id: PositiveId
    attempt_number: int = Field(ge=1)
    execution_status: ScreeningExecutionStatus
    overall_score: int | None = Field(default=None, ge=0, le=100)
    hard_pass: bool | None = None
    recommendation: str | None = Field(default=None, max_length=20)
    evidence_coverage_rate: Decimal | None = Field(default=None, ge=0, le=1)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    trigger_reason: str | None = None
    force_rerun: bool
    is_outdated: bool
    outdated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ApplicationScreeningResultDetailRead(ApplicationScreeningResultSummaryRead):
    input_fingerprint: str | None = Field(default=None, max_length=64)
    skill_score: int | None = Field(default=None, ge=0, le=100)
    experience_score: int | None = Field(default=None, ge=0, le=100)
    project_score: int | None = Field(default=None, ge=0, le=100)
    strengths: list[str] | None = None
    risks: list[str] | None = None
    hard_requirement_checks: list[Any] | None = None
    dimension_scores: dict[str, Any] | None = None
    reason: str | None = None
    pending_questions: list[str] | None = None
    resume_evidence: list[Any] | None = None
    job_evidence: list[Any] | None = None
    candidate_input_snapshot: dict[str, Any] | None = None
    resume_snapshot: dict[str, Any] | None = None
    job_requirements_snapshot: dict[str, Any] | None = None
    rubric_snapshot: dict[str, Any] | None = None
    rules_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)
    model_provider: str | None = Field(default=None, max_length=50)
    model_name: str | None = Field(default=None, max_length=100)
    model_config_version: str | None = Field(default=None, max_length=100)
    job_schema_version: str | None = Field(default=None, max_length=20)
    resume_schema_version: str | None = Field(default=None, max_length=20)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    actor_type: str | None = Field(default=None, max_length=20)
    actor_id: str | None = Field(default=None, max_length=100)
    actor_label: str | None = Field(default=None, max_length=100)
    raw_result: dict[str, Any] | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        protected_namespaces=(),
    )


class ApplicationScreeningRunResponse(BaseModel):
    result: ApplicationScreeningResultDetailRead
    reused: StrictBool
    model_called: StrictBool

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


__all__ = [
    "ApplicationScreeningResultDetailRead",
    "ApplicationScreeningResultSummaryRead",
    "ApplicationScreeningRunResponse",
    "ScreeningExecutionStatus",
]
