from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.interview_record import InterviewRecord
from app.models.offer_record import OfferRecord
from app.models.stage_history import StageHistory
from app.schemas.recruitment_statistics import (
    RecruitmentDurationKey,
    RecruitmentDurationMetric,
    RecruitmentFunnelKey,
    RecruitmentFunnelStep,
    RecruitmentStatisticsCohort,
    RecruitmentStatisticsRead,
    RecruitmentTodoSnapshot,
)


_FUNNEL_ORDER = (
    RecruitmentFunnelKey.APPLICATIONS,
    RecruitmentFunnelKey.SCREENING_PASSED,
    RecruitmentFunnelKey.INTERVIEW_ENTERED,
    RecruitmentFunnelKey.INTERVIEW_COMPLETED,
    RecruitmentFunnelKey.OFFER_SENT,
    RecruitmentFunnelKey.OFFER_ACCEPTED,
    RecruitmentFunnelKey.ADMITTED,
    RecruitmentFunnelKey.HIRED,
)

_DURATION_ORDER = (
    RecruitmentDurationKey.APPLICATION_TO_SCREENING_PASSED,
    RecruitmentDurationKey.SCREENING_PASSED_TO_FIRST_INTERVIEW,
    RecruitmentDurationKey.FIRST_INTERVIEW_TO_LAST_COMPLETED,
    RecruitmentDurationKey.OFFER_ENTERED_TO_SENT,
    RecruitmentDurationKey.OFFER_SENT_TO_RESPONSE,
    RecruitmentDurationKey.OFFER_ACCEPTED_TO_ADMITTED,
    RecruitmentDurationKey.ADMITTED_TO_HIRED,
)


class RecruitmentStatisticsService:
    async def get_statistics(
        self,
        db: AsyncSession,
        *,
        job_id: int | None = None,
        applied_from: datetime | None = None,
        applied_to: datetime | None = None,
    ) -> RecruitmentStatisticsRead:
        cohort_filters = self._cohort_filters(
            job_id=job_id,
            applied_from=applied_from,
            applied_to=applied_to,
        )
        application_rows = (
            await db.execute(
                select(
                    Application.id,
                    Application.applied_at,
                    Application.final_outcome,
                ).where(*cohort_filters)
            )
        ).all()
        application_ids = {row.id for row in application_rows}

        history_rows = []
        interview_rows = []
        offer_rows = []
        if application_ids:
            history_rows = (
                await db.execute(
                    select(
                        StageHistory.application_id,
                        StageHistory.to_recruitment_stage,
                        StageHistory.created_at,
                    ).where(StageHistory.application_id.in_(application_ids))
                )
            ).all()
            interview_rows = (
                await db.execute(
                    select(
                        InterviewRecord.application_id,
                        InterviewRecord.round_number,
                        InterviewRecord.status,
                        InterviewRecord.decision,
                        InterviewRecord.created_at,
                        InterviewRecord.feedback_submitted_at,
                    ).where(InterviewRecord.application_id.in_(application_ids))
                )
            ).all()
            offer_rows = (
                await db.execute(
                    select(
                        OfferRecord.application_id,
                        OfferRecord.status,
                        OfferRecord.sent_at,
                        OfferRecord.responded_at,
                    ).where(OfferRecord.application_id.in_(application_ids))
                )
            ).all()

        histories = self._group_histories(history_rows)
        interviews = self._group_rows(interview_rows)
        offers = self._group_rows(offer_rows)
        applications = {
            row.id: {"applied_at": row.applied_at, "final_outcome": row.final_outcome}
            for row in application_rows
        }

        funnel_counts = self._funnel_counts(
            applications=applications,
            histories=histories,
            interviews=interviews,
            offers=offers,
        )
        durations = self._duration_metrics(
            applications=applications,
            histories=histories,
            interviews=interviews,
            offers=offers,
        )
        todos = await self._todo_snapshot(db, job_id=job_id)

        return RecruitmentStatisticsRead(
            cohort=RecruitmentStatisticsCohort(
                job_id=job_id,
                applied_from=applied_from,
                applied_to=applied_to,
            ),
            funnel=self._funnel_steps(funnel_counts),
            durations=durations,
            todos=todos,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _cohort_filters(
        *,
        job_id: int | None,
        applied_from: datetime | None,
        applied_to: datetime | None,
    ) -> list:
        filters = []
        if job_id is not None:
            filters.append(Application.job_id == job_id)
        if applied_from is not None:
            filters.append(Application.applied_at >= applied_from)
        if applied_to is not None:
            filters.append(Application.applied_at <= applied_to)
        return filters

    @staticmethod
    def _group_histories(rows) -> dict[int, dict[str, list[datetime]]]:
        grouped: dict[int, dict[str, list[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in rows:
            grouped[row.application_id][row.to_recruitment_stage].append(
                row.created_at
            )
        for stages in grouped.values():
            for values in stages.values():
                values.sort()
        return grouped

    @staticmethod
    def _group_rows(rows) -> dict[int, list]:
        grouped: dict[int, list] = defaultdict(list)
        for row in rows:
            grouped[row.application_id].append(row)
        return grouped

    @staticmethod
    def _first_stage(
        histories: dict[int, dict[str, list[datetime]]],
        application_id: int,
        stage: str,
    ) -> datetime | None:
        values = histories.get(application_id, {}).get(stage, [])
        return values[0] if values else None

    def _funnel_counts(
        self,
        *,
        applications: dict[int, dict],
        histories: dict[int, dict[str, list[datetime]]],
        interviews: dict[int, list],
        offers: dict[int, list],
    ) -> dict[RecruitmentFunnelKey, int]:
        counts = {key: 0 for key in _FUNNEL_ORDER}
        counts[RecruitmentFunnelKey.APPLICATIONS] = len(applications)
        for application_id, application in applications.items():
            stages = histories.get(application_id, {})
            interview_records = interviews.get(application_id, [])
            offer_records = offers.get(application_id, [])
            if "screening_passed" in stages:
                counts[RecruitmentFunnelKey.SCREENING_PASSED] += 1
            if any(row.status != "canceled" for row in interview_records):
                counts[RecruitmentFunnelKey.INTERVIEW_ENTERED] += 1
            if any(row.status == "completed" for row in interview_records):
                counts[RecruitmentFunnelKey.INTERVIEW_COMPLETED] += 1
            if any(row.sent_at is not None for row in offer_records):
                counts[RecruitmentFunnelKey.OFFER_SENT] += 1
            if (
                any(row.status == "accepted" for row in offer_records)
                or any(stage in stages for stage in ("offer_accepted", "admitted", "hired"))
            ):
                counts[RecruitmentFunnelKey.OFFER_ACCEPTED] += 1
            if "admitted" in stages or application["final_outcome"] == "hired":
                counts[RecruitmentFunnelKey.ADMITTED] += 1
            if application["final_outcome"] == "hired":
                counts[RecruitmentFunnelKey.HIRED] += 1
        return counts

    @staticmethod
    def _funnel_steps(
        counts: dict[RecruitmentFunnelKey, int],
    ) -> list[RecruitmentFunnelStep]:
        result = []
        previous_count: int | None = None
        for key in _FUNNEL_ORDER:
            count = counts[key]
            conversion_rate = None
            if previous_count:
                conversion_rate = float(
                    (Decimal(count) * Decimal("100") / Decimal(previous_count)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
            result.append(
                RecruitmentFunnelStep(
                    key=key,
                    count=count,
                    conversion_rate=conversion_rate,
                )
            )
            previous_count = count
        return result

    def _duration_metrics(
        self,
        *,
        applications: dict[int, dict],
        histories: dict[int, dict[str, list[datetime]]],
        interviews: dict[int, list],
        offers: dict[int, list],
    ) -> list[RecruitmentDurationMetric]:
        samples: dict[RecruitmentDurationKey, list[float]] = {
            key: [] for key in _DURATION_ORDER
        }
        for application_id, application in applications.items():
            passed_at = self._first_stage(histories, application_id, "screening_passed")
            offer_entered_at = self._first_stage(histories, application_id, "offer")
            accepted_at = self._first_stage(histories, application_id, "offer_accepted")
            admitted_at = self._first_stage(histories, application_id, "admitted")
            hired_at = self._first_stage(histories, application_id, "hired")

            interview_records = interviews.get(application_id, [])
            created_times = [
                row.created_at
                for row in interview_records
                if row.status != "canceled" and row.created_at is not None
            ]
            completed_times = [
                row.feedback_submitted_at
                for row in interview_records
                if row.status == "completed" and row.feedback_submitted_at is not None
            ]
            first_interview_at = min(created_times) if created_times else None
            last_completed_at = max(completed_times) if completed_times else None

            offer_records = offers.get(application_id, [])
            sent_times = [row.sent_at for row in offer_records if row.sent_at is not None]
            first_sent_at = min(sent_times) if sent_times else None
            response_pairs = sorted(
                (
                    (row.responded_at, row.sent_at)
                    for row in offer_records
                    if row.status in {"accepted", "declined"}
                    and row.responded_at is not None
                    and row.sent_at is not None
                ),
                key=lambda pair: pair[0],
            )
            if accepted_at is None:
                accepted_response_times = [
                    row.responded_at
                    for row in offer_records
                    if row.status == "accepted" and row.responded_at is not None
                ]
                accepted_at = (
                    min(accepted_response_times) if accepted_response_times else None
                )

            self._append_duration(
                samples[RecruitmentDurationKey.APPLICATION_TO_SCREENING_PASSED],
                application["applied_at"],
                passed_at,
            )
            self._append_duration(
                samples[RecruitmentDurationKey.SCREENING_PASSED_TO_FIRST_INTERVIEW],
                passed_at,
                first_interview_at,
            )
            self._append_duration(
                samples[RecruitmentDurationKey.FIRST_INTERVIEW_TO_LAST_COMPLETED],
                first_interview_at,
                last_completed_at,
            )
            self._append_duration(
                samples[RecruitmentDurationKey.OFFER_ENTERED_TO_SENT],
                offer_entered_at,
                first_sent_at,
            )
            if response_pairs:
                responded_at, sent_at = response_pairs[0]
                self._append_duration(
                    samples[RecruitmentDurationKey.OFFER_SENT_TO_RESPONSE],
                    sent_at,
                    responded_at,
                )
            self._append_duration(
                samples[RecruitmentDurationKey.OFFER_ACCEPTED_TO_ADMITTED],
                accepted_at,
                admitted_at,
            )
            self._append_duration(
                samples[RecruitmentDurationKey.ADMITTED_TO_HIRED],
                admitted_at,
                hired_at,
            )

        return [
            RecruitmentDurationMetric(
                key=key,
                average_hours=(round(sum(samples[key]) / len(samples[key]), 2) if samples[key] else None),
                sample_count=len(samples[key]),
            )
            for key in _DURATION_ORDER
        ]

    @staticmethod
    def _append_duration(
        samples: list[float],
        started_at: datetime | None,
        ended_at: datetime | None,
    ) -> None:
        if started_at is None or ended_at is None or ended_at < started_at:
            return
        samples.append((ended_at - started_at).total_seconds() / 3600)

    async def _todo_snapshot(
        self,
        db: AsyncSession,
        *,
        job_id: int | None,
    ) -> RecruitmentTodoSnapshot:
        application_filters = [Application.lifecycle_status == "active"]
        if job_id is not None:
            application_filters.append(Application.job_id == job_id)
        application_rows = (
            await db.execute(
                select(Application.id, Application.recruitment_stage).where(
                    *application_filters
                )
            )
        ).all()
        active_ids = {row.id for row in application_rows}
        interview_rows = []
        offer_rows = []
        if active_ids:
            interview_rows = (
                await db.execute(
                    select(
                        InterviewRecord.application_id,
                        InterviewRecord.round_number,
                        InterviewRecord.status,
                        InterviewRecord.decision,
                    ).where(InterviewRecord.application_id.in_(active_ids))
                )
            ).all()
            offer_rows = (
                await db.execute(
                    select(OfferRecord.application_id, OfferRecord.status).where(
                        OfferRecord.application_id.in_(active_ids)
                    )
                )
            ).all()

        application_stages = {row.id: row.recruitment_stage for row in application_rows}
        scheduled = {
            row.application_id
            for row in interview_rows
            if row.status == "scheduled"
            and application_stages[row.application_id] == "interview"
        }
        pending_decisions = {
            row.application_id
            for row in interview_rows
            if row.status == "completed" and row.decision == "pending"
            and application_stages[row.application_id] == "interview"
        }
        rounds_by_application: dict[int, set[int]] = defaultdict(set)
        for row in interview_rows:
            rounds_by_application[row.application_id].add(row.round_number)
        missing_next_round = {
            row.application_id
            for row in interview_rows
            if row.status == "completed"
            and row.decision == "next_round"
            and row.round_number + 1 not in rounds_by_application[row.application_id]
            and application_stages[row.application_id] == "interview"
        }
        draft_offers = {
            row.application_id
            for row in offer_rows
            if row.status == "draft" and application_stages[row.application_id] == "offer"
        }
        sent_offers = {
            row.application_id
            for row in offer_rows
            if row.status == "sent" and application_stages[row.application_id] == "offer"
        }
        accepted_offers = {
            row.application_id
            for row in offer_rows
            if row.status == "accepted"
            and application_stages[row.application_id] == "offer_accepted"
        }
        admitted = {
            row.id for row in application_rows if row.recruitment_stage == "admitted"
        }
        values = {
            "scheduled_interviews": len(scheduled),
            "pending_interview_decisions": len(pending_decisions),
            "next_round_not_scheduled": len(missing_next_round),
            "draft_offers": len(draft_offers),
            "sent_offers": len(sent_offers),
            "accepted_offers": len(accepted_offers),
            "admitted_applications": len(admitted),
        }
        return RecruitmentTodoSnapshot(**values, total=sum(values.values()))


recruitment_statistics_service = RecruitmentStatisticsService()
