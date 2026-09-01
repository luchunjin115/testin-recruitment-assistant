"""v5.0 AI screening operations contract tests.

Tests are organized by responsibility:

- A. Batch limit: v5.0 limit is 5
- B. v5.0 plan gate: screening must require a v5.0-ready plan
- C. Pre-run checks: service validates Application, Resume, plan, concurrency
- D. Idempotency: same fingerprint reuses result, force re-evaluate needs confirmation
- E. Concurrency protection: at most one non-terminal run per Application
- F. Status enums completeness: all required states, waiting reasons, outdated reasons

These tests protect the current production contract.
"""

from __future__ import annotations

import inspect

import pytest

from app.schemas.screening import (
    ScreeningBatchReassessmentRequest,
    ScreeningBatchReassessmentRead,
    ScreeningOutdatedReason,
    ScreeningRunStatus,
    ScreeningRunTriggerType,
    ScreeningWaitingReason,
)
from app.services.screening_service import (
    ScreeningBatchLimitError,
    ScreeningService,
)


# ---------------------------------------------------------------------------
# A. Batch limit (4 tests)
# ---------------------------------------------------------------------------


class TestBatchLimit:
    """v5.0 batch reassessment is capped at five Applications."""

    def test_batch_schema_max_is_5(self) -> None:
        field_info = ScreeningBatchReassessmentRequest.model_fields["application_ids"]
        assert field_info.metadata is not None
        # Pydantic stores max_length on the field or via annotated metadata.
        max_len = getattr(field_info, "max_length", None)
        if max_len is None:
            for meta in field_info.metadata:
                if hasattr(meta, "max_length"):
                    max_len = meta.max_length
                    break
        assert max_len == 5

    def test_batch_response_max_is_5(self) -> None:
        field_info = ScreeningBatchReassessmentRead.model_fields["results"]
        max_len = getattr(field_info, "max_length", None)
        if max_len is None:
            for meta in field_info.metadata:
                if hasattr(meta, "max_length"):
                    max_len = meta.max_length
                    break
        assert max_len == 5

    def test_batch_reassessment_rejects_duplicates(self) -> None:
        """Duplicate application_ids are rejected at schema level."""
        with pytest.raises(Exception):
            ScreeningBatchReassessmentRequest(application_ids=[1, 1])

    def test_batch_method_exists(self) -> None:
        """ScreeningService has a trigger_batch_reassessment method."""
        assert hasattr(ScreeningService, "trigger_batch_reassessment")
        assert callable(getattr(ScreeningService, "trigger_batch_reassessment"))

    def test_service_batch_limit_enforces_upper_bound(self) -> None:
        """trigger_batch_reassessment checks len(application_ids) <= 5."""
        source = inspect.getsource(ScreeningService.trigger_batch_reassessment)
        assert "<= 5" in source


# ---------------------------------------------------------------------------
# B. v5.0 plan gate (3 tests)
# ---------------------------------------------------------------------------


class TestPlanGate:
    """Screening currently requires a v4.0-ready plan.
    v5.0 should introduce a v5.0 plan gate."""

    def test_current_plan_gate_requires_v4(self) -> None:
        """_classify_v4_plan enforces schema_version == '4.0'."""
        source = inspect.getsource(ScreeningService._classify_v4_plan)
        assert "4.0" in source, (
            "Current plan gate must check for schema_version '4.0'"
        )

    def test_v5_plan_gate_exists(self) -> None:
        """A v5.0 plan classification method should exist."""
        # v5.0 needs either _classify_v5_plan or an updated gate accepting "5.0".
        has_v5_classifier = hasattr(ScreeningService, "_classify_v5_plan")
        if not has_v5_classifier:
            # Check if the existing classifier accepts "5.0"
            source = inspect.getsource(ScreeningService._classify_v4_plan)
            has_v5_classifier = "5.0" in source
        assert has_v5_classifier, (
            "v5.0 requires a plan classification that accepts schema_version '5.0'"
        )

    def test_v5_schema_version_not_accepted_by_build_context(self) -> None:
        """_build_context should route to a v5.0 plan gate when schema_version is '5.0'."""
        source = inspect.getsource(ScreeningService._build_context)
        assert "5.0" in source, (
            "_build_context must handle schema_version '5.0' plans"
        )


# ---------------------------------------------------------------------------
# C. Pre-run checks existence (4 tests)
# ---------------------------------------------------------------------------


class TestPreRunChecks:
    """Verify that ScreeningService validates preconditions before starting a run."""

    def test_trigger_checks_application_lifecycle_status(self) -> None:
        """trigger() rejects non-active Applications."""
        source = inspect.getsource(ScreeningService.trigger)
        assert "lifecycle_status" in source, (
            "trigger must check Application.lifecycle_status"
        )
        assert "active" in source, (
            "trigger must only allow 'active' Applications"
        )

    def test_trigger_checks_concurrent_run(self) -> None:
        """trigger() checks for existing non-terminal runs before creating a new one."""
        source = inspect.getsource(ScreeningService.trigger)
        assert "_find_nonterminal_run" in source, (
            "trigger must check for existing non-terminal runs"
        )

    def test_single_screening_method_exists(self) -> None:
        """ScreeningService has a trigger method for single-candidate screening."""
        method = getattr(ScreeningService, "trigger", None)
        assert method is not None
        sig = inspect.signature(method)
        assert "application_id" in sig.parameters, (
            "trigger must accept application_id"
        )

    def test_batch_screening_method_exists(self) -> None:
        """ScreeningService has a trigger_batch_reassessment method for batch screening."""
        method = getattr(ScreeningService, "trigger_batch_reassessment", None)
        assert method is not None
        sig = inspect.signature(method)
        assert "application_ids" in sig.parameters, (
            "trigger_batch_reassessment must accept application_ids"
        )


# ---------------------------------------------------------------------------
# D. Idempotency contract (3 tests)
# ---------------------------------------------------------------------------


class TestIdempotencyContract:
    """Idempotency: same input_fingerprint reuses results.
    Force re-evaluate bypasses fingerprint match."""

    def test_input_fingerprint_reuse_in_trigger(self) -> None:
        """trigger() compares input_fingerprint to reuse existing report."""
        source = inspect.getsource(ScreeningService.trigger)
        assert "input_fingerprint" in source, (
            "trigger must reference input_fingerprint for idempotency"
        )
        assert "reused_report" in source, (
            "trigger must return reused_report when fingerprint matches"
        )

    def test_force_parameter_exists(self) -> None:
        """trigger() has a force parameter to bypass fingerprint match."""
        sig = inspect.signature(ScreeningService.trigger)
        assert "force" in sig.parameters, (
            "trigger must accept a force parameter for re-evaluation"
        )

    def test_force_reevaluate_requires_hr_confirmation(self) -> None:
        """v5.0 force re-evaluate should require explicit HR confirmation token.

        Currently force=True bypasses without confirmation. v5.0 should add
        a confirmation mechanism (e.g. a confirmation_token parameter or
        a two-step process) to prevent accidental re-evaluations.
        """
        sig = inspect.signature(ScreeningService.trigger)
        assert "confirmed" in sig.parameters


# ---------------------------------------------------------------------------
# E. Concurrency protection (3 tests)
# ---------------------------------------------------------------------------


class TestConcurrencyProtection:
    """At most one non-terminal run per Application."""

    def test_nonterminal_status_set_defined(self) -> None:
        """ScreeningService defines a set of non-terminal statuses."""
        nonterminal = ScreeningService._NONTERMINAL_STATUSES
        assert isinstance(nonterminal, tuple)
        assert len(nonterminal) >= 3, (
            "At least 3 non-terminal statuses expected"
        )
        # Terminal statuses should NOT be in the set
        assert ScreeningRunStatus.SUCCEEDED.value not in nonterminal
        assert ScreeningRunStatus.FAILED.value not in nonterminal

    def test_terminal_states_exist(self) -> None:
        """ScreeningRunStatus has terminal states: succeeded and failed."""
        terminal = {ScreeningRunStatus.SUCCEEDED, ScreeningRunStatus.FAILED}
        all_statuses = set(ScreeningRunStatus)
        assert terminal.issubset(all_statuses), (
            "succeeded and failed must exist as terminal states"
        )

    def test_stale_input_detection_in_execute_run(self) -> None:
        """execute_run fails when input changed during the run."""
        source = inspect.getsource(ScreeningService.execute_run)
        assert "input_fingerprint" in source, (
            "execute_run must compare input fingerprints"
        )
        assert "SCREENING_INPUT_OUTDATED_DURING_RUN" in source, (
            "execute_run must fail with SCREENING_INPUT_OUTDATED_DURING_RUN"
        )

    def test_stale_input_detection_in_save_success(self) -> None:
        """_save_success fails when input changed between run start and completion."""
        source = inspect.getsource(ScreeningService._save_success)
        assert "input_fingerprint" in source, (
            "_save_success must compare input fingerprints"
        )
        assert "SCREENING_INPUT_OUTDATED_DURING_RUN" in source, (
            "_save_success must fail with SCREENING_INPUT_OUTDATED_DURING_RUN "
            "when inputs changed after model call"
        )


# ---------------------------------------------------------------------------
# F. Status enums completeness (3 tests)
# ---------------------------------------------------------------------------


class TestStatusEnumsCompleteness:
    """Verify that screening status enums have all required members."""

    def test_screening_run_status_has_required_states(self) -> None:
        """ScreeningRunStatus must include all operational states."""
        required = {
            "waiting_resume",
            "waiting_plan",
            "queued",
            "running",
            "succeeded",
            "failed",
        }
        actual = {member.value for member in ScreeningRunStatus}
        missing = required - actual
        assert not missing, f"ScreeningRunStatus missing states: {missing}"

    def test_screening_waiting_reason_exists(self) -> None:
        """ScreeningWaitingReason enum exists with plan-related reasons."""
        required = {
            "plan_missing",
            "plan_generating",
            "plan_pending_confirmation",
            "plan_failed",
            "plan_outdated",
        }
        actual = {member.value for member in ScreeningWaitingReason}
        missing = required - actual
        assert not missing, f"ScreeningWaitingReason missing: {missing}"

    def test_screening_outdated_reason_exists(self) -> None:
        """ScreeningOutdatedReason enum exists with input-change reasons."""
        required = {
            "resume_changed",
            "jd_changed",
            "evaluation_plan_changed",
        }
        actual = {member.value for member in ScreeningOutdatedReason}
        missing = required - actual
        assert not missing, f"ScreeningOutdatedReason missing: {missing}"
