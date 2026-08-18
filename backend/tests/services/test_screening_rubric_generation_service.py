import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from app.adapters.screening_rubric_generation import (
    RubricGenerationAdapterResult,
    RubricGenerationTimeoutError,
)
from app.prompts.screening_rubric_templates import get_rubric_template
from app.schemas.screening_rubric import (
    ScreeningRubricGenerateRequest,
    ScreeningRubricItemAssistRequest,
)
from app.services.screening_rubric_service import (
    ScreeningRubricDraftAlreadyExistsError,
    ScreeningRubricGenerationInvalidOutputError,
    ScreeningRubricService,
    ScreeningRubricStaleError,
)
from tests.services.test_screening_rubric_service import (
    make_job,
    make_rubric,
    make_session,
)


def generation_content(*, unfair: bool = False) -> str:
    items = []
    for item in get_rubric_template("technical").semantic_items:
        payload = item.model_dump(mode="json")
        payload["source"] = "ai_generated"
        items.append(payload)
    if unfair:
        items[0]["description"] = "根据年龄判断候选人学习能力"
    return json.dumps(
        {
            "schema_version": "1.0",
            "template_key": "technical",
            "rationale": "该岗位需要结合职责、项目和工程实践进行评价",
            "semantic_items": items,
        },
        ensure_ascii=False,
    )


def adapter_result(content: str) -> RubricGenerationAdapterResult:
    return RubricGenerationAdapterResult(
        content=content,
        model="fake-rubric-model",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=200,
    )


def make_adapter(*, content: str | None = None, error: Exception | None = None) -> Mock:
    adapter = Mock()
    adapter.generate = AsyncMock(
        return_value=adapter_result(content or generation_content()),
        side_effect=error,
    )
    adapter.assist_item = AsyncMock()
    return adapter


class ScreeningRubricGenerationServiceTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = ScreeningRubricService()
        self.db = make_session()
        self.job = make_job()

    async def test_fake_generation_saves_validated_ai_draft_after_recheck(self) -> None:
        current = make_rubric()
        adapter = make_adapter()
        self.db.get.return_value = self.job
        self.db.scalar.side_effect = [None, self.job, None, current, 2]

        draft = await self.service.generate_draft(
            self.db,
            1,
            ScreeningRubricGenerateRequest(
                template_key="technical",
                change_detail="AI 生成技术岗位评分标准",
            ),
            adapter=adapter,
        )

        self.assertEqual(draft.status, "draft")
        self.assertFalse(draft.is_current)
        self.assertEqual(draft.source, "ai_generated")
        self.assertEqual(draft.template_key, "technical")
        self.assertEqual(len(draft.semantic_items), 6)
        self.assertEqual(draft.generation_metadata["model"], "fake-rubric-model")
        self.assertEqual(draft.generation_metadata["input_tokens"], 100)
        self.assertTrue(current.is_current)
        self.assertEqual(self.db.rollback.await_count, 1)
        self.db.commit.assert_awaited_once()
        adapter.generate.assert_awaited_once()

    async def test_existing_draft_rejects_before_spending_model_call(self) -> None:
        existing = make_rubric(version=2, is_current=False)
        existing.status = "draft"
        adapter = make_adapter()
        self.db.get.return_value = self.job
        self.db.scalar.return_value = existing

        with self.assertRaises(ScreeningRubricDraftAlreadyExistsError):
            await self.service.generate_draft(
                self.db,
                1,
                ScreeningRubricGenerateRequest(
                    template_key="technical",
                    change_detail="不应重复生成",
                ),
                adapter=adapter,
            )

        adapter.generate.assert_not_awaited()
        self.db.commit.assert_not_awaited()
        self.db.rollback.assert_awaited_once()

    async def test_timeout_or_invalid_output_never_changes_current_rubric(self) -> None:
        cases = (
            (
                make_adapter(error=RubricGenerationTimeoutError("timeout")),
                RubricGenerationTimeoutError,
            ),
            (make_adapter(content="not-json"), ScreeningRubricGenerationInvalidOutputError),
            (
                make_adapter(content=generation_content(unfair=True)),
                ScreeningRubricGenerationInvalidOutputError,
            ),
        )
        for adapter, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                db = make_session()
                db.get.return_value = self.job
                db.scalar.return_value = None
                with self.assertRaises(expected_error):
                    await self.service.generate_draft(
                        db,
                        1,
                        ScreeningRubricGenerateRequest(
                            template_key="technical",
                            change_detail="验证失败不落库",
                        ),
                        adapter=adapter,
                    )
                db.add_all.assert_not_called()
                db.commit.assert_not_awaited()

    async def test_job_change_during_generation_discards_result(self) -> None:
        changed_job = make_job()
        changed_job.description = "AI 调用期间被 HR 修改的新岗位描述"
        adapter = make_adapter()
        self.db.get.return_value = self.job
        self.db.scalar.side_effect = [None, changed_job]

        with self.assertRaises(ScreeningRubricStaleError):
            await self.service.generate_draft(
                self.db,
                1,
                ScreeningRubricGenerateRequest(
                    template_key="technical",
                    change_detail="生成期间岗位发生变化",
                ),
                adapter=adapter,
            )

        self.db.add_all.assert_not_called()
        self.db.commit.assert_not_awaited()
        self.assertEqual(self.db.rollback.await_count, 2)

    async def test_fake_item_assistance_returns_validated_suggestion_only(self) -> None:
        fingerprint = self.service.build_job_fingerprint(
            self.service._generation_job_context(self.job)
        )
        draft = make_rubric(version=2, is_current=False)
        draft.status = "draft"
        draft.job_fingerprint = fingerprint
        assisted = {
            "name": "复杂系统问题解决",
            "description": "评价候选人定位复杂系统问题并推动解决的能力",
            "dimension": "projects_and_capability",
            "suggested_share": 45,
            "high_score_anchor": "有复杂问题闭环和量化改进证据",
            "mid_score_anchor": "有问题处理经历但复杂度或结果一般",
            "low_score_anchor": "仅描述参与，缺少个人分析和结果证据",
        }
        adapter = make_adapter()
        adapter.assist_item.return_value = adapter_result(
            json.dumps(assisted, ensure_ascii=False)
        )
        self.db.get.return_value = self.job
        self.db.scalar.side_effect = [draft, self.job, draft]

        response = await self.service.assist_manual_item(
            self.db,
            1,
            ScreeningRubricItemAssistRequest(
                expected_job_fingerprint=fingerprint,
                item=assisted,
            ),
            adapter=adapter,
        )

        self.assertEqual(response.suggestion.name, "复杂系统问题解决")
        self.assertEqual(response.metadata.model, "fake-rubric-model")
        self.db.add_all.assert_not_called()
        self.db.commit.assert_not_awaited()
        self.assertEqual(self.db.rollback.await_count, 2)
