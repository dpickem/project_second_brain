"""
Application Configuration

This module provides type-safe configuration loading using Pydantic settings.
Environment variables are loaded from .env file and validated.

CONFIGURATION HIERARCHY:
    1. Environment variables (highest priority)
    2. .env file in project root
    3. Defaults defined in this file (lowest priority)

WHAT GOES WHERE:
    - .env / Environment variables: Secrets (API keys, passwords), deployment-specific
    - This file (settings.py): Environment variable definitions with types and defaults
    - config/default.yaml: Application behavior (folder structure, templates, pool sizes)

Usage:
    from app.config import settings

    # Access settings
    db_url = settings.POSTGRES_URL
    redis_url = settings.REDIS_URL
    data_dir = settings.DATA_DIR
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic_settings import BaseSettings

# Project root is the parent of backend/
# backend/app/config/settings.py -> backend/app/config -> backend/app -> backend -> project_root
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = _BACKEND_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = CONFIG_DIR / "templates"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    See .env.example for documentation of each setting.
    """

    # =========================================================================
    # APPLICATION
    # =========================================================================
    APP_NAME: str = "Second Brain"
    DEBUG: bool = False

    # =========================================================================
    # DATA DIRECTORY
    # =========================================================================
    # Root directory for all persistent data (postgres, redis, neo4j, obsidian)
    # Used by docker-compose.yml and setup scripts
    DATA_DIR: str = "~/workspace/obsidian/second_brain"

    @property
    def DATA_DIR_PATH(self) -> Path:
        """Expanded DATA_DIR as Path object."""
        return Path(self.DATA_DIR).expanduser().resolve()

    # =========================================================================
    # POSTGRESQL
    # =========================================================================
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

    # =========================================================================
    # REDIS
    # =========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"

    # =========================================================================
    # CELERY
    # =========================================================================
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # =========================================================================
    # NEO4J
    # =========================================================================
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"  # Default database name

    # =========================================================================
    # OBSIDIAN VAULT
    # =========================================================================
    # Path to Obsidian vault. In Docker, use /vault (mounted volume).
    OBSIDIAN_VAULT_PATH: str = "/vault"

    @property
    def OBSIDIAN_VAULT_PATH_OBJ(self) -> Path:
        """OBSIDIAN_VAULT_PATH as Path object."""
        return Path(self.OBSIDIAN_VAULT_PATH).expanduser().resolve()

    # =========================================================================
    # VAULT SYNC & WATCHER (Phase 4)
    # =========================================================================
    # These settings control bi-directional sync between Obsidian vault and Neo4j.
    #
    # VAULT_WATCH_ENABLED: Whether to monitor the vault for file changes.
    #   - True: Start watchdog file watcher on app startup
    #   - False: No file monitoring (changes won't be detected in real-time)
    #   Use case: Disable if running in read-only mode or during bulk imports.
    #
    # VAULT_SYNC_NEO4J_ENABLED: Whether to sync detected changes to Neo4j.
    #   - True: Update Neo4j knowledge graph when files change
    #   - False: Detect changes but don't update Neo4j (useful for debugging,
    #            or if Neo4j is not configured/available)
    #   Use case: Disable if Neo4j is down for maintenance but you still want
    #             the watcher to log changes for later reconciliation.
    #
    # Common configurations:
    #   Both True (default): Full real-time sync - recommended for normal use
    #   Watch=True, Sync=False: Monitor + log only, no Neo4j updates
    #   Both False: No file monitoring at all
    #
    VAULT_WATCH_ENABLED: bool = True
    # Debounce time in milliseconds for rapid file changes (e.g., auto-save).
    # Prevents excessive syncs when Obsidian saves frequently.
    VAULT_SYNC_DEBOUNCE_MS: int = 1000
    VAULT_SYNC_NEO4J_ENABLED: bool = True

    # =========================================================================
    # FILE UPLOADS
    # =========================================================================
    # Temporary staging area for raw uploads, NOT the vault's assets/.
    # Uploads may fail processing or be rejected; only successful content goes to vault.
    # Flow: Upload → UPLOAD_DIR → Pipeline → Vault assets/ (if successful)
    UPLOAD_DIR: str = "/tmp/second_brain_uploads"

    # =========================================================================
    # LLM API KEYS
    # =========================================================================
    # At least one is required for LLM features
    OPENAI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""  # Google AI Studio / Vertex AI

    # =========================================================================
    # EXTERNAL API TOKENS
    # =========================================================================
    RAINDROP_ACCESS_TOKEN: str = ""
    GITHUB_ACCESS_TOKEN: str = ""

    # =========================================================================
    # LLM MODEL CONFIGURATION
    # =========================================================================
    # Model identifiers use LiteLLM format: provider/model-name
    # See: https://docs.litellm.ai/docs/providers

    # Vision/OCR Model for image processing (book photos, image analysis)
    # Two modes are supported:
    #
    # 1. Vision Chat Models (structured extraction: page numbers, chapters, highlights):
    #    - gemini/gemini-3-flash-preview (fast, recommended default)
    #    - openai/gpt-4o (high quality)
    #    - anthropic/claude-sonnet-4-20250514
    #
    # 2. Mistral OCR (fast, cost-effective pure text extraction):
    #    - mistral/mistral-ocr-latest ($1/1000 pages, excellent accuracy)
    #    Note: Mistral OCR extracts text only, no structured metadata
    #
    VLM_MODEL: str = "gemini/gemini-3-flash-preview"
    OCR_MODEL: str = "gemini/gemini-3-flash-preview"  # Alias for VLM_MODEL
    OCR_MAX_TOKENS: int = 4000
    OCR_USE_JSON_MODE: bool = True

    # Text model for metadata inference, note expansion, analysis
    # See: https://docs.litellm.ai/blog/gemini_3_flash
    TEXT_MODEL: str = "gemini/gemini-3-flash-preview"

    # =========================================================================
    # LLM BUDGET & COST MANAGEMENT
    # =========================================================================
    LITELLM_BUDGET_MAX: float = 100.0  # Monthly budget in USD
    LITELLM_BUDGET_ALERT: float = 80.0  # Alert threshold (percentage of max)

    # =========================================================================
    # PIPELINE SETTINGS
    # =========================================================================
    # PDF processing
    PDF_HANDWRITING_DETECTION: bool = True
    PDF_IMAGE_DPI: int = 300
    PDF_MAX_FILE_SIZE_MB: int = 50

    # Voice transcription
    VOICE_EXPAND_NOTES: bool = True

    # =========================================================================
    # OBSERVABILITY
    # =========================================================================
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields to be ignored (forward compatibility)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


@lru_cache()
def load_yaml_config() -> dict[str, Any]:
    """Load application configuration from config/default.yaml."""
    config_path = CONFIG_DIR / "default.yaml"

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


yaml_config: dict[str, Any] = load_yaml_config()
