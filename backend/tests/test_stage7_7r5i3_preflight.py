from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5i3_preflight as preflight  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402
from tests.fixtures.v5_i3_quality_samples import (  # noqa: E402
    I3_PLAN_JDS,
    I3_REPORT_PAIRS,
    I3_STABILITY_SAMPLE_INDICES,
    compute_i3_fixture_hashes,
)
from tests.fixtures.v5_quality_samples import compute_v5_fixture_hash  # noqa: E402


def test_i3_fixture_is_fresh_complete_and_frozen() -> None:
    hashes = compute_i3_fixture_hashes()
    assert len(I3_PLAN_JDS) == 10
    assert len(I3_REPORT_PAIRS) == 20
    assert len(I3_STABILITY_SAMPLE_INDICES) == 5
    assert len(set(I3_STABILITY_SAMPLE_INDICES)) == 5
    assert hashes == preflight.I3_FROZEN_HASHES
    assert hashes["fixture"] != compute_v5_fixture_hash()
    assert [case["case_id"] for case in I3_PLAN_JDS] == [
        f"I3-P{index:02d}" for index in range(10)
    ]
    assert [case["case_id"] for case in I3_REPORT_PAIRS] == [
        f"I3-R{index:02d}" for index in range(20)
    ]
    directions = [case["labels"]["overall_direction"] for case in I3_REPORT_PAIRS]
    assert directions.count("high_match") == 8
    assert directions.count("partial_match") == 6
    assert directions.count("low_match") == 6


def test_partial_cases_freeze_both_real_strength_and_required_gap() -> None:
    partial_cases = [
        case
        for case in I3_REPORT_PAIRS
        if case["labels"]["overall_direction"] == "partial_match"
    ]
    assert len(partial_cases) == 6
    for case in partial_cases:
        sections = {finding["section"] for finding in case["material_findings"]}
        assert "strengths" in sections
        assert "gaps" in sections
        assert case["labels"]["required_evidence_present"]
        assert case["labels"]["required_evidence_absent"]


def test_stability_selection_is_two_high_two_partial_one_low() -> None:
    directions = [
        I3_REPORT_PAIRS[index]["labels"]["overall_direction"]
        for index in I3_STABILITY_SAMPLE_INDICES
    ]
    assert directions.count("high_match") == 2
    assert directions.count("partial_match") == 2
    assert directions.count("low_match") == 1


def test_every_report_case_has_valid_frozen_v2_labels() -> None:
    for case in I3_REPORT_PAIRS:
        assert case["label_contract_version"] == contract.I3_QUALITY_CONTRACT_VERSION
        validated = contract.validate_i3_case_inputs(case, run_kind="report")
        assert validated["plan_source"] == "confirmed_plan_snapshot"
        assert case["evaluation_reference_at"] == case["application_applied_at"]
        assert contract.validate_i3_time_case(case["time_case"])[
            "calculation_reference"
        ] == "application_applied_at"
        assert contract.validate_i3_material_findings(
            case["material_findings"]
        ) == case["material_findings"]


def test_i3_paths_are_independent_and_only_raw_now_exists() -> None:
    paths = preflight.i3_paths()
    assert preflight.I3_RUN_ID == "7R5-I3-R1"
    assert "7r5i3-r1" in paths["preflight"].name
    assert paths["superseded_preflight"] == preflight.I3_SUPERSEDED_PREFLIGHT_PATH
    assert paths["superseded_preflight"].exists()
    assert paths["preflight"] != contract.I2_PREFLIGHT_PATH
    assert paths["raw"] != contract.I2_RAW_RESULT_PATH
    assert paths["human"] != contract.I2_HUMAN_AUDIT_PATH
    assert paths["final"] != contract.I2_FINAL_RESULT_PATH
    assert paths["raw"].exists()
    assert not paths["human"].exists()
    assert not paths["final"].exists()
    assert contract.classify_result_entry(paths["superseded_preflight"]) == (
        "i3_superseded_preflight"
    )
    assert contract.classify_result_entry(paths["preflight"]) == "i3_preflight"
    assert contract.classify_result_entry(paths["raw"]) == "i3_formal"
    with pytest.raises(RuntimeError, match="未登记"):
        contract.classify_result_entry(
            contract.V5_RESULTS_DIR / "unknown-i3-result.json"
        )


def test_user_rejected_preflight_is_preserved_byte_for_byte() -> None:
    assert hashlib.sha256(
        preflight.I3_SUPERSEDED_PREFLIGHT_PATH.read_bytes()
    ).hexdigest() == "a458fab4e044f38234935b0135c76cfd0b618e5cc8cad1bc83c2e90155c21e17"
    assert hashlib.sha256(
        preflight.I3_SUPERSEDED_REVIEW_PATH.read_bytes()
    ).hexdigest() == "9dc797b83dabfa2bedc7301e7c462ecaeff16d6ace2873eee17a046322a6e3b0"


def test_i3_zero_call_preflight_uses_actual_versions_and_no_external_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("不得读取 API Key")),
        raising=False,
    )
    payload = json.loads(preflight.I3_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    assert payload["stage"] == "7R5-I3-R1"
    assert payload["fixture_revision"] == "r1"
    assert payload["lifecycle"] == "i3_preflight_complete"
    assert payload["quality_contract_version"] == "stage7_v5_quality_contract_v2"
    assert payload["execution_contract"] == {
        "plan_prompt_version": "job_evaluation_plan_lightweight_v3",
        "plan_service_behavior_version": "lightweight_plan_generation_v4",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v6",
        "report_service_behavior_version": "lightweight_report_generation_v8",
        "report_schema_version": "5.0",
    }
    assert payload["fixture_summary"]["plan_case_count"] == 10
    assert payload["fixture_summary"]["report_case_count"] == 20
    assert payload["fixture_summary"]["stability_group_count"] == 5
    assert payload["fixture_summary"]["stability_run_count"] == 15
    assert payload["fixture_summary"]["direction_distribution"] == {
        "high_match": 8,
        "partial_match": 6,
        "low_match": 6,
    }
    assert payload["fixture_summary"]["stability_direction_distribution"] == {
        "high_match": 2,
        "partial_match": 2,
        "low_match": 1,
    }
    assert payload["supersedes"] == {
        "stage": "7R5-I3",
        "preflight_path": str(preflight.I3_SUPERSEDED_PREFLIGHT_PATH),
        "reason": "user_rejected_10_high_0_partial_10_low_distribution",
        "old_fixture_sha256": (
            "5869bc60504195bd392d7880d93bd6c52a770edba6e6ced35586ad706337b481"
        ),
        "old_evidence_preserved": True,
    }
    assert payload["preflight_checks"]["all_passed"] is True
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["input_token_count"] == 0
    assert payload["output_token_count"] == 0
    assert payload["estimated_spend_usd"] == 0
    assert payload["api_key_read"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["pricing_gate_allowed"] is False
    assert payload["real_run_allowed"] is False


def test_i3_preflight_rejects_time_drift_before_any_paid_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = [dict(case) for case in I3_REPORT_PAIRS]
    broken[0]["time_case"] = dict(broken[0]["time_case"])
    broken[0]["time_case"]["evaluation_reference_at"] = (
        "2026-09-01T09:00:00+08:00"
    )
    monkeypatch.setattr(preflight, "I3_REPORT_PAIRS", broken)
    with pytest.raises(RuntimeError, match="必须等于.*投递时间"):
        preflight._validate_frozen_cases()


def test_i3_preflight_artifact_is_write_once(tmp_path: Path) -> None:
    payload = json.loads(preflight.I3_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    target = tmp_path / "i3-preflight.json"
    preflight.write_preflight(target, payload)
    assert target.exists()
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_preflight(target, payload)
