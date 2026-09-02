from datetime import datetime, timezone
from unittest import TestCase
from uuid import UUID

from pydantic import ValidationError

from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.schemas.public_application import (
    ApplicationProcessingRunCreate,
    ApplicationProcessingStatus,
    ApplicationProcessingStep,
    ApplicationProcessingTriggerType,
    ApplicationProcessingWaitingReason,
    ApplicationProcessingWarningCode,
    PublicApplicationErrorCode,
    PublicApplicationForm,
    PublicApplicationIdentityReviewReason,
    PublicApplicationIdentityReviewStatus,
    PublicApplicationSubmissionCreate,
)
from app.schemas.stage_history import StageHistoryReasonCode


NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)
HASH = "a" * 64


class PublicApplicationFormTest(TestCase):
    def valid_payload(self) -> dict:
        return {
            "name": "  张三  ",
            "phone": "+86 138-0013-8000",
            "email": "  Candidate@Example.COM ",
            "job_id": 1,
            "privacy_consent": True,
            "consent_version": " privacy-v1 ",
            "idempotency_key": "12345678-1234-5678-9234-567812345678",
        }

    def test_public_form_normalizes_contacts_and_requires_consent(self) -> None:
        form = PublicApplicationForm.model_validate(self.valid_payload())

        self.assertEqual(form.name, "张三")
        self.assertEqual(form.phone, "+8613800138000")
        self.assertEqual(form.email, "candidate@example.com")
        self.assertEqual(form.consent_version, "privacy-v1")
        self.assertIsInstance(form.idempotency_key, UUID)

        payload = self.valid_payload()
        payload["privacy_consent"] = False
        with self.assertRaises(ValidationError):
            PublicApplicationForm.model_validate(payload)

    def test_public_form_rejects_internal_and_unknown_fields(self) -> None:
        for field, value in (
            ("source", "public_apply"),
            ("candidate_id", 7),
            ("application_id", 8),
            ("hr_decision", "passed"),
        ):
            payload = self.valid_payload()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                PublicApplicationForm.model_validate(payload)

    def test_confirmed_254_character_email_contract_matches_candidate_schema(self) -> None:
        long_email = (
            f"{'a' * 64}@{'b' * 63}.{'c' * 63}.{'d' * 61}"
        )
        self.assertEqual(len(long_email), 254)
        payload = self.valid_payload()
        payload["email"] = long_email

        form = PublicApplicationForm.model_validate(payload)
        CandidateCreate(name="张三", email=form.email)
        CandidateUpdate(email=form.email)

        payload["email"] = f"{long_email}x"
        with self.assertRaises(ValidationError):
            PublicApplicationForm.model_validate(payload)


class PublicApplicationPersistenceSchemaTest(TestCase):
    def valid_submission(self, **overrides) -> dict:
        payload = {
            "application_id": 1,
            "resume_id": 2,
            "submission_reference": "AP-7K9M2Q4X",
            "idempotency_key_hash": HASH,
            "request_fingerprint": "b" * 64,
            "consent_version": "privacy-v1",
            "consented_at": NOW,
        }
        payload.update(overrides)
        return payload

    def test_identity_review_status_and_reasons_are_consistent(self) -> None:
        clear = PublicApplicationSubmissionCreate.model_validate(self.valid_submission())
        self.assertIs(
            clear.identity_review_status,
            PublicApplicationIdentityReviewStatus.CLEAR,
        )

        review = PublicApplicationSubmissionCreate.model_validate(
            self.valid_submission(
                identity_review_status="needs_review",
                identity_review_reasons=["same_name", "contact_conflict"],
            )
        )
        self.assertEqual(
            review.identity_review_reasons,
            [
                PublicApplicationIdentityReviewReason.SAME_NAME,
                PublicApplicationIdentityReviewReason.CONTACT_CONFLICT,
            ],
        )

        invalid_states = (
            {"identity_review_status": "clear", "identity_review_reasons": ["same_name"]},
            {"identity_review_status": "needs_review", "identity_review_reasons": []},
            {
                "identity_review_status": "reviewed",
                "identity_review_reasons": ["same_name", "same_name"],
            },
        )
        for override in invalid_states:
            with self.subTest(override=override), self.assertRaises(ValidationError):
                PublicApplicationSubmissionCreate.model_validate(
                    self.valid_submission(**override)
                )

    def test_processing_enums_match_confirmed_contract(self) -> None:
        self.assertEqual(
            {item.value for item in ApplicationProcessingStatus},
            {
                "queued",
                "running",
                "waiting_screening",
                "succeeded",
                "succeeded_with_warnings",
                "failed",
                "paused",
            },
        )
        self.assertEqual(
            {item.value for item in ApplicationProcessingStep},
            {
                "extract_text",
                "structure_resume",
                "trigger_screening",
                "await_screening",
                "completed",
            },
        )
        self.assertEqual(
            {item.value for item in ApplicationProcessingTriggerType},
            {"automatic", "manual_retry"},
        )
        self.assertEqual(
            {item.value for item in ApplicationProcessingWaitingReason},
            {"job_closed", "existing_application_resume_choice"},
        )

    def test_processing_state_error_warning_and_lease_rules_are_strict(self) -> None:
        base = {
            "submission_id": 1,
            "application_id": 2,
            "resume_id": 3,
            "trigger_type": "automatic",
        }
        queued = ApplicationProcessingRunCreate.model_validate(base)
        self.assertIs(queued.status, ApplicationProcessingStatus.QUEUED)

        ApplicationProcessingRunCreate.model_validate(
            {
                **base,
                "status": "paused",
                "current_step": "trigger_screening",
                "waiting_reason": "job_closed",
            }
        )
        ApplicationProcessingRunCreate.model_validate(
            {
                **base,
                "status": "failed",
                "current_step": "extract_text",
                "completed_at": NOW,
                "error_code": "RESUME_TEXT_EXTRACTION_FAILED",
                "error_message": "无法安全提取简历原文",
            }
        )
        ApplicationProcessingRunCreate.model_validate(
            {
                **base,
                "status": "succeeded_with_warnings",
                "current_step": "completed",
                "completed_at": NOW,
                "warning_codes": ["RESUME_STRUCTURE_FAILED"],
            }
        )

        invalid_payloads = (
            {**base, "status": "paused"},
            {**base, "status": "queued", "waiting_reason": "job_closed"},
            {**base, "status": "failed", "completed_at": NOW},
            {**base, "status": "succeeded", "current_step": "completed"},
            {
                **base,
                "status": "succeeded_with_warnings",
                "current_step": "completed",
                "completed_at": NOW,
            },
            {
                **base,
                "status": "running",
                "started_at": NOW,
                "lease_owner": "worker-1",
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ApplicationProcessingRunCreate.model_validate(payload)

    def test_public_error_and_initial_audit_reason_codes_are_fixed(self) -> None:
        self.assertEqual(
            PublicApplicationErrorCode.REVIEW_REQUIRED.value,
            "PUBLIC_APPLICATION_REVIEW_REQUIRED",
        )
        self.assertEqual(
            ApplicationProcessingWarningCode.RESUME_STRUCTURE_FAILED.value,
            "RESUME_STRUCTURE_FAILED",
        )
        self.assertEqual(
            StageHistoryReasonCode.PUBLIC_APPLICATION_RECEIVED.value,
            "public_application_received",
        )
