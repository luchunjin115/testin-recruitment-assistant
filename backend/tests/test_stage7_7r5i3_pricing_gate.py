from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5i3_pricing_gate as pricing_gate  # noqa: E402


CHECKED_AT = datetime.fromisoformat("2026-08-31T12:24:26+08:00")
OFF_PEAK_RATES = {
    "cache_hit_input": 0.007,
    "cache_miss_input": 0.22,
    "output": 0.66,
}
PEAK_RATES = {
    "cache_hit_input": 0.014,
    "cache_miss_input": 0.44,
    "output": 1.32,
}


def _snapshot() -> dict:
    return pricing_gate.build_pricing_snapshot(
        checked_at=CHECKED_AT,
        model_version_shown_by_provider="DeepSeek-V4-Flash-0731",
        off_peak_rates=OFF_PEAK_RATES,
        peak_rates=PEAK_RATES,
    )


def test_active_r1_preflight_and_frozen_call_budget_are_required() -> None:
    identity = pricing_gate.validate_active_r1_preflight()
    assert identity == {
        "stage": "7R5-I3-R1",
        "lifecycle": "i3_preflight_complete",
        "fixture_revision": "r1",
        "direction_distribution": {
            "high_match": 8,
            "partial_match": 6,
            "low_match": 6,
        },
        "stability_direction_distribution": {
            "high_match": 2,
            "partial_match": 2,
            "low_match": 1,
        },
    }

    budget = pricing_gate.compute_request_budget()
    assert budget["baseline_business_calls"] == 45
    assert budget["maximum_api_attempts"] == 90
    assert budget["baseline_max_output_tokens"] == 500_000
    assert budget["retry_ceiling_max_output_tokens"] == 1_000_000
    assert budget["baseline_input_token_upper_bound"] > 0
    assert budget["retry_ceiling_input_token_upper_bound"] == (
        2 * budget["baseline_input_token_upper_bound"]
    )
    assert budget["input_token_upper_bound_basis"] == "serialized_prompt_utf8_bytes"


def test_provider_schedule_selects_peak_and_off_peak_in_utc() -> None:
    assert pricing_gate.pricing_tier_at(
        datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)
    ) == "peak"
    assert pricing_gate.pricing_tier_at(
        datetime(2026, 8, 31, 3, 59, 59, tzinfo=timezone.utc)
    ) == "peak"
    assert pricing_gate.pricing_tier_at(
        datetime(2026, 8, 31, 4, 0, tzinfo=timezone.utc)
    ) == "off_peak"
    assert pricing_gate.pricing_tier_at(
        datetime(2026, 8, 31, 6, 0, tzinfo=timezone.utc)
    ) == "peak"
    assert pricing_gate.pricing_tier_at(
        datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)
    ) == "off_peak"


def test_snapshot_is_24_hour_zero_call_gate_and_uses_peak_for_cap_request() -> None:
    snapshot = _snapshot()
    assert snapshot["stage"] == "7R5-I3-R1"
    assert snapshot["checked_at"] == CHECKED_AT.isoformat()
    assert snapshot["expires_at"] == (CHECKED_AT + timedelta(hours=24)).isoformat()
    assert snapshot["selected_tier"] == "off_peak"
    assert snapshot["usd_per_million_tokens"] == OFF_PEAK_RATES
    assert snapshot["peak_usd_per_million_tokens"] == PEAK_RATES
    assert snapshot["authorization"]["monetary_cap_usd"] is None
    assert snapshot["authorization"]["user_monetary_authorization_required"] is True
    assert snapshot["authorization"]["real_run_allowed"] is False

    budget = snapshot["call_budget"]
    expected_peak_retry_ceiling = (
        Decimal(budget["retry_ceiling_input_token_upper_bound"])
        * Decimal("0.44")
        + Decimal("1000000") * Decimal("1.32")
    ) / Decimal("1000000")
    assert Decimal(str(snapshot["cost_estimates_usd"]["peak_retry_ceiling"])) == (
        expected_peak_retry_ceiling.quantize(Decimal("0.00000001"))
    )
    assert snapshot["requested_cap_floor_usd"] >= snapshot["cost_estimates_usd"][
        "peak_retry_ceiling"
    ]
    assert snapshot["external_effects"] == {
        "api_key_read": False,
        "real_adapter_instantiated": False,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "input_token_count": 0,
        "output_token_count": 0,
        "estimated_spend_usd": 0,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
    }


def test_snapshot_validation_rejects_expiry_wrong_tier_and_tampering() -> None:
    snapshot = _snapshot()
    assert pricing_gate.validate_pricing_snapshot(
        snapshot, now=CHECKED_AT + timedelta(hours=23, minutes=59)
    )["selected_tier"] == "off_peak"

    with pytest.raises(RuntimeError, match="过期"):
        pricing_gate.validate_pricing_snapshot(
            snapshot, now=CHECKED_AT + timedelta(hours=24, seconds=1)
        )

    wrong_tier = json.loads(json.dumps(snapshot))
    wrong_tier["selected_tier"] = "peak"
    with pytest.raises(RuntimeError, match="时段"):
        pricing_gate.validate_pricing_snapshot(wrong_tier, now=CHECKED_AT)

    lowered_peak = json.loads(json.dumps(snapshot))
    lowered_peak["peak_usd_per_million_tokens"]["output"] = 0.66
    with pytest.raises(RuntimeError, match="费用"):
        pricing_gate.validate_pricing_snapshot(lowered_peak, now=CHECKED_AT)


def test_pricing_snapshot_is_write_once(tmp_path: Path) -> None:
    path = tmp_path / "pricing.json"
    pricing_gate.write_pricing_snapshot(path, _snapshot())
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        pricing_gate.write_pricing_snapshot(path, _snapshot())

