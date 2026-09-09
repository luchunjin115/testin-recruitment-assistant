from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.application import (  # noqa: E402
    ApplicationLifecycleStatus,
    FinalOutcome,
    HRDecision,
    RecruitmentStage,
)
from app.schemas.candidate import CandidateCreate  # noqa: E402
from app.schemas.interview import InterviewRecordCreate  # noqa: E402
from app.schemas.job import JobCreate  # noqa: E402
from app.schemas.offer import OfferRecordCreate  # noqa: E402
from app.schemas.public_application import ApplicationProcessingRunCreate  # noqa: E402


def load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def funnel_counts(applications: list[dict[str, Any]]) -> dict[str, int]:
    passed = {
        "passed_no_interview", "scheduled_interview", "completed_pending",
        "next_round_pending", "offer_draft", "offer_sent", "offer_accepted",
        "admitted", "hired", "interview_rejected", "offer_declined",
        "candidate_withdrew",
    }
    interview_entered = passed - {"passed_no_interview"}
    interview_completed = interview_entered - {"scheduled_interview"}
    offer_sent = {"offer_sent", "offer_accepted", "admitted", "hired", "offer_declined"}
    offer_accepted = {"offer_accepted", "admitted", "hired"}
    admitted = {"admitted", "hired"}
    scenarios = Counter(row["scenario"] for row in applications)
    return {
        "applications": len(applications),
        "screening_passed": sum(scenarios[name] for name in passed),
        "interview_entered": sum(scenarios[name] for name in interview_entered),
        "interview_completed": sum(scenarios[name] for name in interview_completed),
        "offer_sent": sum(scenarios[name] for name in offer_sent),
        "offer_accepted": sum(scenarios[name] for name in offer_accepted),
        "admitted": sum(scenarios[name] for name in admitted),
        "hired": scenarios["hired"],
    }


def main() -> None:
    jobs_doc = load_json("jobs.json")
    candidates_doc = load_json("candidates.json")
    applications_doc = load_json("applications.json")
    expected_doc = load_json("expected_statistics.json")
    jobs = jobs_doc["jobs"]
    candidates = candidates_doc["candidates"]
    applications = applications_doc["applications"]

    versions = {
        jobs_doc["dataset_version"], candidates_doc["dataset_version"],
        applications_doc["dataset_version"], expected_doc["dataset_version"],
    }
    require(len(versions) == 1, "all documents must share one dataset_version")
    require(all(doc["fictional_data_only"] is True for doc in (jobs_doc, candidates_doc, applications_doc, expected_doc)), "fictional_data_only must be true")
    require(all(doc["automatic_database_write"] is False for doc in (jobs_doc, candidates_doc, applications_doc, expected_doc)), "dataset must not auto-write the database")

    require(len(jobs) == 5, "expected exactly 5 jobs")
    require(len(candidates) == 60, "expected exactly 60 candidates")
    require(len(candidates) < 100, "candidate count must stay below 100")
    require(len(applications) == 64, "expected exactly 64 applications")

    job_ids = [row["demo_job_id"] for row in jobs]
    candidate_ids = [row["demo_candidate_id"] for row in candidates]
    application_ids = [row["demo_application_id"] for row in applications]
    require(len(job_ids) == len(set(job_ids)), "job demo IDs must be unique")
    require(len(candidate_ids) == len(set(candidate_ids)), "candidate demo IDs must be unique")
    require(len(application_ids) == len(set(application_ids)), "application demo IDs must be unique")

    for job in jobs:
        JobCreate.model_validate(job["create_payload"])
        payload = job["create_payload"]
        for field in ("job_background", "job_responsibilities", "candidate_requirements", "preferred_qualifications", "public_notes"):
            require(bool(payload.get(field)), f"{job['demo_job_id']} missing five-section JD field {field}")
        require(job["desired_status"] in {"open", "closed"}, "unsupported desired job status")
        if job["desired_status"] == "closed":
            require(job["post_import_actions"] == ["close_after_historical_applications_created"], "closed job needs an explicit post-import close action")

    candidate_id_set = set(candidate_ids)
    job_id_set = set(job_ids)
    for candidate in candidates:
        require(candidate["email"].endswith("@portfolio.example"), f"unsafe demo email: {candidate['demo_candidate_id']}")
        require(candidate["phone"].startswith("+999"), f"unsafe demo phone: {candidate['demo_candidate_id']}")
        require("gender" not in candidate and "age" not in candidate, f"sensitive field in {candidate['demo_candidate_id']}")
        require(candidate["primary_job_id"] in job_id_set, f"unknown primary job for {candidate['demo_candidate_id']}")
        require(candidate["education_records"][0]["is_985"] is False, "school brand flags must not be used in demo evaluation")
        require(candidate["education_records"][0]["is_211"] is False, "school brand flags must not be used in demo evaluation")
        CandidateCreate.model_validate({
            "name": candidate["name"],
            "phone": candidate["phone"],
            "email": candidate["email"],
            "location": candidate["location"],
            "current_company": candidate["current_company"],
            "current_title": candidate["current_title"],
            "work_years": candidate["work_years"],
            "education_level": candidate["education_level"],
            "source": "portfolio_demo",
            "status": "new",
            "tags": candidate["skills"],
            "education_records": candidate["education_records"],
            "work_experiences": candidate["work_experiences"],
            "project_experiences": candidate["project_experiences"],
        })
        resume_path = ROOT / candidate["resume_file"]
        require(resume_path.is_file(), f"missing resume {resume_path.name}")
        content = resume_path.read_text(encoding="utf-8")
        require(candidate["name"] in content, f"resume name mismatch for {candidate['demo_candidate_id']}")
        require(candidate["email"] in content, f"resume email mismatch for {candidate['demo_candidate_id']}")
        require("作品集演示专用" in content and "均为虚构" in content, f"resume disclaimer missing for {candidate['demo_candidate_id']}")

    resume_files = sorted((ROOT / "resumes").glob("candidate_*.txt"))
    require(len(resume_files) == 60, "expected exactly 60 generated resume files")

    primary_counts = Counter()
    applications_by_candidate = Counter()
    for application in applications:
        require(application["demo_candidate_id"] in candidate_id_set, f"unknown candidate reference in {application['demo_application_id']}")
        require(application["demo_job_id"] in job_id_set, f"unknown job reference in {application['demo_application_id']}")
        applications_by_candidate[application["demo_candidate_id"]] += 1
        if application["is_primary_application"]:
            primary_counts[application["demo_job_id"]] += 1
        require(application["source"] in {"public_apply", "hr_screening", "hr_direct"}, "invalid application source")
        ApplicationLifecycleStatus(application["lifecycle_status"])
        RecruitmentStage(application["recruitment_stage"])
        HRDecision(application["hr_decision"])
        if application["final_outcome"] is not None:
            FinalOutcome(application["final_outcome"])
        if application["source"] == "hr_direct":
            require(application["scenario"] in {
                "passed_no_interview", "scheduled_interview", "completed_pending",
                "next_round_pending", "offer_draft", "offer_sent", "offer_accepted",
                "admitted", "hired", "interview_rejected", "offer_declined",
                "candidate_withdrew",
            }, "hr_direct applications must begin as passed")
        if application["processing_run"] is not None:
            require(application["source"] == "public_apply", "only public applications may have a processing run")
            ApplicationProcessingRunCreate.model_validate({
                "submission_id": 1,
                "application_id": 1,
                "resume_id": 1,
                "trigger_type": "automatic",
                **application["processing_run"],
            })
            require(application["processing_run"]["status"] not in {"queued", "running", "waiting_screening"}, "importable demo processing runs must be terminal to prevent automatic model calls")
            if application["processing_run"]["status"] == "paused":
                require(application["demo_job_id"] == "JOB-DA", "job_closed pauses must belong to the closed demo job")
        for interview in application["interviews"]:
            InterviewRecordCreate.model_validate({
                "application_id": 1,
                **{key: value for key, value in interview.items() if key not in {"demo_interview_id", "created_at"}},
            })
        for offer in application["offers"]:
            OfferRecordCreate.model_validate({
                "application_id": 1,
                **{key: value for key, value in offer.items() if key not in {"demo_offer_id", "created_at"}},
            })

    require(dict(primary_counts) == {"JOB-AI": 14, "JOB-BE": 12, "JOB-QA": 12, "JOB-FE": 11, "JOB-DA": 11}, "primary job distribution changed")
    require(Counter(applications_by_candidate.values()) == Counter({1: 56, 2: 4}), "expected 56 single-job and 4 cross-job candidates")
    require(Counter(row["source"] for row in applications) == Counter({"public_apply": 40, "hr_screening": 16, "hr_direct": 8}), "source distribution changed")

    actual_funnel = funnel_counts(applications)
    expected_funnel = {row["key"]: row["count"] for row in expected_doc["overall"]["funnel"]}
    require(actual_funnel == expected_funnel, f"funnel mismatch: {actual_funnel} != {expected_funnel}")
    require(list(actual_funnel.values()) == [64, 32, 27, 23, 11, 7, 5, 3], "portfolio funnel contract changed")
    require(expected_doc["overall"]["todos"] == {
        "scheduled_interviews": 4,
        "pending_interview_decisions": 3,
        "next_round_not_scheduled": 3,
        "draft_offers": 3,
        "sent_offers": 3,
        "accepted_offers": 2,
        "admitted_applications": 2,
        "total": 20,
    }, "todo distribution changed")

    print("portfolio demo dataset validation passed")
    print("5 jobs | 60 fictional candidates | 64 applications | 60 resumes")
    print("funnel: 64 -> 32 -> 27 -> 23 -> 11 -> 7 -> 5 -> 3")
    print("todos: 20 across all 7 stage-9 categories")


if __name__ == "__main__":
    main()
