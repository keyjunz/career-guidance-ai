from pathlib import Path

from pydantic_settings import SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

COMMON_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=str(ENV_FILE_PATH),
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)
