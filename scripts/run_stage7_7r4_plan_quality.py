from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_ROOT))

from app.adapters.job_evaluation_plan import (  # noqa: E402
    DeepSeekJobEvaluationPlanAdapter,
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings  # noqa: E402
from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_CRITERION_GROUPING_PROMPT_VERSION,
    JOB_REQUIREMENT_COVERAGE_REVIEW_PROMPT_VERSION,
    JOB_REQUIREMENT_FACT_EXTRACTION_PROMPT_VERSION,
    JOB_REQUIREMENT_LOCAL_REPAIR_PROMPT_VERSION,
    build_evaluation_criterion_grouping_messages,
    build_requirement_coverage_review_messages,
    build_requirement_fact_extraction_messages,
    build_requirement_local_repair_messages,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION,
    JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION,
    JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_TOKENS,
    JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    GeneratedPlanContentV4,
    JobEvaluationPlanV4GenerationError,
    job_evaluation_plan_service,
)
from stage7_7r4_quality_contract import (  # noqa: E402
    EXPECTED_V4_OUTCOMES,
    EXPECTED_V4_WARNING_CODES,
    EXPECTED_PLAN_PROMPT_VERSIONS,
    FORMAL_CASE_IDS,
    FROZEN_CASE_SHA256,
    HISTORICAL_RESULT_PATHS,
    OFFICIAL_PRICING_SOURCE_URL,
    PLAN_FORMAL_RESULT_PATH,
    PLAN_PROMPT_ROLES,
    PLAN_REPAIR_ROLE,
    PLAN_TARGETED_RESULT_PATH,
    PLANNED_MODEL,
    TARGETED_MAXIMUM_API_ATTEMPTS,
    TARGETED_MAXIMUM_BUSINESS_CALLS,
    TARGETED_CASE_IDS,
    estimate_attempt_cost_usd,
    validate_historical_results,
    load_and_validate_targeted_gate,
    model_and_cost_inputs,
    model_execution_contract,
    plan_quality_gate_passed,
    plan_call_budget,
    result_paths,
    validate_frozen_plan_fixture,
    validate_official_pricing_snapshot,
    validate_result_path_isolation,
    write_new_json,
)
from stage7_7rf_plan_quality_cases import CASES  # noqa: E402


PROMPT_VERSIONS = {
    "fact_extraction": JOB_REQUIREMENT_FACT_EXTRACTION_PROMPT_VERSION,
    "coverage_review": JOB_REQUIREMENT_COVERAGE_REVIEW_PROMPT_VERSION,
    "local_repair": JOB_REQUIREMENT_LOCAL_REPAIR_PROMPT_VERSION,
    "criterion_grouping": JOB_EVALUATION_CRITERION_GROUPING_PROMPT_VERSION,
}
PROMPT_BUILDERS = {
    "fact_extraction": build_requirement_fact_extraction_messages,
    "coverage_review": build_requirement_coverage_review_messages,
    "local_repair": build_requirement_local_repair_messages,
    "criterion_grouping": build_evaluation_criterion_grouping_messages,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_job(case: dict[str, Any], index: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=84_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=case["job_background"],
        job_responsibilities=case["job_responsibilities"],
        candidate_requirements=case["candidate_requirements"],
        preferred_qualifications=case["preferred_qualifications"],
        public_notes=case["public_notes"],
        status="open",
    )


def _selected_cases(mode: str) -> list[dict[str, Any]]:
    selected_ids = TARGETED_CASE_IDS if mode == "targeted" else FORMAL_CASE_IDS
    by_id = {case["case_id"]: case for case in CASES}
    return [by_id[case_id] for case_id in selected_ids]


def _fixture_and_versions() -> dict[str, Any]:
    fixture = validate_frozen_plan_fixture(CASES)
    snapshots: list[dict[str, Any]] = []
    source_unit_counts: dict[str, int] = {}
    public_notes_excluded = True
    for index, case in enumerate(CASES, start=1):
        snapshot = job_evaluation_plan_service.build_v4_input_snapshot(
            _case_job(case, index)
        )
        payload = snapshot.model_dump(mode="json")
        rendered = json.dumps(payload, ensure_ascii=False)
        public_notes_excluded &= case["public_notes"] not in rendered
        snapshots.append(payload)
        source_unit_counts[case["case_id"]] = len(snapshot.source_units or [])
    if not public_notes_excluded:
        raise RuntimeError("public_notes 意外进入 4.0 计划输入")
    if sum(source_unit_counts.values()) != 255:
        raise RuntimeError("冻结 source unit 统计分母已经漂移")
    if JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION != "4.0":
        raise RuntimeError("计划 Schema 版本不是 4.0")
    if JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION != "job_evaluation_input_v4":
        raise RuntimeError("计划指纹规则版本不匹配")
    if (
        JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION
        != "fact_criterion_plan_generation_v1"
    ):
        raise RuntimeError("计划破坏性生成合同版本不匹配")
    if PROMPT_VERSIONS != EXPECTED_PLAN_PROMPT_VERSIONS:
        raise RuntimeError("4.0 Prompt 角色或版本不完整")
    return {
        **fixture,
        "source_unit_denominator": 255,
        "targeted_source_unit_denominator": sum(
            source_unit_counts[case_id] for case_id in TARGETED_CASE_IDS
        ),
        "source_unit_counts": source_unit_counts,
        "public_notes_excluded_from_every_input": public_notes_excluded,
        "plan_schema_version": JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
        "fingerprint_rule_version": JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION,
        "breaking_contract_version": JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION,
        "prompt_versions": PROMPT_VERSIONS,
        "max_output_tokens": JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_TOKENS,
    }


def dry_run_payload() -> dict[str, Any]:
    historical_before = validate_historical_results()
    fixture = _fixture_and_versions()
    path_contract = validate_result_path_isolation()
    historical_after = validate_historical_results()
    if historical_before != historical_after:
        raise RuntimeError("dry-run 期间历史结果发生变化")
    return {
        "stage": "7R4-G",
        "mode": "dry_run",
        "status": "ready_for_7R4_HR2_cost_confirmation",
        "generated_at": _utc_now(),
        "fixture": fixture,
        "call_budget": plan_call_budget(),
        "model_and_cost_inputs": model_and_cost_inputs(),
        "result_path_contract": path_contract,
        "formal_gate": {
            "requires_exact_new_v4_targeted_result": True,
            "required_path": str(PLAN_TARGETED_RESULT_PATH),
            "missing_failed_or_mismatched_result_blocks_before_adapter": True,
            "legacy_3_0_targeted_gate_is_never_accepted": True,
        },
        "historical_results_before": historical_before,
        "historical_results_after": historical_after,
        "real_model_call_count": 0,
        "adapter_instantiated": False,
        "api_key_read_as_prerequisite": False,
        "formal_quality_result_write_count": 0,
        "writes_result_file": False,
        "quality_conclusion_allowed": False,
    }


def _adapter_result(payload: dict[str, Any]) -> JobEvaluationPlanAdapterResult:
    return JobEvaluationPlanAdapterResult(
        content=json.dumps(payload, ensure_ascii=False),
        model="7r4g-fake-plan-model",
        finish_reason="stop",
        input_tokens=100,
        cache_hit_input_tokens=40,
        cache_miss_input_tokens=60,
        output_tokens=50,
    )


def _source_for_expectation(
    expectation: dict[str, Any],
    source_units: list[Any],
) -> tuple[Any, str]:
    for unit in source_units:
        if unit.source_field != expectation["source_field"]:
            continue
        for term in expectation["title_any"]:
            if term in unit.source_text:
                return unit, term
    raise RuntimeError(
        f"冻结 expectation 无法定位：{expectation['expectation_id']}"
    )


def _faithful_extraction(
    case: dict[str, Any],
    snapshot: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    units = list(snapshot.source_units or [])
    candidates: list[dict[str, Any]] = []
    candidate_ids_by_unit: dict[str, list[str]] = defaultdict(list)
    for index, expectation in enumerate(case["expectations"], start=1):
        unit, quote = _source_for_expectation(expectation, units)
        sources = [
            {
                "source_field": unit.source_field,
                "source_unit_id": unit.source_unit_id,
                "source_quote": quote,
            }
        ]
        if expectation["min_sources"] > 1:
            for extra_unit in units:
                if extra_unit.source_unit_id == unit.source_unit_id:
                    continue
                matching_term = next(
                    (
                        term
                        for term in expectation["title_any"]
                        if term in extra_unit.source_text
                    ),
                    None,
                )
                if matching_term is None:
                    continue
                sources.append(
                    {
                        "source_field": extra_unit.source_field,
                        "source_unit_id": extra_unit.source_unit_id,
                        "source_quote": matching_term,
                    }
                )
                if len(sources) >= expectation["min_sources"]:
                    break
        if len(sources) < expectation["min_sources"]:
            raise RuntimeError("冻结多来源 fact 无法构造 Fake 期望")
        candidate_id = f"candidate:{index:04d}"
        candidate = {
            "candidate_id": candidate_id,
            "category": "other",
            "sources": sources,
        }
        candidates.append(candidate)
        for source in sources:
            candidate_ids_by_unit[source["source_unit_id"]].append(candidate_id)
    reviews = []
    for unit in units:
        candidate_ids = list(dict.fromkeys(candidate_ids_by_unit[unit.source_unit_id]))
        reviews.append(
            {
                "source_unit_id": unit.source_unit_id,
                "disposition": "evaluation" if candidate_ids else "non_evaluation",
                "candidate_ids": candidate_ids,
                "non_evaluation_reason": None if candidate_ids else "other",
                "warning_codes": [],
            }
        )
    return (
        {
            "fact_candidates": candidates,
            "source_reviews": reviews,
        },
        candidates,
    )


def _fake_outcomes(
    case: dict[str, Any],
    snapshot: Any,
    *,
    repair: bool,
) -> list[JobEvaluationPlanAdapterResult]:
    extraction, candidates = _faithful_extraction(case, snapshot)
    if not repair:
        fact_ids = [f"fact:{index:04d}" for index in range(1, len(candidates) + 1)]
        return [
            _adapter_result(extraction),
            _adapter_result({"status": "passed", "findings": []}),
            _adapter_result(
                {
                    "criteria": [
                        {"name": "冻结事实", "fact_ids": fact_ids}
                    ],
                }
            ),
        ]

    candidates_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        source_ids = {source["source_unit_id"] for source in candidate["sources"]}
        if len(source_ids) == 1:
            candidates_by_unit[next(iter(source_ids))].append(candidate)
    repair_unit_id = next(
        unit_id for unit_id, values in candidates_by_unit.items() if len(values) == 1
    )
    omitted = candidates_by_unit[repair_unit_id][0]
    extraction["fact_candidates"] = [
        candidate for candidate in candidates if candidate is not omitted
    ]
    for review in extraction["source_reviews"]:
        if review["source_unit_id"] == repair_unit_id:
            review.update(
                {
                    "disposition": "non_evaluation",
                    "candidate_ids": [],
                    "non_evaluation_reason": "other",
                }
            )
    repair_source = omitted["sources"][0]
    repair_payload = {
        "replacement_candidates": [
            {
                "candidate_id": "candidate:0001",
                "category": omitted["category"],
                "sources": [repair_source],
                "merge_into_fact_id": None,
            }
        ],
        "source_reviews": [
            {
                "source_unit_id": repair_unit_id,
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0001"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            }
        ],
        "resolved_finding_indexes": [0],
        "unresolved_finding_indexes": [],
    }
    fact_ids = [f"fact:{index:04d}" for index in range(1, len(candidates) + 1)]
    return [
        _adapter_result(extraction),
        _adapter_result(
            {
                "status": "needs_repair",
                "findings": [
                    {
                        "code": "missing_fact",
                        "source_unit_ids": [repair_unit_id],
                        "fact_ids": [],
                        "message": "Fake 定向制造的可定位漏项",
                    }
                ],
            }
        ),
        _adapter_result(repair_payload),
        _adapter_result(
            {
                "criteria": [{"name": "冻结事实", "fact_ids": fact_ids}],
            }
        ),
    ]


async def run_fake_scenario(*, repair: bool) -> dict[str, Any]:
    case = next(case for case in CASES if case["case_id"] == "J5-03")
    snapshot = job_evaluation_plan_service.build_v4_input_snapshot(
        _case_job(case, 3)
    )
    adapter = FakeJobEvaluationPlanAdapter(
        _fake_outcomes(case, snapshot, repair=repair)
    )
    content = await job_evaluation_plan_service.build_v4_plan_content(
        snapshot,
        adapter=adapter,
    )
    actual_roles = [call["role"] for call in adapter.v4_calls]
    expected_roles = [*PLAN_PROMPT_ROLES[:2]]
    if repair:
        expected_roles.append(PLAN_REPAIR_ROLE)
    expected_roles.append(PLAN_PROMPT_ROLES[2])
    if actual_roles != expected_roles:
        raise RuntimeError("Fake 业务调用顺序不符合 4.0 合同")
    if content.generation_audit.business_call_count != len(expected_roles):
        raise RuntimeError("Fake 业务调用统计不是从实际审计记录产生")
    quality_audit = _audit_success(case, snapshot, content)
    if not quality_audit["sample_contract_passed"]:
        raise RuntimeError("Fake 结果未通过与真实轮相同的第 15 节逐样本审计")
    return {
        "stage": "7R4-G",
        "mode": "fake_repair" if repair else "fake_normal",
        "case_id": case["case_id"],
        "actual_adapter_attempt_count": len(adapter.v4_calls),
        "actual_role_order": actual_roles,
        "generation_audit": content.generation_audit.model_dump(mode="json"),
        "quality_audit": quality_audit,
        "fact_count": len(content.requirement_facts),
        "criterion_count": len(content.evaluation_criteria),
        "real_model_call_count": 0,
        "formal_quality_result_write_count": 0,
        "quality_conclusion_allowed": False,
    }


class QualityRunCallBudgetExceeded(RuntimeError):
    pass


class QualityRunAuditLedger:
    def __init__(
        self,
        pricing_snapshot: dict[str, Any],
        *,
        maximum_business_calls: int = TARGETED_MAXIMUM_BUSINESS_CALLS,
        maximum_api_attempts: int = TARGETED_MAXIMUM_API_ATTEMPTS,
    ) -> None:
        self.pricing_snapshot = validate_official_pricing_snapshot(pricing_snapshot)
        self.maximum_business_calls = maximum_business_calls
        self.maximum_api_attempts = maximum_api_attempts
        self.attempts: list[dict[str, Any]] = []
        self.business_call_count = 0
        self.infrastructure_retry_count = 0
        self.stopped_reason: str | None = None

    def reserve(self, *, case_id: str, role: str) -> dict[str, Any]:
        previous = next(
            (
                item
                for item in reversed(self.attempts)
                if item["case_id"] == case_id
            ),
            None,
        )
        is_infrastructure_retry = bool(
            previous
            and previous["role"] == role
            and previous["result"] == "failed"
            and previous["retryable"] is True
        )
        if is_infrastructure_retry and previous["is_infrastructure_retry"] is True:
            self.stopped_reason = "per_business_call_retry_budget_exhausted"
            raise QualityRunCallBudgetExceeded(self.stopped_reason)
        if len(self.attempts) >= self.maximum_api_attempts:
            self.stopped_reason = "api_attempt_budget_exhausted"
            raise QualityRunCallBudgetExceeded(self.stopped_reason)
        if (
            not is_infrastructure_retry
            and self.business_call_count >= self.maximum_business_calls
        ):
            self.stopped_reason = "business_call_budget_exhausted"
            raise QualityRunCallBudgetExceeded(self.stopped_reason)
        if is_infrastructure_retry:
            self.infrastructure_retry_count += 1
        else:
            self.business_call_count += 1
        return {
            "case_id": case_id,
            "role": role,
            "attempt_number": len(self.attempts) + 1,
            "case_attempt_number": (
                sum(item["case_id"] == case_id for item in self.attempts) + 1
            ),
            "business_call_number": self.business_call_count,
            "is_infrastructure_retry": is_infrastructure_retry,
        }

    def append(self, record: dict[str, Any]) -> None:
        cost = estimate_attempt_cost_usd(
            pricing_snapshot=self.pricing_snapshot,
            input_tokens=record.get("input_tokens"),
            cache_hit_input_tokens=record.get("cache_hit_input_tokens"),
            cache_miss_input_tokens=record.get("cache_miss_input_tokens"),
            output_tokens=record.get("output_tokens"),
        )
        record["cost_estimate"] = cost
        self.attempts.append(record)

    def for_case(self, case_id: str) -> list[dict[str, Any]]:
        return [item for item in self.attempts if item["case_id"] == case_id]

    def summary(self) -> dict[str, Any]:
        priced = [
            item["cost_estimate"]["estimated_cost_usd"]
            for item in self.attempts
            if item["cost_estimate"]["complete"]
        ]
        return {
            "adapter_attempt_count": len(self.attempts),
            "business_call_count": self.business_call_count,
            "infrastructure_retry_count": self.infrastructure_retry_count,
            "content_repair_count": sum(
                item["role"] == PLAN_REPAIR_ROLE
                and item["is_infrastructure_retry"] is False
                for item in self.attempts
            ),
            "succeeded_attempt_count": sum(
                item["result"] == "succeeded" for item in self.attempts
            ),
            "failed_attempt_count": sum(
                item["result"] == "failed" for item in self.attempts
            ),
            "priced_attempt_count": len(priced),
            "unpriced_attempt_count": len(self.attempts) - len(priced),
            "estimated_cost_usd": sum(priced),
            "monetary_cap_usd": None,
            "maximum_business_calls": self.maximum_business_calls,
            "maximum_api_attempts": self.maximum_api_attempts,
            "stopped_reason": self.stopped_reason,
        }


class RecordingAdapter:
    def __init__(
        self,
        delegate: DeepSeekJobEvaluationPlanAdapter,
        *,
        case_id: str,
        ledger: QualityRunAuditLedger,
    ) -> None:
        self.delegate = delegate
        self.case_id = case_id
        self.ledger = ledger

    @property
    def attempts(self) -> list[dict[str, Any]]:
        return self.ledger.for_case(self.case_id)

    async def generate_v4(
        self,
        role: str,
        generation_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        reservation = self.ledger.reserve(case_id=self.case_id, role=role)
        started = time.perf_counter()
        contract = model_execution_contract()
        record: dict[str, Any] = {
            **reservation,
            "input": generation_input,
            "requested_model": contract["model"],
            "thinking": contract["thinking"],
            "temperature": contract["temperature"],
            "response_format": contract["response_format"],
            "max_output_tokens": contract["max_output_tokens_per_business_call"],
            "sdk_automatic_retries": contract["sdk_automatic_retries"],
            "prompt_version": PROMPT_VERSIONS[role],
        }
        try:
            result = await self.delegate.generate_v4(role, generation_input)
        except JobEvaluationPlanAdapterError as exc:
            record.update(
                {
                    "result": "failed",
                    "error_code": exc.code,
                    "retryable": exc.retryable,
                    "model": exc.model,
                    "finish_reason": exc.finish_reason,
                    "input_tokens": exc.input_tokens,
                    "cache_hit_input_tokens": exc.cache_hit_input_tokens,
                    "cache_miss_input_tokens": exc.cache_miss_input_tokens,
                    "output_tokens": exc.output_tokens,
                    "raw_response": exc.raw_response,
                }
            )
            raise
        except Exception as exc:
            record.update(
                {
                    "result": "failed",
                    "error_code": type(exc).__name__,
                    "retryable": False,
                    "model": None,
                    "finish_reason": None,
                    "input_tokens": None,
                    "cache_hit_input_tokens": None,
                    "cache_miss_input_tokens": None,
                    "output_tokens": None,
                    "raw_response": None,
                }
            )
            raise
        else:
            record.update(
                {
                    "result": "succeeded",
                    "error_code": None,
                    "retryable": False,
                    "model": result.model,
                    "finish_reason": result.finish_reason,
                    "input_tokens": result.input_tokens,
                    "cache_hit_input_tokens": result.cache_hit_input_tokens,
                    "cache_miss_input_tokens": result.cache_miss_input_tokens,
                    "output_tokens": result.output_tokens,
                    "raw_response": result.content,
                }
            )
            return result
        finally:
            record["duration_ms"] = round((time.perf_counter() - started) * 1000)
            self.ledger.append(record)

    async def extract(self, extraction_input: dict[str, Any]) -> Any:
        raise AssertionError("4.0 质量运行器不得调用 3.0 extract")


def _audit_success(
    case: dict[str, Any],
    snapshot: Any,
    content: GeneratedPlanContentV4,
) -> dict[str, Any]:
    units = {unit.source_unit_id: unit for unit in snapshot.source_units or []}
    facts = [fact.model_dump(mode="json") for fact in content.requirement_facts]
    matched_expectations = 0
    matched_required = 0
    source_merge_failures = 0
    matches_by_expectation: dict[str, list[str]] = {}
    for expectation in case["expectations"]:
        matches = []
        for fact in facts:
            sources = fact["sources"]
            if expectation["source_field"] not in {
                source["source_field"] for source in sources
            }:
                continue
            combined_quotes = "\n".join(source["source_quote"] for source in sources)
            if any(term in combined_quotes for term in expectation["title_any"]):
                matches.append(fact)
        if matches:
            matched_expectations += 1
            if expectation["explicit_required"] and any(
                fact["priority"] == "required" for fact in matches
            ):
                matched_required += 1
            if not any(
                len(fact["sources"]) >= expectation["min_sources"]
                for fact in matches
            ):
                source_merge_failures += 1
        matches_by_expectation[expectation["expectation_id"]] = [
            fact["fact_id"] for fact in matches
        ]
    traceable = 0
    priority_consistent = 0
    priority_rank = {"general": 0, "preferred": 1, "required": 2}
    priority_by_field = {
        "job_responsibilities": "general",
        "candidate_requirements": "required",
        "preferred_qualifications": "preferred",
    }
    for fact in facts:
        valid = bool(fact["sources"])
        source_priorities = []
        for source in fact["sources"]:
            unit = units.get(source["source_unit_id"])
            valid &= bool(
                unit
                and unit.source_field == source["source_field"]
                and source["source_quote"] in unit.source_text
            )
            source_priorities.append(priority_by_field[source["source_field"]])
        traceable += bool(valid)
        expected_priority = max(source_priorities, key=priority_rank.get)
        priority_consistent += fact["priority"] == expected_priority
    review = content.source_review_summary
    reviewed_ids = [unit.source_unit_id for unit in review.units]
    source_review_complete = bool(
        review.all_reviewed
        and review.total_units == len(units)
        and review.reviewed_units == len(units)
        and len(reviewed_ids) == len(set(reviewed_ids))
        and set(reviewed_ids) == set(units)
    )
    assignments = Counter(
        fact_id
        for criterion in content.evaluation_criteria
        for fact_id in criterion.fact_ids
    )
    fact_ids = {fact["fact_id"] for fact in facts}
    criterion_coverage_ok = set(assignments) == fact_ids and all(
        count == 1 for count in assignments.values()
    )
    criterion_covered_fact_count = sum(assignments[fact_id] == 1 for fact_id in fact_ids)
    incorrect_merge_fact_ids: set[str] = set()
    for fact in facts:
        matching_expectations = [
            expectation
            for expectation in case["expectations"]
            if expectation["distinct"]
            and fact["fact_id"]
            in matches_by_expectation.get(expectation["expectation_id"], [])
        ]
        if len(matching_expectations) > 1:
            incorrect_merge_fact_ids.add(fact["fact_id"])
    source_signatures = [
        tuple(
            sorted(
                (
                    source["source_field"],
                    source["source_unit_id"],
                    " ".join(source["source_quote"].casefold().split()),
                )
                for source in fact["sources"]
            )
        )
        for fact in facts
    ]
    obvious_duplicate_count = sum(
        count - 1 for count in Counter(source_signatures).values() if count > 1
    )
    promotion_terms = (
        "五险一金",
        "带薪年假",
        "下午茶",
        "免费零食",
        "年度旅游",
        "节日礼物",
        "办公环境",
        "员工活动",
        "面试流程",
    )

    def fact_contains_any(fact: dict[str, Any], terms: tuple[str, ...] | list[str]) -> bool:
        return any(
            term.casefold() in source["source_quote"].casefold()
            for source in fact["sources"]
            for term in terms
        )

    pollution_count = sum(
        fact_contains_any(fact, case["forbidden_item_terms"])
        or any(
            source["source_field"] in {"job_background", "public_notes"}
            for source in fact["sources"]
        )
        for fact in facts
    )
    promotion_count = sum(fact_contains_any(fact, promotion_terms) for fact in facts)
    warnings = {warning.code.value for warning in content.warnings}
    expected_warnings = set(EXPECTED_V4_WARNING_CODES.get(case["case_id"], ()))
    warning_hit_count = len(expected_warnings & warnings)
    outcome_ok = EXPECTED_V4_OUTCOMES[case["case_id"]] == "pending_confirmation"
    contract_passed = all(
        (
            outcome_ok,
            matched_expectations == len(case["expectations"]),
            matched_required
            == sum(bool(item["explicit_required"]) for item in case["expectations"]),
            source_merge_failures == 0,
            traceable == len(facts),
            priority_consistent == len(facts),
            source_review_complete,
            criterion_coverage_ok,
            not incorrect_merge_fact_ids,
            obvious_duplicate_count == 0,
            pollution_count == 0,
            promotion_count == 0,
            warning_hit_count == len(expected_warnings),
        )
    )
    return {
        "case_id": case["case_id"],
        "actual_outcome": "pending_confirmation",
        "expected_outcome": EXPECTED_V4_OUTCOMES[case["case_id"]],
        "sample_contract_passed": contract_passed,
        "manual_fact_denominator": len(case["expectations"]),
        "manual_fact_recalled_count": matched_expectations,
        "explicit_required_denominator": sum(
            bool(item["explicit_required"]) for item in case["expectations"]
        ),
        "explicit_required_recalled_count": matched_required,
        "fact_count": len(facts),
        "source_unit_denominator": len(units),
        "reviewed_source_unit_count": len(set(reviewed_ids)) if source_review_complete else 0,
        "source_review_complete": source_review_complete,
        "traceable_fact_count": traceable,
        "priority_consistent_fact_count": priority_consistent,
        "added_requirement_count": len(facts) - traceable,
        "source_merge_failure_count": source_merge_failures,
        "incorrect_merge_count": len(incorrect_merge_fact_ids),
        "incorrect_merge_fact_ids": sorted(incorrect_merge_fact_ids),
        "obvious_duplicate_count": obvious_duplicate_count,
        "background_or_public_notes_pollution_count": pollution_count,
        "promotion_or_benefit_misclassified_count": promotion_count,
        "criterion_coverage_ok": criterion_coverage_ok,
        "criterion_covered_fact_count": criterion_covered_fact_count,
        "expected_warning_codes": sorted(expected_warnings),
        "actual_warning_codes": sorted(warnings),
        "expected_warning_hit_count": warning_hit_count,
        "generation_audit": content.generation_audit.model_dump(mode="json"),
    }


def _audit_generation_error(
    case: dict[str, Any],
    snapshot: Any,
    error: JobEvaluationPlanV4GenerationError,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    units = {unit.source_unit_id: unit for unit in snapshot.source_units or []}
    actual_outcome = "no_facts" if error.code == "JOB_EVALUATION_PLAN_NO_FACTS" else "failed"
    reviewed_ids: list[str] = []
    successful_extraction = next(
        (
            attempt
            for attempt in attempts
            if attempt.get("role") == "fact_extraction"
            and attempt.get("result") == "succeeded"
            and isinstance(attempt.get("raw_response"), str)
        ),
        None,
    )
    if actual_outcome == "no_facts" and successful_extraction is not None:
        raw_response = successful_extraction["raw_response"]
        try:
            parsed = json.loads(raw_response) if isinstance(raw_response, str) else {}
        except json.JSONDecodeError:
            parsed = {}
        reviews = parsed.get("source_reviews") if isinstance(parsed, dict) else None
        if isinstance(reviews, list):
            reviewed_ids = [
                review.get("source_unit_id")
                for review in reviews
                if isinstance(review, dict)
                and isinstance(review.get("source_unit_id"), str)
            ]
    source_review_complete = bool(
        reviewed_ids
        and len(reviewed_ids) == len(set(reviewed_ids))
        and set(reviewed_ids) == set(units)
    )
    outcome_ok = EXPECTED_V4_OUTCOMES[case["case_id"]] == actual_outcome
    expected_warnings = set(EXPECTED_V4_WARNING_CODES.get(case["case_id"], ()))
    return {
        "case_id": case["case_id"],
        "actual_outcome": actual_outcome,
        "expected_outcome": EXPECTED_V4_OUTCOMES[case["case_id"]],
        "sample_contract_passed": bool(
            outcome_ok
            and actual_outcome == "no_facts"
            and source_review_complete
            and not case["expectations"]
            and not expected_warnings
        ),
        "manual_fact_denominator": len(case["expectations"]),
        "manual_fact_recalled_count": 0,
        "explicit_required_denominator": sum(
            bool(item["explicit_required"]) for item in case["expectations"]
        ),
        "explicit_required_recalled_count": 0,
        "fact_count": 0,
        "source_unit_denominator": len(units),
        "reviewed_source_unit_count": len(set(reviewed_ids)) if source_review_complete else 0,
        "source_review_complete": source_review_complete,
        "traceable_fact_count": 0,
        "priority_consistent_fact_count": 0,
        "added_requirement_count": 0,
        "source_merge_failure_count": 0,
        "incorrect_merge_count": 0,
        "incorrect_merge_fact_ids": [],
        "obvious_duplicate_count": 0,
        "background_or_public_notes_pollution_count": 0,
        "promotion_or_benefit_misclassified_count": 0,
        "criterion_coverage_ok": True,
        "criterion_covered_fact_count": 0,
        "expected_warning_codes": sorted(expected_warnings),
        "actual_warning_codes": [],
        "expected_warning_hit_count": 0,
        "error_code": error.code,
        "generation_audit": error.generation_audit.model_dump(mode="json"),
    }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = len(results)
    contract_passed = sum(bool(result["sample_contract_passed"]) for result in results)
    manual_denominator = sum(result["manual_fact_denominator"] for result in results)
    manual_recalled = sum(result["manual_fact_recalled_count"] for result in results)
    required_denominator = sum(
        result["explicit_required_denominator"] for result in results
    )
    required_recalled = sum(
        result["explicit_required_recalled_count"] for result in results
    )
    business_calls = sum(
        (result.get("generation_audit") or {}).get("business_call_count", 0)
        for result in results
    )
    repair_calls = sum(
        (result.get("generation_audit") or {}).get("content_repair_count", 0)
        for result in results
    )
    infrastructure_retries = sum(
        (result.get("generation_audit") or {}).get("infrastructure_retry_count", 0)
        for result in results
    )
    source_units = sum(result["source_unit_denominator"] for result in results)
    reviewed_source_units = sum(
        result["reviewed_source_unit_count"] for result in results
    )
    fact_count = sum(result["fact_count"] for result in results)
    traceable = sum(result["traceable_fact_count"] for result in results)
    priority_consistent = sum(
        result["priority_consistent_fact_count"] for result in results
    )
    criterion_covered = sum(
        result["criterion_covered_fact_count"] for result in results
    )
    warning_expected = sum(len(result["expected_warning_codes"]) for result in results)
    warning_hit = sum(result["expected_warning_hit_count"] for result in results)
    normal_ids = set(FORMAL_CASE_IDS[:18])
    boundary_ids = {"J5-19", "J5-20"}
    return {
        "sample_contract_denominator": denominator,
        "sample_contract_passed_count": contract_passed,
        "manual_fact_denominator": manual_denominator,
        "manual_fact_recalled_count": manual_recalled,
        "manual_fact_recall_rate": (
            manual_recalled / manual_denominator if manual_denominator else 1.0
        ),
        "explicit_required_denominator": required_denominator,
        "explicit_required_recalled_count": required_recalled,
        "explicit_required_recall_rate": (
            required_recalled / required_denominator if required_denominator else 1.0
        ),
        "source_unit_denominator": source_units,
        "reviewed_source_unit_count": reviewed_source_units,
        "source_review_rate": reviewed_source_units / source_units if source_units else 1.0,
        "fact_count": fact_count,
        "traceable_fact_count": traceable,
        "source_traceability_rate": traceable / fact_count if fact_count else 1.0,
        "priority_consistent_fact_count": priority_consistent,
        "priority_consistency_rate": (
            priority_consistent / fact_count if fact_count else 1.0
        ),
        "criterion_covered_fact_count": criterion_covered,
        "criterion_coverage_rate": criterion_covered / fact_count if fact_count else 1.0,
        "normal_ready_denominator": sum(result["case_id"] in normal_ids for result in results),
        "normal_ready_count": sum(
            result["case_id"] in normal_ids
            and result["actual_outcome"] == "pending_confirmation"
            for result in results
        ),
        "boundary_denominator": sum(result["case_id"] in boundary_ids for result in results),
        "boundary_correct_count": sum(
            result["case_id"] in boundary_ids and result["sample_contract_passed"]
            for result in results
        ),
        "expected_warning_count": warning_expected,
        "expected_warning_hit_count": warning_hit,
        "expected_warning_hit_rate": (
            warning_hit / warning_expected if warning_expected else 1.0
        ),
        "added_requirement_count": sum(result["added_requirement_count"] for result in results),
        "source_merge_failure_count": sum(
            result["source_merge_failure_count"] for result in results
        ),
        "incorrect_merge_count": sum(result["incorrect_merge_count"] for result in results),
        "obvious_duplicate_count": sum(result["obvious_duplicate_count"] for result in results),
        "background_or_public_notes_pollution_count": sum(
            result["background_or_public_notes_pollution_count"] for result in results
        ),
        "promotion_or_benefit_misclassified_count": sum(
            result["promotion_or_benefit_misclassified_count"] for result in results
        ),
        "business_call_count": business_calls,
        "content_repair_count": repair_calls,
        "infrastructure_retry_count": infrastructure_retries,
    }


def _build_real_adapter(
    model: str,
    *,
    case_id: str,
    ledger: QualityRunAuditLedger,
) -> RecordingAdapter:
    settings = Settings(JOB_EVALUATION_PLAN_MODEL=model)
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("7R4-H 真实运行缺少 DeepSeek API Key")
    return RecordingAdapter(
        DeepSeekJobEvaluationPlanAdapter(settings=settings),
        case_id=case_id,
        ledger=ledger,
    )


async def _run_real(
    mode: str,
    model: str,
    pricing_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mode == "formal":
        gate = load_and_validate_targeted_gate()
        output_path = PLAN_FORMAL_RESULT_PATH
    else:
        gate = {"targeted_gate_not_required_for_targeted_round": True}
        output_path = PLAN_TARGETED_RESULT_PATH
    if output_path.exists():
        raise RuntimeError("质量结果文件已存在，拒绝付费调用后覆盖")
    historical_before = validate_historical_results()
    expected_historical = {
        str(path.relative_to(PROJECT_ROOT)) for path in HISTORICAL_RESULT_PATHS
    }
    if set(historical_before["required_paths"]) != expected_historical:
        raise RuntimeError("历史质量结果不完整，拒绝开始真实调用")
    if pricing_snapshot is None:
        raise RuntimeError("真实运行缺少本轮官方峰谷价格快照")
    budget = plan_call_budget()[mode]
    ledger = QualityRunAuditLedger(
        pricing_snapshot,
        maximum_business_calls=budget["safety_hard_maximum_business_calls"],
        maximum_api_attempts=budget[
            "maximum_api_attempts_with_infrastructure_retries"
        ],
    )
    results = []
    for index, case in enumerate(_selected_cases(mode), start=1):
        snapshot = job_evaluation_plan_service.build_v4_input_snapshot(
            _case_job(case, index)
        )
        adapter = _build_real_adapter(
            model,
            case_id=case["case_id"],
            ledger=ledger,
        )
        try:
            content = await job_evaluation_plan_service.build_v4_plan_content(
                snapshot,
                adapter=adapter,
            )
        except JobEvaluationPlanV4GenerationError as exc:
            audited = _audit_generation_error(case, snapshot, exc, adapter.attempts)
            audited["attempts"] = adapter.attempts
            results.append(audited)
        else:
            audited = _audit_success(case, snapshot, content)
            audited["attempts"] = adapter.attempts
            results.append(audited)
        if ledger.stopped_reason is not None:
            break
    summary = _summary(results)
    attempt_summary = ledger.summary()
    if summary["business_call_count"] != attempt_summary["business_call_count"]:
        raise RuntimeError("Service 与逐 attempt 审计的业务调用数不一致")
    if (
        summary["infrastructure_retry_count"]
        != attempt_summary["infrastructure_retry_count"]
    ):
        raise RuntimeError("Service 与逐 attempt 审计的基础设施重试数不一致")
    gate_passed = bool(
        ledger.stopped_reason is None
        and plan_quality_gate_passed(summary, mode=mode)
    )
    payload = {
        "stage": "7R4-HR2" if mode == "targeted" else "7R4-H2",
        "result_kind": (
            "plan_quality_targeted_revalidation"
            if mode == "targeted"
            else "plan_quality_formal"
        ),
        "status": "formal",
        "generated_at": _utc_now(),
        "plan_schema_version": "4.0",
        "frozen_case_sha256": FROZEN_CASE_SHA256,
        "selected_case_ids": [case["case_id"] for case in _selected_cases(mode)],
        "model": model,
        "prompt_versions": PROMPT_VERSIONS,
        "model_parameters": model_execution_contract(),
        "official_pricing_snapshot": ledger.pricing_snapshot,
        "attempt_audit_summary": attempt_summary,
        "attempt_audit": ledger.attempts,
        "formal_gate_input": gate,
        "summary": summary,
        "targeted_gate_passed": gate_passed if mode == "targeted" else None,
        "formal_gate_passed": gate_passed if mode == "formal" else None,
        "quality_conclusion_allowed": gate_passed,
        "historical_results_before": historical_before,
        "cases": results,
    }
    write_new_json(output_path, payload)
    if validate_historical_results() != historical_before:
        raise RuntimeError("真实运行期间历史质量结果身份发生变化")
    return payload


def _pricing_snapshot_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_no_monetary_cap:
        raise SystemExit("7R4-HR2 必须显式确认本轮不设置金额上限")
    required = {
        "official_price_checked_at": args.official_price_checked_at,
        "pricing_tier": args.pricing_tier,
        "peak_schedule": args.peak_schedule,
        "off_peak_cache_hit_price": args.off_peak_cache_hit_price,
        "off_peak_cache_miss_price": args.off_peak_cache_miss_price,
        "off_peak_output_price": args.off_peak_output_price,
        "peak_cache_hit_price": args.peak_cache_hit_price,
        "peak_cache_miss_price": args.peak_cache_miss_price,
        "peak_output_price": args.peak_output_price,
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise SystemExit(f"真实运行缺少官方价格参数：{','.join(missing)}")
    snapshot = validate_official_pricing_snapshot(
        {
            "checked_at": args.official_price_checked_at,
            "source_url": OFFICIAL_PRICING_SOURCE_URL,
            "selected_tier": args.pricing_tier,
            "peak_schedule": args.peak_schedule,
            "usd_per_million_tokens": {
                "off_peak": {
                    "cache_hit_input": args.off_peak_cache_hit_price,
                    "cache_miss_input": args.off_peak_cache_miss_price,
                    "output": args.off_peak_output_price,
                },
                "peak": {
                    "cache_hit_input": args.peak_cache_hit_price,
                    "cache_miss_input": args.peak_cache_miss_price,
                    "output": args.peak_output_price,
                },
            },
        }
    )
    checked_at = datetime.fromisoformat(snapshot["checked_at"])
    now = datetime.now(timezone.utc)
    checked_at_utc = checked_at.astimezone(timezone.utc)
    age_seconds = (now - checked_at_utc).total_seconds()
    if age_seconds < -300:
        raise SystemExit("官方价格检查时间不能晚于当前时间 5 分钟以上")
    if age_seconds > 3600:
        raise SystemExit("官方价格快照已超过 1 小时，真实运行前必须重新查询")
    return snapshot


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7 JobEvaluationPlan 4.0 质量运行器")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "fake-normal", "fake-repair", "targeted", "formal"),
        default="dry-run",
    )
    parser.add_argument("--model", default=PLANNED_MODEL)
    parser.add_argument("--confirm-real-model", action="store_true")
    parser.add_argument("--confirm-no-monetary-cap", action="store_true")
    parser.add_argument("--official-price-checked-at")
    parser.add_argument("--pricing-tier", choices=("off_peak", "peak"))
    parser.add_argument("--peak-schedule")
    parser.add_argument("--off-peak-cache-hit-price", type=float)
    parser.add_argument("--off-peak-cache-miss-price", type=float)
    parser.add_argument("--off-peak-output-price", type=float)
    parser.add_argument("--peak-cache-hit-price", type=float)
    parser.add_argument("--peak-cache-miss-price", type=float)
    parser.add_argument("--peak-output-price", type=float)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.mode == "dry-run":
        payload = dry_run_payload()
    elif args.mode == "fake-normal":
        payload = asyncio.run(run_fake_scenario(repair=False))
    elif args.mode == "fake-repair":
        payload = asyncio.run(run_fake_scenario(repair=True))
    else:
        if not args.confirm_real_model:
            raise SystemExit("7R4-HR2/正式轮真实调用必须显式传入 --confirm-real-model")
        if args.model != PLANNED_MODEL:
            raise SystemExit("真实模型必须与本轮单独确认的 planned model 一致")
        pricing_snapshot = _pricing_snapshot_from_args(args)
        payload = asyncio.run(
            _run_real(args.mode, args.model, pricing_snapshot)
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
