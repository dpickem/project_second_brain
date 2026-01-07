"""
FSRS (Free Spaced Repetition Scheduler) Algorithm Implementation

This module wraps the FSRS library to provide a clean interface for
spaced repetition scheduling. FSRS-4.5 is a modern algorithm that
outperforms SM-2 by modeling memory stability and difficulty.

Key Concepts:
- Stability (S): Days until memory strength decays to 90% recall probability
- Difficulty (D): Inherent difficulty of the card (0-1)
- Retrievability (R): Current recall probability based on elapsed time

FSRS State Machine:
    NEW → LEARNING → REVIEW ↔ RELEARNING

Usage:
    from app.services.learning.fsrs import create_scheduler, FSRSScheduler

    scheduler = create_scheduler(retention=0.9, max_interval=365)

    # Review a card
    new_state, log = scheduler.review(card_state, Rating.GOOD)

    # Calculate next due date
    next_due = scheduler.get_next_due(new_state)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from fsrs import Card as FSRSCard, Rating, Scheduler, State

logger = logging.getLogger(__name__)


@dataclass
class CardState:
    """
    FSRS card state for persistence.

    This dataclass represents the scheduling state of a card,
    mapping to columns in the spaced_rep_cards table.

    Note: In fsrs v6+, "new" cards are represented as State.Learning with
    last_review=None. Use is_new() to check if a card is new.

    All datetimes are timezone-aware UTC (matching database TIMESTAMP WITH TIME ZONE).
    """

    state: State = State.Learning
    difficulty: Optional[float] = None  # 0-1, None for new cards
    stability: Optional[float] = None  # Days until 90% retention, None for new
    due: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_review: Optional[datetime] = None
    reps: int = 0  # Consecutive successful reviews
    lapses: int = 0  # Number of times forgotten
    scheduled_days: int = 0  # Days scheduled for next review

    def is_new(self) -> bool:
        """Check if this card has never been reviewed."""
        return self.last_review is None


@dataclass
class ReviewLog:
    """Log entry for a review event."""

    rating: Rating
    state_before: State
    state_after: State
    difficulty_before: float
    difficulty_after: float
    stability_before: float
    stability_after: float
    scheduled_days: int
    elapsed_days: float
    review_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FSRSScheduler:
    """
    FSRS Scheduler wrapper.

    Provides a clean interface to the FSRS algorithm for scheduling
    spaced repetition reviews.

    Attributes:
        desired_retention: Target retention probability (default 0.9 = 90%)
        maximum_interval: Maximum days between reviews (default 365)
    """

    def __init__(
        self,
        desired_retention: float = 0.9,
        maximum_interval: int = 365,
    ):
        """
        Initialize FSRS scheduler.

        Args:
            desired_retention: Target recall probability (0.7-0.99)
            maximum_interval: Maximum interval in days
        """
        self.desired_retention = desired_retention
        self.maximum_interval = maximum_interval

        self._fsrs = Scheduler(
            desired_retention=desired_retention,
            maximum_interval=maximum_interval,
        )

    def review(
        self,
        card_state: CardState,
        rating: Rating,
        review_time: Optional[datetime] = None,
    ) -> tuple[CardState, ReviewLog]:
        """
        Process a review and update card scheduling state using FSRS algorithm.

        This method takes the current card state and a user rating, then calculates
        the optimal next review time based on the FSRS-4.5 spaced repetition algorithm.
        The algorithm updates stability (memory strength) and difficulty based on
        the rating and elapsed time since last review.

        State Transitions:
            - New → Learning: First review of a new card
            - Learning → Review: Card graduates after successful reviews
            - Learning → Learning: Still learning (Again/Hard rating)
            - Review → Review: Successful review maintains review state
            - Review → Relearning: Lapse (Again rating) triggers relearning
            - Relearning → Review: Recovery after successful relearning

        Args:
            card_state: Current scheduling state of the card, including stability,
                difficulty, due date, and review history.
            rating: User's self-assessment of recall quality:
                - Rating.Again (1): Complete failure, reset to short interval
                - Rating.Hard (2): Recalled with significant difficulty
                - Rating.Good (3): Recalled with moderate effort (default)
                - Rating.Easy (4): Recalled effortlessly, increase interval
            review_time: Timestamp of the review. Defaults to current UTC time.
                Pass explicit time for batch processing or testing.

        Returns:
            Tuple containing:
                - CardState: Updated card state with new stability, difficulty,
                  due date, and incremented review counters.
                - ReviewLog: Detailed log of the review for analytics, including
                  before/after states and scheduling decisions.

        Example:
            >>> scheduler = FSRSScheduler(desired_retention=0.9)
            >>> card = CardState()  # New card
            >>> new_state, log = scheduler.review(card, Rating.Good)
            >>> print(f"Next review in {new_state.scheduled_days} days")
        """
        review_time = review_time or datetime.now(timezone.utc)

        # Convert to FSRS Card
        fsrs_card = FSRSCard()
        fsrs_card.state = card_state.state
        if card_state.difficulty is not None:
            fsrs_card.difficulty = card_state.difficulty
        if card_state.stability is not None:
            fsrs_card.stability = card_state.stability
        fsrs_card.due = card_state.due
        fsrs_card.last_review = card_state.last_review

        # Calculate elapsed days
        elapsed_days = 0.0
        if card_state.last_review:
            elapsed_days = (
                review_time - card_state.last_review
            ).total_seconds() / 86400

        # Review the card - returns (updated_card, review_log)
        result_card, _ = self._fsrs.review_card(fsrs_card, rating, review_time)

        # Calculate scheduled days
        scheduled_days = 0
        if result_card.due:
            scheduled_days = max(0, (result_card.due - review_time).days)

        new_state = CardState(
            state=result_card.state,
            difficulty=result_card.difficulty,
            stability=result_card.stability,
            due=result_card.due,
            last_review=review_time,
            reps=card_state.reps + 1,
            lapses=card_state.lapses + (1 if rating == Rating.Again and card_state.state == State.Review else 0),
            scheduled_days=scheduled_days,
        )

        log = ReviewLog(
            rating=rating,
            state_before=card_state.state,
            state_after=new_state.state,
            difficulty_before=card_state.difficulty,
            difficulty_after=new_state.difficulty,
            stability_before=card_state.stability,
            stability_after=new_state.stability,
            scheduled_days=scheduled_days,
            elapsed_days=elapsed_days,
            review_time=review_time,
        )

        return new_state, log

    def get_retrievability(
        self, card_state: CardState, now: Optional[datetime] = None
    ) -> float:
        """
        Get current recall probability for a card.

        Uses the FSRS library's built-in retrievability calculation based on
        the forgetting curve model.

        Args:
            card_state: Current card state with stability and last_review
            now: Reference time (default: current UTC time)

        Returns:
            Probability of recall (0.0 to 1.0). New cards return 1.0.
        """
        if card_state.is_new():
            return 1.0

        now = now or datetime.now(timezone.utc)

        # Build FSRS Card and use library's retrievability calculation
        fsrs_card = FSRSCard()
        fsrs_card.state = card_state.state
        fsrs_card.stability = card_state.stability
        fsrs_card.last_review = card_state.last_review

        return self._fsrs.get_card_retrievability(fsrs_card, now)


def create_scheduler(
    retention: float = 0.9,
    max_interval: int = 365,
) -> FSRSScheduler:
    """
    Create a configured FSRS scheduler.

    Args:
        retention: Target retention probability (default 0.9)
        max_interval: Maximum interval in days (default 365)

    Returns:
        Configured FSRSScheduler instance
    """
    return FSRSScheduler(
        desired_retention=retention,
        maximum_interval=max_interval,
    )


def get_review_forecast(
    cards: list[CardState],
    as_of: Optional[datetime] = None,
) -> dict[str, int]:
    """
    Get forecast of upcoming reviews.

    Args:
        cards: List of card states
        as_of: Reference time (default: now)

    Returns:
        Dict with counts: overdue, today, tomorrow, this_week, later
    """
    as_of = as_of or datetime.now(timezone.utc)
    today_start = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    forecast = {
        "overdue": 0,
        "today": 0,
        "tomorrow": 0,
        "this_week": 0,
        "later": 0,
    }

    for card in cards:
        if card.is_new():
            continue

        if card.due < today_start:
            forecast["overdue"] += 1
        elif card.due < tomorrow_start:
            forecast["today"] += 1
        elif card.due < tomorrow_start + timedelta(days=1):
            forecast["tomorrow"] += 1
        elif card.due < week_end:
            forecast["this_week"] += 1
        else:
            forecast["later"] += 1

    return forecast
