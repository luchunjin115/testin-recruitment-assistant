from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from app.adapters.screening_evaluation import ScreeningEvaluationAdapterResult
from app.core.config import Settings
from app.prompts.screening_evaluation import SCREENING_EVALUATION_V5_PROMPT_VERSION
from app.schemas.screening_evaluation import SCREENING_EVALUATION_V5_SCHEMA_VERSION
from app.services.screening_evaluation_service import SCREENING_REDACTION_VERSION


REFERENCE_AT = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)
RAW_RESUME = """姓名：测试候选人
邮箱：candidate@example.com
工作经历
使用 Python 开发 FastAPI 服务并独立交付订单 API。
项目经历
建立接口监控看板，推动产品与研发周会。
"""


def make_snapshot() -> dict[str, Any]:
    return {
        "schema_version": "5.0",
        "job_context": {
            "title": "后端工程师",
            "department": "平台研发部",
            "job_background": "建设业务服务平台。",
        },
        "evaluation_fields": {
            "job_responsibilities": "负责 API 服务设计与交付。",
            "candidate_requirements": "必须具备 Python 后端开发经验。",
            "preferred_qualifications": "有可观测性建设经验者优先。",
        },
        "source_units": [
            {
                "source_unit_id": "job_responsibilities:0001",
                "source_field": "job_responsibilities",
                "ordinal": 1,
                "source_text": "负责 API 服务设计与交付。",
            },
            {
                "source_unit_id": "candidate_requirements:0001",
                "source_field": "candidate_requirements",
                "ordinal": 1,
                "source_text": "必须具备 Python 后端开发经验。",
            },
            {
                "source_unit_id": "preferred_qualifications:0001",
                "source_field": "preferred_qualifications",
                "ordinal": 1,
                "source_text": "有可观测性建设经验者优先。",
            },
        ],
    }


def make_plan() -> dict[str, Any]:
    return {
        "schema_version": "5.0",
        "criteria": [
            {
                "criterion_id": "criterion:0001",
                "name": "Python 后端开发",
                "importance": "required",
                "description": "核对 Python 后端开发实践。",
                "screening_focus": "寻找 Python 服务项目依据。",
                "origin": "ai_from_jd",
                "sources": [
                    {
                        "source_field": "candidate_requirements",
                        "source_quote": "必须具备 Python 后端开发经验",
                    }
                ],
                "hr_note": None,
            },
            {
                "criterion_id": "criterion:0002",
                "name": "API 交付",
                "importance": "general",
                "description": "核对 API 设计与交付依据。",
                "screening_focus": "寻找独立交付记录。",
                "origin": "ai_from_jd",
                "sources": [
                    {
                        "source_field": "job_responsibilities",
                        "source_quote": "负责 API 服务设计与交付",
                    }
                ],
                "hr_note": None,
            },
            {
                "criterion_id": "criterion:0003",
                "name": "可观测性建设",
                "importance": "preferred",
                "description": "核对监控和可观测性实践。",
                "screening_focus": "寻找监控看板等依据。",
                "origin": "ai_from_jd",
                "sources": [
                    {
                        "source_field": "preferred_qualifications",
                        "source_quote": "有可观测性建设经验者优先",
                    }
                ],
                "hr_note": None,
            },
        ],
    }


def make_report(*, overall_score: int = 78) -> dict[str, Any]:
    return {
        "overall_score": overall_score,
        "overall_summary": "Python 服务与 API 交付依据较充分，可观测性仍需核实。",
        "criterion_assessments": [
            {
                "criterion_id": "criterion:0001",
                "score": 8,
                "reason": "材料支持 Python 服务开发实践。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [
                    {
                        "quote": "AI 判断：Python 与 FastAPI 经历支持该项评分。",
                        "section": "工作经历",
                    }
                ],
            },
            {
                "criterion_id": "criterion:0002",
                "score": 8,
                "reason": "材料支持 API 独立交付经历。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [
                    {
                        "quote": "AI 判断：订单 API 交付经历支持该项评分。",
                        "section": "工作经历",
                    }
                ],
            },
            {
                "criterion_id": "criterion:0003",
                "score": 5,
                "reason": "材料体现监控看板实践，但深度仍需核实。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [
                    {
                        "quote": "AI 判断：监控看板经历提供了部分相关依据。",
                        "section": "项目经历",
                    }
                ],
            },
        ],
        "strengths": [
            {
                "summary": "具备 API 服务开发和交付经历。",
                "criterion_ids": ["criterion:0001", "criterion:0002"],
                "evidence": [],
            }
        ],
        "gaps": [
            {
                "summary": "可观测性建设深度仍需核实。",
                "criterion_ids": ["criterion:0003"],
                "evidence": [],
            }
        ],
        "risks_or_conflicts": [],
        "missing_info": [],
        "hr_follow_up_questions": ["请核实监控告警覆盖范围和实际效果。"],
    }


def make_settings(**updates: object) -> Settings:
    values: dict[str, object] = {
        "SCREENING_EVALUATION_ENABLED": True,
        "SCREENING_EVALUATION_MODEL": "fake-p5r-ga-model",
        "SCREENING_EVALUATION_V5_PROMPT_VERSION": (
            SCREENING_EVALUATION_V5_PROMPT_VERSION
        ),
        "SCREENING_EVALUATION_V5_SCHEMA_VERSION": (
            SCREENING_EVALUATION_V5_SCHEMA_VERSION
        ),
        "SCREENING_EVALUATION_TIMEZONE": "Asia/Shanghai",
        "EXPERIENCE_PERIOD_FACTS_RULE_VERSION": "experience_period_facts_v1",
        "SCREENING_REDACTION_VERSION": SCREENING_REDACTION_VERSION,
        "DEEPSEEK_API_KEY": "",
    }
    values.update(updates)
    return Settings(_env_file=None, **values)


def adapter_result(
    content: str | dict[str, Any],
    *,
    input_tokens: int | None = 100,
    output_tokens: int | None = 50,
) -> ScreeningEvaluationAdapterResult:
    serialized = (
        json.dumps(content, ensure_ascii=False)
        if isinstance(content, dict)
        else content
    )
    return ScreeningEvaluationAdapterResult(
        content=serialized,
        model="fake-p5r-ga-model",
        finish_reason="stop",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class RepairCapableFakeAdapter:
    """Zero-network fake that exposes the future independent repair call."""

    def __init__(
        self,
        initial_outcomes: Iterable[ScreeningEvaluationAdapterResult | Exception],
        repair_outcomes: Iterable[ScreeningEvaluationAdapterResult | Exception] = (),
    ) -> None:
        self._initial_outcomes = list(initial_outcomes)
        self._repair_outcomes = list(repair_outcomes)
        self.initial_calls: list[dict[str, Any]] = []
        self.repair_calls: list[dict[str, Any]] = []

    async def evaluate_v5(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        self.initial_calls.append(copy.deepcopy(kwargs))
        if not self._initial_outcomes:
            raise AssertionError("Fake Adapter 没有首次报告结果")
        outcome = self._initial_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    async def evaluate(self, **kwargs: Any) -> ScreeningEvaluationAdapterResult:
        return await self.evaluate_v5(**kwargs)

    async def repair_v5(
        self,
        *,
        sanitized_resume: str,
        confirmed_criteria: list[dict[str, Any]],
        original_response: str,
        validation_errors: list[dict[str, str]],
    ) -> ScreeningEvaluationAdapterResult:
        self.repair_calls.append(
            {
                "sanitized_resume": sanitized_resume,
                "confirmed_criteria": copy.deepcopy(confirmed_criteria),
                "original_response": original_response,
                "validation_errors": copy.deepcopy(validation_errors),
            }
        )
        if not self._repair_outcomes:
            raise AssertionError("Fake Adapter 没有 Repair 结果")
        outcome = self._repair_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


