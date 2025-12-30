"""
Unit tests for ingestion pipelines.

Tests the base pipeline and specific pipeline implementations.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from app.models.content import (
    ContentType,
    AnnotationType,
    UnifiedContent,
)
from app.pipelines.base import BasePipeline, PipelineRegistry


class DummyPipeline(BasePipeline):
    """Concrete implementation of BasePipeline for testing."""

    def supports(self, input_data) -> bool:
        return isinstance(input_data, str) and input_data.endswith(".dummy")

    async def process(self, input_data) -> UnifiedContent:
        return UnifiedContent(
            source_type=ContentType.IDEA,
            title=f"Processed: {input_data}",
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

        assert pipeline.supports("test.dummy") is True
        assert pipeline.supports("test.pdf") is False
        assert pipeline.supports(123) is False

    @pytest.mark.asyncio
    async def test_process(self):
        """Test the process method."""
        pipeline = DummyPipeline()

        result = await pipeline.process("test.dummy")

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

        # Should find pipeline for .dummy files
        found = registry.get_pipeline("test.dummy")
        assert found is pipeline

        # Should not find pipeline for .pdf files
        not_found = registry.get_pipeline("test.pdf")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_process_through_registry(self):
        """Test processing input through registry."""
        registry = PipelineRegistry()
        registry.register(DummyPipeline())

        # Process supported input
        result = await registry.process("test.dummy")
        assert isinstance(result, UnifiedContent)

        # Process unsupported input
        result = await registry.process("test.pdf")
        assert result is None


class TestPDFProcessor:
    """Tests for the PDF processor pipeline."""

    @pytest.fixture
    def pdf_processor(self):
        """Create a PDF processor instance."""
        from app.pipelines.pdf_processor import PDFProcessor

        return PDFProcessor(
            enable_handwriting_detection=False,  # Disable for unit tests
        )

    def test_supports_pdf(self, pdf_processor):
        """Test that processor supports PDF files."""
        assert pdf_processor.supports(Path("test.pdf")) is True
        assert pdf_processor.supports(Path("test.PDF")) is True
        assert pdf_processor.supports(Path("test.txt")) is False
        assert pdf_processor.supports("test.pdf") is True

    def test_infer_content_type_paper(self, pdf_processor):
        """Test content type inference for papers."""
        metadata = {"title": "Machine Learning Paper"}
        text = """
        Abstract
        This paper presents a new approach...
        Introduction
        Related work...
        Methodology
        References
        [1] Some reference
        """

        content_type = pdf_processor._infer_content_type(metadata, text)
        assert content_type == ContentType.PAPER

    def test_infer_content_type_book(self, pdf_processor):
        """Test content type inference for books."""
        metadata = {"title": "Programming Guide"}
        text = """
        Table of Contents
        Chapter 1: Introduction
        Chapter 2: Getting Started
        Preface
        """

        content_type = pdf_processor._infer_content_type(metadata, text)
        assert content_type == ContentType.BOOK


class TestVoiceTranscriber:
    """Tests for the voice transcription pipeline."""

    @pytest.fixture
    def voice_transcriber(self):
        """Create a voice transcriber instance."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        return VoiceTranscriber()

    def test_supports_audio_formats(self, voice_transcriber):
        """Test that transcriber supports common audio formats."""
        assert voice_transcriber.supports(Path("test.mp3")) is True
        assert voice_transcriber.supports(Path("test.wav")) is True
        assert voice_transcriber.supports(Path("test.m4a")) is True
        assert voice_transcriber.supports(Path("test.webm")) is True
        assert voice_transcriber.supports(Path("test.pdf")) is False

    def test_generate_title(self, voice_transcriber):
        """Test title generation from content."""
        content = "# Important Meeting Notes\n\nDiscussed project timeline..."
        title = voice_transcriber._generate_title(content)
        assert title == "Important Meeting Notes"

        # Test with plain text
        content2 = "Quick idea about the new feature"
        title2 = voice_transcriber._generate_title(content2)
        assert title2 == "Quick idea about the new feature"

    def test_estimate_duration(self, voice_transcriber):
        """Test duration estimation from transcript length."""
        # Short memo
        short = voice_transcriber._estimate_duration(100)
        assert "minute" in short

        # Longer memo
        long = voice_transcriber._estimate_duration(5000)
        assert "minutes" in long


class TestBookOCRPipeline:
    """Tests for the book OCR pipeline."""

    @pytest.fixture
    def book_pipeline(self):
        """Create a book OCR pipeline instance."""
        from app.pipelines.book_ocr import BookOCRPipeline

        return BookOCRPipeline()

    def test_supports_image_formats(self, book_pipeline):
        """Test that pipeline supports image formats."""
        assert book_pipeline.supports([Path("page.jpg")]) is True
        assert book_pipeline.supports([Path("page.png")]) is True
        assert book_pipeline.supports([Path("page.heic")]) is True
        assert book_pipeline.supports([Path("page.pdf")]) is False

    def test_build_page_label(self, book_pipeline):
        """Test page label building."""
        # Page with number and chapter
        label = book_pipeline._build_page_label(
            page_num=42,
            chapter={"number": "5", "title": "Memory"},
            result={"source_image": "page.jpg"},
        )
        assert "Page 42" in label
        assert "Ch. 5" in label
        assert "Memory" in label

        # Page with number only
        label2 = book_pipeline._build_page_label(
            page_num=10, chapter=None, result={"source_image": "page.jpg"}
        )
        assert label2 == "Page 10"

        # Page without number
        label3 = book_pipeline._build_page_label(
            page_num=None, chapter=None, result={"source_image": "page.jpg"}
        )
        assert "page.jpg" in label3
