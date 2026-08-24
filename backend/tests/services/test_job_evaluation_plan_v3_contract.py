from __future__ import annotations

import json
from typing import Any

import pytest

from app.prompts.job_evaluation_plan import JOB_EVALUATION_PLAN_PROMPT_VERSION
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanContentError,
    job_evaluation_plan_service,
)
from tests.fixtures.job_evaluation_plan_v3 import (
    make_ai_review,
    make_ai_v3_response,
    make_five_section_job,
)


def _snapshot(job: Any):
    try:
        return job_evaluation_plan_service.build_input_snapshot(job)
    except Exception as exc:  # the assertion records a missing production capability
        pytest.fail(f"7R-C 尚不能构建五段式 input snapshot：{type(exc).__name__}: {exc}")


def _content(snapshot: Any, response: dict[str, Any]):
    try:
        return job_evaluation_plan_service.build_plan_content(
            snapshot,
            json.dumps(response, ensure_ascii=False),
        )
    except Exception as exc:  # keep expected red lights as assertion failures, not fixture errors
        pytest.fail(f"7R-C 尚不能组装 3.0 计划：{type(exc).__name__}: {exc}")


def _units(snapshot: Any) -> list[Any]:
    units = getattr(snapshot, "source_units", None)
    assert units is not None, "3.0 input snapshot 必须直接保存 source_units"
    return list(units)


def _unit_value(unit: Any, name: str) -> Any:
    return getattr(unit, name, unit[name] if isinstance(unit, dict) else None)


def _warnings(content: Any) -> list[dict[str, Any]]:
    return [
        warning.model_dump(mode="json") if hasattr(warning, "model_dump") else warning
        for warning in content.warnings
    ]


def test_v3_uses_prompt_v5() -> None:
    assert JOB_EVALUATION_PLAN_PROMPT_VERSION == "job_evaluation_plan_v5"


def test_snapshot_contains_context_and_three_evaluation_fields_only() -> None:
    payload = _snapshot(make_five_section_job()).model_dump(mode="json")
    assert payload["job_context"] == {
        "title": "AI 应用工程师",
        "department": "技术研发部",
        "job_background": "建设面向企业客户的 AI 应用平台。",
    }
    assert set(payload["evaluation_fields"]) == {
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
    }
    assert all(
        field not in str(payload)
        for field in ("public_notes", "location", "employment_type", "headcount")
    )


def test_source_units_cover_all_three_fields_with_stable_ids_and_ordinals() -> None:
    first = _units(_snapshot(make_five_section_job()))
    second = _units(_snapshot(make_five_section_job()))
    assert [unit.model_dump(mode="json") for unit in first] == [
        unit.model_dump(mode="json") for unit in second
    ]
    assert {_unit_value(unit, "source_field") for unit in first} == {
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
    }
    for field in {"job_responsibilities", "candidate_requirements", "preferred_qualifications"}:
        field_units = [unit for unit in first if _unit_value(unit, "source_field") == field]
        assert [_unit_value(unit, "ordinal") for unit in field_units] == list(
            range(1, len(field_units) + 1)
        )
        assert all(
            _unit_value(unit, "source_unit_id") == f"{field}:{index:04d}"
            for index, unit in enumerate(field_units, start=1)
        )


def test_source_units_preserve_paragraph_bullets_and_indented_continuation() -> None:
    job = make_five_section_job(
        job_responsibilities=(
            "第一自然段说明。\n\n"
            "1. 负责服务设计\n"
            "   包括监控、告警和故障复盘\n"
            "• 推动跨部门项目交付"
        ),
        candidate_requirements="具备 Python 开发经验",
        preferred_qualifications=None,
    )
    texts = [_unit_value(unit, "source_text") for unit in _units(_snapshot(job))]
    assert "第一自然段说明。" in texts
    assert "1. 负责服务设计\n   包括监控、告警和故障复盘" in texts
    assert "• 推动跨部门项目交付" in texts


def test_source_units_normalize_crlf_and_lf_to_same_contract() -> None:
    lf = _snapshot(
        make_five_section_job(candidate_requirements="- Python\n  FastAPI 项目\n- PostgreSQL")
    )
    crlf = _snapshot(
        make_five_section_job(candidate_requirements="- Python\r\n  FastAPI 项目\r\n- PostgreSQL")
    )
    assert lf.model_dump(mode="json") == crlf.model_dump(mode="json")


def test_source_units_do_not_split_commas_conjunctions_or_and() -> None:
    snapshot = _snapshot(
        make_five_section_job(
            job_responsibilities="使用 Python、PostgreSQL 和 Redis 交付 API and worker 服务",
            candidate_requirements=None,
            preferred_qualifications=None,
        )
    )
    units = _units(snapshot)
    assert len(units) == 1
    assert _unit_value(units[0], "source_text") == (
        "使用 Python、PostgreSQL 和 Redis 交付 API and worker 服务"
    )


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "department",
        "job_background",
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
    ],
)
def test_jd_fingerprint_changes_for_each_prompt_field(field: str) -> None:
    baseline = make_five_section_job()
    changed = make_five_section_job(**{field: f"{getattr(baseline, field)}（变化）"})
    assert job_evaluation_plan_service.fingerprint_snapshot(_snapshot(baseline)) != (
        job_evaluation_plan_service.fingerprint_snapshot(_snapshot(changed))
    )


@pytest.mark.parametrize(
    "field",
    ["public_notes", "location", "employment_type", "headcount"],
)
def test_jd_fingerprint_excludes_non_prompt_fields(field: str) -> None:
    baseline = make_five_section_job()
    replacement: Any = 9 if field == "headcount" else f"changed-{field}"
    changed = make_five_section_job(**{field: replacement})
    assert job_evaluation_plan_service.fingerprint_snapshot(_snapshot(baseline)) == (
        job_evaluation_plan_service.fingerprint_snapshot(_snapshot(changed))
    )


@pytest.mark.parametrize(
    "variant",
    [
        "  - Python  \n- PostgreSQL   ",
        "- Python\r\n- PostgreSQL",
        "- Python\r- PostgreSQL",
    ],
)
def test_jd_fingerprint_normalizes_outer_line_end_and_newline_encoding(
    variant: str,
) -> None:
    baseline = make_five_section_job(candidate_requirements="- Python\n- PostgreSQL")
    changed = make_five_section_job(candidate_requirements=variant)
    assert job_evaluation_plan_service.fingerprint_snapshot(_snapshot(baseline)) == (
        job_evaluation_plan_service.fingerprint_snapshot(_snapshot(changed))
    )


@pytest.mark.parametrize(
    "variant",
    [
        "- Python - PostgreSQL",
        "- Python\n\n- PostgreSQL",
        "• Python\n- PostgreSQL",
        "- python\n- PostgreSQL",
        "- Python\n- PostgreSQL。",
    ],
)
def test_jd_fingerprint_preserves_meaningful_layout_and_text_changes(
    variant: str,
) -> None:
    baseline = make_five_section_job(candidate_requirements="- Python\n- PostgreSQL")
    changed = make_five_section_job(candidate_requirements=variant)
    assert job_evaluation_plan_service.fingerprint_snapshot(_snapshot(baseline)) != (
        job_evaluation_plan_service.fingerprint_snapshot(_snapshot(changed))
    )


def test_input_fingerprint_versions_job_evaluation_input_v3_rule() -> None:
    snapshot = _snapshot(make_five_section_job())
    base_contract = {
        "breaking_contract_version": "five_section_plan_generation_v1",
        "ai_schema_version": "3.0",
        "plan_schema_version": "3.0",
        "source_unit_rule_version": "five_section_source_units_v1",
        "fingerprint_rule_version": "job_evaluation_input_v3",
    }
    changed_contract = {
        **base_contract,
        "fingerprint_rule_version": "future_breaking_fingerprint_rule",
    }
    assert job_evaluation_plan_service.fingerprint_input(
        snapshot,
        base_contract,
    ) != job_evaluation_plan_service.fingerprint_input(snapshot, changed_contract)


def test_exact_duplicate_items_merge_all_sources_and_highest_priority() -> None:
    snapshot = _snapshot(
        make_five_section_job(
            job_responsibilities="使用 Python 构建后端服务",
            candidate_requirements="具备 Python 后端服务经验",
            preferred_qualifications=None,
        )
    )
    units = _units(snapshot)
    reviews = [
        make_ai_review(
            source_unit_id=_unit_value(unit, "source_unit_id"),
            items=[
                {
                    "title": "Python 后端服务能力",
                    "category": "skill",
                    "source_quote": _unit_value(unit, "source_text"),
                }
            ],
        )
        for unit in units
    ]
    content = _content(snapshot, make_ai_v3_response(reviews))
    assert len(content.items) == 1
    assert content.items[0].priority.value == "required"
    assert len(content.items[0].sources) == 2
    assert {source.source_field for source in content.items[0].sources} == {
        "job_responsibilities",
        "candidate_requirements",
    }


@pytest.mark.parametrize("review_problem", ["missing", "duplicate", "unknown"])
def test_every_source_unit_must_be_reviewed_exactly_once(review_problem: str) -> None:
    snapshot = _snapshot(
        make_five_section_job(
            job_responsibilities="负责服务开发",
            candidate_requirements="具备 Python 经验",
            preferred_qualifications=None,
        )
    )
    units = _units(snapshot)
    reviews = [
        make_ai_review(
            source_unit_id=_unit_value(unit, "source_unit_id"),
            items=[
                {
                    "title": _unit_value(unit, "source_text"),
                    "category": "responsibility",
                    "source_quote": _unit_value(unit, "source_text"),
                }
            ],
        )
        for unit in units
    ]
    if review_problem == "missing":
        reviews.pop()
    elif review_problem == "duplicate":
        reviews.append(dict(reviews[0]))
    else:
        reviews[0]["source_unit_id"] = "candidate_requirements:9999"

    with pytest.raises(JobEvaluationPlanContentError):
        job_evaluation_plan_service.build_plan_content(
            snapshot,
            json.dumps(make_ai_v3_response(reviews), ensure_ascii=False),
        )


def test_source_quote_must_be_continuous_unmodified_original_text() -> None:
    snapshot = _snapshot(
        make_five_section_job(
            job_responsibilities=None,
            candidate_requirements="具备 Python 后端开发经验",
            preferred_qualifications=None,
        )
    )
    review = make_ai_review(
        items=[
            {
                "title": "Python 后端开发经验",
                "category": "experience",
                "source_quote": "具备高级 Python 后端开发经验",
            }
        ]
    )
    with pytest.raises(JobEvaluationPlanContentError):
        job_evaluation_plan_service.build_plan_content(
            snapshot,
            json.dumps(make_ai_v3_response([review]), ensure_ascii=False),
        )


def test_controlled_title_summary_cannot_add_skill_year_or_mandatory_force() -> None:
    snapshot = _snapshot(
        make_five_section_job(
            job_responsibilities=None,
            candidate_requirements="具备 Python 后端开发经验",
            preferred_qualifications=None,
        )
    )
    review = make_ai_review(
        items=[
            {
                "title": "必须具备五年以上 Python 与 Go 后端开发经验",
                "category": "experience",
                "source_quote": "具备 Python 后端开发经验",
            }
        ]
    )
    with pytest.raises(JobEvaluationPlanContentError):
        job_evaluation_plan_service.build_plan_content(
            snapshot,
            json.dumps(make_ai_v3_response([review]), ensure_ascii=False),
        )


@pytest.mark.parametrize(
    ("job_field", "text", "disposition", "reason", "warning_code"),
    [
        (
            "candidate_requirements",
            "RAG 经验优先",
            "evaluation",
            None,
            "priority_signal_conflict",
        ),
        (
            "candidate_requirements",
            "我们提供五险一金和下午茶",
            "non_evaluation",
            "benefit",
            "misplaced_non_evaluation_content",
        ),
    ],
)
def test_v3_emits_controlled_semantic_warnings(
    job_field: str,
    text: str,
    disposition: str,
    reason: str | None,
    warning_code: str,
) -> None:
    values = {
        "job_responsibilities": None,
        "candidate_requirements": None,
        "preferred_qualifications": None,
        job_field: text,
    }
    if disposition == "non_evaluation":
        values["job_responsibilities"] = "负责服务开发"
    snapshot = _snapshot(make_five_section_job(**values))
    reviews = []
    for unit in _units(snapshot):
        if _unit_value(unit, "source_field") == job_field:
            reviews.append(
                make_ai_review(
                    source_unit_id=_unit_value(unit, "source_unit_id"),
                    disposition=disposition,
                    non_evaluation_reason=reason,
                    items=(
                        [{
                            "title": "RAG 经验",
                            "category": "experience",
                            "source_quote": "RAG 经验",
                        }]
                        if disposition == "evaluation"
                        else []
                    ),
                )
            )
        else:
            reviews.append(
                make_ai_review(
                    source_unit_id=_unit_value(unit, "source_unit_id"),
                    items=[{
                        "title": "服务开发",
                        "category": "responsibility",
                        "source_quote": "服务开发",
                    }],
                )
            )
    content = _content(snapshot, make_ai_v3_response(reviews))
    assert warning_code in {warning["code"] for warning in _warnings(content)}


@pytest.mark.parametrize(
    ("item_count", "expected_status"),
    [(0, "no_items"), (1, "limited"), (4, "limited"), (5, "ready"), (30, "ready"), (31, "too_many_items")],
)
def test_v3_item_count_boundaries_are_never_truncated_or_force_merged(
    item_count: int,
    expected_status: str,
) -> None:
    if item_count == 0:
        job = make_five_section_job(
            job_responsibilities=None,
            candidate_requirements="我们提供五险一金",
            preferred_qualifications=None,
        )
    else:
        job = make_five_section_job(
            job_responsibilities=None,
            candidate_requirements="\n".join(
                f"- 独立评价要求 {index:02d}" for index in range(1, item_count + 1)
            ),
            preferred_qualifications=None,
        )
    snapshot = _snapshot(job)
    units = _units(snapshot)
    reviews = []
    for index, unit in enumerate(units, start=1):
        if item_count == 0:
            reviews.append(
                make_ai_review(
                    source_unit_id=_unit_value(unit, "source_unit_id"),
                    disposition="non_evaluation",
                    non_evaluation_reason="benefit",
                    items=[],
                )
            )
        else:
            quote = f"独立评价要求 {index:02d}"
            reviews.append(
                make_ai_review(
                    source_unit_id=_unit_value(unit, "source_unit_id"),
                    items=[
                        {
                            "title": quote,
                            "category": "other",
                            "source_quote": quote,
                        }
                    ],
                )
            )
    response = json.dumps(make_ai_v3_response(reviews), ensure_ascii=False)
    if expected_status in {"no_items", "too_many_items"}:
        expected_code = (
            "JOB_EVALUATION_PLAN_NO_ITEMS"
            if expected_status == "no_items"
            else "JOB_EVALUATION_PLAN_TOO_MANY_ITEMS"
        )
        with pytest.raises(JobEvaluationPlanContentError) as caught:
            job_evaluation_plan_service.build_plan_content(snapshot, response)
        assert caught.value.code == expected_code
        return

    content = _content(snapshot, make_ai_v3_response(reviews))
    assert len(content.items) == item_count
    warning_codes = {warning["code"] for warning in _warnings(content)}
    assert ("limited_basis" in warning_codes) is (expected_status == "limited")
