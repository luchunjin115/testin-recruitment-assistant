from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5i3_real as real_runner  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402
from tests.fixtures.v5_i3_quality_samples import (  # noqa: E402
    I3_REPORT_PAIRS,
)


PRICING_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-31-stage7-7r5i3-r1-pricing-snapshot.json"
)


def test_offline_settings_keep_historical_i3_model_frozen() -> None:
    settings = real_runner._offline_settings()

    assert settings.JOB_EVALUATION_PLAN_MODEL == contract.PLANNED_MODEL
    assert settings.SCREENING_EVALUATION_MODEL == contract.PLANNED_MODEL


def _authorization(pricing: dict) -> dict:
    return {
        "stage": "7R5-I3-R1",
        "purpose": "single_close_06c_real_raw_authorization",
        "confirmed_at": "2026-08-31T12:38:08+08:00",
        "user_directive": "确认 USD 2 硬上限，开始 CLOSE-06C",
        "pricing_snapshot_path": str(PRICING_PATH),
        "pricing_snapshot_sha256": real_runner.sha256_file(PRICING_PATH),
        "monetary_cap_usd": 2.0,
        "baseline_business_calls": 45,
        "maximum_api_attempts": 90,
        "content_error_retry_count": 0,
        "authorizes_single_real_raw": True,
        "authorizes_human_or_final": False,
    }


def test_i3_lifecycle_is_independent_and_raw_is_sealed() -> None:
    lifecycle = contract.validate_result_lifecycle(
        run_id="7R5-I3-R1", expected_state="i3_raw_complete"
    )
    assert lifecycle["run_id"] == "7R5-I3-R1"
    assert lifecycle["state"] == "i3_raw_complete"
    assert lifecycle["active_paths"] == contract.result_paths("7R5-I3-R1")
    assert contract.I2_FINAL_RESULT_PATH.exists()
    assert contract.I3_RAW_RESULT_PATH.exists()
    assert not contract.I3_HUMAN_AUDIT_PATH.exists()
    assert not contract.I3_FINAL_RESULT_PATH.exists()


def test_preconditions_validate_price_cap_and_tier_before_reading_settings(
    tmp_path: Path,
) -> None:
    pricing = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(
        json.dumps(_authorization(pricing)), encoding="utf-8"
    )
    with patch.object(
        real_runner,
        "validate_pricing_snapshot",
        return_value=pricing,
    ), patch.object(
        real_runner, "get_settings", side_effect=AssertionError("不得提前读取 Key")
    ):
        with pytest.raises(RuntimeError, match="生命周期|正式结果"):
            real_runner.validate_zero_call_preconditions(
                pricing_path=PRICING_PATH,
                authorization_path=authorization_path,
                now=datetime.fromisoformat("2026-08-31T12:40:00+08:00"),
            )

        too_low = _authorization(pricing)
        too_low["monetary_cap_usd"] = 1.98
        authorization_path.write_text(json.dumps(too_low), encoding="utf-8")
        with pytest.raises(RuntimeError, match="金额"):
            real_runner.validate_zero_call_preconditions(
                pricing_path=PRICING_PATH,
                authorization_path=authorization_path,
                now=datetime.fromisoformat("2026-08-31T12:40:00+08:00"),
            )


def test_report_requests_use_confirmed_plan_and_application_time() -> None:
    for case in I3_REPORT_PAIRS:
        request = real_runner.build_report_request(case)
        assert request["evaluation_plan"] == case["confirmed_plan_snapshot"]["plan"]
        assert request["evaluation_reference_at"].isoformat() == case[
            "application_applied_at"
        ]
        assert request["evaluation_reference_at"].isoformat() == case[
            "evaluation_reference_at"
        ]
        assert request["confirmed_plan_snapshot_sha256"] == case[
            "confirmed_plan_snapshot"
        ]["snapshot_sha256"]


def test_full_45_call_fake_preflight_uses_production_service_paths() -> None:
    result = asyncio.run(real_runner.zero_call_fake_preflight())
    assert result == {
        "plan_succeeded": 10,
        "report_succeeded": 20,
        "stability_succeeded": 15,
        "fake_business_call_count": 45,
        "real_model_call_count": 0,
        "api_key_read": False,
        "formal_result_write_count": 0,
    }


def test_raw_payload_keeps_45_denominators_and_cannot_claim_quality() -> None:
    plan_records = [{"case_id": f"I3-P{i:02d}", "status": "failed"} for i in range(10)]
    report_records = [
        {"case_id": f"I3-R{i:02d}", "sample_index": i, "status": "failed"}
        for i in range(20)
    ]
    stability_records = [
        {
            "case_id": f"I3-S{sample:02d}-{run}",
            "sample_index": sample,
            "status": "failed",
        }
        for sample in (0, 4, 8, 10, 14)
        for run in range(1, 4)
    ]
    payload = real_runner.build_raw_payload(
        gate={
            "pricing": {"selected_tier": "off_peak"},
            "authorization": {"monetary_cap_usd": 2.0},
            "preflight": {"fixture_hashes": {"fixture": "fixture-hash"}},
            "lifecycle": {"state": "i3_preflight_complete"},
        },
        attempts=[],
        plan_records=plan_records,
        report_records=report_records,
        stability_records=stability_records,
        estimated_spend_usd=0,
        failed_attempt_reserve_usd=0,
        terminal_status="completed_with_failures",
        terminal_error=None,
    )
    assert len(payload["plan_records"]) == 10
    assert len(payload["report_records"]) == 20
    assert len(payload["stability_records"]) == 15
    assert payload["quality_gate_passed"] is None
    assert payload["quality_conclusion_allowed"] is False
    assert payload["requires_frozen_human_audit"] is True
    assert payload["postgresql_write_count"] == 0


def test_raw_writer_is_exclusive(tmp_path: Path) -> None:
    path = tmp_path / "raw.json"
    real_runner.write_raw_once(path, {"stage": "7R5-I3-R1"})
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        real_runner.write_raw_once(path, {"stage": "7R5-I3-R1"})


def test_sealed_raw_has_fixed_identity_denominators_and_stop_point() -> None:
    result = real_runner.validate_sealed_raw()
    raw = result["raw"]
    assert result["lifecycle"]["state"] == "i3_raw_complete"
    assert len(raw["plan_records"]) == 10
    assert len(raw["report_records"]) == 20
    assert len(raw["stability_records"]) == 15
    assert raw["attempt_audit_summary"]["api_attempt_count"] == 45
    assert raw["quality_gate_passed"] is None
