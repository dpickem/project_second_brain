"""
Ingestion Pipelines Package

This package contains all content ingestion pipelines that convert diverse
source formats into the Unified Content Format (UCF).

Pipelines (via registry):
- PDFProcessor: Extract text, highlights, and handwritten annotations from PDFs
- BookOCRPipeline: OCR book photos with margin notes
- VoiceTranscriber: Transcribe voice memos using Whisper
- WebArticlePipeline: Extract content from web article URLs
- GitHubImporter: Analyze and import GitHub repositories (requires token)

Batch Sync Pipelines (not via registry):
- RaindropSync: Sync bookmarks and highlights from Raindrop.io (use directly)

Core Types:
- PipelineInput: Wrapper for pipeline input with content type context
- PipelineContentType: Enum for routing inputs to correct pipeline
- PipelineRegistry: Registry for routing inputs to pipelines

Usage:
    from app.pipelines import (
        PipelineInput, PipelineContentType,
        get_registry,  # Use this for the pre-configured registry
    )

    # Get the default registry (singleton, lazily initialized)
    registry = get_registry()

    input_data = PipelineInput(
        path=Path("paper.pdf"),
        content_type=PipelineContentType.PDF,
    )
    content = await registry.process(input_data)

    # Direct pipeline usage (bypasses registry)
    from app.pipelines import PDFProcessor
    processor = PDFProcessor()
    content = await processor.process_path(Path("paper.pdf"))

    # Batch sync (not via registry)
    from app.pipelines import RaindropSync
    sync = RaindropSync(access_token="...")
    items = await sync.sync_collection(since=datetime.now() - timedelta(days=1))
"""

from typing import Optional

from app.pipelines.base import (
    BasePipeline,
    PipelineContentType,
    PipelineInput,
    PipelineRegistry,
)
from app.pipelines.pdf_processor import PDFProcessor
from app.pipelines.book_ocr import BookOCRPipeline
from app.pipelines.voice_transcribe import VoiceTranscriber
from app.pipelines.web_article import WebArticlePipeline
from app.pipelines.github_importer import GitHubImporter
from app.pipelines.raindrop_sync import RaindropSync

__all__ = [
    # Core types
    "BasePipeline",
    "PipelineContentType",
    "PipelineInput",
    "PipelineRegistry",
    # Registry access
    "get_registry",
    "reset_registry",
    # Pipelines (via registry)
    "PDFProcessor",
    "BookOCRPipeline",
    "VoiceTranscriber",
    "WebArticlePipeline",
    "GitHubImporter",
    # Batch sync pipelines (not via registry)
    "RaindropSync",
]

# Singleton registry instance
_registry: Optional[PipelineRegistry] = None


def get_registry() -> PipelineRegistry:
    """
    Get the default pipeline registry (singleton).

    The registry is lazily initialized on first access and configured with
    all available pipelines using settings from app.config.

    Returns:
        Pre-configured PipelineRegistry with all pipelines registered.

    Usage:
        from app.pipelines import get_registry, PipelineInput, PipelineContentType

        registry = get_registry()
        input_data = PipelineInput(
            path=Path("paper.pdf"),
            content_type=PipelineContentType.PDF,
        )
        content = await registry.process(input_data)
    """
    global _registry

    if _registry is None:
        _registry = _create_registry()

    return _registry


def _create_registry() -> PipelineRegistry:
    """
    Create and configure a new pipeline registry.

    Registers all available pipelines with appropriate configuration
    from app.config.settings.

    Note: RaindropSync is NOT registered here because it's designed for
    batch sync operations via sync_collection(), not single-item processing.
    Use RaindropSync directly for Raindrop.io bookmark sync.
    """
    from app.config import settings

    registry = PipelineRegistry()

    # File-based pipelines (no external API tokens needed)
    registry.register(PDFProcessor())
    registry.register(BookOCRPipeline())
    registry.register(VoiceTranscriber())

    # URL-based pipelines
    registry.register(WebArticlePipeline())  # Generic article extraction

    # GitHub importer (requires API token)
    if settings.GITHUB_ACCESS_TOKEN:
        registry.register(GitHubImporter(access_token=settings.GITHUB_ACCESS_TOKEN))

    return registry


def reset_registry() -> None:
    """
    Reset the singleton registry (useful for testing).

    The next call to get_registry() will create a fresh instance.
    """
    global _registry
    _registry = None
