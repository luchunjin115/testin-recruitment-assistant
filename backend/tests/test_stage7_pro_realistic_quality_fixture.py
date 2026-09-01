from __future__ import annotations

import json
import re
from collections import Counter
from types import SimpleNamespace

from app.core.config import Settings
from app.prompts.job_evaluation_plan import build_job_evaluation_plan_v5_messages
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from app.services.screening_evaluation_service import screening_evaluation_service

from tests.fixtures.stage7_pro_realistic_quality_samples import (
    CONFLICT_CASE_IDS,
    EXPECTED_NORMALIZED_FINGERPRINT,
    PLAN_JDS,
    REPORT_PAIRS,
    REVIEW_PATH,
    STABILITY_CASE_IDS,
    direction_counts,
    normalized_fixture_fingerprint,
)


def test_reviewed_fixture_has_fixed_denominators_and_unique_ids() -> None:
    assert REVIEW_PATH.exists()
    assert len(PLAN_JDS) == 5
    assert len(REPORT_PAIRS) == 20
    assert [item["case_id"] for item in PLAN_JDS] == [
        f"JD-{index:02d}" for index in range(1, 6)
    ]
    assert [item["case_id"] for item in REPORT_PAIRS] == [
        f"R{index:02d}" for index in range(1, 21)
    ]
    assert Counter(item["job_case_id"] for item in REPORT_PAIRS) == {
        f"JD-{index:02d}": 4 for index in range(1, 6)
    }


def test_each_job_keeps_the_complete_five_section_input_contract() -> None:
    required_fields = {
        "title",
        "department",
        "job_background",
        "job_responsibilities",
        "candidate_requirements",
        "preferred_qualifications",
        "public_notes",
    }
    for job in PLAN_JDS:
        assert required_fields < job.keys()
        assert all(job[field].strip() for field in required_fields)
        assert "不进入当前 AI 初筛评分" in job["candidate_requirements"]
        assert any(
            marker in job["public_notes"]
            for marker in ("不得", "不参与", "不作为")
        )


def test_pre_call_labels_are_balanced_bounded_and_evidence_is_locatable() -> None:
    assert direction_counts() == {
        "high_match": 5,
        "partial_match": 10,
        "low_match": 5,
    }
    for pair in REPORT_PAIRS:
        labels = pair["labels"]
        lower, upper = labels["score_range"]
        assert 0 <= lower <= upper <= 100
        assert labels["key_evidence_quotes"]
        assert all(
            quote in pair["resume_text"] for quote in labels["key_evidence_quotes"]
        )


def test_conflict_and_stability_sets_are_frozen_before_model_calls() -> None:
    pairs = {item["case_id"]: item for item in REPORT_PAIRS}
    assert CONFLICT_CASE_IDS == ("R04", "R08", "R12", "R16", "R20")
    assert STABILITY_CASE_IDS == ("R01", "R05", "R09", "R13", "R17")
    assert all(pairs[case_id]["labels"]["expected_conflicts"] for case_id in CONFLICT_CASE_IDS)
    assert all(
        pairs[case_id]["labels"]["expected_direction"] == "high_match"
        for case_id in STABILITY_CASE_IDS
    )


def test_fixture_contains_no_direct_contact_or_identity_values() -> None:
    rendered = "\n".join(
        [
            *(value for job in PLAN_JDS for value in job.values() if isinstance(value, str)),
            *(item["resume_text"] for item in REPORT_PAIRS),
        ]
    )
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", rendered)
    assert not re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", rendered)
    assert not re.search(r"(?<!\d)\d{17}[\dXx](?!\d)", rendered)
    assert all(term not in rendered for term in ("身份证号：", "手机号：", "邮箱：", "姓名："))


def test_normalized_fixture_fingerprint_is_frozen() -> None:
    assert EXPECTED_NORMALIZED_FINGERPRINT
    assert normalized_fixture_fingerprint() == EXPECTED_NORMALIZED_FINGERPRINT


def test_p1_zero_call_preflight_matches_the_frozen_fixture() -> None:
    preflight_path = (
        REVIEW_PATH.parent
        / "2026-09-01-stage7-pro-realistic-p1-zero-call-preflight.json"
    )
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))

    assert preflight["status"] == "passed"
    assert preflight["normalized_fixture_fingerprint"] == normalized_fixture_fingerprint()
    assert preflight["denominators"]["plan_job_count"] == len(PLAN_JDS)
    assert preflight["denominators"]["report_pair_count"] == len(REPORT_PAIRS)
    assert preflight["denominators"]["planned_business_call_count"] == 40
    assert preflight["case_contract"]["conflict_case_ids"] == list(CONFLICT_CASE_IDS)
    assert preflight["case_contract"]["stability_case_ids"] == list(STABILITY_CASE_IDS)
    assert preflight["preflight_checks"]["all_passed"] is True
    assert preflight["external_effects"] == {
        "api_key_read": False,
        "real_adapter_instantiated": False,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "input_token_count": 0,
        "output_token_count": 0,
        "estimated_spend_usd": 0,
        "postgresql_write_count": 0,
    }


def test_frozen_text_is_compatible_with_current_production_input_boundaries() -> None:
    settings = Settings(_env_file=None)
    for index, job in enumerate(PLAN_JDS, start=1):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            SimpleNamespace(id=240_000 + index, status="open", **job)
        )
        serialized_messages = json.dumps(
            build_job_evaluation_plan_v5_messages(snapshot.model_dump(mode="json")),
            ensure_ascii=False,
        )
        assert snapshot.schema_version == "5.0"
        assert "public_notes" not in serialized_messages
        assert len(serialized_messages) <= settings.JOB_EVALUATION_PLAN_MAX_INPUT_CHARS

    for pair in REPORT_PAIRS:
        sanitized = screening_evaluation_service.sanitize_resume_text(
            pair["resume_text"]
        )
        assert sanitized
        assert len(sanitized) <= settings.SCREENING_EVALUATION_MAX_INPUT_CHARS
        assert all(
            quote in sanitized for quote in pair["labels"]["key_evidence_quotes"]
        )
