from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.education import router
from app.core.database import get_db
from app.models.rebuilt.education import Education
from app.schemas.rebuilt.education import EducationCreate, EducationUpdate
from app.services.rebuilt.education_service import education_service


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def make_education(education_id: int, school: str, candidate_id: int = 10) -> Education:
    return Education(
        id=education_id,
        candidate_id=candidate_id,
        school=school,
        degree="本科",
        major="计算机科学",
        start_date="2020-09",
        end_date="2024-06",
        is_985=False,
        is_211=True,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class EducationApiTest(TestCase):
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

    def test_create_education_returns_201(self) -> None:
        create_mock = AsyncMock(return_value=make_education(1, "示例大学"))
        with patch.object(education_service, "create_education", create_mock):
            response = self.client.post(
                "/education?candidate_id=10",
                json={"school": "示例大学", "degree": "本科", "is_211": True},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["school"], "示例大学")
        passed_db, passed_candidate_id, passed_data = create_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_candidate_id, 10)
        self.assertIsInstance(passed_data, EducationCreate)

    def test_create_education_returns_404_for_missing_candidate(self) -> None:
        create_mock = AsyncMock(return_value=None)
        with patch.object(education_service, "create_education", create_mock):
            response = self.client.post(
                "/education?candidate_id=999", json={"school": "示例大学"}
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "候选人不存在"})

    def test_create_validation_happens_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(education_service, "create_education", create_mock):
            invalid_id = self.client.post(
                "/education?candidate_id=0", json={"school": "示例大学"}
            )
            invalid_school = self.client.post(
                "/education?candidate_id=10", json={"school": "x" * 201}
            )

        self.assertEqual(invalid_id.status_code, 422)
        self.assertEqual(invalid_school.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_education_passes_optional_filter(self) -> None:
        list_mock = AsyncMock(return_value=[make_education(2, "大学二")])
        with patch.object(education_service, "list_education", list_mock):
            response = self.client.get("/education?candidate_id=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(self.db, 10)

    def test_list_education_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])
        with patch.object(education_service, "list_education", list_mock):
            response = self.client.get("/education")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        list_mock.assert_awaited_once_with(self.db, None)

    def test_get_education_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_education(7, "示例大学"), None])
        with patch.object(education_service, "get_education", get_mock):
            found = self.client.get("/education/7")
            missing = self.client.get("/education/999")

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()["id"], 7)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "教育经历不存在"})

    def test_update_education_success_and_not_found(self) -> None:
        update_mock = AsyncMock(side_effect=[make_education(3, "新大学"), None])
        with patch.object(education_service, "update_education", update_mock):
            updated = self.client.put("/education/3", json={"school": "新大学"})
            missing = self.client.put("/education/999", json={"school": "新大学"})

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["school"], "新大学")
        self.assertIsInstance(update_mock.await_args_list[0].args[2], EducationUpdate)
        self.assertEqual(missing.status_code, 404)

    def test_delete_education_success_and_not_found(self) -> None:
        delete_mock = AsyncMock(side_effect=[True, False])
        with patch.object(education_service, "delete_education", delete_mock):
            deleted = self.client.delete("/education/4")
            missing = self.client.delete("/education/999")

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "教育经历不存在"})
