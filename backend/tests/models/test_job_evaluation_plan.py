from unittest import TestCase

from sqlalchemy import CheckConstraint

from app.models import Job, JobEvaluationPlan


class JobEvaluationPlanModelTest(TestCase):
    def test_columns_relationship_and_json_contract_are_independent(self) -> None:
        table = JobEvaluationPlan.__table__

        self.assertEqual(table.name, "job_evaluation_plans")
        self.assertEqual(
            next(iter(table.c.job_id.foreign_keys)).target_fullname,
            "jobs.id",
        )
        # 4.0 rows store facts/criteria in dedicated columns and keep legacy items NULL.
        self.assertTrue(table.c["items"].nullable)
        self.assertTrue(table.c.structured_coverage.nullable)
        self.assertTrue(table.c.free_text_coverage.nullable)
        self.assertTrue(table.c.source_review_summary.nullable)
        self.assertNotIn("contract_outdated", table.c)
        self.assertFalse(table.c.input_snapshot.nullable)
        self.assertEqual(table.c.jd_fingerprint.type.length, 64)
        self.assertEqual(table.c.error_code.type.length, 100)
        self.assertIn("evaluation_plans", Job.__mapper__.relationships)
        self.assertEqual(
            JobEvaluationPlan.__mapper__.relationships["job"].back_populates,
            "evaluation_plans",
        )

    def test_constraints_and_indexes_limit_current_plan_and_status(self) -> None:
        table = JobEvaluationPlan.__table__
        constraint_names = {constraint.name for constraint in table.constraints}
        index_names = {index.name for index in table.indexes}

        self.assertIn("ck_job_evaluation_plans_status_allowed", constraint_names)
        self.assertIn("ck_job_evaluation_plans_outdated_not_current", constraint_names)
        self.assertIn(
            "ck_job_evaluation_plans_free_text_coverage_object",
            constraint_names,
        )
        self.assertIn(
            "ck_job_evaluation_plans_v2_ready_has_free_text_coverage",
            constraint_names,
        )
        self.assertIn(
            "ck_job_evaluation_plans_source_review_summary_object",
            constraint_names,
        )
        self.assertIn(
            "ck_job_evaluation_plans_schema_version_allowed",
            constraint_names,
        )
        self.assertIn(
            "ck_job_evaluation_plans_v3_ready_has_source_review_summary",
            constraint_names,
        )
        self.assertIn(
            "ck_job_evaluation_plans_v3_has_no_legacy_coverage",
            constraint_names,
        )
        self.assertIn("uq_job_evaluation_plans_legacy_job_input", index_names)
        self.assertIn(
            "uq_job_evaluation_plans_v5_job_input_edit_version",
            index_names,
        )
        self.assertIn("uq_job_evaluation_plans_current_job", index_names)
        current_index = next(
            index
            for index in table.indexes
            if index.name == "uq_job_evaluation_plans_current_job"
        )
        self.assertTrue(current_index.unique)
        self.assertIsNotNone(current_index.dialect_options["postgresql"]["where"])

        legacy_index = next(
            index
            for index in table.indexes
            if index.name == "uq_job_evaluation_plans_legacy_job_input"
        )
        v5_index = next(
            index
            for index in table.indexes
            if index.name == "uq_job_evaluation_plans_v5_job_input_edit_version"
        )
        self.assertTrue(legacy_index.unique)
        self.assertEqual(
            [column.name for column in legacy_index.columns],
            ["job_id", "input_fingerprint"],
        )
        self.assertTrue(v5_index.unique)
        self.assertEqual(
            [column.name for column in v5_index.columns],
            ["job_id", "input_fingerprint", "edit_version"],
        )
        self.assertIn(
            "schema_version <> '5.0'",
            str(legacy_index.dialect_options["postgresql"]["where"]),
        )
        self.assertIn(
            "schema_version = '5.0'",
            str(v5_index.dialect_options["postgresql"]["where"]),
        )
        self.assertTrue(
            any(
                isinstance(constraint, CheckConstraint)
                and "generating" in str(constraint.sqltext)
                for constraint in table.constraints
            )
        )
