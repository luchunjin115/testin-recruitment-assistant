from datetime import datetime, timezone
from unittest import TestCase

from app.services.experience_period_service import ExperiencePeriodService


REFERENCE = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)


class ExperiencePeriodServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = ExperiencePeriodService()

    def build(self, text: str, reference: datetime = REFERENCE):
        return self.service.build(text, evaluation_reference_at=reference)

    def test_month_formats_and_present_terms_use_application_month(self) -> None:
        snapshot = self.build(
            "\n".join(
                (
                    "2021-07—2026-08",
                    "2021.07—Present",
                    "2021/07—Current",
                    "2021年7月—至今",
                )
            )
        )
        self.assertEqual(snapshot.reference_month, "2026-08")
        self.assertEqual([fact.duration_months for fact in snapshot.facts], [61] * 4)
        self.assertEqual(len({fact.key for fact in snapshot.facts}), 4)

    def test_shanghai_month_boundary_does_not_use_server_timezone(self) -> None:
        before = self.build(
            "2021-07—至今",
            datetime(2026, 7, 31, 15, 59, 59, tzinfo=timezone.utc),
        )
        after = self.build(
            "2021-07—至今",
            datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(before.reference_month, "2026-07")
        self.assertEqual(before.facts[0].duration_months, 60)
        self.assertEqual(after.reference_month, "2026-08")
        self.assertEqual(after.facts[0].duration_months, 61)

    def test_year_only_keeps_bounds_instead_of_inventing_months(self) -> None:
        fact = self.build("2021—2023").facts[0]
        self.assertIsNone(fact.normalized_start_month)
        self.assertIsNone(fact.normalized_end_month)
        self.assertIsNone(fact.duration_months)
        self.assertEqual(fact.duration_months_lower_bound, 13)
        self.assertEqual(fact.duration_months_upper_bound, 35)
        self.assertIn("year_precision_only", fact.warnings)

    def test_overlapping_periods_are_not_double_counted(self) -> None:
        snapshot = self.build("2021-01—2023-01\n2022-01—2024-01")
        keys = [fact.key for fact in snapshot.facts]
        self.assertEqual(self.service.duration_bounds_for_keys(snapshot.facts, keys), (36, 36))

    def test_invalid_and_post_application_periods_are_unusable(self) -> None:
        snapshot = self.build(
            "2025-01—2024-01\n2027-01—至今\n2025-01—2027-01"
        )
        first, second, third = snapshot.facts
        self.assertFalse(first.usable_for_reference)
        self.assertIn("end_before_start", first.warnings)
        self.assertFalse(second.usable_for_reference)
        self.assertIn("start_after_evaluation_reference", second.warnings)
        self.assertTrue(third.usable_for_reference)
        self.assertEqual(third.duration_months, 19)
        self.assertIn("end_after_evaluation_reference", third.warnings)

    def test_unparseable_text_does_not_fabricate_a_fact(self) -> None:
        self.assertEqual(self.build("多年互联网经验，时间记不清").facts, [])
