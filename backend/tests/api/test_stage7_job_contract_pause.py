from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import BackgroundTasks

from app.api.job_evaluation_plans import (
    confirm_current_evaluation_plan,
    generate_current_evaluation_plan,
    regenerate_failed_evaluation_plan,
)
from app.api.jobs import create_job, open_job, reopen_job, update_job
from app.schemas.job import JobCreate, JobStatus, JobUpdate
from app.schemas.job_evaluation_plan import JobEvaluationPlanRead
from tests.fixtures.job_evaluation_plan_v4 import make_v4_plan


def open_job_record():
    return SimpleNamespace(
        id=11,
        status="open",
        title="AI 应用工程师",
        department="研发部",
        location="长沙",
        employment_type="full_time",
        headcount=2,
        job_background="建设 AI 应用平台",
        job_responsibilities="负责 AI 应用设计与交付",
        candidate_requirements="具备后端开发经验",
        preferred_qualifications=None,
        public_notes=None,
    )


class Stage7JobContractGenerationTest(IsolatedAsyncioTestCase):
    async def test_open_transitions_schedule_generation_but_open_edit_only_outdates(self) -> None:
        db = Mock()
        job = open_job_record()
        create_data = JobCreate.model_construct(
            title=job.title,
            status=JobStatus.OPEN,
            job_responsibilities=job.job_responsibilities,
            candidate_requirements=job.candidate_requirements,
        )
        update_data = JobUpdate.model_construct(
            job_background="新背景",
            _fields_set={"job_background"},
        )

        operations = (
            ("create_open", create_job, (create_data,), "create_job"),
            ("open_draft", open_job, (job.id,), "open_job"),
            ("reopen_closed", reopen_job, (job.id,), "reopen_job"),
        )
        for name, operation, args, service_method in operations:
            background = BackgroundTasks()
            with self.subTest(operation=name), patch(
                f"app.api.jobs.job_service.{service_method}",
                AsyncMock(return_value=job),
            ):
                await operation(*args, background, db)
            self.assertEqual(len(background.tasks), 1)

        outdate = AsyncMock(return_value=None)
        background = BackgroundTasks()
        with (
            patch("app.api.jobs.job_service.update_job", AsyncMock(return_value=job)),
            patch(
                "app.api.jobs.mark_evaluation_plan_outdated_after_job_commit",
                outdate,
            ),
        ):
            await update_job(job.id, update_data, db)
        outdate.assert_awaited_once_with(job.id)
        self.assertEqual(len(background.tasks), 0)

    async def test_explicit_generate_regenerate_and_confirm_use_v4_state_flow(self) -> None:
        db = Mock()
        db.rollback = AsyncMock()
        operations = (
            (
                generate_current_evaluation_plan,
                "generate_for_job",
                "pending_confirmation",
                False,
            ),
            (
                regenerate_failed_evaluation_plan,
                "regenerate_failed_plan",
                "pending_confirmation",
                False,
            ),
            (
                confirm_current_evaluation_plan,
                "confirm_current_plan",
                "ready",
                True,
            ),
        )
        for operation, service_name, plan_status, plan_ready in operations:
            plan = SimpleNamespace(status=plan_status)
            read_model = JobEvaluationPlanRead.model_validate(
                make_v4_plan(status=plan_status)
            )
            service = AsyncMock(return_value=plan)
            notify = AsyncMock(return_value=None)
            with (
                patch(
                    f"app.api.job_evaluation_plans.job_evaluation_plan_service.{service_name}",
                    service,
                ),
                patch(
                    "app.api.job_evaluation_plans.job_evaluation_plan_service.build_read_model",
                    Mock(return_value=read_model),
                ),
                patch(
                    "app.api.job_evaluation_plans._notify_screening_plan_changed",
                    notify,
                ),
            ):
                result = await operation(11, db)
            self.assertEqual(result.schema_version, "4.0")
            self.assertEqual(result.status.value, plan_status)
            service.assert_awaited_once_with(db, 11)
            notify.assert_awaited_once_with(db, 11, plan_ready=plan_ready)
