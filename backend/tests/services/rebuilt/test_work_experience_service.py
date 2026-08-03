from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.work_experience import WorkExperienceCreate, WorkExperienceUpdate
from app.services.rebuilt.work_experience_service import WorkExperienceService


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


class WorkExperienceServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = WorkExperienceService()
        self.db = make_session()

    async def test_create_for_existing_candidate(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")
        experience = await self.service.create_work_experience(
            self.db,
            10,
            WorkExperienceCreate(
                company="示例科技",
                title="后端工程师",
                tech_stack=["Python", "PostgreSQL"],
            ),
        )

        self.assertIsNotNone(experience)
        self.assertEqual(experience.candidate_id, 10)
        self.assertEqual(experience.tech_stack, ["Python", "PostgreSQL"])
        self.db.add.assert_called_once_with(experience)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(experience)

    async def test_create_returns_none_for_missing_candidate(self) -> None:
        self.db.get.return_value = None
        result = await self.service.create_work_experience(
            self.db, 999, WorkExperienceCreate(company="示例科技")
        )

        self.assertIsNone(result)
        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_get_returns_database_result(self) -> None:
        expected = WorkExperience(id=7, candidate_id=10, company="示例科技")
        self.db.get.return_value = expected
        result = await self.service.get_work_experience(self.db, 7)

        self.assertIs(result, expected)
        self.db.get.assert_awaited_once_with(WorkExperience, 7)

    async def test_list_returns_rows_and_accepts_candidate_filter(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = [
            WorkExperience(id=2, candidate_id=10, company="公司二")
        ]
        self.db.scalars.return_value = scalar_result
        result = await self.service.list_work_experiences(self.db, candidate_id=10)

        self.assertEqual(len(result), 1)
        statement = self.db.scalars.await_args.args[0]
        self.assertIn("work_experience.candidate_id", str(statement))

    async def test_update_only_changes_requested_fields(self) -> None:
        existing = WorkExperience(
            id=3,
            candidate_id=10,
            company="原公司",
            title="原职位",
            tech_stack=["Python"],
        )
        self.db.get.return_value = existing
        result = await self.service.update_work_experience(
            self.db,
            3,
            WorkExperienceUpdate(title="高级工程师", tech_stack=["Python", "FastAPI"]),
        )

        self.assertIs(result, existing)
        self.assertEqual(existing.company, "原公司")
        self.assertEqual(existing.title, "高级工程师")
        self.assertEqual(existing.tech_stack, ["Python", "FastAPI"])
        self.db.commit.assert_awaited_once()

    async def test_update_returns_none_when_not_found(self) -> None:
        self.db.get.return_value = None
        result = await self.service.update_work_experience(
            self.db, 999, WorkExperienceUpdate(title="高级工程师")
        )

        self.assertIsNone(result)
        self.db.commit.assert_not_awaited()

    async def test_delete_success_and_not_found(self) -> None:
        existing = WorkExperience(id=4, candidate_id=10, company="待删除公司")
        self.db.get.side_effect = [existing, None]

        self.assertTrue(await self.service.delete_work_experience(self.db, 4))
        self.assertFalse(await self.service.delete_work_experience(self.db, 999))
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_write_failure_rolls_back(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_work_experience(
                self.db, 10, WorkExperienceCreate(company="回滚公司")
            )

        self.db.rollback.assert_awaited_once()
