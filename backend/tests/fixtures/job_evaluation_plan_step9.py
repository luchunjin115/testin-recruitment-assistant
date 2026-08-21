from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


EMPTY_REQUIREMENTS: dict[str, Any] = {
    "schema_version": "1.0",
    "responsibilities": [],
    "required_skills": [],
    "preferred_skills": [],
    "minimum_work_years": None,
    "education_requirement": None,
    "required_experiences": [],
    "preferred_experiences": [],
    "keywords": [],
    "additional_requirements": [],
}


def make_snapshot_payload(
    description: str | None,
    *,
    title: str = "虚构脱敏岗位",
    department: str | None = "测试部",
    requirements: dict[str, Any] | None = None,
    job_id: int = 901,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "title": title,
        "department": department,
        "description": description,
        "requirements": deepcopy(requirements or EMPTY_REQUIREMENTS),
    }


def review_item(
    title: str,
    category: str,
    equivalent_structured_item_key: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "equivalent_structured_item_key": equivalent_structured_item_key,
    }


def requirement_review(
    source_id: str,
    *items: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "disposition": "requirements",
        "non_requirement_reason": None,
        "items": list(items),
    }


def non_requirement_review(
    source_id: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "disposition": "non_requirement",
        "non_requirement_reason": reason,
        "items": [],
    }


def v2_content(*reviews: dict[str, Any]) -> str:
    return json.dumps(
        {"schema_version": "2.0", "source_reviews": list(reviews)},
        ensure_ascii=False,
    )


@dataclass(frozen=True, slots=True)
class SourceUnitCase:
    case_id: str
    description: str
    expected_texts: tuple[str, ...]


SOURCE_UNIT_CASES = (
    SourceUnitCase(
        "pure_chinese",
        "负责用户调研。必须能独立设计实验；有增长经验优先。",
        ("负责用户调研。", "必须能独立设计实验；", "有增长经验优先。"),
    ),
    SourceUnitCase(
        "english_and_mixed",
        "Design LLM applications and evaluation pipelines.\n必须使用 English 进行客户会议。",
        (
            "Design LLM applications and evaluation pipelines.",
            "必须使用 English 进行客户会议。",
        ),
    ),
    SourceUnitCase(
        "list_cleanup",
        "  1. 负责数据分析\r\n\t• 必须掌握 Node.js\r\n（3）有 A/B 测试经验优先  ",
        ("负责数据分析", "必须掌握 Node.js", "有 A/B 测试经验优先"),
    ),
)


JD04 = make_snapshot_payload(
    "Design LLM applications and evaluation pipelines.",
    title="AI 应用工程师",
    department="智能产品部",
    job_id=4,
)

JD08 = make_snapshot_payload(
    "负责拉新、激活和留存实验。",
    title="增长运营",
    department="运营部",
    job_id=8,
)

JD11 = make_snapshot_payload(
    "Own onboarding and renewal for enterprise customers.\n"
    "必须可使用 English 进行客户会议；"
    "SaaS implementation experience preferred。",
    title="Customer Success Manager",
    department="国际业务部",
    job_id=11,
)


EXPECTED_RED_CAPABILITIES = {
    "source_unit_segmentation": "9-B source-unit：确定性切片、稳定 ID 和原文保留",
    "v2_schema_legal_shape": "9-C Prompt/AI Schema/Adapter：接受 source_reviews 2.0 合法形状",
    "traceability_and_recall": "9-D Service：原文追溯、拆分、关联去重和覆盖审计",
    "persistence_and_fingerprint": "9-E 持久化与版本：2.0 审计列、新指纹与新旧行并存",
    "legacy_plan_upgrade": "9-F 旧计划升级：contract_outdated 读取合同",
}
