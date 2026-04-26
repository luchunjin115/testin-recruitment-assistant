import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas.candidate import CandidateCreate
from ..services.candidate_service import candidate_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apply", tags=["在线投递"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")


@router.post("/")
def submit_application(
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    school: str = Form(""),
    degree: str = Form(""),
    major: str = Form(""),
    job_id: int = Form(...),
    target_role: str = Form(""),
    skills: str = Form("[]"),
    self_intro: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="请输入姓名")
    name = name.strip()

    if not PHONE_REGEX.match(phone):
        raise HTTPException(status_code=400, detail="请输入有效的手机号码")

    from ..services.job_service import job_service
    job = job_service.get_active_job(db, job_id)
    if not job:
        raise HTTPException(status_code=400, detail="所选岗位不存在或已停用，请刷新页面后重新选择")

    try:
        skills_list = json.loads(skills)
        if not isinstance(skills_list, list):
            skills_list = []
    except (json.JSONDecodeError, TypeError):
        skills_list = []

    resume_path = ""
    if file and file.filename:
        settings = get_settings()
        original_filename = Path(file.filename).name
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

        with open(file_path, "wb") as f:
            f.write(content)

        resume_path = str(file_path)
        resume_original_filename = original_filename
        resume_file_size = len(content)
        resume_uploaded_at = datetime.now()
    else:
        resume_original_filename = ""
        resume_file_size = None
        resume_uploaded_at = None

    data = CandidateCreate(
        name=name,
        phone=phone,
        email=email.strip(),
        school=school.strip(),
        degree=degree.strip(),
        major=major.strip(),
        job_id=job.id,
        target_role=job.title,
        experience_years=0,
        experience_desc="",
        skills=skills_list,
        self_intro=self_intro.strip(),
        source_channel="在线投递",
        hr_notes="",
    )

    try:
        candidate = candidate_service.create_candidate(db, data, source="在线投递")
    except ValueError as exc:
        db.rollback()
        if resume_path:
            resume_file = Path(resume_path)
            if resume_file.exists():
                resume_file.unlink()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError:
        db.rollback()
        if resume_path:
            resume_file = Path(resume_path)
            if resume_file.exists():
                resume_file.unlink()
        raise HTTPException(
            status_code=409,
            detail="该手机号已提交过申请，请勿重复投递",
        )

    if resume_path:
        candidate_service.attach_resume(
            db,
            candidate,
            file_path=resume_path,
            original_filename=resume_original_filename,
            file_size=resume_file_size,
            uploaded_at=resume_uploaded_at,
        )

    return {"success": True, "message": "投递成功！我们已收到您的信息，会尽快审核。"}
