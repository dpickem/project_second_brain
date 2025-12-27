"""
Application Configuration

This module provides type-safe configuration loading using Pydantic settings.
Environment variables are loaded from .env file and validated.

Usage:
    from app.config import settings

    # Access settings
    db_url = settings.POSTGRES_URL
    redis_url = settings.REDIS_URL
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Second Brain"
    DEBUG: bool = False

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "secondbrain"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "secondbrain"

    @property
    def POSTGRES_URL(self) -> str:
        """Async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def POSTGRES_URL_SYNC(self) -> str:
        """Sync PostgreSQL connection URL for Alembic migrations."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Obsidian
    OBSIDIAN_VAULT_PATH: str = "/vault"

    # OpenAI
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


@lru_cache()
def load_yaml_config() -> dict[str, Any]:
    """Load application configuration from config/default.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


yaml_config: dict[str, Any] = load_yaml_config()
