from unittest import TestCase

from pydantic import ValidationError

from app.schemas.screening_evaluation import AIScreeningEvaluationOutput


def make_output(**overrides):
    values = {
        "overall_score": 78,
        "overall_summary": "当前简历展示的后端经历与岗位主要要求较为匹配。",
        "requirement_assessments": [
            {
                "requirement_key": "requirement:skill:python",
                "score": 8,
                "reason": "有可核对的 Python 项目经历。",
                "calculation_note": None,
                "experience_period_fact_keys": [],
                "evidence": [
                    {"quote": "使用 Python 开发 FastAPI 服务", "section": "专业技能"}
                ],
            }
        ],
        "bonus_highlights": [],
        "tradeoff_reason": None,
        "interview_questions": ["请说明 Python 服务的个人贡献。"],
    }
    values.update(overrides)
    return values


class ScreeningEvaluationSchemaTest(TestCase):
    def test_valid_contract_accepts_empty_bonus_and_forbids_old_or_extra_fields(self) -> None:
        report = AIScreeningEvaluationOutput.model_validate(make_output())
        self.assertEqual(report.overall_score, 78)
        self.assertEqual(report.bonus_highlights, [])

        for field in ("display_label", "strengths", "gaps", "risks", "decision"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                AIScreeningEvaluationOutput.model_validate(
                    make_output(**{field: "不允许"})
                )

    def test_scores_are_strict_integers_and_bounded(self) -> None:
        invalid = (
            make_output(overall_score=-1),
            make_output(overall_score=101),
            make_output(overall_score=78.0),
            make_output(
                requirement_assessments=[
                    {
                        **make_output()["requirement_assessments"][0],
                        "score": "8",
                    }
                ]
            ),
            make_output(
                requirement_assessments=[
                    {
                        **make_output()["requirement_assessments"][0],
                        "score": 11,
                    }
                ]
            ),
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                AIScreeningEvaluationOutput.model_validate(payload)

    def test_text_lengths_item_counts_and_nested_extra_fields_are_bounded(self) -> None:
        assessment = make_output()["requirement_assessments"][0]
        invalid = (
            make_output(overall_summary=""),
            make_output(overall_summary="x" * 3_001),
            make_output(interview_questions=["问题"] * 6),
            make_output(requirement_assessments=[assessment] * 31),
            make_output(
                requirement_assessments=[
                    {**assessment, "reason": "x" * 1_001}
                ]
            ),
            make_output(
                requirement_assessments=[
                    {
                        **assessment,
                        "evidence": [{"quote": "证据", "page": 1}],
                    }
                ]
            ),
        )
        for payload in invalid:
            with self.subTest(), self.assertRaises(ValidationError):
                AIScreeningEvaluationOutput.model_validate(payload)

    def test_bonus_count_score_and_evidence_are_strict(self) -> None:
        bonus = {
            "title": "跨团队协作",
            "score": 8,
            "reason": "能为岗位协作带来正向价值。",
            "evidence": [{"quote": "推动跨团队协作", "section": "项目经历"}],
        }
        AIScreeningEvaluationOutput.model_validate(
            make_output(bonus_highlights=[bonus])
        )

        invalid = (
            make_output(bonus_highlights=[bonus] * 6),
            make_output(bonus_highlights=[{**bonus, "score": 6}]),
            make_output(bonus_highlights=[{**bonus, "score": 11}]),
            make_output(bonus_highlights=[{**bonus, "evidence": []}]),
        )
        for payload in invalid:
            with self.subTest(), self.assertRaises(ValidationError):
                AIScreeningEvaluationOutput.model_validate(payload)

    def test_experience_fact_keys_are_structured_and_bounded(self) -> None:
        assessment = make_output()["requirement_assessments"][0]
        valid_key = "experience_period:" + "a" * 16
        report = AIScreeningEvaluationOutput.model_validate(
            make_output(
                requirement_assessments=[
                    {**assessment, "experience_period_fact_keys": [valid_key]}
                ]
            )
        )
        self.assertEqual(
            report.requirement_assessments[0].experience_period_fact_keys,
            [valid_key],
        )
        with self.assertRaises(ValidationError):
            AIScreeningEvaluationOutput.model_validate(
                make_output(
                    requirement_assessments=[
                        {
                            **assessment,
                            "experience_period_fact_keys": ["not-a-fact-key"],
                        }
                    ]
                )
            )
