from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas import (
    ApplicationCreate,
    ApplicationIntakeRequest,
    ApplicationIntakeResponse,
    ApplicationLifecycleStatus,
    ApplicationRead,
    ApplicationSource,
    HRDecision,
    RecruitmentStage,
)


class ApplicationIntakeRequestTest(TestCase):
    def valid_payload(self) -> dict:
        return {
            "name": "  张三  ",
            "phone": "+86 138-0013-8000",
            "email": "  Candidate@Example.COM ",
            "job_id": 2,
            "current_resume_id": 3,
            "source": "hr_screening",
        }

    def test_contact_fields_are_required_and_normalized(self) -> None:
        request = ApplicationIntakeRequest.model_validate(self.valid_payload())

        self.assertEqual(request.name, "张三")
        self.assertEqual(request.phone, "+8613800138000")
        self.assertEqual(request.email, "candidate@example.com")
        self.assertIs(request.source, ApplicationSource.HR_SCREENING)

        for missing_field in ("name", "phone", "email", "job_id", "current_resume_id"):
            payload = self.valid_payload()
            payload.pop(missing_field)
            with self.subTest(field=missing_field), self.assertRaises(ValidationError):
                ApplicationIntakeRequest.model_validate(payload)

    def test_invalid_phone_and_email_formats_are_rejected(self) -> None:
        for phone in ("123", "138.0013.8000", "phone-number", 13800138000):
            payload = self.valid_payload()
            payload["phone"] = phone
            with self.subTest(phone=phone), self.assertRaises(ValidationError):
                ApplicationIntakeRequest.model_validate(payload)

        for email in ("missing-at.example.com", "a..b@example.com", "a@example", 123):
            payload = self.valid_payload()
            payload["email"] = email
            with self.subTest(email=email), self.assertRaises(ValidationError):
                ApplicationIntakeRequest.model_validate(payload)

    def test_hr_direct_requires_explicit_pass_confirmation(self) -> None:
        payload = self.valid_payload()
        payload["source"] = "hr_direct"

        with self.assertRaises(ValidationError):
            ApplicationIntakeRequest.model_validate(payload)

        payload["confirm_hr_pass"] = True
        request = ApplicationIntakeRequest.model_validate(payload)
        self.assertTrue(request.confirm_hr_pass)

    def test_screening_intake_cannot_claim_hr_pass(self) -> None:
        payload = self.valid_payload()
        payload["confirm_hr_pass"] = True

        with self.assertRaises(ValidationError):
            ApplicationIntakeRequest.model_validate(payload)

    def test_resume_profile_accepts_job_material_but_forbids_identity_override(self) -> None:
        payload = self.valid_payload()
        payload["resume_profile"] = {
            "current_company": "示例科技",
            "skills": ["Python", "FastAPI"],
            "education_records": [{"school": "示例大学", "degree": "本科"}],
        }

        request = ApplicationIntakeRequest.model_validate(payload)

        self.assertEqual(request.resume_profile.current_company, "示例科技")
        self.assertEqual(request.resume_profile.skills, ["Python", "FastAPI"])
        self.assertEqual(request.resume_profile.education_records[0].school, "示例大学")

        payload["resume_profile"]["phone"] = "13900139000"
        with self.assertRaises(ValidationError):
            ApplicationIntakeRequest.model_validate(payload)

        payload = self.valid_payload()
        payload["candidate_profile"] = {"skills": ["Python"]}
        with self.assertRaises(ValidationError):
            ApplicationIntakeRequest.model_validate(payload)

    def test_unknown_fields_non_strict_ids_and_unknown_sources_are_rejected(self) -> None:
        invalid_payloads = []
        for field, value in (
            ("job_id", "2"),
            ("candidate_id", 0),
            ("source", "public_apply"),
            ("confirm_hr_pass", 1),
        ):
            payload = self.valid_payload()
            payload[field] = value
            invalid_payloads.append(payload)

        payload = self.valid_payload()
        payload["unknown"] = True
        invalid_payloads.append(payload)

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ApplicationIntakeRequest.model_validate(payload)


class ApplicationPersistenceSchemaTest(TestCase):
    def test_hr_direct_initial_state_is_fixed(self) -> None:
        application = ApplicationCreate(
            candidate_id=1,
            job_id=2,
            current_resume_id=3,
            source="hr_direct",
            recruitment_stage="screening_passed",
            hr_decision="passed",
        )

        self.assertIs(application.lifecycle_status, ApplicationLifecycleStatus.ACTIVE)

        with self.assertRaises(ValidationError):
            ApplicationCreate(
                candidate_id=1,
                job_id=2,
                current_resume_id=3,
                source="hr_direct",
                recruitment_stage="applied",
                hr_decision="pending",
            )

    def test_screening_initial_state_and_resume_requirement_are_fixed(self) -> None:
        application = ApplicationCreate(
            candidate_id=1,
            job_id=2,
            current_resume_id=3,
            source="hr_screening",
            recruitment_stage="applied",
            hr_decision="pending",
        )
        self.assertIs(application.recruitment_stage, RecruitmentStage.APPLIED)

        with self.assertRaises(ValidationError):
            ApplicationCreate(
                candidate_id=1,
                job_id=2,
                current_resume_id=None,
                source="hr_screening",
                recruitment_stage="applied",
                hr_decision="pending",
            )

    def test_legacy_source_and_legacy_stage_are_rejected(self) -> None:
        payload = {
            "candidate_id": 1,
            "job_id": 2,
            "current_resume_id": 3,
            "source": "legacy_migration",
            "recruitment_stage": "applied",
            "hr_decision": "pending",
        }
        with self.assertRaises(ValidationError):
            ApplicationCreate.model_validate(payload)

        payload["source"] = "hr_screening"
        payload["legacy_stage"] = "interview_pending"
        with self.assertRaises(ValidationError):
            ApplicationCreate.model_validate(payload)

    def test_read_requires_timezone_aware_timestamps_and_stable_enums(self) -> None:
        timestamp = datetime(2026, 8, 17, tzinfo=timezone.utc)
        application = ApplicationRead(
            id=1,
            candidate_id=2,
            job_id=3,
            current_resume_id=4,
            source="hr_screening",
            lifecycle_status="active",
            recruitment_stage="hr_review",
            hr_decision="pending",
            applied_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.assertIs(application.hr_decision, HRDecision.PENDING)

        payload = application.model_dump()
        payload["applied_at"] = datetime(2026, 8, 17)
        with self.assertRaises(ValidationError):
            ApplicationRead.model_validate(payload)


class ApplicationIntakeResponseTest(TestCase):
    def test_response_wraps_application_and_candidate_resolution(self) -> None:
        timestamp = datetime(2026, 8, 17, tzinfo=timezone.utc)
        response = ApplicationIntakeResponse.model_validate(
            {
                "application": {
                    "id": 1,
                    "candidate_id": 2,
                    "job_id": 3,
                    "current_resume_id": 4,
                    "source": "hr_screening",
                    "lifecycle_status": "active",
                    "recruitment_stage": "applied",
                    "hr_decision": "pending",
                    "applied_at": timestamp,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
                "candidate_resolution": "created",
                "existing_application_reused": False,
                "suspected_duplicate_candidate_ids": [7],
            }
        )

        self.assertEqual(response.application.id, 1)
        self.assertEqual(response.candidate_resolution.value, "created")
        self.assertEqual(response.suspected_duplicate_candidate_ids, [7])
