from pathlib import Path
from unittest import TestCase


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b7f2c9d4e816_add_screening_reports_and_runs.py"
)


class ScreeningMigrationTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = MIGRATION.read_text(encoding="utf-8")

    def test_is_forward_migration_from_plan_head(self) -> None:
        self.assertIn('revision: str = "b7f2c9d4e816"', self.source)
        self.assertIn('down_revision: str | None = "a6d4e8f2c713"', self.source)

    def test_creates_both_new_tables_and_downgrade_only_drops_them(self) -> None:
        self.assertIn('"screening_reports"', self.source)
        self.assertIn('"screening_runs"', self.source)
        self.assertNotIn('drop_table("applications")', self.source)
        self.assertNotIn('drop_table("job_evaluation_plans")', self.source)

    def test_contains_required_unique_and_restrict_contracts(self) -> None:
        self.assertIn("uq_screening_reports_application_id", self.source)
        self.assertIn("uq_screening_runs_active_input", self.source)
        self.assertIn('ondelete="RESTRICT"', self.source)
