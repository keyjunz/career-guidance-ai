"""SQLAlchemy async engine and session factory helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .settings import Settings, get_settings


def create_async_engine_from_settings(settings: Settings | None = None) -> AsyncEngine:
    """Create SQLAlchemy async engine from application settings."""

    cfg = settings or get_settings()
    return create_async_engine(
        cfg.db.url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


def create_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a configured async session maker."""

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return cached async engine based on current settings."""

    return create_async_engine_from_settings()


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return cached async session factory."""

    return create_async_session_factory(get_engine())


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncIterator[AsyncSession]:
    """FastAPI-compatible async session dependency with proper cleanup."""

    factory = session_factory or get_session_factory()
    async with factory() as session:
        yield session


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncIterator[AsyncSession]:
    """Provide a transactional async session scope with commit and rollback."""

    factory = session_factory or get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
