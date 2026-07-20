from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = None
    requirements: dict[str, Any] | None = None
    status: str = Field(default="open", max_length=20)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = None
    requirements: dict[str, Any] | None = None
    status: str | None = Field(default=None, max_length=20)


class JobRead(BaseModel):
    id: int
    title: str
    department: str | None
    description: str | None
    requirements: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
