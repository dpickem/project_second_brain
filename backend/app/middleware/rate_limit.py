"""
Rate Limiting Middleware

Prevents abuse and ensures fair resource usage using SlowAPI.

Usage:
    from app.middleware.rate_limit import limiter
    from app.enums import RateLimitType
    from app.config import settings

    @router.post("/exercise/generate")
    @limiter.limit(settings.get_rate_limit(RateLimitType.LLM_HEAVY))
    async def generate_exercise(request: Request, ...):
        ...

Rate limit configurations (from settings):
- DEFAULT: General API endpoints (100/minute)
- LLM_HEAVY: Endpoints that call LLMs (10/minute)
- SEARCH: Search endpoints (30/minute)
- CAPTURE: File upload endpoints (20/minute)
- AUTH: Login attempts (5/minute for future use)
- GRAPH: Graph queries (60/minute)
- ANALYTICS: Analytics endpoints (30/minute)
- BATCH: Batch operations (5/minute)
"""

import logging

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.enums import RateLimitType

logger = logging.getLogger(__name__)


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.

    Uses X-Forwarded-For header if behind a proxy,
    otherwise falls back to direct IP address.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or identifier
    """
    # Check for forwarded header (behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client address
    return get_remote_address(request)


# Initialize limiter with default key function
limiter = Limiter(key_func=get_client_identifier)


def setup_rate_limiting(app: FastAPI, enabled: bool = True) -> None:
    """
    Configure rate limiting on the FastAPI app.

    Args:
        app: FastAPI application instance
        enabled: Whether to enable rate limiting
    """
    if not enabled:
        logger.info("Rate limiting disabled")
        return

    # Store limiter in app state
    app.state.limiter = limiter

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add middleware
    app.add_middleware(SlowAPIMiddleware)

    logger.info("Rate limiting enabled")


def get_rate_limit(rate_limit_type: RateLimitType) -> str:
    """
    Get rate limit string for an endpoint type.

    Args:
        rate_limit_type: RateLimitType enum value

    Returns:
        Rate limit string (e.g., "100/minute")
    """
    return settings.get_rate_limit(rate_limit_type)


# Convenience decorators for common rate limits
def limit_llm(func):
    """Decorator for LLM-heavy endpoints."""
    return limiter.limit(settings.get_rate_limit(RateLimitType.LLM_HEAVY))(func)


def limit_search(func):
    """Decorator for search endpoints."""
    return limiter.limit(settings.get_rate_limit(RateLimitType.SEARCH))(func)


def limit_capture(func):
    """Decorator for capture/upload endpoints."""
    return limiter.limit(settings.get_rate_limit(RateLimitType.CAPTURE))(func)
