from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.job_evaluation_plans import router
from app.core.database import get_db
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import JobEvaluationPlanInputSnapshot
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanJobNotFoundError,
    JobEvaluationPlanJobNotOpenError,
    JobEvaluationPlanNotRegenerableError,
    job_evaluation_plan_service,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def make_plan(*, status: str = "ready") -> JobEvaluationPlan:
    failed = status == "failed"
    return JobEvaluationPlan(
        id=3,
        job_id=1,
        jd_fingerprint=FINGERPRINT,
        status=status,
        is_current=True,
        items=(
            []
            if failed
            else [
                {
                    "key": "requirement:skill:python",
                    "title": "Python",
                    "category": "skill",
                    "priority": "required",
                    "source_type": "structured",
                    "source_field": "requirements.required_skills",
                    "source_quote": None,
                }
            ]
        ),
        structured_coverage={
            "source_schema_version": "1.0",
            "fields": [],
            "all_covered": True,
        },
        warnings=[],
        prompt_version="job_evaluation_plan_v1",
        model_version="fake-model",
        schema_version="1.0",
        input_fingerprint=FINGERPRINT,
        input_snapshot={
            "job_id": 1,
            "title": "后端工程师",
            "department": "研发部",
            "description": "负责后端开发",
            "requirements": {
                "schema_version": "1.0",
                "responsibilities": [],
                "required_skills": ["Python"],
                "preferred_skills": [],
                "minimum_work_years": None,
                "education_requirement": None,
                "required_experiences": [],
                "preferred_experiences": [],
                "keywords": [],
                "additional_requirements": [],
            },
        },
        error_code=("JOB_EVALUATION_PLAN_TIMEOUT" if failed else None),
        error_message=("模型服务暂时不可用" if failed else None),
        created_at=NOW,
        completed_at=NOW,
        updated_at=NOW,
    )


class JobEvaluationPlanApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.db = Mock()

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_read_returns_current_plan_and_not_found_code(self) -> None:
        service_mock = AsyncMock(return_value=make_plan())
        with (
            patch.object(
                job_evaluation_plan_service,
                "get_current_plan",
                service_mock,
            ),
            patch.object(
                job_evaluation_plan_service,
                "generate_for_job",
                AsyncMock(),
            ) as generate_mock,
        ):
            response = self.client.get("/jobs/1/evaluation-plan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertTrue(response.json()["contract_outdated"])
        self.assertEqual(response.json()["items"][0]["priority"], "required")
        self.assertNotIn("free_text_coverage", response.json())
        service_mock.assert_awaited_once_with(self.db, 1)
        generate_mock.assert_not_awaited()
        self.db.commit.assert_not_called()
        self.db.add.assert_not_called()

        with patch.object(
            job_evaluation_plan_service,
            "get_current_plan",
            AsyncMock(return_value=None),
        ):
            response = self.client.get("/jobs/1/evaluation-plan")
        self.assert_error(response, 404, "JOB_EVALUATION_PLAN_NOT_FOUND")

    def test_generate_and_regenerate_use_separate_stable_actions(self) -> None:
        generate_mock = AsyncMock(return_value=make_plan())
        regenerate_mock = AsyncMock(return_value=make_plan())
        with patch.object(
            job_evaluation_plan_service,
            "generate_for_job",
            generate_mock,
        ):
            generated = self.client.post("/jobs/1/evaluation-plan/generate")
        with patch.object(
            job_evaluation_plan_service,
            "regenerate_failed_plan",
            regenerate_mock,
        ):
            regenerated = self.client.post("/jobs/1/evaluation-plan/regenerate")

        self.assertEqual(generated.status_code, 200)
        self.assertEqual(regenerated.status_code, 200)
        generate_mock.assert_awaited_once_with(self.db, 1)
        regenerate_mock.assert_awaited_once_with(self.db, 1)

    def test_read_current_contract_returns_not_outdated(self) -> None:
        plan = make_plan()
        snapshot = JobEvaluationPlanInputSnapshot.model_validate(
            plan.input_snapshot
        )
        plan.prompt_version = "job_evaluation_plan_v4"
        plan.schema_version = "2.0"
        plan.input_fingerprint = job_evaluation_plan_service.fingerprint_input(
            snapshot
        )

        with patch.object(
            job_evaluation_plan_service,
            "get_current_plan",
            AsyncMock(return_value=plan),
        ):
            response = self.client.get("/jobs/1/evaluation-plan")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["contract_outdated"])

    def test_business_errors_have_stable_status_and_safe_messages(self) -> None:
        cases = (
            (
                "/jobs/99/evaluation-plan/generate",
                "generate_for_job",
                JobEvaluationPlanJobNotFoundError("postgresql://private"),
                404,
                "JOB_NOT_FOUND",
            ),
            (
                "/jobs/1/evaluation-plan/generate",
                "generate_for_job",
                JobEvaluationPlanJobNotOpenError("private"),
                409,
                "JOB_EVALUATION_PLAN_JOB_NOT_OPEN",
            ),
            (
                "/jobs/1/evaluation-plan/regenerate",
                "regenerate_failed_plan",
                JobEvaluationPlanNotRegenerableError("private"),
                409,
                "JOB_EVALUATION_PLAN_NOT_REGENERABLE",
            ),
        )
        for path, method, error, status_code, code in cases:
            with self.subTest(code=code), patch.object(
                job_evaluation_plan_service,
                method,
                AsyncMock(side_effect=error),
            ):
                response = self.client.post(path)
            self.assert_error(response, status_code, code)
            self.assertNotIn("private", response.text)
            self.assertNotIn("postgresql", response.text)

    def test_unexpected_errors_are_sanitized(self) -> None:
        with patch.object(
            job_evaluation_plan_service,
            "generate_for_job",
            AsyncMock(side_effect=RuntimeError("api-key=secret")),
        ):
            response = self.client.post("/jobs/1/evaluation-plan/generate")

        self.assert_error(
            response,
            500,
            "JOB_EVALUATION_PLAN_OPERATION_FAILED",
        )
        self.assertNotIn("secret", response.text)

    def test_openapi_and_main_app_use_nested_api_v2_job_style(self) -> None:
        expected = {
            "/jobs/{job_id}/evaluation-plan": {"get"},
            "/jobs/{job_id}/evaluation-plan/generate": {"post"},
            "/jobs/{job_id}/evaluation-plan/regenerate": {"post"},
        }
        local_schema = self.app.openapi()
        for path, methods in expected.items():
            self.assertEqual(set(local_schema["paths"][path]), methods)

        from app.main import app as main_app

        main_schema = main_app.openapi()
        for path, methods in expected.items():
            prefixed = f"/api/v2{path}"
            self.assertEqual(set(main_schema["paths"][prefixed]), methods)

    def assert_error(self, response, status_code: int, code: str) -> None:
        self.assertEqual(response.status_code, status_code)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], code)
        self.assertIsInstance(detail["message"], str)
