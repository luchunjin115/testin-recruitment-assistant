from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.candidate import ChatRequest, ChatResponse, InterviewSummaryRequest, InterviewSummaryResponse
from ..services.ai_service import ai_service
from ..services.candidate_service import candidate_service

router = APIRouter(prefix="/ai", tags=["AI能力"])


@router.post("/summary/{candidate_id}")
def generate_summary(candidate_id: int, db: Session = Depends(get_db)):
    summary = candidate_service.regenerate_summary(db, candidate_id)
    if not summary and not candidate_service.get_candidate(db, candidate_id):
        raise HTTPException(status_code=404, detail="候选人不存在")
    return {"summary": summary}


@router.post("/tags/{candidate_id}")
def generate_tags(candidate_id: int, db: Session = Depends(get_db)):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    tags = candidate_service.regenerate_tags(db, candidate_id)
    return {"tags": tags}


@router.post("/followup/{candidate_id}")
def get_followup(candidate_id: int, db: Session = Depends(get_db)):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    suggestion = candidate_service.get_followup_suggestion(db, candidate_id)
    return {"suggestion": suggestion.get("followup_suggestion", ""), **suggestion}


@router.post("/interview-summary/{candidate_id}", response_model=InterviewSummaryResponse)
def generate_interview_summary(
    candidate_id: int,
    req: InterviewSummaryRequest,
    db: Session = Depends(get_db),
):
    try:
        result = candidate_service.generate_interview_summary(
            db,
            candidate_id=candidate_id,
            feedback_text=req.interview_feedback_text,
            interviewer=req.interviewer or "",
            interview_round=req.interview_round or "",
            feedback_time=req.feedback_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return result


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    stats = candidate_service.get_dashboard_stats(db)
    alerts = candidate_service.get_follow_up_alerts(db)
    context = {
        "total_candidates": stats["total_candidates"],
        "new_today": stats["new_today"],
        "in_pipeline": stats["in_pipeline"],
        "follow_up_count": len(alerts),
    }
    reply = ai_service.chat(req.messages, context)
    return {"reply": reply}
