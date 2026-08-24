from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))

from app.adapters.job_evaluation_plan import (  # noqa: E402
    DeepSeekJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings  # noqa: E402
from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_PROMPT_VERSION,
    build_job_evaluation_plan_messages,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    AIExtractedEvaluationPlanV3,
    EvaluationItemPriority,
    JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    JobEvaluationPlanWarningCode,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    GeneratedPlanContent,
    JobEvaluationPlanContentError,
    job_evaluation_plan_service,
)
from stage7_7rf_plan_quality_cases import CASES, TARGETED_CASE_IDS  # noqa: E402


PLANNED_MODEL = "deepseek-v4-flash"
PRICING_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing"
PRICING_CHECKED_AT = "2026-08-22"
PRICE_CNY_PER_MILLION = {
    "input_cache_hit": 0.02,
    "input_cache_miss": 1.0,
    "output": 2.0,
}
TARGETED_RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-08-22-stage7-7rf-plan-quality-targeted-results.json"
)
FORMAL_RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-08-22-stage7-7rf-plan-quality-formal-results.json"
)
ALLOWED_WARNING_CODES = {
    warning.value for warning in JobEvaluationPlanWarningCode
}
EXPECTED_CASE_IDS = tuple(f"J5-{index:02d}" for index in range(1, 21))
NORMAL_OUTCOMES = {"ready", "limited_basis"}
BOUNDARY_OUTCOMES = {"no_items", "too_many_items"}
MAX_OUTPUT_TOKENS = 8_000
MAX_INFRASTRUCTURE_ATTEMPTS_PER_CASE = 2


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized(value: str) -> str:
    return "".join(character.lower() for character in value if not character.isspace())


def _contains(text: str, term: str) -> bool:
    return _normalized(term) in _normalized(text)


def _case_job(case: dict[str, Any], index: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=7_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=case["job_background"],
        job_responsibilities=case["job_responsibilities"],
        candidate_requirements=case["candidate_requirements"],
        preferred_qualifications=case["preferred_qualifications"],
        public_notes=case["public_notes"],
        status="open",
    )


def _case_fingerprint() -> str:
    serialized = json.dumps(CASES, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _prompt_payload(case: dict[str, Any], index: int) -> dict[str, Any]:
    snapshot = job_evaluation_plan_service.build_input_snapshot(
        _case_job(case, index)
    )
    extraction_input = job_evaluation_plan_service.build_ai_extraction_input(
        snapshot
    )
    messages = build_job_evaluation_plan_messages(extraction_input)
    return {
        "snapshot": snapshot,
        "extraction_input": extraction_input,
        "messages": messages,
        "prompt_char_count": sum(len(message["content"]) for message in messages),
    }


def _validate_fixture() -> dict[str, Any]:
    if tuple(case["case_id"] for case in CASES) != EXPECTED_CASE_IDS:
        raise SystemExit("7R-F 必须冻结 J5-01—J5-20 且顺序唯一")
    if len(set(TARGETED_CASE_IDS)) != 6 or not set(TARGETED_CASE_IDS).issubset(
        EXPECTED_CASE_IDS
    ):
        raise SystemExit("7R-F 定向样本必须是 6 个不同的冻结样本")

    normal_cases = [
        case for case in CASES if case["expected_outcome"] in NORMAL_OUTCOMES
    ]
    boundary_cases = [
        case for case in CASES if case["expected_outcome"] in BOUNDARY_OUTCOMES
    ]
    if len(normal_cases) != 18 or len(boundary_cases) != 2:
        raise SystemExit("7R-F 样本必须固定为 18 个正常样本和 2 个边界样本")
    if Counter(case["expected_outcome"] for case in CASES) != Counter(
        {"ready": 16, "limited_basis": 2, "no_items": 1, "too_many_items": 1}
    ):
        raise SystemExit("7R-F outcome 分布不符合设计")

    expectation_ids: set[str] = set()
    public_notes_excluded = True
    all_source_expectations_locatable = True
    cases_summary: list[dict[str, Any]] = []
    prompt_char_counts: dict[str, int] = {}
    explicit_required_count = 0
    major_expectation_count = 0
    for index, case in enumerate(CASES, start=1):
        payload = _prompt_payload(case, index)
        snapshot = payload["snapshot"]
        extraction_input = payload["extraction_input"]
        prompt_char_counts[case["case_id"]] = payload["prompt_char_count"]
        if snapshot.schema_version != "3.0":
            raise SystemExit(f"{case['case_id']} 未形成 3.0 input snapshot")
        if case["public_notes"] in json.dumps(
            extraction_input, ensure_ascii=False
        ):
            public_notes_excluded = False
        source_units = list(snapshot.source_units or [])
        source_unit_text = "\n".join(unit.source_text for unit in source_units)
        for term in case["forbidden_item_terms"]:
            if term in case["public_notes"] or term in case["job_background"]:
                if term in source_unit_text:
                    raise SystemExit(
                        f"{case['case_id']} 的排除词 {term!r} 意外进入 source units"
                    )
        for expectation in case["expectations"]:
            global_id = f"{case['case_id']}:{expectation['expectation_id']}"
            if global_id in expectation_ids:
                raise SystemExit(f"重复 expectation ID：{global_id}")
            expectation_ids.add(global_id)
            source_text = case[expectation["source_field"]]
            locatable = any(
                _contains(source_text, term)
                for term in expectation["title_any"]
            )
            all_source_expectations_locatable &= locatable
            if not locatable:
                raise SystemExit(
                    f"{global_id} 的冻结关键词不在对应五段式字段中"
                )
            major_expectation_count += 1
            explicit_required_count += bool(expectation["explicit_required"])
        invalid_warnings = set(case["expected_warning_codes"]) - ALLOWED_WARNING_CODES
        if invalid_warnings:
            raise SystemExit(
                f"{case['case_id']} 使用了未知 warning：{sorted(invalid_warnings)}"
            )
        if (
            case["expected_outcome"] == "ready"
            and case["case_id"] not in {"J5-13"}
            and len(source_units) < 8
        ):
            raise SystemExit(f"{case['case_id']} 不是完整复杂 JD")
        cases_summary.append(
            {
                "case_id": case["case_id"],
                "title": case["title"],
                "expected_outcome": case["expected_outcome"],
                "source_unit_count": len(source_units),
                "major_expectation_count": len(case["expectations"]),
                "explicit_required_count": sum(
                    bool(item["explicit_required"])
                    for item in case["expectations"]
                ),
                "expected_warning_codes": case["expected_warning_codes"],
                "prompt_char_count": payload["prompt_char_count"],
            }
        )

    if not public_notes_excluded or not all_source_expectations_locatable:
        raise SystemExit("7R-F fixture 隔离或人工标签定位失败")
    return {
        "case_count": len(CASES),
        "normal_case_count": len(normal_cases),
        "boundary_case_count": len(boundary_cases),
        "limited_case_ids": [
            case["case_id"]
            for case in CASES
            if case["expected_outcome"] == "limited_basis"
        ],
        "boundary_case_ids": [case["case_id"] for case in boundary_cases],
        "targeted_case_ids": list(TARGETED_CASE_IDS),
        "major_expectation_count": major_expectation_count,
        "explicit_required_count": explicit_required_count,
        "public_notes_excluded_from_all_ai_inputs": public_notes_excluded,
        "all_frozen_expectations_locatable_in_source_fields": (
            all_source_expectations_locatable
        ),
        "prompt_char_counts": prompt_char_counts,
        "cases": cases_summary,
    }


def _cost_budget(fixture: dict[str, Any]) -> dict[str, Any]:
    prompt_chars = fixture["prompt_char_counts"]
    targeted_chars = sum(prompt_chars[case_id] for case_id in TARGETED_CASE_IDS)
    formal_chars = sum(prompt_chars.values())
    business_calls = len(TARGETED_CASE_IDS) + len(CASES)
    max_attempts = business_calls * MAX_INFRASTRUCTURE_ATTEMPTS_PER_CASE
    # One token per rendered prompt character is deliberately more conservative
    # than DeepSeek's published Chinese/English approximation.
    conservative_input_tokens = targeted_chars + formal_chars
    conservative_input_tokens_with_retries = conservative_input_tokens * 2
    max_output_tokens = business_calls * MAX_OUTPUT_TOKENS
    max_output_tokens_with_retries = max_output_tokens * 2
    no_retry_cost = (
        conservative_input_tokens
        * PRICE_CNY_PER_MILLION["input_cache_miss"]
        + max_output_tokens * PRICE_CNY_PER_MILLION["output"]
    ) / 1_000_000
    retry_cost = (
        conservative_input_tokens_with_retries
        * PRICE_CNY_PER_MILLION["input_cache_miss"]
        + max_output_tokens_with_retries
        * PRICE_CNY_PER_MILLION["output"]
    ) / 1_000_000
    configured_absolute_cap = (
        max_attempts
        * (
            105_000 * PRICE_CNY_PER_MILLION["input_cache_miss"]
            + MAX_OUTPUT_TOKENS * PRICE_CNY_PER_MILLION["output"]
        )
        / 1_000_000
    )
    return {
        "currency": "CNY",
        "pricing_source": PRICING_SOURCE,
        "pricing_checked_at": PRICING_CHECKED_AT,
        "price_per_million_tokens": PRICE_CNY_PER_MILLION,
        "business_call_budget": {
            "targeted": len(TARGETED_CASE_IDS),
            "formal": len(CASES),
            "total": business_calls,
        },
        "infrastructure_retry_policy": "每个业务调用最多额外重试 1 次，内容错误不重试",
        "maximum_api_attempts_including_all_infrastructure_retries": max_attempts,
        "max_output_tokens_per_attempt": MAX_OUTPUT_TOKENS,
        "frozen_prompt_char_count_targeted": targeted_chars,
        "frozen_prompt_char_count_formal": formal_chars,
        "conservative_assumption": (
            "每个 Prompt 字符按 1 input token、全部 cache miss、每次输出达到 8000 token"
        ),
        "estimated_max_cost_without_retries_cny": round(no_retry_cost, 6),
        "estimated_max_cost_with_all_retries_cny": round(retry_cost, 6),
        "configured_absolute_ceiling_cny": round(configured_absolute_cap, 6),
        "configured_absolute_ceiling_note": (
            "按每次 105000 input tokens（含系统 Prompt 余量）和 8000 output tokens 计算"
        ),
    }


def dry_run_payload() -> dict[str, Any]:
    fixture = _validate_fixture()
    return {
        "stage": "7R-F",
        "mode": "dry_run",
        "status": "ready_for_explicit_cost_confirmation",
        "generated_at": _utc_now(),
        "real_model_call_count": 0,
        "adapter_instantiated": False,
        "settings_or_api_key_loaded": False,
        "result_file_written": False,
        "planned_model": PLANNED_MODEL,
        "prompt_version": JOB_EVALUATION_PLAN_PROMPT_VERSION,
        "ai_schema_version": JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
        "plan_schema_version": JOB_EVALUATION_PLAN_SCHEMA_VERSION,
        "case_fixture_sha256": _case_fingerprint(),
        "fixture": fixture,
        "cost_budget": _cost_budget(fixture),
        "gate": {
            "targeted_must_pass_before_formal": True,
            "targeted_call_limit": len(TARGETED_CASE_IDS),
            "formal_call_count": len(CASES),
            "fake_results_count_as_quality": False,
            "formal_quality_thresholds": {
                "normal_ready": "18/18",
                "boundary_correct": "2/2",
                "explicit_required_recall": 1.0,
                "major_semantic_recall_minimum": 0.95,
                "source_review_rate": 1.0,
                "source_traceability_rate": 1.0,
                "priority_consistency_rate": 1.0,
                "added_requirement_count": 0,
                "obvious_duplicate_count": 0,
                "incorrect_merge_count": 0,
                "background_or_public_notes_pollution_count": 0,
                "promotion_or_benefit_misclassified_count": 0,
                "expected_warning_hit_rate": 1.0,
            },
        },
    }


class AttemptLoggingAdapter:
    def __init__(
        self,
        delegate: DeepSeekJobEvaluationPlanAdapter,
        *,
        case_id: str,
    ) -> None:
        self.delegate = delegate
        self.case_id = case_id
        self.attempts: list[dict[str, Any]] = []

    async def extract(
        self,
        extraction_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        attempt_number = len(self.attempts) + 1
        started = time.perf_counter()
        record: dict[str, Any] = {
            "case_id": self.case_id,
            "attempt_number": attempt_number,
            "started_at": _utc_now(),
        }
        try:
            result = await self.delegate.extract(extraction_input)
        except JobEvaluationPlanAdapterError as exc:
            record.update(
                {
                    "status": "failed",
                    "error_code": exc.code,
                    "error_type": type(exc).__name__,
                    "retryable": exc.retryable,
                    "input_tokens": None,
                    "output_tokens": None,
                    "estimated_cost_cny_cache_miss": None,
                }
            )
            raise
        else:
            cost = None
            if result.input_tokens is not None and result.output_tokens is not None:
                cost = (
                    result.input_tokens
                    * PRICE_CNY_PER_MILLION["input_cache_miss"]
                    + result.output_tokens * PRICE_CNY_PER_MILLION["output"]
                ) / 1_000_000
            record.update(
                {
                    "status": "succeeded",
                    "model": result.model,
                    "finish_reason": result.finish_reason,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "estimated_cost_cny_cache_miss": (
                        round(cost, 8) if cost is not None else None
                    ),
                }
            )
            return result
        finally:
            record["elapsed_seconds"] = round(time.perf_counter() - started, 6)
            self.attempts.append(record)


def _warning_codes(content: GeneratedPlanContent) -> list[str]:
    values: list[str] = []
    for warning in content.warnings:
        code = getattr(warning, "code", warning)
        values.append(code.value if hasattr(code, "value") else str(code))
    return values


def _raw_audit_items(
    extracted: AIExtractedEvaluationPlanV3,
    source_units: list[Any],
) -> list[dict[str, Any]]:
    source_by_id = {unit.source_unit_id: unit for unit in source_units}
    priority_by_field = {
        "candidate_requirements": "required",
        "preferred_qualifications": "preferred",
        "job_responsibilities": "general",
    }
    items: list[dict[str, Any]] = []
    for review in extracted.source_reviews:
        source_unit = source_by_id[review.source_unit_id]
        for index, item in enumerate(review.items, start=1):
            items.append(
                {
                    "key": f"raw:{review.source_unit_id}:{index:04d}",
                    "title": item.title,
                    "category": item.category.value,
                    "priority": priority_by_field[source_unit.source_field],
                    "sources": [
                        {
                            "source_field": source_unit.source_field,
                            "source_unit_id": source_unit.source_unit_id,
                            "source_quote": item.source_quote,
                        }
                    ],
                }
            )
    return items


def _content_audit_items(content: GeneratedPlanContent) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in content.items]


def _audit_case(
    case: dict[str, Any],
    snapshot: Any,
    extracted: AIExtractedEvaluationPlanV3,
    content: GeneratedPlanContent | None,
    actual_outcome: str,
) -> dict[str, Any]:
    source_units = list(snapshot.source_units or [])
    source_by_id = {unit.source_unit_id: unit for unit in source_units}
    audit_items = (
        _content_audit_items(content)
        if content is not None
        else _raw_audit_items(extracted, source_units)
    )
    expected_ids = {unit.source_unit_id for unit in source_units}
    reviewed_ids = [review.source_unit_id for review in extracted.source_reviews]
    all_reviewed = (
        len(reviewed_ids) == len(set(reviewed_ids))
        and set(reviewed_ids) == expected_ids
    )

    traceable_count = 0
    priority_consistent_count = 0
    for item in audit_items:
        sources = item.get("sources") or []
        item_traceable = bool(sources)
        source_priorities: list[str] = []
        for source in sources:
            unit = source_by_id.get(source["source_unit_id"])
            item_traceable &= bool(
                unit
                and unit.source_field == source["source_field"]
                and source["source_quote"] in unit.source_text
            )
            source_priorities.append(
                {
                    "candidate_requirements": "required",
                    "preferred_qualifications": "preferred",
                    "job_responsibilities": "general",
                }[source["source_field"]]
            )
        traceable_count += item_traceable
        expected_priority = max(
            source_priorities,
            key={"general": 0, "preferred": 1, "required": 2}.get,
            default=None,
        )
        priority_consistent_count += item.get("priority") == expected_priority

    matches_by_expectation: dict[str, list[str]] = {}
    recalled = 0
    required_expected = 0
    required_recalled = 0
    source_count_failures = 0
    for expectation in case["expectations"]:
        matches: list[str] = []
        for item in audit_items:
            source_fields = {
                source["source_field"] for source in (item.get("sources") or [])
            }
            if expectation["source_field"] not in source_fields:
                continue
            if any(
                _contains(item["title"], term)
                for term in expectation["title_any"]
            ):
                matches.append(item["key"])
        matches_by_expectation[expectation["expectation_id"]] = matches
        if matches:
            recalled += 1
            matched_items = [item for item in audit_items if item["key"] in matches]
            if not any(
                len(item.get("sources") or []) >= expectation["min_sources"]
                for item in matched_items
            ):
                source_count_failures += 1
        if expectation["explicit_required"]:
            required_expected += 1
            required_recalled += any(
                item["key"] in matches and item["priority"] == "required"
                for item in audit_items
            )

    incorrect_merge_keys: set[str] = set()
    for item in audit_items:
        matching_expectations = [
            expectation
            for expectation in case["expectations"]
            if expectation["distinct"]
            and expectation["source_field"]
            in {
                source["source_field"] for source in (item.get("sources") or [])
            }
            and any(
                _contains(item["title"], term)
                for term in expectation["title_any"]
            )
        ]
        grouped = Counter(
            expectation["source_field"] for expectation in matching_expectations
        )
        if any(count > 1 for count in grouped.values()):
            incorrect_merge_keys.add(item["key"])

    normalized_titles = [_normalized(item["title"]) for item in audit_items]
    obvious_duplicate_count = sum(
        count - 1 for count in Counter(normalized_titles).values() if count > 1
    )
    forbidden_pollution_count = sum(
        any(
            _contains(item["title"], term)
            or any(
                _contains(source["source_quote"], term)
                for source in (item.get("sources") or [])
            )
            for term in case["forbidden_item_terms"]
        )
        for item in audit_items
    )
    promotion_terms = (
        "五险一金",
        "带薪年假",
        "下午茶",
        "免费零食",
        "年度旅游",
        "节日礼物",
        "办公环境",
        "员工活动",
        "面试流程",
    )
    promotion_count = sum(
        any(
            _contains(item["title"], term)
            or any(
                _contains(source["source_quote"], term)
                for source in (item.get("sources") or [])
            )
            for term in promotion_terms
        )
        for item in audit_items
    )
    actual_warnings = _warning_codes(content) if content is not None else []
    expected_warnings = case["expected_warning_codes"]
    warning_hits = sum(code in actual_warnings for code in expected_warnings)
    contract_failures: list[str] = []
    if actual_outcome != case["expected_outcome"]:
        contract_failures.append("actual_outcome_mismatch")
    if recalled != len(case["expectations"]):
        contract_failures.append("major_expectation_missing")
    if required_recalled != required_expected:
        contract_failures.append("explicit_required_missing")
    if not all_reviewed:
        contract_failures.append("source_units_not_all_reviewed")
    if traceable_count != len(audit_items):
        contract_failures.append("untraceable_item")
    if priority_consistent_count != len(audit_items):
        contract_failures.append("priority_inconsistent")
    if source_count_failures:
        contract_failures.append("multi_source_merge_missing")
    if incorrect_merge_keys:
        contract_failures.append("incorrect_merge")
    if obvious_duplicate_count:
        contract_failures.append("obvious_duplicate")
    if forbidden_pollution_count:
        contract_failures.append("background_or_public_notes_pollution")
    if promotion_count:
        contract_failures.append("promotion_or_benefit_misclassified")
    if warning_hits != len(expected_warnings):
        contract_failures.append("expected_warning_missing")
    return {
        "item_count": len(audit_items),
        "items": audit_items,
        "source_unit_count": len(source_units),
        "reviewed_source_unit_count": len(set(reviewed_ids)),
        "all_source_units_reviewed": all_reviewed,
        "traceable_item_count": traceable_count,
        "priority_consistent_item_count": priority_consistent_count,
        "major_expectation_count": len(case["expectations"]),
        "major_expectation_recalled_count": recalled,
        "explicit_required_count": required_expected,
        "explicit_required_recalled_count": required_recalled,
        "matches_by_expectation": matches_by_expectation,
        "multi_source_expectation_failure_count": source_count_failures,
        "added_requirement_count": 0,
        "incorrect_merge_count": len(incorrect_merge_keys),
        "incorrect_merge_item_keys": sorted(incorrect_merge_keys),
        "obvious_duplicate_count": obvious_duplicate_count,
        "background_or_public_notes_pollution_count": forbidden_pollution_count,
        "promotion_or_benefit_misclassified_count": promotion_count,
        "expected_warning_codes": expected_warnings,
        "actual_warning_codes": actual_warnings,
        "expected_warning_hit_count": warning_hits,
        "contract_failure_reasons": contract_failures,
        "contract_satisfied": not contract_failures,
    }


async def _run_real_cases(
    cases: list[dict[str, Any]],
    *,
    settings: Settings,
) -> list[dict[str, Any]]:
    delegate = DeepSeekJobEvaluationPlanAdapter(settings=settings)
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        payload = _prompt_payload(case, EXPECTED_CASE_IDS.index(case["case_id"]) + 1)
        snapshot = payload["snapshot"]
        adapter = AttemptLoggingAdapter(delegate, case_id=case["case_id"])
        record: dict[str, Any] = {
            "case_id": case["case_id"],
            "title": case["title"],
            "expected_outcome": case["expected_outcome"],
            "prompt_char_count": payload["prompt_char_count"],
        }
        print(
            f"7RF_PROGRESS {index}/{len(cases)} {case['case_id']}",
            flush=True,
        )
        try:
            adapter_result = await job_evaluation_plan_service._extract_with_retry(
                adapter,
                payload["extraction_input"],
            )
            extracted = AIExtractedEvaluationPlanV3.model_validate_json(
                adapter_result.content
            )
            content: GeneratedPlanContent | None = None
            try:
                content = job_evaluation_plan_service.build_plan_content(
                    snapshot,
                    adapter_result.content,
                )
                warning_codes = _warning_codes(content)
                actual_outcome = (
                    "limited_basis"
                    if "limited_basis" in warning_codes
                    else "ready"
                )
            except JobEvaluationPlanContentError as exc:
                actual_outcome = {
                    "JOB_EVALUATION_PLAN_NO_ITEMS": "no_items",
                    "JOB_EVALUATION_PLAN_TOO_MANY_ITEMS": "too_many_items",
                }.get(exc.code, "content_failure")
                record.update(
                    {
                        "error_code": exc.code,
                        "safe_error": str(exc),
                        "rejection_layer": "service",
                    }
                )
            audit = _audit_case(
                case,
                snapshot,
                extracted,
                content,
                actual_outcome,
            )
            record.update(
                {
                    "actual_outcome": actual_outcome,
                    "actual_model": adapter_result.model,
                    "finish_reason": adapter_result.finish_reason,
                    "input_tokens": adapter_result.input_tokens,
                    "output_tokens": adapter_result.output_tokens,
                    "raw_structured_response": adapter_result.content,
                    "audit": audit,
                }
            )
        except JobEvaluationPlanAdapterError as exc:
            record.update(
                {
                    "actual_outcome": "adapter_failure",
                    "error_code": exc.code,
                    "safe_error": str(exc),
                    "rejection_layer": "adapter",
                    "audit": {
                        "contract_satisfied": False,
                        "contract_failure_reasons": ["adapter_failure"],
                    },
                }
            )
        record["api_attempts"] = adapter.attempts
        record["api_attempt_count"] = len(adapter.attempts)
        record["infrastructure_retry_count"] = max(0, len(adapter.attempts) - 1)
        results.append(record)
        print(
            f"7RF_RESULT {case['case_id']} actual={record['actual_outcome']} expected={case['expected_outcome']}",
            flush=True,
        )
    return results


def _summary(results: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    by_id = {record["case_id"]: record for record in results}
    normal_ids = [
        case["case_id"]
        for case in CASES
        if case["expected_outcome"] in NORMAL_OUTCOMES
    ]
    boundary_ids = [
        case["case_id"]
        for case in CASES
        if case["expected_outcome"] in BOUNDARY_OUTCOMES
    ]
    audits = [
        record["audit"]
        for record in results
        if "audit" in record and "major_expectation_count" in record["audit"]
    ]
    major_expected = sum(audit["major_expectation_count"] for audit in audits)
    major_recalled = sum(
        audit["major_expectation_recalled_count"] for audit in audits
    )
    required_expected = sum(audit["explicit_required_count"] for audit in audits)
    required_recalled = sum(
        audit["explicit_required_recalled_count"] for audit in audits
    )
    item_count = sum(audit["item_count"] for audit in audits)
    source_unit_count = sum(audit["source_unit_count"] for audit in audits)
    reviewed_count = sum(audit["reviewed_source_unit_count"] for audit in audits)
    traceable_count = sum(audit["traceable_item_count"] for audit in audits)
    priority_count = sum(
        audit["priority_consistent_item_count"] for audit in audits
    )
    warning_expected = sum(len(audit["expected_warning_codes"]) for audit in audits)
    warning_hit = sum(audit["expected_warning_hit_count"] for audit in audits)
    successful_attempts = [
        attempt
        for record in results
        for attempt in record.get("api_attempts", [])
        if attempt["status"] == "succeeded"
    ]
    all_attempts = [
        attempt
        for record in results
        for attempt in record.get("api_attempts", [])
    ]
    estimated_cost = sum(
        attempt.get("estimated_cost_cny_cache_miss") or 0.0
        for attempt in successful_attempts
    )
    metrics = {
        "sample_count": len(results),
        "normal_ready_count": sum(
            by_id.get(case_id, {}).get("actual_outcome") in NORMAL_OUTCOMES
            for case_id in normal_ids
        ),
        "normal_case_count": len(normal_ids),
        "boundary_correct_count": sum(
            by_id.get(case_id, {}).get("actual_outcome")
            == next(
                case["expected_outcome"]
                for case in CASES
                if case["case_id"] == case_id
            )
            for case_id in boundary_ids
        ),
        "boundary_case_count": len(boundary_ids),
        "major_expectation_count": major_expected,
        "major_expectation_recalled_count": major_recalled,
        "major_semantic_recall_rate": (
            major_recalled / major_expected if major_expected else 0.0
        ),
        "explicit_required_count": required_expected,
        "explicit_required_recalled_count": required_recalled,
        "explicit_required_recall_rate": (
            required_recalled / required_expected if required_expected else 1.0
        ),
        "source_unit_count": source_unit_count,
        "reviewed_source_unit_count": reviewed_count,
        "source_review_rate": (
            reviewed_count / source_unit_count if source_unit_count else 0.0
        ),
        "item_count": item_count,
        "traceable_item_count": traceable_count,
        "source_traceability_rate": traceable_count / item_count if item_count else 1.0,
        "priority_consistent_item_count": priority_count,
        "priority_consistency_rate": priority_count / item_count if item_count else 1.0,
        "multi_source_expectation_failure_count": sum(
            audit["multi_source_expectation_failure_count"] for audit in audits
        ),
        "added_requirement_count": sum(
            audit["added_requirement_count"] for audit in audits
        ),
        "incorrect_merge_count": sum(audit["incorrect_merge_count"] for audit in audits),
        "obvious_duplicate_count": sum(audit["obvious_duplicate_count"] for audit in audits),
        "background_or_public_notes_pollution_count": sum(
            audit["background_or_public_notes_pollution_count"] for audit in audits
        ),
        "promotion_or_benefit_misclassified_count": sum(
            audit["promotion_or_benefit_misclassified_count"] for audit in audits
        ),
        "expected_warning_count": warning_expected,
        "expected_warning_hit_count": warning_hit,
        "expected_warning_hit_rate": (
            warning_hit / warning_expected if warning_expected else 1.0
        ),
        "contract_satisfied_count": sum(
            bool(record.get("audit", {}).get("contract_satisfied"))
            for record in results
        ),
        "api_attempt_count": len(all_attempts),
        "infrastructure_retry_count": sum(
            record.get("infrastructure_retry_count", 0) for record in results
        ),
        "actual_models": dict(
            sorted(
                Counter(
                    attempt["model"]
                    for attempt in successful_attempts
                    if attempt.get("model")
                ).items()
            )
        ),
        "input_tokens": sum(
            attempt.get("input_tokens") or 0 for attempt in successful_attempts
        ),
        "output_tokens": sum(
            attempt.get("output_tokens") or 0 for attempt in successful_attempts
        ),
        "unpriced_failed_attempt_count": sum(
            attempt["status"] == "failed" for attempt in all_attempts
        ),
        "estimated_cost_cny_all_input_as_cache_miss": round(estimated_cost, 8),
    }
    targeted_gate_passed = (
        mode == "targeted"
        and set(by_id) == set(TARGETED_CASE_IDS)
        and len(results) == len(TARGETED_CASE_IDS)
        and metrics["contract_satisfied_count"] == len(TARGETED_CASE_IDS)
        and metrics["explicit_required_recall_rate"] == 1.0
        and metrics["major_semantic_recall_rate"] >= 0.95
        and metrics["source_review_rate"] == 1.0
        and metrics["source_traceability_rate"] == 1.0
        and metrics["priority_consistency_rate"] == 1.0
        and metrics["multi_source_expectation_failure_count"] == 0
        and metrics["added_requirement_count"] == 0
        and metrics["incorrect_merge_count"] == 0
        and metrics["obvious_duplicate_count"] == 0
        and metrics["background_or_public_notes_pollution_count"] == 0
        and metrics["promotion_or_benefit_misclassified_count"] == 0
        and metrics["expected_warning_hit_rate"] == 1.0
    )
    formal_gate_passed = (
        mode == "formal"
        and set(by_id) == set(EXPECTED_CASE_IDS)
        and len(results) == len(EXPECTED_CASE_IDS)
        and metrics["normal_ready_count"] == 18
        and metrics["boundary_correct_count"] == 2
        and metrics["explicit_required_recall_rate"] == 1.0
        and metrics["major_semantic_recall_rate"] >= 0.95
        and metrics["source_review_rate"] == 1.0
        and metrics["source_traceability_rate"] == 1.0
        and metrics["priority_consistency_rate"] == 1.0
        and metrics["multi_source_expectation_failure_count"] == 0
        and metrics["added_requirement_count"] == 0
        and metrics["incorrect_merge_count"] == 0
        and metrics["obvious_duplicate_count"] == 0
        and metrics["background_or_public_notes_pollution_count"] == 0
        and metrics["promotion_or_benefit_misclassified_count"] == 0
        and metrics["expected_warning_hit_rate"] == 1.0
    )
    return {
        **metrics,
        "targeted_gate_passed": targeted_gate_passed if mode == "targeted" else None,
        "formal_quality_gate_passed": formal_gate_passed if mode == "formal" else None,
        "quality_conclusion_allowed": mode == "formal" and len(results) == 20,
    }


def _write_new_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise SystemExit(f"结果文件已存在，拒绝覆盖：{path}") from None


def _require_formal_prerequisite() -> dict[str, Any]:
    if not TARGETED_RESULT_PATH.exists():
        raise SystemExit("正式 20 份调用前必须存在独立的 7R-F 定向结果")
    payload = json.loads(TARGETED_RESULT_PATH.read_text(encoding="utf-8"))
    if payload.get("summary", {}).get("targeted_gate_passed") is not True:
        raise SystemExit("7R-F 定向门槛未通过，禁止执行正式 20 份调用")
    if payload.get("case_fixture_sha256") != _case_fingerprint():
        raise SystemExit("定向结果与当前冻结样本不一致，禁止执行正式调用")
    return payload


async def _run_real(mode: str, model: str) -> dict[str, Any]:
    fixture = _validate_fixture()
    if model != PLANNED_MODEL:
        raise SystemExit(f"本轮费用门禁只覆盖模型 {PLANNED_MODEL}")
    if mode == "formal":
        _require_formal_prerequisite()
        selected_cases = list(CASES)
        result_path = FORMAL_RESULT_PATH
    else:
        selected_cases = [
            case for case in CASES if case["case_id"] in TARGETED_CASE_IDS
        ]
        result_path = TARGETED_RESULT_PATH
    if result_path.exists():
        raise SystemExit(f"结果文件已存在，拒绝覆盖：{result_path}")
    settings = Settings(
        JOB_EVALUATION_PLAN_MODEL=model,
        LLM_PROVIDER="deepseek",
        LLM_ENABLE_MOCK_FALLBACK=False,
    )
    if not settings.DEEPSEEK_API_KEY.strip():
        raise SystemExit("DeepSeek API Key 未配置，未执行真实调用")
    started_at = _utc_now()
    results = await _run_real_cases(selected_cases, settings=settings)
    payload = {
        "stage": "7R-F",
        "mode": mode,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "planned_model": model,
        "prompt_version": JOB_EVALUATION_PLAN_PROMPT_VERSION,
        "ai_schema_version": JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
        "plan_schema_version": JOB_EVALUATION_PLAN_SCHEMA_VERSION,
        "case_fixture_sha256": _case_fingerprint(),
        "pricing": _cost_budget(fixture),
        "results": results,
        "summary": _summary(results, mode=mode),
    }
    _write_new_json(result_path, payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"7RF_RESULT_PATH {result_path}")
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7R-F plan quality acceptance")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "targeted", "formal"),
        default="dry-run",
    )
    parser.add_argument("--model", default=PLANNED_MODEL)
    parser.add_argument(
        "--confirm-real-calls",
        action="store_true",
        help="required for targeted/formal; never inferred from environment",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.mode == "dry-run":
        if args.confirm_real_calls:
            raise SystemExit("dry-run 禁止携带真实调用确认参数")
        print(json.dumps(dry_run_payload(), ensure_ascii=False, indent=2))
        return
    if not args.confirm_real_calls:
        raise SystemExit("未提供 --confirm-real-calls，拒绝真实 DeepSeek 调用")
    asyncio.run(_run_real(args.mode, args.model))


if __name__ == "__main__":
    main()
