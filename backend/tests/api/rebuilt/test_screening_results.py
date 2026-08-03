from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.screening_results import router
from app.core.database import get_db
from app.models.rebuilt.screening_result import ScreeningResult
from app.schemas.rebuilt.screening_result import ScreeningResultCreate, ScreeningResultUpdate
from app.services.rebuilt.screening_result_service import (
    ScreeningResultAlreadyExistsError,
    ScreeningResultDependencyNotFoundError,
    screening_result_service,
)


TEST_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def make_result(result_id: int, score: int = 88) -> ScreeningResult:
    return ScreeningResult(
        id=result_id,
        candidate_id=10,
        job_id=3,
        overall_score=score,
        hard_pass=True,
        skill_score=90,
        experience_score=85,
        project_score=86,
        strengths=["技能匹配"],
        risks=["经验年限待核实"],
        recommendation="推荐",
        reason="综合匹配良好",
        raw_result={"source": "test"},
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class ScreeningResultApiTest(TestCase):
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

    def test_create_returns_201(self) -> None:
        create_mock = AsyncMock(return_value=make_result(1))
        with patch.object(screening_result_service, "create_screening_result", create_mock):
            response = self.client.post(
                "/screening-results",
                json={"candidate_id": 10, "job_id": 3, "overall_score": 88},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["overall_score"], 88)
        self.assertIsInstance(create_mock.await_args.args[1], ScreeningResultCreate)

    def test_create_maps_dependency_and_duplicate_errors(self) -> None:
        create_mock = AsyncMock(
            side_effect=[
                ScreeningResultDependencyNotFoundError("candidate"),
                ScreeningResultDependencyNotFoundError("job"),
                ScreeningResultAlreadyExistsError(),
            ]
        )
        payload = {"candidate_id": 10, "job_id": 3}
        with patch.object(screening_result_service, "create_screening_result", create_mock):
            missing_candidate = self.client.post("/screening-results", json=payload)
            missing_job = self.client.post("/screening-results", json=payload)
            duplicate = self.client.post("/screening-results", json=payload)

        self.assertEqual(missing_candidate.json(), {"detail": "候选人不存在"})
        self.assertEqual(missing_job.json(), {"detail": "岗位不存在"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json(), {"detail": "该候选人与岗位的筛选结果已存在"})

    def test_score_validation_happens_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(screening_result_service, "create_screening_result", create_mock):
            response = self.client.post(
                "/screening-results",
                json={"candidate_id": 10, "job_id": 3, "overall_score": 101},
            )
        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_passes_filters(self) -> None:
        list_mock = AsyncMock(return_value=[make_result(2)])
        with patch.object(screening_result_service, "list_screening_results", list_mock):
            response = self.client.get("/screening-results?candidate_id=10&job_id=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(self.db, 10, 3)

    def test_get_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_result(7), None])
        with patch.object(screening_result_service, "get_screening_result", get_mock):
            found = self.client.get("/screening-results/7")
            missing = self.client.get("/screening-results/999")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "筛选结果不存在"})

    def test_update_success_and_not_found(self) -> None:
        update_mock = AsyncMock(side_effect=[make_result(4, 92), None])
        with patch.object(screening_result_service, "update_screening_result", update_mock):
            updated = self.client.put("/screening-results/4", json={"overall_score": 92})
            missing = self.client.put("/screening-results/999", json={"overall_score": 92})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["overall_score"], 92)
        self.assertIsInstance(update_mock.await_args_list[0].args[2], ScreeningResultUpdate)
        self.assertEqual(missing.status_code, 404)

    def test_delete_success_and_not_found(self) -> None:
        delete_mock = AsyncMock(side_effect=[True, False])
        with patch.object(screening_result_service, "delete_screening_result", delete_mock):
            deleted = self.client.delete("/screening-results/5")
            missing = self.client.delete("/screening-results/999")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing.status_code, 404)
