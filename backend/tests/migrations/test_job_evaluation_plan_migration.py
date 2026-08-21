from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "a6d4e8f2c713_add_job_evaluation_plans.py"
)


def load_migration_module():
    spec = spec_from_file_location("add_job_evaluation_plans", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 JobEvaluationPlan migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JobEvaluationPlanMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_is_forward_only_from_legacy_cleanup_head(self) -> None:
        self.assertEqual(self.migration.revision, "a6d4e8f2c713")
        self.assertEqual(self.migration.down_revision, "c4a9d8e7f621")

    def test_upgrade_creates_only_new_plan_structure(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        operation_mock.create_table.assert_called_once()
        self.assertEqual(
            operation_mock.create_table.call_args.args[0],
            "job_evaluation_plans",
        )
        created_indexes = {
            call.args[0]: call for call in operation_mock.create_index.call_args_list
        }
        self.assertEqual(
            set(created_indexes),
            {
                "ix_job_evaluation_plans_job_id",
                "ix_job_evaluation_plans_status",
                "uq_job_evaluation_plans_current_job",
            },
        )
        self.assertTrue(
            created_indexes["uq_job_evaluation_plans_current_job"].kwargs["unique"]
        )
        operation_mock.drop_table.assert_not_called()
        operation_mock.drop_column.assert_not_called()

    def test_downgrade_removes_only_new_plan_table(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.downgrade()

        operation_mock.drop_table.assert_called_once_with("job_evaluation_plans")
        self.assertEqual(operation_mock.drop_index.call_count, 3)
        operation_mock.create_table.assert_not_called()
        operation_mock.drop_column.assert_not_called()
