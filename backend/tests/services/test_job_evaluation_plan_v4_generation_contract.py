from __future__ import annotations

import inspect
import json
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.adapters.job_evaluation_plan import (
    DeepSeekJobEvaluationPlanAdapter,
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
    JobEvaluationPlanAuthenticationError,
    JobEvaluationPlanTimeoutError,
)
from app.core.config import Settings
from app.prompts import job_evaluation_plan as prompts
from app.schemas.job_evaluation_plan import (
    AIEvaluationCriterionGroupingOutput,
    AIRequirementCoverageReviewOutput,
    AIRequirementFactExtractionOutput,
    AIRequirementLocalRepairOutput,
    JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
    JobEvaluationPlanInputSnapshot,
    JobEvaluationPlanSourceUnit,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanContentError,
    JobEvaluationPlanV4GenerationError,
    job_evaluation_plan_service,
)


def _snapshot(*, two_units: bool = False) -> JobEvaluationPlanInputSnapshot:
    source_units = [
        {
            "source_unit_id": "candidate_requirements:0001",
            "source_field": "candidate_requirements",
            "ordinal": 1,
            "source_text": "具备 Python 后端开发经验",
        }
    ]
    preferred = None
    if two_units:
        preferred = "有 RAG 项目经验者优先"
        source_units.append(
            {
                "source_unit_id": "preferred_qualifications:0001",
                "source_field": "preferred_qualifications",
                "ordinal": 1,
                "source_text": preferred,
            }
        )
    return JobEvaluationPlanInputSnapshot.model_validate(
        {
            "schema_version": "4.0",
            "job_context": {
                "title": "AI 应用工程师",
                "department": "技术研发部",
                "job_background": "建设企业 AI 应用平台",
            },
            "evaluation_fields": {
                "job_responsibilities": None,
                "candidate_requirements": "具备 Python 后端开发经验",
                "preferred_qualifications": preferred,
            },
            "source_units": source_units,
        }
    )


def _result(payload: object, *, model: str = "fake-plan-model") -> JobEvaluationPlanAdapterResult:
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return JobEvaluationPlanAdapterResult(
        content=content,
        model=model,
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
    )


def _fact_extraction(*, two_units: bool = False) -> dict:
    candidates = [
        {
            "candidate_id": "candidate:0001",
            "category": "experience",
            "sources": [
                {
                    "source_field": "candidate_requirements",
                    "source_unit_id": "candidate_requirements:0001",
                    "source_quote": "具备 Python 后端开发经验",
                }
            ],
        }
    ]
    reviews = [
        {
            "source_unit_id": "candidate_requirements:0001",
            "disposition": "evaluation",
            "candidate_ids": ["candidate:0001"],
            "non_evaluation_reason": None,
            "warning_codes": [],
        }
    ]
    if two_units:
        reviews.append(
            {
                "source_unit_id": "preferred_qualifications:0001",
                "disposition": "non_evaluation",
                "candidate_ids": [],
                "non_evaluation_reason": "other",
                "warning_codes": [],
            }
        )
    return {
        "schema_version": "4.0",
        "fact_candidates": candidates,
        "source_reviews": reviews,
    }


def _coverage_passed() -> dict:
    return {"schema_version": "4.0", "status": "passed", "findings": []}


def _grouping(*fact_ids: str) -> dict:
    return {
        "schema_version": "4.0",
        "criteria": [{"name": "岗位评价事实", "fact_ids": list(fact_ids)}],
    }


def _run(coroutine):
    return asyncio.run(coroutine)


def _without_schema_version(payload: dict) -> dict:
    value = json.loads(json.dumps(payload, ensure_ascii=False))
    value.pop("schema_version", None)
    return value


def _real_adapter_result(role: str, payload: dict) -> JobEvaluationPlanAdapterResult:
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content),
            )
        ],
        model="deepseek-test",
        usage=SimpleNamespace(
            prompt_tokens=10,
            prompt_cache_hit_tokens=4,
            prompt_cache_miss_tokens=6,
            completion_tokens=5,
        ),
    )
    adapter = DeepSeekJobEvaluationPlanAdapter(
        settings=Settings(
            _env_file=None,
            DEEPSEEK_API_KEY="test-key",
            JOB_EVALUATION_PLAN_MODEL="deepseek-test",
        ),
        client=Mock(),
    )
    return adapter._read_v4_response(response, role=role)


@pytest.mark.parametrize(
    ("constant_name", "expected"),
    [
        ("JOB_REQUIREMENT_FACT_EXTRACTION_PROMPT_VERSION", "job_requirement_fact_extraction_v3"),
        ("JOB_REQUIREMENT_COVERAGE_REVIEW_PROMPT_VERSION", "job_requirement_coverage_review_v3"),
        ("JOB_REQUIREMENT_LOCAL_REPAIR_PROMPT_VERSION", "job_requirement_local_repair_v2"),
        ("JOB_EVALUATION_CRITERION_GROUPING_PROMPT_VERSION", "job_evaluation_criterion_grouping_v2"),
    ],
)
def test_v4_declares_four_independent_prompt_roles(
    constant_name: str,
    expected: str,
) -> None:
    assert getattr(prompts, constant_name, None) == expected


def test_v4_prompt_builders_do_not_accept_public_notes() -> None:
    builder_names = (
        "build_requirement_fact_extraction_messages",
        "build_requirement_coverage_review_messages",
        "build_requirement_local_repair_messages",
        "build_evaluation_criterion_grouping_messages",
    )
    for name in builder_names:
        builder = getattr(prompts, name, None)
        assert builder is not None, f"7R4-C 缺少 Prompt builder：{name}"
        assert "public_notes" not in inspect.signature(builder).parameters


def test_v4_fact_and_coverage_v2_prompts_require_global_source_merge_review() -> None:
    extraction_prompt = prompts._FACT_EXTRACTION_SYSTEM_PROMPT
    coverage_prompt = prompts._COVERAGE_REVIEW_SYSTEM_PROMPT

    assert "先完整阅读输入中的全部 source units" in extraction_prompt
    assert "同一类简历证据" in extraction_prompt
    assert "输出前再次扫描全部 candidates" in extraction_prompt
    assert "只共享“客户/数据/项目”等普通词" in extraction_prompt
    assert "missing_source_merge 是强制复核项" in coverage_prompt
    assert "source_unit_ids 中引用全部相关来源" in coverage_prompt
    assert "fact_ids 中引用全部相关现有 facts" in coverage_prompt


def test_v4_prompts_leave_schema_version_to_the_service() -> None:
    for system_prompt in (
        prompts._FACT_EXTRACTION_SYSTEM_PROMPT,
        prompts._COVERAGE_REVIEW_SYSTEM_PROMPT,
        prompts._LOCAL_REPAIR_SYSTEM_PROMPT,
        prompts._CRITERION_GROUPING_SYSTEM_PROMPT,
    ):
        assert "schema_version" not in system_prompt


@pytest.mark.parametrize(
    ("role", "payload", "output_type"),
    [
        (
            "fact_extraction",
            _without_schema_version(_fact_extraction()),
            AIRequirementFactExtractionOutput,
        ),
        (
            "coverage_review",
            _without_schema_version(_coverage_passed()),
            AIRequirementCoverageReviewOutput,
        ),
        (
            "local_repair",
            {
                "replacement_candidates": [],
                "source_reviews": [
                    {
                        "source_unit_id": "candidate_requirements:0001",
                        "disposition": "non_evaluation",
                        "candidate_ids": [],
                        "non_evaluation_reason": "other",
                        "warning_codes": ["non_evaluation_content"],
                    }
                ],
                "resolved_finding_indexes": [0],
                "unresolved_finding_indexes": [],
            },
            AIRequirementLocalRepairOutput,
        ),
        (
            "criterion_grouping",
            _without_schema_version(_grouping("fact:0001")),
            AIEvaluationCriterionGroupingOutput,
        ),
    ],
)
def test_v4_real_adapter_raw_objects_are_service_injected_and_fully_validated(
    role: str,
    payload: dict,
    output_type: type,
) -> None:
    raw_result = _real_adapter_result(role, payload)
    adapter = FakeJobEvaluationPlanAdapter([raw_result])
    audit_calls = []

    parsed = _run(
        job_evaluation_plan_service._invoke_v4_role(
            adapter,
            role,
            {},
            output_type,
            audit_calls,
        )
    )

    assert parsed.schema_version == JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
    assert raw_result.content == json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert "schema_version" not in raw_result.content
    assert len(adapter.v4_calls) == 1
    assert audit_calls[0].result == "succeeded"


def test_v4_explicit_current_schema_version_is_accepted() -> None:
    adapter = FakeJobEvaluationPlanAdapter([_result(_fact_extraction())])
    parsed = _run(
        job_evaluation_plan_service._invoke_v4_role(
            adapter,
            "fact_extraction",
            {},
            AIRequirementFactExtractionOutput,
            [],
        )
    )
    assert parsed.schema_version == JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION


@pytest.mark.parametrize(
    "schema_version",
    ["3.0", "5.0", "4.00", 4, True, None, {"value": "4.0"}, ["4.0"]],
)
def test_v4_conflicting_schema_versions_fail_once_without_retry(
    schema_version: object,
) -> None:
    payload = _fact_extraction()
    payload["schema_version"] = schema_version
    adapter = FakeJobEvaluationPlanAdapter([_result(payload)])

    with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )

    assert caught.value.code == "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"
    assert len(adapter.v4_calls) == 1
    assert caught.value.generation_audit.infrastructure_retry_count == 0


@pytest.mark.parametrize(
    ("role", "payload", "output_type"),
    [
        ("fact_extraction", {"source_reviews": []}, AIRequirementFactExtractionOutput),
        ("fact_extraction", {"fact_candidates": []}, AIRequirementFactExtractionOutput),
        ("coverage_review", {"findings": []}, AIRequirementCoverageReviewOutput),
        ("coverage_review", {"status": "passed"}, AIRequirementCoverageReviewOutput),
        (
            "local_repair",
            {
                "source_reviews": [],
                "resolved_finding_indexes": [],
                "unresolved_finding_indexes": [],
            },
            AIRequirementLocalRepairOutput,
        ),
        ("criterion_grouping", {}, AIEvaluationCriterionGroupingOutput),
    ],
)
def test_v4_missing_business_fields_remain_strict_schema_failures(
    role: str,
    payload: dict,
    output_type: type,
) -> None:
    adapter = FakeJobEvaluationPlanAdapter([_result(payload)])
    with pytest.raises(JobEvaluationPlanContentError) as caught:
        _run(
            job_evaluation_plan_service._invoke_v4_role(
                adapter,
                role,
                {},
                output_type,
                [],
            )
        )
    assert caught.value.code == "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"
    assert len(adapter.v4_calls) == 1


def test_v4_extra_business_field_remains_forbidden() -> None:
    payload = _fact_extraction()
    payload.pop("schema_version")
    payload["unexpected"] = True
    adapter = FakeJobEvaluationPlanAdapter([_result(payload)])
    with pytest.raises(JobEvaluationPlanContentError) as caught:
        _run(
            job_evaluation_plan_service._invoke_v4_role(
                adapter,
                "fact_extraction",
                {},
                AIRequirementFactExtractionOutput,
                [],
            )
        )
    assert caught.value.code == "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"
    assert len(adapter.v4_calls) == 1


def test_v4_service_exposes_pure_generation_workflow() -> None:
    assert hasattr(job_evaluation_plan_service, "build_v4_plan_content")
    assert inspect.iscoroutinefunction(job_evaluation_plan_service.build_v4_plan_content)


def test_v4_normal_workflow_contract_is_three_business_calls() -> None:
    method = getattr(job_evaluation_plan_service, "build_v4_plan_content", None)
    assert method is not None
    source = inspect.getsource(method)
    for role in ("fact_extraction", "coverage_review", "criterion_grouping"):
        assert role in source
    assert "local_repair" in source


def test_v4_content_repair_is_limited_to_one_round() -> None:
    value = getattr(job_evaluation_plan_service, "MAX_V4_CONTENT_REPAIRS", None)
    assert value == 1


def test_v4_infrastructure_retry_is_counted_separately() -> None:
    method = getattr(job_evaluation_plan_service, "build_v4_plan_content", None)
    assert method is not None
    source = inspect.getsource(method)
    assert "infrastructure_retry_count" in source
    assert "content_repair_count" in source


def test_v4_local_repair_accepts_only_failed_source_units() -> None:
    method = getattr(job_evaluation_plan_service, "repair_v4_source_units", None)
    assert method is not None
    signature = inspect.signature(method)
    assert "failed_source_unit_ids" in signature.parameters


def test_v4_priority_is_computed_by_service_not_model() -> None:
    method = getattr(job_evaluation_plan_service, "priority_for_v4_sources", None)
    assert method is not None
    assert method(["general", "preferred", "required"]) == "required"


def test_v4_thirty_one_facts_warn_without_failure_or_truncation() -> None:
    method = getattr(job_evaluation_plan_service, "v4_quantity_warnings", None)
    assert method is not None
    warnings = method(31)
    assert "overly_broad_jd" in warnings
    assert "JOB_EVALUATION_PLAN_TOO_MANY_ITEMS" not in str(warnings)


def test_v4_zero_facts_remains_controlled_failure() -> None:
    method = getattr(job_evaluation_plan_service, "validate_v4_fact_count", None)
    assert method is not None
    with pytest.raises(Exception) as caught:
        method(0)
    assert "JOB_EVALUATION_PLAN_NO_FACTS" in str(caught.value)


def test_v4_failed_generation_does_not_expose_partial_facts_or_criteria() -> None:
    method = getattr(job_evaluation_plan_service, "clear_v4_partial_content", None)
    assert method is not None
    payload = method({"requirement_facts": [{"fact_id": "fact:0001"}]})
    assert payload.get("requirement_facts") in (None, [])
    assert payload.get("evaluation_criteria") in (None, [])


def test_v4_fake_normal_flow_is_exactly_three_business_calls() -> None:
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(_fact_extraction()),
            _result(_coverage_passed()),
            _result(_grouping("fact:0001")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(
            _snapshot(), adapter=adapter
        )
    )

    assert [call["role"] for call in adapter.v4_calls] == [
        "fact_extraction",
        "coverage_review",
        "criterion_grouping",
    ]
    assert content.generation_audit.business_call_count == 3
    assert content.generation_audit.content_repair_count == 0
    assert content.generation_audit.infrastructure_retry_count == 0
    assert content.requirement_facts[0].fact_id == "fact:0001"
    assert content.requirement_facts[0].priority.value == "required"
    assert content.evaluation_criteria[0].criterion_id == "criterion:0001"


def test_v4_fake_repair_flow_is_four_calls_and_only_receives_failed_units() -> None:
    extraction = _fact_extraction(two_units=True)
    extraction["source_reviews"][0]["warning_codes"] = ["ambiguous_requirement"]
    coverage = {
        "schema_version": "4.0",
        "status": "needs_repair",
        "findings": [
            {
                "code": "missing_fact",
                "source_unit_ids": ["preferred_qualifications:0001"],
                "fact_ids": [],
                "message": "加分项尚未形成事实",
            }
        ],
    }
    repair = {
        "schema_version": "4.0",
        "replacement_candidates": [
            {
                "candidate_id": "candidate:0001",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "preferred_qualifications",
                        "source_unit_id": "preferred_qualifications:0001",
                        "source_quote": "有 RAG 项目经验者优先",
                    }
                ],
                "merge_into_fact_id": None,
            }
        ],
        "source_reviews": [
            {
                "source_unit_id": "preferred_qualifications:0001",
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0001"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            }
        ],
        "resolved_finding_indexes": [0],
        "unresolved_finding_indexes": [],
    }
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(extraction),
            _result(coverage),
            _result(repair),
            _result(_grouping("fact:0001", "fact:0002")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(
            _snapshot(two_units=True), adapter=adapter
        )
    )

    assert [call["role"] for call in adapter.v4_calls] == [
        "fact_extraction",
        "coverage_review",
        "local_repair",
        "criterion_grouping",
    ]
    repair_input = adapter.v4_calls[2]["input"]
    assert [unit["source_unit_id"] for unit in repair_input["source_units"]] == [
        "preferred_qualifications:0001"
    ]
    serialized_repair = json.dumps(repair_input, ensure_ascii=False)
    assert "具备 Python 后端开发经验" not in serialized_repair
    assert "public_notes" not in serialized_repair
    assert content.generation_audit.business_call_count == 4
    assert content.generation_audit.content_repair_count == 1
    assert content.coverage_review_summary.repair_performed is True
    assert len(content.requirement_facts) == 2
    assert any(
        warning.code.value == "ambiguous_requirement"
        and warning.source_unit_ids == ["candidate_requirements:0001"]
        for warning in content.warnings
    )


def test_v4_missing_source_merge_repair_merges_sources_into_existing_fact() -> None:
    snapshot = JobEvaluationPlanInputSnapshot.model_validate(
        {
            "schema_version": "4.0",
            "job_context": {"title": "产品经理"},
            "evaluation_fields": {
                "job_responsibilities": None,
                "candidate_requirements": "具备客户访谈经验",
                "preferred_qualifications": "有客户访谈经验者优先",
            },
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": "具备客户访谈经验",
                },
                {
                    "source_unit_id": "preferred_qualifications:0001",
                    "source_field": "preferred_qualifications",
                    "ordinal": 1,
                    "source_text": "有客户访谈经验者优先",
                },
            ],
        }
    )
    extraction = {
        "schema_version": "4.0",
        "fact_candidates": [
            {
                "candidate_id": "candidate:0001",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "candidate_requirements",
                        "source_unit_id": "candidate_requirements:0001",
                        "source_quote": "具备客户访谈经验",
                    }
                ],
            },
            {
                "candidate_id": "candidate:0002",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "preferred_qualifications",
                        "source_unit_id": "preferred_qualifications:0001",
                        "source_quote": "有客户访谈经验者优先",
                    }
                ],
            },
        ],
        "source_reviews": [
            {
                "source_unit_id": "candidate_requirements:0001",
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0001"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            },
            {
                "source_unit_id": "preferred_qualifications:0001",
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0002"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            },
        ],
    }
    coverage = {
        "schema_version": "4.0",
        "status": "needs_repair",
        "findings": [
            {
                "code": "missing_source_merge",
                "source_unit_ids": [
                    "candidate_requirements:0001",
                    "preferred_qualifications:0001",
                ],
                "fact_ids": ["fact:0001", "fact:0002"],
                "message": "同一客户访谈经验被拆成两条事实",
            }
        ],
    }
    repair = {
        "schema_version": "4.0",
        "replacement_candidates": [
            {
                "candidate_id": "candidate:0001",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "candidate_requirements",
                        "source_unit_id": "candidate_requirements:0001",
                        "source_quote": "具备客户访谈经验",
                    },
                    {
                        "source_field": "preferred_qualifications",
                        "source_unit_id": "preferred_qualifications:0001",
                        "source_quote": "有客户访谈经验者优先",
                    },
                ],
                "merge_into_fact_id": "fact:0001",
            }
        ],
        "source_reviews": [
            {
                "source_unit_id": source_unit_id,
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0001"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            }
            for source_unit_id in (
                "candidate_requirements:0001",
                "preferred_qualifications:0001",
            )
        ],
        "resolved_finding_indexes": [0],
        "unresolved_finding_indexes": [],
    }
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(extraction),
            _result(coverage),
            _result(repair),
            _result(_grouping("fact:0001")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(snapshot, adapter=adapter)
    )

    assert [call["role"] for call in adapter.v4_calls] == [
        "fact_extraction",
        "coverage_review",
        "local_repair",
        "criterion_grouping",
    ]
    assert len(content.requirement_facts) == 1
    assert len(content.requirement_facts[0].sources) == 2
    assert content.requirement_facts[0].priority.value == "required"
    assert content.evaluation_criteria[0].fact_ids == ["fact:0001"]


def test_v4_related_customer_work_stays_as_separate_facts_inside_one_criterion() -> None:
    source_texts = [
        "开展客户访谈",
        "编写客户需求文档",
        "组织客户项目版本复盘",
    ]
    snapshot = JobEvaluationPlanInputSnapshot.model_validate(
        {
            "schema_version": "4.0",
            "job_context": {"title": "产品经理"},
            "evaluation_fields": {
                "job_responsibilities": "\n".join(source_texts),
                "candidate_requirements": None,
                "preferred_qualifications": None,
            },
            "source_units": [
                {
                    "source_unit_id": f"job_responsibilities:{index:04d}",
                    "source_field": "job_responsibilities",
                    "ordinal": index,
                    "source_text": source_text,
                }
                for index, source_text in enumerate(source_texts, start=1)
            ],
        }
    )
    extraction = {
        "schema_version": "4.0",
        "fact_candidates": [
            {
                "candidate_id": f"candidate:{index:04d}",
                "category": "responsibility",
                "sources": [
                    {
                        "source_field": "job_responsibilities",
                        "source_unit_id": f"job_responsibilities:{index:04d}",
                        "source_quote": source_text,
                    }
                ],
            }
            for index, source_text in enumerate(source_texts, start=1)
        ],
        "source_reviews": [
            {
                "source_unit_id": f"job_responsibilities:{index:04d}",
                "disposition": "evaluation",
                "candidate_ids": [f"candidate:{index:04d}"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            }
            for index in range(1, 4)
        ],
    }
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(extraction),
            _result(_coverage_passed()),
            _result(_grouping("fact:0001", "fact:0002", "fact:0003")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(snapshot, adapter=adapter)
    )

    assert len(content.requirement_facts) == 3
    assert [
        fact.sources[0].source_quote for fact in content.requirement_facts
    ] == source_texts
    assert len(content.evaluation_criteria) == 1
    assert content.evaluation_criteria[0].fact_ids == [
        "fact:0001",
        "fact:0002",
        "fact:0003",
    ]


@pytest.mark.parametrize(
    ("source_field", "source_text", "expected"),
    [
        ("candidate_requirements", "SQL 数据核查经验优先", True),
        ("candidate_requirements", "SQL experience is PREFERRED", True),
        ("candidate_requirements", "SQL experience is a Plus", True),
        ("candidate_requirements", "必须具备 SQL 数据核查经验", False),
        ("candidate_requirements", "能够优先处理高风险告警", False),
        ("candidate_requirements", "SQL 经验不作为加分项，仅作必备要求", False),
        ("candidate_requirements", "负责设计积分加分规则", False),
        ("candidate_requirements", "Implement the PLUS operator", False),
        ("candidate_requirements", "Store the preferred name", False),
        ("preferred_qualifications", "必须具备审计项目经验", True),
        ("preferred_qualifications", "Audit experience is REQUIRED", True),
        ("preferred_qualifications", "Candidates MUST have audit experience", True),
        ("preferred_qualifications", "审计项目经验优先", False),
        ("preferred_qualifications", "该证书不是必须条件", False),
        ("preferred_qualifications", "Parse the REQUIRED field", False),
        ("preferred_qualifications", "Clients must not expose a required field", False),
    ],
)
def test_v4_priority_signal_conflict_detection_avoids_simple_keyword_false_positives(
    source_field: str,
    source_text: str,
    expected: bool,
) -> None:
    source_unit = JobEvaluationPlanSourceUnit(
        source_unit_id=f"{source_field}:0001",
        source_field=source_field,
        ordinal=1,
        source_text=source_text,
    )
    assert (
        job_evaluation_plan_service._v4_priority_signal_conflicts_with_field(
            source_unit
        )
        is expected
    )


def test_v4_priority_warning_keeps_sql_check_and_audit_project_as_separate_facts() -> None:
    snapshot = JobEvaluationPlanInputSnapshot.model_validate(
        {
            "schema_version": "4.0",
            "job_context": {"title": "安全合规分析师"},
            "evaluation_fields": {
                "job_responsibilities": None,
                "candidate_requirements": "SQL 数据核查经验优先",
                "preferred_qualifications": "必须具备审计项目经验",
            },
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": "SQL 数据核查经验优先",
                },
                {
                    "source_unit_id": "preferred_qualifications:0001",
                    "source_field": "preferred_qualifications",
                    "ordinal": 1,
                    "source_text": "必须具备审计项目经验",
                },
            ],
        }
    )
    extraction = {
        "schema_version": "4.0",
        "fact_candidates": [
            {
                "candidate_id": "candidate:0001",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "candidate_requirements",
                        "source_unit_id": "candidate_requirements:0001",
                        "source_quote": "SQL 数据核查经验优先",
                    }
                ],
            },
            {
                "candidate_id": "candidate:0002",
                "category": "experience",
                "sources": [
                    {
                        "source_field": "preferred_qualifications",
                        "source_unit_id": "preferred_qualifications:0001",
                        "source_quote": "必须具备审计项目经验",
                    }
                ],
            },
        ],
        "source_reviews": [
            {
                "source_unit_id": "candidate_requirements:0001",
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0001"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            },
            {
                "source_unit_id": "preferred_qualifications:0001",
                "disposition": "evaluation",
                "candidate_ids": ["candidate:0002"],
                "non_evaluation_reason": None,
                "warning_codes": [],
            },
        ],
    }
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(extraction),
            _result(_coverage_passed()),
            _result(_grouping("fact:0001", "fact:0002")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(snapshot, adapter=adapter)
    )

    assert len(content.requirement_facts) == 2
    assert [len(fact.sources) for fact in content.requirement_facts] == [1, 1]
    conflicts = [
        warning
        for warning in content.warnings
        if warning.code.value == "conflicting_requirements"
    ]
    assert len(conflicts) == 1
    assert conflicts[0].source_unit_ids == [
        "candidate_requirements:0001",
        "preferred_qualifications:0001",
    ]
    assert conflicts[0].fact_ids == ["fact:0001", "fact:0002"]


def test_v4_infrastructure_retry_adds_attempt_not_business_call() -> None:
    adapter = FakeJobEvaluationPlanAdapter(
        [
            JobEvaluationPlanTimeoutError("temporary timeout"),
            _result(_fact_extraction()),
            _result(_coverage_passed()),
            _result(_grouping("fact:0001")),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(
            _snapshot(), adapter=adapter
        )
    )

    assert len(adapter.v4_calls) == 4
    assert content.generation_audit.business_call_count == 3
    assert content.generation_audit.content_repair_count == 0
    assert content.generation_audit.infrastructure_retry_count == 1
    assert content.generation_audit.calls[0].infrastructure_retry_count == 1


@pytest.mark.parametrize(
    "outcome",
    [
        _result("not-json"),
        _result("[]"),
        _result("null"),
        _result('{"fact_candidates":[],"fact_candidates":[]}'),
        JobEvaluationPlanAuthenticationError("secret upstream detail"),
    ],
)
def test_v4_json_and_authentication_failures_are_not_retried(outcome: object) -> None:
    adapter = FakeJobEvaluationPlanAdapter([outcome])

    with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )

    assert len(adapter.v4_calls) == 1
    assert caught.value.requirement_facts is None
    assert caught.value.evaluation_criteria is None
    assert "secret upstream detail" not in str(caught.value)


def test_v4_zero_facts_fails_before_review_without_partial_payload() -> None:
    extraction = {
        "schema_version": "4.0",
        "fact_candidates": [],
        "source_reviews": [
            {
                "source_unit_id": "candidate_requirements:0001",
                "disposition": "non_evaluation",
                "candidate_ids": [],
                "non_evaluation_reason": "other",
                "warning_codes": ["non_evaluation_content"],
            }
        ],
    }
    adapter = FakeJobEvaluationPlanAdapter([_result(extraction)])

    with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )

    assert caught.value.code == "JOB_EVALUATION_PLAN_NO_FACTS"
    assert caught.value.generation_audit.business_call_count == 1
    assert len(adapter.v4_calls) == 1
    assert caught.value.requirement_facts is None


def test_v4_invalid_quote_and_coverage_reference_fail_safely() -> None:
    invalid_extraction = _fact_extraction()
    invalid_extraction["fact_candidates"][0]["sources"][0][
        "source_quote"
    ] = "原文中不存在的改写"
    adapter = FakeJobEvaluationPlanAdapter([_result(invalid_extraction)])
    with pytest.raises(JobEvaluationPlanV4GenerationError) as quote_error:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )
    assert quote_error.value.code == "JOB_EVALUATION_PLAN_V4_SOURCE_QUOTE_INVALID"

    invalid_coverage = {
        "schema_version": "4.0",
        "status": "needs_repair",
        "findings": [
            {
                "code": "unsupported_fact",
                "source_unit_ids": ["candidate_requirements:0001"],
                "fact_ids": ["fact:9999"],
                "message": "引用不存在",
            }
        ],
    }
    adapter = FakeJobEvaluationPlanAdapter(
        [_result(_fact_extraction()), _result(invalid_coverage)]
    )
    with pytest.raises(JobEvaluationPlanV4GenerationError) as coverage_error:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )
    assert coverage_error.value.code == "JOB_EVALUATION_PLAN_V4_COVERAGE_INVALID"


def test_v4_grouping_failure_has_no_partial_payload() -> None:
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(_fact_extraction()),
            _result(_coverage_passed()),
            _result(_grouping("fact:9999")),
        ]
    )

    with pytest.raises(JobEvaluationPlanV4GenerationError) as caught:
        _run(
            job_evaluation_plan_service.build_v4_plan_content(
                _snapshot(), adapter=adapter
            )
        )

    assert caught.value.code == "JOB_EVALUATION_PLAN_V4_GROUPING_INVALID"
    assert caught.value.requirement_facts is None
    assert caught.value.evaluation_criteria is None
    assert caught.value.generation_audit.business_call_count == 3


def test_v4_thirty_one_facts_are_preserved_with_warning() -> None:
    quotes = [f"要求{index:02d}" for index in range(1, 32)]
    source_text = "；".join(quotes)
    snapshot = JobEvaluationPlanInputSnapshot.model_validate(
        {
            "schema_version": "4.0",
            "job_context": {"title": "复杂岗位"},
            "evaluation_fields": {
                "job_responsibilities": None,
                "candidate_requirements": source_text,
                "preferred_qualifications": None,
            },
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": source_text,
                }
            ],
        }
    )
    candidates = [
        {
            "candidate_id": f"candidate:{index:04d}",
            "category": "other",
            "sources": [
                {
                    "source_field": "candidate_requirements",
                    "source_unit_id": "candidate_requirements:0001",
                    "source_quote": quote,
                }
            ],
        }
        for index, quote in enumerate(quotes, start=1)
    ]
    extraction = {
        "schema_version": "4.0",
        "fact_candidates": candidates,
        "source_reviews": [
            {
                "source_unit_id": "candidate_requirements:0001",
                "disposition": "evaluation",
                "candidate_ids": [item["candidate_id"] for item in candidates],
                "non_evaluation_reason": None,
                "warning_codes": [],
            }
        ],
    }
    fact_ids = [f"fact:{index:04d}" for index in range(1, 32)]
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(extraction),
            _result(_coverage_passed()),
            _result(_grouping(*fact_ids)),
        ]
    )

    content = _run(
        job_evaluation_plan_service.build_v4_plan_content(
            snapshot, adapter=adapter
        )
    )

    assert len(content.requirement_facts) == 31
    assert any(warning.code.value == "overly_broad_jd" for warning in content.warnings)


def test_v4_public_notes_never_enters_any_role_input() -> None:
    adapter = FakeJobEvaluationPlanAdapter(
        [
            _result(_fact_extraction()),
            _result(_coverage_passed()),
            _result(_grouping("fact:0001")),
        ]
    )

    _run(
        job_evaluation_plan_service.build_v4_plan_content(
            _snapshot(), adapter=adapter
        )
    )

    assert all(
        "public_notes" not in json.dumps(call["input"], ensure_ascii=False)
        for call in adapter.v4_calls
    )
