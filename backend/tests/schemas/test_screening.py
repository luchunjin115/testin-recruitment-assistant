from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.screening import (
    ScreeningBatchReassessmentRequest,
    ScreeningReportRead,
    ScreeningRunRead,
)


NOW = datetime(2026, 8, 20, tzinfo=timezone.utc)
FP = "a" * 64


def report_payload() -> dict:
    return {
        "id": 1,
        "application_id": 2,
        "job_id": 3,
        "resume_id": 4,
        "job_evaluation_plan_id": 5,
        "overall_score": 80,
        "display_label": "整体较匹配",
        "overall_summary": "岗位相关经历较为充分。",
        "requirement_assessments": [],
        "bonus_highlights": [],
        "tradeoff_reason": None,
        "interview_questions": [],
        "input_fingerprint": FP,
        "jd_fingerprint": FP,
        "plan_fingerprint": FP,
        "resume_fingerprint": FP,
        "prompt_version": "screening_evaluation_v3",
        "model_version": "fake-model",
        "schema_version": "2.0",
        "redaction_version": "screening_redaction_v1",
        "evaluation_reference_at": NOW,
        "evaluation_timezone": "Asia/Shanghai",
        "experience_period_facts_rule_version": "experience_period_facts_v1",
        "experience_period_facts": {
            "rule_version": "experience_period_facts_v1",
            "evaluation_reference_at": NOW.isoformat(),
            "evaluation_timezone": "Asia/Shanghai",
            "reference_month": "2026-08",
            "facts": [],
        },
        "is_outdated": False,
        "outdated_reasons": [],
        "outdated_at": None,
        "generated_at": NOW,
        "updated_at": NOW,
    }


def run_payload() -> dict:
    return {
        "id": 1,
        "application_id": 2,
        "job_id": 3,
        "resume_id": 4,
        "job_evaluation_plan_id": 5,
        "trigger_type": "automatic",
        "status": "queued",
        "input_fingerprint": FP,
        "prompt_version": "screening_evaluation_v3",
        "model_version": "fake-model",
        "schema_version": "2.0",
        "redaction_version": "screening_redaction_v1",
        "evaluation_reference_at": NOW,
        "evaluation_timezone": "Asia/Shanghai",
        "experience_period_facts_rule_version": "experience_period_facts_v1",
        "experience_period_facts_fingerprint": FP,
        "started_at": None,
        "completed_at": None,
        "error_code": None,
        "error_message": None,
        "input_tokens": None,
        "output_tokens": None,
        "duration_ms": None,
        "attempt_count": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }


class ScreeningSchemaTest(TestCase):
    def test_report_accepts_fresh_current_contract(self) -> None:
        report = ScreeningReportRead.model_validate(report_payload())
        self.assertFalse(report.is_outdated)
        serialized = report.model_dump(mode="json")
        self.assertEqual(serialized["evaluation_timezone"], "Asia/Shanghai")
        self.assertNotIn("experience_period_facts", serialized)

    def test_report_requires_outdated_reason_and_time_together(self) -> None:
        payload = report_payload()
        payload["is_outdated"] = True
        with self.assertRaises(ValidationError):
            ScreeningReportRead.model_validate(payload)

    def test_report_rejects_unknown_outdated_reason(self) -> None:
        payload = report_payload()
        payload.update(
            is_outdated=True,
            outdated_reasons=["prompt_changed"],
            outdated_at=NOW,
        )
        with self.assertRaises(ValidationError):
            ScreeningReportRead.model_validate(payload)

    def test_run_accepts_all_product_statuses(self) -> None:
        for status in (
            "waiting_resume",
            "waiting_plan",
            "queued",
            "running",
            "succeeded",
            "failed",
            "paused",
        ):
            with self.subTest(status=status):
                payload = run_payload()
                payload["status"] = status
                self.assertEqual(
                    ScreeningRunRead.model_validate(payload).status.value,
                    status,
                )

    def test_run_rejects_internal_extra_fields(self) -> None:
        payload = run_payload()
        payload["lease_owner"] = "private-worker"
        with self.assertRaises(ValidationError):
            ScreeningRunRead.model_validate(payload)

    def test_batch_accepts_one_to_twenty_unique_ids(self) -> None:
        self.assertEqual(
            len(
                ScreeningBatchReassessmentRequest(
                    application_ids=list(range(1, 21))
                ).application_ids
            ),
            20,
        )

    def test_batch_rejects_empty_over_limit_and_duplicates(self) -> None:
        for values in ([], list(range(1, 22)), [1, 1]):
            with self.subTest(values=len(values)), self.assertRaises(ValidationError):
                ScreeningBatchReassessmentRequest(application_ids=values)

    def test_schema_does_not_expose_raw_model_or_resume_content(self) -> None:
        fields = set(ScreeningReportRead.model_fields) | set(ScreeningRunRead.model_fields)
        self.assertFalse(
            fields.intersection(
                {"raw_response", "raw_model_response", "resume_text", "api_key", "stack"}
            )
        )
