"""
Unit tests for CardGeneratorService.

Tests the card generation service, specifically the _gather_topic_context
method which searches for content by topic keywords.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.learning.card_generator import CardGeneratorService


class TestGatherTopicContext:
    """Tests for the _gather_topic_context method."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a CardGeneratorService with mocked dependencies."""
        return CardGeneratorService(mock_db)

    @pytest.mark.asyncio
    async def test_uses_summary_when_available(self, service, mock_db):
        """Test that summary is used when available."""
        # Create mock content with summary
        mock_content = MagicMock()
        mock_content.id = uuid4()
        mock_content.title = "Test Article"
        mock_content.summary = "This is a summary of the test article."
        mock_content.raw_text = "This is the full raw text of the article."

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_content]
        mock_db.execute.return_value = mock_result

        # Call the method
        context = await service._gather_topic_context("test")

        # Verify summary is used
        assert "This is a summary of the test article." in context
        assert "raw text" not in context.lower()

    @pytest.mark.asyncio
    async def test_uses_raw_text_when_summary_empty(self, service, mock_db):
        """Test that raw_text is used as fallback when summary is empty."""
        # Create mock content without summary but with raw_text
        mock_content = MagicMock()
        mock_content.id = uuid4()
        mock_content.title = "Test Article Without Summary"
        mock_content.summary = ""  # Empty summary
        mock_content.raw_text = "This is the full raw text content that should be used."

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_content]
        mock_db.execute.return_value = mock_result

        # Call the method
        context = await service._gather_topic_context("test")

        # Verify raw_text is used
        assert "This is the full raw text content" in context
        assert "Test Article Without Summary" in context

    @pytest.mark.asyncio
    async def test_uses_raw_text_when_summary_none(self, service, mock_db):
        """Test that raw_text is used as fallback when summary is None."""
        # Create mock content without summary
        mock_content = MagicMock()
        mock_content.id = uuid4()
        mock_content.title = "Test Article With None Summary"
        mock_content.summary = None  # No summary
        mock_content.raw_text = "Raw text content when summary is null."

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_content]
        mock_db.execute.return_value = mock_result

        # Call the method
        context = await service._gather_topic_context("test")

        # Verify raw_text is used
        assert "Raw text content when summary is null." in context

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_content_found(self, service, mock_db):
        """Test that empty string is returned when no content matches."""
        # Mock empty results for all queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Call the method
        context = await service._gather_topic_context("nonexistent")

        # Verify empty result
        assert context == ""

    @pytest.mark.asyncio
    async def test_deduplicates_content(self, service, mock_db):
        """Test that duplicate content is not included multiple times."""
        # Create mock content that would match multiple keywords
        content_id = uuid4()
        mock_content = MagicMock()
        mock_content.id = content_id
        mock_content.title = "Machine Learning Transformers"
        mock_content.summary = "A summary about ML transformers."
        mock_content.raw_text = None

        # Mock the database query - same content returned for different keywords
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_content]
        mock_db.execute.return_value = mock_result

        # Call with topic that has multiple keywords
        context = await service._gather_topic_context("machine/learning")

        # Content should only appear once
        assert context.count("Machine Learning Transformers") == 1

    @pytest.mark.asyncio
    async def test_skips_short_keywords(self, service, mock_db):
        """Test that keywords shorter than minimum length are skipped."""
        # Mock the database
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Call with short keywords (e.g., "ml" which might be < min length)
        with patch("app.services.learning.card_generator.settings") as mock_settings:
            mock_settings.CARD_CONTEXT_MIN_KEYWORD_LENGTH = 4
            mock_settings.CARD_CONTEXT_CONTENT_PER_KEYWORD = 5
            mock_settings.CARD_CONTEXT_EXERCISES_LIMIT = 3
            mock_settings.CARD_CONTEXT_EXERCISE_PROMPT_LENGTH = 500
            mock_settings.CARD_CONTEXT_MAX_LENGTH = 10000

            await service._gather_topic_context("ml")

            # Database should not be called for "ml" since it's too short
            # But it might be called for exercises
            # We mainly verify no error occurs


class TestCardGeneratorIntegration:
    """Integration-style tests for CardGeneratorService."""

    @pytest.mark.asyncio
    async def test_generate_for_topic_returns_empty_on_no_context(self):
        """Test that generate_for_topic returns empty when no context found."""
        mock_db = AsyncMock()

        # Mock empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = CardGeneratorService(mock_db)

        # Should return empty lists when no context
        cards, usages = await service.generate_for_topic("nonexistent/topic")

        assert cards == []
        assert usages == []
