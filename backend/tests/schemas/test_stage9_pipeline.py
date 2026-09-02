from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase

from pydantic import ValidationError

from app.schemas import (
    ApplicationLifecycleStatus,
    ApplicationRead,
    FinalOutcome,
    HRDecision,
    InterviewDecision,
    InterviewFeedbackSubmitRequest,
    InterviewRecordCreate,
    InterviewScheduleCreate,
    OfferRecordCreate,
    OfferStatus,
    RecruitmentStage,
    StageHistoryCreate,
)


UTC_NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


class Stage9ApplicationSchemaTest(TestCase):
    def test_status_dimensions_are_independent_and_complete(self) -> None:
        self.assertEqual(
            {item.value for item in RecruitmentStage},
            {
                "applied",
                "hr_review",
                "screening_passed",
                "backup",
                "rejected",
                "interview",
                "offer",
                "offer_accepted",
                "admitted",
                "hired",
            },
        )
        self.assertEqual(
            {item.value for item in FinalOutcome},
            {
                "screening_rejected",
                "interview_rejected",
                "interview_no_show",
                "offer_declined",
                "offer_withdrawn",
                "offer_expired",
                "candidate_withdrew",
                "company_canceled",
                "hired",
            },
        )
        self.assertIsNot(RecruitmentStage, HRDecision)
        self.assertIsNot(RecruitmentStage, ApplicationLifecycleStatus)
        self.assertIsNot(FinalOutcome, RecruitmentStage)
        self.assertEqual(RecruitmentStage.OFFER_ACCEPTED.value, "offer_accepted")
        self.assertEqual(RecruitmentStage.ADMITTED.value, "admitted")
        self.assertEqual(RecruitmentStage.HIRED.value, "hired")

    def test_application_read_exposes_nullable_final_outcome(self) -> None:
        application = ApplicationRead(
            id=1,
            candidate_id=2,
            job_id=3,
            current_resume_id=4,
            source="hr_screening",
            lifecycle_status="ended",
            recruitment_stage="offer",
            hr_decision="passed",
            final_outcome="offer_declined",
            applied_at=UTC_NOW,
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        self.assertIs(application.final_outcome, FinalOutcome.OFFER_DECLINED)


class Stage9StageHistorySchemaTest(TestCase):
    def test_history_supports_lifecycle_outcome_and_source_records(self) -> None:
        history = StageHistoryCreate.model_validate(
            {
                "application_id": 1,
                "interview_record_id": 2,
                "from_lifecycle_status": "active",
                "to_lifecycle_status": "ended",
                "from_recruitment_stage": "interview",
                "to_recruitment_stage": "rejected",
                "from_hr_decision": "passed",
                "to_hr_decision": "passed",
                "from_final_outcome": None,
                "to_final_outcome": "interview_rejected",
                "reason_code": "interview_rejected",
                "actor_type": "hr",
                "actor_label": "本地 HR（未认证）",
            }
        )
        self.assertEqual(history.interview_record_id, 2)
        self.assertIs(history.to_final_outcome, FinalOutcome.INTERVIEW_REJECTED)

    def test_old_history_rows_remain_readable_with_nullable_stage9_fields(self) -> None:
        history = StageHistoryCreate.model_validate(
            {
                "application_id": 1,
                "from_recruitment_stage": None,
                "to_recruitment_stage": "applied",
                "from_hr_decision": None,
                "to_hr_decision": "pending",
                "reason_code": "application_created",
                "actor_type": "system",
                "actor_label": "系统",
            }
        )
        self.assertIsNone(history.to_lifecycle_status)
        self.assertIsNone(history.to_final_outcome)
        self.assertIsNone(history.offer_record_id)


class InterviewRecordSchemaTest(TestCase):
    def valid_payload(self) -> dict:
        return {
            "application_id": 1,
            "round_number": 1,
            "interview_type": "video",
            "status": "scheduled",
            "scheduled_start_at": UTC_NOW,
            "duration_minutes": 60,
            "timezone": "Asia/Shanghai",
            "interviewer_names": ["面试官甲"],
            "meeting_link": "https://meet.example.test/round-1",
        }

    def test_schedule_contract_and_bounds_are_strict(self) -> None:
        interview = InterviewRecordCreate.model_validate(self.valid_payload())
        self.assertEqual(interview.round_number, 1)
        self.assertEqual(interview.decision, InterviewDecision.PENDING)

        for field, value in (
            ("round_number", 0),
            ("round_number", "1"),
            ("duration_minutes", 14),
            ("duration_minutes", 481),
            ("interviewer_names", []),
            ("timezone", "not-a-zone"),
        ):
            payload = self.valid_payload()
            payload[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(
                ValidationError
            ):
                InterviewRecordCreate.model_validate(payload)

    def test_non_pending_decision_requires_completed_feedback(self) -> None:
        payload = self.valid_payload()
        payload["decision"] = "proceed_offer"
        with self.assertRaises(ValidationError):
            InterviewRecordCreate.model_validate(payload)

        payload.update(
            {
                "status": "completed",
                "feedback_summary": "技术证据完整，可进入 Offer。",
                "strengths": ["能清楚解释事务边界"],
                "feedback_submitted_by_label": "本地 HR（未认证）",
                "feedback_submitted_at": UTC_NOW,
            }
        )
        interview = InterviewRecordCreate.model_validate(payload)
        self.assertEqual(interview.decision, InterviewDecision.PROCEED_OFFER)

    def test_extra_fields_are_rejected(self) -> None:
        payload = self.valid_payload()
        payload["salary"] = 100
        with self.assertRaises(ValidationError):
            InterviewRecordCreate.model_validate(payload)

    def test_9b_action_schemas_validate_real_timezone_version_and_reason(self) -> None:
        schedule = {
            "round_number": 1,
            "interview_type": "video",
            "scheduled_start_at": UTC_NOW,
            "duration_minutes": 60,
            "timezone": "Asia/Shanghai",
            "interviewer_names": ["面试官甲"],
        }
        self.assertEqual(
            InterviewScheduleCreate.model_validate(schedule).timezone,
            "Asia/Shanghai",
        )
        invalid_timezone = {**schedule, "timezone": "Asia/Definitely_Not_A_Zone"}
        with self.assertRaises(ValidationError):
            InterviewScheduleCreate.model_validate(invalid_timezone)

        feedback = InterviewFeedbackSubmitRequest.model_validate(
            {
                "expected_version": 1,
                "feedback_summary": "人工完成本轮面试。",
                "decision": "pending",
                "reason_code": "interview_round_completed",
            }
        )
        self.assertEqual(feedback.expected_version, 1)
        for field, value in (("expected_version", "1"), ("confirmed", 1)):
            payload = feedback.model_dump()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                InterviewFeedbackSubmitRequest.model_validate(payload)


class OfferRecordSchemaTest(TestCase):
    def valid_payload(self) -> dict:
        return {
            "application_id": 1,
            "version_number": 1,
            "status": "draft",
            "position_title": "后端工程师",
            "currency": "CNY",
            "salary_period": "monthly",
            "base_salary_amount": Decimal("25000.00"),
            "salary_months": Decimal("13.0"),
            "valid_until": date(2026, 9, 10),
            "expected_start_date": date(2026, 10, 8),
        }

    def test_decimal_compensation_is_preserved_and_float_is_rejected(self) -> None:
        offer = OfferRecordCreate.model_validate(self.valid_payload())
        self.assertEqual(offer.base_salary_amount, Decimal("25000.00"))
        self.assertEqual(offer.salary_months, Decimal("13.0"))

        payload = self.valid_payload()
        payload["base_salary_amount"] = 25000.0
        with self.assertRaises(ValidationError):
            OfferRecordCreate.model_validate(payload)

    def test_salary_period_and_timestamp_combinations_are_enforced(self) -> None:
        annual = self.valid_payload()
        annual.update(
            {
                "salary_period": "annual",
                "base_salary_amount": Decimal("360000.00"),
                "salary_months": None,
            }
        )
        self.assertEqual(
            OfferRecordCreate.model_validate(annual).salary_period.value,
            "annual",
        )

        invalid = self.valid_payload()
        invalid["salary_period"] = "annual"
        with self.assertRaises(ValidationError):
            OfferRecordCreate.model_validate(invalid)

        accepted = self.valid_payload()
        accepted.update(
            {
                "status": "accepted",
                "sent_at": UTC_NOW,
                "responded_at": datetime(2026, 9, 3, tzinfo=timezone.utc),
            }
        )
        offer = OfferRecordCreate.model_validate(accepted)
        self.assertIs(offer.status, OfferStatus.ACCEPTED)

    def test_unknown_status_and_extra_fields_are_rejected(self) -> None:
        for field, value in (("status", "approved"), ("unknown", True)):
            payload = self.valid_payload()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                OfferRecordCreate.model_validate(payload)
