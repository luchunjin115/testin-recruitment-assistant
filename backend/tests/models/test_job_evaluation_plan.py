from unittest import TestCase

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models import Job, JobEvaluationPlan


class JobEvaluationPlanModelTest(TestCase):
    def test_columns_relationship_and_json_contract_are_independent(self) -> None:
        table = JobEvaluationPlan.__table__

        self.assertEqual(table.name, "job_evaluation_plans")
        self.assertEqual(
            next(iter(table.c.job_id.foreign_keys)).target_fullname,
            "jobs.id",
        )
        self.assertFalse(table.c["items"].nullable)
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
        self.assertIn(
            "uq_job_evaluation_plans_job_input_fingerprint",
            constraint_names,
        )
        self.assertIn("uq_job_evaluation_plans_current_job", index_names)
        current_index = next(
            index
            for index in table.indexes
            if index.name == "uq_job_evaluation_plans_current_job"
        )
        self.assertTrue(current_index.unique)
        self.assertIsNotNone(current_index.dialect_options["postgresql"]["where"])

        unique_constraints = [
            constraint
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        self.assertEqual(len(unique_constraints), 1)
        self.assertEqual(
            [column.name for column in unique_constraints[0].columns],
            ["job_id", "input_fingerprint"],
        )
        self.assertTrue(
            any(
                isinstance(constraint, CheckConstraint)
                and "generating" in str(constraint.sqltext)
                for constraint in table.constraints
            )
        )
