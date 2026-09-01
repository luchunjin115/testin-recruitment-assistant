from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.job_evaluation_plan import (  # noqa: E402
    DeepSeekJobEvaluationPlanAdapter,
    FakeJobEvaluationPlanAdapter,
)
from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
    JobEvaluationPlanV5GenerationError,
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationServiceError,
    screening_evaluation_service,
)
from run_stage7_7r5_quality import (  # noqa: E402
    AuditedPlanAdapter,
    AuditedReportAdapter,
    CostGuard,
    _fake_plan_result,
    _fake_report_payload,
    _fake_report_result,
    summarize_attempts,
)
from run_stage7_7r5i4_pricing_gate import (  # noqa: E402
    PRICING_SNAPSHOT_PATH,
    pricing_tier_at,
    validate_pricing_snapshot,
)
from stage7_7r5_quality_contract import (  # noqa: E402
    I2_FINAL_RESULT_PATH,
    I2_HUMAN_AUDIT_PATH,
    I2_RAW_RESULT_PATH,
    I4_FINAL_RESULT_PATH,
    I4_HUMAN_AUDIT_PATH,
    I4_PREFLIGHT_PATH,
    I4_QUALITY_CONTRACT_VERSION,
    I4_RAW_RESULT_PATH,
    I4_RUN_ID,
    MAXIMUM_API_ATTEMPTS,
    PLAN_MAX_OUTPUT_TOKENS,
    PLANNED_MODEL,
    REPORT_MAX_OUTPUT_TOKENS,
    call_budget,
    validate_historical_results,
    validate_result_lifecycle,
    write_new_json,
)
from tests.fixtures.v5_i4_quality_samples import (  # noqa: E402
    I4_PLAN_JDS,
    I4_REPORT_PAIRS,
    I4_STABILITY_RUNS_PER_SAMPLE,
    I4_STABILITY_SAMPLE_INDICES,
)


AUTHORIZATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-31-stage7-7r5i4-real-authorization.json"
)
I4_REPORT_SECTION_FIELDS = (
    "strengths", "gaps", "risks_or_conflicts", "missing_info", "hr_follow_up_questions"
)


def execution_contract() -> dict[str, Any]:
    return {
        "model": PLANNED_MODEL,
        "temperature": 0.1,
        "thinking": "disabled",
        "response_format": "json_object",
        "sdk_automatic_retries": 0,
        "plan_prompt_version": JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
        "plan_service_behavior_version": JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
        "plan_schema_version": JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
        "report_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "report_service_behavior_version": "lightweight_report_generation_v9",
        "report_schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
        "normal_business_calls_per_sample": 1,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _offline_settings() -> Settings:
    return Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="",
        JOB_EVALUATION_PLAN_MODEL=PLANNED_MODEL,
        SCREENING_EVALUATION_MODEL=PLANNED_MODEL,
    )


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


def _direction_for_score(score: int) -> str:
    if score >= 70:
        return "high_match"
    if score >= 40:
        return "partial_match"
    return "low_match"


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError(f"{label} 无法读取") from None
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} 必须是 JSON object")
    return value


def _validate_authorization(
    payload: dict[str, Any], *, pricing_path: Path, pricing: dict[str, Any]
) -> dict[str, Any]:
    expected = {
        "stage": I4_RUN_ID,
        "purpose": "single_close_06r2_c_real_raw_authorization",
        "monetary_cap_usd": 2.0,
        "baseline_business_calls": 45,
        "maximum_api_attempts": 90,
        "content_error_retry_count": 0,
        "authorizes_single_real_raw": True,
        "authorizes_human_or_final": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"CLOSE-06R2-C 金额或单轮授权字段不一致：{key}")
    if payload.get("user_directive") != "明确授权 7R5-I4 硬上限 USD 2.00，并开始 CLOSE-06R2-C。":
        raise RuntimeError("CLOSE-06R2-C 用户授权原文不一致")
    try:
        confirmed_at = datetime.fromisoformat(str(payload["confirmed_at"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("CLOSE-06R2-C 授权时间非法") from None
    if confirmed_at.tzinfo is None:
        raise RuntimeError("CLOSE-06R2-C 授权时间必须包含时区")
    if (
        Path(str(payload.get("pricing_snapshot_path"))).resolve()
        != pricing_path.resolve()
        or payload.get("pricing_snapshot_sha256") != sha256_file(pricing_path)
    ):
        raise RuntimeError("CLOSE-06R2-C 授权没有绑定当前价格快照")
    if payload.get("model") != pricing["model"] or payload.get("selected_tier") != pricing["selected_tier"]:
        raise RuntimeError("CLOSE-06R2-C 授权没有绑定当前模型或价格档位")
    if payload["monetary_cap_usd"] < pricing["authorization_gate"]["minimum_required_usd"]:
        raise RuntimeError("CLOSE-06R2-C 金额上限低于价格门禁的最坏费用")
    return payload


def validate_zero_call_preconditions(
    *,
    pricing_path: Path,
    authorization_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    pricing = validate_pricing_snapshot(
        _load_json(pricing_path, label="I4-R1 价格快照"), now=current
    )
    if pricing_tier_at(current) != pricing["selected_tier"]:
        raise RuntimeError("当前价格时段已变化，必须返回 CLOSE-06R2-B 重新查询")
    authorization = _validate_authorization(
        _load_json(authorization_path, label="I4-R1 用户授权"),
        pricing_path=pricing_path,
        pricing=pricing,
    )
    lifecycle = validate_result_lifecycle(
        run_id=I4_RUN_ID, expected_state="i4_preflight_complete"
    )
    preflight = _load_json(I4_PREFLIGHT_PATH, label="I4-R1 preflight")
    if (
        preflight.get("stage") != I4_RUN_ID
        or preflight.get("lifecycle") != "i4_preflight_complete"
        or not preflight.get("preflight_checks", {}).get("all_passed")
    ):
        raise RuntimeError("I4-R1 preflight 身份或零调用检查不合法")
    if any(path.exists() for path in (I4_RAW_RESULT_PATH, I4_HUMAN_AUDIT_PATH, I4_FINAL_RESULT_PATH)):
        raise RuntimeError("I4-R1 正式结果路径必须在唯一 real 前为空")
    if not all(path.exists() for path in (I2_RAW_RESULT_PATH, I2_HUMAN_AUDIT_PATH, I2_FINAL_RESULT_PATH)):
        raise RuntimeError("I2 正式证据缺失，拒绝开始 I4-R1")
    return {
        "pricing": pricing,
        "authorization": authorization,
        "preflight": preflight,
        "lifecycle": lifecycle,
        "historical_results_before": validate_historical_results(),
    }


def build_report_request(case: dict[str, Any]) -> dict[str, Any]:
    if case["confirmed_plan_snapshot"].get("status") != "confirmed":
        raise RuntimeError("I4-R1 报告必须使用 HR 已确认计划快照")
    return {
        "job_snapshot": job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, int(case["case_id"].rsplit("R", 1)[-1]))
        ),
        "evaluation_plan": case["confirmed_plan_snapshot"]["plan"],
        "resume_text": case["resume_text"],
        "evaluation_reference_at": datetime(2026, 8, 31, tzinfo=timezone.utc),
        "evaluation_timezone": "",
        "experience_period_facts": {},
        "confirmed_plan_snapshot_sha256": case["confirmed_plan_snapshot"][
            "snapshot_sha256"
        ],
    }


def _validate_runtime_settings(settings: Settings, preflight: dict[str, Any]) -> None:
    expected = execution_contract()
    if preflight.get("execution_contract") != {
        "plan_prompt_version": expected["plan_prompt_version"],
        "plan_service_behavior_version": expected[
            "plan_service_behavior_version"
        ],
        "plan_schema_version": expected["plan_schema_version"],
        "report_prompt_version": expected["report_prompt_version"],
        "report_service_behavior_version": expected[
            "report_service_behavior_version"
        ],
        "report_schema_version": expected["report_schema_version"],
    }:
        raise RuntimeError("I4-R1 preflight 的实际执行版本已经漂移")
    if (
        JOB_EVALUATION_PLAN_V5_PROMPT_VERSION != expected["plan_prompt_version"]
        or JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION
        != expected["plan_service_behavior_version"]
        or JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION != expected["plan_schema_version"]
        or SCREENING_EVALUATION_V5_PROMPT_VERSION != expected["report_prompt_version"]
        or SCREENING_EVALUATION_V5_SCHEMA_VERSION != expected["report_schema_version"]
        or settings.JOB_EVALUATION_PLAN_MODEL != PLANNED_MODEL
        or settings.SCREENING_EVALUATION_MODEL != PLANNED_MODEL
        or settings.JOB_EVALUATION_PLAN_V5_PROMPT_VERSION
        != expected["plan_prompt_version"]
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
        != expected["report_prompt_version"]
        or settings.JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION != "5.0"
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION != "5.0"
        or settings.JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS
        != PLAN_MAX_OUTPUT_TOKENS
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS
        != REPORT_MAX_OUTPUT_TOKENS
    ):
        raise RuntimeError("I4-R1 真实运行配置与冻结合同不一致")


async def _run_plan_case(
    case: dict[str, Any], index: int, adapter: Any
) -> dict[str, Any]:
    snapshot = job_evaluation_plan_service.build_v5_input_snapshot(_job(case, index))
    try:
        content = await job_evaluation_plan_service.build_v5_plan_content(
            snapshot, adapter=adapter
        )
    except JobEvaluationPlanV5GenerationError as exc:
        return {
            "case_id": case["case_id"],
            "status": "failed",
            "error_code": exc.code,
            "error_message": str(exc),
            "rendered_criteria": "",
            "all_criteria_traceable": False,
        }
    rendered = "\n".join(
        "\n".join(
            (
                criterion.name,
                criterion.description,
                criterion.screening_focus,
                *(source.source_quote for source in criterion.sources),
            )
        )
        for criterion in content.criteria
    )
    return {
        "case_id": case["case_id"],
        "status": "succeeded",
        "criteria_count": len(content.criteria),
        "warnings": [item.model_dump(mode="json") for item in content.warnings],
        "criteria": [item.model_dump(mode="json") for item in content.criteria],
        "rendered_criteria": rendered,
        "all_criteria_traceable": all(item.sources for item in content.criteria),
        "business_call_count": content.business_call_count,
        "adapter_attempt_count": content.adapter_attempt_count,
        "infrastructure_retry_count": content.infrastructure_retry_count,
    }


async def _run_report_case(
    case: dict[str, Any], sample_index: int, adapter: Any, *, case_id: str
) -> dict[str, Any]:
    request = build_report_request(case)
    confirmed_sha = request.pop("confirmed_plan_snapshot_sha256")
    try:
        result = await screening_evaluation_service.evaluate_v5(
            **request,
            adapter=adapter,
            settings=_offline_settings(),
        )
    except (ScreeningEvaluationServiceError, ScreeningEvaluationAdapterError) as exc:
        return {
            "case_id": case_id,
            "sample_index": sample_index,
            "status": "failed",
            "error_code": exc.code,
            "error_message": str(exc),
            "manual_direction": case["labels"]["overall_direction"],
            "confirmed_plan_snapshot_sha256": confirmed_sha,
        }
    report = result.report
    serialized = report.model_dump(mode="json")
    nonzero = [
        item.assessment
        for item in report.criterion_assessments
        if item.assessment.score > 0
    ]
    return {
        "case_id": case_id,
        "sample_index": sample_index,
        "status": "succeeded",
        "manual_direction": case["labels"]["overall_direction"],
        "overall_score": report.overall_score,
        "actual_direction": _direction_for_score(report.overall_score),
        "nonzero_assessment_count": len(nonzero),
        "nonzero_with_evidence_count": sum(bool(item.evidence) for item in nonzero),
        "required_section_fields_legal": all(
            field in serialized and isinstance(serialized[field], list)
            for field in I4_REPORT_SECTION_FIELDS
        ),
        "confirmed_plan_snapshot_sha256": confirmed_sha,
        "report": serialized,
    }


async def zero_call_fake_preflight() -> dict[str, Any]:
    plan_records: list[dict[str, Any]] = []
    for index, case in enumerate(I4_PLAN_JDS):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, index)
        )
        adapter = FakeJobEvaluationPlanAdapter([_fake_plan_result(snapshot)])
        plan_records.append(await _run_plan_case(case, index, adapter))

    report_records: list[dict[str, Any]] = []
    for index, case in enumerate(I4_REPORT_PAIRS):
        confirmed = SimpleNamespace(
            criteria=[
                SimpleNamespace(criterion_id=item["criterion_id"])
                for item in case["confirmed_plan_snapshot"]["plan"]["criteria"]
            ]
        )
        fake_payload = _fake_report_payload(
            confirmed,
            case["resume_text"],
            case["labels"]["overall_direction"],
        )
        adapter = FakeScreeningEvaluationAdapter(
            [_fake_report_result(fake_payload)]
        )
        report_records.append(
            await _run_report_case(
                case, index, adapter, case_id=case["case_id"]
            )
        )

    stability_records: list[dict[str, Any]] = []
    for index in I4_STABILITY_SAMPLE_INDICES:
        case = I4_REPORT_PAIRS[index]
        confirmed = SimpleNamespace(
            criteria=[
                SimpleNamespace(criterion_id=item["criterion_id"])
                for item in case["confirmed_plan_snapshot"]["plan"]["criteria"]
            ]
        )
        for run_number in range(1, I4_STABILITY_RUNS_PER_SAMPLE + 1):
            fake_payload = _fake_report_payload(
                confirmed,
                case["resume_text"],
                case["labels"]["overall_direction"],
            )
            adapter = FakeScreeningEvaluationAdapter(
                [_fake_report_result(fake_payload)]
            )
            stability_records.append(
                await _run_report_case(
                    case,
                    index,
                    adapter,
                    case_id=f"I4-S{index:02d}-{run_number}",
                )
            )
    return {
        "plan_succeeded": sum(
            item["status"] == "succeeded" for item in plan_records
        ),
        "report_succeeded": sum(
            item["status"] == "succeeded" for item in report_records
        ),
        "stability_succeeded": sum(
            item["status"] == "succeeded" for item in stability_records
        ),
        "fake_business_call_count": 45,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "formal_result_write_count": 0,
        "postgresql_write_count": 0,
    }


async def capture_one_fake_report_boundary() -> dict[str, Any]:
    case = I4_REPORT_PAIRS[0]
    confirmed = SimpleNamespace(criteria=[SimpleNamespace(criterion_id=item["criterion_id"]) for item in case["confirmed_plan_snapshot"]["plan"]["criteria"]])
    payload = _fake_report_payload(confirmed, case["resume_text"], case["labels"]["overall_direction"])
    observed: dict[str, Any] = {}

    class CaptureAdapter:
        async def evaluate_v5(self, **kwargs: Any) -> Any:
            observed.update(kwargs)
            return _fake_report_result(payload)

    record = await _run_report_case(case, 0, CaptureAdapter(), case_id=case["case_id"])
    observed["confirmed_plan_snapshot_used"] = record["confirmed_plan_snapshot_sha256"] == case["confirmed_plan_snapshot"]["snapshot_sha256"]
    return observed


def _pad_records(
    records: list[dict[str, Any]], expected: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observed = {item["case_id"] for item in records}
    return records + [item for item in expected if item["case_id"] not in observed]


def _summarize_plans(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": 10,
        "structure_legal_count": sum(item["status"] == "succeeded" for item in records),
        "traceable_plan_count": sum(
            item.get("all_criteria_traceable", False) for item in records
        ),
        "semantic_counts_require_frozen_human_audit": True,
    }


def _summarize_reports(
    records: list[dict[str, Any]], *, stability: bool = False
) -> dict[str, Any]:
    legal = [item for item in records if item["status"] == "succeeded"]
    result: dict[str, Any] = {
        "scheduled_run_count": len(records),
        "legal_report_count": len(legal),
        "direction_consistent_count": sum(
            item.get("actual_direction") == item.get("manual_direction")
            for item in legal
        ),
        "nonzero_assessment_count": sum(
            item.get("nonzero_assessment_count", 0) for item in legal
        ),
        "nonzero_with_evidence_count": sum(
            item.get("nonzero_with_evidence_count", 0) for item in legal
        ),
        "required_section_fields_legal_count": sum(
            item.get("required_section_fields_legal", False) for item in legal
        ),
        "human_fact_direction_and_material_finding_audit_required": True,
    }
    if stability:
        groups = []
        for index in I4_STABILITY_SAMPLE_INDICES:
            group = [item for item in records if item["sample_index"] == index]
            scores = [
                item["overall_score"]
                for item in group
                if item["status"] == "succeeded"
            ]
            directions = {
                item["actual_direction"]
                for item in group
                if item["status"] == "succeeded"
            }
            groups.append(
                {
                    "sample_index": index,
                    "case_id": I4_REPORT_PAIRS[index]["case_id"],
                    "legal_run_count": len(scores),
                    "max_score_difference": (
                        max(scores) - min(scores) if len(scores) == 3 else None
                    ),
                    "direction_stable": len(scores) == 3 and len(directions) == 1,
                    "extreme_direction_flip": (
                        "high_match" in directions and "low_match" in directions
                    ),
                }
            )
        result["groups"] = groups
        result["direction_stable_group_count"] = sum(
            item["direction_stable"] for item in groups
        )
        result["max_difference_le_10_group_count"] = sum(
            item["max_score_difference"] is not None
            and item["max_score_difference"] <= 10
            for item in groups
        )
        result["extreme_direction_flip_count"] = sum(
            item["extreme_direction_flip"] for item in groups
        )
    return result


def build_raw_payload(
    *,
    gate: dict[str, Any],
    attempts: list[dict[str, Any]],
    plan_records: list[dict[str, Any]],
    report_records: list[dict[str, Any]],
    stability_records: list[dict[str, Any]],
    estimated_spend_usd: float,
    failed_attempt_reserve_usd: float,
    terminal_status: str,
    terminal_error: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_records = _pad_records(
        plan_records,
        [
            {"case_id": case["case_id"], "status": "not_executed"}
            for case in I4_PLAN_JDS
        ],
    )
    report_records = _pad_records(
        report_records,
        [
            {
                "case_id": case["case_id"],
                "sample_index": index,
                "status": "not_executed",
            }
            for index, case in enumerate(I4_REPORT_PAIRS)
        ],
    )
    stability_records = _pad_records(
        stability_records,
        [
            {
                "case_id": f"I4-S{index:02d}-{run}",
                "sample_index": index,
                "status": "not_executed",
            }
            for index in I4_STABILITY_SAMPLE_INDICES
            for run in range(1, I4_STABILITY_RUNS_PER_SAMPLE + 1)
        ],
    )
    pricing = gate["pricing"]
    authorization = gate["authorization"]
    return {
        "stage": I4_RUN_ID,
        "mode": "real_raw",
        "lifecycle": "i4_raw_complete",
        "generated_at": _utc_now(),
        "terminal_status": terminal_status,
        "terminal_error": terminal_error,
        "quality_contract_version": I4_QUALITY_CONTRACT_VERSION,
        "preflight_path": str(I4_PREFLIGHT_PATH),
        "preflight_sha256": sha256_file(I4_PREFLIGHT_PATH),
        "fixture_hashes": gate["preflight"]["fixture_hashes"],
        "execution_contract": execution_contract(),
        "call_budget": call_budget(),
        "result_lifecycle_before": gate["lifecycle"],
        "official_pricing_snapshot": pricing,
        "real_authorization": authorization,
        "monetary_cap_usd": authorization["monetary_cap_usd"],
        "estimated_spend_usd": estimated_spend_usd,
        "failed_attempt_reserve_usd": failed_attempt_reserve_usd,
        "attempt_audit_summary": {
            "scheduled_business_call_count": 45,
            "executed_business_call_count": len(
                {item["case_id"] for item in attempts}
            ),
            "api_attempt_count": len(attempts),
            "infrastructure_retry_count": sum(
                item["attempt_number"] == 2 for item in attempts
            ),
            "succeeded_attempt_count": sum(
                item["result"] == "succeeded" for item in attempts
            ),
            "failed_attempt_count": sum(
                item["result"] == "failed" for item in attempts
            ),
            "maximum_api_attempts": MAXIMUM_API_ATTEMPTS,
            "estimated_spend_usd": estimated_spend_usd,
            "failed_attempt_reserve_usd": failed_attempt_reserve_usd,
        },
        "attempt_audit": attempts,
        "plan_records": plan_records,
        "report_records": report_records,
        "stability_records": stability_records,
        "summaries": {
            "plans": _summarize_plans(plan_records),
            "reports": _summarize_reports(report_records),
            "stability": _summarize_reports(stability_records, stability=True),
        },
        "historical_results_before": gate.get("historical_results_before"),
        "historical_results_after": validate_historical_results(),
        "requires_frozen_human_audit": True,
        "quality_gate_passed": None,
        "quality_conclusion_allowed": False,
        "api_key_persisted": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 1,
    }


def write_raw_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("I4-R1 raw 已存在，拒绝覆盖") from None


def build_raw_payload_for_test(*, authorization: dict[str, Any], terminal_status: str) -> dict[str, Any]:
    return build_raw_payload(
        gate={
            "pricing": {"selected_tier": "off_peak"},
            "authorization": authorization,
            "preflight": {"fixture_hashes": {"fixture": "test"}},
            "lifecycle": {"state": "i4_preflight_complete"},
            "historical_results_before": validate_historical_results(),
        },
        attempts=[], plan_records=[], report_records=[], stability_records=[],
        estimated_spend_usd=0, failed_attempt_reserve_usd=0,
        terminal_status=terminal_status, terminal_error=None,
    )


def validate_sealed_raw() -> dict[str, Any]:
    lifecycle = validate_result_lifecycle(
        run_id=I4_RUN_ID, expected_state="i4_raw_complete"
    )
    raw = _load_json(I4_RAW_RESULT_PATH, label="I4-R1 raw")
    if (
        raw.get("stage") != I4_RUN_ID
        or raw.get("mode") != "real_raw"
        or raw.get("lifecycle") != "i4_raw_complete"
        or raw.get("preflight_sha256") != sha256_file(I4_PREFLIGHT_PATH)
        or raw.get("quality_contract_version") != I4_QUALITY_CONTRACT_VERSION
    ):
        raise RuntimeError("I4-R1 raw 身份、生命周期或冻结 preflight 不一致")
    expected_lengths = {
        "plan_records": 10,
        "report_records": 20,
        "stability_records": 15,
    }
    if any(
        not isinstance(raw.get(key), list) or len(raw[key]) != length
        for key, length in expected_lengths.items()
    ):
        raise RuntimeError("I4-R1 raw 的 10/20/15 固定分母不完整")
    attempts = raw.get("attempt_audit")
    summary = raw.get("attempt_audit_summary")
    if (
        not isinstance(attempts, list)
        or not isinstance(summary, dict)
        or len(attempts) > MAXIMUM_API_ATTEMPTS
        or summary.get("api_attempt_count") != len(attempts)
        or summary.get("scheduled_business_call_count") != 45
    ):
        raise RuntimeError("I4-R1 raw 的 45/90 调用审计不一致")
    if (
        raw.get("monetary_cap_usd") != 2.0
        or raw.get("estimated_spend_usd", 3) > 2.0
        or raw.get("quality_gate_passed") is not None
        or raw.get("quality_conclusion_allowed") is not False
        or raw.get("postgresql_write_count") != 0
        or I4_HUMAN_AUDIT_PATH.exists()
        or I4_FINAL_RESULT_PATH.exists()
    ):
        raise RuntimeError("I4-R1 raw 的金额、质量停止点或零数据库合同不一致")
    return {
        "lifecycle": lifecycle,
        "raw": raw,
        "raw_sha256": sha256_file(I4_RAW_RESULT_PATH),
    }


async def run_real(
    *, pricing_path: Path, authorization_path: Path
) -> dict[str, Any]:
    gate = validate_zero_call_preconditions(
        pricing_path=pricing_path,
        authorization_path=authorization_path,
    )
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("CLOSE-06R2-C 已授权，但 DeepSeek API Key 未配置")
    _validate_runtime_settings(settings, gate["preflight"])
    if pricing_tier_at(datetime.now(timezone.utc)) != gate["pricing"]["selected_tier"]:
        raise RuntimeError("实例化 Adapter 前价格时段已变化，返回 CLOSE-06R2-B")

    guard = CostGuard(
        pricing=gate["pricing"],
        cap_usd=gate["authorization"]["monetary_cap_usd"],
    )
    attempts: list[dict[str, Any]] = []
    plan_records: list[dict[str, Any]] = []
    report_records: list[dict[str, Any]] = []
    stability_records: list[dict[str, Any]] = []
    terminal_status = "completed"
    terminal_error: dict[str, Any] | None = None
    plan_delegate = DeepSeekJobEvaluationPlanAdapter(settings=settings)
    report_delegate = DeepSeekScreeningEvaluationAdapter(settings=settings)
    try:
        for index, case in enumerate(I4_PLAN_JDS):
            plan_records.append(
                await _run_plan_case(
                    case,
                    index,
                    AuditedPlanAdapter(
                        plan_delegate, attempts, guard, case["case_id"]
                    ),
                )
            )
        for index, case in enumerate(I4_REPORT_PAIRS):
            report_records.append(
                await _run_report_case(
                    case,
                    index,
                    AuditedReportAdapter(
                        report_delegate, attempts, guard, case["case_id"]
                    ),
                    case_id=case["case_id"],
                )
            )
        for index in I4_STABILITY_SAMPLE_INDICES:
            case = I4_REPORT_PAIRS[index]
            for run_number in range(1, I4_STABILITY_RUNS_PER_SAMPLE + 1):
                case_id = f"I4-S{index:02d}-{run_number}"
                stability_records.append(
                    await _run_report_case(
                        case,
                        index,
                        AuditedReportAdapter(
                            report_delegate, attempts, guard, case_id
                        ),
                        case_id=case_id,
                    )
                )
        if any(
            item["status"] != "succeeded"
            for item in (*plan_records, *report_records, *stability_records)
        ):
            terminal_status = "completed_with_failures"
    except Exception as exc:  # raw must preserve the one started real run
        if not attempts:
            raise
        terminal_status = "stopped_by_runner_gate"
        terminal_error = {
            "type": type(exc).__name__,
            "message": "真实运行已停止；不得补跑，具体失败见 attempt 和 case 记录。",
        }

    if len(attempts) > MAXIMUM_API_ATTEMPTS:
        terminal_status = "stopped_by_runner_gate"
        terminal_error = {
            "type": "MaximumApiAttemptsExceeded",
            "message": "真实 API attempt 超过冻结上限。",
        }
    payload = build_raw_payload(
        gate=gate,
        attempts=attempts,
        plan_records=plan_records,
        report_records=report_records,
        stability_records=stability_records,
        estimated_spend_usd=guard.estimated_spend_usd,
        failed_attempt_reserve_usd=guard.failed_attempt_reserve_usd,
        terminal_status=terminal_status,
        terminal_error=terminal_error,
    )
    if payload["historical_results_before"] != payload["historical_results_after"]:
        raise RuntimeError("I4-R1 真实运行期间历史证据发生变化，拒绝写 raw")
    write_new_json(
        I4_RAW_RESULT_PATH,
        payload,
        run_id=I4_RUN_ID,
        expected_state="i4_preflight_complete",
    )
    return payload


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the single I4-R1 real raw")
    parser.add_argument("--pricing-snapshot", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--monetary-cap-usd", type=float, required=True)
    args = parser.parse_args()
    if args.monetary_cap_usd != 2.0:
        raise RuntimeError("CLOSE-06R2-C CLI 金额必须与用户确认的 USD 2 完全一致")
    payload = await run_real(
        pricing_path=args.pricing_snapshot,
        authorization_path=args.authorization,
    )
    print(
        json.dumps(
            {
                "raw_path": str(I4_RAW_RESULT_PATH),
                "stage": payload["stage"],
                "lifecycle": payload["lifecycle"],
                "terminal_status": payload["terminal_status"],
                "attempt_audit_summary": payload["attempt_audit_summary"],
                "summaries": payload["summaries"],
                "quality_gate_passed": payload["quality_gate_passed"],
                "quality_conclusion_allowed": payload[
                    "quality_conclusion_allowed"
                ],
                "postgresql_write_count": payload["postgresql_write_count"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
