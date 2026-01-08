"""
Enhanced Error Handling Middleware

Provides consistent, informative error responses across the API.

Features:
- Standardized error response format
- Correlation IDs for log tracking
- Sanitized responses (hides internal details in production)
- Custom exception classes for different error types

Usage:
    from app.middleware.error_handling import ErrorHandlingMiddleware, ServiceError

    # Add middleware to app
    app.add_middleware(ErrorHandlingMiddleware)

    # Raise custom exceptions
    raise ServiceError("Something went wrong", status_code=500)

How Exception Interception Works:
    This middleware uses ASGI middleware architecture (via Starlette's
    BaseHTTPMiddleware), not special Python exception hooks.

    The `dispatch()` method wraps `call_next(request)` in a try/except block.
    Since `call_next()` executes all downstream code (other middleware, route
    handlers, dependencies, services), any unhandled exception bubbles up
    through normal Python exception propagation and is caught here.

    Exception flow:
        Request → ErrorHandlingMiddleware.dispatch()
                      │
                      └─ try:
                            await call_next(request)  ← entire app runs here
                                 │
                                 └─ raise SomeException  ← bubbles up
                         except ServiceError:  ← caught here
                         except Exception:     ← or here

    Exception handling hierarchy:
        - HTTPException: Re-raised for FastAPI's built-in handler
        - ServiceError: Custom exceptions → structured JSON response
        - Exception: Catch-all for unexpected errors → sanitized response

    Caveat: BaseHTTPMiddleware cannot catch exceptions raised after the
    response body starts streaming (not an issue for JSON APIs).
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Schema
# =============================================================================


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: str  # Error code (e.g., "internal_server_error")
    message: str  # Human-readable message
    error_id: str  # For log correlation
    details: Optional[dict] = None  # Additional context (sanitized)
    timestamp: datetime


# =============================================================================
# Custom Exceptions
# =============================================================================


class ServiceError(Exception):
    """
    Base exception for service errors.
    
    Provides consistent error handling with:
    - HTTP status code
    - Error code for categorization
    - Optional details for debugging
    
    Example:
        raise ServiceError("Database connection failed", status_code=503)
    """

    status_code: int = 500
    error_code: str = "service_error"

    def __init__(
        self,
        message: str,
        status_code: int = None,
        error_code: str = None,
        details: dict = None,
    ):
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details


class LLMError(ServiceError):
    """
    LLM provider error.
    
    Raised when LLM API calls fail (rate limits, timeouts, etc.)
    """

    status_code = 502
    error_code = "llm_error"


class GraphQueryError(ServiceError):
    """
    Neo4j query error.
    
    Raised when graph database queries fail.
    """

    status_code = 500
    error_code = "graph_error"


class ValidationError(ServiceError):
    """
    Data validation error.
    
    Raised when input data fails validation.
    """

    status_code = 422
    error_code = "validation_error"


class NotFoundError(ServiceError):
    """
    Resource not found error.
    
    Raised when a requested resource doesn't exist.
    """

    status_code = 404
    error_code = "not_found"


class RateLimitError(ServiceError):
    """
    Rate limit exceeded error.
    
    Raised when client exceeds rate limits.
    """

    status_code = 429
    error_code = "rate_limit_exceeded"


class AuthorizationError(ServiceError):
    """
    Authorization error.
    
    Raised when user lacks permission.
    """

    status_code = 403
    error_code = "forbidden"


# =============================================================================
# Error Handling Middleware
# =============================================================================


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.

    - Catches unhandled exceptions
    - Logs with correlation ID
    - Returns consistent error format
    - Hides internal details in production
    """

    def __init__(self, app, debug: bool = False):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI/Starlette application
            debug: Whether to include stack traces in responses
        """
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next):
        """Process request and handle any errors."""
        error_id = str(uuid4())[:8]

        try:
            response = await call_next(request)
            return response

        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise

        except ServiceError as e:
            # Handle custom service errors
            logger.error(
                f"[{error_id}] {e.error_code}: {e.message}",
                extra={
                    "error_id": error_id,
                    "error_code": e.error_code,
                    "path": request.url.path,
                    "method": request.method,
                    "details": e.details,
                },
            )

            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.error_code,
                    "message": e.message,
                    "error_id": error_id,
                    "details": e.details if self.debug else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            # Log full traceback for unexpected errors
            logger.error(
                f"[{error_id}] Unhandled error: {type(e).__name__}: {e}",
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc(),
                },
            )

            # Return sanitized response
            content = {
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "error_id": error_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Include details in debug mode
            if self.debug:
                content["details"] = {
                    "exception": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }

            return JSONResponse(status_code=500, content=content)


# =============================================================================
# Setup Function
# =============================================================================


def setup_error_handling(app: FastAPI, debug: bool = False) -> None:
    """
    Configure error handling on the FastAPI app.
    
    Args:
        app: FastAPI application instance
        debug: Whether to include stack traces in responses
    """
    app.add_middleware(ErrorHandlingMiddleware, debug=debug)
    logger.info(f"Error handling middleware enabled (debug={debug})")


# =============================================================================
# Helper Functions
# =============================================================================


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: dict = None,
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_code: Error code for categorization
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional details
        
    Returns:
        JSONResponse with standardized error format
    """
    error_id = str(uuid4())[:8]

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": message,
            "error_id": error_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

