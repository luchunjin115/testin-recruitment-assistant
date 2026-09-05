from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.offers import install_offer_exception_handlers, router
from app.core.database import get_db
from app.models.application import Application
from app.models.offer_record import OfferRecord
from app.services.offer_service import (
    OfferActiveConflictError,
    OfferTransitionInvalidError,
    OfferVersionConflictError,
    offer_service,
)


NOW = datetime(2026, 9, 4, tzinfo=timezone.utc)


def offer_payload() -> dict:
    return {
        "position_title": "阶段 9D 虚构工程师",
        "currency": "CNY",
        "salary_period": "monthly",
        "base_salary_amount": "18888.80",
        "salary_months": "13.0",
        "bonus_note": "虚构奖金",
        "benefits_note": "虚构福利",
        "valid_until": "2026-10-01",
        "expected_start_date": "2026-10-15",
        "note": "虚构内部说明",
    }


def make_offer(status: str = "draft", version: int = 1) -> OfferRecord:
    return OfferRecord(
        id=31,
        application_id=7,
        version_number=1,
        status=status,
        position_title="阶段 9D 虚构工程师",
        currency="CNY",
        salary_period="monthly",
        base_salary_amount=Decimal("18888.80"),
        salary_months=Decimal("13.0"),
        bonus_note="虚构奖金",
        benefits_note="虚构福利",
        valid_until=date(2026, 10, 1),
        expected_start_date=date(2026, 10, 15),
        note="虚构内部说明",
        sent_at=NOW if status != "draft" else None,
        responded_at=NOW if status in {"accepted", "declined"} else None,
        closed_at=NOW if status in {"withdrawn", "expired"} else None,
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def make_application(stage: str = "offer") -> Application:
    return Application(
        id=7,
        candidate_id=2,
        job_id=3,
        current_resume_id=4,
        source="hr_screening",
        lifecycle_status="active",
        recruitment_stage=stage,
        hr_decision="passed",
        final_outcome=None,
        applied_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


class OfferApiTest(TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        install_offer_exception_handlers(self.app)
        self.app.include_router(router)
        self.db = Mock(name="test_database_session")

        async def override_get_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_offer_routes_call_services_and_serialize_decimal_as_string(self) -> None:
        offer = make_offer()
        with patch.object(
            offer_service, "list_offers", AsyncMock(return_value=[offer])
        ) as service_mock:
            response = self.client.get("/applications/7/offers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["base_salary_amount"], "18888.80")
        service_mock.assert_awaited_once_with(self.db, 7)

        with patch.object(
            offer_service, "create_offer", AsyncMock(return_value=offer)
        ) as service_mock:
            response = self.client.post(
                "/applications/7/offers", json=offer_payload()
            )
        self.assertEqual(response.status_code, 201)
        service_mock.assert_awaited_once()

    def test_all_high_risk_routes_require_explicit_confirmation(self) -> None:
        cases = (
            ("/offers/31/send", "offer_sent"),
            ("/offers/31/accept", "offer_accepted"),
            ("/offers/31/decline", "offer_declined"),
            ("/offers/31/withdraw", "offer_withdrawn"),
            ("/offers/31/expire", "offer_expired"),
            ("/applications/7/confirm-admission", "application_admitted"),
            ("/applications/7/confirm-hire", "application_hired"),
            ("/applications/7/withdraw", "candidate_withdrew"),
            ("/applications/7/cancel-process", "company_canceled"),
            ("/applications/7/reopen-stage9", "stage9_reopened"),
        )
        for path, reason_code in cases:
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    json={
                        "expected_version": 1,
                        "reason_code": reason_code,
                        "reason_detail": "虚构测试说明",
                        "confirmed": False,
                    },
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.json()["detail"]["code"],
                    "HR_ACTION_CONFIRMATION_REQUIRED",
                )

    def test_validation_errors_never_echo_sensitive_offer_values(self) -> None:
        sensitive = "987654321.12"
        response = self.client.post(
            "/applications/7/offers",
            json={**offer_payload(), "base_salary_amount": sensitive, "salary_months": None},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"], "OFFER_COMPENSATION_INVALID"
        )
        self.assertNotIn(sensitive, response.text)

    def test_stable_conflict_errors_do_not_leak_internal_messages(self) -> None:
        for exc, code in (
            (OfferActiveConflictError("salary=secret"), "OFFER_ACTIVE_CONFLICT"),
            (OfferTransitionInvalidError("salary=secret"), "OFFER_TRANSITION_INVALID"),
            (OfferVersionConflictError("salary=secret"), "OFFER_VERSION_CONFLICT"),
        ):
            with self.subTest(code=code), patch.object(
                offer_service, "create_offer", AsyncMock(side_effect=exc)
            ):
                response = self.client.post(
                    "/applications/7/offers", json=offer_payload()
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["detail"]["code"], code)
                self.assertNotIn("secret", response.text)

    def test_application_milestone_route_returns_independent_stage(self) -> None:
        application = make_application("admitted")
        with patch.object(
            offer_service, "confirm_admission", AsyncMock(return_value=application)
        ) as service_mock:
            response = self.client.post(
                "/applications/7/confirm-admission",
                json={
                    "expected_version": 3,
                    "reason_code": "application_admitted",
                    "reason_detail": "HR 已核实录取",
                    "confirmed": True,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitment_stage"], "admitted")
        service_mock.assert_awaited_once()

    def test_openapi_registers_each_9d_route_once(self) -> None:
        expected = {
            ("GET", "/applications/{application_id}/offers"),
            ("POST", "/applications/{application_id}/offers"),
            ("PUT", "/offers/{offer_id}"),
            ("POST", "/offers/{offer_id}/send"),
            ("POST", "/offers/{offer_id}/accept"),
            ("POST", "/offers/{offer_id}/decline"),
            ("POST", "/offers/{offer_id}/withdraw"),
            ("POST", "/offers/{offer_id}/expire"),
            ("POST", "/applications/{application_id}/confirm-admission"),
            ("POST", "/applications/{application_id}/confirm-hire"),
            ("POST", "/applications/{application_id}/withdraw"),
            ("POST", "/applications/{application_id}/cancel-process"),
            ("POST", "/applications/{application_id}/reopen-stage9"),
        }
        actual = [
            (method, route.path)
            for route in self.app.routes
            for method in getattr(route, "methods", set())
            if (method, route.path) in expected
        ]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
