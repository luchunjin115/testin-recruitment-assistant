from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    build_screening_evaluation_v5_messages,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    AIScreeningEvaluationV5Output,
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    ScreeningEvaluationPlanInputV5,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationInvalidOutputError,
    screening_evaluation_service,
)
from run_stage7_p5r_evidence_retest import (  # noqa: E402
    MODEL,
    PEAK_RATES_USD_PER_MILLION,
    REFERENCE_AT,
    REPORT_MAX_OUTPUT_TOKENS,
    _build_frozen_inputs,
    _pricing,
)
from run_stage7_pro_realistic_p3 import CostGuard  # noqa: E402
from tests.fixtures.stage7_pro_realistic_quality_samples import (  # noqa: E402
    REPORT_PAIRS,
)


MONETARY_CAP_USD = 0.10
CASE_ID = "R04"
BUSINESS_CALL_ID = "P5R-F-R04"
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-f-r04-diagnostic-raw-results.json"
)
ATTEMPT_PATHS = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-f-r04-attempt-01.json",
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-f-r04-attempt-02.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_x(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _r04_inputs() -> dict[str, Any]:
    confirmed, plans, snapshots = _build_frozen_inputs()
    pair = next(item for item in REPORT_PAIRS if item["case_id"] == CASE_ID)
    job_case_id = pair["job_case_id"]
    sanitized_resume = screening_evaluation_service.sanitize_resume_text(
        pair["resume_text"]
    )
    snapshot = snapshots[job_case_id]
    plan = plans[job_case_id]["plan"]
    screening_evaluation_service._prepare_v5_inputs(
        snapshot, plan, pair["resume_text"]
    )
    return {
        "confirmed": confirmed,
        "pair": pair,
        "job_case_id": job_case_id,
        "snapshot": snapshot,
        "plan": plan,
        "sanitized_resume": sanitized_resume,
    }


def _adapter_kwargs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_snapshot": inputs["snapshot"].model_dump(mode="json"),
        "evaluation_plan": inputs["plan"],
        "sanitized_resume": inputs["sanitized_resume"],
        "evaluation_reference_at": REFERENCE_AT.isoformat(),
        "evaluation_timezone": "Asia/Shanghai",
        "experience_period_facts": {},
    }


def peak_cost_upper_bound_usd(inputs: dict[str, Any]) -> float:
    messages = build_screening_evaluation_v5_messages(**_adapter_kwargs(inputs))
    input_upper = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
    return (
        input_upper * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
        + REPORT_MAX_OUTPUT_TOKENS * PEAK_RATES_USD_PER_MILLION["output"]
    ) / 1_000_000


def offline_preflight() -> dict[str, Any]:
    if RESULT_PATH.exists() or any(path.exists() for path in ATTEMPT_PATHS):
        raise RuntimeError("P5R-F 独立结果或 attempt 路径已存在，拒绝覆盖或补跑")
    inputs = _r04_inputs()
    settings = Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="",
        SCREENING_EVALUATION_MODEL=MODEL,
        SCREENING_EVALUATION_V5_PROMPT_VERSION=(
            SCREENING_EVALUATION_V5_PROMPT_VERSION
        ),
        SCREENING_EVALUATION_V5_SCHEMA_VERSION=(
            SCREENING_EVALUATION_V5_SCHEMA_VERSION
        ),
        SCREENING_EVALUATION_MAX_OUTPUT_TOKENS=REPORT_MAX_OUTPUT_TOKENS,
    )
    if (
        settings.SCREENING_EVALUATION_MODEL != MODEL
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
        != SCREENING_EVALUATION_V5_SCHEMA_VERSION
    ):
        raise RuntimeError("P5R-F 当前配置与冻结合同不一致")
    upper = peak_cost_upper_bound_usd(inputs)
    if upper > MONETARY_CAP_USD:
        raise RuntimeError("P5R-F peak 单次保守上界超过 USD 0.10")
    return {"inputs": inputs, "peak_cost_upper_bound_usd": upper}


def diagnose_raw_response(
    content: str,
    *,
    evaluation_plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        payload = json.loads(
            content,
            object_pairs_hook=screening_evaluation_service._unique_json_object,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "layer": "json",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    try:
        output = AIScreeningEvaluationV5Output.model_validate(payload)
        plan = ScreeningEvaluationPlanInputV5.model_validate(evaluation_plan)
    except ValidationError as exc:
        return {
            "layer": "schema",
            "error_type": "ValidationError",
            "errors": exc.errors(include_url=False, include_context=False),
        }
    checks = (
        (
            "criterion_cross_reference",
            lambda: screening_evaluation_service.validate_v5_criterion_cross_reference(
                output, plan
            ),
        ),
        (
            "compatibility_time_fields",
            lambda: [
                screening_evaluation_service._validate_v5_compatibility_time_fields(
                    item
                )
                for item in output.criterion_assessments
            ],
        ),
        (
            "findings",
            lambda: screening_evaluation_service._validate_v5_findings(output, plan),
        ),
        ("safety", lambda: screening_evaluation_service._validate_v5_safety(output)),
    )
    for layer, check in checks:
        try:
            check()
        except ScreeningEvaluationInvalidOutputError as exc:
            return {
                "layer": layer,
                "error_type": type(exc).__name__,
                "error_code": exc.code,
                "message": str(exc),
            }
    return {"layer": "none", "message": "原始响应通过全部 Schema/Service 检查"}


async def run() -> dict[str, Any]:
    preflight = offline_preflight()
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("P5R-F 已获金额授权，但 DeepSeek API Key 未配置")
    if (
        settings.SCREENING_EVALUATION_MODEL != MODEL
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
    ):
        raise RuntimeError("P5R-F 真实设置与当前合同不一致")

    inputs = preflight["inputs"]
    kwargs = _adapter_kwargs(inputs)
    messages = build_screening_evaluation_v5_messages(**kwargs)
    pricing = _pricing(datetime.now(timezone.utc))
    guard = CostGuard(pricing=pricing, cap_usd=MONETARY_CAP_USD)
    adapter = DeepSeekScreeningEvaluationAdapter(settings=settings)
    attempts: list[dict[str, Any]] = []
    adapter_result = None

    for attempt_number in (1, 2):
        reservation = guard.reserve(messages)
        started = time.perf_counter()
        try:
            result = await adapter.evaluate_v5(**kwargs)
        except ScreeningEvaluationAdapterError as exc:
            reserved = guard.retain_failed_reservation()
            attempt = {
                "business_call_id": BUSINESS_CALL_ID,
                "attempt_number": attempt_number,
                "result": "failed",
                "error_code": exc.code,
                "retryable": exc.retryable,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "requested_model": MODEL,
                "raw_response": None,
                "reserved_cost_upper_bound_usd": reserved,
            }
            _write_json_x(ATTEMPT_PATHS[attempt_number - 1], attempt)
            attempt["journal_path"] = str(
                ATTEMPT_PATHS[attempt_number - 1].relative_to(PROJECT_ROOT)
            ).replace("\\", "/")
            attempt["journal_sha256"] = _sha256(ATTEMPT_PATHS[attempt_number - 1])
            attempts.append(attempt)
            if exc.retryable and attempt_number == 1:
                continue
            break

        estimate = guard.charge(result)
        attempt = {
            "business_call_id": BUSINESS_CALL_ID,
            "attempt_number": attempt_number,
            "result": "succeeded",
            "error_code": None,
            "retryable": False,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "requested_model": MODEL,
            "model": result.model,
            "finish_reason": result.finish_reason,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_estimate": estimate,
            "reservation_before_call_usd": reservation,
            "raw_response": result.content,
        }
        _write_json_x(ATTEMPT_PATHS[attempt_number - 1], attempt)
        attempt["journal_path"] = str(
            ATTEMPT_PATHS[attempt_number - 1].relative_to(PROJECT_ROOT)
        ).replace("\\", "/")
        attempt["journal_sha256"] = _sha256(ATTEMPT_PATHS[attempt_number - 1])
        attempts.append(attempt)
        adapter_result = result
        break

    service_status = "not_run"
    service_error: dict[str, Any] | None = None
    diagnosis: dict[str, Any] | None = None
    report = None
    if adapter_result is not None:
        try:
            parsed = screening_evaluation_service.parse_and_validate_v5_output(
                adapter_result.content,
                evaluation_plan=inputs["plan"],
                sanitized_resume=inputs["sanitized_resume"],
            )
        except ScreeningEvaluationInvalidOutputError as exc:
            service_status = "rejected"
            service_error = {
                "error_code": exc.code,
                "message": str(exc),
            }
            diagnosis = diagnose_raw_response(
                adapter_result.content,
                evaluation_plan=inputs["plan"],
            )
        else:
            service_status = "legal"
            diagnosis = {"layer": "none", "message": "报告通过当前 Service"}
            report = parsed.model_dump(mode="json")

    payload = {
        "stage": "stage7-p5r-r04-diagnostic",
        "batch": "P5R-F",
        "mode": "single_real_raw_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if adapter_result is not None else "adapter_failed",
        "authorization": {
            "user_directive": "费用上限 USD 0.10",
            "monetary_cap_usd": MONETARY_CAP_USD,
        },
        "execution_contract": {
            "business_call_id": BUSINESS_CALL_ID,
            "source_case_id": CASE_ID,
            "model": MODEL,
            "prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
            "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "content_error_retry_count": 0,
            "infrastructure_retry_maximum": 1,
            "api_attempt_limit": 2,
        },
        "pricing": pricing,
        "peak_cost_upper_bound_usd": preflight["peak_cost_upper_bound_usd"],
        "attempt_summary": {
            "api_attempt_count": len(attempts),
            "infrastructure_retry_count": sum(
                item["attempt_number"] == 2 for item in attempts
            ),
            "estimated_spend_usd": guard.estimated_spend_usd,
        },
        "attempt_audit": attempts,
        "service_status": service_status,
        "service_error": service_error,
        "diagnosis": diagnosis,
        "report": report,
        "postgresql_write_count": 0,
        "api_key_persisted": False,
        "next_step": "停止并向用户报告 R04 结果；不得在本批修改生产规则或继续调用。",
    }
    _write_json_x(RESULT_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-p5r-f", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    args = parser.parse_args()
    if not args.confirm_p5r_f or args.cap_usd != MONETARY_CAP_USD:
        raise SystemExit("P5R-F 必须使用 --confirm-p5r-f --cap-usd 0.10")
    payload = asyncio.run(run())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "service_status": payload["service_status"],
                "diagnosis": payload["diagnosis"],
                "attempt_summary": payload["attempt_summary"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
