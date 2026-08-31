from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.adapters.screening_evaluation import (
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterResult,
)
from app.api import applications, job_evaluation_plans, screening
from app.core.config import Settings
from app.core.database import get_db
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.report import Report
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.models.stage_history import StageHistory
from app.services.screening_service import screening_service


NOW = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)
COUNTED_MODELS = (
    Job,
    Candidate,
    Resume,
    Application,
    JobEvaluationPlan,
    ScreeningRun,
    ScreeningReport,
    StageHistory,
    Report,
)


async def _counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


def _plan_adapter() -> FakeJobEvaluationPlanAdapter:
    payload = {
        "criteria": [
            {
                "name": "Python 后端项目经验",
                "importance": "required",
                "description": "核对 Python 后端项目实践。",
                "screening_focus": "寻找 Python API 服务证据。",
                "sources": [
                    {
                        "source_field": "candidate_requirements",
                        "source_quote": "必须具备 Python 后端项目经验",
                    }
                ],
            }
        ]
    }
    return FakeJobEvaluationPlanAdapter(
        [
            JobEvaluationPlanAdapterResult(
                content=json.dumps(payload, ensure_ascii=False),
                model="fake-close07-plan-model",
                finish_reason="stop",
                input_tokens=100,
                output_tokens=50,
            )
        ]
    )


def _report_adapter(score: int = 82) -> FakeScreeningEvaluationAdapter:
    payload = {
        "overall_score": score,
        "overall_summary": "Python API 项目证据与岗位要求整体匹配。",
        "criterion_assessments": [
            {
                "criterion_id": "criterion:0001",
                "score": 8,
                "reason": "简历记录了 Python API 服务交付。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [
                    {"quote": "使用 Python 开发 API 服务", "section": "工作经历"}
                ],
            }
        ],
        "strengths": [
            {
                "summary": "具备 Python API 服务实践。",
                "criterion_ids": ["criterion:0001"],
                "evidence": [
                    {"quote": "使用 Python 开发 API 服务", "section": "工作经历"}
                ],
            }
        ],
        "gaps": [],
        "risks_or_conflicts": [],
        "missing_info": [],
        "hr_follow_up_questions": ["请说明该 API 项目的职责边界。"],
    }
    return FakeScreeningEvaluationAdapter(
        [
            ScreeningEvaluationAdapterResult(
                content=json.dumps(payload, ensure_ascii=False),
                model="fake-close07-report-model",
                finish_reason="stop",
                input_tokens=120,
                output_tokens=60,
            )
        ]
    )


class Stage7Close07V5ApiPostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.settings = Settings(_env_file=None, DEEPSEEK_API_KEY="")
        self.engine = create_async_engine(
            self.settings.async_database_url,
            poolclass=NullPool,
        )
        async with AsyncSession(self.engine) as outside:
            self.counts_before = await _counts(outside)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        app = FastAPI()
        applications.install_application_exception_handlers(app)
        screening.install_screening_exception_handlers(app)
        app.include_router(job_evaluation_plans.router, prefix="/api/v2")
        app.include_router(applications.router, prefix="/api/v2")
        app.include_router(screening.router, prefix="/api/v2")

        async def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://close07.test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            counts_after = await _counts(outside)
        await self.engine.dispose()
        self.assertEqual(counts_after, self.counts_before)

    async def test_v5_http_service_worker_decision_and_postgres_chain(self) -> None:
        job = Job(
            title="CLOSE-07 虚构 Python 岗位",
            department="验收部",
            job_background="建设企业内部服务。",
            job_responsibilities="负责 API 服务交付。",
            candidate_requirements="必须具备 Python 后端项目经验。",
            preferred_qualifications="有容器化实践者优先。",
            public_notes="仅用于隔离验收。",
            status="open",
        )
        self.db.add(job)
        await self.db.commit()

        plan_adapter = _plan_adapter()
        with patch(
            "app.services.job_evaluation_plan_service.DeepSeekJobEvaluationPlanAdapter",
            return_value=plan_adapter,
        ):
            generated = await self.client.post(
                f"/api/v2/jobs/{job.id}/evaluation-plan/generate"
            )
        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertEqual(generated.json()["schema_version"], "5.0")
        self.assertEqual(generated.json()["status"], "pending_confirmation")
        self.assertEqual(len(plan_adapter.v5_calls), 1)

        confirmed = await self.client.post(
            f"/api/v2/jobs/{job.id}/evaluation-plan/confirm",
            json={"edit_version": generated.json()["edit_version"]},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["status"], "ready")

        candidate = Candidate(name="CLOSE-07 虚构候选人")
        self.db.add(candidate)
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="close07.txt",
            file_path="private/close07.txt",
            file_type="text/plain",
            raw_text="工作经历\n使用 Python 开发 API 服务",
            parse_status="parsed",
        )
        self.db.add(resume)
        await self.db.flush()
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            current_resume_id=resume.id,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="applied",
            hr_decision="pending",
            applied_at=NOW,
        )
        self.db.add(application)
        await self.db.commit()

        trigger = await self.client.post(
            f"/api/v2/applications/{application.id}/screening"
        )
        self.assertEqual(trigger.status_code, 202, trigger.text)
        self.assertEqual(trigger.json()["run"]["status"], "queued")

        claimed = await screening_service.claim_next_run(
            self.db,
            worker_id="close07-worker",
            lease_seconds=60,
            clock=lambda: NOW,
        )
        self.assertIsNotNone(claimed)
        report_adapter = _report_adapter()
        await screening_service.execute_run(
            self.db,
            claimed.id,
            adapter=report_adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(len(report_adapter.calls), 1)

        state = await self.client.get(
            f"/api/v2/applications/{application.id}/screening"
        )
        self.assertEqual(state.status_code, 200, state.text)
        self.assertEqual(state.json()["latest_run"]["status"], "succeeded")
        self.assertEqual(state.json()["report"]["schema_version"], "5.0")
        self.assertEqual(state.json()["report"]["overall_score"], 82)

        passed = await self.client.post(
            f"/api/v2/applications/{application.id}/pass",
            json={"reason_code": "meets_requirements"},
        )
        self.assertEqual(passed.status_code, 200, passed.text)
        self.assertEqual(passed.json()["hr_decision"], "passed")
        backup = await self.client.post(
            f"/api/v2/applications/{application.id}/backup",
            json={
                "reason_code": "information_pending",
                "reason_detail": "等待补充可验证项目材料",
            },
        )
        self.assertEqual(backup.status_code, 200, backup.text)
        self.assertEqual(backup.json()["hr_decision"], "backup")
        history = await self.client.get(
            f"/api/v2/applications/{application.id}/history"
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(
            [item["to_hr_decision"] for item in history.json()][-2:],
            ["passed", "backup"],
        )

        current_reports = await self.db.scalars(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application.id,
                ScreeningReport.is_current.is_(True),
            )
        )
        self.assertEqual(len(current_reports.all()), 1)
