from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import router
from app.core.database import get_db
from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate
from app.services.rebuilt.job_service import job_service


class CreateJobApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
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
        created_at = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        created_job = Job(
            id=1,
            title="后端开发工程师",
            department="研发部",
            description="负责招聘平台后端开发",
            requirements={"required_skills": ["Python", "PostgreSQL"]},
            status="open",
            created_at=created_at,
            updated_at=created_at,
        )
        create_job_mock = AsyncMock(return_value=created_job)

        with patch.object(job_service, "create_job", create_job_mock):
            response = self.client.post(
                "/jobs",
                json={
                    "title": "后端开发工程师",
                    "department": "研发部",
                    "description": "负责招聘平台后端开发",
                    "requirements": {
                        "required_skills": ["Python", "PostgreSQL"],
                    },
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["title"], "后端开发工程师")
        self.assertEqual(response.json()["status"], "open")

        create_job_mock.assert_awaited_once()
        passed_db, passed_data = create_job_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertIsInstance(passed_data, JobCreate)
        self.assertEqual(passed_data.title, "后端开发工程师")
        self.assertEqual(passed_data.status, "open")

    def test_create_job_rejects_empty_title_before_service_call(self) -> None:
        create_job_mock = AsyncMock()

        with patch.object(job_service, "create_job", create_job_mock):
            response = self.client.post("/jobs", json={"title": ""})

        self.assertEqual(response.status_code, 422)
        create_job_mock.assert_not_awaited()
