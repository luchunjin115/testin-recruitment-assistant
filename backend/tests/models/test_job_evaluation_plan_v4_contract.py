from __future__ import annotations

from sqlalchemy import CheckConstraint

from app.models.job_evaluation_plan import JobEvaluationPlan


def test_v4_model_adds_four_nullable_jsonb_columns() -> None:
    columns = JobEvaluationPlan.__table__.c
    for name in (
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
    ):
        assert name in columns, f"7R4-B Model 缺少 {name}"
        assert columns[name].nullable is True
        assert columns[name].type.__class__.__name__ == "JSONB"


def test_v4_model_constraint_supports_pending_confirmation_and_ready() -> None:
    sql = " ".join(
        str(constraint.sqltext)
        for constraint in JobEvaluationPlan.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ).lower()
    assert "4.0" in sql
    assert "pending_confirmation" in sql
    for column in (
        "requirement_facts is not null",
        "evaluation_criteria is not null",
        "coverage_review_summary is not null",
        "generation_audit is not null",
    ):
        assert column in sql


def test_v4_model_forbids_legacy_items_on_current_contract() -> None:
    sql = " ".join(
        str(constraint.sqltext)
        for constraint in JobEvaluationPlan.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ).lower()
    assert "items" in sql and "4.0" in sql and "is null" in sql
