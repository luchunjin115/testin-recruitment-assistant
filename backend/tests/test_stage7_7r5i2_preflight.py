from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
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


def test_preflight_accepts_source_raw_with_crlf_byte_drift(tmp_path: Path) -> None:
    source = preflight.RAW_RESULT_PATH.read_text(encoding="utf-8")
    crlf_copy = tmp_path / "crlf-raw.json"
    crlf_copy.write_bytes(
        source.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    )
    payload = asyncio.run(preflight.build_preflight_payload(source_path=crlf_copy))
    assert payload["source_raw_identity"]["stage"] == "7R5-I"
    assert payload["source_raw_identity"]["attempt_count"] == 29


def test_preflight_rejects_wrong_source_identity_and_denominator(tmp_path: Path) -> None:
    raw = json.loads(preflight.RAW_RESULT_PATH.read_text(encoding="utf-8"))
    raw["stage"] = "wrong-stage"
    wrong_stage = tmp_path / "wrong-stage.json"
    wrong_stage.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RuntimeError, match="7R5-I real raw"):
        asyncio.run(preflight.build_preflight_payload(source_path=wrong_stage))

    raw["stage"] = "7R5-I"
    raw["report_records"].pop()
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RuntimeError, match="分母不完整"):
        asyncio.run(preflight.build_preflight_payload(source_path=incomplete))


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
    payload = preflight.load_r1c_diagnostic()
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
    payload = preflight.load_r1c_diagnostic()
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
        "R00": "AI 年限结论与后端经历时间事实冲突",
        "R09": "5.0 单项高分与未发现证据说明方向明显矛盾",
        "R16": "无直接证据的报告结论只能表达缺口、风险或待核实信息",
        "S00-1": "AI 年限结论与后端经历时间事实冲突",
        "S00-2": "AI 年限结论与后端经历时间事实冲突",
        "S00-3": "AI 年限结论与后端经历时间事实冲突",
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


def test_r1c_diagnostic_has_no_raw_response_prompt_or_stack() -> None:
    payload = preflight.load_r1c_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized


def test_r1c_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r1c_diagnostic()
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


def test_r1c_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="只允许读取既有诊断"):
        asyncio.run(preflight.build_r1c_replay_payload())


def test_r2e_replays_only_twelve_frozen_duration_rejections() -> None:
    payload = preflight.load_r2e_diagnostic()
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
    payload = preflight.load_r2e_diagnostic()
    assert payload["summary"] == {
        "target_case_count": 12,
        "old_duration_gate_removed_count": 12,
        "old_duration_gate_still_rejected_count": 0,
        "full_report_accepted_count": 1,
        "next_service_gate_rejected_count": 11,
        "future_human_quality_review_case_count": 2,
    }
    assert all(record["old_duration_gate_removed"] for record in payload["records"])
    assert [
        record["case_id"]
        for record in payload["records"]
        if record["current_report_status"] == "succeeded"
    ] == ["R05"]
    assert payload["pricing_gate_allowed"] is False
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_or_service_adjudication_required"] is True


def test_r2e_records_each_next_gate_and_preserves_r15_r19_model_risk() -> None:
    payload = preflight.load_r2e_diagnostic()
    assert {
        record["case_id"]: record["current_report_error_message"]
        for record in payload["records"]
    } == {
        "R00": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "R05": None,
        "R07": "无直接证据的报告结论只能表达缺口、风险或待核实信息",
        "R15": "AI 初筛理由包含 Resume 无法支持的事实",
        "R17": "AI 初筛理由包含 Resume 无法支持的数值事实",
        "R18": "无直接证据的报告结论只能表达缺口、风险或待核实信息",
        "R19": "无直接证据的报告结论只能表达缺口、风险或待核实信息",
        "S00-1": "AI 初筛理由与引用证据缺少可核对联系",
        "S00-2": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "S00-3": "5.0 单项高分与未发现证据说明方向明显矛盾",
        "S04-2": "无直接证据的报告结论只能表达缺口、风险或待核实信息",
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
    payload = preflight.load_r2e_diagnostic()
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


def test_r2e_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r2e_diagnostic()
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


def test_r2e_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="只允许读取既有诊断"):
        asyncio.run(preflight.build_r2e_replay_payload())


def test_r3d_diagnostic_records_exactly_six_frozen_no_evidence_rejections() -> None:
    payload = preflight.load_r3d_diagnostic()
    assert payload["target_case_ids"] == [
        "R07",
        "R10",
        "R16",
        "R18",
        "R19",
        "S04-2",
    ]
    assert payload["summary"]["target_case_count"] == 6
    assert {
        record["case_id"]: record["previous_gate_source"]
        for record in payload["records"]
    } == {
        "R07": "7R5-I2-R2-E",
        "R10": "7R5-I2-C",
        "R16": "7R5-I2-R1-C",
        "R18": "7R5-I2-R2-E",
        "R19": "7R5-I2-R2-E",
        "S04-2": "7R5-I2-R2-E",
    }
    assert all(
        record["previous_gate_error_message"]
        == "无直接证据的报告结论只能表达缺口、风险或待核实信息"
        for record in payload["records"]
    )


def test_r3d_removes_old_gate_without_claiming_content_quality() -> None:
    payload = preflight.load_r3d_diagnostic()
    assert payload["summary"] == {
        "target_case_count": 6,
        "old_no_evidence_gate_removed_count": 6,
        "old_no_evidence_gate_still_rejected_count": 0,
        "full_report_accepted_count": 3,
        "next_service_gate_rejected_count": 3,
        "future_human_quality_review_case_count": 6,
    }
    assert all(record["old_no_evidence_gate_removed"] for record in payload["records"])
    assert {
        record["case_id"]: record["current_report_error_message"]
        for record in payload["records"]
    } == {
        "R07": "5.0 AI 初筛输出包含不得参与评价的敏感个人属性",
        "R10": None,
        "R16": "5.0 综合说明包含当前 Resume 证据无法支持的事实",
        "R18": "5.0 综合说明包含当前 Resume 证据无法支持的事实",
        "R19": None,
        "S04-2": None,
    }
    assert payload["pricing_gate_allowed"] is False
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_or_service_adjudication_required"] is True
    assert payload["replay_limitations"] == {
        "service_acceptance_proves_content_quality": False,
        "responses_received_new_model_review": False,
        "future_human_quality_review_required": True,
    }


def test_r3d_is_zero_call_and_does_not_copy_sensitive_content() -> None:
    payload = preflight.load_r3d_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["diagnostic_write_count"] == 1
    assert payload["raw_response_copied"] is False
    assert payload["historical_results"]["all_present_and_readable"] is True


def test_r3d_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r3d_diagnostic()
    target = tmp_path / "r3d.json"
    preflight.write_r3d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R3-D"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r3d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r3d_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )


def test_r3d_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="只允许读取既有诊断"):
        asyncio.run(preflight.build_r3d_replay_payload())


def test_r4c_replays_exactly_three_frozen_sensitive_gate_cases() -> None:
    payload = preflight.load_r4c_diagnostic()
    assert payload["target_case_ids"] == ["R07", "R00", "S00-2"]
    assert payload["supporting_plan_case_ids"] == ["P00", "P07"]
    assert {
        record["case_id"]: record["previous_gate_source"]
        for record in payload["records"]
    } == {
        "R07": "7R5-I2-R3-D",
        "R00": "7R5-I2-R2-E",
        "S00-2": "7R5-I2-R2-E",
    }
    assert all(
        record["previous_gate_error_message"]
        == "5.0 AI 初筛输出包含不得参与评价的敏感个人属性"
        for record in payload["records"]
    )
    assert payload["source_r2e_diagnostic_identity"]["batch"] == "7R5-I2-R2-E"
    assert payload["source_r3d_diagnostic_identity"]["batch"] == "7R5-I2-R3-D"
    assert payload["execution_contract"]["report_service_behavior_version"] == (
        "lightweight_report_generation_v4"
    )


def test_r4c_removes_all_three_old_sensitive_gates_without_claiming_quality() -> None:
    payload = preflight.load_r4c_diagnostic()
    assert payload["summary"] == {
        "target_case_count": 3,
        "old_sensitive_gate_removed_count": 3,
        "old_sensitive_gate_still_rejected_count": 0,
        "full_report_accepted_count": 3,
        "next_service_gate_rejected_count": 0,
        "future_human_quality_review_case_count": 3,
    }
    assert all(record["old_sensitive_gate_removed"] for record in payload["records"])
    assert {
        record["case_id"]: (
            record["current_report_status"],
            record["current_report_error_message"],
        )
        for record in payload["records"]
    } == {
        "R07": ("succeeded", None),
        "R00": ("succeeded", None),
        "S00-2": ("succeeded", None),
    }
    assert payload["quality_conclusion_allowed"] is False
    assert payload["human_or_service_adjudication_required"] is True
    assert payload["replay_limitations"] == {
        "service_acceptance_proves_content_quality": False,
        "responses_received_new_model_review": False,
        "protected_attribute_semantics_evaluated": False,
        "future_human_quality_review_required": True,
    }


def test_r4c_is_zero_call_and_does_not_copy_sensitive_content() -> None:
    payload = preflight.load_r4c_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["diagnostic_write_count"] == 1
    assert payload["raw_response_copied"] is False
    assert payload["pricing_gate_allowed"] is False


def test_r4c_diagnostic_is_isolated_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r4c_diagnostic()
    target = tmp_path / "r4c.json"
    preflight.write_r4c_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R4-C"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r4c_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r4c_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )


def test_r4c_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="只允许读取既有诊断"):
        asyncio.run(preflight.build_r4c_replay_payload())


def test_r5d_replays_all_eleven_remaining_cases_from_latest_sources() -> None:
    payload = preflight.load_r5d_diagnostic()
    assert payload["target_case_ids"] == [
        "R04",
        "R06",
        "R09",
        "R15",
        "R16",
        "R17",
        "R18",
        "S00-1",
        "S00-3",
        "S04-1",
        "S04-3",
    ]
    assert payload["supporting_plan_case_ids"] == [
        "P00",
        "P04",
        "P06",
        "P07",
        "P09",
    ]
    assert {
        record["case_id"]: record["previous_gate_source"]
        for record in payload["records"]
    } == {
        "R04": "7R5-I2-C",
        "R06": "7R5-I2-C",
        "R09": "7R5-I2-R1-C",
        "R15": "7R5-I2-R2-E",
        "R16": "7R5-I2-R3-D",
        "R17": "7R5-I2-R2-E",
        "R18": "7R5-I2-R3-D",
        "S00-1": "7R5-I2-R2-E",
        "S00-3": "7R5-I2-R2-E",
        "S04-1": "7R5-I2-C",
        "S04-3": "7R5-I2-R2-E",
    }
    assert payload["execution_contract"]["report_service_behavior_version"] == (
        "lightweight_report_generation_v5"
    )


def test_r5d_removes_all_previous_gates_and_records_two_next_source_gates() -> None:
    payload = preflight.load_r5d_diagnostic()
    assert payload["summary"] == {
        "target_case_count": 11,
        "previous_service_gate_removed_count": 11,
        "previous_service_gate_still_rejected_count": 0,
        "full_report_accepted_count": 9,
        "next_service_gate_rejected_count": 2,
        "future_human_quality_review_case_count": 11,
    }
    assert all(
        record["previous_service_gate_removed"] for record in payload["records"]
    )
    assert {
        record["case_id"]: (
            record["current_report_status"],
            record["current_report_error_message"],
        )
        for record in payload["records"]
    } == {
        "R04": ("succeeded", None),
        "R06": ("succeeded", None),
        "R09": ("succeeded", None),
        "R15": ("succeeded", None),
        "R16": ("failed", "AI 初筛理由包含 Resume 无法支持的数值事实"),
        "R17": ("succeeded", None),
        "R18": ("succeeded", None),
        "S00-1": ("succeeded", None),
        "S00-3": ("failed", "AI 初筛理由包含 Resume 无法支持的数值事实"),
        "S04-1": ("succeeded", None),
        "S04-3": ("succeeded", None),
    }


def test_r5d_keeps_known_content_risks_for_future_human_review() -> None:
    payload = preflight.load_r5d_diagnostic()
    assert payload["known_model_risk_case_ids"] == ["R06", "R15", "R16"]
    assert {
        record["case_id"]: record["known_model_content_risk"]
        for record in payload["records"]
        if record["known_model_content_risk"] is not None
    } == {
        "R06": "评价点年限与报告年限结论仍需人工核对",
        "R15": "报告内部年限结论仍需人工核对",
        "R16": "能力迁移推断仍需人工核对",
    }
    assert all(
        record["future_human_quality_review_required"]
        for record in payload["records"]
    )
    assert payload["quality_conclusion_allowed"] is False
    assert payload["replay_limitations"] == {
        "service_acceptance_proves_content_quality": False,
        "responses_received_new_model_review": False,
        "known_model_content_risks_resolved": False,
        "future_human_quality_review_required": True,
    }


def test_r5d_is_zero_call_content_safe_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r5d_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["diagnostic_write_count"] == 1
    assert payload["raw_response_copied"] is False
    assert payload["pricing_gate_allowed"] is False

    target = tmp_path / "r5d.json"
    preflight.write_r5d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R5-D"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r5d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r5d_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )


def test_r5d_sealed_diagnostic_is_readable_and_identity_locked() -> None:
    payload = preflight.load_r5d_diagnostic()
    assert payload["stage"] == "7R5-I2"
    assert payload["batch"] == "7R5-I2-R5-D"
    assert payload["mode"] == "zero_call_remaining_service_v5_replay"
    assert payload["summary"]["full_report_accepted_count"] == 9
    assert payload["summary"]["next_service_gate_rejected_count"] == 2


def test_r5d_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="行为版本不是 v5"):
        asyncio.run(preflight.build_r5d_replay_payload())


def test_r6d_dynamic_rebuild_is_retired_after_behavior_version_change() -> None:
    with pytest.raises(RuntimeError, match="行为版本不是 v6"):
        asyncio.run(preflight.build_r6d_replay_payload())


def test_r6d_removes_both_old_source_gates_and_accepts_all_responses() -> None:
    payload = preflight.load_r6d_diagnostic()
    assert payload["summary"] == {
        "target_case_count": 19,
        "report_response_count": 13,
        "stability_response_count": 6,
        "missing_report_response_count": 7,
        "missing_stability_response_count": 9,
        "previously_accepted_count": 17,
        "previously_rejected_count": 2,
        "old_free_text_source_gate_target_count": 2,
        "old_free_text_source_gate_removed_count": 2,
        "old_free_text_source_gate_still_rejected_count": 0,
        "full_report_accepted_count": 19,
        "next_service_gate_rejected_count": 0,
        "future_human_quality_review_case_count": 19,
    }
    assert {
        record["case_id"]
        for record in payload["records"]
        if record["previous_free_text_source_gate"]
    } == {"R16", "S00-3"}
    assert all(
        record["old_free_text_source_gate_removed"] is True
        for record in payload["records"]
        if record["previous_free_text_source_gate"]
    )
    assert all(
        record["current_report_status"] == "succeeded"
        and record["current_report_error_message"] is None
        for record in payload["records"]
    )


def test_r6d_records_missing_answers_without_reconstructing_them() -> None:
    payload = preflight.load_r6d_diagnostic()
    assert payload["missing_report_case_ids"] == [
        "R01",
        "R02",
        "R03",
        "R08",
        "R11",
        "R12",
        "R13",
    ]
    assert payload["missing_stability_case_ids"] == [
        "S01-1",
        "S01-2",
        "S01-3",
        "S02-1",
        "S02-2",
        "S02-3",
        "S03-1",
        "S03-2",
        "S03-3",
    ]
    assert payload["replay_limitations"][
        "missing_responses_were_reconstructed"
    ] is False


def test_r6d_keeps_known_content_risks_and_quality_limitations() -> None:
    payload = preflight.load_r6d_diagnostic()
    assert payload["known_model_risk_case_ids"] == [
        "R06",
        "R14",
        "R15",
        "R16",
        "R19",
    ]
    assert {
        record["case_id"]: record["known_model_content_risk"]
        for record in payload["records"]
        if record["known_model_content_risk"] is not None
    } == {
        "R06": "评价点年限与报告年限结论仍需人工核对",
        "R14": "五个报告分区的完整性和内容价值仍需人工核对",
        "R15": "报告内部年限结论仍需人工核对",
        "R16": "能力迁移推断仍需人工核对",
        "R19": "既有模型内容风险仍需人工核对",
    }
    assert all(
        record["future_human_quality_review_required"]
        for record in payload["records"]
    )
    assert payload["quality_conclusion_allowed"] is False
    assert payload["pricing_gate_allowed"] is False
    assert payload["replay_limitations"] == {
        "service_acceptance_proves_content_quality": False,
        "responses_received_new_model_review": False,
        "known_model_content_risks_resolved": False,
        "missing_responses_were_reconstructed": False,
        "future_human_quality_review_required": True,
    }


def test_r6d_is_zero_call_content_safe_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r6d_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["diagnostic_write_count"] == 1
    assert payload["raw_response_copied"] is False

    target = tmp_path / "r6d.json"
    preflight.write_r6d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R6-D"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r6d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r6d_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )


def test_r7d_replays_exact_six_i2_time_key_failures_with_service_v7() -> None:
    payload = asyncio.run(preflight.build_r7d_replay_payload())
    assert payload["target_case_ids"] == [
        "R00",
        "S00-1",
        "S00-2",
        "S00-3",
        "S04-2",
        "S04-3",
    ]
    assert payload["supporting_plan_case_ids"] == ["P00", "P04"]
    assert payload["source_raw_identity"] == {
        "stage": "7R5-I2",
        "mode": "real_raw",
        "plan_case_count": 10,
        "report_case_count": 20,
        "stability_case_count": 15,
        "attempt_count": 45,
        "report_prompt_version": "screening_evaluation_lightweight_v3",
        "report_service_behavior_version": "lightweight_report_generation_v6",
    }
    assert payload["execution_contract"]["report_prompt_version"] == (
        "screening_evaluation_lightweight_v4"
    )
    assert payload["execution_contract"][
        "report_service_behavior_version"
    ] == "lightweight_report_generation_v7"
    assert payload["lifecycle"]["state"] in {
        "i2_human_complete",
        "i2_final_complete",
    }
    assert payload["summary"] == {
        "target_case_count": 6,
        "report_response_count": 1,
        "stability_response_count": 5,
        "old_keyword_gate_target_count": 6,
        "old_keyword_gate_removed_count": 6,
        "old_keyword_gate_still_rejected_count": 0,
        "full_report_accepted_count": 0,
        "next_deterministic_gate_rejected_count": 6,
        "missing_calculation_note_count": 6,
        "future_human_quality_review_case_count": 6,
    }


def test_r7d_preserves_response_identity_and_records_next_deterministic_gate() -> None:
    payload = asyncio.run(preflight.build_r7d_replay_payload())
    assert all(
        record["source_status"] == "failed"
        and record["source_error_message"]
        == "非经历时间评价点不得引用经历时间事实"
        and record["old_keyword_gate_removed"] is True
        and record["current_report_status"] == "failed"
        and record["current_report_error_message"]
        == "引用经历时间事实时必须提供 calculation_note"
        and record["missing_calculation_note_after_keyword_gate"] is True
        and len(record["raw_response_sha256"]) == 64
        and record["raw_response_length"] > 0
        for record in payload["records"]
    )
    assert len(
        {record["raw_response_sha256"] for record in payload["records"]}
    ) == 6


def test_r7d_sealed_diagnostic_is_identity_locked() -> None:
    payload = preflight.load_r7d_diagnostic()
    assert payload["stage"] == "7R5-I2"
    assert payload["batch"] == "7R5-I2-R7-D"
    assert payload["mode"] == "zero_call_time_key_service_v7_replay"
    assert payload["summary"]["old_keyword_gate_removed_count"] == 6
    assert payload["summary"]["missing_calculation_note_count"] == 6


def test_r7d_is_zero_call_content_safe_and_write_once(tmp_path: Path) -> None:
    payload = preflight.load_r7d_diagnostic()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"raw_response"' not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "chain_of_thought" not in serialized
    assert "stack_trace" not in serialized
    assert payload["real_model_call_count"] == 0
    assert payload["api_attempt_count"] == 0
    assert payload["api_key_read"] is False
    assert payload["adapter_instantiated"] is False
    assert payload["postgresql_write_count"] == 0
    assert payload["formal_result_write_count"] == 0
    assert payload["diagnostic_write_count"] == 1
    assert payload["raw_response_copied"] is False
    assert payload["pricing_gate_allowed"] is False
    assert payload["quality_conclusion_allowed"] is False

    target = tmp_path / "r7d.json"
    preflight.write_r7d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["batch"] == (
        "7R5-I2-R7-D"
    )
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        preflight.write_r7d_diagnostic(target, payload, diagnostic_dir=tmp_path)
    with pytest.raises(RuntimeError, match="隔离诊断目录"):
        preflight.write_r7d_diagnostic(
            tmp_path.parent / "outside.json",
            payload,
            diagnostic_dir=tmp_path,
        )
