from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import job_evaluation_plan as schema
from tests.fixtures.job_evaluation_plan_v4 import (
    make_evaluation_criterion,
    make_requirement_fact,
    make_source,
    make_v4_plan,
)
from tests.fixtures.job_evaluation_plan_v3 import make_plan_read as make_v3_plan


def _contract_type(name: str):
    assert hasattr(schema, name), f"7R4-B 缺少 4.0 Schema：{name}"
    return getattr(schema, name)


def _validate_v4_plan(payload: dict):
    try:
        return schema.JobEvaluationPlanRead.model_validate(payload)
    except ValidationError as exc:
        pytest.fail(f"7R4-B 尚不能解析 4.0 计划：{exc}")


@pytest.mark.parametrize(
    ("constant_name", "expected"),
    [
        ("JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION", "4.0"),
        (
            "JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION",
            "job_evaluation_input_v4",
        ),
        (
            "JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION",
            "fact_criterion_plan_generation_v1",
        ),
    ],
)
def test_v4_breaking_contract_versions_are_explicit(
    constant_name: str,
    expected: str,
) -> None:
    assert getattr(schema, constant_name) == expected


def test_v4_status_adds_pending_confirmation() -> None:
    values = {item.value for item in schema.JobEvaluationPlanStatus}
    assert "pending_confirmation" in values


def test_requirement_fact_has_no_ai_generated_title_or_statement() -> None:
    fact_type = _contract_type("RequirementFact")
    parsed = fact_type.model_validate(make_requirement_fact())
    fields = set(parsed.model_dump(mode="json"))
    assert fields == {"fact_id", "category", "priority", "sources"}
    assert {"title", "statement", "text"}.isdisjoint(fields)


def test_requirement_fact_category_is_exactly_five_controlled_values() -> None:
    category_type = _contract_type("RequirementFactCategory")
    assert {item.value for item in category_type} == {
        "skill",
        "experience",
        "responsibility",
        "education",
        "other",
    }


def test_requirement_fact_keeps_multiple_continuous_sources() -> None:
    fact_type = _contract_type("RequirementFact")
    parsed = fact_type.model_validate(
        make_requirement_fact(
            sources=[
                make_source(),
                make_source(
                    source_field="preferred_qualifications",
                    source_unit_id="preferred_qualifications:0001",
                    source_quote="有 Python 服务端项目经验者优先",
                ),
            ]
        )
    )
    assert len(parsed.sources) == 2


def test_requirement_fact_rejects_empty_sources() -> None:
    fact_type = _contract_type("RequirementFact")
    with pytest.raises(ValidationError):
        fact_type.model_validate(make_requirement_fact(sources=[]))


def test_evaluation_criterion_only_groups_fact_ids() -> None:
    criterion_type = _contract_type("EvaluationCriterion")
    parsed = criterion_type.model_validate(make_evaluation_criterion())
    fields = set(parsed.model_dump(mode="json"))
    assert fields == {"criterion_id", "name", "fact_ids"}
    assert {"weight", "score", "threshold", "priority"}.isdisjoint(fields)


def test_v4_plan_requires_facts_criteria_reviews_and_audit() -> None:
    parsed = _validate_v4_plan(make_v4_plan())
    payload = parsed.model_dump(mode="json")
    for field in (
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
    ):
        assert payload[field]
    assert payload["items"] == []


def test_v4_snapshot_and_plan_forbid_public_notes() -> None:
    _validate_v4_plan(make_v4_plan())
    invalid = make_v4_plan()
    invalid["input_snapshot"]["job_context"]["public_notes"] = "必须熟悉 Go"
    invalid["public_notes"] = "必须熟悉 Go"
    with pytest.raises(ValidationError):
        schema.JobEvaluationPlanRead.model_validate(invalid)


def test_v4_plan_rejects_fact_assigned_to_zero_or_multiple_criteria() -> None:
    _validate_v4_plan(make_v4_plan())
    for criteria in (
        [],
        [
            make_evaluation_criterion(criterion_id="criterion:0001"),
            make_evaluation_criterion(criterion_id="criterion:0002"),
        ],
    ):
        with pytest.raises(ValidationError):
            schema.JobEvaluationPlanRead.model_validate(
                make_v4_plan(evaluation_criteria=criteria)
            )


def test_v4_warning_codes_include_all_five_controlled_cases() -> None:
    warning_type = _contract_type("JobEvaluationPlanV4WarningCode")
    assert {item.value for item in warning_type} == {
        "limited_basis",
        "overly_broad_jd",
        "conflicting_requirements",
        "ambiguous_requirement",
        "non_evaluation_content",
    }


def test_legacy_versions_remain_declared_for_read_only_history() -> None:
    annotation = schema.JobEvaluationPlanRead.model_fields["schema_version"].annotation
    assert set(annotation.__args__) >= {"1.0", "2.0", "3.0", "4.0"}


def test_v4_accepts_thirty_one_facts_without_legacy_item_limit() -> None:
    assert schema.JOB_EVALUATION_PLAN_V4_MAX_SOURCE_UNITS == 512
    assert schema.JOB_EVALUATION_PLAN_V4_MAX_FACTS == 512
    assert schema.JOB_EVALUATION_PLAN_V4_MAX_CRITERIA == 512
    fact_ids = [f"fact:{index:04d}" for index in range(1, 32)]
    facts = [make_requirement_fact(fact_id=fact_id) for fact_id in fact_ids]
    source_review = make_v4_plan()["source_review_summary"]
    source_review["units"][0]["fact_ids"] = fact_ids

    parsed = _validate_v4_plan(
        make_v4_plan(
            requirement_facts=facts,
            evaluation_criteria=[make_evaluation_criterion(fact_ids=fact_ids)],
            source_review_summary=source_review,
        )
    )

    assert len(parsed.requirement_facts or []) == 31


@pytest.mark.parametrize(
    "fact",
    [
        make_requirement_fact(priority="preferred"),
        make_requirement_fact(
            sources=[make_source(source_quote="原文中不存在的改写事实")]
        ),
    ],
)
def test_v4_rejects_priority_or_quote_not_derived_from_source(fact: dict) -> None:
    with pytest.raises(ValidationError):
        schema.JobEvaluationPlanRead.model_validate(
            make_v4_plan(requirement_facts=[fact])
        )


def test_v4_fact_source_accepts_full_ten_thousand_character_source_unit() -> None:
    source_text = "技" * 10_000
    payload = make_v4_plan(
        requirement_facts=[
            make_requirement_fact(
                sources=[make_source(source_quote=source_text)]
            )
        ]
    )
    payload["input_snapshot"]["evaluation_fields"][
        "candidate_requirements"
    ] = source_text
    payload["input_snapshot"]["source_units"][0]["source_text"] = source_text

    parsed = _validate_v4_plan(payload)

    assert len(parsed.requirement_facts[0].sources[0].source_quote) == 10_000


def test_v4_failed_plan_forbids_partial_payload() -> None:
    failed = make_v4_plan(
        status="failed",
        error_code="JOB_EVALUATION_PLAN_FAILED",
        error_message="评价计划生成失败",
    )
    with pytest.raises(ValidationError):
        schema.JobEvaluationPlanRead.model_validate(failed)

    for field in (
        "requirement_facts",
        "evaluation_criteria",
        "source_review_summary",
        "coverage_review_summary",
        "generation_audit",
    ):
        failed[field] = None
    parsed = schema.JobEvaluationPlanRead.model_validate(failed)
    assert parsed.status is schema.JobEvaluationPlanStatus.FAILED


def test_v3_history_does_not_serialize_null_v4_payload() -> None:
    payload = schema.JobEvaluationPlanRead.model_validate(
        make_v3_plan()
    ).model_dump(mode="json")
    assert {
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
    }.isdisjoint(payload)
