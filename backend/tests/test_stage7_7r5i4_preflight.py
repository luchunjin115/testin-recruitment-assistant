from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import stage7_7r5_quality_contract as contract  # noqa: E402


def _preflight_module():
    return importlib.import_module("run_stage7_7r5i4_preflight")


def test_i4_paths_are_registered_and_isolated_from_i2_and_i3_r1() -> None:
    paths = {
        key: Path(value)
        for key, value in contract.result_paths(contract.I4_RUN_ID).items()
    }
    protected = {
        Path(value).resolve()
        for run_id in (contract.ACTIVE_RUN_ID, contract.I3_RUN_ID)
        for value in contract.result_paths(run_id).values()
    }

    assert set(paths) == {"preflight", "raw", "human_audit", "final"}
    assert all("7r5i4" in path.name for path in paths.values())
    assert {path.resolve() for path in paths.values()}.isdisjoint(protected)
    assert contract.I4_REVIEW_PATH.name.endswith("7r5i4-fixture-review.md")


def test_i4_preflight_and_raw_are_the_only_existing_i4_formal_results() -> None:
    paths = {
        key: Path(value)
        for key, value in contract.result_paths(contract.I4_RUN_ID).items()
    }

    assert paths["preflight"].exists()
    assert paths["raw"].exists()
    assert not paths["human_audit"].exists()
    assert not paths["final"].exists()
    assert contract.I4_REVIEW_PATH.exists()
    assert contract.validate_result_lifecycle(
        run_id=contract.I4_RUN_ID,
        expected_state="i4_raw_complete",
    )["state"] == "i4_raw_complete"


def test_i4_zero_call_payload_binds_v3_current_versions_and_frozen_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = _preflight_module()
    monkeypatch.setattr(
        preflight,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("不得读取 API Key")),
        raising=False,
    )

    payload = json.loads(contract.I4_PREFLIGHT_PATH.read_text(encoding="utf-8"))

    assert payload["stage"] == "7R5-I4"
    assert payload["mode"] == "zero_call_fresh_fixture_preflight"
    assert payload["lifecycle"] == "i4_preflight_complete"
    assert payload["quality_contract_version"] == "stage7_v5_quality_contract_v3"
    assert payload["execution_contract"] == {
        "plan_prompt_version": "job_evaluation_plan_lightweight_v4",
        "plan_service_behavior_version": "lightweight_plan_generation_v5",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v7",
        "report_service_behavior_version": "lightweight_report_generation_v9",
        "report_schema_version": "5.0",
    }
    assert payload["fixture_summary"]["plan_case_count"] == 10
    assert payload["fixture_summary"]["report_case_count"] == 20
    assert payload["fixture_summary"]["stability_case_count"] == 5
    assert payload["fixture_summary"]["stability_run_count"] == 15
    assert payload["fixture_summary"]["manual_direction_denominators"] == {
        "high_match": 8,
        "partial_match": 6,
        "low_match": 6,
    }
    assert payload["fixture_summary"]["stability_direction_distribution"] == {
        "high_match": 2,
        "partial_match": 2,
        "low_match": 1,
    }
    assert payload["fixture_summary"]["pure_work_duration_excluded_count"] == 10
    assert payload["fixture_summary"]["mixed_capability_retained_count"] == 10
    assert payload["preflight_checks"]["all_passed"] is True


def test_i4_preflight_records_zero_external_activity_and_protects_old_runs() -> None:
    payload = json.loads(contract.I4_PREFLIGHT_PATH.read_text(encoding="utf-8"))

    assert payload["historical_lifecycles"] == {
        "7R5-I2": "i2_final_complete",
        "7R5-I3-R1": "i3_raw_complete",
    }
    assert payload["historical_recalculation_allowed"] is False
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["input_token_count"] == 0
    assert payload["output_token_count"] == 0
    assert payload["estimated_spend_usd"] == 0
    assert payload["api_key_read"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["pricing_lookup_count"] == 0
    assert payload["formal_raw_human_final_write_count"] == 0
    assert payload["pricing_gate_allowed"] is False
    assert payload["real_run_allowed"] is False


def test_i4_review_makes_resume_date_policy_and_stop_point_explicit() -> None:
    review = contract.I4_REVIEW_PATH.read_text(encoding="utf-8")

    assert "简历中的任职起止日期可以保留" in review
    assert "不得计算工作年限" in review
    assert "纯工作年限要求不进入 required 分母" in review
    assert "混合要求保留非年限能力" in review
    assert "CLOSE-06R2-B" in review
    assert "尚未开始" in review


def test_i4_preflight_bundle_is_write_once(tmp_path: Path) -> None:
    preflight = _preflight_module()
    preflight_path = tmp_path / "i4-preflight.json"
    review_path = tmp_path / "i4-review.md"
    payload = {"stage": "7R5-I4"}

    preflight.write_preflight_bundle(
        preflight_path=preflight_path,
        review_path=review_path,
        payload=payload,
        review="# I4 review\n",
    )
    assert json.loads(preflight_path.read_text(encoding="utf-8")) == payload
    assert review_path.read_text(encoding="utf-8") == "# I4 review\n"

    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_preflight_bundle(
            preflight_path=preflight_path,
            review_path=review_path,
            payload=payload,
            review="# changed\n",
        )
