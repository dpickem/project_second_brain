"""
Unit Tests for Ingestion Pipelines

Tests the base pipeline and specific pipeline implementations.
These are fast, isolated unit tests that do not require external services.

Test Organization
-----------------
Pipeline tests are split between unit and integration:

**Unit Tests (this file):**
- Test pipeline logic in isolation with no external dependencies
- No database, no network, no file I/O (except temp files)
- Test: supports(), format validation, helper methods, parsing logic
- Run fast, suitable for CI on every commit

**Integration Tests (tests/integration/test_pipelines.py):**
- Test full pipeline flow with real test files from test_data/
- Mock external APIs (LLM, OCR, GitHub, Raindrop, Jina Reader)
- Test: process() end-to-end, file hashing, content extraction
- Still isolated from production - see safety guarantees below

Database Safety Guarantees
--------------------------
NEITHER unit nor integration pipeline tests write to any database:

1. **Unit tests**: No database interaction at all - pure logic testing

2. **Integration tests**: Multiple layers of protection:
   - `mock_cost_tracker` autouse fixture: Patches CostTracker.log_usages_batch
     and CostTracker.log_usage for ALL tests
   - `mock_task_session_maker` autouse fixture: Patches the database session
     factory to prevent any connections
   - `track_costs=False` parameter: Pipelines instantiated with cost tracking off
   - All external API calls (LLM, OCR, HTTP) are mocked

3. **What CostTracker does**: It logs LLM usage/costs to PostgreSQL via
   task_session_maker(). The integration tests mock this at multiple levels
   to ensure no database writes occur.

Pipelines Covered
-----------------
- BasePipeline: Abstract base class with shared utilities
- PipelineRegistry: Routes content to appropriate pipeline
- PDFProcessor: PDF text extraction via OCR
- VoiceTranscriber: Audio transcription via Whisper
- BookOCRPipeline: Book page photos via Vision LLM
- WebArticlePipeline: Article extraction via Jina/trafilatura
- GitHubImporter: Repository analysis via GitHub API
- RaindropSync: Bookmark sync via Raindrop.io API

Running Tests
-------------
Unit tests only (fast):
    pytest tests/unit/test_pipelines.py -v

Integration tests only:
    pytest tests/integration/test_pipelines.py -v

All pipeline tests:
    pytest tests/unit/test_pipelines.py tests/integration/test_pipelines.py -v
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from app.models.content import (
    ContentType,
    UnifiedContent,
)
from app.pipelines.utils.cost_types import LLMUsage
from app.pipelines.base import (
    BasePipeline,
    PipelineRegistry,
    PipelineInput,
    PipelineContentType,
)
from app.pipelines.pdf_processor import PDFProcessor
from app.pipelines.voice_transcribe import VoiceTranscriber
from app.pipelines.book_ocr import BookOCRPipeline, ChapterInfo


class DummyPipeline(BasePipeline):
    """Concrete implementation of BasePipeline for testing."""

    SUPPORTED_CONTENT_TYPES = {PipelineContentType.IDEA}

    def supports(self, input_data: PipelineInput) -> bool:
        if not isinstance(input_data, PipelineInput):
            return False
        if input_data.content_type != PipelineContentType.IDEA:
            return False
        if input_data.text:
            return input_data.text.endswith(".dummy")
        return False

    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        return UnifiedContent(
            source_type=ContentType.IDEA,
            title=f"Processed: {input_data.text}",
            full_text="Dummy content",
        )


class TestBasePipeline:
    """Tests for the BasePipeline abstract class."""

    def test_calculate_hash(self):
        """Test file hash calculation."""
        pipeline = DummyPipeline()

        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            hash1 = pipeline.calculate_hash(temp_path)
            hash2 = pipeline.calculate_hash(temp_path)

            # Same file should produce same hash
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex length
        finally:
            temp_path.unlink()

    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        pipeline = DummyPipeline()

        hash1 = pipeline.calculate_content_hash("test content")
        hash2 = pipeline.calculate_content_hash("test content")
        hash3 = pipeline.calculate_content_hash("different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64

    def test_validate_file_exists(self):
        """Test file validation for existing file."""
        pipeline = DummyPipeline()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)

        try:
            assert pipeline.validate_file(temp_path) is True
        finally:
            temp_path.unlink()

    def test_validate_file_not_exists(self):
        """Test file validation for non-existing file."""
        pipeline = DummyPipeline()

        with pytest.raises(FileNotFoundError):
            pipeline.validate_file(Path("/nonexistent/file.txt"))

    def test_validate_file_size_limit(self):
        """Test file validation for size limits."""
        pipeline = DummyPipeline()

        # Create a file larger than limit
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * (2 * 1024 * 1024))  # 2 MB
            temp_path = Path(f.name)

        try:
            # Should fail with 1 MB limit
            with pytest.raises(ValueError, match="exceeds limit"):
                pipeline.validate_file(temp_path, max_size_mb=1)

            # Should pass with 5 MB limit
            assert pipeline.validate_file(temp_path, max_size_mb=5) is True
        finally:
            temp_path.unlink()

    def test_supports(self):
        """Test the supports method."""
        pipeline = DummyPipeline()

        # With PipelineInput and correct content type
        dummy_input = PipelineInput(
            text="test.dummy", content_type=PipelineContentType.IDEA
        )
        assert pipeline.supports(dummy_input) is True

        # Wrong text ending
        pdf_input = PipelineInput(
            text="test.pdf", content_type=PipelineContentType.IDEA
        )
        assert pipeline.supports(pdf_input) is False

        # Wrong content type
        wrong_type_input = PipelineInput(
            text="test.dummy", content_type=PipelineContentType.PDF
        )
        assert pipeline.supports(wrong_type_input) is False

    @pytest.mark.asyncio
    async def test_process(self):
        """Test the process method."""
        pipeline = DummyPipeline()

        input_data = PipelineInput(
            text="test.dummy", content_type=PipelineContentType.IDEA
        )
        result = await pipeline.process(input_data)

        assert isinstance(result, UnifiedContent)
        assert result.source_type == ContentType.IDEA
        assert "test.dummy" in result.title


class TestPipelineRegistry:
    """Tests for the PipelineRegistry."""

    def test_register_pipeline(self):
        """Test registering a pipeline."""
        registry = PipelineRegistry()
        pipeline = DummyPipeline()

        registry.register(pipeline)

        assert pipeline in registry._pipelines

    def test_get_pipeline(self):
        """Test getting appropriate pipeline for input."""
        registry = PipelineRegistry()
        pipeline = DummyPipeline()
        registry.register(pipeline)

        # Should find pipeline for .dummy files with correct content type
        dummy_input = PipelineInput(
            text="test.dummy", content_type=PipelineContentType.IDEA
        )
        found = registry.get_pipeline(dummy_input)
        assert found is pipeline

        # Should not find pipeline for wrong content type
        pdf_input = PipelineInput(text="test.pdf", content_type=PipelineContentType.PDF)
        not_found = registry.get_pipeline(pdf_input)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_process_through_registry(self):
        """Test processing input through registry."""
        registry = PipelineRegistry()
        registry.register(DummyPipeline())

        # Process supported input
        dummy_input = PipelineInput(
            text="test.dummy", content_type=PipelineContentType.IDEA
        )
        result = await registry.process(dummy_input)
        assert isinstance(result, UnifiedContent)

        # Process unsupported input
        pdf_input = PipelineInput(text="test.pdf", content_type=PipelineContentType.PDF)
        result = await registry.process(pdf_input)
        assert result is None


class TestPDFProcessor:
    """Tests for the PDF processor pipeline."""

    @pytest.fixture
    def pdf_processor(self):
        """Create a PDF processor instance."""
        return PDFProcessor()

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client for content type inference tests."""
        mock_client = AsyncMock()

        async def mock_complete(**kwargs):
            # Return appropriate content type based on test context
            return "paper", LLMUsage(
                model="test-model",
                provider="test",
                request_type="completion",
                prompt_tokens=100,
                completion_tokens=10,
                total_tokens=110,
                cost_usd=0.001,
                latency_ms=100,
            )

        mock_client.complete = mock_complete
        return mock_client

    def test_supports_pdf(self, pdf_processor):
        """Test that processor supports PDF files."""
        # Supported: PDF with correct content type
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.PDF
        )
        assert pdf_processor.supports(pdf_input) is True

        # Also works with uppercase extension (case insensitive)
        pdf_upper = PipelineInput(
            path=Path("test.PDF"), content_type=PipelineContentType.PDF
        )
        assert pdf_processor.supports(pdf_upper) is True

        # Unsupported: wrong file extension
        txt_input = PipelineInput(
            path=Path("test.txt"), content_type=PipelineContentType.PDF
        )
        assert pdf_processor.supports(txt_input) is False

        # Unsupported: wrong content type
        wrong_type = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.BOOK
        )
        assert pdf_processor.supports(wrong_type) is False

    @pytest.mark.asyncio
    async def test_infer_content_type_paper(self, pdf_processor):
        """Test content type inference for papers."""

        title = "Machine Learning Paper"
        text = """
        Abstract
        This paper presents a new approach...
        Introduction
        Related work...
        Methodology
        References
        [1] Some reference
        """

        # Mock the LLM client to return "paper"
        mock_client = AsyncMock()
        async def mock_complete(**kwargs):
            return "paper", LLMUsage(
                model="test-model", provider="test", request_type="completion",
                prompt_tokens=100, completion_tokens=10, total_tokens=110,
                cost_usd=0.001, latency_ms=100,
            )
        mock_client.complete = mock_complete

        with patch("app.pipelines.pdf_processor.get_llm_client", return_value=mock_client):
            content_type = await pdf_processor._infer_content_type(title, text)
            assert content_type == ContentType.PAPER

    @pytest.mark.asyncio
    async def test_infer_content_type_book(self, pdf_processor):
        """Test content type inference for books."""
        title = "Programming Guide"
        text = """
        Table of Contents
        Chapter 1: Introduction
        Chapter 2: Getting Started
        Preface
        """

        # Mock the LLM client to return "book"
        mock_client = AsyncMock()
        async def mock_complete(**kwargs):
            return "book", LLMUsage(
                model="test-model", provider="test", request_type="completion",
                prompt_tokens=100, completion_tokens=10, total_tokens=110,
                cost_usd=0.001, latency_ms=100,
            )
        mock_client.complete = mock_complete

        with patch("app.pipelines.pdf_processor.get_llm_client", return_value=mock_client):
            content_type = await pdf_processor._infer_content_type(title, text)
            assert content_type == ContentType.BOOK


class TestVoiceTranscriber:
    """Tests for the voice transcription pipeline."""

    @pytest.fixture
    def voice_transcriber(self):
        """Create a voice transcriber instance."""
        return VoiceTranscriber()

    def test_supports_audio_formats(self, voice_transcriber):
        """Test that transcriber supports common audio formats."""
        # Supported formats with correct content type
        mp3_input = PipelineInput(
            path=Path("test.mp3"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert voice_transcriber.supports(mp3_input) is True

        wav_input = PipelineInput(
            path=Path("test.wav"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert voice_transcriber.supports(wav_input) is True

        m4a_input = PipelineInput(
            path=Path("test.m4a"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert voice_transcriber.supports(m4a_input) is True

        webm_input = PipelineInput(
            path=Path("test.webm"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert voice_transcriber.supports(webm_input) is True

        # Unsupported format
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert voice_transcriber.supports(pdf_input) is False

    def test_format_duration(self, voice_transcriber):
        """Test duration formatting from seconds."""
        # Short duration (under 1 minute)
        short = voice_transcriber._format_duration(45)
        assert short == "0:45"

        # Medium duration (minutes)
        medium = voice_transcriber._format_duration(125)
        assert medium == "2:05"

        # Long duration (over an hour)
        long = voice_transcriber._format_duration(3725)
        assert long == "1:02:05"

        # None returns unknown
        unknown = voice_transcriber._format_duration(None)
        assert unknown == "unknown"


class TestBookOCRPipeline:
    """Tests for the book OCR pipeline."""

    @pytest.fixture
    def book_pipeline(self):
        """Create a book OCR pipeline instance."""
        return BookOCRPipeline()

    def test_supports_image_formats(self, book_pipeline):
        """Test that pipeline supports image formats."""
        # Test that SUPPORTED_FORMATS contains expected image types
        assert ".jpg" in book_pipeline.SUPPORTED_FORMATS
        assert ".jpeg" in book_pipeline.SUPPORTED_FORMATS
        assert ".png" in book_pipeline.SUPPORTED_FORMATS
        assert ".heic" in book_pipeline.SUPPORTED_FORMATS
        assert ".pdf" not in book_pipeline.SUPPORTED_FORMATS

        # Test content type filtering
        book_input = PipelineInput(
            path=Path("page.jpg"), content_type=PipelineContentType.BOOK
        )
        pdf_content_input = PipelineInput(
            path=Path("page.jpg"), content_type=PipelineContentType.PDF
        )

        # Correct content type should be supported (non-existent paths treated as directories)
        assert book_pipeline.supports(book_input) is True

        # Wrong content type should not be supported
        assert book_pipeline.supports(pdf_content_input) is False

    def test_build_page_label(self, book_pipeline):
        """Test page label building."""
        # Page with number and chapter
        chapter = ChapterInfo(number="5", title="Memory")
        label = book_pipeline._build_page_label(
            page_num=42,
            chapter=chapter,
            source_image="page.jpg",
        )
        assert "Page 42" in label
        assert "Ch. 5" in label
        assert "Memory" in label

        # Page with number only
        label2 = book_pipeline._build_page_label(
            page_num=10, chapter=None, source_image="page.jpg"
        )
        assert label2 == "Page 10"

        # Page without number
        label3 = book_pipeline._build_page_label(
            page_num=None, chapter=None, source_image="page.jpg"
        )
        assert "page.jpg" in label3
