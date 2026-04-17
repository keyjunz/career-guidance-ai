from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.app_settings import AppSettings
from src.config.settings_models.common import COMMON_SETTINGS_CONFIG
from src.config.settings_models.database_settings import DatabaseSettings
from src.config.settings_models.llm_settings import LLMSettings
from src.config.settings_models.redis_settings import RedisSettings
from src.config.settings_models.vector_store_settings import VectorStoreSettings
from src.config.settings_models.web_search_settings import WebSearchSettings


class Settings(BaseSettings):
    """Centralized settings container for all configuration sections."""

    model_config = COMMON_SETTINGS_CONFIG

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)
