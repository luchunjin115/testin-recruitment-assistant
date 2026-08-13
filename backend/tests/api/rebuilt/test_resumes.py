from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.resumes import router
from app.core.database import get_db
from app.adapters.rebuilt.resume_structure import (
    ResumeStructureAuthenticationError,
    ResumeStructureEmptyResponseError,
    ResumeStructureQuotaError,
    ResumeStructureRateLimitError,
    ResumeStructureResponseInterruptedError,
    ResumeStructureServiceUnavailableError,
    ResumeStructureTimeoutError,
    ResumeStructureUpstreamError,
)
from app.models.rebuilt.resume import Resume
from app.schemas.rebuilt.resume import ResumeCreate, ResumeUpdate
from app.schemas.rebuilt.resume_parse import ResumeParseDraft
from app.services.rebuilt.resume_service import resume_service
from app.services.rebuilt.resume_service import (
    ResumeAlreadyBoundError,
    ResumeFileDescriptor,
    ResumeFileUnavailableError,
    ResumeCandidateNotFoundError,
    ResumeJobNotFoundError,
    ResumeTextExtractionConflictError,
    ResumeTextExtractionFailedError,
    UnsupportedResumeFileError,
    UnsupportedResumeTextExtractionError,
)
from app.services.rebuilt.resume_structure_service import (
    ResumeStructureConflictError,
    ResumeStructureConfigurationError,
    ResumeStructureDisabledError,
    ResumeStructureInputError,
    ResumeStructureInvalidOutputError,
    ResumeStructureNotFoundError,
    ResumeStructurePrerequisiteError,
    ResumeStructureServiceResult,
    ResumeStructureSnapshotMetadata,
    ResumeStructureUnexpectedError,
    resume_structure_service,
)
from app.services.rebuilt.resume_file_cleanup import (
    ResumeCleanupStorageError,
    ResumeCleanupValidationError,
    UnsupportedResumeCleanupError,
)
from app.services.rebuilt.resume_storage import (
    EmptyResumeFileError,
    InvalidResumeContentError,
    ResumeFileTooLargeError,
    ResumeStorageError,
    UnsupportedResumeTypeError,
)


TEST_TIME = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
TEST_ATTEMPT_ID = "11111111-1111-4111-8111-111111111111"


def make_structure_draft() -> ResumeParseDraft:
    return ResumeParseDraft.model_validate(
        {
            "schema_version": "1.0",
            "basic_info": {
                "name": "测试候选人",
                "phone": "13800138000",
                "email": "candidate@example.com",
                "gender": None,
                "age": None,
                "location": "上海",
                "current_company": None,
                "current_title": None,
                "work_years": None,
                "education_level": "本科",
            },
            "education_records": [],
            "work_experiences": [],
            "project_experiences": [],
            "skills": ["Python"],
            "certifications": [],
            "self_evaluation": None,
            "warnings": [],
            "missing_fields": [],
        }
    )


def make_structure_result(
    *,
    structure_status: str = "succeeded",
    structure_error: str | None = None,
    from_cache: bool = False,
    has_previous_draft: bool = False,
) -> ResumeStructureServiceResult:
    return ResumeStructureServiceResult(
        resume_id=32,
        structure_status=structure_status,
        structure_error=structure_error,
        draft=make_structure_draft(),
        metadata=ResumeStructureSnapshotMetadata(
            model="deepseek-v4-flash",
            prompt_version="resume_structure_v1",
            schema_version="1.0",
            structured_at=TEST_TIME,
            input_characters=100,
            input_tokens=20,
            output_tokens=40,
            attempt_id=TEST_ATTEMPT_ID,
        ),
        from_cache=from_cache,
        has_previous_draft=has_previous_draft,
    )


def make_resume(
    resume_id: int,
    filename: str,
    *,
    candidate_id: int | None = 10,
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
        structure_status="not_started",
        structure_error=None,
        structure_attempt_id=None,
        structure_started_at=None,
        structured_at=None,
        structure_schema_version=None,
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

    def test_upload_resume_returns_201_and_calls_safe_upload_service(self) -> None:
        created = make_resume(8, "candidate.pdf", candidate_id=10, job_id=3)
        created.file_type = "application/pdf"
        upload_mock = AsyncMock(return_value=created)

        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "10", "job_id": "3"},
                files={"file": ("candidate.pdf", b"%PDF-1.4\nresume", "application/pdf")},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 8)
        self.assertEqual(response.json()["file_type"], "application/pdf")
        passed = upload_mock.await_args.kwargs
        self.assertIs(passed["db"], self.db)
        self.assertEqual(passed["candidate_id"], 10)
        self.assertEqual(passed["job_id"], 3)
        self.assertGreater(passed["max_size_bytes"], 0)

    def test_upload_resume_allows_candidate_to_be_omitted(self) -> None:
        created = make_resume(9, "candidate.txt", candidate_id=None, job_id=None)
        created.file_type = "text/plain"
        upload_mock = AsyncMock(return_value=created)

        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                files={"file": ("candidate.txt", b"resume", "text/plain")},
            )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["candidate_id"])
        passed = upload_mock.await_args.kwargs
        self.assertIsNone(passed["candidate_id"])
        self.assertIsNone(passed["job_id"])

    def test_upload_resume_maps_missing_candidate_to_404(self) -> None:
        upload_mock = AsyncMock(side_effect=ResumeCandidateNotFoundError("候选人不存在"))
        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "999"},
                files={"file": ("candidate.txt", b"resume", "text/plain")},
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "候选人不存在"})

    def test_upload_resume_maps_missing_job_to_404(self) -> None:
        upload_mock = AsyncMock(side_effect=ResumeJobNotFoundError("岗位不存在"))
        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "10", "job_id": "999"},
                files={"file": ("candidate.txt", b"resume", "text/plain")},
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "岗位不存在"})

    def test_upload_resume_maps_unsupported_type_to_415(self) -> None:
        upload_mock = AsyncMock(side_effect=UnsupportedResumeTypeError("unsupported"))
        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "10"},
                files={"file": ("candidate.exe", b"binary", "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 415)

    def test_upload_resume_maps_too_large_to_413(self) -> None:
        upload_mock = AsyncMock(side_effect=ResumeFileTooLargeError("too large"))
        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "10"},
                files={"file": ("candidate.txt", b"resume", "text/plain")},
            )
        self.assertEqual(response.status_code, 413)

    def test_upload_resume_maps_invalid_file_to_400(self) -> None:
        for error in (EmptyResumeFileError("empty"), InvalidResumeContentError("invalid")):
            with self.subTest(error=type(error).__name__):
                upload_mock = AsyncMock(side_effect=error)
                with patch.object(resume_service, "upload_resume", upload_mock):
                    response = self.client.post(
                        "/resumes/upload",
                        data={"candidate_id": "10"},
                        files={"file": ("candidate.txt", b"resume", "text/plain")},
                    )
                self.assertEqual(response.status_code, 400)

    def test_upload_resume_hides_storage_details_behind_500(self) -> None:
        upload_mock = AsyncMock(side_effect=ResumeStorageError("C:/private/path failed"))
        with patch.object(resume_service, "upload_resume", upload_mock):
            response = self.client.post(
                "/resumes/upload",
                data={"candidate_id": "10"},
                files={"file": ("candidate.txt", b"resume", "text/plain")},
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "文件保存失败"})

    def test_extract_text_returns_200_and_parsed_resume(self) -> None:
        parsed = make_resume(9, "candidate.txt", job_id=None, parse_status="parsed")
        parsed.file_type = "text/plain"
        parsed.raw_text = "完整 TXT 简历"
        parsed.parsed_at = TEST_TIME
        extract_mock = AsyncMock(return_value=parsed)

        with patch.object(resume_service, "extract_text", extract_mock):
            response = self.client.post("/resumes/9/extract-text")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parse_status"], "parsed")
        self.assertEqual(response.json()["raw_text"], "完整 TXT 简历")
        passed = extract_mock.await_args.kwargs
        self.assertIs(passed["db"], self.db)
        self.assertEqual(passed["resume_id"], 9)

    def test_extract_text_returns_404_when_resume_does_not_exist(self) -> None:
        with patch.object(resume_service, "extract_text", AsyncMock(return_value=None)):
            response = self.client.post("/resumes/999/extract-text")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "简历不存在"})

    def test_extract_text_maps_parsing_conflict_to_409(self) -> None:
        error = ResumeTextExtractionConflictError("简历正在解析中")
        with patch.object(resume_service, "extract_text", AsyncMock(side_effect=error)):
            response = self.client.post("/resumes/9/extract-text")
        self.assertEqual(response.status_code, 409)

    def test_extract_text_maps_unsupported_file_to_415(self) -> None:
        error = UnsupportedResumeTextExtractionError("当前步骤只支持 TXT 文本提取")
        with patch.object(resume_service, "extract_text", AsyncMock(side_effect=error)):
            response = self.client.post("/resumes/9/extract-text")
        self.assertEqual(response.status_code, 415)

    def test_extract_text_maps_extraction_failure_to_422(self) -> None:
        error = ResumeTextExtractionFailedError("原始简历文件不存在")
        with patch.object(resume_service, "extract_text", AsyncMock(side_effect=error)):
            response = self.client.post("/resumes/9/extract-text")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "原始简历文件不存在"})

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
        list_mock.assert_awaited_once_with(self.db, candidate_id=None)

    def test_list_resumes_returns_empty_list(self) -> None:
        list_mock = AsyncMock(return_value=[])

        with patch.object(resume_service, "list_resumes", list_mock):
            response = self.client.get("/resumes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_resumes_passes_candidate_filter(self) -> None:
        list_mock = AsyncMock(return_value=[make_resume(32, "candidate.pdf", candidate_id=64)])

        with patch.object(resume_service, "list_resumes", list_mock):
            response = self.client.get("/resumes?candidate_id=64")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["candidate_id"], 64)
        list_mock.assert_awaited_once_with(self.db, candidate_id=64)

    def test_get_resume_file_returns_inline_pdf_with_private_headers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "server.pdf"
            content = b"%PDF-1.4\nprivate resume"
            path.write_bytes(content)
            descriptor = ResumeFileDescriptor(
                path=path,
                filename="卢椿锦简历.pdf",
                media_type="application/pdf",
                supports_inline_preview=True,
            )
            get_file_mock = AsyncMock(return_value=descriptor)

            with patch.object(resume_service, "get_resume_file", get_file_mock):
                response = self.client.get("/resumes/32/file")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.headers["content-disposition"].startswith("inline;"))
        self.assertIn("filename*=utf-8''", response.headers["content-disposition"])
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_get_resume_file_download_query_forces_attachment(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "server.txt"
            path.write_text("candidate resume", encoding="utf-8")
            descriptor = ResumeFileDescriptor(
                path=path,
                filename="candidate.txt",
                media_type="text/plain",
                supports_inline_preview=True,
            )
            with patch.object(
                resume_service,
                "get_resume_file",
                AsyncMock(return_value=descriptor),
            ):
                response = self.client.get("/resumes/9/file?download=true")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-disposition"].startswith("attachment;"))

    def test_get_resume_file_docx_defaults_to_attachment(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "server.docx"
            path.write_bytes(b"docx")
            descriptor = ResumeFileDescriptor(
                path=path,
                filename="candidate.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                supports_inline_preview=False,
            )
            with patch.object(
                resume_service,
                "get_resume_file",
                AsyncMock(return_value=descriptor),
            ):
                response = self.client.get("/resumes/9/file")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-disposition"].startswith("attachment;"))

    def test_get_resume_file_maps_not_found_unsupported_and_unavailable(self) -> None:
        scenarios = [
            (None, 404, "简历不存在"),
            (UnsupportedResumeFileError("不支持"), 415, "不支持"),
            (ResumeFileUnavailableError("原始简历文件不存在"), 422, "文件不存在"),
        ]
        for result, expected_status, expected_detail in scenarios:
            with self.subTest(status=expected_status):
                mock = (
                    AsyncMock(return_value=None)
                    if result is None
                    else AsyncMock(side_effect=result)
                )
                with patch.object(resume_service, "get_resume_file", mock):
                    response = self.client.get("/resumes/999/file")
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_detail, response.json()["detail"])

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
        passed_db, passed_id = delete_mock.await_args.args
        self.assertIs(passed_db, self.db)
        self.assertEqual(passed_id, 4)
        self.assertIsInstance(delete_mock.await_args.kwargs["storage_root"], Path)

    def test_delete_resume_returns_404_when_not_found(self) -> None:
        delete_mock = AsyncMock(return_value=False)

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "简历不存在"})

    def test_delete_resume_rejects_bound_resume(self) -> None:
        delete_mock = AsyncMock(
            side_effect=ResumeAlreadyBoundError("已绑定候选人的简历不能通过放弃接口删除")
        )

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/4")

        self.assertEqual(response.status_code, 409)
        self.assertIn("已绑定", response.json()["detail"])

    def test_delete_resume_rejects_unsupported_stored_type(self) -> None:
        delete_mock = AsyncMock(
            side_effect=UnsupportedResumeCleanupError("当前文件类型不支持安全清理")
        )

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/4")

        self.assertEqual(response.status_code, 415)

    def test_delete_resume_rejects_invalid_file_metadata(self) -> None:
        delete_mock = AsyncMock(
            side_effect=ResumeCleanupValidationError("简历文件大小与上传记录不一致")
        )

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/4")

        self.assertEqual(response.status_code, 422)

    def test_delete_resume_hides_filesystem_failure_details(self) -> None:
        delete_mock = AsyncMock(
            side_effect=ResumeCleanupStorageError("C:/private/secret/file.pdf")
        )

        with patch.object(resume_service, "delete_resume", delete_mock):
            response = self.client.delete("/resumes/4")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "简历文件清理失败"})
        self.assertNotIn("private", response.text)

    def test_structure_resume_uses_false_by_default_and_returns_draft(self) -> None:
        structure_mock = AsyncMock(return_value=make_structure_result())

        with patch.object(resume_structure_service, "structure_resume", structure_mock):
            response = self.client.post("/resumes/32/structure", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resume_id"], 32)
        self.assertEqual(response.json()["structure_status"], "succeeded")
        self.assertFalse(response.json()["from_cache"])
        self.assertFalse(response.json()["has_previous_draft"])
        self.assertEqual(response.json()["draft"]["basic_info"]["name"], "测试候选人")
        self.assertNotIn("metadata", response.json())
        structure_mock.assert_awaited_once_with(db=self.db, resume_id=32, force=False)

    def test_structure_resume_passes_force_to_service(self) -> None:
        structure_mock = AsyncMock(
            return_value=make_structure_result(
                has_previous_draft=True,
            )
        )

        with patch.object(resume_structure_service, "structure_resume", structure_mock):
            response = self.client.post("/resumes/32/structure", json={"force": True})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["from_cache"])
        self.assertTrue(response.json()["has_previous_draft"])
        structure_mock.assert_awaited_once_with(db=self.db, resume_id=32, force=True)

    def test_structure_resume_rejects_unknown_request_fields(self) -> None:
        structure_mock = AsyncMock()

        with patch.object(resume_structure_service, "structure_resume", structure_mock):
            response = self.client.post(
                "/resumes/32/structure",
                json={"force": False, "draft": {}},
            )

        self.assertEqual(response.status_code, 422)
        structure_mock.assert_not_awaited()

    def test_structure_resume_maps_local_service_errors(self) -> None:
        cases = (
            (ResumeStructureNotFoundError("Resume 不存在"), 404),
            (ResumeStructurePrerequisiteError("简历原文尚未成功提取"), 409),
            (ResumeStructureConflictError("该简历正在进行结构化识别"), 409),
            (ResumeStructureInputError("简历原文超过安全长度上限"), 422),
            (ResumeStructureDisabledError("功能未启用"), 503),
            (ResumeStructureConfigurationError("配置无效"), 503),
            (ResumeStructureUnexpectedError("结构化识别元数据无效"), 500),
        )

        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                structure_mock = AsyncMock(side_effect=error)
                with patch.object(
                    resume_structure_service,
                    "structure_resume",
                    structure_mock,
                ):
                    response = self.client.post("/resumes/32/structure", json={})

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json(), {"detail": str(error)})

    def test_structure_resume_maps_upstream_errors(self) -> None:
        cases = (
            (ResumeStructureRateLimitError("请求达到速率上限"), 429),
            (ResumeStructureEmptyResponseError("模型返回空内容"), 502),
            (ResumeStructureResponseInterruptedError("模型输出被截断"), 502),
            (ResumeStructureInvalidOutputError("草稿校验失败"), 502),
            (ResumeStructureUpstreamError("上游请求失败"), 502),
            (ResumeStructureAuthenticationError("认证失败"), 503),
            (ResumeStructureQuotaError("余额不足"), 503),
            (ResumeStructureServiceUnavailableError("服务不可用"), 503),
            (ResumeStructureTimeoutError("模型调用超时"), 504),
        )

        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                structure_mock = AsyncMock(side_effect=error)
                with patch.object(
                    resume_structure_service,
                    "structure_resume",
                    structure_mock,
                ):
                    response = self.client.post("/resumes/32/structure", json={})

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json(), {"detail": str(error)})

    def test_failed_forced_refresh_returns_safe_error_and_previous_draft(self) -> None:
        private_error = "模型调用超时"
        previous = make_structure_result(
            structure_status="failed",
            structure_error=private_error,
            from_cache=True,
            has_previous_draft=True,
        )
        structure_mock = AsyncMock(side_effect=ResumeStructureTimeoutError(private_error))
        current_mock = AsyncMock(return_value=previous)

        with (
            patch.object(resume_structure_service, "structure_resume", structure_mock),
            patch.object(resume_structure_service, "get_current_result", current_mock),
        ):
            response = self.client.post(
                "/resumes/32/structure",
                json={"force": True},
            )

        self.assertEqual(response.status_code, 504)
        error_body = response.json()["detail"]
        self.assertEqual(error_body["detail"], private_error)
        self.assertEqual(error_body["structure_status"], "failed")
        self.assertEqual(error_body["structure_error"], private_error)
        self.assertTrue(error_body["from_cache"])
        self.assertTrue(error_body["has_previous_draft"])
        self.assertEqual(error_body["draft"]["skills"], ["Python"])
        self.assertNotIn("metadata", error_body)
        current_mock.assert_awaited_once_with(self.db, 32)

    def test_non_forced_failure_does_not_query_previous_draft(self) -> None:
        structure_mock = AsyncMock(side_effect=ResumeStructureTimeoutError("模型调用超时"))
        current_mock = AsyncMock()

        with (
            patch.object(resume_structure_service, "structure_resume", structure_mock),
            patch.object(resume_structure_service, "get_current_result", current_mock),
        ):
            response = self.client.post("/resumes/32/structure", json={})

        self.assertEqual(response.status_code, 504)
        current_mock.assert_not_awaited()

    def test_unexpected_error_response_is_sanitized(self) -> None:
        structure_mock = AsyncMock(
            side_effect=RuntimeError("candidate@example.com sk-private C:/secret")
        )

        with patch.object(resume_structure_service, "structure_resume", structure_mock):
            response = self.client.post("/resumes/32/structure", json={})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": "简历结构化识别发生未预期错误"},
        )
        self.assertNotIn("candidate@example.com", response.text)
        self.assertNotIn("sk-private", response.text)

    def test_failed_previous_draft_lookup_falls_back_to_safe_error(self) -> None:
        structure_mock = AsyncMock(side_effect=ResumeStructureTimeoutError("模型调用超时"))
        current_mock = AsyncMock(side_effect=RuntimeError("postgresql://private"))

        with (
            patch.object(resume_structure_service, "structure_resume", structure_mock),
            patch.object(resume_structure_service, "get_current_result", current_mock),
        ):
            response = self.client.post(
                "/resumes/32/structure",
                json={"force": True},
            )

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json(), {"detail": "模型调用超时"})
        self.assertNotIn("postgresql", response.text)

    def test_structure_route_openapi_contract_is_registered_once(self) -> None:
        schema = self.app.openapi()
        operation = schema["paths"]["/resumes/{resume_id}/structure"]["post"]

        self.assertEqual(operation["tags"], ["resumes"])
        self.assertEqual(
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ResumeStructureRequest",
        )
        self.assertEqual(
            operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ResumeStructureResponse",
        )
        matching_routes = [
            route
            for route in self.app.routes
            if getattr(route, "path", None) == "/resumes/{resume_id}/structure"
            and "POST" in getattr(route, "methods", set())
        ]
        self.assertEqual(len(matching_routes), 1)
