from contextlib import asynccontextmanager
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import ai, apply, candidates, dashboard, jobs, resume, screening, sync


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scripts.ensure_demo_data import ensure_demo_data

    ensure_demo_data()
    yield


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

upload_dir = settings.UPLOAD_DIR
Path(upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Testin云测招聘助手"}
