from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.rebuilt import (
    BackupApplicationRequest,
    HRDecision,
    PassApplicationRequest,
    RejectApplicationRequest,
    ReverseDecisionRequest,
    StageHistoryActorType,
    StageHistoryCreate,
    StageHistoryRead,
    VoidApplicationRequest,
)


class DecisionRequestSchemaTest(TestCase):
    def test_pass_reason_is_fixed_and_manual_override_needs_detail(self) -> None:
        request = PassApplicationRequest(reason_code="meets_requirements")
        self.assertEqual(request.reason_code.value, "meets_requirements")

        with self.assertRaises(ValidationError):
            PassApplicationRequest(reason_code="manual_override")

        override = PassApplicationRequest(
            reason_code="manual_override",
            reason_detail="  HR 已核对补充证明材料  ",
        )
        self.assertEqual(override.reason_detail, "HR 已核对补充证明材料")

    def test_backup_and_reject_only_accept_job_related_reason_codes(self) -> None:
        backup = BackupApplicationRequest(reason_code="limited_headcount")
        self.assertEqual(backup.reason_code.value, "limited_headcount")

        for payload in (
            {"reason_code": "age"},
            {"reason_code": "gender"},
            {"reason_code": "manual_override"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                RejectApplicationRequest.model_validate({**payload, "confirmed": True})

    def test_reject_and_void_require_strict_confirmation(self) -> None:
        for confirmed in (False, "true", 1):
            with self.subTest(confirmed=confirmed), self.assertRaises(ValidationError):
                RejectApplicationRequest(
                    reason_code="required_skill_missing",
                    confirmed=confirmed,
                )
            with self.subTest(confirmed=confirmed), self.assertRaises(ValidationError):
                VoidApplicationRequest(reason_code="entry_error", confirmed=confirmed)

        rejected = RejectApplicationRequest(
            reason_code="required_skill_missing",
            confirmed=True,
        )
        voided = VoidApplicationRequest(reason_code="wrong_job", confirmed=True)
        self.assertTrue(rejected.confirmed)
        self.assertTrue(voided.confirmed)

    def test_decision_reversal_requires_fixed_reason_and_explanation(self) -> None:
        with self.assertRaises(ValidationError):
            ReverseDecisionRequest(reason_code="new_evidence", reason_detail="   ")
        with self.assertRaises(ValidationError):
            ReverseDecisionRequest(reason_code="personal_preference", reason_detail="说明")

        request = ReverseDecisionRequest(
            reason_code="new_evidence",
            reason_detail="收到新的岗位相关证明",
        )
        self.assertEqual(request.reason_detail, "收到新的岗位相关证明")


class StageHistorySchemaTest(TestCase):
    def valid_payload(self) -> dict:
        return {
            "application_id": 1,
            "from_recruitment_stage": "hr_review",
            "to_recruitment_stage": "screening_passed",
            "from_hr_decision": "pending",
            "to_hr_decision": "passed",
            "reason_code": "meets_requirements",
            "reason_detail": None,
            "actor_type": "hr",
            "actor_id": None,
            "actor_label": "本地 HR（未认证）",
            "screening_result_id": 2,
            "overrides_ai_recommendation": False,
        }

    def test_create_uses_stable_stage_decision_actor_and_reason_enums(self) -> None:
        history = StageHistoryCreate.model_validate(self.valid_payload())

        self.assertIs(history.to_hr_decision, HRDecision.PASSED)
        self.assertIs(history.actor_type, StageHistoryActorType.HR)
        self.assertEqual(history.reason_code.value, "meets_requirements")

    def test_application_created_is_a_stable_initial_history_reason(self) -> None:
        payload = self.valid_payload()
        payload.update(
            {
                "from_recruitment_stage": None,
                "to_recruitment_stage": "applied",
                "from_hr_decision": None,
                "to_hr_decision": "pending",
                "reason_code": "application_created",
                "screening_result_id": None,
            }
        )

        history = StageHistoryCreate.model_validate(payload)
        self.assertEqual(history.reason_code.value, "application_created")

    def test_create_rejects_unknown_fields_values_and_coerced_types(self) -> None:
        invalid_payloads = []
        for field, value in (
            ("application_id", "1"),
            ("to_recruitment_stage", "interviewing"),
            ("to_hr_decision", "approved"),
            ("reason_code", "free_text_reason"),
            ("actor_type", "ai"),
            ("overrides_ai_recommendation", 1),
        ):
            payload = self.valid_payload()
            payload[field] = value
            invalid_payloads.append(payload)

        payload = self.valid_payload()
        payload["unknown"] = True
        invalid_payloads.append(payload)

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                StageHistoryCreate.model_validate(payload)

    def test_read_requires_server_id_and_timezone_aware_timestamp(self) -> None:
        payload = self.valid_payload()
        payload.update({"id": 10, "created_at": datetime(2026, 8, 17, tzinfo=timezone.utc)})
        history = StageHistoryRead.model_validate(payload)
        self.assertEqual(history.id, 10)

        payload["created_at"] = datetime(2026, 8, 17)
        with self.assertRaises(ValidationError):
            StageHistoryRead.model_validate(payload)
