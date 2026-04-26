import csv
import io
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas.candidate import (
    CandidateCreate, CandidateDetailRead, CandidateRead, CandidateUpdate,
    StageUpdate, VALID_STAGES, VALID_HR_ACTIONS, HRActionRequest,
    StageChangeLogRead, BatchStatusRequest, BatchIdsRequest,
)
from ..services.ai_service import ai_service
from ..services.candidate_service import candidate_service
from ..services.file_parser import file_parser
from ..services.followup_service import followup_service

router = APIRouter(prefix="/candidates", tags=["候选人管理"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")


def _build_resume_info(c) -> dict:
    resume_path = (c.resume_path or "").strip()
    if not resume_path:
        return {
            "resume_path": "",
            "resume_filename": "",
            "resume_file_type": "",
            "resume_file_size": None,
            "resume_url": "",
            "resume_uploaded_at": None,
        }

    file_path = Path(resume_path)
    if not file_path.exists():
        settings = get_settings()
        upload_dir = Path(settings.UPLOAD_DIR)
        alt_path = upload_dir / file_path.name
        if alt_path.exists():
            file_path = alt_path
    file_exists = file_path.exists()

    resume_filename = (c.resume_filename or "").strip() or file_path.name
    resume_file_type = (c.resume_file_type or "").strip().lower()
    if not resume_file_type and Path(resume_filename).suffix:
        resume_file_type = Path(resume_filename).suffix.lower().lstrip(".")

    resume_file_size = c.resume_file_size
    if resume_file_size is None and file_exists:
        resume_file_size = file_path.stat().st_size

    resume_uploaded_at = c.resume_uploaded_at
    if resume_uploaded_at is None and file_exists:
        resume_uploaded_at = datetime.fromtimestamp(file_path.stat().st_mtime)

    return {
        "resume_path": resume_path,
        "resume_filename": resume_filename,
        "resume_file_type": resume_file_type,
        "resume_file_size": resume_file_size,
        "resume_url": f"/uploads/{quote(file_path.name)}" if file_exists and file_path.name else "",
        "resume_uploaded_at": resume_uploaded_at,
    }


def _to_read(c) -> dict:
    skills = c.skills
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except Exception:
            skills = []
    ai_tags = c.ai_tags
    if isinstance(ai_tags, str):
        try:
            ai_tags = json.loads(ai_tags)
        except Exception:
            ai_tags = []
    risk_flags = c.risk_flags
    if isinstance(risk_flags, str):
        try:
            risk_flags = json.loads(risk_flags)
        except Exception:
            risk_flags = []
    interview_ai_risk_points = c.interview_ai_risk_points
    if isinstance(interview_ai_risk_points, str):
        try:
            interview_ai_risk_points = json.loads(interview_ai_risk_points)
        except Exception:
            interview_ai_risk_points = []
    data = {
        "id": c.id, "name": c.name, "phone": c.phone, "email": c.email,
        "school": c.school, "degree": c.degree, "major": c.major,
        "job_id": c.job_id,
        "target_role": c.target_role, "experience_years": c.experience_years,
        "experience_desc": c.experience_desc, "skills": skills,
        "self_intro": c.self_intro,
        "source_channel": c.source_channel, "stage": c.stage,
        "screening_status": c.screening_status or "pending",
        **candidate_service.get_new_candidate_marker(c),
        "interview_time": c.interview_time,
        "interview_method": c.interview_method,
        "interviewer": c.interviewer,
        "interview_note": c.interview_note,
        "interview_feedback_text": c.interview_feedback_text,
        "interview_round": c.interview_round,
        "feedback_time": c.feedback_time,
        "interview_ai_technical_summary": c.interview_ai_technical_summary,
        "interview_ai_communication_summary": c.interview_ai_communication_summary,
        "interview_ai_job_match": c.interview_ai_job_match,
        "interview_ai_risk_points": interview_ai_risk_points,
        "interview_ai_recommendation": c.interview_ai_recommendation,
        "interview_ai_next_step": c.interview_ai_next_step,
        "interview_ai_generated_at": c.interview_ai_generated_at,
        "recheck_note": c.recheck_note,
        "second_interview_time": c.second_interview_time,
        "second_interviewer": c.second_interviewer,
        "offer_position": c.offer_position,
        "salary_range": c.salary_range,
        "expected_onboard_date": c.expected_onboard_date,
        "offer_note": c.offer_note,
        "onboard_date": c.onboard_date,
        "onboard_note": c.onboard_note,
        "reject_reason": c.reject_reason,
        "reject_note": c.reject_note,
        "stage_source": c.stage_source,
        "ai_summary": c.ai_summary, "ai_tags": ai_tags,
        "match_score": c.match_score,
        "priority_level": c.priority_level,
        "screening_result": c.screening_result,
        "screening_reason": c.screening_reason,
        "risk_flags": risk_flags,
        "screening_updated_at": c.screening_updated_at,
        **followup_service.generate_followup_suggestion(c),
        "hr_notes": c.hr_notes, "follow_up_date": c.follow_up_date,
        "is_duplicate": c.is_duplicate, "duplicate_of_id": c.duplicate_of_id,
        "created_at": c.created_at, "updated_at": c.updated_at,
    }
    data.update(_build_resume_info(c))
    return data


def _clean_text(value: Optional[str]) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip() if isinstance(value, str) else str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="工作年限格式不正确") from exc


def _parse_skills(skills_raw: str) -> list[str]:
    try:
        items = json.loads(skills_raw or "[]")
    except (TypeError, json.JSONDecodeError):
        items = []

    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _merge_resume_suggestions(manual_data: dict, extracted: dict) -> dict:
    merged = dict(manual_data)
    for field in [
        "name",
        "phone",
        "email",
        "school",
        "degree",
        "major",
        "target_role",
        "experience_desc",
        "self_intro",
    ]:
        if merged.get(field):
            continue
        extracted_value = extracted.get(field)
        if isinstance(extracted_value, str):
            extracted_value = extracted_value.strip()
        if extracted_value:
            merged[field] = extracted_value

    if not merged.get("skills") and isinstance(extracted.get("skills"), list):
        merged["skills"] = [
            str(item).strip() for item in extracted["skills"] if str(item).strip()
        ]

    if merged.get("experience_years") is None:
        extracted_years = extracted.get("experience_years")
        if extracted_years not in (None, ""):
            try:
                merged["experience_years"] = float(extracted_years)
            except (TypeError, ValueError):
                pass

    if merged.get("experience_years") is None:
        merged["experience_years"] = 0

    return merged


def _save_resume_file(file: UploadFile) -> tuple[str, str, int, datetime, dict]:
    settings = get_settings()
    original_filename = Path(file.filename or "").name
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式，支持 PDF、DOCX、TXT",
        )

    content = file.file.read()
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过{settings.MAX_FILE_SIZE_MB}MB限制",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as output:
        output.write(content)

    extracted = {}
    try:
        raw_text = file_parser.parse(str(file_path))
        extracted = ai_service.extract_resume(raw_text)
    except Exception:
        extracted = {}

    return str(file_path), original_filename, len(content), datetime.now(), extracted


@router.post("/", response_model=CandidateRead)
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    try:
        candidate = candidate_service.create_candidate(db, data, source="HR手动录入")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_read(candidate)


@router.post("/hr-create", response_model=CandidateRead)
def create_hr_candidate(
    name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    school: str = Form(""),
    degree: str = Form(""),
    major: str = Form(""),
    job_id: Optional[int] = Form(None),
    target_role: str = Form(""),
    experience_years: str = Form(""),
    experience_desc: str = Form(""),
    skills: str = Form("[]"),
    self_intro: str = Form(""),
    source_channel: str = Form("HR手动录入"),
    hr_notes: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    resume_path = ""
    resume_original_filename = ""
    resume_file_size = None
    resume_uploaded_at = None
    extracted = {}

    def cleanup_resume():
        if resume_path:
            resume_file = Path(resume_path)
            if resume_file.exists():
                resume_file.unlink()

    try:
        manual_data = {
            "name": _clean_text(name),
            "phone": _clean_text(phone),
            "email": _clean_text(email),
            "school": _clean_text(school),
            "degree": _clean_text(degree),
            "major": _clean_text(major),
            "job_id": job_id,
            "target_role": _clean_text(target_role),
            "experience_years": _parse_optional_float(experience_years),
            "experience_desc": _clean_text(experience_desc),
            "skills": _parse_skills(skills),
            "self_intro": _clean_text(self_intro),
        }

        if file and file.filename:
            (
                resume_path,
                resume_original_filename,
                resume_file_size,
                resume_uploaded_at,
                extracted,
            ) = _save_resume_file(file)

        merged = _merge_resume_suggestions(manual_data, extracted)
        if not merged["name"]:
            raise HTTPException(status_code=400, detail="请输入姓名，或上传可识别姓名的简历")
        if not PHONE_REGEX.match(merged["phone"]):
            raise HTTPException(status_code=400, detail="请输入有效手机号，或上传可识别手机号的简历")

        data = CandidateCreate(
            name=merged["name"],
            phone=merged["phone"],
            email=merged["email"],
            school=merged["school"],
            degree=merged["degree"],
            major=merged["major"],
            job_id=merged.get("job_id"),
            target_role=merged["target_role"],
            experience_years=merged["experience_years"],
            experience_desc=merged["experience_desc"],
            skills=merged["skills"],
            self_intro=merged["self_intro"],
            source_channel=_clean_text(source_channel) or "HR手动录入",
            hr_notes=_clean_text(hr_notes),
        )

        try:
            candidate = candidate_service.create_candidate(db, data, source="HR手动录入")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if resume_path:
            candidate = candidate_service.attach_resume(
                db,
                candidate,
                file_path=resume_path,
                original_filename=resume_original_filename,
                file_size=resume_file_size,
                uploaded_at=resume_uploaded_at,
            )
        return _to_read(candidate)
    except IntegrityError:
        db.rollback()
        cleanup_resume()
        raise HTTPException(status_code=409, detail="该手机号已存在，请检查是否重复录入")
    except HTTPException:
        cleanup_resume()
        raise


@router.get("/")
def list_candidates(
    target_role: Optional[str] = None,
    stage: Optional[str] = None,
    channel: Optional[str] = None,
    recruiting_stage: Optional[str] = None,
    source_channel: Optional[str] = None,
    candidate_scope: str = Query("formal", pattern="^(formal|backup|rejected)$"),
    screening_status: Optional[str] = Query(None, pattern="^(pending|passed|backup|rejected)$"),
    is_today_new: bool = Query(False),
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    candidates, total = candidate_service.list_candidates(
        db,
        target_role=target_role,
        stage=stage or recruiting_stage,
        channel=channel or source_channel,
        candidate_scope=candidate_scope,
        screening_status=screening_status,
        keyword=keyword,
        is_today_new=is_today_new,
        page=page, page_size=page_size,
    )
    return {
        "items": [_to_read(c) for c in candidates],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/filter-options")
def get_filter_options(db: Session = Depends(get_db)):
    return candidate_service.get_filter_options(db)


@router.post("/{candidate_id}/screening/pass", response_model=CandidateRead)
def pass_screening(candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = candidate_service.pass_screening(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


@router.post("/{candidate_id}/screening/backup", response_model=CandidateRead)
def mark_screening_backup(candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = candidate_service.mark_screening_backup(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


@router.post("/{candidate_id}/screening/reject", response_model=CandidateRead)
def reject_screening(
    candidate_id: int,
    data: HRActionRequest,
    db: Session = Depends(get_db),
):
    try:
        candidate = candidate_service.reject_screening(
            db,
            candidate_id,
            reject_reason=data.reject_reason or data.reason or "",
            reject_note=data.reject_note or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


def _validate_batch_ids(candidate_ids):
    if not candidate_ids:
        raise HTTPException(status_code=400, detail="candidate_ids 不能为空")


@router.post("/batch/status")
def batch_update_status(data: BatchStatusRequest, db: Session = Depends(get_db)):
    _validate_batch_ids(data.candidate_ids)
    try:
        return candidate_service.batch_update_stage(
            db,
            candidate_ids=data.candidate_ids,
            target_stage=data.target_stage,
            reason=data.reason,
            source=data.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch/followup")
def batch_generate_followup(data: BatchIdsRequest, db: Session = Depends(get_db)):
    _validate_batch_ids(data.candidate_ids)
    try:
        return candidate_service.batch_generate_followups(db, data.candidate_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch/export")
def batch_export_csv(data: BatchIdsRequest, db: Session = Depends(get_db)):
    _validate_batch_ids(data.candidate_ids)
    try:
        candidates = candidate_service.get_candidates_by_ids(db, data.candidate_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    found_ids = {candidate.id for candidate in candidates}
    missing_ids = [candidate_id for candidate_id in data.candidate_ids if candidate_id not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"候选人不存在: {missing_ids}")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "姓名", "手机号", "邮箱", "学校", "学历", "专业", "应聘岗位",
        "当前阶段", "来源渠道", "AI摘要", "AI跟进建议", "创建时间",
    ])
    for candidate in candidates:
        read_data = _to_read(candidate)
        writer.writerow([
            read_data["name"],
            read_data["phone"],
            read_data["email"],
            read_data["school"],
            read_data["degree"],
            read_data["major"],
            read_data["target_role"],
            read_data["stage"],
            read_data["source_channel"],
            read_data["ai_summary"],
            read_data.get("followup_suggestion", ""),
            read_data["created_at"],
        ])

    candidate_service.log_batch_export(db, candidates)
    content = "\ufeff" + buffer.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=selected_candidates.csv"},
    )


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    data = _to_read(candidate)
    data["activity_logs"] = [
        {
            "id": log.id,
            "candidate_id": log.candidate_id,
            "action": log.action,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in candidate.activity_logs
    ]
    return data


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(candidate_id: int, data: CandidateUpdate, db: Session = Depends(get_db)):
    try:
        candidate = candidate_service.update_candidate(db, candidate_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


@router.patch("/{candidate_id}/stage", response_model=CandidateRead)
def update_stage(candidate_id: int, data: StageUpdate, db: Session = Depends(get_db)):
    if data.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"无效阶段: {data.stage}")
    candidate = candidate_service.update_stage(db, candidate_id, data.stage)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    success = candidate_service.delete_candidate(db, candidate_id)
    if not success:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return {"message": "删除成功"}


@router.post("/{candidate_id}/hr-action/{action_name}", response_model=CandidateRead)
def execute_hr_action(
    candidate_id: int,
    action_name: str,
    data: HRActionRequest,
    db: Session = Depends(get_db),
):
    if action_name not in VALID_HR_ACTIONS:
        raise HTTPException(status_code=400, detail=f"未知的HR操作: {action_name}，有效值: {VALID_HR_ACTIONS}")
    try:
        candidate = candidate_service.execute_hr_action(db, candidate_id, action_name, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return _to_read(candidate)


@router.get("/{candidate_id}/stage-logs")
def get_stage_logs(candidate_id: int, db: Session = Depends(get_db)):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    logs = candidate_service.get_stage_change_logs(db, candidate_id)
    return logs
