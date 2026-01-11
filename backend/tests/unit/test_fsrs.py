"""
Unit tests for FSRS (Free Spaced Repetition Scheduler) implementation.

Tests the scheduling algorithm, state transitions, and interval calculations.

Note: These tests require the fsrs package to be installed.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fsrs import Rating, State

from app.services.learning.fsrs import (
    FSRSScheduler,
    CardState,
    ReviewLog,
    create_scheduler,
    get_review_forecast,
)


class TestFSRSScheduler:
    """Tests for FSRSScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a default scheduler."""
        return FSRSScheduler(desired_retention=0.9, maximum_interval=365)

    @pytest.fixture
    def new_card(self):
        """Create a new card state (never reviewed)."""
        return CardState(
            state=State.Learning,
            difficulty=None,
            stability=None,
            due=datetime.now(timezone.utc),
            last_review=None,  # None indicates new card
            reps=0,
            lapses=0,
            scheduled_days=0,
        )

    @pytest.fixture
    def learning_card(self):
        """Create a learning card state."""
        return CardState(
            state=State.Learning,
            difficulty=0.3,
            stability=1.0,
            due=datetime.now(timezone.utc),
            last_review=datetime.now(timezone.utc) - timedelta(hours=1),
            reps=1,
            lapses=0,
            scheduled_days=1,
        )

    @pytest.fixture
    def review_card(self):
        """Create a review card state."""
        return CardState(
            state=State.Review,
            difficulty=0.3,
            stability=10.0,
            due=datetime.now(timezone.utc),
            last_review=datetime.now(timezone.utc) - timedelta(days=10),
            reps=5,
            lapses=0,
            scheduled_days=10,
        )

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes with correct parameters."""
        assert scheduler.desired_retention == 0.9
        assert scheduler.maximum_interval == 365

    def test_review_new_card_good(self, scheduler, new_card):
        """Test reviewing a new card with GOOD rating."""
        assert new_card.is_new()  # Verify it's a new card
        new_state, log = scheduler.review(new_card, Rating.Good)

        assert new_state.state in (State.Learning, State.Review)
        assert new_state.stability is not None and new_state.stability > 0
        assert new_state.last_review is not None
        assert not new_state.is_new()  # No longer new after review
        assert log.rating == Rating.Good

    def test_review_new_card_again(self, scheduler, new_card):
        """Test reviewing a new card with AGAIN rating."""
        new_state, log = scheduler.review(new_card, Rating.Again)

        assert new_state.state == State.Learning
        assert log.state_after == State.Learning

    def test_review_new_card_easy(self, scheduler, new_card):
        """Test reviewing a new card with EASY rating."""
        new_state, log = scheduler.review(new_card, Rating.Easy)

        assert new_state.state == State.Review  # Should graduate immediately
        assert new_state.stability is not None and new_state.stability > 0

    def test_review_learning_card_good(self, scheduler, learning_card):
        """Test reviewing a learning card with GOOD rating."""
        new_state, log = scheduler.review(learning_card, Rating.Good)

        # In FSRS v6, graduation depends on learning_steps, may still be Learning
        assert new_state.state in (State.Learning, State.Review)
        assert new_state.stability is not None
        assert new_state.reps > learning_card.reps

    def test_review_learning_card_again(self, scheduler, learning_card):
        """Test reviewing a learning card with AGAIN rating."""
        new_state, log = scheduler.review(learning_card, Rating.Again)

        assert new_state.state == State.Learning
        # FSRS v6 doesn't reset reps on Again during learning

    def test_review_card_good_increases_stability(self, scheduler, review_card):
        """Test that GOOD review increases stability."""
        new_state, log = scheduler.review(review_card, Rating.Good)

        assert new_state.state == State.Review
        assert new_state.stability > review_card.stability
        assert new_state.scheduled_days > 0

    def test_review_card_again_triggers_lapse(self, scheduler, review_card):
        """Test that AGAIN on review card triggers lapse."""
        new_state, log = scheduler.review(review_card, Rating.Again)

        assert new_state.state == State.Relearning
        assert new_state.lapses == review_card.lapses + 1
        assert new_state.stability < review_card.stability

    def test_review_card_hard_reduces_stability_gain(self, scheduler, review_card):
        """Test that HARD rating reduces stability gain."""
        good_state, _ = scheduler.review(review_card, Rating.Good)
        hard_state, _ = scheduler.review(review_card, Rating.Hard)

        # HARD should result in lower stability than GOOD
        assert hard_state.stability <= good_state.stability

    def test_review_card_easy_bonus(self, scheduler, review_card):
        """Test that EASY rating gives bonus to stability."""
        good_state, _ = scheduler.review(review_card, Rating.Good)
        easy_state, _ = scheduler.review(review_card, Rating.Easy)

        # EASY should result in higher stability than GOOD
        assert easy_state.stability >= good_state.stability

    def test_maximum_interval_respected(self, scheduler):
        """Test that maximum interval is respected."""
        # Create a card with very high stability
        card = CardState(
            state=State.Review,
            difficulty=0.1,
            stability=1000.0,  # Very stable
            due=datetime.now(timezone.utc),
            last_review=datetime.now(timezone.utc) - timedelta(days=100),
            reps=50,
            lapses=0,
            scheduled_days=100,
        )

        new_state, _ = scheduler.review(card, Rating.Easy)

        # Scheduled days should not exceed maximum
        assert new_state.scheduled_days <= scheduler.maximum_interval

    def test_difficulty_bounds(self, scheduler, new_card):
        """Test that difficulty stays within valid bounds."""
        # Review with AGAIN multiple times to increase difficulty
        card = new_card
        for _ in range(10):
            card, _ = scheduler.review(card, Rating.Again)

        # FSRS v6 difficulty is clamped to [1, 10]
        assert 1.0 <= card.difficulty <= 10.0

        # Review with EASY multiple times to decrease difficulty
        card = new_card
        for _ in range(10):
            card, _ = scheduler.review(card, Rating.Easy)

        assert 1.0 <= card.difficulty <= 10.0

    def test_review_log_structure(self, scheduler, new_card):
        """Test that review log contains all required fields."""
        _, log = scheduler.review(new_card, Rating.Good)

        assert isinstance(log, ReviewLog)
        assert log.rating == Rating.Good
        assert log.state_before == State.Learning  # New cards start as Learning
        assert log.state_after in (State.Learning, State.Review)
        assert log.difficulty_after is not None
        assert log.stability_after is not None
        assert log.scheduled_days >= 0
        assert log.review_time is not None

    def test_get_retrievability_new_card(self, scheduler, new_card):
        """Test retrievability for new card."""
        r = scheduler.get_retrievability(new_card)
        assert r == 1.0  # New cards have perfect retrievability

    def test_get_retrievability_decays(self, scheduler, review_card):
        """Test retrievability decays over time."""
        # Just reviewed
        review_card.last_review = datetime.now(timezone.utc)
        r_now = scheduler.get_retrievability(review_card)

        # Reviewed a while ago
        review_card.last_review = datetime.now(timezone.utc) - timedelta(days=30)
        r_later = scheduler.get_retrievability(review_card)

        assert r_now > r_later  # Retrievability should decay


class TestCreateScheduler:
    """Tests for create_scheduler factory function."""

    def test_create_default_scheduler(self):
        """Test creating scheduler with defaults."""
        scheduler = create_scheduler()
        assert scheduler.desired_retention == 0.9
        assert scheduler.maximum_interval == 365

    def test_create_custom_scheduler(self):
        """Test creating scheduler with custom parameters."""
        scheduler = create_scheduler(retention=0.85, max_interval=180)
        assert scheduler.desired_retention == 0.85
        assert scheduler.maximum_interval == 180


class TestGetReviewForecast:
    """Tests for get_review_forecast function."""

    def test_empty_cards(self):
        """Test forecast with no cards."""
        forecast = get_review_forecast([])
        assert forecast["overdue"] == 0
        assert forecast["today"] == 0
        assert forecast["tomorrow"] == 0
        assert forecast["this_week"] == 0
        assert forecast["later"] == 0

    def test_forecast_categorization(self):
        """Test cards are categorized correctly."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        cards = [
            # Overdue
            CardState(
                state=State.Review,
                due=today_start - timedelta(days=2),
                last_review=today_start - timedelta(days=10),
            ),
            # Today
            CardState(
                state=State.Review,
                due=today_start + timedelta(hours=5),
                last_review=today_start - timedelta(days=5),
            ),
            # Tomorrow
            CardState(
                state=State.Review,
                due=today_start + timedelta(days=1, hours=3),
                last_review=today_start - timedelta(days=3),
            ),
            # This week
            CardState(
                state=State.Review,
                due=today_start + timedelta(days=4),
                last_review=today_start - timedelta(days=10),
            ),
            # Later
            CardState(
                state=State.Review,
                due=today_start + timedelta(days=30),
                last_review=today_start - timedelta(days=20),
            ),
            # New card (should be skipped) - new cards have last_review=None
            CardState(state=State.Learning, last_review=None, due=now),
        ]

        forecast = get_review_forecast(cards, as_of=now)

        assert forecast["overdue"] == 1
        assert forecast["today"] == 1
        assert forecast["tomorrow"] == 1
        assert forecast["this_week"] == 1
        assert forecast["later"] == 1

    def test_forecast_new_cards_skipped(self):
        """Test that new cards are not included in forecast."""
        cards = [
            CardState(
                state=State.Learning, last_review=None, due=datetime.now(timezone.utc)
            ),
            CardState(
                state=State.Learning, last_review=None, due=datetime.now(timezone.utc)
            ),
        ]

        forecast = get_review_forecast(cards)

        total = sum(forecast.values())
        assert total == 0


class TestCardStateDataclass:
    """Tests for CardState dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        card = CardState()
        assert card.state == State.Learning
        assert card.difficulty is None  # New cards have None
        assert card.stability is None  # New cards have None
        assert card.reps == 0
        assert card.lapses == 0
        assert card.scheduled_days == 0
        assert card.due is not None
        assert card.last_review is None
        assert card.is_new()  # Should be new

    def test_custom_values(self):
        """Test custom values are accepted."""
        now = datetime.now(timezone.utc)
        card = CardState(
            state=State.Review,
            difficulty=0.5,
            stability=15.0,
            due=now + timedelta(days=7),
            last_review=now,
            reps=10,
            lapses=2,
            scheduled_days=7,
        )
        assert card.state == State.Review
        assert card.difficulty == 0.5
        assert card.stability == 15.0
        assert card.reps == 10
        assert card.lapses == 2
        assert not card.is_new()  # Has been reviewed
