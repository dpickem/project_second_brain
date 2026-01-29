"""
SQLAlchemy Database Models

These models define the PostgreSQL schema for the Second Brain system.
They track content metadata and system configuration.

Tables:
- content: Ingested content (papers, articles, etc.)
- annotations: User annotations on content
- tags: Tag definitions
- llm_usage_logs: LLM API usage tracking
- llm_cost_summaries: Aggregated cost reports
- system_meta: System configuration key-value store

Learning system models (practice_sessions, practice_attempts, spaced_rep_cards,
mastery_snapshots, exercises, exercise_attempts) are defined in models_learning.py.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


if TYPE_CHECKING:
    from app.db.models_learning import SpacedRepCard


class ContentStatus(enum.Enum):
    """
    Status of content processing.

    Values:
        PENDING: Content has been ingested but not yet processed.
        PROCESSING: Content is currently being processed by a pipeline.
        PROCESSED: Content has been successfully processed and is ready for use.
        FAILED: Content processing failed; check error logs for details.
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Content(Base):
    """
    Ingested content records.

    Tracks all content that has been ingested into the system,
    including papers, articles, books, code, and ideas.

    Attributes:
        id: Primary key, auto-incrementing integer identifier. Used internally for
            database relationships (foreign keys). NOT exposed externally.
        content_uuid: Globally unique UUID string identifier (e.g., "550e8400-e29b-...").
            This is the PRIMARY identifier used throughout the application for lookups,
            API responses, and external references. Indexed with unique constraint.
            Generated at ingestion time via uuid.uuid4().
        content_type: Type of content (e.g., "paper", "article", "book", "code", "idea").
            Used for routing to appropriate processing pipelines and templates.
        title: Human-readable title of the content, max 500 characters.
        source_url: Original URL where the content was obtained (e.g., arXiv link,
            blog post URL). Optional, max 2000 characters.
        source_path: Original filesystem path for locally-sourced content (e.g., PDF
            file path, voice memo location). Optional, max 1000 characters.
        vault_path: Relative path to the generated Obsidian markdown note within the
            vault (e.g., "papers/attention-is-all-you-need.md"). Optional, max 1000 chars.
        status: Current processing status (PENDING, PROCESSING, PROCESSED, FAILED).
            Defaults to PENDING on creation.
        raw_text: Full extracted/OCR'd text content. May be large for books/papers.
            Optional until processing completes.
        summary: LLM-generated summary of the content. Optional, populated during
            processing.
        metadata_json: Flexible JSON field for content-type-specific metadata (e.g.,
            authors, publication date, ISBN, page count, duration for audio).
        created_at: Timestamp when the content record was first created.
        processed_at: Timestamp when processing completed successfully. Null if not
            yet processed or if processing failed.
        updated_at: Timestamp of last modification, auto-updated on changes.
        annotations: List of user annotations (highlights, notes) linked to this content.
        cards: List of spaced repetition cards generated from this content.
    """

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Content identification
    # content_uuid is the PRIMARY external identifier (UUID string)
    # id (integer) is for internal DB relationships only
    content_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    content_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[Optional[str]] = mapped_column(String(2000))
    source_path: Mapped[Optional[str]] = mapped_column(String(1000))

    # Obsidian integration
    vault_path: Mapped[Optional[str]] = mapped_column(String(1000))

    # Processing
    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(ContentStatus), default=ContentStatus.PENDING
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    # Relationships
    annotations: Mapped[List["Annotation"]] = relationship(back_populates="content")
    cards: Mapped[List["SpacedRepCard"]] = relationship(
        back_populates="content", foreign_keys="SpacedRepCard.source_content_pk"
    )
    images: Mapped[List["Image"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )


class Annotation(Base):
    """
    User annotations on content.

    Stores highlights, notes, and other user-created annotations
    that are linked to specific content.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        content_id: Foreign key reference to the parent Content record.
        annotation_type: Type of annotation (e.g., "highlight", "note", "question",
            "bookmark"). Determines how the annotation is displayed and processed.
        text: The actual annotation text. For highlights, this is the highlighted
            passage. For notes, this is the user's written note.
        context: Surrounding text that provides context for the annotation. Useful
            for understanding highlights without referring back to the source.
        page_number: Page number in the source document where the annotation was made.
            Optional, only applicable to paginated content like PDFs/books.
        is_handwritten: Whether this annotation originated from handwritten notes
            that were OCR'd. Defaults to False.
        ocr_confidence: Confidence score (0.0-1.0) from OCR processing for handwritten
            annotations. Null for typed annotations. Low scores may indicate
            transcription errors.
        created_at: Timestamp when the annotation was created.
        content: Reference to the parent Content object this annotation belongs to.
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id"))

    # Annotation details
    annotation_type: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[str]] = mapped_column(Text)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)

    # For handwritten notes (OCR)
    is_handwritten: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    content: Mapped["Content"] = relationship(back_populates="annotations")


class Image(Base):
    """
    Extracted images from content (PDFs, books, etc.).

    Stores metadata for images extracted during content processing,
    linked to their source content for easy retrieval and display.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        content_id: Foreign key reference to the parent Content record.
        content_uuid: UUID string of the parent content (for convenient lookups).
        filename: Image filename (e.g., "page_1_img_0.png").
        vault_path: Relative path within the Obsidian vault
            (e.g., "assets/images/{uuid}/page_1_img_0.png").
        page_number: Page number in the source document where image was found.
        image_index: Zero-based index of the image on its page.
        width: Image width in pixels.
        height: Image height in pixels.
        file_size: File size in bytes.
        description: OCR-extracted or LLM-generated description of the image.
        created_at: Timestamp when the image record was created.
        content: Reference to the parent Content object.
    """

    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id", ondelete="CASCADE"))

    # Content UUID for convenient lookups without joins
    content_uuid: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    # Image file info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    vault_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Location in source document
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    image_index: Mapped[int] = mapped_column(Integer, default=0)

    # Image metadata
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)

    # Description (from OCR or LLM)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    content: Mapped["Content"] = relationship(back_populates="images")


class Tag(Base):
    """
    Tag definitions.

    Stores the controlled vocabulary of tags used across the system.
    Tags follow the domain/category/topic hierarchy.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        name: Unique tag name following hierarchical format (e.g., "ml/transformers/attention",
            "programming/python/async"). Max 100 characters. Slashes denote hierarchy:
            domain/category/topic.
        description: Human-readable description of what this tag represents, when to
            apply it, and examples. Optional but recommended for discoverability.
        created_at: Timestamp when the tag was first created.
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class LLMUsageLog(Base):
    """
    LLM API usage and cost tracking.

    Records every LLM API call (vision/text) with associated costs
    for spend tracking, budgeting, and cost optimization.

    This enables:
    - Per-request cost tracking
    - Monthly/daily spend reports
    - Cost attribution to specific pipelines/content
    - Budget alerts and limits
    - Model performance vs cost analysis

    ID System (IMPORTANT):
        This model uses TWO content identifiers to avoid confusion:

        1. content_uuid (String): The UUID string passed from pipelines.
           This is the logical identifier used throughout the application.
           Stored for debugging, tracing, and human-readable references.

        2. db_content_id (Integer FK): The resolved database primary key.
           Used for foreign key relationship to Content table.
           Resolved from content_uuid at insert time by CostTracker.

        This separation prevents bugs from overloading a single field with
        different types (UUID string vs integer).

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        request_id: Unique UUID string for request deduplication and tracing.
            Max 64 characters. Indexed for fast lookups.
        model: Full model identifier including provider prefix (e.g.,
            "mistral/mistral-ocr-latest", "openai/gpt-4-turbo"). Max 100 chars. Indexed.
        provider: LLM provider name (e.g., "mistral", "openai", "anthropic").
            Max 50 characters. Indexed for cost-by-provider queries.
        request_type: Type of LLM request (e.g., "vision" for image processing,
            "text" for text completion, "embedding" for embeddings). Max 20 chars.
        prompt_tokens: Number of tokens in the input/prompt. Used for cost calculation.
            Optional, may be null if provider doesn't report.
        completion_tokens: Number of tokens in the model's response/completion.
            Optional, may be null for embeddings or if not reported.
        total_tokens: Sum of prompt_tokens and completion_tokens. Optional,
            provided for convenience.
        cost_usd: Total cost of this request in US dollars. Calculated from
            token counts and model pricing. Optional.
        input_cost_usd: Cost attributed to input/prompt tokens in USD. Optional,
            allows breakdown of input vs output costs.
        output_cost_usd: Cost attributed to completion/output tokens in USD. Optional.
        pipeline: Name of the processing pipeline that made this request (e.g.,
            "book_ocr", "pdf_processor", "voice_transcribe"). Max 50 chars. Indexed
            for cost-by-pipeline analysis.
        content_uuid: UUID string of the content this request was made for.
            Stored as-is from pipelines for debugging/tracing. Max 64 chars. Indexed.
        db_content_id: Integer FK to Content record. Resolved from content_uuid
            at insert time. Optional, indexed. Enables cost attribution queries.
        operation: Specific operation within the pipeline (e.g., "handwriting_detection",
            "metadata_inference", "summarization"). Max 100 chars. Provides granular
            cost attribution.
        latency_ms: Request latency in milliseconds from send to response. Optional.
            Useful for performance monitoring and optimization.
        success: Whether the request completed successfully. Defaults to True.
            Failed requests should still be logged for cost tracking.
        error_message: Error details if success is False. Optional. Useful for
            debugging and identifying problematic patterns.
        created_at: Timestamp when this log entry was created. Indexed for
            time-range queries in reports.
        content: Reference to associated Content record via db_content_id. Optional.
    """

    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Request identification
    request_id: Mapped[str] = mapped_column(String(64), index=True)

    # Model information
    model: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)

    # Request details
    request_type: Mapped[str] = mapped_column(String(20))
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer)

    # Cost tracking (in USD)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    input_cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    output_cost_usd: Mapped[Optional[float]] = mapped_column(Float)

    # Context for attribution
    pipeline: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    # UUID string from pipelines - stored as-is for debugging/tracing
    content_uuid: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    # Integer FK resolved from content_uuid at insert time
    db_content_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content.id"), index=True
    )
    operation: Mapped[Optional[str]] = mapped_column(String(100))

    # Performance metrics
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, index=True
    )

    # Relationships (uses db_content_id FK)
    content: Mapped[Optional["Content"]] = relationship(foreign_keys=[db_content_id])


class LLMCostSummary(Base):
    """
    Aggregated cost summaries for reporting.

    Pre-aggregated daily/monthly summaries for fast dashboard queries.
    Updated periodically or on-demand.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        period_type: Granularity of this summary (e.g., "daily", "monthly", "weekly").
            Max 10 characters. Indexed for filtering by period type.
        period_start: Start timestamp of the period this summary covers (inclusive).
            Indexed for time-range queries.
        period_end: End timestamp of the period this summary covers (exclusive).
            For daily: period_start + 1 day. For monthly: period_start + 1 month.
        total_cost_usd: Sum of all LLM costs in USD for this period. Defaults to 0.0.
        total_requests: Count of all LLM API requests in this period. Defaults to 0.
        total_tokens: Sum of all tokens (input + output) consumed in this period.
            Defaults to 0.
        cost_by_model: JSON dictionary mapping model identifiers to their costs in USD
            (e.g., {"mistral/mistral-ocr-latest": 5.23, "openai/gpt-4": 12.50}).
            Optional, enables breakdown charts.
        cost_by_pipeline: JSON dictionary mapping pipeline names to their costs in USD
            (e.g., {"book_ocr": 8.00, "pdf_processor": 3.50}). Optional, enables
            cost attribution analysis.
        created_at: Timestamp when this summary record was first created.
        updated_at: Timestamp of last update to this summary. Auto-updated on changes.
            Used to track freshness of aggregations.
    """

    __tablename__ = "llm_cost_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Time period (timezone-aware UTC)
    period_type: Mapped[str] = mapped_column(String(10), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Aggregations
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Breakdown by model (JSON: {"mistral/mistral-ocr-latest": 5.23, ...})
    cost_by_model: Mapped[Optional[dict]] = mapped_column(JSON)
    cost_by_pipeline: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )


class SystemMeta(Base):
    """
    System metadata key-value store.

    Stores system-level configuration and state that needs to persist
    across restarts, such as:
    - Last vault sync timestamp
    - Schema version
    - Feature flags

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        key: Unique key name (e.g., "vault_last_sync_time", "schema_version").
            Max 100 characters. Unique and indexed.
        value: String value for the key. Can store JSON strings for complex data.
        description: Human-readable description of what this key stores. Optional.
        created_at: Timestamp when the key was first created.
        updated_at: Timestamp of last update to this key.
    """

    __tablename__ = "system_meta"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Key-value
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )
