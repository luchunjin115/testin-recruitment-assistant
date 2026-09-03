from __future__ import annotations

import re
from datetime import datetime
from math import ceil
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.application import Application
from app.models.application_processing_run import ApplicationProcessingRun
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.public_application_submission import PublicApplicationSubmission
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.models.screening_run import ScreeningRun
from app.schemas.application import (
    ApplicationLifecycleStatus,
    ApplicationSource,
    FinalOutcome,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.public_application import ApplicationProcessingStatus
from app.schemas.screening_center import (
    ScreeningAbilityTag,
    ScreeningCenterAllowedAction,
    ScreeningCenterApplicationPage,
    ScreeningCenterApplicationSummary,
    ScreeningCenterDisplayLabel,
    ScreeningCenterProcessingPool,
    ScreeningCenterReportStatus,
    ScreeningCenterSort,
)
from app.schemas.screening_evaluation import ScreeningEvaluationV5ReportPayload


_NORMAL_PROCESSING_STATUSES = {"queued", "running", "waiting_screening", "succeeded"}
_EXCEPTION_PROCESSING_STATUSES = {"failed", "paused", "succeeded_with_warnings"}
_ACTIVE_SCREENING_STATUSES = {"waiting_resume", "waiting_plan", "queued", "running", "paused"}
_SENSITIVE_TAG_PATTERN = re.compile(
    r"(?:公司|企业|雇主|品牌|学校|院校|毕业院校|性别|年龄|婚育|婚姻|民族|国籍|宗教|籍贯|户籍|薪资|工资|"
    r"company|employer|brand|university|college|school|gender|marital|ethnicity|nationality|religion|salary)",
    re.IGNORECASE,
)
_IMPORTANCE_RANK = {"required": 0, "preferred": 1, "general": 2}


def _clean_excerpt(value: str | None, *, limit: int = 360) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 1]}…"


def _normalized_label(value: str) -> str:
    return " ".join(value.split()).strip()


def extract_screening_ability_tags(
    report: ScreeningReport | Any,
) -> list[ScreeningAbilityTag]:
    """Derive display tags only from validated current Schema 5 evidence."""
    if report is None or report.schema_version != "5.0" or not report.v5_report:
        return []
    try:
        payload = ScreeningEvaluationV5ReportPayload.model_validate(report.v5_report)
    except (TypeError, ValueError):
        return []

    assessments = {
        item.criterion.criterion_id: item
        for item in payload.criterion_assessments
        if item.assessment.score > 0 and item.assessment.evidence
    }
    criterion_order = {
        item.criterion.criterion_id: index
        for index, item in enumerate(payload.criterion_assessments)
    }
    candidates: list[tuple[int, int, int, int, str, Any]] = []
    for strength_index, strength in enumerate(payload.strengths):
        for criterion_id in strength.criterion_ids:
            item = assessments.get(criterion_id)
            if item is None:
                continue
            label = _normalized_label(item.criterion.name)
            if not label or _SENSITIVE_TAG_PATTERN.search(label):
                continue
            candidates.append(
                (
                    -item.assessment.score,
                    _IMPORTANCE_RANK[item.criterion.importance.value],
                    strength_index,
                    criterion_order[criterion_id],
                    label.casefold(),
                    item,
                )
            )
    candidates.sort(key=lambda value: value[:5])

    tags: list[ScreeningAbilityTag] = []
    seen: set[str] = set()
    for *_, normalized, item in candidates:
        if normalized in seen:
            continue
        seen.add(normalized)
        tags.append(
            ScreeningAbilityTag(
                criterion_id=item.criterion.criterion_id,
                label=_normalized_label(item.criterion.name),
                score=item.assessment.score,
                importance=item.criterion.importance,
                evidence_count=len(item.assessment.evidence),
                is_outdated=bool(report.is_outdated),
            )
        )
        if len(tags) == 4:
            break
    return tags


def _masked_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7:
        return "****"
    prefix = "+" if value.strip().startswith("+") else ""
    return f"{prefix}{digits[:3]}****{digits[-4:]}"


class ScreeningCenterService:
    async def list_applications(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 30,
        application_id: int | None = None,
        job_id: int | None = None,
        source: ApplicationSource | None = None,
        hr_decision: HRDecision | None = None,
        recruitment_stage: RecruitmentStage | None = None,
        lifecycle_status: ApplicationLifecycleStatus | None = None,
        final_outcome: FinalOutcome | None = None,
        processing_pool: ScreeningCenterProcessingPool = ScreeningCenterProcessingPool.ALL,
        processing_status: ApplicationProcessingStatus | None = None,
        display_label: ScreeningCenterDisplayLabel | None = None,
        score_min: int | None = None,
        score_max: int | None = None,
        applied_from: datetime | None = None,
        applied_to: datetime | None = None,
        sort: ScreeningCenterSort = ScreeningCenterSort.APPLIED_DESC,
    ) -> ScreeningCenterApplicationPage:
        screening_run_alias = aliased(ScreeningRun)
        processing_run_alias = aliased(ApplicationProcessingRun)
        latest_screening_run_id = (
            select(ScreeningRun.id)
            .where(ScreeningRun.application_id == Application.id)
            .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
            .limit(1)
            .correlate(Application)
            .scalar_subquery()
        )
        latest_processing_run_id = (
            select(ApplicationProcessingRun.id)
            .where(ApplicationProcessingRun.application_id == Application.id)
            .order_by(ApplicationProcessingRun.created_at.desc(), ApplicationProcessingRun.id.desc())
            .limit(1)
            .correlate(Application)
            .scalar_subquery()
        )
        from_clause = (
            Application.__table__
            .join(Candidate.__table__, Candidate.id == Application.candidate_id)
            .join(Job.__table__, Job.id == Application.job_id)
            .join(Resume.__table__, Resume.id == Application.current_resume_id)
            .outerjoin(
                ScreeningReport.__table__,
                and_(ScreeningReport.application_id == Application.id, ScreeningReport.is_current.is_(True)),
            )
            .outerjoin(screening_run_alias, screening_run_alias.id == latest_screening_run_id)
            .outerjoin(PublicApplicationSubmission.__table__, PublicApplicationSubmission.application_id == Application.id)
            .outerjoin(processing_run_alias, processing_run_alias.id == latest_processing_run_id)
        )
        conditions = []
        if application_id is not None:
            conditions.append(Application.id == application_id)
        if job_id is not None:
            conditions.append(Application.job_id == job_id)
        if source is not None:
            conditions.append(Application.source == source.value)
        if hr_decision is not None:
            conditions.append(Application.hr_decision == hr_decision.value)
        if recruitment_stage is not None:
            conditions.append(Application.recruitment_stage == recruitment_stage.value)
        if lifecycle_status is not None:
            conditions.append(Application.lifecycle_status == lifecycle_status.value)
        if final_outcome is not None:
            conditions.append(Application.final_outcome == final_outcome.value)
        if processing_status is not None:
            conditions.append(processing_run_alias.status == processing_status.value)
        if display_label is not None:
            conditions.append(ScreeningReport.display_label == display_label.value)
        if score_min is not None:
            conditions.append(ScreeningReport.overall_score >= score_min)
        if score_max is not None:
            conditions.append(ScreeningReport.overall_score <= score_max)
        if applied_from is not None:
            conditions.append(Application.applied_at >= applied_from)
        if applied_to is not None:
            conditions.append(Application.applied_at <= applied_to)
        if processing_pool is ScreeningCenterProcessingPool.INTERNAL:
            conditions.append(PublicApplicationSubmission.id.is_(None))
        elif processing_pool is ScreeningCenterProcessingPool.NORMAL:
            conditions.extend(
                [
                    PublicApplicationSubmission.id.is_not(None),
                    PublicApplicationSubmission.identity_review_status != "needs_review",
                    processing_run_alias.status.in_(_NORMAL_PROCESSING_STATUSES),
                ]
            )
        elif processing_pool is ScreeningCenterProcessingPool.EXCEPTION:
            conditions.extend(
                [
                    PublicApplicationSubmission.id.is_not(None),
                    or_(
                        PublicApplicationSubmission.identity_review_status == "needs_review",
                        processing_run_alias.status.in_(_EXCEPTION_PROCESSING_STATUSES),
                    ),
                ]
            )

        count_statement = select(func.count()).select_from(from_clause).where(*conditions)
        total = int(await db.scalar(count_statement) or 0)
        statement = select(
            Application,
            Candidate,
            Job,
            Resume,
            ScreeningReport,
            screening_run_alias,
            PublicApplicationSubmission,
            processing_run_alias,
        ).select_from(from_clause).where(*conditions)
        if sort is ScreeningCenterSort.UPDATED_DESC:
            updated = func.greatest(
                Application.updated_at,
                Candidate.updated_at,
                Job.updated_at,
                ScreeningReport.updated_at,
                screening_run_alias.updated_at,
                PublicApplicationSubmission.updated_at,
                processing_run_alias.updated_at,
            )
            statement = statement.order_by(updated.desc().nullslast(), Application.id.desc())
        elif sort is ScreeningCenterSort.SCORE_DESC:
            statement = statement.order_by(ScreeningReport.overall_score.desc().nullslast(), Application.id.desc())
        elif sort is ScreeningCenterSort.SCORE_ASC:
            statement = statement.order_by(ScreeningReport.overall_score.asc().nullslast(), Application.id.desc())
        else:
            statement = statement.order_by(Application.applied_at.desc(), Application.id.desc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(statement)).all()
        items = [self._summary(*row) for row in rows]
        return ScreeningCenterApplicationPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    @classmethod
    def _summary(
        cls,
        application: Application,
        candidate: Candidate,
        job: Job,
        resume: Resume,
        report: ScreeningReport | None,
        screening_run: ScreeningRun | None,
        submission: PublicApplicationSubmission | None,
        processing_run: ApplicationProcessingRun | None,
    ) -> ScreeningCenterApplicationSummary:
        report_status = cls._report_status(report, screening_run)
        processing_pool = cls._processing_pool(submission, processing_run)
        business_times = [application.updated_at, candidate.updated_at, job.updated_at]
        business_times.extend(
            value
            for value in (
                report.updated_at if report else None,
                screening_run.updated_at if screening_run else None,
                submission.updated_at if submission else None,
                processing_run.updated_at if processing_run else None,
            )
            if value is not None
        )
        v5 = None
        if report is not None and report.schema_version == "5.0" and report.v5_report:
            try:
                v5 = ScreeningEvaluationV5ReportPayload.model_validate(report.v5_report)
            except (TypeError, ValueError):
                v5 = None
        gaps = [] if v5 is None else [item.summary for item in [*v5.gaps, *v5.risks_or_conflicts]][:2]
        strengths = [] if v5 is None else [item.summary for item in v5.strengths[:2]]
        return ScreeningCenterApplicationSummary(
            application_id=application.id,
            candidate_id=candidate.id,
            job_id=job.id,
            resume_id=resume.id,
            candidate_name=candidate.name,
            masked_phone=_masked_phone(candidate.phone),
            current_title=candidate.current_title,
            job_title=job.title,
            job_status=job.status,
            source=application.source,
            submission_id=submission.id if submission else None,
            submission_reference=submission.submission_reference if submission else None,
            lifecycle_status=application.lifecycle_status,
            recruitment_stage=application.recruitment_stage,
            hr_decision=application.hr_decision,
            final_outcome=application.final_outcome,
            processing_pool=processing_pool,
            processing_status=processing_run.status if processing_run else None,
            processing_step=processing_run.current_step if processing_run else None,
            processing_warning_codes=list(processing_run.warning_codes or []) if processing_run else [],
            screening_status=report_status,
            screening_run_status=screening_run.status if screening_run else None,
            screening_waiting_reason=screening_run.waiting_reason if screening_run else None,
            screening_error_message=_clean_excerpt(screening_run.error_message, limit=500) if screening_run else None,
            score=report.overall_score if report else None,
            display_label=report.display_label if report else None,
            report_id=report.id if report else None,
            report_is_outdated=bool(report.is_outdated) if report else False,
            ability_tags=extract_screening_ability_tags(report),
            overall_summary=_clean_excerpt(report.overall_summary) if report else None,
            strengths=[value for value in (_clean_excerpt(item, limit=240) for item in strengths) if value],
            gaps_or_risks=[value for value in (_clean_excerpt(item, limit=240) for item in gaps) if value],
            applied_at=application.applied_at,
            business_updated_at=max(business_times),
            allowed_actions=cls._allowed_actions(application, job, report, screening_run),
        )

    @staticmethod
    def _processing_pool(
        submission: PublicApplicationSubmission | None,
        run: ApplicationProcessingRun | None,
    ) -> ScreeningCenterProcessingPool:
        if submission is None:
            return ScreeningCenterProcessingPool.INTERNAL
        if submission.identity_review_status == "needs_review" or (
            run is not None and run.status in _EXCEPTION_PROCESSING_STATUSES
        ):
            return ScreeningCenterProcessingPool.EXCEPTION
        return ScreeningCenterProcessingPool.NORMAL

    @staticmethod
    def _report_status(
        report: ScreeningReport | None,
        run: ScreeningRun | None,
    ) -> ScreeningCenterReportStatus:
        if report is not None and report.is_outdated:
            return ScreeningCenterReportStatus.OUTDATED
        if report is not None and run is not None and run.status == "failed" and run.created_at >= report.generated_at:
            return ScreeningCenterReportStatus.OLD_REPORT_RETAINED
        if run is not None and run.status in _ACTIVE_SCREENING_STATUSES:
            return ScreeningCenterReportStatus(run.status)
        if report is not None:
            return ScreeningCenterReportStatus.READY
        if run is not None and run.status == "failed":
            return ScreeningCenterReportStatus.FAILED
        return ScreeningCenterReportStatus.NOT_STARTED

    @staticmethod
    def _allowed_actions(
        application: Application,
        job: Job,
        report: ScreeningReport | None,
        run: ScreeningRun | None,
    ) -> list[ScreeningCenterAllowedAction]:
        actions = [ScreeningCenterAllowedAction.VIEW_DETAIL]
        active_run = run is not None and run.status in _ACTIVE_SCREENING_STATUSES
        if application.lifecycle_status == "active" and job.status == "open" and not active_run:
            actions.append(
                ScreeningCenterAllowedAction.REASSESS_SCREENING
                if report is not None
                else ScreeningCenterAllowedAction.START_SCREENING
            )
        if application.lifecycle_status == "active":
            if application.hr_decision in {"pending", "backup"}:
                actions.append(ScreeningCenterAllowedAction.PASS)
            if application.hr_decision in {"pending", "passed"}:
                actions.append(ScreeningCenterAllowedAction.BACKUP)
            if application.hr_decision in {"pending", "passed", "backup"}:
                actions.append(ScreeningCenterAllowedAction.REJECT)
            if application.hr_decision == "passed" and application.recruitment_stage == "screening_passed":
                actions.append(ScreeningCenterAllowedAction.SCHEDULE_INTERVIEW)
        elif (
            application.lifecycle_status == "ended"
            and application.recruitment_stage == "rejected"
            and application.hr_decision == "rejected"
            and application.final_outcome == "screening_rejected"
        ):
            actions.append(ScreeningCenterAllowedAction.UNDO_REJECTION)
        return actions


screening_center_service = ScreeningCenterService()


__all__ = ["ScreeningCenterService", "extract_screening_ability_tags", "screening_center_service"]
