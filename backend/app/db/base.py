"""
Database Base Configuration

Sets up the async SQLAlchemy engine and session management for PostgreSQL.

Usage:
    from app.db.base import async_session_maker, Base

    # In a route
    async with async_session_maker() as session:
        result = await session.execute(...)
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings, yaml_config


# Get pool configuration from yaml config
db_config: dict[str, Any] = yaml_config.get("database", {})
pool_size: int = db_config.get("pool_size", 5)
max_overflow: int = db_config.get("max_overflow", 10)
pool_timeout: int = db_config.get("pool_timeout", 30)

# Create async engine
engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    echo=settings.DEBUG,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
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
