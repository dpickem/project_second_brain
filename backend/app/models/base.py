"""
Strict Base Model for API Request/Response Validation

This module provides base classes with strict validation settings to harden
the API contract between backend and frontend.

MOTIVATION:
    Parameter mismatches between frontend and backend are a common source of bugs.
    By enforcing strict validation:
    - Unknown fields are rejected with 422 (extra="forbid")
    - Required vs optional is enforced at compile-time
    - Type mismatches fail fast with clear error messages

Usage:
    # For request bodies (strictest validation)
    class ItemCreate(StrictRequest):
        name: str
        quantity: int

    # For response bodies (allows extra fields from DB)
    class ItemResponse(StrictResponse):
        id: str
        name: str
        quantity: int

Architecture:
    API Request → StrictRequest (extra="forbid") → Route Handler
    DB Model → StrictResponse (extra="ignore") → API Response
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StrictRequest(BaseModel):
    """
    Base model for API request bodies with strict validation.

    Rejects any fields not explicitly declared in the model, catching
    frontend typos and mismatches at request time rather than runtime.

    Features:
        - extra="forbid": Unknown fields raise 422 Unprocessable Entity
        - validate_default=True: Validates default values
        - str_strip_whitespace=True: Trims whitespace from strings
        - from_attributes=True: Allows ORM model conversion

    Example:
        >>> class ItemCreate(StrictRequest):
        ...     name: str
        ...     quantity: int
        >>>
        >>> ItemCreate(name="Widget", quantity=5)  # OK
        >>> ItemCreate(name="Widget", qty=5)  # Raises ValidationError
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_default=True,  # Validate defaults
        str_strip_whitespace=True,  # Clean string inputs
        from_attributes=True,  # Enable ORM conversion
    )


class StrictResponse(BaseModel):
    """
    Base model for API response bodies.

    More lenient than StrictRequest to allow flexibility in response data.
    Still enforces type validation but allows extra fields.

    Features:
        - extra="ignore": Silently ignores extra fields (DB may have more columns)
        - validate_default=True: Validates default values
        - from_attributes=True: Allows ORM model conversion

    Example:
        >>> class ItemResponse(StrictResponse):
        ...     id: str
        ...     name: str
        >>>
        >>> # DB model might have extra fields - they're ignored
        >>> ItemResponse.model_validate(db_item)
    """

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields in responses
        validate_default=True,  # Validate defaults
        from_attributes=True,  # Enable ORM conversion
    )


class APIModel(BaseModel):
    """
    Base model for bidirectional API models (used in both requests and responses).

    Use this when the same model is used for input and output, like
    configuration objects or simple DTOs.

    Features:
        - extra="forbid": Strict for requests
        - from_attributes=True: Enable ORM conversion

    Note: Prefer StrictRequest/StrictResponse for clarity about intent.
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )


# =============================================================================
# Common Response Patterns
# =============================================================================


class ErrorDetail(StrictResponse):
    """
    Standardized error response detail.

    Matches the error format from the error_handling middleware.
    Frontend clients can rely on this consistent structure.
    """

    error: str  # Error code (e.g., "validation_error")
    message: str  # Human-readable message
    error_id: str  # Correlation ID for log lookup
    details: Optional[dict] = None  # Additional context
    timestamp: datetime


class PaginatedResponse(StrictResponse):
    """
    Base model for paginated list responses.

    Subclass and add an 'items' field with the appropriate type:

        class ItemList(PaginatedResponse):
            items: list[ItemResponse]
    """

    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class SuccessResponse(StrictResponse):
    """
    Simple success response for operations without complex output.

    Example usage:
        @router.delete("/items/{id}", response_model=SuccessResponse)
        async def delete_item(id: str):
            # ... delete logic
            return SuccessResponse(message="Item deleted successfully")
    """

    success: bool = True
    message: str


# =============================================================================
# Query Parameter Models
# =============================================================================


class PaginationParams(StrictRequest):
    """
    Standard pagination query parameters.

    Use with FastAPI's Depends() for consistent pagination:

        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


class SearchParams(StrictRequest):
    """
    Standard search query parameters.

    Use with FastAPI's Depends() for consistent search:

        @router.get("/items")
        async def list_items(search: SearchParams = Depends()):
            ...
    """

    q: Optional[str] = None  # Search query
    sort_by: Optional[str] = None  # Field to sort by
    sort_order: str = "desc"  # asc or desc
