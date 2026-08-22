import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.screening_evaluation import (
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterResult,
    ScreeningEvaluationTimeoutError,
)
from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.schemas.screening import ScreeningRunStatus, ScreeningRunTriggerType
from app.services.screening_service import (
    ScreeningBatchJobMismatchError,
    ScreeningBatchLimitError,
    screening_service,
)
from app.services.job_evaluation_plan_service import job_evaluation_plan_service


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def requirements() -> dict:
    return {
        "schema_version": "1.0",
        "responsibilities": ["开发后端服务"],
        "required_skills": ["Python"],
        "preferred_skills": [],
        "minimum_work_years": 1,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": [],
        "additional_requirements": [],
    }


def item() -> dict:
    return {
        "key": "requirement:skill:python",
        "title": "Python",
        "category": "skill",
        "priority": "required",
        "source_type": "structured",
        "source_field": "requirements.required_skills",
        "source_quote": None,
    }


def valid_model_result(*, score: int = 80) -> ScreeningEvaluationAdapterResult:
    return ScreeningEvaluationAdapterResult(
        content=json.dumps(
            {
                "overall_score": score,
                "overall_summary": "Python 项目经验与岗位要求整体较匹配。",
                "requirement_assessments": [
                    {
                        "requirement_key": "requirement:skill:python",
                        "score": 8,
                        "reason": "使用 Python 开发 API 服务，岗位相关经验较充分。",
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
                "interview_questions": ["请介绍 Python API 项目的职责。"],
            },
            ensure_ascii=False,
        ),
        model="fake-screening-model",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
    )


class ScreeningServiceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            self.settings_url(),
            poolclass=NullPool,
        )
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.settings = Settings(_env_file=None)
        self.db = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        self._legacy_job_refs: list[Job] = []
        self.application = await self._create_application()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    @staticmethod
    def settings_url() -> str:
        return Settings(_env_file=None).async_database_url

    async def _create_application(
        self,
        *,
        job: Job | None = None,
        parsed: bool = True,
        candidate: Candidate | None = None,
    ) -> Application:
        if job is None:
            job = Job(
                title="后端工程师",
                department="研发部",
                location="上海",
                employment_type="full_time",
                headcount=1,
                job_background=None,
                job_responsibilities="负责 Python API 开发",
                candidate_requirements="具备 Python 开发经验",
                preferred_qualifications=None,
                public_notes=None,
                status="open",
            )
            job.description = "负责 Python API 开发"
            job.requirements = requirements()
            # Keep the test-only legacy attributes alive in SQLAlchemy's weak
            # identity map. Production Job instances never receive them.
            self._legacy_job_refs.append(job)
            self.db.add(job)
            await self.db.flush()
            snapshot = screening_service._sha256(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "department": job.department,
                    "description": job.description,
                    "requirements": requirements(),
                }
            )
            plan = JobEvaluationPlan(
                job_id=job.id,
                jd_fingerprint=snapshot,
                status="ready",
                is_current=True,
                items=[item()],
                structured_coverage={
                    "source_schema_version": "1.0",
                    "fields": [],
                    "all_covered": True,
                },
                warnings=[],
                prompt_version="job_evaluation_plan_v1",
                model_version="fake-plan-model",
                schema_version="1.0",
                input_fingerprint=snapshot,
                input_snapshot={
                    "job_id": job.id,
                    "title": job.title,
                    "department": job.department,
                    "description": job.description,
                    "requirements": requirements(),
                },
                completed_at=NOW,
            )
            self.db.add(plan)
        if candidate is None:
            candidate = Candidate(name="测试候选人")
            self.db.add(candidate)
            await self.db.flush()
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename="resume.txt",
            file_path=f"private/{candidate.id}.txt",
            file_type="text/plain",
            raw_text=("工作经历\n使用 Python 开发 API 服务" if parsed else None),
            parse_status=("parsed" if parsed else "uploaded"),
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
        return application

    async def _queue_and_claim(self) -> ScreeningRun:
        triggered = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertIsNotNone(triggered.run)
        claimed = await screening_service.claim_next_run(
            self.db,
            worker_id="test-worker",
            lease_seconds=300,
            clock=lambda: NOW,
        )
        self.assertIsNotNone(claimed)
        return claimed

    async def _complete_success(self) -> tuple[ScreeningRun, FakeScreeningEvaluationAdapter]:
        run = await self._queue_and_claim()
        adapter = FakeScreeningEvaluationAdapter([valid_model_result()])
        completed = await screening_service.execute_run(
            self.db,
            run.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        return completed, adapter

    async def test_input_fingerprint_is_stable_and_versioned(self) -> None:
        first = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        second = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        changed = await screening_service._build_context(
            self.db,
            self.application,
            self.settings.model_copy(
                update={"SCREENING_EVALUATION_MODEL": "new-model"}
            ),
        )
        self.assertEqual(first.input_fingerprint, second.input_fingerprint)
        self.assertNotEqual(first.input_fingerprint, changed.input_fingerprint)
        self.assertEqual(first.evaluation_reference_at, NOW)
        self.assertEqual(first.evaluation_timezone, "Asia/Shanghai")
        self.assertEqual(
            first.experience_period_facts_rule_version,
            "experience_period_facts_v1",
        )

    async def test_applied_at_is_frozen_in_run_report_and_adapter_input(self) -> None:
        original_applied_at = self.application.applied_at
        completed, adapter = await self._complete_success()
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        self.assertEqual(completed.evaluation_reference_at, original_applied_at)
        self.assertEqual(report.evaluation_reference_at, original_applied_at)
        self.assertEqual(completed.evaluation_timezone, "Asia/Shanghai")
        self.assertEqual(report.evaluation_timezone, "Asia/Shanghai")
        self.assertEqual(
            adapter.calls[0]["evaluation_reference_at"],
            original_applied_at.isoformat(),
        )
        await self.db.refresh(self.application)
        self.assertEqual(self.application.applied_at, original_applied_at)

    async def test_normal_request_and_reassessment_keep_original_reference(self) -> None:
        completed, _ = await self._complete_success()
        original_reference = completed.evaluation_reference_at
        reused = await screening_service.trigger(
            self.db,
            self.application.id,
            settings=self.settings,
        )
        self.assertTrue(reused.reused_report)
        reassessed = await screening_service.trigger(
            self.db,
            self.application.id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        self.assertEqual(reassessed.run.evaluation_reference_at, original_reference)
        self.assertEqual(reassessed.run.input_fingerprint, completed.input_fingerprint)

    async def test_resume_switch_changes_resume_and_fact_fingerprints_not_reference(self) -> None:
        before = await screening_service._build_context(
            self.db,
            self.application,
            self.settings,
        )
        candidate = await self.db.get(Candidate, self.application.candidate_id)
        new_resume = Resume(
            candidate_id=candidate.id,
            job_id=self.application.job_id,
            filename="dated.txt",
            file_path="private/dated.txt",
            file_type="text/plain",
            raw_text="工作经历\n2021.07—至今，使用 Python 开发 API 服务",
            parse_status="parsed",
        )
        self.db.add(new_resume)
        await self.db.commit()
        await screening_service.switch_current_resume(
            self.db,
            self.application.id,
            new_resume.id,
        )
        await self.db.refresh(self.application)
        after = await screening_service._build_context(
            self.db,
            self.application,
            self.settings,
        )
        self.assertEqual(after.evaluation_reference_at, before.evaluation_reference_at)
        self.assertNotEqual(after.resume_fingerprint, before.resume_fingerprint)
        self.assertNotEqual(
            after.experience_period_facts_fingerprint,
            before.experience_period_facts_fingerprint,
        )

    async def test_resume_jd_and_plan_content_each_change_fingerprint(self) -> None:
        base = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        resume = await self.db.get(Resume, self.application.current_resume_id)
        resume.raw_text += "\n维护异步任务"
        resume_changed = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        resume.raw_text = "工作经历\n使用 Python 开发 API 服务"
        job = await self.db.get(Job, self.application.job_id)
        job.description = "负责新的 Python 平台"
        jd_changed = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        job.description = "负责 Python API 开发"
        plan = await self.db.scalar(
            select(JobEvaluationPlan).where(JobEvaluationPlan.job_id == job.id)
        )
        plan.items = [item() | {"title": "Python API"}]
        plan_changed = await screening_service._build_context(
            self.db, self.application, self.settings
        )
        self.assertNotEqual(base.input_fingerprint, resume_changed.input_fingerprint)
        self.assertNotEqual(base.input_fingerprint, jd_changed.input_fingerprint)
        self.assertNotEqual(base.input_fingerprint, plan_changed.input_fingerprint)

    async def test_waiting_resume_does_not_call_adapter(self) -> None:
        resume = await self.db.get(Resume, self.application.current_resume_id)
        resume.parse_status = "failed"
        resume.raw_text = None
        await self.db.commit()
        result = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        self.assertEqual(result.run.status, "waiting_resume")
        self.assertIsNone(
            await screening_service.claim_next_run(
                self.db, worker_id="worker", lease_seconds=300
            )
        )

    async def test_waiting_plan_does_not_queue_model(self) -> None:
        plan = await self.db.scalar(
            select(JobEvaluationPlan).where(
                JobEvaluationPlan.job_id == self.application.job_id
            )
        )
        plan.status = "generating"
        await self.db.commit()
        result = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        self.assertEqual(result.run.status, "waiting_plan")

    async def test_same_queued_input_reuses_run(self) -> None:
        first = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        second = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        self.assertEqual(first.run.id, second.run.id)
        self.assertTrue(second.reused_run)

    async def test_success_saves_one_report_and_normal_request_reuses_it(self) -> None:
        completed, adapter = await self._complete_success()
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        reused = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        self.assertEqual(completed.status, "succeeded")
        self.assertEqual(report.display_label, "整体较匹配")
        self.assertTrue(reused.reused_report)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(
            len(
                (
                    await self.db.scalars(
                        select(ScreeningReport).where(
                            ScreeningReport.application_id == self.application.id
                        )
                    )
                ).all()
            ),
            1,
        )

    async def test_network_failure_retries_once(self) -> None:
        run = await self._queue_and_claim()
        adapter = FakeScreeningEvaluationAdapter(
            [ScreeningEvaluationTimeoutError("private"), valid_model_result()]
        )
        completed = await screening_service.execute_run(
            self.db,
            run.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(completed.status, "succeeded")
        self.assertEqual(completed.attempt_count, 2)
        self.assertEqual(len(adapter.calls), 2)

    async def test_content_failure_does_not_retry_or_replace_old_report(self) -> None:
        await self._complete_success()
        old_report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        old_score = old_report.overall_score
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        claimed = await screening_service.claim_next_run(
            self.db, worker_id="worker", lease_seconds=300
        )
        adapter = FakeScreeningEvaluationAdapter(
            [
                ScreeningEvaluationAdapterResult(
                    content="not-json",
                    model="fake",
                    finish_reason="stop",
                )
            ]
        )
        failed = await screening_service.execute_run(
            self.db,
            claimed.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        await self.db.refresh(old_report)
        self.assertEqual(result.run.id, claimed.id)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(old_report.overall_score, old_score)

    async def test_year_fact_conflict_fails_and_preserves_old_report(self) -> None:
        application_id = self.application.id
        await self._complete_success()
        old_report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id
            )
        )
        old_report_id = old_report.id
        old_score = old_report.overall_score
        resume = await self.db.get(Resume, self.application.current_resume_id)
        resume.raw_text = "工作经历\n2021.07—至今，使用 Python 开发 API 服务"
        plan = await self.db.scalar(
            select(JobEvaluationPlan).where(
                JobEvaluationPlan.job_id == self.application.job_id
            )
        )
        years_item = {
            "key": "requirement:experience:years",
            "title": "至少 2 年工作经验",
            "category": "experience",
            "priority": "required",
            "source_type": "structured",
            "source_field": "requirements.minimum_work_years",
            "source_quote": None,
        }
        plan.items = [item(), years_item]
        await self.db.commit()
        context = await screening_service._build_context(
            self.db,
            self.application,
            self.settings,
        )
        fact_key = context.experience_period_facts.facts[0].key
        triggered = await screening_service.trigger(
            self.db,
            application_id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        claimed = await screening_service.claim_next_run(
            self.db,
            worker_id="worker",
            lease_seconds=300,
            clock=lambda: NOW,
        )
        conflicting_payload = {
            "overall_score": 80,
            "overall_summary": "Python 项目经验与岗位要求整体较匹配。",
            "requirement_assessments": [
                {
                    "requirement_key": "requirement:skill:python",
                    "score": 8,
                    "reason": "使用 Python 开发 API 服务，岗位相关经验较充分。",
                    "calculation_note": None,
                    "experience_period_fact_keys": [],
                    "evidence": [
                        {"quote": "使用 Python 开发 API 服务", "section": "工作经历"}
                    ],
                },
                {
                    "requirement_key": "requirement:experience:years",
                    "score": 8,
                    "reason": "相关开发经历满足至少 2 年要求。",
                    "calculation_note": "相关经历精确为 3 年，满足至少 2 年要求。",
                    "experience_period_fact_keys": [fact_key],
                    "evidence": [
                        {
                            "quote": "2021.07—至今，使用 Python 开发 API 服务",
                            "section": "工作经历",
                        }
                    ],
                },
            ],
            "bonus_highlights": [],
            "tradeoff_reason": None,
            "interview_questions": [],
        }
        failed = await screening_service.execute_run(
            self.db,
            claimed.id,
            adapter=FakeScreeningEvaluationAdapter(
                [
                    ScreeningEvaluationAdapterResult(
                        content=json.dumps(conflicting_payload, ensure_ascii=False),
                        model="fake-screening-model",
                        finish_reason="stop",
                    )
                ]
            ),
            settings=self.settings,
            clock=lambda: NOW,
        )
        current = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id
            )
        )
        self.assertEqual(triggered.run.id, claimed.id)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error_code, "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT")
        self.assertEqual(current.id, old_report_id)
        self.assertEqual(current.overall_score, old_score)

    async def test_screening_never_changes_hr_decision_or_recruitment_state(self) -> None:
        before = (
            self.application.hr_decision,
            self.application.recruitment_stage,
            self.application.lifecycle_status,
        )
        await self._complete_success()
        await self.db.refresh(self.application)
        self.assertEqual(
            (
                self.application.hr_decision,
                self.application.recruitment_stage,
                self.application.lifecycle_status,
            ),
            before,
        )

    async def test_reassessment_same_input_creates_new_run(self) -> None:
        completed, _ = await self._complete_success()
        reassessed = await screening_service.trigger(
            self.db,
            self.application.id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        self.assertNotEqual(completed.id, reassessed.run.id)
        self.assertEqual(reassessed.run.trigger_type, "single_reassessment")

    async def test_late_response_after_resume_switch_cannot_replace_report(self) -> None:
        run = await self._queue_and_claim()
        candidate = await self.db.get(Candidate, self.application.candidate_id)
        new_resume = Resume(
            candidate_id=candidate.id,
            job_id=self.application.job_id,
            filename="new.txt",
            file_path="private/new.txt",
            file_type="text/plain",
            raw_text="工作经历\n使用 Python 开发 API 服务",
            parse_status="parsed",
        )
        self.db.add(new_resume)
        await self.db.commit()
        await screening_service.switch_current_resume(
            self.db, self.application.id, new_resume.id
        )
        adapter = FakeScreeningEvaluationAdapter([valid_model_result()])
        failed = await screening_service.execute_run(
            self.db,
            run.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(failed.error_code, "SCREENING_RUN_SUPERSEDED")
        self.assertEqual(len(adapter.calls), 0)
        self.assertIsNone(
            await self.db.scalar(
                select(ScreeningReport).where(
                    ScreeningReport.application_id == self.application.id
                )
            )
        )

    async def test_running_task_can_finish_after_job_closes(self) -> None:
        run = await self._queue_and_claim()
        job = await self.db.get(Job, self.application.job_id)
        job.status = "closed"
        await self.db.commit()
        completed = await screening_service.execute_run(
            self.db,
            run.id,
            adapter=FakeScreeningEvaluationAdapter([valid_model_result()]),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(completed.status, "succeeded")

    async def test_job_close_pauses_not_started_run(self) -> None:
        result = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        await screening_service.after_job_closed(self.db, self.application.job_id)
        await self.db.refresh(result.run)
        self.assertEqual(result.run.status, "paused")

    async def test_resume_switch_marks_report_outdated_without_new_run(self) -> None:
        await self._complete_success()
        candidate = await self.db.get(Candidate, self.application.candidate_id)
        new_resume = Resume(
            candidate_id=candidate.id,
            job_id=self.application.job_id,
            filename="updated.txt",
            file_path="private/updated.txt",
            file_type="text/plain",
            raw_text="工作经历\n使用 Python 开发 API 服务",
            parse_status="parsed",
        )
        self.db.add(new_resume)
        await self.db.commit()
        before = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )
        await screening_service.switch_current_resume(
            self.db, self.application.id, new_resume.id
        )
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        after = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )
        self.assertTrue(report.is_outdated)
        self.assertIn("resume_changed", report.outdated_reasons)
        self.assertEqual(before, after)

    async def test_prompt_version_change_alone_does_not_mark_report_outdated(self) -> None:
        await self._complete_success()
        state = await screening_service.get_state(self.db, self.application.id)
        self.assertFalse(state.report.is_outdated)

    async def test_jd_and_current_plan_changes_expire_report_without_new_run(self) -> None:
        await self._complete_success()
        before = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )
        job = await self.db.get(Job, self.application.job_id)
        job.description = "负责新的 Python 平台"
        await self.db.commit()
        await screening_service.after_plan_changed(self.db, job.id, plan_ready=False)
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        self.assertIn("jd_changed", report.outdated_reasons)

        old_plan = await self.db.scalar(
            select(JobEvaluationPlan).where(JobEvaluationPlan.job_id == job.id)
        )
        old_plan.is_current = False
        old_plan.status = "outdated"
        snapshot = {
            "job_id": job.id,
            "title": job.title,
            "department": job.department,
            "description": job.description,
            "requirements": requirements(),
        }
        fingerprint = screening_service._sha256(snapshot)
        self.db.add(
            JobEvaluationPlan(
                job_id=job.id,
                jd_fingerprint=fingerprint,
                status="ready",
                is_current=True,
                items=[item()],
                structured_coverage={
                    "source_schema_version": "1.0",
                    "fields": [],
                    "all_covered": True,
                },
                warnings=[],
                prompt_version="job_evaluation_plan_v1",
                model_version="fake-plan-model",
                schema_version="1.0",
                input_fingerprint=fingerprint,
                input_snapshot=snapshot,
                completed_at=NOW,
            )
        )
        await self.db.commit()
        await screening_service.after_plan_changed(self.db, job.id, plan_ready=True)
        await self.db.refresh(report)
        after = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )
        self.assertIn("evaluation_plan_changed", report.outdated_reasons)
        self.assertEqual(before, after)

    async def test_plan_contract_upgrade_keeps_historical_report_foreign_key(
        self,
    ) -> None:
        await self._complete_success()
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == self.application.id
            )
        )
        old_plan_id = report.job_evaluation_plan_id
        before_runs = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )
        adapter = FakeJobEvaluationPlanAdapter(
            [
                JobEvaluationPlanAdapterResult(
                    content=json.dumps(
                        {
                            "schema_version": "2.0",
                            "source_reviews": [
                                {
                                    "source_id": "description:0001",
                                    "disposition": "requirements",
                                    "non_requirement_reason": None,
                                    "items": [
                                        {
                                            "title": "Python API 开发",
                                            "category": "responsibility",
                                            "equivalent_structured_item_key": None,
                                        }
                                    ],
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    model="fake-plan-model-v2",
                    finish_reason="stop",
                )
            ]
        )
        settings = Settings(
            _env_file=None,
            DEEPSEEK_API_KEY="test-key",
            JOB_EVALUATION_PLAN_MODEL="fake-plan-model-v2",
        )

        new_plan = await job_evaluation_plan_service.generate_for_job(
            self.db,
            self.application.job_id,
            adapter=adapter,
            settings=settings,
            clock=lambda: NOW,
        )
        await screening_service.after_plan_changed(
            self.db,
            self.application.job_id,
            plan_ready=True,
        )
        await self.db.refresh(report)
        old_plan = await self.db.get(JobEvaluationPlan, old_plan_id)
        after_runs = len(
            (
                await self.db.scalars(
                    select(ScreeningRun).where(
                        ScreeningRun.application_id == self.application.id
                    )
                )
            ).all()
        )

        self.assertNotEqual(new_plan.id, old_plan_id)
        self.assertEqual(old_plan.status, "outdated")
        self.assertFalse(old_plan.is_current)
        self.assertEqual(report.job_evaluation_plan_id, old_plan_id)
        self.assertTrue(report.is_outdated)
        self.assertIn("evaluation_plan_changed", report.outdated_reasons)
        self.assertEqual(before_runs, after_runs)

    async def test_failed_reassessment_can_be_requested_again(self) -> None:
        application_id = self.application.id
        await self._complete_success()
        first = await screening_service.trigger(
            self.db,
            application_id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        claimed = await screening_service.claim_next_run(
            self.db, worker_id="worker", lease_seconds=300
        )
        failed = await screening_service.execute_run(
            self.db,
            claimed.id,
            adapter=FakeScreeningEvaluationAdapter(
                [
                    ScreeningEvaluationAdapterResult(
                        content="{}",
                        model="fake",
                        finish_reason="stop",
                    )
                ]
            ),
            settings=self.settings,
            clock=lambda: NOW,
        )
        failed_status = failed.status
        second = await screening_service.trigger(
            self.db,
            application_id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        self.assertEqual(failed_status, "failed")
        self.assertNotEqual(first.run.id, second.run.id)

    async def test_paused_run_resumes_after_job_reopens(self) -> None:
        result = await screening_service.trigger(
            self.db, self.application.id, settings=self.settings
        )
        job = await self.db.get(Job, self.application.job_id)
        job.status = "closed"
        await self.db.commit()
        await screening_service.after_job_closed(self.db, job.id)
        job.status = "open"
        await self.db.commit()
        await screening_service.after_job_reopened(self.db, job.id)
        await self.db.refresh(result.run)
        self.assertEqual(result.run.status, "queued")

    async def test_paused_manual_reassessment_with_old_report_resumes_after_reopen(
        self,
    ) -> None:
        await self._complete_success()
        result = await screening_service.trigger(
            self.db,
            self.application.id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        job = await self.db.get(Job, self.application.job_id)
        job.status = "closed"
        await self.db.commit()
        await screening_service.after_job_closed(self.db, job.id)
        job.status = "open"
        await self.db.commit()
        await screening_service.after_job_reopened(self.db, job.id)
        await self.db.refresh(result.run)
        self.assertEqual(result.run.status, "queued")
        self.assertEqual(result.run.trigger_type, "single_reassessment")

    async def test_batch_accepts_same_job_and_rejects_cross_job_or_over_limit(self) -> None:
        second = await self._create_application(
            job=await self.db.get(Job, self.application.job_id)
        )
        results = await screening_service.trigger_batch_reassessment(
            self.db,
            self.application.job_id,
            [self.application.id, second.id],
            settings=self.settings,
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(
            all(item.run.trigger_type == "batch_reassessment" for item in results)
        )
        with self.assertRaises(ScreeningBatchLimitError):
            await screening_service.trigger_batch_reassessment(
                self.db,
                self.application.job_id,
                list(range(1, 22)),
                settings=self.settings,
            )
        other = await self._create_application()
        with self.assertRaises(ScreeningBatchJobMismatchError):
            await screening_service.trigger_batch_reassessment(
                self.db,
                self.application.job_id,
                [self.application.id, other.id],
                settings=self.settings,
            )

    async def test_batch_item_failure_does_not_rollback_other_application(self) -> None:
        first_application_id = self.application.id
        job_id = self.application.job_id
        second = await self._create_application(
            job=await self.db.get(Job, job_id)
        )
        second_application_id = second.id
        await screening_service.trigger_batch_reassessment(
            self.db,
            job_id,
            [first_application_id, second_application_id],
            settings=self.settings,
        )
        first_run = await screening_service.claim_next_run(
            self.db, worker_id="worker", lease_seconds=300
        )
        failed = await screening_service.execute_run(
            self.db,
            first_run.id,
            adapter=FakeScreeningEvaluationAdapter(
                [
                    ScreeningEvaluationAdapterResult(
                        content="invalid-json",
                        model="fake",
                        finish_reason="stop",
                    )
                ]
            ),
            settings=self.settings,
            clock=lambda: NOW,
        )
        failed_status = failed.status
        second_run = await screening_service.claim_next_run(
            self.db, worker_id="worker", lease_seconds=300
        )
        succeeded = await screening_service.execute_run(
            self.db,
            second_run.id,
            adapter=FakeScreeningEvaluationAdapter([valid_model_result()]),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(failed_status, "failed")
        self.assertEqual(succeeded.status, "succeeded")
        reports = (
            await self.db.scalars(
                select(ScreeningReport).where(
                    ScreeningReport.application_id.in_(
                        [first_application_id, second_application_id]
                    )
                )
            )
        ).all()
        self.assertEqual(len(reports), 1)

    async def test_database_commit_failure_preserves_old_report(self) -> None:
        application_id = self.application.id
        await self._complete_success()
        report = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id
            )
        )
        original_score = report.overall_score
        await screening_service.trigger(
            self.db,
            application_id,
            trigger_type=ScreeningRunTriggerType.SINGLE_REASSESSMENT,
            force=True,
            settings=self.settings,
        )
        run = await screening_service.claim_next_run(
            self.db, worker_id="worker", lease_seconds=300
        )
        real_commit = self.db.commit
        calls = 0

        async def fail_once() -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("private SQL failure")
            await real_commit()

        with patch.object(self.db, "commit", AsyncMock(side_effect=fail_once)):
            failed = await screening_service.execute_run(
                self.db,
                run.id,
                adapter=FakeScreeningEvaluationAdapter([valid_model_result(score=90)]),
                settings=self.settings,
                clock=lambda: NOW,
            )
        current = await self.db.scalar(
            select(ScreeningReport).where(
                ScreeningReport.application_id == application_id
            )
        )
        self.assertEqual(failed.error_code, "SCREENING_DATABASE_COMMIT_FAILED")
        self.assertEqual(current.overall_score, original_score)
