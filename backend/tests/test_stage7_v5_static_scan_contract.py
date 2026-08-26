"""v5.0 static scan contract tests.

Static proofs that v5.0 removes all weight/weighted scoring, has no
RequirementFact dependency in the v5 code path, and that quality baseline
constants are correctly defined.

These tests scan source code and project structure -- they do NOT call
AI services or require a database.

Sections:
- A. No weight fields in schemas (5 tests)
- B. No weight in services (3 tests)
- C. RequirementFact separation proof (4 tests)
- D. Quality baseline constants (5 tests)
- E. Historical result protection (3 tests)
- F. No Python weighted total (2 tests)
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent
_SCHEMAS_DIR = _BACKEND_ROOT / "app" / "schemas"
_SERVICES_DIR = _BACKEND_ROOT / "app" / "services"

_SCREENING_EVAL_SCHEMA_PATH = _SCHEMAS_DIR / "screening_evaluation.py"
_JOB_EVAL_PLAN_SCHEMA_PATH = _SCHEMAS_DIR / "job_evaluation_plan.py"
_SCREENING_SCHEMA_PATH = _SCHEMAS_DIR / "screening.py"
_SCREENING_EVAL_SERVICE_PATH = _SERVICES_DIR / "screening_evaluation_service.py"
_SCREENING_SERVICE_PATH = _SERVICES_DIR / "screening_service.py"
_JOB_EVAL_PLAN_SERVICE_PATH = _SERVICES_DIR / "job_evaluation_plan_service.py"

_V4_FORMAL_RESULTS_PATH = (
    _PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-25-stage7-7r4h-plan-quality-formal-results.json"
)
_V4_REVALIDATION_RESULTS_PATH = (
    _PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-08-26-stage7-7r4hr2-plan-quality-targeted-revalidation-results.json"
)
_V5_RESULTS_DIR = _PROJECT_ROOT / "docs" / "stages" / "stage7" / "v5-quality-results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_source(path: Path) -> str:
    """Read a Python source file and return its text."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _class_field_names(module_path: Path, class_name: str) -> list[str]:
    """Parse a module with ast and return annotated field names for a class."""
    source = _read_source(module_path)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: list[str] = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    fields.append(item.target.id)
            return fields
    raise LookupError(f"Class {class_name} not found in {module_path}")


def _source_assignments(source: str) -> list[str]:
    """Return lines that contain assignment-like patterns (= not ==)."""
    result: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        # Skip comments and pure strings
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
            continue
        # Look for assignment (=) but not comparison (==, !=, <=, >=)
        if re.search(r"(?<!=)=(?!=)", stripped):
            result.append(stripped)
    return result


# ===========================================================================
# A. No weight fields in schemas (5 tests) -- static proof, should PASS
# ===========================================================================


class TestNoWeightFieldsInSchemas:
    """Prove that current screening evaluation schemas contain no
    weight/weighted fields -- a core v5.0 invariant."""

    def test_ai_screening_evaluation_output_has_no_weight_field(self) -> None:
        """AIScreeningEvaluationOutput must not contain any field with
        'weight' in its name."""
        fields = _class_field_names(
            _SCREENING_EVAL_SCHEMA_PATH, "AIScreeningEvaluationOutput"
        )
        weight_fields = [f for f in fields if "weight" in f.lower()]
        assert weight_fields == [], (
            f"AIScreeningEvaluationOutput contains weight field(s): {weight_fields}"
        )

    def test_requirement_assessment_has_no_weight_field(self) -> None:
        """RequirementAssessment must not contain any field with 'weight'
        in its name."""
        fields = _class_field_names(
            _SCREENING_EVAL_SCHEMA_PATH, "RequirementAssessment"
        )
        weight_fields = [f for f in fields if "weight" in f.lower()]
        assert weight_fields == [], (
            f"RequirementAssessment contains weight field(s): {weight_fields}"
        )

    def test_screening_report_read_has_no_weight_field(self) -> None:
        """ScreeningReportRead must not contain any field with 'weight'
        in its name."""
        fields = _class_field_names(
            _SCREENING_SCHEMA_PATH, "ScreeningReportRead"
        )
        weight_fields = [f for f in fields if "weight" in f.lower()]
        assert weight_fields == [], (
            f"ScreeningReportRead contains weight field(s): {weight_fields}"
        )

    def test_overall_score_type_has_no_weighted_calculation(self) -> None:
        """OverallScore type alias and any validators around it must not
        reference weighted calculation logic."""
        source = _read_source(_SCREENING_EVAL_SCHEMA_PATH)
        # Find the OverallScore definition and surrounding context
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "OverallScore" in line:
                # Check surrounding 5 lines for weighted calculation hints
                context = "\n".join(
                    lines[max(0, i - 2) : min(len(lines), i + 5)]
                )
                assert "weighted" not in context.lower(), (
                    f"OverallScore definition context references 'weighted': "
                    f"{context}"
                )

    def test_screening_evaluation_schema_file_has_no_weighted_keyword(self) -> None:
        """The entire screening_evaluation.py schema file must not contain
        'weighted' or 'weight_score' anywhere."""
        source = _read_source(_SCREENING_EVAL_SCHEMA_PATH)
        source_lower = source.lower()
        assert "weighted" not in source_lower, (
            "screening_evaluation.py contains 'weighted'"
        )
        assert "weight_score" not in source_lower, (
            "screening_evaluation.py contains 'weight_score'"
        )


# ===========================================================================
# B. No weight in services (3 tests) -- static proof, should PASS
# ===========================================================================


class TestNoWeightInServices:
    """Prove that screening evaluation services do not use weight-based
    scoring in their business logic."""

    def test_screening_evaluation_service_no_weight_assignment(self) -> None:
        """screening_evaluation_service.py must not assign to any variable
        containing 'weight' (comments and strings excluded)."""
        source = _read_source(_SCREENING_EVAL_SERVICE_PATH)
        assignments = _source_assignments(source)
        weight_assignments = [
            line
            for line in assignments
            if re.search(r"\bweight\b", line, re.IGNORECASE)
        ]
        assert weight_assignments == [], (
            f"screening_evaluation_service.py has weight assignment(s): "
            f"{weight_assignments}"
        )

    def test_screening_service_no_weighted_keyword(self) -> None:
        """screening_service.py must not contain the word 'weighted'."""
        source = _read_source(_SCREENING_SERVICE_PATH)
        source_lower = source.lower()
        assert "weighted" not in source_lower, (
            "screening_service.py contains 'weighted'"
        )

    def test_display_label_for_score_does_not_use_weights(self) -> None:
        """display_label_for_score must be a pure score-to-label mapper
        with no weight references."""
        from app.services.screening_evaluation_service import (
            ScreeningEvaluationService,
        )

        source = inspect.getsource(
            ScreeningEvaluationService.display_label_for_score
        )
        source_lower = source.lower()
        assert "weight" not in source_lower, (
            "display_label_for_score references 'weight'"
        )


# ===========================================================================
# C. RequirementFact separation proof (4 tests)
# ===========================================================================


class TestRequirementFactSeparation:
    """Document RequirementFact's role in v4.0 and prove v5.0 will not
    depend on it."""

    def test_requirement_fact_class_exists(self) -> None:
        """RequirementFact class must exist for v4.0 compatibility."""
        from app.schemas.job_evaluation_plan import RequirementFact

        assert RequirementFact is not None
        # Verify it has fact_id, category, priority, sources
        field_names = set(RequirementFact.model_fields.keys())
        assert {"fact_id", "category", "priority", "sources"}.issubset(
            field_names
        ), f"RequirementFact is missing expected fields; has: {field_names}"

    @pytest.mark.xfail(
        reason="7R5-A: v5 screening code path does not exist yet",
        strict=True,
    )
    def test_v5_code_path_does_not_import_requirement_fact(self) -> None:
        """When a v5 screening evaluation module exists, it must not
        import RequirementFact.

        This test will pass once the v5 code path is implemented without
        RequirementFact dependency."""
        # The v5 screening evaluation path would be a separate module or
        # a clearly identifiable branch. For now we look for a v5 service.
        v5_service_path = _SERVICES_DIR / "screening_evaluation_v5_service.py"
        assert v5_service_path.exists(), (
            "v5 screening evaluation service does not exist yet"
        )
        source = _read_source(v5_service_path)
        assert "RequirementFact" not in source, (
            "v5 screening evaluation service must not import RequirementFact"
        )

    def test_current_screening_pipeline_uses_requirement_fact(self) -> None:
        """Document that the current (v4.0) screening pipeline depends
        on RequirementFact."""
        source = _read_source(_SCREENING_EVAL_SERVICE_PATH)
        assert "RequirementFact" in source, (
            "Current screening_evaluation_service.py must import "
            "RequirementFact (v4.0 dependency)"
        )

    @pytest.mark.xfail(
        reason="7R5-A: v5.0 schema version constant not yet defined",
        strict=True,
    )
    def test_v5_schema_version_constant_exists(self) -> None:
        """A SCREENING_EVALUATION_V5_SCHEMA_VERSION constant should exist
        once v5.0 is implemented."""
        from app.schemas import screening_evaluation as mod

        assert hasattr(mod, "SCREENING_EVALUATION_V5_SCHEMA_VERSION"), (
            "SCREENING_EVALUATION_V5_SCHEMA_VERSION not yet defined"
        )
        assert getattr(mod, "SCREENING_EVALUATION_V5_SCHEMA_VERSION") == "5.0"


# ===========================================================================
# D. Quality baseline constants (5 tests) -- partially xfail
# ===========================================================================


_V5_FIXTURE_MODULE = "backend.tests.fixtures.v5_quality_samples"


def _try_import_v5_fixtures():
    """Attempt to import v5 quality fixtures; return None if unavailable."""
    try:
        return importlib.import_module("tests.fixtures.v5_quality_samples")
    except (ImportError, ModuleNotFoundError):
        return None


class TestQualityBaselineConstants:
    """Verify v5.0 quality baseline budgets and paths.

    These tests read from the v5 fixtures module. If the module does not
    exist yet, they xfail with a clear reason."""

    def test_v5_result_path_prefix_distinct_from_v4(self) -> None:
        """v5 results must go to a different directory than v4 results."""
        fixtures = _try_import_v5_fixtures()
        if fixtures is None:
            pytest.xfail("7R5-A: fixture not yet created")
        v5_path = getattr(fixtures, "V5_RESULT_PATH_PREFIX", None)
        assert v5_path is not None, (
            "V5_RESULT_PATH_PREFIX not defined in fixtures"
        )
        # v4 results live directly under docs/stages/stage7/
        assert "v5-quality-results" in str(v5_path), (
            "v5 result path must contain 'v5-quality-results'"
        )
        # Must not overlap with v4 result file paths
        assert v5_path != "docs/stages/stage7/", (
            "v5 result path must differ from v4 results directory"
        )

    def test_v5_plan_jd_count_is_10(self) -> None:
        """v5.0 plan acceptance uses 10 JDs."""
        fixtures = _try_import_v5_fixtures()
        if fixtures is None:
            pytest.xfail("7R5-A: fixture not yet created")
        count = getattr(fixtures, "V5_PLAN_JD_COUNT", None)
        assert count == 10, f"Expected 10 JDs, got {count}"

    def test_v5_report_pair_count_is_20(self) -> None:
        """v5.0 report acceptance uses 20 JD+Resume pairs."""
        fixtures = _try_import_v5_fixtures()
        if fixtures is None:
            pytest.xfail("7R5-A: fixture not yet created")
        count = getattr(fixtures, "V5_REPORT_PAIR_COUNT", None)
        assert count == 20, f"Expected 20 pairs, got {count}"

    def test_v5_stability_sample_and_runs(self) -> None:
        """v5.0 stability tests use 5 samples x 3 runs each."""
        fixtures = _try_import_v5_fixtures()
        if fixtures is None:
            pytest.xfail("7R5-A: fixture not yet created")
        samples = getattr(fixtures, "V5_STABILITY_SAMPLE_COUNT", None)
        runs = getattr(fixtures, "V5_STABILITY_RUNS_PER_SAMPLE", None)
        assert samples == 5, f"Expected 5 stability samples, got {samples}"
        assert runs == 3, f"Expected 3 runs per sample, got {runs}"

    def test_v5_call_budgets_correct(self) -> None:
        """v5.0 total call budget is 10 + 20 + 15 = 45."""
        fixtures = _try_import_v5_fixtures()
        if fixtures is None:
            pytest.xfail("7R5-A: fixture not yet created")
        plan_budget = getattr(fixtures, "V5_PLAN_CALL_BUDGET", None)
        report_budget = getattr(fixtures, "V5_REPORT_CALL_BUDGET", None)
        stability_budget = getattr(fixtures, "V5_STABILITY_CALL_BUDGET", None)
        assert plan_budget == 10, f"Plan budget: expected 10, got {plan_budget}"
        assert report_budget == 20, (
            f"Report budget: expected 20, got {report_budget}"
        )
        assert stability_budget == 15, (
            f"Stability budget: expected 15, got {stability_budget}"
        )
        total = plan_budget + report_budget + stability_budget
        assert total == 45, f"Total budget: expected 45, got {total}"


# ===========================================================================
# E. Historical result protection (3 tests) -- should PASS
# ===========================================================================


class TestHistoricalResultProtection:
    """Verify that v4.0 results are preserved and v5.0 results directory
    starts clean."""

    def test_v4_formal_results_file_exists(self) -> None:
        """The 4.0 formal results JSON file must exist at its expected
        path and must not be overwritten by v5 work."""
        assert _V4_FORMAL_RESULTS_PATH.exists(), (
            f"4.0 formal results file missing: {_V4_FORMAL_RESULTS_PATH}"
        )
        assert _V4_FORMAL_RESULTS_PATH.stat().st_size > 0, (
            "4.0 formal results file is empty"
        )

    def test_v4_targeted_revalidation_results_file_exists(self) -> None:
        """The 4.0 targeted revalidation results JSON file must exist."""
        assert _V4_REVALIDATION_RESULTS_PATH.exists(), (
            f"4.0 revalidation results file missing: "
            f"{_V4_REVALIDATION_RESULTS_PATH}"
        )
        assert _V4_REVALIDATION_RESULTS_PATH.stat().st_size > 0, (
            "4.0 revalidation results file is empty"
        )

    def test_v5_results_directory_is_clean(self) -> None:
        """The v5-quality-results/ directory must either not exist or be
        empty -- clean separation from v4."""
        if not _V5_RESULTS_DIR.exists():
            return  # Directory absent is fine -- cleanest state
        contents = list(_V5_RESULTS_DIR.iterdir())
        assert contents == [], (
            f"v5-quality-results/ should be empty but contains: "
            f"{[p.name for p in contents]}"
        )


# ===========================================================================
# F. No Python weighted total (2 tests) -- static proof, should PASS
# ===========================================================================


class TestNoPythonWeightedTotal:
    """Prove that no service computes a weighted total or weighted average
    from requirement scores."""

    def test_job_evaluation_plan_service_no_weighted_average_or_total(
        self,
    ) -> None:
        """job_evaluation_plan_service.py must not contain
        'weighted_average' or 'weighted_total'."""
        source = _read_source(_JOB_EVAL_PLAN_SERVICE_PATH)
        source_lower = source.lower()
        assert "weighted_average" not in source_lower, (
            "job_evaluation_plan_service.py contains 'weighted_average'"
        )
        assert "weighted_total" not in source_lower, (
            "job_evaluation_plan_service.py contains 'weighted_total'"
        )

    def test_screening_evaluation_service_no_score_times_weight(self) -> None:
        """screening_evaluation_service.py must not contain any expression
        that multiplies scores by weights (e.g., score * weight,
        weight * score, sum of weighted)."""
        source = _read_source(_SCREENING_EVAL_SERVICE_PATH)
        # Look for common weighted calculation patterns
        weighted_patterns = [
            r"score\s*\*\s*weight",
            r"weight\s*\*\s*score",
            r"weighted_sum",
            r"weighted_total",
            r"weighted_average",
            r"\bweight\b\s*\*",
            r"\*\s*\bweight\b",
        ]
        for pattern in weighted_patterns:
            matches = re.findall(pattern, source, re.IGNORECASE)
            assert matches == [], (
                f"screening_evaluation_service.py contains weighted "
                f"calculation pattern '{pattern}': {matches}"
            )
