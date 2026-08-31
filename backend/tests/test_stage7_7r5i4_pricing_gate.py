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

import run_stage7_7r5i4_pricing_gate as pricing_gate  # noqa: E402


CHECKED_AT = datetime.fromisoformat("2026-08-31T19:50:18.531201+08:00")
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
    return json.loads(pricing_gate.PRICING_SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_active_i4_preflight_and_current_production_versions_are_required() -> None:
    identity = pricing_gate.validate_active_i4_preflight()
    assert identity == {
        "stage": "7R5-I4",
        "lifecycle": "i4_preflight_complete",
        "quality_contract_version": "stage7_v5_quality_contract_v3",
        "plan_prompt_version": "job_evaluation_plan_lightweight_v4",
        "plan_service_behavior_version": "lightweight_plan_generation_v5",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v7",
        "report_service_behavior_version": "lightweight_report_generation_v9",
        "report_schema_version": "5.0",
        "historical_lifecycles": {
            "7R5-I2": "i2_final_complete",
            "7R5-I3-R1": "i3_raw_complete",
        },
    }


def test_i4_call_and_token_budget_is_conservative_and_frozen() -> None:
    budget = pricing_gate.compute_request_budget()
    assert budget["plan_business_calls"] == 10
    assert budget["report_business_calls"] == 20
    assert budget["stability_business_calls"] == 15
    assert budget["baseline_business_calls"] == 45
    assert budget["maximum_infrastructure_retries_per_business_call"] == 1
    assert budget["maximum_infrastructure_retries"] == 45
    assert budget["maximum_api_attempts"] == 90
    assert budget["content_error_retry_count"] == 0
    assert budget["plan_max_output_tokens_per_attempt"] == 8_000
    assert budget["report_max_output_tokens_per_attempt"] == 12_000
    assert budget["baseline_max_output_tokens"] == 500_000
    assert budget["retry_ceiling_max_output_tokens"] == 1_000_000
    assert budget["baseline_input_token_upper_bound"] > 0
    assert budget["retry_ceiling_input_token_upper_bound"] == (
        2 * budget["baseline_input_token_upper_bound"]
    )
    assert budget["baseline_total_token_upper_bound"] == (
        budget["baseline_input_token_upper_bound"] + 500_000
    )
    assert budget["retry_ceiling_total_token_upper_bound"] == (
        budget["retry_ceiling_input_token_upper_bound"] + 1_000_000
    )
    assert budget["input_token_upper_bound_basis"] == "serialized_prompt_utf8_bytes"
    assert budget["cache_assumption"] == "all_input_cache_miss"


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
        datetime(2026, 8, 31, 11, 50, tzinfo=timezone.utc)
    ) == "off_peak"


def test_snapshot_binds_i4_prices_budget_and_zero_external_effects() -> None:
    snapshot = _snapshot()
    assert snapshot["stage"] == "7R5-I4"
    assert snapshot["purpose"] == "i4_official_pricing_and_usd_authorization_gate"
    assert snapshot["checked_at"] == CHECKED_AT.isoformat()
    assert snapshot["expires_at"] == (CHECKED_AT + timedelta(hours=24)).isoformat()
    assert snapshot["source_url"] == "https://api-docs.deepseek.com/quick_start/pricing/"
    assert snapshot["model"] == "deepseek-v4-flash"
    assert snapshot["model_version_shown_by_provider"] == "DeepSeek-V4-Flash-0731"
    assert snapshot["official_model_supported"] is True
    assert snapshot["selected_tier"] == "off_peak"
    assert snapshot["usd_per_million_tokens"] == OFF_PEAK_RATES
    assert snapshot["off_peak_usd_per_million_tokens"] == OFF_PEAK_RATES
    assert snapshot["peak_usd_per_million_tokens"] == PEAK_RATES
    assert snapshot["authorization_gate"]["monetary_cap_usd"] is None
    assert snapshot["authorization_gate"]["real_run_allowed"] is False
    assert snapshot["authorization_gate"]["explicit_usd_amount_required"] is True
    assert snapshot["authorization_gate"]["bind_i4_snapshot_and_model"] is True
    assert snapshot["external_effects"] == pricing_gate.ZERO_EXTERNAL_EFFECTS


def test_costs_use_cache_miss_and_peak_retry_ceiling_for_authorization_floor() -> None:
    snapshot = _snapshot()
    budget = snapshot["call_budget"]
    expected_off_peak_baseline = (
        Decimal(budget["baseline_input_token_upper_bound"]) * Decimal("0.22")
        + Decimal("500000") * Decimal("0.66")
    ) / Decimal("1000000")
    expected_peak_retry = (
        Decimal(budget["retry_ceiling_input_token_upper_bound"]) * Decimal("0.44")
        + Decimal("1000000") * Decimal("1.32")
    ) / Decimal("1000000")
    assert Decimal(str(snapshot["cost_estimates_usd"]["off_peak_baseline"])) == (
        expected_off_peak_baseline.quantize(Decimal("0.00000001"))
    )
    assert Decimal(str(snapshot["cost_estimates_usd"]["peak_retry_ceiling"])) == (
        expected_peak_retry.quantize(Decimal("0.00000001"))
    )
    assert snapshot["authorization_gate"]["minimum_required_usd"] >= snapshot[
        "cost_estimates_usd"
    ]["peak_retry_ceiling"]
    assert snapshot["authorization_gate"]["suggested_hard_cap_usd"] >= snapshot[
        "authorization_gate"
    ]["minimum_required_usd"]


def test_snapshot_validation_rejects_expiry_model_tier_price_and_authorization() -> None:
    snapshot = _snapshot()
    assert pricing_gate.validate_pricing_snapshot(
        snapshot, now=CHECKED_AT + timedelta(hours=23, minutes=59)
    )["selected_tier"] == "off_peak"

    with pytest.raises(RuntimeError, match="过期"):
        pricing_gate.validate_pricing_snapshot(
            snapshot, now=CHECKED_AT + timedelta(hours=24, seconds=1)
        )

    for field, value, message in (
        ("model", "deepseek-v4-pro", "模型"),
        ("selected_tier", "peak", "时段"),
    ):
        tampered = json.loads(json.dumps(snapshot))
        tampered[field] = value
        with pytest.raises(RuntimeError, match=message):
            pricing_gate.validate_pricing_snapshot(tampered, now=CHECKED_AT)

    lowered_peak = json.loads(json.dumps(snapshot))
    lowered_peak["peak_usd_per_million_tokens"]["output"] = 0.66
    with pytest.raises(RuntimeError, match="费用"):
        pricing_gate.validate_pricing_snapshot(lowered_peak, now=CHECKED_AT)

    premature = json.loads(json.dumps(snapshot))
    premature["authorization_gate"]["monetary_cap_usd"] = 2
    premature["authorization_gate"]["real_run_allowed"] = True
    with pytest.raises(RuntimeError, match="不得提前"):
        pricing_gate.validate_pricing_snapshot(premature, now=CHECKED_AT)


def test_future_authorization_requires_bound_usd_amount_and_fresh_unchanged_gate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pricing.json"
    snapshot = _snapshot()
    pricing_gate.write_pricing_snapshot(path, snapshot)
    snapshot_sha256 = pricing_gate.sha256_file(path)
    minimum = snapshot["authorization_gate"]["minimum_required_usd"]
    authorization = {
        "stage": "7R5-I4",
        "pricing_snapshot_path": str(path),
        "pricing_snapshot_sha256": snapshot_sha256,
        "model": "deepseek-v4-flash",
        "selected_tier": "off_peak",
        "monetary_cap_usd": minimum,
        "explicit_user_authorization": True,
    }
    validated = pricing_gate.validate_future_real_authorization(
        snapshot,
        authorization,
        snapshot_path=path,
        now=CHECKED_AT + timedelta(minutes=1),
        observed_model="deepseek-v4-flash",
        observed_tier="off_peak",
        observed_off_peak_rates=OFF_PEAK_RATES,
        observed_peak_rates=PEAK_RATES,
    )
    assert validated["monetary_cap_usd"] == minimum

    too_low = dict(authorization)
    too_low["monetary_cap_usd"] = minimum - 0.01
    with pytest.raises(RuntimeError, match="低于"):
        pricing_gate.validate_future_real_authorization(
            snapshot,
            too_low,
            snapshot_path=path,
            now=CHECKED_AT + timedelta(minutes=1),
            observed_model="deepseek-v4-flash",
            observed_tier="off_peak",
            observed_off_peak_rates=OFF_PEAK_RATES,
            observed_peak_rates=PEAK_RATES,
        )

    changed_tier = dict(authorization)
    changed_tier["selected_tier"] = "peak"
    with pytest.raises(RuntimeError, match="返回 CLOSE-06R2-B"):
        pricing_gate.validate_future_real_authorization(
            snapshot,
            changed_tier,
            snapshot_path=path,
            now=CHECKED_AT + timedelta(minutes=1),
            observed_model="deepseek-v4-flash",
            observed_tier="peak",
            observed_off_peak_rates=OFF_PEAK_RATES,
            observed_peak_rates=PEAK_RATES,
        )


def test_pricing_snapshot_is_write_once(tmp_path: Path) -> None:
    path = tmp_path / "pricing.json"
    pricing_gate.write_pricing_snapshot(path, _snapshot())
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        pricing_gate.write_pricing_snapshot(path, _snapshot())
