from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = COMMON_SETTINGS_CONFIG

    redis_url: str = Field(..., alias="REDIS_URL")
