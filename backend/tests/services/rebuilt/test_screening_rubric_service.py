from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.activity_log import ActivityLog
from app.models.rebuilt.job import Job
from app.models.rebuilt.job_screening_rubric import JobScreeningRubric
from app.schemas.rebuilt.screening_rubric import (
    JobScreeningRubricRead,
    ScreeningRubricUpdateRequest,
)
from app.services.rebuilt.screening_rubric_service import (
    CurrentScreeningRubricNotFoundError,
    ScreeningRubricJobNotFoundError,
    ScreeningRubricService,
)


TEST_TIME = datetime(2026, 8, 17, tzinfo=timezone.utc)


def make_job(job_id: int = 1) -> Job:
    return Job(
        id=job_id,
        title="后端开发工程师",
        requirements={"schema_version": "1.0"},
        status="open",
    )


def make_rubric(
    rubric_id: int = 10,
    *,
    job_id: int = 1,
    version: int = 1,
    is_current: bool = True,
    weights: tuple[int, int, int, int, int] = (40, 25, 20, 10, 5),
) -> JobScreeningRubric:
    return JobScreeningRubric(
        id=rubric_id,
        job_id=job_id,
        version=version,
        must_have_requirements_weight=weights[0],
        work_experience_relevance_weight=weights[1],
        projects_and_capability_weight=weights[2],
        preferred_qualifications_weight=weights[3],
        keywords_and_additional_weight=weights[4],
        schema_version="1.0",
        subcriteria_version="1.0",
        recommendation_thresholds_version="1.0",
        fairness_rules_version="1.0",
        is_current=is_current,
        change_reason="initial_default",
        change_detail="默认规则",
        created_by="system",
        created_at=TEST_TIME,
    )


def make_session() -> Mock:
    session = Mock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.add_all = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class ScreeningRubricServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ScreeningRubricService()
        self.db = make_session()

    async def test_get_current_rubric_checks_job_and_returns_current_version(self) -> None:
        job = make_job()
        rubric = make_rubric()
        self.db.get.return_value = job
        self.db.scalar.return_value = rubric

        result = await self.service.get_current_rubric(self.db, 1)

        self.assertIs(result, rubric)
        self.db.get.assert_awaited_once_with(Job, 1)
        statement = self.db.scalar.await_args.args[0]
        self.assertIn("job_screening_rubrics.is_current IS true", str(statement))

    async def test_missing_job_and_missing_current_rubric_are_distinct(self) -> None:
        self.db.get.return_value = None
        with self.assertRaises(ScreeningRubricJobNotFoundError):
            await self.service.get_current_rubric(self.db, 99)
        self.db.scalar.assert_not_awaited()

        missing_rubric_db = make_session()
        missing_rubric_db.get.return_value = make_job()
        missing_rubric_db.scalar.return_value = None
        with self.assertRaises(CurrentScreeningRubricNotFoundError):
            await self.service.get_current_rubric(missing_rubric_db, 1)

    async def test_update_creates_new_version_and_activity_log_in_one_transaction(self) -> None:
        current = make_rubric()
        self.db.scalar.side_effect = [make_job(), current]
        request = ScreeningRubricUpdateRequest(
            weights={
                "must_have_requirements": 45,
                "work_experience_relevance": 25,
                "projects_and_capability": 20,
                "preferred_qualifications": 5,
                "keywords_and_additional": 5,
            },
            change_detail="提高必备条件权重",
        )

        result = await self.service.update_rubric(self.db, 1, request)

        self.assertFalse(current.is_current)
        self.assertEqual(result.version, 2)
        self.assertTrue(result.is_current)
        self.assertEqual(result.change_reason, "hr_adjustment")
        self.assertEqual(result.weights["must_have_requirements"], 45)
        rubric, activity = self.db.add_all.call_args.args[0]
        self.assertIs(rubric, result)
        self.assertIsInstance(activity, ActivityLog)
        self.assertEqual(activity.action, "job_screening_rubric_updated")
        self.assertEqual(activity.detail["from_version"], 1)
        self.assertEqual(activity.detail["to_version"], 2)
        self.assertEqual(self.db.flush.await_count, 2)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(result)
        self.db.rollback.assert_not_awaited()

    async def test_restore_default_creates_audited_version(self) -> None:
        current = make_rubric(weights=(45, 25, 20, 5, 5))
        self.db.scalar.side_effect = [make_job(), current]

        result = await self.service.update_rubric(
            self.db,
            1,
            ScreeningRubricUpdateRequest(
                restore_defaults=True,
                change_detail="恢复平台默认评分权重",
            ),
        )

        self.assertEqual(result.weights, {
            "must_have_requirements": 40,
            "work_experience_relevance": 25,
            "projects_and_capability": 20,
            "preferred_qualifications": 10,
            "keywords_and_additional": 5,
        })
        self.assertEqual(result.change_reason, "restore_default")

    async def test_failure_rolls_back_old_and_new_versions_together(self) -> None:
        current = make_rubric()
        self.db.scalar.side_effect = [make_job(), current]
        self.db.flush.side_effect = [None, RuntimeError("database failure")]

        with self.assertRaises(RuntimeError):
            await self.service.update_rubric(
                self.db,
                1,
                ScreeningRubricUpdateRequest(
                    restore_defaults=True,
                    change_detail="验证事务回滚",
                ),
            )

        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_model_weights_property_satisfies_strict_read_schema(self) -> None:
        result = JobScreeningRubricRead.model_validate(make_rubric())

        self.assertEqual(result.weights.must_have_requirements, 40)
        self.assertEqual(result.version, 1)
