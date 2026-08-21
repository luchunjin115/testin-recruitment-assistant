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
        self.assertFalse(table.c.structured_coverage.nullable)
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
            "uq_job_evaluation_plans_job_jd_fingerprint",
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
        self.assertTrue(
            any(
                isinstance(constraint, CheckConstraint)
                and "generating" in str(constraint.sqltext)
                for constraint in table.constraints
            )
        )
