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
    build_screening_evaluation_v5_messages,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    screening_evaluation_service,
)
from run_stage7_pro_realistic_p3 import (  # noqa: E402
    AuditedReportAdapter,
    CostGuard,
    MODEL,
    REFERENCE_AT,
    REPORT_MAX_OUTPUT_TOKENS,
    _fingerprint,
    _job,
    _pricing,
    _run_business_call,
)
from tests.fixtures.stage7_pro_realistic_quality_samples import (  # noqa: E402
    EXPECTED_NORMALIZED_FINGERPRINT,
    PLAN_JDS,
    REPORT_PAIRS,
    normalized_fixture_fingerprint,
)


AUTHORIZATION_DIRECTIVE = "开始实施P5R的A-E，不需要再经过我确认"
P3_RAW_SHA256 = "94f68aa48bec09204359222deab35c6a03ea543a4108eb93375efe0b39574679"
CONFIRMED_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p2-confirmed-plans.json"
)
P3_RAW_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p3-report-raw-results.json"
)
RESULT_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-p5r-evidence-real-retest-raw-results.json"
)
SOURCE_CALL_SCHEDULE = (
    ("P3-R04", "R04", "report", 1),
    ("P3-R09", "R09", "report", 1),
    ("P3-R14", "R14", "report", 1),
    ("P3-S-R09-1", "R09", "stability", 1),
    ("P3-S-R09-2", "R09", "stability", 2),
    ("P3-S-R09-3", "R09", "stability", 3),
    ("P3-S-R17-1", "R17", "stability", 1),
)
PEAK_RATES_USD_PER_MILLION = {
    "cache_hit_input": 0.044,
    "cache_miss_input": 1.32,
    "output": 3.96,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if normalized_fixture_fingerprint() != EXPECTED_NORMALIZED_FINGERPRINT:
        raise RuntimeError("P1 冻结 fixture 身份已经漂移")
    if _sha256(P3_RAW_PATH) != P3_RAW_SHA256:
        raise RuntimeError("P3 raw 身份已经漂移")
    confirmed = json.loads(CONFIRMED_PATH.read_text(encoding="utf-8"))
    if (
        confirmed.get("status") != "complete"
        or confirmed.get("confirmed_plan_count") != 5
        or not confirmed.get("p3_input_ready")
        or confirmed.get("source_fixture_fingerprint")
        != EXPECTED_NORMALIZED_FINGERPRINT
    ):
        raise RuntimeError("P2 confirmed snapshots 不满足 P5R-E 输入门禁")

    jobs = {item["case_id"]: item for item in PLAN_JDS}
    plans = {item["case_id"]: item for item in confirmed["plans"]}
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

    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    for _, case_id, _, _ in SOURCE_CALL_SCHEDULE:
        pair = pairs[case_id]
        screening_evaluation_service._prepare_v5_inputs(
            snapshots[pair["job_case_id"]],
            plans[pair["job_case_id"]]["plan"],
            pair["resume_text"],
        )
    return confirmed, plans, snapshots


def _message_payloads(
    plans: dict[str, Any], snapshots: dict[str, Any]
) -> list[list[dict[str, str]]]:
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    payloads = []
    for _, case_id, _, _ in SOURCE_CALL_SCHEDULE:
        pair = pairs[case_id]
        payloads.append(
            build_screening_evaluation_v5_messages(
                job_snapshot=snapshots[pair["job_case_id"]].model_dump(mode="json"),
                evaluation_plan=plans[pair["job_case_id"]]["plan"],
                sanitized_resume=screening_evaluation_service.sanitize_resume_text(
                    pair["resume_text"]
                ),
                evaluation_reference_at=REFERENCE_AT.isoformat(),
                evaluation_timezone="Asia/Shanghai",
                experience_period_facts={},
            )
        )
    return payloads


def peak_cost_upper_bound_usd(
    plans: dict[str, Any], snapshots: dict[str, Any]
) -> float:
    total = 0.0
    for messages in _message_payloads(plans, snapshots):
        input_upper = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
        total += (
            input_upper * PEAK_RATES_USD_PER_MILLION["cache_miss_input"]
            + REPORT_MAX_OUTPUT_TOKENS * PEAK_RATES_USD_PER_MILLION["output"]
        ) / 1_000_000
    return total


def offline_preflight() -> dict[str, Any]:
    if RESULT_PATH.exists():
        raise RuntimeError("P5R-E 独立 raw 路径已存在，拒绝覆盖或补跑")
    confirmed, plans, snapshots = _build_frozen_inputs()
    p3_raw = json.loads(P3_RAW_PATH.read_text(encoding="utf-8"))
    old_failed_ids = {
        item["business_call_id"]
        for item in p3_raw["reports"] + p3_raw["stability_runs"]
        if item["status"] == "failed"
    }
    scheduled_ids = [item[0] for item in SOURCE_CALL_SCHEDULE]
    if not set(scheduled_ids).issubset(old_failed_ids):
        raise RuntimeError("P5R-E 调用表包含 P3 非失败调用")

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
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS
        != REPORT_MAX_OUTPUT_TOKENS
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != SCREENING_EVALUATION_V5_PROMPT_VERSION
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
        != SCREENING_EVALUATION_V5_SCHEMA_VERSION
    ):
        raise RuntimeError("当前报告配置与 P5R-E 合同不一致")

    return {
        "confirmed": confirmed,
        "plans": plans,
        "snapshots": snapshots,
        "scheduled_source_call_ids": scheduled_ids,
        "peak_cost_upper_bound_usd": peak_cost_upper_bound_usd(plans, snapshots),
    }


def _attempt_summary(
    attempts: list[dict[str, Any]], guard: CostGuard
) -> dict[str, Any]:
    succeeded = [item for item in attempts if item["result"] == "succeeded"]
    return {
        "scheduled_business_call_count": len(SOURCE_CALL_SCHEDULE),
        "executed_business_call_count": len(
            {item["business_call_id"] for item in attempts}
        ),
        "api_attempt_count": len(attempts),
        "api_attempt_limit": len(SOURCE_CALL_SCHEDULE) * 2,
        "succeeded_attempt_count": len(succeeded),
        "failed_attempt_count": len(attempts) - len(succeeded),
        "infrastructure_retry_count": sum(
            item["attempt_number"] == 2 for item in attempts
        ),
        "input_tokens": sum(item["input_tokens"] or 0 for item in succeeded),
        "output_tokens": sum(item["output_tokens"] or 0 for item in succeeded),
        "estimated_spend_usd": guard.estimated_spend_usd,
        "failed_attempt_reserve_usd": guard.failed_attempt_reserve_usd,
    }


async def run(*, monetary_cap_usd: float) -> dict[str, Any]:
    preflight = offline_preflight()
    if monetary_cap_usd <= 0:
        raise RuntimeError("P5R-E 美元费用上限必须大于 0")
    if monetary_cap_usd < preflight["peak_cost_upper_bound_usd"]:
        raise RuntimeError("P5R-E 美元费用上限低于 7 次调用的 peak 保守上界")
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("P5R-E 已获金额授权，但 DeepSeek API Key 未配置")

    pricing = _pricing(datetime.now(timezone.utc))
    guard = CostGuard(pricing=pricing, cap_usd=monetary_cap_usd)
    attempts: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    delegate = DeepSeekScreeningEvaluationAdapter(settings=settings)
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    status = "completed"
    fatal_error: dict[str, str] | None = None

    try:
        for index, (source_call_id, case_id, run_kind, run_number) in enumerate(
            SOURCE_CALL_SCHEDULE, 1
        ):
            record = await _run_business_call(
                business_call_id=source_call_id,
                pair=pairs[case_id],
                run_kind=run_kind,
                run_number=run_number,
                plans=preflight["plans"],
                snapshots=preflight["snapshots"],
                delegate=delegate,
                attempts=attempts,
                guard=guard,
            )
            records.append(record)
            detail = (
                f"score={record['overall_score']}"
                if record["status"] == "succeeded"
                else f"error={record['error_code']}"
            )
            print(
                f"[{index}/7] {source_call_id} {record['status']} {detail} "
                f"cost=${guard.estimated_spend_usd:.6f}",
                flush=True,
            )
    except Exception as exc:
        status = "stopped_partial"
        fatal_error = {"type": type(exc).__name__, "message": str(exc)}

    payload = {
        "stage": "stage7-p5r-evidence-contract",
        "batch": "P5R-E",
        "mode": "real_evidence_retest_raw",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "fatal_error": fatal_error,
        "authorization": {
            "authorized_by": "project_owner_user",
            "user_directive": AUTHORIZATION_DIRECTIVE,
            "monetary_cap_usd": monetary_cap_usd,
        },
        "source_p3_raw_path": str(P3_RAW_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "source_p3_raw_sha256": P3_RAW_SHA256,
        "source_call_schedule": preflight["scheduled_source_call_ids"],
        "execution_contract": {
            "model": MODEL,
            "prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
            "behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
            "content_error_retry_count": 0,
            "infrastructure_retry_maximum_per_business_call": 1,
            "api_attempt_limit": 14,
        },
        "pricing": pricing,
        "peak_cost_upper_bound_usd": preflight["peak_cost_upper_bound_usd"],
        "attempt_summary": _attempt_summary(attempts, guard),
        "attempt_audit": attempts,
        "records": records,
        "service_legal_count": sum(
            item["status"] == "succeeded" for item in records
        ),
        "quality_conclusion_allowed": False,
        "postgresql_write_count": 0,
        "api_key_persisted": False,
        "next_step": "停止并向用户报告七例前后对照，不自动宣布阶段 7 通过。",
    }
    with RESULT_PATH.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-p5r-e", action="store_true")
    parser.add_argument("--cap-usd", type=float)
    args = parser.parse_args()
    if not args.confirm_p5r_e or args.cap_usd is None:
        raise SystemExit("P5R-E 必须同时提供 --confirm-p5r-e 和 --cap-usd")
    payload = asyncio.run(run(monetary_cap_usd=args.cap_usd))
    print(json.dumps(payload["attempt_summary"], ensure_ascii=False), flush=True)
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
