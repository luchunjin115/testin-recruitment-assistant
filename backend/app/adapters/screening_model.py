from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.config import Settings, get_settings
from app.core.llm import get_screening_model_llm_client
from app.prompts.screening_evaluation import (
    SCREENING_EVALUATION_PROMPT_VERSION,
    ScreeningPromptBuilder,
)
from app.schemas.screening_evaluation import (
    SCREENING_EVALUATION_SCHEMA_VERSION,
    ScreeningCandidateMaterial,
)
from app.schemas.screening_rubric import SemanticRubricCriterion


SCREENING_MODEL_CONFIG_VERSION = "1.0"


class ScreeningModelAdapterError(RuntimeError):
    """Privacy-safe base error for candidate semantic evaluation providers."""

    code = "screening_model_upstream_error"


class ScreeningModelConfigurationError(ScreeningModelAdapterError):
    code = "screening_model_configuration_error"


class ScreeningModelInputError(ScreeningModelAdapterError):
    code = "screening_model_input_error"


class ScreeningModelAuthenticationError(ScreeningModelAdapterError):
    code = "screening_model_authentication_error"


class ScreeningModelQuotaError(ScreeningModelAdapterError):
    code = "screening_model_quota_error"


class ScreeningModelRateLimitError(ScreeningModelAdapterError):
    code = "screening_model_rate_limit_error"


class ScreeningModelTimeoutError(ScreeningModelAdapterError):
    code = "screening_model_timeout_error"


class ScreeningModelServiceUnavailableError(ScreeningModelAdapterError):
    code = "screening_model_service_unavailable"


class ScreeningModelEmptyResponseError(ScreeningModelAdapterError):
    code = "screening_model_empty_response"


class ScreeningModelResponseInterruptedError(ScreeningModelAdapterError):
    code = "screening_model_response_interrupted"


class ScreeningModelUpstreamError(ScreeningModelAdapterError):
    code = "screening_model_upstream_error"


@dataclass(frozen=True, slots=True)
class ScreeningModelAdapterResult:
    content: str
    model: str
    finish_reason: str
    duration_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: Decimal | None = None


class DeepSeekScreeningModelAdapter:
    """Make exactly one bounded, non-streaming candidate evaluation request."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._validate_configuration()
        if client is None:
            if not self.settings.DEEPSEEK_API_KEY.strip():
                raise ScreeningModelConfigurationError("DeepSeek API Key 未配置")
            client = get_screening_model_llm_client(self.settings)
        self.client = client

    async def evaluate(
        self,
        job_context: Mapping[str, Any],
        semantic_items: Sequence[SemanticRubricCriterion],
        candidate_material: ScreeningCandidateMaterial,
    ) -> ScreeningModelAdapterResult:
        try:
            messages = ScreeningPromptBuilder.build_messages(
                job_context,
                semantic_items,
                candidate_material,
            )
        except (TypeError, ValueError):
            raise ScreeningModelInputError("候选人语义评价输入不合法") from None
        input_chars = sum(len(message["content"]) for message in messages)
        if input_chars > self.settings.SCREENING_MODEL_MAX_INPUT_CHARS:
            raise ScreeningModelInputError("候选人语义评价输入超过安全长度上限")
        started = time.perf_counter_ns()
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.SCREENING_MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.settings.SCREENING_MODEL_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError:
            raise ScreeningModelTimeoutError("候选人语义评价模型调用超时") from None
        except AuthenticationError:
            raise ScreeningModelAuthenticationError("DeepSeek 认证失败") from None
        except RateLimitError:
            raise ScreeningModelRateLimitError("DeepSeek 请求达到速率上限") from None
        except InternalServerError:
            raise ScreeningModelServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        except APIConnectionError:
            raise ScreeningModelServiceUnavailableError("无法连接 DeepSeek 服务") from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception:
            raise ScreeningModelUpstreamError("DeepSeek 返回未识别的上游错误") from None
        duration_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
        return self._read_response(response, duration_ms=duration_ms)

    def _validate_configuration(self) -> None:
        if not self.settings.SCREENING_MODEL_ENABLED:
            raise ScreeningModelConfigurationError("候选人语义评价模型未启用")
        if (
            self.settings.SCREENING_MODEL_PROMPT_VERSION
            != SCREENING_EVALUATION_PROMPT_VERSION
        ):
            raise ScreeningModelConfigurationError("候选人语义评价 Prompt 版本不一致")
        if (
            self.settings.SCREENING_MODEL_SCHEMA_VERSION
            != SCREENING_EVALUATION_SCHEMA_VERSION
        ):
            raise ScreeningModelConfigurationError("候选人语义评价 Schema 版本不一致")

    @staticmethod
    def _raise_status_error(exc: APIStatusError) -> None:
        if exc.status_code in {401, 403}:
            raise ScreeningModelAuthenticationError("DeepSeek 认证或访问授权失败") from None
        if exc.status_code == 402:
            raise ScreeningModelQuotaError("DeepSeek 账户余额或配额不足") from None
        if exc.status_code == 429:
            raise ScreeningModelRateLimitError("DeepSeek 请求达到速率上限") from None
        if exc.status_code >= 500:
            raise ScreeningModelServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        raise ScreeningModelUpstreamError("DeepSeek 拒绝了候选人语义评价请求") from None

    def _read_response(
        self,
        response: Any,
        *,
        duration_ms: int,
    ) -> ScreeningModelAdapterResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise ScreeningModelEmptyResponseError("DeepSeek 未返回候选结果")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            raise ScreeningModelResponseInterruptedError("DeepSeek 输出未正常完成")
        content = getattr(getattr(choice, "message", None), "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ScreeningModelEmptyResponseError("DeepSeek 返回了空内容")
        usage = getattr(response, "usage", None)
        input_tokens = self._optional_int(getattr(usage, "prompt_tokens", None))
        output_tokens = self._optional_int(getattr(usage, "completion_tokens", None))
        model = getattr(response, "model", None)
        return ScreeningModelAdapterResult(
            content=content,
            model=(
                model
                if isinstance(model, str) and model
                else self.settings.SCREENING_MODEL_NAME
            ),
            finish_reason=finish_reason,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(
        self,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> Decimal | None:
        input_price = self.settings.SCREENING_MODEL_INPUT_COST_PER_MILLION
        output_price = self.settings.SCREENING_MODEL_OUTPUT_COST_PER_MILLION
        if (
            input_tokens is None
            or output_tokens is None
            or input_price is None
            or output_price is None
        ):
            return None
        million = Decimal("1000000")
        return (
            Decimal(input_tokens) * input_price / million
            + Decimal(output_tokens) * output_price / million
        ).quantize(Decimal("0.000001"))

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None


__all__ = [
    "SCREENING_MODEL_CONFIG_VERSION",
    "DeepSeekScreeningModelAdapter",
    "ScreeningModelAdapterError",
    "ScreeningModelAdapterResult",
    "ScreeningModelAuthenticationError",
    "ScreeningModelConfigurationError",
    "ScreeningModelEmptyResponseError",
    "ScreeningModelInputError",
    "ScreeningModelQuotaError",
    "ScreeningModelRateLimitError",
    "ScreeningModelResponseInterruptedError",
    "ScreeningModelServiceUnavailableError",
    "ScreeningModelTimeoutError",
    "ScreeningModelUpstreamError",
]
