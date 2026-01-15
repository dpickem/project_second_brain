"""
Unit tests for SpacedRepService.

Tests the service layer for spaced repetition card management.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models_learning import CardReviewHistory
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

    @pytest.mark.asyncio
    async def test_review_creates_history_record(self, mock_db, mock_card):
        """Test that reviewing a card creates a CardReviewHistory record."""
        service = SpacedRepService(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_card
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = CardReviewRequest(
            card_id=1,
            rating=Rating.GOOD,
            time_spent_seconds=15,
        )

        await service.review_card(request)

        # Verify a CardReviewHistory was added to the session
        add_calls = mock_db.add.call_args_list
        history_added = any(
            isinstance(call.args[0], CardReviewHistory) for call in add_calls
        )
        assert history_added, "CardReviewHistory record should be added to session"

    @pytest.mark.asyncio
    async def test_review_history_contains_correct_data(self, mock_db, mock_card):
        """Test that the CardReviewHistory record contains correct data."""
        service = SpacedRepService(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_card
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = CardReviewRequest(
            card_id=1,
            rating=Rating.HARD,
            time_spent_seconds=20,
        )

        await service.review_card(request)

        # Find the CardReviewHistory that was added
        history_record = None
        for call in mock_db.add.call_args_list:
            if isinstance(call.args[0], CardReviewHistory):
                history_record = call.args[0]
                break

        assert history_record is not None
        assert history_record.card_id == 1
        assert history_record.rating == Rating.HARD.value
        assert history_record.time_spent_seconds == 20
        assert history_record.state_before == "review"  # From mock_card.state


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


class TestSpacedRepServiceInterleaving:
    """Tests for card interleaving by topic."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def _create_mock_card(self, card_id: int, tags: list[str]):
        """Create a mock card with specified tags."""
        card = MagicMock()
        card.id = card_id
        card.tags = tags
        return card

    def test_interleave_empty_list(self, mock_db):
        """Test interleaving an empty list returns empty."""
        service = SpacedRepService(mock_db)
        result = service._interleave_by_topic([], 10)
        assert result == []

    def test_interleave_single_card(self, mock_db):
        """Test interleaving a single card returns that card."""
        service = SpacedRepService(mock_db)
        card = self._create_mock_card(1, ["topic_a"])
        result = service._interleave_by_topic([card], 10)
        assert len(result) == 1
        assert result[0].id == 1

    def test_interleave_respects_limit(self, mock_db):
        """Test that interleaving respects the limit parameter."""
        service = SpacedRepService(mock_db)
        cards = [self._create_mock_card(i, [f"topic_{i % 3}"]) for i in range(20)]
        result = service._interleave_by_topic(cards, 5)
        assert len(result) == 5

    def test_interleave_separates_same_topic(self, mock_db):
        """Test that cards from same topic don't appear consecutively."""
        service = SpacedRepService(mock_db)
        # Create 6 cards: 3 from topic_a, 3 from topic_b
        cards = [
            self._create_mock_card(1, ["topic_a"]),
            self._create_mock_card(2, ["topic_a"]),
            self._create_mock_card(3, ["topic_a"]),
            self._create_mock_card(4, ["topic_b"]),
            self._create_mock_card(5, ["topic_b"]),
            self._create_mock_card(6, ["topic_b"]),
        ]
        result = service._interleave_by_topic(cards, 6)

        # Check that no two consecutive cards share the same primary topic
        for i in range(len(result) - 1):
            current_topic = result[i].tags[0] if result[i].tags else "_no_topic"
            next_topic = result[i + 1].tags[0] if result[i + 1].tags else "_no_topic"
            assert (
                current_topic != next_topic
            ), f"Cards at position {i} and {i+1} share topic: {current_topic}"

    def test_interleave_handles_cards_without_tags(self, mock_db):
        """Test that cards without tags are handled correctly."""
        service = SpacedRepService(mock_db)
        cards = [
            self._create_mock_card(1, []),
            self._create_mock_card(2, ["topic_a"]),
            self._create_mock_card(3, []),
        ]
        result = service._interleave_by_topic(cards, 3)
        assert len(result) == 3

    def test_interleave_multiple_topics(self, mock_db):
        """Test interleaving with 3+ different topics."""
        service = SpacedRepService(mock_db)
        cards = [
            self._create_mock_card(1, ["ml"]),
            self._create_mock_card(2, ["ml"]),
            self._create_mock_card(3, ["databases"]),
            self._create_mock_card(4, ["databases"]),
            self._create_mock_card(5, ["networking"]),
            self._create_mock_card(6, ["networking"]),
        ]
        result = service._interleave_by_topic(cards, 6)

        # Should have all 6 cards
        assert len(result) == 6

        # Collect all card IDs to ensure no duplicates
        card_ids = [c.id for c in result]
        assert len(set(card_ids)) == 6
