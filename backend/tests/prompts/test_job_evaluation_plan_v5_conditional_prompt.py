from __future__ import annotations

import json

from app.prompts.job_evaluation_plan import (
    JOB_EVALUATION_PLAN_V5_FEW_SHOT_EXAMPLES,
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
    build_job_evaluation_plan_v5_messages,
)


def _snapshot() -> dict:
    return {
        "schema_version": "5.0",
        "job_context": {
            "title": "虚构岗位",
            "department": "虚构部门",
            "job_background": "仅用于离线 Prompt 合同测试。",
        },
        "evaluation_fields": {
            "job_responsibilities": "负责常规资料归档。",
            "candidate_requirements": "若参与夜间盘点，需能使用手持终端。",
            "preferred_qualifications": "有展陈排期经验者优先。",
        },
        "source_units": [
            {
                "source_unit_id": "job_responsibilities:0001",
                "source_field": "job_responsibilities",
                "ordinal": 1,
                "source_text": "负责常规资料归档。",
            },
            {
                "source_unit_id": "candidate_requirements:0001",
                "source_field": "candidate_requirements",
                "ordinal": 1,
                "source_text": "若参与夜间盘点，需能使用手持终端。",
            },
            {
                "source_unit_id": "preferred_qualifications:0001",
                "source_field": "preferred_qualifications",
                "ordinal": 1,
                "source_text": "有展陈排期经验者优先。",
            },
        ],
    }


def _examples_by_case() -> dict[str, dict]:
    return {
        example["case"]: example
        for example in JOB_EVALUATION_PLAN_V5_FEW_SHOT_EXAMPLES
    }


def test_close_05c_prompt_version_and_generic_conditional_rules_are_frozen() -> None:
    system_prompt = build_job_evaluation_plan_v5_messages(_snapshot())[0]["content"]

    assert JOB_EVALUATION_PLAN_V5_PROMPT_VERSION == (
        "job_evaluation_plan_lightweight_v4"
    )
    for rule in (
        "若、当、仅在",
        "先识别触发条件是否已经由完整 JD 明确成立",
        "不得自行假定触发条件成立",
        "不得删除、弱化或改写触发条件",
        "不得为无条件要求编造前置条件",
        "通常使用 general",
        "完整条件",
        "交给 HR 复核",
    ):
        assert rule in system_prompt


def test_close_05c_few_shots_cover_the_required_generic_semantic_matrix() -> None:
    examples = _examples_by_case()

    assert set(examples) == {
        "responsibility_explicit_strong",
        "requirement_explicit_weak",
        "no_explicit_strength_signal",
        "negation_turn_and_relaxation",
        "multi_source_mixed_strength",
        "conditional_trigger_established",
        "conditional_trigger_unresolved",
        "work_duration_excluded_mixed_capability_retained",
    }

    assert examples["responsibility_explicit_strong"]["output"]["criteria"][0][
        "importance"
    ] == "required"
    assert examples["requirement_explicit_weak"]["output"]["criteria"][0][
        "importance"
    ] == "preferred"
    assert examples["negation_turn_and_relaxation"]["output"]["criteria"][0][
        "importance"
    ] == "preferred"
    assert examples["multi_source_mixed_strength"]["output"]["criteria"][0][
        "importance"
    ] == "required"


def test_close_05c_unresolved_condition_stays_general_and_keeps_full_trigger() -> None:
    criterion = _examples_by_case()["conditional_trigger_unresolved"]["output"][
        "criteria"
    ][0]
    serialized = json.dumps(criterion, ensure_ascii=False, sort_keys=True)

    assert criterion["importance"] == "general"
    assert "仅在参与海外展陈布置时" in serialized
    assert "required" not in serialized


def test_close_05c_established_condition_is_not_mistaken_for_unresolved() -> None:
    example = _examples_by_case()["conditional_trigger_established"]
    criterion = example["output"]["criteria"][0]
    serialized_input = json.dumps(example["input"], ensure_ascii=False)
    serialized_output = json.dumps(criterion, ensure_ascii=False)

    assert "本岗位固定承担夜间库房盘点" in serialized_input
    assert "当承担夜间库房盘点时" in serialized_input
    assert criterion["importance"] == "required"
    assert "夜间库房盘点" in serialized_output


def test_close_05c_unconditional_examples_do_not_invent_trigger_conditions() -> None:
    examples = _examples_by_case()
    for case in (
        "responsibility_explicit_strong",
        "requirement_explicit_weak",
        "no_explicit_strength_signal",
        "negation_turn_and_relaxation",
        "multi_source_mixed_strength",
    ):
        output = json.dumps(examples[case]["output"], ensure_ascii=False)
        assert all(marker not in output for marker in ("若", "当", "仅在"))
