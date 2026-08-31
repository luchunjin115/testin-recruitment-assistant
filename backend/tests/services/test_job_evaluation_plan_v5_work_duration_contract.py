from __future__ import annotations

import asyncio
import json

import pytest

from app.adapters.job_evaluation_plan import (
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.schemas.job_evaluation_plan import (
    JobEvaluationPlanInputSnapshot,
    V5CriterionItem,
)
from app.services.job_evaluation_plan_service import (
    JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
    JobEvaluationPlanContentError,
    JobEvaluationPlanService,
    JobEvaluationPlanV5GenerationError,
)


MIXED_SOURCE = "3 年以上 Java 经验"
PURE_SOURCE = "3 年以上工作经验"
RESPONSIBILITY_SOURCE = "负责订单接口设计和交付"


def _snapshot() -> dict:
    return {
        "schema_version": "5.0",
        "job_context": {
            "title": "订单平台工程师",
            "department": "虚构交易平台组",
            "job_background": "仅用于离线 Service 合同测试。",
        },
        "evaluation_fields": {
            "job_responsibilities": RESPONSIBILITY_SOURCE,
            "candidate_requirements": f"{PURE_SOURCE}；{MIXED_SOURCE}",
            "preferred_qualifications": None,
        },
        "source_units": [
            {
                "source_unit_id": "job_responsibilities:0001",
                "source_field": "job_responsibilities",
                "ordinal": 1,
                "source_text": RESPONSIBILITY_SOURCE,
            },
            {
                "source_unit_id": "candidate_requirements:0001",
                "source_field": "candidate_requirements",
                "ordinal": 1,
                "source_text": f"{PURE_SOURCE}；{MIXED_SOURCE}",
            },
        ],
    }


def _criterion(
    *,
    name: str,
    description: str,
    screening_focus: str,
    source_field: str = "candidate_requirements",
    source_quote: str = MIXED_SOURCE,
) -> dict:
    return {
        "name": name,
        "importance": "required",
        "description": description,
        "screening_focus": screening_focus,
        "sources": [
            {
                "source_field": source_field,
                "source_quote": source_quote,
            }
        ],
    }


def _adapter(payload: dict) -> FakeJobEvaluationPlanAdapter:
    return FakeJobEvaluationPlanAdapter(
        [
            JobEvaluationPlanAdapterResult(
                content=json.dumps(payload, ensure_ascii=False),
                model="fake-plan-model",
                finish_reason="stop",
                input_tokens=100,
                output_tokens=50,
            )
        ]
    )


def test_close_05h_service_v5_accepts_mixed_source_after_duration_is_removed() -> None:
    adapter = _adapter(
        {
            "criteria": [
                _criterion(
                    name="Java 工程实践",
                    description="判断是否具有 Java 工程实践。",
                    screening_focus="寻找 Java 项目职责、实现和交付结果证据。",
                )
            ]
        }
    )

    content = asyncio.run(
        JobEvaluationPlanService().build_v5_plan_content(
            _snapshot(),
            adapter=adapter,
        )
    )

    assert JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION == (
        "lightweight_plan_generation_v5"
    )
    assert content.breaking_contract_version == "lightweight_plan_generation_v5"
    assert content.schema_version == "5.0"
    assert [criterion.name for criterion in content.criteria] == ["Java 工程实践"]
    assert content.criteria[0].sources[0].source_quote == MIXED_SOURCE
    assert len(adapter.v5_calls) == 1


@pytest.mark.parametrize(
    ("name", "description", "screening_focus"),
    [
        ("3 年以上工作经验", "判断工作经验是否达到三年。", "核对累计工作年限。"),
        ("3 年以上 Java 经验", "判断 Java 经验是否满三年。", "核对 Java 工作年限。"),
        ("Java 经验", "判断是否具有至少 36 个月 Java 经验。", "寻找 Java 项目。"),
        ("Java 经验", "判断 Java 工程实践。", "寻找工作满三年的 Java 经历。"),
        ("Java experience", "At least 3 years of Java experience.", "Review projects."),
    ],
)
def test_close_05h_service_rejects_duration_in_candidate_facing_fields_without_retry(
    name: str,
    description: str,
    screening_focus: str,
) -> None:
    adapter = _adapter(
        {
            "criteria": [
                _criterion(
                    name=name,
                    description=description,
                    screening_focus=screening_focus,
                )
            ]
        }
    )

    with pytest.raises(JobEvaluationPlanV5GenerationError) as caught:
        asyncio.run(
            JobEvaluationPlanService().build_v5_plan_content(
                _snapshot(),
                adapter=adapter,
            )
        )

    assert caught.value.code == "JOB_EVALUATION_PLAN_V5_WORK_DURATION_CRITERION"
    assert caught.value.business_call_count == 1
    assert caught.value.adapter_attempt_count == 1
    assert caught.value.infrastructure_retry_count == 0
    assert len(adapter.v5_calls) == 1


def test_close_05h_service_does_not_require_a_criterion_for_pure_duration_source() -> None:
    adapter = _adapter(
        {
            "criteria": [
                _criterion(
                    name="订单接口设计与交付",
                    description="判断是否能够设计并交付订单接口。",
                    screening_focus="寻找订单接口设计、实现和交付结果证据。",
                    source_field="job_responsibilities",
                    source_quote=RESPONSIBILITY_SOURCE,
                )
            ]
        }
    )

    content = asyncio.run(
        JobEvaluationPlanService().build_v5_plan_content(
            _snapshot(),
            adapter=adapter,
        )
    )

    serialized = json.dumps(
        [criterion.model_dump(mode="json") for criterion in content.criteria],
        ensure_ascii=False,
    )
    assert PURE_SOURCE not in serialized
    assert len(content.criteria) == 1


def test_close_05h_service_does_not_mistake_project_cycle_for_work_duration() -> None:
    source = "负责在 3 个月交付周期内完成平台迁移"
    snapshot = _snapshot()
    snapshot["evaluation_fields"]["job_responsibilities"] = source
    snapshot["source_units"][0]["source_text"] = source
    adapter = _adapter(
        {
            "criteria": [
                _criterion(
                    name="平台迁移交付",
                    description="判断是否能在 3 个月交付周期内完成平台迁移。",
                    screening_focus="寻找按项目周期完成平台迁移的证据。",
                    source_field="job_responsibilities",
                    source_quote=source,
                )
            ]
        }
    )

    content = asyncio.run(
        JobEvaluationPlanService().build_v5_plan_content(snapshot, adapter=adapter)
    )

    assert [criterion.name for criterion in content.criteria] == ["平台迁移交付"]


def test_close_05h_hr_added_ai_criterion_cannot_reintroduce_work_duration() -> None:
    criterion = V5CriterionItem.model_validate(
        {
            "criterion_id": "criterion:0001",
            "name": "工作经验",
            "importance": "required",
            "description": "判断是否具有 3 年以上工作经验。",
            "screening_focus": "核对累计工作年限。",
            "origin": "hr_added",
            "sources": [],
            "hr_note": "HR 手工补充",
        }
    )

    with pytest.raises(JobEvaluationPlanContentError) as caught:
        JobEvaluationPlanService()._validate_v5_hr_criterion(
            criterion,
            JobEvaluationPlanInputSnapshot.model_validate(_snapshot()),
        )

    assert caught.value.code == "JOB_EVALUATION_PLAN_V5_WORK_DURATION_CRITERION"
