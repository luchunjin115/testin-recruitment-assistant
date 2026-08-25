from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "stage7_7r4a_capacity_baseline.py"
SPEC = importlib.util.spec_from_file_location("stage7_7r4a_capacity", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
CAPACITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPACITY)


def _payload() -> dict:
    return CAPACITY.build_capacity_baseline()


def test_capacity_baseline_uses_twenty_frozen_cases_and_six_targeted_cases() -> None:
    payload = _payload()
    assert payload["sample_count"] == 20
    assert payload["targeted_case_ids"] == [
        "J5-03",
        "J5-07",
        "J5-14",
        "J5-17",
        "J5-19",
        "J5-20",
    ]


def test_capacity_baseline_counts_all_245_manual_fact_annotations() -> None:
    payload = _payload()
    assert payload["aggregate"]["manual_fact_count"]["sum"] == 245
    assert payload["aggregate"]["manual_fact_count"]["max"] == 31


def test_capacity_baseline_excludes_public_notes_from_snapshot_and_fingerprint() -> None:
    payload = _payload()
    assert payload["public_notes_excluded_from_every_snapshot"] is True
    assert payload["public_notes_excluded_from_every_fingerprint"] is True


def test_capacity_baseline_marks_legacy_thirty_item_limit_as_wrong_for_v4() -> None:
    payload = _payload()
    row = next(item for item in payload["cases"] if item["case_id"] == "J5-20")
    assert row["manual_fact_count"] == 31
    assert row["legacy_30_item_limit_would_reject"] is True
    assert row["v4_expected_outcome"] == "pending_confirmation+overly_broad_jd"


def test_capacity_baseline_is_strictly_offline() -> None:
    payload = _payload()
    assert payload["real_model_call_count"] == 0
    assert payload["adapter_instantiated"] is False
    assert payload["api_key_loaded"] is False
    assert payload["result_file_written"] is False


def test_capacity_limit_candidates_that_can_reject_legal_jd_require_confirmation() -> None:
    payload = _payload()
    candidates = payload["technical_limit_recommendations"]
    assert candidates["input_snapshot_serialized_chars"]["requires_product_confirmation"] is True
    assert candidates["source_unit_count"]["requires_product_confirmation"] is True
    assert candidates["fact_count"]["requires_product_confirmation"] is True
    assert candidates["criterion_count"]["requires_product_confirmation"] is True
