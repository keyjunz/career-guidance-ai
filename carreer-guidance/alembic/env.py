import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context
from src.database import Base
from src.database.models import (
    Conversation,
    Document,
    Message,
    RequestCostLog,
    Role,
    User,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _read_database_url_from_env_file() -> str | None:
    root_dir = Path(__file__).resolve().parents[1]
    env_path = root_dir / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "DATABASE_URL":
            return value.strip().strip('"').strip("'")
    return None


def _resolve_database_url() -> str:
    try:
        from src.config import get_settings

        settings = get_settings()
        if settings.db.url:
            return settings.db.url
    except Exception:
        # Fallback to environment and .env file in migration contexts.
        pass

    env_file_url = _read_database_url_from_env_file()
    if env_file_url:
        return env_file_url

    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url

    raise RuntimeError(
        "DATABASE_URL is missing. Set DATABASE_URL in environment or .env file."
    )


config.set_main_option("sqlalchemy.url", _resolve_database_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode using sync SQLAlchemy engine."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
