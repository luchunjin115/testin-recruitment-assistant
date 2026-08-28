from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for import_path in (BACKEND_ROOT, SCRIPTS_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.services.experience_period_service import (  # noqa: E402
    experience_period_service,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    JobEvaluationPlanContentError,
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationServiceError,
    screening_evaluation_service,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    AIScreeningEvaluationV5Output,
)
from stage7_7r5_quality_contract import (  # noqa: E402
    ACTIVE_RUN_ID,
    FROZEN_FIXTURE_SHA256,
    HISTORICAL_RESULT_HASHES,
    I2_PREFLIGHT_PATH,
    RAW_RESULT_PATH,
    SEALED_RAW_SHA256,
    execution_contract,
    sha256_file,
    validate_frozen_fixture,
    validate_historical_results,
    validate_result_lifecycle,
    write_new_json,
)
from tests.fixtures.v5_quality_samples import (  # noqa: E402
    V5_PLAN_JDS,
    V5_REPORT_PAIRS,
    V5_STABILITY_SAMPLE_INDICES,
    V5_STABILITY_RUNS_PER_SAMPLE,
)


REFERENCE_AT = datetime(2026, 8, 27, 0, 0, tzinfo=timezone.utc)
I2_PREFLIGHT_SHA256 = "185b42d7c55d6654cedfa251f340d89469470800336aa17be192ae3d1c28b6b2"
R1C_DIAGNOSTIC_SHA256 = "f89426b3aa03b005cb533d6305590d17751dbada076dda526295b8a31b9ad3f3"
R1C_TARGET_CASE_IDS = ("R00", "R09", "R16", "S00-1", "S00-2", "S00-3")
R1C_DIAGNOSTIC_DIR = I2_PREFLIGHT_PATH.parent / "7r5i2-diagnostics"
R1C_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-28-stage7-7r5i2-r1c-structure-replay.json"
)
R2E_TARGET_CASE_IDS = (
    "R00",
    "R05",
    "R07",
    "R15",
    "R17",
    "R18",
    "R19",
    "S00-1",
    "S00-2",
    "S00-3",
    "S04-2",
    "S04-3",
)
R2E_MODEL_RISK_CASE_IDS = ("R15", "R19")
R2E_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-28-stage7-7r5i2-r2e-duration-replay.json"
)
OLD_DURATION_GATE_MESSAGE = "AI 年限结论与后端经历时间事实冲突"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _job(case: dict[str, Any], index: int) -> SimpleNamespace:
    jd = case["jd"]
    return SimpleNamespace(
        id=96_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=jd["job_background"],
        job_responsibilities=jd["job_responsibilities"],
        candidate_requirements=jd["candidate_requirements"],
        preferred_qualifications=jd["preferred_qualifications"],
        public_notes=jd["public_notes"],
        status="open",
    )


def _plan_case_index(pair: dict[str, Any]) -> int:
    matches = [
        index for index, case in enumerate(V5_PLAN_JDS) if case["jd"] == pair["jd"]
    ]
    if len(matches) != 1:
        raise RuntimeError("报告样本不能唯一映射到冻结计划 JD")
    return matches[0]


def _load_source_raw(source_path: Path) -> dict[str, Any]:
    if not source_path.exists():
        raise RuntimeError("7R5-I2 零调用预检缺少封存 raw")
    digest = sha256_file(source_path)
    if digest != SEALED_RAW_SHA256:
        raise RuntimeError("7R5-I2 零调用预检的封存 raw SHA-256 不匹配")
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("7R5-I2 零调用预检无法读取封存 raw") from None
    if raw.get("stage") != "7R5-I" or raw.get("mode") != "real_raw":
        raise RuntimeError("零调用预检只接受封存的 7R5-I real raw")
    expected_lengths = {
        "plan_records": 10,
        "report_records": 20,
        "stability_records": 15,
        "attempt_audit": 29,
    }
    for key, expected in expected_lengths.items():
        if not isinstance(raw.get(key), list) or len(raw[key]) != expected:
            raise RuntimeError(f"封存 raw 的 {key} 固定分母不完整")
    fixture = raw.get("fixture")
    if (
        not isinstance(fixture, dict)
        or fixture.get("hashes", {}).get("fixture") != FROZEN_FIXTURE_SHA256
    ):
        raise RuntimeError("封存 raw 未绑定冻结 fixture")
    if (
        raw.get("historical_result_hashes_before") != HISTORICAL_RESULT_HASHES
        or raw.get("historical_result_hashes_after") != HISTORICAL_RESULT_HASHES
    ):
        raise RuntimeError("封存 raw 未证明 13 份历史证据不变")
    attempts = raw["attempt_audit"]
    case_ids = [item.get("case_id") for item in attempts if isinstance(item, dict)]
    if len(case_ids) != len(set(case_ids)) or any(
        not isinstance(case_id, str) for case_id in case_ids
    ):
        raise RuntimeError("封存 raw attempt case ID 缺失或重复")
    if any(
        item.get("attempt_number") != 1
        or item.get("result") != "succeeded"
        or not isinstance(item.get("raw_response"), str)
        for item in attempts
    ):
        raise RuntimeError("封存 raw attempt 不符合本轮 29 次成功响应事实")
    return raw


def _source_records(raw: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {item["case_id"]: item for item in raw[key]}


def _source_attempts(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["case_id"]: item for item in raw["attempt_audit"]}


def _load_source_preflight() -> dict[str, Any]:
    if not I2_PREFLIGHT_PATH.exists():
        raise RuntimeError("I2 定向诊断缺少受保护的 I2-C preflight")
    if sha256_file(I2_PREFLIGHT_PATH) != I2_PREFLIGHT_SHA256:
        raise RuntimeError("I2 定向诊断的 I2-C preflight SHA-256 不匹配")
    try:
        payload = json.loads(I2_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("I2 定向诊断无法读取 I2-C preflight") from None
    if (
        payload.get("stage") != ACTIVE_RUN_ID
        or payload.get("mode") != "zero_call_full_category_preflight"
        or payload.get("source_raw_sha256") != SEALED_RAW_SHA256
    ):
        raise RuntimeError("I2 定向诊断的 I2-C preflight 身份不匹配")
    return payload


def _load_source_r1c_diagnostic() -> dict[str, Any]:
    if not R1C_DIAGNOSTIC_PATH.exists():
        raise RuntimeError("R2-E 缺少受保护的 R1-C 诊断")
    if sha256_file(R1C_DIAGNOSTIC_PATH) != R1C_DIAGNOSTIC_SHA256:
        raise RuntimeError("R2-E 的 R1-C 诊断 SHA-256 不匹配")
    try:
        payload = json.loads(R1C_DIAGNOSTIC_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("R2-E 无法读取 R1-C 诊断") from None
    if (
        payload.get("stage") != ACTIVE_RUN_ID
        or payload.get("batch") != "7R5-I2-R1-C"
        or payload.get("source_raw_sha256") != SEALED_RAW_SHA256
        or payload.get("source_preflight_sha256") != I2_PREFLIGHT_SHA256
    ):
        raise RuntimeError("R2-E 的 R1-C 诊断身份不匹配")
    return payload


def _target_case_context(
    *, case_id: str, raw: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], int]:
    attempts = _source_attempts(raw)
    if case_id.startswith("R"):
        sample_index = int(case_id[1:])
        source = _source_records(raw, "report_records")[case_id]
    elif case_id.startswith("S"):
        sample_text, _, run_text = case_id[1:].partition("-")
        sample_index = int(sample_text)
        run_number = int(run_text)
        if run_number not in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1):
            raise RuntimeError(f"I2 定向诊断稳定性 run 编号非法：{case_id}")
        source = _source_records(raw, "stability_records")[case_id]
    else:
        raise RuntimeError(f"I2 定向诊断未登记 case：{case_id}")
    attempt = attempts.get(case_id)
    if attempt is None:
        raise RuntimeError(f"I2 定向诊断目标 case 缺少封存响应：{case_id}")
    return source, attempt, sample_index


def _parse_supporting_plan(
    *, raw: dict[str, Any], plan_index: int
) -> list[Any]:
    case_id = f"P{plan_index:02d}"
    attempt = _source_attempts(raw).get(case_id)
    if attempt is None:
        raise RuntimeError(f"I2 定向诊断缺少支持计划响应：{case_id}")
    snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
        _job(V5_PLAN_JDS[plan_index], plan_index)
    )
    try:
        criteria, _ = job_evaluation_plan_service._parse_v5_plan_response(
            attempt["raw_response"],
            snapshot,
        )
    except JobEvaluationPlanContentError as exc:
        raise RuntimeError(
            f"I2 定向诊断支持计划当前不可用：{case_id} / {exc.code}"
        ) from None
    return criteria


def _auxiliary_counts(content: str) -> tuple[dict[str, int], bool, str | None]:
    try:
        parsed = json.loads(content)
        output = AIScreeningEvaluationV5Output.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        return {}, False, type(exc).__name__
    fields = (
        "strengths",
        "gaps",
        "risks_or_conflicts",
        "missing_info",
        "hr_follow_up_questions",
    )
    return {field: len(getattr(output, field)) for field in fields}, True, None


async def build_r1c_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle = validate_result_lifecycle(
        run_id=ACTIVE_RUN_ID,
        expected_state="i2_preflight_complete",
    )
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    source_preflight = _load_source_preflight()
    previous_records = {
        item["case_id"]: item
        for item in (
            list(source_preflight["report_records"])
            + list(source_preflight["stability_records"])
        )
    }
    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R1C_TARGET_CASE_IDS:
        source, attempt, sample_index = _target_case_context(
            case_id=case_id,
            raw=raw,
        )
        pair = V5_REPORT_PAIRS[sample_index]
        plan_index = _plan_case_index(pair)
        if plan_index not in plan_cache:
            plan_cache[plan_index] = _parse_supporting_plan(
                raw=raw,
                plan_index=plan_index,
            )
        content = attempt["raw_response"]
        counts, schema_accepted, schema_error_type = _auxiliary_counts(content)
        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        previous = previous_records.get(case_id)
        if previous is None:
            raise RuntimeError(f"R1-C preflight 缺少目标 case：{case_id}")
        if (
            previous.get("current_status") != "failed"
            or previous.get("current_error_message")
            != "5.0 AI 初筛结果未通过严格结构校验"
        ):
            raise RuntimeError(f"R1-C 目标 case 旧状态不是冻结结构失败：{case_id}")
        if not schema_accepted:
            classification = "still_rejected_by_current_schema"
        elif current["current_status"] == "succeeded":
            classification = "quantity_gate_crossed_and_report_accepted"
        else:
            classification = "quantity_gate_crossed_then_next_service_gate_rejected"
        records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "previous_preflight_status": previous["current_status"],
                "previous_preflight_error_code": previous.get("current_error_code"),
                "previous_preflight_error_message": previous.get(
                    "current_error_message"
                ),
                "raw_response_sha256": _response_sha256(content),
                "raw_response_length": len(content),
                "auxiliary_counts": counts,
                "current_schema_accepted": schema_accepted,
                "current_schema_error_type": schema_error_type,
                "quantity_gate_crossed": schema_accepted,
                "current_report_status": current["current_status"],
                "current_report_error_code": current.get("current_error_code"),
                "current_report_error_message": current.get("current_error_message"),
                "automatic_classification": classification,
            }
        )
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R1-C 回放期间 13 份历史证据发生变化")
    if sha256_file(source_path) != SEALED_RAW_SHA256:
        raise RuntimeError("R1-C 回放期间封存 raw 发生变化")
    if sha256_file(I2_PREFLIGHT_PATH) != I2_PREFLIGHT_SHA256:
        raise RuntimeError("R1-C 回放期间 I2-C preflight 发生变化")
    quantity_gate_crossed_count = sum(
        item["quantity_gate_crossed"] for item in records
    )
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R1-C",
        "mode": "zero_call_targeted_structure_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_sha256": SEALED_RAW_SHA256,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_sha256": I2_PREFLIGHT_SHA256,
        "target_case_ids": list(R1C_TARGET_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": execution_contract(),
        "lifecycle": lifecycle,
        "quantity_contract": {
            "recommended_items_per_list": "1-5",
            "accepted_items_per_list": "0-20 or 1-20 according to field",
            "hard_max_items_per_list": 20,
            "silent_truncation_allowed": False,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "quantity_gate_crossed_count": quantity_gate_crossed_count,
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": sum(
                item["automatic_classification"]
                == "quantity_gate_crossed_then_next_service_gate_rejected"
                for item in records
            ),
            "current_schema_rejected_count": len(records)
            - quantity_gate_crossed_count,
        },
        "pricing_gate_allowed": False,
        "quality_conclusion_allowed": False,
        "human_or_service_adjudication_required": accepted_count != len(records),
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "adapter_instantiated": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
        "diagnostic_write_count": 1,
        "raw_response_copied": False,
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": historical_after,
    }


async def build_r2e_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle = validate_result_lifecycle(
        run_id=ACTIVE_RUN_ID,
        expected_state="i2_preflight_complete",
    )
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    source_preflight = _load_source_preflight()
    preflight_records = {
        item["case_id"]: item
        for item in (
            list(source_preflight["report_records"])
            + list(source_preflight["stability_records"])
        )
    }
    source_r1c = _load_source_r1c_diagnostic()
    r1c_records = {item["case_id"]: item for item in source_r1c["records"]}
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_prompt_version")
        != "screening_evaluation_lightweight_v3"
    ):
        raise RuntimeError("R2-E 活动报告 Prompt 版本不是 v3")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R2E_TARGET_CASE_IDS:
        source, attempt, sample_index = _target_case_context(
            case_id=case_id,
            raw=raw,
        )
        pair = V5_REPORT_PAIRS[sample_index]
        plan_index = _plan_case_index(pair)
        if plan_index not in plan_cache:
            plan_cache[plan_index] = _parse_supporting_plan(
                raw=raw,
                plan_index=plan_index,
            )
        if case_id in R1C_TARGET_CASE_IDS:
            previous = r1c_records.get(case_id)
            previous_gate_source = "7R5-I2-R1-C"
            previous_status = (
                previous.get("current_report_status") if previous else None
            )
            previous_error_code = (
                previous.get("current_report_error_code") if previous else None
            )
            previous_error_message = (
                previous.get("current_report_error_message") if previous else None
            )
        else:
            previous = preflight_records.get(case_id)
            previous_gate_source = "7R5-I2-C"
            previous_status = previous.get("current_status") if previous else None
            previous_error_code = (
                previous.get("current_error_code") if previous else None
            )
            previous_error_message = (
                previous.get("current_error_message") if previous else None
            )
        if previous is None:
            raise RuntimeError(f"R2-E preflight 缺少目标 case：{case_id}")
        if (
            previous_status != "failed"
            or previous_error_message != OLD_DURATION_GATE_MESSAGE
        ):
            raise RuntimeError(f"R2-E 目标 case 旧状态不是冻结年限拒绝：{case_id}")

        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        old_duration_gate_removed = (
            current.get("current_error_message") != OLD_DURATION_GATE_MESSAGE
        )
        if not old_duration_gate_removed:
            classification = "old_duration_gate_still_rejects"
        elif current["current_status"] == "succeeded":
            classification = "old_duration_gate_removed_and_report_accepted"
        else:
            classification = "old_duration_gate_removed_then_next_gate_rejected"
        records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "previous_gate_source": previous_gate_source,
                "previous_gate_status": previous_status,
                "previous_gate_error_code": previous_error_code,
                "previous_gate_error_message": previous_error_message,
                "raw_response_sha256": _response_sha256(attempt["raw_response"]),
                "raw_response_length": len(attempt["raw_response"]),
                "current_report_status": current["current_status"],
                "current_report_error_code": current.get("current_error_code"),
                "current_report_error_message": current.get(
                    "current_error_message"
                ),
                "current_overall_score": current.get("overall_score"),
                "old_duration_gate_removed": old_duration_gate_removed,
                "future_human_quality_review_required": case_id
                in R2E_MODEL_RISK_CASE_IDS,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R2-E 回放期间 13 份历史证据发生变化")
    if sha256_file(source_path) != SEALED_RAW_SHA256:
        raise RuntimeError("R2-E 回放期间封存 raw 发生变化")
    if sha256_file(I2_PREFLIGHT_PATH) != I2_PREFLIGHT_SHA256:
        raise RuntimeError("R2-E 回放期间 I2-C preflight 发生变化")
    if sha256_file(R1C_DIAGNOSTIC_PATH) != R1C_DIAGNOSTIC_SHA256:
        raise RuntimeError("R2-E 回放期间 R1-C 诊断发生变化")

    removed_count = sum(item["old_duration_gate_removed"] for item in records)
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    next_gate_rejected_count = sum(
        item["automatic_classification"]
        == "old_duration_gate_removed_then_next_gate_rejected"
        for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R2-E",
        "mode": "zero_call_targeted_duration_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_sha256": SEALED_RAW_SHA256,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_sha256": I2_PREFLIGHT_SHA256,
        "source_r1c_diagnostic_path": str(R1C_DIAGNOSTIC_PATH),
        "source_r1c_diagnostic_sha256": R1C_DIAGNOSTIC_SHA256,
        "target_case_ids": list(R2E_TARGET_CASE_IDS),
        "model_risk_case_ids": list(R2E_MODEL_RISK_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "responses_were_generated_before_prompt_v3": True,
            "prompt_v3_real_model_behavior_evaluated": False,
            "service_acceptance_proves_content_quality": False,
            "r15_r19_require_future_human_quality_review": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "old_duration_gate_removed_count": removed_count,
            "old_duration_gate_still_rejected_count": len(records)
            - removed_count,
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": next_gate_rejected_count,
            "future_human_quality_review_case_count": len(
                R2E_MODEL_RISK_CASE_IDS
            ),
        },
        "pricing_gate_allowed": False,
        "quality_conclusion_allowed": False,
        "human_or_service_adjudication_required": True,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "adapter_instantiated": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
        "diagnostic_write_count": 1,
        "raw_response_copied": False,
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": historical_after,
    }


def write_r1c_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R1-C 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R1-C 诊断已经存在，拒绝覆盖") from None


def write_r2e_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R2-E 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R2-E 诊断已经存在，拒绝覆盖") from None


def _replay_plans(
    raw: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[list[Any] | None]]:
    source_records = _source_records(raw, "plan_records")
    attempts = _source_attempts(raw)
    replay_records: list[dict[str, Any]] = []
    parsed_plans: list[list[Any] | None] = []
    for index, case in enumerate(V5_PLAN_JDS):
        case_id = f"P{index:02d}"
        source = source_records[case_id]
        attempt = attempts[case_id]
        content = attempt["raw_response"]
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, index)
        )
        try:
            criteria, warnings = job_evaluation_plan_service._parse_v5_plan_response(
                content,
                snapshot,
            )
        except JobEvaluationPlanContentError as exc:
            parsed_plans.append(None)
            replay_records.append(
                {
                    "case_id": case_id,
                    "source_status": source["status"],
                    "source_error_code": source.get("error_code"),
                    "raw_response_available": True,
                    "raw_response_sha256": _response_sha256(content),
                    "raw_response_length": len(content),
                    "current_status": "failed",
                    "current_error_code": exc.code,
                    "current_error_message": str(exc),
                    "criteria_count": 0,
                    "all_criteria_traceable": False,
                    "automatic_classification": "current_plan_service_rejected",
                }
            )
            continue
        parsed_plans.append(criteria)
        replay_records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "raw_response_available": True,
                "raw_response_sha256": _response_sha256(content),
                "raw_response_length": len(content),
                "current_status": "succeeded",
                "current_error_code": None,
                "current_error_message": None,
                "criteria_count": len(criteria),
                "warning_codes": [warning.code.value for warning in warnings],
                "all_criteria_traceable": all(item.sources for item in criteria),
                "automatic_classification": "accepted_by_current_plan_service",
            }
        )
    return replay_records, parsed_plans


def _replay_report_case(
    *,
    case_id: str,
    pair: dict[str, Any],
    plan_criteria: list[Any] | None,
    source: dict[str, Any],
    attempt: dict[str, Any] | None,
    plan_index: int,
) -> dict[str, Any]:
    if attempt is None:
        return {
            "case_id": case_id,
            "source_status": source["status"],
            "source_error_code": source.get("error_code"),
            "raw_response_available": False,
            "current_status": "not_replayable",
            "current_error_code": None,
            "current_error_message": "封存 raw 没有该 case 的模型响应",
            "automatic_classification": "no_source_response",
        }
    content = attempt["raw_response"]
    base = {
        "case_id": case_id,
        "source_status": source["status"],
        "source_error_code": source.get("error_code"),
        "raw_response_available": True,
        "raw_response_sha256": _response_sha256(content),
        "raw_response_length": len(content),
    }
    if plan_criteria is None:
        return {
            **base,
            "current_status": "blocked",
            "current_error_code": "CURRENT_PLAN_NOT_LEGAL",
            "current_error_message": "当前计划回放未通过，不能检查报告响应",
            "automatic_classification": "blocked_by_current_plan",
        }
    snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
        _job(V5_PLAN_JDS[plan_index], plan_index)
    )
    sanitized = screening_evaluation_service.sanitize_resume_text(
        pair["resume_text"]
    )
    facts = experience_period_service.build(
        sanitized,
        evaluation_reference_at=REFERENCE_AT,
    )
    evaluation_plan = {
        "schema_version": "5.0",
        "criteria": [item.model_dump(mode="json") for item in plan_criteria],
    }
    try:
        report = screening_evaluation_service.parse_and_validate_v5_output(
            content,
            evaluation_plan=evaluation_plan,
            sanitized_resume=sanitized,
            experience_period_facts=facts,
        )
    except ScreeningEvaluationServiceError as exc:
        return {
            **base,
            "current_status": "failed",
            "current_error_code": exc.code,
            "current_error_message": str(exc),
            "automatic_classification": (
                "current_report_service_rejected_requires_adjudication"
            ),
        }
    nonzero = [
        item.assessment
        for item in report.criterion_assessments
        if item.assessment.score > 0
    ]
    return {
        **base,
        "current_status": "succeeded",
        "current_error_code": None,
        "current_error_message": None,
        "overall_score": report.overall_score,
        "nonzero_assessment_count": len(nonzero),
        "nonzero_with_evidence_count": sum(bool(item.evidence) for item in nonzero),
        "all_required_sections": bool(
            report.strengths
            and report.gaps
            and report.risks_or_conflicts
            and report.missing_info
            and report.hr_follow_up_questions
        ),
        "automatic_safety_and_grounding_checks_passed": True,
        "automatic_classification": "accepted_by_current_report_service",
    }


def _replay_reports_and_stability(
    raw: dict[str, Any],
    parsed_plans: list[list[Any] | None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attempts = _source_attempts(raw)
    report_sources = _source_records(raw, "report_records")
    stability_sources = _source_records(raw, "stability_records")
    report_records: list[dict[str, Any]] = []
    for sample_index, pair in enumerate(V5_REPORT_PAIRS):
        case_id = f"R{sample_index:02d}"
        plan_index = _plan_case_index(pair)
        report_records.append(
            _replay_report_case(
                case_id=case_id,
                pair=pair,
                plan_criteria=parsed_plans[plan_index],
                source=report_sources[case_id],
                attempt=attempts.get(case_id),
                plan_index=plan_index,
            )
        )
    stability_records: list[dict[str, Any]] = []
    for sample_index in V5_STABILITY_SAMPLE_INDICES:
        pair = V5_REPORT_PAIRS[sample_index]
        plan_index = _plan_case_index(pair)
        for run_number in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1):
            case_id = f"S{sample_index:02d}-{run_number}"
            stability_records.append(
                _replay_report_case(
                    case_id=case_id,
                    pair=pair,
                    plan_criteria=parsed_plans[plan_index],
                    source=stability_sources[case_id],
                    attempt=attempts.get(case_id),
                    plan_index=plan_index,
                )
            )
    return report_records, stability_records


def _category_summary(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_case_count": len(records),
        "source_response_count": sum(item["raw_response_available"] for item in records),
        "current_succeeded_count": sum(
            item["current_status"] == "succeeded" for item in records
        ),
        "current_failed_count": sum(
            item["current_status"] == "failed" for item in records
        ),
        "current_blocked_count": sum(
            item["current_status"] == "blocked" for item in records
        ),
        "not_replayable_count": sum(
            item["current_status"] == "not_replayable" for item in records
        ),
    }


async def build_preflight_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle_before = validate_result_lifecycle(run_id=ACTIVE_RUN_ID)
    if lifecycle_before["state"] not in {
        "i2_not_started",
        "i2_preflight_complete",
    }:
        raise RuntimeError("I2-C 只允许在 preflight 之前或完成状态下只读复核")
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    plan_records, parsed_plans = _replay_plans(raw)
    report_records, stability_records = _replay_reports_and_stability(
        raw,
        parsed_plans,
    )
    plan_summary = _category_summary(plan_records)
    report_summary = _category_summary(report_records)
    stability_summary = _category_summary(stability_records)
    remaining_rejections = (
        plan_summary["current_failed_count"]
        + report_summary["current_failed_count"]
        + report_summary["current_blocked_count"]
        + stability_summary["current_failed_count"]
        + stability_summary["current_blocked_count"]
    )
    stop_reasons: list[str] = []
    if plan_summary["current_succeeded_count"] != 10:
        stop_reasons.append("current_plan_service_did_not_accept_all_10")
    if report_summary["current_failed_count"] or report_summary["current_blocked_count"]:
        stop_reasons.append("report_rejections_require_service_or_content_adjudication")
    if stability_summary["current_failed_count"] or stability_summary["current_blocked_count"]:
        stop_reasons.append("stability_rejections_require_service_or_content_adjudication")
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("I2-C 回放期间 13 份历史证据发生变化")
    if sha256_file(source_path) != SEALED_RAW_SHA256:
        raise RuntimeError("I2-C 回放期间封存 raw 发生变化")
    return {
        "stage": ACTIVE_RUN_ID,
        "mode": "zero_call_full_category_preflight",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_sha256": SEALED_RAW_SHA256,
        "source_raw_attempt_count": len(raw["attempt_audit"]),
        "fixture": fixture,
        "execution_contract": execution_contract(),
        "lifecycle_before": lifecycle_before,
        "plan_records": plan_records,
        "report_records": report_records,
        "stability_records": stability_records,
        "summaries": {
            "plans": plan_summary,
            "reports": report_summary,
            "stability": stability_summary,
        },
        "replayed_source_response_count": (
            plan_summary["source_response_count"]
            + report_summary["source_response_count"]
            + stability_summary["source_response_count"]
        ),
        "remaining_current_service_rejection_count": remaining_rejections,
        "stop_reasons": stop_reasons,
        "pricing_gate_allowed": not stop_reasons,
        "human_or_service_adjudication_required": bool(stop_reasons),
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "adapter_instantiated": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 1,
        "quality_conclusion_allowed": False,
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": historical_after,
    }


async def main() -> None:
    validate_result_lifecycle(
        run_id=ACTIVE_RUN_ID,
        expected_state="i2_not_started",
    )
    payload = await build_preflight_payload()
    write_new_json(
        I2_PREFLIGHT_PATH,
        payload,
        run_id=ACTIVE_RUN_ID,
        expected_state="i2_not_started",
    )
    print(
        json.dumps(
            {
                "path": str(I2_PREFLIGHT_PATH),
                "summaries": payload["summaries"],
                "stop_reasons": payload["stop_reasons"],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r1c_main() -> None:
    payload = await build_r1c_replay_payload()
    write_r1c_diagnostic(R1C_DIAGNOSTIC_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(R1C_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r2e_main() -> None:
    payload = await build_r2e_replay_payload()
    write_r2e_diagnostic(R2E_DIAGNOSTIC_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(R2E_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    if "--r2e" in sys.argv[1:]:
        asyncio.run(r2e_main())
    elif "--r1c" in sys.argv[1:]:
        asyncio.run(r1c_main())
    else:
        asyncio.run(main())
