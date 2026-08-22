from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

class JobStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"


JobTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
JobBackgroundText = Annotated[str, StringConstraints(max_length=5_000)]
JobResponsibilitiesText = Annotated[str, StringConstraints(max_length=10_000)]
CandidateRequirementsText = Annotated[str, StringConstraints(max_length=10_000)]
PreferredQualificationsText = Annotated[str, StringConstraints(max_length=5_000)]
PublicNotesText = Annotated[str, StringConstraints(max_length=5_000)]
Headcount = Annotated[StrictInt, Field(ge=1, le=999)]


class JobCreate(BaseModel):
    title: JobTitle
    department: ShortText | None = None
    location: ShortText | None = None
    employment_type: EmploymentType | None = None
    headcount: Headcount | None = None
    job_background: JobBackgroundText | None = None
    job_responsibilities: JobResponsibilitiesText | None = None
    candidate_requirements: CandidateRequirementsText | None = None
    preferred_qualifications: PreferredQualificationsText | None = None
    public_notes: PublicNotesText | None = None
    status: JobStatus = JobStatus.DRAFT

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "department",
        "location",
        "job_background",
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
        "public_notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def reject_initial_closed_status(cls, value: JobStatus) -> JobStatus:
        if value is JobStatus.CLOSED:
            raise ValueError("创建岗位时状态只能为 draft 或 open")
        return value

class JobUpdate(BaseModel):
    title: JobTitle | None = None
    department: ShortText | None = None
    location: ShortText | None = None
    employment_type: EmploymentType | None = None
    headcount: Headcount | None = None
    job_background: JobBackgroundText | None = None
    job_responsibilities: JobResponsibilitiesText | None = None
    candidate_requirements: CandidateRequirementsText | None = None
    preferred_qualifications: PreferredQualificationsText | None = None
    public_notes: PublicNotesText | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "department",
        "location",
        "job_background",
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
        "public_notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_update_fields(self) -> JobUpdate:
        if not self.model_fields_set:
            raise ValueError("岗位更新内容不能为空")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("岗位名称不能为 null")
        return self


class JobRead(BaseModel):
    id: int
    title: str
    department: str | None
    location: str | None = None
    employment_type: EmploymentType | None = None
    headcount: int | None = None
    job_background: str | None
    job_responsibilities: str | None
    candidate_requirements: str | None
    preferred_qualifications: str | None
    public_notes: str | None
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Migration-only compatibility: immutable revision c8e1a6f4d205 imports this name
# while loading Alembic history. Job request/response schemas never expose it.
from app.schemas.job_evaluation_plan import (  # noqa: E402
    LegacyEvaluationPlanRequirements as JobRequirementsV1,
)
