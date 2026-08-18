from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.reports import router
from app.core.database import get_db
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate
from app.services.report_service import (
    ReportDependencyNotFoundError,
    ReportScreeningMismatchError,
    report_service,
)


TEST_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def make_report(report_id: int, title: str = "初筛报告") -> Report:
    return Report(
        id=report_id,
        candidate_id=10,
        job_id=3,
        screening_id=5,
        title=title,
        content="# 初筛报告\n候选人匹配良好",
        report_type="screening",
        format="markdown",
        report_metadata={"version": 1},
        generated_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


class ReportApiTest(TestCase):
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
        create_mock = AsyncMock(return_value=make_report(1))
        with patch.object(report_service, "create_report", create_mock):
            response = self.client.post(
                "/reports",
                json={
                    "candidate_id": 10,
                    "job_id": 3,
                    "screening_id": 5,
                    "title": "初筛报告",
                    "content": "# 初筛报告",
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["format"], "markdown")
        self.assertIsInstance(create_mock.await_args.args[1], ReportCreate)

    def test_create_maps_dependency_and_mismatch_errors(self) -> None:
        create_mock = AsyncMock(
            side_effect=[
                ReportDependencyNotFoundError("screening_result"),
                ReportScreeningMismatchError(),
            ]
        )
        payload = {"candidate_id": 10, "job_id": 3, "content": "报告"}
        with patch.object(report_service, "create_report", create_mock):
            missing = self.client.post("/reports", json=payload)
            mismatch = self.client.post("/reports", json=payload)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "筛选结果不存在"})
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.json(), {"detail": "筛选结果与报告的候选人或岗位不一致"})

    def test_empty_content_is_rejected_before_service(self) -> None:
        create_mock = AsyncMock()
        with patch.object(report_service, "create_report", create_mock):
            response = self.client.post(
                "/reports", json={"candidate_id": 10, "job_id": 3, "content": ""}
            )
        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_passes_filters(self) -> None:
        list_mock = AsyncMock(return_value=[make_report(2)])
        with patch.object(report_service, "list_reports", list_mock):
            response = self.client.get("/reports?candidate_id=10&job_id=3&screening_id=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 2)
        list_mock.assert_awaited_once_with(self.db, 10, 3, 5)

    def test_get_success_and_not_found(self) -> None:
        get_mock = AsyncMock(side_effect=[make_report(7), None])
        with patch.object(report_service, "get_report", get_mock):
            found = self.client.get("/reports/7")
            missing = self.client.get("/reports/999")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "报告不存在"})

    def test_update_success_dependency_error_and_not_found(self) -> None:
        update_mock = AsyncMock(
            side_effect=[
                make_report(4, "更新后的报告"),
                ReportDependencyNotFoundError("screening_result"),
                None,
            ]
        )
        with patch.object(report_service, "update_report", update_mock):
            updated = self.client.put("/reports/4", json={"title": "更新后的报告"})
            missing_screening = self.client.put("/reports/4", json={"screening_id": 999})
            missing_report = self.client.put("/reports/999", json={"title": "更新"})
        self.assertEqual(updated.status_code, 200)
        self.assertIsInstance(update_mock.await_args_list[0].args[2], ReportUpdate)
        self.assertEqual(missing_screening.status_code, 404)
        self.assertEqual(missing_report.status_code, 404)

    def test_delete_success_and_not_found(self) -> None:
        delete_mock = AsyncMock(side_effect=[True, False])
        with patch.object(report_service, "delete_report", delete_mock):
            deleted = self.client.delete("/reports/6")
            missing = self.client.delete("/reports/999")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing.status_code, 404)
