from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.interview_record import InterviewRecord
from app.models.offer_record import OfferRecord
from app.models.stage_history import StageHistory
from app.schemas.recruitment_timeline import RecruitmentTimelineItem
from app.services.interview_service import ApplicationNotFoundError


_CONTROLLED_INTERVIEW_ACTIONS = {
    "interview_scheduled",
    "interview_rescheduled",
    "interview_canceled",
    "interview_no_show",
    "interview_round_completed",
    "interview_next_round",
    "interview_proceed_offer",
    "interview_rejected",
    "candidate_withdrew",
    "stage9_correction",
}
_CONTROLLED_OFFER_ACTIONS = {
    "offer_created",
    "offer_updated",
    "offer_sent",
    "offer_accepted",
    "offer_declined",
    "offer_withdrawn",
    "offer_expired",
    "stage9_correction",
}
_CONTROLLED_APPLICATION_ACTIONS = {
    "application_admitted",
    "application_hired",
    "candidate_withdrew",
    "company_canceled",
    "stage9_reopened",
}


class RecruitmentTimelineService:
    async def list_timeline(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> list[RecruitmentTimelineItem]:
        application = await db.get(Application, application_id)
        if application is None:
            raise ApplicationNotFoundError("Application 不存在")

        histories_result = await db.scalars(
            select(StageHistory)
            .where(StageHistory.application_id == application_id)
            .order_by(StageHistory.created_at, StageHistory.id)
        )
        histories = list(histories_result.all())
        interview_ids = list(
            (
                await db.scalars(
                    select(InterviewRecord.id).where(
                        InterviewRecord.application_id == application_id
                    )
                )
            ).all()
        )
        offer_ids = list(
            (
                await db.scalars(
                    select(OfferRecord.id).where(
                        OfferRecord.application_id == application_id
                    )
                )
            ).all()
        )

        activities: list[ActivityLog] = []
        activity_conditions = [
            and_(
                ActivityLog.target_type == "application",
                ActivityLog.target_id == application_id,
                ActivityLog.action.in_(_CONTROLLED_APPLICATION_ACTIONS),
            )
        ]
        if interview_ids:
            activity_conditions.append(
                and_(
                    ActivityLog.target_type == "interview",
                    ActivityLog.target_id.in_(interview_ids),
                    ActivityLog.action.in_(_CONTROLLED_INTERVIEW_ACTIONS),
                )
            )
        if offer_ids:
            activity_conditions.append(
                and_(
                    ActivityLog.target_type == "offer",
                    ActivityLog.target_id.in_(offer_ids),
                    ActivityLog.action.in_(_CONTROLLED_OFFER_ACTIONS),
                )
            )
        if activity_conditions:
            activities_result = await db.scalars(
                select(ActivityLog)
                .where(or_(*activity_conditions))
                .order_by(ActivityLog.created_at, ActivityLog.id)
            )
            activities = list(activities_result.all())

        items = [self._history_item(item) for item in histories]
        items.extend(
            item
            for activity in activities
            if (item := self._activity_item(application_id, activity)) is not None
        )
        return sorted(
            items,
            key=lambda item: (
                item.occurred_at,
                0 if item.source.value == "stage_history" else 1,
                item.source_id,
            ),
        )

    @staticmethod
    def _history_item(history: StageHistory) -> RecruitmentTimelineItem:
        return RecruitmentTimelineItem(
            source="stage_history",
            source_id=history.id,
            event_type=history.reason_code,
            application_id=history.application_id,
            interview_record_id=history.interview_record_id,
            offer_record_id=history.offer_record_id,
            from_lifecycle_status=history.from_lifecycle_status,
            to_lifecycle_status=history.to_lifecycle_status,
            from_recruitment_stage=history.from_recruitment_stage,
            to_recruitment_stage=history.to_recruitment_stage,
            from_hr_decision=history.from_hr_decision,
            to_hr_decision=history.to_hr_decision,
            from_final_outcome=history.from_final_outcome,
            to_final_outcome=history.to_final_outcome,
            reason_code=history.reason_code,
            # Offer-linked free text may accidentally contain compensation details.
            # The immutable history keeps the audit reason, but the ordinary timeline
            # exposes only the controlled reason code and state transition.
            reason_detail=(
                None if history.offer_record_id is not None else history.reason_detail
            ),
            actor_type=history.actor_type,
            actor_label=history.actor_label,
            occurred_at=history.created_at,
        )

    @staticmethod
    def _activity_item(
        application_id: int,
        activity: ActivityLog,
    ) -> RecruitmentTimelineItem | None:
        detail = activity.detail
        if not isinstance(detail, dict):
            return None
        if detail.get("application_id") != application_id:
            return None
        if isinstance(detail.get("stage_history_id"), int):
            return None

        reason_code = detail.get("reason_code")
        actor_label = detail.get("actor_label")
        interview_record_id = detail.get("interview_record_id")
        offer_record_id = detail.get("offer_record_id")
        if (
            not isinstance(reason_code, str)
            or not isinstance(actor_label, str)
        ):
            return None
        if interview_record_id is not None and not isinstance(
            interview_record_id, int
        ):
            return None
        if offer_record_id is not None and not isinstance(offer_record_id, int):
            return None
        if activity.target_type == "interview" and interview_record_id is None:
            return None
        if activity.target_type == "offer" and offer_record_id is None:
            return None
        reason_detail = detail.get("reason_detail")
        if not isinstance(reason_detail, str):
            reason_detail = None
        if activity.target_type == "offer" or offer_record_id is not None:
            reason_detail = None

        return RecruitmentTimelineItem(
            source="activity_log",
            source_id=activity.id,
            event_type=activity.action,
            application_id=application_id,
            interview_record_id=interview_record_id,
            offer_record_id=offer_record_id,
            from_interview_status=RecruitmentTimelineService._string_or_none(
                detail.get("from_status")
                if activity.target_type == "interview"
                else None
            ),
            to_interview_status=RecruitmentTimelineService._string_or_none(
                detail.get("to_status")
                if activity.target_type == "interview"
                else None
            ),
            from_interview_decision=RecruitmentTimelineService._string_or_none(
                detail.get("from_decision")
                if activity.target_type == "interview"
                else None
            ),
            to_interview_decision=RecruitmentTimelineService._string_or_none(
                detail.get("to_decision")
                if activity.target_type == "interview"
                else None
            ),
            from_offer_status=RecruitmentTimelineService._string_or_none(
                detail.get("from_offer_status", detail.get("from_status"))
                if activity.target_type == "offer"
                else detail.get("from_offer_status")
            ),
            to_offer_status=RecruitmentTimelineService._string_or_none(
                detail.get("to_offer_status", detail.get("to_status"))
                if activity.target_type == "offer"
                else detail.get("to_offer_status")
            ),
            from_scheduled_start_at=RecruitmentTimelineService._datetime_or_none(
                detail.get("from_scheduled_start_at")
            ),
            to_scheduled_start_at=RecruitmentTimelineService._datetime_or_none(
                detail.get("to_scheduled_start_at")
            ),
            from_version=RecruitmentTimelineService._int_or_none(
                detail.get("from_version")
            ),
            to_version=RecruitmentTimelineService._int_or_none(
                detail.get("to_version")
            ),
            reason_code=reason_code,
            reason_detail=reason_detail,
            actor_type="hr",
            actor_label=actor_label,
            occurred_at=activity.created_at,
        )

    @staticmethod
    def _string_or_none(value) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _int_or_none(value) -> int | None:
        return value if isinstance(value, int) and value >= 1 else None

    @staticmethod
    def _datetime_or_none(value) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None


recruitment_timeline_service = RecruitmentTimelineService()


__all__ = [
    "RecruitmentTimelineService",
    "recruitment_timeline_service",
]
