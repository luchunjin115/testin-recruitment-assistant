from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EducationCreate(BaseModel):
    school: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=50)
    major: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    is_985: bool = False
    is_211: bool = False


class EducationUpdate(BaseModel):
    school: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=50)
    major: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    is_985: bool | None = None
    is_211: bool | None = None


class EducationRead(BaseModel):
    id: int
    candidate_id: int
    school: str | None
    degree: str | None
    major: str | None
    start_date: str | None
    end_date: str | None
    is_985: bool
    is_211: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
