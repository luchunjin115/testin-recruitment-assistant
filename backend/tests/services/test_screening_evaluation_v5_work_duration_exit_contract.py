from __future__ import annotations

import asyncio
import json

import pytest

from app.adapters.screening_evaluation import (
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterResult,
)
from app.core.config import Settings
from app.services.screening_evaluation_service import (
    SCREENING_REDACTION_VERSION,
    ScreeningEvaluationInvalidOutputError,
    ScreeningEvaluationService,
)
from tests.services.test_screening_evaluation_v5_service import (
    RAW_RESUME,
    REFERENCE_AT,
    make_plan,
    make_report,
    make_snapshot,
)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        SCREENING_EVALUATION_ENABLED=True,
        SCREENING_EVALUATION_MODEL="fake-v5-model",
        SCREENING_EVALUATION_V5_PROMPT_VERSION=(
            "screening_evaluation_lightweight_v10"
        ),
        SCREENING_EVALUATION_V5_SCHEMA_VERSION="5.0",
        SCREENING_EVALUATION_TIMEZONE="Asia/Shanghai",
        EXPERIENCE_PERIOD_FACTS_RULE_VERSION="experience_period_facts_v1",
        SCREENING_REDACTION_VERSION=SCREENING_REDACTION_VERSION,
    )


def _adapter() -> FakeScreeningEvaluationAdapter:
    return FakeScreeningEvaluationAdapter(
        [
            ScreeningEvaluationAdapterResult(
                content=json.dumps(make_report(), ensure_ascii=False),
                model="fake-v5-model",
                finish_reason="stop",
                input_tokens=120,
                output_tokens=80,
            )
        ]
    )


def test_close_05i_evaluate_ignores_legacy_duration_facts_and_neutralizes_adapter_input() -> None:
    adapter = _adapter()

    result = asyncio.run(
        ScreeningEvaluationService().evaluate_v5(
            job_snapshot=make_snapshot(),
            evaluation_plan=make_plan(),
            resume_text=RAW_RESUME,
            evaluation_reference_at=REFERENCE_AT,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts={
                "invalid_legacy_payload": "must not be parsed",
                "private_duration_marker": "9876 months",
            },
            adapter=adapter,
            settings=_settings(),
        )
    )

    assert result.behavior_version == "lightweight_report_generation_v11"
    assert result.metadata.prompt_version == "screening_evaluation_lightweight_v10"
    assert len(adapter.calls) == 1
    assert adapter.calls[0]["experience_period_facts"] == {}
    assert adapter.calls[0]["evaluation_reference_at"] == ""
    assert adapter.calls[0]["evaluation_timezone"] == ""


def test_close_05i_parser_no_longer_requires_experience_period_facts() -> None:
    service = ScreeningEvaluationService()
    sanitized = service.sanitize_resume_text(RAW_RESUME)

    report = service.parse_and_validate_v5_output(
        json.dumps(make_report(), ensure_ascii=False),
        evaluation_plan=make_plan(),
        sanitized_resume=sanitized,
    )

    assert all(
        item.assessment.experience_period_fact_keys == []
        and item.assessment.calculation_note is None
        for item in report.criterion_assessments
    )


@pytest.mark.parametrize(
    ("fact_keys", "calculation_note"),
    [
        (["experience_period:0123456789abcdef"], None),
        ([], "累计工作 36 个月。"),
        (["experience_period:0123456789abcdef"], "累计工作 36 个月。"),
    ],
)
def test_close_05i_parser_rejects_any_nonempty_compatibility_time_field(
    fact_keys: list[str],
    calculation_note: str | None,
) -> None:
    service = ScreeningEvaluationService()
    sanitized = service.sanitize_resume_text(RAW_RESUME)
    payload = make_report()
    assessment = payload["criterion_assessments"][0]
    assessment["experience_period_fact_keys"] = fact_keys
    assessment["calculation_note"] = calculation_note

    with pytest.raises(
        ScreeningEvaluationInvalidOutputError,
        match="经历时间兼容字段必须为空",
    ):
        service.parse_and_validate_v5_output(
            json.dumps(payload, ensure_ascii=False),
            evaluation_plan=make_plan(),
            sanitized_resume=sanitized,
        )


def test_close_05i_service_does_not_keyword_rejudge_hr_visible_duration_wording() -> None:
    service = ScreeningEvaluationService()
    sanitized = service.sanitize_resume_text(RAW_RESUME)
    payload = make_report()
    payload["overall_summary"] = (
        "项目采用三个月交付周期；工作年限是否满足要求由 HR 在初筛外判断。"
    )

    report = service.parse_and_validate_v5_output(
        json.dumps(payload, ensure_ascii=False),
        evaluation_plan=make_plan(),
        sanitized_resume=sanitized,
    )

    assert report.overall_summary == payload["overall_summary"]
