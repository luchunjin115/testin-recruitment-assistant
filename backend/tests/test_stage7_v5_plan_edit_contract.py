"""Current v5.0 plan editing, confirmation, versioning and gate contracts."""

from __future__ import annotations

import inspect

import pytest

from app.models.job_evaluation_plan import JobEvaluationPlan
from app.schemas.job_evaluation_plan import (
    JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
    JobEvaluationPlanStatus,
)
from app.services.job_evaluation_plan_service import (
    JobEvaluationPlanService,
    JobEvaluationPlanServiceError,
    job_evaluation_plan_service,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICE_METHODS = set(dir(JobEvaluationPlanService))


def _has_method(name: str) -> bool:
    """Return True if *name* is a callable public method on the service class."""
    attr = getattr(JobEvaluationPlanService, name, None)
    return attr is not None and callable(attr)


def _has_column(name: str) -> bool:
    """Return True if the SQLAlchemy model exposes *name* as a mapped column."""
    return hasattr(JobEvaluationPlan, name) and hasattr(
        getattr(JobEvaluationPlan, name, None), "property"
    )


# ===================================================================
# A. Plan editing methods (6 tests)
# ===================================================================


class TestEditingMethods:
    """HR can edit individual criteria before confirming a v5.0 plan."""

    def test_edit_plan_criteria_exists(self) -> None:
        """Bulk criterion edits are available."""
        assert _has_method("edit_plan_criteria")

    def test_add_criterion_exists(self) -> None:
        """HR can add a criterion with origin=hr_added."""
        assert _has_method("add_criterion")

    def test_delete_criterion_exists(self) -> None:
        """HR can remove a criterion."""
        assert _has_method("delete_criterion")

    def test_merge_criteria_exists(self) -> None:
        """HR can merge criteria."""
        assert _has_method("merge_criteria")

    def test_update_criterion_importance_exists(self) -> None:
        """HR can change criterion importance."""
        assert _has_method("update_criterion_importance")

    def test_save_draft_exists(self) -> None:
        """HR can save a pending_confirmation draft."""
        assert _has_method("save_draft")


# ===================================================================
# B. Version and concurrency (4 tests)
# ===================================================================


class TestVersionConcurrency:
    """v5.0 requires optimistic concurrency control so that two HR users
    editing the same plan at the same time get a clear conflict error
    instead of a silent last-write-wins overwrite."""

    def test_check_edit_version_conflict_exists(self) -> None:
        """Concurrent edits have an explicit conflict check."""
        assert _has_method("check_edit_version_conflict")

    def test_model_has_edit_version_column(self) -> None:
        """The model exposes edit_version for optimistic locking."""
        assert _has_column("edit_version")

    def test_model_has_confirmed_at_column(self) -> None:
        """confirmed_at is distinct from AI generation completed_at."""
        assert _has_column("confirmed_at")

    def test_plan_edit_conflict_error_exists(self) -> None:
        """Optimistic-lock conflicts use a dedicated error."""
        from app.services.job_evaluation_plan_service import PlanEditConflictError  # noqa: F811
        assert issubclass(PlanEditConflictError, JobEvaluationPlanServiceError)


# ===================================================================
# C. Version immutability (3 tests)
# ===================================================================


class TestVersionImmutability:
    """Once a plan version has been confirmed and referenced by screening
    reports, it must not be mutated in place.  v5.0 must create a new
    version instead."""

    def test_create_new_version_from_confirmed_exists(self) -> None:
        """A confirmed plan can be forked without mutating the original."""
        assert _has_method("create_new_version_from_confirmed")

    def test_confirmed_plan_version_fork_mechanism(self) -> None:
        """The service exposes a public version-fork method."""
        fork_candidates = [
            name
            for name in dir(JobEvaluationPlanService)
            if not name.startswith("_")
            and callable(getattr(JobEvaluationPlanService, name))
            and "version" in name.lower()
            and "confirm" not in name.lower()
        ]
        assert len(fork_candidates) > 0, "no version-fork method found"

    def test_schema_version_5_0_is_supported(self) -> None:
        """The current schema exposes the persisted v5.0 contract version."""
        from app.schemas.job_evaluation_plan import JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION  # noqa: F811
        assert JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION == "5.0"


# ===================================================================
# D. JD expiration semantics (3 tests)
# ===================================================================


class TestJDExpirationSemantics:
    """Evaluation-relevant JD changes expire plans; display notes do not."""

    def test_mark_outdated_method_exists(self) -> None:
        """``mark_current_plan_outdated_if_input_changed`` is the v4.0
        mechanism for expiring a plan after a JD edit.  It must exist today."""
        assert _has_method("mark_current_plan_outdated_if_input_changed")

    def test_public_notes_not_in_evaluation_snapshot(self) -> None:
        """``public_notes`` is a non-evaluation field.  Changing it must NOT
        cause plan expiration.  The v4.0 input snapshot already excludes it:
        ``build_v4_input_snapshot`` only reads title, department,
        job_background, job_responsibilities, candidate_requirements,
        preferred_qualifications.  If ``public_notes`` appeared in the
        snapshot, its fingerprint would change and the plan would expire."""
        source = inspect.getsource(JobEvaluationPlanService.build_v4_input_snapshot)
        assert "public_notes" not in source, (
            "public_notes must NOT appear in the v4 input snapshot builder"
        )

    def test_candidate_requirements_in_evaluation_snapshot(self) -> None:
        """``candidate_requirements`` is a core evaluation field.  Changing it
        MUST cause plan expiration.  The v4.0 input snapshot includes it in
        ``evaluation_fields``, so the fingerprint will change and the plan
        will be marked outdated."""
        source = inspect.getsource(JobEvaluationPlanService.build_v4_input_snapshot)
        assert "candidate_requirements" in source, (
            "candidate_requirements must appear in the v4 input snapshot builder"
        )


# ===================================================================
# E. 5.0 gate for screening (3 tests)
# ===================================================================


class TestScreeningGate:
    """The service keeps v4 compatibility and uses a dedicated v5 gate."""

    def test_current_screening_gate_requires_4_0(self) -> None:
        """The screening readiness classifier rejects plans whose
        ``schema_version`` is not '4.0'.  This is the existing v4.0 gate
        and must work today."""
        from app.services.screening_service import ScreeningService

        source = inspect.getsource(ScreeningService._classify_v4_plan)
        # The method checks: if current.schema_version != "4.0"
        assert '"4.0"' in source, (
            "screening gate must reference schema_version 4.0"
        )

    def test_v5_screening_gate_method_exists(self) -> None:
        """v5.0 screening uses a dedicated plan classifier."""
        from app.services.screening_service import ScreeningService

        v5_methods = [
            name
            for name in dir(ScreeningService)
            if "v5" in name.lower() and "plan" in name.lower()
        ]
        assert len(v5_methods) > 0, "no v5 plan classifier found on ScreeningService"

    def test_schema_version_5_0_would_pass_screening_gate(self) -> None:
        """The v5 classifier accepts schema_version 5.0."""
        from app.services.screening_service import ScreeningService

        source = inspect.getsource(ScreeningService._classify_v5_plan)
        assert '"5.0"' in source, (
            "screening gate must accept schema_version 5.0 for v5 plans"
        )


# ===================================================================
# F. Read-only history (2 tests) — should pass today
# ===================================================================


class TestReadOnlyHistory:
    """Legacy plan versions (1.0 through 3.0) are read-only artefacts.
    The service correctly flags them as contract-outdated, preventing
    them from being used for new screening or confirmation."""

    @pytest.mark.parametrize("version", ["1.0", "2.0", "3.0"])
    def test_legacy_plans_are_contract_outdated(self, version: str) -> None:
        """Plans with schema_version in {1.0, 2.0, 3.0} must be flagged as
        contract-outdated by ``is_contract_outdated``, making them read-only.
        The current contract versions are 3.0 and 4.0; anything older is
        stale."""
        plan = JobEvaluationPlan()
        plan.schema_version = version
        plan.input_snapshot = {}
        plan.input_fingerprint = "irrelevant"
        svc = JobEvaluationPlanService()
        assert svc.is_contract_outdated(plan) is True

    def test_v4_with_wrong_fingerprint_is_outdated(self) -> None:
        """A v4.0 plan whose ``input_fingerprint`` no longer matches the
        current fingerprint algorithm is also contract-outdated.  This
        prevents stale 4.0 plans from being used for screening."""
        plan = JobEvaluationPlan()
        plan.schema_version = JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
        plan.input_snapshot = {
            "schema_version": "4.0",
            "job_context": {
                "title": "Test",
                "department": None,
                "job_background": None,
            },
            "evaluation_fields": {
                "job_responsibilities": None,
                "candidate_requirements": "test requirement",
                "preferred_qualifications": None,
            },
            "source_units": [
                {
                    "source_unit_id": "candidate_requirements:0001",
                    "source_field": "candidate_requirements",
                    "ordinal": 1,
                    "source_text": "test requirement",
                }
            ],
        }
        # Set a deliberately wrong fingerprint
        plan.input_fingerprint = "wrong_fingerprint_that_will_never_match"
        svc = JobEvaluationPlanService()
        assert svc.is_contract_outdated(plan) is True
