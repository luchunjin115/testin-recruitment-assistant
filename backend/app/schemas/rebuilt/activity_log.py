from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActivityLogCreate(BaseModel):
    user_id: str | None = Field(default=None, max_length=50)
    action: str = Field(min_length=1, max_length=100)
    target_type: str | None = Field(default=None, max_length=50)
    target_id: int | None = None
    detail: dict[str, Any] | None = None


class ActivityLogRead(BaseModel):
    id: int
    user_id: str | None
    action: str
    target_type: str | None
    target_id: int | None
    detail: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
