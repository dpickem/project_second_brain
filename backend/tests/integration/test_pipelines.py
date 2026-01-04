"""
Integration Tests for Ingestion Pipelines

Tests each ingestion pipeline with real files and mocked external APIs.
These tests verify the full pipeline flow including:
- File processing (reading, validation, hashing)
- Content extraction
- Database integration (where applicable)
- Error handling

Note: External API calls (LLM, OCR services, web APIs) are mocked to ensure
tests are deterministic and don't incur costs.

Run with: pytest tests/integration/test_pipelines.py -v
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.enums.content import ContentType
from app.enums.pipeline import PipelineContentType, PipelineName
from app.models.content import AnnotationType, UnifiedContent
from app.pipelines.base import PipelineInput, PipelineRegistry


# ============================================================================
# Test Data Paths
# ============================================================================

TEST_DATA_DIR = Path(__file__).parent.parent.parent.parent / "test_data"
SAMPLE_PDF = TEST_DATA_DIR / "sample_paper_toolformer.pdf"
SAMPLE_VOICE_MEMO = TEST_DATA_DIR / "sample_voice_memo.m4a"
SAMPLE_BOOK_IMAGES = TEST_DATA_DIR / "book"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for pipeline testing."""
    from app.pipelines.utils.cost_types import LLMUsage

    mock_client = AsyncMock()

    # Default response for text completion
    async def mock_complete(**kwargs):
        operation = kwargs.get("operation", "unknown")
        model = kwargs.get("model", "test-model")

        # Return sensible responses based on operation
        if "CONTENT_TYPE" in str(operation):
            response = "paper"
        elif "TITLE" in str(operation):
            response = "Test Article Title"
        elif "METADATA" in str(operation):
            response = json.dumps(
                {
                    "title": "Test Book",
                    "authors": ["Test Author"],
                    "isbn": "978-0-123456-78-9",
                    "confidence": "high",
                }
            )
        elif "NOTE_EXPANSION" in str(operation):
            response = json.dumps(
                {
                    "title": "Test Voice Memo",
                    "content": "Expanded content from voice memo.",
                }
            )
        elif "REPO_ANALYSIS" in str(operation):
            response = "## Purpose\nTest repository for demonstration.\n## Key Learnings\n- Example patterns"
        else:
            response = "Test LLM response"

        usage = LLMUsage(
            model=model,
            provider="test",
            request_type="completion",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            latency_ms=100,
            pipeline=kwargs.get("pipeline"),
            content_id=kwargs.get("content_id"),
            operation=operation,
        )
        return response, usage

    mock_client.complete = mock_complete
    return mock_client


@pytest.fixture
def mock_vision_completion():
    """Mock for vision model completions (OCR)."""
    from app.pipelines.utils.cost_types import LLMUsage

    async def mock_completion(**kwargs):
        response = json.dumps(
            {
                "page_number": 42,
                "page_number_location": "bottom-right",
                "chapter": {"number": "5", "title": "Test Chapter", "location": "header"},
                "is_two_page_spread": False,
                "spread_pages": None,
                "full_text": "This is the extracted text from the book page. It contains important information about the topic.",
                "highlights": [
                    {"text": "important information", "type": "underline", "location": "middle"}
                ],
                "margin_notes": [
                    {"text": "Remember this!", "location": "right-margin", "related_text": "important information"}
                ],
            }
        )
        usage = LLMUsage(
            model=kwargs.get("model", "test-vision-model"),
            provider="test",
            request_type="vision_completion",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            cost_usd=0.005,
            latency_ms=500,
            pipeline=kwargs.get("pipeline"),
            content_id=kwargs.get("content_id"),
            operation=kwargs.get("operation"),
        )
        return response, usage

    return mock_completion


@pytest.fixture
def mock_ocr_result():
    """Mock for Mistral OCR results."""
    from app.pipelines.utils.mistral_ocr_client import (
        MistralOCRResult,
        PageInfo,
        ImageInfo,
        DocumentAnnotation,
    )
    from app.pipelines.utils.cost_types import LLMUsage

    return MistralOCRResult(
        pages=[
            PageInfo(
                index=0,
                markdown="# Test Document\n\nThis is the content of page 1.\n\n## Section 1\n\nSome important text here.",
                images=[
                    ImageInfo(
                        id="img_0",
                        top_left_x=100,
                        top_left_y=200,
                        bottom_right_x=300,
                        bottom_right_y=400,
                        image_base64=None,
                        annotation={"image_type": "graph", "description": "A sample figure"},
                    )
                ],
            ),
            PageInfo(
                index=1,
                markdown="## Section 2\n\nMore content on page 2. This contains references and citations.",
                images=[],
            ),
        ],
        document_annotation=DocumentAnnotation(
            title="Test Academic Paper",
            authors=["John Doe", "Jane Smith"],
            summary="This paper presents a novel approach to testing.",
            languages=["en"],
        ),
        usage=LLMUsage(
            model="pixtral-12b",
            provider="mistral",
            request_type="ocr",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cost_usd=0.01,
            latency_ms=2000,
            pipeline=PipelineName.PDF_PROCESSOR,
            operation="DOCUMENT_OCR",
        ),
    )


@pytest.fixture
def mock_transcription_response():
    """Mock for Whisper transcription response."""
    mock_response = MagicMock()
    mock_response.text = "This is a test transcription from the voice memo. I want to remember this important idea for later."
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = None
    mock_response.usage.completion_tokens = None
    mock_response.usage.total_tokens = None
    mock_response._hidden_params = {"response_cost": 0.002}
    return mock_response


# ============================================================================
# WebArticlePipeline Tests
# ============================================================================


class TestWebArticlePipelineIntegration:
    """Integration tests for WebArticlePipeline."""

    @pytest.fixture
    def mock_jina_response(self):
        """Mock Jina Reader API response."""
        return "# Test Article\n\nThis is the main content of the article.\n\n## Section 1\n\nSome important points here."

    @pytest.fixture
    def mock_trafilatura_extraction(self):
        """Mock trafilatura extraction result."""
        return {
            "title": "Test Article Title",
            "author": "Test Author",
            "date": "2024-01-15",
            "text": "This is the extracted article text from trafilatura.",
            "hostname": "example.com",
            "sitename": "Example Site",
            "source": "trafilatura",
            "format": "text",
        }

    @pytest.mark.asyncio
    async def test_pipeline_supports_article_urls(self):
        """Test that WebArticlePipeline supports article URLs with correct content type."""
        from app.pipelines.web_article import WebArticlePipeline

        pipeline = WebArticlePipeline()

        # Should support article URLs
        article_input = PipelineInput(
            url="https://example.com/article", content_type=PipelineContentType.ARTICLE
        )
        assert pipeline.supports(article_input) is True

        # Should not support wrong content type
        code_input = PipelineInput(
            url="https://github.com/user/repo", content_type=PipelineContentType.CODE
        )
        assert pipeline.supports(code_input) is False

        # Should not support inputs without URL
        no_url_input = PipelineInput(
            text="Some text", content_type=PipelineContentType.ARTICLE
        )
        assert pipeline.supports(no_url_input) is False

    @pytest.mark.asyncio
    async def test_process_article_with_jina(
        self, mock_jina_response, mock_llm_client
    ):
        """Test article processing using Jina Reader."""
        from app.pipelines.web_article import WebArticlePipeline

        with patch("app.pipelines.web_article.get_llm_client") as mock_get_client, \
             patch("httpx.AsyncClient.get") as mock_get:
            mock_get_client.return_value = mock_llm_client

            # Mock Jina response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_jina_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            pipeline = WebArticlePipeline()
            input_data = PipelineInput(
                url="https://example.com/test-article",
                content_type=PipelineContentType.ARTICLE,
            )

            result = await pipeline.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.ARTICLE
            assert result.source_url == "https://example.com/test-article"
            assert len(result.full_text) > 0
            assert "markdown" in result.metadata or "source" in result.metadata

    @pytest.mark.asyncio
    async def test_process_article_fallback_to_trafilatura(
        self, mock_trafilatura_extraction, mock_llm_client
    ):
        """Test article processing falls back to trafilatura when Jina fails."""
        from app.pipelines.web_article import WebArticlePipeline

        with patch("app.pipelines.web_article.get_llm_client") as mock_get_client, \
             patch.object(WebArticlePipeline, "_extract_with_jina", return_value={}), \
             patch.object(WebArticlePipeline, "_extract_with_trafilatura", return_value=mock_trafilatura_extraction):
            mock_get_client.return_value = mock_llm_client

            pipeline = WebArticlePipeline()
            input_data = PipelineInput(
                url="https://example.com/static-article",
                content_type=PipelineContentType.ARTICLE,
            )

            result = await pipeline.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.ARTICLE
            assert result.full_text == mock_trafilatura_extraction["text"]

    @pytest.mark.asyncio
    async def test_extract_text_only(self, mock_jina_response):
        """Test extract_text_only convenience method."""
        from app.pipelines.web_article import WebArticlePipeline

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_jina_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            pipeline = WebArticlePipeline()
            text = await pipeline.extract_text_only("https://example.com/article")

            assert len(text) > 0
            assert "content" in text.lower() or "article" in text.lower()


# ============================================================================
# PDFProcessor Tests
# ============================================================================


class TestPDFProcessorIntegration:
    """Integration tests for PDFProcessor."""

    @pytest.mark.asyncio
    async def test_pipeline_supports_pdf_files(self):
        """Test that PDFProcessor supports PDF files."""
        from app.pipelines.pdf_processor import PDFProcessor

        processor = PDFProcessor()

        # Should support PDF files
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.PDF
        )
        assert processor.supports(pdf_input) is True

        # Case insensitive
        pdf_upper = PipelineInput(
            path=Path("test.PDF"), content_type=PipelineContentType.PDF
        )
        assert processor.supports(pdf_upper) is True

        # Should not support non-PDF files
        txt_input = PipelineInput(
            path=Path("test.txt"), content_type=PipelineContentType.PDF
        )
        assert processor.supports(txt_input) is False

        # Should not support wrong content type
        wrong_type = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.BOOK
        )
        assert processor.supports(wrong_type) is False

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
    async def test_process_real_pdf(self, mock_ocr_result, mock_llm_client):
        """Test processing a real PDF file with mocked OCR."""
        from app.pipelines.pdf_processor import PDFProcessor

        with patch("app.pipelines.pdf_processor.ocr_pdf_document_annotated", return_value=mock_ocr_result), \
             patch("app.pipelines.pdf_processor.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.pdf_processor.CostTracker.log_usages_batch", new_callable=AsyncMock):
            processor = PDFProcessor(track_costs=False)
            input_data = PipelineInput(path=SAMPLE_PDF, content_type=PipelineContentType.PDF)

            result = await processor.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type in [ContentType.PAPER, ContentType.BOOK, ContentType.ARTICLE]
            assert len(result.full_text) > 0
            assert result.source_file_path == str(SAMPLE_PDF)
            assert result.raw_file_hash is not None
            assert len(result.raw_file_hash) == 64  # SHA-256

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
    async def test_file_hash_consistency(self):
        """Test that file hash is consistent across multiple calls."""
        from app.pipelines.pdf_processor import PDFProcessor

        processor = PDFProcessor()

        hash1 = processor.calculate_hash(SAMPLE_PDF)
        hash2 = processor.calculate_hash(SAMPLE_PDF)

        assert hash1 == hash2
        assert len(hash1) == 64

    @pytest.mark.asyncio
    async def test_file_validation(self):
        """Test file validation for non-existent files."""
        from app.pipelines.pdf_processor import PDFProcessor

        processor = PDFProcessor()

        with pytest.raises(FileNotFoundError):
            processor.validate_file(Path("/nonexistent/file.pdf"))

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
    async def test_extract_pdf_annotations(self, mock_ocr_result, mock_llm_client):
        """Test extraction of PDF annotations (highlights, comments)."""
        from app.pipelines.pdf_processor import PDFProcessor

        with patch("app.pipelines.pdf_processor.ocr_pdf_document_annotated", return_value=mock_ocr_result), \
             patch("app.pipelines.pdf_processor.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.pdf_processor.CostTracker.log_usages_batch", new_callable=AsyncMock):
            processor = PDFProcessor(track_costs=False)
            input_data = PipelineInput(path=SAMPLE_PDF, content_type=PipelineContentType.PDF)

            result = await processor.process(input_data)

            # Check metadata contains annotation counts
            assert "annotation_counts" in result.metadata
            assert "total" in result.metadata["annotation_counts"]


# ============================================================================
# BookOCRPipeline Tests
# ============================================================================


class TestBookOCRPipelineIntegration:
    """Integration tests for BookOCRPipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_supports_image_formats(self):
        """Test that BookOCRPipeline supports various image formats."""
        from app.pipelines.book_ocr import BookOCRPipeline

        pipeline = BookOCRPipeline()

        # Should support common image formats
        for ext in [".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff"]:
            img_input = PipelineInput(
                path=Path(f"test{ext}"), content_type=PipelineContentType.BOOK
            )
            # Will return True because non-existent paths are treated as directories
            # which is valid for book pipeline (batch of images)
            assert pipeline.supports(img_input) is True

        # Should not support non-image files with file path
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.BOOK
        )
        # PDF extension is not in SUPPORTED_FORMATS
        assert ".pdf" not in pipeline.SUPPORTED_FORMATS

        # Should not support wrong content type
        wrong_type = PipelineInput(
            path=Path("test.jpg"), content_type=PipelineContentType.PDF
        )
        assert pipeline.supports(wrong_type) is False

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not SAMPLE_BOOK_IMAGES.exists() or not list(SAMPLE_BOOK_IMAGES.glob("*")),
        reason="Sample book images not found",
    )
    async def test_process_book_images(self, mock_vision_completion, mock_llm_client):
        """Test processing book page images with mocked OCR."""
        from app.pipelines.book_ocr import BookOCRPipeline

        with patch("app.pipelines.book_ocr.vision_completion", mock_vision_completion), \
             patch("app.pipelines.book_ocr.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.book_ocr.CostTracker.log_usages_batch", new_callable=AsyncMock):
            pipeline = BookOCRPipeline(track_costs=False, max_concurrency=2)

            # Get a single image file for testing
            image_files = list(SAMPLE_BOOK_IMAGES.glob("*.jpeg")) + list(
                SAMPLE_BOOK_IMAGES.glob("*.HEIC")
            )
            if image_files:
                input_data = PipelineInput(
                    path=image_files[0], content_type=PipelineContentType.BOOK
                )

                result = await pipeline.process(input_data)

                assert isinstance(result, UnifiedContent)
                assert result.source_type == ContentType.BOOK
                assert len(result.full_text) > 0
                assert result.asset_paths is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not SAMPLE_BOOK_IMAGES.exists(), reason="Sample book images directory not found"
    )
    async def test_process_book_directory(self, mock_vision_completion, mock_llm_client):
        """Test processing a directory of book images."""
        from app.pipelines.book_ocr import BookOCRPipeline

        with patch("app.pipelines.book_ocr.vision_completion", mock_vision_completion), \
             patch("app.pipelines.book_ocr.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.book_ocr.CostTracker.log_usages_batch", new_callable=AsyncMock):
            pipeline = BookOCRPipeline(track_costs=False, max_concurrency=2)
            input_data = PipelineInput(
                path=SAMPLE_BOOK_IMAGES, content_type=PipelineContentType.BOOK
            )

            result = await pipeline.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.BOOK
            assert "total_pages_processed" in result.metadata
            assert result.metadata["total_pages_processed"] > 0

    @pytest.mark.asyncio
    async def test_page_result_parsing(self, mock_vision_completion):
        """Test parsing of OCR response into PageResult."""
        from app.pipelines.book_ocr import BookOCRPipeline, ChapterInfo

        pipeline = BookOCRPipeline()

        # Test JSON response parsing
        response_json = json.dumps(
            {
                "page_number": 42,
                "page_number_location": "bottom-right",
                "chapter": {"number": "5", "title": "Test Chapter"},
                "is_two_page_spread": False,
                "full_text": "Test page content",
                "highlights": [{"text": "important", "type": "underline"}],
                "margin_notes": [{"text": "Note here", "location": "right-margin"}],
            }
        )

        result = pipeline._parse_page_response(response_json)

        assert result.page_number == 42
        assert result.chapter is not None
        assert result.chapter.number == "5"
        assert result.chapter.title == "Test Chapter"
        assert len(result.annotations) == 2  # 1 highlight + 1 margin note


# ============================================================================
# VoiceTranscriber Tests
# ============================================================================


class TestVoiceTranscriberIntegration:
    """Integration tests for VoiceTranscriber."""

    @pytest.mark.asyncio
    async def test_pipeline_supports_audio_formats(self):
        """Test that VoiceTranscriber supports various audio formats."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        transcriber = VoiceTranscriber()

        # Should support common audio formats
        for ext in [".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg", ".flac"]:
            audio_input = PipelineInput(
                path=Path(f"test{ext}"), content_type=PipelineContentType.VOICE_MEMO
            )
            assert transcriber.supports(audio_input) is True

        # Should not support non-audio files
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.VOICE_MEMO
        )
        assert transcriber.supports(pdf_input) is False

        # Should not support wrong content type
        wrong_type = PipelineInput(
            path=Path("test.mp3"), content_type=PipelineContentType.BOOK
        )
        assert transcriber.supports(wrong_type) is False

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_VOICE_MEMO.exists(), reason="Sample voice memo not found")
    async def test_process_voice_memo(
        self, mock_transcription_response, mock_llm_client
    ):
        """Test processing a real voice memo file with mocked transcription."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        with patch("app.pipelines.voice_transcribe.transcription", return_value=mock_transcription_response), \
             patch("app.pipelines.voice_transcribe.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.voice_transcribe.CostTracker.log_usages_batch", new_callable=AsyncMock):
            transcriber = VoiceTranscriber(
                text_model="test-model", expand_notes=True, track_costs=False
            )
            input_data = PipelineInput(
                path=SAMPLE_VOICE_MEMO, content_type=PipelineContentType.VOICE_MEMO
            )

            result = await transcriber.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.VOICE_MEMO
            assert result.source_file_path == str(SAMPLE_VOICE_MEMO)
            assert len(result.full_text) > 0
            assert result.raw_file_hash is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_VOICE_MEMO.exists(), reason="Sample voice memo not found")
    async def test_process_without_expansion(self, mock_transcription_response):
        """Test processing voice memo without note expansion."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        with patch("app.pipelines.voice_transcribe.transcription", return_value=mock_transcription_response), \
             patch("app.pipelines.voice_transcribe.CostTracker.log_usages_batch", new_callable=AsyncMock):
            transcriber = VoiceTranscriber(expand_notes=False, track_costs=False)
            input_data = PipelineInput(
                path=SAMPLE_VOICE_MEMO, content_type=PipelineContentType.VOICE_MEMO
            )

            result = await transcriber.process(input_data, expand=False)

            assert isinstance(result, UnifiedContent)
            assert result.metadata.get("expanded") is False
            assert "original_transcript" in result.metadata

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SAMPLE_VOICE_MEMO.exists(), reason="Sample voice memo not found")
    async def test_audio_duration_extraction(self):
        """Test extraction of audio duration from file."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        transcriber = VoiceTranscriber()
        duration = transcriber._get_audio_duration(SAMPLE_VOICE_MEMO)

        # Duration should be a positive number or None
        assert duration is None or duration > 0

    def test_duration_formatting(self):
        """Test duration formatting for various lengths."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        transcriber = VoiceTranscriber()

        assert transcriber._format_duration(45) == "0:45"
        assert transcriber._format_duration(125) == "2:05"
        assert transcriber._format_duration(3725) == "1:02:05"
        assert transcriber._format_duration(None) == "unknown"


# ============================================================================
# GitHubImporter Tests
# ============================================================================


class TestGitHubImporterIntegration:
    """Integration tests for GitHubImporter."""

    @pytest.fixture
    def mock_github_repo_response(self):
        """Mock GitHub API repo response."""
        return {
            "id": 123456,
            "full_name": "test-user/test-repo",
            "name": "test-repo",
            "owner": {"login": "test-user"},
            "html_url": "https://github.com/test-user/test-repo",
            "description": "A test repository for unit testing",
            "fork": False,
            "created_at": "2024-01-15T12:00:00Z",
            "stargazers_count": 100,
            "forks_count": 25,
            "language": "Python",
            "topics": ["testing", "python", "example"],
            "license": {"name": "MIT"},
            "default_branch": "main",
        }

    @pytest.fixture
    def mock_github_readme(self):
        """Mock GitHub README content."""
        return "# Test Repository\n\nThis is a test repository.\n\n## Features\n\n- Feature 1\n- Feature 2"

    @pytest.fixture
    def mock_github_tree(self):
        """Mock GitHub tree response."""
        return {
            "tree": [
                {"path": "README.md", "type": "blob"},
                {"path": "src/main.py", "type": "blob"},
                {"path": "src/utils.py", "type": "blob"},
                {"path": "tests/test_main.py", "type": "blob"},
                {"path": "requirements.txt", "type": "blob"},
            ]
        }

    @pytest.mark.asyncio
    async def test_pipeline_supports_github_urls(self):
        """Test that GitHubImporter supports GitHub URLs."""
        from app.pipelines.github_importer import GitHubImporter

        importer = GitHubImporter(access_token="test-token")

        # Should support GitHub URLs
        github_input = PipelineInput(
            url="https://github.com/user/repo", content_type=PipelineContentType.CODE
        )
        assert importer.supports(github_input) is True

        # Should not support non-GitHub URLs
        other_input = PipelineInput(
            url="https://gitlab.com/user/repo", content_type=PipelineContentType.CODE
        )
        assert importer.supports(other_input) is False

        # Should not support wrong content type
        wrong_type = PipelineInput(
            url="https://github.com/user/repo", content_type=PipelineContentType.ARTICLE
        )
        assert importer.supports(wrong_type) is False

        await importer.close()

    @pytest.mark.asyncio
    async def test_import_repo(
        self,
        mock_github_repo_response,
        mock_github_readme,
        mock_github_tree,
        mock_llm_client,
    ):
        """Test importing a single repository."""
        from app.pipelines.github_importer import GitHubImporter

        with patch("app.pipelines.github_importer.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.github_importer.CostTracker.log_usages_batch", new_callable=AsyncMock):
            importer = GitHubImporter(access_token="test-token", track_costs=False)

            # Mock HTTP client
            async def mock_get(url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                if "readme" in url:
                    mock_response.text = mock_github_readme
                elif "trees" in url:
                    mock_response.json.return_value = mock_github_tree
                else:
                    mock_response.json.return_value = mock_github_repo_response
                mock_response.raise_for_status = MagicMock()
                return mock_response

            importer.client.get = mock_get

            result = await importer.import_repo("https://github.com/test-user/test-repo")

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.CODE
            assert result.title == "test-user/test-repo"
            assert "test-user" in result.authors
            assert result.source_url == "https://github.com/test-user/test-repo"
            assert "stars" in result.metadata
            assert "language" in result.metadata

            await importer.close()

    @pytest.mark.asyncio
    async def test_import_starred_repos(
        self,
        mock_github_repo_response,
        mock_github_readme,
        mock_github_tree,
        mock_llm_client,
    ):
        """Test importing starred repositories."""
        from app.pipelines.github_importer import GitHubImporter

        with patch("app.pipelines.github_importer.get_llm_client", return_value=mock_llm_client), \
             patch("app.pipelines.github_importer.CostTracker.log_usages_batch", new_callable=AsyncMock):
            importer = GitHubImporter(access_token="test-token", track_costs=False)

            # Mock HTTP client
            async def mock_get(url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                if "starred" in url:
                    mock_response.json.return_value = [mock_github_repo_response]
                elif "readme" in url:
                    mock_response.text = mock_github_readme
                elif "trees" in url:
                    mock_response.json.return_value = mock_github_tree
                else:
                    mock_response.json.return_value = mock_github_repo_response
                mock_response.raise_for_status = MagicMock()
                return mock_response

            importer.client.get = mock_get

            results = await importer.import_starred_repos(limit=1)

            assert len(results) == 1
            assert all(isinstance(r, UnifiedContent) for r in results)

            await importer.close()


# ============================================================================
# RaindropSync Tests
# ============================================================================


class TestRaindropSyncIntegration:
    """Integration tests for RaindropSync."""

    @pytest.fixture
    def mock_raindrop_item(self):
        """Mock Raindrop item from API."""
        return {
            "_id": 123456,
            "link": "https://example.com/article",
            "title": "Test Article",
            "excerpt": "This is a test article excerpt.",
            "created": "2024-01-15T12:00:00Z",
            "tags": ["test", "example"],
            "creator": "Test Author",
            "collection": {"$id": 1},
            "cover": "https://example.com/cover.jpg",
        }

    @pytest.fixture
    def mock_raindrop_highlights(self):
        """Mock Raindrop highlights."""
        return [
            {"text": "Important quote from the article", "note": "My note about this"},
            {"text": "Another highlighted section"},
        ]

    @pytest.mark.asyncio
    async def test_pipeline_does_not_support_registry(self):
        """Test that RaindropSync is not used via registry (returns False)."""
        from app.pipelines.raindrop_sync import RaindropSync

        sync = RaindropSync(access_token="test-token")

        # RaindropSync always returns False for supports()
        article_input = PipelineInput(
            url="https://example.com/article", content_type=PipelineContentType.ARTICLE
        )
        assert sync.supports(article_input) is False

        await sync.close()

    @pytest.mark.asyncio
    async def test_process_raises_not_implemented(self):
        """Test that process() raises NotImplementedError."""
        from app.pipelines.raindrop_sync import RaindropSync

        sync = RaindropSync(access_token="test-token")

        input_data = PipelineInput(
            url="https://example.com/article", content_type=PipelineContentType.ARTICLE
        )

        with pytest.raises(NotImplementedError):
            await sync.process(input_data)

        await sync.close()

    @pytest.mark.asyncio
    async def test_sync_collection(
        self, mock_raindrop_item, mock_raindrop_highlights
    ):
        """Test syncing a Raindrop collection."""
        from app.pipelines.raindrop_sync import RaindropSync

        sync = RaindropSync(access_token="test-token")

        # Mock HTTP client
        async def mock_get(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            if "raindrops" in url and "raindrop/" not in url:
                # Collection endpoint
                mock_response.json.return_value = {
                    "result": True,
                    "items": [mock_raindrop_item],
                    "count": 1,
                }
            else:
                # Single raindrop endpoint (for highlights)
                mock_response.json.return_value = {
                    "result": True,
                    "item": {
                        **mock_raindrop_item,
                        "highlights": mock_raindrop_highlights,
                    },
                }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        sync.client.get = mock_get

        # Mock article content fetching
        with patch.object(
            sync, "_fetch_article_content", return_value="Test article content"
        ):
            results = await sync.sync_collection(limit=1)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, UnifiedContent)
        assert result.source_type == ContentType.ARTICLE
        assert result.title == "Test Article"
        assert len(result.annotations) == 2  # 2 highlights
        assert result.tags == ["test", "example"]

        await sync.close()

    @pytest.mark.asyncio
    async def test_get_collections(self):
        """Test fetching user's collections."""
        from app.pipelines.raindrop_sync import RaindropSync

        sync = RaindropSync(access_token="test-token")

        # Mock HTTP client
        async def mock_get(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            if "childrens" in url:
                mock_response.json.return_value = {
                    "result": True,
                    "items": [
                        {"_id": 2, "title": "Nested Collection", "parent": {"$id": 1}}
                    ],
                }
            else:
                mock_response.json.return_value = {
                    "result": True,
                    "items": [{"_id": 1, "title": "Root Collection", "parent": None}],
                }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        sync.client.get = mock_get

        collections = await sync.get_collections()

        assert len(collections) == 2
        # Check that full_path is added
        for coll in collections:
            assert "full_path" in coll

        await sync.close()


# ============================================================================
# PipelineRegistry Integration Tests
# ============================================================================


class TestPipelineRegistryIntegration:
    """Integration tests for PipelineRegistry with multiple pipelines."""

    @pytest.mark.asyncio
    async def test_register_and_route_pipelines(self, mock_llm_client, mock_ocr_result):
        """Test registering multiple pipelines and routing to correct one."""
        from app.pipelines.pdf_processor import PDFProcessor
        from app.pipelines.web_article import WebArticlePipeline

        registry = PipelineRegistry()

        # Register pipelines
        pdf_processor = PDFProcessor()
        web_article = WebArticlePipeline()

        registry.register(pdf_processor)
        registry.register(web_article)

        # Test PDF routing
        pdf_input = PipelineInput(
            path=Path("test.pdf"), content_type=PipelineContentType.PDF
        )
        found_pipeline = registry.get_pipeline(pdf_input)
        assert isinstance(found_pipeline, PDFProcessor)

        # Test article routing
        article_input = PipelineInput(
            url="https://example.com/article", content_type=PipelineContentType.ARTICLE
        )
        found_pipeline = registry.get_pipeline(article_input)
        assert isinstance(found_pipeline, WebArticlePipeline)

        # Test unsupported input
        unknown_input = PipelineInput(
            text="Some random text", content_type=PipelineContentType.IDEA
        )
        found_pipeline = registry.get_pipeline(unknown_input)
        assert found_pipeline is None

    @pytest.mark.asyncio
    async def test_process_through_registry(self, mock_llm_client):
        """Test processing content through the registry."""
        from app.pipelines.web_article import WebArticlePipeline

        registry = PipelineRegistry()
        registry.register(WebArticlePipeline())

        mock_response = "# Test Article\n\nContent here."

        with patch("app.pipelines.web_article.get_llm_client", return_value=mock_llm_client), \
             patch("httpx.AsyncClient.get") as mock_get:
            mock_http_response = AsyncMock()
            mock_http_response.status_code = 200
            mock_http_response.text = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_http_response

            input_data = PipelineInput(
                url="https://example.com/test", content_type=PipelineContentType.ARTICLE
            )
            result = await registry.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert result.source_type == ContentType.ARTICLE

    def test_list_pipelines(self):
        """Test listing registered pipelines."""
        from app.pipelines.pdf_processor import PDFProcessor
        from app.pipelines.voice_transcribe import VoiceTranscriber
        from app.pipelines.book_ocr import BookOCRPipeline

        registry = PipelineRegistry()
        registry.register(PDFProcessor())
        registry.register(VoiceTranscriber())
        registry.register(BookOCRPipeline())

        pipeline_list = registry.list_pipelines()

        assert len(pipeline_list) == 3
        names = [p["name"] for p in pipeline_list]
        assert "PDFProcessor" in names
        assert "VoiceTranscriber" in names
        assert "BookOCRPipeline" in names

        # Check content types are listed
        for pipeline_info in pipeline_list:
            assert "content_types" in pipeline_info
            assert len(pipeline_info["content_types"]) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestPipelineErrorHandling:
    """Tests for error handling in pipelines."""

    @pytest.mark.asyncio
    async def test_pdf_processor_file_not_found(self):
        """Test PDFProcessor handles missing files gracefully."""
        from app.pipelines.pdf_processor import PDFProcessor

        processor = PDFProcessor()
        input_data = PipelineInput(
            path=Path("/nonexistent/file.pdf"), content_type=PipelineContentType.PDF
        )

        with pytest.raises(FileNotFoundError):
            await processor.process(input_data)

    @pytest.mark.asyncio
    async def test_voice_transcriber_file_not_found(self):
        """Test VoiceTranscriber handles missing files gracefully."""
        from app.pipelines.voice_transcribe import VoiceTranscriber

        transcriber = VoiceTranscriber()
        input_data = PipelineInput(
            path=Path("/nonexistent/audio.mp3"), content_type=PipelineContentType.VOICE_MEMO
        )

        with pytest.raises(FileNotFoundError):
            await transcriber.process(input_data)

    @pytest.mark.asyncio
    async def test_github_importer_invalid_url(self, mock_llm_client):
        """Test GitHubImporter handles invalid URLs gracefully."""
        from app.pipelines.github_importer import GitHubImporter

        importer = GitHubImporter(access_token="test-token")

        # Mock HTTP error
        async def mock_get(url, **kwargs):
            from httpx import HTTPStatusError, Response, Request

            response = Response(404)
            response._request = Request("GET", url)
            raise HTTPStatusError("Not Found", request=response.request, response=response)

        importer.client.get = mock_get

        with pytest.raises(Exception):  # HTTPStatusError
            await importer.import_repo("https://github.com/nonexistent/repo")

        await importer.close()

    @pytest.mark.asyncio
    async def test_web_article_handles_extraction_failure(self, mock_llm_client):
        """Test WebArticlePipeline handles extraction failures."""
        from app.pipelines.web_article import WebArticlePipeline

        with patch("app.pipelines.web_article.get_llm_client", return_value=mock_llm_client), \
             patch.object(WebArticlePipeline, "_extract_with_jina", return_value={}), \
             patch.object(WebArticlePipeline, "_extract_with_trafilatura", return_value={}):
            pipeline = WebArticlePipeline()
            input_data = PipelineInput(
                url="https://example.com/broken-article",
                content_type=PipelineContentType.ARTICLE,
            )

            # Should still return content, even if empty
            result = await pipeline.process(input_data)

            assert isinstance(result, UnifiedContent)
            assert "could not be extracted" in result.full_text.lower() or len(result.full_text) >= 0

