from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.rebuilt.resume_parse import ResumeParseDraft


class ResumeStructureRequest(BaseModel):
    """Client-controlled options for one structure request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    force: bool = False


class ResumeStructureResponse(BaseModel):
    """Stable API view of a validated resume structure draft."""

    model_config = ConfigDict(extra="forbid")

    resume_id: int
    structure_status: Literal["succeeded", "failed"]
    structure_error: str | None
    from_cache: bool
    has_previous_draft: bool
    draft: ResumeParseDraft
