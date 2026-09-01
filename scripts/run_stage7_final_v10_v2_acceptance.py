from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
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
from app.services.job_evaluation_plan_service import (  # noqa: E402
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationServiceError,
    screening_evaluation_service,
)
from run_stage7_pro_realistic_p3 import (  # noqa: E402
    MODEL,
    REFERENCE_AT,
    REPORT_MAX_OUTPUT_TOKENS,
    _direction_for_score,
    _fingerprint,
    _job,
)
from tests.fixtures.stage7_pro_realistic_quality_samples import (  # noqa: E402
    EXPECTED_NORMALIZED_FINGERPRINT,
    PLAN_JDS,
    REPORT_PAIRS,
    STABILITY_CASE_IDS,
    normalized_fixture_fingerprint,
)


STAGE = "stage7-final-v10-v2-acceptance"
MONETARY_CAP_USD = 2.0
BUSINESS_CALL_COUNT = 35
PER_BUSINESS_API_ATTEMPT_LIMIT = 3
CONTENT_REPAIR_MAXIMUM = 1
PEAK_RATES_USD_PER_MILLION = {
    "cache_hit_input": 0.044,
    "cache_miss_input": 1.32,
    "output": 3.96,
}
OFFICIAL_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing/"
CONFIRMED_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p2-confirmed-plans.json"
)
OLD_P3_RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p3-report-raw-results.json"
)
PREFLIGHT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-final-v10-v2-zero-call-preflight.json"
)
JOURNAL_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-final-v10-v2-attempt-journal.jsonl"
)
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-final-v10-v2-raw-results.json"
)


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


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _schedule() -> list[tuple[str, dict[str, Any], str, int]]:
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    return [
        (f"FINAL-{case_id}", pairs[case_id], "report", 1)
        for case_id in pairs
    ] + [
        (
            f"FINAL-S-{case_id}-{run_number}",
            pairs[case_id],
            "stability",
            run_number,
        )
        for case_id in STABILITY_CASE_IDS
        for run_number in range(1, 4)
    ]


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


def _prepare_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if normalized_fixture_fingerprint() != EXPECTED_NORMALIZED_FINGERPRINT:
        raise RuntimeError("最终验收冻结 fixture 身份已经漂移")
    confirmed = json.loads(CONFIRMED_PATH.read_text(encoding="utf-8"))
    if (
        confirmed.get("status") != "complete"
        or confirmed.get("confirmed_plan_count") != 5
        or not confirmed.get("p3_input_ready")
        or confirmed.get("source_fixture_fingerprint")
        != EXPECTED_NORMALIZED_FINGERPRINT
    ):
        raise RuntimeError("confirmed plans 不满足最终验收输入门禁")
    jobs = {item["case_id"]: item for item in PLAN_JDS}
    plans = {item["case_id"]: item for item in confirmed["plans"]}
    if list(jobs) != list(plans) or len(REPORT_PAIRS) != 20:
        raise RuntimeError("最终验收 5 JD / 20 Resume 映射不完整")
    snapshots: dict[str, Any] = {}
    for index, (case_id, job) in enumerate(jobs.items()):
        item = plans[case_id]
        if (
            item.get("status") != "confirmed"
            or _fingerprint(item["plan"]) != item["snapshot_sha256"]
        ):
            raise RuntimeError(f"{case_id} confirmed snapshot 身份无效")
        snapshots[case_id] = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(job, index)
        )
    for pair in REPORT_PAIRS:
        job_case_id = pair["job_case_id"]
        screening_evaluation_service._prepare_v5_inputs(
            snapshots[job_case_id],
            plans[job_case_id]["plan"],
            pair["resume_text"],
        )
    return confirmed, plans, snapshots


def _main_messages(
    pair: dict[str, Any],
    plans: dict[str, Any],
    snapshots: dict[str, Any],
) -> list[dict[str, str]]:
    job_case_id = pair["job_case_id"]
    return build_screening_evaluation_v5_messages(
        job_snapshot=snapshots[job_case_id].model_dump(mode="json"),
        evaluation_plan=plans[job_case_id]["plan"],
        sanitized_resume=screening_evaluation_service.sanitize_resume_text(
            pair["resume_text"]
        ),
        evaluation_reference_at=REFERENCE_AT.isoformat(),
        evaluation_timezone="Asia/Shanghai",
        experience_period_facts={},
    )


def _reservation_usd(messages: list[dict[str, str]]) -> float:
    input_byte_upper = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
    return (
        input_byte_upper * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
        + REPORT_MAX_OUTPUT_TOKENS * PEAK_RATES_USD_PER_MILLION["output"]
    ) / 1_000_000


def build_zero_call_preflight() -> dict[str, Any]:
    if not OLD_P3_RESULT_PATH.is_file():
        raise RuntimeError("旧 P3 冻结 raw 不存在")
    confirmed, plans, snapshots = _prepare_inputs()
    settings = _zero_key_settings()
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
        raise RuntimeError("最终验收零调用配置与代码合同不一致")
    schedule = _schedule()
    reservations = [
        _reservation_usd(_main_messages(pair, plans, snapshots))
        for _, pair, _, _ in schedule
    ]
    if max(reservations) >= MONETARY_CAP_USD:
        raise RuntimeError("单次主报告调用预留超过最终验收 USD 2 硬上限")
    return {
        "stage": STAGE,
        "mode": "zero_call_preflight",
        "generated_at": _utc_now(),
        "status": "passed",
        "contract": {
            "model": MODEL,
            "main_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "repair_prompt_version": SCREENING_EVALUATION_V5_REPAIR_PROMPT_VERSION,
            "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
            "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "business_call_count": BUSINESS_CALL_COUNT,
            "per_business_api_attempt_limit": PER_BUSINESS_API_ATTEMPT_LIMIT,
            "content_repair_maximum": CONTENT_REPAIR_MAXIMUM,
        },
        "source": {
            "fixture_fingerprint": EXPECTED_NORMALIZED_FINGERPRINT,
            "confirmed_plans_path": _relative(CONFIRMED_PATH),
            "confirmed_plans_structured_sha256": _fingerprint(confirmed),
            "old_p3_path": _relative(OLD_P3_RESULT_PATH),
            "old_p3_sha256": _sha256(OLD_P3_RESULT_PATH),
            "confirmed_plan_snapshot_sha256": {
                case_id: item["snapshot_sha256"] for case_id, item in plans.items()
            },
        },
        "schedule": {
            "base_report_count": 20,
            "stability_report_count": 15,
            "business_call_ids": [item[0] for item in schedule],
        },
        "cost_gate": {
            "hard_cap_usd": MONETARY_CAP_USD,
            "official_pricing_url": OFFICIAL_PRICING_URL,
            "official_pricing_checked_on": "2026-09-01",
            "enforcement_tier": "peak",
            "rates_usd_per_million_tokens": PEAK_RATES_USD_PER_MILLION,
            "scheduled_initial_max_output_reservation_usd": sum(reservations),
            "maximum_single_initial_reservation_usd": max(reservations),
            "historical_p3_observed_peak_estimate_usd": 0.59429568,
            "runtime_cumulative_guard_required": True,
            "note": (
                "静态和按每次 12,000 最大输出预留可能高于总上限；"
                "真实执行按成功 token 结算，并在每个新 attempt 前执行累计 USD 2 守门。"
            ),
        },
        "evidence_paths": {
            "attempt_journal": _relative(JOURNAL_PATH),
            "raw_result": _relative(RESULT_PATH),
            "exclusive_create": True,
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


@dataclass(slots=True)
class PeakCostLedger:
    cap_usd: float
    estimated_spend_usd: float = 0.0
    failed_attempt_reserve_usd: float = 0.0
    active_reservation_usd: float = 0.0

    def reserve(self, messages: list[dict[str, str]]) -> float:
        if self.active_reservation_usd:
            raise RuntimeError("上一 API attempt 的费用预留尚未结算")
        reservation = _reservation_usd(messages)
        if self.estimated_spend_usd + reservation > self.cap_usd:
            raise RuntimeError("下一 API attempt 的 peak 保守上界会超过 USD 2 硬上限")
        self.active_reservation_usd = reservation
        return reservation

    def retain_failed(self) -> float:
        reservation = self.active_reservation_usd
        self.active_reservation_usd = 0.0
        self.estimated_spend_usd += reservation
        self.failed_attempt_reserve_usd += reservation
        return reservation

    def charge(self, result: ScreeningEvaluationAdapterResult) -> float:
        if result.input_tokens is None or result.output_tokens is None:
            self.retain_failed()
            raise RuntimeError("真实 attempt 缺少可审计 token，停止后续调用")
        estimate = (
            result.input_tokens * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
            + result.output_tokens * PEAK_RATES_USD_PER_MILLION["output"]
        ) / 1_000_000
        self.active_reservation_usd = 0.0
        self.estimated_spend_usd += estimate
        if self.estimated_spend_usd > self.cap_usd:
            raise RuntimeError("累计 peak 保守估算费用超过 USD 2 硬上限")
        return estimate


@dataclass(slots=True)
class AttemptRegistry:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, entry: dict[str, Any], *, journal_path: Path) -> None:
        sealed = {"journal_sequence": len(self.entries) + 1, **entry}
        _append_jsonl(journal_path, sealed)
        self.entries.append(sealed)


class JournaledAcceptanceAdapter:
    def __init__(
        self,
        *,
        delegate: DeepSeekScreeningEvaluationAdapter,
        ledger: PeakCostLedger,
        business_call_id: str,
        journal_path: Path,
        registry: AttemptRegistry | None = None,
    ) -> None:
        self.delegate = delegate
        self.ledger = ledger
        self.business_call_id = business_call_id
        self.journal_path = journal_path
        self.registry = registry or AttemptRegistry()
        self.api_attempt_count = 0
        self.repair_call_count = 0
        if not journal_path.exists():
            journal_path.touch(exist_ok=False)

    def _record(self, entry: dict[str, Any]) -> None:
        self.registry.add(entry, journal_path=self.journal_path)

    async def _attempt(
        self,
        *,
        call_kind: str,
        messages: list[dict[str, str]],
        operation: Callable[[], Awaitable[ScreeningEvaluationAdapterResult]],
    ) -> ScreeningEvaluationAdapterResult:
        if self.api_attempt_count >= PER_BUSINESS_API_ATTEMPT_LIMIT:
            raise RuntimeError("单个业务 case 已达到 3 次 API attempt 硬上限")
        self.api_attempt_count += 1
        reservation = self.ledger.reserve(messages)
        started = time.perf_counter()
        try:
            result = await operation()
        except ScreeningEvaluationAdapterError as exc:
            charged = self.ledger.retain_failed()
            self._record(
                {
                    "stage": STAGE,
                    "business_call_id": self.business_call_id,
                    "business_attempt_number": self.api_attempt_count,
                    "call_kind": call_kind,
                    "result": "failed",
                    "sealed_at": _utc_now(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "requested_model": MODEL,
                    "model": None,
                    "finish_reason": None,
                    "error_code": exc.code,
                    "retryable": exc.retryable,
                    "input_tokens": None,
                    "output_tokens": None,
                    "peak_reservation_usd": reservation,
                    "peak_estimated_cost_usd": charged,
                    "raw_response": None,
                    "internal_exception_text_persisted": False,
                }
            )
            raise
        charged = self.ledger.charge(result)
        raw_sha256 = hashlib.sha256(result.content.encode("utf-8")).hexdigest()
        self._record(
            {
                "stage": STAGE,
                "business_call_id": self.business_call_id,
                "business_attempt_number": self.api_attempt_count,
                "call_kind": call_kind,
                "result": "succeeded",
                "sealed_at": _utc_now(),
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "requested_model": MODEL,
                "model": result.model,
                "finish_reason": result.finish_reason,
                "error_code": None,
                "retryable": False,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "peak_reservation_usd": reservation,
                "peak_estimated_cost_usd": charged,
                "raw_response_sha256": raw_sha256,
                "raw_response": result.content,
                "raw_sealed_before_service_validation": True,
            }
        )
        return result

    async def evaluate_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        messages = build_screening_evaluation_v5_messages(**kwargs)
        for infrastructure_try in (1, 2):
            try:
                return await self._attempt(
                    call_kind="initial",
                    messages=messages,
                    operation=lambda: self.delegate.evaluate_v5(**kwargs),
                )
            except ScreeningEvaluationAdapterError as exc:
                if not exc.retryable or infrastructure_try == 2:
                    raise
        raise AssertionError("unreachable")

    async def repair_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        if self.repair_call_count >= CONTENT_REPAIR_MAXIMUM:
            raise RuntimeError("单个业务 case 只允许一次 Repair")
        self.repair_call_count += 1
        messages = build_screening_evaluation_v5_repair_messages(**kwargs)
        return await self._attempt(
            call_kind="repair",
            messages=messages,
            operation=lambda: self.delegate.repair_v5(**kwargs),
        )


async def _run_business_call(
    *,
    business_call_id: str,
    pair: dict[str, Any],
    run_kind: str,
    run_number: int,
    plans: dict[str, Any],
    snapshots: dict[str, Any],
    delegate: DeepSeekScreeningEvaluationAdapter,
    ledger: PeakCostLedger,
    registry: AttemptRegistry,
) -> dict[str, Any]:
    job_case_id = pair["job_case_id"]
    adapter = JournaledAcceptanceAdapter(
        delegate=delegate,
        ledger=ledger,
        business_call_id=business_call_id,
        journal_path=JOURNAL_PATH,
        registry=registry,
    )
    started = time.perf_counter()
    result = None
    error: Exception | None = None
    try:
        result = await screening_evaluation_service.evaluate_v5(
            job_snapshot=snapshots[job_case_id],
            evaluation_plan=plans[job_case_id]["plan"],
            resume_text=pair["resume_text"],
            evaluation_reference_at=REFERENCE_AT,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts={},
            adapter=adapter,
        )
    except (ScreeningEvaluationServiceError, ScreeningEvaluationAdapterError) as exc:
        error = exc
    audit = getattr(result, "audit", None) or getattr(error, "audit", None)
    common = {
        "business_call_id": business_call_id,
        "case_id": pair["case_id"],
        "job_case_id": job_case_id,
        "run_kind": run_kind,
        "run_number": run_number,
        "business_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "adapter_attempt_count": adapter.api_attempt_count,
        "content_repair_count": adapter.repair_call_count,
        "validation_errors": list(audit.validation_errors) if audit else [],
        "confirmed_plan_snapshot_sha256": plans[job_case_id]["snapshot_sha256"],
        "labels": pair["labels"],
    }
    if result is None:
        return {
            **common,
            "status": "failed",
            "error_code": getattr(error, "code", type(error).__name__),
            "error_type": type(error).__name__,
            "report": None,
        }
    report = result.report
    nonzero = [item for item in report.criterion_assessments if item.assessment.score > 0]
    actual_direction = _direction_for_score(report.overall_score)
    low, high = pair["labels"]["score_range"]
    return {
        **common,
        "status": "succeeded",
        "error_code": None,
        "error_type": None,
        "overall_score": report.overall_score,
        "display_label": report.display_label,
        "actual_direction": actual_direction,
        "direction_matches_frozen_label": (
            actual_direction == pair["labels"]["expected_direction"]
        ),
        "score_in_frozen_range": low <= report.overall_score <= high,
        "criterion_assessment_count": len(report.criterion_assessments),
        "nonzero_assessment_count": len(nonzero),
        "nonzero_with_evidence_count": sum(
            bool(item.assessment.evidence) for item in nonzero
        ),
        "section_counts": {
            "strengths": len(report.strengths),
            "gaps": len(report.gaps),
            "risks_or_conflicts": len(report.risks_or_conflicts),
            "missing_info": len(report.missing_info),
            "hr_follow_up_questions": len(report.hr_follow_up_questions),
        },
        "model_version": result.metadata.model_version,
        "prompt_version": result.metadata.prompt_version,
        "schema_version": result.metadata.schema_version,
        "behavior_version": result.behavior_version,
        "report": report.model_dump(mode="json"),
    }


def _stability_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for case_id in STABILITY_CASE_IDS:
        group = [item for item in records if item["case_id"] == case_id]
        legal = [item for item in group if item["status"] == "succeeded"]
        scores = [item["overall_score"] for item in legal]
        directions = [item["actual_direction"] for item in legal]
        summary.append(
            {
                "case_id": case_id,
                "scheduled_run_count": 3,
                "legal_run_count": len(legal),
                "scores": scores,
                "directions": directions,
                "score_spread": max(scores) - min(scores) if len(scores) == 3 else None,
                "direction_stable": len(directions) == 3 and len(set(directions)) == 1,
                "spread_le_10": (
                    len(scores) == 3 and max(scores) - min(scores) <= 10
                ),
            }
        )
    return summary


def _assert_paths_empty() -> None:
    if PREFLIGHT_PATH.exists() or JOURNAL_PATH.exists() or RESULT_PATH.exists():
        raise RuntimeError("最终验收独立证据路径已存在，拒绝覆盖或补跑")


def seal_zero_call_preflight(payload: dict[str, Any]) -> None:
    _write_json_x(PREFLIGHT_PATH, payload)


def _load_preflight() -> dict[str, Any]:
    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("最终验收零调用预检证据不存在")
    payload = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    current = build_zero_call_preflight()
    for section in ("contract", "source", "schedule", "evidence_paths"):
        if payload.get(section) != current.get(section):
            raise RuntimeError(f"最终验收零调用预检 {section} 已漂移")
    return payload


def _assert_real_settings(settings: Settings) -> None:
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("最终验收已获授权，但 DeepSeek API Key 未配置")
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
        raise RuntimeError("真实设置与最终验收 v10/v2/v11/5.0 合同不一致")


async def run_real() -> dict[str, Any]:
    if JOURNAL_PATH.exists() or RESULT_PATH.exists():
        raise RuntimeError("最终验收 raw/journal 已存在，拒绝覆盖或补跑")
    preflight = _load_preflight()
    settings = get_settings()
    _assert_real_settings(settings)
    confirmed, plans, snapshots = _prepare_inputs()
    if _fingerprint(confirmed) != preflight["source"][
        "confirmed_plans_structured_sha256"
    ]:
        raise RuntimeError("最终验收 confirmed plans 身份已漂移")
    JOURNAL_PATH.touch(exist_ok=False)
    ledger = PeakCostLedger(cap_usd=MONETARY_CAP_USD)
    registry = AttemptRegistry()
    delegate = DeepSeekScreeningEvaluationAdapter(settings=settings)
    report_records: list[dict[str, Any]] = []
    stability_records: list[dict[str, Any]] = []
    fatal_error: dict[str, str] | None = None
    status = "completed"
    schedule = _schedule()
    try:
        for index, (business_call_id, pair, run_kind, run_number) in enumerate(
            schedule, 1
        ):
            record = await _run_business_call(
                business_call_id=business_call_id,
                pair=pair,
                run_kind=run_kind,
                run_number=run_number,
                plans=plans,
                snapshots=snapshots,
                delegate=delegate,
                ledger=ledger,
                registry=registry,
            )
            target = report_records if run_kind == "report" else stability_records
            target.append(record)
            detail = (
                f"score={record['overall_score']} direction={record['actual_direction']}"
                if record["status"] == "succeeded"
                else f"error={record['error_code']}"
            )
            print(
                f"[{index:02d}/35] {business_call_id} {record['status']} {detail} "
                f"repair={record['content_repair_count']} "
                f"cost=${ledger.estimated_spend_usd:.6f}",
                flush=True,
            )
    except Exception as exc:
        status = "stopped_partial"
        fatal_error = {"type": type(exc).__name__, "message": str(exc)}
        print(f"final acceptance stopped: {fatal_error}", flush=True)

    successful_reports = [
        item for item in report_records if item["status"] == "succeeded"
    ]
    successful_attempts = [
        item for item in registry.entries if item["result"] == "succeeded"
    ]
    attempt_audit = [
        {key: value for key, value in item.items() if key != "raw_response"}
        for item in registry.entries
    ]
    payload = {
        "stage": STAGE,
        "batch": "FINAL-V10-V2",
        "mode": "real_report_raw_pending_human_audit",
        "generated_at": _utc_now(),
        "status": status,
        "fatal_error": fatal_error,
        "authorization": {
            "authorized_by": "project_owner_user",
            "user_directive": "可以",
            "authorized_business_call_count": BUSINESS_CALL_COUNT,
            "monetary_cap_usd": MONETARY_CAP_USD,
        },
        "execution_contract": preflight["contract"],
        "source": preflight["source"],
        "preflight": {
            "path": _relative(PREFLIGHT_PATH),
            "sha256": _sha256(PREFLIGHT_PATH),
        },
        "attempt_journal": {
            "path": _relative(JOURNAL_PATH),
            "sha256": _sha256(JOURNAL_PATH),
            "line_count": len(registry.entries),
            "raw_sealed_before_service_validation": True,
        },
        "cost_enforcement": {
            "tier": "peak",
            "rates_usd_per_million_tokens": PEAK_RATES_USD_PER_MILLION,
            "estimated_spend_usd": ledger.estimated_spend_usd,
            "failed_attempt_reserve_usd": ledger.failed_attempt_reserve_usd,
            "hard_cap_usd": MONETARY_CAP_USD,
            "within_hard_cap": ledger.estimated_spend_usd <= MONETARY_CAP_USD,
        },
        "attempt_summary": {
            "scheduled_business_call_count": BUSINESS_CALL_COUNT,
            "executed_business_call_count": len(report_records)
            + len(stability_records),
            "api_attempt_count": len(registry.entries),
            "succeeded_attempt_count": len(successful_attempts),
            "failed_attempt_count": len(registry.entries)
            - len(successful_attempts),
            "infrastructure_retry_count": sum(
                item["call_kind"] == "initial"
                and item["business_attempt_number"] == 2
                for item in registry.entries
            ),
            "content_repair_count": sum(
                item["call_kind"] == "repair" for item in registry.entries
            ),
            "input_tokens": sum(
                item["input_tokens"] or 0 for item in successful_attempts
            ),
            "output_tokens": sum(
                item["output_tokens"] or 0 for item in successful_attempts
            ),
        },
        "report_summary": {
            "scheduled_count": 20,
            "legal_count": len(successful_reports),
            "failed_count": len(report_records) - len(successful_reports),
            "direction_match_count": sum(
                item["direction_matches_frozen_label"] for item in successful_reports
            ),
            "score_in_frozen_range_count": sum(
                item["score_in_frozen_range"] for item in successful_reports
            ),
            "repair_triggered_count": sum(
                item["content_repair_count"] for item in report_records
            ),
        },
        "stability_summary": _stability_summary(stability_records),
        "reports": report_records,
        "stability_runs": stability_records,
        "attempt_audit": attempt_audit,
        "quality_gate_passed": None,
        "quality_conclusion_allowed": False,
        "requires_human_audit": True,
        "postgresql_write_count": 0,
        "api_key_persisted": False,
        "next_step": (
            "停止真实调用；完成自动回归后交由用户人工审核事实、证据、方向和分数。"
        ),
    }
    _write_json_x(RESULT_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--confirm-final-v10-v2", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    args = parser.parse_args()
    if args.preflight:
        if args.confirm_final_v10_v2 or args.cap_usd is not None:
            raise SystemExit("零调用预检不能同时执行真实调用")
        _assert_paths_empty()
        payload = build_zero_call_preflight()
        seal_zero_call_preflight(payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "contract": payload["contract"],
                    "schedule": payload["schedule"],
                    "cost_gate": payload["cost_gate"],
                    "safety": payload["safety"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if not args.confirm_final_v10_v2 or args.cap_usd != MONETARY_CAP_USD:
        raise SystemExit(
            "最终验收必须使用 --confirm-final-v10-v2 --cap-usd 2.0"
        )
    payload = asyncio.run(run_real())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "attempt_summary": payload["attempt_summary"],
                "report_summary": payload["report_summary"],
                "stability_summary": payload["stability_summary"],
                "cost_enforcement": payload["cost_enforcement"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
