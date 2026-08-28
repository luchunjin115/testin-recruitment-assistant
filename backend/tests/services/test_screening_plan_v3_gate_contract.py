from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from sqlalchemy import null
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.adapters.screening_evaluation import (
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterResult,
)
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from app.services.screening_service import (
    ScreeningApplicationNotEligibleError,
    screening_service,
)


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


class ScreeningPlanV5GateContractTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.settings = Settings(_env_file=None)
        self.engine = create_async_engine(
            self.settings.async_database_url,
            poolclass=NullPool,
        )
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        candidate = Candidate(name="五段式合同候选人")
        job = Job(
            title="AI 应用工程师",
            department="技术研发部",
            location="长沙",
            employment_type="full_time",
            headcount=1,
            job_background="建设企业 AI 应用平台",
            job_responsibilities="负责 AI 应用设计、开发和上线",
            candidate_requirements="具备 Python 后端开发经验",
            preferred_qualifications="有 RAG 项目经验者优先",
            public_notes="面试共三轮",
            status="open",
        )
        self.db.add_all([candidate, job])
        await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="v3-contract.txt",
            file_path="private/v3-contract.txt",
            file_type="text/plain",
            raw_text="工作经历\n使用 Python 开发 AI 应用",
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
        self.job = job
        self.application = application

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def _add_plan(
        self,
        *,
        status: str = "ready",
        schema_version: str = "5.0",
        is_current: bool = True,
    ) -> JobEvaluationPlan:
        if schema_version == "5.0":
            snapshot = job_evaluation_plan_service.build_v5_input_snapshot(self.job)
            has_payload = status in {
                "pending_confirmation",
                "ready",
                "outdated",
            }
            plan = JobEvaluationPlan(
                job_id=self.job.id,
                jd_fingerprint=job_evaluation_plan_service.fingerprint_snapshot(
                    snapshot
                ),
                status=status,
                is_current=is_current,
                items=null(),
                structured_coverage=null(),
                free_text_coverage=null(),
                source_review_summary=null(),
                requirement_facts=null(),
                evaluation_criteria=null(),
                coverage_review_summary=null(),
                generation_audit=null(),
                v5_criteria=(
                    [
                        {
                            "criterion_id": "criterion:0001",
                            "name": "Python 后端开发",
                            "importance": "required",
                            "description": "核对 Python 后端开发实践。",
                            "screening_focus": "寻找 Python 项目证据。",
                            "origin": "ai_from_jd",
                            "sources": [
                                {
                                    "source_field": "candidate_requirements",
                                    "source_quote": self.job.candidate_requirements,
                                }
                            ],
                            "hr_note": None,
                        }
                    ]
                    if has_payload
                    else null()
                ),
                edit_version=1,
                confirmed_at=NOW if status == "ready" else None,
                warnings=[],
                prompt_version="job_evaluation_plan_lightweight_v2",
                model_version="fake-plan-model",
                schema_version="5.0",
                input_fingerprint=job_evaluation_plan_service.fingerprint_input(
                    snapshot
                ),
                input_snapshot=snapshot.model_dump(mode="json"),
                error_code=(
                    "JOB_EVALUATION_PLAN_FAILED" if status == "failed" else None
                ),
                error_message=("评价计划生成失败" if status == "failed" else None),
                completed_at=None if status == "generating" else NOW,
            )
            self.db.add(plan)
            await self.db.commit()
            return plan
        snapshot = (
            job_evaluation_plan_service.build_v4_input_snapshot(self.job)
            if schema_version == "4.0"
            else job_evaluation_plan_service.build_input_snapshot(self.job)
        )
        snapshot_payload = snapshot.model_dump(mode="json")
        source_units = snapshot.source_units or []
        sources = [
            {
                "source_field": unit.source_field,
                "source_unit_id": unit.source_unit_id,
                "source_quote": unit.source_text,
            }
            for unit in source_units
        ]
        legacy_items = (
            [
                {
                    "key": "item:0001",
                    "title": "岗位综合要求",
                    "category": "experience",
                    "priority": "required",
                    "sources": sources,
                }
            ]
            if schema_version != "4.0" and status == "ready"
            else []
        )
        v3_summary = {
            "rule_version": "five_section_source_units_v1",
            "total_units": len(source_units),
            "reviewed_units": len(source_units),
            "evaluation_units": len(source_units),
            "non_evaluation_units": 0,
            "all_reviewed": True,
            "units": [
                {
                    "source_unit_id": unit.source_unit_id,
                    "disposition": "evaluation",
                    "non_evaluation_reason": None,
                    "item_keys": ["item:0001"],
                }
                for unit in source_units
            ],
        }
        has_v4_payload = schema_version == "4.0" and status in {
            "pending_confirmation",
            "ready",
            "outdated",
        }
        facts = [
            {
                "fact_id": "fact:0001",
                "category": "experience",
                "priority": "required",
                "sources": sources,
            }
        ]
        criteria = [
            {
                "criterion_id": "criterion:0001",
                "name": "岗位综合要求",
                "fact_ids": ["fact:0001"],
            }
        ]
        v4_summary = {
            "rule_version": "five_section_source_units_v1",
            "total_units": len(source_units),
            "reviewed_units": len(source_units),
            "evaluation_units": len(source_units),
            "non_evaluation_units": 0,
            "all_reviewed": True,
            "units": [
                {
                    "source_unit_id": unit.source_unit_id,
                    "disposition": "evaluation",
                    "non_evaluation_reason": None,
                    "fact_ids": ["fact:0001"],
                }
                for unit in source_units
            ],
        }
        plan = JobEvaluationPlan(
            job_id=self.job.id,
            jd_fingerprint=job_evaluation_plan_service.fingerprint_snapshot(snapshot),
            status=status,
            is_current=is_current,
            items=legacy_items if schema_version != "4.0" else null(),
            structured_coverage={} if schema_version == "2.0" else null(),
            free_text_coverage=(
                {
                    "rule_version": "jd_source_units_v1",
                    "all_reviewed": True,
                    "units": [],
                }
                if schema_version == "2.0"
                else null()
            ),
            warnings=[],
            prompt_version=(
                "job_requirement_fact_extraction_v1"
                if schema_version == "4.0"
                else "job_evaluation_plan_v5"
            ),
            model_version="fake-plan-model",
            schema_version=schema_version,
            input_fingerprint=job_evaluation_plan_service.fingerprint_input(snapshot),
            input_snapshot=snapshot_payload,
            error_code=("JOB_EVALUATION_PLAN_FAILED" if status == "failed" else None),
            error_message=("评价计划生成失败" if status == "failed" else None),
            completed_at=(None if status == "generating" else NOW),
        )
        plan.source_review_summary = (
            v4_summary
            if has_v4_payload
            else v3_summary
            if schema_version == "3.0" and status == "ready"
            else null()
        )
        plan.requirement_facts = facts if has_v4_payload else null()
        plan.evaluation_criteria = criteria if has_v4_payload else null()
        plan.coverage_review_summary = (
            {
                "status": "passed",
                "findings": [],
                "repair_performed": False,
                "reviewed_source_unit_ids": [
                    unit.source_unit_id for unit in source_units
                ],
            }
            if has_v4_payload
            else null()
        )
        plan.generation_audit = (
            {
                "business_call_count": 3,
                "content_repair_count": 0,
                "infrastructure_retry_count": 0,
                "calls": [
                    {
                        "role": role,
                        "prompt_version": prompt_version,
                        "model": "fake-plan-model",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "duration_ms": 10,
                        "infrastructure_retry_count": 0,
                        "result": "succeeded",
                    }
                    for role, prompt_version in (
                        ("fact_extraction", "job_requirement_fact_extraction_v1"),
                        ("coverage_review", "job_requirement_coverage_review_v1"),
                        ("criterion_grouping", "job_evaluation_criterion_grouping_v1"),
                    )
                ],
            }
            if has_v4_payload
            else null()
        )
        self.db.add(plan)
        await self.db.commit()
        return plan

    async def test_missing_plan_waits_with_plan_missing_reason(self) -> None:
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_missing")

    async def test_same_waiting_input_reuses_one_run(self) -> None:
        first = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        second = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertTrue(second.reused_run)
        self.assertEqual(second.run.id, first.run.id)

    async def test_closed_job_has_priority_over_resume_and_plan_waiting(self) -> None:
        resume = await self.db.get(Resume, self.application.current_resume_id)
        resume.parse_status = "pending"
        resume.raw_text = None
        self.job.status = "closed"
        await self.db.commit()

        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
            allow_closed_pending=True,
        )
        self.assertEqual(result.run.status, "paused")
        self.assertEqual(result.run.waiting_reason, "job_closed")

    async def test_resume_waiting_has_priority_over_missing_plan(self) -> None:
        resume = await self.db.get(Resume, self.application.current_resume_id)
        resume.parse_status = "pending"
        resume.raw_text = None
        await self.db.commit()

        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_resume")
        self.assertIsNone(result.run.waiting_reason)

    async def test_ended_application_cannot_start_screening(self) -> None:
        self.application.lifecycle_status = "ended"
        await self.db.commit()

        with self.assertRaises(ScreeningApplicationNotEligibleError):
            await screening_service.trigger(
                self.db,
                self.application.id,
                settings=self.settings,
            )

    async def test_only_current_ready_v5_plan_can_queue_screening(self) -> None:
        plan = await self._add_plan()
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "queued")
        self.assertEqual(result.run.job_evaluation_plan_id, plan.id)

    async def test_legacy_plan_waits_with_contract_outdated_reason(self) -> None:
        await self._add_plan(schema_version="2.0")
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_contract_outdated")

    async def test_generating_plan_waits_with_generating_reason(self) -> None:
        await self._add_plan(status="generating")
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_generating")

    async def test_pending_plan_waits_for_hr_confirmation(self) -> None:
        await self._add_plan(status="pending_confirmation")
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_pending_confirmation")

    async def test_failed_plan_waits_with_failed_reason(self) -> None:
        await self._add_plan(status="failed")
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_failed")

    async def test_only_outdated_history_waits_with_outdated_reason(self) -> None:
        await self._add_plan(status="outdated", is_current=False)
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_outdated")

    async def test_current_plan_for_previous_job_input_waits_as_outdated(self) -> None:
        await self._add_plan()
        self.job.candidate_requirements = "具备 Java 后端开发经验"
        await self.db.commit()

        result = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(result.run.status, "waiting_plan")
        self.assertEqual(result.run.waiting_reason, "plan_outdated")

    async def test_plan_ready_reconciles_first_waiting_application_automatically(self) -> None:
        waiting = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertEqual(waiting.run.status, "waiting_plan")
        await self._add_plan()
        await screening_service.after_plan_changed(
            self.db,
            self.job.id,
            plan_ready=True,
        )
        await self.db.refresh(waiting.run)
        self.assertEqual(waiting.run.status, "queued")

    async def test_failed_plan_reconciles_existing_waiting_reason_in_place(self) -> None:
        waiting = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        await self._add_plan(status="failed")

        await screening_service.after_plan_changed(
            self.db,
            self.job.id,
            plan_ready=False,
        )

        await self.db.refresh(waiting.run)
        self.assertEqual(waiting.run.status, "waiting_plan")
        self.assertEqual(waiting.run.waiting_reason, "plan_failed")

    async def test_waiting_does_not_change_hr_decision_stage_or_lifecycle(self) -> None:
        before = (
            self.application.hr_decision,
            self.application.recruitment_stage,
            self.application.lifecycle_status,
        )
        await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        await self.db.refresh(self.application)
        self.assertEqual(
            (
                self.application.hr_decision,
                self.application.recruitment_stage,
                self.application.lifecycle_status,
            ),
            before,
        )

    async def test_ready_v5_plan_runs_by_criterion_and_preserves_hr_authority(self) -> None:
        application_id = self.application.id
        plan = await self._add_plan()
        plan_id = plan.id
        queued = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        claimed = await screening_service.claim_next_run(
            self.db,
            worker_id="v3-contract-worker",
            lease_seconds=60,
            clock=lambda: NOW,
        )
        self.assertEqual(claimed.id, queued.run.id)
        adapter = FakeScreeningEvaluationAdapter(
            [
                ScreeningEvaluationAdapterResult(
                    content=json.dumps(
                        {
                            "overall_score": 80,
                            "overall_summary": "候选人的 Python 经历与岗位要求匹配。",
                            "criterion_assessments": [
                                {
                                    "criterion_id": "criterion:0001",
                                    "score": 8,
                                    "reason": "简历包含 Python AI 应用开发经历。",
                                    "calculation_note": None,
                                    "experience_period_fact_keys": [],
                                    "evidence": [
                                        {
                                            "quote": "使用 Python 开发 AI 应用",
                                            "section": "工作经历",
                                        }
                                    ],
                                }
                            ],
                            "strengths": [
                                {
                                    "summary": "有 Python AI 应用开发经历。",
                                    "criterion_ids": ["criterion:0001"],
                                    "evidence": [
                                        {
                                            "quote": "使用 Python 开发 AI 应用",
                                            "section": "工作经历",
                                        }
                                    ],
                                }
                            ],
                            "gaps": [
                                {
                                    "summary": "项目规模仍需核实。",
                                    "criterion_ids": ["criterion:0001"],
                                    "evidence": [],
                                }
                            ],
                            "risks_or_conflicts": [],
                            "missing_info": [
                                {
                                    "summary": "缺少项目规模信息。",
                                    "criterion_ids": ["criterion:0001"],
                                    "evidence": [],
                                }
                            ],
                            "hr_follow_up_questions": ["请介绍该 AI 应用的职责。"],
                        },
                        ensure_ascii=False,
                    ),
                    model="fake-screening-model",
                    finish_reason="stop",
                    input_tokens=100,
                    output_tokens=50,
                )
            ]
        )

        completed = await screening_service.execute_run(
            self.db,
            claimed.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id
            )
        )
        application = await self.db.get(Application, application_id)

        self.assertEqual(
            completed.status,
            "succeeded",
            (completed.error_code, completed.error_message),
        )
        self.assertEqual(report.job_evaluation_plan_id, plan_id)
        self.assertEqual(
            report.v5_report["criterion_assessments"][0]["assessment"][
                "criterion_id"
            ],
            "criterion:0001",
        )
        self.assertEqual(application.hr_decision, "pending")
        self.assertEqual(application.recruitment_stage, "hr_review")
        self.assertEqual(application.lifecycle_status, "active")
