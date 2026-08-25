from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api import job_evaluation_plans as api
from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings
from app.core.database import get_db
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import JobEvaluationPlanRead
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanNotConfirmableError,
    job_evaluation_plan_service,
)
from tests.fixtures.job_evaluation_plan_v4 import make_v4_plan


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def _route_paths() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in api.router.routes
        for method in route.methods or set()
    }


def test_v4_api_exposes_explicit_hr_confirmation() -> None:
    assert ("POST", "/jobs/{job_id}/evaluation-plan/confirm") in _route_paths()


def test_v4_confirmation_is_a_service_state_transition() -> None:
    method = getattr(job_evaluation_plan_service, "confirm_current_plan", None)
    assert method is not None
    assert inspect.iscoroutinefunction(method)


def test_v4_confirmation_does_not_accept_editable_facts_or_criteria() -> None:
    matches = [
        route
        for route in api.router.routes
        if route.path == "/jobs/{job_id}/evaluation-plan/confirm"
    ]
    assert len(matches) == 1, "7R4-D 缺少唯一确认路由"
    route = matches[0]
    dependant_fields = {field.name for field in route.dependant.body_params}
    assert dependant_fields.isdisjoint({"requirement_facts", "evaluation_criteria"})


def test_v4_generation_persists_pending_before_ready() -> None:
    method = getattr(job_evaluation_plan_service, "_save_success", None)
    assert method is not None, "7R4-D 缺少计划成功持久化边界"
    source = inspect.getsource(method)
    assert "pending_confirmation" in source
    assert 'status="ready"' not in source


def test_v4_confirm_rechecks_current_contract_and_fingerprint() -> None:
    method = getattr(job_evaluation_plan_service, "confirm_current_plan", None)
    assert method is not None
    source = inspect.getsource(method)
    for token in ("is_current", '"4.0"', "input_fingerprint", "pending_confirmation"):
        assert token in source


def test_v4_confirmation_never_calls_plan_adapter() -> None:
    method = getattr(job_evaluation_plan_service, "confirm_current_plan", None)
    assert method is not None
    source = inspect.getsource(method)
    assert "adapter" not in source.lower()


def _result(payload: dict) -> JobEvaluationPlanAdapterResult:
    return JobEvaluationPlanAdapterResult(
        content=json.dumps(payload, ensure_ascii=False),
        model="fake-plan-model",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
    )


def _generation_adapter() -> FakeJobEvaluationPlanAdapter:
    return FakeJobEvaluationPlanAdapter(
        [
            _result(
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
            _result({"schema_version": "4.0", "status": "passed", "findings": []}),
            _result(
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


def _job(*, title: str = "7R4-D PostgreSQL 岗位") -> Job:
    return Job(
        title=title,
        department="技术研发部",
        job_background="建设企业 AI 应用平台",
        job_responsibilities=None,
        candidate_requirements="具备 Python 后端开发经验",
        preferred_qualifications=None,
        public_notes="候选人可见备注 A",
        status="open",
    )


class JobEvaluationPlanV4PostgresContractTest(IsolatedAsyncioTestCase):
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

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def _generate(self) -> tuple[JobEvaluationPlan, FakeJobEvaluationPlanAdapter]:
        generated = _generation_adapter()
        plan = await job_evaluation_plan_service.generate_for_job(
            self.db,
            self.job.id,
            adapter=generated,
            settings=self.settings,
            clock=lambda: NOW,
        )
        return plan, generated

    async def test_generation_is_pending_idempotent_and_public_notes_do_not_expire(self) -> None:
        plan, generated = await self._generate()

        self.assertEqual(plan.status, "pending_confirmation")
        self.assertEqual(plan.schema_version, "4.0")
        self.assertIsNone(plan.items)
        self.assertEqual(len(plan.requirement_facts), 1)
        self.assertEqual(len(plan.evaluation_criteria), 1)
        self.assertEqual(len(generated.v4_calls), 3)

        reused = await job_evaluation_plan_service.generate_for_job(
            self.db,
            self.job.id,
            adapter=FakeJobEvaluationPlanAdapter([]),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(reused.id, plan.id)
        self.assertEqual(reused.status, "pending_confirmation")

        self.job.public_notes = "候选人可见备注 B"
        await self.db.commit()
        ready = await job_evaluation_plan_service.confirm_current_plan(
            self.db,
            self.job.id,
        )
        self.assertEqual(ready.status, "ready")
        self.assertFalse(job_evaluation_plan_service.is_contract_outdated(ready))

        confirmed_again = await job_evaluation_plan_service.confirm_current_plan(
            self.db,
            self.job.id,
        )
        self.assertEqual(confirmed_again.id, ready.id)
        self.assertEqual(confirmed_again.status, "ready")

    async def test_jd_change_makes_pending_plan_outdated_and_blocks_confirmation(self) -> None:
        plan, _ = await self._generate()
        self.job.candidate_requirements = "具备 Go 服务端开发经验"
        await self.db.commit()

        with self.assertRaises(JobEvaluationPlanNotConfirmableError):
            await job_evaluation_plan_service.confirm_current_plan(
                self.db,
                self.job.id,
            )

        stored = await self.db.get(JobEvaluationPlan, plan.id)
        await self.db.refresh(stored)
        self.assertEqual(stored.status, "outdated")
        self.assertFalse(stored.is_current)

    async def test_closed_job_cannot_confirm_and_pending_payload_is_preserved(self) -> None:
        plan, _ = await self._generate()
        plan_id = plan.id
        job_id = self.job.id
        self.job.status = "closed"
        await self.db.commit()

        with self.assertRaises(JobEvaluationPlanNotConfirmableError):
            await job_evaluation_plan_service.confirm_current_plan(
                self.db,
                job_id,
            )

        stored = await self.db.get(JobEvaluationPlan, plan_id)
        await self.db.refresh(stored)
        self.assertEqual(stored.status, "pending_confirmation")
        self.assertTrue(stored.is_current)
        self.assertEqual(len(stored.requirement_facts), 1)

    async def test_invalid_generation_fails_without_partial_v4_payload(self) -> None:
        invalid = FakeJobEvaluationPlanAdapter(
            [
                JobEvaluationPlanAdapterResult(
                    content="not-json",
                    model="fake-plan-model",
                    finish_reason="stop",
                )
            ]
        )
        failed = await job_evaluation_plan_service.generate_for_job(
            self.db,
            self.job.id,
            adapter=invalid,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.items)
        self.assertIsNone(failed.requirement_facts)
        self.assertIsNone(failed.evaluation_criteria)
        self.assertIsNone(failed.source_review_summary)
        self.assertIsNone(failed.coverage_review_summary)
        self.assertIsNone(failed.generation_audit)
        self.assertEqual(len(invalid.v4_calls), 1)

        regenerated = await job_evaluation_plan_service.regenerate_failed_plan(
            self.db,
            self.job.id,
            adapter=_generation_adapter(),
            settings=self.settings,
            clock=lambda: NOW,
        )
        self.assertEqual(regenerated.id, failed.id)
        self.assertEqual(regenerated.status, "pending_confirmation")

    async def test_new_input_failure_keeps_old_ready_payload_and_late_success_cannot_overwrite(self) -> None:
        old, _ = await self._generate()
        old = await job_evaluation_plan_service.confirm_current_plan(
            self.db,
            self.job.id,
        )
        old_id = old.id
        old_model = old.model_version
        old_facts = list(old.requirement_facts)

        snapshot = job_evaluation_plan_service.build_v4_input_snapshot(self.job)
        content = await job_evaluation_plan_service.build_v4_plan_content(
            snapshot,
            adapter=_generation_adapter(),
        )
        late = await job_evaluation_plan_service._save_success(
            self.db,
            old.id,
            old.input_fingerprint,
            content,
            model_version="late-model-must-not-win",
            completed_at=NOW,
        )
        self.assertEqual(late.status, "ready")
        self.assertEqual(late.model_version, old_model)

        self.job.candidate_requirements = "具备 Go 服务端开发经验"
        await self.db.commit()
        failed = await job_evaluation_plan_service.generate_for_job(
            self.db,
            self.job.id,
            adapter=_generation_adapter(),
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(failed.status, "failed")
        self.assertNotEqual(failed.id, old_id)
        stored_old = await self.db.get(JobEvaluationPlan, old_id)
        await self.db.refresh(stored_old)
        self.assertEqual(stored_old.status, "outdated")
        self.assertFalse(stored_old.is_current)
        self.assertEqual(stored_old.requirement_facts, old_facts)


class JobEvaluationPlanV4ConcurrentConfirmationTest(IsolatedAsyncioTestCase):
    async def test_two_confirmations_serialize_to_one_ready_state(self) -> None:
        settings = Settings(_env_file=None, DEEPSEEK_API_KEY="test-key")
        engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
        job_id: int | None = None
        try:
            async with AsyncSession(engine, expire_on_commit=False) as setup_db:
                job = _job(title="7R4-D 并发确认岗位")
                setup_db.add(job)
                await setup_db.commit()
                job_id = job.id
                plan = await job_evaluation_plan_service.generate_for_job(
                    setup_db,
                    job.id,
                    adapter=_generation_adapter(),
                    settings=settings,
                    clock=lambda: NOW,
                )
                self.assertEqual(plan.status, "pending_confirmation")

            async def confirm_once() -> str:
                async with AsyncSession(engine, expire_on_commit=False) as db:
                    confirmed = await job_evaluation_plan_service.confirm_current_plan(
                        db,
                        job_id,
                    )
                    return confirmed.status

            statuses = await asyncio.gather(confirm_once(), confirm_once())
            self.assertEqual(statuses, ["ready", "ready"])

            async with AsyncSession(engine) as verify_db:
                rows = list(
                    (
                        await verify_db.scalars(
                            select(JobEvaluationPlan).where(
                                JobEvaluationPlan.job_id == job_id
                            )
                        )
                    ).all()
                )
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].status, "ready")
                self.assertTrue(rows[0].is_current)
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


def test_confirm_api_has_no_edit_body_and_reconciles_screening_as_ready() -> None:
    db = AsyncMock()
    plan = Mock(id=4, job_id=701, status="ready")
    read_model = JobEvaluationPlanRead.model_validate(
        make_v4_plan(status="ready")
    )
    app = FastAPI()
    app.include_router(api.router)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with (
        patch.object(
            job_evaluation_plan_service,
            "confirm_current_plan",
            AsyncMock(return_value=plan),
        ) as confirm,
        patch.object(
            job_evaluation_plan_service,
            "build_read_model",
            return_value=read_model,
        ),
        patch.object(
            api,
            "_notify_screening_plan_changed",
            AsyncMock(),
        ) as notify,
    ):
        # The route contract test above already proves there are no editable body fields.
        route = next(
            item
            for item in api.router.routes
            if item.path == "/jobs/{job_id}/evaluation-plan/confirm"
        )
        assert route.dependant.body_params == []
        with TestClient(app) as client:
            response = client.post("/jobs/701/evaluation-plan/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    confirm.assert_awaited_once_with(db, 701)
    notify.assert_awaited_once_with(db, 701, plan_ready=True)


def test_confirm_api_maps_stale_or_invalid_plan_to_safe_409() -> None:
    db = AsyncMock()
    app = FastAPI()
    app.include_router(api.router)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with patch.object(
        job_evaluation_plan_service,
        "confirm_current_plan",
        AsyncMock(
            side_effect=JobEvaluationPlanNotConfirmableError(
                "postgresql://private stale detail"
            )
        ),
    ):
        with TestClient(app) as client:
            response = client.post("/jobs/701/evaluation-plan/confirm")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "JOB_EVALUATION_PLAN_NOT_CONFIRMABLE"
    assert "private" not in response.text
    assert "postgresql" not in response.text
