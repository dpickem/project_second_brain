"""
Pipeline-related enums.

Defines enums for pipeline identification, operations, and content routing.
"""

from enum import Enum


class PipelineName(str, Enum):
    """
    Pipeline names for cost tracking and attribution.

    Each pipeline has a unique name used to track LLM costs and operations.
    Used by LLMClient for cost attribution in usage records.
    """

    # Ingestion pipelines
    BOOK_OCR = "BOOK_OCR"
    PDF_PROCESSOR = "PDF_PROCESSOR"
    VOICE_TRANSCRIBE = "VOICE_TRANSCRIBE"
    GITHUB_IMPORTER = "GITHUB_IMPORTER"
    WEB_ARTICLE = "WEB_ARTICLE"
    RAINDROP_SYNC = "RAINDROP_SYNC"

    # Processing pipeline
    LLM_PROCESSING = "LLM_PROCESSING"


class PipelineOperation(str, Enum):
    """
    Operation types for LLM calls.

    Used for both:
    1. Model selection: LLMClient uses this to pick the right model for each task
    2. Cost tracking: Operations are logged for fine-grained cost analysis

    The LLMClient.MODELS dict maps operations to their optimal models.
    """

    # Book OCR operations
    PAGE_EXTRACTION = "PAGE_EXTRACTION"
    METADATA_INFERENCE = "METADATA_INFERENCE"

    # PDF Processor operations
    DOCUMENT_OCR = "DOCUMENT_OCR"
    CONTENT_TYPE_CLASSIFICATION = "CONTENT_TYPE_CLASSIFICATION"

    # Voice Transcribe operations
    AUDIO_TRANSCRIPTION = "AUDIO_TRANSCRIPTION"
    NOTE_EXPANSION = "NOTE_EXPANSION"

    # GitHub Importer operations
    REPO_ANALYSIS = "REPO_ANALYSIS"

    # Web Article operations
    TITLE_EXTRACTION = "TITLE_EXTRACTION"

    # Raindrop Sync operations
    BOOKMARK_PROCESSING = "BOOKMARK_PROCESSING"

    # LLM Processing operations
    CONTENT_ANALYSIS = "CONTENT_ANALYSIS"
    SUMMARIZATION = "SUMMARIZATION"
    CONCEPT_EXTRACTION = "CONCEPT_EXTRACTION"
    TAG_ASSIGNMENT = "TAG_ASSIGNMENT"
    CONNECTION_DISCOVERY = "CONNECTION_DISCOVERY"
    FOLLOWUP_GENERATION = "FOLLOWUP_GENERATION"
    QUESTION_GENERATION = "QUESTION_GENERATION"

    # Embeddings
    EMBEDDINGS = "EMBEDDINGS"


class PipelineContentType(str, Enum):
    """
    Content type hint for pipeline routing.

    This enum is used to route inputs to the correct pipeline when the
    file format alone is ambiguous (e.g., images could be book pages,
    whiteboards, or documents).

    Note: This is separate from ContentType in enums/content.py, which
    describes the OUTPUT content type. PipelineContentType describes the
    INPUT intent for routing purposes.
    """

    # Image-based content (requires context to route)
    BOOK = "BOOK"  # Book page photos → BookOCRPipeline
    WHITEBOARD = "WHITEBOARD"  # Whiteboard photos (future)
    DOCUMENT = "DOCUMENT"  # Document scans (future)
    PHOTO = "PHOTO"  # General photos (future)

    # File-based content (file extension is sufficient)
    PDF = "PDF"  # PDF files → PDFProcessor
    VOICE_MEMO = "VOICE_MEMO"  # Audio files → VoiceTranscriber

    # URL-based content
    CODE = "CODE"  # GitHub repos → GitHubImporter
    ARTICLE = "ARTICLE"  # Web articles → RaindropSync

    # Text-based content
    IDEA = "IDEA"  # Quick text captures
    NOTE = "NOTE"  # Longer notes
