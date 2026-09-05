from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.recruitment_statistics import RecruitmentStatisticsRead
from app.services.recruitment_statistics_service import recruitment_statistics_service


router = APIRouter(tags=["recruitment-statistics"])


@router.get("/recruitment-statistics", response_model=RecruitmentStatisticsRead)
async def get_recruitment_statistics(
    job_id: int | None = Query(default=None, ge=1),
    applied_from: AwareDatetime | None = None,
    applied_to: AwareDatetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> RecruitmentStatisticsRead:
    if applied_from is not None and applied_to is not None and applied_from > applied_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "RECRUITMENT_STATISTICS_DATE_RANGE_INVALID",
                "message": "投递开始时间不能晚于结束时间",
            },
        )
    try:
        return await recruitment_statistics_service.get_statistics(
            db,
            job_id=job_id,
            applied_from=applied_from,
            applied_to=applied_to,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RECRUITMENT_STATISTICS_QUERY_FAILED",
                "message": "招聘流程统计读取失败，请稍后重试",
            },
        ) from exc
