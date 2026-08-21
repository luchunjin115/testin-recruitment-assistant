from unittest import TestCase

from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun


class ScreeningModelTest(TestCase):
    def test_report_has_one_application_unique_constraint(self) -> None:
        names = {item.name for item in ScreeningReport.__table__.constraints}
        self.assertIn("uq_screening_reports_application_id", names)

    def test_report_foreign_keys_protect_business_rows(self) -> None:
        ondelete = {foreign_key.ondelete for foreign_key in ScreeningReport.__table__.foreign_keys}
        self.assertEqual(ondelete, {"RESTRICT"})

    def test_report_has_score_label_and_json_constraints(self) -> None:
        names = {item.name for item in ScreeningReport.__table__.constraints}
        self.assertTrue(
            {
                "ck_screening_reports_overall_score_range",
                "ck_screening_reports_display_label_allowed",
                "ck_screening_reports_requirements_array",
                "ck_screening_reports_bonuses_array",
                "ck_screening_reports_outdated_state_consistent",
            }.issubset(names)
        )

    def test_run_has_product_state_and_trigger_constraints(self) -> None:
        names = {item.name for item in ScreeningRun.__table__.constraints}
        self.assertIn("ck_screening_runs_status_allowed", names)
        self.assertIn("ck_screening_runs_trigger_type_allowed", names)

    def test_run_active_input_partial_unique_index(self) -> None:
        index = next(
            item
            for item in ScreeningRun.__table__.indexes
            if item.name == "uq_screening_runs_active_input"
        )
        self.assertTrue(index.unique)
        predicate = str(index.dialect_options["postgresql"]["where"])
        self.assertIn("queued", predicate)
        self.assertIn("running", predicate)

    def test_run_does_not_store_full_report_or_raw_response(self) -> None:
        columns = set(ScreeningRun.__table__.columns.keys())
        self.assertFalse(
            columns.intersection(
                {
                    "overall_summary",
                    "requirement_assessments",
                    "bonus_highlights",
                    "raw_response",
                    "resume_text",
                }
            )
        )

    def test_report_and_run_store_the_required_time_audit_boundary(self) -> None:
        report_columns = set(ScreeningReport.__table__.columns.keys())
        run_columns = set(ScreeningRun.__table__.columns.keys())
        self.assertTrue(
            {
                "evaluation_reference_at",
                "evaluation_timezone",
                "experience_period_facts_rule_version",
                "experience_period_facts",
            }.issubset(report_columns)
        )
        self.assertTrue(
            {
                "evaluation_reference_at",
                "evaluation_timezone",
                "experience_period_facts_rule_version",
                "experience_period_facts_fingerprint",
            }.issubset(run_columns)
        )
        self.assertNotIn("experience_period_facts", run_columns)
