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

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings

from app.enums import RateLimitType

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
    # API AUTHENTICATION
    # =========================================================================
    # API key for authenticating the capture API (mobile PWA, external clients).
    # If empty, authentication is disabled (development mode).
    CAPTURE_API_KEY: str = ""

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

    # Web article extraction
    ARTICLE_HTTP_TIMEOUT: float = 30.0  # HTTP timeout in seconds
    JINA_RATE_LIMIT_RPM: int = 20  # Jina Reader API rate limit (requests/minute)
    # Free tier: 20 RPM, Paid tiers: 500-5000 RPM
    # See: https://jina.ai/api-dashboard/rate-limit

    # Raindrop sync - LLM title generation
    RAINDROP_TITLE_SAMPLE_LENGTH: int = 2000  # Chars to sample for title extraction
    RAINDROP_TITLE_MAX_TOKENS: int = 50  # Max tokens for LLM title response
    RAINDROP_TITLE_TEMPERATURE: float = 0.3  # LLM temperature for title extraction
    RAINDROP_TITLE_MIN_LENGTH: int = 3  # Minimum valid title length
    RAINDROP_TITLE_MAX_LENGTH: int = 200  # Maximum valid title length

    # =========================================================================
    # LEARNING SYSTEM
    # =========================================================================
    # Mastery calculation weights (must sum to 1.0)
    MASTERY_SUCCESS_RATE_WEIGHT: float = 0.6  # Weight for success rate in mastery score
    MASTERY_STABILITY_WEIGHT: float = 0.4  # Weight for stability in mastery score

    # Mastery thresholds
    MASTERY_WEAK_SPOT_THRESHOLD: float = 0.6  # Below this is considered a weak spot
    MASTERY_NOVICE_THRESHOLD: float = 0.3  # Below this suggests scaffolded exercises
    MASTERY_INTERMEDIATE_THRESHOLD: float = (
        0.6  # Below this suggests retrieval practice
    )
    MASTERY_LOW_SUCCESS_RATE: float = 0.5  # Below this triggers success rate warning

    # Stability thresholds
    MASTERY_STABILITY_NORMALIZATION_DAYS: float = 30.0  # Days to normalize stability
    MASTERY_MASTERED_STABILITY_DAYS: int = (
        21  # Cards with stability >= this are "mastered"
    )

    # Time windows (days)
    MASTERY_SNAPSHOT_LOOKBACK_DAYS: int = 7  # Days to look back for trend comparison
    MASTERY_STREAK_WINDOW_DAYS: int = 30  # Days to consider for streak calculation
    MASTERY_LEARNING_CURVE_DAYS: int = 30  # Default days for learning curve
    MASTERY_STALE_REVIEW_DAYS: int = 14  # Days without review to trigger recommendation

    # Projection settings
    MASTERY_PROJECTION_WINDOW_DAYS: int = 7  # Days used for projection calculation
    MASTERY_PROJECTION_HORIZON_DAYS: int = 30  # Days to project mastery forward

    # Minimums
    MASTERY_MIN_ATTEMPTS: int = 3  # Minimum reviews before calculating mastery

    # Query limits
    MASTERY_MAX_TOPICS_IN_OVERVIEW: int = 20  # Limit topics in overview for performance

    # Trend detection
    MASTERY_TREND_THRESHOLD: float = 0.05  # Score delta to consider improving/declining

    # Exercise mastery threshold
    EXERCISE_MASTERY_SCORE_THRESHOLD: float = (
        0.8  # Score >= this is considered mastered
    )

    # Streak milestones for gamification (in days)
    STREAK_MILESTONES: list[int] = [7, 14, 30, 60, 90, 180, 365]

    # Activity level thresholds for heatmap (ratio -> level)
    # Higher ratios = higher activity levels (0-4 scale)
    ACTIVITY_LEVEL_HIGH: float = 0.75  # Level 4
    ACTIVITY_LEVEL_MEDIUM_HIGH: float = 0.50  # Level 3
    ACTIVITY_LEVEL_MEDIUM: float = 0.25  # Level 2
    # Below 0.25 but > 0 = Level 1, 0 = Level 0

    # =========================================================================
    # CARD GENERATION SETTINGS
    # =========================================================================
    # Initial FSRS difficulty values by card type (0.0-1.0, higher = harder)
    CARD_DIFFICULTY_DEFINITION: float = 0.3  # Basic definition/application cards
    CARD_DIFFICULTY_EXAMPLE: float = 0.4  # Example cards, properties cards
    CARD_DIFFICULTY_MISCONCEPTION: float = 0.5  # Misconception cards (hardest)

    # Difficulty mapping for on-demand generation
    CARD_DIFFICULTY_EASY: float = 0.2
    CARD_DIFFICULTY_MEDIUM: float = 0.4
    CARD_DIFFICULTY_HARD: float = 0.6
    CARD_DIFFICULTY_MIXED: float = 0.3  # Also used as default

    # Limits per concept during ingestion
    CARD_MAX_EXAMPLES_PER_CONCEPT: int = 2
    CARD_MAX_MISCONCEPTIONS_PER_CONCEPT: int = 2
    CARD_MIN_PROPERTIES_FOR_CARD: int = (
        2  # Minimum properties to generate a properties card
    )

    # On-demand generation defaults
    CARD_DEFAULT_COUNT: int = 10  # Default cards to generate for topic
    CARD_MIN_FOR_TOPIC: int = 5  # Minimum cards to ensure per topic
    CARD_CONTEXT_MAX_LENGTH: int = 8000  # Max context chars for LLM prompt
    CARD_LLM_TEMPERATURE: float = 0.7
    CARD_LLM_MAX_TOKENS: int = 2000

    # Context gathering limits
    CARD_CONTEXT_CONTENT_PER_KEYWORD: int = 3  # Content items per keyword search
    CARD_CONTEXT_EXERCISES_LIMIT: int = 5  # Max exercises for context
    CARD_CONTEXT_EXERCISE_PROMPT_LENGTH: int = 500  # Truncate exercise prompts
    CARD_CONTEXT_MIN_KEYWORD_LENGTH: int = 3  # Skip short keywords

    # =========================================================================
    # SESSION / PRACTICE SETTINGS
    # =========================================================================
    # Time allocation ratios for practice sessions (must sum to 1.0)
    # These are defaults that users can override in the frontend settings
    SESSION_TIME_RATIO_SPACED_REP: float = 0.4  # Due spaced rep cards (consolidation)
    SESSION_TIME_RATIO_WEAK_SPOTS: float = (
        0.3  # Weak spot exercises (deliberate practice)
    )
    SESSION_TIME_RATIO_NEW_CONTENT: float = 0.3  # New/interleaved content (transfer)

    # Estimated time per item in minutes
    SESSION_TIME_PER_CARD: float = 2.0  # Minutes per spaced rep card
    SESSION_TIME_PER_EXERCISE: float = 10.0  # Minutes per exercise (avg across types)

    # Session content limits
    SESSION_MAX_WEAK_SPOTS: int = 3  # Max weak spot topics to consider per session

    # Default content mode: "both", "exercises_only", "cards_only"
    SESSION_DEFAULT_CONTENT_MODE: str = "both"

    # Default source preference: "prefer_existing", "generate_new", "existing_only"
    # - prefer_existing: Use existing content when available, generate if needed
    # - generate_new: Always generate fresh content (more LLM cost)
    # - existing_only: Only use existing content (no LLM cost, may have empty sessions)
    SESSION_DEFAULT_EXERCISE_SOURCE: str = "prefer_existing"
    SESSION_DEFAULT_CARD_SOURCE: str = "prefer_existing"

    # Minimum time budget thresholds (minutes)
    SESSION_MIN_TIME_FOR_EXERCISE: float = 5.0  # Min time to add an exercise
    SESSION_MIN_TIME_FOR_CARD: float = 1.0  # Min time to add a card

    # Topic-focused session allocation (when topic_filter is set)
    # Allocates more time to exercises for focused practice
    SESSION_TOPIC_EXERCISE_RATIO: float = 0.8  # 80% exercises when topic selected
    SESSION_TOPIC_CARD_RATIO: float = 0.2  # 20% cards when topic selected

    # Interleaving settings
    SESSION_INTERLEAVE_ENABLED: bool = True  # Shuffle items for interleaving benefit
    SESSION_WORKED_EXAMPLES_FIRST: bool = True  # Place worked examples at start

    # =========================================================================
    # SPACED REPETITION (FSRS) SETTINGS
    # =========================================================================
    # FSRS algorithm defaults
    FSRS_DEFAULT_RETENTION: float = 0.9  # Target retention probability (90%)
    FSRS_MAX_INTERVAL_DAYS: int = 365  # Maximum interval between reviews

    # Initial card state defaults
    FSRS_INITIAL_STABILITY: float = 0.0  # Stability for new cards
    FSRS_INITIAL_DIFFICULTY: float = (
        0.3  # Difficulty for new cards (same as CARD_DIFFICULTY_MIXED)
    )
    FSRS_FALLBACK_DIFFICULTY: float = 0.3  # Fallback when difficulty is None
    FSRS_FALLBACK_STABILITY: float = 1.0  # Fallback when stability is None (for review)

    # Due cards query settings
    REVIEW_DEFAULT_LIMIT: int = 50  # Default number of due cards to fetch
    REVIEW_INTERLEAVE_FETCH_MULTIPLIER: int = (
        2  # Fetch N times limit for better interleaving
    )
    REVIEW_INTERLEAVE_MAX_FETCH: int = 200  # Cap on cards fetched for interleaving

    # =========================================================================
    # ASSISTANT SERVICE
    # =========================================================================
    # Maximum characters for auto-generated conversation titles
    ASSISTANT_MAX_TITLE_LENGTH: int = 50

    # Knowledge search limits for chat context
    ASSISTANT_CHAT_SEARCH_LIMIT: int = 5
    ASSISTANT_CHAT_SEARCH_MIN_SCORE: float = 0.5

    # Knowledge search limits for explicit search
    ASSISTANT_KNOWLEDGE_SEARCH_LIMIT: int = 20
    ASSISTANT_KNOWLEDGE_SEARCH_MIN_SCORE: float = 0.3

    # Context formatting
    ASSISTANT_MAX_SUMMARY_LENGTH: int = 500
    ASSISTANT_SNIPPET_LENGTH: int = 200

    # Conversation history
    ASSISTANT_MAX_HISTORY_MESSAGES: int = 10
    ASSISTANT_DEFAULT_PAGE_LIMIT: int = 20

    # LLM generation parameters
    ASSISTANT_LLM_TEMPERATURE: float = 0.7
    ASSISTANT_LLM_MAX_TOKENS: int = 2048

    # Quiz generation
    ASSISTANT_DEFAULT_QUIZ_QUESTIONS: int = 5
    ASSISTANT_QUIZ_CONTEXT_LIMIT: int = 5

    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    # Rate limiting is disabled by default for development.
    # Enable in production for protection against abuse.
    RATE_LIMITING_ENABLED: bool = False

    # Rate limits per endpoint type (requests/minute format)
    RATE_LIMIT_DEFAULT: str = "100/minute"  # General API endpoints
    RATE_LIMIT_LLM_HEAVY: str = "10/minute"  # Endpoints that call LLMs
    RATE_LIMIT_SEARCH: str = "30/minute"  # Search endpoints
    RATE_LIMIT_CAPTURE: str = "20/minute"  # File upload endpoints
    RATE_LIMIT_AUTH: str = "5/minute"  # Login/auth attempts
    RATE_LIMIT_GRAPH: str = "60/minute"  # Graph queries
    RATE_LIMIT_ANALYTICS: str = "30/minute"  # Analytics endpoints
    RATE_LIMIT_BATCH: str = "5/minute"  # Batch operations

    def get_rate_limit(self, rate_limit_type: RateLimitType) -> str:
        """
        Get rate limit string for a given rate limit type.

        Args:
            rate_limit_type: RateLimitType enum value

        Returns:
            Rate limit string (e.g., "100/minute")
        """
        rate_limit_map = {
            RateLimitType.DEFAULT: self.RATE_LIMIT_DEFAULT,
            RateLimitType.LLM_HEAVY: self.RATE_LIMIT_LLM_HEAVY,
            RateLimitType.SEARCH: self.RATE_LIMIT_SEARCH,
            RateLimitType.CAPTURE: self.RATE_LIMIT_CAPTURE,
            RateLimitType.AUTH: self.RATE_LIMIT_AUTH,
            RateLimitType.GRAPH: self.RATE_LIMIT_GRAPH,
            RateLimitType.ANALYTICS: self.RATE_LIMIT_ANALYTICS,
            RateLimitType.BATCH: self.RATE_LIMIT_BATCH,
        }
        return rate_limit_map.get(rate_limit_type, self.RATE_LIMIT_DEFAULT)

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
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
