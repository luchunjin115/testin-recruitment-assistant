from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def make_five_section_job(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "id": 701,
        "title": "AI 应用工程师",
        "department": "技术研发部",
        "location": "长沙",
        "employment_type": "full_time",
        "headcount": 2,
        "job_background": "建设面向企业客户的 AI 应用平台。",
        "job_responsibilities": "1. 负责 AI 应用设计、开发和上线\n   包括服务监控与故障复盘",
        "candidate_requirements": "- 具备 Python 后端开发经验\n- 能够跨部门沟通，并推动项目交付",
        "preferred_qualifications": "• 有 RAG 项目经验者优先",
        "public_notes": "面试共三轮，请提前准备项目介绍。",
        "status": "open",
        "updated_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_source_unit(
    *,
    source_field: str = "candidate_requirements",
    ordinal: int = 1,
    source_text: str = "- 具备 Python 后端开发经验",
) -> dict[str, Any]:
    return {
        "source_unit_id": f"{source_field}:{ordinal:04d}",
        "source_field": source_field,
        "ordinal": ordinal,
        "source_text": source_text,
    }


def make_input_snapshot(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "schema_version": "3.0",
        "job_context": {
            "title": "AI 应用工程师",
            "department": "技术研发部",
            "job_background": "建设面向企业客户的 AI 应用平台。",
        },
        "evaluation_fields": {
            "job_responsibilities": "负责 AI 应用设计、开发和上线",
            "candidate_requirements": "具备 Python 后端开发经验",
            "preferred_qualifications": "有 RAG 项目经验者优先",
        },
        "source_units": [make_source_unit()],
    }
    values.update(overrides)
    return values


def make_item_source(
    *,
    source_field: str = "candidate_requirements",
    source_unit_id: str = "candidate_requirements:0001",
    source_quote: str = "具备 Python 后端开发经验",
) -> dict[str, str]:
    return {
        "source_field": source_field,
        "source_unit_id": source_unit_id,
        "source_quote": source_quote,
    }


def make_evaluation_item(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "key": "item:0001",
        "title": "Python 后端开发经验",
        "category": "experience",
        "priority": "required",
        "sources": [make_item_source()],
    }
    values.update(overrides)
    return values


def make_source_review_summary(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "rule_version": "five_section_source_units_v1",
        "total_units": 1,
        "reviewed_units": 1,
        "evaluation_units": 1,
        "non_evaluation_units": 0,
        "all_reviewed": True,
        "units": [
            {
                "source_unit_id": "candidate_requirements:0001",
                "disposition": "evaluation",
                "non_evaluation_reason": None,
                "item_keys": ["item:0001"],
            }
        ],
    }
    values.update(overrides)
    return values


def make_warning(
    code: str = "limited_basis",
    *,
    source_unit_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": f"contract warning: {code}",
        "source_unit_ids": source_unit_ids or [],
    }


def make_plan_read(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "id": 1,
        "job_id": 701,
        "jd_fingerprint": FINGERPRINT,
        "status": "ready",
        "is_current": True,
        "items": [make_evaluation_item()],
        "source_review_summary": make_source_review_summary(),
        "warnings": [],
        "prompt_version": "job_evaluation_plan_v5",
        "model_version": "fake-plan-model",
        "schema_version": "3.0",
        "input_fingerprint": FINGERPRINT,
        "input_snapshot": make_input_snapshot(),
        "contract_outdated": False,
        "error_code": None,
        "error_message": None,
        "created_at": NOW,
        "completed_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


def make_ai_v3_response(
    source_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "3.0",
        "source_reviews": source_reviews,
    }


def make_ai_review(
    *,
    source_unit_id: str = "candidate_requirements:0001",
    disposition: str = "evaluation",
    non_evaluation_reason: str | None = None,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if items is None and disposition == "evaluation":
        items = [
            {
                "title": "Python 后端开发经验",
                "category": "experience",
                "source_quote": "具备 Python 后端开发经验",
            }
        ]
    return {
        "source_unit_id": source_unit_id,
        "disposition": disposition,
        "non_evaluation_reason": non_evaluation_reason,
        "items": items or [],
    }
