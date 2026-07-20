from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    candidate_id: int
    job_id: int
    screening_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1)
    report_type: str = Field(default="screening", max_length=20)
    format: str = Field(default="markdown", max_length=20)
    report_metadata: dict[str, Any] | None = None


class ReportUpdate(BaseModel):
    screening_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    report_type: str | None = Field(default=None, max_length=20)
    format: str | None = Field(default=None, max_length=20)
    report_metadata: dict[str, Any] | None = None


class ReportRead(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    screening_id: int | None
    title: str | None
    content: str
    report_type: str
    format: str
    report_metadata: dict[str, Any] | None
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
