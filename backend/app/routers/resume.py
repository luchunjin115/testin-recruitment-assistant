import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..services.candidate_service import candidate_service
from ..services.file_parser import file_parser

router = APIRouter(prefix="/resume", tags=["简历上传"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("/upload")
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    original_filename = Path(file.filename or "").name
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，支持: {ALLOWED_EXTENSIONS}")

    content = file.file.read()
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"文件大小超过{settings.MAX_FILE_SIZE_MB}MB限制")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        raw_text = file_parser.parse(str(file_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    candidate = candidate_service.create_from_resume(
        db,
        str(file_path),
        raw_text,
        original_filename=original_filename,
        file_size=len(content),
        uploaded_at=datetime.now(),
    )

    from .candidates import _to_read
    return {
        "candidate": _to_read(candidate),
        "extracted_text_preview": raw_text[:500],
    }


@router.post("/parse-preview")
def parse_preview(file: UploadFile = File(...)):
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    content = file.file.read()
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"preview_{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        raw_text = file_parser.parse(str(file_path))
    except ValueError as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    from ..services.ai_service import ai_service
    extracted = ai_service.extract_resume(raw_text)

    os.remove(file_path)

    return {
        "extracted": extracted,
        "raw_text_preview": raw_text[:500],
    }
