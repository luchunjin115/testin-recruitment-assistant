from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b9e2f4a6c801_add_stage9_pipeline_contract.py"
)


def load_migration_module():
    spec = spec_from_file_location("stage9_pipeline_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载阶段 9 pipeline migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage9PipelineMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()
        self.source = MIGRATION_PATH.read_text(encoding="utf-8")

    def test_revision_is_one_forward_step_from_stage8_head(self) -> None:
        self.assertEqual(self.migration.revision, "b9e2f4a6c801")
        self.assertEqual(self.migration.down_revision, "a8d4f2c7e901")

    def test_upgrade_has_preflight_backfill_and_no_synthetic_business_rows(self) -> None:
        self.assertIn("STAGE9_UNEXPLAINED_ENDED_APPLICATIONS", self.source)
        self.assertIn("final_outcome = 'screening_rejected'", self.source)
        self.assertIn("lifecycle_status = 'ended'", self.source)
        self.assertNotIn("INSERT INTO interview_records", self.source)
        self.assertNotIn("INSERT INTO offer_records", self.source)

    def test_required_tables_constraints_and_partial_indexes_are_declared(self) -> None:
        required_fragments = (
            '"interview_records"',
            '"offer_records"',
            "uq_interview_records_application_round",
            "uq_interview_records_one_scheduled_per_application",
            "status = 'scheduled'",
            "uq_offer_records_application_version",
            "uq_offer_records_one_active_per_application",
            "status IN ('draft', 'sent', 'accepted')",
            "sa.Numeric(14, 2)",
            "sa.Numeric(4, 1)",
            "ck_applications_lifecycle_final_outcome_consistent",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)

    def test_downgrade_blocks_destructive_stage9_data_loss(self) -> None:
        self.assertIn("STAGE9_PIPELINE_DOWNGRADE_BLOCKED", self.source)
        self.assertIn("STAGE9_APPLICATION_DOWNGRADE_BLOCKED", self.source)
        self.assertIn("STAGE9_HISTORY_DOWNGRADE_BLOCKED", self.source)
