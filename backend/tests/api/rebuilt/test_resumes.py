from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.resumes import router
from app.core.database import get_db
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeUpdate
from app.services.rebuilt.resume_service import resume_service


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def make_resume(
    resume_id: int,
    filename: str,
    *,
    candidate_id: int = 10,
    job_id: int | None = 3,
    parse_status: str = "uploaded",
) -> Resume:
    return Resume(
        id=resume_id,
        candidate_id=candidate_id,
        job_id=job_id,
        filename=filename,
        file_path=f"uploads/{filename}",
        file_type="pdf",
        file_size=1024,
        raw_text=None,
        parse_status=parse_status,
        parse_error=None,
        parsed_snapshot=None,
        uploaded_at=TEST_TIME,
        parsed_at=None,
    )


class ResumeApiTest(TestCase):
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

    def test_create_resume_returns_201_and_created_resume(self) -> None:
        created = make_resume(1, "zhangsan.pdf")
        create_mock = AsyncMock(return_value=created)

        with patch.object(resume_service, "create_resume", create_mock):
            response = self.client.post(
                "/resumes",
                json={
                    "candidate_id": 10,
                    "job_id": 3,
                    "filename": "zhangsan.pdf",
                    "file_path": "uploads/zhangsan.pdf",
                    "file_type": "pdf",
                    "file_size": 1024,
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["candidate_id"], 10)
        self.assertEqual(response.json()["filename"], "zhangsan.pdf")
        self.assertEqual(response.json()["parse_status"], "uploaded")

        passed_db, passed_data = create_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertIsInstance(passed_data, ResumeCreate)
        self.assertEqual(passed_data.file_size, 1024)

    def test_create_resume_rejects_empty_filename_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(resume_service, "create_resume", create_mock):
            response = self.client.post(
                "/resumes",
                json={"candidate_id": 10, "filename": "", "file_path": "uploads/a.pdf"},
            )

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_create_resume_rejects_empty_file_path_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(resume_service, "create_resume", create_mock):
            response = self.client.post(
                "/resumes",
                json={"candidate_id": 10, "filename": "a.pdf", "file_path": ""},
            )

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_create_resume_rejects_negative_file_size_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(resume_service, "create_resume", create_mock):
            response = self.client.post(
                "/resumes",
                json={
                    "candidate_id": 10,
                    "filename": "a.pdf",
                    "file_path": "uploads/a.pdf",
                    "file_size": -1,
                },
            )

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_create_resume_rejects_invalid_parse_status_before_service_call(self) -> None:
        create_mock = AsyncMock()

        with patch.object(resume_service, "create_resume", create_mock):
            response = self.client.post(
                "/resumes",
                json={
                    "candidate_id": 10,
                    "filename": "a.pdf",
                    "file_path": "uploads/a.pdf",
                    "parse_status": "unknown",
                },
            )

        self.assertEqual(response.status_code, 422)
        create_mock.assert_not_awaited()

    def test_list_resumes_returns_200_and_resume_list(self) -> None:
        list_mock = AsyncMock(
            return_value=[make_resume(2, "new.pdf"), make_resume(1, "old.pdf")]
        )

        with patch.object(resume_service, "list_resumes", list_mock):
            response = self.client.get("/resumes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [2, 1])
        list_mock.assert_awaited_once_with(self.db)

    def test_list_resumes_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])

        with patch.object(resume_service, "list_resumes", list_mock):
            response = self.client.get("/resumes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_resume_returns_200_and_resume(self) -> None:
        get_mock = AsyncMock(return_value=make_resume(7, "resume.pdf"))

        with patch.object(resume_service, "get_resume", get_mock):
            response = self.client.get("/resumes/7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 7)
        self.assertEqual(response.json()["filename"], "resume.pdf")
        get_mock.assert_awaited_once_with(self.db, 7)

    def test_get_resume_returns_404_when_not_found(self) -> None:
        get_mock = AsyncMock(return_value=None)

        with patch.object(resume_service, "get_resume", get_mock):
            response = self.client.get("/resumes/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "简历不存在"})

    def test_update_resume_returns_200_and_updated_resume(self) -> None:
        updated = make_resume(3, "resume.pdf", job_id=None, parse_status="parsed")
        updated.raw_text = "parsed resume text"
        updated.parsed_snapshot = {"name": "Zhang San"}
        updated.parsed_at = TEST_TIME
        update_mock = AsyncMock(return_value=updated)

        with patch.object(resume_service, "update_resume", update_mock):
            response = self.client.put(
                "/resumes/3",
                json={
                    "job_id": None,
                    "raw_text": "parsed resume text",
                    "parse_status": "parsed",
                    "parsed_snapshot": {"name": "Zhang San"},
                    "parsed_at": TEST_TIME.isoformat(),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parse_status"], "parsed")
        self.assertEqual(response.json()["parsed_snapshot"], {"name": "Zhang San"})
        self.assertIsNone(response.json()["job_id"])

        passed_db, passed_id, passed_data = update_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_id, 3)
        self.assertIsInstance(passed_data, ResumeUpdate)

    def test_update_resume_returns_404_when_not_found(self) -> None:
        update_mock = AsyncMock(return_value=None)

        with patch.object(resume_service, "update_resume", update_mock):
            response = self.client.put("/resumes/999", json={"parse_status": "failed"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "简历不存在"})

    def test_update_resume_rejects_invalid_parse_status_before_service_call(self) -> None:
        update_mock = AsyncMock()

        with patch.object(resume_service, "update_resume", update_mock):
            response = self.client.put("/resumes/3", json={"parse_status": "unknown"})

        self.assertEqual(response.status_code, 422)
        update_mock.assert_not_awaited()

    def test_delete_resume_returns_204_and_empty_body(self) -> None:
        delete_mock = AsyncMock(return_value=True)

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/4")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        delete_mock.assert_awaited_once_with(self.db, 4)

    def test_delete_resume_returns_404_when_not_found(self) -> None:
        delete_mock = AsyncMock(return_value=False)

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "简历不存在"})
