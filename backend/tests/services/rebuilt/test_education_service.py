from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.schemas.rebuilt.education import EducationCreate, EducationUpdate
from app.services.rebuilt.education_service import EducationService


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


class EducationServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = EducationService()
        self.db = make_session()

    async def test_create_education_for_existing_candidate(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")

        education = await self.service.create_education(
            self.db,
            10,
            EducationCreate(school="示例大学", degree="本科", is_211=True),
        )

        self.assertIsNotNone(education)
        self.assertEqual(education.candidate_id, 10)
        self.assertEqual(education.school, "示例大学")
        self.assertTrue(education.is_211)
        self.db.get.assert_awaited_once_with(Candidate, 10)
        self.db.add.assert_called_once_with(education)
        self.db.commit.assert_awaited_once()
        self.db.refresh.assert_awaited_once_with(education)

    async def test_create_education_returns_none_for_missing_candidate(self) -> None:
        self.db.get.return_value = None

        education = await self.service.create_education(
            self.db,
            999,
            EducationCreate(school="示例大学"),
        )

        self.assertIsNone(education)
        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_get_education_returns_database_result(self) -> None:
        expected = Education(id=7, candidate_id=10, school="示例大学")
        self.db.get.return_value = expected

        education = await self.service.get_education(self.db, 7)

        self.assertIs(education, expected)
        self.db.get.assert_awaited_once_with(Education, 7)

    async def test_list_education_returns_scalar_rows(self) -> None:
        records = [
            Education(id=2, candidate_id=10, school="大学二"),
            Education(id=1, candidate_id=10, school="大学一"),
        ]
        scalar_result = Mock()
        scalar_result.all.return_value = records
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_education(self.db)

        self.assertEqual(result, records)
        self.db.scalars.assert_awaited_once()

    async def test_list_education_accepts_candidate_filter(self) -> None:
        scalar_result = Mock()
        scalar_result.all.return_value = []
        self.db.scalars.return_value = scalar_result

        result = await self.service.list_education(self.db, candidate_id=10)

        self.assertEqual(result, [])
        statement = self.db.scalars.await_args.args[0]
        self.assertIn("education.candidate_id", str(statement))

    async def test_update_education_only_changes_requested_fields(self) -> None:
        existing = Education(
            id=3,
            candidate_id=10,
            school="原大学",
            degree="本科",
            major="计算机",
            is_985=False,
            is_211=False,
        )
        self.db.get.return_value = existing

        education = await self.service.update_education(
            self.db,
            3,
            EducationUpdate(school="新大学", is_211=True),
        )

        self.assertIs(education, existing)
        self.assertEqual(existing.school, "新大学")
        self.assertEqual(existing.degree, "本科")
        self.assertTrue(existing.is_211)
        self.db.commit.assert_awaited_once()

    async def test_update_education_returns_none_when_not_found(self) -> None:
        self.db.get.return_value = None

        education = await self.service.update_education(
            self.db,
            999,
            EducationUpdate(school="新大学"),
        )

        self.assertIsNone(education)
        self.db.commit.assert_not_awaited()

    async def test_delete_education_commits_when_found(self) -> None:
        existing = Education(id=4, candidate_id=10, school="待删除大学")
        self.db.get.return_value = existing

        deleted = await self.service.delete_education(self.db, 4)

        self.assertTrue(deleted)
        self.db.delete.assert_awaited_once_with(existing)
        self.db.commit.assert_awaited_once()

    async def test_delete_education_returns_false_when_not_found(self) -> None:
        self.db.get.return_value = None

        deleted = await self.service.delete_education(self.db, 999)

        self.assertFalse(deleted)
        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_write_failure_rolls_back_transaction(self) -> None:
        self.db.get.return_value = Candidate(id=10, name="候选人")
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_education(
                self.db,
                10,
                EducationCreate(school="回滚测试大学"),
            )

        self.db.rollback.assert_awaited_once()
