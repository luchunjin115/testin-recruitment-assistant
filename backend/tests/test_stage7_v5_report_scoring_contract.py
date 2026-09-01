"""v5.0 report scoring, evidence, safety, and Service-boundary contracts.

Tests are organized into six groups:

A. No weight fields -- static proof that 5.0 schemas carry no weighting logic.
B. Display label ranges -- the label function already maps scores correctly.
C. Semantic direction judgments stay outside the 5.0 Service.
D. 5.0 report structure fields.
E. Evidence contract.
F. Report safety -- schemas already forbid unsafe fields and extra data.
"""

from __future__ import annotations

import pytest

from app.schemas.screening_evaluation import (
    AIScreeningEvaluationV5Output,
    AIScreeningEvaluationOutput,
    CriterionAssessment,
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
            name for name in _all_field_names(AIScreeningEvaluationV5Output)
            if "weight" in name.lower()
        ]
        assert weight_fields == [], (
            f"AIScreeningEvaluationOutput has weight-related fields: {weight_fields}"
        )

    def test_requirement_assessment_has_no_weight_field(self) -> None:
        """RequirementAssessment must not contain any field whose name
        includes 'weight'."""
        weight_fields = [
            name for name in _all_field_names(CriterionAssessment)
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
# C. Semantic direction judgments are not Service hard gates -- CLOSE-05D
# ===========================================================================


class TestDirectionContradictionDetection:
    """Free-text score direction and tradeoff quality belong to HR/I3 review."""

    @pytest.mark.parametrize(
        "method_name",
        (
            "validate_v5_high_score_no_evidence",
            "validate_v5_low_score_full_match",
            "validate_v5_overall_high_mismatch",
            "validate_v5_overall_low_high_match",
            "validate_v5_required_low_tradeoff",
        ),
    )
    def test_v5_semantic_contradiction_judges_do_not_exist(
        self,
        method_name: str,
    ) -> None:
        assert not hasattr(ScreeningEvaluationService, method_name)

    def test_v5_contradiction_validators_are_registered(self) -> None:
        """Only deterministic cross-reference/evidence validators stay public."""
        v5_methods = {
            name for name in dir(ScreeningEvaluationService)
            if name.startswith("validate_v5_")
        }
        assert v5_methods == {"validate_v5_criterion_cross_reference"}


# ===========================================================================
# D. 5.0 report structure fields missing (5 tests) -- 7R5-E
# ===========================================================================


class TestV5ReportStructureFieldsMissing:
    """v5.0 replaces free-form bonus_highlights with structured report
    sections: strengths, gaps, risks_or_conflicts, missing_info.

    These tests confirm these fields do not exist yet on
    AIScreeningEvaluationOutput, proving the gap that v5.0 must fill.
    """

    def test_ai_output_has_strengths_field(self) -> None:
        """v5.0 report must include a structured 'strengths' section."""
        assert "strengths" in _field_names(AIScreeningEvaluationV5Output)

    def test_ai_output_has_gaps_field(self) -> None:
        """v5.0 report must include a structured 'gaps' section."""
        assert "gaps" in _field_names(AIScreeningEvaluationV5Output)

    def test_ai_output_has_risks_or_conflicts_field(self) -> None:
        """v5.0 report must include a structured 'risks_or_conflicts' section."""
        assert "risks_or_conflicts" in _field_names(AIScreeningEvaluationV5Output)

    def test_ai_output_has_missing_info_field(self) -> None:
        """v5.0 report must include a structured 'missing_info' section."""
        assert "missing_info" in _field_names(AIScreeningEvaluationV5Output)

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
    - Non-zero score MUST have at least one AI-generated basis.
    - Zero score may have an empty or non-empty evidence list.
    - Every score must have a non-empty reason.
    - Cross-reference validation: criterion_id vs plan criteria.

    These tests confirm the deterministic v5.0 enforcement boundary.
    """

    def test_requirement_assessment_rejects_empty_evidence_with_nonzero_score(self) -> None:
        """v5.0 schema must reject a RequirementAssessment with score > 0
        and empty evidence list at Pydantic validation time.

        Current v4.0 allows construction (service validates later), so
        this test proves the schema-level gap."""
        with pytest.raises(ValueError):
            CriterionAssessment(
                criterion_id="criterion:0001",
                score=5,
                reason="Some reason text here",
                evidence=[],
            )

    def test_v5_evidence_content_validator_does_not_exist(self) -> None:
        """The Schema owns presence; Service must not judge evidence content."""
        assert not hasattr(ScreeningEvaluationService, "validate_v5_evidence_required")

    def test_v5_zero_score_semantic_reason_validator_does_not_exist(self) -> None:
        assert not hasattr(ScreeningEvaluationService, "validate_v5_zero_score_reason")

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
            name for name in _all_field_names(AIScreeningEvaluationV5Output)
            if any(fragment in name.lower() for fragment in prohibited_fragments)
        ]
        assert unsafe_fields == [], (
            f"AIScreeningEvaluationOutput has decision-like fields: {unsafe_fields}"
        )

    def test_ai_output_forbids_extra_fields(self) -> None:
        """AIScreeningEvaluationOutput must use extra='forbid' so the model
        cannot sneak in undeclared fields like 'decision' or 'auto_pass'."""
        config = AIScreeningEvaluationV5Output.model_config
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
            name for name in _all_field_names(AIScreeningEvaluationV5Output)
            if any(fragment in name.lower() for fragment in prohibited_fragments)
        ]
        assert unsafe_fields == [], (
            f"AIScreeningEvaluationOutput has sensitive-attribute fields: {unsafe_fields}"
        )
