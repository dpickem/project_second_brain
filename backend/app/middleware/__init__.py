"""
Middleware Package

Provides FastAPI middleware for:
- Rate limiting
- Error handling
- Request logging

Rate limiting usage:
    from app.middleware import limiter
    from app.enums import RateLimitType
    from app.config import settings

    @limiter.limit(settings.get_rate_limit(RateLimitType.LLM_HEAVY))
    async def my_endpoint(request: Request):
        ...
"""

from app.middleware.rate_limit import setup_rate_limiting, limiter, get_rate_limit
from app.middleware.error_handling import ErrorHandlingMiddleware, ServiceError, LLMError

__all__ = [
    "setup_rate_limiting",
    "limiter",
    "get_rate_limit",
    "ErrorHandlingMiddleware",
    "ServiceError",
    "LLMError",
]

