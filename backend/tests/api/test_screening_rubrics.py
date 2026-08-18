from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.screening_rubric_generation import (
    RubricGenerationTimeoutError,
)
from app.api.jobs import install_job_exception_handlers, router
from app.core.database import get_db
from app.models.job_screening_rubric import JobScreeningRubric
from app.services.screening_rubric_service import (
    CurrentScreeningRubricNotFoundError,
    ScreeningRubricDraftAlreadyExistsError,
    ScreeningRubricDraftNotFoundError,
    ScreeningRubricGenerationInvalidOutputError,
    ScreeningRubricJobNotFoundError,
    ScreeningRubricPublishValidationError,
    ScreeningRubricStaleError,
    screening_rubric_service,
)
from app.prompts.screening_rubric_templates import get_rubric_template


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_rubric(
    version: int = 1,
    *,
    status: str = "active",
) -> JobScreeningRubric:
    is_current = status == "active"
    return JobScreeningRubric(
        id=10 + version,
        job_id=1,
        version=version,
        must_have_requirements_weight=40,
        work_experience_relevance_weight=25,
        projects_and_capability_weight=20,
        preferred_qualifications_weight=10,
        keywords_and_additional_weight=5,
        schema_version="2.0",
        subcriteria_version="2.0",
        recommendation_thresholds_version="1.0",
        fairness_rules_version="1.0",
        is_current=is_current,
        source="standard_template",
        template_key="standard",
        status=status,
        semantic_items=[
            item.model_dump(mode="json")
            for item in get_rubric_template("standard").semantic_items
        ],
        job_fingerprint="a" * 64,
        is_stale=False,
        stale_at=None,
        stale_reason=None,
        generation_metadata=None,
        change_reason=("initial_default" if version == 1 else "hr_adjustment"),
        change_detail="评分规则说明",
        created_by="本地 HR（未认证）",
        confirmed_by="本地 HR（未认证）" if is_current else None,
        confirmed_at=TEST_TIME if is_current else None,
        abandoned_at=TEST_TIME if status == "abandoned" else None,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def draft_update_payload() -> dict:
    return {
        "expected_job_fingerprint": "a" * 64,
        "weights": {
            "must_have_requirements": 45,
            "work_experience_relevance": 25,
            "projects_and_capability": 20,
            "preferred_qualifications": 5,
            "keywords_and_additional": 5,
        },
        "change_detail": "提高必备条件权重",
    }


class ScreeningRubricApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_job_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_get_returns_current_version_and_nested_weights(self) -> None:
        service_mock = AsyncMock(return_value=make_rubric())

        with patch.object(
            screening_rubric_service,
            "get_current_rubric",
            service_mock,
        ):
            response = self.client.get("/jobs/1/screening-rubric")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 1)
        self.assertEqual(response.json()["weights"]["must_have_requirements"], 40)
        service_mock.assert_awaited_once_with(self.db, 1)

    def test_create_template_draft_and_get_draft(self) -> None:
        draft = make_rubric(version=2, status="draft")
        cases = (
            (
                "create_template_draft",
                "post",
                "/jobs/1/screening-rubric/draft/from-template",
                {
                    "template_key": "technical",
                    "change_detail": "采用技术岗位模板",
                },
                201,
            ),
            (
                "get_draft_rubric",
                "get",
                "/jobs/1/screening-rubric/draft",
                None,
                200,
            ),
        )
        for method_name, http_method, path, payload, expected_status in cases:
            with self.subTest(method_name=method_name):
                service_mock = AsyncMock(return_value=draft)
                with patch.object(
                    screening_rubric_service,
                    method_name,
                    service_mock,
                ):
                    if payload is None:
                        response = getattr(self.client, http_method)(path)
                    else:
                        response = getattr(self.client, http_method)(path, json=payload)

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["status"], "draft")
                self.assertFalse(response.json()["is_current"])

    def test_update_draft_accepts_fingerprint_and_custom_weights(self) -> None:
        service_mock = AsyncMock(return_value=make_rubric(version=2, status="draft"))
        with patch.object(screening_rubric_service, "update_draft", service_mock):
            response = self.client.put(
                "/jobs/1/screening-rubric/draft",
                json=draft_update_payload(),
            )

        self.assertEqual(response.status_code, 200)
        passed_db, job_id, request = service_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(job_id, 1)
        self.assertEqual(request.expected_job_fingerprint, "a" * 64)

    def test_invalid_draft_has_stable_422_code_before_service(self) -> None:
        payload = draft_update_payload()
        payload["weights"]["must_have_requirements"] = 50
        service_mock = AsyncMock()

        with patch.object(
            screening_rubric_service,
            "update_draft",
            service_mock,
        ):
            response = self.client.put(
                "/jobs/1/screening-rubric/draft",
                json=payload,
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "RUBRIC_DRAFT_INVALID")
        service_mock.assert_not_awaited()

    def test_missing_job_and_missing_current_rubric_are_safely_mapped(self) -> None:
        cases = (
            (ScreeningRubricJobNotFoundError("private"), 404, "JOB_NOT_FOUND"),
            (
                CurrentScreeningRubricNotFoundError("private"),
                500,
                "RUBRIC_OPERATION_FAILED",
            ),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(code=expected_code):
                with patch.object(
                    screening_rubric_service,
                    "get_current_rubric",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.get("/jobs/1/screening-rubric")
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_expected_draft_errors_have_stable_safe_codes(self) -> None:
        cases = (
            (ScreeningRubricDraftNotFoundError("private"), 404, "RUBRIC_DRAFT_NOT_FOUND"),
            (
                ScreeningRubricDraftAlreadyExistsError("private"),
                409,
                "RUBRIC_DRAFT_ALREADY_EXISTS",
            ),
            (ScreeningRubricStaleError("private"), 409, "RUBRIC_DRAFT_STALE"),
            (
                ScreeningRubricPublishValidationError("private"),
                422,
                "RUBRIC_PUBLISH_INVALID",
            ),
        )
        payload = {
            "expected_job_fingerprint": "a" * 64,
            "change_detail": "发布评分标准",
        }
        for error, expected_status, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with patch.object(
                    screening_rubric_service,
                    "publish_draft",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/jobs/1/screening-rubric/draft/publish",
                        json=payload,
                    )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_generate_and_assist_item_endpoints_return_draft_only_results(self) -> None:
        generated = make_rubric(version=2, status="draft")
        generated.source = "ai_generated"
        generate_mock = AsyncMock(return_value=generated)
        with patch.object(screening_rubric_service, "generate_draft", generate_mock):
            response = self.client.post(
                "/jobs/1/screening-rubric/generate",
                json={
                    "template_key": "technical",
                    "change_detail": "AI 生成技术岗位评分标准",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "draft")
        self.assertEqual(response.json()["source"], "ai_generated")
        generate_mock.assert_awaited_once()

        assist_mock = AsyncMock(
            return_value={
                "job_fingerprint": "a" * 64,
                "suggestion": {
                    "name": "问题解决能力",
                    "description": "评价复杂问题分析与闭环能力",
                    "dimension": "projects_and_capability",
                    "suggested_share": 40,
                    "high_score_anchor": "有复杂问题闭环和量化成果",
                    "mid_score_anchor": "有独立处理经历但结果一般",
                    "low_score_anchor": "缺少独立分析和结果证据",
                },
                "metadata": {
                    "model": "fake-rubric-model",
                    "prompt_version": "rubric_item_assist_v1",
                    "schema_version": "1.0",
                    "input_tokens": 10,
                    "output_tokens": 20,
                },
            }
        )
        with patch.object(
            screening_rubric_service,
            "assist_manual_item",
            assist_mock,
        ):
            response = self.client.post(
                "/jobs/1/screening-rubric/draft/assist-item",
                json={
                    "expected_job_fingerprint": "a" * 64,
                    "item": {
                        "name": "问题解决能力",
                        "description": "评价问题解决能力",
                        "dimension": "projects_and_capability",
                        "suggested_share": 40,
                        "high_score_anchor": "有复杂问题闭环证据",
                        "mid_score_anchor": "有独立处理问题经历",
                        "low_score_anchor": "缺少独立分析证据",
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggestion"]["name"], "问题解决能力")
        assist_mock.assert_awaited_once()

    def test_generation_failures_have_safe_stable_codes(self) -> None:
        cases = (
            (
                ScreeningRubricGenerationInvalidOutputError("private output"),
                422,
                "RUBRIC_CRITERIA_INVALID",
            ),
            (
                RubricGenerationTimeoutError("private timeout"),
                503,
                "RUBRIC_GENERATION_MODEL_UNAVAILABLE",
            ),
        )
        payload = {
            "template_key": "technical",
            "change_detail": "生成技术岗位评分标准",
        }
        for error, expected_status, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with patch.object(
                    screening_rubric_service,
                    "generate_draft",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/jobs/1/screening-rubric/generate",
                        json=payload,
                    )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_publish_abandon_and_reconfirm_are_registered(self) -> None:
        cases = (
            (
                "publish_draft",
                "/jobs/1/screening-rubric/draft/publish",
                {"expected_job_fingerprint": "a" * 64, "change_detail": "发布"},
                make_rubric(version=2),
            ),
            (
                "abandon_draft",
                "/jobs/1/screening-rubric/draft/abandon",
                {"change_detail": "放弃草稿"},
                make_rubric(version=2, status="abandoned"),
            ),
            (
                "reconfirm_current",
                "/jobs/1/screening-rubric/reconfirm",
                {"expected_job_fingerprint": "a" * 64, "change_detail": "重新确认"},
                make_rubric(version=2),
            ),
        )
        for method_name, path, payload, rubric in cases:
            with self.subTest(method_name=method_name):
                service_mock = AsyncMock(return_value=rubric)
                with patch.object(screening_rubric_service, method_name, service_mock):
                    response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 200)
                service_mock.assert_awaited_once()

    def test_unexpected_draft_failure_is_sanitized(self) -> None:
        with patch.object(
            screening_rubric_service,
            "update_draft",
            AsyncMock(side_effect=RuntimeError("postgresql://private")),
        ):
            response = self.client.put(
                "/jobs/1/screening-rubric/draft",
                json=draft_update_payload(),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RUBRIC_OPERATION_FAILED",
        )
        self.assertNotIn("postgresql", response.text)

    def test_openapi_registers_current_and_draft_lifecycle_routes(self) -> None:
        matching = [
            (method, route.path)
            for route in self.app.routes
            for method in getattr(route, "methods", set())
            if route.path.startswith("/jobs/{job_id}/screening-rubric")
            and method in {"GET", "POST", "PUT"}
        ]
        self.assertEqual(set(matching), {
            ("GET", "/jobs/{job_id}/screening-rubric"),
            ("GET", "/jobs/{job_id}/screening-rubric/draft"),
            ("POST", "/jobs/{job_id}/screening-rubric/draft/from-template"),
            ("POST", "/jobs/{job_id}/screening-rubric/generate"),
            ("POST", "/jobs/{job_id}/screening-rubric/draft/assist-item"),
            ("PUT", "/jobs/{job_id}/screening-rubric/draft"),
            ("POST", "/jobs/{job_id}/screening-rubric/draft/publish"),
            ("POST", "/jobs/{job_id}/screening-rubric/draft/abandon"),
            ("POST", "/jobs/{job_id}/screening-rubric/reconfirm"),
        })
        self.assertEqual(len(matching), 9)
