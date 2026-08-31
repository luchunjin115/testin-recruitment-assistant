from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_close07_acceptance as close07  # noqa: E402


def test_close07_prerequisites_bind_the_accepted_i4_raw() -> None:
    result = close07.validate_prerequisites()
    assert result["stage"] == "7R5-CLOSE-07"
    assert result["i4_lifecycle"] == "i4_raw_complete"
    assert result["i4_raw_sha256"] == close07.I4_RAW_SHA256
    assert result["i4_plan_valid_count"] == 10
    assert result["i4_report_valid_count"] == 19
    assert result["i4_stability_valid_count"] == 13


def test_close07_never_requires_i4_human_or_final() -> None:
    result = close07.validate_prerequisites()
    assert result["i4_human_exists"] is False
    assert result["i4_final_exists"] is False
    assert result["quality_gate_passed"] is None
    assert result["quality_conclusion_allowed"] is False


def test_close07_has_independent_write_once_result_and_browser_paths() -> None:
    assert close07.RESULT_PATH.name == (
        "2026-08-31-stage7-close07-full-chain-acceptance-results.json"
    )
    assert close07.BROWSER_EVIDENCE_DIR.name == "close07-browser-acceptance-evidence"
    assert close07.RESULT_PATH != close07.I4_RAW_PATH


def test_close07_writer_rejects_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    close07.write_json_once(path, {"stage": "7R5-CLOSE-07"})
    try:
        close07.write_json_once(path, {"stage": "7R5-CLOSE-07"})
    except RuntimeError as exc:
        assert "拒绝覆盖" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("write-once result must reject overwrite")


def test_close07_result_is_absent_or_strictly_valid() -> None:
    if close07.RESULT_PATH.exists():
        result = close07.validate_result()
        assert result["close07_passed"] is True
        assert result["real_model_call_count"] == 0
        assert result["api_attempt_count"] == 0
        assert result["actual_token_usage"] == 0
        assert result["actual_spend_usd"] == 0
        assert result["api_key_read"] is False
    else:
        assert close07.validate_prerequisites()["ready_for_close07"] is True
