from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.interviews import install_interview_exception_handlers, router
from app.core.database import get_db
from app.models.interview_record import InterviewRecord
from app.schemas.recruitment_timeline import RecruitmentTimelineItem
from app.services.interview_service import (
    ApplicationNotFoundError,
    ApplicationNotReadyForInterviewError,
    ApplicationPipelineEndedError,
    HRActionReasonRequiredError,
    InterviewNotFoundError,
    InterviewRoundConflictError,
    InterviewTransitionInvalidError,
    InterviewVersionConflictError,
    interview_service,
)
from app.services.recruitment_timeline_service import recruitment_timeline_service


TEST_TIME = datetime(2026, 9, 3, 2, 0, tzinfo=timezone.utc)


def make_interview() -> InterviewRecord:
    return InterviewRecord(
        id=11,
        application_id=1,
        round_number=1,
        interview_type="video",
        status="scheduled",
        scheduled_start_at=TEST_TIME,
        duration_minutes=60,
        timezone="Asia/Shanghai",
        interviewer_names=["面试官甲"],
        location=None,
        meeting_link="https://meet.example.test/round-1",
        schedule_note=None,
        decision="pending",
        feedback_summary=None,
        strengths=[],
        concerns=[],
        follow_up_questions=[],
        feedback_submitted_by_label=None,
        feedback_submitted_at=None,
        version=1,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def schedule_payload() -> dict:
    return {
        "round_number": 1,
        "interview_type": "video",
        "scheduled_start_at": TEST_TIME.isoformat(),
        "duration_minutes": 60,
        "timezone": "Asia/Shanghai",
        "interviewer_names": ["面试官甲"],
        "meeting_link": "https://meet.example.test/round-1",
    }


class InterviewApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_interview_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_interview_routes_use_strict_schemas_and_services(self) -> None:
        interview = make_interview()
        cases = (
            (
                "POST",
                "/applications/1/interviews",
                "schedule_interview",
                schedule_payload(),
            ),
            (
                "PUT",
                "/interviews/11/schedule",
                "reschedule_interview",
                {**schedule_payload(), "expected_version": 1, "round_number": None},
            ),
            (
                "POST",
                "/interviews/11/cancel",
                "cancel_interview",
                {
                    "expected_version": 1,
                    "reason_code": "interview_canceled",
                    "reason_detail": "候选人申请改期",
                    "confirmed": True,
                },
            ),
            (
                "POST",
                "/interviews/11/no-show",
                "mark_no_show",
                {
                    "expected_version": 1,
                    "reason_code": "interview_no_show",
                    "reason_detail": "约定时间未到场",
                    "confirmed": True,
                },
            ),
            (
                "POST",
                "/interviews/11/feedback",
                "submit_feedback",
                {
                    "expected_version": 1,
                    "feedback_summary": "完成面试，等待进一步决定。",
                    "decision": "pending",
                    "reason_code": "interview_round_completed",
                },
            ),
            (
                "PUT",
                "/interviews/11/feedback",
                "update_feedback",
                {
                    "expected_version": 1,
                    "feedback_summary": "修正后的人工面试反馈。",
                    "decision": "pending",
                    "reason_code": "stage9_correction",
                    "correction_reason": "修正文字记录",
                    "confirmed": True,
                },
            ),
        )
        for method, path, service_method, payload in cases:
            with self.subTest(path=path):
                payload = {key: value for key, value in payload.items() if value is not None}
                service_mock = AsyncMock(return_value=interview)
                with patch.object(interview_service, service_method, service_mock):
                    response = self.client.request(method, path, json=payload)
                self.assertIn(response.status_code, {200, 201})
                self.assertEqual(response.json()["id"], 11)
                service_mock.assert_awaited_once()

    def test_list_and_timeline_routes_return_safe_read_contracts(self) -> None:
        with patch.object(
            interview_service,
            "list_interviews",
            AsyncMock(return_value=[make_interview()]),
        ) as list_mock:
            response = self.client.get("/applications/1/interviews")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["round_number"], 1)
        self.assertNotIn("meeting_link", response.json()[0])
        self.assertNotIn("schedule_note", response.json()[0])
        list_mock.assert_awaited_once_with(self.db, 1)

        item = RecruitmentTimelineItem(
            source="activity_log",
            source_id=2,
            event_type="interview_rescheduled",
            application_id=1,
            interview_record_id=11,
            from_interview_status="scheduled",
            to_interview_status="scheduled",
            from_version=1,
            to_version=2,
            reason_code="interview_rescheduled",
            actor_type="hr",
            actor_label="本地 HR（未认证）",
            occurred_at=TEST_TIME,
        )
        with patch.object(
            recruitment_timeline_service,
            "list_timeline",
            AsyncMock(return_value=[item]),
        ) as timeline_mock:
            response = self.client.get("/applications/1/timeline")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("detail", response.json()[0])
        timeline_mock.assert_awaited_once_with(self.db, 1)

    def test_stable_error_codes_do_not_leak_private_messages(self) -> None:
        cases = (
            (ApplicationNotFoundError("private"), 404, "APPLICATION_NOT_FOUND"),
            (InterviewNotFoundError("private"), 404, "INTERVIEW_NOT_FOUND"),
            (
                ApplicationNotReadyForInterviewError("private"),
                409,
                "APPLICATION_NOT_READY_FOR_INTERVIEW",
            ),
            (
                ApplicationPipelineEndedError("private"),
                409,
                "APPLICATION_PIPELINE_ENDED",
            ),
            (InterviewRoundConflictError("private"), 409, "INTERVIEW_ROUND_CONFLICT"),
            (
                InterviewTransitionInvalidError("private"),
                409,
                "INTERVIEW_TRANSITION_INVALID",
            ),
            (
                InterviewVersionConflictError("private"),
                409,
                "INTERVIEW_VERSION_CONFLICT",
            ),
            (
                HRActionReasonRequiredError("private"),
                422,
                "HR_ACTION_REASON_REQUIRED",
            ),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(code=expected_code):
                with patch.object(
                    interview_service,
                    "schedule_interview",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/applications/1/interviews",
                        json=schedule_payload(),
                    )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertNotIn("private", response.text)

    def test_confirmation_and_reason_failures_have_stable_422_codes(self) -> None:
        service_mock = AsyncMock()
        with patch.object(interview_service, "cancel_interview", service_mock):
            response = self.client.post(
                "/interviews/11/cancel",
                json={
                    "expected_version": 1,
                    "reason_code": "interview_canceled",
                    "reason_detail": "需要改期",
                    "confirmed": False,
                },
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "HR_ACTION_CONFIRMATION_REQUIRED",
        )
        service_mock.assert_not_awaited()

        response = self.client.post(
            "/interviews/11/no-show",
            json={
                "expected_version": 1,
                "reason_code": "interview_no_show",
                "confirmed": True,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "HR_ACTION_REASON_REQUIRED",
        )

    def test_unexpected_failure_is_sanitized(self) -> None:
        with patch.object(
            interview_service,
            "schedule_interview",
            AsyncMock(side_effect=RuntimeError("postgresql://secret")),
        ):
            response = self.client.post(
                "/applications/1/interviews",
                json=schedule_payload(),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RECRUITMENT_PIPELINE_OPERATION_FAILED",
        )
        self.assertNotIn("secret", response.text)

    def test_openapi_registers_each_9b_route_once(self) -> None:
        expected = {
            ("GET", "/applications/{application_id}/interviews"),
            ("POST", "/applications/{application_id}/interviews"),
            ("PUT", "/interviews/{interview_id}/schedule"),
            ("POST", "/interviews/{interview_id}/cancel"),
            ("POST", "/interviews/{interview_id}/no-show"),
            ("POST", "/interviews/{interview_id}/feedback"),
            ("PUT", "/interviews/{interview_id}/feedback"),
            ("GET", "/applications/{application_id}/timeline"),
        }
        actual = [
            (method, route.path)
            for route in self.app.routes
            for method in getattr(route, "methods", set())
            if (method, route.path) in expected
        ]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
