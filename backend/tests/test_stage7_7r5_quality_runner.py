from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5_quality as runner  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402
from app.adapters.screening_evaluation import (  # noqa: E402
    ScreeningEvaluationAdapterResult,
    ScreeningEvaluationInputError,
    ScreeningEvaluationTimeoutError,
)


def _pricing_snapshot(*, age: timedelta = timedelta()) -> dict:
    return {
        "checked_at": (datetime.now(timezone.utc) - age).isoformat(),
        "source_url": contract.OFFICIAL_PRICING_SOURCE_URL,
        "model": contract.PLANNED_MODEL,
        "selected_tier": "peak",
        "schedule": "工作日北京时间 9:00-12:00、14:00-18:00",
        "usd_per_million_tokens": {
            "cache_hit_input": 0.014,
            "cache_miss_input": 0.44,
            "output": 1.32,
        },
    }


def test_frozen_fixture_hashes_denominators_and_call_budget_are_exact() -> None:
    fixture = contract.validate_frozen_fixture()
    assert fixture["plan_case_count"] == 10
    assert fixture["report_case_count"] == 20
    assert fixture["stability_case_count"] == 5
    assert fixture["stability_runs_per_case"] == 3
    assert fixture["manual_direction_denominators"] == {
        "high_match": 8,
        "partial_match": 6,
        "low_match": 6,
    }
    assert fixture["plan_required_label_denominator"] == 55
    assert fixture["plan_non_evaluation_label_denominator"] == 26
    assert fixture["plan_forbidden_addition_denominator"] == 22
    assert fixture["report_required_direction_denominator"] == 107
    assert fixture["failed_cases_remain_in_denominator"] is True

    budget = contract.call_budget()
    assert budget["baseline_business_calls"] == 45
    assert budget["maximum_api_attempts"] == 90
    assert budget["content_error_retry_count"] == 0
    assert budget["baseline_max_output_tokens"] == 500_000
    assert budget["retry_ceiling_max_output_tokens"] == 1_000_000


def test_execution_contract_freezes_model_prompt_schema_and_parameters() -> None:
    assert contract.execution_contract() == {
        "model": "deepseek-v4-flash",
        "temperature": 0.1,
        "thinking": "disabled",
        "response_format": "json_object",
        "sdk_automatic_retries": 0,
        "plan_prompt_version": "job_evaluation_plan_lightweight_v2",
        "report_prompt_version": "screening_evaluation_lightweight_v1",
        "plan_schema_version": "5.0",
        "report_schema_version": "5.0",
        "normal_business_calls_per_sample": 1,
    }


def test_human_audit_contract_freezes_all_semantic_denominators() -> None:
    audit = contract.human_audit_contract()
    assert audit["method"] == "human_review_against_frozen_labels"
    assert audit["llm_as_judge_is_sufficient"] is False
    assert audit["metrics"]["plan_required_covered_count"] == {
        "minimum": 55,
        "maximum": 55,
    }
    assert audit["metrics"]["report_direction_consistent_count"]["maximum"] == 20
    assert audit["metrics"]["required_direction_consistent_count"]["maximum"] == 107
    assert set(audit["metrics"]) == {
        "plan_required_covered_count",
        "plan_forbidden_addition_count",
        "plan_sensitive_criterion_count",
        "plan_non_evaluation_misclassified_count",
        "report_fabricated_fact_count",
        "report_severe_fact_error_count",
        "report_sensitive_scoring_count",
        "report_automatic_decision_count",
        "report_direction_consistent_count",
        "required_direction_consistent_count",
        "stability_severe_fact_error_count",
        "stability_sensitive_scoring_count",
    }


def test_historical_quality_evidence_hashes_are_unchanged() -> None:
    assert contract.validate_historical_results() == contract.HISTORICAL_RESULT_HASHES


def test_new_result_paths_are_isolated_empty_and_non_overwriting() -> None:
    isolation = contract.validate_result_path_isolation(require_empty=True)
    assert isolation["existing"] == []
    assert isolation["overlap_count"] == 0
    assert all("v5-quality-results" in path for path in isolation["paths"].values())


def test_write_new_json_only_accepts_registered_new_path_and_never_overwrites(
    tmp_path: Path,
) -> None:
    paths = {
        "raw": str(tmp_path / "raw.json"),
        "human_audit": str(tmp_path / "human.json"),
        "final": str(tmp_path / "final.json"),
    }
    with patch.object(contract, "result_paths", return_value=paths):
        contract.write_new_json(Path(paths["raw"]), {"ok": True})
        assert json.loads(Path(paths["raw"]).read_text(encoding="utf-8")) == {
            "ok": True
        }
        with pytest.raises(RuntimeError, match="拒绝覆盖"):
            contract.write_new_json(Path(paths["raw"]), {"ok": False})
        with pytest.raises(RuntimeError, match="未登记"):
            contract.write_new_json(tmp_path / "historical.json", {})


def test_dry_run_has_zero_calls_zero_writes_and_does_not_load_settings() -> None:
    with patch.object(runner, "get_settings", side_effect=AssertionError("不应读取配置")):
        payload = runner.dry_run_payload()
    assert payload["real_model_call_count"] == 0
    assert payload["adapter_instantiated"] is False
    assert payload["api_key_read"] is False
    assert payload["formal_result_write_count"] == 0
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_audit_contract"] == contract.human_audit_contract()


def test_offline_settings_ignores_environment_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "must-not-enter-fake-run")
    assert runner._offline_settings().DEEPSEEK_API_KEY == ""


def test_fake_normal_runs_full_service_contract_without_key_network_or_writes() -> None:
    with patch.object(runner, "get_settings", side_effect=AssertionError("不应读取默认配置")):
        payload = asyncio.run(runner.fake_payload(failure=False))
    assert len(payload["plan_records"]) == 10
    assert len(payload["report_records"]) == 20
    assert len(payload["stability_records"]) == 15
    assert payload["summaries"]["plans"]["structure_legal_count"] == 10
    assert payload["summaries"]["reports"]["legal_report_count"] == 20
    assert payload["summaries"]["reports"]["nonzero_assessment_count"] == payload[
        "summaries"
    ]["reports"]["nonzero_with_evidence_count"]
    assert payload["summaries"]["reports"]["all_required_sections_count"] == 20
    assert payload["summaries"]["stability"]["direction_stable_group_count"] == 5
    assert payload["real_model_call_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["formal_result_write_count"] == 0
    assert payload["quality_conclusion_allowed"] is False


def test_fake_failure_is_rejected_without_content_retry_or_partial_write() -> None:
    payload = asyncio.run(runner.fake_payload(failure=True))
    assert payload["summaries"]["plans"]["structure_legal_count"] == 9
    assert payload["summaries"]["reports"]["legal_report_count"] < 20
    assert any(record["status"] == "failed" for record in payload["report_records"])
    assert payload["call_budget"]["content_error_retry_count"] == 0
    assert payload["real_model_call_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["quality_conclusion_allowed"] is False


def test_pricing_snapshot_requires_official_source_model_tier_and_freshness() -> None:
    validated = contract.validate_pricing_snapshot(_pricing_snapshot())
    assert validated["source_url"] == contract.OFFICIAL_PRICING_SOURCE_URL
    assert validated["model"] == contract.PLANNED_MODEL
    assert validated["selected_tier"] == "peak"
    with pytest.raises(RuntimeError, match="过期"):
        contract.validate_pricing_snapshot(_pricing_snapshot(age=timedelta(hours=25)))
    wrong_source = _pricing_snapshot()
    wrong_source["source_url"] = "https://example.invalid/pricing"
    with pytest.raises(RuntimeError, match="官方价格页"):
        contract.validate_pricing_snapshot(wrong_source)


def test_cost_estimate_uses_conservative_cache_miss_when_split_is_unavailable() -> None:
    pricing = contract.validate_pricing_snapshot(_pricing_snapshot())
    estimate = contract.estimate_attempt_cost_usd(
        pricing=pricing,
        input_tokens=1_000,
        cache_hit_input_tokens=None,
        cache_miss_input_tokens=None,
        output_tokens=500,
    )
    assert estimate["complete"] is True
    assert estimate["cache_split_conservative"] is True
    assert estimate["estimated_cost_usd"] == pytest.approx(0.0011)


def test_report_audit_retries_one_retryable_error_and_records_both_attempts() -> None:
    result = ScreeningEvaluationAdapterResult(
        content="{}", model="fake", finish_reason="stop", input_tokens=100, output_tokens=20
    )
    delegate = SimpleNamespace(
        evaluate_v5=AsyncMock(
            side_effect=[ScreeningEvaluationTimeoutError("timeout"), result]
        )
    )
    records: list[dict] = []
    guard = runner.CostGuard(
        pricing=contract.validate_pricing_snapshot(_pricing_snapshot()), cap_usd=None
    )
    adapter = runner.AuditedReportAdapter(delegate, records, guard, "R00")
    with patch.object(runner, "build_screening_evaluation_v5_messages", return_value=[]):
        observed = asyncio.run(adapter.evaluate_v5(any_input=True))
    assert observed is result
    assert [item["attempt_number"] for item in records] == [1, 2]
    assert [item["result"] for item in records] == ["failed", "succeeded"]
    assert records[0]["cost_estimate"]["reserved_cost_upper_bound_usd"] > 0
    assert guard.failed_attempt_reserve_usd == records[0]["cost_estimate"][
        "reserved_cost_upper_bound_usd"
    ]


def test_report_audit_does_not_retry_non_retryable_content_or_input_error() -> None:
    delegate = SimpleNamespace(
        evaluate_v5=AsyncMock(side_effect=ScreeningEvaluationInputError("invalid"))
    )
    records: list[dict] = []
    guard = runner.CostGuard(
        pricing=contract.validate_pricing_snapshot(_pricing_snapshot()), cap_usd=None
    )
    adapter = runner.AuditedReportAdapter(delegate, records, guard, "R00")
    with patch.object(runner, "build_screening_evaluation_v5_messages", return_value=[]):
        with pytest.raises(ScreeningEvaluationInputError):
            asyncio.run(adapter.evaluate_v5(any_input=True))
    assert len(records) == 1
    assert records[0]["attempt_number"] == 1
    assert guard.failed_attempt_reserve_usd > 0


def test_real_mode_checks_pricing_and_empty_paths_before_loading_settings(
    tmp_path: Path,
) -> None:
    stale = tmp_path / "stale-pricing.json"
    stale.write_text(
        json.dumps(_pricing_snapshot(age=timedelta(hours=25))), encoding="utf-8"
    )
    with patch.object(runner, "get_settings", side_effect=AssertionError("不能提前读取 Key")):
        with pytest.raises(RuntimeError, match="过期"):
            asyncio.run(
                runner.real_payload(pricing_path=stale, monetary_cap_usd=0.1)
            )


def test_cost_guard_blocks_before_next_attempt_can_exceed_cap() -> None:
    guard = runner.CostGuard(
        pricing=contract.validate_pricing_snapshot(_pricing_snapshot()),
        cap_usd=0.000001,
    )
    with pytest.raises(RuntimeError, match="超过用户确认金额上限"):
        guard.reserve({"large": "x" * 10_000}, contract.REPORT_MAX_OUTPUT_TOKENS)


def test_cost_guard_keeps_unknown_failed_attempt_reserve_in_cumulative_spend() -> None:
    guard = runner.CostGuard(
        pricing=contract.validate_pricing_snapshot(_pricing_snapshot()), cap_usd=1.0
    )
    reserved = guard.reserve({"input": "冻结样本"}, 100)
    retained = guard.retain_failed_reservation()
    assert retained == reserved
    assert guard.failed_attempt_reserve_usd == reserved
    assert guard.estimated_spend_usd == reserved


def _valid_raw_result() -> dict:
    return {
        "stage": "7R5-I",
        "mode": "real_raw",
        "fixture": {"hashes": {"fixture": contract.FROZEN_FIXTURE_SHA256}},
        "execution_contract": contract.execution_contract(),
        "call_budget": contract.call_budget(),
        "attempt_audit_summary": {"api_attempt_count": 2},
        "attempt_audit": [
            {
                "case_id": "P00",
                "attempt_number": 1,
                "result": "failed",
                "raw_response": None,
            },
            {
                "case_id": "P00",
                "attempt_number": 2,
                "result": "succeeded",
                "raw_response": "{}",
            },
        ],
        "plan_records": [{} for _ in range(10)],
        "report_records": [{} for _ in range(20)],
        "stability_records": [{} for _ in range(15)],
        "historical_result_hashes_before": contract.HISTORICAL_RESULT_HASHES,
        "historical_result_hashes_after": contract.HISTORICAL_RESULT_HASHES,
        "quality_gate_passed": None,
        "quality_conclusion_allowed": False,
    }


def test_finalize_raw_gate_requires_frozen_contract_denominators_and_attempt_limit() -> None:
    raw = _valid_raw_result()
    runner._validate_raw_result_for_finalize(raw)
    raw["report_records"].pop()
    with pytest.raises(RuntimeError, match="固定分母不完整"):
        runner._validate_raw_result_for_finalize(raw)


def test_finalize_raw_gate_rejects_content_retry_beyond_one_extra_attempt() -> None:
    raw = _valid_raw_result()
    raw["attempt_audit"].append(
        {
            "case_id": "P00",
            "attempt_number": 3,
            "result": "succeeded",
            "raw_response": "{}",
        }
    )
    raw["attempt_audit_summary"]["api_attempt_count"] = 3
    with pytest.raises(RuntimeError, match="重试上限非法"):
        runner._validate_raw_result_for_finalize(raw)


def test_finalize_combines_deterministic_and_frozen_human_gates(
    tmp_path: Path,
) -> None:
    raw = _valid_raw_result()
    raw["summaries"] = {
        "plans": {"structure_legal_count": 10, "traceable_plan_count": 10},
        "reports": {
            "legal_report_count": 20,
            "nonzero_assessment_count": 50,
            "nonzero_with_evidence_count": 50,
            "all_required_sections_count": 20,
        },
        "stability": {
            "direction_stable_group_count": 5,
            "max_difference_le_10_group_count": 5,
            "extreme_direction_flip_count": 0,
        },
    }
    raw_path = tmp_path / "raw.json"
    human_path = tmp_path / "human.json"
    final_path = tmp_path / "final.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    metrics = {
        "plan_required_covered_count": 55,
        "plan_forbidden_addition_count": 0,
        "plan_sensitive_criterion_count": 0,
        "plan_non_evaluation_misclassified_count": 0,
        "report_fabricated_fact_count": 0,
        "report_severe_fact_error_count": 0,
        "report_sensitive_scoring_count": 0,
        "report_automatic_decision_count": 0,
        "report_direction_consistent_count": 16,
        "required_direction_consistent_count": 97,
        "stability_severe_fact_error_count": 0,
        "stability_sensitive_scoring_count": 0,
    }
    human_path.write_text(
        json.dumps(
            {
                "raw_result_sha256": contract.sha256_file(raw_path),
                "fixture_sha256": contract.FROZEN_FIXTURE_SHA256,
                "method": "human_review_against_frozen_labels",
                "auditor": "fixture-human-reviewer",
                "audited_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
            }
        ),
        encoding="utf-8",
    )
    written: dict = {}

    def capture(path: Path, payload: dict) -> None:
        written["path"] = path
        written["payload"] = payload

    with (
        patch.object(runner, "RAW_RESULT_PATH", raw_path),
        patch.object(runner, "HUMAN_AUDIT_PATH", human_path),
        patch.object(runner, "FINAL_RESULT_PATH", final_path),
        patch.object(runner, "write_new_json", side_effect=capture),
    ):
        result = runner.finalize_payload()
    assert result["quality_gate_passed"] is True
    assert all(result["gates"].values())
    assert written == {"path": final_path, "payload": result}
