from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.stage_history import StageHistory
from app.schemas.stage_history import (
    BackupApplicationRequest,
    PassApplicationRequest,
    RejectApplicationRequest,
    ReverseDecisionRequest,
    VoidApplicationRequest,
)
from app.services.application_decision_service import (
    ApplicationDecisionService,
    ApplicationNotFoundError,
    InvalidApplicationTransitionError,
)


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_application(
    application_id: int = 1,
    *,
    lifecycle_status: str = "active",
    recruitment_stage: str = "hr_review",
    hr_decision: str = "pending",
) -> Application:
    return Application(
        id=application_id,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status=lifecycle_status,
        recruitment_stage=recruitment_stage,
        hr_decision=hr_decision,
        applied_at=TEST_TIME,
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )


def make_session() -> Mock:
    session = Mock()
    session.add_all = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


def scalar_rows(items: list) -> Mock:
    result = Mock()
    result.all.return_value = items
    return result


class ApplicationDecisionServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ApplicationDecisionService()
        self.db = make_session()

    async def test_pass_updates_application_and_writes_both_audits_atomically(self) -> None:
        application = make_application()
        self.db.scalar.return_value = application
        request = PassApplicationRequest(reason_code="meets_requirements")

        result = await self.service.pass_application(self.db, 1, request)

        self.assertIs(result, application)
        self.assertEqual(application.lifecycle_status, "active")
        self.assertEqual(application.recruitment_stage, "screening_passed")
        self.assertEqual(application.hr_decision, "passed")
        history, activity = self.db.add_all.call_args.args[0]
        self.assertIsInstance(history, StageHistory)
        self.assertEqual(history.from_recruitment_stage, "hr_review")
        self.assertEqual(history.to_recruitment_stage, "screening_passed")
        self.assertEqual(history.reason_code, "meets_requirements")
        self.assertIsInstance(activity, ActivityLog)
        self.assertEqual(activity.action, "application_passed")
        self.assertEqual(activity.target_type, "application")
        self.assertEqual(activity.detail["from_hr_decision"], "pending")
        self.assertEqual(activity.detail["to_hr_decision"], "passed")
        self.db.flush.assert_awaited_once()
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(application)
        self.db.rollback.assert_not_awaited()

    async def test_backup_and_reject_use_fixed_target_states(self) -> None:
        backup_application = make_application()
        self.db.scalar.return_value = backup_application

        await self.service.backup_application(
            self.db,
            1,
            BackupApplicationRequest(reason_code="waiting_for_comparison"),
        )

        self.assertEqual(backup_application.lifecycle_status, "active")
        self.assertEqual(backup_application.recruitment_stage, "backup")
        self.assertEqual(backup_application.hr_decision, "backup")

        reject_db = make_session()
        rejected_application = make_application(
            recruitment_stage="backup",
            hr_decision="backup",
        )
        reject_db.scalar.return_value = rejected_application

        await self.service.reject_application(
            reject_db,
            1,
            RejectApplicationRequest(
                reason_code="required_skill_missing",
                confirmed=True,
            ),
        )

        self.assertEqual(rejected_application.lifecycle_status, "ended")
        self.assertEqual(rejected_application.recruitment_stage, "rejected")
        self.assertEqual(rejected_application.hr_decision, "rejected")
        history, activity = reject_db.add_all.call_args.args[0]
        self.assertEqual(history.reason_code, "required_skill_missing")
        self.assertEqual(activity.action, "application_rejected")

    async def test_passed_and_backup_decisions_can_be_reversed_with_a_reason(self) -> None:
        cases = (
            (
                "backup",
                make_application(
                    recruitment_stage="screening_passed",
                    hr_decision="passed",
                ),
                BackupApplicationRequest(
                    reason_code="information_pending",
                    reason_detail="需要补充证明材料",
                ),
                "backup",
            ),
            (
                "pass",
                make_application(recruitment_stage="backup", hr_decision="backup"),
                PassApplicationRequest(
                    reason_code="meets_requirements",
                    reason_detail="补充材料已核实",
                ),
                "passed",
            ),
        )
        for method_name, application, request, expected_decision in cases:
            with self.subTest(method=method_name):
                db = make_session()
                db.scalar.return_value = application
                method = getattr(self.service, f"{method_name}_application")

                await method(db, application.id, request)

                self.assertEqual(application.hr_decision, expected_decision)
                history, _ = db.add_all.call_args.args[0]
                self.assertIsNotNone(history.reason_detail)

    async def test_undo_rejection_reopens_to_pending_hr_review(self) -> None:
        application = make_application(
            lifecycle_status="ended",
            recruitment_stage="rejected",
            hr_decision="rejected",
        )
        self.db.scalar.side_effect = [application, None]

        result = await self.service.undo_rejection(
            self.db,
            1,
            ReverseDecisionRequest(
                reason_code="new_evidence",
                reason_detail="候选人补充了可验证项目材料",
            ),
        )

        self.assertIs(result, application)
        self.assertEqual(application.lifecycle_status, "active")
        self.assertEqual(application.recruitment_stage, "hr_review")
        self.assertEqual(application.hr_decision, "pending")
        history, activity = self.db.add_all.call_args.args[0]
        self.assertEqual(history.reason_code, "new_evidence")
        self.assertEqual(activity.action, "application_rejection_undone")
        self.assertEqual(self.db.scalar.await_count, 2)

    async def test_undo_rejection_rejects_another_active_application(self) -> None:
        rejected = make_application(
            lifecycle_status="ended",
            recruitment_stage="rejected",
            hr_decision="rejected",
        )
        active = make_application(application_id=2)
        self.db.scalar.side_effect = [rejected, active]

        with self.assertRaises(InvalidApplicationTransitionError):
            await self.service.undo_rejection(
                self.db,
                1,
                ReverseDecisionRequest(
                    reason_code="decision_correction",
                    reason_detail="修正错误决定",
                ),
            )

        self.db.add_all.assert_not_called()
        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_void_preserves_decision_but_ends_record_as_voided(self) -> None:
        application = make_application(
            recruitment_stage="screening_passed",
            hr_decision="passed",
        )
        self.db.scalar.return_value = application

        await self.service.void_application(
            self.db,
            1,
            VoidApplicationRequest(reason_code="wrong_job", confirmed=True),
        )

        self.assertEqual(application.lifecycle_status, "voided")
        self.assertEqual(application.recruitment_stage, "screening_passed")
        self.assertEqual(application.hr_decision, "passed")
        history, activity = self.db.add_all.call_args.args[0]
        self.assertEqual(history.from_hr_decision, history.to_hr_decision)
        self.assertEqual(activity.detail["to_lifecycle_status"], "voided")
        self.assertEqual(activity.action, "application_voided")

    async def test_missing_and_invalid_transitions_roll_back_without_audit(self) -> None:
        cases = (
            None,
            make_application(
                recruitment_stage="screening_passed",
                hr_decision="passed",
            ),
            make_application(
                lifecycle_status="ended",
                recruitment_stage="rejected",
                hr_decision="rejected",
            ),
        )
        for application in cases:
            with self.subTest(application=application):
                db = make_session()
                db.scalar.return_value = application
                expected_error = (
                    ApplicationNotFoundError
                    if application is None
                    else InvalidApplicationTransitionError
                )

                with self.assertRaises(expected_error):
                    await self.service.pass_application(
                        db,
                        1,
                        PassApplicationRequest(reason_code="meets_requirements"),
                    )

                db.add_all.assert_not_called()
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_audit_write_failure_rolls_back_application_change(self) -> None:
        application = make_application()
        self.db.scalar.return_value = application
        self.db.flush.side_effect = RuntimeError("database failure")

        with self.assertRaises(RuntimeError):
            await self.service.pass_application(
                self.db,
                1,
                PassApplicationRequest(reason_code="meets_requirements"),
            )

        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_list_history_is_ordered_and_missing_application_is_rejected(self) -> None:
        histories = [Mock(spec=StageHistory), Mock(spec=StageHistory)]
        self.db.get.return_value = make_application()
        self.db.scalars.return_value = scalar_rows(histories)

        result = await self.service.list_history(self.db, 1)

        self.assertEqual(result, histories)
        statement = self.db.scalars.await_args.args[0]
        self.assertIn("ORDER BY", str(statement))

        missing_db = make_session()
        missing_db.get.return_value = None
        with self.assertRaises(ApplicationNotFoundError):
            await self.service.list_history(missing_db, 99)
        missing_db.scalars.assert_not_awaited()
