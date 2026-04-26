from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.candidate_service import candidate_service

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return candidate_service.get_dashboard_stats(db)


@router.get("/follow-ups")
def get_follow_ups(db: Session = Depends(get_db)):
    return candidate_service.get_follow_up_alerts(db)


@router.get("/recent-logs")
def get_recent_logs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return candidate_service.get_recent_logs(db, limit=limit)


@router.get("/daily-summary")
def get_daily_summary(
    target_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    d = None
    if target_date:
        try:
            d = date.fromisoformat(target_date)
        except ValueError:
            pass
    return candidate_service.get_daily_summary(db, d)
