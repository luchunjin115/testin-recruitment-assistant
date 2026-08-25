from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError
from sqlalchemy import null, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.job_evaluation_plan import (
    DeepSeekJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
    V4_PROMPT_VERSIONS,
)
from app.core.config import Settings, get_settings
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.prompts.job_evaluation_plan import (
    JOB_EVALUATION_PLAN_PROMPT_VERSION,
)
from app.schemas.job_evaluation_plan import (
    AIEvaluationCriterionGroupingOutput,
    AIExtractedEvaluationItem,
    AIExtractedEvaluationPlan,
    AIExtractedEvaluationPlanV2,
    AIExtractedEvaluationPlanV3,
    AIRequirementCoverageReviewOutput,
    AIRequirementFactCandidate,
    AIRequirementFactExtractionOutput,
    AIRequirementLocalRepairOutput,
    JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION,
    JOB_EVALUATION_PLAN_FINGERPRINT_RULE_VERSION,
    JOB_EVALUATION_PLAN_MAX_ITEMS,
    JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
    JOB_EVALUATION_PLAN_V4_MAX_CRITERIA_JSON_CHARS,
    JOB_EVALUATION_PLAN_V4_MAX_FACTS,
    JOB_EVALUATION_PLAN_V4_MAX_FACTS_JSON_CHARS,
    JOB_EVALUATION_PLAN_V4_MAX_INPUT_CHARS,
    JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_JSON_CHARS,
    JOB_EVALUATION_PLAN_V4_MAX_SOURCE_UNITS,
    JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION,
    JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION,
    JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
    LEGACY_JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
    LEGACY_JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION,
    LEGACY_JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    LEGACY_JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
    EvaluationItemCategory,
    EvaluationItemPriority,
    EvaluationItemSourceType,
    EvaluationCriterion,
    JobEvaluationCriterionGroupingInput,
    JobEvaluationPlanAIInput,
    JobEvaluationPlanAIInputV3,
    JobEvaluationItem,
    JobEvaluationItemSource,
    JobEvaluationPlanFreeTextCoverage,
    JobEvaluationPlanInputSnapshot,
    JobEvaluationPlanCoverageFinding,
    JobEvaluationPlanCoverageReviewSummary,
    JobEvaluationPlanGenerationAudit,
    JobEvaluationPlanGenerationCallAudit,
    JobEvaluationPlanRead,
    JobEvaluationPlanSourceReviewSummary,
    JobEvaluationPlanSourceReviewSummaryV4,
    JobEvaluationPlanSourceReviewUnit,
    JobEvaluationPlanSourceReviewUnitV4,
    JobEvaluationPlanSourceUnit,
    JobEvaluationPlanStatus,
    JobEvaluationPlanWarning,
    JobEvaluationPlanWarningDetail,
    JobEvaluationPlanWarningCode,
    JobEvaluationPlanV4WarningCode,
    JobEvaluationPlanV4WarningDetail,
    JobRequirementCoverageReviewInput,
    JobRequirementFactExtractionInput,
    JobRequirementLocalRepairInput,
    LegacyEvaluationPlanRequirements,
    StructuredCoverageResult,
    StructuredFieldCoverage,
    RequirementFact,
    RequirementFactSource,
)


LEGACY_JOB_EVALUATION_PLAN_PROMPT_VERSION = "job_evaluation_plan_v4"


class JobEvaluationPlanServiceError(RuntimeError):
    code = "JOB_EVALUATION_PLAN_OPERATION_FAILED"


class JobEvaluationPlanDisabledError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_DISABLED"


class JobEvaluationPlanConfigurationError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_CONFIGURATION_ERROR"


class JobEvaluationPlanNotFoundError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_NOT_FOUND"


class JobEvaluationPlanJobNotFoundError(JobEvaluationPlanServiceError):
    code = "JOB_NOT_FOUND"


class JobEvaluationPlanJobNotOpenError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_JOB_NOT_OPEN"


class JobEvaluationPlanNotRegenerableError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_NOT_REGENERABLE"


class JobEvaluationPlanNotConfirmableError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_NOT_CONFIRMABLE"


class JobEvaluationPlanContentError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        if code is not None:
            self.code = code
        super().__init__(message)


class JobEvaluationPlanV4GenerationError(JobEvaluationPlanServiceError):
    """Safe terminal error for the pure 4.0 workflow, with no partial plan."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        generation_audit: JobEvaluationPlanGenerationAudit,
    ) -> None:
        self.code = code
        self.generation_audit = generation_audit
        self.requirement_facts = None
        self.evaluation_criteria = None
        super().__init__(message)


class JobEvaluationPlanAdapter(Protocol):
    async def extract(
        self,
        extraction_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult: ...

    async def generate_v4(
        self,
        role: str,
        generation_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult: ...


@dataclass(frozen=True, slots=True)
class GeneratedPlanContent:
    items: list[JobEvaluationItem]
    structured_coverage: StructuredCoverageResult | None
    warnings: list[JobEvaluationPlanWarning | JobEvaluationPlanWarningDetail]
    free_text_coverage: dict[str, Any] | None = None
    source_review_summary: JobEvaluationPlanSourceReviewSummary | None = None


@dataclass(frozen=True, slots=True)
class GeneratedPlanContentV4:
    requirement_facts: list[RequirementFact]
    evaluation_criteria: list[EvaluationCriterion]
    source_review_summary: JobEvaluationPlanSourceReviewSummaryV4
    coverage_review_summary: JobEvaluationPlanCoverageReviewSummary
    warnings: list[JobEvaluationPlanV4WarningDetail]
    generation_audit: JobEvaluationPlanGenerationAudit


@dataclass(frozen=True)
class DescriptionSourceUnit:
    source_id: str
    source_field: str
    source_text: str


@dataclass(slots=True)
class _CandidateItem:
    item: JobEvaluationItem
    source_fields: list[str]


class JobEvaluationPlanService:
    MAX_V4_CONTENT_REPAIRS = 1
    # Reuse the existing Job description and AI extraction safety boundaries.
    _DESCRIPTION_MAX_LENGTH = 20_000
    _DESCRIPTION_MAX_SOURCE_UNITS = 100
    _SOURCE_SENTENCE_BOUNDARY_RE = re.compile(
        r"[。！？!?；;]+|\.(?=(?:\s|$|[A-Z\u4e00-\u9fff]))"
    )
    _SOURCE_PRIORITY_BOUNDARY_RE = re.compile(
        r"(?P<separator>[，,:：]\s*)"
        r"(?=(?:必须|至少|要求具备|要求|需具备|硬性要求|优先|加分|最好具备|"
        r"required\b|must\b|preferred\b|plus\b))",
        re.IGNORECASE,
    )
    _SOURCE_LIST_PREFIX_RE = re.compile(
        r"^(?:(?:[-*•●▪◦·])|"
        r"(?:\d{1,4}[.)、．])|"
        r"(?:[（(]\d{1,4}[）)])|"
        r"(?:[一二三四五六七八九十百]+[、.．]))\s*"
    )
    _SOURCE_WRAPPERS = (
        ("（", "）"),
        ("(", ")"),
        ("【", "】"),
        ("[", "]"),
    )
    _PROMOTION_TERMS = (
        "公司介绍",
        "公司简介",
        "团队氛围",
        "团队宣传",
        "五险一金",
        "员工福利",
        "福利待遇",
        "团建活动",
        "组织团建",
        "下午茶",
        "年度旅游",
        "带薪年假",
        "免费零食",
        "办公环境",
        "薪资待遇",
    )
    _REQUIREMENT_ACTION_RE = re.compile(
        r"(?:负责|参与|主导|设计|开发|维护|优化|分析|制定|执行|搭建|推动|管理|"
        r"协作|支持|具备|熟悉|掌握|能够|经验|学历|职责)|"
        r"\b(?:design|own|build|develop|maintain|optimi[sz]e|analy[sz]e|lead|"
        r"manage|drive|support|responsible|experience|proficient|familiar)\b",
        re.IGNORECASE,
    )
    _REQUIRED_TERMS = (
        "必须",
        "至少",
        "要求",
        "需",
        "需具备",
        "要求具备",
        "硬性要求",
        "required",
        "must",
    )
    _PREFERRED_TERMS = (
        "优先",
        "加分",
        "最好具备",
        "preferred",
        "plus",
    )
    _GENERIC_TITLE_TERMS = (
        "熟练掌握",
        "熟悉",
        "掌握",
        "具备",
        "拥有",
        "能够",
        "能力",
        "经验",
        "相关",
        "负责",
        "要求",
        "至少",
        "必须",
        "优先",
    )
    _PRIORITY_RANK = {
        EvaluationItemPriority.GENERAL: 0,
        EvaluationItemPriority.PREFERRED: 1,
        EvaluationItemPriority.REQUIRED: 2,
    }
    _EDUCATION_LABELS = {
        "none": "学历不限",
        "associate_or_above": "大专及以上学历",
        "bachelor_or_above": "本科及以上学历",
        "master_or_above": "硕士及以上学历",
        "doctorate": "博士学历",
    }

    async def get_current_plan(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobEvaluationPlan | None:
        job = await db.get(Job, job_id)
        if job is None:
            raise JobEvaluationPlanJobNotFoundError("岗位不存在")
        return await db.scalar(
            select(JobEvaluationPlan).where(
                JobEvaluationPlan.job_id == job_id,
                JobEvaluationPlan.is_current.is_(True),
            )
        )

    async def get_plan_for_display(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobEvaluationPlan | None:
        """Return the current plan, or the newest history row for read-only UI."""
        current = await self.get_current_plan(db, job_id)
        if current is not None:
            return current
        return await db.scalar(
            select(JobEvaluationPlan)
            .where(JobEvaluationPlan.job_id == job_id)
            .order_by(
                JobEvaluationPlan.updated_at.desc(),
                JobEvaluationPlan.id.desc(),
            )
            .limit(1)
        )

    def is_contract_outdated(self, plan: JobEvaluationPlan) -> bool:
        """Compare a stored plan with the current extraction contract without writes."""
        if plan.schema_version not in {
            JOB_EVALUATION_PLAN_SCHEMA_VERSION,
            JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
        }:
            return True
        try:
            snapshot = JobEvaluationPlanInputSnapshot.model_validate(
                plan.input_snapshot
            )
            expected_fingerprint = self.fingerprint_input(snapshot)
        except (AttributeError, TypeError, ValueError, ValidationError):
            return True
        return plan.input_fingerprint != expected_fingerprint

    def build_read_model(self, plan: JobEvaluationPlan) -> JobEvaluationPlanRead:
        if plan.schema_version == "3.0":
            payload = {
                field: getattr(plan, field)
                for field in JobEvaluationPlanRead.model_fields
                if field != "contract_outdated"
            }
            payload["structured_coverage"] = None
            read_model = JobEvaluationPlanRead.model_validate(payload)
        else:
            read_model = JobEvaluationPlanRead.model_validate(plan)
        return read_model.model_copy(
            update={"contract_outdated": self.is_contract_outdated(plan)}
        )

    async def regenerate_failed_plan(
        self,
        db: AsyncSession,
        job_id: int,
        *,
        adapter: JobEvaluationPlanAdapter | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> JobEvaluationPlan:
        current = await self.get_current_plan(db, job_id)
        if current is None:
            raise JobEvaluationPlanNotFoundError("当前岗位还没有评价计划")
        if current.status != JobEvaluationPlanStatus.FAILED.value:
            raise JobEvaluationPlanNotRegenerableError(
                "只有失败的当前评价计划可以重新生成"
            )
        return await self.generate_for_job(
            db,
            job_id,
            force=True,
            adapter=adapter,
            settings=settings,
            clock=clock,
        )

    async def generate_for_job(
        self,
        db: AsyncSession,
        job_id: int,
        *,
        force: bool = False,
        adapter: JobEvaluationPlanAdapter | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> JobEvaluationPlan:
        """Generate the only writable plan contract: JobEvaluationPlan 4.0."""
        resolved_settings = settings or get_settings()
        if not resolved_settings.JOB_EVALUATION_PLAN_ENABLED:
            raise JobEvaluationPlanDisabledError("岗位评价计划功能当前未启用")
        now_provider = clock or (lambda: datetime.now(timezone.utc))
        started_at = self._aware_time(now_provider())

        try:
            job = await self._get_locked_job(db, job_id)
            if job is None:
                raise JobEvaluationPlanJobNotFoundError("岗位不存在")
            if job.status != "open":
                raise JobEvaluationPlanJobNotOpenError(
                    "只有开放岗位可以生成评价计划"
                )

            snapshot = self.build_v4_input_snapshot(job)
            snapshot_payload = snapshot.model_dump(mode="json")
            jd_fingerprint = self.fingerprint_snapshot(snapshot)
            input_fingerprint = self.fingerprint_input(snapshot)
            plan, should_generate = await self._prepare_plan(
                db,
                job,
                snapshot_payload,
                jd_fingerprint,
                input_fingerprint,
                force=force,
                settings=resolved_settings,
                started_at=started_at,
            )
            if not should_generate:
                await db.commit()
                await db.refresh(plan)
                return plan
            await db.commit()
            await db.refresh(plan)
        except JobEvaluationPlanServiceError:
            await db.rollback()
            raise
        except BaseException:
            await db.rollback()
            raise

        try:
            resolved_adapter = adapter or DeepSeekJobEvaluationPlanAdapter(
                settings=resolved_settings
            )
            content = await self.build_v4_plan_content(
                snapshot,
                adapter=resolved_adapter,
            )
        except JobEvaluationPlanV4GenerationError as exc:
            return await self._save_failure(
                db,
                plan.id,
                input_fingerprint,
                code=exc.code,
                message=str(exc),
                completed_at=self._aware_time(now_provider()),
            )
        except Exception:
            return await self._save_failure(
                db,
                plan.id,
                input_fingerprint,
                code="JOB_EVALUATION_PLAN_UNEXPECTED_ERROR",
                message="岗位评价计划生成发生未预期错误",
                completed_at=self._aware_time(now_provider()),
            )

        model_version = (
            content.generation_audit.calls[0].model
            if content.generation_audit.calls
            else resolved_settings.JOB_EVALUATION_PLAN_MODEL
        )
        return await self._save_success(
            db,
            plan.id,
            input_fingerprint,
            content,
            model_version=model_version,
            completed_at=self._aware_time(now_provider()),
        )

    async def _generate_legacy_for_job(
        self,
        db: AsyncSession,
        job_id: int,
        *,
        force: bool = False,
        adapter: JobEvaluationPlanAdapter | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> JobEvaluationPlan:
        resolved_settings = settings or get_settings()
        self._validate_configuration(resolved_settings)
        now_provider = clock or (lambda: datetime.now(timezone.utc))
        started_at = self._aware_time(now_provider())

        try:
            job = await self._get_locked_job(db, job_id)
            if job is None:
                raise JobEvaluationPlanJobNotFoundError("岗位不存在")
            if job.status != "open":
                raise JobEvaluationPlanJobNotOpenError(
                    "只有开放岗位可以生成评价计划"
                )

            snapshot = self.build_input_snapshot(job)
            snapshot_payload = snapshot.model_dump(mode="json")
            jd_fingerprint = self.fingerprint_snapshot(snapshot)
            input_fingerprint = self.fingerprint_input(snapshot)
            plan, should_generate = await self._prepare_plan(
                db,
                job,
                snapshot_payload,
                jd_fingerprint,
                input_fingerprint,
                force=force,
                settings=resolved_settings,
                started_at=started_at,
            )
            if not should_generate:
                await db.commit()
                await db.refresh(plan)
                return plan
            await db.commit()
            await db.refresh(plan)
        except JobEvaluationPlanServiceError:
            await db.rollback()
            raise
        except BaseException:
            await db.rollback()
            raise

        try:
            resolved_adapter = adapter or DeepSeekJobEvaluationPlanAdapter(
                settings=resolved_settings
            )
            extraction_input = self.build_ai_extraction_input(snapshot)
            adapter_result = await self._extract_with_retry(
                resolved_adapter,
                extraction_input,
            )
            content = self.build_plan_content(snapshot, adapter_result.content)
            if (
                snapshot.schema_version != "3.0"
                and content.free_text_coverage is None
            ):
                raise JobEvaluationPlanContentError(
                    "新合同成功计划缺少自由文本覆盖审计",
                    code="JOB_EVALUATION_PLAN_INCOMPLETE_FREE_TEXT_COVERAGE",
                )
        except JobEvaluationPlanAdapterError as exc:
            return await self._save_failure(
                db,
                plan.id,
                input_fingerprint,
                code=exc.code,
                message=self._safe_adapter_message(exc),
                completed_at=self._aware_time(now_provider()),
            )
        except JobEvaluationPlanContentError as exc:
            return await self._save_failure(
                db,
                plan.id,
                input_fingerprint,
                code=exc.code,
                message=str(exc),
                completed_at=self._aware_time(now_provider()),
            )
        except Exception:
            return await self._save_failure(
                db,
                plan.id,
                input_fingerprint,
                code="JOB_EVALUATION_PLAN_UNEXPECTED_ERROR",
                message="岗位评价计划生成发生未预期错误",
                completed_at=self._aware_time(now_provider()),
            )

        return await self._save_legacy_success(
            db,
            plan.id,
            input_fingerprint,
            content,
            model_version=adapter_result.model,
            completed_at=self._aware_time(now_provider()),
        )

    async def _prepare_plan(
        self,
        db: AsyncSession,
        job: Job,
        snapshot_payload: dict[str, Any],
        jd_fingerprint: str,
        input_fingerprint: str,
        *,
        force: bool,
        settings: Settings,
        started_at: datetime,
    ) -> tuple[JobEvaluationPlan, bool]:
        current = await db.scalar(
            select(JobEvaluationPlan)
            .where(
                JobEvaluationPlan.job_id == job.id,
                JobEvaluationPlan.is_current.is_(True),
            )
            .with_for_update()
        )
        if current is not None and current.input_fingerprint == input_fingerprint:
            if not force or current.status == JobEvaluationPlanStatus.GENERATING.value:
                return current, False
            self._reset_generating_plan(
                current,
                snapshot_payload,
                jd_fingerprint,
                input_fingerprint,
                settings,
            )
            return current, True

        if current is not None:
            current.status = JobEvaluationPlanStatus.OUTDATED.value
            current.is_current = False
            if current.completed_at is None:
                current.completed_at = started_at
            await db.flush()

        existing = await db.scalar(
            select(JobEvaluationPlan)
            .where(
                JobEvaluationPlan.job_id == job.id,
                JobEvaluationPlan.input_fingerprint == input_fingerprint,
            )
            .with_for_update()
        )
        if existing is not None:
            existing.is_current = True
            self._reset_generating_plan(
                existing,
                snapshot_payload,
                jd_fingerprint,
                input_fingerprint,
                settings,
            )
            return existing, True

        plan = JobEvaluationPlan(
            job_id=job.id,
            jd_fingerprint=jd_fingerprint,
            status=JobEvaluationPlanStatus.GENERATING.value,
            is_current=True,
            items=(
                null()
                if snapshot_payload.get("schema_version") == "4.0"
                else []
            ),
            structured_coverage=(
                null()
                if snapshot_payload.get("schema_version") in {"3.0", "4.0"}
                else self._empty_coverage()
            ),
            free_text_coverage=null(),
            source_review_summary=null(),
            requirement_facts=null(),
            evaluation_criteria=null(),
            coverage_review_summary=null(),
            generation_audit=null(),
            warnings=[],
            prompt_version=(
                V4_PROMPT_VERSIONS["fact_extraction"]
                if snapshot_payload.get("schema_version") == "4.0"
                else settings.JOB_EVALUATION_PLAN_PROMPT_VERSION
            ),
            model_version=settings.JOB_EVALUATION_PLAN_MODEL,
            schema_version=(
                JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
                if snapshot_payload.get("schema_version") == "4.0"
                else settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION
            ),
            input_fingerprint=input_fingerprint,
            input_snapshot=snapshot_payload,
            error_code=None,
            error_message=None,
            completed_at=None,
        )
        db.add(plan)
        return plan, True

    @staticmethod
    def _reset_generating_plan(
        plan: JobEvaluationPlan,
        snapshot_payload: dict[str, Any],
        jd_fingerprint: str,
        input_fingerprint: str,
        settings: Settings,
    ) -> None:
        plan.status = JobEvaluationPlanStatus.GENERATING.value
        plan.is_current = True
        is_v4 = snapshot_payload.get("schema_version") == "4.0"
        plan.items = null() if is_v4 else []
        is_v3 = snapshot_payload.get("schema_version") == "3.0"
        plan.structured_coverage = (
            null()
            if is_v3 or is_v4
            else JobEvaluationPlanService._empty_coverage()
        )
        plan.free_text_coverage = null()
        plan.source_review_summary = null()
        plan.requirement_facts = null()
        plan.evaluation_criteria = null()
        plan.coverage_review_summary = null()
        plan.generation_audit = null()
        plan.warnings = []
        plan.prompt_version = (
            V4_PROMPT_VERSIONS["fact_extraction"]
            if is_v4
            else settings.JOB_EVALUATION_PLAN_PROMPT_VERSION
        )
        plan.model_version = settings.JOB_EVALUATION_PLAN_MODEL
        plan.schema_version = (
            JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
            if is_v4
            else settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION
        )
        plan.jd_fingerprint = jd_fingerprint
        plan.input_fingerprint = input_fingerprint
        plan.input_snapshot = snapshot_payload
        plan.error_code = None
        plan.error_message = None
        plan.completed_at = None

    async def mark_current_plan_outdated_if_input_changed(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobEvaluationPlan | None:
        """After an open Job edit, invalidate stale plan data without calling AI."""
        try:
            job = await self._get_locked_job(db, job_id)
            if job is None:
                return None
            current = await db.scalar(
                select(JobEvaluationPlan)
                .where(
                    JobEvaluationPlan.job_id == job_id,
                    JobEvaluationPlan.is_current.is_(True),
                )
                .with_for_update()
            )
            if current is None:
                await db.rollback()
                return None
            snapshot = self.build_v4_input_snapshot(job)
            if (
                current.schema_version == JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
                and current.input_fingerprint == self.fingerprint_input(snapshot)
            ):
                await db.commit()
                await db.refresh(current)
                return current
            current.status = JobEvaluationPlanStatus.OUTDATED.value
            current.is_current = False
            if current.completed_at is None:
                current.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(current)
            return current
        except BaseException:
            await db.rollback()
            raise

    async def confirm_current_plan(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobEvaluationPlan:
        """Move the current validated 4.0 pending_confirmation plan to ready."""
        stale_plan: JobEvaluationPlan | None = None
        try:
            job = await self._get_locked_job(db, job_id)
            if job is None:
                raise JobEvaluationPlanJobNotFoundError("岗位不存在")
            plan = await db.scalar(
                select(JobEvaluationPlan)
                .where(
                    JobEvaluationPlan.job_id == job_id,
                    JobEvaluationPlan.is_current.is_(True),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if plan is None:
                raise JobEvaluationPlanNotFoundError("当前岗位还没有评价计划")
            if job.status != "open":
                raise JobEvaluationPlanNotConfirmableError(
                    "关闭岗位不能确认评价计划"
                )

            snapshot = self.build_v4_input_snapshot(job)
            input_fingerprint = self.fingerprint_input(snapshot)
            if (
                not plan.is_current
                or plan.schema_version != "4.0"
                or plan.input_fingerprint != input_fingerprint
                or plan.jd_fingerprint != self.fingerprint_snapshot(snapshot)
            ):
                plan.status = JobEvaluationPlanStatus.OUTDATED.value
                plan.is_current = False
                await db.commit()
                await db.refresh(plan)
                stale_plan = plan
            elif plan.status == JobEvaluationPlanStatus.READY.value:
                self.build_read_model(plan)
                await db.commit()
                await db.refresh(plan)
                return plan
            elif plan.status != "pending_confirmation":
                raise JobEvaluationPlanNotConfirmableError(
                    "只有当前待确认的 4.0 评价计划可以确认"
                )
            else:
                self.build_read_model(plan)
                plan.status = JobEvaluationPlanStatus.READY.value
                await db.commit()
                await db.refresh(plan)
                return plan
        except JobEvaluationPlanServiceError:
            await db.rollback()
            raise
        except (AttributeError, ValidationError, TypeError, ValueError):
            await db.rollback()
            raise JobEvaluationPlanNotConfirmableError(
                "待确认评价计划没有通过 4.0 完整性复核"
            ) from None
        except BaseException:
            await db.rollback()
            raise

        if stale_plan is not None:
            raise JobEvaluationPlanNotConfirmableError(
                "岗位输入已经变化，旧评价计划已过期"
            )
        raise AssertionError("unreachable")

    async def _extract_with_retry(
        self,
        adapter: JobEvaluationPlanAdapter,
        extraction_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        for attempt in range(2):
            try:
                return await adapter.extract(extraction_input)
            except JobEvaluationPlanAdapterError as exc:
                if not exc.retryable or attempt == 1:
                    raise
        raise AssertionError("unreachable")

    async def build_v4_plan_content(
        self,
        snapshot: JobEvaluationPlanInputSnapshot | dict[str, Any],
        *,
        adapter: JobEvaluationPlanAdapter,
        input_is_current: Callable[[], bool] | None = None,
    ) -> GeneratedPlanContentV4:
        """Build validated 4.0 content without API, Model, or PostgreSQL writes."""
        audit_calls: list[JobEvaluationPlanGenerationCallAudit] = []
        try:
            validated_snapshot = JobEvaluationPlanInputSnapshot.model_validate(snapshot)
            if validated_snapshot.schema_version != "4.0":
                raise JobEvaluationPlanContentError(
                    "纯生成工作流只接受 4.0 input snapshot",
                    code="JOB_EVALUATION_PLAN_V4_INPUT_REQUIRED",
                )
            snapshot_payload = validated_snapshot.model_dump(mode="json")
            self._validate_v4_serialized_size(
                snapshot_payload,
                JOB_EVALUATION_PLAN_V4_MAX_INPUT_CHARS,
                "JOB_EVALUATION_PLAN_V4_INPUT_TOO_LARGE",
            )
            source_units = list(validated_snapshot.source_units or [])

            extraction_input = JobRequirementFactExtractionInput(
                input_snapshot=validated_snapshot,
                source_units=source_units,
            )
            extraction = await self._invoke_v4_role(
                adapter,
                "fact_extraction",
                extraction_input.model_dump(mode="json"),
                AIRequirementFactExtractionOutput,
                audit_calls,
            )
            facts, source_review, warning_signals = self._build_v4_extracted_facts(
                source_units,
                extraction,
            )
            self.validate_v4_fact_count(len(facts))
            self._ensure_v4_input_current(input_is_current)

            coverage_input = JobRequirementCoverageReviewInput(
                source_units=source_units,
                requirement_facts=facts,
                source_review_summary=source_review,
            )
            coverage = await self._invoke_v4_role(
                adapter,
                "coverage_review",
                coverage_input.model_dump(mode="json"),
                AIRequirementCoverageReviewOutput,
                audit_calls,
            )
            self._validate_v4_coverage_findings(source_units, facts, coverage)
            repair_performed = False
            if coverage.status == "needs_repair":
                failed_source_unit_ids = sorted(
                    {
                        source_unit_id
                        for finding in coverage.findings
                        for source_unit_id in finding.source_unit_ids
                    }
                )
                facts, source_review, repaired_signals = (
                    await self.repair_v4_source_units(
                        snapshot=validated_snapshot,
                        requirement_facts=facts,
                        source_review_summary=source_review,
                        findings=coverage.findings,
                        failed_source_unit_ids=failed_source_unit_ids,
                        adapter=adapter,
                        audit_calls=audit_calls,
                    )
                )
                warning_signals.update(repaired_signals)
                repair_performed = True
                self.validate_v4_fact_count(len(facts))
            self._ensure_v4_input_current(input_is_current)

            grouping_input = JobEvaluationCriterionGroupingInput(
                requirement_facts=facts
            )
            grouping = await self._invoke_v4_role(
                adapter,
                "criterion_grouping",
                grouping_input.model_dump(mode="json"),
                AIEvaluationCriterionGroupingOutput,
                audit_calls,
            )
            criteria = self._build_v4_criteria(facts, grouping)
            self._ensure_v4_input_current(input_is_current)

            coverage_summary = JobEvaluationPlanCoverageReviewSummary(
                status="passed",
                findings=[],
                repair_performed=repair_performed,
                reviewed_source_unit_ids=[
                    unit.source_unit_id for unit in source_units
                ],
            )
            warnings = self._build_v4_warnings(
                facts,
                source_review,
                warning_signals,
            )
            self._validate_v4_output_sizes(facts, criteria)
            generation_audit = self._build_v4_generation_audit(audit_calls)
            role_order = tuple(call.role for call in generation_audit.calls)
            if role_order not in {
                ("fact_extraction", "coverage_review", "criterion_grouping"),
                (
                    "fact_extraction",
                    "coverage_review",
                    "local_repair",
                    "criterion_grouping",
                ),
            }:
                raise JobEvaluationPlanContentError(
                    "岗位评价计划 4.0 业务调用顺序不合法",
                    code="JOB_EVALUATION_PLAN_V4_CALL_ORDER_INVALID",
                )
            infrastructure_retry_count = sum(
                call.infrastructure_retry_count for call in generation_audit.calls
            )
            content_repair_count = sum(
                call.role == "local_repair" for call in generation_audit.calls
            )
            if (
                generation_audit.infrastructure_retry_count
                != infrastructure_retry_count
                or generation_audit.content_repair_count != content_repair_count
            ):
                raise JobEvaluationPlanContentError(
                    "岗位评价计划 4.0 调用审计计数不一致",
                    code="JOB_EVALUATION_PLAN_V4_AUDIT_INVALID",
                )
            return GeneratedPlanContentV4(
                requirement_facts=facts,
                evaluation_criteria=criteria,
                source_review_summary=source_review,
                coverage_review_summary=coverage_summary,
                warnings=warnings,
                generation_audit=generation_audit,
            )
        except JobEvaluationPlanV4GenerationError:
            raise
        except JobEvaluationPlanAdapterError as exc:
            raise self._v4_generation_failure(
                code=exc.code,
                message=self._safe_adapter_message(exc),
                audit_calls=audit_calls,
            ) from None
        except JobEvaluationPlanContentError as exc:
            if exc.code != "JOB_EVALUATION_PLAN_INPUT_OUTDATED_DURING_GENERATION":
                self._mark_last_v4_call_failed(audit_calls, exc.code)
            raise self._v4_generation_failure(
                code=exc.code,
                message=str(exc),
                audit_calls=audit_calls,
            ) from None
        except (ValidationError, TypeError, ValueError):
            self._mark_last_v4_call_failed(
                audit_calls,
                "JOB_EVALUATION_PLAN_V4_BUSINESS_VALIDATION_FAILED",
            )
            raise self._v4_generation_failure(
                code="JOB_EVALUATION_PLAN_V4_BUSINESS_VALIDATION_FAILED",
                message="岗位评价计划 4.0 内容未通过确定性校验",
                audit_calls=audit_calls,
            ) from None
        except Exception:
            raise self._v4_generation_failure(
                code="JOB_EVALUATION_PLAN_UNEXPECTED_ERROR",
                message="岗位评价计划 4.0 生成发生未预期错误",
                audit_calls=audit_calls,
            ) from None

    async def _invoke_v4_role(
        self,
        adapter: JobEvaluationPlanAdapter,
        role: str,
        generation_input: dict[str, Any],
        output_type: type[BaseModel],
        audit_calls: list[JobEvaluationPlanGenerationCallAudit],
    ) -> Any:
        self._validate_v4_serialized_size(
            generation_input,
            JOB_EVALUATION_PLAN_V4_MAX_INPUT_CHARS,
            "JOB_EVALUATION_PLAN_V4_INPUT_TOO_LARGE",
        )
        started_at = time.perf_counter()
        for attempt in range(2):
            try:
                result = await adapter.generate_v4(role, generation_input)
                try:
                    payload = json.loads(
                        result.content,
                        object_pairs_hook=self._json_object_without_duplicate_keys,
                    )
                    parsed = output_type.model_validate(payload)
                except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                    audit_calls.append(
                        self._v4_call_audit(
                            role=role,
                            model=result.model,
                            result="failed",
                            error_code="JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT",
                            input_tokens=result.input_tokens,
                            output_tokens=result.output_tokens,
                            duration_ms=self._elapsed_ms(started_at),
                            infrastructure_retry_count=attempt,
                        )
                    )
                    raise JobEvaluationPlanContentError(
                        f"{role} 输出未通过独立 JSON Schema 校验",
                        code="JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT",
                    ) from None
                audit_calls.append(
                    self._v4_call_audit(
                        role=role,
                        model=result.model,
                        result="succeeded",
                        error_code=None,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        duration_ms=self._elapsed_ms(started_at),
                        infrastructure_retry_count=attempt,
                    )
                )
                return parsed
            except JobEvaluationPlanAdapterError as exc:
                if exc.retryable and attempt == 0:
                    continue
                audit_calls.append(
                    self._v4_call_audit(
                        role=role,
                        model=self._v4_adapter_model(adapter),
                        result="failed",
                        error_code=exc.code,
                        input_tokens=None,
                        output_tokens=None,
                        duration_ms=self._elapsed_ms(started_at),
                        infrastructure_retry_count=attempt,
                    )
                )
                raise
        raise AssertionError("unreachable")

    async def repair_v4_source_units(
        self,
        *,
        snapshot: JobEvaluationPlanInputSnapshot,
        requirement_facts: list[RequirementFact],
        source_review_summary: JobEvaluationPlanSourceReviewSummaryV4,
        findings: list[JobEvaluationPlanCoverageFinding],
        failed_source_unit_ids: list[str],
        adapter: JobEvaluationPlanAdapter,
        audit_calls: list[JobEvaluationPlanGenerationCallAudit],
    ) -> tuple[
        list[RequirementFact],
        JobEvaluationPlanSourceReviewSummaryV4,
        dict[str, set[str]],
    ]:
        if not failed_source_unit_ids:
            raise JobEvaluationPlanContentError(
                "coverage finding 无法定位到 source unit",
                code="JOB_EVALUATION_PLAN_V4_REPAIR_SCOPE_INVALID",
            )
        source_by_id = {
            unit.source_unit_id: unit for unit in (snapshot.source_units or [])
        }
        failed_ids = set(failed_source_unit_ids)
        if not failed_ids.issubset(source_by_id):
            raise JobEvaluationPlanContentError(
                "局部修复引用了不存在的 source unit",
                code="JOB_EVALUATION_PLAN_V4_REPAIR_SCOPE_INVALID",
            )
        cited_fact_ids = {
            fact_id for finding in findings for fact_id in finding.fact_ids
        }
        related_facts = [
            fact
            for fact in requirement_facts
            if fact.fact_id in cited_fact_ids
            or any(source.source_unit_id in failed_ids for source in fact.sources)
        ]
        repair_input = JobRequirementLocalRepairInput(
            source_units=[source_by_id[source_id] for source_id in failed_source_unit_ids],
            related_facts=related_facts,
            findings=findings,
        )
        repair = await self._invoke_v4_role(
            adapter,
            "local_repair",
            repair_input.model_dump(mode="json"),
            AIRequirementLocalRepairOutput,
            audit_calls,
        )
        expected_indexes = set(range(len(findings)))
        if repair.unresolved_finding_indexes or set(
            repair.resolved_finding_indexes
        ) != expected_indexes:
            raise JobEvaluationPlanContentError(
                "局部修复仍存在未解决的 coverage finding",
                code="JOB_EVALUATION_PLAN_V4_REPAIR_UNRESOLVED",
            )
        review_ids = {review.source_unit_id for review in repair.source_reviews}
        if review_ids != failed_ids:
            raise JobEvaluationPlanContentError(
                "局部修复没有完整且唯一地处理失败 source units",
                code="JOB_EVALUATION_PLAN_V4_REPAIR_SCOPE_INVALID",
            )
        repair_candidate_ids = {
            item.candidate_id for item in repair.replacement_candidates
        }
        referenced_candidate_ids = {
            candidate_id
            for review in repair.source_reviews
            for candidate_id in review.candidate_ids
        }
        if referenced_candidate_ids != repair_candidate_ids:
            raise JobEvaluationPlanContentError(
                "局部修复候选事实必须且只能被 source review 引用",
                code="JOB_EVALUATION_PLAN_V4_REPAIR_INVALID",
            )
        for review in repair.source_reviews:
            if not set(review.candidate_ids).issubset(repair_candidate_ids):
                raise JobEvaluationPlanContentError(
                    "局部修复 source review 引用了不存在的候选事实",
                    code="JOB_EVALUATION_PLAN_V4_REPAIR_INVALID",
                )
        related_fact_ids = {fact.fact_id for fact in related_facts}
        for candidate in repair.replacement_candidates:
            if candidate.merge_into_fact_id not in related_fact_ids | {None}:
                raise JobEvaluationPlanContentError(
                    "局部修复只能合并到输入中的相关 fact",
                    code="JOB_EVALUATION_PLAN_V4_REPAIR_SCOPE_INVALID",
                )
            if any(source.source_unit_id not in failed_ids for source in candidate.sources):
                raise JobEvaluationPlanContentError(
                    "局部修复返回了失败范围之外的来源",
                    code="JOB_EVALUATION_PLAN_V4_REPAIR_SCOPE_INVALID",
                )
            self._validate_v4_sources(candidate.sources, source_by_id)
            candidate_source_ids = {
                source.source_unit_id for source in candidate.sources
            }
            review_source_ids = {
                review.source_unit_id
                for review in repair.source_reviews
                if candidate.candidate_id in review.candidate_ids
            }
            if candidate_source_ids != review_source_ids:
                raise JobEvaluationPlanContentError(
                    "局部修复候选来源与 source review 引用不一致",
                    code="JOB_EVALUATION_PLAN_V4_REPAIR_INVALID",
                )

        groups: list[dict[str, Any]] = []
        group_by_old_fact_id: dict[str, dict[str, Any]] = {}
        for fact in requirement_facts:
            retained_sources = [
                source
                for source in fact.sources
                if source.source_unit_id not in failed_ids
            ]
            group = {
                "category": fact.category,
                "sources": retained_sources,
                "old_fact_id": fact.fact_id,
            }
            groups.append(group)
            group_by_old_fact_id[fact.fact_id] = group
        for candidate in repair.replacement_candidates:
            if candidate.merge_into_fact_id is not None:
                target = group_by_old_fact_id[candidate.merge_into_fact_id]
                target["category"] = candidate.category
                target["sources"].extend(candidate.sources)
            else:
                groups.append(
                    {
                        "category": candidate.category,
                        "sources": list(candidate.sources),
                        "old_fact_id": None,
                    }
                )
        facts = self._stable_v4_facts_from_groups(
            [group for group in groups if group["sources"]],
            list(source_by_id.values()),
        )
        self.validate_v4_fact_count(len(facts))

        old_review_by_id = {
            review.source_unit_id: review for review in source_review_summary.units
        }
        repaired_review_by_id = {
            review.source_unit_id: review for review in repair.source_reviews
        }
        non_evaluation_reasons: dict[str, str | None] = {}
        warning_signals: dict[str, set[str]] = {}
        for source_id in source_by_id:
            review = repaired_review_by_id.get(source_id)
            if review is None:
                old_review = old_review_by_id[source_id]
                non_evaluation_reasons[source_id] = old_review.non_evaluation_reason
            else:
                non_evaluation_reasons[source_id] = review.non_evaluation_reason
                warning_signals[source_id] = set(review.warning_codes)
        source_review = self._rebuild_v4_source_review(
            list(source_by_id.values()),
            facts,
            non_evaluation_reasons,
        )
        return facts, source_review, warning_signals

    @staticmethod
    def priority_for_v4_sources(source_fields: Iterable[str]) -> str:
        priorities = {
            "job_responsibilities": "general",
            "candidate_requirements": "required",
            "preferred_qualifications": "preferred",
            "general": "general",
            "required": "required",
            "preferred": "preferred",
        }
        rank = {"general": 0, "preferred": 1, "required": 2}
        resolved = [priorities[value] for value in source_fields if value in priorities]
        if not resolved:
            raise JobEvaluationPlanContentError(
                "RequirementFact 缺少可计算 priority 的来源",
                code="JOB_EVALUATION_PLAN_V4_SOURCE_INVALID",
            )
        return max(resolved, key=rank.__getitem__)

    @staticmethod
    def v4_quantity_warnings(fact_count: int) -> list[str]:
        if 1 <= fact_count <= 4:
            return ["limited_basis"]
        if fact_count >= 31:
            return ["overly_broad_jd"]
        return []

    @staticmethod
    def validate_v4_fact_count(fact_count: int) -> None:
        if fact_count == 0:
            raise JobEvaluationPlanContentError(
                "JOB_EVALUATION_PLAN_NO_FACTS：岗位没有形成可评价事实",
                code="JOB_EVALUATION_PLAN_NO_FACTS",
            )
        if fact_count > JOB_EVALUATION_PLAN_V4_MAX_FACTS:
            raise JobEvaluationPlanContentError(
                "RequirementFact 数量超过技术安全边界",
                code="JOB_EVALUATION_PLAN_V4_FACT_LIMIT_EXCEEDED",
            )

    @staticmethod
    def clear_v4_partial_content(payload: dict[str, Any]) -> dict[str, Any]:
        cleared = dict(payload)
        for field in (
            "requirement_facts",
            "evaluation_criteria",
            "source_review_summary",
            "coverage_review_summary",
        ):
            cleared[field] = None
        return cleared

    def _build_v4_extracted_facts(
        self,
        source_units: list[JobEvaluationPlanSourceUnit],
        extraction: AIRequirementFactExtractionOutput,
    ) -> tuple[
        list[RequirementFact],
        JobEvaluationPlanSourceReviewSummaryV4,
        dict[str, set[str]],
    ]:
        source_by_id = {unit.source_unit_id: unit for unit in source_units}
        reviews = {review.source_unit_id: review for review in extraction.source_reviews}
        if set(reviews) != set(source_by_id):
            raise JobEvaluationPlanContentError(
                "事实提取必须完整且唯一地审阅全部 source units",
                code="JOB_EVALUATION_PLAN_V4_SOURCE_REVIEW_INCOMPLETE",
            )
        candidate_by_id = {
            candidate.candidate_id: candidate
            for candidate in extraction.fact_candidates
        }
        referenced_ids = {
            candidate_id
            for review in extraction.source_reviews
            for candidate_id in review.candidate_ids
        }
        if referenced_ids != set(candidate_by_id):
            raise JobEvaluationPlanContentError(
                "事实候选必须且只能被 source review 引用",
                code="JOB_EVALUATION_PLAN_V4_FACT_REFERENCE_INVALID",
            )
        for candidate in extraction.fact_candidates:
            self._validate_v4_sources(candidate.sources, source_by_id)
            candidate_source_ids = {
                source.source_unit_id for source in candidate.sources
            }
            review_source_ids = {
                review.source_unit_id
                for review in extraction.source_reviews
                if candidate.candidate_id in review.candidate_ids
            }
            if candidate_source_ids != review_source_ids:
                raise JobEvaluationPlanContentError(
                    "事实候选来源与 source review 引用不一致",
                    code="JOB_EVALUATION_PLAN_V4_FACT_REFERENCE_INVALID",
                )
        groups = [
            {
                "category": candidate.category,
                "sources": list(candidate.sources),
                "old_fact_id": None,
            }
            for candidate in extraction.fact_candidates
        ]
        facts = self._stable_v4_facts_from_groups(groups, source_units)
        non_evaluation_reasons = {
            source_id: review.non_evaluation_reason
            for source_id, review in reviews.items()
        }
        source_review = self._rebuild_v4_source_review(
            source_units,
            facts,
            non_evaluation_reasons,
        )
        warning_signals = {
            source_id: set(review.warning_codes)
            for source_id, review in reviews.items()
        }
        return facts, source_review, warning_signals

    def _stable_v4_facts_from_groups(
        self,
        groups: list[dict[str, Any]],
        source_units: list[JobEvaluationPlanSourceUnit],
    ) -> list[RequirementFact]:
        source_order = {
            unit.source_unit_id: index for index, unit in enumerate(source_units)
        }
        merged: list[dict[str, Any]] = []
        for group in groups:
            sources = self._deduplicate_v4_sources(group["sources"])
            normalized_quotes = {
                self._normalize_fingerprint_text(source.source_quote)
                for source in sources
            }
            target = next(
                (
                    existing
                    for existing in merged
                    if existing["category"] == group["category"]
                    and existing["normalized_quotes"] & normalized_quotes
                ),
                None,
            )
            if target is None:
                merged.append(
                    {
                        "category": group["category"],
                        "sources": sources,
                        "normalized_quotes": normalized_quotes,
                    }
                )
            else:
                target["sources"] = self._deduplicate_v4_sources(
                    [*target["sources"], *sources]
                )
                target["normalized_quotes"].update(normalized_quotes)
        merged.sort(
            key=lambda group: (
                min(source_order[source.source_unit_id] for source in group["sources"]),
                min(source.source_quote for source in group["sources"]),
                str(group["category"]),
            )
        )
        facts: list[RequirementFact] = []
        for index, group in enumerate(merged, start=1):
            ordered_sources = sorted(
                group["sources"],
                key=lambda source: (
                    -self._v4_source_priority_rank(source.source_field),
                    source_order[source.source_unit_id],
                    source.source_quote,
                ),
            )
            facts.append(
                RequirementFact(
                    fact_id=f"fact:{index:04d}",
                    category=group["category"],
                    priority=self.priority_for_v4_sources(
                        source.source_field for source in ordered_sources
                    ),
                    sources=ordered_sources,
                )
            )
        return facts

    @staticmethod
    def _deduplicate_v4_sources(
        sources: Iterable[RequirementFactSource],
    ) -> list[RequirementFactSource]:
        values: list[RequirementFactSource] = []
        seen: set[tuple[str, str, str]] = set()
        for source in sources:
            identity = (
                source.source_field,
                source.source_unit_id,
                source.source_quote,
            )
            if identity not in seen:
                seen.add(identity)
                values.append(source)
        return values

    @staticmethod
    def _v4_source_priority_rank(source_field: str) -> int:
        return {
            "job_responsibilities": 0,
            "preferred_qualifications": 1,
            "candidate_requirements": 2,
        }[source_field]

    def _validate_v4_sources(
        self,
        sources: Iterable[RequirementFactSource],
        source_by_id: Mapping[str, JobEvaluationPlanSourceUnit],
    ) -> None:
        for source in sources:
            unit = source_by_id.get(source.source_unit_id)
            if unit is None or unit.source_field != source.source_field:
                raise JobEvaluationPlanContentError(
                    "RequirementFact 引用了不存在或字段不一致的 source unit",
                    code="JOB_EVALUATION_PLAN_V4_SOURCE_INVALID",
                )
            if source.source_quote not in unit.source_text:
                raise JobEvaluationPlanContentError(
                    "RequirementFact source quote 无法在原文中连续定位",
                    code="JOB_EVALUATION_PLAN_V4_SOURCE_QUOTE_INVALID",
                )

    def _rebuild_v4_source_review(
        self,
        source_units: list[JobEvaluationPlanSourceUnit],
        facts: list[RequirementFact],
        non_evaluation_reasons: Mapping[str, str | None],
    ) -> JobEvaluationPlanSourceReviewSummaryV4:
        review_units: list[JobEvaluationPlanSourceReviewUnitV4] = []
        for unit in source_units:
            fact_ids = [
                fact.fact_id
                for fact in facts
                if any(
                    source.source_unit_id == unit.source_unit_id
                    for source in fact.sources
                )
            ]
            if fact_ids:
                review_units.append(
                    JobEvaluationPlanSourceReviewUnitV4(
                        source_unit_id=unit.source_unit_id,
                        disposition="evaluation",
                        fact_ids=fact_ids,
                        non_evaluation_reason=None,
                    )
                )
            else:
                reason = non_evaluation_reasons.get(unit.source_unit_id)
                if reason is None:
                    raise JobEvaluationPlanContentError(
                        "没有事实的 source unit 缺少受控排除原因",
                        code="JOB_EVALUATION_PLAN_V4_SOURCE_REVIEW_INCOMPLETE",
                    )
                review_units.append(
                    JobEvaluationPlanSourceReviewUnitV4(
                        source_unit_id=unit.source_unit_id,
                        disposition="non_evaluation",
                        fact_ids=[],
                        non_evaluation_reason=reason,
                    )
                )
        evaluation_count = sum(
            unit.disposition == "evaluation" for unit in review_units
        )
        return JobEvaluationPlanSourceReviewSummaryV4(
            rule_version=JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
            total_units=len(source_units),
            reviewed_units=len(review_units),
            evaluation_units=evaluation_count,
            non_evaluation_units=len(review_units) - evaluation_count,
            all_reviewed=True,
            units=review_units,
        )

    def _validate_v4_coverage_findings(
        self,
        source_units: list[JobEvaluationPlanSourceUnit],
        facts: list[RequirementFact],
        coverage: AIRequirementCoverageReviewOutput,
    ) -> None:
        source_ids = {unit.source_unit_id for unit in source_units}
        fact_ids = {fact.fact_id for fact in facts}
        for finding in coverage.findings:
            if not set(finding.source_unit_ids).issubset(source_ids):
                raise JobEvaluationPlanContentError(
                    "coverage finding 引用了不存在的 source unit",
                    code="JOB_EVALUATION_PLAN_V4_COVERAGE_INVALID",
                )
            if not set(finding.fact_ids).issubset(fact_ids):
                raise JobEvaluationPlanContentError(
                    "coverage finding 引用了不存在的 fact",
                    code="JOB_EVALUATION_PLAN_V4_COVERAGE_INVALID",
                )

    def _build_v4_criteria(
        self,
        facts: list[RequirementFact],
        grouping: AIEvaluationCriterionGroupingOutput,
    ) -> list[EvaluationCriterion]:
        expected = {fact.fact_id for fact in facts}
        grouped = [fact_id for item in grouping.criteria for fact_id in item.fact_ids]
        if len(grouped) != len(set(grouped)):
            raise JobEvaluationPlanContentError(
                "每条 fact 只能属于一个 criterion",
                code="JOB_EVALUATION_PLAN_V4_GROUPING_INVALID",
            )
        if set(grouped) != expected:
            raise JobEvaluationPlanContentError(
                "criterion grouping 必须完整覆盖全部 facts",
                code="JOB_EVALUATION_PLAN_V4_GROUPING_INVALID",
            )
        return [
            EvaluationCriterion(
                criterion_id=f"criterion:{index:04d}",
                name=item.name,
                fact_ids=item.fact_ids,
            )
            for index, item in enumerate(grouping.criteria, start=1)
        ]

    def _build_v4_warnings(
        self,
        facts: list[RequirementFact],
        source_review: JobEvaluationPlanSourceReviewSummaryV4,
        warning_signals: Mapping[str, set[str]],
    ) -> list[JobEvaluationPlanV4WarningDetail]:
        review_by_id = {unit.source_unit_id: unit for unit in source_review.units}
        warnings: list[JobEvaluationPlanV4WarningDetail] = []
        evaluation_source_ids = [
            unit.source_unit_id
            for unit in source_review.units
            if unit.disposition == "evaluation"
        ]
        quantity_messages = {
            "limited_basis": "当前计划只有 1—4 条事实，评价依据有限",
            "overly_broad_jd": "当前计划包含 31 条及以上事实，请 HR 重点复核",
        }
        for code in self.v4_quantity_warnings(len(facts)):
            warnings.append(
                JobEvaluationPlanV4WarningDetail(
                    code=code,
                    message=quantity_messages[code],
                    source_unit_ids=evaluation_source_ids,
                    fact_ids=[fact.fact_id for fact in facts],
                )
            )
        for source_id, codes in warning_signals.items():
            review = review_by_id[source_id]
            for code in sorted(codes):
                message = (
                    "原文要求较模糊，未补充原文不存在的具体条件"
                    if code == "ambiguous_requirement"
                    else "评价字段中包含未生成事实的非评价内容"
                )
                warnings.append(
                    JobEvaluationPlanV4WarningDetail(
                        code=code,
                        message=message,
                        source_unit_ids=[source_id],
                        fact_ids=review.fact_ids,
                    )
                )
        for fact in facts:
            source_priorities = {
                self.priority_for_v4_sources([source.source_field])
                for source in fact.sources
            }
            if len(source_priorities) > 1:
                warnings.append(
                    JobEvaluationPlanV4WarningDetail(
                        code=JobEvaluationPlanV4WarningCode.CONFLICTING_REQUIREMENTS,
                        message="同一事实出现在不同优先级字段，最终按最高优先级计算",
                        source_unit_ids=list(
                            dict.fromkeys(
                                source.source_unit_id for source in fact.sources
                            )
                        ),
                        fact_ids=[fact.fact_id],
                    )
                )
        unique: list[JobEvaluationPlanV4WarningDetail] = []
        seen: set[str] = set()
        for warning in warnings:
            key = json.dumps(
                warning.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
            )
            if key not in seen:
                seen.add(key)
                unique.append(warning)
        return unique

    def _validate_v4_output_sizes(
        self,
        facts: list[RequirementFact],
        criteria: list[EvaluationCriterion],
    ) -> None:
        fact_payload = [fact.model_dump(mode="json") for fact in facts]
        criterion_payload = [item.model_dump(mode="json") for item in criteria]
        self._validate_v4_serialized_size(
            fact_payload,
            JOB_EVALUATION_PLAN_V4_MAX_FACTS_JSON_CHARS,
            "JOB_EVALUATION_PLAN_V4_FACTS_JSON_TOO_LARGE",
        )
        self._validate_v4_serialized_size(
            criterion_payload,
            JOB_EVALUATION_PLAN_V4_MAX_CRITERIA_JSON_CHARS,
            "JOB_EVALUATION_PLAN_V4_CRITERIA_JSON_TOO_LARGE",
        )
        self._validate_v4_serialized_size(
            {
                "requirement_facts": fact_payload,
                "evaluation_criteria": criterion_payload,
            },
            JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_JSON_CHARS,
            "JOB_EVALUATION_PLAN_V4_OUTPUT_JSON_TOO_LARGE",
        )

    @staticmethod
    def _validate_v4_serialized_size(
        payload: Any,
        maximum: int,
        error_code: str,
    ) -> None:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(serialized) > maximum:
            raise JobEvaluationPlanContentError(
                "岗位评价计划 4.0 结构化内容超过技术安全边界",
                code=error_code,
            )

    @staticmethod
    def _ensure_v4_input_current(
        input_is_current: Callable[[], bool] | None,
    ) -> None:
        if input_is_current is not None and not input_is_current():
            raise JobEvaluationPlanContentError(
                "岗位输入在 4.0 生成期间已经变化",
                code="JOB_EVALUATION_PLAN_INPUT_OUTDATED_DURING_GENERATION",
            )

    @staticmethod
    def _json_object_without_duplicate_keys(
        pairs: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("JSON 对象包含重复字段")
            value[key] = item
        return value

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))

    @staticmethod
    def _v4_adapter_model(adapter: JobEvaluationPlanAdapter) -> str:
        settings = getattr(adapter, "settings", None)
        model = getattr(settings, "JOB_EVALUATION_PLAN_MODEL", None)
        if isinstance(model, str) and model.strip():
            return model
        return "unknown-model"

    @staticmethod
    def _v4_call_audit(
        *,
        role: str,
        model: str,
        result: str,
        error_code: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        duration_ms: int,
        infrastructure_retry_count: int,
    ) -> JobEvaluationPlanGenerationCallAudit:
        return JobEvaluationPlanGenerationCallAudit(
            role=role,
            prompt_version=V4_PROMPT_VERSIONS[role],
            model=model,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            duration_ms=duration_ms,
            infrastructure_retry_count=infrastructure_retry_count,
            result=result,
            error_code=error_code,
        )

    @staticmethod
    def _mark_last_v4_call_failed(
        audit_calls: list[JobEvaluationPlanGenerationCallAudit],
        error_code: str,
    ) -> None:
        if audit_calls and audit_calls[-1].result == "succeeded":
            audit_calls[-1] = audit_calls[-1].model_copy(
                update={"result": "failed", "error_code": error_code}
            )

    @staticmethod
    def _build_v4_generation_audit(
        audit_calls: list[JobEvaluationPlanGenerationCallAudit],
    ) -> JobEvaluationPlanGenerationAudit:
        return JobEvaluationPlanGenerationAudit(
            business_call_count=len(audit_calls),
            content_repair_count=sum(
                call.role == "local_repair" for call in audit_calls
            ),
            infrastructure_retry_count=sum(
                call.infrastructure_retry_count for call in audit_calls
            ),
            calls=audit_calls,
        )

    def _v4_generation_failure(
        self,
        *,
        code: str,
        message: str,
        audit_calls: list[JobEvaluationPlanGenerationCallAudit],
    ) -> JobEvaluationPlanV4GenerationError:
        return JobEvaluationPlanV4GenerationError(
            message,
            code=code,
            generation_audit=self._build_v4_generation_audit(audit_calls),
        )

    def build_input_snapshot(self, job: Job) -> JobEvaluationPlanInputSnapshot:
        if not (
            hasattr(job, "requirements")
            and hasattr(job, "description")
            and getattr(job, "requirements", None) is not None
        ):
            return self._build_v3_input_snapshot(job)
        try:
            requirements = LegacyEvaluationPlanRequirements.model_validate(
                job.requirements
            )
            return JobEvaluationPlanInputSnapshot(
                job_id=job.id,
                title=job.title,
                department=job.department,
                description=job.description,
                requirements=requirements.model_dump(mode="json"),
            )
        except (ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanContentError(
                "岗位结构化要求不符合当前 Schema",
                code="JOB_EVALUATION_PLAN_INVALID_JOB_INPUT",
            ) from None

    def _build_v3_input_snapshot(self, job: Job) -> JobEvaluationPlanInputSnapshot:
        try:
            context = {
                "title": self._normalize_fingerprint_text(job.title),
                "department": self._normalize_optional_text(job.department),
                "job_background": self._normalize_optional_text(job.job_background),
            }
            evaluation_fields = {
                "job_responsibilities": self._normalize_optional_text(
                    job.job_responsibilities
                ),
                "candidate_requirements": self._normalize_optional_text(
                    job.candidate_requirements
                ),
                "preferred_qualifications": self._normalize_optional_text(
                    job.preferred_qualifications
                ),
            }
            source_units = self.build_five_section_source_units(evaluation_fields)
            return JobEvaluationPlanInputSnapshot.model_validate(
                {
                    "schema_version": "3.0",
                    "job_context": context,
                    "evaluation_fields": evaluation_fields,
                    "source_units": [
                        unit.model_dump(mode="json") for unit in source_units
                    ],
                }
            )
        except JobEvaluationPlanContentError:
            raise
        except (AttributeError, ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanContentError(
                "五段式岗位输入不符合当前 Schema",
                code="JOB_EVALUATION_PLAN_INVALID_JOB_INPUT",
            ) from None

    def build_v4_input_snapshot(self, job: Job) -> JobEvaluationPlanInputSnapshot:
        """Build the writable 4.0 snapshot used by the current Job/API flow."""
        try:
            context = {
                "title": self._normalize_fingerprint_text(job.title),
                "department": self._normalize_optional_text(job.department),
                "job_background": self._normalize_optional_text(job.job_background),
            }
            evaluation_fields = {
                "job_responsibilities": self._normalize_optional_text(
                    job.job_responsibilities
                ),
                "candidate_requirements": self._normalize_optional_text(
                    job.candidate_requirements
                ),
                "preferred_qualifications": self._normalize_optional_text(
                    job.preferred_qualifications
                ),
            }
            source_units = self.build_five_section_source_units(
                evaluation_fields,
                max_source_units=JOB_EVALUATION_PLAN_V4_MAX_SOURCE_UNITS,
            )
            return JobEvaluationPlanInputSnapshot.model_validate(
                {
                    "schema_version": "4.0",
                    "job_context": context,
                    "evaluation_fields": evaluation_fields,
                    "source_units": [
                        unit.model_dump(mode="json") for unit in source_units
                    ],
                }
            )
        except JobEvaluationPlanContentError:
            raise
        except (AttributeError, ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanContentError(
                "五段式岗位输入不符合 4.0 Schema",
                code="JOB_EVALUATION_PLAN_INVALID_JOB_INPUT",
            ) from None

    def build_five_section_source_units(
        self,
        evaluation_fields: Mapping[str, str | None],
        *,
        max_source_units: int | None = None,
    ) -> tuple[JobEvaluationPlanSourceUnit, ...]:
        resolved_max_units = max_source_units or self._DESCRIPTION_MAX_SOURCE_UNITS
        units: list[JobEvaluationPlanSourceUnit] = []
        for source_field in (
            "job_responsibilities",
            "candidate_requirements",
            "preferred_qualifications",
        ):
            value = evaluation_fields.get(source_field)
            if not value:
                continue
            fragments = self._split_five_section_field(value)
            for ordinal, source_text in enumerate(fragments, start=1):
                units.append(
                    JobEvaluationPlanSourceUnit(
                        source_unit_id=f"{source_field}:{ordinal:04d}",
                        source_field=source_field,
                        ordinal=ordinal,
                        source_text=source_text,
                    )
                )
                if len(units) > resolved_max_units:
                    raise JobEvaluationPlanContentError(
                        "五段式岗位原文片段超过安全数量上限",
                        code="JOB_EVALUATION_PLAN_TOO_MANY_SOURCE_UNITS",
                    )
        if not units:
            raise JobEvaluationPlanContentError(
                "岗位评价字段没有可审阅内容",
                code="JOB_EVALUATION_PLAN_EMPTY_EVALUATION_FIELDS",
            )
        return tuple(units)

    def _split_five_section_field(self, value: str) -> list[str]:
        if self._contains_unsafe_source_text(value):
            raise JobEvaluationPlanContentError(
                "岗位评价字段包含无法安全处理的字符",
                code="JOB_EVALUATION_PLAN_UNSAFE_SOURCE_TEXT",
            )
        lines = value.split("\n")
        fragments: list[str] = []
        current: list[str] = []
        current_is_list = False

        def flush() -> None:
            nonlocal current, current_is_list
            if not current:
                return
            block = "\n".join(current).strip()
            if block:
                if current_is_list or "\n" in block:
                    fragments.append(block)
                else:
                    fragments.extend(self._split_source_sentences(block))
            current = []
            current_is_list = False

        for line in lines:
            if not line.strip():
                flush()
                continue
            is_indented = line[:1].isspace()
            is_list_start = (
                not is_indented
                and self._SOURCE_LIST_PREFIX_RE.match(line.strip()) is not None
            )
            if is_list_start:
                flush()
                current = [line.rstrip()]
                current_is_list = True
            elif is_indented and current:
                current.append(line.rstrip())
            elif current_is_list:
                current.append(line.rstrip())
            else:
                flush()
                current = [line.rstrip()]
        flush()
        return fragments

    @staticmethod
    def _normalize_fingerprint_text(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("岗位文本必须是字符串")
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
        return normalized.strip()

    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = cls._normalize_fingerprint_text(value)
        return normalized or None

    def build_description_source_units(
        self,
        description: str | None,
    ) -> tuple[DescriptionSourceUnit, ...]:
        """Split description into stable, reviewable, continuous source fragments."""
        if (
            description is None
            or not isinstance(description, str)
            or not description.strip()
        ):
            raise JobEvaluationPlanContentError(
                "岗位 description 不能为空",
                code="JOB_EVALUATION_PLAN_EMPTY_DESCRIPTION",
            )
        if len(description) > self._DESCRIPTION_MAX_LENGTH:
            raise JobEvaluationPlanContentError(
                "岗位 description 超过安全长度上限",
                code="JOB_EVALUATION_PLAN_DESCRIPTION_TOO_LONG",
            )
        if self._contains_unsafe_source_text(description):
            raise JobEvaluationPlanContentError(
                "岗位 description 包含无法安全处理的字符",
                code="JOB_EVALUATION_PLAN_UNSAFE_DESCRIPTION",
            )

        fragments: list[str] = []
        for line in re.split(r"\r\n?|\n", description):
            cleaned_line = self._strip_source_unit_formatting(line)
            if not cleaned_line:
                continue
            for sentence in self._split_source_sentences(cleaned_line):
                fragments.extend(self._split_source_priority_boundaries(sentence))
                if len(fragments) > self._DESCRIPTION_MAX_SOURCE_UNITS:
                    raise JobEvaluationPlanContentError(
                        "岗位 description 片段超过安全数量上限",
                        code="JOB_EVALUATION_PLAN_TOO_MANY_SOURCE_UNITS",
                    )

        if not fragments:
            raise JobEvaluationPlanContentError(
                "岗位 description 不能为空",
                code="JOB_EVALUATION_PLAN_EMPTY_DESCRIPTION",
            )
        return tuple(
            DescriptionSourceUnit(
                source_id=f"description:{index:04d}",
                source_field="description",
                source_text=fragment,
            )
            for index, fragment in enumerate(fragments, start=1)
        )

    def build_ai_extraction_input(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
    ) -> dict[str, Any]:
        """Build the complete, program-owned input contract for AI extraction."""
        if snapshot.schema_version == "3.0":
            try:
                extraction_input = JobEvaluationPlanAIInputV3.model_validate(
                    {
                        "input_snapshot": snapshot.model_dump(mode="json"),
                        "source_units": [
                            unit.model_dump(mode="json")
                            for unit in (snapshot.source_units or [])
                        ],
                    }
                )
            except (ValidationError, TypeError, ValueError):
                raise JobEvaluationPlanContentError(
                    "五段式岗位评价计划 AI 输入未通过业务校验",
                    code="JOB_EVALUATION_PLAN_INVALID_JOB_INPUT",
                ) from None
            return extraction_input.model_dump(mode="json")
        try:
            requirements = LegacyEvaluationPlanRequirements.model_validate(
                snapshot.requirements
            )
            source_units = self.build_description_source_units(snapshot.description)
            structured_candidates, _ = self._build_structured_candidates(requirements)
            extraction_input = JobEvaluationPlanAIInput.model_validate(
                {
                    "input_snapshot": snapshot.model_dump(mode="json"),
                    "source_units": [
                        {
                            "source_id": unit.source_id,
                            "source_field": unit.source_field,
                            "source_text": unit.source_text,
                        }
                        for unit in source_units
                    ],
                    "structured_candidates": [
                        {
                            "key": candidate.item.key,
                            "title": candidate.item.title,
                            "category": candidate.item.category,
                            "priority": candidate.item.priority,
                            "source_field": candidate.item.source_field,
                        }
                        for candidate in structured_candidates
                    ],
                }
            )
        except JobEvaluationPlanContentError:
            raise
        except (ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanContentError(
                "岗位评价计划 AI 输入未通过业务校验",
                code="JOB_EVALUATION_PLAN_INVALID_JOB_INPUT",
            ) from None
        return extraction_input.model_dump(mode="json")

    @staticmethod
    def _contains_unsafe_source_text(value: str) -> bool:
        if any(
            (ord(character) < 32 and character not in "\r\n\t")
            or ord(character) == 127
            for character in value
        ):
            return True
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return True
        return False

    def _strip_source_unit_formatting(self, value: str) -> str:
        cleaned = value.strip()
        while cleaned:
            matched = self._SOURCE_LIST_PREFIX_RE.match(cleaned)
            if matched is None:
                break
            cleaned = cleaned[matched.end() :].lstrip()
        for opening, closing in self._SOURCE_WRAPPERS:
            if cleaned.startswith(opening) and cleaned.endswith(closing):
                cleaned = cleaned[len(opening) : -len(closing)].strip()
                break
        return cleaned

    def _split_source_sentences(self, value: str) -> list[str]:
        fragments: list[str] = []
        start = 0
        for matched in self._SOURCE_SENTENCE_BOUNDARY_RE.finditer(value):
            fragment = value[start : matched.end()].strip()
            if fragment:
                fragments.append(fragment)
            start = matched.end()
        tail = value[start:].strip()
        if tail:
            fragments.append(tail)
        return fragments

    def _split_source_priority_boundaries(self, value: str) -> list[str]:
        fragments: list[str] = []
        start = 0
        for matched in self._SOURCE_PRIORITY_BOUNDARY_RE.finditer(value):
            fragment = value[start : matched.end()].strip()
            if fragment:
                fragments.append(fragment)
            start = matched.end()
        tail = value[start:].strip()
        if tail:
            fragments.append(tail)
        return fragments

    @staticmethod
    def fingerprint_snapshot(snapshot: JobEvaluationPlanInputSnapshot) -> str:
        serialized = json.dumps(
            snapshot.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def fingerprint_input(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
        contract: Mapping[str, str] | None = None,
    ) -> str:
        if contract is not None:
            resolved_contract = contract
        elif snapshot.schema_version == "4.0":
            resolved_contract = {
                "breaking_contract_version": (
                    JOB_EVALUATION_PLAN_V4_BREAKING_CONTRACT_VERSION
                ),
                "ai_schema_version": JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
                "plan_schema_version": JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION,
                "source_unit_rule_version": (
                    JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION
                ),
                "fingerprint_rule_version": (
                    JOB_EVALUATION_PLAN_V4_FINGERPRINT_RULE_VERSION
                ),
            }
        elif snapshot.schema_version == "3.0":
            resolved_contract = {
                "breaking_contract_version": (
                    JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION
                ),
                "ai_schema_version": JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
                "plan_schema_version": JOB_EVALUATION_PLAN_SCHEMA_VERSION,
                "source_unit_rule_version": (
                    JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION
                ),
                "fingerprint_rule_version": (
                    JOB_EVALUATION_PLAN_FINGERPRINT_RULE_VERSION
                ),
            }
        else:
            resolved_contract = {
                "breaking_contract_version": (
                    LEGACY_JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION
                ),
                "ai_schema_version": LEGACY_JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
                "plan_schema_version": LEGACY_JOB_EVALUATION_PLAN_SCHEMA_VERSION,
                "source_unit_rule_version": (
                    LEGACY_JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION
                ),
            }
        contract_keys = [
            "breaking_contract_version",
            "ai_schema_version",
            "plan_schema_version",
            "source_unit_rule_version",
        ]
        if snapshot.schema_version in {"3.0", "4.0"}:
            contract_keys.append("fingerprint_rule_version")
        try:
            breaking_contract = {
                key: resolved_contract[key]
                for key in contract_keys
                if isinstance(resolved_contract[key], str)
                and resolved_contract[key].strip()
            }
        except KeyError:
            breaking_contract = {}
        if len(breaking_contract) != len(contract_keys):
            raise JobEvaluationPlanContentError(
                "岗位评价计划破坏性合同版本不完整",
                code="JOB_EVALUATION_PLAN_CONFIGURATION_ERROR",
            )
        fingerprint_payload = (
            {"jd_fingerprint": self.fingerprint_snapshot(snapshot)}
            if snapshot.schema_version in {"3.0", "4.0"}
            else {"input_snapshot": snapshot.model_dump(mode="json")}
        )
        serialized = json.dumps(
            {**fingerprint_payload, "breaking_contract": breaking_contract},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def build_plan_content(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
        raw_content: str,
    ) -> GeneratedPlanContent:
        try:
            payload = json.loads(raw_content)
            extracted = AIExtractedEvaluationPlan.model_validate(payload)
            if snapshot.schema_version == "3.0":
                if not isinstance(extracted, AIExtractedEvaluationPlanV3):
                    raise ValueError("3.0 input 必须对应 3.0 AI 输出")
                return self._build_v3_plan_content(snapshot, extracted)
            requirements = LegacyEvaluationPlanRequirements.model_validate(
                snapshot.requirements
            )
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanContentError(
                "DeepSeek 返回内容未通过岗位评价计划 Schema 校验"
            ) from None

        candidates, coverage_sources = self._build_structured_candidates(requirements)
        if isinstance(extracted, AIExtractedEvaluationPlanV2):
            free_text_coverage = self._apply_source_reviews(
                snapshot,
                extracted,
                candidates,
            )
        else:
            self._apply_legacy_extracted_items(snapshot, extracted.items, candidates)
            free_text_coverage = None

        return self._finalize_plan_content(
            candidates,
            coverage_sources,
            requirements,
            free_text_coverage=free_text_coverage,
        )

    def _build_v3_plan_content(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
        extracted: AIExtractedEvaluationPlanV3,
    ) -> GeneratedPlanContent:
        source_units = list(snapshot.source_units or [])
        expected_ids = [unit.source_unit_id for unit in source_units]
        review_ids = [review.source_unit_id for review in extracted.source_reviews]
        if len(review_ids) != len(set(review_ids)):
            self._raise_business_validation("AI 重复审阅了同一个 source unit")
        if review_ids and set(review_ids) != set(expected_ids):
            self._raise_business_validation("AI 遗漏或伪造了 source unit")
        if len(review_ids) != len(expected_ids):
            self._raise_business_validation("AI 未完整审阅全部 source units")

        candidates: list[JobEvaluationItem] = []
        unit_item_keys: dict[str, list[str]] = {source_id: [] for source_id in expected_ids}
        priority_conflict_ids: list[str] = []
        misplaced_ids: list[str] = []
        review_by_id = {
            review.source_unit_id: review for review in extracted.source_reviews
        }

        for source_unit in source_units:
            review = review_by_id[source_unit.source_unit_id]
            if self._has_v3_priority_conflict(source_unit):
                priority_conflict_ids.append(source_unit.source_unit_id)
            if review.disposition == "non_evaluation":
                if self._is_obvious_dropped_requirement(source_unit):
                    self._raise_business_validation("AI 把明确岗位要求误判为非评价内容")
                if review.non_evaluation_reason in {
                    "company_info",
                    "benefit",
                    "promotion",
                    "recruitment_process",
                    "candidate_note",
                }:
                    misplaced_ids.append(source_unit.source_unit_id)
                continue

            for extracted_item in review.items:
                if extracted_item.source_quote not in source_unit.source_text:
                    self._raise_business_validation("AI source_quote 不是来源片段的连续原文")
                if not self._v3_title_supported(
                    extracted_item.title,
                    extracted_item.source_quote,
                ):
                    self._raise_business_validation("AI 事项标题添加了原文没有的要求")
                source = JobEvaluationItemSource(
                    source_field=source_unit.source_field,
                    source_unit_id=source_unit.source_unit_id,
                    source_quote=extracted_item.source_quote,
                )
                provisional = JobEvaluationItem(
                    key=self._item_key(extracted_item.category, extracted_item.title),
                    title=extracted_item.title,
                    category=extracted_item.category,
                    priority=self._priority_from_v3_field(source_unit.source_field),
                    sources=[source],
                )
                existing = self._find_v3_duplicate(candidates, provisional)
                if existing is None:
                    candidates.append(provisional)
                    kept_key = provisional.key
                else:
                    sources = list(existing.sources or [])
                    if source not in sources:
                        sources.append(source)
                    priority = existing.priority
                    incoming_priority = provisional.priority
                    if self._PRIORITY_RANK[incoming_priority] > self._PRIORITY_RANK[priority]:
                        priority = incoming_priority
                    existing_index = candidates.index(existing)
                    candidates[existing_index] = existing.model_copy(
                        update={"priority": priority, "sources": sources}
                    )
                    kept_key = existing.key
                self._append_unique(
                    unit_item_keys[source_unit.source_unit_id],
                    kept_key,
                )

        if not candidates:
            raise JobEvaluationPlanContentError(
                "没有识别到可评价的岗位要求",
                code="JOB_EVALUATION_PLAN_NO_ITEMS",
            )
        if len(candidates) > JOB_EVALUATION_PLAN_MAX_ITEMS:
            raise JobEvaluationPlanContentError(
                "评价事项超过 30 项，请精简或调整 JD",
                code="JOB_EVALUATION_PLAN_TOO_MANY_ITEMS",
            )

        key_map: dict[str, str] = {}
        items: list[JobEvaluationItem] = []
        for index, candidate in enumerate(candidates, start=1):
            final_key = f"item:{index:04d}"
            key_map[candidate.key] = final_key
            items.append(candidate.model_copy(update={"key": final_key}))

        summary_units: list[JobEvaluationPlanSourceReviewUnit] = []
        for source_unit in source_units:
            review = review_by_id[source_unit.source_unit_id]
            summary_units.append(
                JobEvaluationPlanSourceReviewUnit(
                    source_unit_id=source_unit.source_unit_id,
                    disposition=review.disposition,
                    non_evaluation_reason=review.non_evaluation_reason,
                    item_keys=[
                        key_map[key]
                        for key in unit_item_keys[source_unit.source_unit_id]
                    ],
                )
            )
        evaluation_units = sum(
            unit.disposition == "evaluation" for unit in summary_units
        )
        source_review_summary = JobEvaluationPlanSourceReviewSummary(
            rule_version=JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
            total_units=len(source_units),
            reviewed_units=len(summary_units),
            evaluation_units=evaluation_units,
            non_evaluation_units=len(summary_units) - evaluation_units,
            all_reviewed=True,
            units=summary_units,
        )

        warnings: list[JobEvaluationPlanWarningDetail] = []
        if len(items) <= 4:
            warnings.append(
                JobEvaluationPlanWarningDetail(
                    code=JobEvaluationPlanWarningCode.LIMITED_BASIS,
                    message=f"当前计划只有 {len(items)} 项评价事项，评价依据有限",
                    source_unit_ids=[],
                )
            )
        if priority_conflict_ids:
            warnings.append(
                JobEvaluationPlanWarningDetail(
                    code=JobEvaluationPlanWarningCode.PRIORITY_SIGNAL_CONFLICT,
                    message="原文强弱措辞与所在字段不一致，已保留字段固定优先级",
                    source_unit_ids=priority_conflict_ids,
                )
            )
        if misplaced_ids:
            warnings.append(
                JobEvaluationPlanWarningDetail(
                    code=JobEvaluationPlanWarningCode.MISPLACED_NON_EVALUATION_CONTENT,
                    message="评价字段包含未生成事项的宣传、福利或流程内容",
                    source_unit_ids=misplaced_ids,
                )
            )
        return GeneratedPlanContent(
            items=items,
            structured_coverage=None,
            warnings=warnings,
            source_review_summary=source_review_summary,
        )

    @staticmethod
    def _priority_from_v3_field(source_field: str) -> EvaluationItemPriority:
        return {
            "candidate_requirements": EvaluationItemPriority.REQUIRED,
            "preferred_qualifications": EvaluationItemPriority.PREFERRED,
            "job_responsibilities": EvaluationItemPriority.GENERAL,
        }[source_field]

    def _find_v3_duplicate(
        self,
        candidates: list[JobEvaluationItem],
        incoming: JobEvaluationItem,
    ) -> JobEvaluationItem | None:
        incoming_title = self._v3_dedup_text(incoming.title)
        for existing in candidates:
            if (
                existing.category is incoming.category
                and self._v3_dedup_text(existing.title) == incoming_title
            ):
                return existing
        return None

    @staticmethod
    def _v3_dedup_text(value: str) -> str:
        return re.sub(r"[^a-z0-9+#.\u4e00-\u9fff]", "", value.lower())

    def _v3_title_supported(self, title: str, quote: str) -> bool:
        title_ascii = set(re.findall(r"[a-z][a-z0-9+#.]*", title.lower()))
        quote_ascii = set(re.findall(r"[a-z][a-z0-9+#.]*", quote.lower()))
        if not title_ascii.issubset(quote_ascii):
            return False
        title_years = set(re.findall(r"(?:\d+|[一二三四五六七八九十]+)年", title))
        quote_years = set(re.findall(r"(?:\d+|[一二三四五六七八九十]+)年", quote))
        if not title_years.issubset(quote_years):
            return False
        for force_term in ("必须", "至少", "硬性要求", "required", "must"):
            if force_term in title.lower() and force_term not in quote.lower():
                return False
        return self._title_supported(title, quote)

    def _has_v3_priority_conflict(self, source_unit: JobEvaluationPlanSourceUnit) -> bool:
        signaled = self._priority_from_quote(source_unit.source_text)
        fixed = self._priority_from_v3_field(source_unit.source_field)
        return signaled is not EvaluationItemPriority.GENERAL and signaled is not fixed

    def _is_obvious_dropped_requirement(
        self,
        source_unit: JobEvaluationPlanSourceUnit,
    ) -> bool:
        text = self._strip_source_unit_formatting(source_unit.source_text)
        lowered = text.lower()
        if any(
            marker in text
            for marker in ("我们提供", "公司提供", "团队负责为员工", "福利", "下午茶")
        ):
            return False
        if source_unit.source_field == "job_responsibilities":
            return re.match(
                r"^(?:负责|主导|参与|设计|开发|维护|优化|推动|管理|分析|搭建|支持)",
                text,
            ) is not None
        if source_unit.source_field == "preferred_qualifications":
            return any(term in lowered for term in self._PREFERRED_TERMS)
        return (
            any(term in lowered for term in self._REQUIRED_TERMS if term != "需")
            or re.search(r"(?:具备|熟悉|掌握|能够|经验|学历)", text) is not None
        )

    def _apply_legacy_extracted_items(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
        extracted_items: list[AIExtractedEvaluationItem],
        candidates: list[_CandidateItem],
    ) -> None:
        source_text = self._snapshot_source_text(snapshot)
        for extracted_item in extracted_items:
            if self._is_promotional(extracted_item):
                continue
            if extracted_item.source_quote not in source_text:
                raise JobEvaluationPlanContentError(
                    "AI 评价事项无法追溯到 JD 原文",
                    code="JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED",
                )
            for split_item in self._split_ai_item(extracted_item):
                if not self._title_supported(split_item.title, split_item.source_quote):
                    raise JobEvaluationPlanContentError(
                        "AI 评价事项添加了 JD 未提出的要求",
                        code="JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED",
                    )
                item = JobEvaluationItem(
                    key=self._item_key(split_item.category, split_item.title),
                    title=split_item.title,
                    category=split_item.category,
                    priority=self._priority_from_quote(split_item.source_quote),
                    source_type=EvaluationItemSourceType.AI_EXTRACTED,
                    source_field=None,
                    source_quote=split_item.source_quote,
                )
                self._merge_candidate(candidates, _CandidateItem(item, []))

    def _apply_source_reviews(
        self,
        snapshot: JobEvaluationPlanInputSnapshot,
        extracted: AIExtractedEvaluationPlanV2,
        candidates: list[_CandidateItem],
    ) -> dict[str, Any]:
        source_units = self.build_description_source_units(snapshot.description)
        expected_ids = [unit.source_id for unit in source_units]
        review_by_id: dict[str, Any] = {}
        for review in extracted.source_reviews:
            if review.source_id in review_by_id:
                self._raise_business_validation("AI 重复审阅了同一个 JD 原文片段")
            review_by_id[review.source_id] = review
        if set(review_by_id) != set(expected_ids) or len(review_by_id) != len(
            expected_ids
        ):
            self._raise_business_validation("AI 未完整审阅指定的 JD 原文片段")

        structured_by_key = {candidate.item.key: candidate for candidate in candidates}
        coverage_units: list[dict[str, Any]] = []
        for source_unit in source_units:
            review = review_by_id[source_unit.source_id]
            if (
                review.disposition == "non_requirement"
                and self._has_requirement_signal(source_unit.source_text)
            ):
                self._raise_business_validation("AI 把明确岗位要求误判为非要求内容")

            item_keys: list[str] = []
            equivalent_keys: list[str] = []
            for reviewed_item in review.items:
                if reviewed_item.title not in source_unit.source_text:
                    self._raise_business_validation("AI 评价事项不是来源片段的连续原文")
                if self._is_promotional_text(reviewed_item.title):
                    self._raise_business_validation("AI 把宣传或福利内容识别成了评价事项")

                ai_item = JobEvaluationItem(
                    key=self._item_key(reviewed_item.category, reviewed_item.title),
                    title=reviewed_item.title,
                    category=reviewed_item.category,
                    priority=self._priority_from_quote(source_unit.source_text),
                    source_type=EvaluationItemSourceType.AI_EXTRACTED,
                    source_field="description",
                    source_quote=source_unit.source_text,
                )
                equivalent_key = reviewed_item.equivalent_structured_item_key
                if equivalent_key is not None:
                    equivalent = structured_by_key.get(equivalent_key)
                    if (
                        equivalent is None
                        or equivalent.item.category is not reviewed_item.category
                    ):
                        self._raise_business_validation(
                            "AI 引用了未知或跨类别的结构化评价事项"
                        )
                    kept_key = equivalent.item.key
                    self._append_unique(equivalent_keys, kept_key)
                else:
                    existing = self._find_conservative_match(candidates, ai_item)
                    if existing is None:
                        candidates.append(_CandidateItem(ai_item, []))
                        kept_key = ai_item.key
                    else:
                        kept_key = existing.item.key
                        if (
                            existing.item.source_type
                            is EvaluationItemSourceType.AI_EXTRACTED
                            and self._PRIORITY_RANK[ai_item.priority]
                            > self._PRIORITY_RANK[existing.item.priority]
                        ):
                            existing.item = ai_item
                            kept_key = ai_item.key
                self._append_unique(item_keys, kept_key)

            coverage_units.append(
                {
                    "source_id": source_unit.source_id,
                    "disposition": review.disposition,
                    "item_keys": item_keys,
                    "equivalent_structured_item_keys": equivalent_keys,
                }
            )

        try:
            coverage = JobEvaluationPlanFreeTextCoverage.model_validate(
                {
                    "rule_version": LEGACY_JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
                    "all_reviewed": True,
                    "units": coverage_units,
                }
            )
        except ValidationError:
            raise JobEvaluationPlanContentError(
                "自由文本覆盖审计未通过 Schema 校验",
                code="JOB_EVALUATION_PLAN_INCOMPLETE_FREE_TEXT_COVERAGE",
            ) from None
        return coverage.model_dump(mode="json")

    def _finalize_plan_content(
        self,
        candidates: list[_CandidateItem],
        coverage_sources: list[tuple[str, list[str]]],
        requirements: LegacyEvaluationPlanRequirements,
        *,
        free_text_coverage: dict[str, Any] | None,
    ) -> GeneratedPlanContent:
        items = [candidate.item for candidate in candidates]
        if not items:
            raise JobEvaluationPlanContentError(
                "没有识别到可评价的岗位要求",
                code="JOB_EVALUATION_PLAN_NO_ITEMS",
            )
        if len(items) > JOB_EVALUATION_PLAN_MAX_ITEMS:
            raise JobEvaluationPlanContentError(
                "评价事项超过 30 项，请精简或调整 JD",
                code="JOB_EVALUATION_PLAN_TOO_MANY_ITEMS",
            )
        if len({item.key for item in items}) != len(items):
            raise JobEvaluationPlanContentError(
                "评价事项存在未解决的重复项",
                code="JOB_EVALUATION_PLAN_DUPLICATE_ITEMS",
            )

        final_keys = {item.key for item in items}
        coverage_fields: list[StructuredFieldCoverage] = []
        for source_field, keys in coverage_sources:
            resolved_keys = [self._resolve_merged_key(candidates, key) for key in keys]
            if any(key not in final_keys for key in resolved_keys):
                raise JobEvaluationPlanContentError(
                    "结构化岗位要求未被完整补齐",
                    code="JOB_EVALUATION_PLAN_INCOMPLETE_STRUCTURED_COVERAGE",
                )
            coverage_fields.append(
                StructuredFieldCoverage(
                    source_field=source_field,
                    source_value_count=len(keys),
                    item_keys=resolved_keys,
                )
            )
        coverage = StructuredCoverageResult(
            source_schema_version=requirements.schema_version,
            fields=coverage_fields,
            all_covered=True,
        )
        warnings = (
            [JobEvaluationPlanWarning.LIMITED_BASIS]
            if len(items) <= 4
            else []
        )
        return GeneratedPlanContent(
            items=items,
            structured_coverage=coverage,
            warnings=warnings,
            free_text_coverage=free_text_coverage,
        )

    def _find_conservative_match(
        self,
        candidates: list[_CandidateItem],
        incoming: JobEvaluationItem,
    ) -> _CandidateItem | None:
        incoming_text = self._semantic_text(incoming.title)
        for existing in candidates:
            if existing.item.category is not incoming.category:
                continue
            if self._semantic_text(existing.item.title) == incoming_text:
                return existing
        return None

    def _has_requirement_signal(self, value: str) -> bool:
        if self._priority_from_quote(value) is not EvaluationItemPriority.GENERAL:
            return True
        return self._REQUIREMENT_ACTION_RE.search(value) is not None

    def _is_promotional_text(self, value: str) -> bool:
        return any(term in value for term in self._PROMOTION_TERMS)

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _raise_business_validation(message: str) -> None:
        raise JobEvaluationPlanContentError(
            message,
            code="JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED",
        )

    def _build_structured_candidates(
        self,
        requirements: LegacyEvaluationPlanRequirements,
    ) -> tuple[list[_CandidateItem], list[tuple[str, list[str]]]]:
        candidates: list[_CandidateItem] = []
        coverage: list[tuple[str, list[str]]] = []

        def add_values(
            source_field: str,
            values: list[str],
            category: EvaluationItemCategory,
            priority: EvaluationItemPriority,
        ) -> None:
            source_keys: list[str] = []
            for value in values:
                key = self._item_key(category, value)
                item = JobEvaluationItem(
                    key=key,
                    title=value,
                    category=category,
                    priority=priority,
                    source_type=EvaluationItemSourceType.STRUCTURED,
                    source_field=source_field,
                    source_quote=None,
                )
                kept_key = self._merge_candidate(
                    candidates,
                    _CandidateItem(item, [source_field]),
                )
                source_keys.append(kept_key)
            coverage.append((source_field, source_keys))

        add_values(
            "requirements.responsibilities",
            requirements.responsibilities,
            EvaluationItemCategory.RESPONSIBILITY,
            EvaluationItemPriority.GENERAL,
        )
        add_values(
            "requirements.required_skills",
            requirements.required_skills,
            EvaluationItemCategory.SKILL,
            EvaluationItemPriority.REQUIRED,
        )
        add_values(
            "requirements.preferred_skills",
            requirements.preferred_skills,
            EvaluationItemCategory.SKILL,
            EvaluationItemPriority.PREFERRED,
        )
        years = (
            []
            if requirements.minimum_work_years is None
            else [
                "工作经验不限"
                if requirements.minimum_work_years == 0
                else f"至少 {requirements.minimum_work_years} 年工作经验"
            ]
        )
        add_values(
            "requirements.minimum_work_years",
            years,
            EvaluationItemCategory.EXPERIENCE,
            (
                EvaluationItemPriority.GENERAL
                if requirements.minimum_work_years == 0
                else EvaluationItemPriority.REQUIRED
            ),
        )
        education_value = (
            getattr(requirements.education_requirement, "value", None)
            if requirements.education_requirement is not None
            else None
        )
        education = (
            [] if education_value is None else [self._EDUCATION_LABELS[education_value]]
        )
        add_values(
            "requirements.education_requirement",
            education,
            EvaluationItemCategory.EDUCATION,
            (
                EvaluationItemPriority.GENERAL
                if education_value == "none"
                else EvaluationItemPriority.REQUIRED
            ),
        )
        add_values(
            "requirements.required_experiences",
            requirements.required_experiences,
            EvaluationItemCategory.EXPERIENCE,
            EvaluationItemPriority.REQUIRED,
        )
        add_values(
            "requirements.preferred_experiences",
            requirements.preferred_experiences,
            EvaluationItemCategory.EXPERIENCE,
            EvaluationItemPriority.PREFERRED,
        )
        add_values(
            "requirements.keywords",
            requirements.keywords,
            EvaluationItemCategory.OTHER,
            EvaluationItemPriority.GENERAL,
        )
        add_values(
            "requirements.additional_requirements",
            requirements.additional_requirements,
            EvaluationItemCategory.OTHER,
            EvaluationItemPriority.GENERAL,
        )
        return candidates, coverage

    def _merge_candidate(
        self,
        candidates: list[_CandidateItem],
        incoming: _CandidateItem,
    ) -> str:
        for existing in candidates:
            if not self._semantically_equal(existing.item, incoming.item):
                continue
            existing.source_fields.extend(
                field
                for field in incoming.source_fields
                if field not in existing.source_fields
            )
            if (
                self._PRIORITY_RANK[incoming.item.priority]
                > self._PRIORITY_RANK[existing.item.priority]
            ):
                existing.item = existing.item.model_copy(
                    update={"priority": incoming.item.priority}
                )
            return existing.item.key
        candidates.append(incoming)
        return incoming.item.key

    @staticmethod
    def _resolve_merged_key(candidates: list[_CandidateItem], key: str) -> str:
        if any(candidate.item.key == key for candidate in candidates):
            return key
        return key

    def _semantically_equal(
        self,
        left: JobEvaluationItem,
        right: JobEvaluationItem,
    ) -> bool:
        if left.category is not right.category:
            return False
        left_value = self._semantic_text(left.title)
        right_value = self._semantic_text(right.title)
        if left_value == right_value:
            return True
        shorter, longer = sorted((left_value, right_value), key=len)
        if len(shorter) >= 5 and shorter in longer:
            return True
        left_tokens = set(re.findall(r"[a-z0-9+#.]+", left.title.lower()))
        right_tokens = set(re.findall(r"[a-z0-9+#.]+", right.title.lower()))
        return bool(left_tokens and left_tokens == right_tokens)

    def _split_ai_item(
        self,
        item: AIExtractedEvaluationItem,
    ) -> list[AIExtractedEvaluationItem]:
        if item.category is not EvaluationItemCategory.SKILL:
            return [item]
        parts = [
            part.strip()
            for part in re.split(r"(?:、|，|,|\s+和\s+|\s+及\s+)", item.title)
            if part.strip()
        ]
        if len(parts) <= 1 or any(part not in item.source_quote for part in parts):
            return [item]
        return [item.model_copy(update={"title": part}) for part in parts]

    def _priority_from_quote(self, quote: str) -> EvaluationItemPriority:
        lowered = quote.lower()
        has_required_term = any(
            term != "需" and term in lowered for term in self._REQUIRED_TERMS
        ) or re.search(r"需(?!求)", lowered) is not None
        if has_required_term:
            return EvaluationItemPriority.REQUIRED
        if any(term in lowered for term in self._PREFERRED_TERMS):
            return EvaluationItemPriority.PREFERRED
        return EvaluationItemPriority.GENERAL

    def _is_promotional(self, item: AIExtractedEvaluationItem) -> bool:
        combined = f"{item.title}\n{item.source_quote}"
        return any(term in combined for term in self._PROMOTION_TERMS)

    def _title_supported(self, title: str, quote: str) -> bool:
        title_value = self._semantic_text(title)
        quote_value = self._semantic_text(quote)
        if title_value and title_value in quote_value:
            return True
        title_ascii = set(re.findall(r"[a-z0-9+#.]{2,}", title.lower()))
        quote_ascii = set(re.findall(r"[a-z0-9+#.]{2,}", quote.lower()))
        if title_ascii and title_ascii.intersection(quote_ascii):
            return True
        title_chinese = set(re.findall(r"[\u4e00-\u9fff]", title_value))
        quote_chinese = set(re.findall(r"[\u4e00-\u9fff]", quote_value))
        return len(title_chinese.intersection(quote_chinese)) >= min(
            2,
            len(title_chinese),
        )

    def _semantic_text(self, value: str) -> str:
        normalized = value.lower()
        for term in self._GENERIC_TITLE_TERMS:
            normalized = normalized.replace(term, "")
        return re.sub(r"[^a-z0-9+#.\u4e00-\u9fff]", "", normalized)

    def _item_key(
        self,
        category: EvaluationItemCategory,
        title: str,
    ) -> str:
        semantic = self._semantic_text(title) or title.strip().lower()
        digest = hashlib.sha256(semantic.encode("utf-8")).hexdigest()[:16]
        return f"requirement:{category.value}:{digest}"

    @staticmethod
    def _snapshot_source_text(snapshot: JobEvaluationPlanInputSnapshot) -> str:
        values: list[str] = [snapshot.title]
        if snapshot.department:
            values.append(snapshot.department)
        if snapshot.description:
            values.append(snapshot.description)

        def collect(value: Any) -> None:
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)

        collect(snapshot.requirements.model_dump(mode="json"))
        return "\n".join(values)

    async def _save_success(
        self,
        db: AsyncSession,
        plan_id: int,
        input_fingerprint: str,
        content: GeneratedPlanContentV4,
        *,
        model_version: str,
        completed_at: datetime,
    ) -> JobEvaluationPlan:
        """Persist a complete 4.0 result as pending_confirmation, never ready."""
        try:
            plan = await self._get_locked_plan(db, plan_id)
            if plan is None:
                raise JobEvaluationPlanNotFoundError("评价计划不存在")
            job = await self._get_locked_job(db, plan.job_id)
            if plan.status != JobEvaluationPlanStatus.GENERATING.value:
                await db.commit()
                await db.refresh(plan)
                return plan
            if (
                job is None
                or self.fingerprint_input(self.build_v4_input_snapshot(job))
                != input_fingerprint
                or plan.input_fingerprint != input_fingerprint
                or plan.schema_version != "4.0"
                or not plan.is_current
            ):
                plan.status = JobEvaluationPlanStatus.OUTDATED.value
                plan.is_current = False
                plan.completed_at = completed_at
                await db.commit()
                await db.refresh(plan)
                return plan

            plan.status = "pending_confirmation"
            plan.items = null()
            plan.structured_coverage = null()
            plan.free_text_coverage = null()
            plan.requirement_facts = [
                fact.model_dump(mode="json") for fact in content.requirement_facts
            ]
            plan.evaluation_criteria = [
                criterion.model_dump(mode="json")
                for criterion in content.evaluation_criteria
            ]
            plan.source_review_summary = content.source_review_summary.model_dump(
                mode="json"
            )
            plan.coverage_review_summary = (
                content.coverage_review_summary.model_dump(mode="json")
            )
            plan.generation_audit = content.generation_audit.model_dump(mode="json")
            plan.warnings = [
                warning.model_dump(mode="json") for warning in content.warnings
            ]
            plan.prompt_version = V4_PROMPT_VERSIONS["fact_extraction"]
            plan.model_version = model_version
            plan.schema_version = JOB_EVALUATION_PLAN_V4_SCHEMA_VERSION
            plan.error_code = None
            plan.error_message = None
            plan.completed_at = completed_at
            await db.commit()
            await db.refresh(plan)
            return plan
        except BaseException:
            await db.rollback()
            raise

    async def _save_legacy_success(
        self,
        db: AsyncSession,
        plan_id: int,
        input_fingerprint: str,
        content: GeneratedPlanContent,
        *,
        model_version: str,
        completed_at: datetime,
    ) -> JobEvaluationPlan:
        try:
            plan = await self._get_locked_plan(db, plan_id)
            if plan is None:
                raise JobEvaluationPlanNotFoundError("评价计划不存在")
            job = await self._get_locked_job(db, plan.job_id)
            if (
                job is None
                or self.fingerprint_input(self.build_input_snapshot(job))
                != input_fingerprint
                or plan.input_fingerprint != input_fingerprint
                or not plan.is_current
            ):
                plan.status = JobEvaluationPlanStatus.OUTDATED.value
                plan.is_current = False
                plan.completed_at = completed_at
                await db.commit()
                await db.refresh(plan)
                return plan

            plan.status = JobEvaluationPlanStatus.READY.value
            plan.items = [item.model_dump(mode="json") for item in content.items]
            plan.structured_coverage = (
                content.structured_coverage.model_dump(mode="json")
                if content.structured_coverage is not None
                else null()
            )
            plan.free_text_coverage = (
                content.free_text_coverage
                if content.free_text_coverage is not None
                else null()
            )
            plan.source_review_summary = (
                content.source_review_summary.model_dump(mode="json")
                if content.source_review_summary is not None
                else null()
            )
            plan.warnings = [
                warning.model_dump(mode="json")
                if isinstance(warning, JobEvaluationPlanWarningDetail)
                else warning.value
                for warning in content.warnings
            ]
            plan.model_version = model_version
            plan.error_code = None
            plan.error_message = None
            plan.completed_at = completed_at
            await db.commit()
            await db.refresh(plan)
            return plan
        except BaseException:
            await db.rollback()
            raise

    async def _save_failure(
        self,
        db: AsyncSession,
        plan_id: int,
        input_fingerprint: str,
        *,
        code: str,
        message: str,
        completed_at: datetime,
    ) -> JobEvaluationPlan:
        try:
            plan = await self._get_locked_plan(db, plan_id)
            if plan is None:
                raise JobEvaluationPlanNotFoundError("评价计划不存在")
            job = await self._get_locked_job(db, plan.job_id)
            current_snapshot = (
                self.build_v4_input_snapshot(job)
                if job is not None and plan.schema_version == "4.0"
                else self.build_input_snapshot(job)
                if job is not None
                else None
            )
            if plan.status != JobEvaluationPlanStatus.GENERATING.value:
                await db.commit()
                await db.refresh(plan)
                return plan
            if (
                job is None
                or current_snapshot is None
                or self.fingerprint_input(current_snapshot) != input_fingerprint
                or plan.input_fingerprint != input_fingerprint
                or not plan.is_current
            ):
                plan.status = JobEvaluationPlanStatus.OUTDATED.value
                plan.is_current = False
            else:
                plan.status = JobEvaluationPlanStatus.FAILED.value
                plan.items = null() if plan.schema_version == "4.0" else []
                plan.source_review_summary = null()
                if plan.schema_version in {"3.0", "4.0"}:
                    plan.structured_coverage = null()
                    plan.free_text_coverage = null()
                if plan.schema_version == "4.0":
                    plan.requirement_facts = null()
                    plan.evaluation_criteria = null()
                    plan.coverage_review_summary = null()
                    plan.generation_audit = null()
                plan.warnings = []
                plan.error_code = code
                plan.error_message = message[:500]
            plan.completed_at = completed_at
            await db.commit()
            await db.refresh(plan)
            return plan
        except BaseException:
            await db.rollback()
            raise

    @staticmethod
    async def _get_locked_job(db: AsyncSession, job_id: int) -> Job | None:
        return await db.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    @staticmethod
    async def _get_locked_plan(
        db: AsyncSession,
        plan_id: int,
    ) -> JobEvaluationPlan | None:
        return await db.scalar(
            select(JobEvaluationPlan)
            .where(JobEvaluationPlan.id == plan_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def _validate_configuration(settings: Settings) -> None:
        if not settings.JOB_EVALUATION_PLAN_ENABLED:
            raise JobEvaluationPlanDisabledError("岗位评价计划功能当前未启用")
        versions = (
            settings.JOB_EVALUATION_PLAN_PROMPT_VERSION,
            settings.JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
            settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION,
        )
        current_versions = (
            JOB_EVALUATION_PLAN_PROMPT_VERSION,
            JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
            JOB_EVALUATION_PLAN_SCHEMA_VERSION,
        )
        legacy_versions = (
            LEGACY_JOB_EVALUATION_PLAN_PROMPT_VERSION,
            LEGACY_JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
            LEGACY_JOB_EVALUATION_PLAN_SCHEMA_VERSION,
        )
        if versions not in {current_versions, legacy_versions}:
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 Prompt、AI Schema 与计划 Schema 版本组合不一致"
            )

    @staticmethod
    def _safe_adapter_message(exc: JobEvaluationPlanAdapterError) -> str:
        if exc.retryable:
            return "模型服务暂时不可用，已自动重试一次，请稍后重新生成"
        messages = {
            "JOB_EVALUATION_PLAN_CONFIGURATION_ERROR": "模型服务配置不完整，请联系管理员",
            "JOB_EVALUATION_PLAN_INPUT_ERROR": "岗位评价计划模型输入不合法",
            "JOB_EVALUATION_PLAN_AUTHENTICATION_ERROR": "模型服务认证或授权失败，请联系管理员",
            "JOB_EVALUATION_PLAN_QUOTA_ERROR": "模型服务余额或配额不足，请联系管理员",
            "JOB_EVALUATION_PLAN_EMPTY_RESPONSE": "模型服务没有返回可用内容",
            "JOB_EVALUATION_PLAN_RESPONSE_INTERRUPTED": "模型输出未完整结束，请重新生成",
            "JOB_EVALUATION_PLAN_INVALID_RESPONSE": "模型输出未通过安全格式校验",
            "JOB_EVALUATION_PLAN_UPSTREAM_ERROR": "模型服务返回了不可用结果",
        }
        return messages.get(exc.code, "岗位评价计划模型调用失败")

    @staticmethod
    def _empty_coverage() -> dict[str, Any]:
        return {
            "source_schema_version": "1.0",
            "fields": [],
            "all_covered": True,
        }

    @staticmethod
    def _aware_time(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise JobEvaluationPlanServiceError("评价计划时钟必须包含时区")
        return value


job_evaluation_plan_service = JobEvaluationPlanService()
