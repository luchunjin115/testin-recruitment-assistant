import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock

from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
    JobEvaluationPlanAuthenticationError,
    JobEvaluationPlanTimeoutError,
)
from app.core.config import Settings
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import JobEvaluationPlanWarning
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanContentError,
    JobEvaluationPlanService,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def make_requirements(**overrides) -> dict:
    values = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台核心服务"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 2,
        "education_requirement": "bachelor_or_above",
        "required_experiences": ["有后端服务开发经验"],
        "preferred_experiences": ["有招聘系统经验"],
        "keywords": ["异步服务"],
        "additional_requirements": ["具备良好沟通能力"],
    }
    values.update(overrides)
    return values


def make_job(**overrides) -> Job:
    values = {
        "id": 1,
        "title": "后端工程师",
        "department": "研发部",
        "description": (
            "参与性能优化。熟悉 Redis、Kafka 优先。"
            "公司介绍：我们提供五险一金和团建活动。"
        ),
        "requirements": make_requirements(),
        "status": "open",
    }
    values.update(overrides)
    return Job(**values)


def ai_content(items: list[dict]) -> str:
    return json.dumps(
        {"schema_version": "1.0", "items": items},
        ensure_ascii=False,
    )


def adapter_result(content: str) -> JobEvaluationPlanAdapterResult:
    return JobEvaluationPlanAdapterResult(
        content=content,
        model="fake-deepseek-v1",
        finish_reason="stop",
    )


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="test-key",
        JOB_EVALUATION_PLAN_MODEL="fake-deepseek",
    )


def make_session(*scalar_results) -> Mock:
    session = Mock()
    session.scalar = AsyncMock(side_effect=list(scalar_results))
    session.get = AsyncMock()
    session.add = Mock(side_effect=lambda value: setattr(value, "id", value.id or 1))
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class JobEvaluationPlanContentTest(TestCase):
    def setUp(self) -> None:
        self.service = JobEvaluationPlanService()

    def test_structured_fields_are_fully_covered_and_skills_are_independent(self) -> None:
        snapshot = self.service.build_input_snapshot(make_job())

        result = self.service.build_plan_content(snapshot, ai_content([]))

        coverage = {
            field.source_field: field for field in result.structured_coverage.fields
        }
        expected_counts = {
            "requirements.responsibilities": 1,
            "requirements.required_skills": 2,
            "requirements.preferred_skills": 1,
            "requirements.minimum_work_years": 1,
            "requirements.education_requirement": 1,
            "requirements.required_experiences": 1,
            "requirements.preferred_experiences": 1,
            "requirements.keywords": 1,
            "requirements.additional_requirements": 1,
        }
        self.assertEqual(
            {key: field.source_value_count for key, field in coverage.items()},
            expected_counts,
        )
        self.assertTrue(result.structured_coverage.all_covered)
        skill_titles = [
            item.title for item in result.items if item.category.value == "skill"
        ]
        self.assertIn("Python", skill_titles)
        self.assertIn("PostgreSQL", skill_titles)
        self.assertIn("Docker", skill_titles)

    def test_b_plus_c_merge_deduplicates_and_keeps_structured_required(self) -> None:
        snapshot = self.service.build_input_snapshot(make_job())
        raw = ai_content(
            [
                {
                    "title": "熟练掌握 Python",
                    "category": "skill",
                    "priority": "general",
                    "source_quote": "Python",
                },
                {
                    "title": "Python",
                    "category": "skill",
                    "priority": "general",
                    "source_quote": "Python",
                },
            ]
        )

        result = self.service.build_plan_content(snapshot, raw)

        python_items = [item for item in result.items if "Python" in item.title]
        self.assertEqual(len(python_items), 1)
        self.assertEqual(python_items[0].source_type.value, "structured")
        self.assertEqual(python_items[0].priority.value, "required")

    def test_ai_priority_comes_from_quote_and_vague_text_cannot_be_required(self) -> None:
        snapshot = self.service.build_input_snapshot(make_job())
        raw = ai_content(
            [
                {
                    "title": "性能优化",
                    "category": "responsibility",
                    "priority": "required",
                    "source_quote": "参与性能优化",
                },
                {
                    "title": "Redis、Kafka",
                    "category": "skill",
                    "priority": "required",
                    "source_quote": "熟悉 Redis、Kafka 优先",
                },
            ]
        )

        result = self.service.build_plan_content(snapshot, raw)

        performance = next(item for item in result.items if item.title == "性能优化")
        self.assertEqual(performance.priority.value, "general")
        redis = next(item for item in result.items if item.title == "Redis")
        kafka = next(item for item in result.items if item.title == "Kafka")
        self.assertEqual(redis.priority.value, "preferred")
        self.assertEqual(kafka.priority.value, "preferred")

    def test_requirement_noun_does_not_accidentally_become_required(self) -> None:
        job = make_job(
            description="负责客户需求调研和需求文档整理。需要独立撰写分析结论。",
            requirements=make_requirements(
                responsibilities=[],
                required_skills=[],
                preferred_skills=[],
                minimum_work_years=None,
                education_requirement=None,
                required_experiences=[],
                preferred_experiences=[],
                keywords=[],
                additional_requirements=[],
            ),
        )
        snapshot = self.service.build_input_snapshot(job)
        raw = ai_content(
            [
                {
                    "title": "客户需求调研",
                    "category": "responsibility",
                    "priority": "required",
                    "source_quote": "负责客户需求调研",
                },
                {
                    "title": "需求文档整理",
                    "category": "responsibility",
                    "priority": "required",
                    "source_quote": "需求文档整理",
                },
                {
                    "title": "独立撰写分析结论",
                    "category": "responsibility",
                    "priority": "general",
                    "source_quote": "需要独立撰写分析结论",
                },
            ]
        )

        result = self.service.build_plan_content(snapshot, raw)
        priorities = {item.title: item.priority.value for item in result.items}

        self.assertEqual(priorities["客户需求调研"], "general")
        self.assertEqual(priorities["需求文档整理"], "general")
        self.assertEqual(priorities["独立撰写分析结论"], "required")

    def test_promotional_text_is_filtered_and_source_quote_is_required(self) -> None:
        snapshot = self.service.build_input_snapshot(make_job())
        raw = ai_content(
            [
                {
                    "title": "五险一金",
                    "category": "other",
                    "priority": "general",
                    "source_quote": "我们提供五险一金和团建活动",
                }
            ]
        )
        result = self.service.build_plan_content(snapshot, raw)
        self.assertFalse(any(item.title == "五险一金" for item in result.items))

        with self.assertRaises(JobEvaluationPlanContentError) as raised:
            self.service.build_plan_content(
                snapshot,
                ai_content(
                    [
                        {
                            "title": "量子计算",
                            "category": "skill",
                            "priority": "required",
                            "source_quote": "JD 中不存在的引用",
                        }
                    ]
                ),
            )
        self.assertEqual(
            raised.exception.code,
            "JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED",
        )

    def test_one_to_four_items_warn_zero_fails_and_over_thirty_fails(self) -> None:
        limited_job = make_job(
            description=None,
            requirements=make_requirements(
                responsibilities=["负责后端开发"],
                required_skills=[],
                preferred_skills=[],
                minimum_work_years=None,
                education_requirement=None,
                required_experiences=[],
                preferred_experiences=[],
                keywords=[],
                additional_requirements=[],
            ),
        )
        limited = self.service.build_plan_content(
            self.service.build_input_snapshot(limited_job),
            ai_content([]),
        )
        self.assertEqual(limited.warnings, [JobEvaluationPlanWarning.LIMITED_BASIS])

        empty_job = make_job(
            description=None,
            requirements=make_requirements(
                responsibilities=[],
                required_skills=[],
                preferred_skills=[],
                minimum_work_years=None,
                education_requirement=None,
                required_experiences=[],
                preferred_experiences=[],
                keywords=[],
                additional_requirements=[],
            ),
        )
        with self.assertRaises(JobEvaluationPlanContentError) as zero:
            self.service.build_plan_content(
                self.service.build_input_snapshot(empty_job),
                ai_content([]),
            )
        self.assertEqual(zero.exception.code, "JOB_EVALUATION_PLAN_NO_ITEMS")

        crowded_job = make_job(
            requirements=make_requirements(
                responsibilities=[],
                required_skills=[f"技能 {index}" for index in range(31)],
                preferred_skills=[],
                minimum_work_years=None,
                education_requirement=None,
                required_experiences=[],
                preferred_experiences=[],
                keywords=[],
                additional_requirements=[],
            )
        )
        with self.assertRaises(JobEvaluationPlanContentError) as crowded:
            self.service.build_plan_content(
                self.service.build_input_snapshot(crowded_job),
                ai_content([]),
            )
        self.assertEqual(
            crowded.exception.code,
            "JOB_EVALUATION_PLAN_TOO_MANY_ITEMS",
        )

    def test_fingerprint_changes_only_for_evaluation_relevant_jd(self) -> None:
        first = make_job(location="上海", headcount=2)
        second = make_job(location="杭州", headcount=8)
        changed = make_job(description="必须掌握 Python")

        first_fingerprint = self.service.fingerprint_snapshot(
            self.service.build_input_snapshot(first)
        )
        second_fingerprint = self.service.fingerprint_snapshot(
            self.service.build_input_snapshot(second)
        )
        changed_fingerprint = self.service.fingerprint_snapshot(
            self.service.build_input_snapshot(changed)
        )

        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertNotEqual(first_fingerprint, changed_fingerprint)


class JobEvaluationPlanWorkflowTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = JobEvaluationPlanService()
        self.settings = make_settings()

    async def test_generation_persists_ready_plan_with_fake_adapter(self) -> None:
        job = make_job()
        plan_holder: list[JobEvaluationPlan] = []
        db = make_session(job, None, None)
        db.add.side_effect = lambda plan: (
            setattr(plan, "id", 1),
            plan_holder.append(plan),
        )
        adapter = FakeJobEvaluationPlanAdapter([adapter_result(ai_content([]))])

        async def scalar(statement):
            if db.scalar.await_count <= 3:
                return [job, None, None][db.scalar.await_count - 1]
            return plan_holder[0] if db.scalar.await_count == 4 else job

        db.scalar.side_effect = scalar

        plan = await self.service.generate_for_job(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(plan.status, "ready")
        self.assertTrue(plan.is_current)
        self.assertEqual(plan.model_version, "fake-deepseek-v1")
        self.assertGreater(len(plan.items), 0)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(db.commit.await_count, 2)

    async def test_same_jd_ready_plan_is_idempotent_without_model_call(self) -> None:
        job = make_job()
        fingerprint = self.service.fingerprint_snapshot(
            self.service.build_input_snapshot(job)
        )
        existing = JobEvaluationPlan(
            id=1,
            job_id=job.id,
            jd_fingerprint=fingerprint,
            input_fingerprint=fingerprint,
            status="ready",
            is_current=True,
        )
        db = make_session(job, existing)
        adapter = FakeJobEvaluationPlanAdapter([])

        result = await self.service.generate_for_job(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertIs(result, existing)
        self.assertEqual(adapter.calls, [])
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_jd_change_marks_old_plan_outdated_before_new_generation(self) -> None:
        job = make_job(description="新的 JD：必须掌握 Python")
        old = JobEvaluationPlan(
            id=8,
            job_id=job.id,
            jd_fingerprint="0" * 64,
            input_fingerprint="0" * 64,
            status="ready",
            is_current=True,
            completed_at=NOW,
        )
        new_holder: list[JobEvaluationPlan] = []
        db = make_session()
        db.add.side_effect = lambda plan: (
            setattr(plan, "id", 9),
            new_holder.append(plan),
        )

        async def scalar(statement):
            results = [job, old, None]
            if db.scalar.await_count <= 3:
                return results[db.scalar.await_count - 1]
            return new_holder[0] if db.scalar.await_count == 4 else job

        db.scalar.side_effect = scalar
        adapter = FakeJobEvaluationPlanAdapter([adapter_result(ai_content([]))])

        current = await self.service.generate_for_job(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(old.status, "outdated")
        self.assertFalse(old.is_current)
        self.assertEqual(current.status, "ready")
        self.assertTrue(current.is_current)
        db.flush.assert_awaited_once()

    async def test_retryable_error_retries_once_then_succeeds(self) -> None:
        job = make_job()
        holder: list[JobEvaluationPlan] = []
        db = make_session()
        db.add.side_effect = lambda plan: (
            setattr(plan, "id", 1),
            holder.append(plan),
        )

        async def scalar(statement):
            initial = [job, None, None]
            if db.scalar.await_count <= 3:
                return initial[db.scalar.await_count - 1]
            return holder[0] if db.scalar.await_count == 4 else job

        db.scalar.side_effect = scalar
        adapter = FakeJobEvaluationPlanAdapter(
            [
                JobEvaluationPlanTimeoutError("timeout"),
                adapter_result(ai_content([])),
            ]
        )

        result = await self.service.generate_for_job(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(result.status, "ready")
        self.assertEqual(len(adapter.calls), 2)

    async def test_content_and_nonretryable_errors_do_not_retry(self) -> None:
        cases = (
            (adapter_result("not-json"), "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"),
            (
                JobEvaluationPlanAuthenticationError("认证失败"),
                "JOB_EVALUATION_PLAN_AUTHENTICATION_ERROR",
            ),
        )
        for outcome, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                job = make_job()
                holder: list[JobEvaluationPlan] = []
                db = make_session()
                db.add.side_effect = lambda plan: (
                    setattr(plan, "id", 1),
                    holder.append(plan),
                )

                async def scalar(statement):
                    initial = [job, None, None]
                    if db.scalar.await_count <= 3:
                        return initial[db.scalar.await_count - 1]
                    return holder[0] if db.scalar.await_count == 4 else job

                db.scalar.side_effect = scalar
                adapter = FakeJobEvaluationPlanAdapter([outcome])

                result = await self.service.generate_for_job(
                    db,
                    job.id,
                    adapter=adapter,
                    settings=self.settings,
                    clock=lambda: NOW,
                )

                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error_code, expected_code)
                self.assertEqual(len(adapter.calls), 1)

    async def test_retryable_error_fails_after_exactly_two_calls(self) -> None:
        job = make_job()
        holder: list[JobEvaluationPlan] = []
        db = make_session()
        db.add.side_effect = lambda plan: (
            setattr(plan, "id", 1),
            holder.append(plan),
        )

        async def scalar(statement):
            initial = [job, None, None]
            if db.scalar.await_count <= 3:
                return initial[db.scalar.await_count - 1]
            return holder[0] if db.scalar.await_count == 4 else job

        db.scalar.side_effect = scalar
        adapter = FakeJobEvaluationPlanAdapter(
            [
                JobEvaluationPlanTimeoutError("first"),
                JobEvaluationPlanTimeoutError("second"),
            ]
        )

        result = await self.service.generate_for_job(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "JOB_EVALUATION_PLAN_TIMEOUT")
        self.assertEqual(len(adapter.calls), 2)
        self.assertNotIn("first", result.error_message)

    async def test_failed_current_plan_can_be_regenerated(self) -> None:
        job = make_job()
        fingerprint = self.service.fingerprint_snapshot(
            self.service.build_input_snapshot(job)
        )
        failed = JobEvaluationPlan(
            id=1,
            job_id=job.id,
            jd_fingerprint=fingerprint,
            input_fingerprint=fingerprint,
            status="failed",
            is_current=True,
            items=[],
            error_code="JOB_EVALUATION_PLAN_TIMEOUT",
            error_message="模型服务暂时不可用",
            completed_at=NOW,
        )
        db = make_session(failed, job, failed, failed, job)
        db.get.return_value = job
        adapter = FakeJobEvaluationPlanAdapter([adapter_result(ai_content([]))])

        result = await self.service.regenerate_failed_plan(
            db,
            job.id,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
        )

        self.assertEqual(result.status, "ready")
        self.assertIsNone(result.error_code)
        self.assertEqual(len(adapter.calls), 1)
