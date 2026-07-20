from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScreeningResultCreate(BaseModel):
    candidate_id: int
    job_id: int
    overall_score: int | None = Field(default=None, ge=0, le=100)
    hard_pass: bool | None = None
    skill_score: int | None = Field(default=None, ge=0, le=100)
    experience_score: int | None = Field(default=None, ge=0, le=100)
    project_score: int | None = Field(default=None, ge=0, le=100)
    strengths: list[str] | None = None
    risks: list[str] | None = None
    recommendation: str | None = Field(default=None, max_length=20)
    reason: str | None = None
    raw_result: dict[str, Any] | None = None


class ScreeningResultUpdate(BaseModel):
    overall_score: int | None = Field(default=None, ge=0, le=100)
    hard_pass: bool | None = None
    skill_score: int | None = Field(default=None, ge=0, le=100)
    experience_score: int | None = Field(default=None, ge=0, le=100)
    project_score: int | None = Field(default=None, ge=0, le=100)
    strengths: list[str] | None = None
    risks: list[str] | None = None
    recommendation: str | None = Field(default=None, max_length=20)
    reason: str | None = None
    raw_result: dict[str, Any] | None = None


class ScreeningResultRead(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    overall_score: int | None
    hard_pass: bool | None
    skill_score: int | None
    experience_score: int | None
    project_score: int | None
    strengths: list[str] | None
    risks: list[str] | None
    recommendation: str | None
    reason: str | None
    raw_result: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
