from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))

from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_MAX_ITEMS,
    JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    job_evaluation_plan_service,
)
from stage7_7rf_plan_quality_cases import CASES, TARGETED_CASE_IDS  # noqa: E402


EXPECTED_CASE_IDS = tuple(f"J5-{index:02d}" for index in range(1, 21))
PRIORITY_BY_FIELD = {
    "job_responsibilities": "general",
    "candidate_requirements": "required",
    "preferred_qualifications": "preferred",
}


def _serialized(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _case_job(case: dict[str, Any], index: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=74_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=case["job_background"],
        job_responsibilities=case["job_responsibilities"],
        candidate_requirements=case["candidate_requirements"],
        preferred_qualifications=case["preferred_qualifications"],
        public_notes=case["public_notes"],
        status="open",
    )


def _normalized(value: str) -> str:
    return "".join(character.lower() for character in value if not character.isspace())


def _matching_units(expectation: dict[str, Any], units: list[Any]) -> list[Any]:
    terms = [_normalized(term) for term in expectation["title_any"]]
    preferred = [
        unit
        for unit in units
        if unit.source_field == expectation["source_field"]
        and any(term in _normalized(unit.source_text) for term in terms)
    ]
    if expectation["min_sources"] <= 1:
        return preferred[:1]
    all_matches = [
        unit
        for unit in units
        if any(term in _normalized(unit.source_text) for term in terms)
    ]
    return all_matches


def _projected_facts(case: dict[str, Any], units: list[Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for index, expectation in enumerate(case["expectations"], start=1):
        matches = _matching_units(expectation, units)
        if len(matches) < expectation["min_sources"]:
            raise RuntimeError(
                f"{case['case_id']}:{expectation['expectation_id']} 的人工事实来源不足"
            )
        sources = [
            {
                "source_field": unit.source_field,
                "source_unit_id": unit.source_unit_id,
                # 使用完整 unit 作为容量估算的保守 quote；生产事实仍应取最小连续原文。
                "source_quote": unit.source_text,
            }
            for unit in matches
        ]
        priorities = {PRIORITY_BY_FIELD[source["source_field"]] for source in sources}
        priority = next(
            value for value in ("required", "preferred", "general") if value in priorities
        )
        facts.append(
            {
                "fact_id": f"fact:{index:04d}",
                "category": "other",
                "priority": priority,
                "sources": sources,
            }
        )
    return facts


def _projected_criteria(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 这里只估算 JSON 容量，不创建业务目标：每 3 条顺序事实形成一个临时容量分组。
    return [
        {
            "criterion_id": f"criterion:{group_index:04d}",
            "name": f"容量估算分组 {group_index:02d}",
            "fact_ids": [fact["fact_id"] for fact in facts[offset : offset + 3]],
        }
        for group_index, offset in enumerate(range(0, len(facts), 3), start=1)
    ]


def _distribution(values: list[int]) -> dict[str, int | float]:
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "min": min(ordered),
        "median": statistics.median(ordered),
        "p95": ordered[p95_index],
        "max": max(ordered),
        "sum": sum(ordered),
    }


def build_capacity_baseline() -> dict[str, Any]:
    if tuple(case["case_id"] for case in CASES) != EXPECTED_CASE_IDS:
        raise RuntimeError("容量基线必须严格复用冻结的 J5-01—J5-20")
    if tuple(TARGETED_CASE_IDS) != (
        "J5-03",
        "J5-07",
        "J5-14",
        "J5-17",
        "J5-19",
        "J5-20",
    ):
        raise RuntimeError("容量基线必须严格复用冻结的 6 份定向样本")

    rows: list[dict[str, Any]] = []
    public_notes_excluded = True
    for index, case in enumerate(CASES, start=1):
        job = _case_job(case, index)
        snapshot = job_evaluation_plan_service.build_input_snapshot(job)
        changed_notes_snapshot = job_evaluation_plan_service.build_input_snapshot(
            _case_job({**case, "public_notes": f"{case['public_notes']}（仅备注变化）"}, index)
        )
        snapshot_payload = snapshot.model_dump(mode="json")
        units = list(snapshot.source_units or [])
        facts = _projected_facts(case, units)
        criteria = _projected_criteria(facts)
        snapshot_json = _serialized(snapshot_payload)
        units_json = _serialized(snapshot_payload["source_units"])
        facts_json = _serialized(facts)
        criteria_json = _serialized(criteria)
        combined_json = _serialized(
            {"requirement_facts": facts, "evaluation_criteria": criteria}
        )
        public_notes_excluded &= (
            case["public_notes"] not in snapshot_json
            and snapshot.model_dump(mode="json")
            == changed_notes_snapshot.model_dump(mode="json")
            and job_evaluation_plan_service.fingerprint_snapshot(snapshot)
            == job_evaluation_plan_service.fingerprint_snapshot(changed_notes_snapshot)
        )
        expected_outcome = (
            "failed:JOB_EVALUATION_PLAN_NO_FACTS"
            if not facts
            else (
                "pending_confirmation+overly_broad_jd"
                if len(facts) >= 31
                else (
                    "pending_confirmation+limited_basis"
                    if len(facts) <= 4
                    else "pending_confirmation"
                )
            )
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "title": case["title"],
                "targeted": case["case_id"] in TARGETED_CASE_IDS,
                "source_unit_count": len(units),
                "source_units_serialized_chars": len(units_json),
                "manual_fact_count": len(facts),
                "estimated_criterion_count": len(criteria),
                "input_snapshot_serialized_chars": len(snapshot_json),
                "facts_serialized_chars": len(facts_json),
                "criteria_serialized_chars": len(criteria_json),
                "facts_criteria_serialized_chars": len(combined_json),
                "legacy_30_item_limit_would_reject": (
                    len(facts) > JOB_EVALUATION_PLAN_MAX_ITEMS
                ),
                "legacy_100_source_unit_limit_would_reject": (
                    len(units) > JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS
                ),
                "v4_expected_outcome": expected_outcome,
            }
        )

    metric_names = (
        "source_unit_count",
        "source_units_serialized_chars",
        "manual_fact_count",
        "estimated_criterion_count",
        "input_snapshot_serialized_chars",
        "facts_serialized_chars",
        "criteria_serialized_chars",
        "facts_criteria_serialized_chars",
    )
    aggregate = {
        name: _distribution([int(row[name]) for row in rows]) for name in metric_names
    }
    frozen_sha = hashlib.sha256(_serialized(CASES).encode("utf-8")).hexdigest()
    return {
        "stage": "7R4-A",
        "mode": "offline_capacity_baseline",
        "sample_count": len(rows),
        "targeted_case_ids": list(TARGETED_CASE_IDS),
        "frozen_case_sha256": frozen_sha,
        "manual_fact_definition": (
            "复用 3.0 冻结质量夹具中的 245 条人工主要语义 expectation；"
            "每条 expectation 作为 4.0 最低一条独立 fact，J5-14 的客户访谈保留多来源"
        ),
        "criterion_estimation_method": (
            "仅为容量估算按原顺序每 3 条 facts 分一组；不是业务数量目标，"
            "真实 criterion 可从 1 到 fact 数量"
        ),
        "public_notes_excluded_from_every_snapshot": public_notes_excluded,
        "public_notes_excluded_from_every_fingerprint": public_notes_excluded,
        "current_v3_limits": {
            "item_count": JOB_EVALUATION_PLAN_MAX_ITEMS,
            "source_unit_count": JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS,
            "adapter_input_chars": 100_000,
            "adapter_output_tokens": 8_000,
        },
        "aggregate": aggregate,
        "cases": rows,
        "technical_limit_recommendations": {
            "input_snapshot_serialized_chars": {
                "candidate": 1_000_000,
                "reason": (
                    "冻结样本远低于该值；但极端碎片化会放大 source-unit JSON，"
                    "现有 100000 可能拒绝字段长度仍合法的 JD"
                ),
                "requires_product_confirmation": True,
            },
            "single_source_unit_chars": {
                "candidate": 10_000,
                "reason": "与任一评价字段当前最大长度一致，不截断单个合法字段",
                "requires_product_confirmation": False,
            },
            "source_unit_count": {
                "candidate": 512,
                "reason": "高于冻结最大值的多倍余量，但极端碎片化的合法 JD 仍可能超过",
                "requires_product_confirmation": True,
            },
            "fact_count": {
                "candidate": 512,
                "reason": "移除 30 条业务硬失败；候选值只作技术防护，仍可能拒绝极端合法 JD",
                "requires_product_confirmation": True,
            },
            "criterion_count": {
                "candidate": 512,
                "reason": "允许 criterion 数量等于 fact 数量；与 fact 技术候选值保持一致",
                "requires_product_confirmation": True,
            },
            "facts_serialized_chars": {
                "candidate": 262_144,
                "reason": "覆盖冻结 facts 最大序列化尺寸并为多来源原文留出余量",
                "requires_product_confirmation": True,
            },
            "criteria_serialized_chars": {
                "candidate": 131_072,
                "reason": "覆盖 criterion 等于 fact 数量时的 ID 与名称开销",
                "requires_product_confirmation": True,
            },
            "combined_structured_output_chars": {
                "candidate": 393_216,
                "reason": "facts 与 criteria 独立上限之和；不得静默截断",
                "requires_product_confirmation": True,
            },
            "model_output_tokens_per_business_call": {
                "candidate": 16_000,
                "reason": "4.0 拆为独立输出且 31+ 合法；现有 8000 需在 7R4-C/G 再以 Fake 和 dry-run 验证",
                "requires_product_confirmation": True,
            },
        },
        "recommendation_gate": (
            "不把需要确认的候选值写入生产代码；它们可能让当前字段长度内的极端碎片化 JD 技术失败"
        ),
        "real_model_call_count": 0,
        "adapter_instantiated": False,
        "api_key_loaded": False,
        "result_file_written": False,
    }


def main() -> None:
    print(json.dumps(build_capacity_baseline(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
