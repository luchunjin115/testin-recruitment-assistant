import asyncio
from contextlib import asynccontextmanager, suppress
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import activity_logs as rebuilt_activity_logs
from .api import candidates as rebuilt_candidates
from .api import education as rebuilt_education
from .api import jobs as rebuilt_jobs
from .api import project_experiences as rebuilt_project_experiences
from .api import reports as rebuilt_reports
from .api import resumes as rebuilt_resumes
from .api import screening_results as rebuilt_screening_results
from .api import work_experiences as rebuilt_work_experiences
from .config import get_settings
from .routers import ai, apply, candidates, dashboard, jobs, resume, screening, sync


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scripts.ensure_demo_data import ensure_demo_data
    from .core.config import get_settings as get_rebuilt_settings
    from .core.database import get_sessionmaker
    from .services.rebuilt.resume_retention_service import run_resume_retention_loop

    ensure_demo_data()
    rebuilt_settings = get_rebuilt_settings()
    cleanup_task = None
    if rebuilt_settings.RESUME_CLEANUP_ENABLED:
        cleanup_task = asyncio.create_task(
            run_resume_retention_loop(
                session_factory=get_sessionmaker(),
                storage_root=Path(rebuilt_settings.V2_STORAGE_DIR),
                retention_hours=rebuilt_settings.RESUME_UNBOUND_RETENTION_HOURS,
                interval_seconds=(
                    rebuilt_settings.RESUME_CLEANUP_INTERVAL_MINUTES * 60
                ),
                batch_size=rebuilt_settings.RESUME_CLEANUP_BATCH_SIZE,
                processing_lease_seconds=(
                    rebuilt_settings.RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS
                ),
            ),
            name="resume-retention-cleanup",
        )
    try:
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


settings = get_settings()

app = FastAPI(
    title="Testin云测招聘助手",
    description="AI驱动的招聘数据自动化记录与跟踪系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(screening.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(apply.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(rebuilt_activity_logs.router, prefix="/api/v2")
app.include_router(rebuilt_candidates.router, prefix="/api/v2")
app.include_router(rebuilt_education.router, prefix="/api/v2")
app.include_router(rebuilt_jobs.router, prefix="/api/v2")
app.include_router(rebuilt_project_experiences.router, prefix="/api/v2")
app.include_router(rebuilt_reports.router, prefix="/api/v2")
app.include_router(rebuilt_resumes.router, prefix="/api/v2")
app.include_router(rebuilt_screening_results.router, prefix="/api/v2")
app.include_router(rebuilt_work_experiences.router, prefix="/api/v2")

upload_dir = settings.UPLOAD_DIR
Path(upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Testin云测招聘助手"}
