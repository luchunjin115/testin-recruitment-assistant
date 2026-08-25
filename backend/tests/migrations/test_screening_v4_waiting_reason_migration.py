from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "d6f4a2b8e913_add_screening_v4_pending_reason.py"
)


def _load_migration():
    spec = spec_from_file_location("screening_v4_waiting_reason_migration", MIGRATION)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 Screening 4.0 waiting reason migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operation_mock(*, has_v4_reason: bool = False) -> Mock:
    operation = Mock()
    result = Mock()
    result.scalar_one.return_value = has_v4_reason
    connection = Mock()
    connection.execute.return_value = result
    operation.get_bind.return_value = connection
    return operation


def test_migration_extends_v4_plan_head_and_adds_pending_reason() -> None:
    migration = _load_migration()
    assert migration.down_revision == "c7d9e2f4a681"
    assert "plan_pending_confirmation" in migration._V4_EXPRESSION
    assert "plan_pending_confirmation" not in migration._V3_EXPRESSION


def test_upgrade_only_replaces_waiting_reason_constraint() -> None:
    migration = _load_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.upgrade()

    operation.drop_constraint.assert_called_once_with(
        "ck_screening_runs_waiting_reason_matches_status",
        "screening_runs",
        type_="check",
    )
    operation.create_check_constraint.assert_called_once()
    assert "plan_pending_confirmation" in operation.create_check_constraint.call_args.args[2]
    operation.add_column.assert_not_called()
    operation.execute.assert_not_called()


def test_downgrade_blocks_before_ddl_when_pending_reason_history_exists() -> None:
    migration = _load_migration()
    operation = _operation_mock(has_v4_reason=True)

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_SCREENING_V4_DOWNGRADE_BLOCKED",
    ):
        migration.downgrade()

    operation.drop_constraint.assert_not_called()
    operation.create_check_constraint.assert_not_called()


def test_downgrade_restores_previous_constraint_without_rewriting_rows() -> None:
    migration = _load_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.downgrade()

    operation.drop_constraint.assert_called_once()
    assert "plan_pending_confirmation" not in operation.create_check_constraint.call_args.args[2]
    operation.execute.assert_not_called()
