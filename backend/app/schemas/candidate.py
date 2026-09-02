from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.education import EducationCreate, EducationRead
from app.schemas.project_experience import ProjectExperienceCreate, ProjectExperienceRead
from app.schemas.work_experience import WorkExperienceCreate, WorkExperienceRead


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    gender: str | None = Field(default=None, max_length=10)
    age: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)
    current_company: str | None = Field(default=None, max_length=200)
    current_title: str | None = Field(default=None, max_length=200)
    work_years: int | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=50)
    status: str = Field(default="new", max_length=50)
    applied_job_id: int | None = None
    resume_file_path: str | None = Field(default=None, max_length=500)
    resume_text: str | None = None
    parsed_data: dict[str, Any] | None = None
    ai_summary: str | None = None
    tags: list[str] | None = None
    education_records: list[EducationCreate] = Field(default_factory=list)
    work_experiences: list[WorkExperienceCreate] = Field(default_factory=list)
    project_experiences: list[ProjectExperienceCreate] = Field(default_factory=list)


class CandidateFromResumeCreate(BaseModel):
    resume_id: int = Field(ge=1)
    candidate: CandidateCreate


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    gender: str | None = Field(default=None, max_length=10)
    age: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)
    current_company: str | None = Field(default=None, max_length=200)
    current_title: str | None = Field(default=None, max_length=200)
    work_years: int | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    applied_job_id: int | None = None
    resume_file_path: str | None = Field(default=None, max_length=500)
    resume_text: str | None = None
    parsed_data: dict[str, Any] | None = None
    ai_summary: str | None = None
    tags: list[str] | None = None


class CandidateRead(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    gender: str | None
    age: int | None
    location: str | None
    current_company: str | None
    current_title: str | None
    work_years: int | None
    education_level: str | None
    source: str | None
    status: str
    applied_job_id: int | None
    resume_file_path: str | None
    resume_text: str | None
    parsed_data: dict[str, Any] | None
    ai_summary: str | None
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime
    education_records: list[EducationRead] = Field(default_factory=list)
    work_experiences: list[WorkExperienceRead] = Field(default_factory=list)
    project_experiences: list[ProjectExperienceRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
