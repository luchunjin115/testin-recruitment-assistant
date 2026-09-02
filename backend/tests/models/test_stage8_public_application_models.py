from unittest import TestCase

from app.core.database import Base
from app.models import ApplicationProcessingRun, Candidate, PublicApplicationSubmission


class Stage8PublicApplicationModelTest(TestCase):
    def test_candidate_email_storage_matches_public_contract(self) -> None:
        self.assertEqual(Candidate.__table__.c.email.type.length, 254)

    def test_submission_has_one_to_one_identity_and_audit_constraints(self) -> None:
        table = PublicApplicationSubmission.__table__
        constraint_names = {item.name for item in table.constraints}
        self.assertTrue(
            {
                "uq_public_application_submissions_application_id",
                "uq_public_application_submissions_resume_id",
                "uq_public_application_submissions_reference",
                "uq_public_application_submissions_idempotency_hash",
                "uq_public_application_submissions_frozen_identity",
                "ck_public_application_submissions_identity_status_allowed",
                "ck_public_application_submissions_identity_reasons_allowed",
                "ck_public_application_submissions_identity_review_consistent",
            }.issubset(constraint_names)
        )
        self.assertEqual(
            {foreign_key.ondelete for foreign_key in table.foreign_keys},
            {"RESTRICT"},
        )
        self.assertFalse(
            set(table.c.keys()).intersection(
                {"ip_address", "user_agent", "idempotency_key", "form_payload"}
            )
        )

    def test_processing_run_has_frozen_identity_and_state_constraints(self) -> None:
        table = ApplicationProcessingRun.__table__
        constraint_names = {item.name for item in table.constraints}
        self.assertTrue(
            {
                "fk_application_processing_runs_frozen_submission_identity",
                "ck_application_processing_runs_trigger_type_allowed",
                "ck_application_processing_runs_status_allowed",
                "ck_application_processing_runs_current_step_allowed",
                "ck_application_processing_runs_attempt_count_range",
                "ck_application_processing_runs_waiting_reason_matches_status",
                "ck_application_processing_runs_failed_has_safe_error",
                "ck_application_processing_runs_warning_codes_allowed",
                "ck_application_processing_runs_lease_consistent",
            }.issubset(constraint_names)
        )
        self.assertEqual(
            {foreign_key.ondelete for foreign_key in table.foreign_keys},
            {"RESTRICT"},
        )

    def test_only_one_active_processing_run_is_allowed_per_submission(self) -> None:
        index = next(
            item
            for item in ApplicationProcessingRun.__table__.indexes
            if item.name == "uq_application_processing_runs_active_submission"
        )
        self.assertTrue(index.unique)
        self.assertEqual([column.name for column in index.columns], ["submission_id"])
        predicate = str(index.dialect_options["postgresql"]["where"])
        for status in ("queued", "running", "waiting_screening"):
            self.assertIn(status, predicate)
        for historical_status in (
            "paused",
            "failed",
            "succeeded",
            "succeeded_with_warnings",
        ):
            self.assertNotIn(f"'{historical_status}'", predicate)

    def test_processing_run_does_not_store_sensitive_or_model_payloads(self) -> None:
        columns = set(ApplicationProcessingRun.__table__.columns.keys())
        self.assertFalse(
            columns.intersection(
                {
                    "resume_text",
                    "raw_response",
                    "prompt",
                    "api_key",
                    "input_tokens",
                    "output_tokens",
                }
            )
        )
        self.assertTrue(
            {
                "public_application_submissions",
                "application_processing_runs",
            }.issubset(Base.metadata.tables)
        )
