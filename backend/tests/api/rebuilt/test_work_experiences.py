from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.work_experiences import router
from app.core.database import get_db
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.work_experience import WorkExperienceCreate, WorkExperienceUpdate
from app.services.rebuilt.work_experience_service import work_experience_service


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def make_experience(experience_id: int, company: str) -> WorkExperience:
    return WorkExperience(
        id=experience_id,
        candidate_id=10,
        company=company,
        title="后端工程师",
        start_date="2024-01",
        end_date="至今",
        description="负责后端服务",
        tech_stack=["Python", "PostgreSQL"],
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class WorkExperienceApiTest(TestCase):
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
        create_mock = AsyncMock(side_effect=[make_experience(1, "示例科技"), None])
        with patch.object(work_experience_service, "create_work_experience", create_mock):
            created = self.client.post(
                "/work-experiences?candidate_id=10",
                json={"company": "示例科技", "tech_stack": ["Python"]},
            )
            missing = self.client.post(
                "/work-experiences?candidate_id=999", json={"company": "示例科技"}
            )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["tech_stack"], ["Python", "PostgreSQL"])
        self.assertIsInstance(create_mock.await_args_list[0].args[2], WorkExperienceCreate)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "候选人不存在"})

    def test_create_validation_happens_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(work_experience_service, "create_work_experience", create_mock):
            invalid_id = self.client.post(
                "/work-experiences?candidate_id=0", json={"company": "示例科技"}
            )
            invalid_company = self.client.post(
                "/work-experiences?candidate_id=10", json={"company": "x" * 201}
            )

        self.assertEqual(invalid_id.status_code, 422)
        self.assertEqual(invalid_company.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_passes_optional_candidate_filter(self) -> None:
        list_mock = AsyncMock(return_value=[make_experience(2, "示例科技")])
        with patch.object(work_experience_service, "list_work_experiences", list_mock):
            response = self.client.get("/work-experiences?candidate_id=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(self.db, 10)

    def test_list_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])
        with patch.object(work_experience_service, "list_work_experiences", list_mock):
            response = self.client.get("/work-experiences")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        list_mock.assert_awaited_once_with(self.db, None)

    def test_get_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_experience(7, "示例科技"), None])
        with patch.object(work_experience_service, "get_work_experience", get_mock):
            found = self.client.get("/work-experiences/7")
            missing = self.client.get("/work-experiences/999")

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()["id"], 7)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "工作经历不存在"})

    def test_update_success_and_not_found(self) -> None:
        updated_record = make_experience(3, "示例科技")
        updated_record.title = "高级后端工程师"
        update_mock = AsyncMock(side_effect=[updated_record, None])
        with patch.object(work_experience_service, "update_work_experience", update_mock):
            updated = self.client.put(
                "/work-experiences/3", json={"title": "高级后端工程师"}
            )
            missing = self.client.put(
                "/work-experiences/999", json={"title": "高级后端工程师"}
            )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "高级后端工程师")
        self.assertIsInstance(update_mock.await_args_list[0].args[2], WorkExperienceUpdate)
        self.assertEqual(missing.status_code, 404)

    def test_delete_success_and_not_found(self) -> None:
        delete_mock = AsyncMock(side_effect=[True, False])
        with patch.object(work_experience_service, "delete_work_experience", delete_mock):
            deleted = self.client.delete("/work-experiences/4")
            missing = self.client.delete("/work-experiences/999")

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "工作经历不存在"})
