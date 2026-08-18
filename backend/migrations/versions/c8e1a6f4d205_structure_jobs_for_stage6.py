"""structure jobs for stage 6

Revision ID: c8e1a6f4d205
Revises: f5a7c9e2d104
Create Date: 2026-08-15 11:00:00
"""

from __future__ import annotations

import re
from typing import Any

from alembic import op
import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.schemas.job import JobRequirementsV1


revision = "c8e1a6f4d205"
down_revision = "f5a7c9e2d104"
branch_labels = None
depends_on = None


EMPTY_REQUIREMENTS_V1: dict[str, Any] = {
    "schema_version": "1.0",
    "responsibilities": [],
    "required_skills": [],
    "preferred_skills": [],
    "minimum_work_years": None,
    "education_requirement": None,
    "required_experiences": [],
    "preferred_experiences": [],
    "keywords": [],
    "additional_requirements": [],
}


def _normalize_text_list(value: Any, *, limit: int, item_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned:
            continue
        cleaned = cleaned[:item_limit]
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
        if len(normalized) == limit:
            break
    return normalized


def _combine_text_lists(
    requirements: dict[str, Any],
    keys: tuple[str, ...],
    *,
    limit: int,
    item_limit: int,
) -> list[str]:
    combined: list[Any] = []
    for key in keys:
        value = requirements.get(key)
        if isinstance(value, list):
            combined.extend(value)
    return _normalize_text_list(combined, limit=limit, item_limit=item_limit)


def _parse_work_years(value: Any) -> tuple[int | None, str | None]:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 80:
        return value, None
    if not isinstance(value, str) or not value.strip():
        return None, None

    cleaned = value.strip()
    matched = re.search(r"(?<!\d)(\d{1,2})\s*年\s*(?:以上|及以上)", cleaned)
    if matched:
        years = int(matched.group(1))
        if 0 <= years <= 80:
            return years, None
    return None, cleaned


def _parse_education(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None

    cleaned = value.strip()
    stable_values = {
        "none",
        "associate_or_above",
        "bachelor_or_above",
        "master_or_above",
        "doctorate",
    }
    if cleaned in stable_values:
        return cleaned, None

    for keyword, stable_value in (
        ("不限", "none"),
        ("博士", "doctorate"),
        ("硕士", "master_or_above"),
        ("本科", "bachelor_or_above"),
        ("大专", "associate_or_above"),
    ):
        if keyword in cleaned:
            return stable_value, None
    return None, cleaned


def _append_additional(values: list[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    cleaned = value.strip()[:1_000]
    if cleaned and cleaned not in values and len(values) < 50:
        values.append(cleaned)


def _convert_requirements(requirements: Any, description: str | None) -> tuple[dict[str, Any], Any]:
    try:
        validated = JobRequirementsV1.model_validate(requirements)
    except ValidationError:
        validated = None

    if validated is not None:
        return validated.model_dump(mode="json"), None

    if requirements is None or requirements == {}:
        return dict(EMPTY_REQUIREMENTS_V1), None

    legacy_snapshot = requirements
    source = requirements if isinstance(requirements, dict) else {}
    responsibilities = _normalize_text_list(
        source.get("responsibilities"),
        limit=50,
        item_limit=1_000,
    )
    if not responsibilities and isinstance(description, str) and description.strip():
        responsibilities = [description.strip()[:1_000]]

    additional = _normalize_text_list(
        source.get("additional_requirements"),
        limit=50,
        item_limit=1_000,
    )
    _append_additional(additional, source.get("summary"))

    minimum_work_years, unparsed_experience = _parse_work_years(
        source.get("experience_requirement")
    )
    education_requirement, unparsed_education = _parse_education(
        source.get("education_requirement")
    )
    _append_additional(additional, unparsed_experience)
    _append_additional(additional, unparsed_education)

    converted = {
        "schema_version": "1.0",
        "responsibilities": responsibilities,
        "required_skills": _combine_text_lists(
            source,
            ("required_skills",),
            limit=100,
            item_limit=100,
        ),
        "preferred_skills": _combine_text_lists(
            source,
            ("bonus_skills", "preferred_skills"),
            limit=100,
            item_limit=100,
        ),
        "minimum_work_years": minimum_work_years,
        "education_requirement": education_requirement,
        "required_experiences": _combine_text_lists(
            source,
            ("required_experiences",),
            limit=50,
            item_limit=1_000,
        ),
        "preferred_experiences": _combine_text_lists(
            source,
            ("preferred_experiences",),
            limit=50,
            item_limit=1_000,
        ),
        "keywords": _combine_text_lists(
            source,
            ("job_keywords", "keywords"),
            limit=100,
            item_limit=100,
        ),
        "additional_requirements": additional,
    }
    validated = JobRequirementsV1.model_validate(converted)
    return validated.model_dump(mode="json"), legacy_snapshot


def _map_status(value: Any) -> str:
    if value in {"active", "open"}:
        return "open"
    if value in {"inactive", "closed"}:
        return "closed"
    return "draft"


def _is_open_complete(
    *,
    title: Any,
    department: Any,
    location: Any,
    employment_type: Any,
    headcount: Any,
    description: Any,
    requirements: dict[str, Any],
) -> bool:
    required_texts = (title, department, location, description)
    if not all(isinstance(value, str) and value.strip() for value in required_texts):
        return False
    if employment_type not in {"full_time", "part_time", "internship", "contract"}:
        return False
    if isinstance(headcount, bool) or not isinstance(headcount, int) or not 1 <= headcount <= 999:
        return False
    return (
        bool(requirements["responsibilities"])
        and bool(requirements["required_skills"])
        and requirements["minimum_work_years"] is not None
        and requirements["education_requirement"] is not None
    )


def upgrade() -> None:
    op.add_column("jobs", sa.Column("location", sa.String(length=100), nullable=True))
    op.add_column("jobs", sa.Column("employment_type", sa.String(length=30), nullable=True))
    op.add_column("jobs", sa.Column("headcount", sa.Integer(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column(
            "legacy_requirements",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
    )

    jobs = sa.table(
        "jobs",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("department", sa.String()),
        sa.column("location", sa.String()),
        sa.column("employment_type", sa.String()),
        sa.column("headcount", sa.Integer()),
        sa.column("description", sa.Text()),
        sa.column("requirements", postgresql.JSONB()),
        sa.column("legacy_requirements", postgresql.JSONB(none_as_null=True)),
        sa.column("status", sa.String()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            jobs.c.id,
            jobs.c.title,
            jobs.c.department,
            jobs.c.location,
            jobs.c.employment_type,
            jobs.c.headcount,
            jobs.c.description,
            jobs.c.requirements,
            jobs.c.status,
        ).order_by(jobs.c.id)
    ).mappings()

    for row in rows:
        requirements, legacy_snapshot = _convert_requirements(
            row["requirements"],
            row["description"],
        )
        status = _map_status(row["status"])
        if status == "open" and not _is_open_complete(
            title=row["title"],
            department=row["department"],
            location=row["location"],
            employment_type=row["employment_type"],
            headcount=row["headcount"],
            description=row["description"],
            requirements=requirements,
        ):
            status = "draft"

        bind.execute(
            sa.update(jobs)
            .where(jobs.c.id == row["id"])
            .values(
                requirements=requirements,
                legacy_requirements=legacy_snapshot,
                status=status,
            )
        )

    op.alter_column("jobs", "requirements", existing_type=postgresql.JSONB(), nullable=False)
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.String(length=20),
        server_default="draft",
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_jobs_status_allowed",
        "jobs",
        "status IN ('draft', 'open', 'closed')",
    )
    op.create_check_constraint(
        "ck_jobs_headcount_range",
        "jobs",
        "headcount IS NULL OR headcount BETWEEN 1 AND 999",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jobs_headcount_range", "jobs", type_="check")
    op.drop_constraint("ck_jobs_status_allowed", "jobs", type_="check")

    jobs = sa.table(
        "jobs",
        sa.column("requirements", postgresql.JSONB()),
        sa.column("legacy_requirements", postgresql.JSONB(none_as_null=True)),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(jobs)
        .where(jobs.c.legacy_requirements.is_not(None))
        .values(requirements=jobs.c.legacy_requirements)
    )

    op.alter_column("jobs", "requirements", existing_type=postgresql.JSONB(), nullable=True)
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.String(length=20),
        server_default="open",
        existing_nullable=False,
    )
    op.drop_column("jobs", "legacy_requirements")
    op.drop_column("jobs", "headcount")
    op.drop_column("jobs", "employment_type")
    op.drop_column("jobs", "location")
