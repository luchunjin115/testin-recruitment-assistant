"""v5.0 AI screening schema/model contract tests.

Tests are organized by responsibility batch:

- 7R5-B: schema_version "5.0" support, lightweight criterion fields, model columns
- 7R5-E: structured report sections (strengths, gaps, risks, missing_info)
- Static proof: fields that must never exist (weights) and display label ranges

Every xfail test SHOULD fail because v5.0 production code has not been built yet.
When implementation lands, the strict xfail will alert us that the test now passes
and the marker can be removed.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import (
    EvaluationCriterion,
    JobEvaluationPlanRead,
    JobEvaluationPlanInputSnapshot,
)
from app.schemas.screening_evaluation import (
    ScreeningEvaluationPlanInput,
)
from app.schemas.screening_evaluation import AIScreeningEvaluationOutput


# ---------------------------------------------------------------------------
# A. Schema version 5.0 not yet supported (7R5-B)
# ---------------------------------------------------------------------------


class TestSchemaVersion50NotSupported:
    """5.0 schema version is not accepted by any current schema or model.
    All tests xfail because 7R5-B has not landed yet."""

    def test_plan_read_accepts_valid_schema_version_5(self) -> None:
        """JobEvaluationPlanRead accepts a complete 5.0 pending draft."""
        plan = JobEvaluationPlanRead.model_validate({
            "id": 1,
            "job_id": 1,
            "jd_fingerprint": "a" * 64,
            "status": "pending_confirmation",
            "is_current": True,
            "items": None,
            "v5_criteria": [
                {
                    "criterion_id": "criterion:0001",
                    "name": "Python 后端经验",
                    "importance": "required",
                    "description": "核对 Python 后端项目经验。",
                    "screening_focus": "寻找 Python 后端项目证据。",
                    "origin": "ai_from_jd",
                    "sources": [
                        {
                            "source_field": "candidate_requirements",
                            "source_quote": "必须具备 Python 后端项目经验",
                        }
                    ],
                    "hr_note": None,
                }
            ],
            "edit_version": 1,
            "confirmed_at": None,
            "warnings": [],
            "prompt_version": "v1",
            "model_version": "v1",
            "schema_version": "5.0",
            "input_fingerprint": "b" * 64,
            "input_snapshot": {
                "schema_version": "5.0",
                "job_context": {"title": "后端工程师"},
                "evaluation_fields": {
                    "job_responsibilities": None,
                    "candidate_requirements": "必须具备 Python 后端项目经验",
                    "preferred_qualifications": None,
                },
                "source_units": [
                    {
                        "source_unit_id": "candidate_requirements:0001",
                        "source_field": "candidate_requirements",
                        "ordinal": 1,
                        "source_text": "必须具备 Python 后端项目经验",
                    }
                ],
            },
            "error_code": None,
            "error_message": None,
            "created_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        })
        assert plan.schema_version == "5.0"
        assert plan.edit_version == 1

    def test_input_snapshot_rejects_schema_version_5(self) -> None:
        """JobEvaluationPlanInputSnapshot.schema_version Literal['3.0', '4.0']
        does not include '5.0'. After 7R5-B it should."""
        JobEvaluationPlanInputSnapshot.model_validate({
            "schema_version": "5.0",
            "job_context": {"title": "Test"},
            "evaluation_fields": {},
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": "Test requirement",
                },
            ],
        })

    def test_model_check_constraint_excludes_5(self) -> None:
        """The model-level CheckConstraint on schema_version must allow '5.0'.

        Currently: schema_version IN ('1.0', '2.0', '3.0', '4.0').
        After 7R5-B: should include '5.0'.
        """
        constraint_texts = []
        for constraint in JobEvaluationPlan.__table_args__:
            if hasattr(constraint, "name") and constraint.name == "ck_job_evaluation_plans_schema_version_allowed":
                constraint_texts.append(str(constraint.sqltext))
        assert len(constraint_texts) == 1, "Expected exactly one schema_version CheckConstraint"
        assert "'5.0'" in constraint_texts[0], (
            "CheckConstraint must include '5.0' after 7R5-B"
        )

    def test_screening_evaluation_plan_input_only_accepts_4(self) -> None:
        """ScreeningEvaluationPlanInput.schema_version is pinned to r'^4\\.0$'.

        After 7R5-B the screening pipeline must also accept 5.0 plans.
        """
        ScreeningEvaluationPlanInput.model_validate({
            "schema_version": "5.0",
            "requirement_facts": [
                {
                    "fact_id": "fact:0001",
                    "category": "skill",
                    "priority": "required",
                    "sources": [
                        {
                            "source_field": "candidate_requirements",
                            "source_unit_id": "candidate_requirements:0001",
                            "source_quote": "Python required",
                        },
                    ],
                },
            ],
            "evaluation_criteria": [
                {
                    "criterion_id": "criterion:0001",
                    "name": "Python",
                    "fact_ids": ["fact:0001"],
                },
            ],
        })


# ---------------------------------------------------------------------------
# B. v5 criterion fields don't exist yet (7R5-B)
# ---------------------------------------------------------------------------


class TestV5CriterionFieldsMissing:
    """v5.0 lightweight criteria need new fields that don't exist on
    current EvaluationCriterion or as standalone schemas."""

    def test_no_v5_criterion_item_schema(self) -> None:
        """A dedicated V5CriterionItem (or V5LightweightCriterion) should exist
        in the job_evaluation_plan schema module for 5.0 plans.

        Currently absent -- importing it raises ImportError.
        """
        import app.schemas.job_evaluation_plan as plan_mod

        # Try common naming conventions
        v5_names = [
            "V5CriterionItem",
            "V5LightweightCriterion",
            "LightweightCriterion",
            "V5Criterion",
        ]
        found = [name for name in v5_names if hasattr(plan_mod, name)]
        assert found, (
            "Expected at least one v5 criterion schema class: "
            + ", ".join(v5_names)
        )

    def test_evaluation_criterion_has_no_description(self) -> None:
        """v5.0 criteria need a 'description' field for screening focus context.

        Current EvaluationCriterion only has: criterion_id, name, fact_ids.
        """
        assert "description" in EvaluationCriterion.model_fields, (
            "EvaluationCriterion should have a 'description' field for v5.0"
        )

    def test_evaluation_criterion_has_no_screening_focus(self) -> None:
        """v5.0 criteria need a 'screening_focus' field to guide the AI screener
        on what to look for in resumes for this criterion."""
        assert "screening_focus" in EvaluationCriterion.model_fields, (
            "EvaluationCriterion should have a 'screening_focus' field for v5.0"
        )

    def test_evaluation_criterion_has_no_origin(self) -> None:
        """v5.0 criteria need an 'origin' field to distinguish AI-generated
        criteria (ai_from_jd) from HR-added criteria (hr_added)."""
        assert "origin" in EvaluationCriterion.model_fields, (
            "EvaluationCriterion should have an 'origin' field for v5.0"
        )

    def test_evaluation_criterion_has_no_hr_note(self) -> None:
        """v5.0 criteria need an 'hr_note' field so HR can annotate criteria
        with context or instructions for the AI screener."""
        assert "hr_note" in EvaluationCriterion.model_fields, (
            "EvaluationCriterion should have an 'hr_note' field for v5.0"
        )


# ---------------------------------------------------------------------------
# D. Model constraints (7R5-B)
# ---------------------------------------------------------------------------


class TestModelConstraints:
    """DB model must be extended for v5.0 with edit versioning and
    new payload columns."""

    def test_schema_version_constraint_only_allows_up_to_4(self) -> None:
        """The model's schema_version CheckConstraint currently only allows
        '1.0', '2.0', '3.0', '4.0'.

        After 7R5-B, it must also allow '5.0'.
        """
        constraint_text = None
        for constraint in JobEvaluationPlan.__table_args__:
            if hasattr(constraint, "name") and constraint.name == "ck_job_evaluation_plans_schema_version_allowed":
                constraint_text = str(constraint.sqltext)
                break
        assert constraint_text is not None, "schema_version constraint not found"
        # After 7R5-B this must include '5.0'
        assert "'5.0'" in constraint_text, (
            "schema_version CheckConstraint must include '5.0'"
        )

    def test_model_has_no_edit_version_columns(self) -> None:
        """v5.0 requires version/concurrency columns for HR editing:
        edit_version and/or confirmed_version.

        Currently absent from the model.
        """
        column_names = {col.name for col in JobEvaluationPlan.__table__.columns}
        version_columns = column_names & {"edit_version", "confirmed_version"}
        assert version_columns, (
            "Model should have edit_version and/or confirmed_version "
            "for v5.0 HR editing concurrency"
        )

    def test_model_has_no_v5_criteria_column(self) -> None:
        """v5.0 may need a dedicated column for the lightweight criteria snapshot
        (criteria_snapshot or v5_criteria) separate from the v4 evaluation_criteria.

        Currently absent from the model.
        """
        column_names = {col.name for col in JobEvaluationPlan.__table__.columns}
        v5_columns = column_names & {"criteria_snapshot", "v5_criteria"}
        assert v5_columns, (
            "Model should have a criteria_snapshot or v5_criteria column for v5.0"
        )


# ---------------------------------------------------------------------------
# F. 5.0 report structure (7R5-E)
# ---------------------------------------------------------------------------


class TestV5ReportStructureMissing:
    """v5.0 reports need structured narrative sections (strengths, gaps,
    risks, missing_info) on AIScreeningEvaluationOutput.

    These fields don't exist yet; 7R5-E will add them."""

    @pytest.mark.xfail(reason="7R5-E: AIScreeningEvaluationOutput has no 'strengths' field yet", strict=True)
    def test_ai_output_has_no_strengths(self) -> None:
        """v5.0 reports need a 'strengths' section listing candidate strengths
        relative to the criteria."""
        assert "strengths" in AIScreeningEvaluationOutput.model_fields, (
            "AIScreeningEvaluationOutput should have a 'strengths' field for v5.0"
        )

    @pytest.mark.xfail(reason="7R5-E: AIScreeningEvaluationOutput has no 'gaps' field yet", strict=True)
    def test_ai_output_has_no_gaps(self) -> None:
        """v5.0 reports need a 'gaps' section listing where the candidate
        falls short of criteria requirements."""
        assert "gaps" in AIScreeningEvaluationOutput.model_fields, (
            "AIScreeningEvaluationOutput should have a 'gaps' field for v5.0"
        )

    @pytest.mark.xfail(reason="7R5-E: AIScreeningEvaluationOutput has no 'risks' field yet", strict=True)
    def test_ai_output_has_no_risks(self) -> None:
        """v5.0 reports need a 'risks' section for concerns about the candidate
        (e.g., short tenures, unexplained gaps)."""
        assert "risks" in AIScreeningEvaluationOutput.model_fields, (
            "AIScreeningEvaluationOutput should have a 'risks' field for v5.0"
        )

    @pytest.mark.xfail(reason="7R5-E: AIScreeningEvaluationOutput has no 'missing_info' field yet", strict=True)
    def test_ai_output_has_no_missing_info(self) -> None:
        """v5.0 reports need a 'missing_info' section for information that
        could not be determined from the resume."""
        assert "missing_info" in AIScreeningEvaluationOutput.model_fields, (
            "AIScreeningEvaluationOutput should have a 'missing_info' field for v5.0"
        )
