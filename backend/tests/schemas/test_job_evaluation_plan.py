from datetime import datetime, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.schemas.job_evaluation_plan import (
    AIExtractedEvaluationPlan,
    JobEvaluationPlanAIInput,
    JobEvaluationPlanFreeTextCoverage,
    JobEvaluationItem,
    JobEvaluationPlanRead,
    StructuredCoverageResult,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def make_item(**overrides):
    values = {
        "key": "requirement:skill:python",
        "title": "Python",
        "category": "skill",
        "priority": "required",
        "source_type": "structured",
        "source_field": "requirements.required_skills",
        "source_quote": None,
    }
    values.update(overrides)
    return values


def make_plan(**overrides):
    values = {
        "id": 1,
        "job_id": 2,
        "jd_fingerprint": FINGERPRINT,
        "status": "ready",
        "is_current": True,
        "items": [make_item()],
        "structured_coverage": {
            "source_schema_version": "1.0",
            "fields": [
                {
                    "source_field": "requirements.required_skills",
                    "source_value_count": 1,
                    "item_keys": ["requirement:skill:python"],
                }
            ],
            "all_covered": True,
        },
        "warnings": [],
        "prompt_version": "job_evaluation_plan_v1",
        "model_version": "deepseek-chat",
        "schema_version": "1.0",
        "input_fingerprint": FINGERPRINT,
        "input_snapshot": {
            "job_id": 2,
            "title": "后端工程师",
            "department": "研发部",
            "description": "负责后端开发",
            "requirements": {
                "schema_version": "1.0",
                "responsibilities": [],
                "required_skills": ["Python"],
                "preferred_skills": [],
                "minimum_work_years": None,
                "education_requirement": None,
                "required_experiences": [],
                "preferred_experiences": [],
                "keywords": [],
                "additional_requirements": [],
            },
        },
        "error_code": None,
        "error_message": None,
        "created_at": NOW,
        "completed_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


class JobEvaluationPlanSchemaTest(TestCase):
    def test_item_enums_source_rules_and_extra_fields_are_strict(self) -> None:
        item = JobEvaluationItem.model_validate(make_item())
        self.assertEqual(item.priority.value, "required")

        invalid_cases = (
            make_item(priority="mandatory"),
            make_item(category="culture"),
            make_item(source_type="structured", source_field=None),
            make_item(
                source_type="ai_extracted",
                source_field=None,
                source_quote=None,
            ),
            make_item(weight=40),
        )
        for payload in invalid_cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                JobEvaluationItem.model_validate(payload)

    def test_item_key_and_text_lengths_are_bounded(self) -> None:
        cases = (
            make_item(key="非法 key"),
            make_item(title="x" * 501),
            make_item(source_field="X-Invalid"),
            make_item(
                source_type="ai_extracted",
                source_field=None,
                source_quote="x" * 2_001,
            ),
        )
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                JobEvaluationItem.model_validate(payload)

    def test_plan_limits_items_and_enforces_status_payload(self) -> None:
        JobEvaluationPlanRead.model_validate(make_plan())

        invalid_cases = (
            make_plan(items=[make_item(key=f"item:{index}") for index in range(31)]),
            make_plan(status="ready", completed_at=None),
            make_plan(status="ready", items=[]),
            make_plan(
                status="failed",
                items=[],
                completed_at=NOW,
                error_code=None,
                error_message=None,
            ),
            make_plan(status="outdated", is_current=True),
            make_plan(legacy_weight=40),
        )
        for payload in invalid_cases:
            with self.subTest(status=payload.get("status")), self.assertRaises(
                ValidationError
            ):
                JobEvaluationPlanRead.model_validate(payload)

    def test_public_read_accepts_legacy_and_v2_without_exposing_internal_audit(
        self,
    ) -> None:
        legacy = JobEvaluationPlanRead.model_validate(
            make_plan(contract_outdated=True)
        )
        current = JobEvaluationPlanRead.model_validate(
            make_plan(schema_version="2.0", contract_outdated=False)
        )

        self.assertEqual(legacy.schema_version, "1.0")
        self.assertTrue(legacy.contract_outdated)
        self.assertEqual(current.schema_version, "2.0")
        self.assertFalse(current.contract_outdated)
        self.assertNotIn("free_text_coverage", current.model_dump(mode="json"))

    def test_internal_free_text_coverage_is_strict_and_complete(self) -> None:
        payload = {
            "rule_version": "jd_source_units_v1",
            "all_reviewed": True,
            "units": [
                {
                    "source_id": "description:0001",
                    "disposition": "requirements",
                    "item_keys": ["requirement:skill:python"],
                    "equivalent_structured_item_keys": [
                        "requirement:skill:python"
                    ],
                }
            ],
        }
        parsed = JobEvaluationPlanFreeTextCoverage.model_validate(payload)
        self.assertTrue(parsed.all_reviewed)

        invalid_cases = (
            dict(payload, all_reviewed=False),
            {
                **payload,
                "units": [
                    {
                        "source_id": "description:0001",
                        "disposition": "requirements",
                        "item_keys": [],
                        "equivalent_structured_item_keys": [],
                    }
                ],
            },
            {**payload, "unexpected": True},
        )
        for invalid in invalid_cases:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                JobEvaluationPlanFreeTextCoverage.model_validate(invalid)

    def test_failed_and_generating_statuses_have_safe_contracts(self) -> None:
        failed = JobEvaluationPlanRead.model_validate(
            make_plan(
                status="failed",
                items=[],
                completed_at=NOW,
                error_code="JOB_EVALUATION_PLAN_NO_ITEMS",
                error_message="没有识别到可评价的岗位要求",
            )
        )
        self.assertEqual(failed.error_code, "JOB_EVALUATION_PLAN_NO_ITEMS")

        generating = JobEvaluationPlanRead.model_validate(
            make_plan(
                status="generating",
                items=[],
                completed_at=None,
                error_code=None,
                error_message=None,
            )
        )
        self.assertIsNone(generating.completed_at)

    def test_structured_coverage_and_ai_output_reject_unknown_shape(self) -> None:
        with self.assertRaises(ValidationError):
            StructuredCoverageResult.model_validate(
                {
                    "source_schema_version": "1.0",
                    "fields": [
                        {
                            "source_field": "requirements.required_skills",
                            "source_value_count": 2,
                            "item_keys": ["requirement:skill:python"],
                        }
                    ],
                    "all_covered": True,
                }
            )

        with self.assertRaises(ValidationError):
            AIExtractedEvaluationPlan.model_validate(
                {
                    "schema_version": "1.0",
                    "items": [],
                    "overall_score": 90,
                }
            )

    def test_ai_schema_2_accepts_strict_source_reviews(self) -> None:
        parsed = AIExtractedEvaluationPlan.model_validate(
            {
                "schema_version": "2.0",
                "source_reviews": [
                    {
                        "source_id": "description:0001",
                        "disposition": "requirements",
                        "non_requirement_reason": None,
                        "items": [
                            {
                                "title": "Python",
                                "category": "skill",
                                "equivalent_structured_item_key": None,
                            }
                        ],
                    }
                ],
            }
        )

        self.assertEqual(parsed.schema_version, "2.0")
        self.assertEqual(parsed.source_reviews[0].items[0].title, "Python")

    def test_ai_schema_2_rejects_model_owned_business_fields_and_empty_reviews(self) -> None:
        invalid_cases = (
            {"schema_version": "2.0", "source_reviews": []},
            {
                "schema_version": "2.0",
                "source_reviews": [
                    {
                        "source_id": "description:0001",
                        "disposition": "requirements",
                        "non_requirement_reason": None,
                        "items": [
                            {
                                "title": "Python",
                                "category": "skill",
                                "equivalent_structured_item_key": None,
                                "priority": "required",
                            }
                        ],
                    }
                ],
            },
        )
        for payload in invalid_cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                AIExtractedEvaluationPlan.model_validate(payload)

    def test_ai_input_requires_snapshot_units_and_strict_structured_candidates(self) -> None:
        with self.assertRaises(ValidationError):
            JobEvaluationPlanAIInput.model_validate(make_plan()["input_snapshot"])
