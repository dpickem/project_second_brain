"""
API-related enums.

Defines enums for rate limiting, API versioning, and other API concerns.
"""

from enum import Enum


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

