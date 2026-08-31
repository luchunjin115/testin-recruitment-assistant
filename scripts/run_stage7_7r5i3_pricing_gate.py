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
    build_job_evaluation_plan_v5_messages,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    build_screening_evaluation_v5_messages,
)
from app.services.experience_period_service import experience_period_service  # noqa: E402
from app.services.job_evaluation_plan_service import job_evaluation_plan_service  # noqa: E402
from app.services.screening_evaluation_service import screening_evaluation_service  # noqa: E402
from run_stage7_7r5i3_preflight import I3_FROZEN_HASHES  # noqa: E402
from stage7_7r5_quality_contract import (  # noqa: E402
    I3_FINAL_RESULT_PATH,
    I3_HUMAN_AUDIT_PATH,
    I3_PREFLIGHT_PATH,
    I3_QUALITY_CONTRACT_VERSION,
    I3_RAW_RESULT_PATH,
    I3_RUN_ID,
    OFFICIAL_PRICING_SOURCE_URL,
    PLANNED_MODEL,
    call_budget,
)
from tests.fixtures.v5_i3_quality_samples import (  # noqa: E402
    I3_PLAN_JDS,
    I3_REPORT_PAIRS,
    I3_STABILITY_RUNS_PER_SAMPLE,
    I3_STABILITY_SAMPLE_INDICES,
)


PRICING_SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-31-stage7-7r5i3-r1-pricing-snapshot.json"
)
BEIJING = timezone(timedelta(hours=8), name="Asia/Shanghai")
SCHEDULE = (
    "Monday-Friday UTC 01:00-04:00 and 06:00-10:00 are peak; "
    "all other hours are off_peak"
)
RATE_KEYS = ("cache_hit_input", "cache_miss_input", "output")
ZERO_EXTERNAL_EFFECTS = {
    "api_key_read": False,
    "real_adapter_instantiated": False,
    "real_model_call_count": 0,
    "api_attempt_count": 0,
    "input_token_count": 0,
    "output_token_count": 0,
    "estimated_spend_usd": 0,
    "postgresql_write_count": 0,
    "formal_result_write_count": 0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job(case: dict[str, Any], index: int) -> SimpleNamespace:
    jd = case["jd"]
    return SimpleNamespace(
        id=193_000 + index,
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


def validate_active_r1_preflight(
    *, require_formal_results_absent: bool = False
) -> dict[str, Any]:
    if not I3_PREFLIGHT_PATH.exists():
        raise RuntimeError("活动 I3-R1 preflight 缺失，必须返回 CLOSE-06A-R1")
    if require_formal_results_absent and any(
        path.exists()
        for path in (
            I3_RAW_RESULT_PATH,
            I3_HUMAN_AUDIT_PATH,
            I3_FINAL_RESULT_PATH,
        )
    ):
        raise RuntimeError("CLOSE-06B 前不得存在 I3-R1 raw/human/final")
    try:
        payload = json.loads(I3_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("活动 I3-R1 preflight 无法读取") from None

    summary = payload.get("fixture_summary", {})
    identity = {
        "stage": payload.get("stage"),
        "lifecycle": payload.get("lifecycle"),
        "fixture_revision": payload.get("fixture_revision"),
        "direction_distribution": summary.get("direction_distribution"),
        "stability_direction_distribution": summary.get(
            "stability_direction_distribution"
        ),
    }
    expected = {
        "stage": I3_RUN_ID,
        "lifecycle": "i3_preflight_complete",
        "fixture_revision": "r1",
        "direction_distribution": {
            "high_match": 8,
            "partial_match": 6,
            "low_match": 6,
        },
        "stability_direction_distribution": {
            "high_match": 2,
            "partial_match": 2,
            "low_match": 1,
        },
    }
    if identity != expected:
        raise RuntimeError("活动 I3-R1 preflight 身份、生命周期或方向分布不一致")
    if payload.get("fixture_hashes") != I3_FROZEN_HASHES:
        raise RuntimeError("活动 I3-R1 preflight 的冻结样本指纹不一致")
    if payload.get("quality_contract_version") != I3_QUALITY_CONTRACT_VERSION:
        raise RuntimeError("活动 I3-R1 preflight 的质量合同版本不一致")
    if not payload.get("preflight_checks", {}).get("all_passed"):
        raise RuntimeError("活动 I3-R1 preflight 未通过全部零调用检查")
    if any(
        payload.get(key) not in (0, False)
        for key in (
            "real_model_call_count",
            "api_attempt_count",
            "input_token_count",
            "output_token_count",
            "estimated_spend_usd",
            "api_key_read",
            "postgresql_write_count",
            "formal_result_write_count",
        )
    ):
        raise RuntimeError("活动 I3-R1 preflight 不是零调用、零费用状态")
    return identity


def _report_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    sanitized = screening_evaluation_service.sanitize_resume_text(
        case["resume_text"]
    )
    reference = datetime.fromisoformat(case["evaluation_reference_at"])
    facts = experience_period_service.build(
        sanitized,
        evaluation_reference_at=reference,
        evaluation_timezone="Asia/Shanghai",
    ).model_dump(mode="json")
    return build_screening_evaluation_v5_messages(
        job_snapshot=case["jd"],
        evaluation_plan=case["confirmed_plan_snapshot"]["plan"],
        sanitized_resume=sanitized,
        evaluation_reference_at=case["evaluation_reference_at"],
        evaluation_timezone="Asia/Shanghai",
        experience_period_facts=facts,
    )


def compute_request_budget() -> dict[str, Any]:
    validate_active_r1_preflight()
    frozen = call_budget()
    plan_bytes = 0
    for index, case in enumerate(I3_PLAN_JDS):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, index)
        ).model_dump(mode="json")
        plan_bytes += _serialized_utf8_bytes(
            build_job_evaluation_plan_v5_messages(snapshot)
        )

    report_message_bytes: dict[int, int] = {}
    for index, case in enumerate(I3_REPORT_PAIRS):
        report_message_bytes[index] = _serialized_utf8_bytes(
            _report_messages(case)
        )
    report_bytes = sum(report_message_bytes.values())
    stability_bytes = sum(
        report_message_bytes[index] * I3_STABILITY_RUNS_PER_SAMPLE
        for index in I3_STABILITY_SAMPLE_INDICES
    )
    baseline_input_upper = plan_bytes + report_bytes + stability_bytes
    return {
        "plan_business_calls": len(I3_PLAN_JDS),
        "report_business_calls": len(I3_REPORT_PAIRS),
        "stability_business_calls": len(I3_STABILITY_SAMPLE_INDICES)
        * I3_STABILITY_RUNS_PER_SAMPLE,
        "baseline_business_calls": frozen["baseline_business_calls"],
        "maximum_infrastructure_retries": frozen[
            "maximum_infrastructure_retries"
        ],
        "maximum_api_attempts": frozen["maximum_api_attempts"],
        "content_error_retry_count": frozen["content_error_retry_count"],
        "baseline_max_output_tokens": frozen["baseline_max_output_tokens"],
        "retry_ceiling_max_output_tokens": frozen[
            "retry_ceiling_max_output_tokens"
        ],
        "baseline_input_token_upper_bound": baseline_input_upper,
        "retry_ceiling_input_token_upper_bound": baseline_input_upper * 2,
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


def _validated_rates(raw: dict[str, Any], *, label: str) -> dict[str, float]:
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
    checked_at = checked_at.astimezone(BEIJING)
    off_peak = _validated_rates(off_peak_rates, label="off_peak")
    peak = _validated_rates(peak_rates, label="peak")
    for key in RATE_KEYS:
        if Decimal(str(off_peak[key])) * 2 != Decimal(str(peak[key])):
            raise RuntimeError("官方 peak/off_peak 费用不是当前页面展示的两倍关系")

    budget = compute_request_budget()
    estimates = _cost_estimates(
        budget, off_peak_rates=off_peak, peak_rates=peak
    )
    requested_cap_floor = math.ceil(estimates["peak_retry_ceiling"] * 100) / 100
    selected_tier = pricing_tier_at(checked_at)
    selected_rates = off_peak if selected_tier == "off_peak" else peak
    return {
        "stage": I3_RUN_ID,
        "purpose": "independent_real_quality_revalidation_pricing_gate",
        "quality_contract_version": I3_QUALITY_CONTRACT_VERSION,
        "preflight_path": str(I3_PREFLIGHT_PATH),
        "preflight_sha256": _sha256(I3_PREFLIGHT_PATH),
        "checked_at": checked_at.isoformat(),
        "expires_at": (checked_at + timedelta(hours=24)).isoformat(),
        "source_url": OFFICIAL_PRICING_SOURCE_URL,
        "model": PLANNED_MODEL,
        "model_version_shown_by_provider": model_version_shown_by_provider,
        "selected_tier": selected_tier,
        "timezone": "Asia/Shanghai",
        "schedule": SCHEDULE,
        "usd_per_million_tokens": selected_rates,
        "off_peak_usd_per_million_tokens": off_peak,
        "peak_usd_per_million_tokens": peak,
        "call_budget": budget,
        "cost_estimates_usd": estimates,
        "requested_cap_basis": "peak_retry_ceiling_rounded_up_to_cent",
        "requested_cap_floor_usd": requested_cap_floor,
        "authorization": {
            "monetary_cap_usd": None,
            "user_monetary_authorization_required": True,
            "real_run_allowed": False,
        },
        "external_effects": dict(ZERO_EXTERNAL_EFFECTS),
        "notes": [
            "Input token upper bounds use serialized prompt UTF-8 bytes, which conservatively overstate token counts.",
            "All input is priced as cache miss; the requested cap floor uses peak rates and the 90-attempt retry ceiling.",
            "This snapshot does not contain an API key and does not authorize any real model call.",
            "CLOSE-06C must return to CLOSE-06B if the official price, model, tier, or 24-hour validity changes before execution.",
        ],
    }


def validate_pricing_snapshot(
    payload: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    validate_active_r1_preflight()
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("价格快照缺少合法的查询或过期时间") from None
    if checked_at.tzinfo is None or expires_at.tzinfo is None:
        raise RuntimeError("价格快照时间必须包含时区")
    if expires_at != checked_at + timedelta(hours=24):
        raise RuntimeError("价格快照有效期必须精确为 24 小时")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise RuntimeError("当前校验时间必须包含时区")
    age_seconds = (
        current.astimezone(timezone.utc) - checked_at.astimezone(timezone.utc)
    ).total_seconds()
    if age_seconds < -300 or current > expires_at:
        raise RuntimeError("价格快照已过期或查询时间异常")

    if (
        payload.get("stage") != I3_RUN_ID
        or payload.get("quality_contract_version") != I3_QUALITY_CONTRACT_VERSION
        or payload.get("source_url") != OFFICIAL_PRICING_SOURCE_URL
        or payload.get("model") != PLANNED_MODEL
        or payload.get("preflight_sha256") != _sha256(I3_PREFLIGHT_PATH)
    ):
        raise RuntimeError("价格快照与活动 I3-R1 身份、官方来源或模型不一致")
    expected_tier = pricing_tier_at(checked_at)
    if payload.get("selected_tier") != expected_tier:
        raise RuntimeError("价格快照选择的 peak/off_peak 时段不正确")
    off_peak = _validated_rates(
        payload.get("off_peak_usd_per_million_tokens"), label="off_peak"
    )
    peak = _validated_rates(
        payload.get("peak_usd_per_million_tokens"), label="peak"
    )
    for key in RATE_KEYS:
        if Decimal(str(off_peak[key])) * 2 != Decimal(str(peak[key])):
            raise RuntimeError("价格快照的 peak/off_peak 费用关系被篡改")
    selected = _validated_rates(
        payload.get("usd_per_million_tokens"), label="selected"
    )
    if selected != (off_peak if expected_tier == "off_peak" else peak):
        raise RuntimeError("价格快照的当前时段费用与两档官方费用不一致")

    expected_budget = compute_request_budget()
    if payload.get("call_budget") != expected_budget:
        raise RuntimeError("价格快照的冻结调用分母或 token 上界被篡改")
    expected_estimates = _cost_estimates(
        expected_budget, off_peak_rates=off_peak, peak_rates=peak
    )
    if payload.get("cost_estimates_usd") != expected_estimates:
        raise RuntimeError("价格快照的保守费用公式或结果不一致")
    expected_floor = math.ceil(expected_estimates["peak_retry_ceiling"] * 100) / 100
    if payload.get("requested_cap_floor_usd") != expected_floor:
        raise RuntimeError("价格快照的金额授权下限未覆盖最坏费用")
    if payload.get("authorization") != {
        "monetary_cap_usd": None,
        "user_monetary_authorization_required": True,
        "real_run_allowed": False,
    }:
        raise RuntimeError("CLOSE-06B 不得提前写入金额或真实运行授权")
    if payload.get("external_effects") != ZERO_EXTERNAL_EFFECTS:
        raise RuntimeError("CLOSE-06B 外部调用或写入计数必须全部为 0")
    return payload


def write_pricing_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("I3-R1 价格快照已存在，拒绝覆盖") from None


def _rate_args(args: argparse.Namespace, prefix: str) -> dict[str, float]:
    return {
        "cache_hit_input": getattr(args, f"{prefix}_cache_hit"),
        "cache_miss_input": getattr(args, f"{prefix}_cache_miss"),
        "output": getattr(args, f"{prefix}_output"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the zero-call I3-R1 pricing gate")
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--checked-at")
    parser.add_argument("--model-version")
    for tier in ("off_peak", "peak"):
        parser.add_argument(f"--{tier.replace('_', '-')}-cache-hit", type=float)
        parser.add_argument(f"--{tier.replace('_', '-')}-cache-miss", type=float)
        parser.add_argument(f"--{tier.replace('_', '-')}-output", type=float)
    args = parser.parse_args()

    if args.write_snapshot:
        validate_active_r1_preflight(require_formal_results_absent=True)
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
            parser.error("写入快照时必须显式提供官方查询时间、模型版本和两档价格")
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
                "cost_estimates_usd": validated["cost_estimates_usd"],
                "requested_cap_floor_usd": validated["requested_cap_floor_usd"],
                "real_run_allowed": validated["authorization"][
                    "real_run_allowed"
                ],
                **validated["external_effects"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
