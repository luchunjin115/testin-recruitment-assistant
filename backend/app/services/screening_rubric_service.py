from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.screening_rubric_generation import (
    DeepSeekRubricGenerationAdapter,
    RubricGenerationAdapterResult,
)
from app.core.config import get_settings
from app.models.activity_log import ActivityLog
from app.models.job import Job
from app.models.job_screening_rubric import JobScreeningRubric
from app.models.screening_result import ScreeningResult
from app.schemas.screening_rubric import (
    RUBRIC_FAIRNESS_RULES_VERSION,
    RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION,
    RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION,
    RUBRIC_SUBCRITERIA_VERSION,
    SCREENING_RUBRIC_SCHEMA_VERSION,
    RubricChangeReasonCode,
    RubricLifecycleStatus,
    RubricGenerationSuggestion,
    RubricModelMetadata,
    RubricSource,
    RubricTemplateKey,
    ScreeningRubricAbandonRequest,
    ScreeningRubricDraftUpdateRequest,
    ScreeningRubricGenerateRequest,
    ScreeningRubricItemAssistRequest,
    ScreeningRubricItemAssistResponse,
    ScreeningRubricPublishContent,
    ScreeningRubricPublishRequest,
    ScreeningRubricReconfirmRequest,
    ScreeningRubricTemplateDraftRequest,
    ScreeningRubricUpdateRequest,
    ScreeningRubricWeights,
    ManualSemanticCriterionInput,
)
from app.prompts.screening_rubric import (
    RUBRIC_GENERATION_PROMPT_VERSION,
    RUBRIC_ITEM_ASSIST_PROMPT_VERSION,
)
from app.prompts.screening_rubric_templates import get_rubric_template


LOCAL_HR_ACTOR_LABEL = "本地 HR（未认证）"


class ScreeningRubricError(ValueError):
    pass


class ScreeningRubricJobNotFoundError(ScreeningRubricError):
    pass


class CurrentScreeningRubricNotFoundError(ScreeningRubricError):
    pass


class ScreeningRubricDraftNotFoundError(ScreeningRubricError):
    pass


class ScreeningRubricDraftAlreadyExistsError(ScreeningRubricError):
    pass


class ScreeningRubricStaleError(ScreeningRubricError):
    pass


class ScreeningRubricPublishValidationError(ScreeningRubricError):
    pass


class ScreeningRubricGenerationInvalidOutputError(ScreeningRubricError):
    pass


class ScreeningRubricGenerationDisabledError(ScreeningRubricError):
    pass


class RubricGenerationAdapter(Protocol):
    async def generate(
        self,
        job_context: Mapping[str, Any],
        template_key: RubricTemplateKey,
    ) -> RubricGenerationAdapterResult: ...

    async def assist_item(
        self,
        job_context: Mapping[str, Any],
        item: ManualSemanticCriterionInput,
    ) -> RubricGenerationAdapterResult: ...


class ScreeningRubricService:
    async def generate_draft(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricGenerateRequest,
        *,
        adapter: RubricGenerationAdapter | None = None,
    ) -> JobScreeningRubric:
        """Generate outside a DB transaction, then recheck and save one draft."""
        try:
            job = await db.get(Job, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            existing = await self._get_draft_rubric(db, job_id, for_update=False)
            if existing is not None and not data.replace_existing:
                raise ScreeningRubricDraftAlreadyExistsError(
                    "岗位已有正在编辑的 Rubric 草稿"
                )
            job_context = self._generation_job_context(job)
            initial_fingerprint = self.build_job_fingerprint(job_context)
        except Exception:
            await db.rollback()
            raise

        # Release the read transaction before waiting on an external model.
        await db.rollback()
        resolved_adapter = adapter or self._build_generation_adapter()
        result = await resolved_adapter.generate(job_context, data.template_key)
        suggestion = self._parse_generation_suggestion(
            result.content,
            expected_template=data.template_key,
        )

        try:
            locked_job = await self._get_job_for_update(db, job_id)
            if locked_job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            current_fingerprint = self.build_job_fingerprint(
                self._generation_job_context(locked_job)
            )
            if current_fingerprint != initial_fingerprint:
                raise ScreeningRubricStaleError(
                    "AI 生成期间岗位内容已变化，本次结果不能保存"
                )

            existing = await self._get_draft_rubric(db, job_id, for_update=True)
            if existing is not None and not data.replace_existing:
                raise ScreeningRubricDraftAlreadyExistsError(
                    "岗位已有正在编辑的 Rubric 草稿"
                )
            if existing is not None:
                existing.status = RubricLifecycleStatus.ABANDONED.value
                existing.abandoned_at = datetime.now(timezone.utc)
                existing.change_reason = RubricChangeReasonCode.DRAFT_ABANDONED.value
                existing.change_detail = "AI 生成新草稿时替换旧草稿"
                await db.flush()

            current = await self._get_current_rubric(db, job_id, for_update=True)
            if current is None:
                raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")
            version = await self._next_version(db, job_id)
            draft = self._build_rubric(
                job_id=job_id,
                version=version,
                weights=ScreeningRubricWeights.model_validate(current.weights),
                semantic_items=[
                    item.model_dump(mode="json")
                    for item in suggestion.semantic_items
                ],
                source=RubricSource.AI_GENERATED,
                template_key=data.template_key,
                status=RubricLifecycleStatus.DRAFT,
                job_fingerprint=initial_fingerprint,
                change_reason=RubricChangeReasonCode.AI_GENERATED_DRAFT,
                change_detail=data.change_detail,
                created_by=LOCAL_HR_ACTOR_LABEL,
                generation_metadata={
                    "model": result.model,
                    "prompt_version": RUBRIC_GENERATION_PROMPT_VERSION,
                    "schema_version": RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "rationale": suggestion.rationale,
                },
            )
            db.add_all(
                [
                    draft,
                    self._activity(
                        job_id,
                        "job_screening_rubric_ai_draft_generated",
                        {
                            "draft_version": version,
                            "template_key": data.template_key.value,
                            "model": result.model,
                            "semantic_item_count": len(suggestion.semantic_items),
                            "replaced_existing": existing is not None,
                            "change_detail": data.change_detail,
                        },
                    ),
                ]
            )
            await db.flush()
            await db.commit()
            await db.refresh(draft)
            return draft
        except Exception:
            await db.rollback()
            raise

    async def assist_manual_item(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricItemAssistRequest,
        *,
        adapter: RubricGenerationAdapter | None = None,
    ) -> ScreeningRubricItemAssistResponse:
        try:
            job = await db.get(Job, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            draft = await self._get_draft_rubric(db, job_id, for_update=False)
            if draft is None:
                raise ScreeningRubricDraftNotFoundError(
                    "请先创建 Rubric 草稿，再使用单项 AI 辅助"
                )
            job_context = self._generation_job_context(job)
            initial_fingerprint = self.build_job_fingerprint(job_context)
            self._ensure_fingerprint(
                draft,
                expected=data.expected_job_fingerprint,
                current=initial_fingerprint,
            )
        except Exception:
            await db.rollback()
            raise

        await db.rollback()
        resolved_adapter = adapter or self._build_generation_adapter()
        result = await resolved_adapter.assist_item(job_context, data.item)
        suggestion = self._parse_assisted_item(result.content)

        try:
            locked_job = await self._get_job_for_update(db, job_id)
            if locked_job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            draft = await self._get_draft_rubric(db, job_id, for_update=True)
            if draft is None:
                raise ScreeningRubricDraftNotFoundError("Rubric 草稿已不存在")
            current_fingerprint = self.build_job_fingerprint(
                self._generation_job_context(locked_job)
            )
            self._ensure_fingerprint(
                draft,
                expected=initial_fingerprint,
                current=current_fingerprint,
            )
            response = ScreeningRubricItemAssistResponse(
                job_fingerprint=current_fingerprint,
                suggestion=suggestion,
                metadata=RubricModelMetadata(
                    model=result.model,
                    prompt_version=RUBRIC_ITEM_ASSIST_PROMPT_VERSION,
                    schema_version=RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                ),
            )
            await db.rollback()
            return response
        except Exception:
            await db.rollback()
            raise

    async def get_current_rubric(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobScreeningRubric:
        job = await db.get(Job, job_id)
        if job is None:
            raise ScreeningRubricJobNotFoundError("岗位不存在")
        rubric = await self._get_current_rubric(db, job_id, for_update=False)
        if rubric is None:
            raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")
        return rubric

    async def get_draft_rubric(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> JobScreeningRubric:
        job = await db.get(Job, job_id)
        if job is None:
            raise ScreeningRubricJobNotFoundError("岗位不存在")
        draft = await self._get_draft_rubric(db, job_id, for_update=False)
        if draft is None:
            raise ScreeningRubricDraftNotFoundError("岗位没有正在编辑的 Rubric 草稿")
        return draft

    async def create_template_draft(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricTemplateDraftRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            existing = await self._get_draft_rubric(db, job_id, for_update=True)
            if existing is not None and not data.replace_existing:
                raise ScreeningRubricDraftAlreadyExistsError("岗位已有正在编辑的 Rubric 草稿")
            if existing is not None:
                existing.status = RubricLifecycleStatus.ABANDONED.value
                existing.abandoned_at = datetime.now(timezone.utc)
                existing.change_reason = RubricChangeReasonCode.DRAFT_ABANDONED.value
                existing.change_detail = "创建新模板草稿时替换旧草稿"
                await db.flush()

            current = await self._get_current_rubric(db, job_id, for_update=True)
            if current is None:
                raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")
            version = await self._next_version(db, job_id)
            template = get_rubric_template(data.template_key)
            fingerprint = self.build_job_fingerprint(self._job_values(job))
            draft = self._build_rubric(
                job_id=job_id,
                version=version,
                weights=ScreeningRubricWeights.model_validate(current.weights),
                semantic_items=[
                    item.model_dump(mode="json") for item in template.semantic_items
                ],
                source=template.source,
                template_key=template.key,
                status=RubricLifecycleStatus.DRAFT,
                job_fingerprint=fingerprint,
                change_reason=RubricChangeReasonCode.TEMPLATE_DRAFT,
                change_detail=data.change_detail,
                created_by=LOCAL_HR_ACTOR_LABEL,
                generation_metadata={"template_version": template.version},
            )
            activity = self._activity(
                job_id,
                "job_screening_rubric_draft_created",
                {
                    "draft_version": version,
                    "template_key": template.key.value,
                    "replaced_existing": existing is not None,
                    "change_detail": data.change_detail,
                },
            )
            db.add_all([draft, activity])
            await db.flush()
            await db.commit()
            await db.refresh(draft)
            return draft
        except Exception:
            await db.rollback()
            raise

    async def update_draft(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricDraftUpdateRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            draft = await self._get_draft_rubric(db, job_id, for_update=True)
            if draft is None:
                raise ScreeningRubricDraftNotFoundError("岗位没有正在编辑的 Rubric 草稿")
            current_fingerprint = self.build_job_fingerprint(self._job_values(job))
            self._ensure_fingerprint(
                draft,
                expected=data.expected_job_fingerprint,
                current=current_fingerprint,
            )

            if data.weights is not None:
                self._apply_weights(draft, data.weights)
            if data.semantic_items is not None:
                draft.semantic_items = [
                    item.model_dump(mode="json") for item in data.semantic_items
                ]
            draft.change_reason = RubricChangeReasonCode.DRAFT_UPDATED.value
            draft.change_detail = data.change_detail

            db.add(
                self._activity(
                    job_id,
                    "job_screening_rubric_draft_updated",
                    {
                        "draft_version": draft.version,
                        "semantic_item_count": len(draft.semantic_items),
                        "change_detail": data.change_detail,
                    },
                )
            )
            await db.commit()
            await db.refresh(draft)
            return draft
        except Exception:
            await db.rollback()
            raise

    async def publish_draft(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricPublishRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            draft = await self._get_draft_rubric(db, job_id, for_update=True)
            if draft is None:
                raise ScreeningRubricDraftNotFoundError("岗位没有正在编辑的 Rubric 草稿")
            current = await self._get_current_rubric(db, job_id, for_update=True)
            if current is None:
                raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")

            current_fingerprint = self.build_job_fingerprint(self._job_values(job))
            self._ensure_fingerprint(
                draft,
                expected=data.expected_job_fingerprint,
                current=current_fingerprint,
            )
            self._validate_publishable(draft)

            current.is_current = False
            current.status = RubricLifecycleStatus.ARCHIVED.value
            await db.flush()

            now = datetime.now(timezone.utc)
            draft.is_current = True
            draft.status = RubricLifecycleStatus.ACTIVE.value
            draft.is_stale = False
            draft.stale_at = None
            draft.stale_reason = None
            draft.change_reason = RubricChangeReasonCode.DRAFT_PUBLISHED.value
            draft.change_detail = data.change_detail
            draft.confirmed_by = LOCAL_HR_ACTOR_LABEL
            draft.confirmed_at = now
            await self._mark_screening_results_outdated(db, job_id, now)
            db.add(
                self._activity(
                    job_id,
                    "job_screening_rubric_draft_published",
                    {
                        "from_version": current.version,
                        "to_version": draft.version,
                        "semantic_item_count": len(draft.semantic_items),
                        "change_detail": data.change_detail,
                    },
                )
            )
            await db.flush()
            await db.commit()
            await db.refresh(draft)
            return draft
        except Exception:
            await db.rollback()
            raise

    async def abandon_draft(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricAbandonRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            draft = await self._get_draft_rubric(db, job_id, for_update=True)
            if draft is None:
                raise ScreeningRubricDraftNotFoundError("岗位没有正在编辑的 Rubric 草稿")
            draft.status = RubricLifecycleStatus.ABANDONED.value
            draft.abandoned_at = datetime.now(timezone.utc)
            draft.change_reason = RubricChangeReasonCode.DRAFT_ABANDONED.value
            draft.change_detail = data.change_detail
            db.add(
                self._activity(
                    job_id,
                    "job_screening_rubric_draft_abandoned",
                    {
                        "draft_version": draft.version,
                        "change_detail": data.change_detail,
                    },
                )
            )
            await db.commit()
            await db.refresh(draft)
            return draft
        except Exception:
            await db.rollback()
            raise

    async def reconfirm_current(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricReconfirmRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            current = await self._get_current_rubric(db, job_id, for_update=True)
            if current is None:
                raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")
            if not current.is_stale:
                raise ScreeningRubricStaleError("当前 Rubric 没有过期，无需重新确认")
            current_fingerprint = self.build_job_fingerprint(self._job_values(job))
            if data.expected_job_fingerprint != current_fingerprint:
                raise ScreeningRubricStaleError("岗位内容已再次变化，请刷新后重新确认")

            current.is_current = False
            current.status = RubricLifecycleStatus.ARCHIVED.value
            await db.flush()
            version = await self._next_version(db, job_id)
            rubric = self.build_default_rubric(
                job_id=job_id,
                version=version,
                weights=ScreeningRubricWeights.model_validate(current.weights),
                semantic_items=list(current.semantic_items),
                source=current.source,
                template_key=current.template_key,
                job_fingerprint=current_fingerprint,
                change_reason=RubricChangeReasonCode.JOB_RECONFIRMED,
                change_detail=data.change_detail,
                created_by=LOCAL_HR_ACTOR_LABEL,
            )
            db.add_all(
                [
                    rubric,
                    self._activity(
                        job_id,
                        "job_screening_rubric_reconfirmed",
                        {
                            "from_version": current.version,
                            "to_version": version,
                            "change_detail": data.change_detail,
                        },
                    ),
                ]
            )
            await db.flush()
            await db.commit()
            await db.refresh(rubric)
            return rubric
        except Exception:
            await db.rollback()
            raise

    async def mark_current_stale(
        self,
        db: AsyncSession,
        *,
        job_id: int,
        old_fingerprint: str,
        new_fingerprint: str,
        reason: str,
    ) -> None:
        """Mark the active rubric and existing screening results stale in caller transaction."""
        now = datetime.now(timezone.utc)
        await db.execute(
            update(JobScreeningRubric)
            .where(
                JobScreeningRubric.job_id == job_id,
                JobScreeningRubric.is_current.is_(True),
            )
            .values(
                is_stale=True,
                stale_at=now,
                stale_reason=reason,
            )
        )
        await self._mark_screening_results_outdated(db, job_id, now)
        db.add(
            self._activity(
                job_id,
                "job_screening_rubric_marked_stale",
                {
                    "old_job_fingerprint": old_fingerprint,
                    "new_job_fingerprint": new_fingerprint,
                    "reason": reason,
                },
            )
        )

    async def update_rubric(
        self,
        db: AsyncSession,
        job_id: int,
        data: ScreeningRubricUpdateRequest,
    ) -> JobScreeningRubric:
        try:
            job = await self._get_job_for_update(db, job_id)
            if job is None:
                raise ScreeningRubricJobNotFoundError("岗位不存在")
            current = await self._get_current_rubric(db, job_id, for_update=True)
            if current is None:
                raise CurrentScreeningRubricNotFoundError("岗位缺少当前 Rubric")

            weights = data.resolved_weights()
            current.is_current = False
            current.status = RubricLifecycleStatus.ARCHIVED.value
            await db.flush()

            change_reason = (
                RubricChangeReasonCode.RESTORE_DEFAULT
                if data.restore_defaults
                else RubricChangeReasonCode.HR_ADJUSTMENT
            )
            rubric = self.build_default_rubric(
                job_id=job_id,
                version=current.version + 1,
                weights=weights,
                change_reason=change_reason,
                change_detail=data.change_detail,
                created_by=LOCAL_HR_ACTOR_LABEL,
                semantic_items=getattr(current, "semantic_items", None),
                source=getattr(current, "source", None) or RubricSource.STANDARD_TEMPLATE,
                template_key=(
                    getattr(current, "template_key", None) or RubricTemplateKey.STANDARD
                ),
                job_fingerprint=getattr(current, "job_fingerprint", None),
            )
            activity_log = ActivityLog(
                user_id=None,
                action="job_screening_rubric_updated",
                target_type="job",
                target_id=job_id,
                detail={
                    "from_version": current.version,
                    "to_version": rubric.version,
                    "from_weights": current.weights,
                    "to_weights": rubric.weights,
                    "change_reason": change_reason.value,
                    "change_detail": data.change_detail,
                    "actor_label": LOCAL_HR_ACTOR_LABEL,
                },
            )
            db.add_all([rubric, activity_log])
            await db.flush()
            await db.commit()
            await db.refresh(rubric)
            return rubric
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    def build_default_rubric(
        *,
        job_id: int,
        version: int = 1,
        weights: ScreeningRubricWeights | None = None,
        change_reason: RubricChangeReasonCode = RubricChangeReasonCode.INITIAL_DEFAULT,
        change_detail: str | None = "岗位创建时生成默认 Rubric",
        created_by: str | None = "system",
        semantic_items: list[dict] | None = None,
        source: RubricSource | str = RubricSource.STANDARD_TEMPLATE,
        template_key: RubricTemplateKey | str | None = RubricTemplateKey.STANDARD,
        job_fingerprint: str | None = None,
    ) -> JobScreeningRubric:
        resolved = weights or ScreeningRubricWeights()
        resolved_template_key = (
            template_key.value if isinstance(template_key, RubricTemplateKey) else template_key
        )
        if semantic_items is None:
            template = get_rubric_template(resolved_template_key or RubricTemplateKey.STANDARD)
            semantic_items = [
                item.model_dump(mode="json") for item in template.semantic_items
            ]
        return ScreeningRubricService._build_rubric(
            job_id=job_id,
            version=version,
            weights=resolved,
            semantic_items=semantic_items,
            source=source,
            template_key=template_key,
            status=RubricLifecycleStatus.ACTIVE,
            job_fingerprint=job_fingerprint,
            change_reason=change_reason,
            change_detail=change_detail,
            created_by=created_by,
        )

    @staticmethod
    def _build_rubric(
        *,
        job_id: int,
        version: int,
        weights: ScreeningRubricWeights,
        semantic_items: list[dict],
        source: RubricSource | str,
        template_key: RubricTemplateKey | str | None,
        status: RubricLifecycleStatus,
        job_fingerprint: str | None,
        change_reason: RubricChangeReasonCode,
        change_detail: str | None,
        created_by: str | None,
        generation_metadata: dict | None = None,
    ) -> JobScreeningRubric:
        resolved_source = source.value if isinstance(source, RubricSource) else source
        resolved_template_key = (
            template_key.value if isinstance(template_key, RubricTemplateKey) else template_key
        )
        is_active = status is RubricLifecycleStatus.ACTIVE
        now = datetime.now(timezone.utc) if is_active else None
        return JobScreeningRubric(
            job_id=job_id,
            version=version,
            must_have_requirements_weight=weights.must_have_requirements,
            work_experience_relevance_weight=weights.work_experience_relevance,
            projects_and_capability_weight=weights.projects_and_capability,
            preferred_qualifications_weight=weights.preferred_qualifications,
            keywords_and_additional_weight=weights.keywords_and_additional,
            schema_version=SCREENING_RUBRIC_SCHEMA_VERSION,
            subcriteria_version=RUBRIC_SUBCRITERIA_VERSION,
            recommendation_thresholds_version=(
                RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION
            ),
            fairness_rules_version=RUBRIC_FAIRNESS_RULES_VERSION,
            is_current=is_active,
            source=resolved_source,
            template_key=resolved_template_key,
            status=status.value,
            semantic_items=semantic_items,
            job_fingerprint=job_fingerprint,
            is_stale=False,
            stale_at=None,
            stale_reason=None,
            generation_metadata=generation_metadata,
            change_reason=change_reason.value,
            change_detail=change_detail,
            created_by=created_by,
            confirmed_by=created_by if is_active else None,
            confirmed_at=now,
            abandoned_at=None,
        )

    @staticmethod
    def build_job_fingerprint(values: Mapping[str, Any]) -> str:
        scoring_payload = {
            "title": values.get("title"),
            "description": values.get("description"),
            "requirements": values.get("requirements"),
        }
        serialized = json.dumps(
            scoring_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_generation_adapter() -> RubricGenerationAdapter:
        settings = get_settings()
        if not settings.RUBRIC_GENERATION_ENABLED:
            raise ScreeningRubricGenerationDisabledError("Rubric AI 生成功能未启用")
        return DeepSeekRubricGenerationAdapter(settings=settings)

    @staticmethod
    def _parse_generation_suggestion(
        content: str,
        *,
        expected_template: RubricTemplateKey,
    ) -> RubricGenerationSuggestion:
        try:
            payload = json.loads(content)
            suggestion = RubricGenerationSuggestion.model_validate(payload)
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise ScreeningRubricGenerationInvalidOutputError(
                "AI 返回的 Rubric 评分项不符合合同"
            ) from exc
        if suggestion.template_key is not expected_template:
            raise ScreeningRubricGenerationInvalidOutputError(
                "AI 返回的模板类型与请求不一致"
            )
        return suggestion

    @staticmethod
    def _parse_assisted_item(content: str) -> ManualSemanticCriterionInput:
        try:
            return ManualSemanticCriterionInput.model_validate(json.loads(content))
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise ScreeningRubricGenerationInvalidOutputError(
                "AI 返回的单项评分建议不符合合同"
            ) from exc

    @staticmethod
    def _job_values(job: Job) -> dict[str, Any]:
        return {
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
        }

    @staticmethod
    def _generation_job_context(job: Job) -> dict[str, Any]:
        return {
            "title": job.title,
            "department": job.department,
            "description": job.description,
            "requirements": job.requirements,
        }

    @staticmethod
    def _apply_weights(
        rubric: JobScreeningRubric,
        weights: ScreeningRubricWeights,
    ) -> None:
        rubric.must_have_requirements_weight = weights.must_have_requirements
        rubric.work_experience_relevance_weight = weights.work_experience_relevance
        rubric.projects_and_capability_weight = weights.projects_and_capability
        rubric.preferred_qualifications_weight = weights.preferred_qualifications
        rubric.keywords_and_additional_weight = weights.keywords_and_additional

    @staticmethod
    def _ensure_fingerprint(
        draft: JobScreeningRubric,
        *,
        expected: str,
        current: str,
    ) -> None:
        if expected != current or draft.job_fingerprint != current:
            raise ScreeningRubricStaleError(
                "岗位内容已变化，当前草稿不能直接保存或发布"
            )

    @staticmethod
    def _validate_publishable(draft: JobScreeningRubric) -> None:
        try:
            ScreeningRubricPublishContent.model_validate(
                {
                    "source": draft.source,
                    "template_key": draft.template_key,
                    "job_fingerprint": draft.job_fingerprint,
                    "weights": draft.weights,
                    "semantic_items": draft.semantic_items,
                }
            )
        except ValidationError as exc:
            raise ScreeningRubricPublishValidationError(
                "Rubric 草稿尚未达到发布条件"
            ) from exc

    @staticmethod
    def _activity(job_id: int, action: str, detail: dict) -> ActivityLog:
        return ActivityLog(
            user_id=None,
            action=action,
            target_type="job",
            target_id=job_id,
            detail={**detail, "actor_label": LOCAL_HR_ACTOR_LABEL},
        )

    @staticmethod
    async def _mark_screening_results_outdated(
        db: AsyncSession,
        job_id: int,
        when: datetime,
    ) -> None:
        await db.execute(
            update(ScreeningResult)
            .where(
                ScreeningResult.job_id == job_id,
                ScreeningResult.is_outdated.is_(False),
            )
            .values(is_outdated=True, outdated_at=when)
        )

    @staticmethod
    async def _get_job_for_update(db: AsyncSession, job_id: int) -> Job | None:
        statement = select(Job).where(Job.id == job_id).with_for_update()
        return await db.scalar(statement)

    @staticmethod
    async def _get_current_rubric(
        db: AsyncSession,
        job_id: int,
        *,
        for_update: bool,
    ) -> JobScreeningRubric | None:
        statement = select(JobScreeningRubric).where(
            JobScreeningRubric.job_id == job_id,
            JobScreeningRubric.is_current.is_(True),
        )
        if for_update:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    @staticmethod
    async def _get_draft_rubric(
        db: AsyncSession,
        job_id: int,
        *,
        for_update: bool,
    ) -> JobScreeningRubric | None:
        statement = select(JobScreeningRubric).where(
            JobScreeningRubric.job_id == job_id,
            JobScreeningRubric.status == RubricLifecycleStatus.DRAFT.value,
        )
        if for_update:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    @staticmethod
    async def _next_version(db: AsyncSession, job_id: int) -> int:
        statement = select(
            func.coalesce(func.max(JobScreeningRubric.version), 0) + 1
        ).where(JobScreeningRubric.job_id == job_id)
        return int(await db.scalar(statement))


screening_rubric_service = ScreeningRubricService()


__all__ = [
    "CurrentScreeningRubricNotFoundError",
    "ScreeningRubricDraftAlreadyExistsError",
    "ScreeningRubricDraftNotFoundError",
    "ScreeningRubricGenerationDisabledError",
    "ScreeningRubricGenerationInvalidOutputError",
    "ScreeningRubricJobNotFoundError",
    "ScreeningRubricPublishValidationError",
    "ScreeningRubricService",
    "ScreeningRubricStaleError",
    "screening_rubric_service",
]
