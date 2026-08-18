from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError
from sqlalchemy import DateTime, String, Text

from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeUpdate


TEST_TIME = datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)


class ResumeStructureStateModelTest(TestCase):
    def test_model_has_six_independent_structure_columns(self) -> None:
        table = Resume.__table__

        self.assertIsInstance(table.c.structure_status.type, String)
        self.assertEqual(table.c.structure_status.type.length, 30)
        self.assertFalse(table.c.structure_status.nullable)
        self.assertEqual(table.c.structure_status.server_default.arg, "not_started")
        self.assertIsInstance(table.c.structure_error.type, Text)
        self.assertTrue(table.c.structure_error.nullable)
        self.assertEqual(table.c.structure_attempt_id.type.length, 36)
        self.assertIsInstance(table.c.structure_started_at.type, DateTime)
        self.assertTrue(table.c.structure_started_at.type.timezone)
        self.assertIsInstance(table.c.structured_at.type, DateTime)
        self.assertTrue(table.c.structured_at.type.timezone)
        self.assertEqual(table.c.structure_schema_version.type.length, 20)

    def test_structure_status_index_is_separate_from_parse_status_index(self) -> None:
        indexes = {index.name: tuple(column.name for column in index.columns) for index in Resume.__table__.indexes}

        self.assertEqual(indexes["ix_resumes_parse_status"], ("parse_status",))
        self.assertEqual(indexes["ix_resumes_structure_status"], ("structure_status",))

    def test_read_schema_exposes_structure_state(self) -> None:
        resume = Resume(
            id=100,
            candidate_id=None,
            job_id=None,
            filename="candidate.txt",
            file_path="v2/resumes/candidate.txt",
            file_type="text/plain",
            file_size=100,
            raw_text="候选人简历原文",
            parse_status="parsed",
            parse_error=None,
            parsed_snapshot=None,
            structure_status="processing",
            structure_error=None,
            structure_attempt_id="12345678-1234-1234-1234-123456789012",
            structure_started_at=TEST_TIME,
            structured_at=None,
            structure_schema_version=None,
            uploaded_at=TEST_TIME,
            parsed_at=TEST_TIME,
        )

        response = ResumeRead.model_validate(resume)

        self.assertEqual(response.parse_status, "parsed")
        self.assertEqual(response.structure_status, "processing")
        self.assertEqual(response.structure_attempt_id, "12345678-1234-1234-1234-123456789012")
        self.assertIsNone(response.structured_at)

    def test_read_schema_rejects_unknown_structure_status(self) -> None:
        payload = {
            "id": 100,
            "candidate_id": None,
            "job_id": None,
            "filename": "candidate.txt",
            "file_path": "v2/resumes/candidate.txt",
            "file_type": "text/plain",
            "file_size": 100,
            "raw_text": "候选人简历原文",
            "parse_status": "parsed",
            "parse_error": None,
            "parsed_snapshot": None,
            "structure_status": "unknown",
            "structure_error": None,
            "structure_attempt_id": None,
            "structure_started_at": None,
            "structured_at": None,
            "structure_schema_version": None,
            "uploaded_at": TEST_TIME,
            "parsed_at": TEST_TIME,
        }

        with self.assertRaises(ValidationError):
            ResumeRead.model_validate(payload)

    def test_general_create_and_update_schemas_cannot_write_structure_state(self) -> None:
        create_fields = ResumeCreate.model_fields
        update_fields = ResumeUpdate.model_fields

        for field_name in (
            "structure_status",
            "structure_error",
            "structure_attempt_id",
            "structure_started_at",
            "structured_at",
            "structure_schema_version",
        ):
            with self.subTest(field_name=field_name):
                self.assertNotIn(field_name, create_fields)
                self.assertNotIn(field_name, update_fields)
