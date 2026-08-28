from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api import job_evaluation_plans as api
from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import (
    JobEvaluationPlanV5DraftCriterion,
    JobEvaluationPlanV5DraftSaveRequest,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanNotEditableError,
    PlanEditConflictError,
    job_evaluation_plan_service,
)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def _job(*, title: str = "7R5-D 轻量计划岗位") -> Job:
    return Job(
        title=title,
        department="技术研发部",
        job_background="建设企业内部应用平台。",
        job_responsibilities="负责按期完成项目交付。",
        candidate_requirements="必须具备 Python 后端项目经验。",
        preferred_qualifications="有 Kubernetes 生产实践者优先。",
        public_notes="候选人可见备注 A",
        status="open",
    )


def _criterion(
    name: str,
    importance: str,
    source_field: str,
    source_quote: str,
) -> dict:
    return {
        "name": name,
        "importance": importance,
        "description": f"根据 JD 核对{name}。",
        "screening_focus": f"寻找{name}的工作或项目证据。",
        "sources": [
            {"source_field": source_field, "source_quote": source_quote}
        ],
    }


def _payload() -> dict:
    return {
        "criteria": [
            _criterion(
                "项目交付",
                "general",
                "job_responsibilities",
                "负责按期完成项目交付",
            ),
            _criterion(
                "Python 后端项目经验",
                "required",
                "candidate_requirements",
                "必须具备 Python 后端项目经验",
            ),
            _criterion(
                "Kubernetes 生产实践",
                "preferred",
                "preferred_qualifications",
                "有 Kubernetes 生产实践者优先",
            ),
        ]
    }


def _adapter() -> FakeJobEvaluationPlanAdapter:
    return FakeJobEvaluationPlanAdapter(
        [
            JobEvaluationPlanAdapterResult(
                content=json.dumps(_payload(), ensure_ascii=False),
                model="fake-v5-plan-model",
                finish_reason="stop",
                input_tokens=100,
                output_tokens=50,
            )
        ]
    )


def _draft_payload(plan: JobEvaluationPlan) -> list[dict]:
    return [dict(item) for item in (plan.v5_criteria or [])]


def _importance_warning_ids(plan: JobEvaluationPlan) -> set[str]:
    return {
        warning["criterion_id"]
        for warning in plan.warnings
        if warning["code"] == "importance_review_required"
    }


def test_v5_hr_added_schema_requires_note_and_forbids_fake_sources() -> None:
    valid = JobEvaluationPlanV5DraftCriterion.model_validate(
        {
            "criterion_id": None,
            "name": "HR 补充的现场协调能力",
            "importance": "general",
            "description": "由 HR 补充审核。",
            "screening_focus": "寻找现场协调案例。",
            "origin": "hr_added",
            "sources": [],
            "hr_note": "业务团队要求补充检查。",
        }
    )
    assert valid.origin == "hr_added"

    for invalid in (
        {**valid.model_dump(mode="json"), "hr_note": None},
        {
            **valid.model_dump(mode="json"),
            "sources": [
                {
                    "source_field": "candidate_requirements",
                    "source_quote": "伪造来源",
                }
            ],
        },
        {**valid.model_dump(mode="json"), "origin": "ai_from_jd"},
    ):
        with pytest.raises(ValidationError):
            JobEvaluationPlanV5DraftCriterion.model_validate(invalid)


def test_v5_api_routes_and_conflict_mapping_are_explicit() -> None:
    route_paths = {
        (method, route.path)
        for route in api.router.routes
        for method in route.methods or set()
    }
    assert {
        ("PUT", "/jobs/{job_id}/evaluation-plan/draft"),
        ("POST", "/jobs/{job_id}/evaluation-plan/versions"),
        ("POST", "/jobs/{job_id}/evaluation-plan/confirm"),
        ("GET", "/jobs/{job_id}/evaluation-plans"),
    }.issubset(route_paths)
    assert "generate_v5_for_job" in inspect.getsource(
        api.generate_current_evaluation_plan
    )
    mapped = api._map_expected_error(PlanEditConflictError("private detail"))
    assert mapped.status_code == 409
    assert mapped.detail == {
        "code": "JOB_EVALUATION_PLAN_EDIT_CONFLICT",
        "message": "评价计划已更新，请刷新后重试",
    }


class JobEvaluationPlanV5EditPostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.settings = Settings(_env_file=None, DEEPSEEK_API_KEY="test-key")
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
        self.job = _job()
        self.db.add(self.job)
        await self.db.commit()
        self.job_id = self.job.id

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def _generate(self) -> tuple[JobEvaluationPlan, FakeJobEvaluationPlanAdapter]:
        adapter = _adapter()
        plan = await job_evaluation_plan_service.generate_v5_for_job(
            self.db,
            self.job_id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )
        return plan, adapter

    async def test_generation_is_pending_single_call_and_idempotent(self) -> None:
        plan, adapter = await self._generate()

        self.assertEqual(plan.status, "pending_confirmation")
        self.assertEqual(plan.schema_version, "5.0")
        self.assertEqual(plan.edit_version, 1)
        self.assertIsNone(plan.confirmed_at)
        self.assertEqual(len(plan.v5_criteria), 3)
        self.assertEqual(len(adapter.v5_calls), 1)
        self.assertEqual(
            job_evaluation_plan_service.build_read_model(plan).edit_version,
            1,
        )

        reused = await job_evaluation_plan_service.generate_v5_for_job(
            self.db,
            self.job_id,
            adapter=FakeJobEvaluationPlanAdapter([]),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(reused.id, plan.id)
        self.assertEqual(reused.edit_version, 1)

    async def test_save_recalculates_warning_and_rejects_stale_version(self) -> None:
        plan, _ = await self._generate()
        draft = _draft_payload(plan)
        python_item = next(item for item in draft if "Python" in item["name"])
        python_item["importance"] = "preferred"

        saved = await job_evaluation_plan_service.save_draft(
            self.db,
            self.job_id,
            {"edit_version": 1, "criteria": draft},
        )
        self.assertEqual(saved.edit_version, 2)
        self.assertIn(python_item["criterion_id"], _importance_warning_ids(saved))

        with self.assertRaises(PlanEditConflictError):
            await job_evaluation_plan_service.save_draft(
                self.db,
                self.job_id,
                {"edit_version": 1, "criteria": draft},
            )

        saved = await job_evaluation_plan_service.get_current_plan(
            self.db,
            self.job_id,
        )
        corrected = _draft_payload(saved)
        next(item for item in corrected if "Python" in item["name"])[
            "importance"
        ] = "required"
        saved = await job_evaluation_plan_service.save_draft(
            self.db,
            self.job_id,
            {"edit_version": 2, "criteria": corrected},
        )
        self.assertNotIn(python_item["criterion_id"], _importance_warning_ids(saved))

    async def test_ai_from_jd_common_abbreviation_edit_remains_pending(self) -> None:
        plan, _ = await self._generate()
        draft = _draft_payload(plan)
        kubernetes_item = next(
            item for item in draft if "Kubernetes" in item["name"]
        )
        original_sources = list(kubernetes_item["sources"])
        kubernetes_item["name"] = "Kubernetes（K8s）生产实践"
        kubernetes_item["description"] = (
            "根据 JD 核对 Kubernetes（K8s）生产实践。"
        )
        kubernetes_item["screening_focus"] = (
            "寻找 Kubernetes 或 K8s 生产环境实践证据。"
        )

        saved = await job_evaluation_plan_service.save_draft(
            self.db,
            self.job_id,
            {"edit_version": 1, "criteria": draft},
        )

        saved_item = next(
            item
            for item in saved.v5_criteria
            if item["criterion_id"] == kubernetes_item["criterion_id"]
        )
        self.assertEqual(saved.status, "pending_confirmation")
        self.assertEqual(saved.edit_version, 2)
        self.assertEqual(saved_item["origin"], "ai_from_jd")
        self.assertEqual(saved_item["sources"], original_sources)
        self.assertIn("K8s", saved_item["name"])

    async def test_atomic_save_supports_hr_add_delete_and_merge(self) -> None:
        plan, _ = await self._generate()
        original = _draft_payload(plan)
        retained_id = original[0]["criterion_id"]
        retained = {
            "criterion_id": retained_id,
            "name": "HR 合并后的综合交付复核",
            "importance": "general",
            "description": "由 HR 合并两个原评价点后统一复核。",
            "screening_focus": "寻找综合交付案例。",
            "origin": "hr_added",
            "sources": [],
            "hr_note": "合并原有交付与 Python 经验评价点。",
        }
        hr_added = {
            "criterion_id": None,
            "name": "现场协调能力",
            "importance": "general",
            "description": "HR 补充检查现场协调能力。",
            "screening_focus": "寻找现场协调案例。",
            "origin": "hr_added",
            "sources": [],
            "hr_note": "业务团队新增的人工审核要求。",
        }
        saved = await job_evaluation_plan_service.save_draft(
            self.db,
            self.job_id,
            {
                "edit_version": 1,
                "criteria": [retained, original[2], hr_added],
            },
        )

        ids = [item["criterion_id"] for item in saved.v5_criteria]
        self.assertEqual(len(ids), 3)
        self.assertIn(retained_id, ids)
        self.assertNotIn(original[1]["criterion_id"], ids)
        self.assertEqual(ids[-1], "criterion:0004")
        self.assertEqual(saved.v5_criteria[0]["origin"], "hr_added")
        self.assertEqual(saved.v5_criteria[0]["sources"], [])

    async def test_confirm_allows_warning_and_ready_forks_without_mutation(self) -> None:
        plan, _ = await self._generate()
        draft = _draft_payload(plan)
        next(item for item in draft if "Python" in item["name"])[
            "importance"
        ] = "preferred"
        plan = await job_evaluation_plan_service.save_draft(
            self.db,
            self.job_id,
            {"edit_version": 1, "criteria": draft},
        )
        self.assertTrue(_importance_warning_ids(plan))

        ready = await job_evaluation_plan_service.confirm_current_plan(
            self.db,
            self.job_id,
            plan.edit_version,
            clock=lambda: NOW,
        )
        ready_id = ready.id
        ready_version = ready.edit_version
        ready_payload = list(ready.v5_criteria)
        self.assertEqual(ready.status, "ready")
        self.assertEqual(ready.confirmed_at, NOW)

        with self.assertRaises(JobEvaluationPlanNotEditableError):
            await job_evaluation_plan_service.save_draft(
                self.db,
                self.job_id,
                {"edit_version": ready_version, "criteria": draft},
            )

        forked = await job_evaluation_plan_service.create_new_version_from_confirmed(
            self.db,
            self.job_id,
            ready_version,
            clock=lambda: NOW,
        )
        self.assertNotEqual(forked.id, ready_id)
        self.assertEqual(forked.status, "pending_confirmation")
        self.assertEqual(forked.edit_version, ready_version + 1)
        self.assertIsNone(forked.confirmed_at)

        stored_ready = await self.db.get(JobEvaluationPlan, ready_id)
        await self.db.refresh(stored_ready)
        self.assertEqual(stored_ready.status, "ready")
        self.assertFalse(stored_ready.is_current)
        self.assertEqual(stored_ready.v5_criteria, ready_payload)
        history = await job_evaluation_plan_service.list_plan_history(
            self.db,
            self.job_id,
        )
        self.assertEqual({item.id for item in history}, {ready_id, forked.id})

    async def test_public_notes_do_not_expire_but_evaluation_input_does(self) -> None:
        plan, _ = await self._generate()
        self.job.public_notes = "候选人可见备注 B"
        await self.db.commit()
        unchanged = (
            await job_evaluation_plan_service.mark_current_plan_outdated_if_input_changed(
                self.db,
                self.job_id,
            )
        )
        self.assertTrue(unchanged.is_current)
        self.assertEqual(unchanged.status, "pending_confirmation")

        self.job.candidate_requirements = "必须具备 Go 服务端项目经验。"
        await self.db.commit()
        outdated = (
            await job_evaluation_plan_service.mark_current_plan_outdated_if_input_changed(
                self.db,
                self.job_id,
            )
        )
        self.assertEqual(outdated.id, plan.id)
        self.assertEqual(outdated.status, "outdated")
        self.assertFalse(outdated.is_current)

    async def test_failed_generation_can_explicitly_regenerate_same_row(self) -> None:
        invalid = FakeJobEvaluationPlanAdapter(
            [
                JobEvaluationPlanAdapterResult(
                    content="{not-json",
                    model="fake-v5-plan-model",
                    finish_reason="stop",
                )
            ]
        )
        failed = await job_evaluation_plan_service.generate_v5_for_job(
            self.db,
            self.job_id,
            adapter=invalid,
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.v5_criteria)
        self.assertEqual(failed.edit_version, 1)

        regenerated = await job_evaluation_plan_service.regenerate_failed_v5_plan(
            self.db,
            self.job_id,
            adapter=_adapter(),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(regenerated.id, failed.id)
        self.assertEqual(regenerated.status, "pending_confirmation")
        self.assertEqual(regenerated.edit_version, 1)

    async def test_late_success_cannot_become_current_after_jd_change(self) -> None:
        job = await job_evaluation_plan_service._get_locked_job(
            self.db,
            self.job_id,
        )
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(job)
        input_fingerprint = job_evaluation_plan_service.fingerprint_input(snapshot)
        plan, should_generate = await job_evaluation_plan_service._prepare_v5_plan(
            self.db,
            job,
            snapshot.model_dump(mode="json"),
            job_evaluation_plan_service.fingerprint_snapshot(snapshot),
            input_fingerprint,
            force=False,
            settings=self.settings,
            started_at=NOW,
        )
        self.assertTrue(should_generate)
        await self.db.commit()
        await self.db.refresh(plan)
        content = await job_evaluation_plan_service.build_v5_plan_content(
            snapshot,
            adapter=_adapter(),
        )

        self.job.candidate_requirements = "必须具备 Go 服务端项目经验。"
        await self.db.commit()
        late = await job_evaluation_plan_service._save_v5_success(
            self.db,
            plan.id,
            input_fingerprint,
            content,
            completed_at=NOW,
        )
        self.assertEqual(late.status, "outdated")
        self.assertFalse(late.is_current)
        self.assertIsNone(late.v5_criteria)


class JobEvaluationPlanV5ConcurrentEditTest(IsolatedAsyncioTestCase):
    async def test_same_edit_version_allows_only_one_concurrent_save(self) -> None:
        settings = Settings(_env_file=None, DEEPSEEK_API_KEY="test-key")
        engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
        job_id: int | None = None
        try:
            async with AsyncSession(engine, expire_on_commit=False) as setup_db:
                job = _job(title="7R5-D 并发编辑岗位")
                setup_db.add(job)
                await setup_db.commit()
                job_id = job.id
                plan = await job_evaluation_plan_service.generate_v5_for_job(
                    setup_db,
                    job_id,
                    adapter=_adapter(),
                    settings=settings,
                    clock=lambda: NOW,
                )
                request = JobEvaluationPlanV5DraftSaveRequest.model_validate(
                    {"edit_version": 1, "criteria": _draft_payload(plan)}
                )

            async def save_once() -> str:
                async with AsyncSession(engine, expire_on_commit=False) as db:
                    try:
                        saved = await job_evaluation_plan_service.save_draft(
                            db,
                            job_id,
                            request,
                        )
                        return f"saved:{saved.edit_version}"
                    except PlanEditConflictError:
                        return "conflict"

            results = await asyncio.gather(save_once(), save_once())
            self.assertEqual(sorted(results), ["conflict", "saved:2"])
        finally:
            if job_id is not None:
                async with AsyncSession(engine) as cleanup_db:
                    await cleanup_db.execute(
                        delete(JobEvaluationPlan).where(
                            JobEvaluationPlan.job_id == job_id
                        )
                    )
                    await cleanup_db.execute(delete(Job).where(Job.id == job_id))
                    await cleanup_db.commit()
            await engine.dispose()
