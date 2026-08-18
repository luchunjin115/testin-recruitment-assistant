from unittest import TestCase

from pydantic import ValidationError

from app.schemas.screening_batch import ScreeningBatchRunRequest


class ScreeningBatchRunRequestTest(TestCase):
    def test_accepts_one_to_five_unique_application_ids(self) -> None:
        request = ScreeningBatchRunRequest(application_ids=[1, 2, 3, 4, 5])

        self.assertEqual(request.application_ids, [1, 2, 3, 4, 5])
        self.assertFalse(request.retry_failed_only)

    def test_rejects_empty_too_large_duplicate_and_non_strict_ids(self) -> None:
        invalid_ids = ([], [1, 2, 3, 4, 5, 6], [1, 1], ["1"])

        for application_ids in invalid_ids:
            with self.subTest(application_ids=application_ids), self.assertRaises(
                ValidationError
            ):
                ScreeningBatchRunRequest(application_ids=application_ids)

    def test_retry_failed_only_cannot_force_rerun(self) -> None:
        with self.assertRaises(ValidationError):
            ScreeningBatchRunRequest(
                application_ids=[1],
                retry_failed_only=True,
                force=True,
                confirm_force=True,
                reason="人工复核",
            )

    def test_force_rules_match_single_screening_request(self) -> None:
        with self.assertRaises(ValidationError):
            ScreeningBatchRunRequest(application_ids=[1], force=True)

        request = ScreeningBatchRunRequest(
            application_ids=[1],
            force=True,
            confirm_force=True,
            reason="  岗位规则变化后复核  ",
        )
        self.assertEqual(request.to_single_run_request().reason, "岗位规则变化后复核")
