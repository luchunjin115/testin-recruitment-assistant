from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


def _resolve_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((BACKEND_DIR / path).resolve())


class Settings(BaseSettings):
    APP_NAME: str = "HR Agent Recruitment Platform"
    APP_ENV: str = "development"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    PORT: Optional[int] = None
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    FRONTEND_ORIGIN: str = ""

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/"
        "recruitment_assistant"
    )
    POSTGRES_DB: str = "recruitment_assistant"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://localhost:6379/0"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_RESUMES: str = "resumes"

    LLM_PROVIDER: str = "mock"
    LLM_ENABLE_MOCK_FALLBACK: bool = True
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    RESUME_STRUCTURE_ENABLED: bool = True
    RESUME_STRUCTURE_MODEL: str = "deepseek-v4-flash"
    RESUME_STRUCTURE_TIMEOUT_SECONDS: float = Field(default=90, gt=0, le=600)
    RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS: int = Field(default=180, ge=30, le=3600)
    RESUME_STRUCTURE_MAX_INPUT_CHARS: int = Field(default=100_000, ge=1_000, le=1_000_000)
    RESUME_STRUCTURE_MAX_OUTPUT_TOKENS: int = Field(default=12_000, ge=1_000, le=384_000)
    RESUME_STRUCTURE_PROMPT_VERSION: str = Field(
        default="resume_structure_v1",
        min_length=1,
        max_length=100,
    )
    RESUME_STRUCTURE_SCHEMA_VERSION: str = Field(
        default="1.0",
        min_length=1,
        max_length=20,
    )
    JOB_EVALUATION_PLAN_ENABLED: bool = True
    JOB_EVALUATION_PLAN_MODEL: str = Field(
        default="deepseek-v4-flash",
        min_length=1,
        max_length=100,
    )
    JOB_EVALUATION_PLAN_TIMEOUT_SECONDS: float = Field(default=90, gt=0, le=600)
    JOB_EVALUATION_PLAN_MAX_INPUT_CHARS: int = Field(
        default=100_000,
        ge=1_000,
        le=1_000_000,
    )
    JOB_EVALUATION_PLAN_MAX_OUTPUT_TOKENS: int = Field(
        default=8_000,
        ge=1_000,
        le=384_000,
    )
    JOB_EVALUATION_PLAN_PROMPT_VERSION: str = Field(
        default="job_evaluation_plan_v5",
        min_length=1,
        max_length=100,
    )
    JOB_EVALUATION_PLAN_AI_SCHEMA_VERSION: str = Field(
        default="3.0",
        min_length=1,
        max_length=20,
    )
    JOB_EVALUATION_PLAN_SCHEMA_VERSION: str = Field(
        default="3.0",
        min_length=1,
        max_length=20,
    )
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION: str = Field(
        default="job_evaluation_plan_lightweight_v2",
        min_length=1,
        max_length=100,
    )
    JOB_EVALUATION_PLAN_V5_AI_SCHEMA_VERSION: str = Field(
        default="5.0",
        min_length=1,
        max_length=20,
    )
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION: str = Field(
        default="5.0",
        min_length=1,
        max_length=20,
    )
    SCREENING_EVALUATION_ENABLED: bool = True
    SCREENING_EVALUATION_MODEL: str = Field(
        default="deepseek-v4-flash",
        min_length=1,
        max_length=100,
    )
    SCREENING_EVALUATION_TIMEOUT_SECONDS: float = Field(default=90, gt=0, le=600)
    SCREENING_EVALUATION_MAX_INPUT_CHARS: int = Field(
        default=150_000,
        ge=1_000,
        le=1_000_000,
    )
    SCREENING_EVALUATION_MAX_OUTPUT_TOKENS: int = Field(
        default=12_000,
        ge=1_000,
        le=384_000,
    )
    SCREENING_EVALUATION_PROMPT_VERSION: str = Field(
        default="screening_evaluation_v4",
        min_length=1,
        max_length=100,
    )
    SCREENING_EVALUATION_SCHEMA_VERSION: str = Field(
        default="2.0",
        min_length=1,
        max_length=20,
    )
    SCREENING_EVALUATION_V5_PROMPT_VERSION: str = Field(
        default="screening_evaluation_lightweight_v1",
        min_length=1,
        max_length=100,
    )
    SCREENING_EVALUATION_V5_SCHEMA_VERSION: str = Field(
        default="5.0",
        min_length=1,
        max_length=20,
    )
    SCREENING_EVALUATION_TIMEZONE: str = Field(
        default="Asia/Shanghai",
        min_length=1,
        max_length=100,
    )
    EXPERIENCE_PERIOD_FACTS_RULE_VERSION: str = Field(
        default="experience_period_facts_v1",
        min_length=1,
        max_length=100,
    )
    SCREENING_REDACTION_VERSION: str = Field(
        default="screening_redaction_v1",
        min_length=1,
        max_length=100,
    )
    SCREENING_WORKER_ENABLED: bool = True
    SCREENING_WORKER_POLL_SECONDS: float = Field(default=1.0, ge=0.1, le=60)
    SCREENING_WORKER_LEASE_SECONDS: int = Field(default=300, ge=30, le=3_600)
    SCREENING_WORKER_BATCH_SIZE: int = Field(default=5, ge=1, le=20)
    STORAGE_DIR: str = str((BACKEND_DIR / "storage").resolve())
    MAX_FILE_SIZE_MB: int = 10
    RESUME_CLEANUP_ENABLED: bool = True
    RESUME_UNBOUND_RETENTION_HOURS: int = Field(default=24, ge=1, le=24 * 365)
    RESUME_CLEANUP_INTERVAL_MINUTES: int = Field(default=60, ge=1, le=24 * 60)
    RESUME_CLEANUP_BATCH_SIZE: int = Field(default=50, ge=1, le=1000)

    @field_validator("STORAGE_DIR")
    @classmethod
    def normalize_storage_dir(cls, value: str) -> str:
        return _resolve_path(value)

    @model_validator(mode="after")
    def validate_screening_worker_lease(self) -> "Settings":
        minimum_lease = int(self.SCREENING_EVALUATION_TIMEOUT_SECONDS * 2) + 30
        if self.SCREENING_WORKER_LEASE_SECONDS < minimum_lease:
            raise ValueError(
                "SCREENING_WORKER_LEASE_SECONDS 必须覆盖两次模型超时和收尾时间"
            )
        return self

    @property
    def backend_port(self) -> int:
        return self.PORT or self.BACKEND_PORT

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
        for value in [self.CORS_ORIGINS, self.FRONTEND_ORIGIN]:
            origins.extend(origin.strip() for origin in value.split(",") if origin.strip())
        return list(dict.fromkeys(origins))

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL
        if self.DATABASE_URL.startswith("sqlite"):
            user = quote_plus(self.POSTGRES_USER)
            password = quote_plus(self.POSTGRES_PASSWORD)
            return (
                f"postgresql+asyncpg://{user}:{password}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self.DATABASE_URL

    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER.strip().lower()

    @property
    def llm_api_key(self) -> str:
        if self.llm_provider == "deepseek":
            return self.DEEPSEEK_API_KEY or self.OPENAI_API_KEY
        return self.OPENAI_API_KEY

    @property
    def llm_base_url(self) -> str:
        if self.llm_provider == "deepseek":
            return self.DEEPSEEK_BASE_URL
        return self.OPENAI_BASE_URL

    @property
    def llm_model(self) -> str:
        if self.llm_provider == "deepseek":
            return self.DEEPSEEK_MODEL
        return self.OPENAI_MODEL

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
