from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.config import Settings, get_settings
from app.core.llm import get_screening_evaluation_llm_client
from app.prompts.screening_evaluation import (
    SCREENING_EVALUATION_PROMPT_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    build_screening_evaluation_messages,
    build_screening_evaluation_v5_messages,
)
from app.schemas.screening_evaluation import (
    SCREENING_EVALUATION_SCHEMA_VERSION,
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)


class ScreeningEvaluationAdapterError(RuntimeError):
    code = "SCREENING_EVALUATION_UPSTREAM_ERROR"
    retryable = False


class ScreeningEvaluationConfigurationError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_CONFIGURATION_ERROR"


class ScreeningEvaluationInputError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_INPUT_ERROR"


class ScreeningEvaluationAuthenticationError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_AUTHENTICATION_ERROR"


class ScreeningEvaluationQuotaError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_QUOTA_ERROR"


class ScreeningEvaluationRateLimitError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_RATE_LIMITED"
    retryable = True


class ScreeningEvaluationTimeoutError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_TIMEOUT"
    retryable = True


class ScreeningEvaluationServiceUnavailableError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_SERVICE_UNAVAILABLE"
    retryable = True


class ScreeningEvaluationEmptyResponseError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_EMPTY_RESPONSE"


class ScreeningEvaluationResponseInterruptedError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_RESPONSE_INTERRUPTED"


class ScreeningEvaluationUpstreamError(ScreeningEvaluationAdapterError):
    code = "SCREENING_EVALUATION_UPSTREAM_ERROR"


@dataclass(frozen=True, slots=True)
class ScreeningEvaluationAdapterResult:
    content: str
    model: str
    finish_reason: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class DeepSeekScreeningEvaluationAdapter:
    """Call DeepSeek once and translate only response data and provider errors."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if (
            self.settings.SCREENING_EVALUATION_PROMPT_VERSION
            != SCREENING_EVALUATION_PROMPT_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛 Prompt 版本与代码不一致"
            )
        if (
            self.settings.SCREENING_EVALUATION_SCHEMA_VERSION
            != SCREENING_EVALUATION_SCHEMA_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛 Schema 版本与代码不一致"
            )
        if (
            self.settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
            != SCREENING_EVALUATION_V5_PROMPT_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "5.0 AI 初筛 Prompt 版本与代码不一致"
            )
        if (
            self.settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
            != SCREENING_EVALUATION_V5_SCHEMA_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "5.0 AI 初筛 Schema 版本与代码不一致"
            )
        if client is None:
            if not self.settings.DEEPSEEK_API_KEY.strip():
                raise ScreeningEvaluationConfigurationError(
                    "AI 初筛所需的 DeepSeek API Key 未配置"
                )
            client = get_screening_evaluation_llm_client(self.settings)
        self.client = client

    async def evaluate(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult:
        payload = {
            "job": job_snapshot,
            "job_evaluation_plan": evaluation_plan,
            "evaluation_reference_at": evaluation_reference_at,
            "evaluation_timezone": evaluation_timezone,
            "experience_period_facts": experience_period_facts,
            "resume": sanitized_resume,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if (
            not job_snapshot
            or not evaluation_plan
            or not sanitized_resume.strip()
            or len(serialized) > self.settings.SCREENING_EVALUATION_MAX_INPUT_CHARS
        ):
            raise ScreeningEvaluationInputError("AI 初筛输入为空或超过安全长度上限")

        return await self._evaluate_with_messages(
            messages=build_screening_evaluation_messages(
                job_snapshot=job_snapshot,
                evaluation_plan=evaluation_plan,
                sanitized_resume=sanitized_resume,
                evaluation_reference_at=evaluation_reference_at,
                evaluation_timezone=evaluation_timezone,
                experience_period_facts=experience_period_facts,
            )
        )

    async def evaluate_v5(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult:
        payload = {
            "job": job_snapshot,
            "job_evaluation_plan": evaluation_plan,
            "evaluation_reference_at": evaluation_reference_at,
            "evaluation_timezone": evaluation_timezone,
            "experience_period_facts": experience_period_facts,
            "resume": sanitized_resume,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if (
            not job_snapshot
            or not evaluation_plan
            or not sanitized_resume.strip()
            or len(serialized) > self.settings.SCREENING_EVALUATION_MAX_INPUT_CHARS
        ):
            raise ScreeningEvaluationInputError("5.0 AI 初筛输入为空或超过安全长度上限")
        return await self._evaluate_with_messages(
            messages=build_screening_evaluation_v5_messages(
                job_snapshot=job_snapshot,
                evaluation_plan=evaluation_plan,
                sanitized_resume=sanitized_resume,
                evaluation_reference_at=evaluation_reference_at,
                evaluation_timezone=evaluation_timezone,
                experience_period_facts=experience_period_facts,
            )
        )

    async def _evaluate_with_messages(
        self,
        *,
        messages: list[dict[str, str]],
    ) -> ScreeningEvaluationAdapterResult:
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.SCREENING_EVALUATION_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.settings.SCREENING_EVALUATION_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError:
            raise ScreeningEvaluationTimeoutError("AI 初筛模型调用超时") from None
        except AuthenticationError:
            raise ScreeningEvaluationAuthenticationError(
                "AI 初筛模型认证失败"
            ) from None
        except RateLimitError:
            raise ScreeningEvaluationRateLimitError(
                "AI 初筛模型请求达到速率上限"
            ) from None
        except InternalServerError:
            raise ScreeningEvaluationServiceUnavailableError(
                "AI 初筛模型服务暂时不可用"
            ) from None
        except APIConnectionError:
            raise ScreeningEvaluationServiceUnavailableError(
                "无法连接 AI 初筛模型服务"
            ) from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception:
            raise ScreeningEvaluationUpstreamError(
                "AI 初筛模型返回未识别的上游错误"
            ) from None

        return self._read_response(response)

    @staticmethod
    def _raise_status_error(exc: APIStatusError) -> None:
        if exc.status_code in {401, 403}:
            raise ScreeningEvaluationAuthenticationError(
                "AI 初筛模型认证或访问授权失败"
            ) from None
        if exc.status_code == 402:
            raise ScreeningEvaluationQuotaError(
                "AI 初筛模型账户余额或配额不足"
            ) from None
        if exc.status_code == 429:
            raise ScreeningEvaluationRateLimitError(
                "AI 初筛模型请求达到速率上限"
            ) from None
        if exc.status_code >= 500:
            raise ScreeningEvaluationServiceUnavailableError(
                "AI 初筛模型服务暂时不可用"
            ) from None
        raise ScreeningEvaluationUpstreamError("AI 初筛模型拒绝了请求") from None

    def _read_response(self, response: Any) -> ScreeningEvaluationAdapterResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise ScreeningEvaluationEmptyResponseError("AI 初筛模型未返回候选结果")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            message = (
                "AI 初筛模型输出达到长度上限，结果可能被截断"
                if finish_reason == "length"
                else "AI 初筛模型输出未正常完成"
            )
            raise ScreeningEvaluationResponseInterruptedError(message)
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ScreeningEvaluationEmptyResponseError("AI 初筛模型返回了空内容")

        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None)
        return ScreeningEvaluationAdapterResult(
            content=content,
            model=(
                model
                if isinstance(model, str) and model
                else self.settings.SCREENING_EVALUATION_MODEL
            ),
            finish_reason=finish_reason,
            input_tokens=self._optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=self._optional_int(
                getattr(usage, "completion_tokens", None)
            ),
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None


class FakeScreeningEvaluationAdapter:
    """Deterministic test adapter; it never performs network access."""

    def __init__(
        self,
        outcomes: Iterable[ScreeningEvaluationAdapterResult | Exception],
    ) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def evaluate(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult:
        self.calls.append(
            {
                "job_snapshot": job_snapshot,
                "evaluation_plan": evaluation_plan,
                "sanitized_resume": sanitized_resume,
                "evaluation_reference_at": evaluation_reference_at,
                "evaluation_timezone": evaluation_timezone,
                "experience_period_facts": experience_period_facts,
            }
        )
        if not self._outcomes:
            raise AssertionError("Fake Adapter 没有可返回的预设结果")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def evaluate_v5(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult:
        return await self.evaluate(
            job_snapshot=job_snapshot,
            evaluation_plan=evaluation_plan,
            sanitized_resume=sanitized_resume,
            evaluation_reference_at=evaluation_reference_at,
            evaluation_timezone=evaluation_timezone,
            experience_period_facts=experience_period_facts,
        )
