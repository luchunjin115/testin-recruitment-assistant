from openai import AsyncOpenAI

from app.core.config import Settings, get_settings


def get_llm_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.llm_api_key or "missing-api-key",
        base_url=settings.llm_base_url,
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
