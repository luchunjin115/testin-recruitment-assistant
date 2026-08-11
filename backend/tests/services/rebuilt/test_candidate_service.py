from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.job import Job
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.candidate import CandidateCreate, CandidateUpdate
from app.schemas.rebuilt.education import EducationCreate
from app.schemas.rebuilt.project_experience import ProjectExperienceCreate
from app.schemas.rebuilt.work_experience import WorkExperienceCreate
from app.services.rebuilt.candidate_service import (
    CandidateJobNotFoundError,
    CandidateResumeAlreadyBoundError,
    CandidateResumeJobConflictError,
    CandidateResumeNotFoundError,
    CandidateService,
)


def make_session() -> Mock:
    session = Mock()
    session.add = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
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

    async def test_create_candidate_from_resume_commits_candidate_and_binding(self) -> None:
        resume = Resume(
            id=20,
            candidate_id=None,
            job_id=None,
            filename="candidate.txt",
            file_path="v2/resumes/2026/08/server.txt",
            raw_text="服务端提取的完整原文",
            parsed_snapshot={"source": "resume"},
            parse_status="parsed",
        )
        self.db.scalar.return_value = resume
        self.db.get.return_value = Job(id=3, title="后端工程师")

        async def assign_candidate_id() -> None:
            self.db.add.call_args.args[0].id = 51

        self.db.flush.side_effect = assign_candidate_id
        data = CandidateCreate(
            name="待确认候选人",
            applied_job_id=3,
            resume_file_path="../../伪造路径.txt",
            resume_text="客户端伪造原文",
            parsed_data={"source": "client"},
            education_records=[EducationCreate(school="示例大学")],
        )

        candidate = await self.service.create_candidate_from_resume(
            self.db,
            20,
            data,
        )

        self.assertEqual(candidate.id, 51)
        self.assertEqual(candidate.resume_file_path, resume.file_path)
        self.assertEqual(candidate.resume_text, resume.raw_text)
        self.assertEqual(candidate.parsed_data, resume.parsed_snapshot)
        self.assertEqual(candidate.applied_job_id, 3)
        self.assertEqual(candidate.education_records[0].school, "示例大学")
        self.assertEqual(resume.candidate_id, 51)
        self.assertEqual(resume.job_id, 3)
        statement = self.db.scalar.await_args.args[0]
        self.assertIsNotNone(statement._for_update_arg)
        self.assertEqual(self.db.flush.await_count, 2)
        self.db.commit.assert_awaited_once()
        self.assertEqual(self.db.refresh.await_count, 2)
        self.db.rollback.assert_not_awaited()

    async def test_create_candidate_from_resume_inherits_resume_job(self) -> None:
        resume = Resume(
            id=21,
            candidate_id=None,
            job_id=4,
            filename="candidate.txt",
            file_path="v2/resumes/candidate.txt",
        )
        self.db.scalar.return_value = resume
        self.db.get.return_value = Job(id=4, title="测试工程师")

        async def assign_candidate_id() -> None:
            self.db.add.call_args.args[0].id = 52

        self.db.flush.side_effect = assign_candidate_id

        candidate = await self.service.create_candidate_from_resume(
            self.db,
            21,
            CandidateCreate(name="继承岗位候选人"),
        )

        self.assertEqual(candidate.applied_job_id, 4)
        self.assertEqual(resume.job_id, 4)

    async def test_create_candidate_from_resume_rejects_missing_resume(self) -> None:
        self.db.scalar.return_value = None

        with self.assertRaises(CandidateResumeNotFoundError):
            await self.service.create_candidate_from_resume(
                self.db,
                999,
                CandidateCreate(name="候选人"),
            )

        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_create_candidate_from_resume_rejects_already_bound_resume(self) -> None:
        self.db.scalar.return_value = Resume(
            id=22,
            candidate_id=8,
            filename="bound.txt",
            file_path="v2/resumes/bound.txt",
        )

        with self.assertRaises(CandidateResumeAlreadyBoundError):
            await self.service.create_candidate_from_resume(
                self.db,
                22,
                CandidateCreate(name="重复绑定候选人"),
            )

        self.db.add.assert_not_called()

    async def test_create_candidate_from_resume_rejects_job_conflict(self) -> None:
        self.db.scalar.return_value = Resume(
            id=23,
            candidate_id=None,
            job_id=3,
            filename="conflict.txt",
            file_path="v2/resumes/conflict.txt",
        )

        with self.assertRaises(CandidateResumeJobConflictError):
            await self.service.create_candidate_from_resume(
                self.db,
                23,
                CandidateCreate(name="岗位冲突候选人", applied_job_id=4),
            )

        self.db.get.assert_not_awaited()
        self.db.add.assert_not_called()

    async def test_create_candidate_from_resume_rejects_missing_job(self) -> None:
        self.db.scalar.return_value = Resume(
            id=24,
            candidate_id=None,
            filename="missing-job.txt",
            file_path="v2/resumes/missing-job.txt",
        )
        self.db.get.return_value = None

        with self.assertRaises(CandidateJobNotFoundError):
            await self.service.create_candidate_from_resume(
                self.db,
                24,
                CandidateCreate(name="岗位不存在候选人", applied_job_id=999),
            )

        self.db.add.assert_not_called()

    async def test_create_candidate_from_resume_commit_failure_rolls_back(self) -> None:
        resume = Resume(
            id=25,
            candidate_id=None,
            filename="rollback.txt",
            file_path="v2/resumes/rollback.txt",
        )
        self.db.scalar.return_value = resume

        async def assign_candidate_id() -> None:
            self.db.add.call_args.args[0].id = 53

        self.db.flush.side_effect = assign_candidate_id
        self.db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.service.create_candidate_from_resume(
                self.db,
                25,
                CandidateCreate(name="回滚候选人"),
            )

        self.db.rollback.assert_awaited_once()

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
