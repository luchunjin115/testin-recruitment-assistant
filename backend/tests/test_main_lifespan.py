import asyncio
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch

from app.main import lifespan


class MainLifespanTest(IsolatedAsyncioTestCase):
    async def test_lifespan_starts_configured_cleanup_and_cancels_it(self) -> None:
        settings = Mock(
            RESUME_CLEANUP_ENABLED=True,
            V2_STORAGE_DIR="C:/private-storage",
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
            patch("scripts.ensure_demo_data.ensure_demo_data") as ensure_demo,
            patch("app.core.config.get_settings", return_value=settings),
            patch("app.core.database.get_sessionmaker", return_value=session_factory),
            patch(
                "app.services.rebuilt.resume_retention_service.run_resume_retention_loop",
                side_effect=fake_loop,
            ) as cleanup_loop,
        ):
            async with lifespan(Mock()):
                await asyncio.wait_for(started.wait(), timeout=1)
                self.assertIsNotNone(captured_task)
                self.assertFalse(captured_task.done())

        ensure_demo.assert_called_once_with()
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
            patch("scripts.ensure_demo_data.ensure_demo_data"),
            patch("app.core.config.get_settings", return_value=settings),
            patch("app.core.database.get_sessionmaker") as sessionmaker,
            patch(
                "app.services.rebuilt.resume_retention_service.run_resume_retention_loop",
            ) as cleanup_loop,
        ):
            async with lifespan(Mock()):
                pass

        sessionmaker.assert_not_called()
        cleanup_loop.assert_not_called()
