from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "a8d4f2c7e901_add_public_application_processing_contract.py"
)


def load_migration_module():
    spec = spec_from_file_location("stage8_public_application_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载阶段 8 公开投递迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage8PublicApplicationMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_is_a_single_forward_migration_from_stage7_head(self) -> None:
        self.assertEqual(self.migration.revision, "a8d4f2c7e901")
        self.assertEqual(self.migration.down_revision, "e7f9a1b3c545")

    def test_upgrade_widens_email_and_creates_both_stage8_tables(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        email_change = operation_mock.alter_column.call_args_list[0]
        self.assertEqual(email_change.args[:2], ("candidates", "email"))
        self.assertEqual(email_change.kwargs["existing_type"].length, 100)
        self.assertEqual(email_change.kwargs["type_"].length, 254)

        table_names = [call.args[0] for call in operation_mock.create_table.call_args_list]
        self.assertEqual(
            table_names,
            ["public_application_submissions", "application_processing_runs"],
        )

    def test_migration_declares_required_uniques_checks_indexes_and_frozen_fk(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        required_fragments = (
            "uq_public_application_submissions_application_id",
            "uq_public_application_submissions_resume_id",
            "uq_public_application_submissions_reference",
            "uq_public_application_submissions_idempotency_hash",
            "fk_application_processing_runs_frozen_submission_identity",
            "ck_application_processing_runs_waiting_reason_matches_status",
            "ck_application_processing_runs_failed_has_safe_error",
            "ck_application_processing_runs_warning_codes_allowed",
            "uq_application_processing_runs_active_submission",
            "status IN ('queued', 'running', 'waiting_screening')",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_downgrade_blocks_unsafe_email_narrowing(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        self.assertIn("length(email) > 100", source)
        self.assertIn("STAGE8_CANDIDATE_EMAIL_DOWNGRADE_BLOCKED", source)
