from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class AppSettings(BaseSettings):
    """Application runtime settings."""

    model_config = COMMON_SETTINGS_CONFIG

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
