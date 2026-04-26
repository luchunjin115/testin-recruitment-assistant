"""Ensure a fresh checkout has runnable demo data.

This script is safe to call on every backend startup:
- create the SQLite database and tables if needed
- create uploads directory if needed
- initialize default jobs only when the job table is empty
- generate demo candidates only when the candidate table is empty
"""
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
os.chdir(str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, init_db, run_migrations  # noqa: E402
from app.models.candidate import Candidate  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.services.job_service import job_service  # noqa: E402
from reset_demo_data import reset_demo_data  # noqa: E402


def ensure_demo_data() -> bool:
    """Return True when demo candidates were generated."""
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    run_migrations()

    db = SessionLocal()
    try:
        job_count = db.query(Job).count()
        if job_count == 0:
            job_service.seed_default_jobs(db)
            job_count = db.query(Job).count()
            print(f"岗位库为空，已初始化默认岗位：{job_count} 个")

        candidate_count = db.query(Candidate).count()
        if candidate_count > 0:
            print(f"已存在候选人数据：{candidate_count} 条，跳过演示数据自动初始化")
            return False
    finally:
        db.close()

    print("候选人表为空，开始自动初始化演示数据...")
    reset_demo_data()
    return True


if __name__ == "__main__":
    ensure_demo_data()
