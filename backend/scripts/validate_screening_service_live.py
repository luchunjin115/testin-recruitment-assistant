from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app.adapters.screening_model import (
    DeepSeekScreeningModelAdapter,
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
from app.models.work_experience import WorkExperience
from app.schemas.application import ScreeningRunRequest
from app.schemas.screening_evaluation import ScreeningSemanticEvaluation
from app.services.screening_rubric_service import ScreeningRubricService
from app.services.screening_service import ScreeningService


class CountingAdapter:
    def __init__(self, adapter: DeepSeekScreeningModelAdapter) -> None:
        self.adapter = adapter
        self.calls = 0
        self.last_content: str | None = None
        self.last_items = None
        self.last_material = None

    async def evaluate(self, *args, **kwargs):
        self.calls += 1
        self.last_items = args[1]
        self.last_material = args[2]
        result = await self.adapter.evaluate(*args, **kwargs)
        self.last_content = result.content
        return result

    def safe_validation_diagnostic(self) -> dict:
        if self.last_content is None:
            return {"stage": "empty_adapter_result"}
        try:
            evaluation = ScreeningSemanticEvaluation.model_validate_json(
                self.last_content
            )
        except ValidationError as exc:
            return {
                "stage": "schema",
                "errors": [
                    {
                        "loc": [str(part) for part in error["loc"]],
                        "type": error["type"],
                        "message": error["msg"],
                    }
                    for error in exc.errors(include_input=False)
                ],
            }
        try:
            evaluation.validate_against(self.last_items, self.last_material)
        except ValueError as exc:
            return {"stage": "business_validation", "message": str(exc)}
        return {"stage": "passed_when_rechecked"}


class TimeoutAdapter:
    async def evaluate(self, *args, **kwargs):
        del args, kwargs
        raise ScreeningModelTimeoutError("候选人语义评价模型调用超时")


def _semantic_items() -> list[dict]:
    return [
        {
            "key": "backend_delivery",
            "name": "后端交付能力",
            "description": "评价是否实际交付过可运行的后端服务",
            "dimension": "must_have_requirements",
            "max_score": 10,
            "suggested_share": 20,
            "high_score_anchor": "独立交付核心服务并有明确结果",
            "mid_score_anchor": "参与服务开发并承担部分职责",
            "low_score_anchor": "只有学习描述或缺少实际交付职责",
            "source": "hr_manual",
        },
        {
            "key": "responsibility_ownership",
            "name": "职责承担深度",
            "description": "评价在工作经历中承担职责的深度",
            "dimension": "work_experience_relevance",
            "max_score": 10,
            "suggested_share": 20,
            "high_score_anchor": "负责核心模块并处理复杂问题",
            "mid_score_anchor": "负责明确模块并能说明工作内容",
            "low_score_anchor": "职责描述笼统或仅参与辅助工作",
            "source": "hr_manual",
        },
        {
            "key": "project_depth",
            "name": "项目与成果深度",
            "description": "评价项目复杂度、技术深度和可核对成果",
            "dimension": "projects_and_capability",
            "max_score": 10,
            "suggested_share": 20,
            "high_score_anchor": "复杂项目中有明确技术方案和量化成果",
            "mid_score_anchor": "有相关项目和可说明的实现内容",
            "low_score_anchor": "项目相关性或成果证据较弱",
            "source": "hr_manual",
        },
        {
            "key": "engineering_practice",
            "name": "工程实践",
            "description": "评价测试、数据库和交付方面的工程实践",
            "dimension": "preferred_qualifications",
            "max_score": 10,
            "suggested_share": 20,
            "high_score_anchor": "具备完整测试、数据库和稳定交付实践",
            "mid_score_anchor": "具备部分工程实践证据",
            "low_score_anchor": "缺少可核对的工程实践",
            "source": "hr_manual",
        },
    ]


async def _create_fixture() -> int:
    requirements = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台后端服务与数据库设计"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 3,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": ["FastAPI"],
        "additional_requirements": [],
    }
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        job = Job(
            title="虚构 Python 后端工程师",
            department="虚构研发部",
            description="负责招聘平台后端服务与数据库设计",
            requirements=requirements,
            status="open",
        )
        candidate = Candidate(
            name="虚构候选人甲",
            phone="13800138000",
            email="synthetic@example.com",
            current_title="后端工程师",
            work_years=5,
            education_level="本科",
            parsed_data={
                "draft": {
                    "basic_info": {
                        "name": "虚构候选人甲",
                        "phone": "13800138000",
                        "email": "synthetic@example.com",
                        "current_title": "后端工程师",
                        "work_years": 5,
                        "education_level": "本科",
                    },
                    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                    "work_experiences": [
                        {
                            "company": "虚构科技公司",
                            "title": "后端工程师",
                            "description": "负责招聘平台后端服务与数据库设计",
                            "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                        }
                    ],
                    "project_experiences": [
                        {
                            "project_name": "虚构招聘平台",
                            "role": "后端负责人",
                            "description": "设计异步 API 和 PostgreSQL 数据模型",
                            "tech_stack": ["FastAPI", "PostgreSQL", "Docker"],
                            "achievements": "将核心接口平均响应时间从 400ms 降低到 180ms",
                        }
                    ],
                }
            },
        )
        db.add_all([job, candidate])
        await db.flush()
        db.add(
            WorkExperience(
                candidate_id=candidate.id,
                company="虚构科技公司",
                title="后端工程师",
                description="负责招聘平台后端服务与数据库设计",
                tech_stack=["Python", "FastAPI", "PostgreSQL"],
            )
        )
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="synthetic-step7.txt",
            file_path="validation/synthetic-step7.txt",
            file_type="text/plain",
            raw_text=(
                "姓名：虚构候选人甲\n"
                "电话：13800138000\n"
                "邮箱：synthetic@example.com\n"
                "具备 5 年后端开发经验。\n"
                "负责招聘平台后端服务与数据库设计。\n"
                "使用 Python、FastAPI 和 PostgreSQL 设计异步 API。\n"
                "将核心接口平均响应时间从 400ms 降低到 180ms。\n"
                "使用 Docker 完成开发环境交付。"
            ),
            parsed_snapshot=candidate.parsed_data,
            parse_status="parsed",
            structure_status="structured",
            structure_schema_version="1.0",
        )
        db.add(resume)
        await db.flush()
        rubric = JobScreeningRubric(
            job_id=job.id,
            version=1,
            must_have_requirements_weight=40,
            work_experience_relevance_weight=25,
            projects_and_capability_weight=20,
            preferred_qualifications_weight=10,
            keywords_and_additional_weight=5,
            schema_version="2.0",
            subcriteria_version="2.0",
            recommendation_thresholds_version="1.0",
            fairness_rules_version="1.0",
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
            change_detail="步骤 7 隔离验证",
            confirmed_by="validation",
            confirmed_at=datetime.now(timezone.utc),
        )
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
        db.add_all([rubric, application])
        await db.commit()
        await db.refresh(application)
        return application.id


async def _verify() -> None:
    application_id = await _create_fixture()
    settings = get_settings()
    counting = CountingAdapter(DeepSeekScreeningModelAdapter(settings=settings))
    service = ScreeningService(model_adapter=counting, settings=settings)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        first = await service.run(db, application_id)
        if first.result.execution_status != "completed":
            raise RuntimeError(
                f"真实评分没有完成：{first.result.execution_status}/"
                f"{first.result.error_code}/"
                f"{json.dumps(counting.safe_validation_diagnostic(), ensure_ascii=False)}"
            )
        reused = await service.run(db, application_id)
        if not reused.reused or counting.calls != 1:
            raise RuntimeError("相同输入没有复用第一次成功结果")

        snapshot = json.dumps(
            first.result.candidate_input_snapshot,
            ensure_ascii=False,
        )
        for forbidden in ("虚构候选人甲", "13800138000", "synthetic@example.com"):
            if forbidden in snapshot:
                raise RuntimeError("候选人直接身份信息进入了模型输入快照")

        resume = await db.get(Resume, first.result.resume_id)
        if resume is None:
            raise RuntimeError("验证简历不存在")
        resume.raw_text = f"{resume.raw_text}\n新增一条会改变输入指纹的虚构项目说明。"
        await db.commit()

    failing_service = ScreeningService(model_adapter=TimeoutAdapter(), settings=settings)
    async with sessionmaker() as db:
        failed = await failing_service.run(db, application_id)
        application = await db.get(Application, application_id)
        previous = await db.get(ScreeningResult, first.result.id)
        if failed.result.execution_status != "failed":
            raise RuntimeError("模拟超时没有保存为 failed 结果")
        if application is None or application.current_screening_result_id != first.result.id:
            raise RuntimeError("新评分失败后覆盖了旧成功结果")
        if previous is None or not previous.is_outdated:
            raise RuntimeError("输入变化后旧成功结果没有标记 outdated")
        old_success_preserved = (
            application.current_screening_result_id == first.result.id
        )
        old_success_outdated = previous.is_outdated

        running = ScreeningResult(
            candidate_id=first.result.candidate_id,
            job_id=first.result.job_id,
            application_id=application_id,
            resume_id=first.result.resume_id,
            attempt_number=3,
            execution_status="screening",
            input_fingerprint="a" * 64,
            started_at=datetime.now(timezone.utc),
        )
        db.add(running)
        await db.commit()
        duplicate = ScreeningResult(
            candidate_id=first.result.candidate_id,
            job_id=first.result.job_id,
            application_id=application_id,
            resume_id=first.result.resume_id,
            attempt_number=4,
            execution_status="screening",
            input_fingerprint="b" * 64,
            started_at=datetime.now(timezone.utc),
        )
        db.add(duplicate)
        concurrency_constraint_enforced = False
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            concurrency_constraint_enforced = True
        if not concurrency_constraint_enforced:
            raise RuntimeError("PostgreSQL 未阻止同一 Application 的并发评分")

        running = await db.scalar(
            select(ScreeningResult).where(
                ScreeningResult.application_id == application_id,
                ScreeningResult.attempt_number == 3,
            )
        )
        if running is None:
            raise RuntimeError("并发约束验证记录不存在")
        running.execution_status = "failed"
        running.error_code = "validation_cleanup"
        running.error_message = "隔离验证结束，关闭人工构造的运行记录"
        running.finished_at = datetime.now(timezone.utc)
        await db.commit()

        stored_attempts = list(
            (
                await db.scalars(
                    select(ScreeningResult)
                    .where(ScreeningResult.application_id == application_id)
                    .order_by(ScreeningResult.attempt_number)
                )
            ).all()
        )
        print(
            json.dumps(
                {
                    "application_id": application_id,
                    "first_attempt": first.result.attempt_number,
                    "first_status": first.result.execution_status,
                    "overall_score": first.result.overall_score,
                    "recommendation": first.result.recommendation,
                    "evidence_coverage_rate": float(
                        first.result.evidence_coverage_rate or 0
                    ),
                    "real_model_calls": counting.calls,
                    "same_input_reused": reused.reused,
                    "failed_attempt_status": failed.result.execution_status,
                    "old_success_preserved": old_success_preserved,
                    "old_success_outdated": old_success_outdated,
                    "concurrency_constraint_enforced": concurrency_constraint_enforced,
                    "stored_attempt_statuses": [
                        item.execution_status for item in stored_attempts
                    ],
                    "model": first.result.model_name,
                    "tokens": {
                        "input": first.result.prompt_tokens,
                        "output": first.result.completion_tokens,
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    asyncio.run(_verify())
