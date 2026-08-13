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
from app.core.llm import get_resume_structure_llm_client
from app.prompts.rebuilt.resume_structure import (
    RESUME_STRUCTURE_PROMPT_VERSION,
    build_resume_structure_messages,
)
from app.schemas.rebuilt.resume_parse import RESUME_PARSE_SCHEMA_VERSION


class ResumeStructureAdapterError(RuntimeError):
    """Base error with a stable, privacy-safe message for upper layers."""

    code = "resume_structure_upstream_error"


class ResumeStructureConfigurationError(ResumeStructureAdapterError):
    code = "resume_structure_configuration_error"


class ResumeStructureInputError(ResumeStructureAdapterError):
    code = "resume_structure_input_error"


class ResumeStructureAuthenticationError(ResumeStructureAdapterError):
    code = "resume_structure_authentication_error"


class ResumeStructureQuotaError(ResumeStructureAdapterError):
    code = "resume_structure_quota_error"


class ResumeStructureRateLimitError(ResumeStructureAdapterError):
    code = "resume_structure_rate_limit_error"


class ResumeStructureTimeoutError(ResumeStructureAdapterError):
    code = "resume_structure_timeout_error"


class ResumeStructureServiceUnavailableError(ResumeStructureAdapterError):
    code = "resume_structure_service_unavailable"


class ResumeStructureEmptyResponseError(ResumeStructureAdapterError):
    code = "resume_structure_empty_response"


class ResumeStructureResponseInterruptedError(ResumeStructureAdapterError):
    code = "resume_structure_response_interrupted"


class ResumeStructureUpstreamError(ResumeStructureAdapterError):
    code = "resume_structure_upstream_error"


@dataclass(frozen=True, slots=True)
class ResumeStructureAdapterResult:
    content: str
    model: str
    finish_reason: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class DeepSeekResumeStructureAdapter:
    """Send one non-streaming DeepSeek JSON Output request per method call."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if self.settings.RESUME_STRUCTURE_PROMPT_VERSION != RESUME_STRUCTURE_PROMPT_VERSION:
            raise ResumeStructureConfigurationError("简历结构化 Prompt 版本与代码不一致")
        if self.settings.RESUME_STRUCTURE_SCHEMA_VERSION != RESUME_PARSE_SCHEMA_VERSION:
            raise ResumeStructureConfigurationError("简历结构化 Schema 版本与代码不一致")
        if client is None:
            if not self.settings.DEEPSEEK_API_KEY.strip():
                raise ResumeStructureConfigurationError("DeepSeek API Key 未配置")
            client = get_resume_structure_llm_client(self.settings)
        self.client = client

    async def extract(self, raw_text: str) -> ResumeStructureAdapterResult:
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ResumeStructureInputError("简历原文为空，无法进行结构化识别")
        if len(raw_text) > self.settings.RESUME_STRUCTURE_MAX_INPUT_CHARS:
            raise ResumeStructureInputError("简历原文超过结构化识别的安全长度上限")

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.RESUME_STRUCTURE_MODEL,
                messages=build_resume_structure_messages(raw_text),
                response_format={"type": "json_object"},
                max_tokens=self.settings.RESUME_STRUCTURE_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError as exc:
            raise ResumeStructureTimeoutError("简历结构化模型调用超时") from None
        except AuthenticationError as exc:
            raise ResumeStructureAuthenticationError("DeepSeek 认证失败") from None
        except RateLimitError as exc:
            raise ResumeStructureRateLimitError("DeepSeek 请求达到速率上限") from None
        except InternalServerError as exc:
            raise ResumeStructureServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        except APIConnectionError as exc:
            raise ResumeStructureServiceUnavailableError("无法连接 DeepSeek 服务") from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception as exc:
            raise ResumeStructureUpstreamError("DeepSeek 返回未识别的上游错误") from None

        return self._read_response(response)

    def _raise_status_error(self, exc: APIStatusError) -> None:
        status_code = exc.status_code
        if status_code in {401, 403}:
            raise ResumeStructureAuthenticationError("DeepSeek 认证或访问授权失败") from None
        if status_code == 402:
            raise ResumeStructureQuotaError("DeepSeek 账户余额或配额不足") from None
        if status_code == 429:
            raise ResumeStructureRateLimitError("DeepSeek 请求达到速率上限") from None
        if status_code >= 500:
            raise ResumeStructureServiceUnavailableError("DeepSeek 服务暂时不可用") from None
        raise ResumeStructureUpstreamError("DeepSeek 拒绝了结构化识别请求") from None

    def _read_response(self, response: Any) -> ResumeStructureAdapterResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise ResumeStructureEmptyResponseError("DeepSeek 未返回候选结果")

        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            if finish_reason == "length":
                message = "DeepSeek 输出达到长度上限，结果可能被截断"
            elif finish_reason:
                message = "DeepSeek 输出未正常完成"
            else:
                message = "DeepSeek 响应缺少完成状态"
            raise ResumeStructureResponseInterruptedError(message)

        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ResumeStructureEmptyResponseError("DeepSeek 返回了空内容")

        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None)
        return ResumeStructureAdapterResult(
            content=content,
            model=model if isinstance(model, str) and model else self.settings.RESUME_STRUCTURE_MODEL,
            finish_reason=finish_reason,
            input_tokens=self._optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=self._optional_int(getattr(usage, "completion_tokens", None)),
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
