"""Stage 7 v5.0 HR decision and StageHistory contract tests.

Verifies that the three-dimensional status model (AI run status, HR decision,
recruitment stage), decision transitions, stage history audit trail, and
AI-to-HR handoff contracts are in place.

These tests protect the current production contract.
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# Production imports
# ---------------------------------------------------------------------------
from app.schemas.application import HRDecision, RecruitmentStage
from app.schemas.screening import ScreeningRunStatus
from app.schemas.stage_history import (
    StageHistoryActorType,
    StageHistoryCreate,
    StageHistoryRead,
)
from app.models.stage_history import StageHistory
from app.services.application_decision_service import ApplicationDecisionService


# ===================================================================
# A. Decision enums exist (3 tests) -- should PASS
# ===================================================================


class TestDecisionEnumsExist:
    """Verify that HR decision and recruitment stage enums contain the
    required values and that AI run status lives in a separate enum."""

    def test_hr_decision_values_include_required_set(self) -> None:
        """HRDecision must contain pending, passed, backup, rejected."""
        expected = {"pending", "passed", "backup", "rejected"}
        actual = {member.value for member in HRDecision}
        assert expected.issubset(actual), (
            f"HRDecision is missing values: {expected - actual}"
        )

    def test_recruitment_stage_values_include_required_set(self) -> None:
        """RecruitmentStage must contain applied, hr_review,
        screening_passed, backup, rejected."""
        expected = {"applied", "hr_review", "screening_passed", "backup", "rejected"}
        actual = {member.value for member in RecruitmentStage}
        assert expected.issubset(actual), (
            f"RecruitmentStage is missing values: {expected - actual}"
        )

    def test_ai_run_status_is_separate_from_hr_decision(self) -> None:
        """AI run status (ScreeningRunStatus) must be a different enum from
        HRDecision -- the two status dimensions must not be conflated."""
        assert ScreeningRunStatus is not HRDecision, (
            "ScreeningRunStatus and HRDecision must be separate enums"
        )
        # Also verify they have genuinely different member sets.
        ai_values = {m.value for m in ScreeningRunStatus}
        hr_values = {m.value for m in HRDecision}
        assert ai_values != hr_values, (
            "ScreeningRunStatus and HRDecision should have different value sets"
        )


# ===================================================================
# B. StageHistory fields (4 tests)
# ===================================================================


class TestStageHistoryFields:
    """Verify that StageHistory (schema and model) exposes the audit trail
    fields required by the v5.0 contract."""

    def test_has_before_after_stage_fields(self) -> None:
        """StageHistoryCreate must have from/to recruitment stage fields."""
        fields = StageHistoryCreate.model_fields
        assert "from_recruitment_stage" in fields, (
            "StageHistoryCreate missing from_recruitment_stage"
        )
        assert "to_recruitment_stage" in fields, (
            "StageHistoryCreate missing to_recruitment_stage"
        )

    def test_has_before_after_decision_fields(self) -> None:
        """StageHistoryCreate must have from/to HR decision fields."""
        fields = StageHistoryCreate.model_fields
        assert "from_hr_decision" in fields, (
            "StageHistoryCreate missing from_hr_decision"
        )
        assert "to_hr_decision" in fields, (
            "StageHistoryCreate missing to_hr_decision"
        )

    def test_has_actor_source_field(self) -> None:
        """StageHistoryCreate must have actor_type and actor_label fields."""
        fields = StageHistoryCreate.model_fields
        assert "actor_type" in fields, (
            "StageHistoryCreate missing actor_type"
        )
        assert "actor_label" in fields, (
            "StageHistoryCreate missing actor_label"
        )
        # Confirm the actor type enum includes HR and SYSTEM.
        actor_values = {m.value for m in StageHistoryActorType}
        assert {"hr", "system"}.issubset(actor_values)

    def test_has_report_id_field(self) -> None:
        """StageHistory audit rows should reference the screening report
        that was current at the time of the transition."""
        # Check schema first
        schema_fields = StageHistoryCreate.model_fields
        assert "report_id" in schema_fields, (
            "StageHistoryCreate missing report_id"
        )
        # Check model columns
        model_columns = {c.key for c in StageHistory.__table__.columns}
        assert "report_id" in model_columns, (
            "StageHistory model missing report_id column"
        )


# ===================================================================
# C. Decision service methods (4 tests)
# ===================================================================


class TestDecisionServiceMethods:
    """Verify ApplicationDecisionService exposes the expected decision
    methods and enforces reason-text requirements."""

    def test_has_decision_methods(self) -> None:
        """ApplicationDecisionService must expose pass, backup, reject,
        undo_rejection, and void methods."""
        service = ApplicationDecisionService
        for method_name in (
            "pass_application",
            "backup_application",
            "reject_application",
            "undo_rejection",
            "void_application",
        ):
            assert hasattr(service, method_name), (
                f"ApplicationDecisionService missing {method_name}"
            )
            assert callable(getattr(service, method_name)), (
                f"{method_name} is not callable"
            )

    def test_backup_decision_requires_reason_detail(self) -> None:
        """BackupApplicationRequest should make reason_detail required
        (not optional) so HR must always explain a backup decision."""
        from app.schemas.stage_history import BackupApplicationRequest

        field_info = BackupApplicationRequest.model_fields["reason_detail"]
        # If reason_detail allows None it is optional -- v5.0 requires it.
        assert field_info.is_required(), (
            "reason_detail should be required for backup decisions"
        )

    def test_reject_decision_requires_reason_detail(self) -> None:
        """RejectApplicationRequest should make reason_detail required
        (not optional) so HR must always explain a rejection."""
        from app.schemas.stage_history import RejectApplicationRequest

        field_info = RejectApplicationRequest.model_fields["reason_detail"]
        assert field_info.is_required(), (
            "reason_detail should be required for reject decisions"
        )

    def test_pass_decision_does_not_require_reason_detail(self) -> None:
        """PassApplicationRequest should allow reason_detail to be
        optional -- passing is a positive action that needs no justification."""
        from app.schemas.stage_history import PassApplicationRequest

        field_info = PassApplicationRequest.model_fields["reason_detail"]
        assert not field_info.is_required(), (
            "reason_detail should be optional for pass decisions"
        )


# ===================================================================
# D. AI -> HR handoff (3 tests)
# ===================================================================


class TestAIToHRHandoff:
    """Verify the v5.0 contract for AI completion automatically advancing
    the recruitment stage and HR being able to override AI."""

    def test_ai_completion_auto_advances_to_hr_review(self) -> None:
        """When an AI screening run succeeds and the application is still
        at the 'applied' stage, the system should automatically advance
        recruitment_stage to 'hr_review' without changing hr_decision."""
        service = ApplicationDecisionService
        # The service should expose a method that handles AI-triggered
        # stage advancement (e.g. on_screening_completed, advance_to_hr_review).
        ai_advance_methods = [
            name for name in dir(service)
            if "advance" in name.lower() or "screening_complete" in name.lower()
            or "on_screening" in name.lower()
        ]
        assert len(ai_advance_methods) > 0, (
            "ApplicationDecisionService needs a method to auto-advance "
            "from applied to hr_review after AI screening completes"
        )

    def test_ai_failure_does_not_block_hr_decision(self) -> None:
        """When AI screening fails, the application must remain accessible
        for HR manual decision -- AI failure must not set hr_decision to
        rejected or prevent HR from acting."""
        service = ApplicationDecisionService
        # There should be a method or documented pathway for HR to make
        # decisions on applications whose AI screening has failed.
        # The pass_application method's allowed_decisions should include
        # a state reachable after AI failure.
        source = inspect.getsource(service.pass_application)
        # In v5.0, pass_application should work even when AI has failed,
        # meaning allowed_decisions should include a state that exists
        # after AI failure. We check for an explicit handler.
        ai_failure_methods = [
            name for name in dir(service)
            if "ai_fail" in name.lower() or "screening_fail" in name.lower()
            or "manual_override" in name.lower()
        ]
        assert len(ai_failure_methods) > 0, (
            "ApplicationDecisionService needs explicit handling for "
            "HR decisions when AI screening has failed"
        )

    def test_hr_direct_pass_skips_ai(self) -> None:
        """When HR directly passes an application, the recruitment stage
        should jump to screening_passed immediately and any pending or
        future AI screening report becomes supplementary, not blocking."""
        service = ApplicationDecisionService
        # There should be a code path or method that allows HR to bypass
        # AI screening entirely and directly pass an application.
        direct_pass_methods = [
            name for name in dir(service)
            if "direct_pass" in name.lower() or "skip_ai" in name.lower()
            or "hr_override" in name.lower()
        ]
        assert len(direct_pass_methods) > 0, (
            "ApplicationDecisionService needs a method for HR direct pass "
            "that skips AI screening and sets stage to screening_passed"
        )


# ===================================================================
# E. Stage 7 boundary after the stage 9 shared contract (3 tests)
# ===================================================================


class TestStage7ScopeBoundary:
    """Verify stage 7 HR decisions remain independent after shared stage
    enums expand for stage 9, and history stays append-only."""

    def test_shared_stage_values_include_stage9_without_changing_hr_decisions(self) -> None:
        """The shared Application enum now includes stage 9 nodes while the
        stage 7 HR decision enum remains the original independent dimension."""
        stage_values = {member.value for member in RecruitmentStage}
        assert {
            "interview",
            "offer",
            "offer_accepted",
            "admitted",
            "hired",
        }.issubset(stage_values)
        assert {member.value for member in HRDecision} == {
            "pending",
            "passed",
            "backup",
            "rejected",
        }

    def test_stage_history_is_append_only(self) -> None:
        """StageHistory model should be append-only -- the service must
        not expose update or delete operations on history rows."""
        service = ApplicationDecisionService
        public_methods = [
            name for name in dir(service)
            if not name.startswith("_") and callable(getattr(service, name))
        ]
        mutation_keywords = {"update_history", "delete_history", "remove_history", "edit_history"}
        violating = [m for m in public_methods if m in mutation_keywords]
        assert not violating, (
            f"StageHistory must be append-only but found mutation methods: {violating}"
        )

    def test_history_preserves_chronological_order(self) -> None:
        """The list_history method must return records ordered by
        created_at (chronological order)."""
        source = inspect.getsource(ApplicationDecisionService.list_history)
        assert "order_by" in source, (
            "list_history must use order_by to guarantee chronological order"
        )
        assert "created_at" in source, (
            "list_history must order by created_at for chronological order"
        )
