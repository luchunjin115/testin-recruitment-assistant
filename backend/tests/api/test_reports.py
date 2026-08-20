from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.reports import router
from app.core.database import get_db
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate
from app.services.report_service import ReportDependencyNotFoundError, report_service


TEST_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def make_report(report_id: int, title: str = "通用报告") -> Report:
    return Report(
        id=report_id,
        candidate_id=10,
        job_id=3,
        title=title,
        content="# 报告\n候选人记录",
        report_type="general",
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

    def test_crud_contract_has_no_screening_dependency(self) -> None:
        create_mock = AsyncMock(return_value=make_report(1))
        with patch.object(report_service, "create_report", create_mock):
            response = self.client.post(
                "/reports",
                json={"candidate_id": 10, "job_id": 3, "content": "报告"},
            )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("screening_id", response.json())
        self.assertIsInstance(create_mock.await_args.args[1], ReportCreate)

        list_mock = AsyncMock(return_value=[make_report(2)])
        with patch.object(report_service, "list_reports", list_mock):
            listed = self.client.get("/reports?candidate_id=10&job_id=3")
        self.assertEqual(listed.status_code, 200)
        list_mock.assert_awaited_once_with(self.db, 10, 3)

    def test_dependency_error_and_update_not_found_are_safe(self) -> None:
        with patch.object(
            report_service,
            "create_report",
            AsyncMock(side_effect=ReportDependencyNotFoundError("candidate")),
        ):
            missing = self.client.post(
                "/reports",
                json={"candidate_id": 10, "job_id": 3, "content": "报告"},
            )
        self.assertEqual(missing.status_code, 404)

        update_mock = AsyncMock(side_effect=[make_report(4, "更新"), None])
        with patch.object(report_service, "update_report", update_mock):
            updated = self.client.put("/reports/4", json={"title": "更新"})
            not_found = self.client.put("/reports/999", json={"title": "更新"})
        self.assertEqual(updated.status_code, 200)
        self.assertIsInstance(update_mock.await_args_list[0].args[2], ReportUpdate)
        self.assertEqual(not_found.status_code, 404)
