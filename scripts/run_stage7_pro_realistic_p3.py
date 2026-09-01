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
from types import SimpleNamespace
from typing import Any


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
    build_screening_evaluation_v5_messages,
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
from stage7_7r5_quality_contract import estimate_attempt_cost_usd  # noqa: E402
from tests.fixtures.stage7_pro_realistic_quality_samples import (  # noqa: E402
    EXPECTED_NORMALIZED_FINGERPRINT,
    PLAN_JDS,
    REPORT_PAIRS,
    STABILITY_CASE_IDS,
    normalized_fixture_fingerprint,
)


MODEL = "deepseek-v4-pro"
MONETARY_CAP_USD = 2.0
REPORT_MAX_OUTPUT_TOKENS = 12_000
AUTHORIZATION_DIRECTIVE = "确认开始 P3"
REFERENCE_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
CONFIRMED_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p2-confirmed-plans.json"
)
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p3-report-raw-results.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pricing(now: datetime) -> dict[str, Any]:
    peak = now.weekday() < 5 and (1 <= now.hour < 4 or 6 <= now.hour < 10)
    selected_tier = "peak" if peak else "off_peak"
    tiers = {
        "off_peak": {
            "cache_hit_input": 0.022,
            "cache_miss_input": 0.66,
            "output": 1.98,
        },
        "peak": {
            "cache_hit_input": 0.044,
            "cache_miss_input": 1.32,
            "output": 3.96,
        },
    }
    return {
        "source": "https://api-docs.deepseek.com/quick_start/pricing/",
        "verified_at": now.isoformat(),
        "official_model": MODEL,
        "official_version": "DeepSeek-V4-Pro-0813",
        "selected_tier": selected_tier,
        "selection_rule": "peak on Monday-Friday UTC 01:00-04:00 and 06:00-10:00",
        "usd_per_million_tokens": tiers[selected_tier],
        "all_tiers": tiers,
    }


def _job(job: dict[str, Any], index: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=97_000 + index,
        title=job["title"],
        department=job["department"],
        job_background=job["job_background"],
        job_responsibilities=job["job_responsibilities"],
        candidate_requirements=job["candidate_requirements"],
        preferred_qualifications=job["preferred_qualifications"],
        public_notes=job["public_notes"],
        status="open",
    )


def _direction_for_score(score: int) -> str:
    return "high_match" if score >= 70 else "partial_match" if score >= 40 else "low_match"


@dataclass
class CostGuard:
    pricing: dict[str, Any]
    cap_usd: float
    estimated_spend_usd: float = 0.0
    failed_attempt_reserve_usd: float = 0.0
    active_reservation_usd: float = 0.0

    def reserve(self, messages: Any) -> float:
        if self.active_reservation_usd:
            raise RuntimeError("上一 API attempt 的费用预留尚未结算")
        rates = self.pricing["usd_per_million_tokens"]
        input_upper = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
        ceiling = (
            input_upper * rates["cache_miss_input"]
            + REPORT_MAX_OUTPUT_TOKENS * rates["output"]
        ) / 1_000_000
        if self.estimated_spend_usd + ceiling > self.cap_usd:
            raise RuntimeError("下一次调用的保守费用上界会超过 USD 2 硬上限")
        self.active_reservation_usd = ceiling
        return ceiling

    def retain_failed_reservation(self) -> float:
        ceiling = self.active_reservation_usd
        self.active_reservation_usd = 0.0
        self.estimated_spend_usd += ceiling
        self.failed_attempt_reserve_usd += ceiling
        return ceiling

    def charge(self, result: ScreeningEvaluationAdapterResult) -> dict[str, Any]:
        estimate = estimate_attempt_cost_usd(
            pricing=self.pricing,
            input_tokens=result.input_tokens,
            cache_hit_input_tokens=None,
            cache_miss_input_tokens=None,
            output_tokens=result.output_tokens,
        )
        if not estimate["complete"]:
            self.retain_failed_reservation()
            raise RuntimeError("真实 attempt 缺少可审计 token，停止后续调用")
        self.active_reservation_usd = 0.0
        self.estimated_spend_usd += estimate["estimated_cost_usd"]
        if self.estimated_spend_usd > self.cap_usd:
            raise RuntimeError("累计估算费用超过 USD 2 硬上限")
        return estimate


class AuditedReportAdapter:
    def __init__(
        self,
        delegate: DeepSeekScreeningEvaluationAdapter,
        attempts: list[dict[str, Any]],
        guard: CostGuard,
        business_call_id: str,
    ) -> None:
        self.delegate = delegate
        self.attempts = attempts
        self.guard = guard
        self.business_call_id = business_call_id

    async def evaluate_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        messages = build_screening_evaluation_v5_messages(**kwargs)
        for attempt_number in (1, 2):
            self.guard.reserve(messages)
            started = time.perf_counter()
            try:
                result = await self.delegate.evaluate_v5(**kwargs)
            except ScreeningEvaluationAdapterError as exc:
                reserve = self.guard.retain_failed_reservation()
                self.attempts.append(
                    {
                        "business_call_id": self.business_call_id,
                        "attempt_number": attempt_number,
                        "result": "failed",
                        "error_code": exc.code,
                        "retryable": exc.retryable,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                        "requested_model": MODEL,
                        "model": None,
                        "finish_reason": None,
                        "input_tokens": None,
                        "cache_hit_input_tokens": None,
                        "cache_miss_input_tokens": None,
                        "output_tokens": None,
                        "cost_estimate": {
                            "complete": False,
                            "estimated_cost_usd": None,
                            "reserved_cost_upper_bound_usd": reserve,
                            "reason": "provider_usage_unavailable",
                        },
                        "raw_response": None,
                    }
                )
                if exc.retryable and attempt_number == 1:
                    continue
                raise
            estimate = self.guard.charge(result)
            self.attempts.append(
                {
                    "business_call_id": self.business_call_id,
                    "attempt_number": attempt_number,
                    "result": "succeeded",
                    "error_code": None,
                    "retryable": False,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "requested_model": MODEL,
                    "model": result.model,
                    "finish_reason": result.finish_reason,
                    "input_tokens": result.input_tokens,
                    "cache_hit_input_tokens": None,
                    "cache_miss_input_tokens": None,
                    "output_tokens": result.output_tokens,
                    "cost_estimate": estimate,
                    "raw_response": result.content,
                }
            )
            return result
        raise AssertionError("unreachable")


def preflight() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if RESULT_PATH.exists():
        raise RuntimeError("P3 raw 结果路径已存在，拒绝覆盖或补跑")
    if normalized_fixture_fingerprint() != EXPECTED_NORMALIZED_FINGERPRINT:
        raise RuntimeError("P1 冻结 fixture 身份已经漂移")
    confirmed = json.loads(CONFIRMED_PATH.read_text(encoding="utf-8"))
    if (
        confirmed.get("status") != "complete"
        or confirmed.get("confirmed_plan_count") != 5
        or not confirmed.get("p3_input_ready")
        or confirmed.get("source_fixture_fingerprint") != EXPECTED_NORMALIZED_FINGERPRINT
    ):
        raise RuntimeError("P2 confirmed snapshots 不满足 P3 输入门禁")
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("P3 已授权，但 DeepSeek API Key 未配置")
    if (
        settings.SCREENING_EVALUATION_MODEL != MODEL
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS != REPORT_MAX_OUTPUT_TOKENS
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
        != SCREENING_EVALUATION_V5_SCHEMA_VERSION
    ):
        raise RuntimeError("当前报告配置与 P3 冻结执行合同不一致")
    jobs = {item["case_id"]: item for item in PLAN_JDS}
    plans = {item["case_id"]: item for item in confirmed["plans"]}
    if list(jobs) != list(plans) or len(REPORT_PAIRS) != 20:
        raise RuntimeError("5 JD / 20 Resume 映射不完整")
    snapshots: dict[str, Any] = {}
    for index, (case_id, job) in enumerate(jobs.items()):
        item = plans[case_id]
        if item.get("status") != "confirmed" or _fingerprint(item["plan"]) != item["snapshot_sha256"]:
            raise RuntimeError(f"{case_id} confirmed snapshot 身份无效")
        snapshots[case_id] = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(job, index)
        )
    for pair in REPORT_PAIRS:
        job_case_id = pair["job_case_id"]
        screening_evaluation_service._prepare_v5_inputs(
            snapshots[job_case_id], plans[job_case_id]["plan"], pair["resume_text"]
        )
    return confirmed, plans, snapshots


async def _run_business_call(
    *,
    business_call_id: str,
    pair: dict[str, Any],
    run_kind: str,
    run_number: int,
    plans: dict[str, Any],
    snapshots: dict[str, Any],
    delegate: DeepSeekScreeningEvaluationAdapter,
    attempts: list[dict[str, Any]],
    guard: CostGuard,
) -> dict[str, Any]:
    job_case_id = pair["job_case_id"]
    attempt_start = len(attempts)
    started = time.perf_counter()
    try:
        result = await screening_evaluation_service.evaluate_v5(
            job_snapshot=snapshots[job_case_id],
            evaluation_plan=plans[job_case_id]["plan"],
            resume_text=pair["resume_text"],
            evaluation_reference_at=REFERENCE_AT,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts={},
            adapter=AuditedReportAdapter(delegate, attempts, guard, business_call_id),
        )
    except (ScreeningEvaluationServiceError, ScreeningEvaluationAdapterError) as exc:
        return {
            "business_call_id": business_call_id,
            "case_id": pair["case_id"],
            "job_case_id": job_case_id,
            "run_kind": run_kind,
            "run_number": run_number,
            "status": "failed",
            "error_code": getattr(exc, "code", type(exc).__name__),
            "error_message": str(exc),
            "business_duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "adapter_attempt_count": len(attempts) - attempt_start,
            "confirmed_plan_snapshot_sha256": plans[job_case_id]["snapshot_sha256"],
            "labels": pair["labels"],
            "report": None,
        }
    report = result.report
    nonzero = [item for item in report.criterion_assessments if item.assessment.score > 0]
    actual_direction = _direction_for_score(report.overall_score)
    low, high = pair["labels"]["score_range"]
    return {
        "business_call_id": business_call_id,
        "case_id": pair["case_id"],
        "job_case_id": job_case_id,
        "run_kind": run_kind,
        "run_number": run_number,
        "status": "succeeded",
        "error_code": None,
        "error_message": None,
        "business_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "adapter_attempt_count": len(attempts) - attempt_start,
        "confirmed_plan_snapshot_sha256": plans[job_case_id]["snapshot_sha256"],
        "labels": pair["labels"],
        "overall_score": report.overall_score,
        "display_label": report.display_label,
        "actual_direction": actual_direction,
        "direction_matches_frozen_label": actual_direction
        == pair["labels"]["expected_direction"],
        "score_in_frozen_range": low <= report.overall_score <= high,
        "criterion_assessment_count": len(report.criterion_assessments),
        "nonzero_assessment_count": len(nonzero),
        "nonzero_with_evidence_count": sum(bool(item.assessment.evidence) for item in nonzero),
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


def _attempt_summary(attempts: list[dict[str, Any]], guard: CostGuard) -> dict[str, Any]:
    succeeded = [item for item in attempts if item["result"] == "succeeded"]
    return {
        "scheduled_business_call_count": 35,
        "executed_business_call_count": len({item["business_call_id"] for item in attempts}),
        "api_attempt_count": len(attempts),
        "succeeded_attempt_count": len(succeeded),
        "failed_attempt_count": len(attempts) - len(succeeded),
        "infrastructure_retry_count": sum(item["attempt_number"] == 2 for item in attempts),
        "input_tokens": sum(item["input_tokens"] or 0 for item in succeeded),
        "cache_hit_input_tokens": None,
        "cache_miss_input_tokens": None,
        "output_tokens": sum(item["output_tokens"] or 0 for item in succeeded),
        "estimated_spend_usd": guard.estimated_spend_usd,
        "failed_attempt_reserve_usd": guard.failed_attempt_reserve_usd,
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
                "spread_le_10": len(scores) == 3 and max(scores) - min(scores) <= 10,
            }
        )
    return summary


async def run() -> dict[str, Any]:
    confirmed, plans, snapshots = preflight()
    pricing = _pricing(datetime.now(timezone.utc))
    guard = CostGuard(pricing=pricing, cap_usd=MONETARY_CAP_USD)
    attempts: list[dict[str, Any]] = []
    report_records: list[dict[str, Any]] = []
    stability_records: list[dict[str, Any]] = []
    delegate = DeepSeekScreeningEvaluationAdapter(settings=get_settings())
    status = "completed"
    fatal_error: dict[str, str] | None = None
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    schedule = [
        (f"P3-{case_id}", pairs[case_id], "report", 1)
        for case_id in pairs
    ] + [
        (f"P3-S-{case_id}-{run_number}", pairs[case_id], "stability", run_number)
        for case_id in STABILITY_CASE_IDS
        for run_number in range(1, 4)
    ]
    try:
        for index, (business_call_id, pair, run_kind, run_number) in enumerate(schedule, 1):
            record = await _run_business_call(
                business_call_id=business_call_id,
                pair=pair,
                run_kind=run_kind,
                run_number=run_number,
                plans=plans,
                snapshots=snapshots,
                delegate=delegate,
                attempts=attempts,
                guard=guard,
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
                f"cost=${guard.estimated_spend_usd:.6f}",
                flush=True,
            )
    except Exception as exc:
        status = "stopped_partial"
        fatal_error = {"type": type(exc).__name__, "message": str(exc)}
        print(f"P3 stopped: {fatal_error}", flush=True)
    successful_reports = [item for item in report_records if item["status"] == "succeeded"]
    payload = {
        "stage": "stage7-pro-realistic-quality",
        "batch": "P3",
        "mode": "real_report_raw",
        "generated_at": _utc_now(),
        "status": status,
        "fatal_error": fatal_error,
        "authorization": {
            "authorized_by": "project_owner_user",
            "user_directive": AUTHORIZATION_DIRECTIVE,
            "authorized_business_call_count": 35,
            "monetary_cap_usd": MONETARY_CAP_USD,
        },
        "source_fixture_fingerprint": EXPECTED_NORMALIZED_FINGERPRINT,
        "source_confirmed_plans_path": str(CONFIRMED_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "source_confirmed_plans_structured_sha256": _fingerprint(confirmed),
        "confirmed_plan_snapshot_sha256": {
            case_id: item["snapshot_sha256"] for case_id, item in plans.items()
        },
        "execution_contract": {
            "model": MODEL,
            "prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
            "max_output_tokens": REPORT_MAX_OUTPUT_TOKENS,
            "temperature": 0.1,
            "thinking": "disabled",
            "content_error_retry_count": 0,
            "infrastructure_retry_maximum_per_business_call": 1,
        },
        "pricing": pricing,
        "monetary_cap_usd": MONETARY_CAP_USD,
        "attempt_summary": _attempt_summary(attempts, guard),
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
        },
        "stability_summary": _stability_summary(stability_records),
        "reports": report_records,
        "stability_runs": stability_records,
        "attempt_audit": attempts,
        "quality_gate_passed": None,
        "quality_conclusion_allowed": False,
        "requires_human_audit": True,
        "postgresql_write_count": 0,
        "api_key_persisted": False,
        "next_step": "停止并等待用户另行确认 P4 人工质量审核。",
    }
    with RESULT_PATH.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-p3", action="store_true")
    args = parser.parse_args()
    if not args.confirm_p3:
        raise SystemExit("P3 必须使用 --confirm-p3 显式执行")
    payload = asyncio.run(run())
    print(json.dumps(payload["attempt_summary"], ensure_ascii=False), flush=True)
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
