from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.adapters.screening_model import (
    ScreeningModelAdapterResult,
    ScreeningModelTimeoutError,
)
from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_screening_rubric import JobScreeningRubric
from app.models.resume import Resume
from app.models.screening_result import ScreeningResult
from app.schemas.screening_batch import ScreeningBatchRunRequest
from app.services.screening_batch_service import ScreeningBatchService
from app.services.screening_rubric_service import ScreeningRubricService
from app.services.screening_service import ScreeningService


def _semantic_items() -> list[dict]:
    dimensions = (
        "must_have_requirements",
        "work_experience_relevance",
        "projects_and_capability",
        "preferred_qualifications",
    )
    return [
        {
            "key": f"criterion_{index}",
            "name": f"验证评分项 {index}",
            "description": f"验证候选人的岗位能力 {index}",
            "dimension": dimension,
            "max_score": 10,
            "suggested_share": 20,
            "high_score_anchor": "有充分且可核对的岗位相关证据",
            "mid_score_anchor": "有部分岗位相关证据",
            "low_score_anchor": "岗位相关证据较弱",
            "source": "hr_manual",
        }
        for index, dimension in enumerate(dimensions, start=1)
    ]


class ControlledAdapter:
    def __init__(self) -> None:
        self.failed_application_ids: set[int] = set()
        self.calls: list[int] = []

    async def evaluate(self, job_context, semantic_items, candidate_material):
        del job_context
        application_id = int(candidate_material.application_ref.rsplit("-", 1)[1])
        self.calls.append(application_id)
        if application_id in self.failed_application_ids:
            raise ScreeningModelTimeoutError("批量隔离验证中的可控超时")
        content = json.dumps(
            {
                "schema_version": "1.0",
                "evaluations": [
                    {
                        "criterion_key": item.key,
                        "score": 8,
                        "confidence": "high",
                        "evidence": [
                            {
                                "source": "resume_text",
                                "locator": "工作经历",
                                "quote": "负责招聘平台后端服务",
                            }
                        ],
                        "reason": "简历提供了可以定位的岗位相关交付证据",
                        "strengths": ["具备相关后端交付经验"],
                        "gaps": [],
                    }
                    for item in semantic_items
                ],
            },
            ensure_ascii=False,
        )
        return ScreeningModelAdapterResult(
            content=content,
            model="controlled-step8-model",
            finish_reason="stop",
            duration_ms=10,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.001000"),
        )


async def _create_fixture() -> tuple[int, list[int]]:
    requirements = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台后端服务"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 2,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": ["FastAPI"],
        "additional_requirements": [],
    }
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        job = Job(
            title="步骤 8 虚构后端岗位",
            department="虚构研发部",
            description="负责招聘平台后端服务",
            requirements=requirements,
            status="open",
        )
        db.add(job)
        await db.flush()
        rubric = JobScreeningRubric(
            job_id=job.id,
            version=1,
            is_current=True,
            source="hr_manual",
            status="active",
            semantic_items=_semantic_items(),
            job_fingerprint=ScreeningRubricService.build_job_fingerprint(
                {
                    "title": job.title,
                    "description": job.description,
                    "requirements": requirements,
                }
            ),
            is_stale=False,
            change_reason="draft_published",
            change_detail="步骤 8 临时数据库验证",
            confirmed_by="validation",
            confirmed_at=datetime.now(timezone.utc),
        )
        db.add(rubric)

        application_ids: list[int] = []
        for index in range(1, 6):
            blocked = index == 3
            candidate = Candidate(
                name=f"虚构候选人 {index}",
                phone=f"1390000000{index}",
                email=f"synthetic-step8-{index}@example.com",
                current_title=None if blocked else "后端工程师",
                work_years=None if blocked else 4,
                education_level=None if blocked else "本科",
                parsed_data=(
                    {"draft": {"basic_info": {"name": f"虚构候选人 {index}"}}}
                    if blocked
                    else {
                        "draft": {
                            "basic_info": {
                                "name": f"虚构候选人 {index}",
                                "current_title": "后端工程师",
                                "work_years": 4,
                                "education_level": "本科",
                            },
                            "skills": ["Python", "FastAPI", "PostgreSQL"],
                        }
                    }
                ),
            )
            db.add(candidate)
            await db.flush()
            resume = Resume(
                candidate_id=candidate.id,
                job_id=job.id,
                filename=f"synthetic-step8-{index}.txt",
                file_path=f"validation/synthetic-step8-{index}.txt",
                file_type="text/plain",
                raw_text=(
                    None
                    if blocked
                    else (
                        "工作经历：负责招聘平台后端服务，使用 Python、FastAPI "
                        "和 PostgreSQL 交付核心接口，并使用 Docker 完成交付。"
                    )
                ),
                parsed_snapshot=candidate.parsed_data,
                parse_status="parsed",
                structure_status="structured",
                structure_schema_version="1.0",
            )
            db.add(resume)
            await db.flush()
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id,
                current_resume_id=resume.id,
                source="hr_screening",
                lifecycle_status="active",
                recruitment_stage="applied",
                ai_status="not_started",
                hr_decision="pending",
            )
            db.add(application)
            await db.flush()
            application_ids.append(application.id)

        await db.commit()
        return job.id, application_ids


async def _verify() -> None:
    job_id, application_ids = await _create_fixture()
    adapter = ControlledAdapter()
    single_service = ScreeningService(
        model_adapter=adapter,
        settings=get_settings(),
    )
    batch_service = ScreeningBatchService(single_service=single_service)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        preexisting = await single_service.run(db, application_ids[3])
        if preexisting.result.execution_status != "completed":
            raise RuntimeError("无法建立用于复用验证的预先成功结果")

        adapter.failed_application_ids.add(application_ids[1])
        first = await batch_service.run(
            db,
            job_id,
            ScreeningBatchRunRequest(application_ids=application_ids),
        )
        first_statuses = [item.status.value for item in first.items]
        expected = ["completed", "failed", "blocked", "reused", "completed"]
        if first_statuses != expected:
            raise RuntimeError(f"批量混合状态不符合预期：{first_statuses}")

        adapter.failed_application_ids.clear()
        retry = await batch_service.run(
            db,
            job_id,
            ScreeningBatchRunRequest(
                application_ids=application_ids,
                retry_failed_only=True,
            ),
        )
        retry_statuses = [item.status.value for item in retry.items]
        if retry_statuses != ["skipped", "completed", "skipped", "skipped", "skipped"]:
            raise RuntimeError(f"仅重试失败项不符合预期：{retry_statuses}")

        stored = list(
            (
                await db.scalars(
                    select(ScreeningResult)
                    .where(ScreeningResult.application_id.in_(application_ids))
                    .order_by(
                        ScreeningResult.application_id,
                        ScreeningResult.attempt_number,
                    )
                )
            ).all()
        )
        stored_by_application = {
            application_id: [
                item.execution_status
                for item in stored
                if item.application_id == application_id
            ]
            for application_id in application_ids
        }
        expected_stored = {
            application_ids[0]: ["completed"],
            application_ids[1]: ["failed", "completed"],
            application_ids[2]: ["blocked"],
            application_ids[3]: ["completed"],
            application_ids[4]: ["completed"],
        }
        if stored_by_application != expected_stored:
            raise RuntimeError(f"逐项持久化结果不符合预期：{stored_by_application}")

        print(
            json.dumps(
                {
                    "job_id": job_id,
                    "application_ids": application_ids,
                    "first_batch_statuses": first_statuses,
                    "first_batch_summary": first.summary.model_dump(),
                    "retry_statuses": retry_statuses,
                    "retry_summary": retry.summary.model_dump(),
                    "stored_attempts": stored_by_application,
                    "controlled_model_calls": adapter.calls,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    asyncio.run(_verify())
