"""v5.0 report scoring, evidence, safety, and direction-consistency contracts.

Tests are organized into six groups:

A. No weight fields -- static proof that 5.0 schemas carry no weighting logic.
B. Display label ranges -- the label function already maps scores correctly.
C. Direction contradiction detection -- 5.0 validators not yet implemented.
D. 5.0 report structure fields -- structured sections not yet on the schema.
E. Evidence contract -- 5.0 evidence enforcement not yet implemented.
F. Report safety -- schemas already forbid unsafe fields and extra data.
"""

from __future__ import annotations

import inspect

import pytest

from app.schemas.screening_evaluation import (
    AIScreeningEvaluationOutput,
    RequirementAssessment,
    ScreeningEvidence,
)
from app.schemas.screening import ScreeningReportRead
from app.services.screening_evaluation_service import ScreeningEvaluationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _field_names(model_cls: type) -> set[str]:
    """Return the set of field names declared on a Pydantic model."""
    return set(model_cls.model_fields.keys())


def _all_field_names(model_cls: type) -> list[str]:
    """Return all field names declared on a Pydantic model as a sorted list."""
    return sorted(model_cls.model_fields.keys())


# ===========================================================================
# A. No weight fields (3 tests) -- static proof, should PASS
# ===========================================================================


class TestNoWeightFields:
    """v5.0 contract: no weight/weights/weighted_score fields in runtime schemas.

    Python does NOT calculate average or weighted total; the AI directly gives
    the overall 0-100 score.  These tests statically verify that none of the
    three core screening schemas expose any weighting concept.
    """

    def test_ai_screening_evaluation_output_has_no_weight_field(self) -> None:
        """AIScreeningEvaluationOutput must not contain any field whose name
        includes 'weight' (e.g. weight, weights, weighted_score)."""
        weight_fields = [
            name for name in _all_field_names(AIScreeningEvaluationOutput)
            if "weight" in name.lower()
        ]
        assert weight_fields == [], (
            f"AIScreeningEvaluationOutput has weight-related fields: {weight_fields}"
        )

    def test_requirement_assessment_has_no_weight_field(self) -> None:
        """RequirementAssessment must not contain any field whose name
        includes 'weight'."""
        weight_fields = [
            name for name in _all_field_names(RequirementAssessment)
            if "weight" in name.lower()
        ]
        assert weight_fields == [], (
            f"RequirementAssessment has weight-related fields: {weight_fields}"
        )

    def test_screening_report_read_has_no_weight_field(self) -> None:
        """ScreeningReportRead must not contain any field whose name
        includes 'weight'."""
        weight_fields = [
            name for name in _all_field_names(ScreeningReportRead)
            if "weight" in name.lower()
        ]
        assert weight_fields == [], (
            f"ScreeningReportRead has weight-related fields: {weight_fields}"
        )


# ===========================================================================
# B. Display label ranges (5 tests) -- should PASS (labels already exist)
# ===========================================================================


class TestDisplayLabelRanges:
    """v5.0 display labels:
        0-29  -> 关联较弱
        30-49 -> 存在明显差距
        50-69 -> 部分匹配
        70-84 -> 整体较匹配
        85-100 -> 高度匹配
    """

    _label_fn = staticmethod(ScreeningEvaluationService.display_label_for_score)

    def test_score_0_to_29_returns_weak_relevance(self) -> None:
        """Scores 0-29 must produce label '关联较弱'."""
        for score in (0, 15, 29):
            assert self._label_fn(score) == "关联较弱", f"score={score}"

    def test_score_30_to_49_returns_significant_gap(self) -> None:
        """Scores 30-49 must produce label '存在明显差距'."""
        for score in (30, 40, 49):
            assert self._label_fn(score) == "存在明显差距", f"score={score}"

    def test_score_50_to_69_returns_partial_match(self) -> None:
        """Scores 50-69 must produce label '部分匹配'."""
        for score in (50, 60, 69):
            assert self._label_fn(score) == "部分匹配", f"score={score}"

    def test_score_70_to_84_returns_overall_match(self) -> None:
        """Scores 70-84 must produce label '整体较匹配'."""
        for score in (70, 77, 84):
            assert self._label_fn(score) == "整体较匹配", f"score={score}"

    def test_score_85_to_100_returns_high_match(self) -> None:
        """Scores 85-100 must produce label '高度匹配'."""
        for score in (85, 92, 100):
            assert self._label_fn(score) == "高度匹配", f"score={score}"


# ===========================================================================
# C. Direction contradiction detection (6 tests) -- 7R5-E
# ===========================================================================


class TestDirectionContradictionDetection:
    """v5.0 requires dedicated validation functions that detect and reject
    direction contradictions between scores and textual assessments.

    The current v4.0 service already performs some of this validation via
    _validate_score_reason_direction and _validate_safety_and_consistency,
    but v5.0 needs these as explicit, standalone, public-facing contract
    validators that can be invoked and tested independently.

    These tests assert that the specific v5.0 contradiction-check methods
    do not exist yet, proving the gap that v5.0 must fill.
    """

    @pytest.mark.xfail(reason="7R5-E: v5.0 dedicated high-score-no-evidence validator not yet implemented", strict=True)
    def test_validate_high_score_no_evidence_method_exists(self) -> None:
        """v5.0 must have a dedicated method to reject score 7-10 when
        evidence says 'not found'."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_high_score_no_evidence")

    @pytest.mark.xfail(reason="7R5-E: v5.0 dedicated low-score-full-match validator not yet implemented", strict=True)
    def test_validate_low_score_full_match_method_exists(self) -> None:
        """v5.0 must have a dedicated method to reject score 0-3 when
        reason says 'fully satisfies'."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_low_score_full_match")

    @pytest.mark.xfail(reason="7R5-E: v5.0 dedicated overall-high-mismatch validator not yet implemented", strict=True)
    def test_validate_overall_high_but_mismatch_method_exists(self) -> None:
        """v5.0 must have a dedicated method to reject overall 70-100 when
        summary says 'obviously does not match'."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_overall_high_mismatch")

    @pytest.mark.xfail(reason="7R5-E: v5.0 dedicated overall-low-high-match validator not yet implemented", strict=True)
    def test_validate_overall_low_but_high_match_method_exists(self) -> None:
        """v5.0 must have a dedicated method to reject overall 0-49 when
        summary says 'highly matching'."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_overall_low_high_match")

    @pytest.mark.xfail(reason="7R5-E: v5.0 dedicated required-low-overall-high tradeoff validator not yet implemented", strict=True)
    def test_validate_required_low_overall_high_tradeoff_method_exists(self) -> None:
        """v5.0 must have a dedicated method to require an explicit
        risk/tradeoff explanation when a required item scores 0-3 and
        overall >= 70."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_required_low_tradeoff")

    @pytest.mark.xfail(reason="7R5-E: v5.0 contradiction check methods not yet added to service", strict=True)
    def test_v5_contradiction_validators_are_registered(self) -> None:
        """v5.0 must expose a list or registry of all contradiction-check
        validators on the service class."""
        v5_methods = [
            name for name in dir(ScreeningEvaluationService)
            if name.startswith("validate_v5_")
        ]
        assert len(v5_methods) >= 5, (
            f"Expected at least 5 v5 contradiction validators, found: {v5_methods}"
        )


# ===========================================================================
# D. 5.0 report structure fields missing (5 tests) -- 7R5-E
# ===========================================================================


class TestV5ReportStructureFieldsMissing:
    """v5.0 replaces free-form bonus_highlights with structured report
    sections: strengths, gaps, risks_or_conflicts, missing_info.

    These tests confirm these fields do not exist yet on
    AIScreeningEvaluationOutput, proving the gap that v5.0 must fill.
    """

    @pytest.mark.xfail(reason="7R5-E: v5.0 structured 'strengths' field not yet added", strict=True)
    def test_ai_output_has_strengths_field(self) -> None:
        """v5.0 report must include a structured 'strengths' section."""
        assert "strengths" in _field_names(AIScreeningEvaluationOutput)

    @pytest.mark.xfail(reason="7R5-E: v5.0 structured 'gaps' field not yet added", strict=True)
    def test_ai_output_has_gaps_field(self) -> None:
        """v5.0 report must include a structured 'gaps' section."""
        assert "gaps" in _field_names(AIScreeningEvaluationOutput)

    @pytest.mark.xfail(reason="7R5-E: v5.0 structured 'risks_or_conflicts' field not yet added", strict=True)
    def test_ai_output_has_risks_or_conflicts_field(self) -> None:
        """v5.0 report must include a structured 'risks_or_conflicts' section."""
        assert "risks_or_conflicts" in _field_names(AIScreeningEvaluationOutput)

    @pytest.mark.xfail(reason="7R5-E: v5.0 structured 'missing_info' field not yet added", strict=True)
    def test_ai_output_has_missing_info_field(self) -> None:
        """v5.0 report must include a structured 'missing_info' section."""
        assert "missing_info" in _field_names(AIScreeningEvaluationOutput)

    def test_bonus_highlights_is_current_mechanism(self) -> None:
        """v4.0 uses bonus_highlights as the unstructured mechanism.
        v5.0 will replace this with structured sections.  This test
        confirms the current mechanism is still in place."""
        assert "bonus_highlights" in _field_names(AIScreeningEvaluationOutput), (
            "bonus_highlights must exist in v4.0 AIScreeningEvaluationOutput"
        )


# ===========================================================================
# E. Evidence contract (4 tests) -- 7R5-E
# ===========================================================================


class TestEvidenceContract:
    """v5.0 evidence contract rules:
    - Non-zero score MUST have current resume evidence.
    - Zero score reason must say '当前简历未发现证据', not '候选人不会'.
    - Cross-reference validation: criterion_id vs plan criteria.

    These tests confirm the v5.0-specific enforcement does not exist yet.
    """

    @pytest.mark.xfail(reason="7R5-E: v5.0 will enforce non-zero score requires evidence at schema level", strict=True)
    def test_requirement_assessment_rejects_empty_evidence_with_nonzero_score(self) -> None:
        """v5.0 schema must reject a RequirementAssessment with score > 0
        and empty evidence list at Pydantic validation time.

        Current v4.0 allows construction (service validates later), so
        this test proves the schema-level gap."""
        assessment = RequirementAssessment(
            requirement_key="test-key",
            score=5,
            reason="Some reason text here",
            evidence=[],
        )
        # If we get here, schema allowed it -- v5.0 should not
        pytest.fail(
            "v5.0 must reject empty evidence for non-zero score at schema level"
        )

    @pytest.mark.xfail(reason="7R5-E: v5.0 evidence validator function not yet implemented", strict=True)
    def test_v5_evidence_validator_exists(self) -> None:
        """v5.0 must have a dedicated evidence validation function that
        enforces the non-zero-score-needs-evidence rule."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_evidence_required")

    @pytest.mark.xfail(reason="7R5-E: v5.0 zero-score reason validator not yet implemented", strict=True)
    def test_v5_zero_score_reason_validator_exists(self) -> None:
        """v5.0 must have a validator ensuring zero-score reasons say
        '当前简历未发现证据' rather than asserting candidate inability."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_zero_score_reason")

    @pytest.mark.xfail(reason="7R5-E: v5.0 criterion cross-reference validator not yet implemented", strict=True)
    def test_v5_criterion_cross_reference_validator_exists(self) -> None:
        """v5.0 must validate that each assessment's criterion_id matches
        a criterion in the evaluation plan, not legacy requirement_key/fact_id."""
        assert hasattr(ScreeningEvaluationService, "validate_v5_criterion_cross_reference")


# ===========================================================================
# F. Report safety (3 tests) -- should partially pass
# ===========================================================================


class TestReportSafety:
    """Safety contracts that the screening schemas must uphold.

    The current schemas already forbid extra fields and do not include
    decision or sensitive-attribute fields.
    """

    def test_ai_output_has_no_decision_or_recommendation_field(self) -> None:
        """AIScreeningEvaluationOutput must not have any field that implies
        an auto-pass/fail/reject decision or recommendation.

        Prohibited field name fragments: decision, recommendation,
        auto_pass, auto_reject, auto_fail."""
        prohibited_fragments = ("decision", "recommendation", "auto_pass", "auto_reject", "auto_fail")
        unsafe_fields = [
            name for name in _all_field_names(AIScreeningEvaluationOutput)
            if any(fragment in name.lower() for fragment in prohibited_fragments)
        ]
        assert unsafe_fields == [], (
            f"AIScreeningEvaluationOutput has decision-like fields: {unsafe_fields}"
        )

    def test_ai_output_forbids_extra_fields(self) -> None:
        """AIScreeningEvaluationOutput must use extra='forbid' so the model
        cannot sneak in undeclared fields like 'decision' or 'auto_pass'."""
        config = AIScreeningEvaluationOutput.model_config
        assert config.get("extra") == "forbid", (
            "AIScreeningEvaluationOutput must set extra='forbid' to prevent "
            "undeclared fields from model output"
        )

    def test_ai_output_has_no_sensitive_attribute_field(self) -> None:
        """AIScreeningEvaluationOutput must not have any field related to
        sensitive personal attributes that are prohibited in recruitment
        evaluation.

        Prohibited field name fragments: gender, sex, age, ethnicity,
        marital, sensitive_attribute, race, religion, nationality."""
        prohibited_fragments = (
            "gender", "sex", "age", "ethnicity", "marital",
            "sensitive_attribute", "race", "religion", "nationality",
        )
        unsafe_fields = [
            name for name in _all_field_names(AIScreeningEvaluationOutput)
            if any(fragment in name.lower() for fragment in prohibited_fragments)
        ]
        assert unsafe_fields == [], (
            f"AIScreeningEvaluationOutput has sensitive-attribute fields: {unsafe_fields}"
        )
