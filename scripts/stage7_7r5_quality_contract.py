from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
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


STAGE7_RESULTS_DIR = PROJECT_ROOT / "docs" / "stages" / "stage7"
V5_RESULTS_DIR = STAGE7_RESULTS_DIR / "v5-quality-results"
RAW_RESULT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-quality-raw-results.json"
HUMAN_AUDIT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-human-audit.json"
FINAL_RESULT_PATH = V5_RESULTS_DIR / "2026-08-27-stage7-7r5i-quality-final-results.json"

FROZEN_FIXTURE_SHA256 = "2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643"
PLAN_SAMPLE_SHA256 = "c86ed29acc38206714c253a022d9b4ca2fe9aa32078aae599115bac40ea8823f"
PLAN_LABEL_SHA256 = "3f8a22656814b1ce9c4f8929e3b93de37e6e7a337c672752895920e022ac0cf6"
REPORT_SAMPLE_SHA256 = "ee7f4d5a5673a5a6a15c1ef0d469f67eee50e3b4e3172d8c23415605f84f0dd3"
REPORT_LABEL_SHA256 = "a088f763eb011d34131b5dd34f6c2fe2558649ea5f9e41499d101ec270009d75"
STABILITY_SELECTION_SHA256 = "7f2c5f390b0c7e30e5a644380decea0554bbb62cfc03eff193d13a8c1a117708"

HISTORICAL_RESULT_HASHES = {
    "2026-08-20-stage7-quality-acceptance-results.json": "75e31dce20c1fd8dcecdc29e35345cd75e726d4f02fecaf9c06bb39ed7d1f1ea",
    "2026-08-20-stage7-quality-acceptance.md": "056bffaccd5f18794ad9504461102e1067b019822dd0cc1b360d22f21de326e7",
    "2026-08-21-stage7-step9-full-chain-diagnostic-results.json": "9892f62a0035e303f67e7cb140c9225a4ce2be9bf9360f3d260e522c29b5de9f",
    "2026-08-21-stage7-step9-full-chain-diagnostic-results.md": "29af2b9fbcc5aac6cd98ed54dd8a2a6817a2db54ea15cf6a18bd14dce920631b",
    "2026-08-21-stage7-step9-jd-decomposition-debug-results.json": "f4c1019536aa5e4d13d55f86caba7b9b27f245a2e9c0a83ed942974a048de3c2",
    "2026-08-21-stage7-step9-jd-decomposition-results.json": "ab99a6e1742876fd95b8bd2a1987c783825738477c137726b710b6aedfce6e77",
    "2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json": "41b34c01bd5a19715f728a9bcb67ce0adfc8324cce953455b56d9651da5fcbe4",
    "2026-08-21-stage7-time-fact-revalidation-results.json": "193613f05bc8263ce630be9a7cbfdbd6cdca093c08be46c9f9d44d4b1a530b17",
    "2026-08-22-stage7-7rf-plan-quality-targeted-results.json": "567b56c674314e5c94bf6997f0da5a96fb53130e60724a24af29628ccab218f9",
    "2026-08-25-stage7-7r4h-plan-quality-formal-results.json": "b416809973ef0013a125736d8acafc024b610882608967f42c6ab10fc8a20b50",
    "2026-08-25-stage7-7r4h-plan-quality-targeted-results.json": "ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f",
    "2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json": "f1de3930c16e628617d4213ad0f85bf3a25fa0272945e5806e00c69a5d0df4d4",
    "2026-08-26-stage7-7r4hr2-plan-quality-targeted-revalidation-results.json": "4b7c44d4874f3ece189b50d4488d305a1161dbbcdf291277de45945844030ce9",
}

PLANNED_MODEL = "deepseek-v4-flash"
PLAN_PROMPT_VERSION = "job_evaluation_plan_lightweight_v2"
REPORT_PROMPT_VERSION = "screening_evaluation_lightweight_v1"
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def validate_historical_results() -> dict[str, str]:
    observed: dict[str, str] = {}
    for filename, expected_hash in HISTORICAL_RESULT_HASHES.items():
        path = STAGE7_RESULTS_DIR / filename
        if not path.exists():
            raise RuntimeError(f"历史质量证据缺失：{filename}")
        digest = sha256_file(path)
        if digest != expected_hash:
            raise RuntimeError(f"历史质量证据 SHA-256 已变化：{filename}")
        observed[filename] = digest
    return observed


def result_paths() -> dict[str, str]:
    return {
        "raw": str(RAW_RESULT_PATH),
        "human_audit": str(HUMAN_AUDIT_PATH),
        "final": str(FINAL_RESULT_PATH),
    }


def validate_result_path_isolation(*, require_empty: bool) -> dict[str, Any]:
    paths = tuple(Path(value).resolve() for value in result_paths().values())
    historical = tuple((STAGE7_RESULTS_DIR / name).resolve() for name in HISTORICAL_RESULT_HASHES)
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


def write_new_json(path: Path, payload: dict[str, Any]) -> None:
    allowed = {Path(value).resolve() for value in result_paths().values()}
    resolved = path.resolve()
    if resolved not in allowed:
        raise RuntimeError("拒绝写入未登记的 5.0 质量结果路径")
    if resolved.exists():
        raise RuntimeError("5.0 质量结果已经存在，拒绝覆盖")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
