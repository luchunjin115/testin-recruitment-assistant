from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.resume_parse import ResumeParseDraft


class ResumeStructureRequest(BaseModel):
    """Client-controlled options for one structure request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    force: bool = False


class ResumeStructurePerformance(BaseModel):
    """Privacy-safe timing breakdown for the current structure request."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    total_ms: int = Field(ge=0)
    preparation_ms: int = Field(ge=0)
    model_ms: int = Field(ge=0)
    validation_ms: int = Field(ge=0)
    persistence_ms: int = Field(ge=0)


class ResumeStructureResponse(BaseModel):
    """Stable API view of a validated resume structure draft."""

    model_config = ConfigDict(extra="forbid")

    resume_id: int
    structure_status: Literal["succeeded", "failed"]
    structure_error: str | None
    from_cache: bool
    has_previous_draft: bool
    draft: ResumeParseDraft
    performance: ResumeStructurePerformance | None = None
