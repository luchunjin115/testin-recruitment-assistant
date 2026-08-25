from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def _v4_migration_text() -> str:
    matches = sorted(MIGRATIONS.glob("*_job_evaluation_plan_v4_*.py"))
    assert len(matches) == 1, "7R4-B 必须新增且只能新增一条 4.0 migration"
    return matches[0].read_text(encoding="utf-8")


def _load_v4_migration():
    matches = sorted(MIGRATIONS.glob("*_job_evaluation_plan_v4_*.py"))
    assert len(matches) == 1, "7R4-B 必须新增且只能新增一条 4.0 migration"
    spec = spec_from_file_location("job_evaluation_plan_v4_migration", matches[0])
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 JobEvaluationPlan 4.0 migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operation_mock(*, found_plan_id: int | None = None) -> Mock:
    operation = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = found_plan_id
    connection = Mock()
    connection.execute.return_value = result
    operation.get_bind.return_value = connection
    return operation


def test_v4_migration_extends_current_head_without_rewriting_history() -> None:
    migration = _load_v4_migration()
    assert migration.down_revision == "b4e8c2d7f913"


def test_v4_migration_adds_contract_columns_and_pending_status() -> None:
    text = _v4_migration_text()
    for token in (
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
        "pending_confirmation",
        "4.0",
    ):
        assert token in text


def test_v4_upgrade_adds_only_nullable_payload_columns_and_constraints() -> None:
    migration = _load_v4_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.upgrade()

    assert operation.add_column.call_count == 4
    added_columns = [call.args[1] for call in operation.add_column.call_args_list]
    assert {column.name for column in added_columns} == {
        "requirement_facts",
        "evaluation_criteria",
        "coverage_review_summary",
        "generation_audit",
    }
    assert all(column.nullable is True for column in added_columns)
    operation.execute.assert_not_called()


def test_v4_upgrade_stops_before_ddl_for_unknown_history() -> None:
    migration = _load_v4_migration()
    operation = _operation_mock(found_plan_id=88)

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V4_UNKNOWN_HISTORY",
    ):
        migration.upgrade()

    operation.add_column.assert_not_called()
    operation.alter_column.assert_not_called()
    operation.create_check_constraint.assert_not_called()


def test_v4_downgrade_stops_before_ddl_when_v4_history_exists() -> None:
    migration = _load_v4_migration()
    operation = _operation_mock(found_plan_id=99)

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V4_DOWNGRADE_BLOCKED",
    ):
        migration.downgrade()

    operation.drop_constraint.assert_not_called()
    operation.drop_column.assert_not_called()
    operation.alter_column.assert_not_called()


def test_v4_downgrade_restores_v3_shape_without_row_rewrites() -> None:
    migration = _load_v4_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.downgrade()

    assert operation.drop_column.call_count == 4
    operation.alter_column.assert_called_once()
    assert operation.alter_column.call_args.args == (
        "job_evaluation_plans",
        "items",
    )
    assert operation.alter_column.call_args.kwargs["nullable"] is False
    operation.execute.assert_not_called()
