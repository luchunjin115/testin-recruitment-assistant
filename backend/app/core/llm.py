from openai import AsyncOpenAI

from app.core.config import Settings, get_settings


def get_llm_client() -> AsyncOpenAI:
    settings = get_settings()
    if settings.llm_provider == "deepseek":
        return AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


def get_llm_model() -> str:
    return get_settings().llm_model


def get_resume_structure_llm_client(settings: Settings | None = None) -> AsyncOpenAI:
    """Build the stage 5 client with retries disabled and a bounded timeout."""
    resolved_settings = settings or get_settings()
    return AsyncOpenAI(
        api_key=resolved_settings.DEEPSEEK_API_KEY or "missing-api-key",
        base_url=resolved_settings.DEEPSEEK_BASE_URL,
        timeout=resolved_settings.RESUME_STRUCTURE_TIMEOUT_SECONDS,
        max_retries=0,
    )


def get_job_evaluation_plan_llm_client(
    settings: Settings | None = None,
) -> AsyncOpenAI:
    """Build the JD decomposition client with SDK retries disabled."""
    resolved_settings = settings or get_settings()
    return AsyncOpenAI(
        api_key=resolved_settings.DEEPSEEK_API_KEY or "missing-api-key",
        base_url=resolved_settings.DEEPSEEK_BASE_URL,
        timeout=resolved_settings.JOB_EVALUATION_PLAN_TIMEOUT_SECONDS,
        max_retries=0,
    )


def get_screening_evaluation_llm_client(
    settings: Settings | None = None,
) -> AsyncOpenAI:
    """Build the one-call screening client with SDK retries disabled."""
    resolved_settings = settings or get_settings()
    return AsyncOpenAI(
        api_key=resolved_settings.DEEPSEEK_API_KEY or "missing-api-key",
        base_url=resolved_settings.DEEPSEEK_BASE_URL,
        timeout=resolved_settings.SCREENING_EVALUATION_TIMEOUT_SECONDS,
        max_retries=0,
    )
