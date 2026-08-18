import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

import httpx
from openai import APITimeoutError

from app.adapters.screening_rubric_generation import (
    DeepSeekRubricGenerationAdapter,
    RubricGenerationConfigurationError,
    RubricGenerationEmptyResponseError,
    RubricGenerationResponseInterruptedError,
    RubricGenerationTimeoutError,
)
from app.core.config import Settings
from app.core.llm import get_rubric_generation_llm_client


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "DEEPSEEK_API_KEY": "stage7-test-key",
        "RUBRIC_GENERATION_MODEL": "deepseek-v4-flash",
        "RUBRIC_GENERATION_TIMEOUT_SECONDS": 15,
        "RUBRIC_GENERATION_MAX_OUTPUT_TOKENS": 4_000,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_response(
    *,
    content: str | None = '{"schema_version":"1.0"}',
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


class RubricGenerationClientFactoryTest(TestCase):
    @patch("app.core.llm.AsyncOpenAI")
    def test_client_has_bounded_timeout_and_no_hidden_retries(self, client_class: Mock) -> None:
        get_rubric_generation_llm_client(make_settings())

        client_class.assert_called_once_with(
            api_key="stage7-test-key",
            base_url="https://api.deepseek.com",
            timeout=15,
            max_retries=0,
        )

    def test_adapter_rejects_missing_key_and_version_drift(self) -> None:
        with self.assertRaises(RubricGenerationConfigurationError):
            DeepSeekRubricGenerationAdapter(
                settings=make_settings(DEEPSEEK_API_KEY="")
            )
        with self.assertRaises(RubricGenerationConfigurationError):
            DeepSeekRubricGenerationAdapter(
                settings=make_settings(RUBRIC_GENERATION_SCHEMA_VERSION="2.0"),
                client=make_client(result=make_response()),
            )


class DeepSeekRubricGenerationAdapterTest(IsolatedAsyncioTestCase):
    async def test_generate_sends_one_json_request_with_safe_job_context(self) -> None:
        client = make_client(result=make_response())
        adapter = DeepSeekRubricGenerationAdapter(
            settings=make_settings(),
            client=client,
        )

        result = await adapter.generate(
            {
                "title": "后端工程师",
                "description": "负责平台开发",
                "phone": "13800138000",
            },
            "technical",
        )

        self.assertEqual(result.model, "deepseek-v4-flash-0813")
        self.assertEqual(result.input_tokens, 200)
        request = client.chat.completions.create.await_args.kwargs
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["max_tokens"], 4_000)
        self.assertFalse(request["stream"])
        serialized_messages = json.dumps(request["messages"], ensure_ascii=False)
        self.assertIn("后端工程师", serialized_messages)
        self.assertNotIn("13800138000", serialized_messages)

    async def test_timeout_is_sanitized(self) -> None:
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
        adapter = DeepSeekRubricGenerationAdapter(
            settings=make_settings(),
            client=make_client(error=APITimeoutError(request=request)),
        )

        with self.assertRaises(RubricGenerationTimeoutError) as raised:
            await adapter.generate({"title": "私密岗位"}, "standard")

        self.assertNotIn("私密岗位", str(raised.exception))

    async def test_empty_or_interrupted_response_is_rejected(self) -> None:
        cases = (
            (make_response(choices=[]), RubricGenerationEmptyResponseError),
            (make_response(content=" "), RubricGenerationEmptyResponseError),
            (
                make_response(finish_reason="length"),
                RubricGenerationResponseInterruptedError,
            ),
        )
        for response, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                adapter = DeepSeekRubricGenerationAdapter(
                    settings=make_settings(),
                    client=make_client(result=response),
                )
                with self.assertRaises(expected_error):
                    await adapter.generate({"title": "测试岗位"}, "standard")
