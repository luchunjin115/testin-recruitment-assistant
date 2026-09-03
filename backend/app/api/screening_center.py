from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.application import (
    ApplicationLifecycleStatus,
    ApplicationSource,
    FinalOutcome,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.public_application import ApplicationProcessingStatus
from app.schemas.screening_center import (
    ScreeningCenterApplicationPage,
    ScreeningCenterDisplayLabel,
    ScreeningCenterProcessingPool,
    ScreeningCenterSort,
)
from app.services.screening_center_service import screening_center_service


router = APIRouter(prefix="/screening-center", tags=["screening-center"])


@router.get("/applications", response_model=ScreeningCenterApplicationPage)
async def list_screening_center_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    application_id: int | None = Query(default=None, ge=1),
    job_id: int | None = Query(default=None, ge=1),
    source: ApplicationSource | None = None,
    hr_decision: HRDecision | None = None,
    stage: RecruitmentStage | None = None,
    lifecycle: ApplicationLifecycleStatus | None = None,
    final_outcome: FinalOutcome | None = None,
    processing_pool: ScreeningCenterProcessingPool = ScreeningCenterProcessingPool.ALL,
    processing_status: ApplicationProcessingStatus | None = None,
    display_label: ScreeningCenterDisplayLabel | None = None,
    score_min: int | None = Query(default=None, ge=0, le=100),
    score_max: int | None = Query(default=None, ge=0, le=100),
    applied_from: datetime | None = None,
    applied_to: datetime | None = None,
    sort: ScreeningCenterSort = ScreeningCenterSort.APPLIED_DESC,
    db: AsyncSession = Depends(get_db),
) -> ScreeningCenterApplicationPage:
    if score_min is not None and score_max is not None and score_min > score_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "SCREENING_CENTER_SCORE_RANGE_INVALID", "message": "最低分不能高于最高分"},
        )
    if applied_from is not None and applied_to is not None and applied_from > applied_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "SCREENING_CENTER_DATE_RANGE_INVALID", "message": "开始日期不能晚于结束日期"},
        )
    try:
        return await screening_center_service.list_applications(
            db,
            page=page,
            page_size=page_size,
            application_id=application_id,
            job_id=job_id,
            source=source,
            hr_decision=hr_decision,
            recruitment_stage=stage,
            lifecycle_status=lifecycle,
            final_outcome=final_outcome,
            processing_pool=processing_pool,
            processing_status=processing_status,
            display_label=display_label,
            score_min=score_min,
            score_max=score_max,
            applied_from=applied_from,
            applied_to=applied_to,
            sort=sort,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SCREENING_CENTER_QUERY_FAILED", "message": "AI 初筛中心读取失败，请稍后重试"},
        ) from exc
