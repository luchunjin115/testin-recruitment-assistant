from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))

from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_PROMPT_VERSION,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_SCHEMA_VERSION,
)
from run_stage7_quality_acceptance import SCREENING_CASES  # noqa: E402
from stage7_7r4_quality_contract import (  # noqa: E402
    PLAN_FORMAL_RESULT_PATH,
    PLANNED_MODEL,
    REPORT_FORMAL_MARKDOWN_PATH,
    REPORT_FORMAL_RESULT_PATH,
    REPORT_TARGETED_RESULT_PATH,
    validate_historical_results,
    model_and_cost_inputs,
    report_label_denominators,
    serialized,
    validate_result_path_isolation,
)


FROZEN_REPORT_CASE_SHA256 = (
    "c612e3e1c55e0d3b6e0efcc3611c4c34f4eb39115e9ac3179555c6dc5ab0be10"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dry_run_payload() -> dict[str, Any]:
    historical_before = validate_historical_results()
    denominators = report_label_denominators(SCREENING_CASES)
    fixture_sha = hashlib.sha256(
        serialized(SCREENING_CASES).encode("utf-8")
    ).hexdigest()
    if fixture_sha != FROZEN_REPORT_CASE_SHA256:
        raise RuntimeError("20 组报告样本、人工标签或顺序已经漂移")
    if SCREENING_EVALUATION_PROMPT_VERSION != "screening_evaluation_v4":
        raise RuntimeError("报告 Prompt 版本尚未衔接 4.0 facts")
    if SCREENING_EVALUATION_SCHEMA_VERSION != "2.0":
        raise RuntimeError("报告输出 Schema 版本发生未确认变化")
    paths = validate_result_path_isolation()
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("报告 dry-run 期间历史结果发生变化")
    return {
        "stage": "7R4-G",
        "future_execution_stage": "7R4-I",
        "mode": "dry_run",
        "status": "prepared_but_not_authorized",
        "generated_at": _utc_now(),
        "selected_case_ids": denominators["case_ids"],
        "frozen_report_case_sha256": fixture_sha,
        "denominators": denominators,
        "prompt_version": SCREENING_EVALUATION_PROMPT_VERSION,
        "schema_version": SCREENING_EVALUATION_SCHEMA_VERSION,
        "planned_model": PLANNED_MODEL,
        "model_and_cost_inputs": {
            **model_and_cost_inputs(),
            "report_targeted_business_call_limit_requires_7R4_I_confirmation": 6,
            "report_formal_business_calls": 60,
            "report_formal_maximum_api_attempts_with_retries": 120,
        },
        "prerequisite_gate": {
            "requires_7R4_H_formal_plan_result": True,
            "required_path": str(PLAN_FORMAL_RESULT_PATH),
            "required_plan_schema_version": "4.0",
            "current_prerequisite_present": PLAN_FORMAL_RESULT_PATH.exists(),
        },
        "future_result_paths": {
            "targeted": str(REPORT_TARGETED_RESULT_PATH),
            "formal_json": str(REPORT_FORMAL_RESULT_PATH),
            "formal_markdown": str(REPORT_FORMAL_MARKDOWN_PATH),
        },
        "result_path_contract": paths,
        "historical_results_before": historical_before,
        "historical_results_after": historical_after,
        "real_model_call_count": 0,
        "adapter_instantiated": False,
        "api_key_read_as_prerequisite": False,
        "formal_quality_result_write_count": 0,
        "writes_result_file": False,
        "quality_conclusion_allowed": False,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 7 4.0 报告质量运行器的 7R4-G 零调用准备"
    )
    parser.add_argument("--dry-run", action="store_true", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    _parse_args(argv)
    print(json.dumps(dry_run_payload(), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
