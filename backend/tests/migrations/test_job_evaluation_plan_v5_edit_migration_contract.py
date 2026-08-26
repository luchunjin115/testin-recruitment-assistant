from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b4c6d8e0f212_add_v5_plan_edit_version_history.py"
)


def _load_migration():
    spec = spec_from_file_location("v5_plan_edit_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 7R5-D migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operation_mock(
    *,
    invalid_plan_id: int | None = None,
    duplicate: tuple[int, str] | None = None,
) -> Mock:
    operation = Mock()
    invalid_result = Mock()
    invalid_result.scalar_one_or_none.return_value = invalid_plan_id
    duplicate_result = Mock()
    duplicate_result.first.return_value = duplicate
    connection = Mock()
    connection.execute.side_effect = [invalid_result, duplicate_result]
    operation.get_bind.return_value = connection
    return operation


def test_v5_edit_migration_extends_v5_persistence_head() -> None:
    migration = _load_migration()
    assert migration.revision == "b4c6d8e0f212"
    assert migration.down_revision == "a3b5c7d9e101"


def test_v5_edit_upgrade_replaces_uniqueness_and_adds_hard_constraints() -> None:
    migration = _load_migration()
    operation = _operation_mock()
    with patch.object(migration, "op", operation):
        migration.upgrade()

    operation.drop_constraint.assert_any_call(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        type_="unique",
    )
    assert operation.create_index.call_count == 2
    created_indexes = {
        call.args[0]: call for call in operation.create_index.call_args_list
    }
    assert set(created_indexes) == {
        "uq_job_evaluation_plans_legacy_job_input",
        "uq_job_evaluation_plans_v5_job_input_edit_version",
    }
    assert created_indexes[
        "uq_job_evaluation_plans_legacy_job_input"
    ].args[2] == ["job_id", "input_fingerprint"]
    assert created_indexes[
        "uq_job_evaluation_plans_v5_job_input_edit_version"
    ].args[2] == ["job_id", "input_fingerprint", "edit_version"]
    assert all(call.kwargs["unique"] for call in created_indexes.values())
    assert all(
        call.kwargs["postgresql_where"] is not None
        for call in created_indexes.values()
    )
    created_checks = {
        call.args[0] for call in operation.create_check_constraint.call_args_list
    }
    assert {
        "ck_job_evaluation_plans_legacy_has_no_v5_payload",
        "ck_job_evaluation_plans_v5_positive_edit_version",
        "ck_job_evaluation_plans_v5_complete_payload",
        "ck_job_evaluation_plans_v5_no_partial_failed_payload",
        "ck_job_evaluation_plans_v5_confirmation_timestamp",
    } == created_checks
    operation.add_column.assert_not_called()
    operation.execute.assert_not_called()


def test_v5_edit_upgrade_stops_before_ddl_for_invalid_v5_history() -> None:
    migration = _load_migration()
    operation = _operation_mock(invalid_plan_id=88)
    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V5_EDIT_CONTRACT_INVALID_HISTORY",
    ):
        migration.upgrade()

    operation.drop_constraint.assert_not_called()
    operation.create_index.assert_not_called()


def test_v5_edit_downgrade_blocks_multiple_versions_before_ddl() -> None:
    migration = _load_migration()
    operation = _operation_mock(duplicate=(7, "a" * 64))
    connection = operation.get_bind.return_value
    connection.execute.side_effect = None
    duplicate_result = Mock()
    duplicate_result.first.return_value = (7, "a" * 64)
    connection.execute.return_value = duplicate_result

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V5_EDIT_DOWNGRADE_BLOCKED",
    ):
        migration.downgrade()

    operation.drop_constraint.assert_not_called()
    operation.create_unique_constraint.assert_not_called()


def test_v5_edit_downgrade_restores_previous_unique_constraint() -> None:
    migration = _load_migration()
    operation = _operation_mock()
    connection = operation.get_bind.return_value
    connection.execute.side_effect = None
    duplicate_result = Mock()
    duplicate_result.first.return_value = None
    connection.execute.return_value = duplicate_result

    with patch.object(migration, "op", operation):
        migration.downgrade()

    operation.drop_index.assert_any_call(
        "uq_job_evaluation_plans_v5_job_input_edit_version",
        table_name="job_evaluation_plans",
    )
    operation.drop_index.assert_any_call(
        "uq_job_evaluation_plans_legacy_job_input",
        table_name="job_evaluation_plans",
    )
    operation.create_unique_constraint.assert_called_once_with(
        "uq_job_evaluation_plans_job_input_fingerprint",
        "job_evaluation_plans",
        ["job_id", "input_fingerprint"],
    )
    operation.drop_column.assert_not_called()
