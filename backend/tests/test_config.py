import ast
from pathlib import Path
from unittest import TestCase

from pydantic import ValidationError

from app.core.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_example_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def _planned_quality_model() -> str:
    source = (PROJECT_ROOT / "scripts" / "stage7_7r4_quality_contract.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "PLANNED_MODEL"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise AssertionError("质量合同缺少 PLANNED_MODEL 字符串常量")


class SettingsTest(TestCase):
    def test_model_calling_defaults_examples_and_quality_contract_stay_aligned(self) -> None:
        settings = Settings(_env_file=None)
        example = _env_example_values()
        expected = "deepseek-v4-flash"

        self.assertEqual(settings.DEEPSEEK_MODEL, expected)
        self.assertEqual(settings.JOB_EVALUATION_PLAN_MODEL, expected)
        self.assertEqual(settings.SCREENING_EVALUATION_MODEL, expected)
        self.assertEqual(example["DEEPSEEK_MODEL"], expected)
        self.assertEqual(example["JOB_EVALUATION_PLAN_MODEL"], expected)
        self.assertEqual(example["SCREENING_EVALUATION_MODEL"], expected)
        self.assertEqual(_planned_quality_model(), expected)

    def test_resume_cleanup_defaults_are_safe_and_bounded(self) -> None:
        settings = Settings(_env_file=None)

        self.assertTrue(settings.RESUME_CLEANUP_ENABLED)
        self.assertEqual(settings.RESUME_UNBOUND_RETENTION_HOURS, 24)
        self.assertEqual(settings.RESUME_CLEANUP_INTERVAL_MINUTES, 60)
        self.assertEqual(settings.RESUME_CLEANUP_BATCH_SIZE, 50)

    def test_resume_cleanup_rejects_non_positive_values(self) -> None:
        for field in (
            "RESUME_UNBOUND_RETENTION_HOURS",
            "RESUME_CLEANUP_INTERVAL_MINUTES",
            "RESUME_CLEANUP_BATCH_SIZE",
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: 0})

    def test_resume_structure_defaults_are_bounded_and_versioned(self) -> None:
        settings = Settings(_env_file=None)

        self.assertTrue(settings.RESUME_STRUCTURE_ENABLED)
        self.assertEqual(settings.RESUME_STRUCTURE_MODEL, "deepseek-v4-flash")
        self.assertEqual(settings.RESUME_STRUCTURE_TIMEOUT_SECONDS, 90)
        self.assertEqual(settings.RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS, 180)
        self.assertEqual(settings.RESUME_STRUCTURE_MAX_INPUT_CHARS, 100_000)
        self.assertEqual(settings.RESUME_STRUCTURE_MAX_OUTPUT_TOKENS, 12_000)
        self.assertEqual(settings.RESUME_STRUCTURE_PROMPT_VERSION, "resume_structure_v1")
        self.assertEqual(settings.RESUME_STRUCTURE_SCHEMA_VERSION, "1.0")

    def test_resume_structure_rejects_unsafe_numeric_configuration(self) -> None:
        invalid_values = {
            "RESUME_STRUCTURE_TIMEOUT_SECONDS": 0,
            "RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS": 29,
            "RESUME_STRUCTURE_MAX_INPUT_CHARS": 999,
            "RESUME_STRUCTURE_MAX_OUTPUT_TOKENS": 999,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: value})

    def test_job_evaluation_plan_defaults_are_bounded_and_versioned(self) -> None:
        settings = Settings(_env_file=None)

        self.assertTrue(settings.JOB_EVALUATION_PLAN_ENABLED)
        self.assertEqual(settings.JOB_EVALUATION_PLAN_MODEL, "deepseek-v4-flash")
        self.assertEqual(settings.JOB_EVALUATION_PLAN_TIMEOUT_SECONDS, 90)
        self.assertEqual(settings.JOB_EVALUATION_PLAN_MAX_INPUT_CHARS, 100_000)
        self.assertEqual(settings.JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS, 8_000)
        self.assertEqual(
            settings.JOB_EVALUATION_PLAN_PROMPT_VERSION,
            "job_evaluation_plan_v5",
        )
        self.assertEqual(settings.JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION, "3.0")
        self.assertEqual(settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION, "3.0")
        self.assertEqual(
            settings.JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
            "job_evaluation_plan_lightweight_v2",
        )
        self.assertEqual(
            _env_example_values()["JOB_EVALUATION_PLAN_V5_PROMPT_VERSION"],
            "job_evaluation_plan_lightweight_v2",
        )
        self.assertEqual(settings.JOB_EVALUATION_PLAN_V5_AI_SCHEMA_VERSION, "5.0")
        self.assertEqual(settings.JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION, "5.0")

    def test_job_evaluation_plan_rejects_unsafe_numeric_configuration(self) -> None:
        invalid_values = {
            "JOB_EVALUATION_PLAN_TIMEOUT_SECONDS": 0,
            "JOB_EVALUATION_PLAN_MAX_INPUT_CHARS": 999,
            "JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS": 999,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: value})

    def test_screening_evaluation_defaults_are_bounded_and_versioned(self) -> None:
        settings = Settings(_env_file=None)

        self.assertTrue(settings.SCREENING_EVALUATION_ENABLED)
        self.assertEqual(settings.SCREENING_EVALUATION_MODEL, "deepseek-v4-flash")
        self.assertEqual(settings.SCREENING_EVALUATION_TIMEOUT_SECONDS, 90)
        self.assertEqual(settings.SCREENING_EVALUATION_MAX_INPUT_CHARS, 150_000)
        self.assertEqual(settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS, 12_000)
        self.assertEqual(
            settings.SCREENING_EVALUATION_PROMPT_VERSION,
            "screening_evaluation_v4",
        )
        self.assertEqual(settings.SCREENING_EVALUATION_SCHEMA_VERSION, "2.0")
        self.assertEqual(
            settings.SCREENING_EVALUATION_V5_PROMPT_VERSION,
            "screening_evaluation_lightweight_v1",
        )
        self.assertEqual(settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION, "5.0")
        self.assertEqual(settings.SCREENING_EVALUATION_TIMEZONE, "Asia/Shanghai")
        self.assertEqual(
            settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION,
            "experience_period_facts_v1",
        )
        self.assertEqual(settings.SCREENING_REDACTION_VERSION, "screening_redaction_v1")

    def test_screening_evaluation_rejects_unsafe_numeric_configuration(self) -> None:
        invalid_values = {
            "SCREENING_EVALUATION_TIMEOUT_SECONDS": 0,
            "SCREENING_EVALUATION_MAX_INPUT_CHARS": 999,
            "SCREENING_EVALUATION_MAX_OUTPUT_TOKENS": 999,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: value})

    def test_screening_worker_defaults_are_bounded_and_persistent_queue_friendly(self) -> None:
        settings = Settings(_env_file=None)
        self.assertTrue(settings.SCREENING_WORKER_ENABLED)
        self.assertEqual(settings.SCREENING_WORKER_POLL_SECONDS, 1.0)
        self.assertEqual(settings.SCREENING_WORKER_LEASE_SECONDS, 300)
        self.assertEqual(settings.SCREENING_WORKER_BATCH_SIZE, 5)

    def test_screening_worker_rejects_unsafe_limits(self) -> None:
        invalid_values = {
            "SCREENING_WORKER_POLL_SECONDS": 0,
            "SCREENING_WORKER_LEASE_SECONDS": 29,
            "SCREENING_WORKER_BATCH_SIZE": 21,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: value})

        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                SCREENING_EVALUATION_TIMEOUT_SECONDS=200,
                SCREENING_WORKER_LEASE_SECONDS=300,
            )
