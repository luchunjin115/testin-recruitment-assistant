from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


VALID_JOB_STATUSES = ["active", "inactive"]


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = ""
    description: Optional[str] = ""
    requirements: Optional[str] = ""
    required_skills: Optional[str] = ""
    bonus_skills: Optional[str] = ""
    education_requirement: Optional[str] = ""
    experience_requirement: Optional[str] = ""
    job_keywords: Optional[str] = ""
    risk_keywords: Optional[str] = ""
    status: str = "active"


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    required_skills: Optional[str] = None
    bonus_skills: Optional[str] = None
    education_requirement: Optional[str] = None
    experience_requirement: Optional[str] = None
    job_keywords: Optional[str] = None
    risk_keywords: Optional[str] = None
    status: Optional[str] = None


class JobStatusUpdate(BaseModel):
    status: str


class JobRead(BaseModel):
    id: int
    title: str
    department: str
    description: str
    requirements: str
    required_skills: str
    bonus_skills: str
    education_requirement: str
    experience_requirement: str
    job_keywords: str
    risk_keywords: str
    status: str
    candidate_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
