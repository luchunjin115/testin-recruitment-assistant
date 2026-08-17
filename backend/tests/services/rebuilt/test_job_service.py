from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from sqlalchemy.dialects import postgresql

from app.models.rebuilt.job import Job
from app.models.rebuilt.job_screening_rubric import JobScreeningRubric
from app.schemas.rebuilt.job import JobCreate, JobUpdate
from app.services.rebuilt.job_service import (
    InvalidJobStatusTransitionError,
    JobHasReferencesError,
    JobMustBeClosedBeforeDeleteError,
    JobOpenValidationError,
    JobReferenceCounts,
    JobService,
)


def make_requirements(**overrides) -> dict:
    requirements = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台核心服务"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": [],
        "minimum_work_years": 2,
        "education_requirement": "bachelor_or_above",
        "required_experiences": [],
        "preferred_experiences": [],
        "keywords": [],
        "additional_requirements": [],
    }
    requirements.update(overrides)
    return requirements


def make_job(*, job_id: int = 1, status: str = "draft", **overrides) -> Job:
    values = {
        "id": job_id,
        "title": "后端开发工程师",
        "department": "研发部",
        "location": "上海",
        "employment_type": "full_time",
        "headcount": 2,
        "description": "负责招聘平台后端开发",
        "requirements": make_requirements(),
        "status": status,
    }
    values.update(overrides)
    return Job(**values)


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


def set_reference_counts(session: Mock, **overrides: int) -> None:
    values = {
        "candidates": 0,
        "resumes": 0,
        "screening_results": 0,
        "reports": 0,
    }
    values.update(overrides)
    result = Mock()
    result.one.return_value = SimpleNamespace(**values)
    session.execute.return_value = result


class JobServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = JobService()
        self.db = make_session()

    async def test_create_draft_commits_complete_empty_v1(self) -> None:
        async def assign_job_id() -> None:
            for call in self.db.add.call_args_list:
                item = call.args[0]
                if isinstance(item, Job) and item.id is None:
                    item.id = 1

        self.db.flush.side_effect = assign_job_id
        job = await self.service.create_job(
            self.db,
            JobCreate(title="后端开发工程师", department="研发部"),
        )

        self.assertEqual(job.title, "后端开发工程师")
        self.assertEqual(job.status, "draft")
        self.assertEqual(job.requirements["schema_version"], "1.0")
        added = [call.args[0] for call in self.db.add.call_args_list]
        rubric = next(item for item in added if isinstance(item, JobScreeningRubric))
        self.assertIn(job, added)
        self.assertEqual(rubric.job_id, 1)
        self.assertEqual(rubric.version, 1)
        self.assertEqual(rubric.weights["must_have_requirements"], 40)
        self.assertTrue(rubric.is_current)
        self.db.flush.assert_awaited_once()
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(job)
        self.db.rollback.assert_not_awaited()

    async def test_create_complete_open_job_succeeds(self) -> None:
        data = JobCreate(
            title="后端开发工程师",
            department="研发部",
            location="上海",
            employment_type="full_time",
            headcount=2,
            description="负责招聘平台后端开发",
            requirements=make_requirements(),
            status="open",
        )

        job = await self.service.create_job(self.db, data)

        self.assertEqual(job.status, "open")
        self.db.commit.assert_awaited_once()

    async def test_create_incomplete_open_job_returns_all_missing_fields(self) -> None:
        with self.assertRaises(JobOpenValidationError) as raised:
            await self.service.create_job(
                self.db,
                JobCreate(title="未完成岗位", status="open"),
            )

        self.assertEqual(
            raised.exception.fields,
            (
                "department",
                "location",
                "employment_type",
                "headcount",
                "description",
                "requirements.responsibilities",
                "requirements.required_skills",
                "requirements.minimum_work_years",
                "requirements.education_requirement",
            ),
        )
        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_get_job_returns_database_result(self) -> None:
        expected = make_job(job_id=7)
        self.db.get.return_value = expected

        job = await self.service.get_job(self.db, 7)

        self.assertIs(job, expected)
        self.db.get.assert_awaited_once_with(Job, 7)

    async def test_list_jobs_returns_rows_and_accepts_status_filter(self) -> None:
        jobs = [make_job(job_id=2), make_job(job_id=1)]
        scalar_result = Mock()
        scalar_result.all.return_value = jobs
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_jobs(self.db, status="draft")

        self.assertEqual(result, jobs)
        statement = self.db.scalars.await_args.args[0]
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("WHERE jobs.status =", compiled)
        self.assertIn("jobs.updated_at DESC, jobs.id DESC", compiled)

    async def test_update_uses_row_lock_and_allows_incomplete_closed_job(self) -> None:
        existing = make_job(status="closed", description="原描述")
        self.db.scalar.return_value = existing

        job = await self.service.update_job(
            self.db,
            1,
            JobUpdate(department=None, description=None),
        )

        self.assertIs(job, existing)
        self.assertIsNone(existing.department)
        self.assertIsNone(existing.description)
        self.assertEqual(existing.status, "closed")
        self.assert_locked_query()
        self.db.commit.assert_awaited_once()

    async def test_update_open_job_validates_merged_result_before_mutation(self) -> None:
        existing = make_job(status="open", location="上海")
        self.db.scalar.return_value = existing

        with self.assertRaises(JobOpenValidationError) as raised:
            await self.service.update_job(
                self.db,
                1,
                JobUpdate(location=None, description=None),
            )

        self.assertEqual(raised.exception.fields, ("location", "description"))
        self.assertEqual(existing.location, "上海")
        self.assertEqual(existing.description, "负责招聘平台后端开发")
        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_update_complete_open_job_commits(self) -> None:
        existing = make_job(status="open")
        self.db.scalar.return_value = existing

        job = await self.service.update_job(
            self.db,
            1,
            JobUpdate(title="高级后端开发工程师", headcount=3),
        )

        self.assertIs(job, existing)
        self.assertEqual(existing.title, "高级后端开发工程师")
        self.assertEqual(existing.headcount, 3)
        self.db.commit.assert_awaited_once()

    async def test_update_returns_none_when_not_found(self) -> None:
        self.db.scalar.return_value = None

        job = await self.service.update_job(
            self.db,
            999,
            JobUpdate(title="不存在的岗位"),
        )

        self.assertIsNone(job)
        self.db.commit.assert_not_awaited()

    async def test_open_draft_close_open_and_reopen_closed(self) -> None:
        transitions = (
            ("open_job", "draft", "open"),
            ("close_job", "open", "closed"),
            ("reopen_job", "closed", "open"),
        )

        for method_name, initial_status, expected_status in transitions:
            with self.subTest(method_name=method_name):
                db = make_session()
                job = make_job(status=initial_status)
                db.scalar.return_value = job

                result = await getattr(self.service, method_name)(db, job.id)

                self.assertIs(result, job)
                self.assertEqual(job.status, expected_status)
                db.commit.assert_awaited_once()
                db.refresh.assert_awaited_once_with(job)

    async def test_every_invalid_status_transition_rolls_back(self) -> None:
        invalid_cases = (
            ("open_job", "open"),
            ("open_job", "closed"),
            ("close_job", "draft"),
            ("close_job", "closed"),
            ("reopen_job", "draft"),
            ("reopen_job", "open"),
        )

        for method_name, current_status in invalid_cases:
            with self.subTest(method_name=method_name, current_status=current_status):
                db = make_session()
                job = make_job(status=current_status)
                db.scalar.return_value = job

                with self.assertRaises(InvalidJobStatusTransitionError) as raised:
                    await getattr(self.service, method_name)(db, job.id)

                self.assertEqual(raised.exception.current_status, current_status)
                self.assertEqual(job.status, current_status)
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_open_and_reopen_recheck_current_completeness(self) -> None:
        for method_name, status in (("open_job", "draft"), ("reopen_job", "closed")):
            with self.subTest(method_name=method_name):
                db = make_session()
                job = make_job(status=status, requirements=make_requirements(required_skills=[]))
                db.scalar.return_value = job

                with self.assertRaises(JobOpenValidationError) as raised:
                    await getattr(self.service, method_name)(db, job.id)

                self.assertEqual(
                    raised.exception.fields,
                    ("requirements.required_skills",),
                )
                self.assertEqual(job.status, status)
                db.rollback.assert_awaited_once()

    async def test_status_action_returns_none_when_job_not_found(self) -> None:
        for method_name in ("open_job", "close_job", "reopen_job"):
            with self.subTest(method_name=method_name):
                db = make_session()
                db.scalar.return_value = None

                result = await getattr(self.service, method_name)(db, 999)

                self.assertIsNone(result)
                db.commit.assert_not_awaited()

    async def test_get_reference_counts_returns_all_four_relations(self) -> None:
        set_reference_counts(
            self.db,
            candidates=2,
            resumes=3,
            screening_results=4,
            reports=5,
        )

        counts = await self.service.get_reference_counts(self.db, 1)

        self.assertEqual(
            counts,
            JobReferenceCounts(
                candidates=2,
                resumes=3,
                screening_results=4,
                reports=5,
            ),
        )
        self.assertEqual(counts.total, 14)
        self.assertEqual(
            counts.as_dict(),
            {
                "candidates": 2,
                "resumes": 3,
                "screening_results": 4,
                "reports": 5,
            },
        )

    async def test_delete_open_job_is_rejected_before_reference_query(self) -> None:
        self.db.scalar.return_value = make_job(status="open")

        with self.assertRaises(JobMustBeClosedBeforeDeleteError):
            await self.service.delete_job(self.db, 1)

        self.db.execute.assert_not_awaited()
        self.db.delete.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_each_reference_type_blocks_delete_with_all_counts(self) -> None:
        for field in ("candidates", "resumes", "screening_results", "reports"):
            with self.subTest(field=field):
                db = make_session()
                db.scalar.return_value = make_job(status="closed")
                set_reference_counts(db, **{field: 1})

                with self.assertRaises(JobHasReferencesError) as raised:
                    await self.service.delete_job(db, 1)

                self.assertEqual(raised.exception.references.as_dict()[field], 1)
                db.delete.assert_not_awaited()
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_delete_unreferenced_draft_or_closed_job_commits(self) -> None:
        for status in ("draft", "closed"):
            with self.subTest(status=status):
                db = make_session()
                existing = make_job(status=status)
                db.scalar.return_value = existing
                set_reference_counts(db)

                deleted = await self.service.delete_job(db, existing.id)

                self.assertTrue(deleted)
                self.assertEqual(db.execute.await_count, 2)
                rubric_delete = db.execute.await_args_list[1].args[0]
                self.assertIn(
                    "DELETE FROM job_screening_rubrics",
                    str(rubric_delete.compile(dialect=postgresql.dialect())),
                )
                db.delete.assert_awaited_once_with(existing)
                db.commit.assert_awaited_once()

    async def test_delete_returns_false_when_not_found(self) -> None:
        self.db.scalar.return_value = None

        deleted = await self.service.delete_job(self.db, 999)

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_write_and_locked_query_failures_roll_back(self) -> None:
        self.db.commit.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_job(self.db, JobCreate(title="回滚测试岗位"))
        self.db.rollback.assert_awaited_once()

        db = make_session()
        db.scalar.side_effect = RuntimeError("lock query failed")
        with self.assertRaisesRegex(RuntimeError, "lock query failed"):
            await self.service.close_job(db, 1)
        db.rollback.assert_awaited_once()

    def assert_locked_query(self) -> None:
        statement = self.db.scalar.await_args.args[0]
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("FOR UPDATE", compiled)
