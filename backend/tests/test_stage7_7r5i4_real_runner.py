from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5i4_real as real_runner  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402


PRICING_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-31-stage7-7r5i4-pricing-snapshot.json"
)


def _authorization() -> dict:
    return {
        "stage": "7R5-I4",
        "purpose": "single_close_06r2_c_real_raw_authorization",
        "confirmed_at": "2026-08-31T20:18:22+08:00",
        "user_directive": (
            "明确授权 7R5-I4 硬上限 USD 2.00，并开始 CLOSE-06R2-C。"
        ),
        "pricing_snapshot_path": str(PRICING_PATH),
        "pricing_snapshot_sha256": real_runner.sha256_file(PRICING_PATH),
        "model": "deepseek-v4-flash",
        "selected_tier": "off_peak",
        "monetary_cap_usd": 2.0,
        "baseline_business_calls": 45,
        "maximum_api_attempts": 90,
        "content_error_retry_count": 0,
        "authorizes_single_real_raw": True,
        "authorizes_human_or_final": False,
    }


def test_i4_paths_and_lifecycle_are_independent_after_real() -> None:
    lifecycle = contract.validate_result_lifecycle(
        run_id="7R5-I4", expected_state="i4_raw_complete"
    )
    assert lifecycle["active_paths"] == contract.result_paths("7R5-I4")
    assert contract.I4_RAW_RESULT_PATH.exists()
    assert not contract.I4_HUMAN_AUDIT_PATH.exists()
    assert not contract.I4_FINAL_RESULT_PATH.exists()


def test_price_authorization_and_lifecycle_precede_key_read(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(json.dumps(_authorization()), encoding="utf-8")
    snapshot = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    checked_at = datetime.fromisoformat(snapshot["checked_at"])
    with patch.object(
        real_runner, "get_settings", side_effect=AssertionError("不得提前读取 Key")
    ):
        with pytest.raises(RuntimeError, match="生命周期|正式结果"):
            real_runner.validate_zero_call_preconditions(
                pricing_path=PRICING_PATH,
                authorization_path=authorization_path,
                now=checked_at + timedelta(minutes=20),
            )


def test_full_45_call_fake_preflight_uses_current_service_paths() -> None:
    result = asyncio.run(real_runner.zero_call_fake_preflight())
    assert result == {
        "plan_succeeded": 10,
        "report_succeeded": 20,
        "stability_succeeded": 15,
        "fake_business_call_count": 45,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "formal_result_write_count": 0,
        "postgresql_write_count": 0,
    }


def test_report_model_boundary_has_no_time_facts() -> None:
    observed = asyncio.run(real_runner.capture_one_fake_report_boundary())
    assert observed["evaluation_reference_at"] == ""
    assert observed["evaluation_timezone"] == ""
    assert observed["experience_period_facts"] == {}
    assert observed["confirmed_plan_snapshot_used"] is True


def test_raw_payload_keeps_denominators_cap_and_stop_point() -> None:
    payload = real_runner.build_raw_payload_for_test(
        authorization=_authorization(), terminal_status="completed_with_failures"
    )
    assert payload["stage"] == "7R5-I4"
    assert payload["lifecycle"] == "i4_raw_complete"
    assert len(payload["plan_records"]) == 10
    assert len(payload["report_records"]) == 20
    assert len(payload["stability_records"]) == 15
    assert payload["monetary_cap_usd"] == 2.0
    assert payload["quality_gate_passed"] is None
    assert payload["quality_conclusion_allowed"] is False
    assert payload["postgresql_write_count"] == 0


def test_raw_writer_is_exclusive(tmp_path: Path) -> None:
    path = tmp_path / "raw.json"
    real_runner.write_raw_once(path, {"stage": "7R5-I4"})
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        real_runner.write_raw_once(path, {"stage": "7R5-I4"})


def test_sealed_i4_raw_has_fixed_identity_and_stop_point() -> None:
    result = real_runner.validate_sealed_raw()
    raw = result["raw"]
    assert result["lifecycle"]["state"] == "i4_raw_complete"
    assert len(raw["plan_records"]) == 10
    assert len(raw["report_records"]) == 20
    assert len(raw["stability_records"]) == 15
    assert raw["attempt_audit_summary"]["api_attempt_count"] <= 90
    assert raw["estimated_spend_usd"] <= 2.0
    assert raw["quality_gate_passed"] is None
    assert raw["quality_conclusion_allowed"] is False
