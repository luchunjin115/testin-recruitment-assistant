from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate
from app.services.report_service import (
    ReportDependencyNotFoundError,
    ReportScreeningMismatchError,
    report_service,
)


router = APIRouter(prefix="/reports", tags=["reports"])
REPORT_NOT_FOUND = "报告不存在"
REPORT_SCREENING_MISMATCH = "筛选结果与报告的候选人或岗位不一致"
DEPENDENCY_NOT_FOUND = {
    "candidate": "候选人不存在",
    "job": "岗位不存在",
    "screening_result": "筛选结果不存在",
}


def raise_report_dependency_error(exc: Exception) -> None:
    if isinstance(exc, ReportDependencyNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=DEPENDENCY_NOT_FOUND[exc.resource],
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=REPORT_SCREENING_MISMATCH,
    ) from exc


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
) -> Report:
    try:
        return await report_service.create_report(db, data)
    except (ReportDependencyNotFoundError, ReportScreeningMismatchError) as exc:
        raise_report_dependency_error(exc)


@router.get("", response_model=list[ReportRead])
async def list_reports(
    candidate_id: int | None = Query(default=None, ge=1),
    job_id: int | None = Query(default=None, ge=1),
    screening_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[Report]:
    return await report_service.list_reports(db, candidate_id, job_id, screening_id)


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> Report:
    report = await report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=REPORT_NOT_FOUND,
        )
    return report


@router.put("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: int,
    data: ReportUpdate,
    db: AsyncSession = Depends(get_db),
) -> Report:
    try:
        report = await report_service.update_report(db, report_id, data)
    except (ReportDependencyNotFoundError, ReportScreeningMismatchError) as exc:
        raise_report_dependency_error(exc)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=REPORT_NOT_FOUND,
        )
    return report


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await report_service.delete_report(db, report_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=REPORT_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
