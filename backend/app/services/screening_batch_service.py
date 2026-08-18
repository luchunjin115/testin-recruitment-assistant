from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.job import Job
from app.schemas.screening_batch import (
    ScreeningBatchItemResult,
    ScreeningBatchItemStatus,
    ScreeningBatchRunRequest,
    ScreeningBatchRunResponse,
    ScreeningBatchSummary,
)
from app.services.screening_service import (
    ScreeningAlreadyRunningError,
    ScreeningApplicationNotFoundError,
    ScreeningNotAllowedError,
    ScreeningRunOutcome,
    ScreeningService,
    screening_service,
)


class ScreeningBatchServiceError(ValueError):
    pass


class ScreeningBatchJobNotFoundError(ScreeningBatchServiceError):
    pass


class ScreeningBatchJobNotOpenError(ScreeningBatchServiceError):
    pass


class ScreeningBatchApplicationsNotFoundError(ScreeningBatchServiceError):
    def __init__(self, application_ids: Sequence[int]) -> None:
        self.application_ids = tuple(application_ids)
        super().__init__("批次中存在找不到的 Application")


class ScreeningBatchJobMismatchError(ScreeningBatchServiceError):
    def __init__(self, application_ids: Sequence[int]) -> None:
        self.application_ids = tuple(application_ids)
        super().__init__("批次中的 Application 不属于指定岗位")


class ScreeningBatchService:
    """Run a small same-job batch while keeping each Application transaction isolated."""

    def __init__(self, *, single_service: ScreeningService | None = None) -> None:
        self.single_service = single_service or screening_service

    async def run(
        self,
        db: AsyncSession,
        job_id: int,
        request: ScreeningBatchRunRequest,
    ) -> ScreeningBatchRunResponse:
        applications = await self._validate_scope(
            db,
            job_id,
            request.application_ids,
        )
        by_id = {application.id: application for application in applications}
        single_request = request.to_single_run_request()
        items: list[ScreeningBatchItemResult] = []

        for application_id in request.application_ids:
            application = by_id[application_id]
            if request.retry_failed_only and application.ai_status != "failed":
                items.append(
                    self._skipped(
                        application_id,
                        "SCREENING_NOT_FAILED",
                        "该 Application 当前不是 failed，未执行重试",
                    )
                )
                continue

            try:
                outcome = await self.single_service.run(
                    db,
                    application_id,
                    single_request,
                    actor_type="hr",
                    actor_label="HR batch screening",
                )
            except ScreeningAlreadyRunningError:
                items.append(
                    self._skipped(
                        application_id,
                        "SCREENING_ALREADY_RUNNING",
                        "该 Application 正在评分，本批次未重复启动",
                    )
                )
            except ScreeningApplicationNotFoundError:
                items.append(
                    self._skipped(
                        application_id,
                        "APPLICATION_NOT_FOUND",
                        "Application 已不存在，本批次未启动评分",
                    )
                )
            except ScreeningNotAllowedError:
                items.append(
                    self._skipped(
                        application_id,
                        "SCREENING_NOT_ALLOWED",
                        "Application 当前状态或资料不允许启动评分",
                    )
                )
            except Exception:
                await db.rollback()
                items.append(
                    ScreeningBatchItemResult(
                        application_id=application_id,
                        status=ScreeningBatchItemStatus.FAILED,
                        error_code="SCREENING_ITEM_FAILED",
                        error_message="该项评分执行失败，其他项目不受影响",
                    )
                )
            else:
                items.append(self._from_outcome(application_id, outcome))

        return ScreeningBatchRunResponse(
            job_id=job_id,
            items=items,
            summary=self._summary(items),
        )

    @staticmethod
    async def _validate_scope(
        db: AsyncSession,
        job_id: int,
        application_ids: Sequence[int],
    ) -> list[Application]:
        job = await db.get(Job, job_id)
        if job is None:
            raise ScreeningBatchJobNotFoundError("岗位不存在")
        if job.status != "open":
            raise ScreeningBatchJobNotOpenError("岗位当前不是 open 状态")

        query_result = await db.execute(
            select(Application).where(Application.id.in_(application_ids))
        )
        applications = list(query_result.scalars().all())
        found_ids = {application.id for application in applications}
        missing_ids = [item for item in application_ids if item not in found_ids]
        if missing_ids:
            raise ScreeningBatchApplicationsNotFoundError(missing_ids)

        mismatched_ids = [
            application.id
            for application in applications
            if application.job_id != job_id
        ]
        if mismatched_ids:
            raise ScreeningBatchJobMismatchError(mismatched_ids)
        return applications

    @staticmethod
    def _skipped(
        application_id: int,
        code: str,
        message: str,
    ) -> ScreeningBatchItemResult:
        return ScreeningBatchItemResult(
            application_id=application_id,
            status=ScreeningBatchItemStatus.SKIPPED,
            error_code=code,
            error_message=message,
        )

    @staticmethod
    def _from_outcome(
        application_id: int,
        outcome: ScreeningRunOutcome,
    ) -> ScreeningBatchItemResult:
        result = outcome.result
        item_status = (
            ScreeningBatchItemStatus.REUSED
            if outcome.reused
            else ScreeningBatchItemStatus(result.execution_status)
        )
        return ScreeningBatchItemResult(
            application_id=application_id,
            status=item_status,
            screening_result_id=result.id,
            attempt_number=result.attempt_number,
            reused=outcome.reused,
            model_called=outcome.model_called,
            error_code=result.error_code,
            error_message=result.error_message,
        )

    @staticmethod
    def _summary(items: Sequence[ScreeningBatchItemResult]) -> ScreeningBatchSummary:
        counts = {status: 0 for status in ScreeningBatchItemStatus}
        for item in items:
            counts[item.status] += 1
        return ScreeningBatchSummary(
            selected=len(items),
            executed=len(items) - counts[ScreeningBatchItemStatus.SKIPPED],
            completed=counts[ScreeningBatchItemStatus.COMPLETED],
            failed=counts[ScreeningBatchItemStatus.FAILED],
            blocked=counts[ScreeningBatchItemStatus.BLOCKED],
            reused=counts[ScreeningBatchItemStatus.REUSED],
            skipped=counts[ScreeningBatchItemStatus.SKIPPED],
        )


screening_batch_service = ScreeningBatchService()


__all__ = [
    "ScreeningBatchApplicationsNotFoundError",
    "ScreeningBatchJobMismatchError",
    "ScreeningBatchJobNotFoundError",
    "ScreeningBatchJobNotOpenError",
    "ScreeningBatchService",
    "ScreeningBatchServiceError",
    "screening_batch_service",
]
