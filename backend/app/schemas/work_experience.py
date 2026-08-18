from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkExperienceCreate(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    description: str | None = None
    tech_stack: list[str] | None = None


class WorkExperienceUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    description: str | None = None
    tech_stack: list[str] | None = None


class WorkExperienceRead(BaseModel):
    id: int
    candidate_id: int
    company: str | None
    title: str | None
    start_date: str | None
    end_date: str | None
    description: str | None
    tech_stack: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
