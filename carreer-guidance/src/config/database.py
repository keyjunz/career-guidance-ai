from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .settings_models import Settings, get_settings


def create_engine_from_settings(settings: Settings | None = None) -> Engine:
    cfg = settings or get_settings()
    return create_engine(
        cfg.db.url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return cached sync engine based on current settings."""

    return create_engine_from_settings()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return cached sync session factory."""

    return create_session_factory(get_engine())


def get_session(
    session_factory: sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """FastAPI-compatible sync session dependency with proper cleanup."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        yield session


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """Provide a transactional sync session scope with commit and rollback."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# Backward-compatible aliases for older imports.
create_async_engine_from_settings = create_engine_from_settings
create_async_session_factory = create_session_factory
