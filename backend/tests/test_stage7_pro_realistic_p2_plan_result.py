from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.fixtures.stage7_pro_realistic_quality_samples import (
    EXPECTED_NORMALIZED_FINGERPRINT,
    PLAN_JDS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-09-01-stage7-pro-realistic-p2-plan-raw-results.json"
)
REVIEW_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-09-01-stage7-pro-realistic-p2-plan-review.md"
)
CONFIRMATION_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-09-01-stage7-pro-realistic-p2-confirmed-plans.json"
)


def _result() -> dict:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_p2_result_keeps_identity_model_cost_and_stop_point() -> None:
    result = _result()

    assert result["stage"] == "stage7-pro-realistic-quality"
    assert result["batch"] == "P2"
    assert result["mode"] == "real_plan_raw"
    assert result["status"] == "completed"
    assert result["source_fixture_fingerprint"] == EXPECTED_NORMALIZED_FINGERPRINT
    assert result["model"] == "deepseek-v4-pro"
    assert result["pricing"]["selected_tier"] == "peak"
    assert result["attempt_summary"] == {
        "scheduled_business_call_count": 5,
        "executed_business_call_count": 5,
        "api_attempt_count": 5,
        "succeeded_attempt_count": 5,
        "failed_attempt_count": 0,
        "infrastructure_retry_count": 0,
        "input_tokens": 21324,
        "cache_hit_input_tokens": 12288,
        "cache_miss_input_tokens": 9036,
        "output_tokens": 7878,
        "estimated_spend_usd": 0.043665072,
        "failed_attempt_reserve_usd": 0.0,
    }
    assert result["attempt_summary"]["estimated_spend_usd"] <= result["monetary_cap_usd"]
    assert result["requires_user_plan_review"] is True
    assert result["report_calls_allowed"] is False
    assert result["postgresql_write_count"] == 0
    assert result["api_key_persisted"] is False


def test_all_five_plans_passed_current_structure_source_and_year_boundaries() -> None:
    result = _result()
    jobs = {item["case_id"]: item for item in PLAN_JDS}

    assert [item["case_id"] for item in result["plans"]] == list(jobs)
    assert [item["criteria_count"] for item in result["plans"]] == [14, 12, 12, 12, 12]
    for plan in result["plans"]:
        assert plan["status"] == "succeeded"
        assert plan["all_criteria_traceable"] is True
        assert plan["business_call_count"] == 1
        assert plan["adapter_attempt_count"] == 1
        assert plan["infrastructure_retry_count"] == 0
        assert 5 <= plan["criteria_count"] <= 30
        assert [item["criterion_id"] for item in plan["criteria"]] == [
            f"criterion:{index:04d}"
            for index in range(1, plan["criteria_count"] + 1)
        ]
        job = jobs[plan["case_id"]]
        for criterion in plan["criteria"]:
            for source in criterion["sources"]:
                assert source["source_quote"] in job[source["source_field"]]
                assert "3 年以上" not in source["source_quote"]
            assert job["public_notes"] not in json.dumps(
                criterion, ensure_ascii=False
            )


def test_attempt_audit_uses_only_pro_and_contains_no_secret() -> None:
    result = _result()
    assert len(result["attempt_audit"]) == 5
    for attempt in result["attempt_audit"]:
        assert attempt["result"] == "succeeded"
        assert attempt["attempt_number"] == 1
        assert attempt["requested_model"] == "deepseek-v4-pro"
        assert attempt["model"] == "deepseek-v4-pro"
        assert attempt["finish_reason"] == "stop"
        assert attempt["input_tokens"] > 0
        assert attempt["output_tokens"] > 0
        assert attempt["cost_estimate"]["complete"] is True

    serialized = RESULT_PATH.read_text(encoding="utf-8").lower()
    assert "deepseek_api_key" not in serialized
    assert '"api_key"' not in serialized
    assert "sk-" not in serialized


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_review_card_contains_every_plan_and_records_user_confirmation() -> None:
    review = REVIEW_PATH.read_text(encoding="utf-8")
    for job in PLAN_JDS:
        assert f"## {job['case_id']}：{job['title']}" in review
    assert review.count("用户结论：按当前计划确认") == 5
    assert "confirmed snapshots 已冻结" in review
    assert "P3 报告调用尚未单独授权" in review


def test_confirmed_snapshots_bind_the_exact_p2_plans_and_keep_p3_closed() -> None:
    raw = _result()
    confirmation = json.loads(CONFIRMATION_PATH.read_text(encoding="utf-8"))
    raw_plans = {item["case_id"]: item for item in raw["plans"]}

    assert confirmation["status"] == "complete"
    assert confirmation["confirmed_plan_count"] == 5
    assert confirmation["source_fixture_fingerprint"] == EXPECTED_NORMALIZED_FINGERPRINT
    assert confirmation["source_raw_structured_sha256"] == _fingerprint(raw)
    assert confirmation["all_warnings_acknowledged"] is True
    assert confirmation["p3_input_ready"] is True
    assert confirmation["p3_report_calls_authorized"] is False
    assert confirmation["real_model_call_count"] == 0
    assert confirmation["postgresql_write_count"] == 0

    for snapshot in confirmation["plans"]:
        raw_plan = raw_plans[snapshot["case_id"]]
        assert snapshot["status"] == "confirmed"
        assert snapshot["confirmed_by"] == "project_owner_user"
        assert snapshot["user_directive"] == "全部按当前计划确认"
        assert snapshot["warnings_acknowledged"] is True
        assert snapshot["warning_count"] == len(raw_plan["warnings"])
        assert snapshot["plan"] == {
            "schema_version": "5.0",
            "criteria": raw_plan["criteria"],
        }
        assert snapshot["snapshot_sha256"] == _fingerprint(snapshot["plan"])
