from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from app.schemas.application import PositiveId, ReasonText, ScreeningRunRequest


class ScreeningBatchItemStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    REUSED = "reused"
    SKIPPED = "skipped"


class ScreeningBatchRunRequest(BaseModel):
    application_ids: list[PositiveId] = Field(min_length=1, max_length=5)
    retry_failed_only: StrictBool = False
    force: StrictBool = False
    confirm_force: StrictBool = False
    reason: ReasonText | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_batch_options(self) -> ScreeningBatchRunRequest:
        if len(set(self.application_ids)) != len(self.application_ids):
            raise ValueError("同一批次不能重复选择 Application")
        if self.retry_failed_only and self.force:
            raise ValueError("仅重试失败项不能同时强制重跑")
        ScreeningRunRequest(
            force=self.force,
            confirm_force=self.confirm_force,
            reason=self.reason,
        )
        return self

    def to_single_run_request(self) -> ScreeningRunRequest:
        return ScreeningRunRequest(
            force=self.force,
            confirm_force=self.confirm_force,
            reason=self.reason,
        )


class ScreeningBatchItemResult(BaseModel):
    application_id: PositiveId
    status: ScreeningBatchItemStatus
    screening_result_id: PositiveId | None = None
    attempt_number: PositiveId | None = None
    reused: StrictBool = False
    model_called: StrictBool = False
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=1_000)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ScreeningBatchSummary(BaseModel):
    selected: int = Field(ge=1, le=5)
    executed: int = Field(ge=0, le=5)
    completed: int = Field(ge=0, le=5)
    failed: int = Field(ge=0, le=5)
    blocked: int = Field(ge=0, le=5)
    reused: int = Field(ge=0, le=5)
    skipped: int = Field(ge=0, le=5)

    model_config = ConfigDict(extra="forbid")


class ScreeningBatchRunResponse(BaseModel):
    job_id: PositiveId
    items: list[ScreeningBatchItemResult] = Field(min_length=1, max_length=5)
    summary: ScreeningBatchSummary

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "ScreeningBatchItemResult",
    "ScreeningBatchItemStatus",
    "ScreeningBatchRunRequest",
    "ScreeningBatchRunResponse",
    "ScreeningBatchSummary",
]
