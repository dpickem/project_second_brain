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

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Obsidian
    OBSIDIAN_VAULT_PATH: str = "/vault"

    # File uploads - temporary staging area for raw uploads, NOT the vault's assets/.
    # Uploads may fail processing or be rejected; only successful content goes to vault.
    # Flow: Upload → UPLOAD_DIR → Pipeline → Vault assets/ (if successful)
    UPLOAD_DIR: str = "/tmp/second_brain_uploads"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Mistral (for OCR)
    MISTRAL_API_KEY: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # External API Tokens
    RAINDROP_ACCESS_TOKEN: str = ""
    GITHUB_ACCESS_TOKEN: str = ""

    # OCR Configuration (model-agnostic via LiteLLM)
    # Format: provider/model-name
    # Examples: mistral/mistral-ocr-2512, openai/gpt-5.1-chat-latest, anthropic/claude-4-5-sonnet-202509
    OCR_MODEL: str = "mistral/mistral-ocr-2512"
    OCR_MAX_TOKENS: int = 4000
    OCR_USE_JSON_MODE: bool = True

    # Text model for metadata inference, note expansion
    TEXT_MODEL: str = "openai/gpt-5-mini"

    # LiteLLM spend management
    LITELLM_BUDGET_MAX: float = 100.0  # Monthly budget in USD
    LITELLM_BUDGET_ALERT: float = 80.0  # Alert at 80% usage

    # Pipeline settings
    PDF_HANDWRITING_DETECTION: bool = True
    PDF_IMAGE_DPI: int = 300
    PDF_MAX_FILE_SIZE_MB: int = 50

    VOICE_EXPAND_NOTES: bool = True

    # Langfuse observability (optional)
    LANGFUSE_ENABLED: bool = False

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
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


yaml_config: dict[str, Any] = load_yaml_config()
