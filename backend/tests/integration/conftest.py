"""
Integration Test Fixtures

Provides fixtures for integration tests that require running services.
These fixtures set up real database connections and clean up after tests.

IMPORTANT: All integration tests use the TEST database only (via POSTGRES_TEST_* env vars).
The test_client fixture overrides get_db to ensure the production database is never touched.
A safety check fixture (verify_test_database) runs at session start to fail fast if
production credentials are detected.

Note: app.main imports are kept inside fixtures because they require
environment variables that are set up by the session-scoped fixtures
in the parent conftest.py.
"""

import os
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import quote_plus

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env file FIRST, before reading any environment variables
# This ensures POSTGRES_TEST_* variables are available
_project_root = Path(__file__).parent.parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)


# =============================================================================
# Safety Check - Runs before any integration tests
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def verify_test_database():
    """
    Safety check: Verify we're using test database credentials.

    This runs once at the start of the integration test session and fails fast
    if production credentials are detected. Applies to ALL integration tests.

    Set ALLOW_PROD_DB_TESTS=1 to skip this check (for local development only).
    """
    # Allow skipping the check for local development
    if os.environ.get("ALLOW_PROD_DB_TESTS", "").lower() in ("1", "true", "yes"):
        return

    db_name = os.environ.get("POSTGRES_DB", "")
    db_user = os.environ.get("POSTGRES_USER", "")

    # Fail if using production database name or user
    production_indicators = ["secondbrain", "prod", "production"]
    for indicator in production_indicators:
        assert indicator not in db_name.lower(), (
            f"SAFETY CHECK FAILED: Database name '{db_name}' looks like production! "
            "Set POSTGRES_TEST_DB environment variable or ALLOW_PROD_DB_TESTS=1."
        )
        assert indicator not in db_user.lower(), (
            f"SAFETY CHECK FAILED: Database user '{db_user}' looks like production! "
            "Set POSTGRES_TEST_USER environment variable or ALLOW_PROD_DB_TESTS=1."
        )


# =============================================================================
# Database Configuration
# =============================================================================


def get_test_db_config() -> dict:
    """
    Get test database configuration from environment variables.

    Priority: POSTGRES_TEST_* > POSTGRES_* > defaults
    This allows using the same DB as the app (docker-compose) or a dedicated test DB.
    """
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "user": os.environ.get(
            "POSTGRES_TEST_USER",
            os.environ.get("POSTGRES_USER", "testuser")
        ),
        "password": os.environ.get(
            "POSTGRES_TEST_PASSWORD",
            os.environ.get("POSTGRES_PASSWORD", "testpass")
        ),
        "db": os.environ.get(
            "POSTGRES_TEST_DB",
            os.environ.get("POSTGRES_DB", "testdb")
        ),
    }


def get_test_db_url(async_driver: bool = True) -> str:
    """Build database URL from test config environment variables."""
    config = get_test_db_config()
    # URL-encode the password to handle special characters
    encoded_password = quote_plus(config["password"])
    driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
    return f"{driver}://{config['user']}:{encoded_password}@{config['host']}:{config['port']}/{config['db']}"


# Skip marker removed - tests will fail with clear DB connection errors if unavailable
pytestmark = pytest.mark.integration

# Track if tables have been created
_tables_created = False


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Create database tables before any tests run.

    Uses synchronous SQLAlchemy to avoid event loop issues.
    Tables are dropped and recreated at the start of the test session
    to ensure schema is up-to-date with models.
    """
    global _tables_created
    if _tables_created:
        return

    from app.db.base import Base

    # Import models to ensure they're registered with Base.metadata
    from app.db import models  # noqa: F401
    from app.db import models_learning  # noqa: F401

    # Use synchronous engine to create tables (avoids event loop issues)
    sync_engine = create_engine(get_test_db_url(async_driver=False))

    # Drop all tables first to ensure schema matches models
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    _tables_created = True

    yield

    # Optionally drop tables after all tests (uncomment if desired)
    # Base.metadata.drop_all(sync_engine)

    sync_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for testing.

    Creates a fresh engine per test to avoid event loop issues.

    Each test gets a fresh session that is rolled back after the test.
    This ensures test isolation without affecting the database.
    """
    # Create a fresh engine for this test's event loop
    test_engine = create_async_engine(get_test_db_url(async_driver=True), echo=False)
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def clean_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a session with cleaned tables for testing.

    Creates its own session and truncates tables before/after each test.
    WARNING: This truncates tables! Only use for integration tests.
    """
    # Tables to clean (in order to respect foreign key constraints)
    tables_to_clean = [
        "exercise_attempts",
        "exercises",
        "practice_attempts",
        "spaced_rep_cards",
        "practice_sessions",
        "mastery_snapshots",
        "annotations",
        "content",
        "tags",
    ]

    # Create fresh engine and session for this test
    test_engine = create_async_engine(get_test_db_url(async_driver=True), echo=False)
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_session_maker() as session:
        # Clean tables before test
        for table in tables_to_clean:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except Exception:
                await session.rollback()

        await session.commit()

        yield session

        # Rollback any pending transaction before cleanup
        await session.rollback()

        # Clean tables after test
        for table in tables_to_clean:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except Exception:
                await session.rollback()

        await session.commit()

    await test_engine.dispose()


@pytest_asyncio.fixture
async def redis_client():
    """
    Create a Redis client for testing.

    Uses a separate database number to avoid affecting production data.
    """
    from app.db.redis import get_redis

    client = await get_redis()

    # Clear test keys before test
    keys = await client.keys("test:*")
    if keys:
        await client.delete(*keys)

    yield client

    # Clean up test keys after test
    keys = await client.keys("test:*")
    if keys:
        await client.delete(*keys)


@pytest.fixture
def test_client(clean_db: AsyncSession):
    """
    Create a FastAPI test client configured to use the test database.

    IMPORTANT: This overrides the app's get_db dependency to ensure
    tests NEVER touch the production database. The clean_db fixture
    provides a session connected to the test database.
    """
    # Import here to defer until after environment is configured
    from app.db.base import get_db
    from app.main import app

    # Override get_db to use test database session
    async def get_test_db():
        """Yield the test database session instead of production."""
        yield clean_db

    app.dependency_overrides[get_db] = get_test_db

    try:
        yield TestClient(app)
    finally:
        # Clean up dependency override after test
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def async_test_client(clean_db: AsyncSession):
    """
    Create an async HTTP client configured to use the test database.

    IMPORTANT: This overrides the app's get_db dependency to ensure
    tests NEVER touch the production database.

    Note: As of httpx 0.28+, ASGITransport must be used instead of passing
    `app` directly to AsyncClient.
    """
    # Import here to defer until after environment is configured
    from app.db.base import get_db
    from app.main import app

    # Override get_db to use test database session
    async def get_test_db():
        """Yield the test database session instead of production."""
        yield clean_db

    app.dependency_overrides[get_db] = get_test_db

    # Use ASGITransport for httpx 0.28+ compatibility
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up dependency override after test
    app.dependency_overrides.pop(get_db, None)
