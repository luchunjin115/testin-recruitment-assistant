from pathlib import Path
from unittest import TestCase


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "d9a1f4c7e820_add_screening_evaluation_time_context.py"
)


class ScreeningEvaluationTimeContextMigrationTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = MIGRATION.read_text(encoding="utf-8")

    def test_is_one_forward_migration_from_screening_head(self) -> None:
        self.assertIn('revision: str = "d9a1f4c7e820"', self.source)
        self.assertIn('down_revision: str | None = "b7f2c9d4e816"', self.source)

    def test_backfills_reference_only_from_application_applied_at(self) -> None:
        self.assertIn("application.applied_at", self.source)
        self.assertNotIn("SET evaluation_reference_at = now()", self.source)
        self.assertNotIn("'[]'::jsonb", self.source)

    def test_adds_report_snapshot_and_run_fingerprint_without_raw_resume(self) -> None:
        for field in (
            "evaluation_reference_at",
            "evaluation_timezone",
            "experience_period_facts_rule_version",
            "experience_period_facts",
            "experience_period_facts_fingerprint",
        ):
            self.assertIn(field, self.source)
        self.assertNotIn("raw_resume", self.source)
        self.assertNotIn("model_response", self.source)
