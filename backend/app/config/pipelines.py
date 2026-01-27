"""
Pipeline Configuration

Provides type-safe configuration for all ingestion pipelines using Pydantic settings.
Configuration is loaded from environment variables with sensible defaults.

Usage:
    from app.config.pipelines import pipeline_settings

    model = pipeline_settings.OCR_MODEL
    max_size = pipeline_settings.PDF_MAX_FILE_SIZE_MB

Environment Variables:
    PIPELINE_OCR_MODEL - Vision model for OCR (default: mistral/mistral-ocr-latest)
    PIPELINE_TEXT_MODEL - Text model for inference (default: gemini/gemini-3-flash-preview)
    PIPELINE_PDF_HANDWRITING_DETECTION - Enable handwriting detection (default: True)
    etc.
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class PipelineSettings(BaseSettings):
    """Configuration for all ingestion pipelines."""

    # ===========================================
    # PDF Processing
    # ===========================================
    PDF_TEXT_ENGINE: str = "pymupdf"  # or "pdfplumber"
    PDF_HANDWRITING_DETECTION: bool = True
    PDF_IMAGE_DPI: int = 300
    PDF_MAX_FILE_SIZE_MB: int = 50

    # ===========================================
    # Vision OCR - Model-agnostic via LiteLLM
    # ===========================================
    # Format: provider/model-name
    # Supported models include (Updated Dec 2025):
    #   - mistral/mistral-ocr-latest (default - SOTA for document OCR, uses litellm.ocr API)
    #   - gemini/gemini-2.5-flash (Google's vision model, uses chat completion API)
    #   - openai/gpt-4o (OpenAI's vision model, uses chat completion API)
    #   - openai/gpt-5.1-chat-latest, openai/gpt-5-mini
    #   - anthropic/claude-4-5-opus-202511, anthropic/claude-4-5-sonnet-202509
    #   - gemini/gemini-3-flash-preview
    OCR_MODEL: str = "mistral/mistral-ocr-latest"
    OCR_MAX_TOKENS: int = 4000
    OCR_USE_JSON_MODE: bool = True
    OCR_TIMEOUT_SECONDS: int = 60
    OCR_MAX_RETRIES: int = 3

    # ===========================================
    # LiteLLM Spend Management
    # ===========================================
    LITELLM_BUDGET_MAX: float = 100.0  # Monthly budget in USD
    LITELLM_BUDGET_ALERT: float = 80.0  # Alert at 80% usage
    LITELLM_LOG_COSTS: bool = True

    # ===========================================
    # Text Model for Metadata/Inference
    # ===========================================
    TEXT_MODEL: str = "gemini/gemini-3-flash-preview"

    # ===========================================
    # Raindrop.io Sync
    # ===========================================
    RAINDROP_SYNC_INTERVAL_HOURS: int = 6
    RAINDROP_FETCH_FULL_CONTENT: bool = True
    RAINDROP_MAX_CONCURRENT: int = 5

    # ===========================================
    # GitHub Import
    # ===========================================
    GITHUB_SYNC_STARRED: bool = True
    GITHUB_MAX_REPOS: int = 100
    GITHUB_ANALYZE_STRUCTURE: bool = True

    # ===========================================
    # Voice Transcription
    # ===========================================
    VOICE_TRANSCRIPTION_MODEL: str = "whisper-1"
    VOICE_EXPAND_NOTES: bool = True

    # ===========================================
    # Book OCR
    # ===========================================
    BOOK_OCR_MODEL: str = ""  # Falls back to OCR_MODEL if empty
    BOOK_PREPROCESS_IMAGES: bool = True

    # ===========================================
    # Deduplication
    # ===========================================
    DEDUP_ENABLED: bool = True
    DEDUP_WINDOW_DAYS: int = 30
    DEDUP_HASH_ALGORITHM: str = "sha256"

    class Config:
        env_prefix = "PIPELINE_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars not defined in this class

    @property
    def effective_book_ocr_model(self) -> str:
        """Get the effective Book OCR model, falling back to general OCR model."""
        return self.BOOK_OCR_MODEL or self.OCR_MODEL


@lru_cache()
def get_pipeline_settings() -> PipelineSettings:
    """Get cached pipeline settings instance."""
    return PipelineSettings()


# Global settings instance
pipeline_settings = get_pipeline_settings()
