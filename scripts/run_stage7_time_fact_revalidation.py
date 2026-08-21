from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
QUALITY_RESULTS = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-20-stage7-quality-acceptance-results.json"
)
OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-21-stage7-time-fact-revalidation-results.json"
)
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_stage7_quality_acceptance import JD_CASES, SCREENING_CASES  # noqa: E402

from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
)
from app.core.config import get_settings  # noqa: E402
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JobEvaluationItem,
    JobEvaluationPlanInputSnapshot,
)
from app.services.experience_period_service import (  # noqa: E402
    experience_period_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    screening_evaluation_service,
)


REFERENCE_AT = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)
TARGETS = ("SR05", "SR15")


class CountingRealAdapter:
    def __init__(self, delegate: DeepSeekScreeningEvaluationAdapter) -> None:
        self.delegate = delegate
        self.call_attempts = 0
        self.completed_responses = 0
        self.last_content: str | None = None

    async def evaluate(self, **kwargs: Any) -> Any:
        self.call_attempts += 1
        result = await self.delegate.evaluate(**kwargs)
        self.completed_responses += 1
        self.last_content = result.content
        return result


def _safe_year_assessments_from_content(content: str | None) -> list[dict[str, Any]]:
    """Keep only structured year-related fields, never the full model response."""
    if not content:
        return []
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []
    assessments = payload.get("requirement_assessments")
    if not isinstance(assessments, list):
        return []
    safe_items: list[dict[str, Any]] = []
    for assessment in assessments:
        if not isinstance(assessment, dict):
            continue
        fact_keys = assessment.get("experience_period_fact_keys")
        calculation_note = assessment.get("calculation_note")
        if not fact_keys and not calculation_note:
            continue
        safe_items.append(
            {
                "item_key": assessment.get("item_key"),
                "conclusion": assessment.get("conclusion"),
                "reason": assessment.get("reason"),
                "calculation_note": calculation_note,
                "experience_period_fact_keys": fact_keys,
            }
        )
    return safe_items


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prior = json.loads(QUALITY_RESULTS.read_text(encoding="utf-8"))
    jd_by_id = {case["case_id"]: case for case in JD_CASES}
    screening_by_id = {case["case_id"]: case for case in SCREENING_CASES}
    plan_by_id = {
        case["case_id"]: case["items"]
        for case in prior["jd_acceptance"]["cases"]
        if "items" in case
    }
    return jd_by_id, screening_by_id, plan_by_id


async def main() -> None:
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise SystemExit("DeepSeek Key 不可用，未执行真实定向复验")
    jd_by_id, screening_by_id, plan_by_id = _load_inputs()
    results: list[dict[str, Any]] = []

    for case_id in TARGETS:
        case = screening_by_id[case_id]
        job_case_id = case["job_case_id"]
        snapshot = JobEvaluationPlanInputSnapshot.model_validate(
            jd_by_id[job_case_id]["snapshot"]
        )
        items = [
            JobEvaluationItem.model_validate(item) for item in plan_by_id[job_case_id]
        ]
        sanitized_resume = screening_evaluation_service.sanitize_resume_text(
            case["resume"]
        )
        period_facts = experience_period_service.build(
            sanitized_resume,
            evaluation_reference_at=REFERENCE_AT,
        )
        case_result: dict[str, Any] = {
            "case_id": case_id,
            "job_case_id": job_case_id,
            "fictional_redacted_sample": True,
            "evaluation_reference_at": REFERENCE_AT.isoformat(),
            "evaluation_timezone": period_facts.evaluation_timezone,
            "experience_period_facts_rule_version": period_facts.rule_version,
            "experience_period_facts": [
                {
                    "key": fact.key,
                    "source_date_text": fact.source_date_text,
                    "resolved_cutoff_month": fact.resolved_cutoff_month,
                    "duration_months": fact.duration_months,
                    "duration_months_lower_bound": fact.duration_months_lower_bound,
                    "duration_months_upper_bound": fact.duration_months_upper_bound,
                    "warnings": fact.warnings,
                    "usable_for_reference": fact.usable_for_reference,
                }
                for fact in period_facts.facts
            ],
            "runs": [],
        }
        for run_number in range(1, 4):
            adapter = CountingRealAdapter(
                DeepSeekScreeningEvaluationAdapter(settings=settings)
            )
            try:
                result = await screening_evaluation_service.evaluate(
                    job_snapshot=snapshot,
                    evaluation_plan=items,
                    resume_text=case["resume"],
                    evaluation_reference_at=REFERENCE_AT,
                    evaluation_timezone="Asia/Shanghai",
                    experience_period_facts=period_facts,
                    adapter=adapter,
                    settings=settings,
                )
                year_assessments = [
                    assessment.model_dump(mode="json")
                    for assessment in result.report.requirement_assessments
                    if assessment.experience_period_fact_keys
                ]
                case_result["runs"].append(
                    {
                        "run": run_number,
                        "actual_model_call_attempts": adapter.call_attempts,
                        "completed_model_responses": adapter.completed_responses,
                        "validation_passed": True,
                        "overall_score": result.report.overall_score,
                        "year_assessments": year_assessments,
                        "model": result.metadata.model_version,
                        "input_tokens": result.metadata.input_tokens,
                        "output_tokens": result.metadata.output_tokens,
                    }
                )
            except Exception as exc:
                case_result["runs"].append(
                    {
                        "run": run_number,
                        "actual_model_call_attempts": adapter.call_attempts,
                        "completed_model_responses": adapter.completed_responses,
                        "validation_passed": False,
                        "error_code": getattr(
                            exc, "code", "SCREENING_REVALIDATION_FAILED"
                        ),
                        "safe_error": str(exc)[:500],
                        "year_assessments": _safe_year_assessments_from_content(
                            adapter.last_content
                        ),
                    }
                )
        case_result["actual_model_call_attempts"] = sum(
            run["actual_model_call_attempts"] for run in case_result["runs"]
        )
        case_result["completed_model_responses"] = sum(
            run["completed_model_responses"] for run in case_result["runs"]
        )
        case_result["validated_report_count"] = sum(
            bool(run["validation_passed"]) for run in case_result["runs"]
        )
        results.append(case_result)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "stage7 time-fact targeted revalidation only",
        "updates_formal_20_jd_or_20_screening_statistics": False,
        "provider": "deepseek",
        "mock_fallback": False,
        "cases": results,
        "aggregate": {
            "case_count": len(results),
            "actual_model_call_attempts": sum(
                case["actual_model_call_attempts"] for case in results
            ),
            "completed_model_responses": sum(
                case["completed_model_responses"] for case in results
            ),
            "validated_report_count": sum(
                case["validated_report_count"] for case in results
            ),
            "year_fact_conflict_count": sum(
                run.get("error_code") == "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT"
                and "年限结论" in run.get("safe_error", "")
                for case in results
                for run in case["runs"]
            ),
        },
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload["aggregate"], ensure_ascii=False))
    print(f"RESULT_PATH={OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
