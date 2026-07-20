from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.job import Job
from app.schemas.rebuilt.job import JobCreate, JobUpdate
from app.services.rebuilt.job_service import JobService


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.get = AsyncMock()
    session.scalars = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class JobServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = JobService()
        self.db = make_session()

    async def test_create_job_commits_and_refreshes(self) -> None:
        data = JobCreate(
            title="后端开发工程师",
            department="研发部",
            requirements={"required_skills": ["Python", "PostgreSQL"]},
        )

        job = await self.service.create_job(self.db, data)

        self.assertEqual(job.title, "后端开发工程师")
        self.assertEqual(job.status, "open")
        self.db.add.assert_called_once_with(job)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(job)
        self.db.rollback.assert_not_awaited()

    async def test_get_job_returns_database_result(self) -> None:
        expected = Job(id=7, title="测试工程师")
        self.db.get.return_value = expected

        job = await self.service.get_job(self.db, 7)

        self.assertIs(job, expected)
        self.db.get.assert_awaited_once_with(Job, 7)

    async def test_list_jobs_returns_scalar_rows(self) -> None:
        jobs = [Job(id=2, title="岗位二"), Job(id=1, title="岗位一")]
        scalar_result = Mock()
        scalar_result.all.return_value = jobs
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_jobs(self.db)

        self.assertEqual(result, jobs)
        self.db.scalars.assert_awaited_once()

    async def test_update_job_only_changes_fields_in_request(self) -> None:
        existing = Job(
            id=3,
            title="原岗位",
            department="原部门",
            description="原描述",
            status="open",
        )
        self.db.get.return_value = existing

        job = await self.service.update_job(
            self.db,
            3,
            JobUpdate(title="新岗位", department=None),
        )

        self.assertIs(job, existing)
        self.assertEqual(existing.title, "新岗位")
        self.assertIsNone(existing.department)
        self.assertEqual(existing.description, "原描述")
        self.assertEqual(existing.status, "open")
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(existing)

    async def test_update_job_returns_none_when_not_found(self) -> None:
        self.db.get.return_value = None

        job = await self.service.update_job(
            self.db,
            999,
            JobUpdate(title="不存在的岗位"),
        )

        self.assertIsNone(job)
        self.db.commit.assert_not_awaited()

    async def test_delete_job_commits_when_found(self) -> None:
        existing = Job(id=4, title="待删除岗位")
        self.db.get.return_value = existing

        deleted = await self.service.delete_job(self.db, 4)

        self.assertTrue(deleted)
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_delete_job_returns_false_when_not_found(self) -> None:
        self.db.get.return_value = None

        deleted = await self.service.delete_job(self.db, 999)

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_write_failure_rolls_back_transaction(self) -> None:
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_job(
                self.db,
                JobCreate(title="回滚测试岗位"),
            )

        self.db.rollback.assert_awaited_once()
