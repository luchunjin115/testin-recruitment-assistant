from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.config import Settings, get_settings
from app.core.llm import get_job_evaluation_plan_llm_client
from app.prompts.job_evaluation_plan import (
    JOB_EVALUATION_CRITERION_GROUPING_PROMPT_VERSION,
    JOB_EVALUATION_PLAN_PROMPT_VERSION,
    JOB_REQUIREMENT_COVERAGE_REVIEW_PROMPT_VERSION,
    JOB_REQUIREMENT_FACT_EXTRACTION_PROMPT_VERSION,
    JOB_REQUIREMENT_LOCAL_REPAIR_PROMPT_VERSION,
    build_evaluation_criterion_grouping_messages,
    build_job_evaluation_plan_messages,
    build_requirement_coverage_review_messages,
    build_requirement_fact_extraction_messages,
    build_requirement_local_repair_messages,
)
from app.schemas.job_evaluation_plan import (
    AIEvaluationCriterionGroupingOutput,
    AIExtractedEvaluationPlanV3,
    AIRequirementCoverageReviewOutput,
    AIRequirementFactExtractionOutput,
    AIRequirementLocalRepairOutput,
    JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_SCHEMA_VERSION,
    JOB_EVALUATION_PLAN_V4_MAX_INPUT_CHARS,
    JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_TOKENS,
    JobEvaluationCriterionGroupingInput,
    JobEvaluationPlanAIInputV3,
    JobRequirementCoverageReviewInput,
    JobRequirementFactExtractionInput,
    JobRequirementLocalRepairInput,
)


_V4_INPUT_TYPES: dict[str, type[BaseModel]] = {
    "fact_extraction": JobRequirementFactExtractionInput,
    "coverage_review": JobRequirementCoverageReviewInput,
    "local_repair": JobRequirementLocalRepairInput,
    "criterion_grouping": JobEvaluationCriterionGroupingInput,
}
_V4_OUTPUT_TYPES: dict[str, type[BaseModel]] = {
    "fact_extraction": AIRequirementFactExtractionOutput,
    "coverage_review": AIRequirementCoverageReviewOutput,
    "local_repair": AIRequirementLocalRepairOutput,
    "criterion_grouping": AIEvaluationCriterionGroupingOutput,
}
_V4_PROMPT_BUILDERS = {
    "fact_extraction": build_requirement_fact_extraction_messages,
    "coverage_review": build_requirement_coverage_review_messages,
    "local_repair": build_requirement_local_repair_messages,
    "criterion_grouping": build_evaluation_criterion_grouping_messages,
}
V4_PROMPT_VERSIONS = {
    "fact_extraction": JOB_REQUIREMENT_FACT_EXTRACTION_PROMPT_VERSION,
    "coverage_review": JOB_REQUIREMENT_COVERAGE_REVIEW_PROMPT_VERSION,
    "local_repair": JOB_REQUIREMENT_LOCAL_REPAIR_PROMPT_VERSION,
    "criterion_grouping": JOB_EVALUATION_CRITERION_GROUPING_PROMPT_VERSION,
}


class JobEvaluationPlanAdapterError(RuntimeError):
    code = "JOB_EVALUATION_PLAN_UPSTREAM_ERROR"
    retryable = False


class JobEvaluationPlanConfigurationError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_CONFIGURATION_ERROR"


class JobEvaluationPlanInputError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_INPUT_ERROR"


class JobEvaluationPlanAuthenticationError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_AUTHENTICATION_ERROR"


class JobEvaluationPlanQuotaError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_QUOTA_ERROR"


class JobEvaluationPlanRateLimitError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_RATE_LIMITED"
    retryable = True


class JobEvaluationPlanTimeoutError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_TIMEOUT"
    retryable = True


class JobEvaluationPlanServiceUnavailableError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_SERVICE_UNAVAILABLE"
    retryable = True


class JobEvaluationPlanEmptyResponseError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_EMPTY_RESPONSE"


class JobEvaluationPlanResponseInterruptedError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_RESPONSE_INTERRUPTED"


class JobEvaluationPlanUpstreamError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_UPSTREAM_ERROR"


class JobEvaluationPlanInvalidResponseError(JobEvaluationPlanAdapterError):
    code = "JOB_EVALUATION_PLAN_INVALID_RESPONSE"


@dataclass(frozen=True, slots=True)
class JobEvaluationPlanAdapterResult:
    content: str
    model: str
    finish_reason: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class DeepSeekJobEvaluationPlanAdapter:
    """Call DeepSeek and convert only the raw response and metadata."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if (
            self.settings.JOB_EVALUATION_PLAN_PROMPT_VERSION
            != JOB_EVALUATION_PLAN_PROMPT_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 Prompt 版本与代码不一致"
            )
        if (
            self.settings.JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION
            != JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 AI Schema 版本与代码不一致"
            )
        if (
            self.settings.JOB_EVALUATION_PLAN_SCHEMA_VERSION
            != JOB_EVALUATION_PLAN_SCHEMA_VERSION
        ):
            raise JobEvaluationPlanConfigurationError(
                "岗位评价计划 Schema 版本与代码不一致"
            )
        if client is None:
            if not self.settings.DEEPSEEK_API_KEY.strip():
                raise JobEvaluationPlanConfigurationError("DeepSeek API Key 未配置")
            client = get_job_evaluation_plan_llm_client(self.settings)
        self.client = client

    async def extract(
        self,
        input_snapshot: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        try:
            validated_input = JobEvaluationPlanAIInputV3.model_validate(input_snapshot)
        except (ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanInputError(
                "岗位评价计划 AI 输入未通过 Schema 校验"
            ) from None
        serialized = json.dumps(
            validated_input.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )
        if len(serialized) > self.settings.JOB_EVALUATION_PLAN_MAX_INPUT_CHARS:
            raise JobEvaluationPlanInputError("岗位 JD 为空或超过安全长度上限")

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.JOB_EVALUATION_PLAN_MODEL,
                messages=build_job_evaluation_plan_messages(
                    validated_input.model_dump(mode="json")
                ),
                response_format={"type": "json_object"},
                max_tokens=self.settings.JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError:
            raise JobEvaluationPlanTimeoutError("岗位评价计划模型调用超时") from None
        except AuthenticationError:
            raise JobEvaluationPlanAuthenticationError("DeepSeek 认证失败") from None
        except RateLimitError:
            raise JobEvaluationPlanRateLimitError("DeepSeek 请求达到速率上限") from None
        except InternalServerError:
            raise JobEvaluationPlanServiceUnavailableError(
                "DeepSeek 服务暂时不可用"
            ) from None
        except APIConnectionError:
            raise JobEvaluationPlanServiceUnavailableError(
                "无法连接 DeepSeek 服务"
            ) from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception:
            raise JobEvaluationPlanUpstreamError(
                "DeepSeek 返回未识别的上游错误"
            ) from None

        return self._read_response(response)

    async def generate_v4(
        self,
        role: str,
        generation_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        """Run one explicit 4.0 role without activating the Job/API workflow."""
        input_type = _V4_INPUT_TYPES.get(role)
        prompt_builder = _V4_PROMPT_BUILDERS.get(role)
        if input_type is None or prompt_builder is None:
            raise JobEvaluationPlanInputError("未知的岗位评价计划 4.0 调用角色")
        try:
            validated_input = input_type.model_validate(generation_input)
        except (ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanInputError(
                "岗位评价计划 4.0 AI 输入未通过独立 Schema 校验"
            ) from None
        payload = validated_input.model_dump(mode="json")
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(serialized) > JOB_EVALUATION_PLAN_V4_MAX_INPUT_CHARS:
            raise JobEvaluationPlanInputError(
                "岗位评价计划 4.0 单次输入超过技术安全边界"
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.JOB_EVALUATION_PLAN_MODEL,
                messages=prompt_builder(payload),
                response_format={"type": "json_object"},
                max_tokens=JOB_EVALUATION_PLAN_V4_MAX_OUTPUT_TOKENS,
                temperature=0.1,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except APITimeoutError:
            raise JobEvaluationPlanTimeoutError("岗位评价计划模型调用超时") from None
        except AuthenticationError:
            raise JobEvaluationPlanAuthenticationError("DeepSeek 认证失败") from None
        except RateLimitError:
            raise JobEvaluationPlanRateLimitError("DeepSeek 请求达到速率上限") from None
        except InternalServerError:
            raise JobEvaluationPlanServiceUnavailableError(
                "DeepSeek 服务暂时不可用"
            ) from None
        except APIConnectionError:
            raise JobEvaluationPlanServiceUnavailableError(
                "无法连接 DeepSeek 服务"
            ) from None
        except APIStatusError as exc:
            self._raise_status_error(exc)
        except Exception:
            raise JobEvaluationPlanUpstreamError(
                "DeepSeek 返回未识别的上游错误"
            ) from None
        return self._read_v4_response(response, role)

    @staticmethod
    def _raise_status_error(exc: APIStatusError) -> None:
        if exc.status_code in {401, 403}:
            raise JobEvaluationPlanAuthenticationError(
                "DeepSeek 认证或访问授权失败"
            ) from None
        if exc.status_code == 402:
            raise JobEvaluationPlanQuotaError("DeepSeek 账户余额或配额不足") from None
        if exc.status_code == 429:
            raise JobEvaluationPlanRateLimitError(
                "DeepSeek 请求达到速率上限"
            ) from None
        if exc.status_code >= 500:
            raise JobEvaluationPlanServiceUnavailableError(
                "DeepSeek 服务暂时不可用"
            ) from None
        raise JobEvaluationPlanUpstreamError("DeepSeek 拒绝了岗位拆解请求") from None

    def _read_response(self, response: Any) -> JobEvaluationPlanAdapterResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise JobEvaluationPlanEmptyResponseError("DeepSeek 未返回候选结果")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            message = (
                "DeepSeek 输出达到长度上限，结果可能被截断"
                if finish_reason == "length"
                else "DeepSeek 输出未正常完成"
            )
            raise JobEvaluationPlanResponseInterruptedError(message)
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise JobEvaluationPlanEmptyResponseError("DeepSeek 返回了空内容")
        try:
            payload = json.loads(
                content,
                object_pairs_hook=self._object_without_duplicate_keys,
            )
            AIExtractedEvaluationPlanV3.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanInvalidResponseError(
                "DeepSeek 返回内容未通过 AI 提取 Schema 3.0 校验"
            ) from None

        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None)
        return JobEvaluationPlanAdapterResult(
            content=content,
            model=(
                model
                if isinstance(model, str) and model
                else self.settings.JOB_EVALUATION_PLAN_MODEL
            ),
            finish_reason=finish_reason,
            input_tokens=self._optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=self._optional_int(
                getattr(usage, "completion_tokens", None)
            ),
        )

    def _read_v4_response(
        self,
        response: Any,
        role: str,
    ) -> JobEvaluationPlanAdapterResult:
        output_type = _V4_OUTPUT_TYPES.get(role)
        if output_type is None:
            raise JobEvaluationPlanInputError("未知的岗位评价计划 4.0 调用角色")
        choices = getattr(response, "choices", None)
        if not choices:
            raise JobEvaluationPlanEmptyResponseError("DeepSeek 未返回候选结果")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            message = (
                "DeepSeek 输出达到长度上限，结果可能被截断"
                if finish_reason == "length"
                else "DeepSeek 输出未正常完成"
            )
            raise JobEvaluationPlanResponseInterruptedError(message)
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise JobEvaluationPlanEmptyResponseError("DeepSeek 返回了空内容")
        try:
            payload = json.loads(
                content,
                object_pairs_hook=self._object_without_duplicate_keys,
            )
            output_type.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise JobEvaluationPlanInvalidResponseError(
                f"DeepSeek {role} 返回内容未通过独立 4.0 Schema 校验"
            ) from None

        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None)
        return JobEvaluationPlanAdapterResult(
            content=content,
            model=(
                model
                if isinstance(model, str) and model
                else self.settings.JOB_EVALUATION_PLAN_MODEL
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

    @staticmethod
    def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("JSON 对象包含重复字段")
            value[key] = item
        return value


class FakeJobEvaluationPlanAdapter:
    """Deterministic test adapter; it never performs network access."""

    def __init__(
        self,
        outcomes: Iterable[JobEvaluationPlanAdapterResult | Exception],
    ) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []
        self.v4_calls: list[dict[str, Any]] = []

    async def extract(
        self,
        input_snapshot: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        self.calls.append(input_snapshot)
        if not self._outcomes:
            raise AssertionError("Fake Adapter 没有可返回的预设结果")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def generate_v4(
        self,
        role: str,
        generation_input: dict[str, Any],
    ) -> JobEvaluationPlanAdapterResult:
        self.v4_calls.append({"role": role, "input": generation_input})
        if not self._outcomes:
            raise AssertionError("Fake Adapter 没有可返回的预设结果")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
