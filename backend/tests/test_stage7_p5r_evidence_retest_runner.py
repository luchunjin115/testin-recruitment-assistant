from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import run_stage7_p5r_evidence_retest as runner


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-zero-call-preflight.json"
)


def test_p5r_e_schedule_remains_frozen_after_execution() -> None:
    assert [item[0] for item in runner.SOURCE_CALL_SCHEDULE] == [
        "P3-R04",
        "P3-R09",
        "P3-R14",
        "P3-S-R09-1",
        "P3-S-R09-2",
        "P3-S-R09-3",
        "P3-S-R17-1",
    ]
    assert runner.RESULT_PATH.exists() is True
    assert hashlib.sha256(runner.P3_RAW_PATH.read_bytes()).hexdigest() == (
        runner.P3_RAW_SHA256
    )


def test_p5r_e_runner_freezes_current_contract_and_safety_budget() -> None:
    assert runner.MODEL == "deepseek-v4-pro"
    assert runner.SCREENING_EVALUATION_V5_PROMPT_VERSION == (
        "screening_evaluation_lightweight_v10"
    )
    assert runner.SCREENING_EVALUATION_V5_BEHAVIOR_VERSION == (
        "lightweight_report_generation_v11"
    )
    assert runner.SCREENING_EVALUATION_V5_SCHEMA_VERSION == "5.0"
    assert len(runner.SOURCE_CALL_SCHEDULE) == 7
    assert len(runner.SOURCE_CALL_SCHEDULE) * 2 == 14


def test_p5r_e_rejects_any_rerun_after_result_creation() -> None:
    with pytest.raises(RuntimeError, match="拒绝覆盖或补跑"):
        runner.offline_preflight()


def test_p5r_e_result_path_is_independent_and_present() -> None:
    assert runner.RESULT_PATH != runner.P3_RAW_PATH
    assert runner.RESULT_PATH.parent == PROJECT_ROOT / "docs/stages/stage7"
    assert runner.RESULT_PATH.exists() is True


def test_p5r_e_source_p3_raw_remains_valid_json() -> None:
    payload = json.loads(runner.P3_RAW_PATH.read_text(encoding="utf-8"))
    assert len(payload["reports"]) + len(payload["stability_runs"]) == 35


def test_p5r_d_zero_call_record_matches_the_frozen_gate() -> None:
    payload = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))

    assert payload["status"] == "complete"
    assert payload["p3_read_only_replay"]["service_legal_count"] == 33
    assert payload["p3_read_only_replay"]["still_rejected_ids"] == [
        "P3-R04",
        "P3-R14",
    ]
    assert payload["real_retest_gate"]["api_attempt_limit"] == 14
    assert payload["pricing"]["seven_call_peak_cost_upper_bound_usd"] == (
        0.56730696
    )
    assert payload["authorization"]["p5r_e_paid_calls_allowed"] is False
    assert payload["external_effects"]["real_model_call_count"] == 0


def test_p5r_e_result_is_preserved_with_known_raw_audit_gap() -> None:
    payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))

    assert hashlib.sha256(runner.RESULT_PATH.read_bytes()).hexdigest() == (
        "4eb8ddd46656e590895a4502bd8b9c205ffd94b9576b7b5b6042c6ec04e966b7"
    )
    assert payload["authorization"]["monetary_cap_usd"] == 0.6
    assert payload["attempt_summary"]["api_attempt_count"] == 7
    assert payload["attempt_summary"]["estimated_spend_usd"] == 0.06159186
    assert payload["service_legal_count"] == 6
    assert [
        item["business_call_id"]
        for item in payload["records"]
        if item["status"] == "failed"
    ] == ["P3-R04"]
    assert "attempt_audit" not in payload


def test_runner_now_persists_attempt_audit_for_any_future_distinct_run() -> None:
    source = runner.__file__ and Path(runner.__file__).read_text(encoding="utf-8")
    assert '"attempt_audit": attempts' in source
