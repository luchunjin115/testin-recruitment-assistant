from __future__ import annotations

from sqlalchemy import CheckConstraint

from app.models.job_evaluation_plan import JobEvaluationPlan


def _constraint_sql() -> dict[str, str]:
    return {
        constraint.name: str(constraint.sqltext)
        for constraint in JobEvaluationPlan.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_v3_model_adds_nullable_source_review_summary_jsonb() -> None:
    column = JobEvaluationPlan.__table__.c.source_review_summary
    assert column.nullable is True
    assert column.type.__class__.__name__ == "JSONB"


def test_v3_model_makes_structured_coverage_legacy_nullable() -> None:
    assert JobEvaluationPlan.__table__.c.structured_coverage.nullable is True


def test_v3_model_keeps_free_text_coverage_legacy_nullable() -> None:
    assert JobEvaluationPlan.__table__.c.free_text_coverage.nullable is True


def test_v3_model_requires_ready_summary_and_forbids_legacy_coverages() -> None:
    sql = " ".join(_constraint_sql().values()).lower()
    assert "schema_version" in sql
    assert "3.0" in sql
    assert "source_review_summary is not null" in sql
    assert "structured_coverage is null" in sql
    assert "free_text_coverage is null" in sql


def test_v5_model_versions_job_input_fingerprint_uniqueness() -> None:
    indexes = {
        index.name: index for index in JobEvaluationPlan.__table__.indexes
    }
    legacy_index = indexes["uq_job_evaluation_plans_legacy_job_input"]
    v5_index = indexes["uq_job_evaluation_plans_v5_job_input_edit_version"]
    assert [column.name for column in legacy_index.columns] == [
        "job_id",
        "input_fingerprint",
    ]
    assert [column.name for column in v5_index.columns] == [
        "job_id",
        "input_fingerprint",
        "edit_version",
    ]
    assert "schema_version <> '5.0'" in str(
        legacy_index.dialect_options["postgresql"]["where"]
    )
    assert "schema_version = '5.0'" in str(
        v5_index.dialect_options["postgresql"]["where"]
    )
