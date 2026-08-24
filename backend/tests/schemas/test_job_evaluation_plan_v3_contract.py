from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import job_evaluation_plan as schema
from app.schemas.job_evaluation_plan import (
    AIExtractedEvaluationPlan,
    JobEvaluationItem,
    JobEvaluationPlanInputSnapshot,
    JobEvaluationPlanRead,
)
from tests.fixtures.job_evaluation_plan_v3 import (
    make_ai_review,
    make_ai_v3_response,
    make_evaluation_item,
    make_input_snapshot,
    make_plan_read,
    make_source_review_summary,
    make_warning,
)


@pytest.mark.parametrize(
    ("constant_name", "expected"),
    [
        ("JOB_EVALUATION_PLAN_SCHEMA_VERSION", "3.0"),
        ("JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION", "3.0"),
        ("JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION", "five_section_source_units_v1"),
        ("JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION", "five_section_plan_generation_v1"),
    ],
)
def test_v3_breaking_contract_versions_are_explicit(
    constant_name: str,
    expected: str,
) -> None:
    assert getattr(schema, constant_name) == expected


def test_v3_input_snapshot_accepts_only_context_evaluation_fields_and_units() -> None:
    parsed = JobEvaluationPlanInputSnapshot.model_validate(make_input_snapshot())
    payload = parsed.model_dump(mode="json")

    assert payload["schema_version"] == "3.0"
    assert set(payload["job_context"]) == {"title", "department", "job_background"}
    assert set(payload["evaluation_fields"]) == {
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
    }
    assert set(payload["source_units"][0]) == {
        "source_unit_id",
        "source_field",
        "ordinal",
        "source_text",
    }
    forbidden = {"public_notes", "location", "employment_type", "headcount"}
    assert forbidden.isdisjoint(str(payload))


@pytest.mark.parametrize(
    "source_field",
    ["job_responsibilities", "candidate_requirements", "preferred_qualifications"],
)
def test_v3_source_units_accept_exactly_three_evaluation_fields(
    source_field: str,
) -> None:
    payload = make_input_snapshot()
    payload["source_units"][0].update(
        {
            "source_unit_id": f"{source_field}:0001",
            "source_field": source_field,
        }
    )
    parsed = JobEvaluationPlanInputSnapshot.model_validate(payload)
    assert parsed.source_units[0].source_field == source_field


def test_v3_input_snapshot_rejects_public_notes_even_when_nested() -> None:
    JobEvaluationPlanInputSnapshot.model_validate(make_input_snapshot())
    payload = make_input_snapshot()
    payload["job_context"]["public_notes"] = "必须熟悉 Go"
    with pytest.raises(ValidationError):
        JobEvaluationPlanInputSnapshot.model_validate(payload)


def test_v3_item_uses_multi_source_trace_without_legacy_source_type() -> None:
    item = make_evaluation_item(
        sources=[
            {
                "source_field": "candidate_requirements",
                "source_unit_id": "candidate_requirements:0001",
                "source_quote": "具备 Python 后端开发经验",
            },
            {
                "source_field": "preferred_qualifications",
                "source_unit_id": "preferred_qualifications:0001",
                "source_quote": "Python 服务经验优先",
            },
        ]
    )
    parsed = JobEvaluationItem.model_validate(item)
    dumped = parsed.model_dump(mode="json")

    assert len(dumped["sources"]) == 2
    assert "source_type" not in dumped
    assert "source_field" not in dumped
    assert "source_quote" not in dumped


@pytest.mark.parametrize(
    "warning_code",
    ["limited_basis", "priority_signal_conflict", "misplaced_non_evaluation_content"],
)
def test_v3_plan_accepts_controlled_warning_objects(warning_code: str) -> None:
    parsed = JobEvaluationPlanRead.model_validate(
        make_plan_read(warnings=[make_warning(warning_code)])
    )
    assert parsed.warnings[0].code == warning_code


def test_v3_ready_plan_requires_complete_source_review_summary() -> None:
    JobEvaluationPlanRead.model_validate(make_plan_read())
    invalid = make_plan_read(
        source_review_summary=make_source_review_summary(
            reviewed_units=0,
            all_reviewed=False,
        )
    )
    with pytest.raises(ValidationError):
        JobEvaluationPlanRead.model_validate(invalid)


def test_v3_ready_plan_does_not_require_legacy_coverage_contracts() -> None:
    parsed = JobEvaluationPlanRead.model_validate(make_plan_read())
    payload = parsed.model_dump(mode="json")
    assert "structured_coverage" not in payload
    assert "free_text_coverage" not in payload
    assert payload["source_review_summary"]["all_reviewed"] is True


def test_v3_ai_output_accepts_each_source_unit_reviewed_once() -> None:
    parsed = AIExtractedEvaluationPlan.model_validate(
        make_ai_v3_response([make_ai_review()])
    )
    assert parsed.schema_version == "3.0"
    assert parsed.source_reviews[0].source_unit_id == "candidate_requirements:0001"


def test_v3_ai_output_rejects_model_owned_priority() -> None:
    AIExtractedEvaluationPlan.model_validate(
        make_ai_v3_response([make_ai_review()])
    )
    review = make_ai_review()
    review["items"][0]["priority"] = "preferred"
    with pytest.raises(ValidationError):
        AIExtractedEvaluationPlan.model_validate(make_ai_v3_response([review]))


@pytest.mark.parametrize("item_count", [0, 31])
def test_ready_plan_rejects_zero_or_more_than_thirty_items(item_count: int) -> None:
    JobEvaluationPlanRead.model_validate(make_plan_read())
    items = [
        make_evaluation_item(key=f"item:{index:04d}")
        for index in range(1, item_count + 1)
    ]
    with pytest.raises(ValidationError):
        JobEvaluationPlanRead.model_validate(make_plan_read(items=items))


@pytest.mark.parametrize("schema_version", ["1.0", "2.0"])
def test_read_schema_declares_legacy_versions_for_history(
    schema_version: str,
) -> None:
    assert schema_version in JobEvaluationPlanRead.model_fields["schema_version"].annotation.__args__
