"""
FastAPI Dependencies

Common dependencies for authentication, database sessions, etc.
"""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_capture_api_key(
    api_key: str | None = Depends(api_key_header),
    x_api_key_query: str | None = Header(None, alias="api_key"),
) -> str:
    """
    Verify Capture API key from header or query parameter.
    
    The API key can be provided via:
    - X-API-Key header (preferred)
    - api_key query parameter (for testing/curl)
    
    If CAPTURE_API_KEY is not configured in settings (empty string),
    authentication is disabled (development mode).
    
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    # If no CAPTURE_API_KEY is configured, skip authentication (dev mode)
    if not settings.CAPTURE_API_KEY:
        return "dev-mode"
    
    # Check header first, then query param
    provided_key = api_key or x_api_key_query
    
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if provided_key != settings.CAPTURE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return provided_key


# Dependency that can be used in routers
RequireCaptureAPIKey = Depends(verify_capture_api_key)
