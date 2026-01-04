"""
Processing Pipeline Configuration

Configuration settings for the LLM processing pipeline. These settings
control model selection, content limits, connection discovery parameters,
and output generation.

All settings can be overridden via environment variables with PROCESSING_ prefix.

Usage:
    from app.config.processing import processing_settings

    max_len = processing_settings.MAX_CONTENT_LENGTH
    threshold = processing_settings.CONNECTION_SIMILARITY_THRESHOLD
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class ProcessingSettings(BaseSettings):
    """
    Processing pipeline configuration.

    Attributes are grouped by category:
    - LLM model configuration
    - Content processing limits
    - Connection discovery parameters
    - Output settings
    - Tag taxonomy settings
    - Quality validation settings
    - Cost management
    """

    # =========================================================================
    # LLM MODEL CONFIGURATION
    # =========================================================================
    # Model identifiers use LiteLLM format: provider/model-name
    # These can be overridden to use different models per task

    # Fast, cost-efficient for structured analysis
    MODEL_CLASSIFICATION: str = "gemini/gemini-3-flash-preview"

    # Long-form understanding, nuanced summaries
    MODEL_SUMMARIZATION: str = "gemini/gemini-3-flash-preview"

    # Strong structured JSON output
    MODEL_EXTRACTION: str = "gemini/gemini-3-flash-preview"

    # Nuanced reasoning for connection evaluation
    MODEL_CONNECTIONS: str = "gemini/gemini-3-flash-preview"

    # Creative yet precise question generation
    MODEL_QUESTIONS: str = "gemini/gemini-3-flash-preview"

    # Document and image understanding
    MODEL_VISION_OCR: str = "gemini/gemini-3-flash-preview"

    # Vector embeddings for similarity search
    MODEL_EMBEDDINGS: str = "openai/text-embedding-3-small"

    # =========================================================================
    # CONTENT PROCESSING LIMITS
    # =========================================================================
    # Maximum character limits for different processing stages

    # Overall content length limit
    MAX_CONTENT_LENGTH: int = 100000

    # Maximum annotations to include in prompts
    MAX_ANNOTATIONS: int = 100

    # Content truncation for analysis stage (characters)
    # Note: Truncation improves cost and speed even with models supporting 1M+ context.
    # Analysis only needs a representative sample to determine type/domain/complexity.
    ANALYSIS_TRUNCATE: int = 20000
    ANALYSIS_TEMPERATURE: float = 0.1
    ANALYSIS_MAX_TOKENS: int = 500

    # Content truncation per summary level (characters)
    SUMMARY_TRUNCATE_BRIEF: int = 10000
    SUMMARY_TRUNCATE_STANDARD: int = 25000
    SUMMARY_TRUNCATE_DETAILED: int = 40000

    # Max tokens for summary generation per level
    SUMMARY_MAX_TOKENS_BRIEF: int = 200
    SUMMARY_MAX_TOKENS_STANDARD: int = 800
    SUMMARY_MAX_TOKENS_DETAILED: int = 2000
    SUMMARY_TEMPERATURE: float = 0.3

    # Annotation formatting limits
    ANNOTATION_TRUNCATE: int = 300  # Max chars per annotation in prompts

    # Content truncation for extraction
    EXTRACTION_TRUNCATE: int = 20000

    # LLM parameters for concept extraction
    EXTRACTION_TEMPERATURE: float = 0.2
    EXTRACTION_MAX_TOKENS: int = 3000

    # =========================================================================
    # NEO4J KNOWLEDGE GRAPH SETTINGS
    # =========================================================================
    # Parameters for Neo4j node storage and graph queries

    # Default number of results for vector similarity search
    NEO4J_VECTOR_SEARCH_TOP_K: int = 10

    # Default similarity threshold for vector search (0-1)
    NEO4J_VECTOR_SEARCH_THRESHOLD: float = 0.7

    # Max chars for summary stored in Neo4j Content nodes
    NEO4J_SUMMARY_TRUNCATE: int = 2000

    # Default max depth for graph traversal queries
    NEO4J_GRAPH_TRAVERSAL_DEPTH: int = 2

    # =========================================================================
    # CONNECTION DISCOVERY
    # =========================================================================
    # Parameters for semantic connection discovery

    # Minimum embedding similarity score for candidates (0-1)
    CONNECTION_SIMILARITY_THRESHOLD: float = 0.7

    # Minimum strength for a connection to be kept (0-1)
    CONNECTION_STRENGTH_THRESHOLD: float = 0.4

    # Maximum candidates to evaluate per content
    MAX_CONNECTION_CANDIDATES: int = 10

    # Multiplier for initial candidate retrieval (gets more, filters later)
    CONNECTION_CANDIDATE_MULTIPLIER: int = 2

    # Max chars of summary for embedding generation
    CONNECTION_EMBEDDING_TRUNCATE: int = 2000

    # Max chars of new content summary for evaluation prompt
    CONNECTION_EVAL_SUMMARY_TRUNCATE: int = 1500

    # Max chars of candidate summary for evaluation prompt
    CONNECTION_CANDIDATE_SUMMARY_TRUNCATE: int = 1000

    # Max concepts to include in evaluation prompt
    CONNECTION_MAX_CONCEPTS: int = 10

    # LLM parameters for connection evaluation
    CONNECTION_TEMPERATURE: float = 0.2
    CONNECTION_MAX_TOKENS: int = 300

    # =========================================================================
    # OUTPUT SETTINGS
    # =========================================================================

    # Whether to organize notes by content type subfolder
    NOTE_SUBFOLDER_BY_TYPE: bool = True

    # Whether to create Neo4j nodes (can be disabled for testing)
    GENERATE_NEO4J_NODES: bool = True

    # Whether to generate Obsidian notes
    GENERATE_OBSIDIAN_NOTES: bool = True

    # =========================================================================
    # TAG TAXONOMY SETTINGS
    # =========================================================================

    # Path to tag taxonomy YAML file (single source of truth)
    TAG_TAXONOMY_PATH: str = "config/tag-taxonomy.yaml"

    # Cache TTL in seconds before re-checking file
    TAG_TAXONOMY_CACHE_TTL: int = 300

    # =========================================================================
    # TAGGING STAGE SETTINGS
    # =========================================================================

    # Max domain tags to include in tagging prompt (prevents token overflow)
    TAGGING_MAX_DOMAIN_TAGS: int = 100

    # Max summary characters to include in tagging prompt
    TAGGING_SUMMARY_TRUNCATE: int = 2000

    # Max key topics to include in tagging prompt
    TAGGING_MAX_KEY_TOPICS: int = 10

    # LLM parameters for tag assignment
    TAGGING_TEMPERATURE: float = 0.1
    TAGGING_MAX_TOKENS: int = 500

    # =========================================================================
    # FOLLOWUP GENERATION SETTINGS
    # =========================================================================

    # Max concepts to include in followup prompt
    FOLLOWUP_MAX_CONCEPTS: int = 10

    # Max chars of summary for followup prompt
    FOLLOWUP_SUMMARY_TRUNCATE: int = 2000

    # Max annotations to include in followup prompt
    FOLLOWUP_MAX_ANNOTATIONS: int = 10

    # Max chars per annotation in followup prompt
    FOLLOWUP_ANNOTATION_TRUNCATE: int = 200

    # LLM parameters for followup generation
    FOLLOWUP_TEMPERATURE: float = 0.4
    FOLLOWUP_MAX_TOKENS: int = 1000

    # =========================================================================
    # MASTERY QUESTION GENERATION SETTINGS
    # =========================================================================

    # Max concepts to include in question generation prompt
    QUESTIONS_MAX_CONCEPTS: int = 10

    # Max key findings to include in question generation prompt
    QUESTIONS_MAX_FINDINGS: int = 10

    # Max chars of summary for question generation prompt
    QUESTIONS_SUMMARY_TRUNCATE: int = 3000

    # Max hints per question
    QUESTIONS_MAX_HINTS: int = 3

    # Max key points per question (for answer evaluation)
    QUESTIONS_MAX_KEY_POINTS: int = 5

    # LLM parameters for question generation
    QUESTIONS_TEMPERATURE: float = 0.4
    QUESTIONS_MAX_TOKENS: int = 2000

    # =========================================================================
    # QUALITY VALIDATION SETTINGS
    # =========================================================================

    # Whether to validate processing outputs
    VALIDATE_OUTPUTS: bool = True

    # Minimum summary length (characters)
    MIN_SUMMARY_LENGTH: int = 100

    # Minimum number of concepts to extract
    MIN_CONCEPTS: int = 1

    # Minimum number of questions to generate
    MIN_QUESTIONS: int = 2

    # =========================================================================
    # PROCESSING TIMEOUTS
    # =========================================================================

    # Maximum time for entire pipeline (seconds)
    PIPELINE_TIMEOUT_SECONDS: int = 300

    # Maximum time for single LLM call (seconds)
    LLM_TIMEOUT_SECONDS: int = 60

    # Maximum retries for failed LLM calls
    MAX_LLM_RETRIES: int = 3

    class Config:
        env_prefix = "PROCESSING_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_processing_settings() -> ProcessingSettings:
    """Get cached processing settings instance."""
    return ProcessingSettings()


# Convenience instance
processing_settings = get_processing_settings()
