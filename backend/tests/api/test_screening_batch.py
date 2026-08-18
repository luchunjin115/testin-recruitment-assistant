from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import install_job_exception_handlers, router
from app.core.database import get_db
from app.schemas.screening_batch import ScreeningBatchRunResponse
from app.services.screening_batch_service import (
    ScreeningBatchApplicationsNotFoundError,
    ScreeningBatchJobMismatchError,
    ScreeningBatchJobNotOpenError,
    screening_batch_service,
)


def make_response() -> ScreeningBatchRunResponse:
    return ScreeningBatchRunResponse.model_validate(
        {
            "job_id": 7,
            "items": [
                {
                    "application_id": 11,
                    "status": "completed",
                    "screening_result_id": 101,
                    "attempt_number": 1,
                    "model_called": True,
                },
                {
                    "application_id": 12,
                    "status": "reused",
                    "screening_result_id": 102,
                    "attempt_number": 1,
                    "reused": True,
                },
            ],
            "summary": {
                "selected": 2,
                "executed": 2,
                "completed": 1,
                "failed": 0,
                "blocked": 0,
                "reused": 1,
                "skipped": 0,
            },
        }
    )


class ScreeningBatchApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_job_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_runs_batch_and_returns_per_item_results(self) -> None:
        run_mock = AsyncMock(return_value=make_response())

        with patch.object(screening_batch_service, "run", run_mock):
            response = self.client.post(
                "/jobs/7/screenings/batch",
                json={"application_ids": [11, 12]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["reused"], 1)
        passed_db, passed_job_id, passed_data = run_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_job_id, 7)
        self.assertEqual(passed_data.application_ids, [11, 12])

    def test_invalid_batch_has_stable_422_code(self) -> None:
        run_mock = AsyncMock()

        with patch.object(screening_batch_service, "run", run_mock):
            too_many = self.client.post(
                "/jobs/7/screenings/batch",
                json={"application_ids": [1, 2, 3, 4, 5, 6]},
            )
            duplicate = self.client.post(
                "/jobs/7/screenings/batch",
                json={"application_ids": [1, 1]},
            )

        for response in (too_many, duplicate):
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"]["code"], "SCREENING_BATCH_INVALID")
        run_mock.assert_not_awaited()

    def test_maps_batch_scope_errors_to_stable_http_details(self) -> None:
        cases = (
            (
                ScreeningBatchJobNotOpenError("closed"),
                409,
                "JOB_NOT_OPEN_FOR_SCREENING",
                None,
            ),
            (
                ScreeningBatchApplicationsNotFoundError([12]),
                404,
                "BATCH_APPLICATIONS_NOT_FOUND",
                [12],
            ),
            (
                ScreeningBatchJobMismatchError([13]),
                409,
                "BATCH_APPLICATION_JOB_MISMATCH",
                [13],
            ),
        )

        for error, status_code, code, application_ids in cases:
            with self.subTest(code=code), patch.object(
                screening_batch_service,
                "run",
                AsyncMock(side_effect=error),
            ):
                response = self.client.post(
                    "/jobs/7/screenings/batch",
                    json={"application_ids": [11]},
                )
            self.assertEqual(response.status_code, status_code)
            self.assertEqual(response.json()["detail"]["code"], code)
            if application_ids is not None:
                self.assertEqual(
                    response.json()["detail"]["application_ids"],
                    application_ids,
                )
