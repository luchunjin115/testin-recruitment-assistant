from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Mapping, Sequence

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.screening_model import (
    SCREENING_MODEL_CONFIG_VERSION,
    DeepSeekScreeningModelAdapter,
    ScreeningModelAdapterError,
    ScreeningModelAdapterResult,
)
from app.core.config import Settings, get_settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_screening_rubric import JobScreeningRubric
from app.models.screening_result import ScreeningResult
from app.prompts.screening_evaluation import SCREENING_EVALUATION_PROMPT_VERSION
from app.schemas.application import ScreeningRunRequest
from app.schemas.job import JOB_REQUIREMENTS_SCHEMA_VERSION, JobRequirementsV1
from app.schemas.screening_evaluation import (
    SCREENING_EVALUATION_SCHEMA_VERSION,
    ScreeningCandidateMaterial,
    ScreeningEvidenceSource,
    ScreeningSemanticEvaluation,
)
from app.schemas.screening_rules import (
    CriterionMatchInput,
    DeterministicCandidateFacts,
    HardRequirementEvaluation,
    ScreeningCriterion,
    ScreeningMatchLevel,
)
from app.schemas.screening_rubric import (
    ScreeningRubricWeights,
    SemanticRubricCriterion,
)
from app.services.screening_input_service import ScreeningInputService
from app.services.screening_rule_service import (
    SCREENING_RULES_VERSION,
    ScreeningRuleService,
)
from app.services.screening_rubric_service import ScreeningRubricService
from app.services.screening_score_service import (
    SCREENING_SCORE_VERSION,
    ScreeningScoreService,
)


RUNNING_SCREENING_UNIQUE_INDEX = "uq_screening_results_running_application"


class ScreeningServiceError(ValueError):
    pass


class ScreeningApplicationNotFoundError(ScreeningServiceError):
    pass


class ScreeningNotAllowedError(ScreeningServiceError):
    pass


class ScreeningResumeRequiredError(ScreeningNotAllowedError):
    pass


class ScreeningJobNotOpenError(ScreeningNotAllowedError):
    pass


class ScreeningRubricInvalidError(ScreeningNotAllowedError):
    pass


class ScreeningRubricStaleError(ScreeningNotAllowedError):
    pass


class ScreeningAlreadyRunningError(ScreeningServiceError):
    pass


@dataclass(frozen=True, slots=True)
class ScreeningRunOutcome:
    result: ScreeningResult
    reused: bool
    model_called: bool


@dataclass(slots=True)
class _StartedScreening:
    application: Application
    candidate: Candidate
    job: Job
    resume: Any
    rubric: JobScreeningRubric
    requirements: JobRequirementsV1
    weights: ScreeningRubricWeights
    semantic_items: list[SemanticRubricCriterion]
    candidate_material: ScreeningCandidateMaterial | None
    input_fingerprint: str
    job_fingerprint: str
    result: ScreeningResult


class ScreeningService:
    """Run one versioned, idempotent Application screening workflow."""

    def __init__(
        self,
        *,
        model_adapter: Any | None = None,
        settings: Settings | None = None,
        input_service: ScreeningInputService | None = None,
        rule_service: ScreeningRuleService | None = None,
        score_service: ScreeningScoreService | None = None,
    ) -> None:
        self.model_adapter = model_adapter
        self.settings = settings or get_settings()
        self.input_service = input_service or ScreeningInputService()
        self.rule_service = rule_service or ScreeningRuleService()
        self.score_service = score_service or ScreeningScoreService()

    async def run(
        self,
        db: AsyncSession,
        application_id: int,
        request: ScreeningRunRequest | None = None,
        *,
        actor_type: str = "system",
        actor_id: str | None = None,
        actor_label: str | None = None,
    ) -> ScreeningRunOutcome:
        request = request or ScreeningRunRequest()
        try:
            started, reused = await self._start_attempt(
                db,
                application_id,
                request,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_label=actor_label,
            )
        except Exception:
            await db.rollback()
            raise
        if reused is not None:
            return ScreeningRunOutcome(result=reused, reused=True, model_called=False)
        if started is None:  # pragma: no cover - 仅用于收窄类型
            raise RuntimeError("评分启动状态不完整")

        if started.candidate_material is None:
            result = await self._finish_blocked(
                db,
                started,
                code="candidate_material_insufficient",
                message="候选人岗位相关材料不足，未调用语义评价模型",
                model_called=False,
            )
            return ScreeningRunOutcome(result=result, reused=False, model_called=False)

        try:
            hard_evaluation, deterministic_matches = self._deterministic_evaluation(started)
        except (ValidationError, ValueError):
            result = await self._finish_failed(
                db,
                started,
                code="screening_rule_input_error",
                message="确定性评分输入不合法",
            )
            return ScreeningRunOutcome(result=result, reused=False, model_called=False)

        try:
            model_result = await self._model().evaluate(
                self._job_context(started.job, started.requirements),
                started.semantic_items,
                started.candidate_material,
            )
        except ScreeningModelAdapterError as exc:
            result = await self._finish_failed(
                db,
                started,
                code=exc.code,
                message=str(exc),
            )
            return ScreeningRunOutcome(result=result, reused=False, model_called=True)

        try:
            semantic_evaluation = ScreeningSemanticEvaluation.model_validate_json(
                model_result.content
            )
            semantic_evaluation.validate_against(
                started.semantic_items,
                started.candidate_material,
            )
        except (ValidationError, ValueError):
            result = await self._finish_failed(
                db,
                started,
                code="screening_model_invalid_output",
                message="候选人语义评价模型返回内容未通过严格校验",
                model_result=model_result,
            )
            return ScreeningRunOutcome(result=result, reused=False, model_called=True)

        try:
            score = self.score_service.score(
                weights=started.weights,
                deterministic_matches=deterministic_matches,
                hard_requirement_checks=hard_evaluation.checks,
                semantic_items=started.semantic_items,
                semantic_evaluation=semantic_evaluation,
            )
        except (ValidationError, ValueError):
            result = await self._finish_failed(
                db,
                started,
                code="screening_score_error",
                message="候选人评分结果无法按已发布 Rubric 合并",
                model_result=model_result,
            )
            return ScreeningRunOutcome(result=result, reused=False, model_called=True)
        result = await self._finish_scored(
            db,
            started,
            hard_evaluation=hard_evaluation,
            semantic_evaluation=semantic_evaluation,
            score=score,
            model_result=model_result,
        )
        return ScreeningRunOutcome(result=result, reused=False, model_called=True)

    async def _start_attempt(
        self,
        db: AsyncSession,
        application_id: int,
        request: ScreeningRunRequest,
        *,
        actor_type: str,
        actor_id: str | None,
        actor_label: str | None,
    ) -> tuple[_StartedScreening | None, ScreeningResult | None]:
        application = await self._load_application_for_update(db, application_id)
        if application is None:
            raise ScreeningApplicationNotFoundError("Application 不存在")
        if application.lifecycle_status != "active":
            raise ScreeningNotAllowedError("只有 active Application 可以执行评分")
        if application.current_resume is None or application.current_resume_id is None:
            raise ScreeningResumeRequiredError("Application 尚未绑定可用简历")
        if application.job.status != "open":
            raise ScreeningJobNotOpenError("只有开放岗位可以启动新评分")

        rubric = self._current_rubric(application.job.screening_rubrics)
        requirements = JobRequirementsV1.model_validate(application.job.requirements)
        weights = ScreeningRubricWeights.model_validate(rubric.weights)
        semantic_items = [
            SemanticRubricCriterion.model_validate(item)
            for item in rubric.semantic_items
        ]
        if not 4 <= len(semantic_items) <= 10:
            raise ScreeningRubricInvalidError(
                "当前已发布 Rubric 不包含 4—10 个语义评分项"
            )

        candidate_profile = self._candidate_profile(application.candidate)
        try:
            material = self.input_service.build_candidate_material(
                application_ref=f"application-{application.id}",
                confirmed_profile=candidate_profile,
                resume_raw_text=application.current_resume.raw_text,
                resume_snapshot=application.current_resume.parsed_snapshot,
            )
        except (ValidationError, ValueError):
            material = None

        job_fingerprint = ScreeningRubricService.build_job_fingerprint(
            self._job_context(application.job, requirements)
        )
        if rubric.job_fingerprint != job_fingerprint:
            raise ScreeningRubricStaleError(
                "当前 Rubric 与岗位评分输入不一致，需由 HR 重新确认"
            )
        input_fingerprint = self._input_fingerprint(
            application=application,
            material=material,
            requirements=requirements,
            rubric=rubric,
            weights=weights,
            semantic_items=semantic_items,
        )

        running = await db.scalar(
            select(ScreeningResult).where(
                ScreeningResult.application_id == application.id,
                ScreeningResult.execution_status == "screening",
            )
        )
        if running is not None:
            raise ScreeningAlreadyRunningError("该 Application 已有评分正在执行")

        reusable = await db.scalar(
            select(ScreeningResult)
            .where(
                ScreeningResult.application_id == application.id,
                ScreeningResult.execution_status == "completed",
                ScreeningResult.input_fingerprint == input_fingerprint,
                ScreeningResult.is_outdated.is_(False),
            )
            .order_by(ScreeningResult.attempt_number.desc())
            .limit(1)
        )
        if reusable is not None and not request.force:
            application.ai_status = "completed"
            application.current_screening_result_id = reusable.id
            await db.commit()
            return None, reusable

        attempt_number = (
            await db.scalar(
                select(func.max(ScreeningResult.attempt_number)).where(
                    ScreeningResult.application_id == application.id
                )
            )
            or 0
        ) + 1
        previous_current = application.current_screening_result
        if (
            previous_current is not None
            and previous_current.input_fingerprint != input_fingerprint
        ):
            previous_current.is_outdated = True
            previous_current.outdated_at = datetime.now(timezone.utc)

        result = ScreeningResult(
            candidate_id=application.candidate_id,
            job_id=application.job_id,
            application_id=application.id,
            resume_id=application.current_resume_id,
            attempt_number=attempt_number,
            execution_status="screening",
            input_fingerprint=input_fingerprint,
            candidate_input_snapshot=(
                material.model_dump(mode="json")
                if material is not None
                else {
                    "application_ref": f"application-{application.id}",
                    "blocked_reason": "candidate_material_insufficient",
                }
            ),
            resume_snapshot=self._resume_snapshot(application.current_resume, material),
            job_requirements_snapshot=requirements.model_dump(mode="json"),
            rubric_snapshot=self._rubric_snapshot(rubric, weights, semantic_items),
            rules_version=f"rules:{SCREENING_RULES_VERSION};score:{SCREENING_SCORE_VERSION}",
            prompt_version=SCREENING_EVALUATION_PROMPT_VERSION,
            model_provider="deepseek",
            model_name=self.settings.SCREENING_MODEL_NAME,
            model_config_version=SCREENING_MODEL_CONFIG_VERSION,
            job_schema_version=JOB_REQUIREMENTS_SCHEMA_VERSION,
            resume_schema_version=application.current_resume.structure_schema_version,
            started_at=datetime.now(timezone.utc),
            trigger_reason=(
                request.reason
                or ("initial_application_screening" if attempt_number == 1 else "manual_rerun")
            ),
            force_rerun=request.force,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_label=actor_label,
        )
        application.ai_status = "screening"
        db.add(result)
        try:
            await db.commit()
            await db.refresh(result)
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) == RUNNING_SCREENING_UNIQUE_INDEX:
                raise ScreeningAlreadyRunningError(
                    "该 Application 已有评分正在执行"
                ) from None
            raise
        return (
            _StartedScreening(
                application=application,
                candidate=application.candidate,
                job=application.job,
                resume=application.current_resume,
                rubric=rubric,
                requirements=requirements,
                weights=weights,
                semantic_items=semantic_items,
                candidate_material=material,
                input_fingerprint=input_fingerprint,
                job_fingerprint=job_fingerprint,
                result=result,
            ),
            None,
        )

    def _deterministic_evaluation(
        self,
        started: _StartedScreening,
    ) -> tuple[HardRequirementEvaluation, list[CriterionMatchInput]]:
        material = started.candidate_material
        if material is None:  # pragma: no cover - 调用方已阻止
            raise ValueError("缺少候选人材料")
        profile = material.confirmed_profile
        facts = DeterministicCandidateFacts(
            work_years=profile.work_years,
            education_level=profile.education_level,
            skills=profile.skills,
            skills_evidence_complete=False,
            required_experiences=[],
        )
        hard = self.rule_service.evaluate_hard_requirements(
            started.requirements,
            facts,
        )
        matches = list(hard.criterion_matches)
        preferred = self._preferred_skill_match(started.requirements, facts)
        if preferred is not None:
            matches.append(preferred)
        keywords = self._keyword_match(started.requirements, material)
        if keywords is not None:
            matches.append(keywords)
        return hard, matches

    def _preferred_skill_match(
        self,
        requirements: JobRequirementsV1,
        facts: DeterministicCandidateFacts,
    ) -> CriterionMatchInput | None:
        if not requirements.preferred_skills:
            return None
        available = {
            self.rule_service.normalize_skill(skill): skill for skill in facts.skills
        }
        matched = [
            available[self.rule_service.normalize_skill(skill)]
            for skill in requirements.preferred_skills
            if self.rule_service.normalize_skill(skill) in available
        ]
        if len(matched) == len(requirements.preferred_skills):
            level = ScreeningMatchLevel.FULL
        elif matched:
            level = ScreeningMatchLevel.PARTIAL
        else:
            level = ScreeningMatchLevel.UNKNOWN
        return CriterionMatchInput(
            criterion=ScreeningCriterion.PREFERRED_SKILLS,
            match_level=level,
            evidence=[f"已确认技能：{skill}" for skill in matched],
        )

    @staticmethod
    def _keyword_match(
        requirements: JobRequirementsV1,
        material: ScreeningCandidateMaterial,
    ) -> CriterionMatchInput | None:
        if not requirements.keywords:
            return None
        searchable = "\n".join(
            material.serialized_source(source)
            for source in ScreeningEvidenceSource
        ).casefold()
        matched = [keyword for keyword in requirements.keywords if keyword.casefold() in searchable]
        if len(matched) == len(requirements.keywords):
            level = ScreeningMatchLevel.FULL
        elif matched:
            level = ScreeningMatchLevel.PARTIAL
        else:
            level = ScreeningMatchLevel.UNKNOWN
        return CriterionMatchInput(
            criterion=ScreeningCriterion.KEYWORDS,
            match_level=level,
            evidence=[f"脱敏材料包含关键词：{keyword}" for keyword in matched],
        )

    async def _finish_scored(
        self,
        db: AsyncSession,
        started: _StartedScreening,
        *,
        hard_evaluation: HardRequirementEvaluation,
        semantic_evaluation: ScreeningSemanticEvaluation,
        score: Any,
        model_result: ScreeningModelAdapterResult,
    ) -> ScreeningResult:
        application, result = await self._lock_finalization_rows(db, started)
        now = datetime.now(timezone.utc)
        result.execution_status = "blocked" if score.blocked else "completed"
        if score.blocked:
            result.error_code = "insufficient_evidence"
            result.error_message = "候选人材料没有形成足够的可定位评分证据"
        result.overall_score = score.overall_score
        result.hard_pass = score.hard_pass
        result.recommendation = (
            score.recommendation.value if score.recommendation is not None else None
        )
        result.evidence_coverage_rate = score.evidence_coverage_rate
        result.hard_requirement_checks = [
            item.model_dump(mode="json") for item in hard_evaluation.checks
        ]
        result.dimension_scores = {
            item.dimension.value: item.model_dump(mode="json")
            for item in score.dimension_scores
        }
        result.skill_score = self._dimension_percentage(score, "must_have_requirements")
        result.experience_score = self._dimension_percentage(
            score,
            "work_experience_relevance",
        )
        result.project_score = self._dimension_percentage(
            score,
            "projects_and_capability",
        )
        result.strengths = score.strengths
        result.risks = score.risks
        result.pending_questions = score.pending_questions
        result.reason = self._score_reason(score)
        result.resume_evidence = self._resume_evidence(semantic_evaluation)
        result.job_evidence = [
            {
                "criterion": item.criterion.value,
                "requirement": item.requirement,
                "status": item.status.value,
                "evidence": item.evidence,
            }
            for item in hard_evaluation.checks
        ]
        result.raw_result = {
            "semantic_evaluation": semantic_evaluation.model_dump(mode="json"),
            "combined_score": score.model_dump(mode="json"),
        }
        self._apply_model_metadata(result, model_result)
        result.finished_at = now
        result.duration_ms = model_result.duration_ms
        result.is_outdated = await self._inputs_changed_during_run(db, started, application)
        result.outdated_at = now if result.is_outdated else None
        application.ai_status = "blocked" if score.blocked else "completed"
        if not score.blocked:
            application.current_screening_result_id = result.id
        await db.commit()
        await db.refresh(result)
        return result

    async def _finish_blocked(
        self,
        db: AsyncSession,
        started: _StartedScreening,
        *,
        code: str,
        message: str,
        model_called: bool,
    ) -> ScreeningResult:
        del model_called
        application, result = await self._lock_finalization_rows(db, started)
        now = datetime.now(timezone.utc)
        result.execution_status = "blocked"
        result.error_code = code
        result.error_message = message
        result.finished_at = now
        result.duration_ms = self._elapsed_ms(result.started_at, now)
        result.is_outdated = await self._inputs_changed_during_run(db, started, application)
        result.outdated_at = now if result.is_outdated else None
        application.ai_status = "blocked"
        await db.commit()
        await db.refresh(result)
        return result

    async def _finish_failed(
        self,
        db: AsyncSession,
        started: _StartedScreening,
        *,
        code: str,
        message: str,
        model_result: ScreeningModelAdapterResult | None = None,
    ) -> ScreeningResult:
        application, result = await self._lock_finalization_rows(db, started)
        now = datetime.now(timezone.utc)
        result.execution_status = "failed"
        result.error_code = code
        result.error_message = message
        result.finished_at = now
        result.duration_ms = (
            model_result.duration_ms
            if model_result is not None
            else self._elapsed_ms(result.started_at, now)
        )
        if model_result is not None:
            self._apply_model_metadata(result, model_result)
        result.is_outdated = await self._inputs_changed_during_run(db, started, application)
        result.outdated_at = now if result.is_outdated else None
        application.ai_status = "failed"
        await db.commit()
        await db.refresh(result)
        return result

    @staticmethod
    async def _lock_finalization_rows(
        db: AsyncSession,
        started: _StartedScreening,
    ) -> tuple[Application, ScreeningResult]:
        application = await db.scalar(
            select(Application)
            .where(Application.id == started.application.id)
            .with_for_update()
        )
        result = await db.scalar(
            select(ScreeningResult)
            .where(ScreeningResult.id == started.result.id)
            .with_for_update()
        )
        if application is None or result is None:
            await db.rollback()
            raise RuntimeError("评分完成时业务记录不存在")
        if result.execution_status != "screening":
            await db.rollback()
            raise RuntimeError("评分尝试已被其他执行者结束")
        return application, result

    async def _inputs_changed_during_run(
        self,
        db: AsyncSession,
        started: _StartedScreening,
        application: Application,
    ) -> bool:
        if application.current_resume_id != started.resume.id:
            return True
        current_rubric_id = await db.scalar(
            select(JobScreeningRubric.id).where(
                JobScreeningRubric.job_id == started.job.id,
                JobScreeningRubric.is_current.is_(True),
                JobScreeningRubric.status == "active",
            )
        )
        if current_rubric_id != started.rubric.id:
            return True
        await db.refresh(started.job, attribute_names=["title", "description", "requirements"])
        latest_job_fingerprint = ScreeningRubricService.build_job_fingerprint(
            {
                "title": started.job.title,
                "description": started.job.description,
                "requirements": started.job.requirements,
            }
        )
        return latest_job_fingerprint != started.job_fingerprint

    @staticmethod
    async def _load_application_for_update(
        db: AsyncSession,
        application_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .options(
                selectinload(Application.current_resume),
                selectinload(Application.current_screening_result),
                selectinload(Application.job).selectinload(Job.screening_rubrics),
                selectinload(Application.candidate).selectinload(
                    Candidate.education_records
                ),
                selectinload(Application.candidate).selectinload(
                    Candidate.work_experiences
                ),
                selectinload(Application.candidate).selectinload(
                    Candidate.project_experiences
                ),
            )
            .where(Application.id == application_id)
            .with_for_update()
        )
        return await db.scalar(statement)

    @staticmethod
    def _current_rubric(
        rubrics: Sequence[JobScreeningRubric],
    ) -> JobScreeningRubric:
        current = [
            rubric
            for rubric in rubrics
            if rubric.is_current and rubric.status == "active"
        ]
        if len(current) != 1:
            raise ScreeningRubricInvalidError("岗位缺少唯一的当前已发布 Rubric")
        rubric = current[0]
        if rubric.is_stale:
            raise ScreeningRubricStaleError("当前 Rubric 已过期，需由 HR 重新确认")
        return rubric

    @staticmethod
    def _candidate_profile(candidate: Candidate) -> dict[str, Any]:
        envelope = candidate.parsed_data if isinstance(candidate.parsed_data, Mapping) else {}
        draft = envelope.get("draft") if isinstance(envelope.get("draft"), Mapping) else envelope
        profile = dict(draft)
        profile.update(
            {
                "name": candidate.name,
                "phone": candidate.phone,
                "email": candidate.email,
                "gender": candidate.gender,
                "age": candidate.age,
                "location": candidate.location,
            }
        )
        for key in ("current_title", "work_years", "education_level"):
            value = getattr(candidate, key)
            if value is not None:
                profile[key] = value
        if candidate.education_records:
            profile["education_records"] = [
                    {
                        "school": item.school,
                        "degree": item.degree,
                        "major": item.major,
                        "start_date": item.start_date,
                        "end_date": item.end_date,
                    }
                    for item in candidate.education_records
                ]
        if candidate.work_experiences:
            profile["work_experiences"] = [
                    {
                        "company": item.company,
                        "title": item.title,
                        "start_date": item.start_date,
                        "end_date": item.end_date,
                        "description": item.description,
                        "tech_stack": item.tech_stack or [],
                    }
                    for item in candidate.work_experiences
                ]
        if candidate.project_experiences:
            profile["project_experiences"] = [
                    {
                        "project_name": item.project_name,
                        "role": item.role,
                        "start_date": item.start_date,
                        "end_date": item.end_date,
                        "description": item.description,
                        "tech_stack": item.tech_stack or [],
                        "achievements": item.achievements,
                    }
                    for item in candidate.project_experiences
                ]
        return profile

    def _input_fingerprint(
        self,
        *,
        application: Application,
        material: ScreeningCandidateMaterial | None,
        requirements: JobRequirementsV1,
        rubric: JobScreeningRubric,
        weights: ScreeningRubricWeights,
        semantic_items: Sequence[SemanticRubricCriterion],
    ) -> str:
        payload = {
            "application": {
                "id": application.id,
                "candidate_id": application.candidate_id,
                "job_id": application.job_id,
                "resume_id": application.current_resume_id,
            },
            "candidate_material": (
                material.model_dump(mode="json") if material is not None else None
            ),
            "job_requirements": requirements.model_dump(mode="json"),
            "rubric": {
                "id": rubric.id,
                "version": rubric.version,
                "weights": weights.model_dump(mode="json"),
                "semantic_items": [item.model_dump(mode="json") for item in semantic_items],
                "schema_version": rubric.schema_version,
                "subcriteria_version": rubric.subcriteria_version,
                "fairness_rules_version": rubric.fairness_rules_version,
                "thresholds_version": rubric.recommendation_thresholds_version,
            },
            "versions": {
                "rules": SCREENING_RULES_VERSION,
                "score": SCREENING_SCORE_VERSION,
                "prompt": SCREENING_EVALUATION_PROMPT_VERSION,
                "output_schema": SCREENING_EVALUATION_SCHEMA_VERSION,
                "model_provider": "deepseek",
                "model_name": self.settings.SCREENING_MODEL_NAME,
                "model_config": SCREENING_MODEL_CONFIG_VERSION,
                "max_output_tokens": self.settings.SCREENING_MODEL_MAX_OUTPUT_TOKENS,
                "temperature": 0.1,
                "thinking": "disabled",
            },
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _resume_snapshot(resume: Any, material: ScreeningCandidateMaterial | None) -> dict:
        return {
            "resume_id": resume.id,
            "structure_schema_version": resume.structure_schema_version,
            "resume_text": material.resume_text if material is not None else None,
            "structured_resume": (
                material.structured_resume.model_dump(mode="json")
                if material is not None
                else None
            ),
        }

    @staticmethod
    def _rubric_snapshot(
        rubric: JobScreeningRubric,
        weights: ScreeningRubricWeights,
        semantic_items: Sequence[SemanticRubricCriterion],
    ) -> dict:
        return {
            "id": rubric.id,
            "version": rubric.version,
            "weights": weights.model_dump(mode="json"),
            "semantic_items": [item.model_dump(mode="json") for item in semantic_items],
            "schema_version": rubric.schema_version,
            "subcriteria_version": rubric.subcriteria_version,
            "recommendation_thresholds_version": rubric.recommendation_thresholds_version,
            "fairness_rules_version": rubric.fairness_rules_version,
            "job_fingerprint": rubric.job_fingerprint,
        }

    @staticmethod
    def _job_context(job: Job, requirements: JobRequirementsV1) -> dict[str, Any]:
        return {
            "title": job.title,
            "department": job.department,
            "description": job.description,
            "requirements": requirements.model_dump(mode="json"),
        }

    def _model(self) -> Any:
        if self.model_adapter is None:
            self.model_adapter = DeepSeekScreeningModelAdapter(settings=self.settings)
        return self.model_adapter

    @staticmethod
    def _dimension_percentage(score: Any, dimension: str) -> int | None:
        item = next(
            (
                item
                for item in score.dimension_scores
                if item.dimension.value == dimension
            ),
            None,
        )
        return round(item.score_percentage) if item is not None else None

    @staticmethod
    def _score_reason(score: Any) -> str:
        if score.blocked:
            return "候选人材料没有形成足够的可定位证据，未生成总分"
        capped = "；推荐等级已按风险边界封顶" if score.recommendation_capped else ""
        return (
            f"规则与语义评分按已发布 Rubric 合并，总分 {score.overall_score}，"
            f"证据覆盖率 {score.evidence_coverage_rate:.2%}{capped}"
        )

    @staticmethod
    def _resume_evidence(evaluation: ScreeningSemanticEvaluation) -> list[dict]:
        return [
            {
                "criterion_key": item.criterion_key,
                **evidence.model_dump(mode="json"),
            }
            for item in evaluation.evaluations
            for evidence in item.evidence
        ]

    @staticmethod
    def _apply_model_metadata(
        result: ScreeningResult,
        model_result: ScreeningModelAdapterResult,
    ) -> None:
        result.model_name = model_result.model
        result.prompt_tokens = model_result.input_tokens
        result.completion_tokens = model_result.output_tokens
        result.total_tokens = (
            model_result.input_tokens + model_result.output_tokens
            if model_result.input_tokens is not None
            and model_result.output_tokens is not None
            else None
        )
        result.estimated_cost = model_result.estimated_cost

    @staticmethod
    def _elapsed_ms(started_at: datetime | None, finished_at: datetime) -> int:
        if started_at is None:
            return 0
        return max(0, int((finished_at - started_at).total_seconds() * 1_000))

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        original = getattr(exc, "orig", None)
        diagnostic = getattr(original, "diag", None)
        return getattr(diagnostic, "constraint_name", None)


screening_service = ScreeningService()


__all__ = [
    "ScreeningAlreadyRunningError",
    "ScreeningApplicationNotFoundError",
    "ScreeningNotAllowedError",
    "ScreeningRunOutcome",
    "ScreeningService",
    "ScreeningServiceError",
    "screening_service",
]
