from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ParseStatus = Literal["uploaded", "parsing", "parsed", "failed"]
StructureStatus = Literal["not_started", "processing", "succeeded", "failed"]


class ResumeCreate(BaseModel):
    candidate_id: int
    job_id: int | None = None
    filename: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=500)
    file_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = Field(default=None, ge=0)
    raw_text: str | None = None
    parse_status: ParseStatus = "uploaded"
    parse_error: str | None = None
    parsed_snapshot: dict[str, Any] | None = None
    parsed_at: datetime | None = None


class ResumeUpdate(BaseModel):
    job_id: int | None = None
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    file_path: str | None = Field(default=None, min_length=1, max_length=500)
    file_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = Field(default=None, ge=0)
    raw_text: str | None = None
    parse_status: ParseStatus | None = None
    parse_error: str | None = None
    parsed_snapshot: dict[str, Any] | None = None
    parsed_at: datetime | None = None


class ResumeRead(BaseModel):
    id: int
    candidate_id: int | None
    job_id: int | None
    filename: str
    file_path: str
    file_type: str | None
    file_size: int | None
    raw_text: str | None
    parse_status: ParseStatus
    parse_error: str | None
    parsed_snapshot: dict[str, Any] | None
    structure_status: StructureStatus
    structure_error: str | None
    structure_attempt_id: str | None
    structure_started_at: datetime | None
    structured_at: datetime | None
    structure_schema_version: str | None
    uploaded_at: datetime
    parsed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
