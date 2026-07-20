from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import router
from app.core.database import get_db
from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate, JobUpdate
from app.services.rebuilt.job_service import job_service


TEST_TIME = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


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
        description=f"{title}岗位描述",
        requirements={"required_skills": ["Python", "PostgreSQL"]},
        status=status,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class JobApiTest(TestCase):
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
        created_job = make_job(1, "后端开发工程师")
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

    def test_list_jobs_returns_200_and_job_list(self) -> None:
        list_jobs_mock = AsyncMock(
            return_value=[
                make_job(2, "后端开发工程师"),
                make_job(1, "测试工程师", department="质量保障部"),
            ],
        )

        with patch.object(job_service, "list_jobs", list_jobs_mock):
            response = self.client.get("/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [2, 1])
        self.assertEqual(response.json()[1]["title"], "测试工程师")
        list_jobs_mock.assert_awaited_once_with(self.db)

    def test_list_jobs_returns_empty_list(self) -> None:
        list_jobs_mock = AsyncMock(return_value=[])

        with patch.object(job_service, "list_jobs", list_jobs_mock):
            response = self.client.get("/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        list_jobs_mock.assert_awaited_once_with(self.db)

    def test_get_job_returns_200_and_job(self) -> None:
        get_job_mock = AsyncMock(return_value=make_job(7, "数据分析师"))

        with patch.object(job_service, "get_job", get_job_mock):
            response = self.client.get("/jobs/7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 7)
        self.assertEqual(response.json()["title"], "数据分析师")
        get_job_mock.assert_awaited_once_with(self.db, 7)

    def test_get_job_returns_404_when_not_found(self) -> None:
        get_job_mock = AsyncMock(return_value=None)

        with patch.object(job_service, "get_job", get_job_mock):
            response = self.client.get("/jobs/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "岗位不存在"})
        get_job_mock.assert_awaited_once_with(self.db, 999)

    def test_update_job_returns_200_and_updated_job(self) -> None:
        update_job_mock = AsyncMock(
            return_value=make_job(
                3,
                "高级后端开发工程师",
                department="平台研发部",
                status="closed",
            ),
        )

        with patch.object(job_service, "update_job", update_job_mock):
            response = self.client.put(
                "/jobs/3",
                json={
                    "title": "高级后端开发工程师",
                    "department": "平台研发部",
                    "status": "closed",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 3)
        self.assertEqual(response.json()["title"], "高级后端开发工程师")
        self.assertEqual(response.json()["status"], "closed")

        update_job_mock.assert_awaited_once()
        passed_db, passed_job_id, passed_data = update_job_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_job_id, 3)
        self.assertIsInstance(passed_data, JobUpdate)
        self.assertEqual(passed_data.department, "平台研发部")

    def test_update_job_returns_404_when_not_found(self) -> None:
        update_job_mock = AsyncMock(return_value=None)

        with patch.object(job_service, "update_job", update_job_mock):
            response = self.client.put(
                "/jobs/999",
                json={"title": "不存在的岗位"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "岗位不存在"})
        update_job_mock.assert_awaited_once()

    def test_update_job_rejects_empty_title_before_service_call(self) -> None:
        update_job_mock = AsyncMock()

        with patch.object(job_service, "update_job", update_job_mock):
            response = self.client.put("/jobs/3", json={"title": ""})

        self.assertEqual(response.status_code, 422)
        update_job_mock.assert_not_awaited()

    def test_delete_job_returns_204_and_empty_body(self) -> None:
        delete_job_mock = AsyncMock(return_value=True)

        with patch.object(job_service, "delete_job", delete_job_mock):
            response = self.client.delete("/jobs/4")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        delete_job_mock.assert_awaited_once_with(self.db, 4)

    def test_delete_job_returns_404_when_not_found(self) -> None:
        delete_job_mock = AsyncMock(return_value=False)

        with patch.object(job_service, "delete_job", delete_job_mock):
            response = self.client.delete("/jobs/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "岗位不存在"})
        delete_job_mock.assert_awaited_once_with(self.db, 999)
