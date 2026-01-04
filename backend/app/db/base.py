"""
Database Base Configuration

Sets up the async SQLAlchemy engine and session management for PostgreSQL.

Two session makers are provided:
1. async_session_maker - Uses connection pooling, for FastAPI routes (single event loop)
2. task_session_maker - Uses NullPool, for Celery tasks (new event loop per task)

The distinction is necessary because:
- FastAPI runs in a single persistent event loop, so connection pooling is safe and efficient
- Celery tasks use asyncio.run() which creates a NEW event loop for each task/retry
- Pooled connections are tied to their creation event loop and fail when used in a different loop

Usage:
    from app.db.base import async_session_maker, task_session_maker, Base

    # In a FastAPI route (single event loop)
    async with async_session_maker() as session:
        result = await session.execute(...)

    # In a Celery task (new event loop per asyncio.run())
    async with task_session_maker() as session:
        result = await session.execute(...)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings, yaml_config


# Get pool configuration from yaml config
db_config: dict[str, Any] = yaml_config.get("database", {})
pool_size: int = db_config.get("pool_size", 5)
max_overflow: int = db_config.get("max_overflow", 10)
pool_timeout: int = db_config.get("pool_timeout", 30)

# =============================================================================
# Engine for FastAPI (pooled connections, single event loop)
# =============================================================================
# This engine uses connection pooling for efficiency. It's safe to use in FastAPI
# because the entire application runs in a single persistent event loop.
engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    echo=settings.DEBUG,
)

# Session factory for FastAPI routes
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# =============================================================================
# Engine for Celery tasks (no pooling, safe for multiple event loops)
# =============================================================================
# This engine uses NullPool which creates fresh connections each time.
# This is necessary for Celery tasks because:
# 1. asyncio.run() creates a NEW event loop for each task execution
# 2. Pooled connections are tied to the event loop where they were created
# 3. Using a pooled connection in a different event loop causes:
#    - "Future attached to a different loop" errors
#    - "cannot perform operation: another operation is in progress" errors
#
# NullPool means no connection reuse, which has some performance overhead,
# but is the only safe option when event loops are created/destroyed frequently.
task_engine = create_async_engine(
    settings.POSTGRES_URL,
    poolclass=NullPool,  # No pooling - each connection is fresh
    echo=settings.DEBUG,
)

# Session factory for Celery tasks
task_session_maker = async_sessionmaker(
    task_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Import models AFTER Base is defined to avoid circular imports.
# This ensures all models are registered with Base.metadata.
from app.db import models  # noqa: F401, E402


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions in FastAPI routes.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Called on application startup to create tables that don't exist.
    For production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
