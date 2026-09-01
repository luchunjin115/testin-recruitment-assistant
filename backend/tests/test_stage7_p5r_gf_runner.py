from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from app.adapters.screening_evaluation import (  # noqa: E402
    ScreeningEvaluationAdapterResult,
    ScreeningEvaluationTimeoutError,
)
import run_stage7_p5r_gf_r04_repair as gf  # noqa: E402


class P5RGFOfflineGateTest(TestCase):
    def test_completed_gf_preflight_refuses_current_prompt_version_drift(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_paths = tuple(root / f"attempt-{number}.json" for number in range(3))
            with (
                patch.object(gf, "RESULT_PATH", root / "result.json"),
                patch.object(gf, "ATTEMPT_PATHS", attempt_paths),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "合同字段 main_prompt_version 已漂移",
                ):
                    gf.offline_preflight()

        self.assertEqual(
            gf.SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "screening_evaluation_lightweight_v10",
        )
        self.assertEqual(gf.BUSINESS_CALL_MAXIMUM, 2)
        self.assertEqual(gf.API_ATTEMPT_LIMIT, 3)

    def test_preflight_refuses_to_overwrite_any_gf_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            result_path.write_text("sealed", encoding="utf-8")
            with (
                patch.object(gf, "RESULT_PATH", result_path),
                patch.object(
                    gf,
                    "ATTEMPT_PATHS",
                    tuple(root / f"attempt-{number}.json" for number in range(3)),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "拒绝覆盖"):
                    gf.offline_preflight()


class _SuccessDelegate:
    async def evaluate_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
        return ScreeningEvaluationAdapterResult(
            content="{broken-json",
            model=gf.MODEL,
            finish_reason="stop",
            input_tokens=100,
            output_tokens=20,
        )

    async def repair_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
        return ScreeningEvaluationAdapterResult(
            content='{"complete":"report"}',
            model=gf.MODEL,
            finish_reason="stop",
            input_tokens=120,
            output_tokens=30,
        )


class _RetryOnceDelegate(_SuccessDelegate):
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
        self.calls += 1
        if self.calls == 1:
            raise ScreeningEvaluationTimeoutError("not persisted")
        return await super().evaluate_v5(**kwargs)


class P5RGFJournalAdapterTest(IsolatedAsyncioTestCase):
    async def test_raw_is_exclusively_sealed_before_caller_can_parse_it(self) -> None:
        inputs = gf._r04_inputs()
        kwargs = gf._adapter_kwargs(inputs)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = tuple(root / f"attempt-{number}.json" for number in range(3))
            adapter = gf.JournaledGFAdapter(
                delegate=_SuccessDelegate(),  # type: ignore[arg-type]
                ledger=gf.CostLedger(cap_usd=gf.MONETARY_CAP_USD),
            )
            with patch.object(gf, "ATTEMPT_PATHS", paths):
                result = await adapter.evaluate_v5(**kwargs)
                self.assertTrue(paths[0].exists())
                self.assertIn(result.content, paths[0].read_text(encoding="utf-8"))
                self.assertTrue(
                    adapter.attempts[0]["raw_sealed_before_service_validation"]
                )
                with self.assertRaises(FileExistsError):
                    gf._write_json_x(paths[0], {"overwrite": True})

    async def test_one_initial_infrastructure_retry_uses_two_of_three_attempts(self) -> None:
        inputs = gf._r04_inputs()
        kwargs = gf._adapter_kwargs(inputs)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = tuple(root / f"attempt-{number}.json" for number in range(3))
            delegate = _RetryOnceDelegate()
            adapter = gf.JournaledGFAdapter(
                delegate=delegate,  # type: ignore[arg-type]
                ledger=gf.CostLedger(cap_usd=gf.MONETARY_CAP_USD),
            )
            with patch.object(gf, "ATTEMPT_PATHS", paths):
                await adapter.evaluate_v5(**kwargs)

        self.assertEqual(delegate.calls, 2)
        self.assertEqual(len(adapter.attempts), 2)
        self.assertEqual(
            [item["result"] for item in adapter.attempts],
            ["failed", "succeeded"],
        )
        self.assertLessEqual(adapter.ledger.estimated_spend_usd, gf.MONETARY_CAP_USD)

    async def test_repair_has_no_infrastructure_retry(self) -> None:
        class FailingRepairDelegate(_SuccessDelegate):
            def __init__(self) -> None:
                self.repair_calls = 0

            async def repair_v5(self, **kwargs: object) -> ScreeningEvaluationAdapterResult:
                self.repair_calls += 1
                raise ScreeningEvaluationTimeoutError("not persisted")

        inputs = gf._r04_inputs()
        kwargs = {
            "sanitized_resume": inputs["sanitized_resume"],
            "confirmed_criteria": inputs["plan"]["criteria"],
            "original_response": "{broken-json",
            "validation_errors": [
                {
                    "code": "JSON_SYNTAX_INVALID",
                    "path": "$",
                    "actual_type": "invalid_json",
                    "expected": "完整 JSON",
                    "correction": "重新生成一份可独立解析的完整报告",
                }
            ],
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = tuple(root / f"attempt-{number}.json" for number in range(3))
            delegate = FailingRepairDelegate()
            adapter = gf.JournaledGFAdapter(
                delegate=delegate,  # type: ignore[arg-type]
                ledger=gf.CostLedger(cap_usd=gf.MONETARY_CAP_USD),
            )
            with patch.object(gf, "ATTEMPT_PATHS", paths):
                with self.assertRaises(ScreeningEvaluationTimeoutError):
                    await adapter.repair_v5(**kwargs)
                journal_text = paths[0].read_text(encoding="utf-8")

        self.assertEqual(delegate.repair_calls, 1)
        self.assertEqual(len(adapter.attempts), 1)
        self.assertNotIn("not persisted", journal_text)
