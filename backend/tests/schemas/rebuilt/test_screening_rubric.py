from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.rebuilt import (
    RUBRIC_FAIRNESS_RULES_VERSION,
    RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION,
    RUBRIC_SUBCRITERIA_VERSION,
    SCREENING_RUBRIC_SCHEMA_VERSION,
    JobScreeningRubricCreate,
    JobScreeningRubricRead,
    ScreeningRubricUpdateRequest,
    ScreeningRubricWeights,
    default_screening_rubric_weights,
)
from app.prompts.rebuilt.screening_rubric_templates import get_rubric_template


class ScreeningRubricWeightsTest(TestCase):
    def test_defaults_are_the_confirmed_40_25_20_10_5(self) -> None:
        weights = default_screening_rubric_weights()

        self.assertEqual(
            weights.model_dump(),
            {
                "must_have_requirements": 40,
                "work_experience_relevance": 25,
                "projects_and_capability": 20,
                "preferred_qualifications": 10,
                "keywords_and_additional": 5,
            },
        )

    def test_each_dimension_range_and_strict_integer_type_are_enforced(self) -> None:
        invalid_changes = (
            ("must_have_requirements", 29),
            ("must_have_requirements", 51),
            ("work_experience_relevance", 14),
            ("work_experience_relevance", 36),
            ("projects_and_capability", 9),
            ("projects_and_capability", 31),
            ("preferred_qualifications", -1),
            ("preferred_qualifications", 21),
            ("keywords_and_additional", -1),
            ("keywords_and_additional", 11),
            ("must_have_requirements", "40"),
        )
        defaults = default_screening_rubric_weights().model_dump()
        for field, value in invalid_changes:
            payload = {**defaults, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                ScreeningRubricWeights.model_validate(payload)

    def test_weight_total_must_equal_one_hundred(self) -> None:
        payload = default_screening_rubric_weights().model_dump()
        payload["preferred_qualifications"] = 9

        with self.assertRaises(ValidationError):
            ScreeningRubricWeights.model_validate(payload)

    def test_unknown_fields_are_rejected(self) -> None:
        payload = default_screening_rubric_weights().model_dump()
        payload["culture_fit"] = 10

        with self.assertRaises(ValidationError):
            ScreeningRubricWeights.model_validate(payload)


class ScreeningRubricRequestTest(TestCase):
    def test_create_uses_versioned_default_contract(self) -> None:
        rubric = JobScreeningRubricCreate(job_id=2)

        self.assertEqual(rubric.schema_version, SCREENING_RUBRIC_SCHEMA_VERSION)
        self.assertEqual(rubric.subcriteria_version, RUBRIC_SUBCRITERIA_VERSION)
        self.assertEqual(
            rubric.recommendation_thresholds_version,
            RUBRIC_RECOMMENDATION_THRESHOLDS_VERSION,
        )
        self.assertEqual(rubric.fairness_rules_version, RUBRIC_FAIRNESS_RULES_VERSION)
        self.assertEqual(rubric.weights, default_screening_rubric_weights())

    def test_hr_adjustment_requires_a_change_explanation(self) -> None:
        with self.assertRaises(ValidationError):
            JobScreeningRubricCreate(job_id=2, change_reason="hr_adjustment")

        rubric = JobScreeningRubricCreate(
            job_id=2,
            change_reason="hr_adjustment",
            change_detail="岗位更强调必备技能",
        )
        self.assertEqual(rubric.change_detail, "岗位更强调必备技能")

    def test_update_requires_exactly_one_of_weights_or_restore_defaults(self) -> None:
        invalid_payloads = (
            {"change_detail": "调整"},
            {
                "weights": default_screening_rubric_weights().model_dump(),
                "restore_defaults": True,
                "change_detail": "调整",
            },
            {"restore_defaults": "true", "change_detail": "恢复默认"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ScreeningRubricUpdateRequest.model_validate(payload)

    def test_restore_defaults_resolves_to_confirmed_weights(self) -> None:
        request = ScreeningRubricUpdateRequest(
            restore_defaults=True,
            change_detail="恢复项目统一默认值",
        )
        self.assertEqual(request.resolved_weights(), default_screening_rubric_weights())

    def test_read_schema_requires_complete_versioned_response(self) -> None:
        timestamp = datetime(2026, 8, 17, tzinfo=timezone.utc)
        rubric = JobScreeningRubricRead(
            id=1,
            job_id=2,
            version=1,
            weights=default_screening_rubric_weights(),
            schema_version="2.0",
            subcriteria_version="2.0",
            recommendation_thresholds_version="1.0",
            fairness_rules_version="1.0",
            is_current=True,
            source="standard_template",
            template_key="standard",
            status="active",
            semantic_items=get_rubric_template("standard").semantic_items,
            job_fingerprint="a" * 64,
            is_stale=False,
            stale_at=None,
            stale_reason=None,
            generation_metadata=None,
            change_reason="initial_default",
            change_detail=None,
            created_by=None,
            confirmed_by="system",
            confirmed_at=timestamp,
            abandoned_at=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.assertTrue(rubric.is_current)

        payload = rubric.model_dump()
        payload["schema_version"] = "3.0"
        with self.assertRaises(ValidationError):
            JobScreeningRubricRead.model_validate(payload)

