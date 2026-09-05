from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.recruitment_statistics import router
from app.core.database import get_db
from app.schemas.recruitment_statistics import (
    RecruitmentDurationKey,
    RecruitmentDurationMetric,
    RecruitmentFunnelKey,
    RecruitmentFunnelStep,
    RecruitmentStatisticsCohort,
    RecruitmentStatisticsRead,
    RecruitmentTodoSnapshot,
)
from app.services.recruitment_statistics_service import recruitment_statistics_service


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def statistics_response() -> RecruitmentStatisticsRead:
    return RecruitmentStatisticsRead(
        cohort=RecruitmentStatisticsCohort(
            job_id=7,
            applied_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
            applied_to=datetime(2026, 9, 30, tzinfo=timezone.utc),
        ),
        funnel=[
            RecruitmentFunnelStep(
                key=key,
                count=2,
                conversion_rate=None if index == 0 else 100.0,
            )
            for index, key in enumerate(RecruitmentFunnelKey)
        ],
        durations=[
            RecruitmentDurationMetric(key=key, average_hours=12.5, sample_count=2)
            for key in RecruitmentDurationKey
        ],
        todos=RecruitmentTodoSnapshot(
            scheduled_interviews=1,
            pending_interview_decisions=1,
            next_round_not_scheduled=1,
            draft_offers=1,
            sent_offers=1,
            accepted_offers=1,
            admitted_applications=1,
            total=7,
        ),
        generated_at=NOW,
    )


class RecruitmentStatisticsApiTest(TestCase):
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

    def test_filters_are_forwarded_and_response_contains_no_sensitive_fields(self) -> None:
        with patch.object(
            recruitment_statistics_service,
            "get_statistics",
            AsyncMock(return_value=statistics_response()),
        ) as mocked:
            response = self.client.get(
                "/recruitment-statistics?job_id=7"
                "&applied_from=2026-09-01T00:00:00Z"
                "&applied_to=2026-09-30T00:00:00Z"
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["funnel"][0]["key"], "applications")
        self.assertEqual(body["todos"]["total"], 7)
        self.assertNotIn("salary", response.text.lower())
        kwargs = mocked.await_args.kwargs
        self.assertEqual(kwargs["job_id"], 7)
        self.assertEqual(kwargs["applied_from"].tzinfo, timezone.utc)

    def test_invalid_or_naive_date_ranges_are_rejected_before_query(self) -> None:
        invalid_range = self.client.get(
            "/recruitment-statistics?applied_from=2026-09-03T00:00:00Z"
            "&applied_to=2026-09-01T00:00:00Z"
        )
        self.assertEqual(invalid_range.status_code, 422)
        self.assertEqual(
            invalid_range.json()["detail"]["code"],
            "RECRUITMENT_STATISTICS_DATE_RANGE_INVALID",
        )

        naive = self.client.get(
            "/recruitment-statistics?applied_from=2026-09-01T00:00:00"
        )
        self.assertEqual(naive.status_code, 422)

    def test_query_failure_is_safe(self) -> None:
        with patch.object(
            recruitment_statistics_service,
            "get_statistics",
            AsyncMock(side_effect=RuntimeError("salary=987654321.12")),
        ):
            response = self.client.get("/recruitment-statistics")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "RECRUITMENT_STATISTICS_QUERY_FAILED",
                "message": "招聘流程统计读取失败，请稍后重试",
            },
        )
        self.assertNotIn("987654321.12", response.text)
