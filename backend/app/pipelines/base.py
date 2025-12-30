"""
Abstract Base Pipeline

All ingestion pipelines inherit from BasePipeline, which enforces a consistent
interface and provides shared utilities:

- Polymorphism: Route content to appropriate pipeline dynamically
- Shared utilities: Hash calculation, duplicate detection, logging
- Testability: Each pipeline can be tested against the same interface
- Extensibility: Adding new content sources only requires implementing the base interface

Design Principle - One Pipeline Per (file_type, content_type) Pair:
    The routing key is a TUPLE of (file_format, content_type), not just file extension.
    This allows different pipelines to handle the same file format based on context:

    - (image, BOOK) → BookOCRPipeline
    - (image, WHITEBOARD) → WhiteboardOCRPipeline (future)
    - (image, DOCUMENT) → DocumentOCRPipeline (future)
    - (pdf, *) → PDFProcessor
    - (audio, *) → VoiceTranscriber
    - (url, CODE) → GitHubImporter
    - (url, ARTICLE) → RaindropSync

    Use PipelineInput to wrap your input with content type context.

Usage:
    from app.pipelines.base import PipelineInput, PipelineContentType

    # Create input with context
    input_data = PipelineInput(
        path=Path("page.jpg"),
        content_type=PipelineContentType.BOOK,
    )

    # Route through registry
    content = await registry.process(input_data)

    # Or check pipeline support directly
    if pipeline.supports(input_data):
        content = await pipeline.process(input_data)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import logging

from app.models.content import UnifiedContent
from app.pipelines.utils.hash_utils import (
    calculate_file_hash,
    calculate_content_hash as _calculate_content_hash,
)


class PipelineContentType(str, Enum):
    """
    Content type hint for pipeline routing.

    This enum is used to route inputs to the correct pipeline when the
    file format alone is ambiguous (e.g., images could be book pages,
    whiteboards, or documents).

    Note: This is separate from ContentType in models/content.py, which
    describes the OUTPUT content type. PipelineContentType describes the
    INPUT intent for routing purposes.
    """

    # Image-based content (requires context to route)
    BOOK = "book"  # Book page photos → BookOCRPipeline
    WHITEBOARD = "whiteboard"  # Whiteboard photos (future)
    DOCUMENT = "document"  # Document scans (future)
    PHOTO = "photo"  # General photos (future)

    # File-based content (file extension is sufficient)
    PDF = "pdf"  # PDF files → PDFProcessor
    VOICE_MEMO = "voice_memo"  # Audio files → VoiceTranscriber

    # URL-based content
    CODE = "code"  # GitHub repos → GitHubImporter
    ARTICLE = "article"  # Web articles → RaindropSync

    # Text-based content
    IDEA = "idea"  # Quick text captures
    NOTE = "note"  # Longer notes


@dataclass
class PipelineInput:
    """
    Wrapper for pipeline input that provides routing context.

    Combines the actual input (file path, URL, or text) with a content type
    hint that helps the registry route to the correct pipeline.

    Attributes:
        path: File path for file-based content (images, PDFs, audio)
        url: URL for web-based content (GitHub, articles)
        text: Text content for direct text input
        content_type: Hint for pipeline routing

    Usage:
        # File input
        input = PipelineInput(
            path=Path("page.jpg"),
            content_type=PipelineContentType.BOOK,
        )

        # URL input
        input = PipelineInput(
            url="https://github.com/user/repo",
            content_type=PipelineContentType.CODE,
        )
    """

    content_type: PipelineContentType
    path: Optional[Path] = None
    url: Optional[str] = None
    text: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate that at least one input source is provided."""
        if not any([self.path, self.url, self.text]):
            raise ValueError("PipelineInput requires at least one of: path, url, text")


class BasePipeline(ABC):
    """Abstract base class for all ingestion pipelines."""

    # Subclasses should define which content types they handle
    SUPPORTED_CONTENT_TYPES: set[PipelineContentType] = set()

    def __init__(self, llm_client: Any = None) -> None:
        """
        Initialize the pipeline.

        Args:
            llm_client: Optional LLM client for pipelines that need LLM processing
        """
        self.llm_client: Any = llm_client
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        """
        Process input and return UnifiedContent.

        Args:
            input_data: PipelineInput with path/url/text and content_type

        Returns:
            UnifiedContent object with extracted/processed content
        """
        pass

    @abstractmethod
    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Implementations should check:
        1. The content_type matches this pipeline's supported types
        2. The file format (if applicable) is supported

        Example:
            def supports(self, input_data: PipelineInput) -> bool:
                if input_data.content_type != PipelineContentType.BOOK:
                    return False
                if input_data.path is None:
                    return False
                return input_data.path.suffix.lower() in self.SUPPORTED_FORMATS

        Args:
            input_data: PipelineInput to check

        Returns:
            True if this pipeline can process the input
        """
        pass

    def calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file for deduplication.

        Args:
            file_path: Path to the file

        Returns:
            Hex string of the SHA-256 hash
        """
        return calculate_file_hash(file_path)

    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of text content for deduplication.

        Args:
            content: Text content to hash

        Returns:
            Hex string of the SHA-256 hash
        """
        return _calculate_content_hash(content)

    async def check_duplicate(self, file_hash: str) -> Optional[UnifiedContent]:
        """
        Check if content with this hash already exists.

        Args:
            file_hash: SHA-256 hash to check

        Returns:
            Existing UnifiedContent if found, None otherwise

        Note:
            This method should be implemented to query the database.
            For now, it returns None (no duplicate checking).
        """
        # TODO: Implement database query for duplicate checking
        # This requires async database access
        self.logger.debug(f"Checking for duplicate with hash: {file_hash[:16]}...")
        return None

    def validate_file(self, file_path: Path, max_size_mb: int = 50) -> bool:
        """
        Validate that a file exists and is within size limits.

        Args:
            file_path: Path to the file
            max_size_mb: Maximum file size in megabytes

        Returns:
            True if file is valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file exceeds size limit
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(
                f"File size {size_mb:.1f}MB exceeds limit of {max_size_mb}MB"
            )

        return True


class PipelineRegistry:
    """
    Registry for managing multiple pipelines.

    Automatically routes content to the appropriate pipeline based on
    the supports() method of each registered pipeline.

    Routing Key:
        The routing key is (file_format, content_type), NOT just file extension.
        This allows different pipelines to handle the same file format based
        on the content type context provided in PipelineInput.

    Example:
        >>> registry = PipelineRegistry()
        >>> registry.register(PDFProcessor())       # Handles PDF content type
        >>> registry.register(BookOCRPipeline())    # Handles BOOK content type
        >>> registry.register(VoiceTranscriber())   # Handles VOICE_MEMO content type
        >>>
        >>> # Route based on content type
        >>> input_data = PipelineInput(
        ...     path=Path("page.jpg"),
        ...     content_type=PipelineContentType.BOOK,
        ... )
        >>> content = await registry.process(input_data)  # Uses BookOCRPipeline
    """

    def __init__(self) -> None:
        self._pipelines: list[BasePipeline] = []
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def register(self, pipeline: BasePipeline) -> None:
        """
        Register a pipeline.

        Args:
            pipeline: The pipeline instance to register
        """
        self._pipelines.append(pipeline)
        self.logger.info(
            f"Registered pipeline: {pipeline.__class__.__name__} "
            f"(content types: {pipeline.SUPPORTED_CONTENT_TYPES})"
        )

    def get_pipeline(self, input_data: PipelineInput) -> Optional[BasePipeline]:
        """
        Get the appropriate pipeline for the input.

        Returns the FIRST registered pipeline whose supports() method returns True
        for the given PipelineInput.

        Args:
            input_data: PipelineInput with content type context

        Returns:
            First pipeline that can handle the input, or None if no match
        """
        for pipeline in self._pipelines:
            if pipeline.supports(input_data):
                return pipeline
        return None

    async def process(self, input_data: PipelineInput) -> Optional[UnifiedContent]:
        """
        Process input using the appropriate pipeline.

        Args:
            input_data: PipelineInput to process

        Returns:
            UnifiedContent if a pipeline was found, None otherwise
        """
        pipeline = self.get_pipeline(input_data)
        if pipeline:
            self.logger.info(
                f"Routing {input_data.content_type.value} to {pipeline.__class__.__name__}"
            )
            return await pipeline.process(input_data)

        self.logger.warning(
            f"No pipeline found for content type: {input_data.content_type}"
        )
        return None

    def list_pipelines(self) -> list[dict[str, Any]]:
        """
        List all registered pipelines and their supported content types.

        Returns:
            List of dicts with 'name' (str) and 'content_types' (list[str]) keys
        """
        return [
            {
                "name": p.__class__.__name__,
                "content_types": [ct.value for ct in p.SUPPORTED_CONTENT_TYPES],
            }
            for p in self._pipelines
        ]
