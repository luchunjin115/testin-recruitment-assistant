from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_stage7_p5r_g_v10_v2_r04_real as runner  # noqa: E402


class P5RGV10V2R04RealRunnerTest(TestCase):
    def test_zero_call_preflight_locks_current_contract_and_frozen_r04_error(self) -> None:
        payload = runner.build_zero_call_preflight()

        self.assertEqual(payload["status"], "passed")
        self.assertEqual(
            payload["contract"]["main_prompt_version"],
            "screening_evaluation_lightweight_v10",
        )
        self.assertEqual(
            payload["contract"]["repair_prompt_version"],
            "screening_evaluation_repair_v2",
        )
        self.assertEqual(payload["contract"]["api_attempt_limit"], 3)
        self.assertEqual(payload["frozen_replay"]["repairable_error_count"], 12)
        self.assertEqual(
            set(payload["frozen_replay"]["validation_errors"][0]),
            {"code", "path", "actual_type", "expected", "correction"},
        )
        self.assertLess(
            payload["cost_gate"]["maximum_single_attempt_reservation_usd"],
            payload["cost_gate"]["hard_cap_usd"],
        )

    def test_preflight_evidence_is_write_once(self) -> None:
        payload = runner.build_zero_call_preflight()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            runner.seal_zero_call_preflight(payload, path=path)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                runner.seal_zero_call_preflight(payload, path=path)

    def test_new_real_paths_do_not_overlap_frozen_gf_paths(self) -> None:
        new_paths = {runner.PREFLIGHT_PATH, runner.RESULT_PATH, *runner.ATTEMPT_PATHS}
        frozen_paths = {
            runner.FROZEN_GF_RESULT_PATH,
            runner.FROZEN_GF_INITIAL_ATTEMPT_PATH,
        }

        self.assertTrue(new_paths.isdisjoint(frozen_paths))
        self.assertTrue(all("v10-v2" in path.name for path in new_paths))

    def test_direct_repair_challenge_runs_only_when_fresh_initial_needed_no_repair(self) -> None:
        self.assertTrue(
            runner.should_run_direct_repair_challenge(
                fresh_result_exists=True,
                fresh_content_repair_count=0,
            )
        )
        self.assertFalse(
            runner.should_run_direct_repair_challenge(
                fresh_result_exists=True,
                fresh_content_repair_count=1,
            )
        )
        self.assertFalse(
            runner.should_run_direct_repair_challenge(
                fresh_result_exists=False,
                fresh_content_repair_count=0,
            )
        )

    def test_sealed_real_result_proves_v10_and_v2_paths(self) -> None:
        payload = json.loads(runner.RESULT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["attempt_summary"]["api_attempt_count"], 2)
        self.assertEqual(payload["attempt_summary"]["business_call_count"], 2)
        self.assertEqual(payload["attempt_summary"]["infrastructure_retry_count"], 0)
        self.assertEqual(payload["fresh_v10_flow"]["status"], "legal")
        self.assertFalse(payload["fresh_v10_flow"]["repair_triggered"])
        self.assertEqual(
            payload["direct_repair_v2_challenge"]["status"],
            "passed",
        )
        self.assertTrue(
            payload["direct_repair_v2_challenge"][
                "full_json_schema_service_revalidation_passed"
            ]
        )
        self.assertTrue(payload["direct_repair_v2_challenge"]["raw_changed"])
        self.assertLessEqual(
            payload["cost_enforcement"]["estimated_spend_usd"],
            payload["cost_enforcement"]["hard_cap_usd"],
        )
        self.assertFalse(runner.ATTEMPT_PATHS[2].exists())

        for index, journal in enumerate(payload["attempt_audit"]):
            path = PROJECT_ROOT / journal["journal_path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                journal["journal_sha256"],
            )

        fresh_report = payload["fresh_v10_flow"]["report"]
        repaired_report = payload["direct_repair_v2_challenge"]["report"]
        self.assertTrue(
            all(
                isinstance(item, str) and item.strip()
                for item in fresh_report["hr_follow_up_questions"]
            )
        )
        self.assertTrue(
            all(
                isinstance(item, str) and item.strip()
                for item in repaired_report["hr_follow_up_questions"]
            )
        )
        self.assertTrue(
            all(
                item.get("assessment", item)["score"] == 0
                or item.get("assessment", item)["evidence"]
                for item in repaired_report["criterion_assessments"]
            )
        )
