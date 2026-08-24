from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.screening import ScreeningRunRead


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "b" * 64


def _run_payload(**overrides):
    values = {
        "id": 1,
        "application_id": 2,
        "job_id": 3,
        "resume_id": 4,
        "job_evaluation_plan_id": None,
        "trigger_type": "automatic",
        "status": "waiting_plan",
        "waiting_reason": "plan_missing",
        "input_fingerprint": FINGERPRINT,
        "prompt_version": "screening_evaluation_v3",
        "model_version": "fake-screening-model",
        "schema_version": "2.0",
        "redaction_version": "screening_redaction_v1",
        "evaluation_reference_at": NOW,
        "evaluation_timezone": "Asia/Shanghai",
        "experience_period_facts_rule_version": "experience_period_facts_v1",
        "experience_period_facts_fingerprint": FINGERPRINT,
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
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "waiting_reason",
    [
        "plan_missing",
        "plan_generating",
        "plan_failed",
        "plan_outdated",
        "plan_contract_outdated",
    ],
)
def test_waiting_plan_response_has_stable_reason_code(waiting_reason: str) -> None:
    parsed = ScreeningRunRead.model_validate(_run_payload(waiting_reason=waiting_reason))
    assert parsed.waiting_reason == waiting_reason


def test_non_waiting_plan_state_rejects_plan_waiting_reason() -> None:
    ScreeningRunRead.model_validate(_run_payload())
    with pytest.raises(ValidationError):
        ScreeningRunRead.model_validate(
            _run_payload(status="queued", waiting_reason="plan_missing")
        )
