from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "f8c2d0e5b317_retire_legacy_application_contract.py"
)


def load_migration_module():
    spec = spec_from_file_location(
        "legacy_application_contract_retirement_migration",
        MIGRATION_PATH,
    )
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载 legacy Application 合同退役迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LegacyApplicationContractRetirementMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_follows_applied_stage7_revision(self) -> None:
        self.assertEqual(self.migration.revision, "f8c2d0e5b317")
        self.assertEqual(self.migration.down_revision, "e7b1c9d4a206")

    def test_upgrade_guards_cleanup_and_retires_legacy_contract(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        guard_sql = str(operation_mock.execute.call_args.args[0])
        self.assertIn("legacy Application rows must be removed", guard_sql)
        self.assertIn("legacy ScreeningResult rows must be removed", guard_sql)

        dropped_columns = {
            (call.args[0], call.args[1])
            for call in operation_mock.drop_column.call_args_list
        }
        self.assertIn(("applications", "legacy_stage"), dropped_columns)

        not_null_columns = {
            (call.args[0], call.args[1])
            for call in operation_mock.alter_column.call_args_list
            if call.kwargs.get("nullable") is False
        }
        self.assertEqual(
            not_null_columns,
            {
                ("applications", "current_resume_id"),
                ("screening_results", "application_id"),
                ("screening_results", "resume_id"),
            },
        )

        checks = {
            call.args[0]: call.args[2]
            for call in operation_mock.create_check_constraint.call_args_list
        }
        self.assertNotIn("legacy_migration", checks["ck_applications_source_allowed"])
        self.assertNotIn(
            "legacy_migration",
            checks["ck_job_screening_rubrics_source_allowed"],
        )
        self.assertNotIn(
            "migration",
            checks["ck_stage_histories_actor_type_allowed"],
        )

        running_index = next(
            call
            for call in operation_mock.create_index.call_args_list
            if call.args[0] == "uq_screening_results_running_application"
        )
        self.assertEqual(
            str(running_index.kwargs["postgresql_where"]),
            "execution_status = 'screening'",
        )
