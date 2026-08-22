from unittest import TestCase

from sqlalchemy import Text

from app.models.job import Job


class JobFiveSectionModelContractTest(TestCase):
    def test_model_has_five_nullable_text_columns_and_no_legacy_jd_columns(self) -> None:
        table = Job.__table__
        five_fields = (
            "job_background",
            "job_responsibilities",
            "candidate_requirements",
            "preferred_qualifications",
            "public_notes",
        )

        for field in five_fields:
            with self.subTest(field=field):
                self.assertIn(field, table.c)
                self.assertIsInstance(table.c[field].type, Text)
                self.assertTrue(table.c[field].nullable)

        for field in ("description", "requirements", "legacy_requirements"):
            with self.subTest(legacy_field=field):
                self.assertNotIn(field, table.c)
