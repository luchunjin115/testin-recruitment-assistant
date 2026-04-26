from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.candidate import HRActionRequest, VALID_HR_ACTIONS
from ..services.candidate_service import candidate_service
from ..services.stage_service import stage_service

router = APIRouter(prefix="/candidates", tags=["HR操作"])


@router.post("/{candidate_id}/actions/{action_name}")
def execute_hr_action(
    candidate_id: int,
    action_name: str,
    body: HRActionRequest = None,
    db: Session = Depends(get_db),
):
    if body is None:
        body = HRActionRequest()

    if action_name not in VALID_HR_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的操作: {action_name}，有效操作: {VALID_HR_ACTIONS}",
        )

    candidate = candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    try:
        candidate = stage_service.execute_hr_action(
            db, candidate, action_name,
            interview_time=body.interview_time,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from .candidates import _to_read
    return _to_read(candidate)
