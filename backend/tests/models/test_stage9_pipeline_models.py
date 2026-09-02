from unittest import TestCase

from sqlalchemy import Numeric

from app.core.database import Base
from app.models import Application, InterviewRecord, OfferRecord, StageHistory


class Stage9PipelineModelTest(TestCase):
    def test_application_and_history_expose_stage9_fields_and_relationships(self) -> None:
        application_columns = Application.__table__.c
        history_columns = StageHistory.__table__.c
        self.assertIn("final_outcome", application_columns)
        self.assertTrue(application_columns.final_outcome.nullable)
        self.assertTrue(
            {
                "from_lifecycle_status",
                "to_lifecycle_status",
                "from_final_outcome",
                "to_final_outcome",
                "interview_record_id",
                "offer_record_id",
            }.issubset(history_columns.keys())
        )
        self.assertIn("interview_records", Application.__mapper__.relationships)
        self.assertIn("offer_records", Application.__mapper__.relationships)

    def test_interview_constraints_and_indexes_are_registered(self) -> None:
        table = InterviewRecord.__table__
        constraints = {item.name for item in table.constraints}
        indexes = {item.name: item for item in table.indexes}
        self.assertIn("uq_interview_records_application_round", constraints)
        self.assertIn("ck_interview_records_feedback_consistent", constraints)
        self.assertTrue(
            indexes[
                "uq_interview_records_one_scheduled_per_application"
            ].unique
        )
        self.assertIn(
            "ix_interview_records_application_status_scheduled_start",
            indexes,
        )

    def test_offer_uses_numeric_and_declares_active_uniqueness(self) -> None:
        table = OfferRecord.__table__
        amount_type = table.c.base_salary_amount.type
        months_type = table.c.salary_months.type
        self.assertIsInstance(amount_type, Numeric)
        self.assertEqual((amount_type.precision, amount_type.scale), (14, 2))
        self.assertEqual((months_type.precision, months_type.scale), (4, 1))
        constraints = {item.name for item in table.constraints}
        indexes = {item.name: item for item in table.indexes}
        self.assertIn("uq_offer_records_application_version", constraints)
        self.assertIn("ck_offer_records_salary_months_consistent", constraints)
        self.assertTrue(indexes["uq_offer_records_one_active_per_application"].unique)

    def test_runtime_metadata_registers_both_new_tables(self) -> None:
        self.assertTrue(
            {"interview_records", "offer_records"}.issubset(Base.metadata.tables)
        )
