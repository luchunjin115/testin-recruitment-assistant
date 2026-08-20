from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c4a9d8e7f621_remove_legacy_rubric_system.py"
)


def load_migration_module():
    spec = spec_from_file_location("remove_legacy_rubric_system", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载旧 Rubric 系统删除迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RemoveLegacyRubricSystemMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_follows_current_head(self) -> None:
        self.assertEqual(self.migration.revision, "c4a9d8e7f621")
        self.assertEqual(self.migration.down_revision, "f8c2d0e5b317")

    def test_upgrade_removes_tables_and_embedded_dependencies(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        self.assertEqual(
            [call.args[0] for call in operation_mock.drop_table.call_args_list],
            ["screening_results", "job_screening_rubrics"],
        )
        dropped_columns = {
            (call.args[0], call.args[1])
            for call in operation_mock.drop_column.call_args_list
        }
        self.assertEqual(
            dropped_columns,
            {
                ("applications", "ai_status"),
                ("applications", "current_screening_result_id"),
                ("stage_histories", "screening_result_id"),
                ("stage_histories", "overrides_ai_recommendation"),
                ("reports", "screening_id"),
            },
        )
        report_default = operation_mock.alter_column.call_args_list[0]
        self.assertEqual(report_default.args[:2], ("reports", "report_type"))
        self.assertEqual(report_default.kwargs["server_default"], "general")

    def test_downgrade_recreates_empty_legacy_structure(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.downgrade()

        created_tables = {
            call.args[0] for call in operation_mock.create_table.call_args_list
        }
        self.assertEqual(
            created_tables,
            {"job_screening_rubrics", "screening_results"},
        )
        restored_columns = {
            (call.args[0], call.args[1].name)
            for call in operation_mock.add_column.call_args_list
        }
        self.assertEqual(
            restored_columns,
            {
                ("applications", "ai_status"),
                ("applications", "current_screening_result_id"),
                ("stage_histories", "screening_result_id"),
                ("stage_histories", "overrides_ai_recommendation"),
                ("reports", "screening_id"),
            },
        )
        self.assertEqual(
            operation_mock.alter_column.call_args.kwargs["server_default"],
            "screening",
        )
