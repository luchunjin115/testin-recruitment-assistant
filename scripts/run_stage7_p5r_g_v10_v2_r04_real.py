from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION,
    build_screening_evaluation_v5_messages,
    build_screening_evaluation_v5_repair_messages,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationRepairableOutputError,
    screening_evaluation_service,
)
import run_stage7_p5r_gf_r04_repair as frozen_gf_runner  # noqa: E402
from run_stage7_p5r_evidence_retest import (  # noqa: E402
    MODEL,
    REFERENCE_AT,
    REPORT_MAX_OUTPUT_TOKENS,
    _pricing,
)
from run_stage7_p5r_f_r04_diagnostic import _r04_inputs  # noqa: E402


STAGE = "stage7-p5r-g-v10-v2-real-validation"
CASE_ID = "R04"
BUSINESS_CALL_ID = "P5R-G-V10-V2-R04"
MONETARY_CAP_USD = 0.20
BUSINESS_CALL_MAXIMUM = 2
API_ATTEMPT_LIMIT = 3
PREFLIGHT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-g-v10-v2-r04-zero-call-preflight.json"
)
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-g-v10-v2-r04-real-results.json"
)
ATTEMPT_PATHS = tuple(
    PROJECT_ROOT
    / f"docs/stages/stage7/2026-09-01-stage7-p5r-g-v10-v2-r04-attempt-{number:02d}.json"
    for number in range(1, API_ATTEMPT_LIMIT + 1)
)
FROZEN_GF_RESULT_PATH = frozen_gf_runner.RESULT_PATH
FROZEN_GF_INITIAL_ATTEMPT_PATH = frozen_gf_runner.ATTEMPT_PATHS[0]
OFFICIAL_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing/"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _write_json_x(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _adapter_kwargs(inputs: dict[str, Any]) -> dict[str, Any]:
    snapshot = inputs["snapshot"]
    plan = inputs["plan"]
    return {
        "job_snapshot": snapshot.model_dump(mode="json"),
        "evaluation_plan": (
            plan.model_dump(mode="json") if hasattr(plan, "model_dump") else plan
        ),
        "sanitized_resume": inputs["sanitized_resume"],
        "evaluation_reference_at": REFERENCE_AT.isoformat(),
        "evaluation_timezone": "Asia/Shanghai",
        "experience_period_facts": {},
    }


def _input_fingerprint(inputs: dict[str, Any]) -> str:
    payload = {
        "case_id": CASE_ID,
        "job_case_id": inputs["job_case_id"],
        "snapshot": inputs["snapshot"].model_dump(mode="json"),
        "plan": (
            inputs["plan"].model_dump(mode="json")
            if hasattr(inputs["plan"], "model_dump")
            else inputs["plan"]
        ),
        "sanitized_resume": inputs["sanitized_resume"],
        "evaluation_reference_at": REFERENCE_AT.isoformat(),
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _frozen_initial_raw_and_errors(
    inputs: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    journal = json.loads(FROZEN_GF_INITIAL_ATTEMPT_PATH.read_text(encoding="utf-8"))
    raw = journal.get("raw_response")
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("冻结 GF 首次 raw 不存在或为空")
    try:
        screening_evaluation_service.parse_and_validate_v5_output(
            raw,
            evaluation_plan=inputs["plan"],
            sanitized_resume=inputs["sanitized_resume"],
        )
    except ScreeningEvaluationRepairableOutputError as exc:
        return raw, list(exc.validation_errors)
    raise RuntimeError("冻结 GF 首次 raw 不再触发 Repair v2 挑战")


def _zero_key_settings() -> Settings:
    return Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="",
        SCREENING_EVALUATION_MODEL=MODEL,
        SCREENING_EVALUATION_V5_PROMPT_VERSION=(
            SCREENING_EVALUATION_V5_PROMPT_VERSION
        ),
        SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION=(
            SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION
        ),
        SCREENING_EVALUATION_V5_SCHEMA_VERSION=(
            SCREENING_EVALUATION_V5_SCHEMA_VERSION
        ),
        SCREENING_EVALUATION_MAX_OUTPUT_TOKENS=REPORT_MAX_OUTPUT_TOKENS,
    )


def build_zero_call_preflight() -> dict[str, Any]:
    if not FROZEN_GF_RESULT_PATH.is_file() or not FROZEN_GF_INITIAL_ATTEMPT_PATH.is_file():
        raise RuntimeError("冻结 GF 结果或首次 attempt 不存在")
    inputs = _r04_inputs()
    settings = _zero_key_settings()
    expected_contract = {
        "model": MODEL,
        "main_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "repair_prompt_version": SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION,
        "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
        "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
        "business_call_maximum": BUSINESS_CALL_MAXIMUM,
        "api_attempt_limit": API_ATTEMPT_LIMIT,
    }
    if (
        settings.SCREENING_EVALUATION_MODEL != MODEL
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
        != SCREENING_EVALUATION_V5_SCHEMA_VERSION
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS
        != REPORT_MAX_OUTPUT_TOKENS
    ):
        raise RuntimeError("v10/v2 零调用配置与代码合同不一致")

    frozen_raw, validation_errors = _frozen_initial_raw_and_errors(inputs)
    initial_messages = build_screening_evaluation_v5_messages(**_adapter_kwargs(inputs))
    repair_messages = build_screening_evaluation_v5_repair_messages(
        sanitized_resume=inputs["sanitized_resume"],
        confirmed_criteria=_adapter_kwargs(inputs)["evaluation_plan"]["criteria"],
        original_response=frozen_raw,
        validation_errors=validation_errors,
    )
    synthetic_large_repair_messages = build_screening_evaluation_v5_repair_messages(
        sanitized_resume=inputs["sanitized_resume"],
        confirmed_criteria=_adapter_kwargs(inputs)["evaluation_plan"]["criteria"],
        original_response="x" * (REPORT_MAX_OUTPUT_TOKENS * 4),
        validation_errors=validation_errors,
    )
    initial_reservation = frozen_gf_runner._reservation_usd(initial_messages)
    frozen_repair_reservation = frozen_gf_runner._reservation_usd(repair_messages)
    large_repair_reservation = frozen_gf_runner._reservation_usd(
        synthetic_large_repair_messages
    )
    maximum_single = max(initial_reservation, large_repair_reservation)
    if maximum_single >= MONETARY_CAP_USD:
        raise RuntimeError("单次 API attempt 的 peak 保守预留超过 USD 0.20")
    if initial_reservation + frozen_repair_reservation >= MONETARY_CAP_USD:
        raise RuntimeError("当前 R04 主调用加冻结 Repair 挑战预留超过 USD 0.20")
    if len(validation_errors) != 12:
        raise RuntimeError("冻结 GF raw 在当前 Service 下不再产生预期的 12 条错误")

    return {
        "stage": STAGE,
        "mode": "zero_call_preflight",
        "generated_at": _utc_now(),
        "status": "passed",
        "contract": expected_contract,
        "source": {
            "case_id": CASE_ID,
            "input_fingerprint_sha256": _input_fingerprint(inputs),
            "frozen_gf_result_path": _relative(FROZEN_GF_RESULT_PATH),
            "frozen_gf_result_sha256": _sha256(FROZEN_GF_RESULT_PATH),
            "frozen_gf_initial_attempt_path": _relative(
                FROZEN_GF_INITIAL_ATTEMPT_PATH
            ),
            "frozen_gf_initial_attempt_sha256": _sha256(
                FROZEN_GF_INITIAL_ATTEMPT_PATH
            ),
        },
        "frozen_replay": {
            "repairable_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "raw_persisted_in_preflight": False,
        },
        "execution_plan": {
            "fresh_v10_call": 1,
            "if_fresh_invalid": "Service 自动调用一次 Repair v2",
            "if_fresh_legal_without_repair": (
                "使用冻结 GF 首次 raw 调用一次 Repair v2 挑战"
            ),
            "maximum_business_calls": BUSINESS_CALL_MAXIMUM,
            "initial_infrastructure_retry_maximum": 1,
            "repair_infrastructure_retry_maximum": 0,
            "maximum_api_attempts": API_ATTEMPT_LIMIT,
            "postgresql_writes_allowed": False,
        },
        "cost_gate": {
            "hard_cap_usd": MONETARY_CAP_USD,
            "official_pricing_url": OFFICIAL_PRICING_URL,
            "official_pricing_checked_on": "2026-09-01",
            "tier": "peak",
            "rates_usd_per_million_tokens": (
                frozen_gf_runner.PEAK_RATES_USD_PER_MILLION
            ),
            "fresh_initial_reservation_usd": initial_reservation,
            "frozen_repair_challenge_reservation_usd": frozen_repair_reservation,
            "planned_two_call_reservation_usd": (
                initial_reservation + frozen_repair_reservation
            ),
            "synthetic_large_repair_reservation_usd": large_repair_reservation,
            "maximum_single_attempt_reservation_usd": maximum_single,
            "runtime_cumulative_guard_required": True,
        },
        "safety": {
            "api_key_read": False,
            "real_adapter_instantiated": False,
            "model_calls": 0,
            "tokens": 0,
            "cost_usd": 0,
            "postgresql_business_writes": 0,
        },
    }


def seal_zero_call_preflight(
    payload: dict[str, Any],
    *,
    path: Path = PREFLIGHT_PATH,
) -> None:
    _write_json_x(path, payload)


def should_run_direct_repair_challenge(
    *,
    fresh_result_exists: bool,
    fresh_content_repair_count: int,
) -> bool:
    return fresh_result_exists and fresh_content_repair_count == 0


def _load_sealed_preflight() -> dict[str, Any]:
    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("v10/v2 零调用预检证据不存在")
    payload = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    current = build_zero_call_preflight()
    for section in ("contract", "source", "frozen_replay", "execution_plan"):
        if payload.get(section) != current.get(section):
            raise RuntimeError(f"v10/v2 零调用预检 {section} 已漂移")
    return payload


def _assert_real_paths_empty() -> None:
    if RESULT_PATH.exists() or any(path.exists() for path in ATTEMPT_PATHS):
        raise RuntimeError("v10/v2 真实结果或 attempt 路径已存在，拒绝覆盖或补跑")


def _assert_real_settings(settings: Settings) -> None:
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("真实测试已获授权，但 DeepSeek API Key 未配置")
    if (
        settings.SCREENING_EVALUATION_MODEL != MODEL
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
        != SCREENING_EVALUATION_V5_SCHEMA_VERSION
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS
        != REPORT_MAX_OUTPUT_TOKENS
    ):
        raise RuntimeError("真实设置与 v10/v2/v11/Schema 5.0 合同不一致")


async def run_real() -> dict[str, Any]:
    _assert_real_paths_empty()
    preflight = _load_sealed_preflight()
    settings = get_settings()
    _assert_real_settings(settings)
    inputs = _r04_inputs()
    if _input_fingerprint(inputs) != preflight["source"]["input_fingerprint_sha256"]:
        raise RuntimeError("R04 冻结输入身份已漂移")

    ledger = frozen_gf_runner.CostLedger(cap_usd=MONETARY_CAP_USD)
    previous_business_call_id = frozen_gf_runner.BUSINESS_CALL_ID
    previous_attempt_paths = frozen_gf_runner.ATTEMPT_PATHS
    frozen_gf_runner.BUSINESS_CALL_ID = BUSINESS_CALL_ID
    frozen_gf_runner.ATTEMPT_PATHS = ATTEMPT_PATHS
    adapter = frozen_gf_runner.JournaledGFAdapter(
        delegate=DeepSeekScreeningEvaluationAdapter(settings=settings),
        ledger=ledger,
    )

    fresh_result = None
    fresh_error: Exception | None = None
    direct_challenge: dict[str, Any] = {
        "triggered": False,
        "status": "not_needed_or_not_reached",
    }
    try:
        try:
            fresh_result = await screening_evaluation_service.evaluate_v5(
                job_snapshot=inputs["snapshot"],
                evaluation_plan=inputs["plan"],
                resume_text=inputs["pair"]["resume_text"],
                evaluation_reference_at=REFERENCE_AT,
                evaluation_timezone="Asia/Shanghai",
                adapter=adapter,
                settings=settings,
            )
        except Exception as exc:
            fresh_error = exc

        fresh_audit = (
            getattr(fresh_result, "audit", None)
            or getattr(fresh_error, "audit", None)
        )
        fresh_content_repair_count = (
            fresh_audit.content_repair_count if fresh_audit is not None else 0
        )
        if should_run_direct_repair_challenge(
            fresh_result_exists=fresh_result is not None,
            fresh_content_repair_count=fresh_content_repair_count,
        ):
            frozen_raw, validation_errors = _frozen_initial_raw_and_errors(inputs)
            direct_challenge = {
                "triggered": True,
                "status": "failed",
                "source_raw_path": _relative(FROZEN_GF_INITIAL_ATTEMPT_PATH),
                "source_raw_sha256": hashlib.sha256(
                    frozen_raw.encode("utf-8")
                ).hexdigest(),
                "validation_errors": validation_errors,
                "complete_report_returned": False,
                "full_json_schema_service_revalidation_passed": False,
            }
            try:
                repair_result = await adapter.repair_v5(
                    sanitized_resume=inputs["sanitized_resume"],
                    confirmed_criteria=_adapter_kwargs(inputs)["evaluation_plan"][
                        "criteria"
                    ],
                    original_response=frozen_raw,
                    validation_errors=validation_errors,
                )
                repaired_report = screening_evaluation_service.parse_and_validate_v5_output(
                    repair_result.content,
                    evaluation_plan=inputs["plan"],
                    sanitized_resume=inputs["sanitized_resume"],
                )
            except Exception as exc:
                direct_challenge["error_type"] = type(exc).__name__
                direct_challenge["error_code"] = getattr(exc, "code", None)
            else:
                direct_challenge.update(
                    {
                        "status": "passed",
                        "complete_report_returned": True,
                        "full_json_schema_service_revalidation_passed": True,
                        "raw_changed": repair_result.content != frozen_raw,
                        "report": repaired_report.model_dump(mode="json"),
                    }
                )
    finally:
        frozen_gf_runner.BUSINESS_CALL_ID = previous_business_call_id
        frozen_gf_runner.ATTEMPT_PATHS = previous_attempt_paths

    fresh_audit = (
        getattr(fresh_result, "audit", None) or getattr(fresh_error, "audit", None)
    )
    fresh_report = (
        fresh_result.report.model_dump(mode="json")
        if fresh_result is not None
        else None
    )
    passed = fresh_result is not None and (
        not direct_challenge["triggered"] or direct_challenge["status"] == "passed"
    )
    attempt_count = len(adapter.attempts)
    payload = {
        "stage": STAGE,
        "batch": "P5R-G-v10-v2-real-validation",
        "mode": "fresh_v10_then_conditional_repair_v2_challenge",
        "generated_at": _utc_now(),
        "status": "passed" if passed else "failed",
        "authorization": {
            "user_directive": "现在我们再拿真实简历进行测试",
            "monetary_cap_usd": MONETARY_CAP_USD,
        },
        "execution_contract": {
            "business_call_id": BUSINESS_CALL_ID,
            "source_case_id": CASE_ID,
            "model": MODEL,
            "main_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "repair_prompt_version": SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION,
            "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
            "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "business_call_maximum": BUSINESS_CALL_MAXIMUM,
            "api_attempt_limit": API_ATTEMPT_LIMIT,
            "postgresql_writes_allowed": False,
        },
        "preflight": {
            "path": _relative(PREFLIGHT_PATH),
            "sha256": _sha256(PREFLIGHT_PATH),
        },
        "pricing": _pricing(datetime.now(timezone.utc)),
        "cost_enforcement": {
            "tier": "peak",
            "rates_usd_per_million_tokens": (
                frozen_gf_runner.PEAK_RATES_USD_PER_MILLION
            ),
            "estimated_spend_usd": ledger.estimated_spend_usd,
            "failed_attempt_reserve_usd": ledger.failed_attempt_reserve_usd,
            "hard_cap_usd": MONETARY_CAP_USD,
            "within_hard_cap": ledger.estimated_spend_usd <= MONETARY_CAP_USD,
        },
        "attempt_summary": {
            "api_attempt_count": attempt_count,
            "business_call_count": len(
                {item["business_call_number"] for item in adapter.attempts}
            ),
            "infrastructure_retry_count": max(
                0,
                sum(item["call_kind"] == "initial" for item in adapter.attempts) - 1,
            ),
            "content_repair_or_challenge_count": sum(
                item["call_kind"] == "repair" for item in adapter.attempts
            ),
            "input_tokens": sum(item["input_tokens"] or 0 for item in adapter.attempts),
            "output_tokens": sum(
                item["output_tokens"] or 0 for item in adapter.attempts
            ),
        },
        "attempt_audit": adapter.attempts,
        "fresh_v10_flow": {
            "status": "legal" if fresh_result is not None else "failed",
            "error_type": type(fresh_error).__name__ if fresh_error else None,
            "error_code": getattr(fresh_error, "code", None),
            "repair_triggered": bool(
                fresh_audit is not None and fresh_audit.content_repair_count == 1
            ),
            "validation_errors": (
                list(fresh_audit.validation_errors) if fresh_audit is not None else []
            ),
            "report": fresh_report,
        },
        "direct_repair_v2_challenge": direct_challenge,
        "postgresql_business_write_count": 0,
        "api_key_persisted": False,
        "internal_exception_text_persisted": False,
        "terminal_instruction": (
            "v10/v2 R04 真实验证已停止；不得覆盖结果或自动扩大样本。"
        ),
    }
    _write_json_x(RESULT_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--confirm-real-r04-v10-v2", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    args = parser.parse_args()
    if args.preflight:
        if args.confirm_real_r04_v10_v2 or args.cap_usd is not None:
            raise SystemExit("零调用预检不能同时请求真实调用")
        payload = build_zero_call_preflight()
        seal_zero_call_preflight(payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "contract": payload["contract"],
                    "frozen_replay_error_count": payload["frozen_replay"][
                        "repairable_error_count"
                    ],
                    "cost_gate": payload["cost_gate"],
                    "safety": payload["safety"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if not args.confirm_real_r04_v10_v2 or args.cap_usd != MONETARY_CAP_USD:
        raise SystemExit(
            "真实验证必须使用 --confirm-real-r04-v10-v2 --cap-usd 0.20"
        )
    payload = asyncio.run(run_real())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "attempt_summary": payload["attempt_summary"],
                "fresh_v10_flow": {
                    key: value
                    for key, value in payload["fresh_v10_flow"].items()
                    if key != "report"
                },
                "direct_repair_v2_challenge": {
                    key: value
                    for key, value in payload[
                        "direct_repair_v2_challenge"
                    ].items()
                    if key not in {"report", "validation_errors"}
                },
                "cost_enforcement": payload["cost_enforcement"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
