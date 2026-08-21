from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanContentError,
    JobEvaluationPlanService,
)


def texts(units) -> tuple[str, ...]:
    return tuple(unit.source_text for unit in units)


def test_source_units_split_crlf_lf_sentences_and_priority_boundaries() -> None:
    service = JobEvaluationPlanService()
    lf = (
        "负责数据分析，并输出周报，必须掌握 Python；"
        "优先有 SaaS implementation experience。\n"
        "Design evaluation pipelines!"
    )
    crlf = lf.replace("\n", "\r\n")

    expected = (
        "负责数据分析，并输出周报，",
        "必须掌握 Python；",
        "优先有 SaaS implementation experience。",
        "Design evaluation pipelines!",
    )
    assert texts(service.build_description_source_units(lf)) == expected
    assert texts(service.build_description_source_units(crlf)) == expected


def test_source_units_do_not_split_connectors_and_preserve_technical_text() -> None:
    description = "负责 LLM、RAG 和 SaaS 集成及 C++/C#/Node.js/A/B 服务 and 数据复盘。"

    units = JobEvaluationPlanService().build_description_source_units(description)

    assert texts(units) == (description,)
    assert units[0].source_field == "description"


def test_source_units_do_not_detach_suffix_preferred_tone() -> None:
    description = "SaaS implementation experience preferred。"

    units = JobEvaluationPlanService().build_description_source_units(description)

    assert texts(units) == (description,)


def test_source_units_use_description_only_not_context_or_requirements() -> None:
    description = "负责客户调研。"

    units = JobEvaluationPlanService().build_description_source_units(description)

    assert texts(units) == (description,)
    assert all(unit.source_field == "description" for unit in units)
    assert all("虚构岗位标题" not in unit.source_text for unit in units)
    assert all("Python" not in unit.source_text for unit in units)


def test_source_units_keep_consecutive_punctuation_without_empty_fragments() -> None:
    units = JobEvaluationPlanService().build_description_source_units(
        "能处理线上异常？！必须完成根因复盘！！"
    )

    assert texts(units) == ("能处理线上异常？！", "必须完成根因复盘！！")


def test_source_units_strip_only_outer_list_and_wrapper_formatting() -> None:
    units = JobEvaluationPlanService().build_description_source_units(
        "  1. （Design LLM applications and evaluation pipelines）  \n"
        "\t• 必须掌握 Node.js  "
    )

    assert texts(units) == (
        "Design LLM applications and evaluation pipelines",
        "必须掌握 Node.js",
    )


def test_source_units_are_stable_unique_and_immutable() -> None:
    service = JobEvaluationPlanService()
    description = "负责用户调研。负责实验设计。"

    first = service.build_description_source_units(description)
    second = service.build_description_source_units(description)

    assert first == second
    assert isinstance(first, tuple)
    assert tuple(unit.source_id for unit in first) == (
        "description:0001",
        "description:0002",
    )
    assert len({unit.source_id for unit in first}) == len(first)
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        setattr(first[0], "source_text", "被改写")


@pytest.mark.parametrize("description", (None, "", " \t\r\n "))
def test_source_units_reject_empty_description(description: str | None) -> None:
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        JobEvaluationPlanService().build_description_source_units(description)

    assert raised.value.code == "JOB_EVALUATION_PLAN_EMPTY_DESCRIPTION"


def test_source_units_reject_overlong_description_without_truncation() -> None:
    accepted = JobEvaluationPlanService().build_description_source_units("A" * 20_000)
    description = "A" * 20_001

    assert len(accepted) == 1
    assert accepted[0].source_text == "A" * 20_000
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        JobEvaluationPlanService().build_description_source_units(description)

    assert raised.value.code == "JOB_EVALUATION_PLAN_DESCRIPTION_TOO_LONG"


def test_source_units_reject_too_many_fragments_without_truncation() -> None:
    accepted = "\n".join(f"虚构要求 {index}。" for index in range(100))
    description = "\n".join(f"虚构要求 {index}。" for index in range(101))

    units = JobEvaluationPlanService().build_description_source_units(accepted)
    assert len(units) == 100
    assert units[-1].source_id == "description:0100"
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        JobEvaluationPlanService().build_description_source_units(description)

    assert raised.value.code == "JOB_EVALUATION_PLAN_TOO_MANY_SOURCE_UNITS"


def test_source_units_reject_unsafe_control_characters() -> None:
    with pytest.raises(JobEvaluationPlanContentError) as raised:
        JobEvaluationPlanService().build_description_source_units(
            "负责数据分析。\x00必须掌握 Python。"
        )

    assert raised.value.code == "JOB_EVALUATION_PLAN_UNSAFE_DESCRIPTION"
