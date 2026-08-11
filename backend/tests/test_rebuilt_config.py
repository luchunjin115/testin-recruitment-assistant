from unittest import TestCase

from pydantic import ValidationError

from app.core.config import Settings


class RebuiltSettingsTest(TestCase):
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
