import asyncio
import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

from app.adapters.job_evaluation_plan import JobEvaluationPlanAdapterResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_stage7_quality_acceptance.py"
SPEC = importlib.util.spec_from_file_location("stage7_quality_acceptance_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def green_records(*, actual_model_call_count: int) -> list[dict]:
    records = []
    for case in runner.JD_CASES:
        is_boundary = case["expected_outcome"] in {"no_items", "too_many_items"}
        records.append(
            {
                "case_id": case["case_id"],
                "actual_outcome": case["expected_outcome"],
                "actual_model_call_count": actual_model_call_count,
                "free_text_expected": len(case["free_text_expectations"]),
                "free_text_found": len(case["free_text_expectations"]),
                "structured_value_count": 0 if is_boundary else 1,
                "structured_covered_count": 0 if is_boundary else 1,
                "item_count": 0 if is_boundary else 1,
                "traceable_item_count": 0 if is_boundary else 1,
                "added_required_count": 0,
                "obvious_duplicate_count": 0,
                "promotion_item_count": 0,
                "activation_assertion_found": case["case_id"] == "JD08",
            }
        )
    return records


def screening_record(
    case_id: str,
    *,
    successful_runs: int,
    direction_consistent: bool,
    actual_calls: int = 3,
    blocked: bool = False,
    max_difference: int | None = None,
    safety_audit: dict | None = None,
) -> dict:
    runs = []
    for index in range(actual_calls):
        legal = index < successful_runs
        run = {
            "run": index + 1,
            "actual_model_call_count": 1,
            "model": "offline-screening-model",
            "input_tokens": 10,
            "output_tokens": 5,
            "model_raw_structured_response": "{}",
        }
        if legal:
            run["score"] = 70 + index
        else:
            run.update(
                {
                    "rejection_layer": "service",
                    "failure_classification": "evidence",
                }
            )
        if safety_audit is not None:
            run["safety_audit"] = safety_audit
        runs.append(run)
    return {
        "case_id": case_id,
        "job_case_id": "JD01",
        "manual_band_locked_before_ai": "high",
        "extreme": None,
        "actual_model_call_count": 0 if blocked else actual_calls,
        "successful_run_count": 0 if blocked else successful_runs,
        "first_ai_score": None if blocked or not successful_runs else 70,
        "first_ai_display_label": None if blocked or not successful_runs else "整体较匹配",
        "first_ai_three_band": None if blocked or not successful_runs else "high",
        "direction_consistent": False if blocked else direction_consistent,
        "scores": [] if blocked else [70 + index for index in range(successful_runs)],
        "max_score_difference": max_difference,
        "display_interval_span": 0 if successful_runs == 3 else None,
        "requirement_direction_reversal_keys": [],
        "redaction_marker_leaks": [],
        "runs": [] if blocked else runs,
        **({"blocked_by": "upstream_job_evaluation_plan_not_ready"} if blocked else {}),
    }


class Step9FixtureAndStatisticsTests(TestCase):
    def test_frozen_fixture_contract_has_20_cases_and_42_expectations(self) -> None:
        fixture = runner.validate_step9_fixture_contract()

        self.assertEqual(fixture["case_count"], 20)
        self.assertEqual(fixture["frozen_free_text_expectation_count"], 42)
        self.assertEqual(fixture["normal_case_count"], 18)
        self.assertEqual(fixture["boundary_case_ids"], ["JD18", "JD19"])
        self.assertEqual(
            fixture["limited_case_ids"],
            ["JD13", "JD15", "JD17", "JD20"],
        )
        self.assertFalse(
            fixture["activation_assertion"]["included_in_frozen_denominator"]
        )

    def test_source_quote_cannot_create_a_false_recognition_hit(self) -> None:
        item = SimpleNamespace(title="拉新", source_quote="拉新、激活与留存")

        self.assertFalse(runner.expectation_found(["激活"], [item]))
        self.assertTrue(
            runner.expectation_found(["激活"], [item], ["激活实验"])
        )

    def test_offline_green_fixture_cannot_claim_real_quality(self) -> None:
        summary = runner.summarize_step9_jd_results(
            green_records(actual_model_call_count=0),
            run_kind="directed_debug",
        )

        self.assertTrue(summary["all_metrics_satisfied"])
        self.assertIsNone(summary["quality_gate_passed"])
        self.assertFalse(summary["quality_conclusion_allowed"])
        self.assertEqual(summary["actual_model_call_count"], 0)

    def test_complete_20_call_final_count_can_reach_the_gate(self) -> None:
        summary = runner.summarize_step9_jd_results(
            green_records(actual_model_call_count=1),
            run_kind="final_count",
        )

        self.assertEqual(summary["free_text_found_count"], 42)
        self.assertEqual(summary["free_text_major_requirement_recognition_rate"], 1.0)
        self.assertEqual(summary["normal_ready_or_limited_count"], 18)
        self.assertEqual(summary["boundary_correct_count"], 2)
        self.assertEqual(summary["limited_correct_count"], 4)
        self.assertTrue(summary["activation_assertion_found"])
        self.assertEqual(summary["structured_explicit_requirement_count"], 18)
        self.assertEqual(summary["structured_covered_count"], 18)
        self.assertEqual(summary["added_required_count"], 0)
        self.assertEqual(summary["obvious_duplicate_count"], 0)
        self.assertEqual(summary["untraceable_item_count"], 0)
        self.assertEqual(summary["promotion_or_benefit_misclassified_count"], 0)
        self.assertTrue(summary["quality_gate_passed"])
        self.assertTrue(summary["quality_conclusion_allowed"])
        self.assertEqual(summary["actual_model_call_count"], 20)

    def test_failed_recall_or_activation_fails_the_metrics(self) -> None:
        records = green_records(actual_model_call_count=1)
        records[0]["free_text_found"] = 0
        next(record for record in records if record["case_id"] == "JD08")[
            "activation_assertion_found"
        ] = False

        summary = runner.summarize_step9_jd_results(
            records,
            run_kind="final_count",
        )

        self.assertFalse(summary["activation_assertion_found"])
        self.assertFalse(summary["all_metrics_satisfied"])
        self.assertFalse(summary["quality_gate_passed"])
        self.assertTrue(summary["quality_conclusion_allowed"])

    def test_final_count_requires_each_frozen_case_exactly_once(self) -> None:
        records = green_records(actual_model_call_count=1)
        records[0]["actual_model_call_count"] = 2
        records[1]["actual_model_call_count"] = 0

        summary = runner.summarize_step9_jd_results(
            records,
            run_kind="final_count",
        )

        self.assertEqual(summary["actual_model_call_count"], 20)
        self.assertIsNone(summary["quality_gate_passed"])
        self.assertFalse(summary["quality_conclusion_allowed"])

    def test_debug_and_final_paths_are_separate_from_historical_result(self) -> None:
        self.assertNotEqual(runner.STEP9_DEBUG_RESULT_PATH, runner.RESULT_PATH)
        self.assertNotEqual(runner.STEP9_FINAL_RESULT_PATH, runner.RESULT_PATH)
        self.assertNotEqual(
            runner.STEP9_DEBUG_RESULT_PATH,
            runner.STEP9_FINAL_RESULT_PATH,
        )
        with self.assertRaises(SystemExit):
            runner.step9_result_path("final_count", runner.RESULT_PATH)

    def test_dry_run_neither_loads_settings_nor_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.json"
            stdout = io.StringIO()
            with patch.object(
                runner,
                "get_settings",
                side_effect=AssertionError("dry-run must not load real settings"),
            ), redirect_stdout(stdout):
                asyncio.run(
                    runner.main(
                        [
                            "--mode",
                            "step9-jd",
                            "--step9-run-kind",
                            "final_count",
                            "--dry-run",
                            "--output",
                            str(output),
                        ]
                    )
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["actual_model_call_count"], 0)
            self.assertFalse(payload["writes_result_file"])
            self.assertFalse(payload["quality_conclusion_allowed"])
            self.assertFalse(output.exists())

    def test_combined_fixture_keeps_all_twenty_labels_and_three_runs(self) -> None:
        fixture = runner.validate_step9_screening_fixture_contract()

        self.assertEqual(fixture["case_count"], 20)
        self.assertEqual(fixture["manual_label_counts"], {"high": 8, "low": 6, "partial": 6})
        self.assertEqual(fixture["runs_per_non_blocked_case"], 3)
        self.assertEqual(fixture["maximum_screening_call_count"], 60)

    def test_combined_result_paths_cannot_target_historical_results(self) -> None:
        with patch.object(runner, "STEP9_REVALIDATION_RESULT_PATH", runner.RESULT_PATH):
            with self.assertRaises(SystemExit):
                runner.validate_combined_result_paths()

    def test_exclusive_result_write_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing.json"
            output.write_text("historical", encoding="utf-8")

            with self.assertRaises(SystemExit):
                runner.write_new_json(output, {"replacement": True})

            self.assertEqual(output.read_text(encoding="utf-8"), "historical")

    def test_blocked_samples_remain_in_all_overall_denominators(self) -> None:
        results = [
            screening_record("SR01", successful_runs=3, direction_consistent=True, max_difference=2),
            screening_record("SR02", successful_runs=0, direction_consistent=False),
            screening_record("SR03", successful_runs=0, direction_consistent=False, blocked=True),
        ]

        summary = runner.summarize_screening_diagnostic(results)

        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["upstream_blocked_sample_count"], 1)
        self.assertEqual(summary["at_least_one_legal_report_sample_count"], 1)
        self.assertEqual(summary["at_least_one_legal_report_rate"], 1 / 3)
        self.assertEqual(summary["direction_consistent_count"], 1)
        self.assertEqual(summary["direction_consistency_rate"], 1 / 3)
        self.assertEqual(
            summary["legal_report_distribution"],
            {"0_of_3": 2, "1_of_3": 0, "2_of_3": 0, "3_of_3": 1},
        )

    def test_stability_uses_only_three_legal_samples_but_twenty_style_sample_denominator_is_preserved(self) -> None:
        results = [
            screening_record("SR01", successful_runs=3, direction_consistent=True, max_difference=5),
            screening_record("SR02", successful_runs=3, direction_consistent=True, max_difference=6),
            screening_record("SR03", successful_runs=2, direction_consistent=True),
        ]

        summary = runner.summarize_screening_diagnostic(results)

        self.assertEqual(summary["three_run_legal_sample_count"], 2)
        self.assertEqual(summary["stability_max_difference_le_5_count"], 1)
        self.assertEqual(summary["stability_max_difference_le_5_rate"], 0.5)
        self.assertEqual(summary["sample_count"], 3)

    def test_call_token_failure_and_safety_statistics_are_exact(self) -> None:
        audit = {
            "positive_basis_evidence_count": 2,
            "locatable_positive_basis_evidence_count": 1,
            "bonus_evidence_count": 1,
            "locatable_bonus_evidence_count": 1,
            "severe_fact_fabrication_detected": True,
            "experience_fact_conflict_count": 1,
            "post_application_fact_misuse_count": 0,
            "sensitive_attribute_scoring_detected": True,
            "recruitment_decision_detected": False,
            "bonus_base_duplicate_count": 1,
            "bonus_job_unrelated_count": 0,
            "missing_as_inability_detected": True,
            "missing_quantification_invalidated_experience_detected": False,
        }
        result = screening_record(
            "SR01",
            successful_runs=2,
            direction_consistent=True,
            safety_audit=audit,
        )

        summary = runner.summarize_screening_diagnostic([result])

        self.assertEqual(summary["actual_model_call_count"], 3)
        self.assertEqual(summary["input_tokens"], 30)
        self.assertEqual(summary["output_tokens"], 15)
        self.assertEqual(summary["total_tokens"], 45)
        self.assertEqual(summary["failure_classification_counts"], {"evidence": 1})
        self.assertEqual(summary["positive_basis_evidence_count"], 6)
        self.assertEqual(summary["locatable_positive_basis_evidence_count"], 3)
        self.assertEqual(summary["severe_fact_fabrication_response_count"], 3)
        self.assertEqual(summary["sensitive_attribute_scoring_response_count"], 3)
        self.assertEqual(summary["bonus_base_duplicate_count"], 3)
        self.assertEqual(summary["missing_as_inability_response_count"], 3)

    def test_non_blocked_samples_must_have_exactly_three_calls(self) -> None:
        result = screening_record(
            "SR01",
            successful_runs=2,
            direction_consistent=True,
            actual_calls=2,
        )

        summary = runner.summarize_screening_diagnostic([result])

        self.assertEqual(summary["non_blocked_cases_with_exactly_three_calls"], 0)
        self.assertEqual(summary["non_blocked_call_count_violation_case_ids"], ["SR01"])


class RecordingNonRequirementAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def extract(self, extraction_input: dict) -> JobEvaluationPlanAdapterResult:
        self.calls.append(extraction_input)
        reviews = [
            {
                "source_id": unit["source_id"],
                "disposition": "non_requirement",
                "non_requirement_reason": "promotion",
                "items": [],
            }
            for unit in extraction_input["source_units"]
        ]
        return JobEvaluationPlanAdapterResult(
            content=json.dumps(
                {"schema_version": "2.0", "source_reviews": reviews},
                ensure_ascii=False,
            ),
            model="offline-test-model",
            finish_reason="stop",
            input_tokens=1,
            output_tokens=1,
        )


class InvalidSchemaAdapter:
    async def extract(self, extraction_input: dict) -> JobEvaluationPlanAdapterResult:
        return JobEvaluationPlanAdapterResult(
            content='{"schema_version":"2.0","source_reviews":"invalid"}',
            model="offline-invalid-schema-model",
            finish_reason="stop",
            input_tokens=12,
            output_tokens=3,
        )


class Step9RunnerContractTests(IsolatedAsyncioTestCase):
    async def test_downstream_rejects_a_plan_not_created_by_current_run(self) -> None:
        case = runner.SCREENING_CASES[0]
        ready_plans = {
            case["job_case_id"]: {
                "snapshot": object(),
                "items": [],
                "provenance": "historical-run",
            }
        }

        with self.assertRaisesRegex(ValueError, "非本轮评价计划"):
            await runner.run_screening_acceptance(
                None,
                ready_plans,
                cases=[case],
                expected_plan_provenance="current-run",
            )

    async def test_missing_current_plan_is_upstream_blocked_with_zero_calls(self) -> None:
        case = runner.SCREENING_CASES[0]

        results, summary = await runner.run_screening_acceptance(
            None,
            {},
            cases=[case],
            expected_plan_provenance="current-run",
        )

        self.assertEqual(results[0]["blocked_by"], "upstream_job_evaluation_plan_not_ready")
        self.assertEqual(results[0]["actual_model_call_count"], 0)
        self.assertEqual(results[0]["successful_run_count"], 0)
        self.assertEqual(summary["sample_count"], 1)
        self.assertEqual(summary["upstream_blocked_sample_count"], 1)
        self.assertEqual(summary["legal_report_distribution"]["0_of_3"], 1)
        self.assertEqual(summary["direction_consistent_count"], 0)

    async def test_runner_uses_schema_2_extraction_input_for_boundary_case(self) -> None:
        case = next(case for case in runner.JD_CASES if case["case_id"] == "JD19")
        adapter = RecordingNonRequirementAdapter()

        results, context = await runner.run_jd_acceptance(
            None,
            cases=[case],
            adapter=adapter,
        )

        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(
            set(adapter.calls[0]),
            {"input_snapshot", "source_units", "structured_candidates"},
        )
        self.assertEqual(results[0]["actual_outcome"], "no_items")
        self.assertEqual(results[0]["actual_model_call_count"], 1)
        self.assertEqual(results[0]["model"], "offline-test-model")
        self.assertEqual(results[0]["input_tokens"], 1)
        self.assertEqual(results[0]["output_tokens"], 1)
        self.assertIn("source_reviews", results[0]["model_raw_structured_response"])
        self.assertTrue(results[0]["contract_satisfied"])
        self.assertIsNone(results[0]["failure_classification"])
        self.assertEqual(context["aggregate"]["all_real_model_calls"], 1)
        self.assertEqual(context["ready_plans"], {})

    async def test_runner_keeps_raw_response_and_metadata_when_schema_rejects(self) -> None:
        case = next(case for case in runner.JD_CASES if case["case_id"] == "JD04")

        results, context = await runner.run_jd_acceptance(
            None,
            cases=[case],
            adapter=InvalidSchemaAdapter(),
        )

        record = results[0]
        self.assertEqual(record["actual_model_call_count"], 1)
        self.assertEqual(record["model"], "offline-invalid-schema-model")
        self.assertEqual(record["input_tokens"], 12)
        self.assertEqual(record["output_tokens"], 3)
        self.assertEqual(
            record["model_raw_structured_response"],
            '{"schema_version":"2.0","source_reviews":"invalid"}',
        )
        self.assertEqual(record["actual_outcome"], "content_failure")
        self.assertFalse(record["contract_satisfied"])
        self.assertEqual(record["rejection_layer"], "schema")
        self.assertEqual(record["failure_classification"], "model_noncompliance")
        self.assertEqual(context["aggregate"]["all_real_model_calls"], 1)
