from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectExperienceCreate(BaseModel):
    project_name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=100)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    description: str | None = None
    tech_stack: list[str] | None = None
    achievements: str | None = None


class ProjectExperienceUpdate(BaseModel):
    project_name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=100)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    description: str | None = None
    tech_stack: list[str] | None = None
    achievements: str | None = None


class ProjectExperienceRead(BaseModel):
    id: int
    candidate_id: int
    project_name: str | None
    role: str | None
    start_date: str | None
    end_date: str | None
    description: str | None
    tech_stack: list[str] | None
    achievements: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
