from unittest import TestCase

from sqlalchemy.orm import configure_mappers

from app.core.database import Base
from app.models.rebuilt import (
    Application,
    JobScreeningRubric,
    ScreeningResult,
    StageHistory,
)


class ApplicationModelTest(TestCase):
    def test_application_columns_and_defaults_match_stage7_contract(self) -> None:
        table = Application.__table__

        self.assertFalse(table.c.candidate_id.nullable)
        self.assertFalse(table.c.job_id.nullable)
        self.assertTrue(table.c.current_resume_id.nullable)
        self.assertTrue(table.c.current_screening_result_id.nullable)
        self.assertEqual(table.c.lifecycle_status.server_default.arg, "active")
        self.assertEqual(table.c.ai_status.server_default.arg, "not_started")
        self.assertTrue(table.c.applied_at.type.timezone)

    def test_application_constraints_and_active_pair_index_are_declared(self) -> None:
        table = Application.__table__
        constraint_names = {constraint.name for constraint in table.constraints}
        index = next(
            item for item in table.indexes if item.name == "uq_applications_active_candidate_job"
        )

        self.assertTrue(
            {
                "ck_applications_source_allowed",
                "ck_applications_lifecycle_status_allowed",
                "ck_applications_recruitment_stage_allowed",
                "ck_applications_ai_status_allowed",
                "ck_applications_hr_decision_allowed",
                "ck_applications_resume_required_unless_legacy",
                "uq_applications_current_screening_result_id",
            }.issubset(constraint_names)
        )
        self.assertTrue(index.unique)
        self.assertEqual(
            str(index.dialect_options["postgresql"]["where"]),
            "lifecycle_status = 'active'",
        )


class JobScreeningRubricModelTest(TestCase):
    def test_rubric_defaults_versions_and_weight_constraints_are_declared(self) -> None:
        table = JobScreeningRubric.__table__
        constraint_names = {constraint.name for constraint in table.constraints}

        self.assertEqual(table.c.must_have_requirements_weight.server_default.arg, "40")
        self.assertEqual(table.c.work_experience_relevance_weight.server_default.arg, "25")
        self.assertEqual(table.c.projects_and_capability_weight.server_default.arg, "20")
        self.assertEqual(table.c.preferred_qualifications_weight.server_default.arg, "10")
        self.assertEqual(table.c.keywords_and_additional_weight.server_default.arg, "5")
        self.assertEqual(table.c.schema_version.server_default.arg, "1.0")
        self.assertTrue(
            {
                "uq_job_screening_rubrics_job_version",
                "ck_job_screening_rubrics_version_positive",
                "ck_job_screening_rubrics_must_have_weight_range",
                "ck_job_screening_rubrics_work_weight_range",
                "ck_job_screening_rubrics_project_weight_range",
                "ck_job_screening_rubrics_preferred_weight_range",
                "ck_job_screening_rubrics_additional_weight_range",
                "ck_job_screening_rubrics_weight_total",
            }.issubset(constraint_names)
        )

    def test_only_one_current_rubric_per_job_index_is_declared(self) -> None:
        index = next(
            item
            for item in JobScreeningRubric.__table__.indexes
            if item.name == "uq_job_screening_rubrics_current_job"
        )

        self.assertTrue(index.unique)
        self.assertEqual(
            str(index.dialect_options["postgresql"]["where"]),
            "is_current = true",
        )


class StageHistoryModelTest(TestCase):
    def test_history_is_append_oriented_and_keeps_actor_and_result_reference(self) -> None:
        table = StageHistory.__table__

        self.assertFalse(table.c.application_id.nullable)
        self.assertFalse(table.c.to_recruitment_stage.nullable)
        self.assertFalse(table.c.to_hr_decision.nullable)
        self.assertFalse(table.c.reason_code.nullable)
        self.assertFalse(table.c.actor_label.nullable)
        self.assertTrue(table.c.screening_result_id.nullable)
        self.assertEqual(table.c.overrides_ai_recommendation.server_default.arg, "false")
        self.assertTrue(table.c.created_at.type.timezone)


class ScreeningResultVersionModelTest(TestCase):
    def test_screening_result_supports_application_attempts_and_legacy_rows(self) -> None:
        table = ScreeningResult.__table__

        self.assertTrue(table.c.application_id.nullable)
        self.assertTrue(table.c.resume_id.nullable)
        self.assertFalse(table.c.attempt_number.nullable)
        self.assertEqual(table.c.attempt_number.server_default.arg, "1")
        self.assertEqual(table.c.execution_status.server_default.arg, "completed")
        self.assertEqual(table.c.force_rerun.server_default.arg, "false")
        self.assertEqual(table.c.is_outdated.server_default.arg, "false")
        self.assertEqual(table.c.input_fingerprint.type.length, 64)

    def test_old_candidate_job_uniqueness_is_replaced_by_application_attempt(self) -> None:
        table = ScreeningResult.__table__
        constraint_names = {constraint.name for constraint in table.constraints}

        self.assertNotIn("uq_screening_candidate_job", constraint_names)
        self.assertIn("uq_screening_results_application_attempt", constraint_names)

        running_index = next(
            item
            for item in table.indexes
            if item.name == "uq_screening_results_running_application"
        )
        self.assertTrue(running_index.unique)
        self.assertIn(
            "execution_status = 'screening'",
            str(running_index.dialect_options["postgresql"]["where"]),
        )

    def test_all_rebuilt_mappers_and_stage7_tables_configure_together(self) -> None:
        configure_mappers()

        self.assertTrue(
            {"applications", "stage_histories", "job_screening_rubrics"}.issubset(
                Base.metadata.tables
            )
        )

