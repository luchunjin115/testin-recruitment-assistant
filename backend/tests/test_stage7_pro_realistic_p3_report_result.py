from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.fixtures.stage7_pro_realistic_quality_samples import (
    EXPECTED_NORMALIZED_FINGERPRINT,
    STABILITY_CASE_IDS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p3-report-raw-results.json"
)
EXPECTED_RESULT_SHA256 = "94f68aa48bec09204359222deab35c6a03ea543a4108eb93375efe0b39574679"


def _result() -> dict:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_p3_raw_identity_authorization_and_stop_point_are_frozen() -> None:
    result = _result()

    assert hashlib.sha256(RESULT_PATH.read_bytes()).hexdigest() == EXPECTED_RESULT_SHA256
    assert result["stage"] == "stage7-pro-realistic-quality"
    assert result["batch"] == "P3"
    assert result["mode"] == "real_report_raw"
    assert result["status"] == "completed"
    assert result["fatal_error"] is None
    assert result["authorization"] == {
        "authorized_by": "project_owner_user",
        "user_directive": "确认开始 P3",
        "authorized_business_call_count": 35,
        "monetary_cap_usd": 2.0,
    }
    assert result["source_fixture_fingerprint"] == EXPECTED_NORMALIZED_FINGERPRINT
    assert result["quality_gate_passed"] is None
    assert result["quality_conclusion_allowed"] is False
    assert result["requires_human_audit"] is True
    assert result["postgresql_write_count"] == 0
    assert result["api_key_persisted"] is False
    assert "P4" in result["next_step"]


def test_p3_attempt_budget_model_tokens_and_cost_are_exact() -> None:
    result = _result()

    assert result["execution_contract"]["model"] == "deepseek-v4-pro"
    assert result["execution_contract"]["content_error_retry_count"] == 0
    assert result["execution_contract"]["infrastructure_retry_maximum_per_business_call"] == 1
    assert result["pricing"]["selected_tier"] == "peak"
    assert result["attempt_summary"] == {
        "scheduled_business_call_count": 35,
        "executed_business_call_count": 35,
        "api_attempt_count": 35,
        "succeeded_attempt_count": 35,
        "failed_attempt_count": 0,
        "infrastructure_retry_count": 0,
        "input_tokens": 203000,
        "cache_hit_input_tokens": None,
        "cache_miss_input_tokens": None,
        "output_tokens": 82408,
        "estimated_spend_usd": 0.5942956799999999,
        "failed_attempt_reserve_usd": 0.0,
    }
    assert result["attempt_summary"]["estimated_spend_usd"] <= result["monetary_cap_usd"]
    assert len(result["attempt_audit"]) == 35
    assert len({item["business_call_id"] for item in result["attempt_audit"]}) == 35
    for attempt in result["attempt_audit"]:
        assert attempt["attempt_number"] == 1
        assert attempt["result"] == "succeeded"
        assert attempt["requested_model"] == "deepseek-v4-pro"
        assert attempt["model"] == "deepseek-v4-pro"
        assert attempt["finish_reason"] == "stop"
        assert attempt["input_tokens"] > 0
        assert attempt["output_tokens"] > 0
        assert attempt["cost_estimate"]["complete"] is True
        assert attempt["raw_response"]


def test_p3_service_legality_direction_and_score_diagnostics_are_preserved() -> None:
    result = _result()

    assert result["report_summary"] == {
        "scheduled_count": 20,
        "legal_count": 17,
        "failed_count": 3,
        "direction_match_count": 14,
        "score_in_frozen_range_count": 10,
    }
    assert [item["case_id"] for item in result["reports"]] == [
        f"R{index:02d}" for index in range(1, 21)
    ]
    failed = [item for item in result["reports"] if item["status"] == "failed"]
    assert [item["case_id"] for item in failed] == ["R04", "R09", "R14"]
    assert all(item["error_code"] == "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT" for item in failed)
    for report in result["reports"]:
        assert report["adapter_attempt_count"] == 1
        if report["status"] != "succeeded":
            continue
        assert report["nonzero_assessment_count"] == report["nonzero_with_evidence_count"]
        assert report["criterion_assessment_count"] == len(report["report"]["criterion_assessments"])
        assert report["model_version"] == "deepseek-v4-pro"
        assert report["schema_version"] == "5.0"


def test_p3_stability_uses_fifteen_additional_independent_calls() -> None:
    result = _result()

    assert len(result["stability_runs"]) == 15
    assert [item["case_id"] for item in result["stability_summary"]] == list(
        STABILITY_CASE_IDS
    )
    assert [item["legal_run_count"] for item in result["stability_summary"]] == [3, 3, 0, 3, 2]
    assert [item["scores"] for item in result["stability_summary"]] == [
        [88, 88, 88],
        [88, 88, 88],
        [],
        [88, 88, 88],
        [88, 88],
    ]
    assert sum(item["direction_stable"] for item in result["stability_summary"]) == 3
    assert sum(item["spread_le_10"] for item in result["stability_summary"]) == 3
    assert [
        item["business_call_id"]
        for item in result["stability_runs"]
        if item["status"] == "failed"
    ] == ["P3-S-R09-1", "P3-S-R09-2", "P3-S-R09-3", "P3-S-R17-1"]


def test_p3_raw_contains_no_persisted_api_key() -> None:
    serialized = RESULT_PATH.read_text(encoding="utf-8").lower()

    assert "deepseek_api_key" not in serialized
    assert '"api_key"' not in serialized
    assert "sk-" not in serialized
