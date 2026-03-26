from functools import lru_cache
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application runtime settings."""

    model_config = SettingsConfigDict(extra="forbid")

    name: str = Field(..., alias="APP_NAME")
    env: Literal["dev", "staging", "prod"] = Field(..., alias="APP_ENV")
    port: int = Field(..., alias="APP_PORT")
    log_level: str = Field(..., alias="LOG_LEVEL")

    @field_validator("env", mode="before")
    @classmethod
    def normalize_env(cls, value: Any) -> str:
        normalized = str(value).strip().lower()
        aliases = {
            "development": "dev",
            "production": "prod",
        }
        return aliases.get(normalized, normalized)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        if value is None:
            return "INFO"
        return str(value).strip().upper()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if value not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return value


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(extra="forbid")

    url: str = Field(
        ...,
        alias="DATABASE_URL",
    )

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        parsed = urlparse(value)
        allowed_schemes = {"postgresql", "postgresql+psycopg2", "postgresql+psycopg"}
        if parsed.scheme not in allowed_schemes:
            raise ValueError(
                "DATABASE_URL must use one of schemes: "
                "postgresql, postgresql+psycopg2, postgresql+psycopg"
            )
        if not parsed.hostname:
            raise ValueError("DATABASE_URL must include a host")
        return value


class LLMSettings(BaseSettings):
    """Gemini model settings."""

    model_config = SettingsConfigDict(extra="forbid")

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(..., alias="GEMINI_MODEL_NAME")
    gemini_embedding_model: str = Field(..., alias="GEMINI_EMBEDDING_MODEL")


class VectorStoreSettings(BaseSettings):
    """Chroma vector store settings."""

    model_config = SettingsConfigDict(extra="forbid")

    chroma_host: str = Field(..., alias="CHROMA_HOST")
    chroma_port: int = Field(..., alias="CHROMA_PORT")


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = SettingsConfigDict(extra="forbid")

    redis_url: str = Field(..., alias="REDIS_URL")


class WebSearchSettings(BaseSettings):
    """Web search provider settings."""

    model_config = SettingsConfigDict(extra="forbid")

    api_key: str = Field(..., alias="WEB_SEARCH_API_KEY")


class Settings(BaseSettings):
    """Centralized settings container for all configuration sections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""

    return Settings()


def validate_startup_config(settings: Settings | None = None) -> None:
    """Fail fast if required configuration is invalid or missing."""

    cfg = settings or get_settings()

    required_values = {
        "APP_NAME": cfg.app.name,
        "APP_ENV": cfg.app.env,
        "APP_PORT": cfg.app.port,
        "LOG_LEVEL": cfg.app.log_level,
        "DATABASE_URL": cfg.db.url,
        "GEMINI_API_KEY": cfg.llm.gemini_api_key,
        "GEMINI_MODEL_NAME": cfg.llm.gemini_model_name,
        "GEMINI_EMBEDDING_MODEL": cfg.llm.gemini_embedding_model,
        "CHROMA_HOST": cfg.vector_store.chroma_host,
        "CHROMA_PORT": cfg.vector_store.chroma_port,
        "REDIS_URL": cfg.redis.redis_url,
        "WEB_SEARCH_API_KEY": cfg.web_search.api_key,
    }

    missing = [
        key for key, value in required_values.items() if str(value).strip() == ""
    ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    if cfg.app.port <= 0:
        raise ValueError("APP_PORT must be a positive integer")
    if cfg.vector_store.chroma_port <= 0:
        raise ValueError("CHROMA_PORT must be a positive integer")
