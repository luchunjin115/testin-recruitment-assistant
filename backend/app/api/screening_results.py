from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rebuilt.screening_result import ScreeningResult
from app.schemas.rebuilt.screening_result import (
    ScreeningResultCreate,
    ScreeningResultRead,
    ScreeningResultUpdate,
)
from app.services.rebuilt.screening_result_service import (
    ScreeningResultAlreadyExistsError,
    ScreeningResultDependencyNotFoundError,
    screening_result_service,
)


router = APIRouter(prefix="/screening-results", tags=["screening-results"])
SCREENING_RESULT_NOT_FOUND = "筛选结果不存在"
SCREENING_RESULT_ALREADY_EXISTS = "该候选人与岗位的筛选结果已存在"
DEPENDENCY_NOT_FOUND = {
    "candidate": "候选人不存在",
    "job": "岗位不存在",
}


@router.post("", response_model=ScreeningResultRead, status_code=status.HTTP_201_CREATED)
async def create_screening_result(
    data: ScreeningResultCreate,
    db: AsyncSession = Depends(get_db),
) -> ScreeningResult:
    try:
        return await screening_result_service.create_screening_result(db, data)
    except ScreeningResultDependencyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=DEPENDENCY_NOT_FOUND[exc.resource],
        ) from exc
    except ScreeningResultAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SCREENING_RESULT_ALREADY_EXISTS,
        ) from exc


@router.get("", response_model=list[ScreeningResultRead])
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


@router.get("/{screening_result_id}", response_model=ScreeningResultRead)
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


@router.put("/{screening_result_id}", response_model=ScreeningResultRead)
async def update_screening_result(
    screening_result_id: int,
    data: ScreeningResultUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScreeningResult:
    screening_result = await screening_result_service.update_screening_result(
        db,
        screening_result_id,
        data,
    )
    if screening_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SCREENING_RESULT_NOT_FOUND,
        )
    return screening_result


@router.delete(
    "/{screening_result_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_screening_result(
    screening_result_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await screening_result_service.delete_screening_result(
        db,
        screening_result_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SCREENING_RESULT_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
