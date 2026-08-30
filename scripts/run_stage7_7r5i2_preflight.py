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
    I2_PREFLIGHT_PATH,
    I2_RAW_RESULT_PATH,
    RAW_RESULT_PATH,
    execution_contract,
    validate_frozen_fixture,
    validate_historical_results,
    validate_result_lifecycle,
    validate_sealed_raw_identity,
    write_new_json,
)
from tests.fixtures.v5_quality_samples import (  # noqa: E402
    V5_PLAN_JDS,
    V5_REPORT_PAIRS,
    V5_STABILITY_SAMPLE_INDICES,
    V5_STABILITY_RUNS_PER_SAMPLE,
)


REFERENCE_AT = datetime(2026, 8, 27, 0, 0, tzinfo=timezone.utc)
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
R3D_TARGET_CASE_IDS = ("R07", "R10", "R16", "R18", "R19", "S04-2")
R3D_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-29-stage7-7r5i2-r3d-no-evidence-replay.json"
)
OLD_NO_EVIDENCE_GATE_MESSAGE = (
    "无直接证据的报告结论只能表达缺口、风险或待核实信息"
)
R4C_TARGET_CASE_IDS = ("R07", "R00", "S00-2")
R4C_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-29-stage7-7r5i2-r4c-sensitive-replay.json"
)
OLD_SENSITIVE_GATE_MESSAGE = "5.0 AI 初筛输出包含不得参与评价的敏感个人属性"
R5D_TARGET_CASE_IDS = (
    "R04",
    "R06",
    "R09",
    "R15",
    "R16",
    "R17",
    "R18",
    "S00-1",
    "S00-3",
    "S04-1",
    "S04-3",
)
R5D_KNOWN_MODEL_RISK_CASE_IDS = ("R06", "R15", "R16")
R5D_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-29-stage7-7r5i2-r5d-service-v5-replay.json"
)
R5D_PREVIOUS_GATE_SOURCES = {
    "R04": ("7R5-I2-C", "AI 初筛理由包含 Resume 无法支持的数值事实"),
    "R06": ("7R5-I2-C", "AI 初筛理由包含 Resume 无法支持的事实"),
    "R09": ("7R5-I2-R1-C", "5.0 单项高分与未发现证据说明方向明显矛盾"),
    "R15": ("7R5-I2-R2-E", "AI 初筛理由包含 Resume 无法支持的事实"),
    "R16": ("7R5-I2-R3-D", "5.0 综合说明包含当前 Resume 证据无法支持的事实"),
    "R17": ("7R5-I2-R2-E", "AI 初筛理由包含 Resume 无法支持的数值事实"),
    "R18": ("7R5-I2-R3-D", "5.0 综合说明包含当前 Resume 证据无法支持的事实"),
    "S00-1": ("7R5-I2-R2-E", "AI 初筛理由与引用证据缺少可核对联系"),
    "S00-3": ("7R5-I2-R2-E", "5.0 单项高分与未发现证据说明方向明显矛盾"),
    "S04-1": ("7R5-I2-C", "AI 初筛理由包含 Resume 无法支持的数值事实"),
    "S04-3": ("7R5-I2-R2-E", "AI 初筛理由包含 Resume 无法支持的数值事实"),
}
R6D_TARGET_CASE_IDS = (
    "R00",
    "R04",
    "R05",
    "R06",
    "R07",
    "R09",
    "R10",
    "R14",
    "R15",
    "R16",
    "R17",
    "R18",
    "R19",
    "S00-1",
    "S00-2",
    "S00-3",
    "S04-1",
    "S04-2",
    "S04-3",
)
R6D_MISSING_REPORT_CASE_IDS = (
    "R01",
    "R02",
    "R03",
    "R08",
    "R11",
    "R12",
    "R13",
)
R6D_MISSING_STABILITY_CASE_IDS = (
    "S01-1",
    "S01-2",
    "S01-3",
    "S02-1",
    "S02-2",
    "S02-3",
    "S03-1",
    "S03-2",
    "S03-3",
)
R6D_KNOWN_MODEL_RISKS = {
    "R06": "评价点年限与报告年限结论仍需人工核对",
    "R14": "五个报告分区的完整性和内容价值仍需人工核对",
    "R15": "报告内部年限结论仍需人工核对",
    "R16": "能力迁移推断仍需人工核对",
    "R19": "既有模型内容风险仍需人工核对",
}
R6D_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-29-stage7-7r5i2-r6d-service-v6-full-replay.json"
)
R7D_TARGET_CASE_IDS = (
    "R00",
    "S00-1",
    "S00-2",
    "S00-3",
    "S04-2",
    "S04-3",
)
R7D_DIAGNOSTIC_PATH = (
    R1C_DIAGNOSTIC_DIR
    / "2026-08-29-stage7-7r5i2-r7d-time-key-service-v7-replay.json"
)
R7D_OLD_KEYWORD_GATE_MESSAGE = "非经历时间评价点不得引用经历时间事实"
R7D_NEXT_DETERMINISTIC_GATE_MESSAGE = (
    "引用经历时间事实时必须提供 calculation_note"
)
R6D_PREVIOUS_SOURCES = {
    "R00": ("7R5-I2-R4-C", "succeeded", None),
    "R04": ("7R5-I2-R5-D", "succeeded", None),
    "R05": ("7R5-I2-R2-E", "succeeded", None),
    "R06": ("7R5-I2-R5-D", "succeeded", None),
    "R07": ("7R5-I2-R4-C", "succeeded", None),
    "R09": ("7R5-I2-R5-D", "succeeded", None),
    "R10": ("7R5-I2-R3-D", "succeeded", None),
    "R14": ("7R5-I2-C", "succeeded", None),
    "R15": ("7R5-I2-R5-D", "succeeded", None),
    "R16": (
        "7R5-I2-R5-D",
        "failed",
        "AI 初筛理由包含 Resume 无法支持的数值事实",
    ),
    "R17": ("7R5-I2-R5-D", "succeeded", None),
    "R18": ("7R5-I2-R5-D", "succeeded", None),
    "R19": ("7R5-I2-R3-D", "succeeded", None),
    "S00-1": ("7R5-I2-R5-D", "succeeded", None),
    "S00-2": ("7R5-I2-R4-C", "succeeded", None),
    "S00-3": (
        "7R5-I2-R5-D",
        "failed",
        "AI 初筛理由包含 Resume 无法支持的数值事实",
    ),
    "S04-1": ("7R5-I2-R5-D", "succeeded", None),
    "S04-2": ("7R5-I2-R3-D", "succeeded", None),
    "S04-3": ("7R5-I2-R5-D", "succeeded", None),
}


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
    validate_sealed_raw_identity(source_path)
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


def _load_i2_raw(source_path: Path = I2_RAW_RESULT_PATH) -> dict[str, Any]:
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("R7-D 无法读取 I2-E raw") from None
    if raw.get("stage") != ACTIVE_RUN_ID or raw.get("mode") != "real_raw":
        raise RuntimeError("R7-D 只接受登记的 7R5-I2 real raw")

    expected_case_ids = {
        "plan_records": [f"P{index:02d}" for index in range(10)],
        "report_records": [f"R{index:02d}" for index in range(20)],
        "stability_records": [
            f"S{index:02d}-{run}"
            for index in V5_STABILITY_SAMPLE_INDICES
            for run in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1)
        ],
    }
    for key, case_ids in expected_case_ids.items():
        records = raw.get(key)
        if not isinstance(records, list) or [
            item.get("case_id") for item in records if isinstance(item, dict)
        ] != case_ids:
            raise RuntimeError(f"R7-D I2 raw 的 {key} case 身份或分母不完整")

    fixture = raw.get("fixture")
    if (
        not isinstance(fixture, dict)
        or fixture.get("hashes", {}).get("fixture") != FROZEN_FIXTURE_SHA256
    ):
        raise RuntimeError("R7-D I2 raw 未绑定冻结 fixture")
    source_contract = raw.get("execution_contract")
    if (
        not isinstance(source_contract, dict)
        or source_contract.get("report_prompt_version")
        != "screening_evaluation_lightweight_v3"
        or source_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v6"
    ):
        raise RuntimeError("R7-D I2 raw 的原始 Prompt/Service 身份不匹配")

    attempts = raw.get("attempt_audit")
    all_case_ids = [
        *expected_case_ids["plan_records"],
        *expected_case_ids["report_records"],
        *expected_case_ids["stability_records"],
    ]
    if (
        not isinstance(attempts, list)
        or len(attempts) != 45
        or {item.get("case_id") for item in attempts if isinstance(item, dict)}
        != set(all_case_ids)
        or any(
            item.get("attempt_number") != 1
            or item.get("result") != "succeeded"
            or not isinstance(item.get("raw_response"), str)
            for item in attempts
            if isinstance(item, dict)
        )
    ):
        raise RuntimeError("R7-D I2 raw 的 45 次响应身份或分母不完整")
    return raw


def _i2_raw_identity(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": raw["stage"],
        "mode": raw["mode"],
        "plan_case_count": len(raw["plan_records"]),
        "report_case_count": len(raw["report_records"]),
        "stability_case_count": len(raw["stability_records"]),
        "attempt_count": len(raw["attempt_audit"]),
        "report_prompt_version": raw["execution_contract"][
            "report_prompt_version"
        ],
        "report_service_behavior_version": raw["execution_contract"][
            "report_service_behavior_version"
        ],
    }


def _source_records(raw: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {item["case_id"]: item for item in raw[key]}


def _source_attempts(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["case_id"]: item for item in raw["attempt_audit"]}


def _load_source_preflight() -> dict[str, Any]:
    if not I2_PREFLIGHT_PATH.exists():
        raise RuntimeError("I2 定向诊断缺少受保护的 I2-C preflight")
    try:
        payload = json.loads(I2_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("I2 定向诊断无法读取 I2-C preflight") from None
    if (
        payload.get("stage") != ACTIVE_RUN_ID
        or payload.get("mode") != "zero_call_full_category_preflight"
    ):
        raise RuntimeError("I2 定向诊断的 I2-C preflight 身份不匹配")
    expected_ids = {
        "plan_records": [f"P{index:02d}" for index in range(10)],
        "report_records": [f"R{index:02d}" for index in range(20)],
        "stability_records": [
            f"S{index:02d}-{run}"
            for index in V5_STABILITY_SAMPLE_INDICES
            for run in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1)
        ],
    }
    for key, case_ids in expected_ids.items():
        records = payload.get(key)
        if not isinstance(records, list) or [
            item.get("case_id") for item in records if isinstance(item, dict)
        ] != case_ids:
            raise RuntimeError(f"I2-C preflight 的 {key} case 身份或分母不完整")
    return payload


def _load_source_r1c_diagnostic() -> dict[str, Any]:
    if not R1C_DIAGNOSTIC_PATH.exists():
        raise RuntimeError("R2-E 缺少受保护的 R1-C 诊断")
    try:
        payload = json.loads(R1C_DIAGNOSTIC_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("R2-E 无法读取 R1-C 诊断") from None
    records = payload.get("records")
    if (
        payload.get("stage") != ACTIVE_RUN_ID
        or payload.get("batch") != "7R5-I2-R1-C"
        or payload.get("mode") != "zero_call_targeted_structure_replay"
        or payload.get("target_case_ids") != list(R1C_TARGET_CASE_IDS)
        or not isinstance(records, list)
        or [item.get("case_id") for item in records if isinstance(item, dict)]
        != list(R1C_TARGET_CASE_IDS)
    ):
        raise RuntimeError("R2-E/R3-D 的 R1-C 诊断身份或分母不匹配")
    return payload


def _load_source_r2e_diagnostic() -> dict[str, Any]:
    if not R2E_DIAGNOSTIC_PATH.exists():
        raise RuntimeError("R3-D 缺少受保护的 R2-E 诊断")
    try:
        payload = json.loads(R2E_DIAGNOSTIC_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("R3-D 无法读取 R2-E 诊断") from None
    records = payload.get("records")
    if (
        payload.get("stage") != ACTIVE_RUN_ID
        or payload.get("batch") != "7R5-I2-R2-E"
        or payload.get("mode") != "zero_call_targeted_duration_replay"
        or payload.get("target_case_ids") != list(R2E_TARGET_CASE_IDS)
        or not isinstance(records, list)
        or [item.get("case_id") for item in records if isinstance(item, dict)]
        != list(R2E_TARGET_CASE_IDS)
    ):
        raise RuntimeError("R3-D 的 R2-E 诊断身份或分母不匹配")
    return payload


def _load_historical_replay_diagnostic(
    *,
    path: Path,
    batch: str,
    mode: str,
    target_case_ids: tuple[str, ...],
    expected_summary: dict[str, int],
) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"R4-B 缺少已封存的 {batch} 诊断")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError(f"R4-B 无法读取已封存的 {batch} 诊断") from None

    records = payload.get("records")
    if (
        payload.get("stage") != "7R5-I2"
        or payload.get("batch") != batch
        or payload.get("mode") != mode
        or payload.get("target_case_ids") != list(target_case_ids)
        or not isinstance(records, list)
        or [item.get("case_id") for item in records if isinstance(item, dict)]
        != list(target_case_ids)
        or payload.get("summary") != expected_summary
    ):
        raise RuntimeError(f"已封存的 {batch} 诊断身份、分母或结论不完整")

    serialized = json.dumps(payload, ensure_ascii=False)
    if any(
        marker in serialized
        for marker in (
            '"raw_response"',
            "DEEPSEEK_API_KEY",
            "chain_of_thought",
            "stack_trace",
        )
    ):
        raise RuntimeError(f"已封存的 {batch} 诊断包含禁止复制的敏感内容")
    if (
        payload.get("real_model_call_count") != 0
        or payload.get("api_attempt_count") != 0
        or payload.get("api_key_read") is not False
        or payload.get("adapter_instantiated") is not False
        or payload.get("postgresql_write_count") != 0
        or payload.get("formal_result_write_count") != 0
        or payload.get("diagnostic_write_count") != 1
        or payload.get("raw_response_copied") is not False
        or payload.get("pricing_gate_allowed") is not False
        or payload.get("quality_conclusion_allowed") is not False
    ):
        raise RuntimeError(f"已封存的 {batch} 诊断零调用或质量限制合同不完整")
    return payload


def load_r1c_diagnostic(path: Path = R1C_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R1-C",
        mode="zero_call_targeted_structure_replay",
        target_case_ids=R1C_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 6,
            "quantity_gate_crossed_count": 6,
            "full_report_accepted_count": 0,
            "next_service_gate_rejected_count": 6,
            "current_schema_rejected_count": 0,
        },
    )
    if (
        payload.get("supporting_plan_case_ids") != ["P00", "P06", "P09"]
        or not all(
            record.get("current_schema_accepted") is True
            and record.get("quantity_gate_crossed") is True
            for record in payload["records"]
        )
    ):
        raise RuntimeError("已封存的 R1-C 诊断结构放宽结论不完整")
    return payload


def load_r2e_diagnostic(path: Path = R2E_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R2-E",
        mode="zero_call_targeted_duration_replay",
        target_case_ids=R2E_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 12,
            "old_duration_gate_removed_count": 12,
            "old_duration_gate_still_rejected_count": 0,
            "full_report_accepted_count": 1,
            "next_service_gate_rejected_count": 11,
            "future_human_quality_review_case_count": 2,
        },
    )
    if (
        payload.get("supporting_plan_case_ids") != ["P00", "P04", "P05", "P07"]
        or payload.get("model_risk_case_ids") != ["R15", "R19"]
        or not all(
            record.get("old_duration_gate_removed") is True
            for record in payload["records"]
        )
        or payload.get("replay_limitations")
        != {
            "responses_were_generated_before_prompt_v3": True,
            "prompt_v3_real_model_behavior_evaluated": False,
            "service_acceptance_proves_content_quality": False,
            "r15_r19_require_future_human_quality_review": True,
        }
    ):
        raise RuntimeError("已封存的 R2-E 诊断年限放宽结论或限制不完整")
    return payload


def load_r3d_diagnostic(path: Path = R3D_DIAGNOSTIC_PATH) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError("R4-B 缺少已封存的 R3-D 诊断")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("R4-B 无法读取已封存的 R3-D 诊断") from None
    expected_summary = {
        "target_case_count": 6,
        "old_no_evidence_gate_removed_count": 6,
        "old_no_evidence_gate_still_rejected_count": 0,
        "full_report_accepted_count": 3,
        "next_service_gate_rejected_count": 3,
        "future_human_quality_review_case_count": 6,
    }
    records = payload.get("records")
    if (
        payload.get("stage") != "7R5-I2"
        or payload.get("batch") != "7R5-I2-R3-D"
        or payload.get("mode") != "zero_call_targeted_no_evidence_replay"
        or payload.get("target_case_ids") != list(R3D_TARGET_CASE_IDS)
        or not isinstance(records, list)
        or [item.get("case_id") for item in records if isinstance(item, dict)]
        != list(R3D_TARGET_CASE_IDS)
        or payload.get("summary") != expected_summary
    ):
        raise RuntimeError("已封存的 R3-D 诊断身份、分母或结论不完整")
    serialized = json.dumps(payload, ensure_ascii=False)
    if any(
        marker in serialized
        for marker in (
            '"raw_response"',
            "DEEPSEEK_API_KEY",
            "chain_of_thought",
            "stack_trace",
        )
    ):
        raise RuntimeError("已封存的 R3-D 诊断包含禁止复制的敏感内容")
    if (
        payload.get("real_model_call_count") != 0
        or payload.get("api_attempt_count") != 0
        or payload.get("api_key_read") is not False
        or payload.get("adapter_instantiated") is not False
        or payload.get("postgresql_write_count") != 0
        or payload.get("formal_result_write_count") != 0
        or payload.get("diagnostic_write_count") != 1
        or payload.get("raw_response_copied") is not False
        or payload.get("pricing_gate_allowed") is not False
        or payload.get("quality_conclusion_allowed") is not False
        or payload.get("replay_limitations")
        != {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "future_human_quality_review_required": True,
        }
    ):
        raise RuntimeError("已封存的 R3-D 诊断零调用或质量限制合同不完整")
    return payload


def load_r4c_diagnostic(path: Path = R4C_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R4-C",
        mode="zero_call_targeted_sensitive_replay",
        target_case_ids=R4C_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 3,
            "old_sensitive_gate_removed_count": 3,
            "old_sensitive_gate_still_rejected_count": 0,
            "full_report_accepted_count": 3,
            "next_service_gate_rejected_count": 0,
            "future_human_quality_review_case_count": 3,
        },
    )
    if (
        payload.get("supporting_plan_case_ids") != ["P00", "P07"]
        or not all(
            record.get("old_sensitive_gate_removed") is True
            for record in payload["records"]
        )
        or payload.get("replay_limitations")
        != {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "protected_attribute_semantics_evaluated": False,
            "future_human_quality_review_required": True,
        }
    ):
        raise RuntimeError("已封存的 R4-C 诊断敏感门禁结论或限制不完整")
    return payload


def load_r5d_diagnostic(path: Path = R5D_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R5-D",
        mode="zero_call_remaining_service_v5_replay",
        target_case_ids=R5D_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 11,
            "previous_service_gate_removed_count": 11,
            "previous_service_gate_still_rejected_count": 0,
            "full_report_accepted_count": 9,
            "next_service_gate_rejected_count": 2,
            "future_human_quality_review_case_count": 11,
        },
    )
    records = payload["records"]
    if (
        payload.get("supporting_plan_case_ids")
        != ["P00", "P04", "P06", "P07", "P09"]
        or payload.get("known_model_risk_case_ids") != ["R06", "R15", "R16"]
        or payload.get("execution_contract", {}).get(
            "report_service_behavior_version"
        )
        != "lightweight_report_generation_v5"
        or not all(
            record.get("previous_service_gate_removed") is True
            and record.get("future_human_quality_review_required") is True
            for record in records
        )
        or {
            record["case_id"]
            for record in records
            if record.get("current_report_status") == "failed"
        }
        != {"R16", "S00-3"}
        or payload.get("replay_limitations")
        != {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "known_model_content_risks_resolved": False,
            "future_human_quality_review_required": True,
        }
    ):
        raise RuntimeError("已封存的 R5-D 诊断回放结论或限制不完整")
    return payload


def load_r6d_diagnostic(path: Path = R6D_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R6-D",
        mode="zero_call_service_v6_full_replay",
        target_case_ids=R6D_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 19,
            "report_response_count": 13,
            "stability_response_count": 6,
            "missing_report_response_count": 7,
            "missing_stability_response_count": 9,
            "previously_accepted_count": 17,
            "previously_rejected_count": 2,
            "old_free_text_source_gate_target_count": 2,
            "old_free_text_source_gate_removed_count": 2,
            "old_free_text_source_gate_still_rejected_count": 0,
            "full_report_accepted_count": 19,
            "next_service_gate_rejected_count": 0,
            "future_human_quality_review_case_count": 19,
        },
    )
    records = payload["records"]
    if (
        payload.get("missing_report_case_ids")
        != list(R6D_MISSING_REPORT_CASE_IDS)
        or payload.get("missing_stability_case_ids")
        != list(R6D_MISSING_STABILITY_CASE_IDS)
        or payload.get("known_model_risk_case_ids")
        != list(R6D_KNOWN_MODEL_RISKS)
        or payload.get("execution_contract", {}).get(
            "report_service_behavior_version"
        )
        != "lightweight_report_generation_v6"
        or not all(
            record.get("current_report_status") == "succeeded"
            and record.get("future_human_quality_review_required") is True
            for record in records
        )
        or {
            record["case_id"]
            for record in records
            if record.get("previous_free_text_source_gate") is True
        }
        != {"R16", "S00-3"}
        or not all(
            record.get("old_free_text_source_gate_removed") is True
            for record in records
            if record.get("previous_free_text_source_gate") is True
        )
        or payload.get("replay_limitations")
        != {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "known_model_content_risks_resolved": False,
            "missing_responses_were_reconstructed": False,
            "future_human_quality_review_required": True,
        }
    ):
        raise RuntimeError("已封存的 R6-D 诊断回放结论或限制不完整")
    return payload


def load_r7d_diagnostic(path: Path = R7D_DIAGNOSTIC_PATH) -> dict[str, Any]:
    payload = _load_historical_replay_diagnostic(
        path=path,
        batch="7R5-I2-R7-D",
        mode="zero_call_time_key_service_v7_replay",
        target_case_ids=R7D_TARGET_CASE_IDS,
        expected_summary={
            "target_case_count": 6,
            "report_response_count": 1,
            "stability_response_count": 5,
            "old_keyword_gate_target_count": 6,
            "old_keyword_gate_removed_count": 6,
            "old_keyword_gate_still_rejected_count": 0,
            "full_report_accepted_count": 0,
            "next_deterministic_gate_rejected_count": 6,
            "missing_calculation_note_count": 6,
            "future_human_quality_review_case_count": 6,
        },
    )
    records = payload["records"]
    if (
        payload.get("supporting_plan_case_ids") != ["P00", "P04"]
        or payload.get("source_raw_identity")
        != {
            "stage": "7R5-I2",
            "mode": "real_raw",
            "plan_case_count": 10,
            "report_case_count": 20,
            "stability_case_count": 15,
            "attempt_count": 45,
            "report_prompt_version": "screening_evaluation_lightweight_v3",
            "report_service_behavior_version": "lightweight_report_generation_v6",
        }
        or payload.get("execution_contract", {}).get(
            "report_service_behavior_version"
        )
        != "lightweight_report_generation_v7"
        or not all(
            record.get("source_status") == "failed"
            and record.get("source_error_message")
            == R7D_OLD_KEYWORD_GATE_MESSAGE
            and record.get("old_keyword_gate_removed") is True
            and record.get("current_report_status") == "failed"
            and record.get("current_report_error_message")
            == R7D_NEXT_DETERMINISTIC_GATE_MESSAGE
            and record.get("missing_calculation_note_after_keyword_gate") is True
            and record.get("future_human_quality_review_required") is True
            and isinstance(record.get("raw_response_sha256"), str)
            and len(record["raw_response_sha256"]) == 64
            and record.get("raw_response_length", 0) > 0
            for record in records
        )
        or payload.get("replay_limitations")
        != {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "prompt_v4_was_applied_to_old_responses": False,
            "time_key_content_was_corrected": False,
            "future_human_quality_review_required": True,
        }
    ):
        raise RuntimeError("已封存的 R7-D 诊断回放结论或限制不完整")
    return payload


def _preflight_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": payload["stage"],
        "mode": payload["mode"],
        "plan_case_count": len(payload["plan_records"]),
        "report_case_count": len(payload["report_records"]),
        "stability_case_count": len(payload["stability_records"]),
    }


def _diagnostic_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": payload["stage"],
        "batch": payload["batch"],
        "mode": payload["mode"],
        "target_case_ids": list(payload["target_case_ids"]),
    }


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
    raise RuntimeError(
        "R1-C 已封存；行为版本升级后只允许读取既有诊断，不得动态重建"
    )
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
    source_raw_identity = validate_sealed_raw_identity(source_path)
    source_preflight_identity = _preflight_identity(_load_source_preflight())
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
        "source_raw_identity": source_raw_identity,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": source_preflight_identity,
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
        "historical_results": historical_after,
    }


async def build_r2e_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    raise RuntimeError(
        "R2-E 已封存；行为版本升级后只允许读取既有诊断，不得动态重建"
    )
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
    source_raw_identity = validate_sealed_raw_identity(source_path)
    source_preflight_identity = _preflight_identity(_load_source_preflight())
    source_r1c_identity = _diagnostic_identity(_load_source_r1c_diagnostic())

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
        "source_raw_identity": source_raw_identity,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": source_preflight_identity,
        "source_r1c_diagnostic_path": str(R1C_DIAGNOSTIC_PATH),
        "source_r1c_diagnostic_identity": source_r1c_identity,
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
        "historical_results": historical_after,
    }


async def build_r3d_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    raise RuntimeError(
        "R3-D 已封存；行为版本升级后只允许读取既有诊断，不得动态重建"
    )
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
    source_r2e = _load_source_r2e_diagnostic()
    r2e_records = {item["case_id"]: item for item in source_r2e["records"]}
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v3"
    ):
        raise RuntimeError("R3-D 活动报告 Service 行为版本不是 v3")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R3D_TARGET_CASE_IDS:
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

        if case_id == "R10":
            previous = preflight_records.get(case_id)
            previous_gate_source = "7R5-I2-C"
            previous_status = previous.get("current_status") if previous else None
            previous_error_code = (
                previous.get("current_error_code") if previous else None
            )
            previous_error_message = (
                previous.get("current_error_message") if previous else None
            )
        elif case_id == "R16":
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
            previous = r2e_records.get(case_id)
            previous_gate_source = "7R5-I2-R2-E"
            previous_status = (
                previous.get("current_report_status") if previous else None
            )
            previous_error_code = (
                previous.get("current_report_error_code") if previous else None
            )
            previous_error_message = (
                previous.get("current_report_error_message") if previous else None
            )
        if previous is None:
            raise RuntimeError(f"R3-D 来源诊断缺少目标 case：{case_id}")
        if (
            previous_status != "failed"
            or previous_error_message != OLD_NO_EVIDENCE_GATE_MESSAGE
        ):
            raise RuntimeError(
                f"R3-D 目标 case 旧状态不是冻结无证据关键词拒绝：{case_id}"
            )

        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        old_gate_removed = (
            current.get("current_error_message") != OLD_NO_EVIDENCE_GATE_MESSAGE
        )
        if not old_gate_removed:
            classification = "old_no_evidence_gate_still_rejects"
        elif current["current_status"] == "succeeded":
            classification = "old_no_evidence_gate_removed_and_report_accepted"
        else:
            classification = "old_no_evidence_gate_removed_then_next_gate_rejected"
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
                "old_no_evidence_gate_removed": old_gate_removed,
                "future_human_quality_review_required": True,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R3-D 回放期间 13 份历史证据发生变化")
    source_raw_identity = validate_sealed_raw_identity(source_path)
    source_preflight_identity = _preflight_identity(_load_source_preflight())
    source_r1c_identity = _diagnostic_identity(_load_source_r1c_diagnostic())
    source_r2e_identity = _diagnostic_identity(_load_source_r2e_diagnostic())
    removed_count = sum(
        item["old_no_evidence_gate_removed"] for item in records
    )
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R3-D",
        "mode": "zero_call_targeted_no_evidence_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": source_raw_identity,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": source_preflight_identity,
        "source_r1c_diagnostic_path": str(R1C_DIAGNOSTIC_PATH),
        "source_r1c_diagnostic_identity": source_r1c_identity,
        "source_r2e_diagnostic_path": str(R2E_DIAGNOSTIC_PATH),
        "source_r2e_diagnostic_identity": source_r2e_identity,
        "target_case_ids": list(R3D_TARGET_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "future_human_quality_review_required": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "old_no_evidence_gate_removed_count": removed_count,
            "old_no_evidence_gate_still_rejected_count": len(records)
            - removed_count,
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": len(records) - accepted_count,
            "future_human_quality_review_case_count": len(records),
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
        "historical_results": historical_after,
    }


async def build_r4c_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    raise RuntimeError(
        "R4-C 已封存；行为版本升级后只允许读取既有诊断，不得动态重建"
    )
    lifecycle = validate_result_lifecycle(
        run_id=ACTIVE_RUN_ID,
        expected_state="i2_preflight_complete",
    )
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    source_preflight = _load_source_preflight()
    source_r2e = load_r2e_diagnostic()
    source_r3d = load_r3d_diagnostic()
    r2e_records = {item["case_id"]: item for item in source_r2e["records"]}
    r3d_records = {item["case_id"]: item for item in source_r3d["records"]}
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v4"
    ):
        raise RuntimeError("R4-C 活动报告 Service 行为版本不是 v4")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R4C_TARGET_CASE_IDS:
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

        if case_id == "R07":
            previous = r3d_records.get(case_id)
            previous_gate_source = "7R5-I2-R3-D"
        else:
            previous = r2e_records.get(case_id)
            previous_gate_source = "7R5-I2-R2-E"
        if previous is None:
            raise RuntimeError(f"R4-C 来源诊断缺少目标 case：{case_id}")
        previous_status = previous.get("current_report_status")
        previous_error_code = previous.get("current_report_error_code")
        previous_error_message = previous.get("current_report_error_message")
        if (
            previous_status != "failed"
            or previous_error_message != OLD_SENSITIVE_GATE_MESSAGE
        ):
            raise RuntimeError(
                f"R4-C 目标 case 旧状态不是冻结敏感门禁拒绝：{case_id}"
            )

        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        old_gate_removed = (
            current.get("current_error_message") != OLD_SENSITIVE_GATE_MESSAGE
        )
        if not old_gate_removed:
            classification = "old_sensitive_gate_still_rejects"
        elif current["current_status"] == "succeeded":
            classification = "old_sensitive_gate_removed_and_report_accepted"
        else:
            classification = "old_sensitive_gate_removed_then_next_gate_rejected"
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
                "old_sensitive_gate_removed": old_gate_removed,
                "future_human_quality_review_required": True,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R4-C 回放期间历史证据身份发生变化")
    source_raw_identity = validate_sealed_raw_identity(source_path)
    removed_count = sum(item["old_sensitive_gate_removed"] for item in records)
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R4-C",
        "mode": "zero_call_targeted_sensitive_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": source_raw_identity,
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": _preflight_identity(source_preflight),
        "source_r2e_diagnostic_path": str(R2E_DIAGNOSTIC_PATH),
        "source_r2e_diagnostic_identity": _diagnostic_identity(source_r2e),
        "source_r3d_diagnostic_path": str(R3D_DIAGNOSTIC_PATH),
        "source_r3d_diagnostic_identity": _diagnostic_identity(source_r3d),
        "target_case_ids": list(R4C_TARGET_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "protected_attribute_semantics_evaluated": False,
            "future_human_quality_review_required": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "old_sensitive_gate_removed_count": removed_count,
            "old_sensitive_gate_still_rejected_count": len(records)
            - removed_count,
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": len(records) - accepted_count,
            "future_human_quality_review_case_count": len(records),
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
        "historical_results": historical_after,
    }


def _validate_post_raw_readonly_lifecycle() -> dict[str, Any]:
    lifecycle = validate_result_lifecycle(run_id=ACTIVE_RUN_ID)
    if lifecycle["state"] not in {
        "i2_raw_complete",
        "i2_human_complete",
        "i2_final_complete",
    }:
        raise RuntimeError(
            "I2 post-raw 只读复核需要 raw、human 或 final 已封存"
        )
    return lifecycle


async def build_r5d_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle = _validate_post_raw_readonly_lifecycle()
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    source_preflight = _load_source_preflight()
    source_r1c = load_r1c_diagnostic()
    source_r2e = load_r2e_diagnostic()
    source_r3d = load_r3d_diagnostic()
    source_records = {
        "7R5-I2-C": {
            item["case_id"]: item
            for item in (
                list(source_preflight["report_records"])
                + list(source_preflight["stability_records"])
            )
        },
        "7R5-I2-R1-C": {
            item["case_id"]: item for item in source_r1c["records"]
        },
        "7R5-I2-R2-E": {
            item["case_id"]: item for item in source_r2e["records"]
        },
        "7R5-I2-R3-D": {
            item["case_id"]: item for item in source_r3d["records"]
        },
    }
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v5"
    ):
        raise RuntimeError("R5-D 活动报告 Service 行为版本不是 v5")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R5D_TARGET_CASE_IDS:
        previous_gate_source, previous_gate_error_message = (
            R5D_PREVIOUS_GATE_SOURCES[case_id]
        )
        previous = source_records[previous_gate_source].get(case_id)
        if previous is None:
            raise RuntimeError(f"R5-D 来源诊断缺少目标 case：{case_id}")
        previous_status = previous.get(
            "current_report_status",
            previous.get("current_status"),
        )
        previous_error_code = previous.get(
            "current_report_error_code",
            previous.get("current_error_code"),
        )
        actual_previous_error = previous.get(
            "current_report_error_message",
            previous.get("current_error_message"),
        )
        if (
            previous_status != "failed"
            or actual_previous_error != previous_gate_error_message
        ):
            raise RuntimeError(
                f"R5-D 目标 case 最近门禁与冻结来源不一致：{case_id}"
            )

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
        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        previous_service_gate_removed = (
            current.get("current_error_message") != previous_gate_error_message
        )
        if not previous_service_gate_removed:
            classification = "previous_service_gate_still_rejects"
        elif current["current_status"] == "succeeded":
            classification = "previous_service_gate_removed_and_report_accepted"
        else:
            classification = "previous_service_gate_removed_then_next_gate_rejected"
        known_model_content_risk = {
            "R06": "评价点年限与报告年限结论仍需人工核对",
            "R15": "报告内部年限结论仍需人工核对",
            "R16": "能力迁移推断仍需人工核对",
        }.get(case_id)
        records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "previous_gate_source": previous_gate_source,
                "previous_gate_status": previous_status,
                "previous_gate_error_code": previous_error_code,
                "previous_gate_error_message": actual_previous_error,
                "raw_response_sha256": _response_sha256(attempt["raw_response"]),
                "raw_response_length": len(attempt["raw_response"]),
                "current_report_status": current["current_status"],
                "current_report_error_code": current.get("current_error_code"),
                "current_report_error_message": current.get(
                    "current_error_message"
                ),
                "current_overall_score": current.get("overall_score"),
                "previous_service_gate_removed": previous_service_gate_removed,
                "known_model_content_risk": known_model_content_risk,
                "future_human_quality_review_required": True,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R5-D 回放期间历史证据身份发生变化")
    removed_count = sum(
        item["previous_service_gate_removed"] for item in records
    )
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R5-D",
        "mode": "zero_call_remaining_service_v5_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": validate_sealed_raw_identity(source_path),
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": _preflight_identity(source_preflight),
        "source_r1c_diagnostic_path": str(R1C_DIAGNOSTIC_PATH),
        "source_r1c_diagnostic_identity": _diagnostic_identity(source_r1c),
        "source_r2e_diagnostic_path": str(R2E_DIAGNOSTIC_PATH),
        "source_r2e_diagnostic_identity": _diagnostic_identity(source_r2e),
        "source_r3d_diagnostic_path": str(R3D_DIAGNOSTIC_PATH),
        "source_r3d_diagnostic_identity": _diagnostic_identity(source_r3d),
        "target_case_ids": list(R5D_TARGET_CASE_IDS),
        "known_model_risk_case_ids": list(R5D_KNOWN_MODEL_RISK_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "known_model_content_risks_resolved": False,
            "future_human_quality_review_required": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "previous_service_gate_removed_count": removed_count,
            "previous_service_gate_still_rejected_count": len(records)
            - removed_count,
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": len(records) - accepted_count,
            "future_human_quality_review_case_count": len(records),
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
        "historical_results": historical_after,
    }


async def build_r6d_replay_payload(
    *, source_path: Path = RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle = _validate_post_raw_readonly_lifecycle()
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_source_raw(source_path)
    source_preflight = _load_source_preflight()
    source_r1c = load_r1c_diagnostic()
    source_r2e = load_r2e_diagnostic()
    source_r3d = load_r3d_diagnostic()
    source_r4c = load_r4c_diagnostic()
    source_r5d = load_r5d_diagnostic()
    source_records = {
        "7R5-I2-C": {
            item["case_id"]: item
            for item in (
                list(source_preflight["report_records"])
                + list(source_preflight["stability_records"])
            )
        },
        "7R5-I2-R1-C": {
            item["case_id"]: item for item in source_r1c["records"]
        },
        "7R5-I2-R2-E": {
            item["case_id"]: item for item in source_r2e["records"]
        },
        "7R5-I2-R3-D": {
            item["case_id"]: item for item in source_r3d["records"]
        },
        "7R5-I2-R4-C": {
            item["case_id"]: item for item in source_r4c["records"]
        },
        "7R5-I2-R5-D": {
            item["case_id"]: item for item in source_r5d["records"]
        },
    }
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v6"
    ):
        raise RuntimeError("R6-D 活动报告 Service 行为版本不是 v6")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R6D_TARGET_CASE_IDS:
        previous_source, expected_status, expected_error = R6D_PREVIOUS_SOURCES[
            case_id
        ]
        previous = source_records[previous_source].get(case_id)
        if previous is None:
            raise RuntimeError(f"R6-D 最近合法来源缺少目标 case：{case_id}")
        previous_status = previous.get(
            "current_report_status",
            previous.get("current_status"),
        )
        previous_error_code = previous.get(
            "current_report_error_code",
            previous.get("current_error_code"),
        )
        previous_error_message = previous.get(
            "current_report_error_message",
            previous.get("current_error_message"),
        )
        if (
            previous_status != expected_status
            or previous_error_message != expected_error
        ):
            raise RuntimeError(
                f"R6-D 目标 case 最近合法来源状态不一致：{case_id}"
            )

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
        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        previous_free_text_source_gate = (
            case_id in {"R16", "S00-3"}
            and previous_status == "failed"
            and previous_error_message
            == "AI 初筛理由包含 Resume 无法支持的数值事实"
        )
        old_free_text_source_gate_removed = (
            previous_free_text_source_gate
            and current.get("current_error_message") != previous_error_message
        )
        if current["current_status"] == "succeeded":
            classification = "accepted_by_service_v6"
        elif previous_free_text_source_gate and not old_free_text_source_gate_removed:
            classification = "old_free_text_source_gate_still_rejects"
        else:
            classification = "next_structural_or_safety_gate_rejected"
        records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "previous_source": previous_source,
                "previous_status": previous_status,
                "previous_error_code": previous_error_code,
                "previous_error_message": previous_error_message,
                "previous_free_text_source_gate": previous_free_text_source_gate,
                "raw_response_sha256": _response_sha256(attempt["raw_response"]),
                "raw_response_length": len(attempt["raw_response"]),
                "current_report_status": current["current_status"],
                "current_report_error_code": current.get("current_error_code"),
                "current_report_error_message": current.get(
                    "current_error_message"
                ),
                "current_overall_score": current.get("overall_score"),
                "old_free_text_source_gate_removed": (
                    old_free_text_source_gate_removed
                    if previous_free_text_source_gate
                    else None
                ),
                "known_model_content_risk": R6D_KNOWN_MODEL_RISKS.get(case_id),
                "future_human_quality_review_required": True,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R6-D 回放期间历史证据身份发生变化")
    old_gate_records = [
        item for item in records if item["previous_free_text_source_gate"]
    ]
    old_gate_removed_count = sum(
        item["old_free_text_source_gate_removed"] for item in old_gate_records
    )
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R6-D",
        "mode": "zero_call_service_v6_full_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": validate_sealed_raw_identity(source_path),
        "source_preflight_path": str(I2_PREFLIGHT_PATH),
        "source_preflight_identity": _preflight_identity(source_preflight),
        "source_r1c_diagnostic_path": str(R1C_DIAGNOSTIC_PATH),
        "source_r1c_diagnostic_identity": _diagnostic_identity(source_r1c),
        "source_r2e_diagnostic_path": str(R2E_DIAGNOSTIC_PATH),
        "source_r2e_diagnostic_identity": _diagnostic_identity(source_r2e),
        "source_r3d_diagnostic_path": str(R3D_DIAGNOSTIC_PATH),
        "source_r3d_diagnostic_identity": _diagnostic_identity(source_r3d),
        "source_r4c_diagnostic_path": str(R4C_DIAGNOSTIC_PATH),
        "source_r4c_diagnostic_identity": _diagnostic_identity(source_r4c),
        "source_r5d_diagnostic_path": str(R5D_DIAGNOSTIC_PATH),
        "source_r5d_diagnostic_identity": _diagnostic_identity(source_r5d),
        "target_case_ids": list(R6D_TARGET_CASE_IDS),
        "missing_report_case_ids": list(R6D_MISSING_REPORT_CASE_IDS),
        "missing_stability_case_ids": list(R6D_MISSING_STABILITY_CASE_IDS),
        "known_model_risk_case_ids": list(R6D_KNOWN_MODEL_RISKS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "known_model_content_risks_resolved": False,
            "missing_responses_were_reconstructed": False,
            "future_human_quality_review_required": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "report_response_count": sum(
                item["case_id"].startswith("R") for item in records
            ),
            "stability_response_count": sum(
                item["case_id"].startswith("S") for item in records
            ),
            "missing_report_response_count": len(R6D_MISSING_REPORT_CASE_IDS),
            "missing_stability_response_count": len(
                R6D_MISSING_STABILITY_CASE_IDS
            ),
            "previously_accepted_count": sum(
                item["previous_status"] == "succeeded" for item in records
            ),
            "previously_rejected_count": sum(
                item["previous_status"] == "failed" for item in records
            ),
            "old_free_text_source_gate_target_count": len(old_gate_records),
            "old_free_text_source_gate_removed_count": old_gate_removed_count,
            "old_free_text_source_gate_still_rejected_count": (
                len(old_gate_records) - old_gate_removed_count
            ),
            "full_report_accepted_count": accepted_count,
            "next_service_gate_rejected_count": len(records) - accepted_count,
            "future_human_quality_review_case_count": len(records),
        },
        "pricing_gate_allowed": False,
        "quality_conclusion_allowed": False,
        "human_quality_review_required": True,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "adapter_instantiated": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
        "diagnostic_write_count": 1,
        "raw_response_copied": False,
        "historical_results": historical_after,
    }


async def build_r7d_replay_payload(
    *, source_path: Path = I2_RAW_RESULT_PATH
) -> dict[str, Any]:
    lifecycle = _validate_post_raw_readonly_lifecycle()
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    raw = _load_i2_raw(source_path)
    active_execution_contract = execution_contract()
    if (
        active_execution_contract.get("report_prompt_version")
        != "screening_evaluation_lightweight_v4"
        or active_execution_contract.get("report_service_behavior_version")
        != "lightweight_report_generation_v7"
    ):
        raise RuntimeError("R7-D 活动报告 Prompt/Service 行为版本不是 v4/v7")

    plan_cache: dict[int, list[Any]] = {}
    records: list[dict[str, Any]] = []
    for case_id in R7D_TARGET_CASE_IDS:
        source, attempt, sample_index = _target_case_context(
            case_id=case_id,
            raw=raw,
        )
        if (
            source.get("status") != "failed"
            or source.get("error_code")
            != "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT"
            or source.get("error_message") != R7D_OLD_KEYWORD_GATE_MESSAGE
        ):
            raise RuntimeError(f"R7-D 目标 case 原始错误身份不匹配：{case_id}")

        pair = V5_REPORT_PAIRS[sample_index]
        plan_index = _plan_case_index(pair)
        if plan_index not in plan_cache:
            plan_cache[plan_index] = _parse_supporting_plan(
                raw=raw,
                plan_index=plan_index,
            )
        current = _replay_report_case(
            case_id=case_id,
            pair=pair,
            plan_criteria=plan_cache[plan_index],
            source=source,
            attempt=attempt,
            plan_index=plan_index,
        )
        old_keyword_gate_removed = (
            current.get("current_error_message") != R7D_OLD_KEYWORD_GATE_MESSAGE
        )
        missing_calculation_note = (
            current.get("current_error_message")
            == R7D_NEXT_DETERMINISTIC_GATE_MESSAGE
        )
        if current["current_status"] == "succeeded":
            classification = "accepted_by_service_v7_requires_human_review"
        elif not old_keyword_gate_removed:
            classification = "old_keyword_gate_still_rejects"
        elif missing_calculation_note:
            classification = "next_deterministic_calculation_note_gate_rejected"
        else:
            classification = "next_structural_or_safety_gate_rejected"
        records.append(
            {
                "case_id": case_id,
                "source_status": source["status"],
                "source_error_code": source.get("error_code"),
                "source_error_message": source.get("error_message"),
                "raw_response_sha256": _response_sha256(
                    attempt["raw_response"]
                ),
                "raw_response_length": len(attempt["raw_response"]),
                "current_report_status": current["current_status"],
                "current_report_error_code": current.get(
                    "current_error_code"
                ),
                "current_report_error_message": current.get(
                    "current_error_message"
                ),
                "current_overall_score": current.get("overall_score"),
                "old_keyword_gate_removed": old_keyword_gate_removed,
                "missing_calculation_note_after_keyword_gate": (
                    missing_calculation_note
                ),
                "future_human_quality_review_required": True,
                "automatic_classification": classification,
            }
        )

    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("R7-D 回放期间历史证据身份发生变化")
    old_gate_removed_count = sum(
        item["old_keyword_gate_removed"] for item in records
    )
    accepted_count = sum(
        item["current_report_status"] == "succeeded" for item in records
    )
    missing_note_count = sum(
        item["missing_calculation_note_after_keyword_gate"] for item in records
    )
    return {
        "stage": ACTIVE_RUN_ID,
        "batch": "7R5-I2-R7-D",
        "mode": "zero_call_time_key_service_v7_replay",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": _i2_raw_identity(raw),
        "target_case_ids": list(R7D_TARGET_CASE_IDS),
        "supporting_plan_case_ids": [
            f"P{index:02d}" for index in sorted(plan_cache)
        ],
        "fixture": fixture,
        "source_execution_contract": raw["execution_contract"],
        "execution_contract": active_execution_contract,
        "lifecycle": lifecycle,
        "replay_limitations": {
            "service_acceptance_proves_content_quality": False,
            "responses_received_new_model_review": False,
            "prompt_v4_was_applied_to_old_responses": False,
            "time_key_content_was_corrected": False,
            "future_human_quality_review_required": True,
        },
        "records": records,
        "summary": {
            "target_case_count": len(records),
            "report_response_count": sum(
                item["case_id"].startswith("R") for item in records
            ),
            "stability_response_count": sum(
                item["case_id"].startswith("S") for item in records
            ),
            "old_keyword_gate_target_count": len(records),
            "old_keyword_gate_removed_count": old_gate_removed_count,
            "old_keyword_gate_still_rejected_count": (
                len(records) - old_gate_removed_count
            ),
            "full_report_accepted_count": accepted_count,
            "next_deterministic_gate_rejected_count": (
                len(records) - accepted_count
            ),
            "missing_calculation_note_count": missing_note_count,
            "future_human_quality_review_case_count": len(records),
        },
        "pricing_gate_allowed": False,
        "quality_conclusion_allowed": False,
        "human_quality_review_required": True,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "api_key_read": False,
        "adapter_instantiated": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
        "diagnostic_write_count": 1,
        "raw_response_copied": False,
        "historical_results": historical_after,
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


def write_r3d_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R3-D 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R3-D 诊断已经存在，拒绝覆盖") from None


def write_r4c_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R4-C 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R4-C 诊断已经存在，拒绝覆盖") from None


def write_r5d_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R5-D 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R5-D 诊断已经存在，拒绝覆盖") from None


def write_r6d_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R6-D 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R6-D 诊断已经存在，拒绝覆盖") from None


def write_r7d_diagnostic(
    path: Path,
    payload: dict[str, Any],
    *,
    diagnostic_dir: Path = R1C_DIAGNOSTIC_DIR,
) -> None:
    resolved = path.resolve()
    resolved_dir = diagnostic_dir.resolve()
    if resolved.parent != resolved_dir or resolved.suffix.lower() != ".json":
        raise RuntimeError("R7-D 诊断只能写入隔离诊断目录中的 JSON")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("R7-D 诊断已经存在，拒绝覆盖") from None


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
        "i2_raw_complete",
        "i2_human_complete",
        "i2_final_complete",
    }:
        raise RuntimeError(
            "I2-C 只允许在未开始或 preflight、raw、human、final 已封存状态下只读复核"
        )
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
    source_raw_identity = validate_sealed_raw_identity(source_path)
    return {
        "stage": ACTIVE_RUN_ID,
        "mode": "zero_call_full_category_preflight",
        "generated_at": _utc_now(),
        "source_raw_path": str(source_path),
        "source_raw_identity": source_raw_identity,
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
        "historical_results": historical_after,
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
    payload = load_r1c_diagnostic()
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
    payload = load_r2e_diagnostic()
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


async def r3d_main() -> None:
    payload = load_r3d_diagnostic()
    print(
        json.dumps(
            {
                "path": str(R3D_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r4c_main() -> None:
    payload = load_r4c_diagnostic()
    print(
        json.dumps(
            {
                "path": str(R4C_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "records": [
                    {
                        "case_id": record["case_id"],
                        "current_report_status": record["current_report_status"],
                        "current_report_error_message": record[
                            "current_report_error_message"
                        ],
                    }
                    for record in payload["records"]
                ],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r5d_main() -> None:
    payload = await build_r5d_replay_payload()
    write_r5d_diagnostic(R5D_DIAGNOSTIC_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(R5D_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "records": [
                    {
                        "case_id": record["case_id"],
                        "previous_gate_source": record["previous_gate_source"],
                        "current_report_status": record["current_report_status"],
                        "current_report_error_message": record[
                            "current_report_error_message"
                        ],
                        "known_model_content_risk": record[
                            "known_model_content_risk"
                        ],
                    }
                    for record in payload["records"]
                ],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r6d_main() -> None:
    payload = await build_r6d_replay_payload()
    write_r6d_diagnostic(R6D_DIAGNOSTIC_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(R6D_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "missing_report_case_ids": payload["missing_report_case_ids"],
                "missing_stability_case_ids": payload[
                    "missing_stability_case_ids"
                ],
                "records": [
                    {
                        "case_id": record["case_id"],
                        "previous_source": record["previous_source"],
                        "current_report_status": record["current_report_status"],
                        "current_report_error_message": record[
                            "current_report_error_message"
                        ],
                        "known_model_content_risk": record[
                            "known_model_content_risk"
                        ],
                    }
                    for record in payload["records"]
                ],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


async def r7d_main() -> None:
    payload = await build_r7d_replay_payload()
    write_r7d_diagnostic(R7D_DIAGNOSTIC_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(R7D_DIAGNOSTIC_PATH),
                "summary": payload["summary"],
                "records": [
                    {
                        "case_id": record["case_id"],
                        "source_error_message": record[
                            "source_error_message"
                        ],
                        "current_report_status": record[
                            "current_report_status"
                        ],
                        "current_report_error_message": record[
                            "current_report_error_message"
                        ],
                        "old_keyword_gate_removed": record[
                            "old_keyword_gate_removed"
                        ],
                    }
                    for record in payload["records"]
                ],
                "pricing_gate_allowed": payload["pricing_gate_allowed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    if "--r7d" in sys.argv[1:]:
        asyncio.run(r7d_main())
    elif "--r6d" in sys.argv[1:]:
        asyncio.run(r6d_main())
    elif "--r5d" in sys.argv[1:]:
        asyncio.run(r5d_main())
    elif "--r4c" in sys.argv[1:]:
        asyncio.run(r4c_main())
    elif "--r3d" in sys.argv[1:]:
        asyncio.run(r3d_main())
    elif "--r2e" in sys.argv[1:]:
        asyncio.run(r2e_main())
    elif "--r1c" in sys.argv[1:]:
        asyncio.run(r1c_main())
    else:
        asyncio.run(main())
