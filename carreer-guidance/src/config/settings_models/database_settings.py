from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = COMMON_SETTINGS_CONFIG

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
