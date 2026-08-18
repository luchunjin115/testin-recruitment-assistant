from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.candidate import Candidate
from app.models.project_experience import ProjectExperience
from app.schemas.project_experience import (
    ProjectExperienceCreate,
    ProjectExperienceUpdate,
)
from app.services.project_experience_service import ProjectExperienceService


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


class ProjectExperienceServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ProjectExperienceService()
        self.db = make_session()

    async def test_create_for_existing_candidate(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")
        experience = await self.service.create_project_experience(
            self.db,
            10,
            ProjectExperienceCreate(
                project_name="招聘助手",
                role="后端开发",
                tech_stack=["FastAPI", "PostgreSQL"],
                achievements="接口响应时间降低 30%",
            ),
        )

        self.assertIsNotNone(experience)
        self.assertEqual(experience.candidate_id, 10)
        self.assertEqual(experience.tech_stack, ["FastAPI", "PostgreSQL"])
        self.assertEqual(experience.achievements, "接口响应时间降低 30%")
        self.db.add.assert_called_once_with(experience)
        self.db.commit.assert_awaited_once()

    async def test_create_returns_none_for_missing_candidate(self) -> None:
        self.db.get.return_value = None
        result = await self.service.create_project_experience(
            self.db, 999, ProjectExperienceCreate(project_name="招聘助手")
        )

        self.assertIsNone(result)
        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_get_returns_database_result(self) -> None:
        expected = ProjectExperience(id=7, candidate_id=10, project_name="招聘助手")
        self.db.get.return_value = expected
        result = await self.service.get_project_experience(self.db, 7)

        self.assertIs(result, expected)
        self.db.get.assert_awaited_once_with(ProjectExperience, 7)

    async def test_list_returns_rows_and_accepts_candidate_filter(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = [
            ProjectExperience(id=2, candidate_id=10, project_name="项目二")
        ]
        self.db.scalars.return_value = scalar_result
        result = await self.service.list_project_experiences(self.db, candidate_id=10)

        self.assertEqual(len(result), 1)
        statement = self.db.scalars.await_args.args[0]
        self.assertIn("project_experience.candidate_id", str(statement))

    async def test_update_only_changes_requested_fields(self) -> None:
        existing = ProjectExperience(
            id=3,
            candidate_id=10,
            project_name="原项目",
            role="开发",
            achievements="原成果",
            tech_stack=["Python"],
        )
        self.db.get.return_value = existing
        result = await self.service.update_project_experience(
            self.db,
            3,
            ProjectExperienceUpdate(
                role="负责人",
                achievements="新成果",
                tech_stack=["Python", "FastAPI"],
            ),
        )

        self.assertIs(result, existing)
        self.assertEqual(existing.project_name, "原项目")
        self.assertEqual(existing.role, "负责人")
        self.assertEqual(existing.achievements, "新成果")
        self.db.commit.assert_awaited_once()

    async def test_update_returns_none_when_not_found(self) -> None:
        self.db.get.return_value = None
        result = await self.service.update_project_experience(
            self.db, 999, ProjectExperienceUpdate(role="负责人")
        )

        self.assertIsNone(result)
        self.db.commit.assert_not_awaited()

    async def test_delete_success_and_not_found(self) -> None:
        existing = ProjectExperience(id=4, candidate_id=10, project_name="待删除项目")
        self.db.get.side_effect = [existing, None]

        self.assertTrue(await self.service.delete_project_experience(self.db, 4))
        self.assertFalse(await self.service.delete_project_experience(self.db, 999))
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_write_failure_rolls_back(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_project_experience(
                self.db, 10, ProjectExperienceCreate(project_name="回滚项目")
            )

        self.db.rollback.assert_awaited_once()
