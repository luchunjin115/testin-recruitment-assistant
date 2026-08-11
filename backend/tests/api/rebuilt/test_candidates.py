from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.candidates import router
from app.core.database import get_db
from app.models.rebuilt.candidate import Candidate
from app.models.rebuilt.education import Education
from app.models.rebuilt.project_experience import ProjectExperience
from app.models.rebuilt.work_experience import WorkExperience
from app.schemas.rebuilt.candidate import (
    CandidateCreate,
    CandidateFromResumeCreate,
    CandidateUpdate,
)
from app.services.rebuilt.candidate_service import (
    CandidateJobNotFoundError,
    CandidateResumeAlreadyBoundError,
    CandidateResumeJobConflictError,
    CandidateResumeNotFoundError,
    candidate_service,
)


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def make_candidate(
    candidate_id: int,
    name: str,
    *,
    status: str = "new",
    with_experiences: bool = False,
) -> Candidate:
    candidate = Candidate(
        id=candidate_id,
        name=name,
        email=f"candidate{candidate_id}@example.com",
        current_title="后端开发工程师",
        status=status,
        tags=["Python", "PostgreSQL"],
        created_at=TEST_TIME,
        updated_at=TEST_TIME,
    )
    candidate.education_records = []
    candidate.work_experiences = []
    candidate.project_experiences = []

    if with_experiences:
        candidate.education_records = [
            Education(
                id=101,
                candidate_id=candidate_id,
                school="示例大学",
                degree="本科",
                is_985=False,
                is_211=True,
                created_at=TEST_TIME,
                updated_at=TEST_TIME,
            )
        ]
        candidate.work_experiences = [
            WorkExperience(
                id=201,
                candidate_id=candidate_id,
                company="示例科技",
                title="开发工程师",
                tech_stack=["Python"],
                created_at=TEST_TIME,
                updated_at=TEST_TIME,
            )
        ]
        candidate.project_experiences = [
            ProjectExperience(
                id=301,
                candidate_id=candidate_id,
                project_name="招聘助手",
                role="后端开发",
                tech_stack=["FastAPI"],
                created_at=TEST_TIME,
                updated_at=TEST_TIME,
            )
        ]
    return candidate


class CandidateApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_create_candidate_returns_201_and_nested_experiences(self) -> None:
        created = make_candidate(1, "张三", with_experiences=True)
        create_mock = AsyncMock(return_value=created)

        with patch.object(candidate_service, "create_candidate", create_mock):
            response = self.client.post(
                "/candidates",
                json={
                    "name": "张三",
                    "email": "zhangsan@example.com",
                    "education_records": [
                        {"school": "示例大学", "degree": "本科", "is_211": True}
                    ],
                    "work_experiences": [
                        {"company": "示例科技", "title": "开发工程师"}
                    ],
                    "project_experiences": [
                        {"project_name": "招聘助手", "role": "后端开发"}
                    ],
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["education_records"][0]["school"], "示例大学")
        self.assertEqual(response.json()["work_experiences"][0]["company"], "示例科技")
        self.assertEqual(response.json()["project_experiences"][0]["project_name"], "招聘助手")

        create_mock.assert_awaited_once()
        passed_db, passed_data = create_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertIsInstance(passed_data, CandidateCreate)
        self.assertEqual(passed_data.education_records[0].school, "示例大学")

    def test_create_candidate_rejects_empty_name_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(candidate_service, "create_candidate", create_mock):
            response = self.client.post("/candidates", json={"name": ""})

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_create_candidate_rejects_negative_age_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(candidate_service, "create_candidate", create_mock):
            response = self.client.post("/candidates", json={"name": "张三", "age": -1})

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_create_candidate_from_resume_returns_201(self) -> None:
        created = make_candidate(12, "简历确认候选人", with_experiences=True)
        confirm_mock = AsyncMock(return_value=created)

        with patch.object(candidate_service, "create_candidate_from_resume", confirm_mock):
            response = self.client.post(
                "/candidates/from-resume",
                json={
                    "resume_id": 20,
                    "candidate": {
                        "name": "简历确认候选人",
                        "education_records": [{"school": "示例大学"}],
                    },
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 12)
        passed_db, passed_resume_id, passed_candidate = confirm_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_resume_id, 20)
        self.assertIsInstance(passed_candidate, CandidateCreate)
        self.assertEqual(passed_candidate.name, "简历确认候选人")

    def test_create_candidate_from_resume_maps_missing_resume_to_404(self) -> None:
        error = CandidateResumeNotFoundError("待绑定简历不存在")
        with patch.object(
            candidate_service,
            "create_candidate_from_resume",
            AsyncMock(side_effect=error),
        ):
            response = self.client.post(
                "/candidates/from-resume",
                json={"resume_id": 999, "candidate": {"name": "候选人"}},
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "待绑定简历不存在"})

    def test_create_candidate_from_resume_maps_missing_job_to_404(self) -> None:
        error = CandidateJobNotFoundError("岗位不存在")
        with patch.object(
            candidate_service,
            "create_candidate_from_resume",
            AsyncMock(side_effect=error),
        ):
            response = self.client.post(
                "/candidates/from-resume",
                json={"resume_id": 20, "candidate": {"name": "候选人"}},
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "岗位不存在"})

    def test_create_candidate_from_resume_maps_binding_conflicts_to_409(self) -> None:
        errors = (
            CandidateResumeAlreadyBoundError("简历已绑定候选人"),
            CandidateResumeJobConflictError("候选人岗位与简历岗位不一致"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with patch.object(
                    candidate_service,
                    "create_candidate_from_resume",
                    AsyncMock(side_effect=error),
                ):
                    response = self.client.post(
                        "/candidates/from-resume",
                        json={"resume_id": 20, "candidate": {"name": "候选人"}},
                    )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json(), {"detail": str(error)})

    def test_create_candidate_from_resume_validates_nested_request(self) -> None:
        confirm_mock = AsyncMock()
        invalid_requests = (
            {"resume_id": 0, "candidate": {"name": "候选人"}},
            {"resume_id": 20, "candidate": {"name": ""}},
        )
        with patch.object(candidate_service, "create_candidate_from_resume", confirm_mock):
            for payload in invalid_requests:
                with self.subTest(payload=payload):
                    response = self.client.post("/candidates/from-resume", json=payload)
                    self.assertEqual(response.status_code, 422)
        confirm_mock.assert_not_awaited()

    def test_list_candidates_returns_200_and_candidate_list(self) -> None:
        list_mock = AsyncMock(
            return_value=[
                make_candidate(2, "候选人二", with_experiences=True),
                make_candidate(1, "候选人一"),
            ]
        )

        with patch.object(candidate_service, "list_candidates", list_mock):
            response = self.client.get("/candidates")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [2, 1])
        self.assertEqual(len(response.json()[0]["education_records"]), 1)
        list_mock.assert_awaited_once_with(self.db)

    def test_list_candidates_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])

        with patch.object(candidate_service, "list_candidates", list_mock):
            response = self.client.get("/candidates")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_candidate_returns_200_and_candidate(self) -> None:
        get_mock = AsyncMock(return_value=make_candidate(7, "王五", with_experiences=True))

        with patch.object(candidate_service, "get_candidate", get_mock):
            response = self.client.get("/candidates/7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 7)
        self.assertEqual(response.json()["name"], "王五")
        get_mock.assert_awaited_once_with(self.db, 7)

    def test_get_candidate_returns_404_when_not_found(self) -> None:
        get_mock = AsyncMock(return_value=None)

        with patch.object(candidate_service, "get_candidate", get_mock):
            response = self.client.get("/candidates/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "候选人不存在"})

    def test_update_candidate_returns_200_and_updated_candidate(self) -> None:
        updated = make_candidate(3, "赵六", status="screening", with_experiences=True)
        updated.current_title = "高级后端开发工程师"
        update_mock = AsyncMock(return_value=updated)

        with patch.object(candidate_service, "update_candidate", update_mock):
            response = self.client.put(
                "/candidates/3",
                json={"current_title": "高级后端开发工程师", "status": "screening"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_title"], "高级后端开发工程师")
        self.assertEqual(response.json()["status"], "screening")

        passed_db, passed_id, passed_data = update_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_id, 3)
        self.assertIsInstance(passed_data, CandidateUpdate)

    def test_update_candidate_returns_404_when_not_found(self) -> None:
        update_mock = AsyncMock(return_value=None)

        with patch.object(candidate_service, "update_candidate", update_mock):
            response = self.client.put("/candidates/999", json={"status": "screening"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "候选人不存在"})

    def test_update_candidate_rejects_empty_name_before_service_call(self) -> None:
        update_mock = AsyncMock()

        with patch.object(candidate_service, "update_candidate", update_mock):
            response = self.client.put("/candidates/3", json={"name": ""})

        self.assertEqual(response.status_code, 422)
        update_mock.assert_not_awaited()

    def test_delete_candidate_returns_204_and_empty_body(self) -> None:
        delete_mock = AsyncMock(return_value=True)

        with patch.object(candidate_service, "delete_candidate", delete_mock):
            response = self.client.delete("/candidates/4")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        delete_mock.assert_awaited_once_with(self.db, 4)

    def test_delete_candidate_returns_404_when_not_found(self) -> None:
        delete_mock = AsyncMock(return_value=False)

        with patch.object(candidate_service, "delete_candidate", delete_mock):
            response = self.client.delete("/candidates/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "候选人不存在"})
