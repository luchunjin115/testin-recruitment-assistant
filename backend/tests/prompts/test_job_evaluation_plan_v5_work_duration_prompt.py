from __future__ import annotations

import json

from app.prompts.job_evaluation_plan import (
    JOB_EVALUATION_PLAN_V5_FEW_SHOT_EXAMPLES,
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
    build_job_evaluation_plan_v5_messages,
)
from tests.fixtures.v5_i4_quality_samples import I4_PLAN_JDS


def _snapshot() -> dict:
    return {
        "schema_version": "5.0",
        "job_context": {
            "title": "虚构基础设施岗位",
            "department": "虚构平台部门",
            "job_background": "仅用于离线 Prompt 合同测试。",
        },
        "evaluation_fields": {
            "job_responsibilities": "负责平台基础设施自动化。",
            "candidate_requirements": "6 年以上工作经验；2 年以上 Go 经验。",
            "preferred_qualifications": None,
        },
        "source_units": [
            {
                "source_unit_id": "job_responsibilities:0001",
                "source_field": "job_responsibilities",
                "ordinal": 1,
                "source_text": "负责平台基础设施自动化。",
            },
            {
                "source_unit_id": "candidate_requirements:0001",
                "source_field": "candidate_requirements",
                "ordinal": 1,
                "source_text": "6 年以上工作经验；2 年以上 Go 经验。",
            },
        ],
    }


def _system_prompt() -> str:
    return build_job_evaluation_plan_v5_messages(_snapshot())[0]["content"]


def test_close_05h_prompt_v4_explicitly_removes_work_duration_from_ai_criteria() -> None:
    prompt = _system_prompt()

    assert JOB_EVALUATION_PLAN_V5_PROMPT_VERSION == (
        "job_evaluation_plan_lightweight_v4"
    )
    for rule in (
        "不计算工作年限",
        "不判断工作年限是否达到 JD 要求",
        "纯工作年限要求不得生成评价点",
        "忽略其中的工作年限",
        "保留非年限能力",
        "name、description、screening_focus",
        "source_quote 可以保留逐字原文",
        "交给 HR 在 AI 初筛之外判断",
    ):
        assert rule in prompt


def test_close_05h_few_shot_omits_pure_duration_and_keeps_mixed_capability() -> None:
    examples = {
        example["case"]: example
        for example in JOB_EVALUATION_PLAN_V5_FEW_SHOT_EXAMPLES
    }
    example = examples["work_duration_excluded_mixed_capability_retained"]
    serialized_input = json.dumps(example["input"], ensure_ascii=False)
    criterion = example["output"]["criteria"][0]
    candidate_facing_output = "\n".join(
        (
            criterion["name"],
            criterion["description"],
            criterion["screening_focus"],
        )
    )

    assert "6 年以上工作经验" in serialized_input
    assert "2 年以上 Go 经验" in serialized_input
    assert "Go" in candidate_facing_output
    assert "6 年以上工作经验" not in candidate_facing_output
    assert "2 年以上" not in candidate_facing_output
    assert "工作年限" not in candidate_facing_output
    assert criterion["sources"][0]["source_quote"] == "2 年以上 Go 经验"


def test_close_05h_prompt_does_not_copy_formal_i4_plan_requirements() -> None:
    prompt = _system_prompt()

    formal_requirements = {
        requirement
        for plan in I4_PLAN_JDS
        for requirement in (
            *plan["labels"]["excluded_pure_work_duration_requirements"],
            *(
                item["source_requirement"]
                for item in plan["labels"]["mixed_requirement_capability_items"]
            ),
        )
    }
    assert formal_requirements
    assert all(requirement not in prompt for requirement in formal_requirements)
