from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.screening_center import (
    ScreeningCenterAllowedAction,
    ScreeningCenterReportStatus,
)
from app.services.screening_center_service import (
    ScreeningCenterService,
    extract_screening_ability_tags,
)


NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def criterion(criterion_id: str, name: str, importance: str, score: int) -> dict:
    return {
        "criterion": {
            "criterion_id": criterion_id,
            "name": name,
            "importance": importance,
            "description": "仅用于确定性合同测试。",
            "screening_focus": "核对简历内可定位证据。",
            "origin": "hr_added",
            "sources": [],
            "hr_note": "虚构测试评价点",
        },
        "assessment": {
            "criterion_id": criterion_id,
            "score": score,
            "reason": "存在可定位的虚构项目证据。",
            "calculation_note": None,
            "experience_period_fact_keys": [],
            "evidence": [{"quote": "虚构项目证据", "section": "项目经历"}],
        },
    }


def report(*, schema_version: str = "5.0", outdated: bool = False):
    items = [
        criterion("criterion:0001", "Python API", "preferred", 9),
        criterion("criterion:0002", "分布式系统", "required", 9),
        criterion("criterion:0003", "Python API", "required", 8),
        criterion("criterion:0004", "毕业院校", "required", 10),
    ]
    return SimpleNamespace(
        schema_version=schema_version,
        is_outdated=outdated,
        generated_at=NOW,
        v5_report={
            "overall_score": 86,
            "display_label": "整体较匹配",
            "overall_summary": "有可靠证据。",
            "criterion_assessments": items,
            "strengths": [
                {
                    "summary": "优势",
                    "criterion_ids": ["criterion:0001", "criterion:0002", "criterion:9999"],
                    "evidence": [],
                },
                {"summary": "优势二", "criterion_ids": ["criterion:0003", "criterion:0004"], "evidence": []},
            ],
            "gaps": [],
            "risks_or_conflicts": [],
            "missing_info": [],
            "hr_follow_up_questions": [],
        },
    )


def test_ability_tags_are_evidence_backed_sorted_deduplicated_and_safe() -> None:
    tags = extract_screening_ability_tags(report(outdated=True))
    assert [tag.label for tag in tags] == ["分布式系统", "Python API"]
    assert [tag.score for tag in tags] == [9, 9]
    assert all(tag.evidence_count == 1 and tag.is_outdated for tag in tags)


def test_old_or_malformed_report_never_invents_tags() -> None:
    assert extract_screening_ability_tags(report(schema_version="4.0")) == []
    malformed = report()
    malformed.v5_report["criterion_assessments"][0]["assessment"]["evidence"] = []
    assert extract_screening_ability_tags(malformed) == []


def test_report_state_does_not_turn_missing_report_into_zero_score() -> None:
    service = ScreeningCenterService()
    failed = SimpleNamespace(status="failed", created_at=NOW)
    waiting = SimpleNamespace(status="waiting_resume", created_at=NOW)
    assert service._report_status(None, None) is ScreeningCenterReportStatus.NOT_STARTED
    assert service._report_status(None, failed) is ScreeningCenterReportStatus.FAILED
    assert service._report_status(None, waiting) is ScreeningCenterReportStatus.WAITING_RESUME
    assert service._report_status(report(), failed) is ScreeningCenterReportStatus.OLD_REPORT_RETAINED


def test_allowed_actions_follow_existing_service_preconditions() -> None:
    service = ScreeningCenterService()
    application = SimpleNamespace(
        lifecycle_status="active",
        recruitment_stage="screening_passed",
        hr_decision="passed",
        final_outcome=None,
    )
    job = SimpleNamespace(status="open")
    actions = service._allowed_actions(application, job, None, None)
    assert ScreeningCenterAllowedAction.SCHEDULE_INTERVIEW in actions
    assert ScreeningCenterAllowedAction.BACKUP in actions
    assert ScreeningCenterAllowedAction.REJECT in actions
    assert ScreeningCenterAllowedAction.PASS not in actions


def test_stage9_allowed_actions_follow_offer_and_final_result_state() -> None:
    service = ScreeningCenterService()
    job = SimpleNamespace(status="open")
    application = SimpleNamespace(
        lifecycle_status="active",
        recruitment_stage="offer",
        hr_decision="passed",
        final_outcome=None,
    )
    assert ScreeningCenterAllowedAction.CREATE_OFFER in service._allowed_actions(
        application, job, None, None, latest_offer_status=None
    )
    draft_actions = service._allowed_actions(
        application, job, None, None, latest_offer_status="draft"
    )
    assert ScreeningCenterAllowedAction.EDIT_OFFER in draft_actions
    assert ScreeningCenterAllowedAction.SEND_OFFER in draft_actions

    sent_actions = service._allowed_actions(
        application, job, None, None, latest_offer_status="sent"
    )
    for expected in (
        ScreeningCenterAllowedAction.EDIT_OFFER,
        ScreeningCenterAllowedAction.ACCEPT_OFFER,
        ScreeningCenterAllowedAction.DECLINE_OFFER,
        ScreeningCenterAllowedAction.WITHDRAW_OFFER,
        ScreeningCenterAllowedAction.EXPIRE_OFFER,
    ):
        assert expected in sent_actions
    for forbidden in (
        ScreeningCenterAllowedAction.PASS,
        ScreeningCenterAllowedAction.BACKUP,
        ScreeningCenterAllowedAction.REJECT,
    ):
        assert forbidden not in sent_actions

    application.recruitment_stage = "offer_accepted"
    accepted_actions = service._allowed_actions(application, job, None, None)
    assert ScreeningCenterAllowedAction.CONFIRM_ADMISSION in accepted_actions
    assert ScreeningCenterAllowedAction.REOPEN_STAGE9 in accepted_actions

    application.recruitment_stage = "admitted"
    admitted_actions = service._allowed_actions(application, job, None, None)
    assert ScreeningCenterAllowedAction.CONFIRM_HIRE in admitted_actions
    assert ScreeningCenterAllowedAction.REOPEN_STAGE9 in admitted_actions

    application.lifecycle_status = "ended"
    application.recruitment_stage = "offer"
    application.final_outcome = "offer_declined"
    ended_actions = service._allowed_actions(application, job, None, None)
    assert ended_actions == [
        ScreeningCenterAllowedAction.VIEW_DETAIL,
        ScreeningCenterAllowedAction.REOPEN_STAGE9,
    ]
