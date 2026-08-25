from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "4" * 64


def make_source(
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


def make_requirement_fact(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "fact_id": "fact:0001",
        "category": "experience",
        "priority": "required",
        "sources": [make_source()],
    }
    values.update(overrides)
    return values


def make_evaluation_criterion(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "criterion_id": "criterion:0001",
        "name": "Python 后端工程经验",
        "fact_ids": ["fact:0001"],
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
                "fact_ids": ["fact:0001"],
                "non_evaluation_reason": None,
            }
        ],
    }
    values.update(overrides)
    return values


def make_coverage_review_summary(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "status": "passed",
        "findings": [],
        "repair_performed": False,
        "reviewed_source_unit_ids": ["candidate_requirements:0001"],
    }
    values.update(overrides)
    return values


def make_generation_audit(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "business_call_count": 3,
        "content_repair_count": 0,
        "infrastructure_retry_count": 0,
        "calls": [
            {
                "role": role,
                "prompt_version": prompt_version,
                "model": "fake-plan-model",
                "input_tokens": 100,
                "output_tokens": 50,
                "duration_ms": 10,
                "infrastructure_retry_count": 0,
                "result": "succeeded",
            }
            for role, prompt_version in (
                ("fact_extraction", "job_requirement_fact_extraction_v1"),
                ("coverage_review", "job_requirement_coverage_review_v1"),
                ("criterion_grouping", "job_evaluation_criterion_grouping_v1"),
            )
        ],
    }
    values.update(overrides)
    return values


def make_v4_plan(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "id": 4,
        "job_id": 701,
        "jd_fingerprint": FINGERPRINT,
        "status": "pending_confirmation",
        "is_current": True,
        "items": [],
        "requirement_facts": [make_requirement_fact()],
        "evaluation_criteria": [make_evaluation_criterion()],
        "source_review_summary": make_source_review_summary(),
        "coverage_review_summary": make_coverage_review_summary(),
        "generation_audit": make_generation_audit(),
        "warnings": [],
        "prompt_version": "job_requirement_fact_extraction_v1",
        "model_version": "fake-plan-model",
        "schema_version": "4.0",
        "input_fingerprint": FINGERPRINT,
        "input_snapshot": {
            "schema_version": "4.0",
            "job_context": {
                "title": "AI 应用工程师",
                "department": "技术研发部",
                "job_background": "建设企业 AI 应用平台",
            },
            "evaluation_fields": {
                "job_responsibilities": "负责 AI 应用开发",
                "candidate_requirements": "具备 Python 后端开发经验",
                "preferred_qualifications": "有 RAG 经验者优先",
            },
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": "具备 Python 后端开发经验",
                }
            ],
        },
        "contract_outdated": False,
        "error_code": None,
        "error_message": None,
        "created_at": NOW,
        "completed_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values
