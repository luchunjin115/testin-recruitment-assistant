from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_7r5i2_preflight as preflight  # noqa: E402


def test_preflight_replays_every_available_response_without_key_adapter_or_write() -> None:
    payload = asyncio.run(preflight.build_preflight_payload())
    assert payload["source_raw_attempt_count"] == 29
    assert payload["replayed_source_response_count"] == 29
    assert payload["summaries"]["plans"]["total_case_count"] == 10
    assert payload["summaries"]["plans"]["source_response_count"] == 10
    assert payload["summaries"]["reports"]["total_case_count"] == 20
    assert payload["summaries"]["reports"]["source_response_count"] == 13
    assert payload["summaries"]["stability"]["total_case_count"] == 15
    assert payload["summaries"]["stability"]["source_response_count"] == 6
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["quality_conclusion_allowed"] is False


def test_preflight_does_not_copy_raw_responses_or_sensitive_diagnostics() -> None:
    payload = asyncio.run(preflight.build_preflight_payload())
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "stack_trace" not in serialized
    assert "chain_of_thought" not in serialized
    for category in ("plan_records", "report_records", "stability_records"):
        assert all("raw_response" not in record for record in payload[category])
        assert all("raw_response_sha256" in record for record in payload[category] if record["raw_response_available"])


def test_preflight_rejects_any_source_raw_hash_drift(tmp_path: Path) -> None:
    tampered = tmp_path / "tampered-raw.json"
    tampered.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256"):
        asyncio.run(preflight.build_preflight_payload(source_path=tampered))


def test_preflight_source_case_ids_are_complete_and_unique() -> None:
    payload = asyncio.run(preflight.build_preflight_payload())
    assert [item["case_id"] for item in payload["plan_records"]] == [
        f"P{index:02d}" for index in range(10)
    ]
    assert [item["case_id"] for item in payload["report_records"]] == [
        f"R{index:02d}" for index in range(20)
    ]
    assert len({item["case_id"] for item in payload["stability_records"]}) == 15


def test_r1c_replays_only_six_frozen_structure_cases_and_crosses_quantity_gate() -> None:
    payload = asyncio.run(preflight.build_r1c_replay_payload())
    assert payload["target_case_ids"] == [
        "R00",
        "R09",
        "R16",
        "S00-1",
        "S00-2",
        "S00-3",
    ]
    assert payload["supporting_plan_case_ids"] == ["P00", "P06", "P09"]
    assert payload["summary"]["target_case_count"] == 6
    assert payload["summary"]["quantity_gate_crossed_count"] == 6
    assert payload["summary"]["current_schema_rejected_count"] == 0
    assert all(record["current_schema_accepted"] for record in payload["records"])
    assert all(record["quantity_gate_crossed"] for record in payload["records"])
    assert all(
        max(record["auxiliary_counts"].values()) <= 20
        for record in payload["records"]
    )


def test_r1c_preserves_next_gate_failures_without_claiming_quality_pass() -> None:
    payload = asyncio.run(preflight.build_r1c_replay_payload())
    assert payload["summary"] == {
        "target_case_count": 6,
        "quantity_gate_crossed_count": 6,
        "full_report_accepted_count": 0,
        "next_service_gate_rejected_count": 6,
        "current_schema_rejected_count": 0,
    }
    assert {
        record["case_id"]: record["current_report_error_message"]
        for record in payload["records"]
    } == {
        "R00": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "R09": "5.0 单项高分与未发现证据说明方向明显矛盾",
        "R16": "5.0 综合说明包含当前 Resume 证据无法支持的事实",
        "S00-1": "AI 初筛理由与引用证据缺少可核对联系",
        "S00-2": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "S00-3": "5.0 单项高分与未发现证据说明方向明显矛盾",
    }
    assert payload["pricing_gate_allowed"] is False
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_or_service_adjudication_required"] is True
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["raw_response_copied"] is False
    assert payload["historical_result_hashes_before"] == payload[
        "historical_result_hashes_after"
    ]


def test_r1c_diagnostic_has_no_raw_response_prompt_or_stack() -> None:
    payload = asyncio.run(preflight.build_r1c_replay_payload())
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized


def test_r1c_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = asyncio.run(preflight.build_r1c_replay_payload())
    target = tmp_path / "r1c.json"
    preflight.write_r1c_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R1-C"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r1c_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r1c_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )


def test_r1c_build_uses_frozen_contract_without_loading_external_settings() -> None:
    with patch.object(
        preflight,
        "execution_contract",
        wraps=preflight.execution_contract,
    ) as execution:
        payload = asyncio.run(preflight.build_r1c_replay_payload())
    execution.assert_called_once_with()
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False


def test_r2e_replays_only_twelve_frozen_duration_rejections() -> None:
    payload = asyncio.run(preflight.build_r2e_replay_payload())
    assert payload["target_case_ids"] == [
        "R00",
        "R05",
        "R07",
        "R15",
        "R17",
        "R18",
        "R19",
        "S00-1",
        "S00-2",
        "S00-3",
        "S04-2",
        "S04-3",
    ]
    assert payload["supporting_plan_case_ids"] == ["P00", "P04", "P05", "P07"]
    assert all(
        record["previous_gate_error_message"]
        == "AI 年限结论与后端经历时间事实冲突"
        for record in payload["records"]
    )
    assert {
        record["case_id"]: record["previous_gate_source"]
        for record in payload["records"]
    } == {
        "R00": "7R5-I2-R1-C",
        "R05": "7R5-I2-C",
        "R07": "7R5-I2-C",
        "R15": "7R5-I2-C",
        "R17": "7R5-I2-C",
        "R18": "7R5-I2-C",
        "R19": "7R5-I2-C",
        "S00-1": "7R5-I2-R1-C",
        "S00-2": "7R5-I2-R1-C",
        "S00-3": "7R5-I2-R1-C",
        "S04-2": "7R5-I2-C",
        "S04-3": "7R5-I2-C",
    }


def test_r2e_removes_old_duration_gate_without_claiming_full_quality_pass() -> None:
    payload = asyncio.run(preflight.build_r2e_replay_payload())
    assert payload["summary"] == {
        "target_case_count": 12,
        "old_duration_gate_removed_count": 12,
        "old_duration_gate_still_rejected_count": 0,
        "full_report_accepted_count": 3,
        "next_service_gate_rejected_count": 9,
        "future_human_quality_review_case_count": 2,
    }
    assert all(record["old_duration_gate_removed"] for record in payload["records"])
    assert [
        record["case_id"]
        for record in payload["records"]
        if record["current_report_status"] == "succeeded"
    ] == ["R05", "R19", "S04-2"]
    assert payload["pricing_gate_allowed"] is False
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_or_service_adjudication_required"] is True


def test_r2e_records_each_next_gate_and_preserves_r15_r19_model_risk() -> None:
    payload = asyncio.run(preflight.build_r2e_replay_payload())
    assert {
        record["case_id"]: record["current_report_error_message"]
        for record in payload["records"]
    } == {
        "R00": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "R05": None,
        "R07": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "R15": "AI 初筛理由包含 Resume 无法支持的事实",
        "R17": "AI 初筛理由包含 Resume 无法支持的数值事实",
        "R18": "5.0 综合说明包含当前 Resume 证据无法支持的事实",
        "R19": None,
        "S00-1": "AI 初筛理由与引用证据缺少可核对联系",
        "S00-2": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "S00-3": "5.0 单项高分与未发现证据说明方向明显矛盾",
        "S04-2": None,
        "S04-3": "AI 初筛理由包含 Resume 无法支持的数值事实",
    }
    assert payload["model_risk_case_ids"] == ["R15", "R19"]
    assert [
        record["case_id"]
        for record in payload["records"]
        if record["future_human_quality_review_required"]
    ] == ["R15", "R19"]
    assert payload["replay_limitations"] == {
        "responses_were_generated_before_prompt_v3": True,
        "prompt_v3_real_model_behavior_evaluated": False,
        "service_acceptance_proves_content_quality": False,
        "r15_r19_require_future_human_quality_review": True,
    }


def test_r2e_is_zero_call_and_does_not_copy_sensitive_content() -> None:
    payload = asyncio.run(preflight.build_r2e_replay_payload())
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["execution_contract"]["report_prompt_version"] == (
        "screening_evaluation_lightweight_v3"
    )
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["raw_response_copied"] is False
    assert payload["historical_result_hashes_before"] == payload[
        "historical_result_hashes_after"
    ]


def test_r2e_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = asyncio.run(preflight.build_r2e_replay_payload())
    target = tmp_path / "r2e.json"
    preflight.write_r2e_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R2-E"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r2e_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r2e_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )
