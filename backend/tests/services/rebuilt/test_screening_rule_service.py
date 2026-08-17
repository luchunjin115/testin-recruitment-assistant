from unittest import TestCase

from pydantic import ValidationError

from app.schemas.rebuilt.job import JobRequirementsV1
from app.schemas.rebuilt.screening_rules import (
    CriterionMatchInput,
    DeterministicCandidateFacts,
    HardRequirementCheck,
    RequiredExperienceAssessment,
    ScreeningCriterion,
    ScreeningRuleScoreRequest,
)
from app.services.rebuilt.screening_rule_service import ScreeningRuleService


def make_requirements(**overrides) -> JobRequirementsV1:
    payload = {
        "schema_version": "1.0",
        "responsibilities": ["负责招聘平台核心服务"],
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "minimum_work_years": 3,
        "education_requirement": "bachelor_or_above",
        "required_experiences": ["高并发系统经验"],
        "preferred_experiences": ["招聘系统经验"],
        "keywords": ["FastAPI"],
        "additional_requirements": ["能够独立排查线上问题"],
    }
    payload.update(overrides)
    return JobRequirementsV1.model_validate(payload)


def match(
    criterion: str,
    level: str,
    *,
    evidence: list[str] | None = None,
) -> CriterionMatchInput:
    return CriterionMatchInput(
        criterion=criterion,
        match_level=level,
        evidence=([] if level == "unknown" else evidence or [f"{criterion} evidence"]),
    )


class ScreeningHardRequirementRuleTest(TestCase):
    def setUp(self) -> None:
        self.service = ScreeningRuleService()

    def test_skill_aliases_match_but_java_never_matches_javascript(self) -> None:
        requirements = make_requirements(
            required_skills=["Node.js", "PostgreSQL", "Java"],
            minimum_work_years=None,
            education_requirement="none",
            required_experiences=[],
        )
        result = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(
                skills=["node", "postgres", "JavaScript"],
                skills_evidence_complete=True,
            ),
        )

        statuses = {check.requirement: check.status.value for check in result.checks}
        self.assertEqual(statuses["Node.js"], "passed")
        self.assertEqual(statuses["PostgreSQL"], "passed")
        self.assertEqual(statuses["Java"], "failed")
        self.assertEqual(result.criterion_matches[0].match_level.value, "none")

    def test_missing_skill_is_unknown_until_hr_confirms_complete_skill_list(self) -> None:
        requirements = make_requirements(
            required_skills=["Python"],
            minimum_work_years=None,
            education_requirement="none",
            required_experiences=[],
        )

        unknown = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(skills=[]),
        )
        failed = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(
                skills=[],
                skills_evidence_complete=True,
            ),
        )

        self.assertEqual(unknown.checks[0].status.value, "unknown")
        self.assertEqual(failed.checks[0].status.value, "failed")

    def test_work_years_and_education_use_explicit_levels_only(self) -> None:
        requirements = make_requirements(
            required_skills=[],
            required_experiences=[],
            minimum_work_years=5,
            education_requirement="master_or_above",
        )
        result = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(
                work_years=4,
                education_level="硕士研究生",
            ),
        )

        statuses = {check.criterion.value: check.status.value for check in result.checks}
        self.assertEqual(statuses["minimum_work_years"], "failed")
        self.assertEqual(statuses["education_requirement"], "passed")

        unknown = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(
                work_years=None,
                education_level="研究生",
            ),
        )
        self.assertTrue(all(check.status.value == "unknown" for check in unknown.checks))

    def test_not_applicable_years_education_and_experience_are_omitted(self) -> None:
        result = self.service.evaluate_hard_requirements(
            make_requirements(
                required_skills=[],
                minimum_work_years=0,
                education_requirement="none",
                required_experiences=[],
            ),
            DeterministicCandidateFacts(),
        )

        self.assertEqual(result.checks, [])
        self.assertEqual(result.criterion_matches, [])

    def test_required_experience_keeps_passed_failed_and_unknown_separate(self) -> None:
        requirements = make_requirements(
            required_skills=[],
            minimum_work_years=None,
            education_requirement="none",
            required_experiences=["支付系统经验", "高并发经验", "带队经验"],
        )
        result = self.service.evaluate_hard_requirements(
            requirements,
            DeterministicCandidateFacts(
                required_experiences=[
                    RequiredExperienceAssessment(
                        requirement="支付系统经验",
                        status="passed",
                        evidence=["项目 A：负责支付链路"],
                    ),
                    RequiredExperienceAssessment(
                        requirement="高并发经验",
                        status="failed",
                        evidence=["HR 确认未参与高并发系统"],
                    ),
                ]
            ),
        )

        statuses = {check.requirement: check.status.value for check in result.checks}
        self.assertEqual(statuses["支付系统经验"], "passed")
        self.assertEqual(statuses["高并发经验"], "failed")
        self.assertEqual(statuses["带队经验"], "unknown")
        self.assertEqual(result.criterion_matches[0].match_level.value, "none")

    def test_undefined_required_experience_assessment_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "未定义"):
            self.service.evaluate_hard_requirements(
                make_requirements(required_experiences=["支付系统经验"]),
                DeterministicCandidateFacts(
                    required_experiences=[
                        RequiredExperienceAssessment(
                            requirement="岗位没有这一项",
                            status="passed",
                            evidence=["evidence"],
                        )
                    ]
                ),
            )


class ScreeningScoreRuleTest(TestCase):
    def setUp(self) -> None:
        self.service = ScreeningRuleService()

    def test_all_full_criteria_score_100_with_complete_coverage(self) -> None:
        matches = [match(criterion.value, "full") for criterion in ScreeningCriterion]

        result = self.service.score(
            ScreeningRuleScoreRequest(criterion_matches=matches)
        )

        self.assertFalse(result.blocked)
        self.assertEqual(result.overall_score, 100)
        self.assertEqual(result.evidence_coverage_rate, 1.0)
        self.assertEqual(result.recommendation.value, "strong_recommend")
        self.assertFalse(result.recommendation_capped)

    def test_match_levels_convert_to_fixed_ratios(self) -> None:
        cases = (
            ("full", "full", 100, "strong_recommend"),
            ("full", "partial", 75, "recommend"),
            ("full", "none", 50, "review_required"),
            ("weak", "weak", 20, "low_match"),
        )
        for skill_level, experience_level, score, recommendation in cases:
            with self.subTest(score=score):
                result = self.service.score(
                    ScreeningRuleScoreRequest(
                        criterion_matches=[
                            match("preferred_skills", skill_level),
                            match("preferred_experiences", experience_level),
                        ]
                    )
                )
                self.assertEqual(result.overall_score, score)
                self.assertEqual(result.recommendation.value, recommendation)

    def test_not_applicable_subcriteria_redistribute_inside_dimension(self) -> None:
        result = self.service.score(
            ScreeningRuleScoreRequest(
                criterion_matches=[match("required_skills", "full")]
            )
        )

        self.assertEqual(result.overall_score, 100)
        self.assertEqual(result.criterion_scores[0].adjusted_weight, 40.0)
        self.assertEqual(result.dimension_scores[0].configured_weight, 40)

    def test_unknown_lowers_coverage_without_becoming_failed(self) -> None:
        result = self.service.score(
            ScreeningRuleScoreRequest(
                criterion_matches=[
                    match("required_skills", "full"),
                    match("responsibility_relevance", "unknown"),
                    match("project_relevance", "unknown"),
                ]
            )
        )

        self.assertFalse(result.blocked)
        self.assertEqual(result.evidence_coverage_rate, 0.4706)
        self.assertNotIn("hard_requirement_unknown", [item.value for item in result.cap_reasons])
        self.assertIn("low_evidence_coverage", [item.value for item in result.cap_reasons])
        self.assertNotIn("hard_requirement_failed", [item.value for item in result.cap_reasons])

    def test_hard_failure_caps_an_otherwise_high_score(self) -> None:
        matches = [match(criterion.value, "full") for criterion in ScreeningCriterion]
        matches = [
            match(item.criterion.value, "none")
            if item.criterion is ScreeningCriterion.EDUCATION_REQUIREMENT
            else item
            for item in matches
        ]
        result = self.service.score(
            ScreeningRuleScoreRequest(
                criterion_matches=matches,
                hard_requirement_checks=[
                    HardRequirementCheck(
                        criterion="education_requirement",
                        requirement="master_or_above",
                        status="failed",
                        evidence=["已确认学历为本科"],
                    )
                ],
            )
        )

        self.assertGreaterEqual(result.overall_score, 85)
        self.assertEqual(result.recommendation.value, "review_required")
        self.assertTrue(result.recommendation_capped)
        self.assertIn("hard_requirement_failed", [item.value for item in result.cap_reasons])

    def test_all_unknown_is_blocked_instead_of_fake_zero_score(self) -> None:
        result = self.service.score(
            ScreeningRuleScoreRequest(
                criterion_matches=[
                    match("required_skills", "unknown"),
                    match("responsibility_relevance", "unknown"),
                ]
            )
        )

        self.assertTrue(result.blocked)
        self.assertIsNone(result.overall_score)
        self.assertIsNone(result.recommendation)

    def test_known_match_without_evidence_and_duplicate_criterion_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CriterionMatchInput(
                criterion="keywords",
                match_level="full",
                evidence=[],
            )

        with self.assertRaises(ValidationError):
            ScreeningRuleScoreRequest(
                criterion_matches=[
                    match("keywords", "full"),
                    match("keywords", "partial"),
                ]
            )
