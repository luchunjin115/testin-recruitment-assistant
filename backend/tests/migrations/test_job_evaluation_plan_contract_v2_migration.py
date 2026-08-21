from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "e4c7a1b9d632_version_job_evaluation_plan_contract_v2.py"
)


def load_migration_module():
    spec = spec_from_file_location("version_job_evaluation_plan_v2", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 JobEvaluationPlan v2 migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JobEvaluationPlanContractV2MigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_is_forward_only_from_current_head(self) -> None:
        self.assertEqual(self.migration.revision, "e4c7a1b9d632")
        self.assertEqual(self.migration.down_revision, "d9a1f4c7e820")

    def test_upgrade_adds_nullable_audit_and_switches_unique_contract(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        operation_mock.add_column.assert_called_once()
        added_column = operation_mock.add_column.call_args.args[1]
        self.assertEqual(added_column.name, "free_text_coverage")
        self.assertTrue(added_column.nullable)
        operation_mock.drop_constraint.assert_called_once_with(
            "uq_job_evaluation_plans_job_jd_fingerprint",
            "job_evaluation_plans",
            type_="unique",
        )
        operation_mock.create_unique_constraint.assert_called_once_with(
            "uq_job_evaluation_plans_job_input_fingerprint",
            "job_evaluation_plans",
            ["job_id", "input_fingerprint"],
        )
        self.assertEqual(operation_mock.create_check_constraint.call_count, 2)
        operation_mock.execute.assert_not_called()

    def test_downgrade_restores_old_constraint_without_rewriting_rows(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.downgrade()

        operation_mock.drop_column.assert_called_once_with(
            "job_evaluation_plans",
            "free_text_coverage",
        )
        operation_mock.create_unique_constraint.assert_called_once_with(
            "uq_job_evaluation_plans_job_jd_fingerprint",
            "job_evaluation_plans",
            ["job_id", "jd_fingerprint"],
        )
        self.assertEqual(operation_mock.drop_constraint.call_count, 3)
        operation_mock.execute.assert_not_called()
