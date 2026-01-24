"""
Unit tests for SessionTimeBudget.

Tests the session budget calculation and time allocation logic.
"""

import pytest
from unittest.mock import patch

from app.services.learning.session_budget import SessionTimeBudget
from app.enums.learning import SessionContentMode


class TestSessionTimeBudget:
    """Tests for SessionTimeBudget class."""

    def test_exercises_only_mode_allocates_all_time_to_exercises(self):
        """Test that exercises_only mode gives all time to exercises."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        assert budget.exercise_budget == 30
        assert budget.card_budget == 0

    def test_cards_only_mode_allocates_all_time_to_cards(self):
        """Test that cards_only mode gives all time to cards."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.CARDS_ONLY,
        )

        assert budget.exercise_budget == 0
        assert budget.card_budget == 30

    def test_max_exercises_returns_zero_for_cards_only(self):
        """Test that max_exercises returns 0 for cards_only mode."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.CARDS_ONLY,
        )

        assert budget.max_exercises() == 0


class TestMaxExercisesWithMinimumTime:
    """Tests for the minimum time threshold logic in max_exercises."""

    @patch("app.services.learning.session_budget.settings")
    def test_allows_one_exercise_when_meeting_minimum_threshold(self, mock_settings):
        """
        Test that at least one exercise is allowed when budget meets minimum threshold,
        even if the math would normally return 0.
        
        This fixes the bug where a 5-minute session with 10-minute default exercise time
        would result in 0 exercises (int(5/10) = 0).
        """
        # Configure settings
        mock_settings.SESSION_TIME_PER_EXERCISE = 10.0  # 10 minutes default
        mock_settings.SESSION_MIN_TIME_FOR_EXERCISE = 5.0  # 5 min minimum threshold
        mock_settings.REVIEW_INTERLEAVE_FETCH_MULTIPLIER = 2
        mock_settings.REVIEW_INTERLEAVE_MAX_FETCH = 100

        budget = SessionTimeBudget(
            total_minutes=5,  # 5-minute session
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        # Should allow 1 exercise since 5 >= 5 (minimum threshold)
        # Previously this would return 0 (int(5/10) = 0)
        assert budget.max_exercises() >= 1

    @patch("app.services.learning.session_budget.settings")
    def test_returns_zero_when_below_minimum_threshold(self, mock_settings):
        """
        Test that 0 exercises are returned when below minimum threshold.
        """
        mock_settings.SESSION_TIME_PER_EXERCISE = 10.0
        mock_settings.SESSION_MIN_TIME_FOR_EXERCISE = 5.0  # 5 min minimum
        mock_settings.REVIEW_INTERLEAVE_FETCH_MULTIPLIER = 2
        mock_settings.REVIEW_INTERLEAVE_MAX_FETCH = 100

        budget = SessionTimeBudget(
            total_minutes=3,  # Only 3 minutes - below minimum
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        # Should return 0 since 3 < 5 (minimum threshold)
        assert budget.max_exercises() == 0

    @patch("app.services.learning.session_budget.settings")
    def test_returns_calculated_count_when_time_is_sufficient(self, mock_settings):
        """
        Test that calculated count is used when time is sufficient for multiple exercises.
        """
        mock_settings.SESSION_TIME_PER_EXERCISE = 10.0
        mock_settings.SESSION_MIN_TIME_FOR_EXERCISE = 5.0
        mock_settings.REVIEW_INTERLEAVE_FETCH_MULTIPLIER = 2
        mock_settings.REVIEW_INTERLEAVE_MAX_FETCH = 100

        budget = SessionTimeBudget(
            total_minutes=30,  # 30 minutes
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        # Should return 3 exercises (int(30/10) = 3)
        assert budget.max_exercises() == 3


class TestBudgetTracking:
    """Tests for budget consumption tracking."""

    def test_add_exercise_updates_consumed_time(self):
        """Test that adding exercises updates consumed time."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        budget.add_exercise(10)

        assert budget.exercise_consumed == 10
        assert budget.exercise_count == 1

    def test_can_fit_exercise_respects_budget(self):
        """Test that can_fit_exercise respects remaining budget."""
        budget = SessionTimeBudget(
            total_minutes=15,
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        # First exercise should fit
        can_fit, _ = budget.can_fit_exercise(10)
        assert can_fit is True

        # Add the exercise
        budget.add_exercise(10)

        # Second 10-minute exercise shouldn't fit (only 5 minutes left)
        can_fit, _ = budget.can_fit_exercise(10)
        assert can_fit is False
