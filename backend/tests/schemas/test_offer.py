from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.offer import (
    OfferDraftCreateRequest,
    OfferRecordRead,
    OfferSendRequest,
    OfferUpdateRequest,
)


class OfferSchemaTest(TestCase):
    def details(self) -> dict:
        return {
            "position_title": "阶段 9D 虚构后端工程师",
            "currency": "CNY",
            "salary_period": "monthly",
            "base_salary_amount": "18888.80",
            "salary_months": "13.0",
            "bonus_note": "虚构奖金说明",
            "benefits_note": "虚构福利说明",
            "valid_until": "2026-10-01",
            "expected_start_date": "2026-10-15",
            "note": "仅用于测试",
        }

    def test_decimal_contract_normalizes_strings_without_float(self) -> None:
        offer = OfferDraftCreateRequest.model_validate(self.details())
        self.assertEqual(offer.currency, "CNY")
        self.assertEqual(offer.base_salary_amount, Decimal("18888.80"))
        self.assertEqual(offer.salary_months, Decimal("13.0"))

        for value in (18888.8, True):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                OfferDraftCreateRequest.model_validate(
                    {**self.details(), "base_salary_amount": value}
                )

    def test_compensation_dates_period_and_extra_fields_are_strict(self) -> None:
        invalid_payloads = (
            {**self.details(), "base_salary_amount": "0"},
            {**self.details(), "salary_months": None},
            {
                **self.details(),
                "salary_period": "annual",
                "salary_months": "12.0",
            },
            {**self.details(), "expected_start_date": "2026-09-30"},
            {**self.details(), "private_salary": "do-not-accept"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                OfferDraftCreateRequest.model_validate(payload)

    def test_action_confirmation_reason_and_version_are_strict(self) -> None:
        valid = OfferSendRequest.model_validate(
            {
                "expected_version": 1,
                "reason_code": "offer_sent",
                "reason_detail": "HR 已通过线下渠道发送",
                "confirmed": True,
            }
        )
        self.assertEqual(valid.expected_version, 1)

        for payload in (
            {
                "expected_version": 1,
                "reason_code": "offer_sent",
                "reason_detail": "",
                "confirmed": True,
            },
            {
                "expected_version": 1.0,
                "reason_code": "offer_sent",
                "reason_detail": "已发送",
                "confirmed": True,
            },
            {
                "expected_version": 1,
                "reason_code": "offer_sent",
                "reason_detail": "已发送",
                "confirmed": "true",
            },
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                OfferSendRequest.model_validate(payload)

    def test_sent_offer_update_carries_correction_controls(self) -> None:
        update = OfferUpdateRequest.model_validate(
            {
                **self.details(),
                "expected_version": 2,
                "confirmed": True,
                "correction_reason": "修正虚构薪资记录",
            }
        )
        self.assertTrue(update.confirmed)
        self.assertEqual(update.expected_version, 2)

    def test_read_model_keeps_decimal_values_exact(self) -> None:
        now = datetime(2026, 9, 4, tzinfo=timezone.utc)
        record = OfferRecordRead.model_validate(
            {
                **self.details(),
                "id": 1,
                "application_id": 1,
                "version_number": 1,
                "status": "draft",
                "version": 1,
                "sent_at": None,
                "responded_at": None,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        self.assertIsInstance(record.base_salary_amount, Decimal)
        self.assertEqual(record.valid_until, date(2026, 10, 1))
