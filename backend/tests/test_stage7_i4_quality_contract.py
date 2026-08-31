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

import run_stage7_7r5_quality as runner  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402


def _fixture_module():
    return importlib.import_module("tests.fixtures.v5_i4_quality_samples")


def _passing_inputs() -> tuple[dict, dict, dict]:
    fixture_summary = contract.validate_i4_fixture()
    automatic = {
        "plans": {"structure_legal_count": 10, "traceable_plan_count": 10},
        "reports": {
            "legal_report_count": 20,
            "required_section_fields_legal_count": 20,
            "nonzero_assessment_count": 40,
            "nonzero_with_evidence_count": 40,
        },
        "stability": {
            "legal_report_count": 15,
            "direction_stable_group_count": 3,
            "max_difference_le_10_group_count": 3,
            "extreme_direction_flip_count": 0,
        },
    }
    metrics = {
        "plan_required_covered_count": fixture_summary[
            "plan_required_label_denominator"
        ],
        "plan_forbidden_addition_count": 0,
        "plan_sensitive_criterion_count": 0,
        "plan_non_evaluation_misclassified_count": 0,
        "plan_work_duration_criterion_count": 0,
        "report_fabricated_fact_count": 0,
        "report_severe_fact_error_count": 0,
        "report_sensitive_scoring_count": 0,
        "report_automatic_decision_count": 0,
        "report_direction_consistent_count": 16,
        "required_direction_consistent_count": 36,
        "report_material_finding_omission_count": 0,
        "report_work_duration_scoring_or_judgment_count": 0,
        "stability_severe_fact_error_count": 0,
        "stability_sensitive_scoring_count": 0,
    }
    denominators = {
        "plan_required": fixture_summary["plan_required_label_denominator"],
        "report_direction": 20,
        "required_direction": 40,
    }
    return automatic, metrics, denominators


def _all_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested
            for item in value.values()
            for nested in _all_keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _all_keys(item)}
    return set()


def test_v3_contract_routes_i4_without_reinterpreting_i2_or_i3_r1() -> None:
    assert contract.I4_QUALITY_CONTRACT_VERSION == "stage7_v5_quality_contract_v3"
    assert contract.quality_contract_for_run(contract.ACTIVE_RUN_ID) == (
        contract.i2_quality_contract()
    )
    assert contract.quality_contract_for_run(contract.I3_RUN_ID) == (
        contract.i3_quality_contract()
    )
    assert contract.quality_contract_for_run(contract.I4_RUN_ID) == (
        contract.i4_quality_contract()
    )
    assert contract.i2_quality_contract()["version"] == (
        "stage7_v5_quality_contract_v1"
    )
    assert contract.i3_quality_contract()["version"] == (
        "stage7_v5_quality_contract_v2"
    )
    assert contract.i4_quality_contract()["version"] == (
        "stage7_v5_quality_contract_v3"
    )
    assert contract.i4_quality_contract()["historical_recalculation_allowed"] is False


def test_i4_fixture_is_fresh_complete_and_uses_v3_labels() -> None:
    fixture = _fixture_module()
    assert len(fixture.I4_PLAN_JDS) == 10
    assert len(fixture.I4_REPORT_PAIRS) == 20
    assert len(fixture.I4_STABILITY_SAMPLE_INDICES) == 5
    assert fixture.I4_STABILITY_RUNS_PER_SAMPLE == 3
    assert {case["label_contract_version"] for case in fixture.I4_PLAN_JDS} == {
        "stage7_v5_quality_contract_v3"
    }
    assert {case["label_contract_version"] for case in fixture.I4_REPORT_PAIRS} == {
        "stage7_v5_quality_contract_v3"
    }
    assert all(case["case_id"].startswith("I4-") for case in fixture.I4_PLAN_JDS)
    assert all(case["case_id"].startswith("I4-") for case in fixture.I4_REPORT_PAIRS)
    assert len(fixture.compute_i4_fixture_hashes()["fixture"]) == 64


def test_i4_required_denominator_excludes_pure_duration_but_keeps_mixed_skill() -> None:
    fixture = _fixture_module()
    java_case = next(case for case in fixture.I4_PLAN_JDS if case["case_id"] == "I4-P00")
    labels = java_case["labels"]
    assert "Java" in labels["key_required_items"]
    assert "3 年以上工作经验" not in labels["key_required_items"]
    assert labels["mixed_requirement_capability_items"] == [
        {
            "source_requirement": "3 年以上 Java 经验",
            "capability_label": "Java",
        }
    ]
    summary = contract.validate_i4_fixture()
    expected_required = sum(
        len(case["labels"]["key_required_items"])
        for case in fixture.I4_PLAN_JDS
    )
    assert summary["plan_required_label_denominator"] == expected_required
    assert summary["pure_work_duration_excluded_count"] == 10
    assert summary["mixed_capability_retained_count"] == 10


def test_i4_labels_contain_no_time_calculation_or_duration_threshold_fields() -> None:
    fixture = _fixture_module()
    label_payload = {
        "plans": [case["labels"] for case in fixture.I4_PLAN_JDS],
        "reports": [
            {
                "labels": case["labels"],
                "material_findings": case["material_findings"],
            }
            for case in fixture.I4_REPORT_PAIRS
        ],
    }
    forbidden_keys = {
        "time_case",
        "time_case_id",
        "evaluation_reference_at",
        "periods",
        "actual_months",
        "threshold_months",
        "duration_threshold_met",
        "work_duration_direction",
    }
    assert _all_keys(label_payload).isdisjoint(forbidden_keys)
    rendered_labels = json.dumps(label_payload, ensure_ascii=False)
    assert "达到 3 年门槛" not in rendered_labels
    assert "未达到 3 年门槛" not in rendered_labels
    assert "按投递时间计算" not in rendered_labels


def test_v3_keeps_19_gates_and_makes_stability_direction_and_spread_diagnostic() -> None:
    automatic, metrics, denominators = _passing_inputs()
    result = runner.build_i4_gate_result(
        automatic=automatic,
        metrics=metrics,
        denominators=denominators,
    )
    assert result["gate_summary"] == {"total": 19, "passed": 19, "failed": 0}
    assert "stability_direction_at_least_4_of_5" not in result["gates"]
    assert "stability_spread_at_least_4_of_5" not in result["gates"]
    assert result["stability_diagnostics"] == {
        "direction_stable_group_count": 3,
        "max_difference_le_10_group_count": 3,
        "direction_target_reference": 4,
        "spread_target_reference": 4,
        "blocking": False,
    }
    assert result["gates"]["plan_work_duration_criterion_zero"] is True
    assert (
        result["gates"]["report_work_duration_scoring_or_judgment_zero"] is True
    )


@pytest.mark.parametrize(
    ("target", "field", "value", "failed_gate"),
    [
        ("automatic", "legal_report_count", 14, "stability_extreme_flip_zero"),
        ("automatic", "extreme_direction_flip_count", 1, "stability_extreme_flip_zero"),
        ("metrics", "report_sensitive_scoring_count", 1, "report_sensitive_scoring_zero"),
        ("metrics", "report_severe_fact_error_count", 1, "report_severe_fact_error_zero"),
        ("metrics", "stability_sensitive_scoring_count", 1, "stability_severe_and_sensitive_zero"),
    ],
)
def test_v3_keeps_legal_extreme_sensitive_and_non_duration_fact_hard_protections(
    target: str, field: str, value: int, failed_gate: str
) -> None:
    automatic, metrics, denominators = _passing_inputs()
    if target == "automatic":
        automatic["stability"][field] = value
    else:
        metrics[field] = value
    result = runner.build_i4_gate_result(
        automatic=automatic,
        metrics=metrics,
        denominators=denominators,
    )
    assert result["quality_gate_passed"] is False
    assert result["gates"][failed_gate] is False


@pytest.mark.parametrize(
    ("metric", "failed_gate"),
    [
        ("plan_work_duration_criterion_count", "plan_work_duration_criterion_zero"),
        (
            "report_work_duration_scoring_or_judgment_count",
            "report_work_duration_scoring_or_judgment_zero",
        ),
    ],
)
def test_v3_new_duration_gates_are_blocking(metric: str, failed_gate: str) -> None:
    automatic, metrics, denominators = _passing_inputs()
    metrics[metric] = 1
    result = runner.build_i4_gate_result(
        automatic=automatic,
        metrics=metrics,
        denominators=denominators,
    )
    assert result["quality_gate_passed"] is False
    assert result["gates"][failed_gate] is False


def test_close_05g_payload_is_offline_and_creates_no_formal_i4_result() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            runner,
            "get_settings",
            lambda: (_ for _ in ()).throw(AssertionError("不得读取 API Key")),
        )
        payload = runner.i4_zero_call_contract_payload()
    assert payload["mode"] == "i4_quality_contract_v3_zero_call"
    assert payload["formal_i4_result_created"] is False
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["input_token_count"] == 0
    assert payload["output_token_count"] == 0
    assert payload["estimated_spend_usd"] == 0
    assert payload["api_key_read"] is False
    assert payload["postgresql_write_count"] == 0


def test_rough_chinese_overlap_remains_review_candidate_only_under_v3() -> None:
    diagnostics = runner.rough_plan_label_diagnostics(
        rendered_criteria="Java 后端开发经验",
        labels={
            "key_required_items": [],
            "non_evaluation_content": ["前端开发经验"],
            "forbidden_additions": [],
        },
    )
    assert diagnostics["non_evaluation_candidates"] == ["前端开发经验"]
    assert diagnostics["formal_semantic_failure_count"] == 0
    assert diagnostics["diagnostic_only"] is True
