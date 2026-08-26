from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE7_RESULTS_DIR = PROJECT_ROOT / "docs" / "stages" / "stage7"

CURRENT_H1_PLAN_TARGETED_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4h-plan-quality-targeted-results.json"
)
CURRENT_H1_PLAN_TARGETED_RESULT_SHA256 = (
    "ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f"
)
CURRENT_HR1_PLAN_TARGETED_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json"
)
CURRENT_HR1_PLAN_TARGETED_RESULT_SHA256 = (
    "f1de3930c16e628617d4213ad0f85bf3a25fa0272945e5806e00c69a5d0df4d4"
)
PLAN_TARGETED_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-26-stage7-7r4hr2-plan-quality-targeted-revalidation-results.json"
)
PLAN_FORMAL_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4h-plan-quality-formal-results.json"
)
REPORT_TARGETED_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4i-report-quality-targeted-results.json"
)
REPORT_FORMAL_RESULT_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4i-report-quality-formal-results.json"
)
REPORT_FORMAL_MARKDOWN_PATH = (
    STAGE7_RESULTS_DIR
    / "2026-08-25-stage7-7r4i-report-quality-formal-results.md"
)

HISTORICAL_RESULT_PATHS = (
    CURRENT_H1_PLAN_TARGETED_RESULT_PATH,
    CURRENT_HR1_PLAN_TARGETED_RESULT_PATH,
    STAGE7_RESULTS_DIR / "2026-08-22-stage7-7rf-plan-quality-targeted-results.json",
    STAGE7_RESULTS_DIR / "2026-08-21-stage7-step9-jd-decomposition-debug-results.json",
    STAGE7_RESULTS_DIR
    / "2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json",
    STAGE7_RESULTS_DIR
    / "2026-08-21-stage7-step9-full-chain-diagnostic-results.json",
    STAGE7_RESULTS_DIR
    / "2026-08-21-stage7-step9-full-chain-diagnostic-results.md",
    STAGE7_RESULTS_DIR / "2026-08-20-stage7-quality-acceptance-results.json",
)

FROZEN_CASE_SHA256 = (
    "23651a92bb68602f096cf30519d5c11cd2ce6e724950f158587ba201e41fdfe0"
)
FORMAL_CASE_IDS = tuple(f"J5-{index:02d}" for index in range(1, 21))
TARGETED_CASE_IDS = (
    "J5-03",
    "J5-07",
    "J5-14",
    "J5-17",
    "J5-19",
    "J5-20",
)
EXPECTED_V4_OUTCOMES = {
    **{case_id: "pending_confirmation" for case_id in FORMAL_CASE_IDS[:18]},
    "J5-19": "no_facts",
    "J5-20": "pending_confirmation",
}
EXPECTED_V4_WARNING_CODES = {
    "J5-09": ("limited_basis",),
    "J5-10": ("limited_basis",),
    "J5-13": ("non_evaluation_content",),
    "J5-17": ("conflicting_requirements",),
    "J5-20": ("overly_broad_jd",),
}

PLANNED_MODEL = "deepseek-v4-flash"
MODEL_TEMPERATURE = 0.1
MAX_OUTPUT_TOKENS_PER_BUSINESS_CALL = 16_000
MAX_INFRASTRUCTURE_RETRIES_PER_BUSINESS_CALL = 1
TARGETED_MAXIMUM_BUSINESS_CALLS = 24
TARGETED_MAXIMUM_API_ATTEMPTS = 48
FORMAL_MAXIMUM_BUSINESS_CALLS = 80
FORMAL_MAXIMUM_API_ATTEMPTS = 160
OFFICIAL_PRICING_SOURCE_URL = (
    "https://api-docs.deepseek.com/quick_start/pricing/"
)
PLAN_PROMPT_ROLES = (
    "fact_extraction",
    "coverage_review",
    "criterion_grouping",
)
PLAN_REPAIR_ROLE = "local_repair"
EXPECTED_PLAN_PROMPT_VERSIONS = {
    "fact_extraction": "job_requirement_fact_extraction_v3",
    "coverage_review": "job_requirement_coverage_review_v3",
    "local_repair": "job_requirement_local_repair_v2",
    "criterion_grouping": "job_evaluation_criterion_grouping_v2",
}
PLAN_QUALITY_ZERO_COUNT_FIELDS = (
    "added_requirement_count",
    "source_merge_failure_count",
    "incorrect_merge_count",
    "obvious_duplicate_count",
    "background_or_public_notes_pollution_count",
    "promotion_or_benefit_misclassified_count",
)


def serialized(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def historical_result_hashes() -> dict[str, str]:
    if not CURRENT_H1_PLAN_TARGETED_RESULT_PATH.exists():
        raise RuntimeError("当前 7R4-H1 真实结果文件缺失")
    current_h1_hash = sha256_file(CURRENT_H1_PLAN_TARGETED_RESULT_PATH)
    if current_h1_hash != CURRENT_H1_PLAN_TARGETED_RESULT_SHA256:
        raise RuntimeError("当前 7R4-H1 真实结果 SHA-256 已变化")
    if not CURRENT_HR1_PLAN_TARGETED_RESULT_PATH.exists():
        raise RuntimeError("当前 7R4-HR1 真实结果文件缺失")
    current_hr1_hash = sha256_file(CURRENT_HR1_PLAN_TARGETED_RESULT_PATH)
    if current_hr1_hash != CURRENT_HR1_PLAN_TARGETED_RESULT_SHA256:
        raise RuntimeError("当前 7R4-HR1 真实结果 SHA-256 已变化")
    return {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in HISTORICAL_RESULT_PATHS
        if path.exists()
    }


def result_paths() -> dict[str, str]:
    return {
        "plan_targeted": str(PLAN_TARGETED_RESULT_PATH),
        "plan_formal": str(PLAN_FORMAL_RESULT_PATH),
        "report_targeted": str(REPORT_TARGETED_RESULT_PATH),
        "report_formal": str(REPORT_FORMAL_RESULT_PATH),
        "report_formal_markdown": str(REPORT_FORMAL_MARKDOWN_PATH),
    }


def validate_result_path_isolation() -> dict[str, Any]:
    new_paths = tuple(Path(value).resolve() for value in result_paths().values())
    historical_paths = tuple(path.resolve() for path in HISTORICAL_RESULT_PATHS)
    if len(new_paths) != len(set(new_paths)):
        raise RuntimeError("4.0 质量结果路径存在重复")
    if set(new_paths) & set(historical_paths):
        raise RuntimeError("4.0 质量结果路径指向了历史结果")
    if any(path.parent != STAGE7_RESULTS_DIR.resolve() for path in new_paths):
        raise RuntimeError("4.0 质量结果必须写入独立的阶段 7 结果目录")
    if "7r4h" not in PLAN_TARGETED_RESULT_PATH.name.lower():
        raise RuntimeError("4.0 定向计划结果缺少独立 7R4-H 命名")
    if "7r4hr2" not in PLAN_TARGETED_RESULT_PATH.name.lower():
        raise RuntimeError("4.0 定向复验结果缺少独立 7R4-HR2 命名")
    if "7r4i" not in REPORT_FORMAL_RESULT_PATH.name.lower():
        raise RuntimeError("4.0 报告结果缺少独立 7R4-I 命名")
    return {
        "new_paths": result_paths(),
        "existing_new_paths": [str(path) for path in new_paths if path.exists()],
        "historical_paths": [str(path) for path in historical_paths],
        "overlap_count": 0,
    }


def validate_frozen_plan_fixture(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_ids = tuple(case["case_id"] for case in cases)
    if case_ids != FORMAL_CASE_IDS:
        raise RuntimeError("4.0 正式计划样本必须严格固定为 J5-01—J5-20")
    digest = hashlib.sha256(serialized(cases).encode("utf-8")).hexdigest()
    if digest != FROZEN_CASE_SHA256:
        raise RuntimeError("冻结 JD 文本、人工标签或顺序已经漂移")
    expectation_count = sum(len(case["expectations"]) for case in cases)
    explicit_required_count = sum(
        bool(expectation["explicit_required"])
        for case in cases
        for expectation in case["expectations"]
    )
    if expectation_count != 245 or explicit_required_count != 97:
        raise RuntimeError("245 条人工 facts 或 97 条明确必测分母已经漂移")
    selected = [case for case in cases if case["case_id"] in TARGETED_CASE_IDS]
    targeted_expectations = sum(len(case["expectations"]) for case in selected)
    targeted_required = sum(
        bool(expectation["explicit_required"])
        for case in selected
        for expectation in case["expectations"]
    )
    if targeted_expectations != 80 or targeted_required != 23:
        raise RuntimeError("4.0 定向人工 facts 分母已经漂移")
    return {
        "formal_case_ids": list(case_ids),
        "targeted_case_ids": list(TARGETED_CASE_IDS),
        "frozen_case_sha256": digest,
        "manual_fact_denominator": expectation_count,
        "explicit_required_denominator": explicit_required_count,
        "targeted_manual_fact_denominator": targeted_expectations,
        "targeted_explicit_required_denominator": targeted_required,
        "expected_outcomes": EXPECTED_V4_OUTCOMES,
        "expected_warning_codes": {
            key: list(value) for key, value in EXPECTED_V4_WARNING_CODES.items()
        },
    }


def plan_call_budget() -> dict[str, Any]:
    def row(
        *,
        case_count: int,
        normal_case_count: int,
        safety_business_calls: int,
        safety_api_attempts: int,
    ) -> dict[str, int]:
        no_facts_case_count = case_count - normal_case_count
        baseline = normal_case_count * 3 + no_facts_case_count
        maximum = normal_case_count * 4 + no_facts_case_count
        return {
            "sample_count": case_count,
            "normal_plan_count": normal_case_count,
            "no_facts_short_circuit_count": no_facts_case_count,
            "baseline_business_calls": baseline,
            "maximum_business_calls_with_local_repair": maximum,
            "safety_hard_maximum_business_calls": safety_business_calls,
            "maximum_api_attempts_with_infrastructure_retries": safety_api_attempts,
            "maximum_output_tokens_without_infrastructure_retries": (
                maximum * MAX_OUTPUT_TOKENS_PER_BUSINESS_CALL
            ),
            "maximum_output_tokens_with_infrastructure_retries": (
                safety_api_attempts * MAX_OUTPUT_TOKENS_PER_BUSINESS_CALL
            ),
        }

    return {
        "targeted": row(
            case_count=len(TARGETED_CASE_IDS),
            normal_case_count=5,
            safety_business_calls=TARGETED_MAXIMUM_BUSINESS_CALLS,
            safety_api_attempts=TARGETED_MAXIMUM_API_ATTEMPTS,
        ),
        "formal": row(
            case_count=len(FORMAL_CASE_IDS),
            normal_case_count=19,
            safety_business_calls=FORMAL_MAXIMUM_BUSINESS_CALLS,
            safety_api_attempts=FORMAL_MAXIMUM_API_ATTEMPTS,
        ),
        "business_call_definition": "一个 Prompt 角色的一次逻辑调用",
        "content_repair_definition": "coverage review 后最多一次 local_repair 业务调用",
        "infrastructure_retry_definition": (
            "每个业务调用遇到网络、超时、限流或 5xx 时最多额外尝试一次"
        ),
        "maximum_infrastructure_retries_per_business_call": (
            MAX_INFRASTRUCTURE_RETRIES_PER_BUSINESS_CALL
        ),
    }


def model_execution_contract() -> dict[str, Any]:
    return {
        "model": PLANNED_MODEL,
        "temperature": MODEL_TEMPERATURE,
        "response_format": "json_object",
        "thinking": "disabled",
        "sdk_automatic_retries": 0,
        "max_output_tokens_per_business_call": MAX_OUTPUT_TOKENS_PER_BUSINESS_CALL,
    }


def model_and_cost_inputs() -> dict[str, Any]:
    budget = plan_call_budget()
    return {
        "candidate_model_from_current_config": PLANNED_MODEL,
        "model_requires_separate_confirmation_before_7R4_H": True,
        **{
            key: value
            for key, value in model_execution_contract().items()
            if key != "model"
        },
        "cost_estimate_inputs": {
            "currency": "CNY",
            "official_price_check_required_before_7R4_H": True,
            "input_cache_hit_price_per_million_tokens": None,
            "input_cache_miss_price_per_million_tokens": None,
            "output_price_per_million_tokens": None,
            "targeted_maximum_business_calls": budget["targeted"][
                "maximum_business_calls_with_local_repair"
            ],
            "formal_maximum_business_calls": budget["formal"][
                "maximum_business_calls_with_local_repair"
            ],
            "targeted_maximum_api_attempts": budget["targeted"][
                "maximum_api_attempts_with_infrastructure_retries"
            ],
            "formal_maximum_api_attempts": budget["formal"][
                "maximum_api_attempts_with_infrastructure_retries"
            ],
            "token_usage_must_be_recorded_per_attempt": True,
            "cache_hit_miss_split_must_be_recorded_when_provider_returns_it": True,
            "estimated_cost_is_not_actual_invoice": True,
        },
    }


def validate_official_pricing_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    checked_at = payload.get("checked_at")
    if not isinstance(checked_at, str):
        raise ValueError("官方价格检查时间不能为空")
    try:
        parsed_at = datetime.fromisoformat(checked_at)
    except ValueError:
        raise ValueError("官方价格检查时间必须是 ISO-8601") from None
    if parsed_at.tzinfo is None:
        raise ValueError("官方价格检查时间必须包含时区")
    if payload.get("source_url") != OFFICIAL_PRICING_SOURCE_URL:
        raise ValueError("官方价格来源必须是固定 DeepSeek 价格页")
    peak_schedule = payload.get("peak_schedule")
    if not isinstance(peak_schedule, str) or not peak_schedule.strip():
        raise ValueError("官方峰谷适用时段不能为空")
    selected_tier = payload.get("selected_tier")
    if selected_tier not in {"off_peak", "peak"}:
        raise ValueError("本次计价时段必须是 off_peak 或 peak")
    raw_tables = payload.get("usd_per_million_tokens")
    if not isinstance(raw_tables, dict):
        raise ValueError("缺少官方美元单价表")
    normalized_tables: dict[str, dict[str, float]] = {}
    for tier in ("off_peak", "peak"):
        raw_row = raw_tables.get(tier)
        if not isinstance(raw_row, dict):
            raise ValueError(f"缺少 {tier} 官方美元单价")
        row: dict[str, float] = {}
        for key in ("cache_hit_input", "cache_miss_input", "output"):
            try:
                value = Decimal(str(raw_row.get(key)))
            except (InvalidOperation, ValueError):
                raise ValueError(f"{tier}.{key} 不是合法单价") from None
            if not value.is_finite() or value < 0:
                raise ValueError(f"{tier}.{key} 不能为负数或无穷值")
            row[key] = float(value)
        normalized_tables[tier] = row
    return {
        "checked_at": parsed_at.isoformat(),
        "source_url": OFFICIAL_PRICING_SOURCE_URL,
        "selected_tier": selected_tier,
        "timezone": "Asia/Shanghai",
        "peak_schedule": peak_schedule.strip(),
        "usd_per_million_tokens": normalized_tables,
        "monetary_cap_usd": None,
    }


def estimate_attempt_cost_usd(
    *,
    pricing_snapshot: dict[str, Any],
    input_tokens: int | None,
    cache_hit_input_tokens: int | None,
    cache_miss_input_tokens: int | None,
    output_tokens: int | None,
) -> dict[str, Any]:
    pricing = validate_official_pricing_snapshot(pricing_snapshot)
    token_values = (
        input_tokens,
        cache_hit_input_tokens,
        cache_miss_input_tokens,
        output_tokens,
    )
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in token_values
    ):
        return {
            "complete": False,
            "estimated_cost_usd": None,
            "reason": "provider_usage_incomplete",
        }
    assert input_tokens is not None
    assert cache_hit_input_tokens is not None
    assert cache_miss_input_tokens is not None
    assert output_tokens is not None
    if cache_hit_input_tokens + cache_miss_input_tokens != input_tokens:
        return {
            "complete": False,
            "estimated_cost_usd": None,
            "reason": "provider_cache_token_split_mismatch",
        }
    rates = pricing["usd_per_million_tokens"][pricing["selected_tier"]]
    hit_cost = (
        Decimal(cache_hit_input_tokens)
        * Decimal(str(rates["cache_hit_input"]))
        / Decimal(1_000_000)
    )
    miss_cost = (
        Decimal(cache_miss_input_tokens)
        * Decimal(str(rates["cache_miss_input"]))
        / Decimal(1_000_000)
    )
    output_cost = (
        Decimal(output_tokens)
        * Decimal(str(rates["output"]))
        / Decimal(1_000_000)
    )
    total = hit_cost + miss_cost + output_cost
    return {
        "complete": True,
        "cache_hit_input_cost_usd": float(hit_cost),
        "cache_miss_input_cost_usd": float(miss_cost),
        "output_cost_usd": float(output_cost),
        "estimated_cost_usd": float(total),
        "reason": None,
    }


def write_new_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    allowed = {Path(value).resolve() for value in result_paths().values()}
    if resolved not in allowed:
        raise RuntimeError("拒绝向未登记的 4.0 质量结果路径写入")
    if resolved.exists():
        raise RuntimeError("4.0 质量结果文件已经存在，拒绝覆盖")
    resolved.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_plan_attempt_audit(payload: dict[str, Any]) -> dict[str, Any]:
    pricing = validate_official_pricing_snapshot(
        payload.get("official_pricing_snapshot") or {}
    )
    selected_case_ids = tuple(payload.get("selected_case_ids") or ())
    if selected_case_ids == TARGETED_CASE_IDS:
        budget = plan_call_budget()["targeted"]
    elif selected_case_ids == FORMAL_CASE_IDS:
        budget = plan_call_budget()["formal"]
    else:
        raise RuntimeError("计划质量逐 attempt 审计的样本集合或顺序不合法")
    cases = payload.get("cases")
    if not isinstance(cases, list) or tuple(
        case.get("case_id") if isinstance(case, dict) else None for case in cases
    ) != selected_case_ids:
        raise RuntimeError("逐样本质量明细必须完整且按冻结顺序排列")
    case_by_id = {case["case_id"]: case for case in cases}
    expected_roles_by_case: dict[str, list[str]] = {}
    generation_audit_by_case: dict[str, dict[str, Any]] = {}
    for case_id in selected_case_ids:
        case = case_by_id[case_id]
        actual_outcome = case.get("actual_outcome")
        if actual_outcome != EXPECTED_V4_OUTCOMES[case_id]:
            raise RuntimeError("逐样本 actual_outcome 与冻结预期不一致")
        generation_audit = case.get("generation_audit")
        if not isinstance(generation_audit, dict):
            raise RuntimeError("逐样本缺少 generation audit")
        calls = generation_audit.get("calls")
        if not isinstance(calls, list) or not calls:
            raise RuntimeError("逐样本 generation audit 缺少业务调用明细")
        roles = [call.get("role") if isinstance(call, dict) else None for call in calls]
        if actual_outcome == "no_facts":
            allowed_role_orders = [["fact_extraction"]]
        else:
            allowed_role_orders = [
                ["fact_extraction", "coverage_review", "criterion_grouping"],
                [
                    "fact_extraction",
                    "coverage_review",
                    "local_repair",
                    "criterion_grouping",
                ],
            ]
        if roles not in allowed_role_orders:
            raise RuntimeError("逐样本业务调用少跑、乱序或 repair 位置不合法")
        if generation_audit.get("business_call_count") != len(calls):
            raise RuntimeError("逐样本 generation audit 业务调用汇总不一致")
        repair_count = sum(role == PLAN_REPAIR_ROLE for role in roles)
        if generation_audit.get("content_repair_count") != repair_count:
            raise RuntimeError("逐样本 generation audit 局部修复汇总不一致")
        if any(
            call.get("prompt_version") != EXPECTED_PLAN_PROMPT_VERSIONS[call.get("role")]
            for call in calls
        ):
            raise RuntimeError("逐样本 generation audit Prompt 版本不一致")
        if actual_outcome == "no_facts":
            extraction_call = calls[0]
            if (
                extraction_call.get("result") != "failed"
                or extraction_call.get("error_code") != "JOB_EVALUATION_PLAN_NO_FACTS"
            ):
                raise RuntimeError("no_facts 必须在事实提取后以稳定错误合法停止")
        elif any(call.get("result") != "succeeded" for call in calls):
            raise RuntimeError("门禁可通过的正常样本业务调用必须全部成功")
        expected_roles_by_case[case_id] = roles
        generation_audit_by_case[case_id] = generation_audit

    attempts = payload.get("attempt_audit")
    if not isinstance(attempts, list) or not attempts:
        raise RuntimeError("4.0 定向结果缺少逐 attempt 审计")
    if len(attempts) > budget["maximum_api_attempts_with_infrastructure_retries"]:
        raise RuntimeError("计划质量实际 API 尝试数超过安全硬上限")
    seen_case_ids: set[str] = set()
    case_attempt_counts: Counter[str] = Counter()
    business_roles_by_case: dict[str, list[str]] = {
        case_id: [] for case_id in selected_case_ids
    }
    retry_counts_by_case: dict[str, list[int]] = {
        case_id: [] for case_id in selected_case_ids
    }
    final_attempts_by_case: dict[str, list[dict[str, Any]]] = {
        case_id: [] for case_id in selected_case_ids
    }
    observed_case_order: list[str] = []
    completed_cases: set[str] = set()
    active_case_id: str | None = None
    previous_attempt: dict[str, Any] | None = None
    derived_business_calls = 0
    for expected_number, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            raise RuntimeError("逐 attempt 审计项不是 JSON 对象")
        case_id = attempt.get("case_id")
        role = attempt.get("role")
        seen_case_ids.add(case_id)
        if case_id not in selected_case_ids:
            raise RuntimeError("逐 attempt 审计引用了非本轮样本")
        if case_id != active_case_id:
            if active_case_id is not None:
                completed_cases.add(active_case_id)
            if case_id in completed_cases:
                raise RuntimeError("逐 attempt 审计不能返回已经结束的样本")
            active_case_id = case_id
            observed_case_order.append(case_id)
        if role not in {*PLAN_PROMPT_ROLES, PLAN_REPAIR_ROLE}:
            raise RuntimeError("逐 attempt 审计角色不合法")
        if attempt.get("attempt_number") != expected_number:
            raise RuntimeError("逐 attempt 编号不连续")
        case_attempt_counts[case_id] += 1
        if attempt.get("case_attempt_number") != case_attempt_counts[case_id]:
            raise RuntimeError("逐样本 attempt 编号不连续")
        if attempt.get("requested_model") != PLANNED_MODEL:
            raise RuntimeError("逐 attempt 请求模型与定向合同不一致")
        if attempt.get("thinking") != "disabled":
            raise RuntimeError("逐 attempt thinking 与定向合同不一致")
        if attempt.get("temperature") != MODEL_TEMPERATURE:
            raise RuntimeError("逐 attempt temperature 与定向合同不一致")
        if attempt.get("response_format") != "json_object":
            raise RuntimeError("逐 attempt JSON 模式与定向合同不一致")
        if attempt.get("max_output_tokens") != MAX_OUTPUT_TOKENS_PER_BUSINESS_CALL:
            raise RuntimeError("逐 attempt token 上限与定向合同不一致")
        if attempt.get("sdk_automatic_retries") != 0:
            raise RuntimeError("逐 attempt SDK 自动重试必须关闭")
        if attempt.get("prompt_version") != EXPECTED_PLAN_PROMPT_VERSIONS[role]:
            raise RuntimeError("逐 attempt Prompt 版本与角色不一致")
        if not isinstance(attempt.get("duration_ms"), (int, float)):
            raise RuntimeError("逐 attempt 缺少耗时")
        if attempt.get("result") not in {"succeeded", "failed"}:
            raise RuntimeError("逐 attempt 结果状态不合法")
        if not isinstance(attempt.get("is_infrastructure_retry"), bool):
            raise RuntimeError("逐 attempt 缺少基础设施重试标记")
        if not isinstance(attempt.get("retryable"), bool):
            raise RuntimeError("逐 attempt 缺少错误重试属性")
        expected_retry = bool(
            previous_attempt
            and previous_attempt.get("case_id") == case_id
            and previous_attempt.get("role") == role
            and previous_attempt.get("result") == "failed"
            and previous_attempt.get("retryable") is True
        )
        if expected_retry and previous_attempt.get("is_infrastructure_retry") is True:
            raise RuntimeError("同一业务调用最多只能有一次基础设施重试")
        if attempt["is_infrastructure_retry"] is not expected_retry:
            raise RuntimeError("基础设施重试标记不能从相邻失败 attempt 推导")
        if not expected_retry:
            derived_business_calls += 1
            business_roles_by_case[case_id].append(role)
            retry_counts_by_case[case_id].append(0)
            final_attempts_by_case[case_id].append(attempt)
        else:
            retry_counts_by_case[case_id][-1] += 1
            final_attempts_by_case[case_id][-1] = attempt
        if attempt.get("business_call_number") != derived_business_calls:
            raise RuntimeError("业务调用编号不能从逐 attempt 记录推导")
        if attempt.get("result") == "succeeded":
            if attempt.get("error_code") is not None or attempt.get("retryable"):
                raise RuntimeError("成功 attempt 不能携带错误或重试属性")
            if attempt.get("finish_reason") != "stop":
                raise RuntimeError("成功 attempt 必须正常 stop")
            if not isinstance(attempt.get("raw_response"), str):
                raise RuntimeError("成功 attempt 缺少原始响应")
        else:
            if not isinstance(attempt.get("error_code"), str):
                raise RuntimeError("失败 attempt 缺少稳定错误码")
            if attempt.get("finish_reason") is not None and not isinstance(
                attempt.get("raw_response"), str
            ):
                raise RuntimeError("已收到模型响应的失败 attempt 缺少原始证据")
        recalculated_cost = estimate_attempt_cost_usd(
            pricing_snapshot=pricing,
            input_tokens=attempt.get("input_tokens"),
            cache_hit_input_tokens=attempt.get("cache_hit_input_tokens"),
            cache_miss_input_tokens=attempt.get("cache_miss_input_tokens"),
            output_tokens=attempt.get("output_tokens"),
        )
        if attempt.get("cost_estimate") != recalculated_cost:
            raise RuntimeError("逐 attempt 费用不能从 token 与官方单价重算")
        if attempt.get("finish_reason") is not None and not recalculated_cost[
            "complete"
        ]:
            raise RuntimeError("已收到模型响应的 attempt 缺少完整计费 token")
        previous_attempt = attempt
    if seen_case_ids != set(selected_case_ids):
        raise RuntimeError("逐 attempt 审计没有覆盖全部定向样本")
    if tuple(observed_case_order) != selected_case_ids:
        raise RuntimeError("逐 attempt 审计没有按冻结样本顺序执行")
    business_calls = derived_business_calls
    infrastructure_retries = len(attempts) - business_calls
    content_repairs = sum(
        attempt["role"] == PLAN_REPAIR_ROLE
        and attempt["is_infrastructure_retry"] is False
        for attempt in attempts
    )
    for case_id in selected_case_ids:
        expected_roles = expected_roles_by_case[case_id]
        if business_roles_by_case[case_id] != expected_roles:
            raise RuntimeError("逐 attempt 角色顺序与逐样本 actual_outcome 不一致")
        if any(
            attempt.get("result") != "succeeded"
            for attempt in final_attempts_by_case[case_id]
        ):
            raise RuntimeError("内容错误不得通过重复业务调用碰运气")
        generation_audit = generation_audit_by_case[case_id]
        calls = generation_audit["calls"]
        retry_counts = retry_counts_by_case[case_id]
        if len(retry_counts) != len(calls) or any(
            call.get("infrastructure_retry_count") != retry_count
            for call, retry_count in zip(calls, retry_counts, strict=True)
        ):
            raise RuntimeError("逐 attempt 基础设施重试与 generation audit 不一致")
        if generation_audit.get("infrastructure_retry_count") != sum(retry_counts):
            raise RuntimeError("逐样本 generation audit 重试汇总不一致")
    if not (
        budget["baseline_business_calls"]
        <= business_calls
        <= budget["maximum_business_calls_with_local_repair"]
    ):
        raise RuntimeError("计划质量业务调用数不符合逐样本合法流程")
    audit_summary = payload.get("attempt_audit_summary")
    if not isinstance(audit_summary, dict):
        raise RuntimeError("4.0 定向结果缺少 attempt 汇总")
    expected_summary_counts = {
        "adapter_attempt_count": len(attempts),
        "business_call_count": business_calls,
        "infrastructure_retry_count": infrastructure_retries,
        "content_repair_count": content_repairs,
        "succeeded_attempt_count": sum(
            attempt["result"] == "succeeded" for attempt in attempts
        ),
        "failed_attempt_count": sum(
            attempt["result"] == "failed" for attempt in attempts
        ),
        "priced_attempt_count": sum(
            attempt["cost_estimate"]["complete"] for attempt in attempts
        ),
        "maximum_business_calls": budget["safety_hard_maximum_business_calls"],
        "maximum_api_attempts": budget["maximum_api_attempts_with_infrastructure_retries"],
    }
    expected_summary_counts["unpriced_attempt_count"] = (
        len(attempts) - expected_summary_counts["priced_attempt_count"]
    )
    for key, value in expected_summary_counts.items():
        if audit_summary.get(key) != value:
            raise RuntimeError(f"逐 attempt 汇总不一致：{key}")
    recalculated_total = sum(
        attempt["cost_estimate"]["estimated_cost_usd"] or 0.0
        for attempt in attempts
    )
    if abs(audit_summary.get("estimated_cost_usd", -1) - recalculated_total) > 1e-12:
        raise RuntimeError("逐 attempt 总费用不能重算")
    if audit_summary.get("monetary_cap_usd") is not None:
        raise RuntimeError("本次定向轮不设置金额硬上限")
    if audit_summary.get("stopped_reason") is not None:
        raise RuntimeError("调用上限触发后不能通过定向门禁")
    quality_summary = payload.get("summary")
    if not isinstance(quality_summary, dict):
        raise RuntimeError("4.0 定向结果缺少质量汇总")
    for key, value in {
        "business_call_count": business_calls,
        "content_repair_count": content_repairs,
        "infrastructure_retry_count": infrastructure_retries,
    }.items():
        if quality_summary.get(key) != value:
            raise RuntimeError(f"质量汇总与逐 attempt 明细不一致：{key}")
    return {
        "attempt_count": len(attempts),
        "business_call_count": business_calls,
        "infrastructure_retry_count": infrastructure_retries,
        "content_repair_count": content_repairs,
        "estimated_cost_usd": recalculated_total,
    }


def validate_targeted_gate_payload(
    payload: dict[str, Any],
    *,
    source_path: Path,
) -> dict[str, Any]:
    if source_path.resolve() != PLAN_TARGETED_RESULT_PATH.resolve():
        raise RuntimeError("正式模式只接受登记的新 4.0 定向结果路径")
    expected = {
        "stage": "7R4-HR2",
        "result_kind": "plan_quality_targeted_revalidation",
        "status": "formal",
        "plan_schema_version": "4.0",
        "frozen_case_sha256": FROZEN_CASE_SHA256,
        "model": PLANNED_MODEL,
        "prompt_versions": EXPECTED_PLAN_PROMPT_VERSIONS,
        "model_parameters": model_execution_contract(),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"4.0 定向结果 {key} 不匹配")
    if tuple(payload.get("selected_case_ids") or ()) != TARGETED_CASE_IDS:
        raise RuntimeError("4.0 定向结果样本集合或顺序不一致")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("4.0 定向结果缺少统计摘要")
    required_counts = {
        "sample_contract_denominator": 6,
        "sample_contract_passed_count": 6,
        "manual_fact_denominator": 80,
        "explicit_required_denominator": 23,
        "source_unit_denominator": 90,
        "normal_ready_denominator": 4,
        "normal_ready_count": 4,
        "boundary_denominator": 2,
        "boundary_correct_count": 2,
    }
    for key, value in required_counts.items():
        if summary.get(key) != value:
            raise RuntimeError(f"4.0 定向结果统计分母异常：{key}")
    if not plan_quality_gate_passed(summary, mode="targeted"):
        raise RuntimeError("4.0 定向结果未满足第 15 节完整质量门槛")
    if payload.get("targeted_gate_passed") is not True:
        raise RuntimeError("4.0 定向结果未明确通过完整门槛")
    if payload.get("quality_conclusion_allowed") is not True:
        raise RuntimeError("4.0 定向结果不允许作为正式门禁依据")
    attempt_audit = validate_plan_attempt_audit(payload)
    return {
        "source_path": str(source_path.resolve()),
        "targeted_gate_passed": True,
        "selected_case_ids": list(TARGETED_CASE_IDS),
        "denominators": required_counts,
        "attempt_audit": attempt_audit,
    }


def plan_quality_gate_passed(summary: dict[str, Any], *, mode: str) -> bool:
    if mode not in {"targeted", "formal"}:
        raise ValueError("计划质量门禁 mode 只能是 targeted 或 formal")
    expected = (
        {
            "sample_contract_denominator": 6,
            "manual_fact_denominator": 80,
            "explicit_required_denominator": 23,
            "source_unit_denominator": 90,
            "normal_ready_denominator": 4,
            "boundary_denominator": 2,
            "expected_warning_count": 2,
        }
        if mode == "targeted"
        else {
            "sample_contract_denominator": 20,
            "manual_fact_denominator": 245,
            "explicit_required_denominator": 97,
            "source_unit_denominator": 255,
            "normal_ready_denominator": 18,
            "boundary_denominator": 2,
            "expected_warning_count": 5,
        }
    )
    if any(summary.get(key) != value for key, value in expected.items()):
        return False
    if summary.get("sample_contract_passed_count") != expected[
        "sample_contract_denominator"
    ]:
        return False
    if summary.get("normal_ready_count") != expected["normal_ready_denominator"]:
        return False
    if summary.get("boundary_correct_count") != expected["boundary_denominator"]:
        return False
    ratio_contracts = (
        (
            "manual_fact_recalled_count",
            "manual_fact_denominator",
            "manual_fact_recall_rate",
            0.95,
        ),
        (
            "explicit_required_recalled_count",
            "explicit_required_denominator",
            "explicit_required_recall_rate",
            1.0,
        ),
        (
            "reviewed_source_unit_count",
            "source_unit_denominator",
            "source_review_rate",
            1.0,
        ),
        (
            "traceable_fact_count",
            "fact_count",
            "source_traceability_rate",
            1.0,
        ),
        (
            "priority_consistent_fact_count",
            "fact_count",
            "priority_consistency_rate",
            1.0,
        ),
        (
            "criterion_covered_fact_count",
            "fact_count",
            "criterion_coverage_rate",
            1.0,
        ),
        (
            "expected_warning_hit_count",
            "expected_warning_count",
            "expected_warning_hit_rate",
            1.0,
        ),
    )
    for numerator_key, denominator_key, rate_key, minimum in ratio_contracts:
        numerator = summary.get(numerator_key)
        denominator = summary.get(denominator_key)
        rate = summary.get(rate_key)
        if (
            not isinstance(numerator, int)
            or isinstance(numerator, bool)
            or not isinstance(denominator, int)
            or isinstance(denominator, bool)
            or denominator <= 0
            or numerator < 0
            or numerator > denominator
        ):
            return False
        calculated = numerator / denominator
        if rate != calculated or calculated < minimum:
            return False
    if summary.get("fact_count", 0) <= 0:
        return False
    return all(summary.get(key) == 0 for key in PLAN_QUALITY_ZERO_COUNT_FIELDS)


def load_and_validate_targeted_gate() -> dict[str, Any]:
    if not PLAN_TARGETED_RESULT_PATH.exists():
        raise RuntimeError("缺少新的 4.0 定向质量结果，正式模式已在调用前阻断")
    try:
        payload = json.loads(PLAN_TARGETED_RESULT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        raise RuntimeError("新的 4.0 定向质量结果不可读取") from None
    if not isinstance(payload, dict):
        raise RuntimeError("新的 4.0 定向质量结果不是 JSON 对象")
    return validate_targeted_gate_payload(
        payload,
        source_path=PLAN_TARGETED_RESULT_PATH,
    )


def report_label_denominators(screening_cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_ids = [case["case_id"] for case in screening_cases]
    if len(case_ids) != 20 or len(set(case_ids)) != 20:
        raise RuntimeError("报告质量必须保留 20 组唯一冻结样本")
    label_counts = Counter(case["manual_band"] for case in screening_cases)
    if label_counts != Counter({"high": 8, "partial": 6, "low": 6}):
        raise RuntimeError("报告质量 high/partial/low 人工标签分母已经漂移")
    return {
        "case_ids": case_ids,
        "case_count": 20,
        "manual_label_counts": dict(sorted(label_counts.items())),
        "runs_per_case": 3,
        "formal_business_call_budget": 60,
        "maximum_api_attempts_with_infrastructure_retries": 120,
        "failed_samples_remain_in_denominator": True,
    }
