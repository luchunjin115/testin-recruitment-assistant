from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
    ScreeningEvaluationAdapterResult,
)
from app.core.config import get_settings  # noqa: E402
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
from app.services.screening_evaluation_service import screening_evaluation_service  # noqa: E402
from run_stage7_p5r_evidence_retest import (  # noqa: E402
    MODEL,
    REFERENCE_AT,
    REPORT_MAX_OUTPUT_TOKENS,
    _pricing,
)
from run_stage7_p5r_f_r04_diagnostic import _r04_inputs  # noqa: E402


CASE_ID = "R04"
BUSINESS_CALL_ID = "P5R-GF-R04"
MONETARY_CAP_USD = 0.20
BUSINESS_CALL_MAXIMUM = 2
API_ATTEMPT_LIMIT = 3
PEAK_RATES_USD_PER_MILLION = {
    "cache_hit_input": 0.044,
    "cache_miss_input": 1.32,
    "output": 3.96,
}
GE_EVIDENCE_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-ge-zero-call-preflight.json"
)
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-gf-r04-repair-results.json"
)
ATTEMPT_PATHS = tuple(
    PROJECT_ROOT
    / f"docs/stages/stage7/2026-09-01-stage7-p5r-gf-r04-attempt-{number:02d}.json"
    for number in range(1, API_ATTEMPT_LIMIT + 1)
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    try:
        display_path = path.relative_to(PROJECT_ROOT)
    except ValueError:
        display_path = path
    return str(display_path).replace("\\", "/")


def _write_json_x(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _adapter_kwargs(inputs: dict[str, Any]) -> dict[str, Any]:
    snapshot = inputs["snapshot"]
    plan = inputs["plan"]
    return {
        "job_snapshot": (
            snapshot.model_dump(mode="json")
            if hasattr(snapshot, "model_dump")
            else snapshot
        ),
        "evaluation_plan": (
            plan.model_dump(mode="json") if hasattr(plan, "model_dump") else plan
        ),
        "sanitized_resume": inputs["sanitized_resume"],
        "evaluation_reference_at": "",
        "evaluation_timezone": "",
        "experience_period_facts": {},
    }


def _message_input_byte_upper(messages: list[dict[str, str]]) -> int:
    return len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))


def _reservation_usd(messages: list[dict[str, str]]) -> float:
    return (
        _message_input_byte_upper(messages)
        * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
        + REPORT_MAX_OUTPUT_TOKENS * PEAK_RATES_USD_PER_MILLION["output"]
    ) / 1_000_000


def _actual_peak_estimate_usd(result: ScreeningEvaluationAdapterResult) -> float | None:
    if result.input_tokens is None or result.output_tokens is None:
        return None
    return (
        result.input_tokens * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
        + result.output_tokens * PEAK_RATES_USD_PER_MILLION["output"]
    ) / 1_000_000


@dataclass(slots=True)
class CostLedger:
    cap_usd: float
    estimated_spend_usd: float = 0.0
    failed_attempt_reserve_usd: float = 0.0

    def reserve(self, messages: list[dict[str, str]]) -> float:
        reservation = _reservation_usd(messages)
        if self.estimated_spend_usd + reservation > self.cap_usd:
            raise RuntimeError("下一 API attempt 的 peak 保守费用上界会超过 P5R-GF USD 0.20 硬上限")
        return reservation

    def retain_failed(self, reservation: float) -> None:
        self.estimated_spend_usd += reservation
        self.failed_attempt_reserve_usd += reservation

    def charge_success(
        self,
        result: ScreeningEvaluationAdapterResult,
        reservation: float,
    ) -> float:
        estimate = _actual_peak_estimate_usd(result)
        charged = reservation if estimate is None else estimate
        self.estimated_spend_usd += charged
        if self.estimated_spend_usd > self.cap_usd:
            raise RuntimeError("P5R-GF 累计 peak 保守估算费用超过 USD 0.20 硬上限")
        return charged


class JournaledGFAdapter:
    """GF-only wrapper: seal each provider response before Service can parse it."""

    def __init__(
        self,
        *,
        delegate: DeepSeekScreeningEvaluationAdapter,
        ledger: CostLedger,
    ) -> None:
        self.delegate = delegate
        self.ledger = ledger
        self.attempts: list[dict[str, Any]] = []

    async def _attempt(
        self,
        *,
        call_kind: str,
        business_call_number: int,
        messages: list[dict[str, str]],
        operation: Callable[[], Awaitable[ScreeningEvaluationAdapterResult]],
    ) -> ScreeningEvaluationAdapterResult:
        attempt_number = len(self.attempts) + 1
        if attempt_number > API_ATTEMPT_LIMIT:
            raise RuntimeError("P5R-GF API attempt 已达到 3 次硬上限")
        reservation = self.ledger.reserve(messages)
        started = time.perf_counter()
        try:
            result = await operation()
        except ScreeningEvaluationAdapterError as exc:
            self.ledger.retain_failed(reservation)
            journal = {
                "stage": "stage7-p5r-gf",
                "business_call_id": BUSINESS_CALL_ID,
                "source_case_id": CASE_ID,
                "attempt_number": attempt_number,
                "business_call_number": business_call_number,
                "call_kind": call_kind,
                "result": "failed",
                "sealed_at": _utc_now(),
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "requested_model": MODEL,
                "error_code": exc.code,
                "retryable": exc.retryable,
                "raw_response": None,
                "input_tokens": None,
                "output_tokens": None,
                "peak_reservation_usd": reservation,
                "peak_estimated_cost_usd": reservation,
                "internal_exception_text_persisted": False,
            }
            self._seal(attempt_number, journal)
            raise

        charged = self.ledger.charge_success(result, reservation)
        journal = {
            "stage": "stage7-p5r-gf",
            "business_call_id": BUSINESS_CALL_ID,
            "source_case_id": CASE_ID,
            "attempt_number": attempt_number,
            "business_call_number": business_call_number,
            "call_kind": call_kind,
            "result": "succeeded",
            "sealed_at": _utc_now(),
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "requested_model": MODEL,
            "model": result.model,
            "finish_reason": result.finish_reason,
            "error_code": None,
            "retryable": False,
            "raw_response": result.content,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "peak_reservation_usd": reservation,
            "peak_estimated_cost_usd": charged,
            "raw_sealed_before_service_validation": True,
        }
        self._seal(attempt_number, journal)
        return result

    def _seal(self, attempt_number: int, journal: dict[str, Any]) -> None:
        path = ATTEMPT_PATHS[attempt_number - 1]
        _write_json_x(path, journal)
        journal["journal_path"] = _relative(path)
        journal["journal_sha256"] = _sha256(path)
        self.attempts.append(journal)

    async def evaluate_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        messages = build_screening_evaluation_v5_messages(**kwargs)
        for infrastructure_try in (1, 2):
            try:
                return await self._attempt(
                    call_kind="initial",
                    business_call_number=1,
                    messages=messages,
                    operation=lambda: self.delegate.evaluate_v5(**kwargs),
                )
            except ScreeningEvaluationAdapterError as exc:
                if not exc.retryable or infrastructure_try == 2:
                    raise
        raise AssertionError("unreachable")

    async def repair_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        messages = build_screening_evaluation_v5_repair_messages(**kwargs)
        return await self._attempt(
            call_kind="repair",
            business_call_number=2,
            messages=messages,
            operation=lambda: self.delegate.repair_v5(**kwargs),
        )


def offline_preflight() -> dict[str, Any]:
    if RESULT_PATH.exists() or any(path.exists() for path in ATTEMPT_PATHS):
        raise RuntimeError("P5R-GF 独立结果或 attempt 路径已存在，拒绝覆盖或补跑")
    ge = json.loads(GE_EVIDENCE_PATH.read_text(encoding="utf-8"))
    if ge.get("status") != "passed_with_preexisting_full_suite_failures":
        raise RuntimeError("P5R-GE 零调用全链预检证据未通过")
    expected_contract = {
        "model": MODEL,
        "main_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "repair_prompt_version": SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION,
        "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
        "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    }
    for key, expected in expected_contract.items():
        if ge.get("contract", {}).get(key) != expected:
            raise RuntimeError(f"P5R-GE 合同字段 {key} 已漂移")
    inputs = _r04_inputs()
    initial_messages = build_screening_evaluation_v5_messages(
        **_adapter_kwargs(inputs)
    )
    ge_upper = ge.get("gf_peak_upper_bound", {}).get("peak_cost_upper_bound_usd")
    if not isinstance(ge_upper, (int, float)) or ge_upper > MONETARY_CAP_USD:
        raise RuntimeError("P5R-GF 两个业务调用的 peak 上界超过 USD 0.20")
    return {
        "inputs": inputs,
        "ge_sha256": _sha256(GE_EVIDENCE_PATH),
        "initial_peak_reservation_usd": _reservation_usd(initial_messages),
        "two_business_call_peak_upper_bound_usd": ge_upper,
    }


def _repair_choice(
    report: dict[str, Any] | None,
    validation_errors: list[dict[str, str]],
) -> dict[str, Any]:
    affected_indexes: set[int] = set()
    for error in validation_errors:
        path = error.get("path", "")
        parts = path.strip("$").strip(".").split(".")
        if len(parts) >= 2 and parts[0] == "criterion_assessments":
            try:
                affected_indexes.add(int(parts[1]))
            except ValueError:
                pass
    if report is None or not affected_indexes:
        return {"classification": "not_applicable", "assessments": []}
    assessments = report.get("criterion_assessments", [])
    choices: list[dict[str, Any]] = []
    for index in sorted(affected_indexes):
        if index >= len(assessments):
            continue
        assessment = assessments[index]
        score = assessment.get("assessment", assessment).get("score")
        evidence = assessment.get("assessment", assessment).get("evidence", [])
        choices.append(
            {
                "index": index,
                "criterion_id": assessment.get("criterion", {}).get(
                    "criterion_id", assessment.get("criterion_id")
                ),
                "score": score,
                "evidence_count": len(evidence),
                "choice": "zero" if score == 0 else "positive_with_evidence",
            }
        )
    classifications = {item["choice"] for item in choices}
    classification = (
        next(iter(classifications)) if len(classifications) == 1 else "mixed"
    )
    return {"classification": classification, "assessments": choices}


async def run() -> dict[str, Any]:
    preflight = offline_preflight()
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("P5R-GF 已获金额授权，但 DeepSeek API Key 未配置")
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
        raise RuntimeError("P5R-GF 真实设置与冻结 v9/v11/Repair v1/Schema 5.0 合同不一致")

    inputs = preflight["inputs"]
    ledger = CostLedger(cap_usd=MONETARY_CAP_USD)
    adapter = JournaledGFAdapter(
        delegate=DeepSeekScreeningEvaluationAdapter(settings=settings),
        ledger=ledger,
    )
    result = None
    error: Exception | None = None
    try:
        result = await screening_evaluation_service.evaluate_v5(
            job_snapshot=inputs["snapshot"],
            evaluation_plan=inputs["plan"],
            resume_text=inputs["pair"]["resume_text"],
            evaluation_reference_at=REFERENCE_AT,
            evaluation_timezone="Asia/Shanghai",
            adapter=adapter,
            settings=settings,
        )
    except Exception as exc:  # GF must seal a terminal result for every outcome.
        error = exc

    audit = getattr(result, "audit", None) or getattr(error, "audit", None)
    report = result.report.model_dump(mode="json") if result is not None else None
    validation_errors = list(audit.validation_errors) if audit is not None else []
    pricing = _pricing(datetime.now(timezone.utc))
    payload = {
        "stage": "stage7-p5r-gf",
        "batch": "P5R-GF",
        "mode": "fixed_r04_single_repair_real_validation",
        "generated_at": _utc_now(),
        "status": "passed" if result is not None else "failed",
        "authorization": {
            "user_directive": "授权 P5R-GF，费用硬上限 USD 0.20",
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
            "initial_infrastructure_retry_maximum": 1,
            "repair_infrastructure_retry_maximum": 0,
            "api_attempt_limit": API_ATTEMPT_LIMIT,
            "postgresql_writes_allowed": False,
        },
        "preflight": {
            "ge_evidence_path": _relative(GE_EVIDENCE_PATH),
            "ge_sha256": preflight["ge_sha256"],
            "initial_peak_reservation_usd": preflight[
                "initial_peak_reservation_usd"
            ],
            "two_business_call_peak_upper_bound_usd": preflight[
                "two_business_call_peak_upper_bound_usd"
            ],
        },
        "pricing": pricing,
        "cost_enforcement": {
            "tier": "peak",
            "rates_usd_per_million_tokens": PEAK_RATES_USD_PER_MILLION,
            "estimated_spend_usd": ledger.estimated_spend_usd,
            "failed_attempt_reserve_usd": ledger.failed_attempt_reserve_usd,
            "within_hard_cap": ledger.estimated_spend_usd <= MONETARY_CAP_USD,
        },
        "attempt_summary": {
            "api_attempt_count": len(adapter.attempts),
            "business_call_count": (
                audit.business_call_count
                if audit is not None
                else len({item["business_call_number"] for item in adapter.attempts})
            ),
            "infrastructure_retry_count": max(
                0,
                sum(item["call_kind"] == "initial" for item in adapter.attempts) - 1,
            ),
            "content_repair_count": (
                audit.content_repair_count
                if audit is not None
                else sum(item["call_kind"] == "repair" for item in adapter.attempts)
            ),
            "input_tokens": sum(
                item["input_tokens"] or 0 for item in adapter.attempts
            ),
            "output_tokens": sum(
                item["output_tokens"] or 0 for item in adapter.attempts
            ),
        },
        "attempt_audit": adapter.attempts,
        "repair": {
            "triggered": any(item["call_kind"] == "repair" for item in adapter.attempts),
            "validation_errors": validation_errors,
            "model_choice_for_initially_invalid_assessments": _repair_choice(
                report, validation_errors
            ),
            "complete_report_returned": report is not None,
            "full_json_schema_service_revalidation_passed": result is not None,
        },
        "service": {
            "status": "legal" if result is not None else "rejected_or_not_reached",
            "error_type": type(error).__name__ if error is not None else None,
            "error_code": getattr(error, "code", None),
            "internal_exception_text_persisted": False,
        },
        "report": report,
        "postgresql_business_write_count": 0,
        "api_key_persisted": False,
        "terminal_instruction": (
            "P5R-GF 已停止；不扩大样本，不修改生产规则，等待用户决定后续工作。"
        ),
    }
    _write_json_x(RESULT_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-p5r-gf", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    args = parser.parse_args()
    if not args.confirm_p5r_gf or args.cap_usd != MONETARY_CAP_USD:
        raise SystemExit("P5R-GF 必须使用 --confirm-p5r-gf --cap-usd 0.20")
    payload = asyncio.run(run())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "attempt_summary": payload["attempt_summary"],
                "repair": payload["repair"],
                "service": payload["service"],
                "cost_enforcement": payload["cost_enforcement"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
