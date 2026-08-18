from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.screening_result import (
    ApplicationScreeningResultDetailRead,
    ApplicationScreeningResultSummaryRead,
)


TEST_TIME = datetime(2026, 8, 18, tzinfo=timezone.utc)


def summary_payload() -> dict:
    return {
        "id": 10,
        "candidate_id": 2,
        "job_id": 3,
        "application_id": 4,
        "resume_id": 5,
        "attempt_number": 2,
        "execution_status": "completed",
        "overall_score": 86,
        "hard_pass": True,
        "recommendation": "strong_recommend",
        "evidence_coverage_rate": Decimal("0.8750"),
        "error_code": None,
        "error_message": None,
        "started_at": TEST_TIME,
        "finished_at": TEST_TIME,
        "duration_ms": 1200,
        "trigger_reason": "manual_rerun",
        "force_rerun": False,
        "is_outdated": False,
        "outdated_at": None,
        "created_at": TEST_TIME,
        "updated_at": TEST_TIME,
    }


class ApplicationScreeningResultSchemaTest(TestCase):
    def test_summary_exposes_status_score_error_and_version_position(self) -> None:
        result = ApplicationScreeningResultSummaryRead.model_validate(summary_payload())

        self.assertEqual(result.attempt_number, 2)
        self.assertEqual(result.execution_status.value, "completed")
        self.assertEqual(result.evidence_coverage_rate, Decimal("0.8750"))
        self.assertFalse(result.is_outdated)

    def test_detail_exposes_evidence_snapshots_and_versions(self) -> None:
        payload = {
            **summary_payload(),
            "input_fingerprint": "a" * 64,
            "hard_requirement_checks": [{"criterion": "work_years"}],
            "dimension_scores": {"must_have_requirements": {"score": 90}},
            "resume_evidence": [{"source": "resume_text", "quote": "Python"}],
            "job_evidence": [{"requirement": "Python"}],
            "candidate_input_snapshot": {"application_ref": "application-4"},
            "resume_snapshot": {"resume_id": 5},
            "job_requirements_snapshot": {"schema_version": "1.0"},
            "rubric_snapshot": {"version": 2},
            "rules_version": "rules:v1;score:v1",
            "prompt_version": "screening_evaluation_v3",
            "model_provider": "deepseek",
            "model_name": "deepseek-v4-flash",
            "model_config_version": "v1",
            "job_schema_version": "1.0",
            "resume_schema_version": "1.0",
        }

        result = ApplicationScreeningResultDetailRead.model_validate(payload)

        self.assertEqual(result.resume_evidence[0]["quote"], "Python")
        self.assertEqual(result.rubric_snapshot["version"], 2)
        self.assertEqual(result.prompt_version, "screening_evaluation_v3")

    def test_invalid_execution_status_and_coverage_are_rejected(self) -> None:
        for field, value in (
            ("execution_status", "queued"),
            ("evidence_coverage_rate", Decimal("1.1")),
        ):
            payload = summary_payload()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ApplicationScreeningResultSummaryRead.model_validate(payload)
