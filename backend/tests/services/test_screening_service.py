import json
from collections import deque
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase

from app.adapters.screening_model import (
    ScreeningModelAdapterResult,
    ScreeningModelTimeoutError,
)
from app.core.config import Settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_screening_rubric import JobScreeningRubric
from app.models.resume import Resume
from app.models.screening_result import ScreeningResult
from app.schemas.application import ScreeningRunRequest
from app.schemas.job import JobRequirementsV1
from app.schemas.screening_rubric import (
    ScreeningRubricWeights,
    SemanticRubricCriterion,
)
from app.services.screening_rubric_service import ScreeningRubricService
from app.services.screening_service import (
    ScreeningAlreadyRunningError,
    ScreeningNotAllowedError,
    ScreeningService,
)


def semantic_items() -> list[dict]:
    dimensions = (
        "must_have_requirements",
        "work_experience_relevance",
        "projects_and_capability",
        "preferred_qualifications",
    )
    return [
        {
            "key": f"criterion_{index}",
            "name": f"评分项 {index}",
            "description": f"评价候选人的岗位能力 {index}",
            "dimension": dimension,
            "max_score": 10,
            "suggested_share": 10,
            "high_score_anchor": "有充分并且可核对的优秀证据",
            "mid_score_anchor": "有部分相关证据",
            "low_score_anchor": "存在明确较弱证据",
            "source": "hr_manual",
        }
        for index, dimension in enumerate(dimensions, start=1)
    ]


def model_content(*, invalid: bool = False) -> str:
    if invalid:
        return '{"schema_version":"1.0","evaluations":[]}'
    return json.dumps(
        {
            "schema_version": "1.0",
            "evaluations": [
                {
                    "criterion_key": f"criterion_{index}",
                    "score": 8,
                    "confidence": "high",
                    "evidence": [
                        {
                            "source": "resume_text",
                            "locator": "工作经历",
                            "quote": "负责招聘平台后端服务",
                        }
                    ],
                    "reason": "候选人材料提供了直接证据",
                    "strengths": ["具备相关交付经验"],
                    "gaps": [],
                }
                for index in range(1, 5)
            ],
        },
        ensure_ascii=False,
    )


class FakeAdapter:
    def __init__(self, *, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content or model_content()
        self.error = error
        self.calls = 0

    async def evaluate(self, job_context, semantic_items, candidate_material):
        del job_context, semantic_items, candidate_material
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ScreeningModelAdapterResult(
            content=self.content,
            model="deepseek-test",
            finish_reason="stop",
            duration_ms=123,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.001000"),
        )


class FakeSession:
    def __init__(self, scalar_values) -> None:
        self.scalar_values = deque(scalar_values)
        self.added: ScreeningResult | None = None
        self.commit_count = 0
        self.rollback_count = 0
        self.refresh_count = 0

    async def scalar(self, statement):
        del statement
        value = self.scalar_values.popleft()
        return value() if callable(value) else value

    def add(self, value) -> None:
        self.added = value
        if value.id is None:
            value.id = 100

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def refresh(self, value, attribute_names=None) -> None:
        del value, attribute_names
        self.refresh_count += 1


def make_graph(*, has_material: bool = True, old_result: ScreeningResult | None = None):
    requirements = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台后端服务"],
        "required_skills": ["Python"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 3,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": ["FastAPI"],
        "additional_requirements": [],
    }
    job = Job(
        id=20,
        title="Python 后端工程师",
        department="研发部",
        description="负责招聘平台后端服务",
        requirements=requirements,
        status="open",
    )
    job_fingerprint = ScreeningRubricService.build_job_fingerprint(
        {
            "title": job.title,
            "description": job.description,
            "requirements": requirements,
        }
    )
    rubric = JobScreeningRubric(
        id=30,
        job_id=20,
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
        semantic_items=semantic_items(),
        job_fingerprint=job_fingerprint,
        is_stale=False,
        change_reason="draft_published",
    )
    job.screening_rubrics = [rubric]

    parsed_data = (
        {
            "draft": {
                "basic_info": {
                    "current_title": "后端工程师",
                    "work_years": 4,
                    "education_level": "本科",
                },
                "skills": ["Python", "FastAPI", "Docker"],
            }
        }
        if has_material
        else None
    )
    candidate = Candidate(
        id=10,
        name="测试候选人",
        phone="13800138000",
        email="candidate@example.com",
        work_years=4 if has_material else None,
        education_level="本科" if has_material else None,
        parsed_data=parsed_data,
    )
    candidate.education_records = []
    candidate.work_experiences = []
    candidate.project_experiences = []
    resume = Resume(
        id=40,
        candidate_id=10,
        filename="resume.txt",
        file_path="safe/resume.txt",
        raw_text=(
            "姓名：测试候选人\n邮箱：candidate@example.com\n负责招聘平台后端服务，使用 FastAPI"
            if has_material
            else "姓名：测试候选人\n邮箱：candidate@example.com"
        ),
        parsed_snapshot=parsed_data,
        structure_schema_version="1.0" if has_material else None,
    )
    application = Application(
        id=50,
        candidate_id=10,
        job_id=20,
        current_resume_id=40,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage="applied",
        ai_status="not_started",
        hr_decision="pending",
        candidate=candidate,
        job=job,
        current_resume=resume,
        current_screening_result=old_result,
        current_screening_result_id=(old_result.id if old_result is not None else None),
    )
    return application, rubric


def settings() -> Settings:
    return Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="test-key",
        SCREENING_MODEL_NAME="deepseek-test",
    )


class ScreeningServiceTest(IsolatedAsyncioTestCase):
    async def test_runs_one_model_call_and_switches_current_success(self) -> None:
        application, rubric = make_graph()
        adapter = FakeAdapter()
        session = FakeSession(
            [
                application,
                None,
                None,
                0,
                application,
                lambda: session.added,
                rubric.id,
            ]
        )
        service = ScreeningService(model_adapter=adapter, settings=settings())

        outcome = await service.run(session, application.id)

        self.assertFalse(outcome.reused)
        self.assertTrue(outcome.model_called)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(outcome.result.execution_status, "completed")
        self.assertEqual(application.ai_status, "completed")
        self.assertEqual(application.current_screening_result_id, outcome.result.id)
        self.assertEqual(outcome.result.model_name, "deepseek-test")
        self.assertEqual(outcome.result.total_tokens, 150)
        self.assertNotIn("测试候选人", json.dumps(outcome.result.candidate_input_snapshot, ensure_ascii=False))
        self.assertEqual(session.commit_count, 2)

    async def test_same_fingerprint_reuses_success_without_model_call(self) -> None:
        application, _ = make_graph()
        adapter = FakeAdapter()
        service = ScreeningService(model_adapter=adapter, settings=settings())
        fingerprint = service._input_fingerprint(
            application=application,
            material=service.input_service.build_candidate_material(
                application_ref="application-50",
                confirmed_profile=service._candidate_profile(application.candidate),
                resume_raw_text=application.current_resume.raw_text,
                resume_snapshot=application.current_resume.parsed_snapshot,
            ),
            requirements=JobRequirementsV1.model_validate(application.job.requirements),
            rubric=application.job.screening_rubrics[0],
            weights=ScreeningRubricWeights.model_validate(
                application.job.screening_rubrics[0].weights
            ),
            semantic_items=[
                SemanticRubricCriterion.model_validate(item)
                for item in application.job.screening_rubrics[0].semantic_items
            ],
        )
        reusable = ScreeningResult(
            id=70,
            candidate_id=10,
            job_id=20,
            application_id=50,
            resume_id=40,
            attempt_number=1,
            execution_status="completed",
            input_fingerprint=fingerprint,
            is_outdated=False,
        )
        session = FakeSession([application, None, reusable])

        outcome = await service.run(session, application.id)

        self.assertTrue(outcome.reused)
        self.assertFalse(outcome.model_called)
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(application.current_screening_result_id, reusable.id)

    async def test_provider_failure_preserves_old_success(self) -> None:
        old = ScreeningResult(
            id=60,
            candidate_id=10,
            job_id=20,
            application_id=50,
            resume_id=40,
            attempt_number=1,
            execution_status="completed",
            input_fingerprint="old-input",
            is_outdated=False,
        )
        application, rubric = make_graph(old_result=old)
        adapter = FakeAdapter(error=ScreeningModelTimeoutError("模型调用超时"))
        session = FakeSession(
            [
                application,
                None,
                None,
                1,
                application,
                lambda: session.added,
                rubric.id,
            ]
        )
        service = ScreeningService(model_adapter=adapter, settings=settings())

        outcome = await service.run(session, application.id)

        self.assertEqual(outcome.result.execution_status, "failed")
        self.assertEqual(outcome.result.error_code, "screening_model_timeout_error")
        self.assertEqual(application.current_screening_result_id, old.id)
        self.assertTrue(old.is_outdated)
        self.assertEqual(application.ai_status, "failed")

    async def test_force_rerun_creates_new_attempt_even_when_success_is_reusable(self) -> None:
        application, rubric = make_graph()
        adapter = FakeAdapter()
        service = ScreeningService(model_adapter=adapter, settings=settings())
        material = service.input_service.build_candidate_material(
            application_ref="application-50",
            confirmed_profile=service._candidate_profile(application.candidate),
            resume_raw_text=application.current_resume.raw_text,
            resume_snapshot=application.current_resume.parsed_snapshot,
        )
        reusable = ScreeningResult(
            id=70,
            candidate_id=10,
            job_id=20,
            application_id=50,
            resume_id=40,
            attempt_number=1,
            execution_status="completed",
            input_fingerprint=service._input_fingerprint(
                application=application,
                material=material,
                requirements=JobRequirementsV1.model_validate(application.job.requirements),
                rubric=rubric,
                weights=ScreeningRubricWeights.model_validate(rubric.weights),
                semantic_items=[
                    SemanticRubricCriterion.model_validate(item)
                    for item in rubric.semantic_items
                ],
            ),
            is_outdated=False,
        )
        application.current_screening_result = reusable
        application.current_screening_result_id = reusable.id
        session = FakeSession(
            [
                application,
                None,
                reusable,
                1,
                application,
                lambda: session.added,
                rubric.id,
            ]
        )

        outcome = await service.run(
            session,
            application.id,
            ScreeningRunRequest(
                force=True,
                confirm_force=True,
                reason="HR 主动复核",
            ),
        )

        self.assertFalse(outcome.reused)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(outcome.result.attempt_number, 2)
        self.assertTrue(outcome.result.force_rerun)
        self.assertEqual(outcome.result.trigger_reason, "HR 主动复核")

    async def test_invalid_model_output_is_saved_as_failed(self) -> None:
        application, rubric = make_graph()
        adapter = FakeAdapter(content=model_content(invalid=True))
        session = FakeSession(
            [application, None, None, 0, application, lambda: session.added, rubric.id]
        )
        service = ScreeningService(model_adapter=adapter, settings=settings())

        outcome = await service.run(session, application.id)

        self.assertEqual(outcome.result.execution_status, "failed")
        self.assertEqual(outcome.result.error_code, "screening_model_invalid_output")
        self.assertEqual(application.ai_status, "failed")

    async def test_identity_only_material_is_blocked_before_model(self) -> None:
        application, rubric = make_graph(has_material=False)
        adapter = FakeAdapter()
        session = FakeSession(
            [application, None, None, 0, application, lambda: session.added, rubric.id]
        )
        service = ScreeningService(model_adapter=adapter, settings=settings())

        outcome = await service.run(session, application.id)

        self.assertEqual(outcome.result.execution_status, "blocked")
        self.assertEqual(outcome.result.error_code, "candidate_material_insufficient")
        self.assertFalse(outcome.model_called)
        self.assertEqual(adapter.calls, 0)
        self.assertIsNone(application.current_screening_result_id)

    async def test_running_attempt_rejects_concurrent_request(self) -> None:
        application, _ = make_graph()
        running = ScreeningResult(
            id=80,
            candidate_id=10,
            job_id=20,
            application_id=50,
            attempt_number=1,
            execution_status="screening",
        )
        session = FakeSession([application, running])
        service = ScreeningService(model_adapter=FakeAdapter(), settings=settings())

        with self.assertRaises(ScreeningAlreadyRunningError):
            await service.run(session, application.id)

        self.assertEqual(session.rollback_count, 1)

    async def test_job_fingerprint_drift_blocks_before_model_call(self) -> None:
        application, _ = make_graph()
        application.job.requirements = {
            **application.job.requirements,
            "minimum_work_years": 6,
        }
        adapter = FakeAdapter()
        session = FakeSession([application])
        service = ScreeningService(model_adapter=adapter, settings=settings())

        with self.assertRaises(ScreeningNotAllowedError):
            await service.run(session, application.id)

        self.assertEqual(adapter.calls, 0)
        self.assertEqual(session.rollback_count, 1)
