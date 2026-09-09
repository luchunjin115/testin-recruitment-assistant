from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import func, null, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
LOCAL_DIR = ROOT / ".local"
MANIFEST_PATH = LOCAL_DIR / "import_manifest.json"
DATASET_VERSION = "portfolio-demo-v1"
STORAGE_FOLDER = "portfolio-demo-v1"

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.database import get_async_engine, get_sessionmaker  # noqa: E402
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.application import Application  # noqa: E402
from app.models.application_processing_run import ApplicationProcessingRun  # noqa: E402
from app.models.candidate import Candidate  # noqa: E402
from app.models.education import Education  # noqa: E402
from app.models.interview_record import InterviewRecord  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_evaluation_plan import JobEvaluationPlan  # noqa: E402
from app.models.offer_record import OfferRecord  # noqa: E402
from app.models.project_experience import ProjectExperience  # noqa: E402
from app.models.public_application_submission import PublicApplicationSubmission  # noqa: E402
from app.models.resume import Resume  # noqa: E402
from app.models.screening_report import ScreeningReport  # noqa: E402
from app.models.screening_run import ScreeningRun  # noqa: E402
from app.models.stage_history import StageHistory  # noqa: E402
from app.models.work_experience import WorkExperience  # noqa: E402
from app.schemas.application import (  # noqa: E402
    ApplicationLifecycleStatus,
    FinalOutcome,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.candidate import CandidateCreate  # noqa: E402
from app.schemas.interview import InterviewRecordCreate  # noqa: E402
from app.schemas.job import JobCreate  # noqa: E402
from app.schemas.job_evaluation_plan import V5CriterionItem  # noqa: E402
from app.schemas.offer import OfferRecordCreate  # noqa: E402
from app.schemas.public_application import (  # noqa: E402
    ApplicationProcessingRunCreate,
    PublicApplicationSubmissionCreate,
)
from app.schemas.screening import ScreeningReportRead  # noqa: E402
from app.schemas.screening_evaluation import (  # noqa: E402
    ScreeningEvaluationV5ReportPayload,
)
from app.services.resume_structure_service import ResumeStructureSnapshot  # noqa: E402
from app.services.recruitment_statistics_service import (  # noqa: E402
    RecruitmentStatisticsService,
)
from validate_dataset import main as validate_static_dataset  # noqa: E402


TRACKED_MODELS = (
    Job,
    Candidate,
    Education,
    WorkExperience,
    ProjectExperience,
    Resume,
    Application,
    JobEvaluationPlan,
    ScreeningRun,
    ScreeningReport,
    PublicApplicationSubmission,
    ApplicationProcessingRun,
    InterviewRecord,
    OfferRecord,
    StageHistory,
    ActivityLog,
)

FIT_SCORES = {
    "high": 88,
    "medium": 76,
    "transition": 66,
    "early_career": 61,
    "evidence_gap": 54,
    "low": 36,
}
CROSS_FIT_OVERRIDES = {
    ("CAND-004", "JOB-BE"): "medium",
    ("CAND-011", "JOB-DA"): "transition",
    ("CAND-018", "JOB-QA"): "medium",
    ("CAND-044", "JOB-AI"): "transition",
}
JOB_CRITERION_IDS = {
    "JOB-AI": "criterion:0001",
    "JOB-BE": "criterion:0002",
    "JOB-QA": "criterion:0003",
    "JOB-FE": "criterion:0004",
    "JOB-DA": "criterion:0005",
}


def load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def ensure_local_database() -> None:
    settings = get_settings()
    environment = settings.APP_ENV.strip().lower()
    if environment not in {"development", "dev", "local", "test"}:
        raise RuntimeError(
            f"refusing portfolio import for APP_ENV={settings.APP_ENV!r}; local development only"
        )
    url = make_url(settings.async_database_url)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("portfolio import requires the current PostgreSQL runtime")
    if (url.host or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("portfolio import refuses a non-local PostgreSQL host")


def ensure_descendant(path: Path, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise RuntimeError(f"unsafe path outside storage root: {resolved_path}")


async def table_counts(db: AsyncSession) -> dict[str, int]:
    result: dict[str, int] = {}
    for model in TRACKED_MODELS:
        result[model.__tablename__] = int(
            await db.scalar(select(func.count()).select_from(model)) or 0
        )
    return result


async def existing_demo_candidate_ids(db: AsyncSession) -> list[int]:
    rows = await db.scalars(
        select(Candidate.id).where(Candidate.email.like("%@portfolio.example"))
    )
    return list(rows)


def validate_manifest_rows(manifest: dict[str, Any], existing_ids: list[int]) -> None:
    expected = sorted(manifest.get("inserted_ids", {}).get("candidates", []))
    if expected != sorted(existing_ids):
        raise RuntimeError(
            "local import manifest and PostgreSQL demo candidate IDs disagree; "
            "stop and inspect before any new write"
        )


def make_storage_plan(
    applications: list[dict[str, Any]],
    candidates_by_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for application in applications:
        app_id = application["demo_application_id"]
        candidate = candidates_by_id[application["demo_candidate_id"]]
        source_path = ROOT / candidate["resume_file"]
        content = source_path.read_text(encoding="utf-8")
        digest = sha256_text(f"{DATASET_VERSION}:{app_id}:{content}")
        stored_name = f"{app_id.lower()}-{digest[:24]}.txt"
        result[app_id] = {
            "source_path": source_path,
            "raw_text": content,
            "file_size": len(content.encode("utf-8")),
            "relative_path": f"{STORAGE_FOLDER}/{stored_name}",
            "stored_name": stored_name,
            "sha256": sha256_text(content),
        }
    return result


def stage_target(
    event: str,
    to_stage: str,
    current: tuple[str | None, str | None, str | None, str | None],
) -> tuple[str, str, str, str | None]:
    lifecycle, _stage, decision, final_outcome = current
    if event == "hr_direct_entry":
        return "active", "screening_passed", "passed", None
    if event in {"application_created", "public_application_received"}:
        return "active", "applied", "pending", None
    if event == "ai_screening_completed":
        return "active", "hr_review", "pending", None
    if event == "meets_requirements":
        return "active", "screening_passed", "passed", None
    if event == "minor_capability_gap":
        return "active", "backup", "backup", None
    if event == "required_experience_missing":
        return "ended", "rejected", "rejected", "screening_rejected"
    if event == "interview_scheduled":
        return "active", "interview", "passed", None
    if event == "interview_proceed_offer":
        return "active", "offer", "passed", None
    if event == "interview_rejected":
        return "ended", "rejected", "passed", "interview_rejected"
    if event == "candidate_withdrew":
        return "ended", to_stage, "passed", "candidate_withdrew"
    if event == "offer_accepted":
        return "active", "offer_accepted", "passed", None
    if event == "offer_declined":
        return "ended", "offer", "passed", "offer_declined"
    if event == "application_admitted":
        return "active", "admitted", "passed", None
    if event == "application_hired":
        return "ended", "hired", "passed", "hired"
    return lifecycle or "active", to_stage, decision or "pending", final_outcome


def actor_label(event: dict[str, Any], source: str) -> str:
    if event["actor_type"] == "hr":
        return "本地 HR（未认证）"
    if event["event"] == "public_application_received" and source == "public_apply":
        return "候选人公开投递（系统受理）"
    return "作品集演示数据导入器"


def reason_detail(event: str) -> str | None:
    values = {
        "meets_requirements": "演示场景：根据岗位相关经历和项目证据由本地 HR 确认通过。",
        "minor_capability_gap": "演示场景：核心能力具备，但复杂项目证据仍需与其他候选人比较。",
        "required_experience_missing": "演示场景：当前简历未提供岗位要求的必要实践证据。",
        "interview_scheduled": "演示场景：HR 已与候选人确认本轮面试安排。",
        "interview_proceed_offer": "演示场景：面试反馈支持进入 Offer 沟通。",
        "interview_rejected": "演示场景：面试中的岗位相关能力证据未达到当前要求。",
        "candidate_withdrew": "演示场景：候选人已明确表示退出当前岗位流程。",
        "offer_accepted": "演示场景：HR 根据线下沟通记录候选人已接受 Offer。",
        "offer_declined": "演示场景：候选人已明确拒绝当前 Offer。",
        "application_admitted": "演示场景：HR 已确认录取，等待实际入职。",
        "application_hired": "演示场景：HR 已确认候选人完成实际入职。",
    }
    return values.get(event)


def candidate_draft(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "basic_info": {
            "name": candidate["name"],
            "phone": candidate["phone"],
            "email": candidate["email"],
            "gender": None,
            "age": None,
            "location": candidate["location"],
            "current_company": candidate["current_company"],
            "current_title": candidate["current_title"],
            "work_years": candidate["work_years"],
            "education_level": candidate["education_level"],
        },
        "education_records": [
            {key: value for key, value in row.items() if key not in {"is_985", "is_211"}}
            for row in candidate["education_records"]
        ],
        "work_experiences": candidate["work_experiences"],
        "project_experiences": candidate["project_experiences"],
        "skills": candidate["skills"],
        "certifications": [],
        "self_evaluation": candidate["profile_summary"],
        "warnings": ["作品集演示数据：结构化内容由确定性导入器生成，不是模型输出。"],
        "missing_fields": [],
    }


def structure_snapshot(
    candidate: dict[str, Any],
    application: dict[str, Any],
    raw_text: str,
) -> dict[str, Any]:
    structured_at = parse_datetime(application["applied_at"]) + timedelta(hours=6)
    payload = {
        "draft": candidate_draft(candidate),
        "metadata": {
            "model": "portfolio-demo-fixture-no-model-call",
            "prompt_version": "portfolio_demo_fixture_v1",
            "schema_version": "1.0",
            "structured_at": structured_at.isoformat(),
            "input_characters": len(raw_text),
            "input_tokens": 0,
            "output_tokens": 0,
            "attempt_id": str(uuid5(NAMESPACE_URL, application["demo_application_id"])),
        },
    }
    return ResumeStructureSnapshot.model_validate(payload).model_dump(mode="json")


def display_label(score: int) -> str:
    if score <= 29:
        return "关联较弱"
    if score <= 49:
        return "存在明显差距"
    if score <= 69:
        return "部分匹配"
    if score <= 84:
        return "整体较匹配"
    return "高度匹配"


def plan_criterion(job: dict[str, Any]) -> dict[str, Any]:
    title = job["create_payload"]["title"]
    payload = {
        "criterion_id": JOB_CRITERION_IDS[job["demo_job_id"]],
        "name": f"{title}核心岗位能力",
        "importance": "required",
        "description": "核对简历是否提供与岗位职责直接相关的可验证实践。",
        "screening_focus": "关注本人职责、具体实现、结果证据和限制说明。",
        "origin": "hr_added",
        "sources": [],
        "hr_note": "作品集演示评价点；由确定性导入器创建，不是模型生成。",
    }
    return V5CriterionItem.model_validate(payload).model_dump(mode="json")


def report_payload(
    candidate: dict[str, Any],
    application: dict[str, Any],
    criterion: dict[str, Any],
) -> dict[str, Any]:
    fit_level = CROSS_FIT_OVERRIDES.get(
        (candidate["demo_candidate_id"], application["demo_job_id"]),
        candidate["fit_level"],
    )
    score = FIT_SCORES[fit_level]
    criterion_score = max(1, min(10, round(score / 10)))
    evidence_quote = candidate["skills"][0]
    assessment = {
        "criterion_id": criterion["criterion_id"],
        "score": criterion_score,
        "reason": "演示数据根据预设匹配层级生成，仅用于验证页面与业务流程，不代表真实 AI 判断。",
        "calculation_note": None,
        "experience_period_fact_keys": [],
        "evidence": [{"quote": evidence_quote, "section": "技能"}],
    }
    finding = {
        "summary": "简历中存在与评价点相关的演示证据。",
        "criterion_ids": [criterion["criterion_id"]],
        "evidence": [{"quote": evidence_quote, "section": "技能"}],
    }
    gap = {
        "summary": "仍需由 HR 在面试中核对复杂场景经验和本人贡献边界。",
        "criterion_ids": [criterion["criterion_id"]],
        "evidence": [],
    }
    payload = {
        "overall_score": score,
        "display_label": display_label(score),
        "overall_summary": candidate["profile_summary"],
        "criterion_assessments": [{"criterion": criterion, "assessment": assessment}],
        "strengths": [finding] if score >= 70 else [],
        "gaps": [] if score >= 85 else [gap],
        "risks_or_conflicts": [],
        "missing_info": [gap] if fit_level == "evidence_gap" else [],
        "hr_follow_up_questions": ["请结合一个具体项目说明本人职责、失败路径和验证证据。"],
    }
    return ScreeningEvaluationV5ReportPayload.model_validate(payload).model_dump(mode="json")


def synthetic_report_time(application: dict[str, Any]) -> datetime:
    for event in application["timeline"]:
        if event["event"] == "ai_screening_completed":
            return parse_datetime(event["at"])
    return parse_datetime(application["applied_at"])


async def build_rows(
    db: AsyncSession,
    jobs_doc: dict[str, Any],
    candidates_doc: dict[str, Any],
    applications_doc: dict[str, Any],
    storage_plan: dict[str, dict[str, Any]],
) -> dict[str, list[Any]]:
    rows: dict[str, list[Any]] = defaultdict(list)
    jobs_by_demo_id: dict[str, Job] = {}
    plans_by_job_id: dict[str, JobEvaluationPlan] = {}
    criteria_by_job_id: dict[str, dict[str, Any]] = {}
    candidates_by_demo_id: dict[str, Candidate] = {}
    candidate_data_by_demo_id = {
        row["demo_candidate_id"]: row for row in candidates_doc["candidates"]
    }

    dataset_created_at = parse_datetime(jobs_doc["dataset_as_of"])
    for job_data in jobs_doc["jobs"]:
        payload = JobCreate.model_validate(job_data["create_payload"]).model_dump()
        payload["status"] = job_data["desired_status"]
        job = Job(
            **payload,
            created_at=dataset_created_at,
            updated_at=dataset_created_at,
        )
        db.add(job)
        rows["jobs"].append(job)
        jobs_by_demo_id[job_data["demo_job_id"]] = job
    await db.flush()

    for job_data in jobs_doc["jobs"]:
        demo_job_id = job_data["demo_job_id"]
        job = jobs_by_demo_id[demo_job_id]
        criterion = plan_criterion(job_data)
        jd_fingerprint = sha256_text(json.dumps(job_data["create_payload"], ensure_ascii=False, sort_keys=True))
        input_fingerprint = sha256_text(f"{DATASET_VERSION}:{demo_job_id}:plan")
        plan = JobEvaluationPlan(
            job_id=job.id,
            jd_fingerprint=jd_fingerprint,
            status="ready",
            is_current=True,
            items=null(),
            structured_coverage=null(),
            free_text_coverage=null(),
            source_review_summary=null(),
            requirement_facts=null(),
            evaluation_criteria=null(),
            coverage_review_summary=null(),
            generation_audit=null(),
            v5_criteria=[criterion],
            edit_version=1,
            confirmed_at=dataset_created_at,
            warnings=["作品集全虚构演示计划；非 DeepSeek 输出。"],
            prompt_version="portfolio_demo_fixture_v1",
            model_version="portfolio-demo-fixture-no-model-call",
            schema_version="5.0",
            input_fingerprint=input_fingerprint,
            input_snapshot={
                "dataset_version": DATASET_VERSION,
                "synthetic": True,
                "notice": "No model call was made.",
            },
            error_code=None,
            error_message=None,
            created_at=dataset_created_at,
            completed_at=dataset_created_at,
            updated_at=dataset_created_at,
        )
        db.add(plan)
        rows["job_evaluation_plans"].append(plan)
        plans_by_job_id[demo_job_id] = plan
        criteria_by_job_id[demo_job_id] = criterion
    await db.flush()

    first_application_at: dict[str, datetime] = {}
    for application in applications_doc["applications"]:
        candidate_id = application["demo_candidate_id"]
        applied_at = parse_datetime(application["applied_at"])
        current = first_application_at.get(candidate_id)
        if current is None or applied_at < current:
            first_application_at[candidate_id] = applied_at

    for candidate_data in candidates_doc["candidates"]:
        CandidateCreate.model_validate({
            "name": candidate_data["name"],
            "phone": candidate_data["phone"],
            "email": candidate_data["email"],
            "location": candidate_data["location"],
            "current_company": candidate_data["current_company"],
            "current_title": candidate_data["current_title"],
            "work_years": candidate_data["work_years"],
            "education_level": candidate_data["education_level"],
            "source": "portfolio_demo",
            "status": "active",
            "tags": candidate_data["skills"],
            "education_records": candidate_data["education_records"],
            "work_experiences": candidate_data["work_experiences"],
            "project_experiences": candidate_data["project_experiences"],
        })
        created_at = first_application_at[candidate_data["demo_candidate_id"]]
        candidate = Candidate(
            name=candidate_data["name"],
            phone=candidate_data["phone"],
            email=candidate_data["email"],
            gender=None,
            age=None,
            location=candidate_data["location"],
            current_company=candidate_data["current_company"],
            current_title=candidate_data["current_title"],
            work_years=candidate_data["work_years"],
            education_level=candidate_data["education_level"],
            source="portfolio_demo",
            status="active",
            applied_job_id=jobs_by_demo_id[candidate_data["primary_job_id"]].id,
            resume_file_path=None,
            resume_text=None,
            parsed_data=None,
            ai_summary=None,
            tags=candidate_data["skills"],
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(candidate)
        rows["candidates"].append(candidate)
        candidates_by_demo_id[candidate_data["demo_candidate_id"]] = candidate
    await db.flush()

    for candidate_data in candidates_doc["candidates"]:
        candidate = candidates_by_demo_id[candidate_data["demo_candidate_id"]]
        for record in candidate_data["education_records"]:
            row = Education(candidate_id=candidate.id, **record)
            db.add(row)
            rows["education"].append(row)
        for record in candidate_data["work_experiences"]:
            row = WorkExperience(candidate_id=candidate.id, **record)
            db.add(row)
            rows["work_experience"].append(row)
        for record in candidate_data["project_experiences"]:
            row = ProjectExperience(candidate_id=candidate.id, **record)
            db.add(row)
            rows["project_experience"].append(row)
    await db.flush()

    applications_by_demo_id: dict[str, Application] = {}
    resumes_by_application_id: dict[str, Resume] = {}
    for application_data in applications_doc["applications"]:
        app_demo_id = application_data["demo_application_id"]
        candidate_data = candidate_data_by_demo_id[application_data["demo_candidate_id"]]
        candidate = candidates_by_demo_id[application_data["demo_candidate_id"]]
        job = jobs_by_demo_id[application_data["demo_job_id"]]
        storage = storage_plan[app_demo_id]
        applied_at = parse_datetime(application_data["applied_at"])
        processing = application_data["processing_run"]
        extraction_failed = bool(
            processing
            and processing["status"] == "failed"
            and processing["current_step"] == "extract_text"
        )
        has_structure_warning = bool(
            processing and "RESUME_STRUCTURE_FAILED" in processing.get("warning_codes", [])
        )
        should_have_report = (
            application_data["screening_plan"] == "generate_through_real_model_when_imported"
        )
        parsed_snapshot = None
        structure_status = "not_started"
        structure_error = None
        structure_attempt_id = None
        structured_at = None
        structure_schema_version = None
        if not extraction_failed and (should_have_report or processing and processing["status"] == "paused"):
            if has_structure_warning:
                structure_status = "failed"
                structure_error = "演示场景：结构化失败，但原文仍可用于初筛。"
            else:
                parsed_snapshot = structure_snapshot(candidate_data, application_data, storage["raw_text"])
                structure_status = "succeeded"
                structure_attempt_id = parsed_snapshot["metadata"]["attempt_id"]
                structured_at = parse_datetime(parsed_snapshot["metadata"]["structured_at"])
                structure_schema_version = "1.0"
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename=f"{candidate_data['name']}-{job.title}-虚构简历.txt",
            file_path=storage["relative_path"],
            file_type="text/plain",
            file_size=storage["file_size"],
            raw_text=None if extraction_failed else storage["raw_text"],
            parse_status="failed" if extraction_failed else "parsed",
            parse_error="演示场景：无法从文件中提取可用文本。" if extraction_failed else None,
            parsed_snapshot=parsed_snapshot,
            structure_status=structure_status,
            structure_error=structure_error,
            structure_attempt_id=structure_attempt_id,
            structure_started_at=None,
            structured_at=structured_at,
            structure_schema_version=structure_schema_version,
            uploaded_at=applied_at,
            parsed_at=None if extraction_failed else applied_at,
        )
        db.add(resume)
        rows["resumes"].append(resume)
        await db.flush()
        lifecycle = ApplicationLifecycleStatus(application_data["lifecycle_status"])
        stage = RecruitmentStage(application_data["recruitment_stage"])
        decision = HRDecision(application_data["hr_decision"])
        outcome = (
            FinalOutcome(application_data["final_outcome"])
            if application_data["final_outcome"] is not None
            else None
        )
        updated_at = max(parse_datetime(event["at"]) for event in application_data["timeline"])
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            current_resume_id=resume.id,
            source=application_data["source"],
            lifecycle_status=lifecycle.value,
            recruitment_stage=stage.value,
            hr_decision=decision.value,
            final_outcome=outcome.value if outcome else None,
            applied_at=applied_at,
            created_at=applied_at,
            updated_at=updated_at,
        )
        db.add(application)
        rows["applications"].append(application)
        applications_by_demo_id[app_demo_id] = application
        resumes_by_application_id[app_demo_id] = resume
        if application_data["is_primary_application"]:
            candidate.resume_file_path = resume.file_path
            candidate.resume_text = resume.raw_text
    await db.flush()

    submissions_by_app_id: dict[str, PublicApplicationSubmission] = {}
    for application_data in applications_doc["applications"]:
        if application_data["source"] != "public_apply":
            continue
        app_demo_id = application_data["demo_application_id"]
        application = applications_by_demo_id[app_demo_id]
        resume = resumes_by_application_id[app_demo_id]
        applied_at = parse_datetime(application_data["applied_at"])
        serial = int(app_demo_id.split("-")[1])
        payload = PublicApplicationSubmissionCreate.model_validate({
            "application_id": application.id,
            "resume_id": resume.id,
            "submission_reference": f"AP-DEMO{serial:06d}",
            "idempotency_key_hash": sha256_text(f"{DATASET_VERSION}:{app_demo_id}:idempotency"),
            "request_fingerprint": sha256_text(f"{DATASET_VERSION}:{app_demo_id}:request"),
            "consent_version": "2026-09-02",
            "consented_at": applied_at,
            "identity_review_status": "clear",
            "identity_review_reasons": [],
        })
        submission = PublicApplicationSubmission(
            **payload.model_dump(mode="python"),
            created_at=applied_at,
            updated_at=applied_at,
        )
        db.add(submission)
        rows["public_application_submissions"].append(submission)
        submissions_by_app_id[app_demo_id] = submission
    await db.flush()

    for application_data in applications_doc["applications"]:
        processing_data = application_data["processing_run"]
        if processing_data is None:
            continue
        app_demo_id = application_data["demo_application_id"]
        application = applications_by_demo_id[app_demo_id]
        resume = resumes_by_application_id[app_demo_id]
        submission = submissions_by_app_id[app_demo_id]
        create_payload = ApplicationProcessingRunCreate.model_validate({
            "submission_id": submission.id,
            "application_id": application.id,
            "resume_id": resume.id,
            "trigger_type": "automatic",
            **processing_data,
        })
        created_at = parse_datetime(application_data["applied_at"])
        processing = ApplicationProcessingRun(
            **create_payload.model_dump(mode="python"),
            created_at=created_at,
            updated_at=parse_datetime(processing_data.get("completed_at")) or created_at,
        )
        db.add(processing)
        rows["application_processing_runs"].append(processing)
    await db.flush()

    reports_by_app_id: dict[str, ScreeningReport] = {}
    for application_data in applications_doc["applications"]:
        if application_data["screening_plan"] != "generate_through_real_model_when_imported":
            continue
        app_demo_id = application_data["demo_application_id"]
        application = applications_by_demo_id[app_demo_id]
        resume = resumes_by_application_id[app_demo_id]
        plan = plans_by_job_id[application_data["demo_job_id"]]
        criterion = criteria_by_job_id[application_data["demo_job_id"]]
        candidate_data = candidate_data_by_demo_id[application_data["demo_candidate_id"]]
        generated_at = synthetic_report_time(application_data)
        payload = report_payload(candidate_data, application_data, criterion)
        input_fingerprint = sha256_text(f"{DATASET_VERSION}:{app_demo_id}:screening")
        resume_fingerprint = storage_plan[app_demo_id]["sha256"]
        report = ScreeningReport(
            application_id=application.id,
            job_id=application.job_id,
            resume_id=resume.id,
            job_evaluation_plan_id=plan.id,
            overall_score=payload["overall_score"],
            display_label=payload["display_label"],
            overall_summary=payload["overall_summary"],
            requirement_assessments=[],
            bonus_highlights=[],
            tradeoff_reason=None,
            interview_questions=[],
            input_fingerprint=input_fingerprint,
            jd_fingerprint=plan.jd_fingerprint,
            plan_fingerprint=plan.input_fingerprint,
            resume_fingerprint=resume_fingerprint,
            prompt_version="portfolio_demo_fixture_v1",
            model_version="portfolio-demo-fixture-no-model-call",
            schema_version="5.0",
            redaction_version="portfolio_demo_redacted_v1",
            evaluation_reference_at=generated_at,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts_rule_version=None,
            experience_period_facts=null(),
            v5_report=payload,
            is_current=True,
            is_outdated=False,
            outdated_reasons=[],
            outdated_at=None,
            generated_at=generated_at,
            updated_at=generated_at,
        )
        db.add(report)
        rows["screening_reports"].append(report)
        reports_by_app_id[app_demo_id] = report
        run = ScreeningRun(
            application_id=application.id,
            job_id=application.job_id,
            resume_id=resume.id,
            job_evaluation_plan_id=plan.id,
            trigger_type="automatic",
            status="succeeded",
            waiting_reason=None,
            input_fingerprint=input_fingerprint,
            prompt_version="portfolio_demo_fixture_v1",
            model_version="portfolio-demo-fixture-no-model-call",
            schema_version="5.0",
            redaction_version="portfolio_demo_redacted_v1",
            evaluation_reference_at=generated_at,
            evaluation_timezone="Asia/Shanghai",
            experience_period_facts_rule_version=None,
            experience_period_facts_fingerprint=None,
            started_at=generated_at,
            completed_at=generated_at,
            error_code=None,
            error_message=None,
            input_tokens=0,
            output_tokens=0,
            duration_ms=0,
            attempt_count=1,
            lease_owner=None,
            lease_expires_at=None,
            created_at=generated_at,
            updated_at=generated_at,
        )
        db.add(run)
        rows["screening_runs"].append(run)
    await db.flush()

    interviews_by_app_id: dict[str, InterviewRecord] = {}
    offers_by_app_id: dict[str, OfferRecord] = {}
    for application_data in applications_doc["applications"]:
        app_demo_id = application_data["demo_application_id"]
        application = applications_by_demo_id[app_demo_id]
        for interview_data in application_data["interviews"]:
            validated = InterviewRecordCreate.model_validate({
                "application_id": application.id,
                **{
                    key: value for key, value in interview_data.items()
                    if key not in {"demo_interview_id", "created_at"}
                },
            })
            created_at = parse_datetime(interview_data["created_at"])
            interview_payload = validated.model_dump(mode="python")
            if interview_payload.get("meeting_link") is not None:
                interview_payload["meeting_link"] = str(interview_payload["meeting_link"])
            interview = InterviewRecord(
                **interview_payload,
                created_at=created_at,
                updated_at=parse_datetime(interview_data.get("feedback_submitted_at")) or created_at,
            )
            db.add(interview)
            rows["interview_records"].append(interview)
            interviews_by_app_id[app_demo_id] = interview
        for offer_data in application_data["offers"]:
            validated = OfferRecordCreate.model_validate({
                "application_id": application.id,
                **{
                    key: value for key, value in offer_data.items()
                    if key not in {"demo_offer_id", "created_at"}
                },
            })
            created_at = parse_datetime(offer_data["created_at"])
            offer = OfferRecord(
                **validated.model_dump(mode="python"),
                created_at=created_at,
                updated_at=parse_datetime(offer_data.get("responded_at")) or created_at,
            )
            db.add(offer)
            rows["offer_records"].append(offer)
            offers_by_app_id[app_demo_id] = offer
    await db.flush()

    for application_data in applications_doc["applications"]:
        app_demo_id = application_data["demo_application_id"]
        application = applications_by_demo_id[app_demo_id]
        state: tuple[str | None, str | None, str | None, str | None] = (None, None, None, None)
        for event in application_data["timeline"]:
            event_at = parse_datetime(event["at"])
            if event["record_type"] == "activity_log":
                target_type = "application"
                target_id = application.id
                if event["event"].startswith("interview_") and app_demo_id in interviews_by_app_id:
                    target_type = "interview"
                    target_id = interviews_by_app_id[app_demo_id].id
                elif event["event"].startswith("offer_") and app_demo_id in offers_by_app_id:
                    target_type = "offer"
                    target_id = offers_by_app_id[app_demo_id].id
                activity = ActivityLog(
                    user_id=None,
                    action=event["event"],
                    target_type=target_type,
                    target_id=target_id,
                    detail={
                        "dataset_version": DATASET_VERSION,
                        "synthetic": True,
                        "application_id": application.id,
                    },
                    created_at=event_at,
                )
                db.add(activity)
                rows["activity_logs"].append(activity)
                continue
            target = stage_target(event["event"], event["to_recruitment_stage"], state)
            report = reports_by_app_id.get(app_demo_id)
            interview = interviews_by_app_id.get(app_demo_id)
            offer = offers_by_app_id.get(app_demo_id)
            history = StageHistory(
                application_id=application.id,
                report_id=(report.id if report and event["event"] in {"ai_screening_completed", "meets_requirements", "minor_capability_gap", "required_experience_missing"} else None),
                interview_record_id=(interview.id if interview and event["event"].startswith("interview_") else None),
                offer_record_id=(offer.id if offer and event["event"].startswith("offer_") else None),
                from_lifecycle_status=state[0],
                to_lifecycle_status=target[0],
                from_recruitment_stage=state[1],
                to_recruitment_stage=target[1],
                from_hr_decision=state[2],
                to_hr_decision=target[2],
                from_final_outcome=state[3],
                to_final_outcome=target[3],
                reason_code=event["event"],
                reason_detail=reason_detail(event["event"]),
                actor_type=event["actor_type"],
                actor_id=None,
                actor_label=actor_label(event, application_data["source"]),
                created_at=event_at,
            )
            db.add(history)
            rows["stage_histories"].append(history)
            state = target
        expected_state = (
            application_data["lifecycle_status"],
            application_data["recruitment_stage"],
            application_data["hr_decision"],
            application_data["final_outcome"],
        )
        if state != expected_state:
            raise RuntimeError(
                f"{app_demo_id} timeline ends at {state}, expected {expected_state}"
            )

    import_log = ActivityLog(
        user_id=None,
        action="portfolio_demo_dataset_imported",
        target_type="portfolio_demo_dataset",
        target_id=None,
        detail={
            "dataset_version": DATASET_VERSION,
            "synthetic": True,
            "candidate_count": len(candidates_doc["candidates"]),
            "application_count": len(applications_doc["applications"]),
            "real_model_calls": 0,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(import_log)
    rows["activity_logs"].append(import_log)
    await db.flush()

    for app_demo_id, report in reports_by_app_id.items():
        await db.refresh(report)
        ScreeningReportRead.model_validate(report)
    return rows


async def verify_imported_cohort(
    db: AsyncSession,
    rows: dict[str, list[Any]],
    expected_doc: dict[str, Any],
    jobs_doc: dict[str, Any],
) -> dict[str, Any]:
    service = RecruitmentStatisticsService()
    expected_by_job = expected_doc["by_job"]
    actual_by_job: dict[str, Any] = {}
    job_rows = rows["jobs"]
    for job_data, job in zip(jobs_doc["jobs"], job_rows):
        result = await service.get_statistics(db, job_id=job.id)
        serialized = result.model_dump(mode="json")
        actual_funnel = [(item["key"], item["count"]) for item in serialized["funnel"]]
        expected_funnel = [
            (item["key"], item["count"])
            for item in expected_by_job[job_data["demo_job_id"]]["funnel"]
        ]
        if actual_funnel != expected_funnel:
            raise RuntimeError(
                f"statistics mismatch for {job_data['demo_job_id']}: "
                f"{actual_funnel} != {expected_funnel}"
            )
        if serialized["todos"] != expected_by_job[job_data["demo_job_id"]]["todos"]:
            raise RuntimeError(
                f"todo mismatch for {job_data['demo_job_id']}: "
                f"{serialized['todos']} != {expected_by_job[job_data['demo_job_id']]['todos']}"
            )
        actual_by_job[job_data["demo_job_id"]] = {
            "database_job_id": job.id,
            "funnel": serialized["funnel"],
            "todos": serialized["todos"],
        }
    return actual_by_job


def inserted_ids(rows: dict[str, list[Any]]) -> dict[str, list[int]]:
    return {
        table_name: sorted(row.id for row in values)
        for table_name, values in rows.items()
        if values and all(getattr(row, "id", None) is not None for row in values)
    }


def prepare_storage(
    storage_root: Path,
    storage_plan: dict[str, dict[str, Any]],
) -> tuple[Path, Path]:
    storage_root.mkdir(parents=True, exist_ok=True)
    final_dir = storage_root / STORAGE_FOLDER
    staging_dir = storage_root / f".{STORAGE_FOLDER}-staging-{uuid4().hex}"
    ensure_descendant(final_dir, storage_root)
    ensure_descendant(staging_dir, storage_root)
    if final_dir.exists():
        raise RuntimeError(f"demo storage directory already exists: {final_dir}")
    staging_dir.mkdir(parents=False, exist_ok=False)
    for item in storage_plan.values():
        shutil.copy2(item["source_path"], staging_dir / item["stored_name"])
    return staging_dir, final_dir


def remove_owned_directory(path: Path, storage_root: Path) -> None:
    ensure_descendant(path, storage_root)
    if path.exists() and path.parent.resolve() == storage_root.resolve():
        shutil.rmtree(path)


def write_manifest(payload: dict[str, Any]) -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = LOCAL_DIR / f".{MANIFEST_PATH.name}.{uuid4().hex}.tmp"
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(MANIFEST_PATH)


async def inspect() -> None:
    ensure_local_database()
    settings = get_settings()
    storage_root = Path(settings.STORAGE_DIR)
    async with get_sessionmaker()() as db:
        counts = await table_counts(db)
        demo_ids = await existing_demo_candidate_ids(db)
    print(f"database environment: {settings.APP_ENV}")
    print(f"migration target database: {(make_url(settings.async_database_url).database or '<unknown>')}")
    print(f"storage root: {storage_root}")
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    print(f"existing portfolio demo candidates: {len(demo_ids)}")
    print(f"local manifest exists: {MANIFEST_PATH.exists()}")


async def execute_import(*, apply: bool, confirmation: str | None) -> None:
    ensure_local_database()
    validate_static_dataset()
    if apply and confirmation != DATASET_VERSION:
        raise RuntimeError(
            f"apply requires --confirm {DATASET_VERSION}"
        )
    jobs_doc = load_json("jobs.json")
    candidates_doc = load_json("candidates.json")
    applications_doc = load_json("applications.json")
    expected_doc = load_json("expected_statistics.json")
    if {jobs_doc["dataset_version"], candidates_doc["dataset_version"], applications_doc["dataset_version"]} != {DATASET_VERSION}:
        raise RuntimeError("dataset version mismatch")
    candidates_by_id = {
        row["demo_candidate_id"]: row for row in candidates_doc["candidates"]
    }
    storage_plan = make_storage_plan(applications_doc["applications"], candidates_by_id)
    settings = get_settings()
    storage_root = Path(settings.STORAGE_DIR)

    async with get_sessionmaker()() as preflight_db:
        before_counts = await table_counts(preflight_db)
        demo_ids = await existing_demo_candidate_ids(preflight_db)
    if demo_ids:
        if MANIFEST_PATH.exists():
            manifest = load_json(".local/import_manifest.json")
            validate_manifest_rows(manifest, demo_ids)
            print(
                f"{DATASET_VERSION} is already imported; "
                f"{len(demo_ids)} demo candidates found. No write performed."
            )
            return
        raise RuntimeError(
            "portfolio demo candidates already exist but the exact local manifest is missing"
        )
    if MANIFEST_PATH.exists():
        raise RuntimeError(
            "local import manifest exists but no demo candidates were found; inspect before writing"
        )

    staging_dir: Path | None = None
    final_dir = storage_root / STORAGE_FOLDER
    promoted = False
    if apply:
        staging_dir, final_dir = prepare_storage(storage_root, storage_plan)

    db = get_sessionmaker()()
    try:
        rows = await build_rows(
            db,
            jobs_doc,
            candidates_doc,
            applications_doc,
            storage_plan,
        )
        actual_by_job = await verify_imported_cohort(db, rows, expected_doc, jobs_doc)
        in_transaction_counts = await table_counts(db)
        ids = inserted_ids(rows)
        if not apply:
            await db.rollback()
            print("real PostgreSQL dry-run passed; transaction rolled back")
            print(json.dumps({key: len(value) for key, value in ids.items()}, ensure_ascii=False, indent=2))
            return

        assert staging_dir is not None
        staging_dir.replace(final_dir)
        promoted = True
        await db.commit()
        after_counts = in_transaction_counts
        manifest = {
            "dataset_version": DATASET_VERSION,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "database_name": make_url(settings.async_database_url).database,
            "storage_root": str(storage_root),
            "storage_folder": STORAGE_FOLDER,
            "storage_files": sorted(item["relative_path"] for item in storage_plan.values()),
            "before_counts": before_counts,
            "after_counts": after_counts,
            "inserted_ids": ids,
            "statistics_by_job": actual_by_job,
            "real_model_calls": 0,
            "synthetic_report_notice": "All imported screening plans/reports are visibly labeled portfolio fixtures, not DeepSeek outputs.",
        }
        write_manifest(manifest)
        print("portfolio demo dataset imported successfully")
        print(json.dumps({key: len(value) for key, value in ids.items()}, ensure_ascii=False, indent=2))
        print(f"manifest: {MANIFEST_PATH}")
    except BaseException:
        await db.rollback()
        if apply:
            if staging_dir is not None:
                remove_owned_directory(staging_dir, storage_root)
            if promoted:
                remove_owned_directory(final_dir, storage_root)
        raise
    finally:
        await db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect, dry-run, or explicitly import the local portfolio dataset."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inspect", help="read-only database and storage preflight")
    subparsers.add_parser("dry-run", help="insert into a real transaction, verify, then roll back")
    apply_parser = subparsers.add_parser("apply", help="commit the verified local import")
    apply_parser.add_argument("--confirm", required=True)
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.command == "inspect":
        await inspect()
    elif args.command == "dry-run":
        await execute_import(apply=False, confirmation=None)
    else:
        await execute_import(apply=True, confirmation=args.confirm)
    engine = get_async_engine()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(async_main())
