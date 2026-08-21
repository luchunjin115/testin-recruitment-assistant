from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import (
    AIExtractedEvaluationPlan,
    EvaluationItemCategory,
    JobEvaluationPlanInputSnapshot,
    JobEvaluationPlanRead,
    JobEvaluationPlanWarning,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanContentError,
    JobEvaluationPlanService,
)
from tests.fixtures.job_evaluation_plan_step9 import (
    EMPTY_REQUIREMENTS,
    EXPECTED_RED_CAPABILITIES,
    JD04,
    JD08,
    JD11,
    SOURCE_UNIT_CASES,
    make_snapshot_payload,
    non_requirement_review,
    requirement_review,
    review_item,
    v2_content,
)


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def snapshot(payload: dict[str, Any]) -> JobEvaluationPlanInputSnapshot:
    return JobEvaluationPlanInputSnapshot.model_validate(payload)


def build_v2(
    service: JobEvaluationPlanService,
    payload: dict[str, Any],
    *reviews: dict[str, Any],
):
    return service.build_plan_content(snapshot(payload), v2_content(*reviews))


def empty_v1_requirements(**overrides: Any) -> dict[str, Any]:
    values = dict(EMPTY_REQUIREMENTS)
    values.update(overrides)
    return values


def read_plan_payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "id": 1,
        "job_id": 901,
        "jd_fingerprint": FINGERPRINT,
        "status": "ready",
        "is_current": True,
        "items": [
            {
                "key": "requirement:skill:python",
                "title": "Python",
                "category": "skill",
                "priority": "required",
                "source_type": "structured",
                "source_field": "requirements.required_skills",
                "source_quote": None,
            }
        ],
        "structured_coverage": {
            "source_schema_version": "1.0",
            "fields": [
                {
                    "source_field": "requirements.required_skills",
                    "source_value_count": 1,
                    "item_keys": ["requirement:skill:python"],
                }
            ],
            "all_covered": True,
        },
        "warnings": [],
        "prompt_version": "job_evaluation_plan_v3",
        "model_version": "fictional-model",
        "schema_version": "1.0",
        "input_fingerprint": FINGERPRINT,
        "input_snapshot": make_snapshot_payload(
            "必须掌握 Python。",
            requirements=empty_v1_requirements(required_skills=["Python"]),
        ),
        "error_code": None,
        "error_message": None,
        "created_at": NOW,
        "completed_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


def unit_text(unit: Any) -> str:
    if isinstance(unit, dict):
        values = unit
    elif hasattr(unit, "model_dump"):
        values = unit.model_dump(mode="json")
    else:
        values = vars(unit)
    for key in ("text", "source_text", "source_quote"):
        if key in values:
            return values[key]
    raise AssertionError("9-B source unit 必须暴露可复核的连续原文")


def unit_id(unit: Any) -> str:
    if isinstance(unit, dict):
        return unit["source_id"]
    return unit.source_id


@pytest.mark.parametrize("case", SOURCE_UNIT_CASES, ids=lambda case: case.case_id)
def test_9b_description_source_units_are_deterministic_and_preserve_original_text(
    case,
) -> None:
    """Expected red -> 9-B source-unit deterministic segmentation."""
    service = JobEvaluationPlanService()
    builder = getattr(service, "build_description_source_units", None)
    assert callable(builder), EXPECTED_RED_CAPABILITIES["source_unit_segmentation"]

    first = builder(case.description)
    second = builder(case.description)

    assert first == second
    assert [unit_id(unit) for unit in first] == [
        f"description:{index:04d}" for index in range(1, len(first) + 1)
    ]
    assert tuple(unit_text(unit) for unit in first) == case.expected_texts


def test_9c_schema_2_0_accepts_legal_null_and_structured_key_shapes() -> None:
    """Expected red -> 9-C AI extraction Schema 2.0."""
    payload = json.loads(
        v2_content(
            requirement_review(
                "description:0001",
                review_item("Design LLM applications", "responsibility"),
                review_item(
                    "evaluation pipelines",
                    "responsibility",
                    "requirement:responsibility:structured",
                ),
            )
        )
    )

    parsed = AIExtractedEvaluationPlan.model_validate(payload)

    assert parsed.schema_version == "2.0"
    assert len(parsed.source_reviews) == 1


@pytest.mark.parametrize(
    "review",
    (
        {
            "source_id": "description:0001",
            "disposition": "requirements",
            "non_requirement_reason": None,
            "items": [],
        },
        {
            "source_id": "description:0001",
            "disposition": "requirements",
            "non_requirement_reason": "context",
            "items": [review_item("数据分析", "skill")],
        },
        {
            "source_id": "description:0001",
            "disposition": "non_requirement",
            "non_requirement_reason": "benefit",
            "items": [review_item("五险一金", "other")],
        },
        {
            "source_id": "description:0001",
            "disposition": "non_requirement",
            "non_requirement_reason": None,
            "items": [],
        },
    ),
    ids=(
        "requirement_without_items",
        "requirement_with_reason",
        "non_requirement_with_items",
        "non_requirement_without_reason",
    ),
)
def test_9c_schema_rejects_illegal_disposition_reason_item_combinations(
    review: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        AIExtractedEvaluationPlan.model_validate(
            {"schema_version": "2.0", "source_reviews": [review]}
        )


def test_9d_jd04_keeps_continuous_english_titles() -> None:
    """Expected red -> 9-D continuous source-title validation."""
    result = build_v2(
        JobEvaluationPlanService(),
        JD04,
        requirement_review(
            "description:0001",
            review_item("Design LLM applications", "responsibility"),
            review_item("evaluation pipelines", "responsibility"),
        ),
    )

    assert {item.title for item in result.items} == {
        "Design LLM applications",
        "evaluation pipelines",
    }
    assert all(item.source_field == "description" for item in result.items)


def test_9d_jd11_full_english_and_mixed_requirements_remain_traceable() -> None:
    """Expected red -> 9-D full-English and mixed source traceability."""
    result = build_v2(
        JobEvaluationPlanService(),
        JD11,
        requirement_review(
            "description:0001",
            review_item("Own onboarding", "responsibility"),
            review_item("renewal", "responsibility"),
        ),
        requirement_review(
            "description:0002",
            review_item("English 进行客户会议", "skill"),
        ),
        requirement_review(
            "description:0003",
            review_item("SaaS implementation experience", "experience"),
        ),
    )

    titles = {item.title for item in result.items}
    assert {
        "Own onboarding",
        "renewal",
        "English 进行客户会议",
        "SaaS implementation experience",
    } <= titles


@pytest.mark.parametrize(
    ("description", "title"),
    (
        ("Design LLM applications.", "设计 LLM 应用"),
        ("Design evaluation pipelines.", "Build evaluation workflows"),
        (
            "Design LLM applications. Evaluation pipelines.",
            "Design LLM applications Evaluation pipelines",
        ),
        ("Design LLM applications.", "design LLM applications"),
    ),
    ids=("translation", "synonym_rewrite", "cross_fragment_join", "case_change"),
)
def test_9d_rejects_translation_rewrite_join_and_internal_case_change(
    description: str,
    title: str,
) -> None:
    """Expected red -> 9-D exact continuous-original enforcement."""
    payload = make_snapshot_payload(description)
    reviews = [
        requirement_review(
            "description:0001",
            review_item(title, "responsibility"),
        )
    ]
    if description.count(".") > 1:
        reviews.append(
            requirement_review(
                "description:0002",
                review_item("Evaluation pipelines", "responsibility"),
            )
        )

    with pytest.raises(JobEvaluationPlanContentError) as raised:
        build_v2(JobEvaluationPlanService(), payload, *reviews)

    assert raised.value.code == "JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED"


def test_9d_preserves_technical_names_exactly() -> None:
    """Expected red -> 9-D exact spelling for abbreviations and technical names."""
    terms = ("LLM", "RAG", "SaaS", "C++", "C#", "Node.js", "A/B")
    payload = make_snapshot_payload(
        "需要 LLM、RAG、SaaS、C++、C#、Node.js 和 A/B 实验经验。"
    )
    result = build_v2(
        JobEvaluationPlanService(),
        payload,
        requirement_review(
            "description:0001",
            *(review_item(term, "skill") for term in terms),
        ),
    )

    assert terms == tuple(item.title for item in result.items)


def test_9d_allows_outer_list_whitespace_and_wrapping_punctuation_cleanup() -> None:
    """Expected red -> 9-B/9-D outer formatting cleanup without inner rewrite."""
    payload = make_snapshot_payload("  • （Design LLM applications）  ")
    result = build_v2(
        JobEvaluationPlanService(),
        payload,
        requirement_review(
            "description:0001",
            review_item("Design LLM applications", "responsibility"),
        ),
    )

    assert [item.title for item in result.items] == ["Design LLM applications"]


def test_9d_jd08_splits_acquisition_activation_and_retention_experiment() -> None:
    """Expected red -> 9-D JD08 minimum independently assessable units."""
    result = build_v2(
        JobEvaluationPlanService(),
        JD08,
        requirement_review(
            "description:0001",
            review_item("拉新", "responsibility"),
            review_item("激活", "responsibility"),
            review_item("留存实验", "responsibility"),
        ),
    )

    assert [item.title for item in result.items] == ["拉新", "激活", "留存实验"]


def test_9d_one_sentence_can_produce_multiple_independent_requirements() -> None:
    """Expected red -> 9-D multi-requirement recall within one source unit."""
    payload = make_snapshot_payload("设计实验、分析结果并复盘结论。")
    result = build_v2(
        JobEvaluationPlanService(),
        payload,
        requirement_review(
            "description:0001",
            review_item("设计实验", "responsibility"),
            review_item("分析结果", "responsibility"),
            review_item("复盘结论", "responsibility"),
        ),
    )

    assert {item.title for item in result.items} == {"设计实验", "分析结果", "复盘结论"}


def test_9d_structured_and_description_equivalent_requirement_is_kept_once() -> None:
    """Expected red -> 9-D controlled structured equivalence merge."""
    service = JobEvaluationPlanService()
    structured_key = service._item_key(EvaluationItemCategory.SKILL, "数据复盘")
    payload = make_snapshot_payload(
        "必须能独立设计活动并复盘数据。",
        requirements=empty_v1_requirements(required_skills=["数据复盘"]),
    )
    result = build_v2(
        service,
        payload,
        requirement_review(
            "description:0001",
            review_item("独立设计活动", "skill"),
            review_item("复盘数据", "skill", structured_key),
        ),
    )

    recap = [item for item in result.items if "复盘" in item.title]
    assert len(recap) == 1
    assert recap[0].title == "数据复盘"
    assert recap[0].source_type.value == "structured"


def test_9d_vague_free_text_does_not_upgrade_required() -> None:
    """Expected red -> 9-D priority must be recalculated from source text."""
    payload = make_snapshot_payload("参与数据分析。")
    result = build_v2(
        JobEvaluationPlanService(),
        payload,
        requirement_review(
            "description:0001",
            review_item("数据分析", "skill"),
        ),
    )

    assert result.items[0].priority.value == "general"


def test_9d_company_benefit_promotion_office_and_team_building_make_no_items() -> None:
    """Expected red -> 9-D non-requirement coverage plus no-items boundary."""
    payload = make_snapshot_payload(
        "公司介绍：我们成立十年。提供五险一金。"
        "办公环境舒适。每月组织团建。"
    )
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        build_v2(
            JobEvaluationPlanService(),
            payload,
            non_requirement_review("description:0001", "company_info"),
            non_requirement_review("description:0002", "benefit"),
            non_requirement_review("description:0003", "promotion"),
            non_requirement_review("description:0004", "promotion"),
        )

    assert raised.value.code == "JOB_EVALUATION_PLAN_NO_ITEMS"


@pytest.mark.parametrize("item_count", (1, 2, 3, 4))
def test_existing_boundary_one_to_four_items_is_ready_with_limited_basis(
    item_count: int,
) -> None:
    service = JobEvaluationPlanService()
    payload = make_snapshot_payload(
        None,
        requirements=empty_v1_requirements(
            responsibilities=[f"虚构职责 {index}" for index in range(item_count)]
        ),
    )
    result = service.build_plan_content(
        snapshot(payload),
        json.dumps({"schema_version": "1.0", "items": []}),
    )

    assert result.warnings == [JobEvaluationPlanWarning.LIMITED_BASIS]


def test_existing_boundary_zero_items_fails() -> None:
    service = JobEvaluationPlanService()
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        service.build_plan_content(
            snapshot(make_snapshot_payload(None)),
            json.dumps({"schema_version": "1.0", "items": []}),
        )
    assert raised.value.code == "JOB_EVALUATION_PLAN_NO_ITEMS"


def test_existing_boundary_over_thirty_fails_without_truncation() -> None:
    service = JobEvaluationPlanService()
    payload = make_snapshot_payload(
        None,
        requirements=empty_v1_requirements(
            required_skills=[f"虚构技能 {index:02d}" for index in range(31)]
        ),
    )
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        service.build_plan_content(
            snapshot(payload),
            json.dumps({"schema_version": "1.0", "items": []}),
        )
    assert raised.value.code == "JOB_EVALUATION_PLAN_TOO_MANY_ITEMS"


@pytest.mark.parametrize(
    "reviews",
    (
        (
            requirement_review(
                "description:0001",
                review_item("负责拉新", "responsibility"),
            ),
        ),
        (
            requirement_review(
                "description:0001",
                review_item("负责拉新", "responsibility"),
            ),
            requirement_review(
                "description:0001",
                review_item("负责拉新", "responsibility"),
            ),
        ),
        (
            requirement_review(
                "description:9999",
                review_item("负责拉新", "responsibility"),
            ),
            requirement_review(
                "description:0002",
                review_item("负责留存", "responsibility"),
            ),
        ),
    ),
    ids=("missing_source_id", "duplicate_source_id", "unknown_source_id"),
)
def test_9d_rejects_missing_duplicate_and_unknown_source_ids(reviews) -> None:
    """Expected red -> 9-D request/response source-ID completeness check."""
    payload = make_snapshot_payload("负责拉新。负责留存。")
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        build_v2(JobEvaluationPlanService(), payload, *reviews)

    assert raised.value.code == "JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED"


def test_9d_equivalent_structured_key_null_is_a_legal_new_item() -> None:
    """Expected red -> 9-D null structured-equivalence path."""
    result = build_v2(
        JobEvaluationPlanService(),
        make_snapshot_payload("复盘运营数据。"),
        requirement_review(
            "description:0001",
            review_item("复盘运营数据", "skill", None),
        ),
    )
    assert [item.title for item in result.items] == ["复盘运营数据"]


@pytest.mark.parametrize("kind", ("unknown", "cross_category"))
def test_9d_rejects_unknown_and_cross_category_structured_keys(kind: str) -> None:
    """Expected red -> 9-D controlled structured-equivalence references."""
    service = JobEvaluationPlanService()
    responsibility_key = service._item_key(
        EvaluationItemCategory.RESPONSIBILITY,
        "数据复盘",
    )
    equivalent_key = (
        "requirement:skill:forged"
        if kind == "unknown"
        else responsibility_key
    )
    payload = make_snapshot_payload(
        "复盘数据。",
        requirements=empty_v1_requirements(responsibilities=["数据复盘"]),
    )
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        build_v2(
            service,
            payload,
            requirement_review(
                "description:0001",
                review_item("复盘数据", "skill", equivalent_key),
            ),
        )

    assert raised.value.code == "JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED"


def test_9d_equivalence_cannot_upgrade_structured_priority() -> None:
    """Expected red -> 9-D equivalence keeps structured priority."""
    service = JobEvaluationPlanService()
    structured_key = service._item_key(EvaluationItemCategory.SKILL, "数据复盘")
    payload = make_snapshot_payload(
        "复盘数据。",
        requirements=empty_v1_requirements(preferred_skills=["数据复盘"]),
    )
    result = build_v2(
        service,
        payload,
        requirement_review(
            "description:0001",
            review_item("复盘数据", "skill", structured_key),
        ),
    )

    assert len(result.items) == 1
    assert result.items[0].priority.value == "preferred"


def test_9e_old_schema_1_plan_remains_readable_without_free_text_coverage() -> None:
    plan = JobEvaluationPlanRead.model_validate(read_plan_payload())
    assert plan.schema_version == "1.0"
    assert "free_text_coverage" not in plan.model_fields_set


def test_9e_schema_2_ready_plan_has_complete_internal_free_text_coverage() -> None:
    """Expected red -> 9-D content audit and 9-E persistence contract."""
    result = build_v2(
        JobEvaluationPlanService(),
        make_snapshot_payload("负责用户调研。"),
        requirement_review(
            "description:0001",
            review_item("用户调研", "responsibility"),
        ),
    )

    coverage = result.free_text_coverage
    assert coverage["rule_version"] == "jd_source_units_v1"
    assert coverage["all_reviewed"] is True
    assert [unit["source_id"] for unit in coverage["units"]] == [
        "description:0001"
    ]


def test_9e_model_adds_nullable_internal_coverage_column_and_reads_schema_2() -> None:
    """Expected red -> 9-E Model/Schema version coexistence."""
    table = JobEvaluationPlan.__table__
    assert "free_text_coverage" in table.c
    assert table.c.free_text_coverage.nullable is True

    plan = JobEvaluationPlanRead.model_validate(
        read_plan_payload(schema_version="2.0")
    )
    assert plan.schema_version == "2.0"
    assert "free_text_coverage" not in plan.model_dump(mode="json")


def contract_fingerprint(
    service: JobEvaluationPlanService,
    payload: JobEvaluationPlanInputSnapshot,
    contract: dict[str, str],
) -> str:
    builder = getattr(service, "fingerprint_input", None)
    assert callable(builder), EXPECTED_RED_CAPABILITIES["persistence_and_fingerprint"]
    return builder(payload, contract)


def test_9e_same_jd_and_same_contract_has_stable_input_fingerprint() -> None:
    """Expected red -> 9-E contract-aware fingerprint helper."""
    service = JobEvaluationPlanService()
    source = snapshot(JD04)
    contract = {
        "breaking_contract_version": "jd_extraction_v2",
        "ai_schema_version": "2.0",
        "plan_schema_version": "2.0",
        "source_unit_rule_version": "jd_source_units_v1",
        "prompt_version": "job_evaluation_plan_v4",
    }
    assert contract_fingerprint(service, source, contract) == contract_fingerprint(
        service,
        source,
        dict(contract),
    )


def test_9e_breaking_contract_change_creates_new_input_fingerprint() -> None:
    """Expected red -> 9-E destructive contract version changes fingerprint."""
    service = JobEvaluationPlanService()
    source = snapshot(JD04)
    v2 = {
        "breaking_contract_version": "jd_extraction_v2",
        "ai_schema_version": "2.0",
        "plan_schema_version": "2.0",
        "source_unit_rule_version": "jd_source_units_v1",
        "prompt_version": "job_evaluation_plan_v4",
    }
    v3 = dict(v2, breaking_contract_version="jd_extraction_v3")

    assert contract_fingerprint(service, source, v2) != contract_fingerprint(
        service,
        source,
        v3,
    )


def test_9e_non_breaking_prompt_wording_does_not_change_input_fingerprint() -> None:
    """Expected red -> 9-E prompt wording is not a destructive contract input."""
    service = JobEvaluationPlanService()
    source = snapshot(JD04)
    first = {
        "breaking_contract_version": "jd_extraction_v2",
        "ai_schema_version": "2.0",
        "plan_schema_version": "2.0",
        "source_unit_rule_version": "jd_source_units_v1",
        "prompt_version": "job_evaluation_plan_v4",
    }
    wording_only = dict(first, prompt_version="job_evaluation_plan_v4_wording_2")

    assert contract_fingerprint(service, source, first) == contract_fingerprint(
        service,
        source,
        wording_only,
    )


def test_9f_old_contract_read_shape_exposes_contract_outdated() -> None:
    """Expected red -> 9-F explicit legacy-plan upgrade read contract."""
    plan = JobEvaluationPlanRead.model_validate(
        read_plan_payload(contract_outdated=True)
    )
    assert plan.contract_outdated is True


def test_expected_red_capability_map_names_only_confirmed_future_batches() -> None:
    assert set(value.split(" ", 1)[0] for value in EXPECTED_RED_CAPABILITIES.values()) == {
        "9-B",
        "9-C",
        "9-D",
        "9-E",
        "9-F",
    }
