from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import install_job_exception_handlers, router
from app.core.database import get_db
from app.models.rebuilt.job_screening_rubric import JobScreeningRubric
from app.services.rebuilt.screening_rubric_service import (
    CurrentScreeningRubricNotFoundError,
    ScreeningRubricJobNotFoundError,
    screening_rubric_service,
)


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_rubric(version: int = 1) -> JobScreeningRubric:
    return JobScreeningRubric(
        id=10 + version,
        job_id=1,
        version=version,
        must_have_requirements_weight=40,
        work_experience_relevance_weight=25,
        projects_and_capability_weight=20,
        preferred_qualifications_weight=10,
        keywords_and_additional_weight=5,
        schema_version="1.0",
        subcriteria_version="1.0",
        recommendation_thresholds_version="1.0",
        fairness_rules_version="1.0",
        is_current=True,
        change_reason=("initial_default" if version == 1 else "hr_adjustment"),
        change_detail="评分规则说明",
        created_by="本地 HR（未认证）",
        created_at=TEST_TIME,
    )


def update_payload() -> dict:
    return {
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

    def test_update_accepts_custom_weights_and_restore_default(self) -> None:
        cases = (
            (update_payload(), False),
            (
                {
                    "restore_defaults": True,
                    "change_detail": "恢复默认权重",
                },
                True,
            ),
        )
        for payload, restore_defaults in cases:
            with self.subTest(restore_defaults=restore_defaults):
                service_mock = AsyncMock(return_value=make_rubric(version=2))
                with patch.object(
                    screening_rubric_service,
                    "update_rubric",
                    service_mock,
                ):
                    response = self.client.put(
                        "/jobs/1/screening-rubric",
                        json=payload,
                    )

                self.assertEqual(response.status_code, 200)
                passed_db, job_id, request = service_mock.await_args.args
                self.assertIs(passed_db, self.db)
                self.assertEqual(job_id, 1)
                self.assertIs(request.restore_defaults, restore_defaults)

    def test_invalid_weights_have_stable_422_code_before_service(self) -> None:
        payload = update_payload()
        payload["weights"]["must_have_requirements"] = 50
        service_mock = AsyncMock()

        with patch.object(
            screening_rubric_service,
            "update_rubric",
            service_mock,
        ):
            response = self.client.put("/jobs/1/screening-rubric", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "RUBRIC_WEIGHT_INVALID")
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

    def test_unexpected_update_failure_is_sanitized(self) -> None:
        with patch.object(
            screening_rubric_service,
            "update_rubric",
            AsyncMock(side_effect=RuntimeError("postgresql://private")),
        ):
            response = self.client.put(
                "/jobs/1/screening-rubric",
                json=update_payload(),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RUBRIC_OPERATION_FAILED",
        )
        self.assertNotIn("postgresql", response.text)

    def test_openapi_registers_get_and_put_once(self) -> None:
        matching = [
            (method, route.path)
            for route in self.app.routes
            for method in getattr(route, "methods", set())
            if route.path == "/jobs/{job_id}/screening-rubric"
            and method in {"GET", "PUT"}
        ]
        self.assertEqual(set(matching), {
            ("GET", "/jobs/{job_id}/screening-rubric"),
            ("PUT", "/jobs/{job_id}/screening-rubric"),
        })
        self.assertEqual(len(matching), 2)
