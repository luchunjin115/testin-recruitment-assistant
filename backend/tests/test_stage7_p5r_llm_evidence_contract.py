from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.schemas.screening_evaluation import (
    CriterionAssessment,
    ScreeningEvaluationPlanInputV5,
)
from app.services.screening_evaluation_service import (
    ScreeningEvaluationInvalidOutputError,
    screening_evaluation_service,
)
from tests.fixtures.stage7_pro_realistic_quality_samples import REPORT_PAIRS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
P3_RAW_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p3-report-raw-results.json"
)
CONFIRMED_PATH = (
    PROJECT_ROOT
    / "docs/stages/stage7/2026-09-01-stage7-pro-realistic-p2-confirmed-plans.json"
)
PROMPT_PATH = PROJECT_ROOT / "backend/app/prompts/screening_evaluation.py"
FRONTEND_VIEW_PATH = (
    PROJECT_ROOT
    / "frontend/src/features/recruitment/ScreeningReportView.tsx"
)
P3_RAW_SHA256 = "94f68aa48bec09204359222deab35c6a03ea543a4108eb93375efe0b39574679"
QUOTE_ONLY_FAILURE_IDS = (
    "P3-R09",
    "P3-S-R09-1",
    "P3-S-R09-2",
    "P3-S-R09-3",
    "P3-S-R17-1",
)
EXPECTED_REPLAY_FAILURE_IDS = ("P3-R04", "P3-R14")


PLAN = {
    "schema_version": "5.0",
    "criteria": [
        {
            "criterion_id": "criterion:0001",
            "name": "接口开发能力",
            "importance": "required",
            "description": "判断候选人是否具备接口设计与开发能力。",
            "screening_focus": "结合当前简历判断接口开发能力。",
            "origin": "ai_from_jd",
            "sources": [
                {
                    "source_field": "candidate_requirements",
                    "source_quote": "需要具备接口设计与开发能力",
                }
            ],
            "hr_note": None,
        }
    ],
}


def _assessment(*, score: int, evidence: list[dict[str, str]]) -> dict:
    return {
        "criterion_id": "criterion:0001",
        "score": score,
        "reason": "这是模型根据当前简历形成的评分解释。",
        "calculation_note": None,
        "experience_period_fact_keys": [],
        "evidence": evidence,
    }


def _output(
    *,
    score: int = 0,
    evidence: list[dict[str, str]] | None = None,
    strengths: list[dict] | None = None,
    overall_summary: str = "当前材料与岗位要求的匹配情况需要结合各评价点阅读。",
) -> dict:
    return {
        "overall_score": 50,
        "overall_summary": overall_summary,
        "criterion_assessments": [
            _assessment(score=score, evidence=evidence or [])
        ],
        "strengths": strengths or [],
        "gaps": [],
        "risks_or_conflicts": [],
        "missing_info": [],
        "hr_follow_up_questions": [],
    }


def _parse(output: dict, resume_text: str = "负责 Spring Boot 接口开发与维护。"):
    return screening_evaluation_service.parse_and_validate_v5_output(
        json.dumps(output, ensure_ascii=False),
        evaluation_plan=PLAN,
        sanitized_resume=resume_text,
    )


def test_positive_score_still_requires_at_least_one_ai_basis() -> None:
    with pytest.raises(ValueError, match="非零分必须至少包含一条 AI 判断依据"):
        CriterionAssessment.model_validate(_assessment(score=6, evidence=[]))


def test_zero_score_can_keep_evidence_empty() -> None:
    assessment = CriterionAssessment.model_validate(
        _assessment(score=0, evidence=[])
    )

    assert assessment.evidence == []


def test_zero_score_can_also_include_an_ai_generated_basis() -> None:
    assessment = CriterionAssessment.model_validate(
        _assessment(
            score=0,
            evidence=[
                {
                    "quote": "AI 检查当前简历后未发现接口设计与开发经历。",
                    "section": "AI 对当前简历的检查结果",
                }
            ],
        )
    )

    assert assessment.evidence[0].quote.startswith("AI 检查")


def test_service_accepts_paraphrased_ai_basis_without_resume_location() -> None:
    report = _parse(
        _output(
            score=8,
            evidence=[
                {
                    "quote": "候选人具有 Spring Boot 接口交付经验。",
                    "section": "工作经历",
                }
            ],
        )
    )

    assert report.criterion_assessments[0].assessment.score == 8


def test_strength_can_rely_on_model_judgment_without_separate_evidence() -> None:
    report = _parse(
        _output(
            score=0,
            strengths=[
                {
                    "summary": "模型认为候选人具有可迁移的接口协作经验。",
                    "criterion_ids": ["criterion:0001"],
                    "evidence": [],
                }
            ],
        )
    )

    assert report.strengths[0].evidence == []


def _p3_inputs() -> tuple[dict, dict, dict, dict]:
    assert hashlib.sha256(P3_RAW_PATH.read_bytes()).hexdigest() == P3_RAW_SHA256
    raw = json.loads(P3_RAW_PATH.read_text(encoding="utf-8"))
    confirmed = json.loads(CONFIRMED_PATH.read_text(encoding="utf-8"))
    plans = {item["case_id"]: item["plan"] for item in confirmed["plans"]}
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    records = {
        item["business_call_id"]: item
        for item in raw["reports"] + raw["stability_runs"]
    }
    attempts = {
        item["business_call_id"]: item for item in raw["attempt_audit"]
    }
    return plans, pairs, records, attempts


@pytest.mark.parametrize("business_call_id", QUOTE_ONLY_FAILURE_IDS)
def test_p3_quote_only_failures_are_legal_under_llm_basis_contract(
    business_call_id: str,
) -> None:
    plans, pairs, records, attempts = _p3_inputs()
    record = records[business_call_id]
    pair = pairs[record["case_id"]]

    report = screening_evaluation_service.parse_and_validate_v5_output(
        attempts[business_call_id]["raw_response"],
        evaluation_plan=ScreeningEvaluationPlanInputV5.model_validate(
            plans[record["job_case_id"]]
        ),
        sanitized_resume=screening_evaluation_service.sanitize_resume_text(
            pair["resume_text"]
        ),
    )

    assert report.overall_score == 88


def test_all_35_p3_raw_responses_replay_as_33_legal_and_2_rejected() -> None:
    plans, pairs, records, attempts = _p3_inputs()
    accepted: list[str] = []
    rejected: list[str] = []

    for business_call_id, record in records.items():
        pair = pairs[record["case_id"]]
        try:
            screening_evaluation_service.parse_and_validate_v5_output(
                attempts[business_call_id]["raw_response"],
                evaluation_plan=ScreeningEvaluationPlanInputV5.model_validate(
                    plans[record["job_case_id"]]
                ),
                sanitized_resume=screening_evaluation_service.sanitize_resume_text(
                    pair["resume_text"]
                ),
            )
        except ScreeningEvaluationInvalidOutputError:
            rejected.append(business_call_id)
        else:
            accepted.append(business_call_id)

    assert len(accepted) == 33
    assert tuple(rejected) == EXPECTED_REPLAY_FAILURE_IDS


def test_unknown_criterion_is_still_rejected() -> None:
    output = _output()
    output["criterion_assessments"][0]["criterion_id"] = "criterion:9999"

    with pytest.raises(
        ScreeningEvaluationInvalidOutputError,
        match="未知或遗漏 criterion_id",
    ):
        _parse(output)


def test_automatic_recruitment_decision_is_still_rejected() -> None:
    with pytest.raises(ScreeningEvaluationInvalidOutputError):
        _parse(_output(overall_summary="建议直接录用该候选人。"))


def test_prompt_defines_evidence_as_ai_basis_instead_of_exact_quote() -> None:
    source = PROMPT_PATH.read_text(encoding="utf-8")

    assert "AI 判断依据" in source
    assert "逐字找到的 evidence.quote" not in source
    assert "0 分：evidence 可以为空或非空" in source


def test_frontend_labels_evidence_as_ai_basis_instead_of_resume_quote() -> None:
    source = FRONTEND_VIEW_PATH.read_text(encoding="utf-8")

    assert "查看 AI 判断依据" in source
    assert "查看简历证据" not in source
    assert "“{item.quote}”" not in source
