from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE7_ROOT = PROJECT_ROOT / "docs" / "stages" / "stage7"
QUALITY_ROOT = STAGE7_ROOT / "v5-quality-results"
I4_RAW_PATH = QUALITY_ROOT / "2026-08-31-stage7-7r5i4-quality-raw-results.json"
I4_HUMAN_PATH = QUALITY_ROOT / "2026-08-31-stage7-7r5i4-quality-human-audit.json"
I4_FINAL_PATH = QUALITY_ROOT / "2026-08-31-stage7-7r5i4-quality-final-results.json"
RESULT_PATH = STAGE7_ROOT / "2026-08-31-stage7-close07-full-chain-acceptance-results.json"
BROWSER_EVIDENCE_DIR = STAGE7_ROOT / "close07-browser-acceptance-evidence"

I4_RAW_SHA256 = "e4d1e01182eecd29423ccc7e89b20a45968ef52730ff27fc09f77580d19c6c33"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON 顶层必须是对象：{path}")
    return value


def validate_prerequisites() -> dict[str, Any]:
    if not I4_RAW_PATH.is_file():
        raise RuntimeError("I4 唯一 raw 不存在，CLOSE-07 不得开始")
    raw_sha256 = sha256_file(I4_RAW_PATH)
    if raw_sha256 != I4_RAW_SHA256:
        raise RuntimeError("I4 raw 身份变化，CLOSE-07 必须停止")
    if I4_HUMAN_PATH.exists() or I4_FINAL_PATH.exists():
        raise RuntimeError("用户已取消 I4 human/final，不得创建或使用")

    raw = _read_json(I4_RAW_PATH)
    summaries = raw.get("summaries") or {}
    plans = summaries.get("plans") or {}
    reports = summaries.get("reports") or {}
    stability = summaries.get("stability") or {}
    expected = {
        "stage": "7R5-I4",
        "lifecycle": "i4_raw_complete",
        "plan": 10,
        "report": 19,
        "stability": 13,
        "direction_stable": 4,
        "difference_stable": 4,
        "extreme_flip": 0,
    }
    observed = {
        "stage": raw.get("stage"),
        "lifecycle": raw.get("lifecycle"),
        "plan": plans.get("structure_legal_count"),
        "report": reports.get("legal_report_count"),
        "stability": stability.get("legal_report_count"),
        "direction_stable": stability.get("direction_stable_group_count"),
        "difference_stable": stability.get("max_difference_le_10_group_count"),
        "extreme_flip": stability.get("extreme_direction_flip_count"),
    }
    if observed != expected:
        raise RuntimeError(f"I4 raw 汇总与 CLOSE-07 冻结合同不一致：{observed}")
    if raw.get("quality_gate_passed") is not None:
        raise RuntimeError("I4 raw quality_gate_passed 必须保持 null")
    if raw.get("quality_conclusion_allowed") is not False:
        raise RuntimeError("I4 raw quality_conclusion_allowed 必须保持 false")

    return {
        "stage": "7R5-CLOSE-07",
        "ready_for_close07": True,
        "i4_lifecycle": raw["lifecycle"],
        "i4_raw_sha256": raw_sha256,
        "i4_plan_valid_count": plans["structure_legal_count"],
        "i4_report_valid_count": reports["legal_report_count"],
        "i4_stability_valid_count": stability["legal_report_count"],
        "i4_direction_stable_group_count": stability["direction_stable_group_count"],
        "i4_max_difference_le_10_group_count": stability["max_difference_le_10_group_count"],
        "i4_extreme_direction_flip_count": stability["extreme_direction_flip_count"],
        "quality_gate_passed": raw["quality_gate_passed"],
        "quality_conclusion_allowed": raw["quality_conclusion_allowed"],
        "i4_human_exists": I4_HUMAN_PATH.exists(),
        "i4_final_exists": I4_FINAL_PATH.exists(),
    }


def write_json_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise RuntimeError(f"正式结果已存在，拒绝覆盖：{path}") from exc


def validate_result(path: Path = RESULT_PATH) -> dict[str, Any]:
    result = _read_json(path)
    prerequisites = validate_prerequisites()
    required_zero = {
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "actual_token_usage": 0,
        "actual_spend_usd": 0,
        "postgresql_residual_write_count": 0,
    }
    if result.get("stage") != "7R5-CLOSE-07":
        raise RuntimeError("CLOSE-07 结果身份错误")
    if result.get("close07_passed") is not True:
        raise RuntimeError("CLOSE-07 尚未通过")
    if result.get("source_i4_raw_sha256") != prerequisites["i4_raw_sha256"]:
        raise RuntimeError("CLOSE-07 未绑定当前 I4 raw")
    for key, expected in required_zero.items():
        if result.get(key) != expected:
            raise RuntimeError(f"CLOSE-07 零调用/零残留字段错误：{key}")
    if result.get("api_key_read") is not False:
        raise RuntimeError("CLOSE-07 不得读取 API Key")
    if (result.get("automated_verification") or {}).get("passed") is not True:
        raise RuntimeError("自动化验证未通过")
    if (result.get("postgresql_api_verification") or {}).get("passed") is not True:
        raise RuntimeError("PostgreSQL/API 验证未通过")
    if (result.get("browser_verification") or {}).get("passed") is not True:
        raise RuntimeError("浏览器验证未通过")
    if (result.get("evidence_protection") or {}).get("passed") is not True:
        raise RuntimeError("正式证据保护未通过")
    return result


if __name__ == "__main__":
    print(json.dumps(validate_prerequisites(), ensure_ascii=False, indent=2))
