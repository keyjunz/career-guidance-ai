from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class LLMSettings(BaseSettings):
    """Gemini model settings."""

    model_config = COMMON_SETTINGS_CONFIG

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(..., alias="GEMINI_MODEL_NAME")
