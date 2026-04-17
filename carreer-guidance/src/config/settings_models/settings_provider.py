from functools import lru_cache

from src.config.settings_models.settings_container import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""

    return Settings()


def validate_startup_config(settings: Settings | None = None) -> None:
    """Fail fast if required configuration is invalid or missing."""

    cfg = settings or get_settings()

    required_values = {
        "APP_NAME": cfg.app.name,
        "APP_ENV": cfg.app.env,
        "APP_PORT": cfg.app.port,
        "LOG_LEVEL": cfg.app.log_level,
        "DATABASE_URL": cfg.db.url,
        "GEMINI_API_KEY": cfg.llm.gemini_api_key,
        "GEMINI_MODEL_NAME": cfg.llm.gemini_model_name,
        "CHROMA_HOST": cfg.vector_store.chroma_host,
        "CHROMA_PORT": cfg.vector_store.chroma_port,
        "REDIS_URL": cfg.redis.redis_url,
        "WEB_SEARCH_API_KEY": cfg.web_search.api_key,
    }

    missing = [
        key for key, value in required_values.items() if str(value).strip() == ""
    ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    if cfg.app.port <= 0:
        raise ValueError("APP_PORT must be a positive integer")
    if cfg.vector_store.chroma_port <= 0:
        raise ValueError("CHROMA_PORT must be a positive integer")
