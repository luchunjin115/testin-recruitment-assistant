from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rebuilt.activity_log import ActivityLog
from app.models.rebuilt.job import Job
from app.models.rebuilt.job_screening_rubric import JobScreeningRubric
from app.schemas.rebuilt.screening_rubric import (
    RUBRIC_FAIRNESS_RULES_VERSION,
    RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION,
    RUBRIC_SUBCRITERIA_VERSION,
    SCREENING_RUBRIC_SCHEMA_VERSION,
    RubricChangeReasonCode,
    ScreeningRubricUpdateRequest,
    ScreeningRubricWeights,
)


LOCAL_HR_ACTOR_LABEL = "本地 HR（未认证）"


class ScreeningRubricError(ValueError):
    pass


class ScreeningRubricJobNotFoundError(ScreeningRubricError):
    pass


class CurrentScreeningRubricNotFoundError(ScreeningRubricError):
    pass


class ScreeningRubricService:
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
    ) -> JobScreeningRubric:
        resolved = weights or ScreeningRubricWeights()
        return JobScreeningRubric(
            job_id=job_id,
            version=version,
            must_have_requirements_weight=resolved.must_have_requirements,
            work_experience_relevance_weight=resolved.work_experience_relevance,
            projects_and_capability_weight=resolved.projects_and_capability,
            preferred_qualifications_weight=resolved.preferred_qualifications,
            keywords_and_additional_weight=resolved.keywords_and_additional,
            schema_version=SCREENING_RUBRIC_SCHEMA_VERSION,
            subcriteria_version=RUBRIC_SUBCRITERIA_VERSION,
            recommendation_thresholds_version=(
                RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION
            ),
            fairness_rules_version=RUBRIC_FAIRNESS_RULES_VERSION,
            is_current=True,
            change_reason=change_reason.value,
            change_detail=change_detail,
            created_by=created_by,
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


screening_rubric_service = ScreeningRubricService()


__all__ = [
    "CurrentScreeningRubricNotFoundError",
    "ScreeningRubricJobNotFoundError",
    "ScreeningRubricService",
    "screening_rubric_service",
]
