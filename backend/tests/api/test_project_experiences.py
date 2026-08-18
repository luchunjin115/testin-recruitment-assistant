from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.project_experiences import router
from app.core.database import get_db
from app.models.project_experience import ProjectExperience
from app.schemas.project_experience import (
    ProjectExperienceCreate,
    ProjectExperienceUpdate,
)
from app.services.project_experience_service import project_experience_service


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def make_experience(experience_id: int, project_name: str) -> ProjectExperience:
    return ProjectExperience(
        id=experience_id,
        candidate_id=10,
        project_name=project_name,
        role="后端开发",
        start_date="2025-01",
        end_date="2025-06",
        description="招聘平台重构",
        tech_stack=["FastAPI", "PostgreSQL"],
        achievements="接口响应时间降低 30%",
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class ProjectExperienceApiTest(TestCase):
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

    def test_create_success_and_missing_candidate(self) -> None:
        create_mock = AsyncMock(side_effect=[make_experience(1, "招聘助手"), None])
        with patch.object(project_experience_service, "create_project_experience", create_mock):
            created = self.client.post(
                "/project-experiences?candidate_id=10",
                json={"project_name": "招聘助手", "tech_stack": ["FastAPI"]},
            )
            missing = self.client.post(
                "/project-experiences?candidate_id=999",
                json={"project_name": "招聘助手"},
            )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["achievements"], "接口响应时间降低 30%")
        self.assertIsInstance(create_mock.await_args_list[0].args[2], ProjectExperienceCreate)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "候选人不存在"})

    def test_create_validation_happens_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(project_experience_service, "create_project_experience", create_mock):
            invalid_id = self.client.post(
                "/project-experiences?candidate_id=0", json={"project_name": "项目"}
            )
            invalid_name = self.client.post(
                "/project-experiences?candidate_id=10",
                json={"project_name": "x" * 201},
            )

        self.assertEqual(invalid_id.status_code, 422)
        self.assertEqual(invalid_name.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_passes_optional_candidate_filter(self) -> None:
        list_mock = AsyncMock(return_value=[make_experience(2, "招聘助手")])
        with patch.object(project_experience_service, "list_project_experiences", list_mock):
            response = self.client.get("/project-experiences?candidate_id=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(self.db, 10)

    def test_list_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])
        with patch.object(project_experience_service, "list_project_experiences", list_mock):
            response = self.client.get("/project-experiences")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_experience(7, "招聘助手"), None])
        with patch.object(project_experience_service, "get_project_experience", get_mock):
            found = self.client.get("/project-experiences/7")
            missing = self.client.get("/project-experiences/999")

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()["tech_stack"], ["FastAPI", "PostgreSQL"])
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "项目经历不存在"})

    def test_update_success_and_not_found(self) -> None:
        updated_record = make_experience(3, "招聘助手")
        updated_record.role = "项目负责人"
        update_mock = AsyncMock(side_effect=[updated_record, None])
        with patch.object(project_experience_service, "update_project_experience", update_mock):
            updated = self.client.put(
                "/project-experiences/3", json={"role": "项目负责人"}
            )
            missing = self.client.put(
                "/project-experiences/999", json={"role": "项目负责人"}
            )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "项目负责人")
        self.assertIsInstance(update_mock.await_args_list[0].args[2], ProjectExperienceUpdate)
        self.assertEqual(missing.status_code, 404)

    def test_delete_success_and_not_found(self) -> None:
        delete_mock = AsyncMock(side_effect=[True, False])
        with patch.object(project_experience_service, "delete_project_experience", delete_mock):
            deleted = self.client.delete("/project-experiences/4")
            missing = self.client.delete("/project-experiences/999")

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "项目经历不存在"})
