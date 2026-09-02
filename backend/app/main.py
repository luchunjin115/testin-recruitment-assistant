import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import activity_logs
from .api import applications
from .api import candidates
from .api import education
from .api import health
from .api import jobs
from .api import job_evaluation_plans
from .api import project_experiences
from .api import public
from .api import public_application_workbench
from .api import reports
from .api import resumes
from .api import screening
from .api import work_experiences
from .core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .core.database import get_sessionmaker
    from .services.application_processing_service import (
        run_application_processing_worker_loop,
    )
    from .services.resume_retention_service import run_resume_retention_loop
    from .services.screening_service import run_screening_worker_loop

    cleanup_task = None
    application_processing_task = None
    screening_task = None
    if settings.RESUME_CLEANUP_ENABLED:
        cleanup_task = asyncio.create_task(
            run_resume_retention_loop(
                session_factory=get_sessionmaker(),
                storage_root=Path(settings.STORAGE_DIR),
                retention_hours=settings.RESUME_UNBOUND_RETENTION_HOURS,
                interval_seconds=(
                    settings.RESUME_CLEANUP_INTERVAL_MINUTES * 60
                ),
                batch_size=settings.RESUME_CLEANUP_BATCH_SIZE,
                processing_lease_seconds=(
                    settings.RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS
                ),
            ),
            name="resume-retention-cleanup",
        )
    if getattr(settings, "SCREENING_WORKER_ENABLED", False) is True:
        screening_task = asyncio.create_task(
            run_screening_worker_loop(
                session_factory=get_sessionmaker(),
                interval_seconds=settings.SCREENING_WORKER_POLL_SECONDS,
                lease_seconds=settings.SCREENING_WORKER_LEASE_SECONDS,
                batch_size=settings.SCREENING_WORKER_BATCH_SIZE,
            ),
            name="screening-postgres-worker",
        )
    if getattr(settings, "APPLICATION_PROCESSING_WORKER_ENABLED", False) is True:
        application_processing_task = asyncio.create_task(
            run_application_processing_worker_loop(
                session_factory=get_sessionmaker(),
                interval_seconds=settings.APPLICATION_PROCESSING_WORKER_POLL_SECONDS,
                lease_seconds=settings.APPLICATION_PROCESSING_WORKER_LEASE_SECONDS,
                batch_size=settings.APPLICATION_PROCESSING_WORKER_BATCH_SIZE,
                max_attempts=settings.APPLICATION_PROCESSING_MAX_ATTEMPTS,
            ),
            name="application-processing-postgres-worker",
        )
    try:
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
        if application_processing_task is not None:
            application_processing_task.cancel()
            with suppress(asyncio.CancelledError):
                await application_processing_task
        if screening_task is not None:
            screening_task.cancel()
            with suppress(asyncio.CancelledError):
                await screening_task


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="基于 PostgreSQL 与 DeepSeek 的 AI 招聘提效平台",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    public.PublicApplicationBodyLimitMiddleware,
    max_body_size=(
        settings.MAX_FILE_SIZE_MB * 1024 * 1024
        + settings.PUBLIC_APPLICATION_MAX_FORM_OVERHEAD_BYTES
    ),
)
jobs.install_job_exception_handlers(app)
applications.install_application_exception_handlers(app)
screening.install_screening_exception_handlers(app)
public.install_public_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(activity_logs.router, prefix="/api/v2")
app.include_router(applications.router, prefix="/api/v2")
app.include_router(candidates.router, prefix="/api/v2")
app.include_router(education.router, prefix="/api/v2")
app.include_router(jobs.router, prefix="/api/v2")
app.include_router(job_evaluation_plans.router, prefix="/api/v2")
app.include_router(project_experiences.router, prefix="/api/v2")
app.include_router(public.router, prefix="/api/v2")
app.include_router(public_application_workbench.router, prefix="/api/v2")
app.include_router(reports.router, prefix="/api/v2")
app.include_router(resumes.router, prefix="/api/v2")
app.include_router(screening.router, prefix="/api/v2")
app.include_router(work_experiences.router, prefix="/api/v2")
