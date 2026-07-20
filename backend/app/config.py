from functools import lru_cache
from pathlib import Path
import re
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import field_validator


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


def _sqlite_url(path: Path) -> str:
    return "sqlite:///" + path.resolve().as_posix()


def _resolve_sqlite_url(value: str) -> str:
    if not value.startswith("sqlite:///"):
        return value

    path_text = value.replace("sqlite:///", "", 1)
    if path_text == ":memory:" or path_text.startswith("file:"):
        return value

    is_absolute = path_text.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", path_text)
    if is_absolute:
        return "sqlite:///" + Path(path_text).as_posix()

    return _sqlite_url(BACKEND_DIR / path_text)


def _resolve_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((BACKEND_DIR / path).resolve())


class Settings(BaseSettings):
    LLM_PROVIDER: str = "mock"
    LLM_ENABLE_MOCK_FALLBACK: bool = True

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    DATABASE_URL: str = _sqlite_url(BACKEND_DIR / "recruit.db")

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    PORT: Optional[int] = None
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    FRONTEND_ORIGIN: str = ""
    VITE_API_BASE_URL: str = ""

    UPLOAD_DIR: str = str((BACKEND_DIR / "uploads").resolve())
    MAX_FILE_SIZE_MB: int = 10

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _resolve_sqlite_url(value)

    @field_validator("UPLOAD_DIR")
    @classmethod
    def normalize_upload_dir(cls, value: str) -> str:
        return _resolve_path(value)

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
        for value in [self.CORS_ORIGINS, self.FRONTEND_ORIGIN]:
            origins.extend(o.strip() for o in value.split(",") if o.strip())
        return list(dict.fromkeys(origins))

    @property
    def backend_port(self) -> int:
        return self.PORT or self.BACKEND_PORT

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

    model_config = {"env_file": str(PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
