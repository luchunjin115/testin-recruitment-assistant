from __future__ import annotations

import json
import hashlib

import pytest

from scripts import run_stage7_p5r_f_r04_diagnostic as runner


def test_r04_diagnostic_preflight_is_single_case_and_below_cap() -> None:
    inputs = runner._r04_inputs()

    assert inputs["pair"]["case_id"] == "R04"
    # The historical P5R-F result stays immutable; this helper prices the current
    # production prompt, which is now v10 rather than the prompt used by P5R-F.
    assert runner.peak_cost_upper_bound_usd(inputs) == pytest.approx(0.0772728)
    assert runner.RESULT_PATH.exists() is True
    assert runner.ATTEMPT_PATHS[0].exists() is True
    assert runner.ATTEMPT_PATHS[1].exists() is False
    with pytest.raises(RuntimeError, match="拒绝覆盖或补跑"):
        runner.offline_preflight()


def test_diagnostic_reports_exact_schema_path_for_nonzero_without_basis() -> None:
    plan = {
        "schema_version": "5.0",
        "criteria": [
            {
                "criterion_id": "criterion:0001",
                "name": "接口开发",
                "importance": "required",
                "description": "评价接口开发能力。",
                "screening_focus": "核对接口项目。",
                "origin": "hr_added",
                "sources": [],
                "hr_note": "HR 补充评价点。",
            }
        ],
    }
    payload = {
        "overall_score": 50,
        "overall_summary": "存在部分匹配。",
        "criterion_assessments": [
            {
                "criterion_id": "criterion:0001",
                "score": 5,
                "reason": "模型给出部分匹配。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [],
            }
        ],
        "strengths": [],
        "gaps": [],
        "risks_or_conflicts": [],
        "missing_info": [],
        "hr_follow_up_questions": [],
    }

    diagnosis = runner.diagnose_raw_response(
        json.dumps(payload, ensure_ascii=False),
        evaluation_plan=plan,
    )

    assert diagnosis["layer"] == "schema"
    assert diagnosis["errors"][0]["loc"] == (
        "criterion_assessments",
        0,
    )
    assert "非零分必须至少包含一条 AI 判断依据" in diagnosis["errors"][0]["msg"]


def test_runner_source_persists_attempt_before_service_parse() -> None:
    source = runner.Path(runner.__file__).read_text(encoding="utf-8")

    write_index = source.index("_write_json_x(ATTEMPT_PATHS[attempt_number - 1], attempt)")
    parse_index = source.index("parse_and_validate_v5_output")
    assert write_index < parse_index


def test_r04_real_result_identifies_all_six_score_evidence_failures() -> None:
    payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))
    attempt_path = runner.ATTEMPT_PATHS[0]

    assert hashlib.sha256(runner.RESULT_PATH.read_bytes()).hexdigest() == (
        "448a5ea7d5c4abadf6d26403d86e4d752b7aa62b065d788fd76e181efbc799ba"
    )
    assert hashlib.sha256(attempt_path.read_bytes()).hexdigest() == (
        "5ebbe912fb8dae0801417a7a03b2d10e33361d757bb0aa49e4c5bc54927c6bde"
    )
    assert payload["service_status"] == "rejected"
    assert payload["diagnosis"]["layer"] == "schema"
    assert [
        item["input"]["criterion_id"] for item in payload["diagnosis"]["errors"]
    ] == [
        "criterion:0004",
        "criterion:0005",
        "criterion:0009",
        "criterion:0012",
        "criterion:0013",
        "criterion:0014",
    ]
    assert all(
        item["input"]["score"] in (1, 2)
        and item["input"]["evidence"] == []
        and "非零分必须至少包含一条 AI 判断依据" in item["msg"]
        for item in payload["diagnosis"]["errors"]
    )
    assert payload["attempt_summary"] == {
        "api_attempt_count": 1,
        "infrastructure_retry_count": 0,
        "estimated_spend_usd": 0.00869088,
    }
    assert payload["attempt_audit"][0]["journal_sha256"] == (
        hashlib.sha256(attempt_path.read_bytes()).hexdigest()
    )
    assert payload["postgresql_write_count"] == 0
