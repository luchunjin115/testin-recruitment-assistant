from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.screening_center import router
from app.core.database import get_db
from app.schemas.screening_center import ScreeningCenterApplicationPage


class ScreeningCenterApiTest(TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        self.db = Mock(name="db")

        async def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    @patch("app.api.screening_center.screening_center_service.list_applications", new_callable=AsyncMock)
    def test_filters_and_pagination_are_forwarded(self, mocked: AsyncMock) -> None:
        mocked.return_value = ScreeningCenterApplicationPage(
            items=[], page=2, page_size=30, total=31, total_pages=2
        )
        response = self.client.get(
            "/screening-center/applications?page=2&job_id=7&source=public_apply"
            "&stage=interview&lifecycle=active&processing_pool=exception"
            "&score_min=60&sort=score_desc&view=candidate&keyword=Application%207"
        )
        assert response.status_code == 200
        assert response.json()["total_pages"] == 2
        kwargs = mocked.await_args.kwargs
        assert kwargs["page"] == 2
        assert kwargs["job_id"] == 7
        assert kwargs["source"].value == "public_apply"
        assert kwargs["view"].value == "candidate"
        assert kwargs["keyword"] == "Application 7"
        assert kwargs["recruitment_stage"].value == "interview"
        assert kwargs["processing_pool"].value == "exception"

    def test_invalid_ranges_are_rejected_before_query(self) -> None:
        response = self.client.get(
            "/screening-center/applications?score_min=80&score_max=20"
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "SCREENING_CENTER_SCORE_RANGE_INVALID"

        response = self.client.get("/screening-center/applications?view=unknown")
        assert response.status_code == 422

    @patch("app.api.screening_center.screening_center_service.list_applications", new_callable=AsyncMock)
    def test_internal_failure_is_safe(self, mocked: AsyncMock) -> None:
        mocked.side_effect = RuntimeError("postgresql://secret")
        response = self.client.get("/screening-center/applications")
        assert response.status_code == 500
        assert response.json()["detail"] == {
            "code": "SCREENING_CENTER_QUERY_FAILED",
            "message": "AI 初筛中心读取失败，请稍后重试",
        }
