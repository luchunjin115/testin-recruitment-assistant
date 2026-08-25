from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.schemas.screening import ScreeningWaitingReason
from app.services.screening_evaluation_service import screening_evaluation_service
from app.services.screening_service import screening_service


def _v4_classifier():
    method = getattr(screening_service, "_classify_v4_plan", None)
    assert method is not None, "7R4-E 缺少 4.0 计划门禁"
    return method


def test_screening_gate_requires_current_ready_v4_contract() -> None:
    source = inspect.getsource(_v4_classifier())
    assert 'schema_version != "4.0"' in source
    assert "pending_confirmation" in source


def test_screening_gate_no_longer_accepts_v3_as_current_input() -> None:
    source = inspect.getsource(_v4_classifier())
    assert 'schema_version != "3.0"' not in source


def test_screening_context_reads_requirement_facts_not_legacy_items() -> None:
    source = inspect.getsource(screening_service._build_context)
    assert "requirement_facts" in source
    assert '"items": plan.items' not in source


def test_screening_evaluation_uses_fact_id_as_requirement_key() -> None:
    source = inspect.getsource(screening_evaluation_service._prepare_inputs)
    assert "RequirementFact" in source
    assert "fact_id" in source


def test_screening_keeps_criteria_as_display_grouping_only() -> None:
    source = inspect.getsource(screening_evaluation_service._prepare_inputs)
    assert "evaluation_criteria" in source
    for forbidden in ("criterion_weight", "criterion_score", "criterion_threshold"):
        assert forbidden not in source


def test_legacy_plans_are_read_only_and_block_new_screening() -> None:
    source = inspect.getsource(_v4_classifier())
    assert "PLAN_CONTRACT_OUTDATED" in source
    assert 'schema_version != "4.0"' in source


@pytest.mark.parametrize("schema_version", ["1.0", "2.0", "3.0"])
def test_every_legacy_contract_is_blocked_at_runtime(schema_version: str) -> None:
    legacy_plan = SimpleNamespace(schema_version=schema_version)

    ready, reason = _v4_classifier()(
        current_snapshot=SimpleNamespace(),
        current_jd_fingerprint="a" * 64,
        current=legacy_plan,
        latest=legacy_plan,
    )

    assert ready is False
    assert reason is ScreeningWaitingReason.PLAN_CONTRACT_OUTDATED
