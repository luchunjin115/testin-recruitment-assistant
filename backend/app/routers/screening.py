import json
from datetime import date, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.candidate_service import candidate_service

router = APIRouter(prefix="/screening", tags=["AI初筛"])


def _split_terms(value: str) -> List[str]:
    if not value:
        return []
    import re
    return [item.strip() for item in re.split(r"[,，;；、\n]+", value) if item.strip()]


def _term_hits(terms: List[str], text: str) -> List[str]:
    lowered = (text or "").lower()
    return [term for term in terms if term.lower() in lowered]


def _job_profile_for_candidate(candidate) -> dict:
    job = getattr(candidate, "job", None)
    if not job:
        return {}
    return {
        "title": job.title or "",
        "description": job.description or "",
        "requirements": job.requirements or "",
        "required_skills": job.required_skills or "",
        "bonus_skills": job.bonus_skills or "",
        "education_requirement": job.education_requirement or "",
        "experience_requirement": job.experience_requirement or "",
        "job_keywords": job.job_keywords or "",
        "risk_keywords": job.risk_keywords or "",
    }


def _job_match_summary(candidate, skills: List[str]) -> str:
    profile = _job_profile_for_candidate(candidate)
    if not profile:
        return "未配置岗位要求"
    searchable = " ".join([
        candidate.target_role or "",
        candidate.school or "",
        candidate.degree or "",
        candidate.major or "",
        candidate.experience_desc or "",
        candidate.self_intro or "",
        " ".join(skills or []),
    ])
    required = _split_terms(profile.get("required_skills", ""))
    bonus = _split_terms(profile.get("bonus_skills", ""))
    keywords = _split_terms(profile.get("job_keywords", ""))
    risks = _split_terms(profile.get("risk_keywords", ""))
    required_hits = _term_hits(required, searchable)
    bonus_hits = _term_hits(bonus, searchable)
    keyword_hits = _term_hits(keywords, searchable)
    risk_hits = _term_hits(risks, searchable)
    parts = []
    if required:
        parts.append(f"必备 {len(required_hits)}/{len(required)}")
    if bonus:
        parts.append(f"加分 {len(bonus_hits)}/{len(bonus)}")
    if keywords:
        parts.append(f"关键词 {len(keyword_hits)}/{len(keywords)}")
    if risks:
        parts.append(f"风险 {len(risk_hits)}项")
    return "；".join(parts) if parts else "岗位要求未细化"


def _screening_to_read(candidate) -> dict:
    skills = candidate.skills
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except Exception:
            skills = []

    risk_flags = candidate.risk_flags
    if isinstance(risk_flags, str):
        try:
            risk_flags = json.loads(risk_flags)
        except Exception:
            risk_flags = []

    return {
        "id": candidate.id,
        "name": candidate.name,
        "school": candidate.school,
        "degree": candidate.degree,
        "major": candidate.major,
        "target_role": candidate.target_role,
        "skills": skills,
        "stage": candidate.stage,
        "screening_status": candidate.screening_status or "pending",
        "match_score": candidate.match_score,
        "priority_level": candidate.priority_level,
        "screening_result": candidate.screening_result,
        "screening_reason": candidate.screening_reason,
        "risk_flags": risk_flags,
        "screening_updated_at": candidate.screening_updated_at,
        "created_at": candidate.created_at,
        "job_match_summary": _job_match_summary(candidate, skills),
        "job_requirement_profile": _job_profile_for_candidate(candidate),
    }


@router.post("/run")
def run_batch_screening(
    target_role: Optional[str] = None,
    priority_level: Optional[str] = None,
    screening_status: Optional[str] = Query(None, pattern="^(screened|unscreened)$"),
    decision_status: Optional[str] = Query("pending"),
    date_range: Optional[str] = Query(None, pattern="^(today|this_week|last_7_days|last_30_days)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start, end = _resolve_date_range(date_range, start_date, end_date)
    candidates = candidate_service.run_pending_screening(
        db,
        target_role=target_role,
        priority_level=priority_level,
        screening_status=screening_status,
        decision_status=decision_status,
        start_date=start,
        end_date=end,
    )
    return {
        "processed_count": len(candidates),
        "items": [_screening_to_read(candidate) for candidate in candidates],
        "message": "批量初筛完成，AI结果仅供HR辅助参考，不会自动淘汰候选人。",
    }


@router.post("/run/{candidate_id}")
def run_single_screening(candidate_id: int, db: Session = Depends(get_db)):
    candidate = candidate_service.run_screening_for_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _screening_to_read(candidate)


def _resolve_date_range(
    date_range: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> Tuple[Optional[date], Optional[date]]:
    today = date.today()
    if date_range == "today":
        return today, today
    if date_range == "this_week":
        return today - timedelta(days=today.weekday()), today
    if date_range == "last_7_days":
        return today - timedelta(days=6), today
    if date_range == "last_30_days":
        return today - timedelta(days=29), today
    return start_date, end_date


@router.get("/results")
def get_screening_results(
    target_role: Optional[str] = None,
    priority_level: Optional[str] = None,
    screening_status: Optional[str] = Query(None, pattern="^(screened|unscreened)$"),
    decision_status: Optional[str] = Query("pending"),
    date_range: Optional[str] = Query(None, pattern="^(today|this_week|last_7_days|last_30_days)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: str = Query("created_at", pattern="^(score_desc|score_asc|updated_desc|created_at)$"),
    sort_order: str = Query("desc", pattern="^(desc|asc)$"),
    db: Session = Depends(get_db),
):
    start, end = _resolve_date_range(date_range, start_date, end_date)
    result = candidate_service.get_screening_results_with_stats(
        db,
        target_role=target_role,
        priority_level=priority_level,
        screening_status=screening_status,
        decision_status=decision_status,
        sort_by=sort_by,
        sort_order=sort_order,
        start_date=start,
        end_date=end,
    )
    return {
        "items": [_screening_to_read(candidate) for candidate in result["items"]],
        "total": result["total"],
        "stats": result["stats"],
        "overall_stats": result["overall_stats"],
    }
