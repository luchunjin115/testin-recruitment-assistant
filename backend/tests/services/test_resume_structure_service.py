import json
from datetime import datetime, timedelta, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.adapters.resume_structure import (
    ResumeStructureAdapterResult,
    ResumeStructureTimeoutError,
)
from app.core.config import Settings
from app.models.resume import Resume
from app.services.resume_structure_service import (
    ResumeStructureAttemptSupersededError,
    ResumeStructureConflictError,
    ResumeStructureConfigurationError,
    ResumeStructureDisabledError,
    ResumeStructureInputError,
    ResumeStructureInvalidOutputError,
    ResumeStructureNotFoundError,
    ResumeStructurePerformance,
    ResumeStructurePrerequisiteError,
    ResumeStructureService,
    ResumeStructureSnapshot,
    ResumeStructureUnexpectedError,
)


NOW = datetime(2026, 8, 13, 10, 0, tzinfo=timezone.utc)
ATTEMPT_ID = "11111111-1111-4111-8111-111111111111"
NEWER_ATTEMPT_ID = "22222222-2222-4222-8222-222222222222"


def draft_payload() -> dict:
    return {
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


def snapshot_payload(*, prompt_version: str = "resume_structure_v1") -> dict:
    return {
        "draft": draft_payload(),
        "metadata": {
            "model": "deepseek-v4-flash-0813",
            "prompt_version": prompt_version,
            "schema_version": "1.0",
            "structured_at": NOW.isoformat(),
            "input_characters": 12,
            "input_tokens": 10,
            "output_tokens": 20,
            "attempt_id": ATTEMPT_ID,
        },
    }


def make_resume(**overrides: object) -> Resume:
    values: dict[str, object] = {
        "id": 7,
        "filename": "resume.txt",
        "file_path": "v2/resumes/2026/08/resume.txt",
        "parse_status": "parsed",
        "raw_text": "姓名：测试候选人\n技能：Python",
        "structure_status": "not_started",
        "structure_error": None,
        "structure_attempt_id": None,
        "structure_started_at": None,
        "structured_at": None,
        "structure_schema_version": None,
        "parsed_snapshot": None,
    }
    values.update(overrides)
    return Resume(**values)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "RESUME_STRUCTURE_ENABLED": True,
        "RESUME_STRUCTURE_MAX_INPUT_CHARS": 1_000,
        "RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS": 180,
        "RESUME_STRUCTURE_PROMPT_VERSION": "resume_structure_v1",
        "RESUME_STRUCTURE_SCHEMA_VERSION": "1.0",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def query_result(resume: Resume | None) -> Mock:
    result = Mock()
    result.scalar_one_or_none.return_value = resume
    return result


def make_session(*resumes: Resume | None) -> Mock:
    db = Mock()
    db.execute = AsyncMock(side_effect=[query_result(resume) for resume in resumes])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def make_adapter(
    *,
    content: str | None = None,
    error: Exception | None = None,
) -> Mock:
    adapter = Mock()
    adapter.extract = AsyncMock(
        return_value=ResumeStructureAdapterResult(
            content=content or json.dumps(draft_payload(), ensure_ascii=False),
            model="deepseek-v4-flash-0813",
            finish_reason="stop",
            input_tokens=50,
            output_tokens=100,
        ),
        side_effect=error,
    )
    return adapter


class ResumeStructureServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ResumeStructureService()
        self.settings = make_settings()

    async def call(self, db: Mock, adapter: Mock, **kwargs: object):
        return await self.service.structure_resume(
            db,
            7,
            adapter=adapter,
            settings=self.settings,
            clock=lambda: NOW,
            attempt_id_factory=lambda: ATTEMPT_ID,
            **kwargs,
        )

    async def test_get_current_result_returns_valid_draft_without_model_call(self) -> None:
        resume = make_resume(
            structure_status="failed",
            structure_error="最近一次重新识别失败",
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
        )
        db = make_session(resume)

        result = await self.service.get_current_result(db, resume.id)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.structure_status, "failed")
        self.assertEqual(result.structure_error, "最近一次重新识别失败")
        self.assertTrue(result.from_cache)
        self.assertTrue(result.has_previous_draft)
        self.assertIsInstance(result.performance, ResumeStructurePerformance)
        assert result.performance is not None
        self.assertEqual(result.performance.model_ms, 0)
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_get_current_result_returns_none_without_valid_snapshot(self) -> None:
        for resume in (None, make_resume(parsed_snapshot=None)):
            with self.subTest(resume=resume):
                db = make_session(resume)

                result = await self.service.get_current_result(db, 7)

                self.assertIsNone(result)
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_success_uses_two_commits_and_persists_server_envelope(self) -> None:
        resume = make_resume()
        db = make_session(resume, resume)
        adapter = make_adapter()
        committed_states: list[tuple[str, str | None]] = []

        async def capture_commit() -> None:
            committed_states.append((resume.structure_status, resume.structure_attempt_id))

        db.commit.side_effect = capture_commit

        timer = Mock(side_effect=[
            0.0,
            0.01,
            0.03,
            0.04,
            1.24,
            1.25,
            1.255,
            1.26,
            1.28,
            1.30,
        ])

        result = await self.call(db, adapter, timer=timer)

        self.assertEqual(
            committed_states,
            [("processing", ATTEMPT_ID), ("succeeded", ATTEMPT_ID)],
        )
        adapter.extract.assert_awaited_once_with(resume.raw_text)
        self.assertEqual(db.execute.await_count, 2)
        self.assertEqual(result.draft.basic_info.name, "测试候选人")
        self.assertFalse(result.from_cache)
        self.assertFalse(result.has_previous_draft)
        self.assertEqual(resume.structure_status, "succeeded")
        self.assertEqual(resume.structure_schema_version, "1.0")
        self.assertEqual(resume.structured_at, NOW)
        snapshot = ResumeStructureSnapshot.model_validate(resume.parsed_snapshot)
        self.assertEqual(snapshot.metadata.attempt_id, ATTEMPT_ID)
        self.assertEqual(snapshot.metadata.input_characters, len(resume.raw_text))
        self.assertEqual(snapshot.metadata.input_tokens, 50)
        self.assertEqual(snapshot.metadata.output_tokens, 100)
        self.assertEqual(
            result.performance,
            ResumeStructurePerformance(
                total_ms=1_300,
                preparation_ms=20,
                model_ms=1_200,
                validation_ms=5,
                persistence_ms=20,
            ),
        )

    async def test_valid_cached_draft_returns_without_adapter_or_commit(self) -> None:
        resume = make_resume(
            structure_status="succeeded",
            structure_attempt_id=ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
            structured_at=NOW,
        )
        db = make_session(resume)
        adapter = make_adapter()

        result = await self.call(db, adapter)

        self.assertTrue(result.from_cache)
        self.assertTrue(result.has_previous_draft)
        self.assertEqual(result.draft.basic_info.name, "测试候选人")
        adapter.extract.assert_not_awaited()
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_failed_refresh_still_returns_previous_successful_draft(self) -> None:
        resume = make_resume(
            structure_status="failed",
            structure_error="最近一次重新识别失败",
            structure_attempt_id=NEWER_ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
            structured_at=NOW,
        )
        db = make_session(resume)
        adapter = make_adapter()

        result = await self.call(db, adapter)

        self.assertTrue(result.from_cache)
        self.assertEqual(result.structure_status, "failed")
        self.assertEqual(result.structure_error, "最近一次重新识别失败")
        self.assertEqual(result.metadata.attempt_id, ATTEMPT_ID)
        adapter.extract.assert_not_awaited()

    async def test_force_true_replaces_valid_cached_draft_once(self) -> None:
        resume = make_resume(
            structure_status="succeeded",
            structure_attempt_id=ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
            structured_at=NOW - timedelta(days=1),
        )
        db = make_session(resume, resume)
        adapter = make_adapter()

        result = await self.call(db, adapter, force=True)

        self.assertFalse(result.from_cache)
        self.assertTrue(result.has_previous_draft)
        adapter.extract.assert_awaited_once()
        self.assertEqual(db.commit.await_count, 2)

    async def test_legacy_or_version_drift_snapshot_is_not_treated_as_cache(self) -> None:
        for parsed_snapshot, schema_version in (
            ({"name": "legacy"}, None),
            (snapshot_payload(prompt_version="resume_structure_v0"), "1.0"),
        ):
            with self.subTest(parsed_snapshot=parsed_snapshot):
                resume = make_resume(
                    structure_status="succeeded",
                    structure_attempt_id=ATTEMPT_ID,
                    structure_schema_version=schema_version,
                    parsed_snapshot=parsed_snapshot,
                )
                db = make_session(resume, resume)
                adapter = make_adapter()

                result = await self.call(db, adapter)

                self.assertFalse(result.from_cache)
                adapter.extract.assert_awaited_once()

    async def test_missing_resume_or_unparsed_text_stops_before_adapter(self) -> None:
        cases = (
            (None, ResumeStructureNotFoundError),
            (make_resume(parse_status="uploaded"), ResumeStructurePrerequisiteError),
            (make_resume(raw_text="   "), ResumeStructurePrerequisiteError),
            (make_resume(raw_text="x" * 1_001), ResumeStructureInputError),
        )
        for resume, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                db = make_session(resume)
                adapter = make_adapter()

                with self.assertRaises(expected_error):
                    await self.call(db, adapter)

                adapter.extract.assert_not_awaited()
                db.commit.assert_not_awaited()
                db.rollback.assert_awaited_once()

    async def test_disabled_feature_stops_before_database_or_adapter(self) -> None:
        db = make_session(make_resume())
        adapter = make_adapter()
        self.settings = make_settings(RESUME_STRUCTURE_ENABLED=False)

        with self.assertRaises(ResumeStructureDisabledError):
            await self.call(db, adapter)

        db.execute.assert_not_awaited()
        adapter.extract.assert_not_awaited()

    async def test_version_drift_stops_before_database_or_adapter(self) -> None:
        for key, value in (
            ("RESUME_STRUCTURE_PROMPT_VERSION", "resume_structure_v2"),
            ("RESUME_STRUCTURE_SCHEMA_VERSION", "2.0"),
        ):
            with self.subTest(key=key):
                db = make_session(make_resume())
                adapter = make_adapter()
                self.settings = make_settings(**{key: value})

                with self.assertRaises(ResumeStructureConfigurationError):
                    await self.call(db, adapter)

                db.execute.assert_not_awaited()
                adapter.extract.assert_not_awaited()

    async def test_active_processing_lease_returns_conflict_without_second_call(self) -> None:
        resume = make_resume(
            structure_status="processing",
            structure_started_at=NOW - timedelta(seconds=60),
            structure_attempt_id=NEWER_ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
        )
        db = make_session(resume)
        adapter = make_adapter()

        with self.assertRaises(ResumeStructureConflictError):
            await self.call(db, adapter)

        adapter.extract.assert_not_awaited()
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_expired_processing_lease_is_taken_over(self) -> None:
        resume = make_resume(
            structure_status="processing",
            structure_started_at=NOW - timedelta(seconds=181),
            structure_attempt_id=NEWER_ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=snapshot_payload(),
        )
        db = make_session(resume, resume)
        adapter = make_adapter()

        result = await self.call(db, adapter)

        self.assertEqual(result.metadata.attempt_id, ATTEMPT_ID)
        self.assertTrue(result.has_previous_draft)
        adapter.extract.assert_awaited_once()
        self.assertEqual(db.commit.await_count, 2)

    async def test_invalid_json_or_schema_records_stable_failure(self) -> None:
        invalid_contents = (
            "not-json candidate@example.com",
            json.dumps({"schema_version": "1.0"}),
        )
        for content in invalid_contents:
            with self.subTest(content=content):
                resume = make_resume()
                db = make_session(resume, resume)
                adapter = make_adapter(content=content)

                with self.assertRaises(ResumeStructureInvalidOutputError):
                    await self.call(db, adapter)

                self.assertEqual(resume.structure_status, "failed")
                self.assertEqual(
                    resume.structure_error,
                    "DeepSeek 返回内容未通过结构化草稿校验",
                )
                self.assertNotIn("candidate@example.com", resume.structure_error)
                self.assertEqual(db.commit.await_count, 2)

    async def test_adapter_failure_preserves_previous_successful_snapshot(self) -> None:
        previous_snapshot = snapshot_payload()
        previous_time = NOW - timedelta(days=1)
        resume = make_resume(
            structure_status="succeeded",
            structure_attempt_id=ATTEMPT_ID,
            structure_schema_version="1.0",
            parsed_snapshot=previous_snapshot,
            structured_at=previous_time,
        )
        db = make_session(resume, resume)
        adapter = make_adapter(error=ResumeStructureTimeoutError("简历结构化模型调用超时"))

        with self.assertRaises(ResumeStructureTimeoutError):
            await self.call(db, adapter, force=True)

        self.assertEqual(resume.structure_status, "failed")
        self.assertEqual(resume.structure_error, "简历结构化模型调用超时")
        self.assertEqual(resume.parsed_snapshot, previous_snapshot)
        self.assertEqual(resume.structured_at, previous_time)
        self.assertEqual(resume.structure_schema_version, "1.0")
        self.assertEqual(db.commit.await_count, 2)

    async def test_unexpected_adapter_error_is_sanitized_and_recorded(self) -> None:
        resume = make_resume()
        db = make_session(resume, resume)
        adapter = make_adapter(error=RuntimeError("private@example.com sk-secret"))

        with self.assertRaises(ResumeStructureUnexpectedError) as raised:
            await self.call(db, adapter)

        self.assertEqual(str(raised.exception), "简历结构化识别发生未预期错误")
        self.assertEqual(resume.structure_error, "简历结构化识别发生未预期错误")
        self.assertNotIn("private@example.com", resume.structure_error)

    async def test_invalid_adapter_metadata_is_sanitized_and_recorded(self) -> None:
        resume = make_resume()
        db = make_session(resume, resume)
        adapter = make_adapter()
        adapter.extract.return_value = ResumeStructureAdapterResult(
            content=json.dumps(draft_payload(), ensure_ascii=False),
            model="",
            finish_reason="stop",
            input_tokens=-1,
            output_tokens=100,
        )

        with self.assertRaises(ResumeStructureUnexpectedError) as raised:
            await self.call(db, adapter)

        self.assertEqual(str(raised.exception), "结构化识别元数据无效")
        self.assertEqual(resume.structure_status, "failed")
        self.assertEqual(resume.structure_error, "结构化识别元数据无效")
        self.assertEqual(db.commit.await_count, 2)

    async def test_old_success_response_cannot_overwrite_newer_attempt(self) -> None:
        original = make_resume()
        newer = make_resume(
            structure_status="processing",
            structure_attempt_id=NEWER_ATTEMPT_ID,
            structure_started_at=NOW,
        )
        db = make_session(original, newer)
        adapter = make_adapter()

        with self.assertRaises(ResumeStructureAttemptSupersededError):
            await self.call(db, adapter)

        self.assertIsNone(newer.parsed_snapshot)
        self.assertEqual(newer.structure_attempt_id, NEWER_ATTEMPT_ID)
        self.assertEqual(db.commit.await_count, 1)
        db.rollback.assert_awaited_once()

    async def test_old_failure_response_cannot_mark_newer_attempt_failed(self) -> None:
        original = make_resume()
        newer = make_resume(
            structure_status="processing",
            structure_attempt_id=NEWER_ATTEMPT_ID,
            structure_started_at=NOW,
        )
        db = make_session(original, newer)
        adapter = make_adapter(error=ResumeStructureTimeoutError("简历结构化模型调用超时"))

        with self.assertRaises(ResumeStructureAttemptSupersededError):
            await self.call(db, adapter)

        self.assertEqual(newer.structure_status, "processing")
        self.assertIsNone(newer.structure_error)
        self.assertEqual(db.commit.await_count, 1)
        db.rollback.assert_awaited_once()

    async def test_first_commit_failure_rolls_back_and_never_calls_adapter(self) -> None:
        resume = make_resume()
        db = make_session(resume)
        db.commit.side_effect = RuntimeError("database unavailable")
        adapter = make_adapter()

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.call(db, adapter)

        adapter.extract.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_success_commit_failure_rolls_back_without_success_response(self) -> None:
        resume = make_resume()
        db = make_session(resume, resume)
        db.commit.side_effect = [None, RuntimeError("database unavailable")]
        adapter = make_adapter()

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.call(db, adapter)

        adapter.extract.assert_awaited_once()
        db.rollback.assert_awaited_once()

    async def test_invalid_attempt_id_and_naive_clock_fail_safely(self) -> None:
        adapter = make_adapter()
        db = make_session(make_resume())
        with self.assertRaises(ResumeStructureUnexpectedError):
            await self.service.structure_resume(
                db,
                7,
                adapter=adapter,
                settings=self.settings,
                clock=lambda: NOW.replace(tzinfo=None),
            )
        db.execute.assert_not_awaited()

        db = make_session(make_resume())
        with self.assertRaises(ResumeStructureUnexpectedError):
            await self.service.structure_resume(
                db,
                7,
                adapter=adapter,
                settings=self.settings,
                clock=lambda: NOW,
                attempt_id_factory=lambda: "short",
            )
        adapter.extract.assert_not_awaited()
        db.rollback.assert_awaited_once()
