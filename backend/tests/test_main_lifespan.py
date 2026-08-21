import asyncio
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.main import app, lifespan


class MainLifespanTest(IsolatedAsyncioTestCase):
    async def test_lifespan_starts_configured_cleanup_and_cancels_it(self) -> None:
        settings = Mock(
            RESUME_CLEANUP_ENABLED=True,
            STORAGE_DIR="C:/private-storage",
            RESUME_UNBOUND_RETENTION_HOURS=24,
            RESUME_CLEANUP_INTERVAL_MINUTES=60,
            RESUME_CLEANUP_BATCH_SIZE=50,
            RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS=180,
        )
        session_factory = Mock()
        started = asyncio.Event()
        captured_task = None

        async def fake_loop(**kwargs):
            nonlocal captured_task
            captured_task = asyncio.current_task()
            started.set()
            await asyncio.Event().wait()

        with (
            patch("app.main.settings", settings),
            patch("app.core.database.get_sessionmaker", return_value=session_factory),
            patch(
                "app.services.resume_retention_service.run_resume_retention_loop",
                side_effect=fake_loop,
            ) as cleanup_loop,
        ):
            async with lifespan(Mock()):
                await asyncio.wait_for(started.wait(), timeout=1)
                self.assertIsNotNone(captured_task)
                self.assertFalse(captured_task.done())

        cleanup_loop.assert_called_once_with(
            session_factory=session_factory,
            storage_root=Path("C:/private-storage"),
            retention_hours=24,
            interval_seconds=3600,
            batch_size=50,
            processing_lease_seconds=180,
        )
        self.assertTrue(captured_task.cancelled())

    async def test_lifespan_does_not_start_cleanup_when_disabled(self) -> None:
        settings = Mock(RESUME_CLEANUP_ENABLED=False)

        with (
            patch("app.main.settings", settings),
            patch("app.core.database.get_sessionmaker") as sessionmaker,
            patch(
                "app.services.resume_retention_service.run_resume_retention_loop",
            ) as cleanup_loop,
        ):
            async with lifespan(Mock()):
                pass

        sessionmaker.assert_not_called()
        cleanup_loop.assert_not_called()

    async def test_lifespan_does_not_scan_or_generate_evaluation_plans(self) -> None:
        settings = Mock(
            RESUME_CLEANUP_ENABLED=False,
            SCREENING_WORKER_ENABLED=False,
        )

        with (
            patch("app.main.settings", settings),
            patch(
                "app.services.job_evaluation_plan_service."
                "job_evaluation_plan_service.generate_for_job",
                AsyncMock(),
            ) as generate_plan,
        ):
            async with lifespan(Mock()):
                pass

        generate_plan.assert_not_awaited()

    async def test_lifespan_starts_and_cancels_postgres_screening_worker(self) -> None:
        settings = Mock(
            RESUME_CLEANUP_ENABLED=False,
            SCREENING_WORKER_ENABLED=True,
            SCREENING_WORKER_POLL_SECONDS=1,
            SCREENING_WORKER_LEASE_SECONDS=300,
            SCREENING_WORKER_BATCH_SIZE=5,
        )
        session_factory = Mock()
        started = asyncio.Event()
        captured_task = None

        async def fake_worker(**kwargs):
            nonlocal captured_task
            captured_task = asyncio.current_task()
            started.set()
            await asyncio.Event().wait()

        with (
            patch("app.main.settings", settings),
            patch("app.core.database.get_sessionmaker", return_value=session_factory),
            patch(
                "app.services.screening_service.run_screening_worker_loop",
                side_effect=fake_worker,
            ) as worker_loop,
        ):
            async with lifespan(Mock()):
                await asyncio.wait_for(started.wait(), timeout=1)
                self.assertFalse(captured_task.done())

        worker_loop.assert_called_once_with(
            session_factory=session_factory,
            interval_seconds=1,
            lease_seconds=300,
            batch_size=5,
        )
        self.assertTrue(captured_task.cancelled())

    def test_main_registers_only_versioned_business_routes(self) -> None:
        api_paths = {
            route.path
            for route in app.routes
            if getattr(route, "path", "").startswith("/api")
        }

        self.assertIn("/api/health", api_paths)
        self.assertTrue(
            all(
                path == "/api/health" or path.startswith("/api/v2/")
                for path in api_paths
            )
        )
        self.assertNotIn("/uploads", {route.path for route in app.routes})

    def test_health_works_and_retired_routes_are_unavailable(self) -> None:
        with TestClient(app) as client:
            health = client.get("/api/health")
            old_jobs = client.get("/api/jobs")
            old_upload = client.get("/uploads/retired.txt")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "hr-agent-platform")
        self.assertEqual(old_jobs.status_code, 404)
        self.assertEqual(old_upload.status_code, 404)
