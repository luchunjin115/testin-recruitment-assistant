from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.jobs import create_job, install_job_exception_handlers, router
from app.schemas.job import JobCreate
from app.core.database import get_db
from app.services.job_service import JobOpenValidationError, job_service


TEST_TIME = datetime(2026, 8, 21, tzinfo=timezone.utc)
FIVE_FIELDS = {
    "job_background": "建设 AI 应用平台",
    "job_responsibilities": "负责 AI 应用设计与交付",
    "candidate_requirements": "具备后端开发经验",
    "preferred_qualifications": "有 RAG 项目经验",
    "public_notes": "候选人可提前准备项目介绍",
}


def make_job():
    return SimpleNamespace(
        id=1,
        title="AI 应用工程师",
        department="研发部",
        location="长沙",
        employment_type="full_time",
        headcount=2,
        **FIVE_FIELDS,
        status="draft",
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
        # 旧响应字段只为使当前 API 完成序列化，再由断言准确指出合同错误。
        description="旧岗位描述",
        requirements={
            "schema_version": "1.0",
            "responsibilities": ["旧职责"],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "minimum_work_years": 1,
            "education_requirement": "bachelor_or_above",
            "required_experiences": [],
            "preferred_experiences": [],
            "keywords": [],
            "additional_requirements": [],
        },
    )


class JobFiveSectionApiContractTest(TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        install_job_exception_handlers(app)
        app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.app = app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_create_accepts_five_sections_and_response_contains_only_new_jd_fields(self) -> None:
        create_mock = AsyncMock(return_value=make_job())
        with patch.object(job_service, "create_job", create_mock):
            response = self.client.post(
                "/jobs",
                json={
                    "title": "AI 应用工程师",
                    "department": "研发部",
                    "location": "长沙",
                    "employment_type": "full_time",
                    "headcount": 2,
                    **FIVE_FIELDS,
                },
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "id",
                "title",
                "department",
                "location",
                "employment_type",
                "headcount",
                *FIVE_FIELDS,
                "status",
                "created_at",
                "updated_at",
            },
        )
        self.assertFalse(
            {"description", "requirements", "legacy_requirements"} & set(body)
        )
        create_mock.assert_awaited_once()

    def test_old_and_unknown_fields_are_rejected_before_service(self) -> None:
        old_requirements = make_job().requirements
        for field, value in (
            ("description", "旧描述"),
            ("requirements", old_requirements),
            ("legacy_requirements", {"summary": "旧要求"}),
            ("unknown_field", True),
        ):
            with self.subTest(field=field):
                create_mock = AsyncMock(return_value=make_job())
                with patch.object(job_service, "create_job", create_mock):
                    response = self.client.post(
                        "/jobs",
                        json={"title": "拒绝旧字段", field: value},
                    )

                self.assertEqual(response.status_code, 422)
                create_mock.assert_not_awaited()


class JobFiveSectionApiErrorMappingContractTest(IsolatedAsyncioTestCase):
    async def test_open_validation_error_exposes_new_field_locations(self) -> None:
        create_mock = AsyncMock(
            side_effect=JobOpenValidationError(
                ("job_responsibilities", "candidate_requirements")
            )
        )
        with patch.object(job_service, "create_job", create_mock):
            with self.assertRaises(HTTPException) as raised:
                await create_job(
                    JobCreate.model_construct(
                        title="不完整岗位",
                        status="open",
                        **FIVE_FIELDS,
                    ),
                    Mock(name="test_database_session"),
                )

        response = raised.exception
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.detail["fields"],
            ["job_responsibilities", "candidate_requirements"],
        )
