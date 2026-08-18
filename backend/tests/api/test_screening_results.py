from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.screening_results import router
from app.core.database import get_db
from app.models.screening_result import ScreeningResult
from app.services.screening_result_service import screening_result_service


TEST_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def make_application_result(result_id: int = 8) -> ScreeningResult:
    return ScreeningResult(
        id=result_id,
        candidate_id=10,
        job_id=3,
        application_id=20,
        resume_id=4,
        attempt_number=2,
        execution_status="completed",
        input_fingerprint="a" * 64,
        overall_score=86,
        hard_pass=True,
        recommendation="strong_recommend",
        evidence_coverage_rate=Decimal("0.9000"),
        strengths=["项目证据充分"],
        risks=[],
        hard_requirement_checks=[{"criterion": "work_years"}],
        dimension_scores={"must_have_requirements": {"score_percentage": 90}},
        pending_questions=[],
        resume_evidence=[{"source": "resume_text", "quote": "Python"}],
        job_evidence=[{"requirement": "Python"}],
        candidate_input_snapshot={"application_ref": "application-20"},
        resume_snapshot={"resume_id": 4},
        job_requirements_snapshot={"schema_version": "1.0"},
        rubric_snapshot={"version": 2},
        prompt_version="screening_evaluation_v3",
        force_rerun=False,
        is_outdated=False,
        started_at=TEST_TIME,
        finished_at=TEST_TIME,
        duration_ms=1500,
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

    def test_list_only_returns_application_screening_contract(self) -> None:
        list_mock = AsyncMock(return_value=[make_application_result()])
        with patch.object(screening_result_service, "list_screening_results", list_mock):
            response = self.client.get("/screening-results?candidate_id=10&job_id=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["application_id"], 20)
        self.assertEqual(response.json()[0]["resume_id"], 4)
        list_mock.assert_awaited_once_with(self.db, 10, 3)

    def test_detail_returns_application_screening_contract(self) -> None:
        get_mock = AsyncMock(return_value=make_application_result())
        with patch.object(screening_result_service, "get_screening_result", get_mock):
            response = self.client.get("/screening-results/8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["application_id"], 20)
        self.assertEqual(response.json()["resume_snapshot"], {"resume_id": 4})
        get_mock.assert_awaited_once_with(self.db, 8)

    def test_detail_returns_404_when_result_is_not_available(self) -> None:
        get_mock = AsyncMock(return_value=None)
        with patch.object(screening_result_service, "get_screening_result", get_mock):
            response = self.client.get("/screening-results/999")

        self.assertEqual(response.status_code, 404)

    def test_generic_mutation_routes_are_retired(self) -> None:
        self.assertEqual(self.client.post("/screening-results", json={}).status_code, 405)
        self.assertEqual(self.client.put("/screening-results/8", json={}).status_code, 405)
        self.assertEqual(self.client.delete("/screening-results/8").status_code, 405)
