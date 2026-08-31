from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
    build_job_evaluation_plan_v5_messages,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    build_screening_evaluation_v5_messages,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    screening_evaluation_service,
)
from run_stage7_7r5i4_preflight import I4_FROZEN_HASHES  # noqa: E402
from stage7_7r5_quality_contract import (  # noqa: E402
    ACTIVE_RUN_ID,
    I3_RUN_ID,
    I4_FINAL_RESULT_PATH,
    I4_HUMAN_AUDIT_PATH,
    I4_PREFLIGHT_PATH,
    I4_QUALITY_CONTRACT_VERSION,
    I4_RAW_RESULT_PATH,
    I4_REVIEW_PATH,
    I4_RUN_ID,
    PLAN_MAX_OUTPUT_TOKENS,
    PLANNED_MODEL,
    REPORT_MAX_OUTPUT_TOKENS,
    validate_result_lifecycle,
)
from tests.fixtures.v5_i4_quality_samples import (  # noqa: E402
    I4_PLAN_JDS,
    I4_REPORT_PAIRS,
    I4_STABILITY_RUNS_PER_SAMPLE,
    I4_STABILITY_SAMPLE_INDICES,
)


PRICING_SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-31-stage7-7r5i4-pricing-snapshot.json"
)
OFFICIAL_PRICING_SOURCE_URL = (
    "https://api-docs.deepseek.com/quick_start/pricing/"
)
BEIJING = timezone(timedelta(hours=8), name="Asia/Shanghai")
SCHEDULE = (
    "Monday-Friday UTC 01:00-04:00 and 06:00-10:00 are peak; "
    "all other hours are off_peak"
)
RATE_KEYS = ("cache_hit_input", "cache_miss_input", "output")
SNAPSHOT_VALIDITY_HOURS = 24
ZERO_EXTERNAL_EFFECTS = {
    "api_key_read": False,
    "real_adapter_instantiated": False,
    "real_model_call_count": 0,
    "api_attempt_count": 0,
    "input_token_count": 0,
    "output_token_count": 0,
    "total_token_usage": 0,
    "estimated_spend_usd": 0,
    "actual_spend_usd": 0,
    "postgresql_write_count": 0,
    "i4_raw_write_count": 0,
    "i4_human_write_count": 0,
    "i4_final_write_count": 0,
    "formal_raw_human_final_write_count": 0,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_execution_contract() -> dict[str, str]:
    return {
        "plan_prompt_version": JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
        "plan_service_behavior_version": (
            JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION
        ),
        "plan_schema_version": JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
        "report_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "report_service_behavior_version": (
            SCREENING_EVALUATION_V5_BEHAVIOR_VERSION
        ),
        "report_schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    }


def validate_active_i4_preflight(
    *, require_formal_results_absent: bool = False
) -> dict[str, Any]:
    lifecycle = validate_result_lifecycle(run_id=I4_RUN_ID)
    allowed_states = {"i4_preflight_complete"} if require_formal_results_absent else {
        "i4_preflight_complete", "i4_raw_complete"
    }
    if lifecycle["state"] not in allowed_states:
        raise RuntimeError("I4 生命周期不允许读取当前价格快照")
    if not I4_PREFLIGHT_PATH.exists() or not I4_REVIEW_PATH.exists():
        raise RuntimeError("I4 preflight 或 fixture review 缺失，必须返回 CLOSE-06R2-A")
    if require_formal_results_absent and any(
        path.exists()
        for path in (
            I4_RAW_RESULT_PATH,
            I4_HUMAN_AUDIT_PATH,
            I4_FINAL_RESULT_PATH,
        )
    ):
        raise RuntimeError("CLOSE-06R2-B 前不得存在 I4 raw/human/final")
    try:
        payload = json.loads(I4_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("I4 preflight 无法读取") from None

    execution = _actual_execution_contract()
    identity = {
        "stage": payload.get("stage"),
        "lifecycle": payload.get("lifecycle"),
        "quality_contract_version": payload.get("quality_contract_version"),
        **execution,
        "historical_lifecycles": payload.get("historical_lifecycles"),
    }
    expected = {
        "stage": I4_RUN_ID,
        "lifecycle": "i4_preflight_complete",
        "quality_contract_version": I4_QUALITY_CONTRACT_VERSION,
        "plan_prompt_version": "job_evaluation_plan_lightweight_v4",
        "plan_service_behavior_version": "lightweight_plan_generation_v5",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v7",
        "report_service_behavior_version": "lightweight_report_generation_v9",
        "report_schema_version": "5.0",
        "historical_lifecycles": {
            ACTIVE_RUN_ID: "i2_final_complete",
            I3_RUN_ID: "i3_raw_complete",
        },
    }
    if identity != expected:
        raise RuntimeError("I4 preflight 身份、生命周期或生产版本不一致")
    if payload.get("execution_contract") != execution:
        raise RuntimeError("I4 preflight 冻结执行合同与当前生产版本不一致")
    if payload.get("fixture_hashes") != I4_FROZEN_HASHES:
        raise RuntimeError("I4 preflight 冻结样本指纹不一致")
    if not payload.get("preflight_checks", {}).get("all_passed"):
        raise RuntimeError("I4 preflight 未通过全部零调用检查")
    zero_keys = (
        "real_model_call_count",
        "api_attempt_count",
        "input_token_count",
        "output_token_count",
        "estimated_spend_usd",
        "api_key_read",
        "postgresql_write_count",
        "formal_raw_human_final_write_count",
    )
    if any(payload.get(key) not in (0, False) for key in zero_keys):
        raise RuntimeError("I4 preflight 不是零调用、零费用、零写入状态")
    return identity


def _job(case: dict[str, Any], index: int) -> SimpleNamespace:
    jd = case["jd"]
    return SimpleNamespace(
        id=194_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=jd["job_background"],
        job_responsibilities=jd["job_responsibilities"],
        candidate_requirements=jd["candidate_requirements"],
        preferred_qualifications=jd["preferred_qualifications"],
        public_notes=jd["public_notes"],
        status="open",
    )


def _serialized_utf8_bytes(value: Any) -> int:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return len(encoded)


def _report_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    sanitized = screening_evaluation_service.sanitize_resume_text(
        case["resume_text"]
    )
    return build_screening_evaluation_v5_messages(
        job_snapshot=case["jd"],
        evaluation_plan=case["confirmed_plan_snapshot"]["plan"],
        sanitized_resume=sanitized,
        evaluation_reference_at="",
        evaluation_timezone="",
        experience_period_facts={},
    )


def compute_request_budget() -> dict[str, Any]:
    validate_active_i4_preflight()
    plan_calls = len(I4_PLAN_JDS)
    report_calls = len(I4_REPORT_PAIRS)
    stability_calls = (
        len(I4_STABILITY_SAMPLE_INDICES) * I4_STABILITY_RUNS_PER_SAMPLE
    )
    if (plan_calls, report_calls, stability_calls) != (10, 20, 15):
        raise RuntimeError("I4 冻结调用分母已经漂移")

    plan_bytes = 0
    for index, case in enumerate(I4_PLAN_JDS):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, index)
        ).model_dump(mode="json")
        plan_bytes += _serialized_utf8_bytes(
            build_job_evaluation_plan_v5_messages(snapshot)
        )

    report_message_bytes = {
        index: _serialized_utf8_bytes(_report_messages(case))
        for index, case in enumerate(I4_REPORT_PAIRS)
    }
    report_bytes = sum(report_message_bytes.values())
    stability_bytes = sum(
        report_message_bytes[index] * I4_STABILITY_RUNS_PER_SAMPLE
        for index in I4_STABILITY_SAMPLE_INDICES
    )
    baseline_input_upper = plan_bytes + report_bytes + stability_bytes
    baseline_output_upper = (
        plan_calls * PLAN_MAX_OUTPUT_TOKENS
        + (report_calls + stability_calls) * REPORT_MAX_OUTPUT_TOKENS
    )
    retry_input_upper = baseline_input_upper * 2
    retry_output_upper = baseline_output_upper * 2
    return {
        "plan_business_calls": plan_calls,
        "report_business_calls": report_calls,
        "stability_business_calls": stability_calls,
        "baseline_business_calls": 45,
        "maximum_infrastructure_retries_per_business_call": 1,
        "maximum_infrastructure_retries": 45,
        "maximum_api_attempts": 90,
        "content_error_retry_count": 0,
        "plan_max_output_tokens_per_attempt": PLAN_MAX_OUTPUT_TOKENS,
        "report_max_output_tokens_per_attempt": REPORT_MAX_OUTPUT_TOKENS,
        "baseline_max_output_tokens": baseline_output_upper,
        "retry_ceiling_max_output_tokens": retry_output_upper,
        "baseline_input_token_upper_bound": baseline_input_upper,
        "retry_ceiling_input_token_upper_bound": retry_input_upper,
        "baseline_total_token_upper_bound": (
            baseline_input_upper + baseline_output_upper
        ),
        "retry_ceiling_total_token_upper_bound": (
            retry_input_upper + retry_output_upper
        ),
        "input_token_upper_bound_basis": "serialized_prompt_utf8_bytes",
        "cache_assumption": "all_input_cache_miss",
    }


def pricing_tier_at(value: datetime) -> str:
    if value.tzinfo is None:
        raise RuntimeError("价格查询时间必须包含时区")
    utc_value = value.astimezone(timezone.utc)
    hour = utc_value.hour
    is_weekday = utc_value.weekday() < 5
    if is_weekday and (1 <= hour < 4 or 6 <= hour < 10):
        return "peak"
    return "off_peak"


def _validated_rates(raw: dict[str, Any] | None, *, label: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise RuntimeError(f"{label} 费用单价缺失")
    result: dict[str, float] = {}
    for key in RATE_KEYS:
        try:
            value = Decimal(str(raw[key]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            raise RuntimeError(f"{label} 费用字段无效：{key}") from None
        if not value.is_finite() or value < 0:
            raise RuntimeError(f"{label} 费用字段不能为负数或无穷值：{key}")
        result[key] = float(value)
    return result


def _estimate(
    *, input_upper: int, output_upper: int, rates: dict[str, float]
) -> Decimal:
    total = (
        Decimal(input_upper) * Decimal(str(rates["cache_miss_input"]))
        + Decimal(output_upper) * Decimal(str(rates["output"]))
    ) / Decimal(1_000_000)
    return total.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def _cost_estimates(
    budget: dict[str, Any],
    *,
    off_peak_rates: dict[str, float],
    peak_rates: dict[str, float],
) -> dict[str, float]:
    return {
        "off_peak_baseline": float(
            _estimate(
                input_upper=budget["baseline_input_token_upper_bound"],
                output_upper=budget["baseline_max_output_tokens"],
                rates=off_peak_rates,
            )
        ),
        "off_peak_retry_ceiling": float(
            _estimate(
                input_upper=budget["retry_ceiling_input_token_upper_bound"],
                output_upper=budget["retry_ceiling_max_output_tokens"],
                rates=off_peak_rates,
            )
        ),
        "peak_baseline": float(
            _estimate(
                input_upper=budget["baseline_input_token_upper_bound"],
                output_upper=budget["baseline_max_output_tokens"],
                rates=peak_rates,
            )
        ),
        "peak_retry_ceiling": float(
            _estimate(
                input_upper=budget["retry_ceiling_input_token_upper_bound"],
                output_upper=budget["retry_ceiling_max_output_tokens"],
                rates=peak_rates,
            )
        ),
    }


def build_pricing_snapshot(
    *,
    checked_at: datetime,
    model_version_shown_by_provider: str,
    off_peak_rates: dict[str, Any],
    peak_rates: dict[str, Any],
) -> dict[str, Any]:
    if checked_at.tzinfo is None:
        raise RuntimeError("官方价格查询时间必须包含时区")
    if model_version_shown_by_provider != "DeepSeek-V4-Flash-0731":
        raise RuntimeError("官方页面模型版本无法可靠映射到计划模型")
    checked_at = checked_at.astimezone(BEIJING)
    off_peak = _validated_rates(off_peak_rates, label="off_peak")
    peak = _validated_rates(peak_rates, label="peak")
    for key in RATE_KEYS:
        if Decimal(str(off_peak[key])) * 2 != Decimal(str(peak[key])):
            raise RuntimeError("官方 peak/off_peak 费用不是当前页面展示的两倍关系")

    identity = validate_active_i4_preflight(require_formal_results_absent=True)
    budget = compute_request_budget()
    estimates = _cost_estimates(
        budget,
        off_peak_rates=off_peak,
        peak_rates=peak,
    )
    minimum_required = math.ceil(estimates["peak_retry_ceiling"] * 100) / 100
    suggested_hard_cap = float(math.ceil(minimum_required))
    selected_tier = pricing_tier_at(checked_at)
    selected_rates = off_peak if selected_tier == "off_peak" else peak
    return {
        "stage": I4_RUN_ID,
        "purpose": "i4_official_pricing_and_usd_authorization_gate",
        "quality_contract_version": I4_QUALITY_CONTRACT_VERSION,
        "preflight_path": str(I4_PREFLIGHT_PATH),
        "preflight_sha256": sha256_file(I4_PREFLIGHT_PATH),
        "fixture_review_path": str(I4_REVIEW_PATH),
        "fixture_review_sha256": sha256_file(I4_REVIEW_PATH),
        "checked_at": checked_at.isoformat(),
        "expires_at": (
            checked_at + timedelta(hours=SNAPSHOT_VALIDITY_HOURS)
        ).isoformat(),
        "timezone": "Asia/Shanghai",
        "source_url": OFFICIAL_PRICING_SOURCE_URL,
        "model": PLANNED_MODEL,
        "model_version_shown_by_provider": model_version_shown_by_provider,
        "official_model_supported": True,
        "selected_tier": selected_tier,
        "schedule": SCHEDULE,
        "usd_per_million_tokens": selected_rates,
        "off_peak_usd_per_million_tokens": off_peak,
        "peak_usd_per_million_tokens": peak,
        "production_execution_contract": {
            key: identity[key]
            for key in (
                "plan_prompt_version",
                "plan_service_behavior_version",
                "plan_schema_version",
                "report_prompt_version",
                "report_service_behavior_version",
                "report_schema_version",
            )
        },
        "historical_lifecycles": identity["historical_lifecycles"],
        "historical_recalculation_allowed": False,
        "call_budget": budget,
        "conservative_calculation_method": {
            "input_upper_bound": "serialized prompt UTF-8 bytes used as a conservative token upper bound",
            "cache": "all input priced as cache miss",
            "baseline": "45 business calls with no infrastructure retry",
            "extreme": "90 API attempts with every business call using its one allowed infrastructure retry",
            "authorization_floor": "peak retry ceiling rounded up to the next USD cent",
        },
        "cost_estimates_usd": estimates,
        "selected_tier_baseline_estimate_usd": estimates[
            f"{selected_tier}_baseline"
        ],
        "selected_tier_extreme_upper_bound_usd": estimates[
            f"{selected_tier}_retry_ceiling"
        ],
        "authorization_gate": {
            "monetary_cap_usd": None,
            "minimum_required_usd": minimum_required,
            "suggested_hard_cap_usd": suggested_hard_cap,
            "explicit_usd_amount_required": True,
            "amount_must_not_be_below_minimum": True,
            "bind_i4_snapshot_and_model": True,
            "return_to_close_06r2_b_on_expiry_model_price_or_tier_change": True,
            "user_monetary_authorization_required": True,
            "real_run_allowed": False,
        },
        "official_pricing_lookup_count": 1,
        "external_effects": dict(ZERO_EXTERNAL_EFFECTS),
        "notes": [
            "This is a new I4 snapshot; no I3 price or authorization was reused.",
            "The official pricing page states that billing uses total input and output tokens.",
            "CLOSE-06R2-B does not contain an API key and does not authorize a real model call.",
            "CLOSE-06R2-C must return to B when the snapshot expires or the official model, price, or execution tier changes.",
        ],
    }


def validate_pricing_snapshot(
    payload: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    identity = validate_active_i4_preflight()
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("价格快照缺少合法的查询或过期时间") from None
    if checked_at.tzinfo is None or expires_at.tzinfo is None:
        raise RuntimeError("价格快照时间必须包含时区")
    if expires_at != checked_at + timedelta(hours=SNAPSHOT_VALIDITY_HOURS):
        raise RuntimeError("价格快照有效期必须精确为 24 小时")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise RuntimeError("当前校验时间必须包含时区")
    age_seconds = (
        current.astimezone(timezone.utc) - checked_at.astimezone(timezone.utc)
    ).total_seconds()
    if age_seconds < -300 or current > expires_at:
        raise RuntimeError("价格快照已过期或查询时间异常")

    if payload.get("stage") != I4_RUN_ID:
        raise RuntimeError("价格快照与 I4 身份不一致")
    if payload.get("quality_contract_version") != I4_QUALITY_CONTRACT_VERSION:
        raise RuntimeError("价格快照与 I4 质量合同不一致")
    if payload.get("source_url") != OFFICIAL_PRICING_SOURCE_URL:
        raise RuntimeError("价格快照不是 DeepSeek 官方来源")
    if (
        payload.get("model") != PLANNED_MODEL
        or payload.get("model_version_shown_by_provider")
        != "DeepSeek-V4-Flash-0731"
        or payload.get("official_model_supported") is not True
    ):
        raise RuntimeError("价格快照模型与官方当前支持模型不一致")
    if payload.get("preflight_sha256") != sha256_file(I4_PREFLIGHT_PATH):
        raise RuntimeError("价格快照未绑定当前 I4 preflight")
    if payload.get("fixture_review_sha256") != sha256_file(I4_REVIEW_PATH):
        raise RuntimeError("价格快照未绑定当前 I4 fixture review")
    expected_execution = {
        key: identity[key]
        for key in (
            "plan_prompt_version",
            "plan_service_behavior_version",
            "plan_schema_version",
            "report_prompt_version",
            "report_service_behavior_version",
            "report_schema_version",
        )
    }
    if payload.get("production_execution_contract") != expected_execution:
        raise RuntimeError("价格快照绑定的生产版本已变化")

    expected_tier = pricing_tier_at(checked_at)
    if payload.get("selected_tier") != expected_tier:
        raise RuntimeError("价格快照选择的 peak/off_peak 时段不正确")
    off_peak = _validated_rates(
        payload.get("off_peak_usd_per_million_tokens"),
        label="off_peak",
    )
    peak = _validated_rates(
        payload.get("peak_usd_per_million_tokens"),
        label="peak",
    )
    for key in RATE_KEYS:
        if Decimal(str(off_peak[key])) * 2 != Decimal(str(peak[key])):
            raise RuntimeError("价格快照的 peak/off_peak 费用关系被篡改")
    selected = _validated_rates(
        payload.get("usd_per_million_tokens"),
        label="selected",
    )
    if selected != (off_peak if expected_tier == "off_peak" else peak):
        raise RuntimeError("价格快照当前时段费用与两档官方费用不一致")

    expected_budget = compute_request_budget()
    if payload.get("call_budget") != expected_budget:
        raise RuntimeError("价格快照的调用分母或 token 上界被篡改")
    expected_estimates = _cost_estimates(
        expected_budget,
        off_peak_rates=off_peak,
        peak_rates=peak,
    )
    if payload.get("cost_estimates_usd") != expected_estimates:
        raise RuntimeError("价格快照的保守费用公式或结果不一致")
    expected_minimum = math.ceil(
        expected_estimates["peak_retry_ceiling"] * 100
    ) / 100
    expected_suggested = float(math.ceil(expected_minimum))
    expected_gate = {
        "monetary_cap_usd": None,
        "minimum_required_usd": expected_minimum,
        "suggested_hard_cap_usd": expected_suggested,
        "explicit_usd_amount_required": True,
        "amount_must_not_be_below_minimum": True,
        "bind_i4_snapshot_and_model": True,
        "return_to_close_06r2_b_on_expiry_model_price_or_tier_change": True,
        "user_monetary_authorization_required": True,
        "real_run_allowed": False,
    }
    if payload.get("authorization_gate") != expected_gate:
        raise RuntimeError("CLOSE-06R2-B 不得提前写入金额或真实运行授权")
    if payload.get("external_effects") != ZERO_EXTERNAL_EFFECTS:
        raise RuntimeError("CLOSE-06R2-B 外部调用或写入计数必须全部为 0")
    return payload


def validate_future_real_authorization(
    snapshot: dict[str, Any],
    authorization: dict[str, Any],
    *,
    snapshot_path: Path,
    now: datetime,
    observed_model: str,
    observed_tier: str,
    observed_off_peak_rates: dict[str, Any],
    observed_peak_rates: dict[str, Any],
) -> dict[str, Any]:
    validate_pricing_snapshot(snapshot, now=now)
    off_peak = _validated_rates(observed_off_peak_rates, label="observed_off_peak")
    peak = _validated_rates(observed_peak_rates, label="observed_peak")
    if (
        observed_model != snapshot["model"]
        or observed_tier != snapshot["selected_tier"]
        or off_peak != snapshot["off_peak_usd_per_million_tokens"]
        or peak != snapshot["peak_usd_per_million_tokens"]
    ):
        raise RuntimeError("模型、价格或执行时段变化，必须返回 CLOSE-06R2-B")
    if not snapshot_path.exists():
        raise RuntimeError("绑定的 I4 价格快照不存在")
    expected_binding = {
        "stage": I4_RUN_ID,
        "pricing_snapshot_path": str(snapshot_path),
        "pricing_snapshot_sha256": sha256_file(snapshot_path),
        "model": snapshot["model"],
        "selected_tier": snapshot["selected_tier"],
    }
    if any(authorization.get(key) != value for key, value in expected_binding.items()):
        raise RuntimeError("美元授权未绑定当前 I4、价格快照、模型或执行时段")
    if authorization.get("explicit_user_authorization") is not True:
        raise RuntimeError("必须取得用户明确的美元金额授权")
    try:
        cap = Decimal(str(authorization["monetary_cap_usd"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise RuntimeError("授权必须明确写出 USD 金额") from None
    minimum = Decimal(str(snapshot["authorization_gate"]["minimum_required_usd"]))
    if not cap.is_finite() or cap < minimum:
        raise RuntimeError("授权 USD 金额低于保守需求")
    return {**authorization, "monetary_cap_usd": float(cap)}


def write_pricing_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("I4 价格快照已存在，拒绝覆盖") from None


def _rate_args(args: argparse.Namespace, prefix: str) -> dict[str, float]:
    return {
        "cache_hit_input": getattr(args, f"{prefix}_cache_hit"),
        "cache_miss_input": getattr(args, f"{prefix}_cache_miss"),
        "output": getattr(args, f"{prefix}_output"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the zero-call I4 official pricing and USD authorization gate"
    )
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--checked-at")
    parser.add_argument("--model-version")
    for tier in ("off_peak", "peak"):
        parser.add_argument(
            f"--{tier.replace('_', '-')}-cache-hit",
            type=float,
        )
        parser.add_argument(
            f"--{tier.replace('_', '-')}-cache-miss",
            type=float,
        )
        parser.add_argument(
            f"--{tier.replace('_', '-')}-output",
            type=float,
        )
    args = parser.parse_args()

    if args.write_snapshot:
        validate_active_i4_preflight(require_formal_results_absent=True)
        required = (
            args.checked_at,
            args.model_version,
            args.off_peak_cache_hit,
            args.off_peak_cache_miss,
            args.off_peak_output,
            args.peak_cache_hit,
            args.peak_cache_miss,
            args.peak_output,
        )
        if any(value is None for value in required):
            parser.error(
                "写入快照时必须显式提供官方查询时间、模型版本和两档价格"
            )
        payload = build_pricing_snapshot(
            checked_at=datetime.fromisoformat(args.checked_at),
            model_version_shown_by_provider=args.model_version,
            off_peak_rates=_rate_args(args, "off_peak"),
            peak_rates=_rate_args(args, "peak"),
        )
        write_pricing_snapshot(PRICING_SNAPSHOT_PATH, payload)
    else:
        payload = json.loads(PRICING_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    validated = validate_pricing_snapshot(payload)
    print(
        json.dumps(
            {
                "path": str(PRICING_SNAPSHOT_PATH),
                "stage": validated["stage"],
                "selected_tier": validated["selected_tier"],
                "expires_at": validated["expires_at"],
                "call_budget": validated["call_budget"],
                "cost_estimates_usd": validated["cost_estimates_usd"],
                "authorization_gate": validated["authorization_gate"],
                **validated["external_effects"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
