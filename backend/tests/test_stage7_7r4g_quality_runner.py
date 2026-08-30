from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))

from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
    JobEvaluationPlanAuthenticationError,
    JobEvaluationPlanInvalidResponseError,
    JobEvaluationPlanTimeoutError,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanV4GenerationError,
    job_evaluation_plan_service,
)


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = _load("stage7_7r4_quality_contract_test", "stage7_7r4_quality_contract.py")
runner = _load("stage7_7r4_plan_quality_test", "run_stage7_7r4_plan_quality.py")
report_runner = _load(
    "stage7_7r4_report_quality_test", "run_stage7_7r4_report_quality.py"
)


def _pricing_snapshot() -> dict:
    return contract.validate_official_pricing_snapshot(
        {
            "checked_at": "2026-08-25T11:41:01+08:00",
            "source_url": contract.OFFICIAL_PRICING_SOURCE_URL,
            "selected_tier": "peak",
            "peak_schedule": "工作日北京时间 9:00-12:00、14:00-18:00",
            "usd_per_million_tokens": {
                "off_peak": {
                    "cache_hit_input": 0.007,
                    "cache_miss_input": 0.22,
                    "output": 0.66,
                },
                "peak": {
                    "cache_hit_input": 0.014,
                    "cache_miss_input": 0.44,
                    "output": 1.32,
                },
            },
        }
    )


def _valid_attempt_audit(
    *,
    repair_case_ids: tuple[str, ...] = (),
    selected_case_ids: tuple[str, ...] = contract.TARGETED_CASE_IDS,
) -> tuple[list[dict], dict, list[dict]]:
    attempts = []
    cases = []
    business_call_number = 0
    for case_id in selected_case_ids:
        roles = (
            ["fact_extraction"]
            if case_id == "J5-19"
            else [
                "fact_extraction",
                "coverage_review",
                *(["local_repair"] if case_id in repair_case_ids else []),
                "criterion_grouping",
            ]
        )
        for case_attempt_number, role in enumerate(
            roles,
            start=1,
        ):
            business_call_number += 1
            cost = contract.estimate_attempt_cost_usd(
                pricing_snapshot=_pricing_snapshot(),
                input_tokens=100,
                cache_hit_input_tokens=40,
                cache_miss_input_tokens=60,
                output_tokens=50,
            )
            attempts.append(
                {
                    "case_id": case_id,
                    "role": role,
                    "attempt_number": len(attempts) + 1,
                    "case_attempt_number": case_attempt_number,
                    "business_call_number": business_call_number,
                    "is_infrastructure_retry": False,
                    "requested_model": contract.PLANNED_MODEL,
                    "thinking": "disabled",
                    "temperature": 0.1,
                    "response_format": "json_object",
                    "max_output_tokens": 16_000,
                    "sdk_automatic_retries": 0,
                    "prompt_version": contract.EXPECTED_PLAN_PROMPT_VERSIONS[role],
                    "result": "succeeded",
                    "error_code": None,
                    "retryable": False,
                    "model": "DeepSeek-V4-Flash-0731",
                    "finish_reason": "stop",
                    "input_tokens": 100,
                    "cache_hit_input_tokens": 40,
                    "cache_miss_input_tokens": 60,
                    "output_tokens": 50,
                    "raw_response": "{}",
                    "duration_ms": 10.0,
                    "cost_estimate": cost,
                }
            )
        generation_calls = [
            {
                "role": role,
                "prompt_version": contract.EXPECTED_PLAN_PROMPT_VERSIONS[role],
                "model": contract.PLANNED_MODEL,
                "input_tokens": 100,
                "output_tokens": 50,
                "duration_ms": 10,
                "infrastructure_retry_count": 0,
                "result": (
                    "failed"
                    if case_id == "J5-19" and role == "fact_extraction"
                    else "succeeded"
                ),
                "error_code": (
                    "JOB_EVALUATION_PLAN_NO_FACTS"
                    if case_id == "J5-19" and role == "fact_extraction"
                    else None
                ),
            }
            for role in roles
        ]
        cases.append(
            {
                "case_id": case_id,
                "actual_outcome": contract.EXPECTED_V4_OUTCOMES[case_id],
                "generation_audit": {
                    "business_call_count": len(generation_calls),
                    "content_repair_count": sum(
                        call["role"] == "local_repair" for call in generation_calls
                    ),
                    "infrastructure_retry_count": 0,
                    "calls": generation_calls,
                },
            }
        )
    total_cost = sum(
        attempt["cost_estimate"]["estimated_cost_usd"] for attempt in attempts
    )
    budget = (
        contract.plan_call_budget()["targeted"]
        if selected_case_ids == contract.TARGETED_CASE_IDS
        else contract.plan_call_budget()["formal"]
    )
    summary = {
        "adapter_attempt_count": len(attempts),
        "business_call_count": len(attempts),
        "infrastructure_retry_count": 0,
        "content_repair_count": len(repair_case_ids),
        "succeeded_attempt_count": len(attempts),
        "failed_attempt_count": 0,
        "priced_attempt_count": len(attempts),
        "unpriced_attempt_count": 0,
        "estimated_cost_usd": total_cost,
        "monetary_cap_usd": None,
        "maximum_business_calls": budget["safety_hard_maximum_business_calls"],
        "maximum_api_attempts": budget[
            "maximum_api_attempts_with_infrastructure_retries"
        ],
        "stopped_reason": None,
    }
    return attempts, summary, cases


def _valid_targeted_payload(*, repair_case_ids: tuple[str, ...] = ()) -> dict:
    attempts, attempt_summary, cases = _valid_attempt_audit(
        repair_case_ids=repair_case_ids
    )
    return {
        "stage": "7R4-HR2",
        "result_kind": "plan_quality_targeted_revalidation",
        "status": "formal",
        "plan_schema_version": "4.0",
        "frozen_case_sha256": contract.FROZEN_CASE_SHA256,
        "selected_case_ids": list(contract.TARGETED_CASE_IDS),
        "model": contract.PLANNED_MODEL,
        "prompt_versions": contract.EXPECTED_PLAN_PROMPT_VERSIONS,
        "model_parameters": contract.model_execution_contract(),
        "official_pricing_snapshot": _pricing_snapshot(),
        "attempt_audit_summary": attempt_summary,
        "attempt_audit": attempts,
        "cases": cases,
        "summary": {
            "business_call_count": attempt_summary["business_call_count"],
            "content_repair_count": attempt_summary["content_repair_count"],
            "infrastructure_retry_count": attempt_summary[
                "infrastructure_retry_count"
            ],
            "sample_contract_denominator": 6,
            "sample_contract_passed_count": 6,
            "manual_fact_denominator": 80,
            "manual_fact_recalled_count": 80,
            "manual_fact_recall_rate": 1.0,
            "explicit_required_denominator": 23,
            "explicit_required_recalled_count": 23,
            "explicit_required_recall_rate": 1.0,
            "source_unit_denominator": 90,
            "reviewed_source_unit_count": 90,
            "source_review_rate": 1.0,
            "fact_count": 80,
            "traceable_fact_count": 80,
            "source_traceability_rate": 1.0,
            "priority_consistent_fact_count": 80,
            "priority_consistency_rate": 1.0,
            "criterion_covered_fact_count": 80,
            "criterion_coverage_rate": 1.0,
            "normal_ready_denominator": 4,
            "normal_ready_count": 4,
            "boundary_denominator": 2,
            "boundary_correct_count": 2,
            "expected_warning_count": 2,
            "expected_warning_hit_count": 2,
            "expected_warning_hit_rate": 1.0,
            "added_requirement_count": 0,
            "source_merge_failure_count": 0,
            "incorrect_merge_count": 0,
            "obvious_duplicate_count": 0,
            "background_or_public_notes_pollution_count": 0,
            "promotion_or_benefit_misclassified_count": 0,
        },
        "targeted_gate_passed": True,
        "quality_conclusion_allowed": True,
    }


def _with_infrastructure_retry(
    payload: dict,
    *,
    case_id: str,
    role: str,
    retry_count: int,
) -> dict:
    mutated = deepcopy(payload)
    attempts = mutated["attempt_audit"]
    target_index = next(
        index
        for index, attempt in enumerate(attempts)
        if attempt["case_id"] == case_id and attempt["role"] == role
    )
    successful_attempt = deepcopy(attempts[target_index])
    failed_attempts = []
    for retry_index in range(retry_count):
        failed = deepcopy(successful_attempt)
        failed.update(
            {
                "is_infrastructure_retry": retry_index > 0,
                "result": "failed",
                "error_code": "JOB_EVALUATION_PLAN_TIMEOUT",
                "retryable": True,
                "model": None,
                "finish_reason": None,
                "input_tokens": None,
                "cache_hit_input_tokens": None,
                "cache_miss_input_tokens": None,
                "output_tokens": None,
                "raw_response": None,
            }
        )
        failed["cost_estimate"] = contract.estimate_attempt_cost_usd(
            pricing_snapshot=mutated["official_pricing_snapshot"],
            input_tokens=None,
            cache_hit_input_tokens=None,
            cache_miss_input_tokens=None,
            output_tokens=None,
        )
        failed_attempts.append(failed)
    successful_attempt["is_infrastructure_retry"] = True
    attempts[target_index : target_index + 1] = [
        *failed_attempts,
        successful_attempt,
    ]

    case_attempt_numbers: dict[str, int] = {}
    business_call_number = 0
    for attempt_number, attempt in enumerate(attempts, start=1):
        attempt["attempt_number"] = attempt_number
        case_attempt_numbers[attempt["case_id"]] = (
            case_attempt_numbers.get(attempt["case_id"], 0) + 1
        )
        attempt["case_attempt_number"] = case_attempt_numbers[attempt["case_id"]]
        if not attempt["is_infrastructure_retry"]:
            business_call_number += 1
        attempt["business_call_number"] = business_call_number

    case = next(case for case in mutated["cases"] if case["case_id"] == case_id)
    call = next(
        call for call in case["generation_audit"]["calls"] if call["role"] == role
    )
    call["infrastructure_retry_count"] = retry_count
    case["generation_audit"]["infrastructure_retry_count"] = retry_count

    attempt_summary = mutated["attempt_audit_summary"]
    attempt_summary["adapter_attempt_count"] += retry_count
    attempt_summary["infrastructure_retry_count"] += retry_count
    attempt_summary["failed_attempt_count"] += retry_count
    attempt_summary["unpriced_attempt_count"] += retry_count
    mutated["summary"]["infrastructure_retry_count"] += retry_count
    return mutated


def test_official_pricing_and_cache_split_cost_are_recalculable() -> None:
    cost = contract.estimate_attempt_cost_usd(
        pricing_snapshot=_pricing_snapshot(),
        input_tokens=100,
        cache_hit_input_tokens=40,
        cache_miss_input_tokens=60,
        output_tokens=50,
    )
    assert cost["complete"] is True
    assert cost["estimated_cost_usd"] == pytest.approx(9.296e-05)
    incomplete = contract.estimate_attempt_cost_usd(
        pricing_snapshot=_pricing_snapshot(),
        input_tokens=100,
        cache_hit_input_tokens=40,
        cache_miss_input_tokens=59,
        output_tokens=50,
    )
    assert incomplete == {
        "complete": False,
        "estimated_cost_usd": None,
        "reason": "provider_cache_token_split_mismatch",
    }


def test_real_run_rejects_stale_official_pricing_snapshot() -> None:
    args = runner.SimpleNamespace(
        confirm_no_monetary_cap=True,
        official_price_checked_at="2026-08-24T08:00:00+08:00",
        pricing_tier="peak",
        peak_schedule="工作日北京时间 9:00-12:00、14:00-18:00",
        off_peak_cache_hit_price=0.007,
        off_peak_cache_miss_price=0.22,
        off_peak_output_price=0.66,
        peak_cache_hit_price=0.014,
        peak_cache_miss_price=0.44,
        peak_output_price=1.32,
    )
    with pytest.raises(SystemExit, match="超过 1 小时"):
        runner._pricing_snapshot_from_args(args)


def test_recording_adapter_keeps_finish_cache_cost_and_failed_raw_response() -> None:
    ledger = runner.QualityRunAuditLedger(_pricing_snapshot())
    raw_success = '{"status":"passed","findings":[]}'
    successful = JobEvaluationPlanAdapterResult(
        content=raw_success,
        model="DeepSeek-V4-Flash-0731",
        finish_reason="stop",
        input_tokens=100,
        cache_hit_input_tokens=40,
        cache_miss_input_tokens=60,
        output_tokens=50,
    )
    delegate = Mock()
    delegate.generate_v4 = AsyncMock(
        side_effect=[
            JobEvaluationPlanTimeoutError("temporary"),
            successful,
            JobEvaluationPlanInvalidResponseError(
                "invalid",
                raw_response='{"schema_version":"3.0"}',
                model="DeepSeek-V4-Flash-0731",
                finish_reason="stop",
                input_tokens=80,
                cache_hit_input_tokens=20,
                cache_miss_input_tokens=60,
                output_tokens=10,
            ),
        ]
    )
    adapter = runner.RecordingAdapter(
        delegate,
        case_id="J5-03",
        ledger=ledger,
    )
    with pytest.raises(JobEvaluationPlanTimeoutError):
        asyncio.run(adapter.generate_v4("fact_extraction", {}))
    asyncio.run(adapter.generate_v4("fact_extraction", {}))
    with pytest.raises(JobEvaluationPlanInvalidResponseError):
        asyncio.run(adapter.generate_v4("coverage_review", {}))

    assert [item["attempt_number"] for item in adapter.attempts] == [1, 2, 3]
    assert adapter.attempts[1]["is_infrastructure_retry"] is True
    assert adapter.attempts[1]["finish_reason"] == "stop"
    assert adapter.attempts[1]["cache_hit_input_tokens"] == 40
    assert adapter.attempts[1]["cache_miss_input_tokens"] == 60
    assert adapter.attempts[1]["cost_estimate"]["complete"] is True
    assert adapter.attempts[1]["raw_response"] == raw_success
    assert "schema_version" not in adapter.attempts[1]["raw_response"]
    assert adapter.attempts[2]["raw_response"] == '{"schema_version":"3.0"}'
    assert adapter.attempts[2]["cost_estimate"]["complete"] is True
    assert ledger.summary()["business_call_count"] == 2
    assert ledger.summary()["infrastructure_retry_count"] == 1


def test_global_24_business_and_48_attempt_budgets_stop_before_extra_call() -> None:
    ledger = runner.QualityRunAuditLedger(_pricing_snapshot())
    for index in range(24):
        case_id = f"case-{index:02d}"
        first = ledger.reserve(case_id=case_id, role="fact_extraction")
        ledger.append(
            {
                **first,
                "result": "failed",
                "retryable": True,
                "input_tokens": None,
                "cache_hit_input_tokens": None,
                "cache_miss_input_tokens": None,
                "output_tokens": None,
            }
        )
        retry = ledger.reserve(case_id=case_id, role="fact_extraction")
        ledger.append(
            {
                **retry,
                "result": "succeeded",
                "retryable": False,
                "input_tokens": 1,
                "cache_hit_input_tokens": 0,
                "cache_miss_input_tokens": 1,
                "output_tokens": 1,
            }
        )
    assert ledger.summary()["business_call_count"] == 24
    assert ledger.summary()["adapter_attempt_count"] == 48
    with pytest.raises(runner.QualityRunCallBudgetExceeded):
        ledger.reserve(case_id="one-too-many", role="fact_extraction")
    assert ledger.stopped_reason == "api_attempt_budget_exhausted"


def test_one_business_call_cannot_retry_twice() -> None:
    ledger = runner.QualityRunAuditLedger(_pricing_snapshot())
    first = ledger.reserve(case_id="J5-03", role="fact_extraction")
    ledger.append(
        {
            **first,
            "result": "failed",
            "retryable": True,
            "input_tokens": None,
            "cache_hit_input_tokens": None,
            "cache_miss_input_tokens": None,
            "output_tokens": None,
        }
    )
    retry = ledger.reserve(case_id="J5-03", role="fact_extraction")
    ledger.append(
        {
            **retry,
            "result": "failed",
            "retryable": True,
            "input_tokens": None,
            "cache_hit_input_tokens": None,
            "cache_miss_input_tokens": None,
            "output_tokens": None,
        }
    )

    with pytest.raises(runner.QualityRunCallBudgetExceeded):
        ledger.reserve(case_id="J5-03", role="fact_extraction")
    assert ledger.stopped_reason == "per_business_call_retry_budget_exhausted"


def test_frozen_plan_fixture_and_denominators_do_not_drift() -> None:
    fixture = runner._fixture_and_versions()
    assert fixture["formal_case_ids"] == [f"J5-{index:02d}" for index in range(1, 21)]
    assert fixture["targeted_case_ids"] == [
        "J5-03",
        "J5-07",
        "J5-14",
        "J5-17",
        "J5-19",
        "J5-20",
    ]
    assert fixture["frozen_case_sha256"] == (
        "23651a92bb68602f096cf30519d5c11cd2ce6e724950f158587ba201e41fdfe0"
    )
    assert fixture["manual_fact_denominator"] == 245
    assert fixture["explicit_required_denominator"] == 97
    assert fixture["targeted_manual_fact_denominator"] == 80
    assert fixture["targeted_explicit_required_denominator"] == 23
    assert fixture["source_unit_denominator"] == 255
    assert fixture["targeted_source_unit_denominator"] == 90


def test_dry_run_is_keyless_adapterless_and_write_free() -> None:
    identities_before = contract.validate_historical_results()
    existing_before = {
        path: path.exists()
        for path in (
            contract.PLAN_TARGETED_RESULT_PATH,
            contract.PLAN_FORMAL_RESULT_PATH,
            contract.REPORT_TARGETED_RESULT_PATH,
            contract.REPORT_FORMAL_RESULT_PATH,
        )
    }
    sentinel = Mock(side_effect=AssertionError("dry-run instantiated real adapter"))
    with patch.object(runner, "DeepSeekJobEvaluationPlanAdapter", sentinel):
        payload = runner.dry_run_payload()
    assert payload["real_model_call_count"] == 0
    assert payload["formal_quality_result_write_count"] == 0
    assert payload["adapter_instantiated"] is False
    assert payload["api_key_read_as_prerequisite"] is False
    assert payload["writes_result_file"] is False
    assert sentinel.call_count == 0
    assert contract.validate_historical_results() == identities_before
    assert {
        path: path.exists() for path in existing_before
    } == existing_before


def test_plan_call_budget_separates_business_repair_and_infrastructure_attempts() -> None:
    budget = contract.plan_call_budget()
    assert budget["targeted"] == {
        "sample_count": 6,
        "normal_plan_count": 5,
        "no_facts_short_circuit_count": 1,
        "baseline_business_calls": 16,
        "maximum_business_calls_with_local_repair": 21,
        "safety_hard_maximum_business_calls": 24,
        "maximum_api_attempts_with_infrastructure_retries": 48,
        "maximum_output_tokens_without_infrastructure_retries": 336_000,
        "maximum_output_tokens_with_infrastructure_retries": 768_000,
    }
    assert budget["formal"]["baseline_business_calls"] == 58
    assert budget["formal"]["maximum_business_calls_with_local_repair"] == 77
    assert budget["formal"]["safety_hard_maximum_business_calls"] == 80
    assert budget["formal"]["maximum_api_attempts_with_infrastructure_retries"] == 160


def test_plan_attempt_audit_accepts_only_legal_baselines_and_repair_totals() -> None:
    targeted_baseline = contract.validate_plan_attempt_audit(
        _valid_targeted_payload()
    )
    assert targeted_baseline["business_call_count"] == 16

    targeted_repaired = contract.validate_plan_attempt_audit(
        _valid_targeted_payload(
            repair_case_ids=tuple(
                case_id
                for case_id in contract.TARGETED_CASE_IDS
                if case_id != "J5-19"
            )
        )
    )
    assert targeted_repaired["business_call_count"] == 21

    for repair_case_ids, expected_business_calls in (
        ((), 58),
        (
            tuple(
                case_id
                for case_id in contract.FORMAL_CASE_IDS
                if case_id != "J5-19"
            ),
            77,
        ),
    ):
        attempts, attempt_summary, cases = _valid_attempt_audit(
            repair_case_ids=repair_case_ids,
            selected_case_ids=contract.FORMAL_CASE_IDS,
        )
        formal_audit = contract.validate_plan_attempt_audit(
            {
                "selected_case_ids": list(contract.FORMAL_CASE_IDS),
                "official_pricing_snapshot": _pricing_snapshot(),
                "attempt_audit": attempts,
                "attempt_audit_summary": attempt_summary,
                "cases": cases,
                "summary": {
                    "business_call_count": expected_business_calls,
                    "content_repair_count": len(repair_case_ids),
                    "infrastructure_retry_count": 0,
                },
            }
        )
        assert formal_audit["business_call_count"] == expected_business_calls


def test_plan_attempt_audit_accepts_one_adjacent_infrastructure_retry() -> None:
    payload = _with_infrastructure_retry(
        _valid_targeted_payload(),
        case_id="J5-03",
        role="fact_extraction",
        retry_count=1,
    )
    audit = contract.validate_plan_attempt_audit(payload)
    assert audit["business_call_count"] == 16
    assert audit["infrastructure_retry_count"] == 1


def test_plan_attempt_audit_rejects_illegal_flow_and_forged_summaries() -> None:
    illegal_payloads = []

    short_flow = deepcopy(_valid_targeted_payload())
    short_flow["cases"][0]["generation_audit"]["calls"].pop()
    short_flow["cases"][0]["generation_audit"]["business_call_count"] -= 1
    illegal_payloads.append(short_flow)

    disordered = deepcopy(_valid_targeted_payload())
    disordered["cases"][0]["generation_audit"]["calls"][1:] = reversed(
        disordered["cases"][0]["generation_audit"]["calls"][1:]
    )
    illegal_payloads.append(disordered)

    no_facts_continued = deepcopy(_valid_targeted_payload())
    no_facts_case = next(
        case for case in no_facts_continued["cases"] if case["case_id"] == "J5-19"
    )
    extra_call = deepcopy(no_facts_case["generation_audit"]["calls"][0])
    extra_call.update(
        {
            "role": "coverage_review",
            "prompt_version": contract.EXPECTED_PLAN_PROMPT_VERSIONS[
                "coverage_review"
            ],
            "result": "succeeded",
            "error_code": None,
        }
    )
    no_facts_case["generation_audit"]["calls"].append(extra_call)
    no_facts_case["generation_audit"]["business_call_count"] += 1
    illegal_payloads.append(no_facts_continued)

    misplaced_repair = _valid_targeted_payload(repair_case_ids=("J5-03",))
    repair_calls = misplaced_repair["cases"][0]["generation_audit"]["calls"]
    repair_calls[2], repair_calls[3] = repair_calls[3], repair_calls[2]
    illegal_payloads.append(misplaced_repair)

    third_technical_attempt = _with_infrastructure_retry(
        _valid_targeted_payload(),
        case_id="J5-03",
        role="fact_extraction",
        retry_count=2,
    )
    illegal_payloads.append(third_technical_attempt)

    forged_quality_summary = deepcopy(_valid_targeted_payload())
    forged_quality_summary["summary"]["business_call_count"] += 1
    illegal_payloads.append(forged_quality_summary)

    forged_generation_summary = deepcopy(_valid_targeted_payload())
    forged_generation_summary["cases"][0]["generation_audit"][
        "business_call_count"
    ] += 1
    illegal_payloads.append(forged_generation_summary)

    for payload in illegal_payloads:
        with pytest.raises(RuntimeError):
            contract.validate_plan_attempt_audit(payload)
    assert contract.model_and_cost_inputs()["cost_estimate_inputs"][
        "official_price_check_required_before_7R4_H"
    ] is True
    assert contract.model_and_cost_inputs()["candidate_model_from_current_config"] == (
        "deepseek-v4-flash"
    )
    assert contract.model_and_cost_inputs()[
        "model_requires_separate_confirmation_before_7R4_H"
    ] is True


def test_fake_normal_and_repair_counts_come_from_generation_audit() -> None:
    normal = asyncio.run(runner.run_fake_scenario(repair=False))
    repaired = asyncio.run(runner.run_fake_scenario(repair=True))
    assert normal["actual_adapter_attempt_count"] == 3
    assert normal["generation_audit"]["business_call_count"] == 3
    assert normal["generation_audit"]["content_repair_count"] == 0
    assert repaired["actual_adapter_attempt_count"] == 4
    assert repaired["generation_audit"]["business_call_count"] == 4
    assert repaired["generation_audit"]["content_repair_count"] == 1
    assert repaired["generation_audit"]["infrastructure_retry_count"] == 0
    assert normal["quality_audit"]["sample_contract_passed"] is True
    assert normal["quality_audit"]["source_review_complete"] is True
    assert normal["quality_audit"]["criterion_coverage_ok"] is True
    assert normal["quality_audit"]["added_requirement_count"] == 0
    assert normal["real_model_call_count"] == repaired["real_model_call_count"] == 0


def test_fake_retry_and_content_failures_have_separate_actual_counts() -> None:
    case = next(case for case in runner.CASES if case["case_id"] == "J5-03")
    snapshot = job_evaluation_plan_service.build_v4_input_snapshot(
        runner._case_job(case, 3)
    )
    normal_outcomes = runner._fake_outcomes(case, snapshot, repair=False)
    retry_adapter = FakeJobEvaluationPlanAdapter(
        [JobEvaluationPlanTimeoutError("temporary"), *normal_outcomes]
    )
    retry_content = asyncio.run(
        job_evaluation_plan_service.build_v4_plan_content(
            snapshot,
            adapter=retry_adapter,
        )
    )
    assert len(retry_adapter.v4_calls) == 4
    assert retry_content.generation_audit.business_call_count == 3
    assert retry_content.generation_audit.content_repair_count == 0
    assert retry_content.generation_audit.infrastructure_retry_count == 1

    invalid_fact = json.loads(normal_outcomes[0].content)
    invalid_fact["fact_candidates"][0]["sources"][0]["source_quote"] = (
        "原文不存在的事实"
    )
    non_retryable_outcomes = (
        JobEvaluationPlanAuthenticationError("private upstream detail"),
        runner._adapter_result("not-json"),
        runner._adapter_result({"schema_version": "3.0"}),
        runner._adapter_result(invalid_fact),
    )
    for outcome in non_retryable_outcomes:
        adapter = FakeJobEvaluationPlanAdapter([outcome])
        with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
            asyncio.run(
                job_evaluation_plan_service.build_v4_plan_content(
                    snapshot,
                    adapter=adapter,
                )
            )
        assert len(adapter.v4_calls) == 1
        assert caught.value.generation_audit.business_call_count == 1
        assert caught.value.generation_audit.content_repair_count == 0
        assert caught.value.generation_audit.infrastructure_retry_count == 0


def test_expected_no_facts_boundary_still_audits_every_source_unit() -> None:
    case = next(case for case in runner.CASES if case["case_id"] == "J5-19")
    snapshot = job_evaluation_plan_service.build_v4_input_snapshot(
        runner._case_job(case, 19)
    )
    outcomes = runner._fake_outcomes(case, snapshot, repair=False)
    adapter = FakeJobEvaluationPlanAdapter(outcomes)
    with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
        asyncio.run(
            job_evaluation_plan_service.build_v4_plan_content(
                snapshot,
                adapter=adapter,
            )
        )
    audit = runner._audit_generation_error(
        case,
        snapshot,
        caught.value,
        [
            {"role": "fact_extraction", "result": "failed"},
            {
                "role": "fact_extraction",
                "result": "succeeded",
                "raw_response": outcomes[0].content,
            },
        ],
    )
    assert audit["actual_outcome"] == "no_facts"
    assert audit["source_review_complete"] is True
    assert audit["reviewed_source_unit_count"] == audit["source_unit_denominator"]
    assert audit["sample_contract_passed"] is True


def test_formal_gate_accepts_only_exact_new_v4_targeted_contract() -> None:
    accepted = contract.validate_targeted_gate_payload(
        _valid_targeted_payload(),
        source_path=contract.PLAN_TARGETED_RESULT_PATH,
    )
    assert accepted["targeted_gate_passed"] is True

    mutations = []
    failed = deepcopy(_valid_targeted_payload())
    failed["targeted_gate_passed"] = False
    mutations.append(failed)
    wrong_version = deepcopy(_valid_targeted_payload())
    wrong_version["plan_schema_version"] = "3.0"
    mutations.append(wrong_version)
    wrong_model = deepcopy(_valid_targeted_payload())
    wrong_model["model"] = "deepseek-v4-pro"
    mutations.append(wrong_model)
    wrong_thinking = deepcopy(_valid_targeted_payload())
    wrong_thinking["model_parameters"]["thinking"] = "enabled"
    mutations.append(wrong_thinking)
    wrong_prompt = deepcopy(_valid_targeted_payload())
    wrong_prompt["prompt_versions"]["coverage_review"] = "stale_prompt"
    mutations.append(wrong_prompt)
    wrong_samples = deepcopy(_valid_targeted_payload())
    wrong_samples["selected_case_ids"] = list(contract.TARGETED_CASE_IDS[:-1])
    mutations.append(wrong_samples)
    wrong_denominator = deepcopy(_valid_targeted_payload())
    wrong_denominator["summary"]["manual_fact_denominator"] = 79
    mutations.append(wrong_denominator)
    low_recall = deepcopy(_valid_targeted_payload())
    low_recall["summary"]["manual_fact_recall_rate"] = 0.94
    mutations.append(low_recall)
    untraceable = deepcopy(_valid_targeted_payload())
    untraceable["summary"]["source_traceability_rate"] = 0.99
    mutations.append(untraceable)
    polluted = deepcopy(_valid_targeted_payload())
    polluted["summary"]["background_or_public_notes_pollution_count"] = 1
    mutations.append(polluted)
    missed_warning = deepcopy(_valid_targeted_payload())
    missed_warning["summary"]["expected_warning_hit_rate"] = 0.5
    mutations.append(missed_warning)
    forged_recall_rate = deepcopy(_valid_targeted_payload())
    forged_recall_rate["summary"]["manual_fact_recalled_count"] = 75
    mutations.append(forged_recall_rate)
    forged_attempt_cost = deepcopy(_valid_targeted_payload())
    forged_attempt_cost["attempt_audit"][0]["cost_estimate"][
        "estimated_cost_usd"
    ] = 999.0
    mutations.append(forged_attempt_cost)
    missing_raw_evidence = deepcopy(_valid_targeted_payload())
    missing_raw_evidence["attempt_audit"][0]["raw_response"] = None
    mutations.append(missing_raw_evidence)
    forged_retry = deepcopy(_valid_targeted_payload())
    forged_retry["attempt_audit"][0]["is_infrastructure_retry"] = True
    mutations.append(forged_retry)
    forged_attempt_summary = deepcopy(_valid_targeted_payload())
    forged_attempt_summary["attempt_audit_summary"]["maximum_api_attempts"] = 49
    mutations.append(forged_attempt_summary)
    for payload in mutations:
        with pytest.raises(RuntimeError):
            contract.validate_targeted_gate_payload(
                payload,
                source_path=contract.PLAN_TARGETED_RESULT_PATH,
            )

    with pytest.raises(RuntimeError):
        contract.validate_targeted_gate_payload(
            _valid_targeted_payload(),
            source_path=contract.HISTORICAL_RESULT_PATHS[0],
        )


def test_missing_or_failed_formal_gate_blocks_before_adapter_factory() -> None:
    adapter_factory = Mock(side_effect=AssertionError("adapter must not be built"))
    with (
        patch.object(
            runner,
            "load_and_validate_targeted_gate",
            side_effect=RuntimeError("gate blocked"),
        ),
        patch.object(runner, "_build_real_adapter", adapter_factory),
    ):
        with pytest.raises(RuntimeError, match="gate blocked"):
            asyncio.run(runner._run_real("formal", contract.PLANNED_MODEL))
    assert adapter_factory.call_count == 0
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "--skip-gate" not in source
    assert "--targeted-result" not in source


def test_v4_result_paths_are_new_and_never_historical() -> None:
    isolation = contract.validate_result_path_isolation()
    assert isolation["overlap_count"] == 0
    # Whether HR2 exists is a run-lifecycle fact, not a permanent path contract:
    # it must be absent before HR2 and present as immutable gate evidence afterward.
    new_paths = {Path(value).resolve() for value in contract.result_paths().values()}
    historical_paths = {path.resolve() for path in contract.HISTORICAL_RESULT_PATHS}
    assert new_paths.isdisjoint(historical_paths)
    assert "7r4hr2" in contract.PLAN_TARGETED_RESULT_PATH.name
    assert "7r4i" in contract.REPORT_FORMAL_RESULT_PATH.name


def test_h1_and_hr1_results_remain_registered_historical_evidence() -> None:
    identities = contract.validate_historical_results()
    assert identities["all_present_and_readable"] is True
    assert identities["required_file_count"] == len(contract.HISTORICAL_RESULT_PATHS)
    assert str(
        contract.CURRENT_H1_PLAN_TARGETED_RESULT_PATH.relative_to(PROJECT_ROOT)
    ) in identities["required_paths"]
    assert str(
        contract.CURRENT_HR1_PLAN_TARGETED_RESULT_PATH.relative_to(PROJECT_ROOT)
    ) in identities["required_paths"]
    assert contract.CURRENT_HR1_PLAN_TARGETED_RESULT_PATH in (
        contract.HISTORICAL_RESULT_PATHS
    )


def test_report_runner_prepares_frozen_denominators_without_calls_or_writes() -> None:
    payload = report_runner.dry_run_payload()
    assert payload["selected_case_ids"] == [f"SR{index:02d}" for index in range(1, 21)]
    assert payload["denominators"]["manual_label_counts"] == {
        "high": 8,
        "low": 6,
        "partial": 6,
    }
    assert payload["denominators"]["formal_business_call_budget"] == 60
    assert payload["denominators"]["failed_samples_remain_in_denominator"] is True
    assert payload["real_model_call_count"] == 0
    assert payload["formal_quality_result_write_count"] == 0
    assert payload["adapter_instantiated"] is False
    assert payload["writes_result_file"] is False


def test_write_helper_refuses_historical_and_existing_targets(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        contract.write_new_json(contract.HISTORICAL_RESULT_PATHS[0], {"bad": True})
    existing = tmp_path / "existing.json"
    existing.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError):
        contract.write_new_json(existing, {"bad": True})
