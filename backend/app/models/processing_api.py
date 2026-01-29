"""
Processing API Request/Response Models

Pydantic models for the processing API endpoints. These are DTOs (Data Transfer Objects)
specifically for API communication, separate from the domain models in processing.py.

Domain models (processing.py): Pipeline data structures, LLM outputs
API models (this file): Request bodies, response schemas, endpoint-specific DTOs

Usage:
    from app.models.processing_api import (
        TriggerProcessingRequest,
        ProcessingStatusResponse,
        FollowupTaskListResponse,
    )
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import StrictRequest
from app.models.processing import (
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Connection,
    FollowupTask,
    MasteryQuestion,
)


# =============================================================================
# Processing Trigger Models
# =============================================================================


class ProcessingConfigRequest(StrictRequest):
    """
    Configuration options for processing request.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    generate_summaries: bool = True
    extract_concepts: bool = True
    assign_tags: bool = True
    generate_cards: bool = True  # Generate spaced repetition cards
    generate_exercises: bool = True  # Generate practice exercises
    discover_connections: bool = True
    generate_followups: bool = True
    generate_questions: bool = True
    create_obsidian_note: bool = True
    create_neo4j_nodes: bool = True
    validate_output: bool = True


class TriggerProcessingRequest(StrictRequest):
    """
    Request body for triggering processing.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    content_id: str = Field(..., description="UUID of content to process")
    config: Optional[ProcessingConfigRequest] = None


class TriggerProcessingResponse(BaseModel):
    """Response for processing trigger."""

    status: str
    content_id: str
    message: str


# =============================================================================
# Processing Status Models
# =============================================================================


class ProcessingStatusResponse(BaseModel):
    """Response for processing status check."""

    status: str  # not_processed, pending, processing, completed, failed
    content_id: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    error_message: Optional[str] = None


class ProcessingResultResponse(BaseModel):
    """Response with full processing result."""

    content_id: str
    analysis: ContentAnalysis
    summaries: dict[str, str]  # level (brief/standard/detailed) -> summary text
    extraction: ExtractionResult
    tags: TagAssignment
    connections: list[Connection]
    followups: list[FollowupTask]
    questions: list[MasteryQuestion]
    obsidian_path: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    processing_time_seconds: float
    estimated_cost_usd: float


# =============================================================================
# Pending Content Models
# =============================================================================


class PendingContentItem(BaseModel):
    """A content item pending processing."""

    content_id: str
    title: str
    content_type: str
    status: str
    source_url: Optional[str] = None
    created_at: str


class PendingContentResponse(BaseModel):
    """Response with list of pending content items."""

    total: int
    items: list[PendingContentItem]


# =============================================================================
# Follow-up Tasks Management Models
# =============================================================================


class FollowupTaskListItem(BaseModel):
    """Follow-up task item for list response."""

    id: str
    content_id: int
    content_title: Optional[str] = None
    task: str
    task_type: str
    priority: str
    estimated_time: str
    completed: bool
    completed_at: Optional[str] = None
    created_at: str


class FollowupTaskListResponse(BaseModel):
    """Response for listing follow-up tasks."""

    total: int
    tasks: list[FollowupTaskListItem]


class UpdateFollowupRequest(StrictRequest):
    """Request body for updating a follow-up task."""

    completed: Optional[bool] = None


class UpdateFollowupResponse(BaseModel):
    """Response for updating a follow-up task."""

    id: str
    completed: bool
    completed_at: Optional[str] = None
    message: str
