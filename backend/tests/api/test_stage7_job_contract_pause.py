from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from app.api.job_evaluation_plans import (
    generate_current_evaluation_plan,
    regenerate_failed_evaluation_plan,
)
from app.api.jobs import create_job, open_job, reopen_job, update_job
from app.schemas.job import JobCreate, JobStatus, JobUpdate


PAUSE_CODE = "JOB_EVALUATION_PLAN_CONTRACT_UPGRADE_IN_PROGRESS"


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


class Stage7JobContractPauseTest(IsolatedAsyncioTestCase):
    async def test_open_job_writes_do_not_enter_old_plan_generation(self) -> None:
        db = Mock()
        legacy_plan_entry = AsyncMock(
            return_value=SimpleNamespace(status="ready", is_current=True)
        )
        adapter_extract = AsyncMock()
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

        with (
            patch(
                "app.services.job_evaluation_plan_service."
                "job_evaluation_plan_service.generate_for_job",
                legacy_plan_entry,
            ),
            patch("app.api.jobs.screening_service.after_plan_changed", AsyncMock()),
            patch(
                "app.adapters.job_evaluation_plan.DeepSeekJobEvaluationPlanAdapter.extract",
                adapter_extract,
            ),
        ):
            operations = (
                (
                    "create_open",
                    create_job,
                    (create_data, db),
                    patch("app.api.jobs.job_service.create_job", AsyncMock(return_value=job)),
                ),
                (
                    "update_open",
                    update_job,
                    (job.id, update_data, db),
                    patch("app.api.jobs.job_service.update_job", AsyncMock(return_value=job)),
                ),
                (
                    "open_draft",
                    open_job,
                    (job.id, db),
                    patch("app.api.jobs.job_service.open_job", AsyncMock(return_value=job)),
                ),
                (
                    "reopen_closed",
                    reopen_job,
                    (job.id, db),
                    patch("app.api.jobs.job_service.reopen_job", AsyncMock(return_value=job)),
                ),
            )
            for name, operation, args, service_patch in operations:
                with self.subTest(operation=name), service_patch:
                    legacy_plan_entry.reset_mock()
                    adapter_extract.reset_mock()
                    await operation(*args)
                    legacy_plan_entry.assert_not_awaited()
                    adapter_extract.assert_not_awaited()

    async def test_explicit_generate_and_regenerate_return_controlled_pause(self) -> None:
        db = Mock()
        adapter_extract = AsyncMock()

        for name, operation, service_path in (
            (
                "generate",
                generate_current_evaluation_plan,
                "app.api.job_evaluation_plans.job_evaluation_plan_service.generate_for_job",
            ),
            (
                "regenerate",
                regenerate_failed_evaluation_plan,
                "app.api.job_evaluation_plans.job_evaluation_plan_service.regenerate_failed_plan",
            ),
        ):
            with self.subTest(operation=name):
                legacy_plan_entry = AsyncMock(
                    side_effect=AssertionError("旧评价计划入口不应执行")
                )
                with (
                    patch(service_path, legacy_plan_entry),
                    patch(
                        "app.adapters.job_evaluation_plan.DeepSeekJobEvaluationPlanAdapter.extract",
                        adapter_extract,
                    ),
                ):
                    with self.assertRaises(HTTPException) as raised:
                        await operation(11, db)

                self.assertEqual(raised.exception.status_code, 503)
                self.assertEqual(raised.exception.detail["code"], PAUSE_CODE)
                self.assertIn("合同升级", raised.exception.detail["message"])
                legacy_plan_entry.assert_not_awaited()
                adapter_extract.assert_not_awaited()
