from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy import null, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.job_evaluation_plan import (
    DeepSeekJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
)
from app.core.config import Settings, get_settings
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.prompts.job_evaluation_plan import JOB_EVALUATION_PLAN_PROMPT_VERSION
from app.schemas.job import JobRequirementsV1
from app.schemas.job_evaluation_plan import (
    AIExtractedEvaluationItem,
    AIExtractedEvaluationPlan,
    AIExtractedEvaluationPlanV2,
    JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION,
    JOB_EVALUATION_PLAN_MAX_ITEMS,
    JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
    EvaluationItemCategory,
    EvaluationItemPriority,
    EvaluationItemSourceType,
    JobEvaluationPlanAIInput,
    JobEvaluationItem,
    JobEvaluationPlanFreeTextCoverage,
    JobEvaluationPlanInputSnapshot,
    JobEvaluationPlanRead,
    JobEvaluationPlanStatus,
    JobEvaluationPlanWarning,
    StructuredCoverageResult,
    StructuredFieldCoverage,
)


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


class JobEvaluationPlanContentError(JobEvaluationPlanServiceError):
    code = "JOB_EVALUATION_PLAN_INVALID_MODEL_OUTPUT"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        if code is not None:
            self.code = code
        super().__init__(message)


class JobEvaluationPlanAdapter(Protocol):
    async def extract(
        self,
        extraction_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult: ...


@dataclass(frozen=True, slots=True)
class GeneratedPlanContent:
    items: list[JobEvaluationItem]
    structured_coverage: StructuredCoverageResult
    warnings: list[JobEvaluationPlanWarning]
    free_text_coverage: dict[str, Any] | None = None


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

    def is_contract_outdated(self, plan: JobEvaluationPlan) -> bool:
        """Compare a stored plan with the current extraction contract without writes."""
        if (
            plan.prompt_version != JOB_EVALUATION_PLAN_PROMPT_VERSION
            or plan.schema_version != JOB_EVALUATION_PLAN_SCHEMA_VERSION
        ):
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
                await db.rollback()
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
            if content.free_text_coverage is None:
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

        return await self._save_success(
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
            items=[],
            structured_coverage=self._empty_coverage(),
            free_text_coverage=null(),
            warnings=[],
            prompt_version=settings.JOB_EVALUATION_PLAN_PROMPT_VERSION,
            model_version=settings.JOB_EVALUATION_PLAN_MODEL,
            schema_version=settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION,
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
        plan.items = []
        plan.structured_coverage = JobEvaluationPlanService._empty_coverage()
        plan.free_text_coverage = null()
        plan.warnings = []
        plan.prompt_version = settings.JOB_EVALUATION_PLAN_PROMPT_VERSION
        plan.model_version = settings.JOB_EVALUATION_PLAN_MODEL
        plan.schema_version = settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION
        plan.jd_fingerprint = jd_fingerprint
        plan.input_fingerprint = input_fingerprint
        plan.input_snapshot = snapshot_payload
        plan.error_code = None
        plan.error_message = None
        plan.completed_at = None

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

    def build_input_snapshot(self, job: Job) -> JobEvaluationPlanInputSnapshot:
        try:
            requirements = JobRequirementsV1.model_validate(job.requirements)
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
        try:
            requirements = JobRequirementsV1.model_validate(snapshot.requirements)
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
        resolved_contract: Mapping[str, str] = contract or {
            "breaking_contract_version": (
                JOB_EVALUATION_PLAN_BREAKING_CONTRACT_VERSION
            ),
            "ai_schema_version": JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
            "plan_schema_version": JOB_EVALUATION_PLAN_SCHEMA_VERSION,
            "source_unit_rule_version": JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
        }
        contract_keys = (
            "breaking_contract_version",
            "ai_schema_version",
            "plan_schema_version",
            "source_unit_rule_version",
        )
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
        serialized = json.dumps(
            {
                "input_snapshot": snapshot.model_dump(mode="json"),
                "breaking_contract": breaking_contract,
            },
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
            requirements = JobRequirementsV1.model_validate(snapshot.requirements)
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
                    "rule_version": JOB_EVALUATION_PLAN_SOURCE_UNIT_RULE_VERSION,
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
        requirements: JobRequirementsV1,
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
        requirements: JobRequirementsV1,
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
            plan.structured_coverage = content.structured_coverage.model_dump(mode="json")
            plan.free_text_coverage = content.free_text_coverage
            plan.warnings = [warning.value for warning in content.warnings]
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
            if (
                job is None
                or self.fingerprint_input(self.build_input_snapshot(job))
                != input_fingerprint
                or plan.input_fingerprint != input_fingerprint
                or not plan.is_current
            ):
                plan.status = JobEvaluationPlanStatus.OUTDATED.value
                plan.is_current = False
            else:
                plan.status = JobEvaluationPlanStatus.FAILED.value
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
            select(Job).where(Job.id == job_id).with_for_update()
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
        )

    @staticmethod
    def _validate_configuration(settings: Settings) -> None:
        if not settings.JOB_EVALUATION_PLAN_ENABLED:
            raise JobEvaluationPlanDisabledError("岗位评价计划功能当前未启用")
        if (
            settings.JOB_EVALUATION_PLAN_PROMPT_VERSION
            != JOB_EVALUATION_PLAN_PROMPT_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 Prompt 版本与当前代码不一致"
            )
        if (
            settings.JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION
            != JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 AI Schema 版本与当前代码不一致"
            )
        if (
            settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION
            != JOB_EVALUATION_PLAN_SCHEMA_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 Schema 版本与当前代码不一致"
            )

    @staticmethod
    def _safe_adapter_message(exc: JobEvaluationPlanAdapterError) -> str:
        if exc.retryable:
            return "模型服务暂时不可用，已自动重试一次，请稍后重新生成"
        return str(exc)[:500]

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
