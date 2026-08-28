from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

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
from app.api import screening as screening_api
from app.core.config import Settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.report import Report
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.models.stage_history import StageHistory
from app.schemas.screening import (
    ScreeningRunStatus,
    ScreeningRunTriggerType,
    ScreeningWaitingReason,
)
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from app.services.screening_service import screening_service


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
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


def _adapter_result(payload: dict) -> JobEvaluationPlanAdapterResult:
    return JobEvaluationPlanAdapterResult(
        content=json.dumps(payload, ensure_ascii=False),
        model="fake-plan-model",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
    )


def _plan_adapter() -> FakeJobEvaluationPlanAdapter:
    return FakeJobEvaluationPlanAdapter(
        [
            _adapter_result(
                {
                    "schema_version": "4.0",
                    "fact_candidates": [
                        {
                            "candidate_id": "candidate:0001",
                            "category": "experience",
                            "sources": [
                                {
                                    "source_field": "candidate_requirements",
                                    "source_unit_id": "candidate_requirements:0001",
                                    "source_quote": "具备 Python 后端开发经验",
                                }
                            ],
                        }
                    ],
                    "source_reviews": [
                        {
                            "source_unit_id": "candidate_requirements:0001",
                            "disposition": "evaluation",
                            "candidate_ids": ["candidate:0001"],
                            "non_evaluation_reason": None,
                            "warning_codes": [],
                        }
                    ],
                }
            ),
            _adapter_result(
                {"schema_version": "4.0", "status": "passed", "findings": []}
            ),
            _adapter_result(
                {
                    "schema_version": "4.0",
                    "criteria": [
                        {
                            "name": "Python 后端工程经验",
                            "fact_ids": ["fact:0001"],
                        }
                    ],
                }
            ),
        ]
    )


def _screening_payload() -> dict:
    return {
        "overall_score": 80,
        "overall_summary": "Python 项目经验与岗位要求整体较匹配。",
        "requirement_assessments": [
            {
                "requirement_key": "fact:0001",
                "score": 8,
                "reason": "使用 Python 开发 API 服务，相关经验较充分。",
                "calculation_note": None,
                "evidence": [
                    {
                        "quote": "使用 Python 开发 API 服务",
                        "section": "工作经历",
                    }
                ],
            }
        ],
        "bonus_highlights": [],
        "tradeoff_reason": None,
        "interview_questions": ["请介绍 Python API 项目中的具体职责。"],
    }


def _screening_result(payload: dict | None = None) -> ScreeningEvaluationAdapterResult:
    return ScreeningEvaluationAdapterResult(
        content=json.dumps(payload or _screening_payload(), ensure_ascii=False),
        model="fake-screening-model",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
    )


async def _table_counts(db: AsyncSession) -> dict[str, int]:
    return {
        model.__tablename__: int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in COUNTED_MODELS
    }


class Stage7R4GFakeApiPostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            self.settings.async_database_url,
            poolclass=NullPool,
        )
        async with AsyncSession(self.engine) as outside_db:
            self.counts_before = await _table_counts(outside_db)

        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside_db:
            counts_after = await _table_counts(outside_db)
        await self.engine.dispose()
        self.assertEqual(counts_after, self.counts_before)

    async def test_legacy_v4_plan_is_read_only_and_cannot_start_new_screening(self) -> None:
        job = Job(
            title="7R4-G Fake integration job",
            department="Engineering",
            candidate_requirements="具备 Python 后端开发经验",
            status="open",
        )
        candidate = Candidate(name="7R4-G Fake candidate")
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="7r4g-fake-resume.txt",
            file_path="private/7r4g-fake-resume.txt",
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
        application_id = application.id

        waiting = await screening_api.trigger_application_screening(
            application_id,
            self.db,
        )
        self.assertEqual(waiting.run.status, ScreeningRunStatus.WAITING_PLAN)
        self.assertEqual(
            waiting.run.waiting_reason,
            ScreeningWaitingReason.PLAN_MISSING,
        )

        plan_adapter = _plan_adapter()
        with patch(
            "app.services.job_evaluation_plan_service.DeepSeekJobEvaluationPlanAdapter",
            return_value=plan_adapter,
        ):
            pending_plan = await job_evaluation_plan_service.generate_for_job(
                self.db,
                job.id,
            )
        self.assertEqual(pending_plan.status, "pending_confirmation")
        self.assertEqual(pending_plan.schema_version, "4.0")
        self.assertEqual(pending_plan.generation_audit["business_call_count"], 3)
        self.assertEqual(len(plan_adapter.v4_calls), 3)

        await screening_service.after_plan_changed(
            self.db,
            job.id,
            plan_ready=False,
        )
        pending_state = await screening_api.get_application_screening(
            application_id,
            self.db,
        )
        self.assertEqual(
            pending_state.latest_run.waiting_reason,
            ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED,
        )

        ready_plan = await job_evaluation_plan_service.confirm_current_plan(
            self.db,
            job.id,
        )
        self.assertEqual(ready_plan.status, "ready")
        self.assertEqual(len(plan_adapter.v4_calls), 3)

        await screening_service.after_plan_changed(
            self.db,
            job.id,
            plan_ready=True,
        )
        final_state = await screening_api.get_application_screening(
            application_id,
            self.db,
        )
        self.assertEqual(final_state.latest_run.status, ScreeningRunStatus.WAITING_PLAN)
        self.assertEqual(
            final_state.latest_run.waiting_reason,
            ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED,
        )
        screening_adapter = FakeScreeningEvaluationAdapter([_screening_result()])
        self.assertEqual(len(screening_adapter.calls), 0)
        self.assertIsNone(final_state.report)
        self.assertEqual(application.recruitment_stage, "applied")
        self.assertEqual(application.hr_decision, "pending")
