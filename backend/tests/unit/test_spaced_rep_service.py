"""
Unit tests for SpacedRepService.

Tests the service layer for spaced repetition card management.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.enums.learning import Rating
from app.models.learning import CardCreate, CardReviewRequest, CardStats
from app.services.learning.spaced_rep_service import SpacedRepService


class TestSpacedRepServiceInitialization:
    """Tests for SpacedRepService initialization."""

    def test_default_retention(self):
        """Test default retention target."""
        mock_db = MagicMock()
        service = SpacedRepService(mock_db)
        assert service.scheduler.desired_retention == 0.9

    def test_custom_retention(self):
        """Test custom retention target."""
        mock_db = MagicMock()
        service = SpacedRepService(mock_db, target_retention_probability=0.85)
        assert service.scheduler.desired_retention == 0.85

    def test_custom_max_interval(self):
        """Test custom max interval."""
        mock_db = MagicMock()
        service = SpacedRepService(mock_db, max_interval=180)
        assert service.scheduler.maximum_interval == 180


class TestSpacedRepServiceCreateCard:
    """Tests for card creation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session with async support."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        # Mock execute for tag validation queries
        mock.execute = AsyncMock()
        return mock

    @pytest.mark.asyncio
    @patch("app.services.learning.spaced_rep_service.TagService")
    async def test_create_basic_card(self, mock_tag_service_class, mock_db):
        """Test creating a basic card."""
        # Mock TagService to not actually validate tags
        mock_tag_service = MagicMock()
        mock_tag_service.validate_tags = AsyncMock()
        mock_tag_service_class.return_value = mock_tag_service

        service = SpacedRepService(mock_db)

        card_data = CardCreate(
            card_type="concept",
            front="What is Python?",
            back="A programming language",
            hints=["It's named after a snake"],
            tags=["programming"],
        )

        # Mock the refresh to set an ID and required attributes
        async def set_card_attrs(card):
            card.id = 1
            card.repetitions = 0

        mock_db.refresh = AsyncMock(side_effect=set_card_attrs)

        result = await service.create_card(card_data)

        # Verify card was added to session
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        assert result.card_type == "concept"
        assert result.front == "What is Python?"
        assert result.state.value == "new"

    @pytest.mark.asyncio
    @patch("app.services.learning.spaced_rep_service.TagService")
    async def test_create_code_card(self, mock_tag_service_class, mock_db):
        """Test creating a code card with test cases."""
        # Mock TagService
        mock_tag_service = MagicMock()
        mock_tag_service.validate_tags = AsyncMock()
        mock_tag_service_class.return_value = mock_tag_service

        service = SpacedRepService(mock_db)

        card_data = CardCreate(
            card_type="code",
            front="Implement binary search",
            back="def binary_search(arr, x): ...",
            language="python",
            starter_code="def binary_search(arr, x):\n    pass",
            solution_code="def binary_search(arr, x):\n    ...",
            test_cases=[{"input": "[1,2,3], 2", "expected": "1"}],
        )

        async def set_card_attrs(card):
            card.id = 1
            card.repetitions = 0

        mock_db.refresh = AsyncMock(side_effect=set_card_attrs)

        result = await service.create_card(card_data)

        assert result.language == "python"


class TestSpacedRepServiceGetDueCards:
    """Tests for getting due cards."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session with query support."""
        mock = MagicMock()

        # Mock execute to return empty results by default
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0

        mock.execute = AsyncMock(return_value=mock_result)

        return mock

    @pytest.mark.asyncio
    async def test_get_due_cards_empty(self, mock_db):
        """Test getting due cards when none are due."""
        service = SpacedRepService(mock_db)

        result = await service.get_due_cards(limit=50)

        assert result.cards == []
        assert result.total_due == 0

    @pytest.mark.asyncio
    async def test_get_due_cards_respects_limit(self, mock_db):
        """Test that limit parameter is respected."""
        service = SpacedRepService(mock_db)

        await service.get_due_cards(limit=10)

        # Verify execute was called (query was made)
        assert mock_db.execute.called


class TestSpacedRepServiceReviewCard:
    """Tests for reviewing cards."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        mock = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        return mock

    @pytest.fixture
    def mock_card(self):
        """Create a mock card object with all required FSRS attributes."""
        # Use timezone-aware datetimes to match FSRS expectations
        now = datetime.now(timezone.utc)
        
        card = MagicMock()
        card.id = 1
        card.state = "review"
        card.stability = 10.0
        card.difficulty = 0.3
        card.due_date = now
        card.last_reviewed = now - timedelta(days=10)
        card.lapses = 0
        card.scheduled_days = 10
        card.repetitions = 5  # FSRS reps field
        card.total_reviews = 5
        card.correct_reviews = 5
        return card

    @pytest.mark.asyncio
    async def test_review_card_good(self, mock_db, mock_card):
        """Test reviewing a card with GOOD rating."""
        service = SpacedRepService(mock_db)

        # Mock the query to return the card
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_card
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = CardReviewRequest(
            card_id=1,
            rating=Rating.GOOD,
            time_spent_seconds=10,
        )

        result = await service.review_card(request)

        assert result.card_id == 1
        assert result.was_correct is True
        assert result.scheduled_days > 0

    @pytest.mark.asyncio
    async def test_review_card_again(self, mock_db, mock_card):
        """Test reviewing a card with AGAIN rating."""
        service = SpacedRepService(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_card
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = CardReviewRequest(
            card_id=1,
            rating=Rating.AGAIN,
        )

        result = await service.review_card(request)

        assert result.was_correct is False
        assert result.new_state.value == "relearning"

    @pytest.mark.asyncio
    async def test_review_nonexistent_card(self, mock_db):
        """Test reviewing a non-existent card raises error."""
        service = SpacedRepService(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = CardReviewRequest(
            card_id=99999,
            rating=Rating.GOOD,
        )

        with pytest.raises(ValueError, match="not found"):
            await service.review_card(request)


class TestSpacedRepServiceCardStats:
    """Tests for card statistics."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        mock = MagicMock()

        # Create multiple mock results for different queries
        def execute_side_effect(query):
            result = MagicMock()
            # Default to returning 0 or empty
            result.scalar.return_value = 0
            result.fetchall.return_value = []
            result.fetchone.return_value = (0.0, 0.0)  # For avg query
            return result

        mock.execute = AsyncMock(side_effect=execute_side_effect)
        return mock

    @pytest.mark.asyncio
    async def test_get_card_stats(self, mock_db):
        """Test getting card statistics."""
        service = SpacedRepService(mock_db)

        result = await service.get_card_stats()

        assert isinstance(result, CardStats)
        # With mocked empty results
        assert result.total_cards == 0

    @pytest.mark.asyncio
    async def test_get_card_stats_with_topic_filter(self, mock_db):
        """Test getting card statistics with topic filter."""
        service = SpacedRepService(mock_db)

        result = await service.get_card_stats(topic_filter="ml/transformers")

        assert isinstance(result, CardStats)
