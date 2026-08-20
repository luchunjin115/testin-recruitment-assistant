from unittest import TestCase

from app.core.database import Base
from app.models import Application, StageHistory


class ApplicationModelTest(TestCase):
    def test_application_keeps_identity_resume_and_hr_contract(self) -> None:
        table = Application.__table__
        self.assertFalse(table.c.candidate_id.nullable)
        self.assertFalse(table.c.job_id.nullable)
        self.assertFalse(table.c.current_resume_id.nullable)
        self.assertIn("hr_decision", table.c)
        self.assertNotIn("ai_status", table.c)
        self.assertNotIn("current_screening_result_id", table.c)
        names = {constraint.name for constraint in table.constraints}
        self.assertIn("ck_applications_hr_decision_allowed", names)
        self.assertIn("uq_applications_active_candidate_job", {index.name for index in table.indexes})

    def test_stage_history_is_independent_from_legacy_ai_result(self) -> None:
        table = StageHistory.__table__
        self.assertIn("application_id", table.c)
        self.assertIn("reason_code", table.c)
        self.assertNotIn("screening_result_id", table.c)
        self.assertNotIn("overrides_ai_recommendation", table.c)

    def test_retired_tables_are_not_registered_in_runtime_metadata(self) -> None:
        self.assertNotIn("job_screening_rubrics", Base.metadata.tables)
        self.assertNotIn("screening_results", Base.metadata.tables)
        self.assertTrue({"applications", "stage_histories"}.issubset(Base.metadata.tables))
