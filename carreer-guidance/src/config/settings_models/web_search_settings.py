from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class WebSearchSettings(BaseSettings):
    """Web search provider settings."""

    model_config = COMMON_SETTINGS_CONFIG

    api_key: str = Field(..., alias="WEB_SEARCH_API_KEY")
