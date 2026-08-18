from unittest import TestCase

from pydantic import ValidationError

from app.core.config import Settings


class SettingsTest(TestCase):
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

    def test_screening_model_defaults_are_bounded_versioned_and_unpriced(self) -> None:
        settings = Settings(_env_file=None)

        self.assertTrue(settings.SCREENING_MODEL_ENABLED)
        self.assertEqual(settings.SCREENING_MODEL_NAME, "deepseek-v4-flash")
        self.assertEqual(settings.SCREENING_MODEL_TIMEOUT_SECONDS, 90)
        self.assertEqual(settings.SCREENING_MODEL_MAX_INPUT_CHARS, 160_000)
        self.assertEqual(settings.SCREENING_MODEL_MAX_OUTPUT_TOKENS, 8_000)
        self.assertEqual(
            settings.SCREENING_MODEL_PROMPT_VERSION,
            "screening_evaluation_v3",
        )
        self.assertEqual(settings.SCREENING_MODEL_SCHEMA_VERSION, "1.0")
        self.assertIsNone(settings.SCREENING_MODEL_INPUT_COST_PER_MILLION)
        self.assertIsNone(settings.SCREENING_MODEL_OUTPUT_COST_PER_MILLION)

    def test_screening_model_rejects_unsafe_numeric_configuration(self) -> None:
        invalid_values = {
            "SCREENING_MODEL_TIMEOUT_SECONDS": 0,
            "SCREENING_MODEL_MAX_INPUT_CHARS": 9_999,
            "SCREENING_MODEL_MAX_OUTPUT_TOKENS": 999,
            "SCREENING_MODEL_INPUT_COST_PER_MILLION": -1,
            "SCREENING_MODEL_OUTPUT_COST_PER_MILLION": -1,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(_env_file=None, **{field: value})
