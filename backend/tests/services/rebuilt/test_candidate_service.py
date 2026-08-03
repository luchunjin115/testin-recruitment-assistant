from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.candidate import Candidate
from app.schemas.rebuilt.candidate import CandidateCreate, CandidateUpdate
from app.schemas.rebuilt.education import EducationCreate
from app.schemas.rebuilt.project_experience import ProjectExperienceCreate
from app.schemas.rebuilt.work_experience import WorkExperienceCreate
from app.services.rebuilt.candidate_service import CandidateService


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class CandidateServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = CandidateService()
        self.db = make_session()

    async def test_create_candidate_with_nested_experiences(self) -> None:
        data = CandidateCreate(
            name="张三",
            current_title="后端开发工程师",
            education_records=[EducationCreate(school="示例大学", degree="本科")],
            work_experiences=[
                WorkExperienceCreate(company="示例科技", title="开发工程师")
            ],
            project_experiences=[
                ProjectExperienceCreate(project_name="招聘助手", role="后端开发")
            ],
        )

        candidate = await self.service.create_candidate(self.db, data)

        self.assertEqual(candidate.name, "张三")
        self.assertEqual(candidate.status, "new")
        self.assertEqual(candidate.education_records[0].school, "示例大学")
        self.assertEqual(candidate.work_experiences[0].company, "示例科技")
        self.assertEqual(candidate.project_experiences[0].project_name, "招聘助手")
        self.db.add.assert_called_once_with(candidate)
        self.db.commit.assert_awaited_once()
        self.assertEqual(self.db.refresh.await_count, 2)
        self.db.rollback.assert_not_awaited()

    async def test_create_candidate_allows_empty_experience_lists(self) -> None:
        candidate = await self.service.create_candidate(
            self.db,
            CandidateCreate(name="李四"),
        )

        self.assertEqual(candidate.education_records, [])
        self.assertEqual(candidate.work_experiences, [])
        self.assertEqual(candidate.project_experiences, [])
        self.db.commit.assert_awaited_once()

    async def test_get_candidate_returns_database_result(self) -> None:
        expected = Candidate(id=7, name="王五")
        self.db.scalar.return_value = expected

        candidate = await self.service.get_candidate(self.db, 7)

        self.assertIs(candidate, expected)
        self.db.scalar.assert_awaited_once()

    async def test_get_candidate_returns_none_when_not_found(self) -> None:
        self.db.scalar.return_value = None

        candidate = await self.service.get_candidate(self.db, 999)

        self.assertIsNone(candidate)

    async def test_list_candidates_returns_scalar_rows(self) -> None:
        candidates = [Candidate(id=2, name="候选人二"), Candidate(id=1, name="候选人一")]
        scalar_result = Mock()
        scalar_result.all.return_value = candidates
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_candidates(self.db)

        self.assertEqual(result, candidates)
        self.db.scalars.assert_awaited_once()

    async def test_update_candidate_only_changes_fields_in_request(self) -> None:
        existing = Candidate(
            id=3,
            name="原姓名",
            current_company="原公司",
            current_title="原职位",
            status="new",
        )
        self.db.scalar.return_value = existing

        candidate = await self.service.update_candidate(
            self.db,
            3,
            CandidateUpdate(current_title="高级后端工程师", current_company=None),
        )

        self.assertIs(candidate, existing)
        self.assertEqual(existing.name, "原姓名")
        self.assertIsNone(existing.current_company)
        self.assertEqual(existing.current_title, "高级后端工程师")
        self.assertEqual(existing.status, "new")
        self.db.commit.assert_awaited_once()

    async def test_update_candidate_returns_none_when_not_found(self) -> None:
        self.db.scalar.return_value = None

        candidate = await self.service.update_candidate(
            self.db,
            999,
            CandidateUpdate(status="screening"),
        )

        self.assertIsNone(candidate)
        self.db.commit.assert_not_awaited()

    async def test_delete_candidate_commits_when_found(self) -> None:
        existing = Candidate(id=4, name="待删除候选人")
        self.db.scalar.return_value = existing

        deleted = await self.service.delete_candidate(self.db, 4)

        self.assertTrue(deleted)
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_delete_candidate_returns_false_when_not_found(self) -> None:
        self.db.scalar.return_value = None

        deleted = await self.service.delete_candidate(self.db, 999)

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_write_failure_rolls_back_transaction(self) -> None:
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_candidate(
                self.db,
                CandidateCreate(name="回滚测试候选人"),
            )

        self.db.rollback.assert_awaited_once()

    def test_owned_experiences_are_deleted_with_candidate(self) -> None:
        relationships = (
            Candidate.education_records,
            Candidate.work_experiences,
            Candidate.project_experiences,
        )

        for relationship in relationships:
            self.assertTrue(relationship.property.cascade.delete)
            self.assertTrue(relationship.property.cascade.delete_orphan)
