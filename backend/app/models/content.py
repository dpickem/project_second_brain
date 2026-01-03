"""
Unified Content Format (UCF) Models

The UCF is the cornerstone of the ingestion architecture. Regardless of source
(PDF, web article, book photo, voice memo), all content is normalized into
this common format. This enables:

- Downstream processing consistency: LLM processors work with one format
- Source-agnostic storage: PostgreSQL stores all content uniformly
- Annotation preservation: Highlights, handwritten notes travel with content
- Validation: Pydantic ensures data integrity before storage

Usage:
    from app.models.content import UnifiedContent, ContentType, Annotation

    content = UnifiedContent(
        source_type=ContentType.PAPER,
        title="Attention Is All You Need",
        full_text="...",
        annotations=[Annotation(type=AnnotationType.DIGITAL_HIGHLIGHT, content="...")]
    )
"""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """
    Built-in content types for the ingestion system.

    This enum should stay in sync with config/default.yaml content_types section.
    The enum provides compile-time type safety in Python code, while the YAML
    config defines runtime behavior (folders, templates, icons).

    TO ADD A NEW CONTENT TYPE:
    1. Add to config/default.yaml content_types section (defines folder, template, etc.)
    2. Add to this enum (e.g., PODCAST = "podcast") for type safety
    3. Create Obsidian template in vault's templates/ folder
    4. Create Jinja2 template in config/templates/
    5. Run `python scripts/setup_vault.py` to create folders

    See config/default.yaml for the full content type registry with all configuration.
    """

    # Technical content
    PAPER = "paper"
    ARTICLE = "article"
    BOOK = "book"
    CODE = "code"
    IDEA = "idea"
    VOICE_MEMO = "voice_memo"

    # Career & personal development
    CAREER = "career"
    PERSONAL = "personal"
    PROJECT = "project"
    REFLECTION = "reflection"
    NON_TECH = "non_tech"

    # System types
    DAILY = "daily"
    CONCEPT = "concept"
    EXERCISE = "exercise"


class AnnotationType(str, Enum):
    """Types of annotations that can be attached to content."""

    DIGITAL_HIGHLIGHT = "digital_highlight"
    HANDWRITTEN_NOTE = "handwritten_note"
    TYPED_COMMENT = "typed_comment"
    DIAGRAM = "diagram"
    UNDERLINE = "underline"


class ProcessingStatus(str, Enum):
    """Processing status for content items.
    
    Values must match the PostgreSQL contentstatus enum (uppercase).
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"  # Note: DB uses PROCESSED, not COMPLETED
    FAILED = "FAILED"


class Annotation(BaseModel):
    """
    Represents an annotation on content.

    Annotations preserve the user's engagement with source material, including
    digital highlights, handwritten margin notes, typed comments, and diagrams.

    Attributes:
        id (str): Unique identifier (UUID v4). Auto-generated if not provided.

        type (AnnotationType): The kind of annotation:
            - DIGITAL_HIGHLIGHT: Text highlighted in a PDF reader or web highlighter
            - HANDWRITTEN_NOTE: Margin notes detected via Vision LLM OCR
            - TYPED_COMMENT: Text comments/notes added by user
            - DIAGRAM: Drawings or diagrams extracted from content
            - UNDERLINE: Underlined text passages

        content (str): The annotation text. Required field.
            For highlights: the highlighted text itself.
            For notes: the transcribed note content.

        page_number (int | None): Page where annotation appears (1-indexed).
            Only applicable for paginated content (PDFs, books).

        position (dict | None): Location information for the annotation.
            Format varies by source:
            - PDF highlights: {"rect": [x1, y1, x2, y2]}
            - Margin notes: {"location": "right-margin", "note_type": "question"}
            - Book pages: {"location": "top", "style": "underline"}

        context (str | None): Surrounding text that the annotation relates to.
            For margin notes: the printed text the note refers to.
            Helps understand what the annotation is about.

        confidence (float | None): OCR confidence score between 0.0 and 1.0.
            Only set for OCR-extracted annotations (handwritten notes).
            Higher values indicate more reliable transcription.

    Example:
        >>> highlight = Annotation(
        ...     type=AnnotationType.DIGITAL_HIGHLIGHT,
        ...     content="attention mechanism",
        ...     page_number=5,
        ...     position={"rect": [100, 200, 400, 220]}
        ... )
        >>> margin_note = Annotation(
        ...     type=AnnotationType.HANDWRITTEN_NOTE,
        ...     content="Key insight!",
        ...     page_number=5,
        ...     context="The attention mechanism allows...",
        ...     confidence=0.92
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: AnnotationType
    content: str
    page_number: Optional[int] = None
    position: Optional[dict] = (
        None  # {x, y, width, height} or {"location": "margin-right"}
    )
    context: Optional[str] = None  # Surrounding text for context
    confidence: Optional[float] = Field(None, ge=0, le=1)  # OCR confidence score

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "digital_highlight",
                "content": "Attention is all you need",
                "page_number": 1,
                "context": "In this paper, we propose a new simple network architecture...",
            }
        }


class UnifiedContent(BaseModel):
    """
    Unified Content Format (UCF) - the standard format for all ingested content.

    All ingestion pipelines (PDF, Raindrop, Book OCR, Voice, GitHub) output
    content in this standardized format, enabling consistent downstream processing.

    Attributes:
        id (str): Unique identifier (UUID v4). Auto-generated if not provided.
            Used as primary key for database storage and cross-referencing.

        source_type (ContentType): The type of content (paper, article, book, etc.).
            Determines which folder and template are used in Obsidian.
            See ContentType enum and config/default.yaml for all types.

        source_url (str | None): Original URL if content was fetched from the web.
            Examples: article URL, GitHub repo URL, Raindrop bookmark URL.

        source_file_path (str | None): Local file path if content came from a file.
            Examples: PDF path, voice memo path, book photo path.

        title (str): Human-readable title for the content. Required field.
            Used as note title in Obsidian and display name in UI.

        authors (list[str]): List of author names. Defaults to empty list.
            Extracted from PDF metadata, GitHub repo owner, or article byline.

        created_at (datetime): When the original content was created.
            For PDFs: document creation date. For articles: publish date.
            Defaults to current time if unknown.

        ingested_at (datetime): When the content was ingested into the system.
            Auto-set to current time. Used for tracking and sorting.

        full_text (str): Complete extracted text content. Defaults to empty string.
            For PDFs: all pages concatenated. For voice: transcript.
            May include page markers like "[Page 1]" for multi-page content.

        annotations (list[Annotation]): User annotations attached to the content.
            Includes highlights, handwritten notes, typed comments.
            Each annotation has type, content, optional page number and position.

        raw_file_hash (str | None): SHA-256 hash of the original file.
            Used for deduplication - prevents re-processing identical files.
            Only set for file-based content (PDFs, images, audio).

        asset_paths (list[str]): Paths to associated assets (images, original files).
            Used to track where uploaded files are stored.
            Examples: ["/uploads/pdfs/abc123.pdf", "/uploads/photos/page1.jpg"]

        processing_status (ProcessingStatus): Current processing state.

        error_message (str | None): Error details if processing_status is FAILED.
            Contains exception message or description of what went wrong.

        obsidian_path (str | None): Path to the generated note in Obsidian vault.
            Set after successful processing. Example: "sources/papers/attention.md"

        tags (list[str]): Tags for categorization and search.
            Can be user-provided at capture time or LLM-extracted during processing.
            Examples: ["ml", "transformers", "attention"]

        metadata (dict): Flexible key-value store for additional data.
            Used for source-specific data that doesn't fit standard fields.
            Examples: {"doi": "10.1234/...", "github_stars": 1000, "isbn": "..."}

    Example:
        >>> content = UnifiedContent(
        ...     source_type=ContentType.PAPER,
        ...     title="Attention Is All You Need",
        ...     authors=["Vaswani et al."],
        ...     full_text="We propose a new architecture...",
        ...     annotations=[
        ...         Annotation(
        ...             type=AnnotationType.DIGITAL_HIGHLIGHT,
        ...             content="self-attention mechanism",
        ...             page_number=3
        ...         )
        ...     ],
        ...     tags=["ml", "transformers"]
        ... )
    """

    # Core identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: ContentType
    source_url: Optional[str] = None
    source_file_path: Optional[str] = None

    # Metadata
    title: str
    authors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    ingested_at: datetime = Field(default_factory=datetime.now)

    # Content
    full_text: str = ""
    annotations: list[Annotation] = Field(default_factory=list)

    # Raw storage
    raw_file_hash: Optional[str] = None  # SHA256 of original file
    asset_paths: list[str] = Field(default_factory=list)  # Paths to images, diagrams

    # Processing status
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None

    # Obsidian integration
    obsidian_path: Optional[str] = None  # Path in Obsidian vault once created

    # Tags (extracted or user-provided)
    tags: list[str] = Field(default_factory=list)

    # Additional metadata (flexible)
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source_type": "paper",
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "full_text": "We propose a new simple network architecture...",
                "processing_status": "PENDING",
            }
        }


class ContentBatch(BaseModel):
    """Batch of content items for bulk processing."""

    items: list[UnifiedContent]
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
