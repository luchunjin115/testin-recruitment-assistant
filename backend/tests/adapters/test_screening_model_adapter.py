import json
from decimal import Decimal
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

import httpx
from openai import APITimeoutError
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.adapters.screening_model import (
    DeepSeekScreeningModelAdapter,
    ScreeningModelConfigurationError,
    ScreeningModelAuthenticationError,
    ScreeningModelEmptyResponseError,
    ScreeningModelInputError,
    ScreeningModelQuotaError,
    ScreeningModelRateLimitError,
    ScreeningModelResponseInterruptedError,
    ScreeningModelServiceUnavailableError,
    ScreeningModelTimeoutError,
    ScreeningModelUpstreamError,
)
from app.core.config import Settings
from app.core.llm import get_screening_model_llm_client
from app.schemas.screening_evaluation import (
    ScreeningCandidateMaterial,
    ScreeningProfileMaterial,
)
from app.schemas.screening_rubric import (
    RubricCriterionSource,
    RubricDimension,
    SemanticRubricCriterion,
)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "DEEPSEEK_API_KEY": "stage7-screening-test-key",
        "SCREENING_MODEL_NAME": "deepseek-v4-flash",
        "SCREENING_MODEL_TIMEOUT_SECONDS": 20,
        "SCREENING_MODEL_MAX_INPUT_CHARS": 160_000,
        "SCREENING_MODEL_MAX_OUTPUT_TOKENS": 4_000,
        "SCREENING_MODEL_INPUT_COST_PER_MILLION": Decimal("1.5"),
        "SCREENING_MODEL_OUTPUT_COST_PER_MILLION": Decimal("2"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_criteria() -> list[SemanticRubricCriterion]:
    return [
        SemanticRubricCriterion(
            key=f"criterion_{index}",
            name=f"评分项 {index}",
            description="评价候选人的岗位相关能力。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            suggested_share=25,
            high_score_anchor="有完整过程和结果证据。",
            mid_score_anchor="有部分过程或结果证据。",
            low_score_anchor="缺少具体过程和结果。",
            source=RubricCriterionSource.TEMPLATE,
        )
        for index in range(1, 5)
    ]


def make_material(text: str = "主导支付系统故障排查。") -> ScreeningCandidateMaterial:
    return ScreeningCandidateMaterial(
        application_ref="application-adapter-test",
        confirmed_profile=ScreeningProfileMaterial(skills=["Python"]),
        resume_text=text,
    )


def make_response(
    *,
    content: str | None = '{"schema_version":"1.0","evaluations":[]}',
    finish_reason: str | None = "stop",
    choices: list[object] | None = None,
) -> SimpleNamespace:
    resolved_choices = choices
    if resolved_choices is None:
        resolved_choices = [
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content),
            )
        ]
    return SimpleNamespace(
        choices=resolved_choices,
        model="deepseek-v4-flash-0813",
        usage=SimpleNamespace(prompt_tokens=200, completion_tokens=300),
    )


def make_client(*, result: object | None = None, error: Exception | None = None) -> Mock:
    client = Mock()
    client.chat.completions.create = AsyncMock(return_value=result, side_effect=error)
    return client


def make_status_error(status_code: int) -> APIStatusError:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(status_code, request=request)
    return APIStatusError(
        "sensitive upstream body",
        response=response,
        body={"detail": "sensitive upstream body"},
    )


class ScreeningModelClientFactoryTest(TestCase):
    @patch("app.core.llm.AsyncOpenAI")
    def test_client_has_bounded_timeout_and_no_hidden_retries(self, client_class: Mock) -> None:
        get_screening_model_llm_client(make_settings())

        client_class.assert_called_once_with(
            api_key="stage7-screening-test-key",
            base_url="https://api.deepseek.com",
            timeout=20,
            max_retries=0,
        )

    def test_adapter_rejects_disabled_missing_key_and_version_drift(self) -> None:
        for settings in (
            make_settings(SCREENING_MODEL_ENABLED=False),
            make_settings(DEEPSEEK_API_KEY=""),
            make_settings(SCREENING_MODEL_PROMPT_VERSION="screening_evaluation_v1"),
            make_settings(SCREENING_MODEL_SCHEMA_VERSION="2.0"),
        ):
            with self.subTest(settings=settings), self.assertRaises(
                ScreeningModelConfigurationError
            ):
                DeepSeekScreeningModelAdapter(settings=settings)


class DeepSeekScreeningModelAdapterTest(IsolatedAsyncioTestCase):
    async def test_evaluate_sends_exactly_one_json_request_and_records_metadata(self) -> None:
        client = make_client(result=make_response())
        adapter = DeepSeekScreeningModelAdapter(
            settings=make_settings(),
            client=client,
        )

        result = await adapter.evaluate(
            {"title": "后端工程师", "candidate_email": "secret@example.com"},
            make_criteria(),
            make_material(),
        )

        self.assertEqual(client.chat.completions.create.await_count, 1)
        request = client.chat.completions.create.await_args.kwargs
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["max_tokens"], 4_000)
        self.assertFalse(request["stream"])
        serialized = json.dumps(request["messages"], ensure_ascii=False)
        self.assertNotIn("secret@example.com", serialized)
        self.assertEqual(result.model, "deepseek-v4-flash-0813")
        self.assertEqual(result.input_tokens, 200)
        self.assertEqual(result.output_tokens, 300)
        self.assertEqual(result.estimated_cost, Decimal("0.000900"))
        self.assertGreaterEqual(result.duration_ms, 0)

    async def test_input_limit_rejects_before_provider_call(self) -> None:
        client = make_client(result=make_response())
        adapter = DeepSeekScreeningModelAdapter(
            settings=make_settings(SCREENING_MODEL_MAX_INPUT_CHARS=10_000),
            client=client,
        )

        with self.assertRaises(ScreeningModelInputError):
            await adapter.evaluate(
                {"title": "后端工程师"},
                make_criteria(),
                make_material("项目经历" * 8_000),
            )

        client.chat.completions.create.assert_not_awaited()

    async def test_timeout_is_sanitized_and_not_retried(self) -> None:
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
        client = make_client(error=APITimeoutError(request=request))
        adapter = DeepSeekScreeningModelAdapter(
            settings=make_settings(),
            client=client,
        )

        with self.assertRaises(ScreeningModelTimeoutError) as raised:
            await adapter.evaluate(
                {"title": "私密岗位"},
                make_criteria(),
                make_material("私密候选人经历"),
            )

        self.assertEqual(client.chat.completions.create.await_count, 1)
        self.assertNotIn("私密岗位", str(raised.exception))
        self.assertNotIn("私密候选人经历", str(raised.exception))

    async def test_known_sdk_failures_map_to_stable_privacy_safe_errors(self) -> None:
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
        cases = (
            (
                AuthenticationError(
                    "secret auth body",
                    response=httpx.Response(401, request=request),
                    body=None,
                ),
                ScreeningModelAuthenticationError,
            ),
            (
                RateLimitError(
                    "secret rate body",
                    response=httpx.Response(429, request=request),
                    body=None,
                ),
                ScreeningModelRateLimitError,
            ),
            (
                InternalServerError(
                    "secret server body",
                    response=httpx.Response(500, request=request),
                    body=None,
                ),
                ScreeningModelServiceUnavailableError,
            ),
            (
                APIConnectionError(message="secret connection", request=request),
                ScreeningModelServiceUnavailableError,
            ),
            (RuntimeError("sk-secret private resume"), ScreeningModelUpstreamError),
        )
        for upstream_error, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                client = make_client(error=upstream_error)
                adapter = DeepSeekScreeningModelAdapter(
                    settings=make_settings(),
                    client=client,
                )
                with self.assertRaises(expected_error) as raised:
                    await adapter.evaluate(
                        {"title": "私密岗位"},
                        make_criteria(),
                        make_material("私密候选人材料"),
                    )
                self.assertNotIn("secret", str(raised.exception))
                self.assertNotIn("私密候选人材料", str(raised.exception))
                self.assertEqual(client.chat.completions.create.await_count, 1)

    async def test_http_statuses_map_without_upstream_body_leaks(self) -> None:
        cases = (
            (402, ScreeningModelQuotaError),
            (503, ScreeningModelServiceUnavailableError),
            (422, ScreeningModelUpstreamError),
        )
        for status_code, expected_error in cases:
            with self.subTest(status_code=status_code):
                adapter = DeepSeekScreeningModelAdapter(
                    settings=make_settings(),
                    client=make_client(error=make_status_error(status_code)),
                )
                with self.assertRaises(expected_error) as raised:
                    await adapter.evaluate(
                        {"title": "测试岗位"},
                        make_criteria(),
                        make_material(),
                    )
                self.assertNotIn("sensitive upstream body", str(raised.exception))

    async def test_empty_or_interrupted_response_is_rejected(self) -> None:
        cases = (
            (make_response(choices=[]), ScreeningModelEmptyResponseError),
            (make_response(content=" "), ScreeningModelEmptyResponseError),
            (
                make_response(finish_reason="length"),
                ScreeningModelResponseInterruptedError,
            ),
        )
        for response, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                adapter = DeepSeekScreeningModelAdapter(
                    settings=make_settings(),
                    client=make_client(result=response),
                )
                with self.assertRaises(expected_error):
                    await adapter.evaluate(
                        {"title": "测试岗位"},
                        make_criteria(),
                        make_material(),
                    )
