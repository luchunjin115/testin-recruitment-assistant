from __future__ import annotations

import json
import re

from app.prompts.screening_evaluation import (
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    _V5_SYSTEM_PROMPT,
    build_screening_evaluation_v5_messages,
)
from app.schemas.screening_evaluation import AIScreeningEvaluationV5Output
from tests.fixtures.v5_i4_quality_samples import I4_REPORT_PAIRS


def _messages() -> list[dict[str, str]]:
    return build_screening_evaluation_v5_messages(
        job_snapshot={"title": "虚构平台岗位"},
        evaluation_plan={"schema_version": "5.0", "criteria": []},
        sanitized_resume="负责虚构平台接口交付。",
        evaluation_reference_at="2099-12-31T23:59:59+00:00",
        evaluation_timezone="PRIVATE_TIMEZONE_MARKER",
        experience_period_facts={
            "private_duration_marker": "9876 months",
            "facts": [{"key": "experience_period:private-marker"}],
        },
    )


def test_current_prompt_and_service_versions_are_v9_and_v10() -> None:
    assert SCREENING_EVALUATION_V5_PROMPT_VERSION == (
        "screening_evaluation_lightweight_v10"
    )
    assert SCREENING_EVALUATION_V5_BEHAVIOR_VERSION == (
        "lightweight_report_generation_v11"
    )


def test_close_05i_model_input_contains_no_reference_or_duration_fact_boundary() -> None:
    user_prompt = _messages()[1]["content"]

    for forbidden in (
        "EVALUATION_REFERENCE",
        "EXPERIENCE_PERIOD_FACTS",
        "2099-12-31T23:59:59+00:00",
        "PRIVATE_TIMEZONE_MARKER",
        "private_duration_marker",
        "9876 months",
        "experience_period:private-marker",
    ):
        assert forbidden not in user_prompt
    for required in ("JOB", "CONFIRMED_EVALUATION_PLAN", "SANITIZED_RESUME"):
        assert f"BEGIN UNTRUSTED {required} DATA" in user_prompt
        assert f"END UNTRUSTED {required} DATA" in user_prompt


def test_close_05i_prompt_forbids_work_duration_across_every_report_section() -> None:
    for required_rule in (
        "不计算工作年限",
        "不判断工作年限是否达到 JD 要求",
        "不因工作年限加分或扣分",
        "overall_score",
        "criterion_assessments",
        "strengths",
        "gaps",
        "risks_or_conflicts",
        "missing_info",
        "hr_follow_up_questions",
        "overall_summary",
        "experience_period_fact_keys=[]",
        "calculation_note=null",
        "交给 HR 在 AI 初筛之外判断",
    ):
        assert required_rule in _V5_SYSTEM_PROMPT

    for removed_instruction in (
        "actual_months",
        "threshold_months",
        "EXPERIENCE_PERIOD_FACTS",
        "evaluation_reference_at 是 application_applied_at",
        "达到至少3年门槛",
    ):
        assert removed_instruction not in _V5_SYSTEM_PROMPT


def test_close_05i_all_few_shots_keep_compatibility_time_fields_empty() -> None:
    examples = re.findall(r"^完整示例 JSON：(\{.*\})$", _V5_SYSTEM_PROMPT, flags=re.MULTILINE)
    assert len(examples) == 1

    for serialized in examples:
        payload = json.loads(serialized)
        output = AIScreeningEvaluationV5Output.model_validate(payload)
        assert all(
            assessment.experience_period_fact_keys == []
            and assessment.calculation_note is None
            for assessment in output.criterion_assessments
        )


def test_close_05i_prompt_does_not_copy_formal_i4_report_material() -> None:
    formal_markers = {
        marker
        for case in I4_REPORT_PAIRS
        for marker in (
            case["jd"]["job_responsibilities"],
            case["resume_text"],
        )
    }
    assert formal_markers
    assert all(marker not in _V5_SYSTEM_PROMPT for marker in formal_markers)
