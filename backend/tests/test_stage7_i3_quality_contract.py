from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5_quality as runner  # noqa: E402
import stage7_7r5_quality_contract as contract  # noqa: E402


def _confirmed_plan_snapshot() -> dict:
    plan = {
        "schema_version": "5.0",
        "criteria": [
            {
                "criterion_id": "C01",
                "name": "Python 后端经验",
                "importance": "required",
            }
        ],
    }
    return {
        "status": "confirmed",
        "confirmed_by": "hr-reviewer",
        "confirmed_at": "2026-08-30T10:00:00+08:00",
        "plan": plan,
        "snapshot_sha256": contract.sha256_value(plan),
    }


def _time_case() -> dict:
    return {
        "time_case_id": "T01",
        "application_applied_at": "2026-08-30T09:30:00+08:00",
        "evaluation_reference_at": "2026-08-30T09:30:00+08:00",
        "periods": [
            {"start_month": "2024-02", "end_month": "present"},
        ],
        "actual_months": 30,
        "threshold_months": 24,
    }


def _passing_inputs() -> tuple[dict, dict, dict]:
    automatic = {
        "plans": {"structure_legal_count": 10, "traceable_plan_count": 10},
        "reports": {
            "legal_report_count": 20,
            "required_section_fields_legal_count": 20,
            "nonzero_assessment_count": 40,
            "nonzero_with_evidence_count": 40,
        },
        "stability": {
            "direction_stable_group_count": 4,
            "max_difference_le_10_group_count": 4,
            "extreme_direction_flip_count": 0,
        },
    }
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
        "report_material_finding_omission_count": 0,
        "stability_severe_fact_error_count": 0,
        "stability_sensitive_scoring_count": 0,
    }
    denominators = {
        "plan_required": 55,
        "report_direction": 20,
        "required_direction": 107,
    }
    return automatic, metrics, denominators


def test_i3_contract_is_v2_while_i2_remains_frozen_v1() -> None:
    assert contract.I2_QUALITY_CONTRACT_VERSION == "stage7_v5_quality_contract_v1"
    assert contract.I3_QUALITY_CONTRACT_VERSION == "stage7_v5_quality_contract_v2"
    assert contract.i2_quality_contract()["version"] == contract.I2_QUALITY_CONTRACT_VERSION
    assert contract.i3_quality_contract()["version"] == contract.I3_QUALITY_CONTRACT_VERSION
    assert contract.i3_quality_contract()["formal_gate_count"] == 19
    assert contract.i3_quality_contract()["i2_recalculation_allowed"] is False
    assert contract.i3_quality_contract()["plan_semantic_gate_source"] == (
        "pre_call_frozen_human_labels"
    )


def test_close_05a_contract_payload_is_offline_and_creates_no_i3_result() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            runner,
            "get_settings",
            lambda: (_ for _ in ()).throw(AssertionError("不得读取 API Key")),
        )
        payload = runner.i3_zero_call_contract_payload()
    assert payload["formal_i3_result_created"] is False
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["input_token_count"] == 0
    assert payload["output_token_count"] == 0
    assert payload["estimated_spend_usd"] == 0
    assert payload["api_key_read"] is False
    assert payload["postgresql_write_count"] == 0


def test_rough_chinese_overlap_is_diagnostic_only() -> None:
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


def test_report_section_contract_allows_honest_empty_lists() -> None:
    report = {field: [] for field in contract.I3_REPORT_SECTION_FIELDS}
    validated = contract.validate_i3_report_sections(report)
    assert validated["structure_legal"] is True
    assert validated["empty_section_diagnostics"] == list(
        contract.I3_REPORT_SECTION_FIELDS
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda report: report.pop("strengths"), "五个分区字段"),
        (lambda report: report.__setitem__("gaps", "无"), "必须是列表"),
    ],
)
def test_report_section_contract_rejects_missing_or_wrong_type(
    mutation, message: str
) -> None:
    report = {field: [] for field in contract.I3_REPORT_SECTION_FIELDS}
    mutation(report)
    with pytest.raises(RuntimeError, match=message):
        contract.validate_i3_report_sections(report)


def test_material_findings_use_frozen_ids_and_count_real_omissions() -> None:
    frozen = [
        {"finding_id": "MF01", "section": "strengths", "label": "有后端交付经验"},
        {"finding_id": "MF02", "section": "gaps", "label": "缺少 Kubernetes 证据"},
    ]
    audit = [
        {"finding_id": "MF01", "present": True},
        {"finding_id": "MF02", "present": False},
    ]
    summary = contract.summarize_i3_material_findings(frozen, audit)
    assert summary == {
        "material_finding_count": 2,
        "present_count": 1,
        "omission_count": 1,
        "omitted_finding_ids": ["MF02"],
        "source": "pre_call_frozen_human_labels",
    }


def test_material_findings_reject_post_call_or_incomplete_audit_labels() -> None:
    frozen = [
        {"finding_id": "MF01", "section": "risks_or_conflicts", "label": "经历时间冲突"}
    ]
    with pytest.raises(RuntimeError, match="逐项覆盖"):
        contract.summarize_i3_material_findings(frozen, [])
    with pytest.raises(RuntimeError, match="调用前冻结"):
        contract.validate_i3_material_findings(frozen, frozen_before_model_call=False)


def test_time_case_uses_application_time_as_the_only_reference() -> None:
    validated = contract.validate_i3_time_case(_time_case())
    assert validated["actual_months"] == 30
    assert validated["evaluation_reference_at"] == validated["application_applied_at"]


def test_time_case_rejects_reference_drift_and_wrong_month_label() -> None:
    drifted = _time_case()
    drifted["evaluation_reference_at"] = "2026-08-31T09:30:00+08:00"
    with pytest.raises(RuntimeError, match="必须等于.*投递时间"):
        contract.validate_i3_time_case(drifted)

    wrong_months = _time_case()
    wrong_months["actual_months"] = 31
    with pytest.raises(RuntimeError, match="actual_months"):
        contract.validate_i3_time_case(wrong_months)


def test_report_and_stability_cases_require_hr_confirmed_plan_snapshot() -> None:
    snapshot = _confirmed_plan_snapshot()
    assert contract.validate_i3_confirmed_plan_snapshot(snapshot)["status"] == "confirmed"
    assert contract.validate_i3_case_inputs(
        {"case_id": "R00", "confirmed_plan_snapshot": snapshot},
        run_kind="report",
    )["plan_source"] == "confirmed_plan_snapshot"
    assert contract.validate_i3_case_inputs(
        {"case_id": "S00", "confirmed_plan_snapshot": snapshot},
        run_kind="stability",
    )["plan_source"] == "confirmed_plan_snapshot"

    draft = _confirmed_plan_snapshot()
    draft["status"] = "pending_confirmation"
    with pytest.raises(RuntimeError, match="HR 确认"):
        contract.validate_i3_case_inputs(
            {"case_id": "R00", "confirmed_plan_snapshot": draft},
            run_kind="report",
        )


def test_i3_final_keeps_19_gates_and_separately_displays_combined_counts() -> None:
    automatic, metrics, denominators = _passing_inputs()
    result = runner.build_i3_gate_result(
        automatic=automatic,
        metrics=metrics,
        denominators=denominators,
    )
    assert result["gate_summary"] == {"total": 19, "passed": 19, "failed": 0}
    assert result["stability_zero_tolerance_counts"] == {
        "severe_fact_error_count": 0,
        "sensitive_scoring_count": 0,
    }
    assert "stability_severe_and_sensitive_zero" in result["gates"]
    assert "stability_severe_fact_error_zero" not in result["gates"]
    assert "stability_sensitive_scoring_zero" not in result["gates"]


def test_i3_stability_thresholds_are_not_lowered_and_illegal_group_fails() -> None:
    automatic, metrics, denominators = _passing_inputs()
    automatic["stability"]["direction_stable_group_count"] = 3
    automatic["stability"]["max_difference_le_10_group_count"] = 3
    metrics["stability_severe_fact_error_count"] = 1
    result = runner.build_i3_gate_result(
        automatic=automatic,
        metrics=metrics,
        denominators=denominators,
    )
    assert result["gates"]["stability_direction_at_least_4_of_5"] is False
    assert result["gates"]["stability_spread_at_least_4_of_5"] is False
    assert result["gates"]["stability_severe_and_sensitive_zero"] is False
    assert result["stability_zero_tolerance_counts"] == {
        "severe_fact_error_count": 1,
        "sensitive_scoring_count": 0,
    }
    assert result["gate_summary"]["total"] == 19


def test_illegal_stability_output_keeps_its_group_out_of_both_pass_counts() -> None:
    records = []
    for sample_index in range(5):
        for run_number in range(1, 4):
            succeeded = not (sample_index == 0 and run_number == 3)
            records.append(
                {
                    "case_id": f"S{sample_index:02d}-{run_number}",
                    "sample_index": sample_index,
                    "run_number": run_number,
                    "status": "succeeded" if succeeded else "failed",
                    "overall_score": 70 + run_number if succeeded else None,
                    "actual_direction": "high_match" if succeeded else None,
                    "manual_direction": "high_match",
                }
            )
    summary = runner.summarize_reports(records, stability=True)
    failed_group = summary["groups"][0]
    assert failed_group["legal_run_count"] == 2
    assert failed_group["direction_stable"] is False
    assert failed_group["max_score_difference"] is None
    assert summary["direction_stable_group_count"] == 4
    assert summary["max_difference_le_10_group_count"] == 4
