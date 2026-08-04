from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_sessionmaker
from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.models.rebuilt.job import Job
from app.models.rebuilt.project_experience import ProjectExperience
from app.models.rebuilt.report import Report
from app.models.rebuilt.resume import Resume
from app.models.rebuilt.screening_result import ScreeningResult
from app.models.rebuilt.work_experience import WorkExperience


LEGACY_STATUS_MAP = {
    "新投递": "new",
    "待筛选": "screening",
    "待约面": "interview_pending",
    "已约面": "interview_scheduled",
    "面试中": "interviewing",
    "复试": "second_interview",
    "offer": "offer",
    "入职": "hired",
    "淘汰": "rejected",
}

CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class LegacySnapshot:
    jobs: list[dict[str, Any]]
    candidates: list[dict[str, Any]]

    @property
    def education_count(self) -> int:
        return sum(
            1
            for item in self.candidates
            if any(_clean_text(item.get(field)) for field in ("school", "degree", "major"))
        )

    @property
    def work_experience_count(self) -> int:
        return sum(1 for item in self.candidates if _clean_text(item.get("experience_desc")))

    @property
    def screening_result_count(self) -> int:
        return sum(1 for item in self.candidates if item.get("match_score") is not None)


@dataclass(frozen=True)
class ImportResult:
    jobs: int
    candidates: int
    education_records: int
    work_experiences: int
    screening_results: int


TARGET_MODELS = (
    Job,
    Candidate,
    Education,
    WorkExperience,
    ProjectExperience,
    Resume,
    ScreeningResult,
    Report,
)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_json_list(value: Any) -> list[str]:
    if value is None:
        return []
    parsed = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in text.replace("，", ",").split(",")]
    if not isinstance(parsed, list):
        parsed = [parsed]

    result: list[str] = []
    for item in parsed:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def map_candidate_status(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return "new"
    return LEGACY_STATUS_MAP.get(text, text[:50])


def map_job_status(value: Any) -> str:
    text = _clean_text(value)
    if text == "active":
        return "open"
    if text in {"inactive", "closed"}:
        return "closed"
    return text[:20] if text else "open"


def build_job_requirements(row: dict[str, Any]) -> dict[str, Any] | None:
    requirements: dict[str, Any] = {}
    summary = _clean_text(row.get("requirements"))
    if summary:
        try:
            parsed_summary = json.loads(summary)
        except json.JSONDecodeError:
            parsed_summary = summary
        if isinstance(parsed_summary, dict):
            requirements.update(parsed_summary)
        else:
            requirements["summary"] = parsed_summary

    list_fields = {
        "required_skills": "required_skills",
        "bonus_skills": "bonus_skills",
        "job_keywords": "job_keywords",
        "risk_keywords": "risk_keywords",
    }
    for source_name, target_name in list_fields.items():
        values = parse_json_list(row.get(source_name))
        if values:
            requirements[target_name] = values

    for field in ("education_requirement", "experience_requirement"):
        value = _clean_text(row.get(field))
        if value:
            requirements[field] = value
    return requirements or None


def resolve_resume_path(
    row: dict[str, Any],
    *,
    backend_dir: Path,
    uploads_dir: Path,
) -> str | None:
    original_path = _clean_text(row.get("resume_path"))
    if not original_path:
        return None
    filename = _clean_text(row.get("resume_filename")) or Path(original_path).name
    restored_path = uploads_dir / filename
    if not restored_path.is_file():
        return None
    try:
        return restored_path.resolve().relative_to(backend_dir.resolve()).as_posix()
    except ValueError:
        return str(restored_path.resolve())


def parse_legacy_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CHINA_STANDARD_TIME)
    return parsed


def load_legacy_snapshot(source_path: Path) -> LegacySnapshot:
    resolved = source_path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"旧版 SQLite 文件不存在：{resolved}")

    connection = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required_tables = {"jobs", "candidates"}
        missing = required_tables - tables
        if missing:
            raise RuntimeError(f"旧版 SQLite 缺少数据表：{', '.join(sorted(missing))}")
        jobs = [dict(row) for row in connection.execute("SELECT * FROM jobs ORDER BY id")]
        candidates = [
            dict(row) for row in connection.execute("SELECT * FROM candidates ORDER BY id")
        ]
    finally:
        connection.close()
    return LegacySnapshot(jobs=jobs, candidates=candidates)


def build_candidate(
    row: dict[str, Any],
    *,
    job: Job | None,
    backend_dir: Path,
    uploads_dir: Path,
) -> Candidate:
    tags = parse_json_list(row.get("ai_tags"))
    for skill in parse_json_list(row.get("skills")):
        if skill not in tags:
            tags.append(skill)

    candidate_kwargs: dict[str, Any] = {
        "name": _clean_text(row.get("name")) or "未命名候选人",
        "phone": _clean_text(row.get("phone")),
        "email": _clean_text(row.get("email")),
        "work_years": int(row["experience_years"])
        if row.get("experience_years") is not None
        else None,
        "education_level": _clean_text(row.get("degree")),
        "source": _clean_text(row.get("source_channel")),
        "status": map_candidate_status(row.get("stage")),
        "resume_file_path": resolve_resume_path(
            row,
            backend_dir=backend_dir,
            uploads_dir=uploads_dir,
        ),
        "ai_summary": _clean_text(row.get("ai_summary")),
        "tags": tags or None,
        "applied_job": job,
    }
    created_at = parse_legacy_datetime(row.get("created_at"))
    updated_at = parse_legacy_datetime(row.get("updated_at"))
    if created_at:
        candidate_kwargs["created_at"] = created_at
    if updated_at:
        candidate_kwargs["updated_at"] = updated_at

    candidate = Candidate(**candidate_kwargs)
    school = _clean_text(row.get("school"))
    degree = _clean_text(row.get("degree"))
    major = _clean_text(row.get("major"))
    if school or degree or major:
        candidate.education_records = [
            Education(school=school, degree=degree, major=major, is_985=False, is_211=False)
        ]

    experience_description = _clean_text(row.get("experience_desc"))
    if experience_description:
        candidate.work_experiences = [
            WorkExperience(description=experience_description, tech_stack=parse_json_list(row.get("skills")) or None)
        ]
    return candidate


def build_screening_result(
    row: dict[str, Any],
    *,
    candidate: Candidate,
    job: Job,
) -> ScreeningResult | None:
    if row.get("match_score") is None:
        return None
    screening_status = _clean_text(row.get("screening_status"))
    hard_pass = True if screening_status == "passed" else False if screening_status in {"backup", "rejected"} else None
    result_kwargs: dict[str, Any] = {
        "candidate": candidate,
        "job": job,
        "overall_score": int(row["match_score"]),
        "hard_pass": hard_pass,
        "risks": parse_json_list(row.get("risk_flags")) or None,
        "recommendation": _clean_text(row.get("screening_result")),
        "reason": _clean_text(row.get("screening_reason")),
        "raw_result": {
            "source": "legacy_sqlite_import",
            "screening_status": screening_status,
            "priority_level": _clean_text(row.get("priority_level")),
        },
    }
    screening_time = parse_legacy_datetime(row.get("screening_updated_at"))
    if screening_time:
        result_kwargs["created_at"] = screening_time
        result_kwargs["updated_at"] = screening_time
    return ScreeningResult(**result_kwargs)


async def get_target_counts(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, int]:
    factory = session_factory or get_sessionmaker()
    async with factory() as session:
        return {
            model.__tablename__: int(
                await session.scalar(select(func.count()).select_from(model)) or 0
            )
            for model in TARGET_MODELS
        }


async def import_legacy_snapshot(
    snapshot: LegacySnapshot,
    *,
    backend_dir: Path,
    uploads_dir: Path,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ImportResult:
    factory = session_factory or get_sessionmaker()
    async with factory() as session:
        async with session.begin():
            target_counts = {
                model.__tablename__: int(
                    await session.scalar(select(func.count()).select_from(model)) or 0
                )
                for model in TARGET_MODELS
            }
            occupied = {name: count for name, count in target_counts.items() if count}
            if occupied:
                details = ", ".join(f"{name}={count}" for name, count in occupied.items())
                raise RuntimeError(
                    "新版 PostgreSQL 业务表不是空库，已拒绝导入，未写入任何数据："
                    + details
                )

            jobs_by_legacy_id: dict[int, Job] = {}
            for row in snapshot.jobs:
                job_kwargs: dict[str, Any] = {
                    "title": _clean_text(row.get("title")) or "未命名岗位",
                    "department": _clean_text(row.get("department")),
                    "description": _clean_text(row.get("description")),
                    "requirements": build_job_requirements(row),
                    "status": map_job_status(row.get("status")),
                }
                created_at = parse_legacy_datetime(row.get("created_at"))
                updated_at = parse_legacy_datetime(row.get("updated_at"))
                if created_at:
                    job_kwargs["created_at"] = created_at
                if updated_at:
                    job_kwargs["updated_at"] = updated_at
                job = Job(**job_kwargs)
                session.add(job)
                jobs_by_legacy_id[int(row["id"])] = job

            candidates: list[Candidate] = []
            screening_results: list[ScreeningResult] = []
            for row in snapshot.candidates:
                legacy_job_id = row.get("job_id")
                job = jobs_by_legacy_id.get(int(legacy_job_id)) if legacy_job_id is not None else None
                candidate = build_candidate(
                    row,
                    job=job,
                    backend_dir=backend_dir,
                    uploads_dir=uploads_dir,
                )
                session.add(candidate)
                candidates.append(candidate)
                if job is not None:
                    screening_result = build_screening_result(
                        row,
                        candidate=candidate,
                        job=job,
                    )
                    if screening_result is not None:
                        session.add(screening_result)
                        screening_results.append(screening_result)

    return ImportResult(
        jobs=len(snapshot.jobs),
        candidates=len(candidates),
        education_records=snapshot.education_count,
        work_experiences=snapshot.work_experience_count,
        screening_results=len(screening_results),
    )
