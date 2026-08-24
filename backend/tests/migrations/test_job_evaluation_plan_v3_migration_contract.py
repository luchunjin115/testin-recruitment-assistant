from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
from unittest.mock import Mock, patch

import pytest


VERSIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
DOWN_REVISION = "f2b8c6d1a940"


def _v3_successors() -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []
    for path in VERSIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if re.search(rf"down_revision\s*(?::[^=]+)?=\s*['\"]{DOWN_REVISION}['\"]", source):
            matches.append((path, source))
    return matches


def _load_v3_migration():
    successors = _v3_successors()
    assert len(successors) == 1
    path = successors[0][0]
    spec = spec_from_file_location("job_evaluation_plan_v3_migration", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("无法加载 JobEvaluationPlan 3.0 migration")
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


def test_v3_has_one_forward_revision_after_five_section_job_head() -> None:
    successors = _v3_successors()
    assert len(successors) == 1, "7R-B 必须新增且只能新增一条接在 f2b8c6d1a940 后的 revision"


def test_v3_revision_adds_summary_and_preserves_legacy_history() -> None:
    successors = _v3_successors()
    assert len(successors) == 1, "当前尚无 7R-B migration"
    source = successors[0][1]
    assert "source_review_summary" in source
    assert "structured_coverage" in source
    assert "free_text_coverage" in source
    assert "3.0" in source
    assert "downgrade" in source
    assert "delete" not in source.lower()


def test_v3_upgrade_adds_only_nullable_summary_and_contract_constraints() -> None:
    migration = _load_v3_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.upgrade()

    operation.add_column.assert_called_once()
    added_column = operation.add_column.call_args.args[1]
    assert added_column.name == "source_review_summary"
    assert added_column.nullable is True
    operation.alter_column.assert_called_once()
    altered = operation.alter_column.call_args
    assert altered.args == ("job_evaluation_plans", "structured_coverage")
    assert altered.kwargs["existing_type"].__class__.__name__ == "JSONB"
    assert altered.kwargs["nullable"] is True
    assert altered.kwargs["server_default"] is None
    assert operation.create_check_constraint.call_count == 4
    operation.execute.assert_not_called()


def test_v3_upgrade_stops_before_ddl_for_unknown_legacy_history() -> None:
    migration = _load_v3_migration()
    operation = _operation_mock(found_plan_id=88)

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V3_UNKNOWN_LEGACY_HISTORY",
    ):
        migration.upgrade()

    operation.add_column.assert_not_called()
    operation.alter_column.assert_not_called()
    operation.create_check_constraint.assert_not_called()


def test_v3_downgrade_stops_before_ddl_when_v3_history_exists() -> None:
    migration = _load_v3_migration()
    operation = _operation_mock(found_plan_id=99)

    with patch.object(migration, "op", operation), pytest.raises(
        RuntimeError,
        match="STAGE7_PLAN_V3_DOWNGRADE_BLOCKED",
    ):
        migration.downgrade()

    operation.drop_constraint.assert_not_called()
    operation.alter_column.assert_not_called()
    operation.drop_column.assert_not_called()


def test_v3_downgrade_restores_legacy_shape_without_row_rewrites() -> None:
    migration = _load_v3_migration()
    operation = _operation_mock()

    with patch.object(migration, "op", operation):
        migration.downgrade()

    assert operation.drop_constraint.call_count == 4
    operation.alter_column.assert_called_once()
    operation.drop_column.assert_called_once_with(
        "job_evaluation_plans",
        "source_review_summary",
    )
    operation.execute.assert_not_called()
