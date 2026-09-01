from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase, TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_final_v10_v2_acceptance as runner  # noqa: E402
from app.adapters.screening_evaluation import (  # noqa: E402
    ScreeningEvaluationAdapterResult,
)


class Stage7FinalAcceptancePreflightTest(TestCase):
    def test_preflight_freezes_current_contract_schedule_and_zero_call_boundary(self) -> None:
        payload = runner.build_zero_call_preflight()

        assert payload["status"] == "passed"
        assert payload["contract"] == {
            "model": "deepseek-v4-pro",
            "main_prompt_version": "screening_evaluation_lightweight_v10",
            "repair_prompt_version": "screening_evaluation_repair_v2",
            "behavior_version": "lightweight_report_generation_v11",
            "schema_version": "5.0",
            "business_call_count": 35,
            "per_business_api_attempt_limit": 3,
            "content_repair_maximum": 1,
        }
        assert payload["schedule"]["base_report_count"] == 20
        assert payload["schedule"]["stability_report_count"] == 15
        assert len(payload["schedule"]["business_call_ids"]) == 35
        assert payload["safety"] == {
            "api_key_read": False,
            "real_adapter_instantiated": False,
            "model_calls": 0,
            "tokens": 0,
            "cost_usd": 0,
            "postgresql_business_writes": 0,
        }

    def test_final_paths_are_new_and_write_once(self) -> None:
        paths = {runner.PREFLIGHT_PATH, runner.RESULT_PATH, runner.JOURNAL_PATH}
        assert all("final-v10-v2" in path.name for path in paths)
        assert runner.OLD_P3_RESULT_PATH not in paths
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            runner._write_json_x(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                runner._write_json_x(path, {"ok": False})


class _FakeDelegate:
    async def evaluate_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
        return ScreeningEvaluationAdapterResult(
            content='{"first":true}',
            model=runner.MODEL,
            finish_reason="stop",
            input_tokens=100,
            output_tokens=20,
        )

    async def repair_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
        return ScreeningEvaluationAdapterResult(
            content='{"repaired":true}',
            model=runner.MODEL,
            finish_reason="stop",
            input_tokens=120,
            output_tokens=30,
        )


class Stage7FinalAcceptanceJournalTest(IsolatedAsyncioTestCase):
    async def test_initial_and_repair_raw_are_sealed_with_one_repair_limit(self) -> None:
        with TemporaryDirectory() as directory:
            journal_path = Path(directory) / "attempts.jsonl"
            ledger = runner.PeakCostLedger(cap_usd=2.0)
            adapter = runner.JournaledAcceptanceAdapter(
                delegate=_FakeDelegate(),  # type: ignore[arg-type]
                ledger=ledger,
                business_call_id="FINAL-R04",
                journal_path=journal_path,
            )
            initial = await adapter.evaluate_v5(
                job_snapshot={"job": True},
                evaluation_plan={"criteria": [{"criterion_id": "c1"}]},
                sanitized_resume="resume",
                evaluation_reference_at="2026-09-01T00:00:00+00:00",
                evaluation_timezone="Asia/Shanghai",
                experience_period_facts={},
            )
            repaired = await adapter.repair_v5(
                sanitized_resume="resume",
                confirmed_criteria=[{"criterion_id": "c1"}],
                original_response="{broken",
                validation_errors=[
                    {
                        "code": "JSON_SYNTAX_INVALID",
                        "path": "$",
                        "actual_type": "invalid_json",
                        "expected": "完整 JSON",
                        "correction": "重新生成完整报告",
                    }
                ],
            )
            with self.assertRaises(RuntimeError):
                await adapter.repair_v5(
                    sanitized_resume="resume",
                    confirmed_criteria=[{"criterion_id": "c1"}],
                    original_response="{broken",
                    validation_errors=[
                        {
                            "code": "JSON_SYNTAX_INVALID",
                            "path": "$",
                            "actual_type": "invalid_json",
                            "expected": "完整 JSON",
                            "correction": "重新生成完整报告",
                        }
                    ],
                )

            lines = journal_path.read_text(encoding="utf-8").splitlines()

        assert initial.content == '{"first":true}'
        assert repaired.content == '{"repaired":true}'
        assert len(lines) == 2
        assert '"call_kind":"initial"' in lines[0]
        assert '"call_kind":"repair"' in lines[1]
        assert "first" in lines[0]
        assert "repaired" in lines[1]
        assert adapter.api_attempt_count == 2


class Stage7FinalAcceptanceSealedResultTest(TestCase):
    def test_sealed_result_has_exact_attempt_cost_and_legality_counts(self) -> None:
        payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))

        assert payload["status"] == "completed"
        assert payload["fatal_error"] is None
        assert payload["attempt_summary"] == {
            "scheduled_business_call_count": 35,
            "executed_business_call_count": 35,
            "api_attempt_count": 35,
            "succeeded_attempt_count": 35,
            "failed_attempt_count": 0,
            "infrastructure_retry_count": 0,
            "content_repair_count": 0,
            "input_tokens": 173530,
            "output_tokens": 75223,
        }
        assert payload["report_summary"] == {
            "scheduled_count": 20,
            "legal_count": 19,
            "failed_count": 1,
            "direction_match_count": 14,
            "score_in_frozen_range_count": 7,
            "repair_triggered_count": 0,
        }
        assert payload["cost_enforcement"]["estimated_spend_usd"] == 0.52694268
        assert payload["cost_enforcement"]["within_hard_cap"] is True
        assert payload["quality_gate_passed"] is None
        assert payload["quality_conclusion_allowed"] is False
        assert payload["requires_human_audit"] is True
        assert payload["postgresql_write_count"] == 0
        assert payload["api_key_persisted"] is False

    def test_all_stability_groups_are_legal_stable_and_within_spread(self) -> None:
        payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))

        assert len(payload["stability_runs"]) == 15
        assert all(item["legal_run_count"] == 3 for item in payload["stability_summary"])
        assert all(item["scores"] == [88, 88, 88] for item in payload["stability_summary"])
        assert all(item["direction_stable"] for item in payload["stability_summary"])
        assert all(item["spread_le_10"] for item in payload["stability_summary"])

    def test_r12_privacy_false_positive_and_direction_mismatches_remain_visible(self) -> None:
        payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))
        failed = [item for item in payload["reports"] if item["status"] == "failed"]
        mismatches = [
            item["case_id"]
            for item in payload["reports"]
            if item["status"] == "succeeded"
            and not item["direction_matches_frozen_label"]
        ]

        assert [item["case_id"] for item in failed] == ["R12"]
        assert failed[0]["content_repair_count"] == 0
        assert failed[0]["validation_errors"] == []
        assert mismatches == ["R04", "R08", "R16", "R18", "R20"]

    def test_journal_and_sources_are_sealed_without_key(self) -> None:
        payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))
        journal_text = runner.JOURNAL_PATH.read_text(encoding="utf-8")
        lines = journal_text.splitlines()

        assert len(lines) == 35
        assert (
            hashlib.sha256(runner.JOURNAL_PATH.read_bytes()).hexdigest()
            == payload["attempt_journal"]["sha256"]
        )
        assert (
            hashlib.sha256(runner.OLD_P3_RESULT_PATH.read_bytes()).hexdigest()
            == payload["source"]["old_p3_sha256"]
        )
        assert all(json.loads(line)["call_kind"] == "initial" for line in lines)
        assert all(
            json.loads(line)["raw_sealed_before_service_validation"]
            for line in lines
        )
        serialized = (runner.RESULT_PATH.read_text(encoding="utf-8") + journal_text).lower()
        assert "deepseek_api_key" not in serialized
        assert '"api_key"' not in serialized
        assert "sk-" not in serialized
