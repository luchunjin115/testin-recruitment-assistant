from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.job_evaluation_plans import router
from app.core.database import get_db
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.services.job_evaluation_plan_service import job_evaluation_plan_service
from tests.fixtures.job_evaluation_plan_v3 import (
    FINGERPRINT,
    make_evaluation_item,
    make_input_snapshot,
    make_source_review_summary,
    make_warning,
)


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def _v3_plan(*, status: str = "ready") -> JobEvaluationPlan:
    plan = JobEvaluationPlan(
        id=7,
        job_id=701,
        jd_fingerprint=FINGERPRINT,
        status=status,
        is_current=True,
        items=[make_evaluation_item()] if status == "ready" else [],
        structured_coverage={},
        free_text_coverage=None,
        warnings=[make_warning("priority_signal_conflict")],
        prompt_version="job_evaluation_plan_v5",
        model_version="fake-plan-model",
        schema_version="3.0",
        input_fingerprint=FINGERPRINT,
        input_snapshot=make_input_snapshot(),
        error_code=None,
        error_message=None,
        created_at=NOW,
        completed_at=NOW,
        updated_at=NOW,
    )
    plan.source_review_summary = make_source_review_summary()
    return plan


def _client() -> tuple[TestClient, Mock, FastAPI]:
    app = FastAPI()
    app.include_router(router)
    db = Mock()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False), db, app


def test_generate_endpoint_resumes_v3_service_instead_of_fixed_503() -> None:
    client, db, app = _client()
    service = AsyncMock(return_value=_v3_plan())
    try:
        with patch.object(job_evaluation_plan_service, "generate_for_job", service):
            response = client.post("/jobs/701/evaluation-plan/generate")
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["schema_version"] == "3.0"
    service.assert_awaited_once_with(db, 701)


def test_regenerate_endpoint_resumes_failed_v3_service_instead_of_fixed_503() -> None:
    client, db, app = _client()
    service = AsyncMock(return_value=_v3_plan())
    try:
        with patch.object(job_evaluation_plan_service, "regenerate_failed_plan", service):
            response = client.post("/jobs/701/evaluation-plan/regenerate")
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["schema_version"] == "3.0"
    service.assert_awaited_once_with(db, 701)


def test_get_endpoint_serializes_v3_sources_warnings_and_review_summary() -> None:
    client, _, app = _client()
    try:
        with patch.object(
            job_evaluation_plan_service,
            "get_plan_for_display",
            AsyncMock(return_value=_v3_plan()),
        ):
            response = client.get("/jobs/701/evaluation-plan")
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "3.0"
    assert payload["source_review_summary"]["all_reviewed"] is True
    assert payload["items"][0]["sources"][0]["source_unit_id"] == (
        "candidate_requirements:0001"
    )
    assert payload["warnings"][0]["code"] == "priority_signal_conflict"
    assert "structured_coverage" not in payload
    assert "free_text_coverage" not in payload
