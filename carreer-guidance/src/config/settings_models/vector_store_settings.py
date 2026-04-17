from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class VectorStoreSettings(BaseSettings):
    """Chroma vector store settings."""

    model_config = COMMON_SETTINGS_CONFIG

    chroma_host: str = Field(..., alias="CHROMA_HOST")
    chroma_port: int = Field(..., alias="CHROMA_PORT")
