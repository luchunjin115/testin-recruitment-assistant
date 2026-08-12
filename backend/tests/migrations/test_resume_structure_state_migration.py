from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import call, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "f5a7c9e2d104_add_resume_structure_state.py"
)


def load_migration_module():
    spec = spec_from_file_location("resume_structure_state_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载 Resume 结构化状态迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResumeStructureStateMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_follows_current_head(self) -> None:
        self.assertEqual(self.migration.revision, "f5a7c9e2d104")
        self.assertEqual(self.migration.down_revision, "d3f6a8c1b204")

    def test_upgrade_adds_six_columns_and_one_index(self) -> None:
        with (
            patch.object(self.migration.op, "add_column") as add_column,
            patch.object(self.migration.op, "create_index") as create_index,
            patch.object(self.migration.op, "f", side_effect=lambda value: value),
        ):
            self.migration.upgrade()

        columns = [called.args[1] for called in add_column.call_args_list]
        self.assertEqual(
            [column.name for column in columns],
            [
                "structure_status",
                "structure_error",
                "structure_attempt_id",
                "structure_started_at",
                "structured_at",
                "structure_schema_version",
            ],
        )
        self.assertFalse(columns[0].nullable)
        self.assertEqual(columns[0].server_default.arg, "not_started")
        create_index.assert_called_once_with(
            "ix_resumes_structure_status",
            "resumes",
            ["structure_status"],
            unique=False,
        )

    def test_downgrade_removes_only_new_index_and_columns(self) -> None:
        with (
            patch.object(self.migration.op, "drop_index") as drop_index,
            patch.object(self.migration.op, "drop_column") as drop_column,
            patch.object(self.migration.op, "f", side_effect=lambda value: value),
        ):
            self.migration.downgrade()

        drop_index.assert_called_once_with(
            "ix_resumes_structure_status",
            table_name="resumes",
        )
        self.assertEqual(
            drop_column.call_args_list,
            [
                call("resumes", "structure_schema_version"),
                call("resumes", "structured_at"),
                call("resumes", "structure_started_at"),
                call("resumes", "structure_attempt_id"),
                call("resumes", "structure_error"),
                call("resumes", "structure_status"),
            ],
        )
