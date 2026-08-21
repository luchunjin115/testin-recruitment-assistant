from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ExperiencePeriodFactKey = Annotated[
    str,
    StringConstraints(pattern=r"^experience_period:[0-9a-f]{16}$"),
]
YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(?:0[1-9]|1[0-2])$")]
DatePrecision = Literal["month", "year", "present"]


class ExperiencePeriodFact(BaseModel):
    """A non-sensitive, auditable calendar fact extracted from a date range."""

    key: ExperiencePeriodFactKey
    source_line: int = Field(ge=1)
    source_date_text: str = Field(min_length=1, max_length=100)
    raw_start: str = Field(min_length=1, max_length=40)
    raw_end: str = Field(min_length=1, max_length=40)
    normalized_start_month: YearMonth | None
    normalized_end_month: YearMonth | None
    start_precision: DatePrecision
    end_precision: DatePrecision
    resolved_cutoff_month: YearMonth
    duration_months: int | None = Field(default=None, ge=0)
    duration_months_lower_bound: int | None = Field(default=None, ge=0)
    duration_months_upper_bound: int | None = Field(default=None, ge=0)
    usable_for_reference: bool
    warnings: list[str] = Field(max_length=10)
    unavailable_reason: str | None = Field(default=None, min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")


class ExperiencePeriodFactsSnapshot(BaseModel):
    rule_version: str = Field(min_length=1, max_length=100)
    evaluation_reference_at: str = Field(min_length=1, max_length=50)
    evaluation_timezone: str = Field(min_length=1, max_length=100)
    reference_month: YearMonth
    facts: list[ExperiencePeriodFact] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid")
