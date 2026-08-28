from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for path in (BACKEND_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.job_evaluation_plan import (  # noqa: E402
    DeepSeekJobEvaluationPlanAdapter,
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
)
from app.adapters.screening_evaluation import (  # noqa: E402
    DeepSeekScreeningEvaluationAdapter,
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
    ScreeningEvaluationAdapterResult,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
    build_job_evaluation_plan_v5_messages,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    build_screening_evaluation_v5_messages,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.experience_period_service import experience_period_service  # noqa: E402
from app.services.job_evaluation_plan_service import (  # noqa: E402
    GeneratedPlanContentV5,
    JobEvaluationPlanV5GenerationError,
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    ScreeningEvaluationServiceError,
    screening_evaluation_service,
)
from stage7_7r5_quality_contract import (  # noqa: E402
    ACTIVE_RUN_ID,
    BASELINE_BUSINESS_CALLS,
    FINAL_RESULT_PATH,
    FROZEN_FIXTURE_SHA256,
    HUMAN_AUDIT_PATH,
    HISTORICAL_RESULT_HASHES,
    I2_RAW_RESULT_PATH,
    MAXIMUM_API_ATTEMPTS,
    PLAN_MAX_OUTPUT_TOKENS,
    PLANNED_MODEL,
    RAW_RESULT_PATH,
    REPORT_MAX_OUTPUT_TOKENS,
    call_budget,
    estimate_attempt_cost_usd,
    execution_contract,
    human_audit_contract,
    result_paths,
    sha256_file,
    validate_frozen_fixture,
    validate_historical_results,
    validate_pricing_snapshot,
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
TOKEN_RE = re.compile(r"[A-Za-z0-9+#.]+|[\u4e00-\u9fff]")


def _offline_settings() -> Settings:
    """Build validated defaults without reading .env or accepting a real API key."""

    return Settings(_env_file=None, DEEPSEEK_API_KEY="")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job(case: dict[str, Any], index: int) -> SimpleNamespace:
    jd = case["jd"]
    return SimpleNamespace(
        id=95_000 + index,
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
    matches = [index for index, case in enumerate(V5_PLAN_JDS) if case["jd"] == pair["jd"]]
    if len(matches) != 1:
        raise RuntimeError("报告样本不能唯一映射到冻结计划 JD")
    return matches[0]


def _fake_plan_payload(snapshot: Any) -> dict[str, Any]:
    units = list(snapshot.source_units or [])
    # Fake 正常链路只选职责原文。学历、证书、办公地点等内容仍保留在冻结
    # 输入中供真实质量验收审阅，但不能被这个“肯定合法”的桩误当成评价点。
    selected = [unit for unit in units if unit.source_field == "job_responsibilities"][:12]
    if not selected:
        raise RuntimeError("冻结 JD 缺少可用于 Fake 正常链路的岗位职责")
    criteria = []
    for unit in selected:
        quote = unit.source_text
        importance = (
            "required" if unit.source_field == "candidate_requirements" and re.search(r"必须|至少|要求|需", quote)
            else "preferred" if unit.source_field == "preferred_qualifications"
            else "general"
        )
        criteria.append(
            {
                "name": quote[:80],
                "importance": importance,
                "description": quote,
                "screening_focus": quote,
                "sources": [{"source_field": unit.source_field, "source_quote": quote}],
            }
        )
    return {"criteria": criteria}


def _fake_plan_result(snapshot: Any, *, invalid: bool = False) -> JobEvaluationPlanAdapterResult:
    payload = _fake_plan_payload(snapshot)
    if invalid:
        payload["criteria"][0]["sources"][0]["source_quote"] = "不存在的冻结 JD 原文"
    return JobEvaluationPlanAdapterResult(
        content=json.dumps(payload, ensure_ascii=False),
        model="7r5h-fake-plan-no-network",
        finish_reason="stop",
        input_tokens=100,
        cache_hit_input_tokens=40,
        cache_miss_input_tokens=60,
        output_tokens=80,
    )


def _resume_evidence(service: Any, resume_text: str) -> tuple[str, str]:
    sanitized = service.sanitize_resume_text(resume_text)
    lines = [line.strip("- •\t") for line in sanitized.splitlines() if len(line.strip("- •\t")) >= 8]
    if not lines:
        raise RuntimeError("冻结 Resume 脱敏后没有可用 Fake 证据")
    return sanitized, lines[0]


def _fake_report_payload(plan: GeneratedPlanContentV5, resume_text: str, direction: str, *, invalid: bool = False) -> dict[str, Any]:
    _, quote = _resume_evidence(screening_evaluation_service, resume_text)
    score = {"high_match": 85, "partial_match": 55, "low_match": 12}[direction]
    item_score = {"high_match": 8, "partial_match": 5, "low_match": 2}[direction]
    assessments = []
    for criterion in plan.criteria:
        if item_score == 0:
            assessments.append(
                {
                    "criterion_id": criterion.criterion_id,
                    "score": 0,
                    "reason": "当前简历未发现相关证据，仅表示现有材料未体现。",
                    "calculation_note": None,
                    "experience_period_fact_keys": [],
                    "evidence": [],
                }
            )
        else:
            assessments.append(
                {
                    "criterion_id": criterion.criterion_id,
                    "score": item_score,
                    "reason": f"当前简历中可定位到项目描述：{quote}",
                    "calculation_note": None,
                    "experience_period_fact_keys": [],
                    "evidence": [{"quote": quote, "section": "简历正文"}],
                }
            )
    if invalid:
        assessments[0]["evidence"] = []
    first_id = plan.criteria[0].criterion_id
    summary = {
        "high_match": "当前简历与岗位整体较匹配，证据较充分。",
        "partial_match": "当前简历与岗位部分匹配，仍需 HR 核实。",
        "low_match": "当前简历与岗位整体不匹配，存在缺口。",
    }[direction]
    strengths = [{
        "summary": f"当前简历包含可定位的项目描述：{quote}",
        "criterion_ids": [first_id],
        "evidence": [{"quote": quote, "section": "简历正文"}],
    }]
    return {
        "overall_score": score,
        "overall_summary": summary,
        "criterion_assessments": assessments,
        "strengths": strengths,
        "gaps": [{"summary": "当前简历未体现该评价点的完整信息，仍需 HR 核实。", "criterion_ids": [first_id], "evidence": []}],
        "risks_or_conflicts": [{"summary": "当前简历未体现该评价点的完整信息，存在待核实风险。", "criterion_ids": [first_id], "evidence": []}],
        "missing_info": [{"summary": "当前简历缺少该评价点的完整信息，仍需 HR 核实。", "criterion_ids": [first_id], "evidence": []}],
        "hr_follow_up_questions": ["请结合具体项目核实候选人的职责和交付结果。"],
    }


def _fake_report_result(payload: dict[str, Any]) -> ScreeningEvaluationAdapterResult:
    return ScreeningEvaluationAdapterResult(
        content=json.dumps(payload, ensure_ascii=False),
        model="7r5h-fake-report-no-network",
        finish_reason="stop",
        input_tokens=120,
        output_tokens=90,
    )


def _normalize_tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if token.strip()}


def _rough_label_match(label: str, text: str) -> bool:
    label_tokens = _normalize_tokens(label)
    text_tokens = _normalize_tokens(text)
    if not label_tokens:
        return False
    overlap = len(label_tokens & text_tokens) / len(label_tokens)
    return label in text or overlap >= 0.55


def summarize_plans(records: list[dict[str, Any]]) -> dict[str, Any]:
    required_total = required_covered = 0
    non_eval_total = non_eval_misclassified = 0
    forbidden_total = forbidden_added = 0
    for record, case in zip(records, V5_PLAN_JDS, strict=True):
        rendered = record.get("rendered_criteria", "")
        labels = case["labels"]
        required_total += len(labels["key_required_items"])
        required_covered += sum(_rough_label_match(label, rendered) for label in labels["key_required_items"])
        non_eval_total += len(labels["non_evaluation_content"])
        non_eval_misclassified += sum(_rough_label_match(label, rendered) for label in labels["non_evaluation_content"])
        forbidden_total += len(labels["forbidden_additions"])
        forbidden_added += sum(_rough_label_match(label, rendered) for label in labels["forbidden_additions"])
    succeeded = sum(record["status"] == "succeeded" for record in records)
    return {
        "case_count": 10,
        "structure_legal_count": succeeded,
        "editable_plan_count": succeeded,
        "traceable_plan_count": sum(record.get("all_criteria_traceable", False) for record in records),
        "required_label_denominator": required_total,
        "rough_required_covered_count": required_covered,
        "non_evaluation_label_denominator": non_eval_total,
        "rough_non_evaluation_misclassified_count": non_eval_misclassified,
        "forbidden_addition_denominator": forbidden_total,
        "rough_forbidden_addition_count": forbidden_added,
        "semantic_counts_require_frozen_human_audit": True,
    }


def _direction_for_score(score: int) -> str:
    return "high_match" if score >= 70 else "partial_match" if score >= 40 else "low_match"


def summarize_reports(records: list[dict[str, Any]], *, stability: bool = False) -> dict[str, Any]:
    legal = [record for record in records if record["status"] == "succeeded"]
    direction_consistent = sum(
        record.get("actual_direction") == record.get("manual_direction") for record in records
    )
    result = {
        "scheduled_run_count": len(records),
        "legal_report_count": len(legal),
        "direction_consistent_count": direction_consistent,
        "nonzero_assessment_count": sum(record.get("nonzero_assessment_count", 0) for record in legal),
        "nonzero_with_evidence_count": sum(record.get("nonzero_with_evidence_count", 0) for record in legal),
        "all_required_sections_count": sum(record.get("all_required_sections", False) for record in legal),
        "service_validated_fabrication_or_safety_rejection_count": sum(record["status"] == "failed" for record in records),
        "human_fact_and_direction_audit_required": True,
    }
    if stability:
        groups = []
        for sample_index in V5_STABILITY_SAMPLE_INDICES:
            group = [record for record in records if record["sample_index"] == sample_index]
            scores = [record["overall_score"] for record in group if record["status"] == "succeeded"]
            directions = {record.get("actual_direction") for record in group if record["status"] == "succeeded"}
            groups.append({
                "sample_index": sample_index,
                "legal_run_count": len(scores),
                "max_score_difference": max(scores) - min(scores) if len(scores) == 3 else None,
                "direction_stable": len(scores) == 3 and len(directions) == 1,
                "extreme_direction_flip": "high_match" in directions and "low_match" in directions,
            })
        result["groups"] = groups
        result["direction_stable_group_count"] = sum(group["direction_stable"] for group in groups)
        result["max_difference_le_10_group_count"] = sum(
            group["max_score_difference"] is not None and group["max_score_difference"] <= 10 for group in groups
        )
        result["extreme_direction_flip_count"] = sum(group["extreme_direction_flip"] for group in groups)
    return result


async def _run_plan(case: dict[str, Any], index: int, adapter: Any) -> tuple[dict[str, Any], GeneratedPlanContentV5 | None]:
    snapshot = job_evaluation_plan_service.build_v5_input_snapshot(_job(case, index))
    try:
        content = await job_evaluation_plan_service.build_v5_plan_content(snapshot, adapter=adapter)
    except JobEvaluationPlanV5GenerationError as exc:
        return ({"case_id": f"P{index:02d}", "status": "failed", "error_code": exc.code, "error_message": str(exc), "rendered_criteria": "", "all_criteria_traceable": False}, None)
    rendered = "\n".join(
        "\n".join((criterion.name, criterion.description, criterion.screening_focus, *(source.source_quote for source in criterion.sources)))
        for criterion in content.criteria
    )
    return ({
        "case_id": f"P{index:02d}",
        "status": "succeeded",
        "criteria_count": len(content.criteria),
        "warnings": [warning.model_dump(mode="json") for warning in content.warnings],
        "criteria": [criterion.model_dump(mode="json") for criterion in content.criteria],
        "rendered_criteria": rendered,
        "all_criteria_traceable": all(criterion.sources for criterion in content.criteria),
        "business_call_count": content.business_call_count,
        "adapter_attempt_count": content.adapter_attempt_count,
        "infrastructure_retry_count": content.infrastructure_retry_count,
    }, content)


async def _run_report(
    pair: dict[str, Any],
    sample_index: int,
    plan: GeneratedPlanContentV5 | None,
    adapter: Any,
    *,
    run_kind: str,
    run_number: int,
) -> dict[str, Any]:
    case_id = f"R{sample_index:02d}" if run_kind == "report" else f"S{sample_index:02d}-{run_number}"
    if plan is None:
        return {"case_id": case_id, "sample_index": sample_index, "run_number": run_number, "status": "blocked", "blocked_by": "plan_not_legal", "manual_direction": pair["labels"]["overall_direction"]}
    snapshot = job_evaluation_plan_service.build_v5_input_snapshot(_job(V5_PLAN_JDS[_plan_case_index(pair)], sample_index))
    sanitized = screening_evaluation_service.sanitize_resume_text(pair["resume_text"])
    facts = experience_period_service.build(sanitized, evaluation_reference_at=REFERENCE_AT)
    try:
        result = await screening_evaluation_service.evaluate_v5(
            job_snapshot=snapshot,
            evaluation_plan={"schema_version": "5.0", "criteria": [criterion.model_dump(mode="json") for criterion in plan.criteria]},
            resume_text=pair["resume_text"],
            evaluation_reference_at=REFERENCE_AT,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts=facts,
            adapter=adapter,
            settings=_offline_settings(),
        )
    except (ScreeningEvaluationServiceError, ScreeningEvaluationAdapterError) as exc:
        return {"case_id": case_id, "sample_index": sample_index, "run_number": run_number, "status": "failed", "error_code": exc.code, "error_message": str(exc), "manual_direction": pair["labels"]["overall_direction"]}
    report = result.report
    nonzero = [item.assessment for item in report.criterion_assessments if item.assessment.score > 0]
    return {
        "case_id": case_id,
        "sample_index": sample_index,
        "run_number": run_number,
        "status": "succeeded",
        "manual_direction": pair["labels"]["overall_direction"],
        "overall_score": report.overall_score,
        "actual_direction": _direction_for_score(report.overall_score),
        "nonzero_assessment_count": len(nonzero),
        "nonzero_with_evidence_count": sum(bool(item.evidence) for item in nonzero),
        "all_required_sections": bool(
            report.strengths
            and report.gaps
            and report.risks_or_conflicts
            and report.missing_info
            and report.hr_follow_up_questions
        ),
        "report": report.model_dump(mode="json"),
    }


async def fake_payload(
    *, failure: bool, run_id: str = ACTIVE_RUN_ID
) -> dict[str, Any]:
    historical_before = validate_historical_results()
    fixture = validate_frozen_fixture()
    lifecycle = validate_result_lifecycle(run_id=run_id)
    plan_records: list[dict[str, Any]] = []
    plans: list[GeneratedPlanContentV5 | None] = []
    for index, case in enumerate(V5_PLAN_JDS):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(_job(case, index))
        adapter = FakeJobEvaluationPlanAdapter([_fake_plan_result(snapshot, invalid=failure and index == 0)])
        record, plan = await _run_plan(case, index, adapter)
        plan_records.append(record)
        plans.append(plan)
    report_records: list[dict[str, Any]] = []
    for index, pair in enumerate(V5_REPORT_PAIRS):
        plan = plans[_plan_case_index(pair)]
        payload = _fake_report_payload(plan, pair["resume_text"], pair["labels"]["overall_direction"], invalid=failure and index == 1) if plan else {}
        adapter = FakeScreeningEvaluationAdapter([_fake_report_result(payload)])
        report_records.append(await _run_report(pair, index, plan, adapter, run_kind="report", run_number=1))
    stability_records: list[dict[str, Any]] = []
    for sample_index in V5_STABILITY_SAMPLE_INDICES:
        pair = V5_REPORT_PAIRS[sample_index]
        plan = plans[_plan_case_index(pair)]
        for run_number in range(1, V5_STABILITY_RUNS_PER_SAMPLE + 1):
            payload = _fake_report_payload(plan, pair["resume_text"], pair["labels"]["overall_direction"]) if plan else {}
            adapter = FakeScreeningEvaluationAdapter([_fake_report_result(payload)])
            stability_records.append(await _run_report(pair, sample_index, plan, adapter, run_kind="stability", run_number=run_number))
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("Fake 运行期间历史质量证据发生变化")
    return {
        "stage": "7R5-H",
        "future_execution_stage": run_id,
        "mode": "fake_failure" if failure else "fake_normal",
        "generated_at": _utc_now(),
        "fixture": fixture,
        "execution_contract": execution_contract(),
        "call_budget": call_budget(),
        "result_lifecycle": lifecycle,
        "plan_records": plan_records,
        "report_records": report_records,
        "stability_records": stability_records,
        "summaries": {
            "plans": summarize_plans(plan_records),
            "reports": summarize_reports(report_records),
            "stability": summarize_reports(stability_records, stability=True),
        },
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": historical_after,
        "real_model_call_count": 0,
        "api_key_read": False,
        "formal_result_write_count": 0,
        "writes_result_file": False,
        "quality_conclusion_allowed": False,
    }


def dry_run_payload(*, run_id: str = ACTIVE_RUN_ID) -> dict[str, Any]:
    historical_before = validate_historical_results()
    lifecycle = validate_result_lifecycle(run_id=run_id)
    payload = {
        "stage": "7R5-H",
        "future_execution_stage": run_id,
        "mode": "dry_run",
        "status": "prepared_but_not_authorized",
        "generated_at": _utc_now(),
        "fixture": validate_frozen_fixture(),
        "execution_contract": execution_contract(),
        "call_budget": call_budget(),
        "result_path_contract": lifecycle,
        "quality_thresholds": {
            "plan_legal": "10/10",
            "plan_required_coverage": "100%",
            "plan_forbidden_sensitive_non_evaluation_errors": 0,
            "report_legal": "20/20",
            "report_nonzero_evidence": "100%",
            "report_fabrication_severe_sensitive_decision_errors": 0,
            "report_direction_consistency_minimum": "80%",
            "required_direction_consistency_minimum": "90%",
            "stability_direction_groups_minimum": "4/5",
            "stability_score_spread_le_10_minimum": "4/5",
            "stability_extreme_flips": 0,
            "human_adjudication_required_for_semantic_quality": True,
        },
        "human_audit_contract": human_audit_contract(),
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": validate_historical_results(),
        "real_model_call_count": 0,
        "adapter_instantiated": False,
        "api_key_read": False,
        "formal_result_write_count": 0,
        "writes_result_file": False,
        "quality_conclusion_allowed": False,
    }
    if payload["historical_result_hashes_before"] != payload["historical_result_hashes_after"]:
        raise RuntimeError("dry-run 期间历史质量证据发生变化")
    return payload


@dataclass
class CostGuard:
    pricing: dict[str, Any]
    cap_usd: float | None
    estimated_spend_usd: float = 0.0
    failed_attempt_reserve_usd: float = 0.0
    _active_reservation_usd: float = 0.0

    def reserve(self, input_value: Any, max_output_tokens: int) -> float:
        if self._active_reservation_usd:
            raise RuntimeError("上一 API attempt 的费用预留尚未结算")
        rates = self.pricing["usd_per_million_tokens"]
        input_upper = len(json.dumps(input_value, ensure_ascii=False).encode("utf-8"))
        ceiling = (
            input_upper * rates["cache_miss_input"] + max_output_tokens * rates["output"]
        ) / 1_000_000
        if self.cap_usd is not None and self.estimated_spend_usd + ceiling > self.cap_usd:
            raise RuntimeError("下一次调用的保守费用上界会超过用户确认金额上限")
        self._active_reservation_usd = ceiling
        return ceiling

    def retain_failed_reservation(self) -> float:
        ceiling = self._active_reservation_usd
        self._active_reservation_usd = 0.0
        self.estimated_spend_usd += ceiling
        self.failed_attempt_reserve_usd += ceiling
        return ceiling

    def charge(self, result: Any) -> dict[str, Any]:
        estimate = estimate_attempt_cost_usd(
            pricing=self.pricing,
            input_tokens=result.input_tokens,
            cache_hit_input_tokens=getattr(result, "cache_hit_input_tokens", None),
            cache_miss_input_tokens=getattr(result, "cache_miss_input_tokens", None),
            output_tokens=result.output_tokens,
        )
        if not estimate["complete"]:
            self.retain_failed_reservation()
            raise RuntimeError("真实 attempt 缺少可审计 token，停止后续调用")
        self._active_reservation_usd = 0.0
        self.estimated_spend_usd += estimate["estimated_cost_usd"]
        if self.cap_usd is not None and self.estimated_spend_usd > self.cap_usd:
            raise RuntimeError("累计估算费用超过用户确认金额上限，停止后续调用")
        return estimate


class AuditedPlanAdapter:
    def __init__(self, delegate: Any, recorder: list[dict[str, Any]], guard: CostGuard, case_id: str) -> None:
        self.delegate, self.recorder, self.guard, self.case_id = delegate, recorder, guard, case_id
        self.attempt_count = 0

    async def generate_v5(self, generation_input: dict[str, Any]) -> JobEvaluationPlanAdapterResult:
        self.attempt_count += 1
        messages = build_job_evaluation_plan_v5_messages(generation_input)
        self.guard.reserve(messages, PLAN_MAX_OUTPUT_TOKENS)
        started = time.perf_counter()
        try:
            result = await self.delegate.generate_v5(generation_input)
        except JobEvaluationPlanAdapterError as exc:
            reserve = self.guard.retain_failed_reservation()
            self.recorder.append({"case_id": self.case_id, "attempt_number": self.attempt_count, "result": "failed", "error_code": exc.code, "retryable": exc.retryable, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "cost_estimate": {"complete": False, "estimated_cost_usd": None, "reserved_cost_upper_bound_usd": reserve, "reason": "provider_usage_unavailable"}, "raw_response": None})
            raise
        estimate = self.guard.charge(result)
        self.recorder.append({"case_id": self.case_id, "attempt_number": self.attempt_count, "result": "succeeded", "error_code": None, "retryable": False, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "requested_model": PLANNED_MODEL, "model": result.model, "finish_reason": result.finish_reason, "input_tokens": result.input_tokens, "cache_hit_input_tokens": result.cache_hit_input_tokens, "cache_miss_input_tokens": result.cache_miss_input_tokens, "output_tokens": result.output_tokens, "cost_estimate": estimate, "raw_response": result.content})
        return result


class AuditedReportAdapter:
    def __init__(self, delegate: Any, recorder: list[dict[str, Any]], guard: CostGuard, case_id: str) -> None:
        self.delegate, self.recorder, self.guard, self.case_id = delegate, recorder, guard, case_id

    async def evaluate_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        messages = build_screening_evaluation_v5_messages(**kwargs)
        for attempt in range(1, 3):
            self.guard.reserve(messages, REPORT_MAX_OUTPUT_TOKENS)
            started = time.perf_counter()
            try:
                result = await self.delegate.evaluate_v5(**kwargs)
            except ScreeningEvaluationAdapterError as exc:
                reserve = self.guard.retain_failed_reservation()
                self.recorder.append({"case_id": self.case_id, "attempt_number": attempt, "result": "failed", "error_code": exc.code, "retryable": exc.retryable, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "cost_estimate": {"complete": False, "estimated_cost_usd": None, "reserved_cost_upper_bound_usd": reserve, "reason": "provider_usage_unavailable"}, "raw_response": None})
                if exc.retryable and attempt == 1:
                    continue
                raise
            estimate = self.guard.charge(result)
            self.recorder.append({"case_id": self.case_id, "attempt_number": attempt, "result": "succeeded", "error_code": None, "retryable": False, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "requested_model": PLANNED_MODEL, "model": result.model, "finish_reason": result.finish_reason, "input_tokens": result.input_tokens, "cache_hit_input_tokens": None, "cache_miss_input_tokens": None, "output_tokens": result.output_tokens, "cost_estimate": estimate, "raw_response": result.content})
            return result
        raise AssertionError("unreachable")


def summarize_attempts(attempts: list[dict[str, Any]], guard: CostGuard) -> dict[str, Any]:
    return {
        "scheduled_business_call_count": BASELINE_BUSINESS_CALLS,
        "executed_business_call_count": len({item["case_id"] for item in attempts}),
        "api_attempt_count": len(attempts),
        "infrastructure_retry_count": sum(item["attempt_number"] == 2 for item in attempts),
        "succeeded_attempt_count": sum(item["result"] == "succeeded" for item in attempts),
        "failed_attempt_count": sum(item["result"] == "failed" for item in attempts),
        "maximum_api_attempts": MAXIMUM_API_ATTEMPTS,
        "estimated_spend_usd": guard.estimated_spend_usd,
        "failed_attempt_reserve_usd": guard.failed_attempt_reserve_usd,
    }


async def real_payload(
    *,
    pricing_path: Path,
    monetary_cap_usd: float | None,
    run_id: str = ACTIVE_RUN_ID,
) -> dict[str, Any]:
    fixture = validate_frozen_fixture()
    historical_before = validate_historical_results()
    pricing = validate_pricing_snapshot(json.loads(pricing_path.read_text(encoding="utf-8")))
    lifecycle = validate_result_lifecycle(
        run_id=run_id, expected_state="i2_preflight_complete"
    )
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("真实运行已授权但 DeepSeek API Key 未配置")
    expected = execution_contract()
    if (
        settings.JOB_EVALUATION_PLAN_MODEL != expected["model"]
        or settings.SCREENING_EVALUATION_MODEL != expected["model"]
        or settings.JOB_EVALUATION_PLAN_V5_PROMPT_VERSION != expected["plan_prompt_version"]
        or settings.SCREENING_EVALUATION_V5_PROMPT_VERSION != expected["report_prompt_version"]
        or settings.JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION != "5.0"
        or settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION != "5.0"
        or settings.JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS != PLAN_MAX_OUTPUT_TOKENS
        or settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS != REPORT_MAX_OUTPUT_TOKENS
    ):
        raise RuntimeError("真实运行配置与 7R5-H 冻结合同不一致")
    guard = CostGuard(pricing=pricing, cap_usd=monetary_cap_usd)
    attempts: list[dict[str, Any]] = []
    plan_delegate = DeepSeekJobEvaluationPlanAdapter(settings=settings)
    report_delegate = DeepSeekScreeningEvaluationAdapter(settings=settings)
    plan_records: list[dict[str, Any]] = []
    plans: list[GeneratedPlanContentV5 | None] = []
    for index, case in enumerate(V5_PLAN_JDS):
        record, plan = await _run_plan(case, index, AuditedPlanAdapter(plan_delegate, attempts, guard, f"P{index:02d}"))
        plan_records.append(record)
        plans.append(plan)
    report_records: list[dict[str, Any]] = []
    for index, pair in enumerate(V5_REPORT_PAIRS):
        report_records.append(await _run_report(pair, index, plans[_plan_case_index(pair)], AuditedReportAdapter(report_delegate, attempts, guard, f"R{index:02d}"), run_kind="report", run_number=1))
    stability_records: list[dict[str, Any]] = []
    for sample_index in V5_STABILITY_SAMPLE_INDICES:
        pair = V5_REPORT_PAIRS[sample_index]
        for run_number in range(1, 4):
            case_id = f"S{sample_index:02d}-{run_number}"
            stability_records.append(await _run_report(pair, sample_index, plans[_plan_case_index(pair)], AuditedReportAdapter(report_delegate, attempts, guard, case_id), run_kind="stability", run_number=run_number))
    if len(attempts) > MAXIMUM_API_ATTEMPTS:
        raise RuntimeError("真实 API attempt 超过冻结安全硬上限")
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("真实运行期间历史结果被修改")
    payload = {
        "stage": run_id,
        "mode": "real_raw",
        "generated_at": _utc_now(),
        "fixture": fixture,
        "execution_contract": expected,
        "call_budget": call_budget(),
        "result_lifecycle_before": lifecycle,
        "official_pricing_snapshot": pricing,
        "monetary_cap_usd": monetary_cap_usd,
        "estimated_spend_usd": guard.estimated_spend_usd,
        "failed_attempt_reserve_usd": guard.failed_attempt_reserve_usd,
        "attempt_audit_summary": summarize_attempts(attempts, guard),
        "attempt_audit": attempts,
        "plan_records": plan_records,
        "report_records": report_records,
        "stability_records": stability_records,
        "summaries": {"plans": summarize_plans(plan_records), "reports": summarize_reports(report_records), "stability": summarize_reports(stability_records, stability=True)},
        "historical_result_hashes_before": historical_before,
        "historical_result_hashes_after": historical_after,
        "requires_frozen_human_audit": True,
        "quality_gate_passed": None,
        "quality_conclusion_allowed": False,
    }
    write_new_json(
        I2_RAW_RESULT_PATH,
        payload,
        run_id=run_id,
        expected_state="i2_preflight_complete",
    )
    return payload


def _validate_raw_result_for_finalize(raw: dict[str, Any]) -> None:
    if raw.get("stage") != "7R5-I" or raw.get("mode") != "real_raw":
        raise RuntimeError("raw result 不是冻结的 7R5-I 原始结果")
    if raw.get("execution_contract") != execution_contract():
        raise RuntimeError("raw result 的模型、Prompt、Schema 或参数合同已漂移")
    if raw.get("call_budget") != call_budget():
        raise RuntimeError("raw result 的调用预算合同已漂移")
    fixture = raw.get("fixture")
    if not isinstance(fixture, dict) or fixture.get("hashes", {}).get("fixture") != FROZEN_FIXTURE_SHA256:
        raise RuntimeError("raw result 没有绑定冻结的 5.0 样本与标签")
    expected_lengths = (("plan_records", 10), ("report_records", 20), ("stability_records", 15))
    if any(not isinstance(raw.get(key), list) or len(raw[key]) != length for key, length in expected_lengths):
        raise RuntimeError("raw result 的计划、报告或稳定性固定分母不完整")
    attempts = raw.get("attempt_audit")
    summary = raw.get("attempt_audit_summary")
    if not isinstance(attempts, list) or not isinstance(summary, dict):
        raise RuntimeError("raw result 缺少逐 attempt 审计或汇总")
    if len(attempts) > MAXIMUM_API_ATTEMPTS or summary.get("api_attempt_count") != len(attempts):
        raise RuntimeError("raw result 超过 attempt 硬上限或汇总不一致")
    per_case: dict[str, list[int]] = {}
    for attempt in attempts:
        if not isinstance(attempt, dict) or not isinstance(attempt.get("case_id"), str):
            raise RuntimeError("raw result 包含非法 attempt 审计")
        per_case.setdefault(attempt["case_id"], []).append(attempt.get("attempt_number"))
        if attempt.get("result") == "succeeded" and not isinstance(attempt.get("raw_response"), str):
            raise RuntimeError("成功 attempt 缺少原始响应审计")
    if any(numbers not in ([1], [1, 2]) for numbers in per_case.values()):
        raise RuntimeError("单次业务调用的 attempt 编号或重试上限非法")
    if raw.get("historical_result_hashes_before") != HISTORICAL_RESULT_HASHES or raw.get(
        "historical_result_hashes_after"
    ) != HISTORICAL_RESULT_HASHES:
        raise RuntimeError("raw result 未证明历史质量证据保持不变")
    if raw.get("quality_gate_passed") is not None or raw.get("quality_conclusion_allowed") is not False:
        raise RuntimeError("raw result 无权在人工审计前给出质量结论")


def finalize_payload() -> dict[str, Any]:
    if not RAW_RESULT_PATH.exists() or not HUMAN_AUDIT_PATH.exists():
        raise RuntimeError("最终汇总需要不可覆盖的真实 raw result 与人工审计文件")
    if FINAL_RESULT_PATH.exists():
        raise RuntimeError("最终质量结果已经存在，拒绝覆盖")
    raw = json.loads(RAW_RESULT_PATH.read_text(encoding="utf-8"))
    audit = json.loads(HUMAN_AUDIT_PATH.read_text(encoding="utf-8"))
    _validate_raw_result_for_finalize(raw)
    if audit.get("raw_result_sha256") != sha256_file(RAW_RESULT_PATH):
        raise RuntimeError("人工审计没有绑定当前不可变 raw result")
    if audit.get("fixture_sha256") != FROZEN_FIXTURE_SHA256:
        raise RuntimeError("人工审计没有绑定冻结样本/标签")
    metrics = audit.get("metrics")
    if not isinstance(metrics, dict):
        raise RuntimeError("人工审计缺少固定 metrics")
    if audit.get("method") != "human_review_against_frozen_labels":
        raise RuntimeError("人工审计方法未绑定冻结人工标签")
    if not isinstance(audit.get("auditor"), str) or not audit["auditor"].strip():
        raise RuntimeError("人工审计缺少审阅人记录")
    try:
        audited_at = datetime.fromisoformat(str(audit["audited_at"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("人工审计缺少带时区 audited_at") from None
    if audited_at.tzinfo is None:
        raise RuntimeError("人工审计 audited_at 必须带时区")
    metric_contract = human_audit_contract()["metrics"]
    if set(metrics) != set(metric_contract):
        raise RuntimeError("人工审计 metrics 未严格覆盖冻结字段")
    for key, bounds in metric_contract.items():
        value = metrics[key]
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < bounds["minimum"]
            or value > bounds["maximum"]
        ):
            raise RuntimeError(f"人工审计 metric 超出冻结范围：{key}")
    automatic = raw["summaries"]
    gates = {
        "plan_10_of_10_legal": automatic["plans"]["structure_legal_count"] == 10,
        "plan_required_coverage_100_percent": metrics.get("plan_required_covered_count") == 55,
        "plan_forbidden_additions_zero": metrics.get("plan_forbidden_addition_count") == 0,
        "plan_sensitive_zero": metrics.get("plan_sensitive_criterion_count") == 0,
        "plan_non_evaluation_zero": metrics.get("plan_non_evaluation_misclassified_count") == 0,
        "plan_traceability_100_percent": automatic["plans"]["traceable_plan_count"] == 10,
        "report_20_of_20_legal": automatic["reports"]["legal_report_count"] == 20,
        "report_nonzero_evidence_100_percent": automatic["reports"]["nonzero_assessment_count"] == automatic["reports"]["nonzero_with_evidence_count"],
        "report_fabrication_zero": metrics.get("report_fabricated_fact_count") == 0,
        "report_severe_fact_error_zero": metrics.get("report_severe_fact_error_count") == 0,
        "report_sensitive_scoring_zero": metrics.get("report_sensitive_scoring_count") == 0,
        "report_automatic_decision_zero": metrics.get("report_automatic_decision_count") == 0,
        "report_direction_at_least_80_percent": metrics.get("report_direction_consistent_count", -1) >= 16,
        "required_direction_at_least_90_percent": metrics.get("required_direction_consistent_count", -1) >= 97,
        "report_sections_20_of_20": automatic["reports"]["all_required_sections_count"] == 20,
        "stability_direction_at_least_4_of_5": automatic["stability"]["direction_stable_group_count"] >= 4,
        "stability_spread_at_least_4_of_5": automatic["stability"]["max_difference_le_10_group_count"] >= 4,
        "stability_extreme_flip_zero": automatic["stability"]["extreme_direction_flip_count"] == 0,
        "stability_severe_and_sensitive_zero": metrics.get("stability_severe_fact_error_count") == 0 and metrics.get("stability_sensitive_scoring_count") == 0,
    }
    payload = {
        "stage": "7R5-I",
        "mode": "finalized_human_and_deterministic_gate",
        "generated_at": _utc_now(),
        "raw_result_path": str(RAW_RESULT_PATH),
        "raw_result_sha256": sha256_file(RAW_RESULT_PATH),
        "human_audit_path": str(HUMAN_AUDIT_PATH),
        "human_audit_sha256": sha256_file(HUMAN_AUDIT_PATH),
        "gates": gates,
        "quality_gate_passed": all(gates.values()),
        "quality_conclusion_allowed": True,
    }
    write_new_json(FINAL_RESULT_PATH, payload)
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7 5.0 quality runner")
    parser.add_argument("--mode", choices=("dry-run", "fake-normal", "fake-failure", "real", "finalize"), required=True)
    parser.add_argument("--pricing-snapshot", type=Path)
    parser.add_argument("--run-id", default=ACTIVE_RUN_ID)
    money = parser.add_mutually_exclusive_group()
    money.add_argument("--monetary-cap-usd", type=float)
    money.add_argument("--no-monetary-cap", action="store_true")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.mode == "dry-run":
        payload = dry_run_payload(run_id=args.run_id)
    elif args.mode == "fake-normal":
        payload = await fake_payload(failure=False, run_id=args.run_id)
    elif args.mode == "fake-failure":
        payload = await fake_payload(failure=True, run_id=args.run_id)
    elif args.mode == "finalize":
        payload = finalize_payload()
    else:
        if args.pricing_snapshot is None:
            raise RuntimeError("真实运行必须提供 24 小时内的官方价格快照")
        if not args.no_monetary_cap and args.monetary_cap_usd is None:
            raise RuntimeError("真实运行必须明确金额上限或 --no-monetary-cap")
        if args.monetary_cap_usd is not None and args.monetary_cap_usd <= 0:
            raise RuntimeError("金额上限必须大于 0")
        payload = await real_payload(
            pricing_path=args.pricing_snapshot,
            monetary_cap_usd=args.monetary_cap_usd,
            run_id=args.run_id,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
