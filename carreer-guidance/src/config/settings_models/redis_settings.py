from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.settings_models.common import COMMON_SETTINGS_CONFIG


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = COMMON_SETTINGS_CONFIG

    redis_url: str = Field(..., alias="REDIS_URL")
    redis_connect_timeout_sec: float = Field(
        default=8.0,
        alias="REDIS_CONNECT_TIMEOUT_SEC",
    )
    redis_socket_timeout_sec: float = Field(
        default=8.0,
        alias="REDIS_SOCKET_TIMEOUT_SEC",
    )
    redis_health_check_interval_sec: int = Field(
        default=30,
        alias="REDIS_HEALTH_CHECK_INTERVAL_SEC",
    )
    redis_ssl_cert_reqs: str = Field(
        default="required",
        alias="REDIS_SSL_CERT_REQS",
    )
