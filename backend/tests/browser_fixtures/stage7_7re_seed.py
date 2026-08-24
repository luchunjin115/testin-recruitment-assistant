"""Seed and remove deterministic 7R-E browser rows without any model call."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import delete, null, select

from app.core.database import get_sessionmaker
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import JobEvaluationPlanInputSnapshot
from app.services.job_evaluation_plan_service import job_evaluation_plan_service


TITLE_PREFIX = "[7R-E验收]"
NOW = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)


def make_job(label: str, status: str = "open") -> Job:
    return Job(
        title=f"{TITLE_PREFIX}{label}",
        department="测试研发部",
        location="长沙",
        employment_type="full_time",
        headcount=1,
        job_background="用于 7R-E 无真实模型浏览器验收。",
        job_responsibilities="负责 Python 服务交付",
        candidate_requirements='必须具备 Python 项目经验；<img src=x onerror="alert(7)"> 仅作为普通文本',
        preferred_qualifications="有 RAG 项目经验者优先",
        public_notes="<script>仅作为普通文本</script>",
        status=status,
    )


def make_v3_payload(job: Job) -> tuple[JobEvaluationPlanInputSnapshot, list[dict], dict]:
    snapshot = job_evaluation_plan_service.build_input_snapshot(job)
    source_by_field = {
        unit.source_field: unit for unit in snapshot.source_units or []
    }
    responsibility = source_by_field["job_responsibilities"]
    required = source_by_field["candidate_requirements"]
    preferred = source_by_field["preferred_qualifications"]
    items = [
        {
            "key": "item:required-python",
            "title": "Python 项目经验与服务交付",
            "category": "experience",
            "priority": "required",
            "sources": [
                {
                    "source_field": required.source_field,
                    "source_unit_id": required.source_unit_id,
                    "source_quote": required.source_text,
                },
                {
                    "source_field": responsibility.source_field,
                    "source_unit_id": responsibility.source_unit_id,
                    "source_quote": responsibility.source_text,
                },
            ],
        },
        {
            "key": "item:preferred-rag",
            "title": "RAG 项目经验",
            "category": "experience",
            "priority": "preferred",
            "sources": [{
                "source_field": preferred.source_field,
                "source_unit_id": preferred.source_unit_id,
                "source_quote": preferred.source_text,
            }],
        },
        {
            "key": "item:general-delivery",
            "title": "完成服务交付",
            "category": "responsibility",
            "priority": "general",
            "sources": [{
                "source_field": responsibility.source_field,
                "source_unit_id": responsibility.source_unit_id,
                "source_quote": responsibility.source_text,
            }],
        },
    ]
    item_keys = {
        "job_responsibilities": ["item:required-python", "item:general-delivery"],
        "candidate_requirements": ["item:required-python"],
        "preferred_qualifications": ["item:preferred-rag"],
    }
    summary = {
        "rule_version": "five_section_source_units_v1",
        "total_units": len(snapshot.source_units or []),
        "reviewed_units": len(snapshot.source_units or []),
        "evaluation_units": len(snapshot.source_units or []),
        "non_evaluation_units": 0,
        "all_reviewed": True,
        "units": [
            {
                "source_unit_id": unit.source_unit_id,
                "disposition": "evaluation",
                "non_evaluation_reason": None,
                "item_keys": item_keys[unit.source_field],
            }
            for unit in snapshot.source_units or []
        ],
    }
    return snapshot, items, summary


def make_v3_plan(job: Job, status: str, *, is_current: bool = True) -> JobEvaluationPlan:
    snapshot, items, summary = make_v3_payload(job)
    input_fingerprint = job_evaluation_plan_service.fingerprint_input(snapshot)
    return JobEvaluationPlan(
        job_id=job.id,
        jd_fingerprint=job_evaluation_plan_service.fingerprint_snapshot(snapshot),
        status=status,
        is_current=is_current,
        items=items if status in {"ready", "outdated"} else [],
        structured_coverage=null(),
        free_text_coverage=null(),
        source_review_summary=summary if status in {"ready", "outdated"} else null(),
        warnings=(
            [
                {"code": "limited_basis", "message": "controlled", "source_unit_ids": []},
                {"code": "priority_signal_conflict", "message": "controlled", "source_unit_ids": ["candidate_requirements:0001"]},
                {"code": "misplaced_non_evaluation_content", "message": "controlled", "source_unit_ids": ["preferred_qualifications:0001"]},
            ]
            if status == "ready" else []
        ),
        prompt_version="job_evaluation_plan_v5",
        model_version="controlled-browser-fixture",
        schema_version="3.0",
        input_fingerprint=input_fingerprint,
        input_snapshot=snapshot.model_dump(mode="json"),
        error_code="JOB_EVALUATION_PLAN_TIMEOUT" if status == "failed" else None,
        error_message="受控夹具：上游暂时不可用" if status == "failed" else None,
        created_at=NOW,
        completed_at=None if status == "generating" else NOW,
        updated_at=NOW,
    )


def make_legacy_plan(job: Job) -> JobEvaluationPlan:
    snapshot = JobEvaluationPlanInputSnapshot.model_validate({
        "job_id": job.id,
        "title": job.title,
        "department": job.department,
        "description": "历史岗位描述",
        "requirements": {
            "schema_version": "1.0",
            "responsibilities": ["历史职责"],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "minimum_work_years": None,
            "education_requirement": None,
            "required_experiences": [],
            "preferred_experiences": [],
            "keywords": [],
            "additional_requirements": [],
        },
    })
    return JobEvaluationPlan(
        job_id=job.id,
        jd_fingerprint=job_evaluation_plan_service.fingerprint_snapshot(snapshot),
        status="ready",
        is_current=True,
        items=[{
            "key": "legacy:python",
            "title": "历史 Python 要求",
            "category": "skill",
            "priority": "required",
            "source_type": "structured",
            "source_field": "requirements.required_skills",
            "source_quote": None,
        }],
        structured_coverage={
            "source_schema_version": "1.0",
            "fields": [{
                "source_field": "requirements.required_skills",
                "source_value_count": 1,
                "item_keys": ["legacy:python"],
            }],
            "all_covered": True,
        },
        free_text_coverage={
            "rule_version": "jd_source_units_v1",
            "all_reviewed": True,
            "units": [{
                "source_id": "description:0001",
                "disposition": "requirements",
                "item_keys": ["legacy:python"],
                "equivalent_structured_item_keys": ["legacy:python"],
            }],
        },
        source_review_summary=null(),
        warnings=["limited_basis"],
        prompt_version="job_evaluation_plan_v4",
        model_version="controlled-browser-fixture",
        schema_version="2.0",
        input_fingerprint=job_evaluation_plan_service.fingerprint_input(snapshot),
        input_snapshot=snapshot.model_dump(mode="json"),
        error_code=None,
        error_message=None,
        created_at=NOW,
        completed_at=NOW,
        updated_at=NOW,
    )


async def clean() -> None:
    async with get_sessionmaker()() as session:
        job_ids = select(Job.id).where(Job.title.like(f"{TITLE_PREFIX}%"))
        await session.execute(delete(JobEvaluationPlan).where(JobEvaluationPlan.job_id.in_(job_ids)))
        await session.execute(delete(Job).where(Job.title.like(f"{TITLE_PREFIX}%")))
        await session.commit()


async def seed() -> None:
    await clean()
    async with get_sessionmaker()() as session:
        jobs = {
            "ready": make_job("01-就绪与三类警告"),
            "missing": make_job("02-开放但无计划"),
            "failed": make_job("03-生成失败"),
            "outdated": make_job("04-JD 已变化"),
            "legacy": make_job("05-旧合同计划"),
            "generating": make_job("06-生成中"),
            "closed": make_job("07-已关闭只读", "closed"),
            "draft": make_job("08-草稿" , "draft"),
        }
        session.add_all(jobs.values())
        await session.flush()
        session.add_all([
            make_v3_plan(jobs["ready"], "ready"),
            make_v3_plan(jobs["failed"], "failed"),
            make_v3_plan(jobs["outdated"], "outdated", is_current=False),
            make_legacy_plan(jobs["legacy"]),
            make_v3_plan(jobs["generating"], "generating"),
            make_v3_plan(jobs["closed"], "ready"),
        ])
        await session.commit()
        print(json.dumps({key: job.id for key, job in jobs.items()}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("seed", "clean"))
    args = parser.parse_args()
    asyncio.run(seed() if args.action == "seed" else clean())


if __name__ == "__main__":
    main()
