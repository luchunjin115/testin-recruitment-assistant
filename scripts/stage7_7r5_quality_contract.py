from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tests.fixtures.v5_quality_samples import (  # noqa: E402
    V5_PLAN_CALL_BUDGET,
    V5_PLAN_JDS,
    V5_REPORT_CALL_BUDGET,
    V5_REPORT_PAIRS,
    V5_STABILITY_CALL_BUDGET,
    V5_STABILITY_RUNS_PER_SAMPLE,
    V5_STABILITY_SAMPLE_INDICES,
    compute_v5_fixture_hash,
)
from tests.fixtures.v5_i4_quality_samples import (  # noqa: E402
    I4_LABEL_CONTRACT_VERSION,
    I4_PLAN_JDS,
    I4_REPORT_PAIRS,
    I4_STABILITY_RUNS_PER_SAMPLE,
    I4_STABILITY_SAMPLE_INDICES,
    compute_i4_fixture_hashes,
)


STAGE7_RESULTS_DIR = PROJECT_ROOT / "docs" / "stages" / "stage7"
V5_RESULTS_DIR = STAGE7_RESULTS_DIR / "v5-quality-results"
SEALED_RUN_ID = "7R5-I"
ACTIVE_RUN_ID = "7R5-I2"
RAW_RESULT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-quality-raw-results.json"
HUMAN_AUDIT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-human-audit.json"
FINAL_RESULT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-quality-final-results.json"
I2_PREFLIGHT_PATH = V5_RESULTS_DIR / "2026-08-28-stage7-7r5i2-zero-call-preflight.json"
I2_RAW_RESULT_PATH = V5_RESULTS_DIR / "2026-08-28-stage7-7r5i2-quality-raw-results.json"
I2_HUMAN_AUDIT_PATH = V5_RESULTS_DIR / "2026-08-28-stage7-7r5i2-quality-human-audit.json"
I2_FINAL_RESULT_PATH = V5_RESULTS_DIR / "2026-08-28-stage7-7r5i2-quality-final-results.json"
I3_SUPERSEDED_RUN_ID = "7R5-I3"
I3_SUPERSEDED_PREFLIGHT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-zero-call-preflight.json"
)
I3_SUPERSEDED_REVIEW_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-fixture-review.md"
)
I3_RUN_ID = "7R5-I3-R1"
I4_RUN_ID = "7R5-I4"
I3_PREFLIGHT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-r1-zero-call-preflight.json"
)
I3_RAW_RESULT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-r1-quality-raw-results.json"
)
I3_HUMAN_AUDIT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-r1-quality-human-audit.json"
)
I3_FINAL_RESULT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i3-r1-quality-final-results.json"
)
I4_PREFLIGHT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i4-zero-call-preflight.json"
)
I4_RAW_RESULT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i4-quality-raw-results.json"
)
I4_HUMAN_AUDIT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i4-quality-human-audit.json"
)
I4_FINAL_RESULT_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i4-quality-final-results.json"
)
I4_REVIEW_PATH = (
    V5_RESULTS_DIR / "2026-08-31-stage7-7r5i4-fixture-review.md"
)
I2_LIFECYCLE_STATES = (
    "i2_not_started",
    "i2_preflight_complete",
    "i2_raw_complete",
    "i2_human_complete",
    "i2_final_complete",
)
I3_LIFECYCLE_STATES = (
    "i3_not_started",
    "i3_preflight_complete",
    "i3_raw_complete",
    "i3_human_complete",
    "i3_final_complete",
)
I4_LIFECYCLE_STATES = (
    "i4_not_started",
    "i4_preflight_complete",
    "i4_raw_complete",
    "i4_human_complete",
    "i4_final_complete",
)
I2_HELPER_PATH = V5_RESULTS_DIR / "7r5i-human-review-helper"

FROZEN_FIXTURE_SHA256 = "2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643"
PLAN_SAMPLE_SHA256 = "c86ed29acc38206714c253a022d9b4ca2fe9aa32078aae599115bac40ea8823f"
PLAN_LABEL_SHA256 = "3f8a22656814b1ce9c4f8929e3b93de37e6e7a337c672752895920e022ac0cf6"
REPORT_SAMPLE_SHA256 = "ee7f4d5a5673a5a6a15c1ef0d469f67eee50e3b4e3172d8c23415605f84f0dd3"
REPORT_LABEL_SHA256 = "a088f763eb011d34131b5dd34f6c2fe2558649ea5f9e41499d101ec270009d75"
STABILITY_SELECTION_SHA256 = "7f2c5f390b0c7e30e5a644380decea0554bbb62cfc03eff193d13a8c1a117708"

HISTORICAL_RESULT_FILENAMES = (
    "2026-08-20-stage7-quality-acceptance-results.json",
    "2026-08-20-stage7-quality-acceptance.md",
    "2026-08-21-stage7-step9-full-chain-diagnostic-results.json",
    "2026-08-21-stage7-step9-full-chain-diagnostic-results.md",
    "2026-08-21-stage7-step9-jd-decomposition-debug-results.json",
    "2026-08-21-stage7-step9-jd-decomposition-results.json",
    "2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json",
    "2026-08-21-stage7-time-fact-revalidation-results.json",
    "2026-08-22-stage7-7rf-plan-quality-targeted-results.json",
    "2026-08-25-stage7-7r4h-plan-quality-formal-results.json",
    "2026-08-25-stage7-7r4h-plan-quality-targeted-results.json",
    "2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json",
    "2026-08-26-stage7-7r4hr2-plan-quality-targeted-revalidation-results.json",
)

PLANNED_MODEL = "deepseek-v4-flash"
PLAN_PROMPT_VERSION = "job_evaluation_plan_lightweight_v3"
REPORT_PROMPT_VERSION = "screening_evaluation_lightweight_v6"
PLAN_SCHEMA_VERSION = "5.0"
REPORT_SCHEMA_VERSION = "5.0"
TEMPERATURE = 0.1
THINKING = "disabled"
RESPONSE_FORMAT = "json_object"
SDK_AUTOMATIC_RETRIES = 0
PLAN_MAX_OUTPUT_TOKENS = 8_000
REPORT_MAX_OUTPUT_TOKENS = 12_000
MAX_INFRASTRUCTURE_RETRIES_PER_BUSINESS_CALL = 1
BASELINE_BUSINESS_CALLS = 45
MAXIMUM_API_ATTEMPTS = 90
OFFICIAL_PRICING_SOURCE_URL = "https://api-docs.deepseek.com/quick_start/pricing/"

I2_QUALITY_CONTRACT_VERSION = "stage7_v5_quality_contract_v1"
I3_QUALITY_CONTRACT_VERSION = "stage7_v5_quality_contract_v2"
I4_QUALITY_CONTRACT_VERSION = "stage7_v5_quality_contract_v3"
I3_REPORT_SECTION_FIELDS = (
    "strengths",
    "gaps",
    "risks_or_conflicts",
    "missing_info",
    "hr_follow_up_questions",
)
I3_MATERIAL_FINDING_SECTIONS = I3_REPORT_SECTION_FIELDS[:4]


def serialized(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: list(item) if isinstance(item, tuple) else None,
    )


def sha256_value(value: Any) -> str:
    return hashlib.sha256(serialized(value).encode("utf-8")).hexdigest()


def i2_quality_contract() -> dict[str, Any]:
    """Describe the sealed interpretation used by I2 without recalculating it."""

    return {
        "version": I2_QUALITY_CONTRACT_VERSION,
        "run_id": ACTIVE_RUN_ID,
        "formal_gate_count": 19,
        "interpretation": "sealed_i2_only",
        "recalculation_allowed": False,
    }


def i3_quality_contract() -> dict[str, Any]:
    """Return the v2 ruler that a separately authorized I3 must bind to."""

    return {
        "version": I3_QUALITY_CONTRACT_VERSION,
        "formal_gate_count": 19,
        "i2_recalculation_allowed": False,
        "rough_overlap_policy": "diagnostic_candidates_only",
        "plan_semantic_gate_source": "pre_call_frozen_human_labels",
        "report_section_policy": {
            "required_fields": list(I3_REPORT_SECTION_FIELDS),
            "empty_lists_allowed": True,
            "formal_semantic_gate": "material_finding_omission_zero",
        },
        "time_policy": {
            "only_reference": "application_applied_at",
            "evaluation_reference_must_equal_application_applied_at": True,
            "actual_months_must_be_calculated_at_application_applied_at": True,
            "mismatch_policy": "preflight_hard_failure_before_paid_call",
        },
        "report_plan_source": "confirmed_plan_snapshot",
        "stability_plan_source": "confirmed_plan_snapshot",
        "stability_thresholds": {
            "direction_stable_groups_minimum": 4,
            "score_spread_le_10_groups_minimum": 4,
            "extreme_direction_flip_maximum": 0,
            "illegal_output_group_passes": False,
        },
        "stability_severe_and_sensitive_gate": "combined_zero_tolerance",
        "stability_counts_displayed_separately": True,
    }


def i4_quality_contract() -> dict[str, Any]:
    """Return the v3 offline ruler for a future, separately authorized I4."""

    return {
        "version": I4_QUALITY_CONTRACT_VERSION,
        "run_id": I4_RUN_ID,
        "formal_gate_count": 19,
        "historical_contracts": {
            ACTIVE_RUN_ID: I2_QUALITY_CONTRACT_VERSION,
            I3_RUN_ID: I3_QUALITY_CONTRACT_VERSION,
        },
        "historical_recalculation_allowed": False,
        "rough_overlap_policy": "manual_review_candidates_only",
        "plan_semantic_gate_source": "pre_call_frozen_human_labels",
        "required_coverage_policy": {
            "pure_work_duration_requirement": "excluded_from_denominator",
            "mixed_requirement": "retain_non_duration_capability_only",
        },
        "work_duration_policy": {
            "ai_calculation_allowed": False,
            "ai_threshold_judgment_allowed": False,
            "ai_scoring_allowed": False,
            "time_calculation_labels_allowed": False,
            "duration_threshold_labels_allowed": False,
            "hr_reviews_original_material_outside_ai_screening": True,
        },
        "stability_policy": {
            "scheduled_run_count": 15,
            "legal_output_required_count": 15,
            "direction_stable_groups": "diagnostic_only",
            "score_spread_le_10_groups": "diagnostic_only",
            "extreme_direction_flip_maximum": 0,
        },
        "severe_fact_error_scope": "non_work_duration_facts_only",
        "replaced_hard_gates": {
            "stability_direction_at_least_4_of_5": (
                "plan_work_duration_criterion_zero"
            ),
            "stability_spread_at_least_4_of_5": (
                "report_work_duration_scoring_or_judgment_zero"
            ),
        },
        "target_production_versions": {
            "plan_prompt": "job_evaluation_plan_lightweight_v4",
            "plan_service": "lightweight_plan_generation_v5",
            "plan_schema": "5.0",
            "report_prompt": "screening_evaluation_lightweight_v7",
            "report_service": "lightweight_report_generation_v9",
            "report_schema": "5.0",
            "implemented_by_close_05g": False,
        },
    }


def quality_contract_for_run(run_id: str) -> dict[str, Any]:
    """Bind each run to its own ruler; never reinterpret historical evidence."""

    if run_id == ACTIVE_RUN_ID:
        return i2_quality_contract()
    if run_id == I3_RUN_ID:
        return i3_quality_contract()
    if run_id == I4_RUN_ID:
        return i4_quality_contract()
    raise RuntimeError(f"未登记质量合同的运行批次：{run_id}")


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for item in value.values() for key in _nested_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _nested_keys(item)}
    return set()


def validate_i4_fixture() -> dict[str, Any]:
    """Validate v3 denominators and labels without freezing formal I4 evidence."""

    if I4_LABEL_CONTRACT_VERSION != I4_QUALITY_CONTRACT_VERSION:
        raise RuntimeError("I4 fixture 未绑定质量合同 v3")
    if (
        len(I4_PLAN_JDS),
        len(I4_REPORT_PAIRS),
        len(I4_STABILITY_SAMPLE_INDICES),
        I4_STABILITY_RUNS_PER_SAMPLE,
    ) != (10, 20, 5, 3):
        raise RuntimeError("I4 离线样本分母必须为 10/20/5x3")
    plan_ids = [case.get("case_id") for case in I4_PLAN_JDS]
    report_ids = [case.get("case_id") for case in I4_REPORT_PAIRS]
    if (
        len(set(plan_ids)) != 10
        or len(set(report_ids)) != 20
        or any(not isinstance(case_id, str) or not case_id.startswith("I4-") for case_id in plan_ids + report_ids)
    ):
        raise RuntimeError("I4 必须使用全新且唯一的 case 身份")

    excluded_count = 0
    mixed_retained_count = 0
    required_denominator = 0
    for case in I4_PLAN_JDS:
        if case.get("label_contract_version") != I4_QUALITY_CONTRACT_VERSION:
            raise RuntimeError("I4 计划标签合同版本漂移")
        labels = case.get("labels")
        if not isinstance(labels, dict):
            raise RuntimeError("I4 计划缺少人工标签")
        required = labels.get("key_required_items")
        excluded = labels.get("excluded_pure_work_duration_requirements")
        mixed = labels.get("mixed_requirement_capability_items")
        if (
            not isinstance(required, list)
            or not required
            or not isinstance(excluded, list)
            or len(excluded) != 1
            or not isinstance(mixed, list)
            or len(mixed) != 1
        ):
            raise RuntimeError("I4 计划 required、纯年限排除或混合能力标签非法")
        if any(item in required for item in excluded):
            raise RuntimeError("I4 纯工作年限错误进入 required 分母")
        mixed_item = mixed[0]
        if (
            not isinstance(mixed_item, dict)
            or mixed_item.get("capability_label") not in required
            or not isinstance(mixed_item.get("source_requirement"), str)
        ):
            raise RuntimeError("I4 混合要求没有保留非年限能力标签")
        required_denominator += len(required)
        excluded_count += len(excluded)
        mixed_retained_count += len(mixed)

    forbidden_label_keys = {
        "time_case",
        "time_case_id",
        "evaluation_reference_at",
        "periods",
        "actual_months",
        "threshold_months",
        "duration_threshold_met",
        "work_duration_direction",
    }
    report_required_denominator = 0
    directions: dict[str, int] = {}
    for case in I4_REPORT_PAIRS:
        if case.get("label_contract_version") != I4_QUALITY_CONTRACT_VERSION:
            raise RuntimeError("I4 报告标签合同版本漂移")
        audited_labels = {
            "labels": case.get("labels"),
            "material_findings": case.get("material_findings"),
        }
        if _nested_keys(audited_labels) & forbidden_label_keys:
            raise RuntimeError("I4 新标签不得包含时间计算或年限达标字段")
        rendered = serialized(audited_labels)
        if any(
            phrase in rendered
            for phrase in ("达到 3 年门槛", "未达到 3 年门槛", "按投递时间计算")
        ):
            raise RuntimeError("I4 报告标签不得判断工作年限")
        labels = case["labels"]
        direction = labels.get("overall_direction")
        directions[direction] = directions.get(direction, 0) + 1
        report_required_denominator += len(
            labels.get("required_evidence_present", [])
        ) + len(labels.get("required_evidence_absent", []))
    if directions != {"high_match": 8, "partial_match": 6, "low_match": 6}:
        raise RuntimeError("I4 报告方向分母必须为 8/6/6")
    stability_directions = [
        I4_REPORT_PAIRS[index]["labels"]["overall_direction"]
        for index in I4_STABILITY_SAMPLE_INDICES
    ]
    if stability_directions != [
        "high_match",
        "high_match",
        "partial_match",
        "partial_match",
        "low_match",
    ]:
        raise RuntimeError("I4 稳定性样本方向必须为 2 high / 2 partial / 1 low")
    return {
        "quality_contract_version": I4_QUALITY_CONTRACT_VERSION,
        "hashes": compute_i4_fixture_hashes(),
        "plan_case_count": 10,
        "report_case_count": 20,
        "stability_case_count": 5,
        "stability_runs_per_case": 3,
        "plan_required_label_denominator": required_denominator,
        "pure_work_duration_excluded_count": excluded_count,
        "mixed_capability_retained_count": mixed_retained_count,
        "report_required_direction_denominator": report_required_denominator,
        "manual_direction_denominators": directions,
        "formal_i4_evidence_created": False,
    }


def validate_i3_report_sections(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise RuntimeError("I3 报告必须是对象")
    missing = [field for field in I3_REPORT_SECTION_FIELDS if field not in report]
    if missing:
        raise RuntimeError("I3 报告缺少五个分区字段：" + ", ".join(missing))
    wrong_types = [
        field
        for field in I3_REPORT_SECTION_FIELDS
        if not isinstance(report[field], list)
    ]
    if wrong_types:
        raise RuntimeError("I3 报告五个分区字段必须是列表：" + ", ".join(wrong_types))
    return {
        "structure_legal": True,
        "empty_section_diagnostics": [
            field for field in I3_REPORT_SECTION_FIELDS if not report[field]
        ],
        "empty_sections_are_semantic_failures": False,
    }


def validate_i3_material_findings(
    findings: list[dict[str, Any]], *, frozen_before_model_call: bool = True
) -> list[dict[str, Any]]:
    if not frozen_before_model_call:
        raise RuntimeError("I3 material_findings 必须在模型调用前冻结")
    if not isinstance(findings, list):
        raise RuntimeError("I3 material_findings 必须是列表")
    identifiers: list[str] = []
    normalized: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise RuntimeError("I3 material_findings 每项必须是对象")
        finding_id = finding.get("finding_id")
        section = finding.get("section")
        label = finding.get("label")
        if not isinstance(finding_id, str) or not finding_id.strip():
            raise RuntimeError("I3 material finding 缺少稳定 finding_id")
        if section not in I3_MATERIAL_FINDING_SECTIONS:
            raise RuntimeError("I3 material finding 的 section 非法")
        if not isinstance(label, str) or not label.strip():
            raise RuntimeError("I3 material finding 缺少人工标签")
        identifiers.append(finding_id)
        normalized.append(
            {"finding_id": finding_id, "section": section, "label": label}
        )
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError("I3 material finding ID 必须唯一")
    return normalized


def summarize_i3_material_findings(
    frozen_findings: list[dict[str, Any]], audit: list[dict[str, Any]]
) -> dict[str, Any]:
    frozen = validate_i3_material_findings(frozen_findings)
    if not isinstance(audit, list):
        raise RuntimeError("I3 material finding 人工审计必须是列表")
    frozen_ids = [item["finding_id"] for item in frozen]
    audit_by_id: dict[str, bool] = {}
    for item in audit:
        if not isinstance(item, dict):
            raise RuntimeError("I3 material finding 人工审计项必须是对象")
        finding_id = item.get("finding_id")
        present = item.get("present")
        if (
            not isinstance(finding_id, str)
            or not isinstance(present, bool)
            or finding_id in audit_by_id
        ):
            raise RuntimeError("I3 material finding 人工审计字段或 ID 非法")
        audit_by_id[finding_id] = present
    if set(audit_by_id) != set(frozen_ids):
        raise RuntimeError("I3 material finding 人工审计必须逐项覆盖调用前冻结标签")
    omitted = [finding_id for finding_id in frozen_ids if not audit_by_id[finding_id]]
    return {
        "material_finding_count": len(frozen_ids),
        "present_count": len(frozen_ids) - len(omitted),
        "omission_count": len(omitted),
        "omitted_finding_ids": omitted,
        "source": "pre_call_frozen_human_labels",
    }


def _parse_aware_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError(f"I3 {field} 必须是带时区 ISO 时间")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise RuntimeError(f"I3 {field} 必须是带时区 ISO 时间") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"I3 {field} 必须是带时区 ISO 时间")
    return parsed


def _month_index(value: str, *, field: str) -> int:
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except (TypeError, ValueError):
        raise RuntimeError(f"I3 {field} 必须是 YYYY-MM") from None
    return parsed.year * 12 + parsed.month - 1


def _union_month_duration(intervals: list[tuple[int, int]]) -> int:
    ordered = sorted(intervals)
    if not ordered:
        return 0
    total = 0
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def validate_i3_time_case(time_case: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(time_case, dict):
        raise RuntimeError("I3 时间标签必须是对象")
    applied = _parse_aware_datetime(
        time_case.get("application_applied_at"), field="application_applied_at"
    )
    reference = _parse_aware_datetime(
        time_case.get("evaluation_reference_at"), field="evaluation_reference_at"
    )
    if reference != applied:
        raise RuntimeError("I3 evaluation_reference_at 必须等于 Application 投递时间")
    actual_months = time_case.get("actual_months")
    threshold_months = time_case.get("threshold_months")
    if (
        not isinstance(actual_months, int)
        or isinstance(actual_months, bool)
        or actual_months < 0
        or not isinstance(threshold_months, int)
        or isinstance(threshold_months, bool)
        or threshold_months < 0
    ):
        raise RuntimeError("I3 actual_months 和 threshold_months 必须是非负整数")
    periods = time_case.get("periods")
    if not isinstance(periods, list) or not periods:
        raise RuntimeError("I3 时间标签必须冻结用于计算的 periods")
    business_zone = timezone(timedelta(hours=8), name="Asia/Shanghai")
    local_applied = applied.astimezone(business_zone)
    cutoff = local_applied.year * 12 + local_applied.month - 1
    intervals: list[tuple[int, int]] = []
    for period in periods:
        if not isinstance(period, dict):
            raise RuntimeError("I3 时间 period 必须是对象")
        start = _month_index(period.get("start_month"), field="start_month")
        raw_end = period.get("end_month")
        end = cutoff if raw_end == "present" else min(
            _month_index(raw_end, field="end_month"), cutoff
        )
        if start > cutoff or end < start:
            raise RuntimeError("I3 时间 period 超出投递时间或结束早于开始")
        intervals.append((start, end))
    calculated = _union_month_duration(intervals)
    if calculated != actual_months:
        raise RuntimeError(
            "I3 actual_months 未按 application_applied_at 计算："
            f"冻结 {actual_months}，应为 {calculated}"
        )
    return {
        **time_case,
        "application_applied_at": time_case["application_applied_at"],
        "evaluation_reference_at": time_case["evaluation_reference_at"],
        "actual_months": actual_months,
        "threshold_months": threshold_months,
        "calculation_reference": "application_applied_at",
    }


def validate_i3_confirmed_plan_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("status") != "confirmed":
        raise RuntimeError("I3 报告与稳定性必须使用 HR 确认的计划快照")
    if not isinstance(snapshot.get("confirmed_by"), str) or not snapshot[
        "confirmed_by"
    ].strip():
        raise RuntimeError("I3 HR 确认计划快照缺少 confirmed_by")
    _parse_aware_datetime(snapshot.get("confirmed_at"), field="confirmed_at")
    plan = snapshot.get("plan")
    if (
        not isinstance(plan, dict)
        or plan.get("schema_version") != "5.0"
        or not isinstance(plan.get("criteria"), list)
        or not plan["criteria"]
    ):
        raise RuntimeError("I3 HR 确认计划快照结构非法")
    if snapshot.get("snapshot_sha256") != sha256_value(plan):
        raise RuntimeError("I3 HR 确认计划快照指纹不一致")
    return snapshot


def validate_i3_case_inputs(
    case: dict[str, Any], *, run_kind: str
) -> dict[str, Any]:
    if run_kind not in {"plan", "report", "stability"}:
        raise RuntimeError("I3 case 的 run_kind 非法")
    if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
        raise RuntimeError("I3 case 缺少稳定 case_id")
    if run_kind == "plan":
        return {"case_id": case["case_id"], "plan_source": "independent_jd"}
    validate_i3_confirmed_plan_snapshot(case.get("confirmed_plan_snapshot"))
    return {
        "case_id": case["case_id"],
        "plan_source": "confirmed_plan_snapshot",
    }


def validate_frozen_fixture() -> dict[str, Any]:
    plan_samples = [{key: value for key, value in item.items() if key != "labels"} for item in V5_PLAN_JDS]
    plan_labels = [item["labels"] for item in V5_PLAN_JDS]
    report_samples = [{key: value for key, value in item.items() if key != "labels"} for item in V5_REPORT_PAIRS]
    report_labels = [item["labels"] for item in V5_REPORT_PAIRS]
    observed = {
        "fixture": compute_v5_fixture_hash(),
        "plan_samples": sha256_value(plan_samples),
        "plan_labels": sha256_value(plan_labels),
        "report_samples": sha256_value(report_samples),
        "report_labels": sha256_value(report_labels),
        "stability_selection": sha256_value(V5_STABILITY_SAMPLE_INDICES),
    }
    expected = {
        "fixture": FROZEN_FIXTURE_SHA256,
        "plan_samples": PLAN_SAMPLE_SHA256,
        "plan_labels": PLAN_LABEL_SHA256,
        "report_samples": REPORT_SAMPLE_SHA256,
        "report_labels": REPORT_LABEL_SHA256,
        "stability_selection": STABILITY_SELECTION_SHA256,
    }
    if observed != expected:
        raise RuntimeError("5.0 冻结样本、人工标签、稳定性选择或顺序已经漂移")
    directions: dict[str, int] = {}
    for pair in V5_REPORT_PAIRS:
        direction = pair["labels"]["overall_direction"]
        directions[direction] = directions.get(direction, 0) + 1
    if directions != {"high_match": 8, "partial_match": 6, "low_match": 6}:
        raise RuntimeError("20 组报告 high/partial/low 人工分母已经漂移")
    if V5_STABILITY_SAMPLE_INDICES != [0, 1, 2, 3, 4]:
        raise RuntimeError("稳定性样本必须固定为报告样本 0—4")
    return {
        "hashes": observed,
        "plan_case_count": len(V5_PLAN_JDS),
        "report_case_count": len(V5_REPORT_PAIRS),
        "stability_case_count": len(V5_STABILITY_SAMPLE_INDICES),
        "stability_runs_per_case": V5_STABILITY_RUNS_PER_SAMPLE,
        "manual_direction_denominators": directions,
        "plan_required_label_denominator": sum(len(item["labels"]["key_required_items"]) for item in V5_PLAN_JDS),
        "plan_non_evaluation_label_denominator": sum(len(item["labels"]["non_evaluation_content"]) for item in V5_PLAN_JDS),
        "plan_forbidden_addition_denominator": sum(len(item["labels"]["forbidden_additions"]) for item in V5_PLAN_JDS),
        "report_required_direction_denominator": sum(
            len(item["labels"]["required_evidence_present"])
            + len(item["labels"]["required_evidence_absent"])
            for item in V5_REPORT_PAIRS
        ),
        "failed_cases_remain_in_denominator": True,
    }


def validate_historical_results() -> dict[str, Any]:
    json_file_count = 0
    markdown_file_count = 0
    for filename in HISTORICAL_RESULT_FILENAMES:
        path = STAGE7_RESULTS_DIR / filename
        if not path.exists():
            raise RuntimeError(f"历史质量证据缺失：{filename}")
        try:
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError(f"历史质量证据 JSON 顶层不是对象：{filename}")
                json_file_count += 1
            else:
                if not path.read_text(encoding="utf-8").strip():
                    raise RuntimeError(f"历史质量证据 Markdown 为空：{filename}")
                markdown_file_count += 1
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            raise RuntimeError(f"历史质量证据 JSON/Markdown 无法读取：{filename}") from None
    return {
        "required_filenames": list(HISTORICAL_RESULT_FILENAMES),
        "required_file_count": len(HISTORICAL_RESULT_FILENAMES),
        "json_file_count": json_file_count,
        "markdown_file_count": markdown_file_count,
        "all_present_and_readable": True,
    }


def validate_sealed_raw_identity(path: Path = RAW_RESULT_PATH) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError("封存的 7R5-I raw 证据缺失")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        raise RuntimeError("封存的 7R5-I raw JSON 无法读取") from None
    if not isinstance(payload, dict) or payload.get("stage") != SEALED_RUN_ID or payload.get("mode") != "real_raw":
        raise RuntimeError("封存 raw 不是登记的 7R5-I real raw")
    expected_case_ids = {
        "plan_records": [f"P{index:02d}" for index in range(len(V5_PLAN_JDS))],
        "report_records": [f"R{index:02d}" for index in range(len(V5_REPORT_PAIRS))],
        "stability_records": [
            f"S{index:02d}-{run}"
            for index in V5_STABILITY_SAMPLE_INDICES
            for run in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1)
        ],
    }
    for key, case_ids in expected_case_ids.items():
        records = payload.get(key)
        if not isinstance(records, list) or [item.get("case_id") for item in records if isinstance(item, dict)] != case_ids:
            raise RuntimeError(f"封存 raw 的 {key} 固定 case 身份或分母不完整")
    attempts = payload.get("attempt_audit")
    if not isinstance(attempts, list) or len(attempts) != 29:
        raise RuntimeError("封存 raw 的 attempt_audit 固定分母不完整")
    attempt_ids = [item.get("case_id") for item in attempts if isinstance(item, dict)]
    if len(attempt_ids) != len(attempts) or len(set(attempt_ids)) != len(attempt_ids):
        raise RuntimeError("封存 raw 的 attempt case ID 缺失或重复")
    return {
        "stage": SEALED_RUN_ID,
        "mode": "real_raw",
        "plan_case_count": len(expected_case_ids["plan_records"]),
        "report_case_count": len(expected_case_ids["report_records"]),
        "stability_case_count": len(expected_case_ids["stability_records"]),
        "attempt_count": len(attempts),
    }


def result_paths(run_id: str = SEALED_RUN_ID) -> dict[str, str]:
    if run_id == SEALED_RUN_ID:
        return {
            "raw": str(RAW_RESULT_PATH),
            "human_audit": str(HUMAN_AUDIT_PATH),
            "final": str(FINAL_RESULT_PATH),
        }
    if run_id == ACTIVE_RUN_ID:
        return {
            "preflight": str(I2_PREFLIGHT_PATH),
            "raw": str(I2_RAW_RESULT_PATH),
            "human_audit": str(I2_HUMAN_AUDIT_PATH),
            "final": str(I2_FINAL_RESULT_PATH),
        }
    if run_id == I3_RUN_ID:
        return {
            "preflight": str(I3_PREFLIGHT_PATH),
            "raw": str(I3_RAW_RESULT_PATH),
            "human_audit": str(I3_HUMAN_AUDIT_PATH),
            "final": str(I3_FINAL_RESULT_PATH),
        }
    if run_id == I4_RUN_ID:
        return {
            "preflight": str(I4_PREFLIGHT_PATH),
            "raw": str(I4_RAW_RESULT_PATH),
            "human_audit": str(I4_HUMAN_AUDIT_PATH),
            "final": str(I4_FINAL_RESULT_PATH),
        }
    raise RuntimeError(f"未登记的 5.0 质量运行批次：{run_id}")


def result_lifecycle_contract() -> dict[str, Any]:
    return {
        "sealed_run_id": SEALED_RUN_ID,
        "active_run_id": ACTIVE_RUN_ID,
        "sealed_raw_identity": {
            "stage": SEALED_RUN_ID,
            "mode": "real_raw",
            "plan_case_count": 10,
            "report_case_count": 20,
            "stability_case_count": 15,
            "attempt_count": 29,
        },
        "active_paths": result_paths(ACTIVE_RUN_ID),
        "states": list(I2_LIFECYCLE_STATES),
        "unknown_json_policy": "reject",
        "helper_can_satisfy_human_audit": False,
        "write_policy": "registered_active_path_once_only",
    }


def classify_result_entry(path: Path) -> str:
    resolved = path.resolve()
    if resolved == RAW_RESULT_PATH.resolve():
        return "sealed_raw"
    if resolved in {
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
    }:
        return "sealed_formal"
    if resolved in {
        Path(value).resolve() for value in result_paths(ACTIVE_RUN_ID).values()
    }:
        return "active_formal"
    if resolved == I3_SUPERSEDED_PREFLIGHT_PATH.resolve():
        return "i3_superseded_preflight"
    i3_paths = {
        key: Path(value).resolve()
        for key, value in result_paths(I3_RUN_ID).items()
    }
    if resolved == i3_paths["preflight"]:
        return "i3_preflight"
    if resolved in {
        i3_paths["raw"],
        i3_paths["human_audit"],
        i3_paths["final"],
    }:
        return "i3_formal"
    i4_paths = {
        key: Path(value).resolve()
        for key, value in result_paths(I4_RUN_ID).items()
    }
    if resolved == i4_paths["preflight"]:
        return "i4_preflight"
    if resolved in {
        i4_paths["raw"],
        i4_paths["human_audit"],
        i4_paths["final"],
    }:
        return "i4_formal"
    if resolved == I2_HELPER_PATH.resolve():
        return "helper"
    if resolved.parent == V5_RESULTS_DIR.resolve() and resolved.suffix.lower() == ".json":
        raise RuntimeError(f"v5-quality-results 存在未登记 JSON：{resolved.name}")
    return "other"


def _active_lifecycle_state() -> tuple[str, list[str]]:
    paths = result_paths(ACTIVE_RUN_ID)
    existing_keys = [key for key, value in paths.items() if Path(value).exists()]
    state_by_existing = {
        (): "i2_not_started",
        ("preflight",): "i2_preflight_complete",
        ("preflight", "raw"): "i2_raw_complete",
        ("preflight", "raw", "human_audit"): "i2_human_complete",
        ("preflight", "raw", "human_audit", "final"): "i2_final_complete",
    }
    state = state_by_existing.get(tuple(existing_keys))
    if state is None:
        raise RuntimeError(
            "7R5-I2 正式结果状态非法或发生越级写入："
            + ", ".join(existing_keys)
        )
    return state, [paths[key] for key in existing_keys]


def _i3_lifecycle_state() -> tuple[str, list[str]]:
    paths = result_paths(I3_RUN_ID)
    existing_keys = [key for key, value in paths.items() if Path(value).exists()]
    state_by_existing = {
        (): "i3_not_started",
        ("preflight",): "i3_preflight_complete",
        ("preflight", "raw"): "i3_raw_complete",
        ("preflight", "raw", "human_audit"): "i3_human_complete",
        ("preflight", "raw", "human_audit", "final"): "i3_final_complete",
    }
    state = state_by_existing.get(tuple(existing_keys))
    if state is None:
        raise RuntimeError(
            "7R5-I3-R1 正式结果状态非法或发生越级写入："
            + ", ".join(existing_keys)
        )
    return state, [paths[key] for key in existing_keys]


def _i4_lifecycle_state() -> tuple[str, list[str]]:
    paths = result_paths(I4_RUN_ID)
    existing_keys = [key for key, value in paths.items() if Path(value).exists()]
    state_by_existing = {
        (): "i4_not_started",
        ("preflight",): "i4_preflight_complete",
        ("preflight", "raw"): "i4_raw_complete",
        ("preflight", "raw", "human_audit"): "i4_human_complete",
        ("preflight", "raw", "human_audit", "final"): "i4_final_complete",
    }
    state = state_by_existing.get(tuple(existing_keys))
    if state is None:
        raise RuntimeError(
            "7R5-I4 正式结果状态非法或发生越级写入："
            + ", ".join(existing_keys)
        )
    return state, [paths[key] for key in existing_keys]


def validate_i3_result_lifecycle(
    *, expected_state: str | None = None
) -> dict[str, Any]:
    historical = validate_historical_results()
    sealed_identity = validate_sealed_raw_identity()
    i3_paths = tuple(
        Path(value).resolve() for value in result_paths(I3_RUN_ID).values()
    )
    protected_paths = {
        RAW_RESULT_PATH.resolve(),
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
        *(
            Path(value).resolve()
            for value in result_paths(ACTIVE_RUN_ID).values()
        ),
        I3_SUPERSEDED_PREFLIGHT_PATH.resolve(),
    }
    historical_paths = {
        (STAGE7_RESULTS_DIR / filename).resolve()
        for filename in HISTORICAL_RESULT_FILENAMES
    }
    if (
        len(i3_paths) != len(set(i3_paths))
        or set(i3_paths) & protected_paths
        or set(i3_paths) & historical_paths
        or any(path.parent != V5_RESULTS_DIR.resolve() for path in i3_paths)
    ):
        raise RuntimeError("7R5-I3-R1 路径重复、越界或覆盖既有证据")
    if V5_RESULTS_DIR.exists():
        for entry in V5_RESULTS_DIR.iterdir():
            classify_result_entry(entry)
    state, existing = _i3_lifecycle_state()
    if expected_state is not None and expected_state not in I3_LIFECYCLE_STATES:
        raise RuntimeError(f"未登记的 7R5-I3-R1 生命周期状态：{expected_state}")
    if expected_state is not None and state != expected_state:
        raise RuntimeError(
            f"7R5-I3-R1 生命周期状态不符：期望 {expected_state}，实际 {state}"
        )
    return {
        "run_id": I3_RUN_ID,
        "state": state,
        "sealed_raw_identity": sealed_identity,
        "active_paths": result_paths(I3_RUN_ID),
        "active_existing": existing,
        "historical_results": historical,
        "helper_can_satisfy_human_audit": False,
    }


def validate_i4_result_lifecycle(
    *, expected_state: str | None = None
) -> dict[str, Any]:
    """Validate I4 without changing or reinterpreting I2/I3-R1 evidence."""

    historical = validate_historical_results()
    sealed_identity = validate_sealed_raw_identity()
    i4_paths = tuple(
        Path(value).resolve() for value in result_paths(I4_RUN_ID).values()
    )
    protected_paths = {
        RAW_RESULT_PATH.resolve(),
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
        *(
            Path(value).resolve()
            for run_id in (ACTIVE_RUN_ID, I3_RUN_ID)
            for value in result_paths(run_id).values()
        ),
        I3_SUPERSEDED_PREFLIGHT_PATH.resolve(),
    }
    historical_paths = {
        (STAGE7_RESULTS_DIR / filename).resolve()
        for filename in HISTORICAL_RESULT_FILENAMES
    }
    if (
        len(i4_paths) != len(set(i4_paths))
        or set(i4_paths) & protected_paths
        or set(i4_paths) & historical_paths
        or any(path.parent != V5_RESULTS_DIR.resolve() for path in i4_paths)
    ):
        raise RuntimeError("7R5-I4 路径重复、越界或覆盖已有证据")
    if I4_REVIEW_PATH.resolve() in protected_paths or (
        I4_REVIEW_PATH.parent.resolve() != V5_RESULTS_DIR.resolve()
    ):
        raise RuntimeError("7R5-I4 复核材料路径越界或覆盖已有证据")
    if V5_RESULTS_DIR.exists():
        for entry in V5_RESULTS_DIR.iterdir():
            classify_result_entry(entry)
    state, existing = _i4_lifecycle_state()
    if expected_state is not None and expected_state not in I4_LIFECYCLE_STATES:
        raise RuntimeError(f"未登记的 7R5-I4 生命周期状态：{expected_state}")
    if expected_state is not None and state != expected_state:
        raise RuntimeError(
            f"7R5-I4 生命周期状态不符：期望 {expected_state}，实际 {state}"
        )
    return {
        "run_id": I4_RUN_ID,
        "state": state,
        "sealed_raw_identity": sealed_identity,
        "active_paths": result_paths(I4_RUN_ID),
        "active_existing": existing,
        "historical_results": historical,
        "helper_can_satisfy_human_audit": False,
    }


def validate_result_lifecycle(
    *, run_id: str, expected_state: str | None = None
) -> dict[str, Any]:
    if run_id == I3_RUN_ID:
        return validate_i3_result_lifecycle(expected_state=expected_state)
    if run_id == I4_RUN_ID:
        return validate_i4_result_lifecycle(expected_state=expected_state)
    if run_id != ACTIVE_RUN_ID:
        raise RuntimeError(f"质量运行批次已经封存或未登记：{run_id}")
    historical = validate_historical_results()
    sealed_identity = validate_sealed_raw_identity()
    if HUMAN_AUDIT_PATH.exists() or FINAL_RESULT_PATH.exists():
        raise RuntimeError("封存的 7R5-I human/final 路径不应被补写")
    active_paths = tuple(
        Path(value).resolve() for value in result_paths(ACTIVE_RUN_ID).values()
    )
    historical_paths = {
        (STAGE7_RESULTS_DIR / filename).resolve()
        for filename in HISTORICAL_RESULT_FILENAMES
    }
    sealed_paths = {
        RAW_RESULT_PATH.resolve(),
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
    }
    if (
        len(active_paths) != len(set(active_paths))
        or set(active_paths) & historical_paths
        or set(active_paths) & sealed_paths
        or any(path.parent != V5_RESULTS_DIR.resolve() for path in active_paths)
    ):
        raise RuntimeError("7R5-I2 路径重复、越界或覆盖旧证据")
    if V5_RESULTS_DIR.exists():
        for entry in V5_RESULTS_DIR.iterdir():
            classify_result_entry(entry)
    state, active_existing = _active_lifecycle_state()
    if expected_state is not None and expected_state not in I2_LIFECYCLE_STATES:
        raise RuntimeError(f"未登记的 7R5-I2 生命周期状态：{expected_state}")
    if expected_state is not None and state != expected_state:
        raise RuntimeError(
            f"7R5-I2 生命周期状态不符：期望 {expected_state}，实际 {state}"
        )
    return {
        "run_id": ACTIVE_RUN_ID,
        "state": state,
        "sealed_raw_identity": sealed_identity,
        "active_paths": result_paths(ACTIVE_RUN_ID),
        "active_existing": active_existing,
        "historical_results": historical,
        "helper_can_satisfy_human_audit": False,
    }


def assert_result_write_allowed(
    *, run_id: str, target: Path, expected_state: str
) -> dict[str, Any]:
    resolved = target.resolve()
    if resolved in {
        RAW_RESULT_PATH.resolve(),
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
    }:
        raise RuntimeError("7R5-I 已封存，拒绝跨轮覆盖")
    if run_id == I4_RUN_ID:
        lifecycle = validate_i4_result_lifecycle(expected_state=expected_state)
        active_paths = {
            key: Path(value).resolve()
            for key, value in result_paths(I4_RUN_ID).items()
        }
        allowed_key_by_state = {
            "i4_not_started": "preflight",
            "i4_preflight_complete": "raw",
            "i4_raw_complete": "human_audit",
            "i4_human_complete": "final",
        }
        allowed_key = allowed_key_by_state.get(lifecycle["state"])
        if allowed_key is None or resolved != active_paths[allowed_key]:
            raise RuntimeError(
                "当前 7R5-I4 状态不允许写入该正式结果路径"
            )
        if resolved.exists():
            raise RuntimeError("7R5-I4 质量结果已经存在，拒绝覆盖")
        return {
            "run_id": I4_RUN_ID,
            "state": lifecycle["state"],
            "target": str(target),
            "write_count": 0,
        }
    if run_id == I3_RUN_ID:
        lifecycle = validate_i3_result_lifecycle(expected_state=expected_state)
        active_paths = {
            key: Path(value).resolve()
            for key, value in result_paths(I3_RUN_ID).items()
        }
        allowed_key_by_state = {
            "i3_not_started": "preflight",
            "i3_preflight_complete": "raw",
            "i3_raw_complete": "human_audit",
            "i3_human_complete": "final",
        }
        allowed_key = allowed_key_by_state.get(lifecycle["state"])
        if allowed_key is None or resolved != active_paths[allowed_key]:
            raise RuntimeError(
                "当前 7R5-I3-R1 状态不允许写入该正式结果路径"
            )
        if resolved.exists():
            raise RuntimeError("7R5-I3-R1 质量结果已经存在，拒绝覆盖")
        return {
            "run_id": I3_RUN_ID,
            "state": lifecycle["state"],
            "target": str(target),
            "write_count": 0,
        }
    lifecycle = validate_result_lifecycle(
        run_id=run_id, expected_state=expected_state
    )
    active_paths = {
        key: Path(value).resolve()
        for key, value in result_paths(ACTIVE_RUN_ID).items()
    }
    allowed_key_by_state = {
        "i2_not_started": "preflight",
        "i2_preflight_complete": "raw",
        "i2_raw_complete": "human_audit",
        "i2_human_complete": "final",
    }
    allowed_key = allowed_key_by_state.get(lifecycle["state"])
    if allowed_key is None or resolved != active_paths[allowed_key]:
        raise RuntimeError("当前 7R5-I2 状态不允许写入该正式结果路径")
    if resolved.exists():
        raise RuntimeError("7R5-I2 质量结果已经存在，拒绝覆盖")
    return {
        "run_id": ACTIVE_RUN_ID,
        "state": lifecycle["state"],
        "target": str(target),
        "write_count": 0,
    }


def validate_result_path_isolation(*, require_empty: bool) -> dict[str, Any]:
    paths = tuple(Path(value).resolve() for value in result_paths().values())
    historical = tuple((STAGE7_RESULTS_DIR / name).resolve() for name in HISTORICAL_RESULT_FILENAMES)
    if len(paths) != len(set(paths)) or set(paths) & set(historical):
        raise RuntimeError("5.0 新结果路径重复或覆盖历史证据")
    if any(path.parent != V5_RESULTS_DIR.resolve() for path in paths):
        raise RuntimeError("5.0 结果必须写入独立 v5-quality-results 目录")
    existing = [str(path) for path in paths if path.exists()]
    if require_empty and existing:
        raise RuntimeError("5.0 正式结果路径并非全空，拒绝再次执行")
    return {"paths": result_paths(), "existing": existing, "overlap_count": 0}


def call_budget() -> dict[str, Any]:
    if (V5_PLAN_CALL_BUDGET, V5_REPORT_CALL_BUDGET, V5_STABILITY_CALL_BUDGET) != (10, 20, 15):
        raise RuntimeError("冻结调用预算已经漂移")
    return {
        "plan_business_calls": 10,
        "report_business_calls": 20,
        "stability_business_calls": 15,
        "baseline_business_calls": BASELINE_BUSINESS_CALLS,
        "maximum_infrastructure_retries": BASELINE_BUSINESS_CALLS,
        "maximum_api_attempts": MAXIMUM_API_ATTEMPTS,
        "content_error_retry_count": 0,
        "maximum_infrastructure_retries_per_business_call": 1,
        "plan_max_output_tokens_per_attempt": PLAN_MAX_OUTPUT_TOKENS,
        "report_max_output_tokens_per_attempt": REPORT_MAX_OUTPUT_TOKENS,
        "baseline_max_output_tokens": 500_000,
        "retry_ceiling_max_output_tokens": 1_000_000,
    }


def execution_contract() -> dict[str, Any]:
    return {
        "model": PLANNED_MODEL,
        "temperature": TEMPERATURE,
        "thinking": THINKING,
        "response_format": RESPONSE_FORMAT,
        "sdk_automatic_retries": SDK_AUTOMATIC_RETRIES,
        "plan_prompt_version": PLAN_PROMPT_VERSION,
        "report_prompt_version": REPORT_PROMPT_VERSION,
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "plan_service_behavior_version": "lightweight_plan_generation_v4",
        "report_service_behavior_version": "lightweight_report_generation_v8",
        "normal_business_calls_per_sample": 1,
    }


def i2_raw_execution_contract() -> dict[str, Any]:
    """Return the execution contract sealed into the paid 7R5-I2 raw run."""

    return {
        "model": "deepseek-v4-flash",
        "temperature": 0.1,
        "thinking": "disabled",
        "response_format": "json_object",
        "sdk_automatic_retries": 0,
        "plan_prompt_version": "job_evaluation_plan_lightweight_v2",
        "report_prompt_version": "screening_evaluation_lightweight_v3",
        "plan_schema_version": "5.0",
        "report_schema_version": "5.0",
        "plan_service_behavior_version": "lightweight_plan_generation_v3",
        "report_service_behavior_version": "lightweight_report_generation_v6",
        "normal_business_calls_per_sample": 1,
    }


def human_audit_contract() -> dict[str, Any]:
    return {
        "method": "human_review_against_frozen_labels",
        "llm_as_judge_is_sufficient": False,
        "metrics": {
            "plan_required_covered_count": {"minimum": 55, "maximum": 55},
            "plan_forbidden_addition_count": {"minimum": 0, "maximum": 22},
            "plan_sensitive_criterion_count": {"minimum": 0, "maximum": 30},
            "plan_non_evaluation_misclassified_count": {"minimum": 0, "maximum": 26},
            "report_fabricated_fact_count": {"minimum": 0, "maximum": 20},
            "report_severe_fact_error_count": {"minimum": 0, "maximum": 20},
            "report_sensitive_scoring_count": {"minimum": 0, "maximum": 20},
            "report_automatic_decision_count": {"minimum": 0, "maximum": 20},
            "report_direction_consistent_count": {"minimum": 0, "maximum": 20},
            "required_direction_consistent_count": {"minimum": 0, "maximum": 107},
            "stability_severe_fact_error_count": {"minimum": 0, "maximum": 15},
            "stability_sensitive_scoring_count": {"minimum": 0, "maximum": 15},
        },
    }


def validate_pricing_snapshot(payload: dict[str, Any], *, max_age_hours: int = 24) -> dict[str, Any]:
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
    except (KeyError, ValueError, TypeError):
        raise RuntimeError("官方价格快照缺少带时区的 checked_at") from None
    if checked_at.tzinfo is None:
        raise RuntimeError("官方价格 checked_at 必须包含时区")
    age_seconds = (datetime.now(timezone.utc) - checked_at.astimezone(timezone.utc)).total_seconds()
    if age_seconds < -300 or age_seconds > max_age_hours * 3600:
        raise RuntimeError("官方价格快照已过期或时间异常，必须重新查询")
    if payload.get("source_url") != OFFICIAL_PRICING_SOURCE_URL:
        raise RuntimeError("价格来源不是冻结的 DeepSeek 官方价格页")
    if payload.get("model") != PLANNED_MODEL:
        raise RuntimeError("价格快照模型与本轮冻结模型不一致")
    selected_tier = payload.get("selected_tier")
    if selected_tier not in {"off_peak", "peak"}:
        raise RuntimeError("价格快照必须明确 peak 或 off_peak")
    raw_rates = payload.get("usd_per_million_tokens")
    if not isinstance(raw_rates, dict):
        raise RuntimeError("价格快照缺少美元单价")
    rates: dict[str, float] = {}
    for key in ("cache_hit_input", "cache_miss_input", "output"):
        try:
            value = Decimal(str(raw_rates[key]))
        except (KeyError, InvalidOperation, ValueError):
            raise RuntimeError(f"价格字段无效：{key}") from None
        if not value.is_finite() or value < 0:
            raise RuntimeError(f"价格字段不能为负数或无穷值：{key}")
        rates[key] = float(value)
    return {
        "checked_at": checked_at.isoformat(),
        "source_url": OFFICIAL_PRICING_SOURCE_URL,
        "model": PLANNED_MODEL,
        "selected_tier": selected_tier,
        "timezone": "Asia/Shanghai",
        "schedule": str(payload.get("schedule") or "").strip(),
        "usd_per_million_tokens": rates,
    }


def estimate_attempt_cost_usd(
    *,
    pricing: dict[str, Any],
    input_tokens: int | None,
    cache_hit_input_tokens: int | None,
    cache_miss_input_tokens: int | None,
    output_tokens: int | None,
) -> dict[str, Any]:
    if input_tokens is None or output_tokens is None:
        return {"complete": False, "estimated_cost_usd": None, "reason": "provider_usage_incomplete"}
    hit = cache_hit_input_tokens
    miss = cache_miss_input_tokens
    conservative = False
    if hit is None or miss is None:
        hit, miss, conservative = 0, input_tokens, True
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (input_tokens, hit, miss, output_tokens)):
        return {"complete": False, "estimated_cost_usd": None, "reason": "invalid_token_usage"}
    if hit + miss != input_tokens:
        return {"complete": False, "estimated_cost_usd": None, "reason": "cache_split_mismatch"}
    rates = pricing["usd_per_million_tokens"]
    total = (
        Decimal(hit) * Decimal(str(rates["cache_hit_input"]))
        + Decimal(miss) * Decimal(str(rates["cache_miss_input"]))
        + Decimal(output_tokens) * Decimal(str(rates["output"]))
    ) / Decimal(1_000_000)
    return {
        "complete": True,
        "estimated_cost_usd": float(total),
        "cache_split_conservative": conservative,
        "reason": None,
    }


def write_new_json(
    path: Path,
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
    expected_state: str | None = None,
) -> None:
    resolved = path.resolve()
    sealed_paths = {
        RAW_RESULT_PATH.resolve(),
        HUMAN_AUDIT_PATH.resolve(),
        FINAL_RESULT_PATH.resolve(),
    }
    if resolved in sealed_paths:
        raise RuntimeError("7R5-I 已封存，拒绝补写或覆盖旧结果")
    if run_id is not None:
        if expected_state is None:
            raise RuntimeError("I2 正式写入必须声明预期生命周期状态")
        assert_result_write_allowed(
            run_id=run_id,
            target=path,
            expected_state=expected_state,
        )
        allowed = {
            Path(value).resolve() for value in result_paths(run_id).values()
        }
    else:
        allowed = {Path(value).resolve() for value in result_paths().values()}
    if resolved not in allowed:
        raise RuntimeError("拒绝写入未登记的 5.0 质量结果路径")
    if resolved.exists():
        raise RuntimeError("5.0 质量结果已经存在，拒绝覆盖")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
