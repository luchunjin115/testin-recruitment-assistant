from unittest import TestCase

from app.models.rebuilt import Job


class JobStructureModelTest(TestCase):
    def test_stage6_columns_match_database_contract(self) -> None:
        table = Job.__table__

        self.assertEqual(table.c.location.type.length, 100)
        self.assertTrue(table.c.location.nullable)
        self.assertEqual(table.c.employment_type.type.length, 30)
        self.assertTrue(table.c.employment_type.nullable)
        self.assertTrue(table.c.headcount.nullable)
        self.assertFalse(table.c.requirements.nullable)
        self.assertTrue(table.c.legacy_requirements.nullable)
        self.assertTrue(table.c.legacy_requirements.type.none_as_null)
        self.assertEqual(table.c.status.default.arg, "draft")
        self.assertEqual(table.c.status.server_default.arg, "draft")

    def test_stage6_check_constraints_are_declared(self) -> None:
        constraints = {
            constraint.name: str(constraint.sqltext)
            for constraint in Job.__table__.constraints
            if constraint.name
        }

        self.assertEqual(
            constraints["ck_jobs_status_allowed"],
            "status IN ('draft', 'open', 'closed')",
        )
        self.assertEqual(
            constraints["ck_jobs_headcount_range"],
            "headcount IS NULL OR headcount BETWEEN 1 AND 999",
        )
