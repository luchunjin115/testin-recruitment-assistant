from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.resume_structure import (
    DeepSeekResumeStructureAdapter,
    ResumeStructureAdapterError,
    ResumeStructureAdapterResult,
)
from app.core.config import Settings, get_settings
from app.models.resume import Resume
from app.prompts.resume_structure import RESUME_STRUCTURE_PROMPT_VERSION
from app.schemas.resume_parse import (
    RESUME_PARSE_SCHEMA_VERSION,
    ResumeParseDraft,
)


class ResumeStructureServiceError(RuntimeError):
    """Base class for stable, privacy-safe structure workflow errors."""


class ResumeStructureDisabledError(ResumeStructureServiceError):
    pass


class ResumeStructureConfigurationError(ResumeStructureServiceError):
    pass


class ResumeStructureNotFoundError(ResumeStructureServiceError):
    pass


class ResumeStructurePrerequisiteError(ResumeStructureServiceError):
    pass


class ResumeStructureInputError(ResumeStructureServiceError):
    pass


class ResumeStructureConflictError(ResumeStructureServiceError):
    pass


class ResumeStructureInvalidOutputError(ResumeStructureServiceError):
    pass


class ResumeStructureAttemptSupersededError(ResumeStructureConflictError):
    pass


class ResumeStructureUnexpectedError(ResumeStructureServiceError):
    pass


class ResumeStructureAdapter(Protocol):
    async def extract(self, raw_text: str) -> ResumeStructureAdapterResult: ...


class ResumeStructureSnapshotMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=200)
    prompt_version: str = Field(min_length=1, max_length=100)
    schema_version: str = Field(min_length=1, max_length=20)
    structured_at: datetime
    input_characters: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    attempt_id: str = Field(min_length=36, max_length=36)


class ResumeStructureSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: ResumeParseDraft
    metadata: ResumeStructureSnapshotMetadata


@dataclass(frozen=True, slots=True)
class ResumeStructurePerformance:
    total_ms: int
    preparation_ms: int
    model_ms: int
    validation_ms: int
    persistence_ms: int


@dataclass(frozen=True, slots=True)
class ResumeStructureServiceResult:
    resume_id: int
    structure_status: str
    structure_error: str | None
    draft: ResumeParseDraft
    metadata: ResumeStructureSnapshotMetadata
    from_cache: bool
    has_previous_draft: bool
    performance: ResumeStructurePerformance | None = None


class ResumeStructureService:
    async def get_current_result(
        self,
        db: AsyncSession,
        resume_id: int,
    ) -> ResumeStructureServiceResult | None:
        """Return the latest valid stored draft without starting a model call."""
        total_started = perf_counter()
        try:
            result = await db.execute(
                select(Resume)
                .where(Resume.id == resume_id)
                .execution_options(populate_existing=True)
            )
            resume = result.scalar_one_or_none()
            if resume is None:
                await db.rollback()
                return None

            snapshot = self._read_current_snapshot(resume)
            if snapshot is None:
                await db.rollback()
                return None

            total_ms = self._elapsed_ms(perf_counter, total_started)
            current_result = self._build_result(
                resume=resume,
                snapshot=snapshot,
                from_cache=True,
                has_previous_draft=True,
                performance=ResumeStructurePerformance(
                    total_ms=total_ms,
                    preparation_ms=total_ms,
                    model_ms=0,
                    validation_ms=0,
                    persistence_ms=0,
                ),
            )
            await db.rollback()
            return current_result
        except BaseException:
            await db.rollback()
            raise

    async def structure_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        *,
        force: bool = False,
        adapter: ResumeStructureAdapter | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
        timer: Callable[[], float] | None = None,
        attempt_id_factory: Callable[[], str] | None = None,
    ) -> ResumeStructureServiceResult:
        timer_provider = timer or perf_counter
        total_started = timer_provider()
        resolved_settings = settings or get_settings()
        if not resolved_settings.RESUME_STRUCTURE_ENABLED:
            raise ResumeStructureDisabledError("简历结构化识别功能当前未启用")
        self._validate_configuration(resolved_settings)

        now_provider = clock or (lambda: datetime.now(timezone.utc))
        current_time = self._aware_time(now_provider())
        new_attempt_id = attempt_id_factory or (lambda: str(uuid4()))
        preparation_started = timer_provider()

        try:
            resume = await self._get_locked_resume(db, resume_id)
            if resume is None:
                raise ResumeStructureNotFoundError("Resume 不存在")

            cached_snapshot = self._read_current_snapshot(resume)
            if (
                cached_snapshot is not None
                and resume.structure_status in {"succeeded", "failed"}
                and not force
            ):
                preparation_ms = self._elapsed_ms(timer_provider, preparation_started)
                total_ms = self._elapsed_ms(timer_provider, total_started)
                current_result = self._build_result(
                    resume=resume,
                    snapshot=cached_snapshot,
                    from_cache=True,
                    has_previous_draft=True,
                    performance=ResumeStructurePerformance(
                        total_ms=total_ms,
                        preparation_ms=preparation_ms,
                        model_ms=0,
                        validation_ms=0,
                        persistence_ms=0,
                    ),
                )
                await db.rollback()
                return current_result

            raw_text = self._validate_resume_and_get_text(resume, resolved_settings)
            self._reject_active_attempt(resume, current_time, resolved_settings)
            attempt_id = self._validated_attempt_id(new_attempt_id())
            has_previous_draft = cached_snapshot is not None

            resume.structure_status = "processing"
            resume.structure_error = None
            resume.structure_attempt_id = attempt_id
            resume.structure_started_at = current_time
            await db.commit()
            preparation_ms = self._elapsed_ms(timer_provider, preparation_started)
        except ResumeStructureServiceError:
            await db.rollback()
            raise
        except BaseException:
            await db.rollback()
            raise

        try:
            resolved_adapter = adapter or DeepSeekResumeStructureAdapter(
                settings=resolved_settings
            )
            model_started = timer_provider()
            adapter_result = await resolved_adapter.extract(raw_text)
            model_ms = self._elapsed_ms(timer_provider, model_started)
            validation_started = timer_provider()
            draft = self._parse_and_validate(adapter_result.content)
            validation_ms = self._elapsed_ms(timer_provider, validation_started)
        except ResumeStructureAdapterError as exc:
            await self._save_failure(db, resume_id, attempt_id, str(exc))
            raise
        except ResumeStructureInvalidOutputError as exc:
            await self._save_failure(db, resume_id, attempt_id, str(exc))
            raise
        except Exception:
            error = ResumeStructureUnexpectedError("简历结构化识别发生未预期错误")
            await self._save_failure(db, resume_id, attempt_id, str(error))
            raise error from None

        persistence_started = timer_provider()
        try:
            completed_at = self._aware_time(now_provider())
            snapshot = ResumeStructureSnapshot(
                draft=draft,
                metadata=ResumeStructureSnapshotMetadata(
                    model=adapter_result.model,
                    prompt_version=resolved_settings.RESUME_STRUCTURE_PROMPT_VERSION,
                    schema_version=resolved_settings.RESUME_STRUCTURE_SCHEMA_VERSION,
                    structured_at=completed_at,
                    input_characters=len(raw_text),
                    input_tokens=adapter_result.input_tokens,
                    output_tokens=adapter_result.output_tokens,
                    attempt_id=attempt_id,
                ),
            )
        except ResumeStructureServiceError as exc:
            await self._save_failure(db, resume_id, attempt_id, str(exc))
            raise
        except Exception:
            error = ResumeStructureUnexpectedError("结构化识别元数据无效")
            await self._save_failure(db, resume_id, attempt_id, str(error))
            raise error from None

        try:
            resume = await self._get_locked_resume(db, resume_id)
            if resume is None or resume.structure_attempt_id != attempt_id:
                raise ResumeStructureAttemptSupersededError(
                    "本次简历结构化识别已被更新的任务取代"
                )

            resume.parsed_snapshot = snapshot.model_dump(mode="json")
            resume.structure_status = "succeeded"
            resume.structure_error = None
            resume.structured_at = completed_at
            resume.structure_schema_version = RESUME_PARSE_SCHEMA_VERSION
            await db.commit()
            persistence_ms = self._elapsed_ms(timer_provider, persistence_started)
        except BaseException:
            await db.rollback()
            raise

        total_ms = self._elapsed_ms(timer_provider, total_started)
        return self._build_result(
            resume=resume,
            snapshot=snapshot,
            from_cache=False,
            has_previous_draft=has_previous_draft,
            performance=ResumeStructurePerformance(
                total_ms=total_ms,
                preparation_ms=preparation_ms,
                model_ms=model_ms,
                validation_ms=validation_ms,
                persistence_ms=persistence_ms,
            ),
        )

    @staticmethod
    async def _get_locked_resume(db: AsyncSession, resume_id: int) -> Resume | None:
        result = await db.execute(
            select(Resume)
            .where(Resume.id == resume_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _validate_resume_and_get_text(resume: Resume, settings: Settings) -> str:
        if resume.parse_status != "parsed":
            raise ResumeStructurePrerequisiteError("简历原文尚未成功提取")
        if not isinstance(resume.raw_text, str) or not resume.raw_text.strip():
            raise ResumeStructurePrerequisiteError("简历原文为空，无法进行结构化识别")
        if len(resume.raw_text) > settings.RESUME_STRUCTURE_MAX_INPUT_CHARS:
            raise ResumeStructureInputError(
                "简历原文超过结构化识别的安全长度上限"
            )
        return resume.raw_text

    @staticmethod
    def _reject_active_attempt(
        resume: Resume,
        current_time: datetime,
        settings: Settings,
    ) -> None:
        if resume.structure_status != "processing":
            return
        started_at = resume.structure_started_at
        if started_at is None:
            return
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            return
        lease_cutoff = current_time - timedelta(
            seconds=settings.RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS
        )
        if started_at > lease_cutoff:
            raise ResumeStructureConflictError("该简历正在进行结构化识别")

    @staticmethod
    def _validated_attempt_id(value: str) -> str:
        if not isinstance(value, str) or len(value) != 36:
            raise ResumeStructureUnexpectedError("无法生成有效的结构化识别任务编号")
        try:
            parsed = UUID(value)
        except ValueError:
            raise ResumeStructureUnexpectedError(
                "无法生成有效的结构化识别任务编号"
            ) from None
        if str(parsed) != value.lower():
            raise ResumeStructureUnexpectedError("无法生成有效的结构化识别任务编号")
        return str(parsed)

    @staticmethod
    def _validate_configuration(settings: Settings) -> None:
        if settings.RESUME_STRUCTURE_PROMPT_VERSION != RESUME_STRUCTURE_PROMPT_VERSION:
            raise ResumeStructureConfigurationError(
                "结构化识别 Prompt 版本与当前代码不一致"
            )
        if settings.RESUME_STRUCTURE_SCHEMA_VERSION != RESUME_PARSE_SCHEMA_VERSION:
            raise ResumeStructureConfigurationError(
                "结构化识别 Schema 版本与当前代码不一致"
            )

    @staticmethod
    def _parse_and_validate(content: str) -> ResumeParseDraft:
        try:
            payload: Any = json.loads(content)
            return ResumeParseDraft.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise ResumeStructureInvalidOutputError(
                "DeepSeek 返回内容未通过结构化草稿校验"
            ) from None

    async def _save_failure(
        self,
        db: AsyncSession,
        resume_id: int,
        attempt_id: str,
        safe_error: str,
    ) -> None:
        try:
            resume = await self._get_locked_resume(db, resume_id)
            if resume is None or resume.structure_attempt_id != attempt_id:
                raise ResumeStructureAttemptSupersededError(
                    "本次简历结构化识别已被更新的任务取代"
                )

            resume.structure_status = "failed"
            resume.structure_error = safe_error
            await db.commit()
        except BaseException:
            await db.rollback()
            raise

    @staticmethod
    def _read_current_snapshot(resume: Resume) -> ResumeStructureSnapshot | None:
        if resume.structure_schema_version != RESUME_PARSE_SCHEMA_VERSION:
            return None
        try:
            snapshot = ResumeStructureSnapshot.model_validate(resume.parsed_snapshot)
        except (ValidationError, TypeError):
            return None
        if snapshot.metadata.schema_version != RESUME_PARSE_SCHEMA_VERSION:
            return None
        if snapshot.metadata.prompt_version != RESUME_STRUCTURE_PROMPT_VERSION:
            return None
        return snapshot

    @staticmethod
    def _build_result(
        *,
        resume: Resume,
        snapshot: ResumeStructureSnapshot,
        from_cache: bool,
        has_previous_draft: bool,
        performance: ResumeStructurePerformance | None,
    ) -> ResumeStructureServiceResult:
        return ResumeStructureServiceResult(
            resume_id=resume.id,
            structure_status=resume.structure_status,
            structure_error=resume.structure_error,
            draft=snapshot.draft,
            metadata=snapshot.metadata,
            from_cache=from_cache,
            has_previous_draft=has_previous_draft,
            performance=performance,
        )

    @staticmethod
    def _elapsed_ms(timer: Callable[[], float], started: float) -> int:
        return max(0, round((timer() - started) * 1_000))

    @staticmethod
    def _aware_time(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ResumeStructureUnexpectedError("结构化识别时钟必须包含时区")
        return value


resume_structure_service = ResumeStructureService()
