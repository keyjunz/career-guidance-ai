from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG

DEFAULT_FIRECRAWL_SEARCH_ENDPOINT = "https://api.firecrawl.dev/v1/search"


class WebSearchSettings(BaseSettings):
    """Web search provider settings (Firecrawl)."""

    model_config = COMMON_SETTINGS_CONFIG

    api_key: str = Field(
        ...,
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "WEB_SEARCH_API_KEY"),
    )
    endpoint: str = Field(
        default=DEFAULT_FIRECRAWL_SEARCH_ENDPOINT,
        alias="FIRECRAWL_SEARCH_ENDPOINT",
    )
    timeout_s: int = Field(default=20, alias="FIRECRAWL_TIMEOUT_S", ge=5, le=120)
