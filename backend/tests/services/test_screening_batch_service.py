from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.screening_result import ScreeningResult
from app.schemas.screening_batch import ScreeningBatchRunRequest
from app.services.screening_batch_service import (
    ScreeningBatchApplicationsNotFoundError,
    ScreeningBatchJobMismatchError,
    ScreeningBatchJobNotOpenError,
    ScreeningBatchService,
)
from app.services.screening_service import (
    ScreeningAlreadyRunningError,
    ScreeningRunOutcome,
)


def make_application(application_id: int, *, job_id: int = 7, ai_status: str = "not_started"):
    return SimpleNamespace(id=application_id, job_id=job_id, ai_status=ai_status)


def make_outcome(
    application_id: int,
    execution_status: str,
    *,
    reused: bool = False,
    model_called: bool = True,
) -> ScreeningRunOutcome:
    result = ScreeningResult(
        id=100 + application_id,
        candidate_id=200 + application_id,
        job_id=7,
        application_id=application_id,
        attempt_number=2,
        execution_status=execution_status,
        error_code=("candidate_material_insufficient" if execution_status == "blocked" else None),
        error_message=("候选人材料不足" if execution_status == "blocked" else None),
    )
    return ScreeningRunOutcome(
        result=result,
        reused=reused,
        model_called=model_called,
    )


class FakeSingleService:
    def __init__(self, outcomes: dict[int, object]) -> None:
        self.outcomes = outcomes
        self.calls: list[int] = []

    async def run(self, db, application_id, request, **actor):
        del db, request
        self.calls.append(application_id)
        assert actor == {"actor_type": "hr", "actor_label": "HR batch screening"}
        outcome = self.outcomes[application_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_db(applications, *, job_status: str = "open"):
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(id=7, status=job_status)
    query_result = Mock()
    query_result.scalars.return_value.all.return_value = applications
    db.execute.return_value = query_result
    return db


class ScreeningBatchServiceTest(IsolatedAsyncioTestCase):
    async def test_returns_mixed_completed_failed_blocked_and_reused_items(self) -> None:
        applications = [make_application(item) for item in range(1, 6)]
        single = FakeSingleService(
            {
                1: make_outcome(1, "completed"),
                2: make_outcome(2, "failed"),
                3: make_outcome(3, "blocked", model_called=False),
                4: make_outcome(4, "completed", reused=True, model_called=False),
                5: make_outcome(5, "completed"),
            }
        )
        service = ScreeningBatchService(single_service=single)

        response = await service.run(
            make_db(applications),
            7,
            ScreeningBatchRunRequest(application_ids=[1, 2, 3, 4, 5]),
        )

        self.assertEqual(
            [item.status.value for item in response.items],
            ["completed", "failed", "blocked", "reused", "completed"],
        )
        self.assertEqual(single.calls, [1, 2, 3, 4, 5])
        self.assertEqual(response.summary.completed, 2)
        self.assertEqual(response.summary.failed, 1)
        self.assertEqual(response.summary.blocked, 1)
        self.assertEqual(response.summary.reused, 1)
        self.assertEqual(response.summary.executed, 5)

    async def test_unexpected_item_failure_rolls_back_only_that_item_and_continues(self) -> None:
        db = make_db([make_application(1), make_application(2), make_application(3)])
        single = FakeSingleService(
            {
                1: make_outcome(1, "completed"),
                2: RuntimeError("database write failed"),
                3: make_outcome(3, "completed"),
            }
        )
        service = ScreeningBatchService(single_service=single)

        response = await service.run(
            db,
            7,
            ScreeningBatchRunRequest(application_ids=[1, 2, 3]),
        )

        self.assertEqual(single.calls, [1, 2, 3])
        self.assertEqual(response.items[1].status.value, "failed")
        self.assertEqual(response.items[1].error_code, "SCREENING_ITEM_FAILED")
        db.rollback.assert_awaited_once()

    async def test_retry_failed_only_executes_failed_applications(self) -> None:
        applications = [
            make_application(1, ai_status="failed"),
            make_application(2, ai_status="completed"),
            make_application(3, ai_status="blocked"),
        ]
        single = FakeSingleService({1: make_outcome(1, "completed")})
        service = ScreeningBatchService(single_service=single)

        response = await service.run(
            make_db(applications),
            7,
            ScreeningBatchRunRequest(
                application_ids=[1, 2, 3],
                retry_failed_only=True,
            ),
        )

        self.assertEqual(single.calls, [1])
        self.assertEqual(
            [item.status.value for item in response.items],
            ["completed", "skipped", "skipped"],
        )
        self.assertEqual(response.summary.executed, 1)
        self.assertEqual(response.summary.skipped, 2)

    async def test_running_item_is_skipped_without_stopping_next_item(self) -> None:
        applications = [make_application(1), make_application(2)]
        single = FakeSingleService(
            {
                1: ScreeningAlreadyRunningError("already running"),
                2: make_outcome(2, "completed"),
            }
        )
        service = ScreeningBatchService(single_service=single)

        response = await service.run(
            make_db(applications),
            7,
            ScreeningBatchRunRequest(application_ids=[1, 2]),
        )

        self.assertEqual(single.calls, [1, 2])
        self.assertEqual(response.items[0].status.value, "skipped")
        self.assertEqual(response.items[0].error_code, "SCREENING_ALREADY_RUNNING")

    async def test_rejects_closed_job_before_loading_applications(self) -> None:
        db = make_db([], job_status="closed")
        single = FakeSingleService({})

        with self.assertRaises(ScreeningBatchJobNotOpenError):
            await ScreeningBatchService(single_service=single).run(
                db,
                7,
                ScreeningBatchRunRequest(application_ids=[1]),
            )

        db.execute.assert_not_awaited()
        self.assertEqual(single.calls, [])

    async def test_rejects_missing_or_cross_job_applications_before_any_run(self) -> None:
        single = FakeSingleService({})
        service = ScreeningBatchService(single_service=single)

        with self.assertRaises(ScreeningBatchApplicationsNotFoundError) as missing:
            await service.run(
                make_db([make_application(1)]),
                7,
                ScreeningBatchRunRequest(application_ids=[1, 2]),
            )
        self.assertEqual(missing.exception.application_ids, (2,))

        with self.assertRaises(ScreeningBatchJobMismatchError) as mismatch:
            await service.run(
                make_db([make_application(1, job_id=8)]),
                7,
                ScreeningBatchRunRequest(application_ids=[1]),
            )
        self.assertEqual(mismatch.exception.application_ids, (1,))
        self.assertEqual(single.calls, [])
