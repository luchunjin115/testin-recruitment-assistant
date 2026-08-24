from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b4e8c2d7f913_add_screening_waiting_reason.py"
)


def _load_migration():
    spec = spec_from_file_location("screening_waiting_reason_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 Screening waiting reason migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_nullable_reason_and_status_constraint_only() -> None:
    migration = _load_migration()
    operation = Mock()

    with patch.object(migration, "op", operation):
        migration.upgrade()

    operation.add_column.assert_called_once()
    table_name, column = operation.add_column.call_args.args
    assert table_name == "screening_runs"
    assert column.name == "waiting_reason"
    assert column.nullable is True
    operation.create_check_constraint.assert_called_once()
    constraint_call = operation.create_check_constraint.call_args
    assert constraint_call.args[0] == "ck_screening_runs_waiting_reason_matches_status"
    assert "plan_contract_outdated" in constraint_call.args[2]
    assert "job_closed" in constraint_call.args[2]
    operation.execute.assert_not_called()


def test_downgrade_removes_only_reason_constraint_and_column() -> None:
    migration = _load_migration()
    operation = Mock()

    with patch.object(migration, "op", operation):
        migration.downgrade()

    operation.drop_constraint.assert_called_once_with(
        "ck_screening_runs_waiting_reason_matches_status",
        "screening_runs",
        type_="check",
    )
    operation.drop_column.assert_called_once_with("screening_runs", "waiting_reason")
    operation.execute.assert_not_called()
