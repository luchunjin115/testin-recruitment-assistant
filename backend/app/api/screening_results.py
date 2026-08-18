from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.screening_result import ScreeningResult
from app.schemas.screening_result import (
    ApplicationScreeningResultDetailRead,
    ApplicationScreeningResultSummaryRead,
)
from app.services.screening_result_service import screening_result_service


router = APIRouter(prefix="/screening-results", tags=["screening-results"])
SCREENING_RESULT_NOT_FOUND = "筛选结果不存在"


@router.get(
    "",
    response_model=list[ApplicationScreeningResultSummaryRead],
)
async def list_screening_results(
    candidate_id: int | None = Query(default=None, ge=1),
    job_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[ScreeningResult]:
    return await screening_result_service.list_screening_results(
        db,
        candidate_id,
        job_id,
    )


@router.get(
    "/{screening_result_id}",
    response_model=ApplicationScreeningResultDetailRead,
)
async def get_screening_result(
    screening_result_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScreeningResult:
    screening_result = await screening_result_service.get_screening_result(
        db,
        screening_result_id,
    )
    if screening_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SCREENING_RESULT_NOT_FOUND,
        )
    return screening_result
