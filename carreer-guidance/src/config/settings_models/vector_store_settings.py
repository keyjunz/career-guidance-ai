from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class VectorStoreSettings(BaseSettings):
    """Chroma vector store settings."""

    model_config = COMMON_SETTINGS_CONFIG

    chroma_host: str = Field(..., alias="CHROMA_HOST")
    chroma_port: int = Field(..., alias="CHROMA_PORT")
    chroma_client_mode: str = Field(default="http", alias="CHROMA_CLIENT_MODE")
    chroma_persist_dir: str = Field(default="./chroma_data", alias="CHROMA_PERSIST_DIR")
