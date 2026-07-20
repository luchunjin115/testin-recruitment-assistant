from openai import AsyncOpenAI

from app.core.config import get_settings


def get_llm_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.llm_api_key or "missing-api-key",
        base_url=settings.llm_base_url,
    )


def get_llm_model() -> str:
    return get_settings().llm_model
