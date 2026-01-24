"""
Session Time Budget Manager

Handles all time allocation logic for practice sessions, including:
- Calculating time budgets for exercises vs cards
- Tracking consumed time and remaining budget
- Determining how many items can fit in remaining time

This class encapsulates the complex budgeting logic that was previously
scattered throughout SessionService.create_session().

Usage:
    budget = SessionTimeBudget(
        total_minutes=30,
        content_mode=SessionContentMode.BOTH,
        exercise_ratio=0.6,
        topic_selected=True,
    )

    # Check available budget
    print(f"Exercise budget: {budget.exercise_budget} min")
    print(f"Card budget: {budget.card_budget} min")

    # Consume time as items are added
    budget.add_exercise(estimated_minutes=10)
    budget.add_card(estimated_minutes=2)

    # Check remaining capacity
    can_fit, reason = budget.can_fit_exercise(10)
    print(f"Can fit 10min exercise: {can_fit} ({reason})")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.config.settings import settings
from app.enums.learning import SessionContentMode, ContentSourcePreference

logger = logging.getLogger(__name__)


@dataclass
class SessionTimeBudget:
    """
    Manages time budget allocation for practice sessions.

    Tracks total duration, allocated budgets for each content type,
    and consumed time as items are added to the session.

    Attributes:
        total_minutes: Total session duration in minutes
        content_mode: What types of content to include
        exercise_ratio: Ratio of time allocated to exercises (0-1)
        topic_selected: Whether a specific topic was selected (affects allocation)
        exercise_budget: Minutes allocated for exercises
        card_budget: Minutes allocated for cards
        exercise_consumed: Minutes consumed by added exercises
        card_consumed: Minutes consumed by added cards
    """

    total_minutes: float
    content_mode: SessionContentMode = SessionContentMode.BOTH
    exercise_ratio: Optional[float] = None
    topic_selected: bool = False

    # Calculated budgets (set in __post_init__)
    exercise_budget: float = field(init=False)
    card_budget: float = field(init=False)

    # Consumed time tracking
    exercise_consumed: float = field(default=0.0, init=False)
    card_consumed: float = field(default=0.0, init=False)

    # Item counts
    exercise_count: int = field(default=0, init=False)
    card_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate initial time budgets based on content mode and ratios."""
        self._calculate_budgets()

    def _calculate_budgets(self):
        """Calculate time budgets for exercises and cards."""
        # Handle content mode
        if self.content_mode == SessionContentMode.EXERCISES_ONLY:
            self.exercise_budget = self.total_minutes
            self.card_budget = 0.0
            return
        elif self.content_mode == SessionContentMode.CARDS_ONLY:
            self.exercise_budget = 0.0
            self.card_budget = self.total_minutes
            return

        # Both content types - determine ratio
        if self.exercise_ratio is not None:
            # Use provided ratio
            ex_ratio = self.exercise_ratio
        elif self.topic_selected:
            # Topic-focused: prioritize exercises
            ex_ratio = settings.SESSION_TOPIC_EXERCISE_RATIO
        else:
            # General session: use standard ratios
            # Exercises = weak spots + new content
            ex_ratio = (
                settings.SESSION_TIME_RATIO_WEAK_SPOTS
                + settings.SESSION_TIME_RATIO_NEW_CONTENT
            )

        self.exercise_budget = self.total_minutes * ex_ratio
        self.card_budget = self.total_minutes * (1 - ex_ratio)

        logger.debug(
            f"Budget calculated: total={self.total_minutes}min, "
            f"exercises={self.exercise_budget:.1f}min ({ex_ratio:.0%}), "
            f"cards={self.card_budget:.1f}min ({1-ex_ratio:.0%})"
        )

    @property
    def exercise_remaining(self) -> float:
        """Remaining time budget for exercises."""
        return max(0, self.exercise_budget - self.exercise_consumed)

    @property
    def card_remaining(self) -> float:
        """Remaining time budget for cards."""
        return max(0, self.card_budget - self.card_consumed)

    @property
    def total_remaining(self) -> float:
        """Total remaining time in session."""
        return max(0, self.total_minutes - self.total_consumed)

    @property
    def total_consumed(self) -> float:
        """Total time consumed by all items."""
        return self.exercise_consumed + self.card_consumed

    @property
    def is_full(self) -> bool:
        """Whether the session budget is fully consumed."""
        return self.total_remaining < min(
            settings.SESSION_MIN_TIME_FOR_EXERCISE,
            settings.SESSION_MIN_TIME_FOR_CARD,
        )

    def max_exercises(self, time_per_exercise: Optional[float] = None) -> int:
        """
        Calculate maximum number of exercises that can fit.

        Args:
            time_per_exercise: Estimated time per exercise (uses setting default)

        Returns:
            Maximum number of exercises that fit in remaining budget
        """
        if self.content_mode == SessionContentMode.CARDS_ONLY:
            return 0

        time = time_per_exercise or settings.SESSION_TIME_PER_EXERCISE
        available = self.exercise_remaining

        # Also consider total remaining (can overflow into card budget if needed)
        if settings.SESSION_MIN_TIME_FOR_EXERCISE <= self.total_remaining:
            available = max(available, self.total_remaining)

        # Calculate how many exercises fit
        count = int(available / time)

        # Allow at least one exercise if we meet the minimum time threshold
        # This prevents 0 exercises for short sessions (e.g., 5 min with 10 min default)
        if count == 0 and available >= settings.SESSION_MIN_TIME_FOR_EXERCISE:
            count = 1

        return max(0, count)

    def max_cards(self, time_per_card: Optional[float] = None) -> int:
        """
        Calculate maximum number of cards that can fit.

        Args:
            time_per_card: Estimated time per card (uses setting default)

        Returns:
            Maximum number of cards that fit in remaining budget
        """
        if self.content_mode == SessionContentMode.EXERCISES_ONLY:
            return 0

        time = time_per_card or settings.SESSION_TIME_PER_CARD
        available = self.card_remaining

        # Also consider total remaining (can overflow into exercise budget if needed)
        if settings.SESSION_MIN_TIME_FOR_CARD <= self.total_remaining:
            available = max(available, self.total_remaining)

        return max(0, int(available / time))

    def can_fit_exercise(
        self,
        estimated_minutes: float,
        allow_overflow: bool = True,
    ) -> tuple[bool, str]:
        """
        Check if an exercise can fit in the remaining budget.

        Args:
            estimated_minutes: Estimated time for the exercise
            allow_overflow: Whether to allow using card budget overflow

        Returns:
            Tuple of (can_fit, reason)
        """
        if self.content_mode == SessionContentMode.CARDS_ONLY:
            return False, "Content mode is cards_only"

        # Check minimum threshold
        if estimated_minutes < settings.SESSION_MIN_TIME_FOR_EXERCISE:
            # Exercise is below minimum, allow anyway
            pass

        # Check exercise budget
        if estimated_minutes <= self.exercise_remaining:
            return True, "Fits in exercise budget"

        # Check overflow
        if allow_overflow and estimated_minutes <= self.total_remaining:
            return True, "Fits in remaining session time (overflow)"

        return (
            False,
            f"Insufficient time: need {estimated_minutes}min, have {self.total_remaining:.1f}min",
        )

    def can_fit_card(
        self,
        estimated_minutes: float,
        allow_overflow: bool = True,
    ) -> tuple[bool, str]:
        """
        Check if a card can fit in the remaining budget.

        Args:
            estimated_minutes: Estimated time for the card
            allow_overflow: Whether to allow using exercise budget overflow

        Returns:
            Tuple of (can_fit, reason)
        """
        if self.content_mode == SessionContentMode.EXERCISES_ONLY:
            return False, "Content mode is exercises_only"

        # Check card budget
        if estimated_minutes <= self.card_remaining:
            return True, "Fits in card budget"

        # Check overflow
        if allow_overflow and estimated_minutes <= self.total_remaining:
            return True, "Fits in remaining session time (overflow)"

        return (
            False,
            f"Insufficient time: need {estimated_minutes}min, have {self.total_remaining:.1f}min",
        )

    def add_exercise(self, estimated_minutes: float) -> bool:
        """
        Add an exercise and consume its time budget.

        Args:
            estimated_minutes: Time estimate for the exercise

        Returns:
            True if added successfully, False if no room
        """
        can_fit, _ = self.can_fit_exercise(estimated_minutes)
        if not can_fit:
            return False

        self.exercise_consumed += estimated_minutes
        self.exercise_count += 1
        return True

    def add_card(self, estimated_minutes: float) -> bool:
        """
        Add a card and consume its time budget.

        Args:
            estimated_minutes: Time estimate for the card

        Returns:
            True if added successfully, False if no room
        """
        can_fit, _ = self.can_fit_card(estimated_minutes)
        if not can_fit:
            return False

        self.card_consumed += estimated_minutes
        self.card_count += 1
        return True

    def summary(self) -> dict:
        """Get a summary of the budget state."""
        return {
            "total_minutes": self.total_minutes,
            "content_mode": self.content_mode.value,
            "exercise_budget": self.exercise_budget,
            "card_budget": self.card_budget,
            "exercise_consumed": self.exercise_consumed,
            "card_consumed": self.card_consumed,
            "exercise_remaining": self.exercise_remaining,
            "card_remaining": self.card_remaining,
            "total_remaining": self.total_remaining,
            "exercise_count": self.exercise_count,
            "card_count": self.card_count,
            "is_full": self.is_full,
        }


def resolve_content_mode(
    request_mode: Optional[SessionContentMode],
) -> SessionContentMode:
    """
    Resolve content mode from request or settings default.

    Args:
        request_mode: Mode from request (may be None)

    Returns:
        Resolved SessionContentMode
    """
    if request_mode is not None:
        return request_mode

    default = settings.SESSION_DEFAULT_CONTENT_MODE
    try:
        return SessionContentMode(default)
    except ValueError:
        logger.warning(f"Invalid SESSION_DEFAULT_CONTENT_MODE: {default}, using 'both'")
        return SessionContentMode.BOTH


def resolve_exercise_source(
    request_source: Optional[ContentSourcePreference],
) -> ContentSourcePreference:
    """
    Resolve exercise source preference from request or settings.

    Args:
        request_source: Source preference from request (may be None)

    Returns:
        Resolved ContentSourcePreference
    """
    if request_source is not None:
        return request_source

    default = settings.SESSION_DEFAULT_EXERCISE_SOURCE
    try:
        return ContentSourcePreference(default)
    except ValueError:
        logger.warning(
            f"Invalid SESSION_DEFAULT_EXERCISE_SOURCE: {default}, using 'prefer_existing'"
        )
        return ContentSourcePreference.PREFER_EXISTING


def resolve_card_source(
    request_source: Optional[ContentSourcePreference],
) -> ContentSourcePreference:
    """
    Resolve card source preference from request or settings.

    Args:
        request_source: Source preference from request (may be None)

    Returns:
        Resolved ContentSourcePreference
    """
    if request_source is not None:
        return request_source

    default = settings.SESSION_DEFAULT_CARD_SOURCE
    try:
        return ContentSourcePreference(default)
    except ValueError:
        logger.warning(
            f"Invalid SESSION_DEFAULT_CARD_SOURCE: {default}, using 'prefer_existing'"
        )
        return ContentSourcePreference.PREFER_EXISTING
