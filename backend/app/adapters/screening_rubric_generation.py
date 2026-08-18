from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.config import Settings, get_settings
from app.core.llm import get_rubric_generation_llm_client
from app.prompts.screening_rubric import (
    RUBRIC_GENERATION_PROMPT_VERSION,
    RUBRIC_ITEM_ASSIST_PROMPT_VERSION,
    ScreeningRubricPromptBuilder,
)
from app.schemas.screening_rubric import (
    RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION,
    ManualSemanticCriterionInput,
    RubricTemplateKey,
)


class RubricGenerationAdapterError(RuntimeError):
    """Privacy-safe base error for rubric generation providers."""

    code = "rubric_generation_upstream_error"


class RubricGenerationConfigurationError(RubricGenerationAdapterError):
    code = "rubric_generation_configuration_error"


class RubricGenerationAuthenticationError(RubricGenerationAdapterError):
    code = "rubric_generation_authentication_error"


class RubricGenerationQuotaError(RubricGenerationAdapterError):
    code = "rubric_generation_quota_error"


class RubricGenerationRateLimitError(RubricGenerationAdapterError):
    code = "rubric_generation_rate_limit_error"


class RubricGenerationTimeoutError(RubricGenerationAdapterError):
    code = "rubric_generation_timeout_error"


class RubricGenerationServiceUnavailableError(RubricGenerationAdapterError):
    code = "rubric_generation_service_unavailable"


class RubricGenerationEmptyResponseError(RubricGenerationAdapterError):
    code = "rubric_generation_empty_response"


class RubricGenerationResponseInterruptedError(RubricGenerationAdapterError):
    code = "rubric_generation_response_interrupted"


class RubricGenerationUpstreamError(RubricGenerationAdapterError):
    code = "rubric_generation_upstream_error"


@dataclass(frozen=True, slots=True)
class RubricGenerationAdapterResult:
    content: str
    model: str
    finish_reason: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class DeepSeekRubricGenerationAdapter:
    """Make one non-streaming JSON request for a whole rubric or one HR item."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._validate_versions()
        if client is None:
            if not self.settings.DEEPSEEK_API_KEY.strip():
                raise RubricGenerationConfigurationError("DeepSeek API Key 未配置")
            client = get_rubric_generation_llm_client(self.settings)
        self.client = client

    async def generate(
        self,
        job_context: Mapping[str, Any],
        template_key: RubricTemplateKey,
    ) -> RubricGenerationAdapterResult:
        messages = ScreeningRubricPromptBuilder.build_generation_messages(
            job_context,
            template_key=template_key,
        )
        return await self._complete(messages)

    async def assist_item(
        self,
        job_context: Mapping[str, Any],
        item: ManualSemanticCriterionInput,
    ) -> RubricGenerationAdapterResult:
        messages = ScreeningRubricPromptBuilder.build_item_assistance_messages(
            job_context,
            item,
        )
        return await self._complete(messages)

    def _validate_versions(self) -> None:
        if (
            self.settings.RUBRIC_GENERATION_PROMPT_VERSION
            != RUBRIC_GENERATION_PROMPT_VERSION
        ):
            raise RubricGenerationConfigurationError("Rubric 生成 Prompt 版本不一致")
        if (
            self.settings.RUBRIC_ITEM_ASSIST_PROMPT_VERSION
            != RUBRIC_ITEM_ASSIST_PROMPT_VERSION
        ):
            raise RubricGenerationConfigurationError("Rubric 单项辅助 Prompt 版本不一致")
        if (
            self.settings.RUBRIC_GENERATION_SCHEMA_VERSION
            != RUBRIC_GENERATION_OUTPUT_SCHEMA_VERSION
        ):
            raise RubricGenerationConfigurationError("Rubric 生成 Schema 版本不一致")

    async def _complete(self, messages: list[dict[str, str]]) -> RubricGenerationAdapterResult:
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.RUBRIC_GENERATION_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.settings.RUBRIC_GENERATION_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError:
            raise RubricGenerationTimeoutError("Rubric 生成模型调用超时") from None
        except AuthenticationError:
            raise RubricGenerationAuthenticationError("DeepSeek 认证失败") from None
        except RateLimitError:
            raise RubricGenerationRateLimitError("DeepSeek 请求达到速率上限") from None
        except InternalServerError:
            raise RubricGenerationServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        except APIConnectionError:
            raise RubricGenerationServiceUnavailableError("无法连接 DeepSeek 服务") from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception:
            raise RubricGenerationUpstreamError("DeepSeek 返回未识别的上游错误") from None
        return self._read_response(response)

    @staticmethod
    def _raise_status_error(exc: APIStatusError) -> None:
        if exc.status_code in {401, 403}:
            raise RubricGenerationAuthenticationError("DeepSeek 认证或访问授权失败") from None
        if exc.status_code == 402:
            raise RubricGenerationQuotaError("DeepSeek 账户余额或配额不足") from None
        if exc.status_code == 429:
            raise RubricGenerationRateLimitError("DeepSeek 请求达到速率上限") from None
        if exc.status_code >= 500:
            raise RubricGenerationServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        raise RubricGenerationUpstreamError("DeepSeek 拒绝了 Rubric 生成请求") from None

    def _read_response(self, response: Any) -> RubricGenerationAdapterResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise RubricGenerationEmptyResponseError("DeepSeek 未返回候选结果")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            raise RubricGenerationResponseInterruptedError("DeepSeek 输出未正常完成")
        content = getattr(getattr(choice, "message", None), "content", None)
        if not isinstance(content, str) or not content.strip():
            raise RubricGenerationEmptyResponseError("DeepSeek 返回了空内容")
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None)
        return RubricGenerationAdapterResult(
            content=content,
            model=(
                model
                if isinstance(model, str) and model
                else self.settings.RUBRIC_GENERATION_MODEL
            ),
            finish_reason=finish_reason,
            input_tokens=self._optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=self._optional_int(getattr(usage, "completion_tokens", None)),
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None


__all__ = [
    "DeepSeekRubricGenerationAdapter",
    "RubricGenerationAdapterError",
    "RubricGenerationAdapterResult",
    "RubricGenerationAuthenticationError",
    "RubricGenerationConfigurationError",
    "RubricGenerationEmptyResponseError",
    "RubricGenerationQuotaError",
    "RubricGenerationRateLimitError",
    "RubricGenerationResponseInterruptedError",
    "RubricGenerationServiceUnavailableError",
    "RubricGenerationTimeoutError",
    "RubricGenerationUpstreamError",
]
