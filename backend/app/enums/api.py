"""
API-related enums.

Defines enums for rate limiting, API versioning, explanation styles,
and other API concerns.
"""

from enum import Enum


class ExplanationStyle(str, Enum):
    """
    Style for AI-generated concept explanations.

    Controls the verbosity and complexity of explanations returned
    by the assistant's explain endpoint.

    Usage:
        from app.enums import ExplanationStyle

        style = ExplanationStyle.ELI5
    """

    # Brief, concise explanation suitable for quick reference.
    SIMPLE = "simple"

    # Comprehensive explanation with full context and nuance.
    DETAILED = "detailed"

    # 'Explain Like I'm 5' - simplified explanation using analogies.
    ELI5 = "eli5"


class RateLimitType(str, Enum):
    """
    Rate limit categories for different endpoint types.

    Each category has a corresponding rate limit configured in settings.
    Usage:
        from app.enums import RateLimitType
        from app.config import settings

        limit = settings.get_rate_limit(RateLimitType.LLM_HEAVY)
    """

    # General API endpoints
    DEFAULT = "default"

    # Endpoints that call LLMs (expensive)
    LLM_HEAVY = "llm_heavy"

    # Search endpoints
    SEARCH = "search"

    # File upload endpoints
    CAPTURE = "capture"

    # Login/auth attempts
    AUTH = "auth"

    # Graph queries (moderate load)
    GRAPH = "graph"

    # Analytics endpoints
    ANALYTICS = "analytics"

    # Batch operations
    BATCH = "batch"

