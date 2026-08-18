from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


JOB_REQUIREMENTS_SCHEMA_VERSION = "1.0"


class JobStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"


class EducationRequirement(str, Enum):
    NONE = "none"
    ASSOCIATE_OR_ABOVE = "associate_or_above"
    BACHELOR_OR_ABOVE = "bachelor_or_above"
    MASTER_OR_ABOVE = "master_or_above"
    DOCTORATE = "doctorate"


JobTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
DescriptionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000),
]
MinimumWorkYears = Annotated[StrictInt, Field(ge=0, le=80)]
Headcount = Annotated[StrictInt, Field(ge=1, le=999)]


class JobRequirementsV1(BaseModel):
    schema_version: Literal["1.0"]
    responsibilities: list[LongText] = Field(max_length=50)
    required_skills: list[ShortText] = Field(max_length=100)
    preferred_skills: list[ShortText] = Field(max_length=100)
    minimum_work_years: MinimumWorkYears | None
    education_requirement: EducationRequirement | None
    required_experiences: list[LongText] = Field(max_length=50)
    preferred_experiences: list[LongText] = Field(max_length=50)
    keywords: list[ShortText] = Field(max_length=100)
    additional_requirements: list[LongText] = Field(max_length=50)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "responsibilities",
        "required_skills",
        "preferred_skills",
        "required_experiences",
        "preferred_experiences",
        "keywords",
        "additional_requirements",
        mode="before",
    )
    @classmethod
    def normalize_text_lists(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value

        normalized: list[Any] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                normalized.append(item)
                continue
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized


def empty_job_requirements_v1() -> JobRequirementsV1:
    return JobRequirementsV1(
        schema_version=JOB_REQUIREMENTS_SCHEMA_VERSION,
        responsibilities=[],
        required_skills=[],
        preferred_skills=[],
        minimum_work_years=None,
        education_requirement=None,
        required_experiences=[],
        preferred_experiences=[],
        keywords=[],
        additional_requirements=[],
    )


class JobCreate(BaseModel):
    title: JobTitle
    department: ShortText | None = None
    location: ShortText | None = None
    employment_type: EmploymentType | None = None
    headcount: Headcount | None = None
    description: DescriptionText | None = None
    requirements: JobRequirementsV1 = Field(default_factory=empty_job_requirements_v1)
    status: JobStatus = JobStatus.DRAFT

    model_config = ConfigDict(extra="forbid")

    @field_validator("department", "location", "description", mode="before")
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
    description: DescriptionText | None = None
    requirements: JobRequirementsV1 | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("department", "location", "description", mode="before")
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
        if "requirements" in self.model_fields_set and self.requirements is None:
            raise ValueError("岗位要求不能为 null")
        return self


class JobRead(BaseModel):
    id: int
    title: str
    department: str | None
    location: str | None = None
    employment_type: EmploymentType | None = None
    headcount: int | None = None
    description: str | None
    requirements: JobRequirementsV1
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
