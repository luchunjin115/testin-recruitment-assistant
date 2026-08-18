from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import install_job_exception_handlers, router
from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate, JobStatus, JobUpdate
from app.services.job_service import (
    InvalidJobStatusTransitionError,
    JobHasReferencesError,
    JobMustBeClosedBeforeDeleteError,
    JobOpenValidationError,
    JobReferenceCounts,
    job_service,
)


TEST_TIME = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


def make_requirements() -> dict:
    return {
        "schema_version": "1.0",
        "responsibilities": ["负责岗位相关工作"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": [],
        "minimum_work_years": 1,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": [],
        "additional_requirements": [],
    }


def make_job(
    job_id: int,
    title: str,
    *,
    department: str = "研发部",
    status: str = "open",
) -> Job:
    return Job(
        id=job_id,
        title=title,
        department=department,
        location="上海",
        employment_type="full_time",
        headcount=2,
        description=f"{title}岗位描述",
        requirements=make_requirements(),
        status=status,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class JobApiTest(TestCase):
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

    def test_create_job_returns_201_and_created_job(self) -> None:
        created_job = make_job(1, "后端开发工程师", status="draft")
        create_job_mock = AsyncMock(return_value=created_job)

        with patch.object(job_service, "create_job", create_job_mock):
            response = self.client.post(
                "/jobs",
                json={
                    "title": "后端开发工程师",
                    "department": "研发部",
                    "description": "负责招聘平台后端开发",
                    "requirements": make_requirements(),
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["status"], "draft")
        passed_db, passed_data = create_job_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertIsInstance(passed_data, JobCreate)

    def test_create_open_validation_error_has_stable_422_detail(self) -> None:
        create_job_mock = AsyncMock(
            side_effect=JobOpenValidationError(
                ("location", "requirements.required_skills")
            )
        )

        with patch.object(job_service, "create_job", create_job_mock):
            response = self.client.post(
                "/jobs",
                json={"title": "未完成岗位", "status": "open"},
            )

        self.assert_error(
            response,
            422,
            "JOB_OPEN_VALIDATION_FAILED",
            fields=["location", "requirements.required_skills"],
        )

    def test_create_schema_error_keeps_fastapi_default_422(self) -> None:
        create_job_mock = AsyncMock()

        with patch.object(job_service, "create_job", create_job_mock):
            response = self.client.post("/jobs", json={"title": "", "salary": 20_000})

        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], list)
        create_job_mock.assert_not_awaited()

    def test_list_jobs_passes_optional_strict_status_filter(self) -> None:
        list_jobs_mock = AsyncMock(return_value=[make_job(2, "后端开发工程师")])

        with patch.object(job_service, "list_jobs", list_jobs_mock):
            response = self.client.get("/jobs?status=open")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [2])
        list_jobs_mock.assert_awaited_once_with(self.db, status=JobStatus.OPEN)

    def test_list_jobs_without_filter_passes_none(self) -> None:
        list_jobs_mock = AsyncMock(return_value=[])

        with patch.object(job_service, "list_jobs", list_jobs_mock):
            response = self.client.get("/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        list_jobs_mock.assert_awaited_once_with(self.db, status=None)

    def test_invalid_status_filter_is_rejected_before_service(self) -> None:
        list_jobs_mock = AsyncMock()

        with patch.object(job_service, "list_jobs", list_jobs_mock):
            response = self.client.get("/jobs?status=active")

        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], list)
        list_jobs_mock.assert_not_awaited()

    def test_get_job_returns_job_or_structured_404(self) -> None:
        with patch.object(
            job_service,
            "get_job",
            AsyncMock(return_value=make_job(7, "数据分析师")),
        ):
            response = self.client.get("/jobs/7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 7)

        with patch.object(job_service, "get_job", AsyncMock(return_value=None)):
            response = self.client.get("/jobs/999")
        self.assert_error(response, 404, "JOB_NOT_FOUND")

    def test_update_job_returns_updated_job(self) -> None:
        update_job_mock = AsyncMock(
            return_value=make_job(
                3,
                "高级后端开发工程师",
                department="平台研发部",
            )
        )

        with patch.object(job_service, "update_job", update_job_mock):
            response = self.client.put(
                "/jobs/3",
                json={"title": "高级后端开发工程师", "department": "平台研发部"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "高级后端开发工程师")
        passed_db, passed_job_id, passed_data = update_job_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_job_id, 3)
        self.assertIsInstance(passed_data, JobUpdate)

    def test_empty_update_has_stable_422_code(self) -> None:
        update_job_mock = AsyncMock()

        with patch.object(job_service, "update_job", update_job_mock):
            response = self.client.put("/jobs/3", json={})

        self.assert_error(response, 422, "JOB_UPDATE_EMPTY")
        update_job_mock.assert_not_awaited()

    def test_update_open_validation_error_and_not_found_are_mapped(self) -> None:
        with patch.object(
            job_service,
            "update_job",
            AsyncMock(side_effect=JobOpenValidationError(("location",))),
        ):
            response = self.client.put("/jobs/3", json={"location": None})
        self.assert_error(
            response,
            422,
            "JOB_OPEN_VALIDATION_FAILED",
            fields=["location"],
        )

        with patch.object(job_service, "update_job", AsyncMock(return_value=None)):
            response = self.client.put("/jobs/999", json={"title": "不存在"})
        self.assert_error(response, 404, "JOB_NOT_FOUND")

    def test_all_three_status_actions_return_updated_job(self) -> None:
        cases = (
            ("open", "open_job", "open"),
            ("close", "close_job", "closed"),
            ("reopen", "reopen_job", "open"),
        )
        for path, method_name, expected_status in cases:
            with self.subTest(path=path):
                action_mock = AsyncMock(
                    return_value=make_job(5, "状态岗位", status=expected_status)
                )
                with patch.object(job_service, method_name, action_mock):
                    response = self.client.post(f"/jobs/5/{path}")

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], expected_status)
                action_mock.assert_awaited_once_with(self.db, 5)

    def test_status_action_not_found_invalid_and_open_validation_are_mapped(self) -> None:
        with patch.object(job_service, "open_job", AsyncMock(return_value=None)):
            response = self.client.post("/jobs/999/open")
        self.assert_error(response, 404, "JOB_NOT_FOUND")

        with patch.object(
            job_service,
            "close_job",
            AsyncMock(
                side_effect=InvalidJobStatusTransitionError(
                    action="close",
                    current_status="draft",
                )
            ),
        ):
            response = self.client.post("/jobs/1/close")
        self.assert_error(response, 409, "INVALID_JOB_STATUS_TRANSITION")

        with patch.object(
            job_service,
            "reopen_job",
            AsyncMock(side_effect=JobOpenValidationError(("department",))),
        ):
            response = self.client.post("/jobs/1/reopen")
        self.assert_error(
            response,
            422,
            "JOB_OPEN_VALIDATION_FAILED",
            fields=["department"],
        )

    def test_delete_success_not_found_and_business_conflicts(self) -> None:
        with patch.object(job_service, "delete_job", AsyncMock(return_value=True)):
            response = self.client.delete("/jobs/4")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        with patch.object(job_service, "delete_job", AsyncMock(return_value=False)):
            response = self.client.delete("/jobs/999")
        self.assert_error(response, 404, "JOB_NOT_FOUND")

        with patch.object(
            job_service,
            "delete_job",
            AsyncMock(side_effect=JobMustBeClosedBeforeDeleteError()),
        ):
            response = self.client.delete("/jobs/4")
        self.assert_error(response, 409, "JOB_MUST_BE_CLOSED_BEFORE_DELETE")

        references = JobReferenceCounts(
            candidates=2,
            resumes=1,
            screening_results=2,
            reports=0,
        )
        with patch.object(
            job_service,
            "delete_job",
            AsyncMock(side_effect=JobHasReferencesError(references)),
        ):
            response = self.client.delete("/jobs/4")
        self.assert_error(
            response,
            409,
            "JOB_HAS_REFERENCES",
            references=references.as_dict(),
        )

    def test_unexpected_service_errors_are_sanitized(self) -> None:
        operations = (
            ("post", "/jobs", {"json": {"title": "测试岗位"}}, "create_job"),
            ("get", "/jobs", {}, "list_jobs"),
            ("get", "/jobs/1", {}, "get_job"),
            ("put", "/jobs/1", {"json": {"title": "测试岗位"}}, "update_job"),
            ("post", "/jobs/1/open", {}, "open_job"),
            ("delete", "/jobs/1", {}, "delete_job"),
        )
        for method, path, kwargs, service_method in operations:
            with self.subTest(path=path):
                with patch.object(
                    job_service,
                    service_method,
                    AsyncMock(side_effect=RuntimeError("postgresql://private")),
                ):
                    response = getattr(self.client, method)(path, **kwargs)

                self.assert_error(response, 500, "JOB_OPERATION_FAILED")
                self.assertNotIn("postgresql", response.text)

    def test_openapi_registers_each_job_route_once(self) -> None:
        schema = self.app.openapi()
        expected_methods = {
            "/jobs": {"get", "post"},
            "/jobs/{job_id}": {"get", "put", "delete"},
            "/jobs/{job_id}/open": {"post"},
            "/jobs/{job_id}/close": {"post"},
            "/jobs/{job_id}/reopen": {"post"},
        }

        for path, methods in expected_methods.items():
            self.assertEqual(set(schema["paths"][path]), methods)

        operation_ids = [
            operation["operationId"]
            for path in expected_methods
            for operation in schema["paths"][path].values()
        ]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))

    def test_main_app_mounts_stage6_job_routes_once_under_api_v2(self) -> None:
        from app.main import app as main_app

        schema = main_app.openapi()
        expected_methods = {
            "/api/v2/jobs": {"get", "post"},
            "/api/v2/jobs/{job_id}": {"get", "put", "delete"},
            "/api/v2/jobs/{job_id}/open": {"post"},
            "/api/v2/jobs/{job_id}/close": {"post"},
            "/api/v2/jobs/{job_id}/reopen": {"post"},
        }

        for path, methods in expected_methods.items():
            self.assertEqual(set(schema["paths"][path]), methods)

    def assert_error(
        self,
        response,
        expected_status: int,
        expected_code: str,
        **extra,
    ) -> None:
        self.assertEqual(response.status_code, expected_status)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], expected_code)
        self.assertIsInstance(detail["message"], str)
        for key, value in extra.items():
            self.assertEqual(detail[key], value)
