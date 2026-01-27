"""
Unit Tests for Analytics Endpoints.

Tests for:
- Streak calculation logic (longest streak, days in period)
- Time investment trend calculations
- Start date calculation for different time periods
- Pydantic model validation (StreakData, TimeInvestmentResponse)

These tests verify the static helper methods in MasteryService and the
Pydantic models used for analytics API responses.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from app.enums.learning import TimePeriod
from app.models.learning import (
    StreakData,
    TimeInvestmentPeriod,
    TimeInvestmentResponse,
)
from app.services.learning.streak_tracking import StreakTrackingService
from app.services.learning.time_tracking import TimeTrackingService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def today() -> date:
    """Return today's date for consistent test data."""
    return date.today()


@pytest.fixture
def now_utc() -> datetime:
    """Return current datetime in UTC for consistent test data."""
    return datetime.now(timezone.utc)


@pytest.fixture
def consecutive_dates(today: date) -> list[date]:
    """Return 5 consecutive days ending today."""
    return [today - timedelta(days=i) for i in range(5)]


@pytest.fixture
def dates_with_gap(today: date) -> list[date]:
    """Return dates with a gap: 3 consecutive days, gap, then 2 more days."""
    return [
        today,
        today - timedelta(days=1),
        today - timedelta(days=2),
        # gap of 2 days
        today - timedelta(days=5),
        today - timedelta(days=6),
    ]


@pytest.fixture
def dates_with_multiple_streaks(today: date) -> list[date]:
    """Return dates with two streaks: 2-day streak and 4-day streak (longer)."""
    return [
        # First streak: 2 days
        today - timedelta(days=0),
        today - timedelta(days=1),
        # Gap
        # Second streak: 4 days (longest)
        today - timedelta(days=5),
        today - timedelta(days=6),
        today - timedelta(days=7),
        today - timedelta(days=8),
    ]


def make_time_period(
    now: datetime, days_offset: int, total_minutes: float
) -> TimeInvestmentPeriod:
    """
    Create a TimeInvestmentPeriod for testing.

    Args:
        now: Reference datetime (UTC).
        days_offset: Days before 'now' for the period start.
        total_minutes: Total minutes for this period.

    Returns:
        TimeInvestmentPeriod spanning one day at the given offset.
    """
    start = now - timedelta(days=days_offset)
    end = now - timedelta(days=days_offset - 1)
    return TimeInvestmentPeriod(
        period_start=start,
        period_end=end,
        total_minutes=total_minutes,
    )


# =============================================================================
# Streak Calculation Tests
# =============================================================================


class TestCalculateLongestStreak:
    """Tests for StreakTrackingService._calculate_longest_streak static method."""

    @pytest.mark.parametrize(
        "dates,expected",
        [
            pytest.param([], 0, id="empty_returns_0"),
            pytest.param([date.today()], 1, id="single_day_returns_1"),
        ],
    )
    def test_edge_cases(self, dates: list[date], expected: int) -> None:
        """Test edge cases: empty list and single date."""
        result = StreakTrackingService._calculate_longest_streak(dates)
        assert result == expected

    def test_consecutive_days(self, consecutive_dates: list[date]) -> None:
        """Consecutive days returns correct streak length."""
        result = StreakTrackingService._calculate_longest_streak(consecutive_dates)
        assert result == 5

    def test_gap_ends_streak(self, dates_with_gap: list[date]) -> None:
        """Gap in dates ends the current streak and starts a new one."""
        result = StreakTrackingService._calculate_longest_streak(dates_with_gap)
        assert result == 3  # First 3 consecutive days

    def test_returns_longest_of_multiple_streaks(
        self, dates_with_multiple_streaks: list[date]
    ) -> None:
        """Returns the longest streak when multiple exist."""
        result = StreakTrackingService._calculate_longest_streak(dates_with_multiple_streaks)
        assert result == 4  # Second streak is longer


class TestCountDaysInPeriod:
    """Tests for StreakTrackingService._count_days_in_period static method."""

    def test_empty_dates_returns_0(self) -> None:
        """Empty dates list returns 0."""
        result = StreakTrackingService._count_days_in_period([], 7)
        assert result == 0

    def test_counts_days_within_window(self, today: date) -> None:
        """Counts only days within the specified window."""
        dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=3),
            today - timedelta(days=10),  # Outside 7-day window
        ]
        result = StreakTrackingService._count_days_in_period(dates, 7)
        assert result == 3  # Only first 3 are within the window


# =============================================================================
# Trend Calculation Tests
# =============================================================================


class TestCalculateTimeTrend:
    """Tests for TimeTrackingService._calculate_time_trend static method."""

    @pytest.mark.parametrize(
        "minutes_sequence,expected_trend",
        [
            pytest.param([30, 32, 30, 31], "stable", id="similar_values_stable"),
            pytest.param([10, 15, 40, 50], "increasing", id="increasing_second_half"),
            pytest.param([50, 45, 10, 5], "decreasing", id="decreasing_second_half"),
        ],
    )
    def test_trend_calculation(
        self, now_utc: datetime, minutes_sequence: list[float], expected_trend: str
    ) -> None:
        """
        Trend is calculated by comparing first half vs second half averages.

        - 'stable': second half is within ±10% of first half
        - 'increasing': second half is >10% higher than first half
        - 'decreasing': second half is >10% lower than first half
        """
        periods = [
            make_time_period(
                now_utc, days_offset=len(minutes_sequence) - i, total_minutes=m
            )
            for i, m in enumerate(minutes_sequence)
        ]
        result = TimeTrackingService._calculate_time_trend(periods)
        assert result == expected_trend

    def test_single_period_returns_stable(self, now_utc: datetime) -> None:
        """Single period always returns 'stable' (not enough data)."""
        periods = [make_time_period(now_utc, days_offset=1, total_minutes=30)]
        result = TimeTrackingService._calculate_time_trend(periods)
        assert result == "stable"

    def test_empty_periods_returns_stable(self) -> None:
        """Empty periods list returns 'stable'."""
        result = TimeTrackingService._calculate_time_trend([])
        assert result == "stable"


# =============================================================================
# Period Start Date Calculation Tests
# =============================================================================


class TestCalculatePeriodStart:
    """Tests for TimeTrackingService._calculate_period_start static method."""

    @pytest.mark.parametrize(
        "period,expected_days_ago",
        [
            pytest.param(TimePeriod.WEEK, 7, id="week_is_7_days"),
            pytest.param(TimePeriod.MONTH, 30, id="month_is_30_days"),
            pytest.param(TimePeriod.QUARTER, 90, id="quarter_is_90_days"),
            pytest.param(TimePeriod.YEAR, 365, id="year_is_365_days"),
        ],
    )
    def test_period_calculation(
        self, period: TimePeriod, expected_days_ago: int
    ) -> None:
        """Each TimePeriod maps to the correct number of days."""
        end_date = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        result = TimeTrackingService._calculate_period_start(period, end_date)

        expected = end_date - timedelta(days=expected_days_ago)
        assert result == expected

    def test_all_returns_2020(self) -> None:
        """TimePeriod.ALL returns a date in 2020 (effectively 'all time')."""
        end_date = datetime(2026, 1, 7, 0, 0, 0, tzinfo=timezone.utc)
        result = TimeTrackingService._calculate_period_start(TimePeriod.ALL, end_date)

        assert result.year == 2020
        assert result.tzinfo == timezone.utc


# =============================================================================
# Pydantic Model Tests
# =============================================================================


class TestStreakDataModel:
    """Tests for StreakData Pydantic model validation and defaults."""

    def test_defaults(self) -> None:
        """StreakData has correct default values for optional fields."""
        data = StreakData(
            current_streak=0,
            longest_streak=0,
            is_active_today=False,
            days_this_week=0,
            days_this_month=0,
        )

        assert data.milestones_reached == []
        assert data.next_milestone is None
        assert data.streak_start is None
        assert data.last_practice is None

    def test_with_milestones(self) -> None:
        """StreakData correctly stores milestone data."""
        data = StreakData(
            current_streak=15,
            longest_streak=35,
            is_active_today=True,
            days_this_week=5,
            days_this_month=15,
            milestones_reached=[7, 14, 30],
            next_milestone=60,
        )

        assert 7 in data.milestones_reached
        assert 14 in data.milestones_reached
        assert 30 in data.milestones_reached
        assert data.next_milestone == 60


class TestTimeInvestmentResponseModel:
    """Tests for TimeInvestmentResponse Pydantic model."""

    def test_creation_with_periods(self, now_utc: datetime) -> None:
        """TimeInvestmentResponse creates correctly with nested period data."""
        period = TimeInvestmentPeriod(
            period_start=now_utc - timedelta(days=1),
            period_end=now_utc,
            total_minutes=60.5,
            by_topic={"ml": 30.0, "web": 30.5},
            by_activity={"review": 40.0, "exercise": 20.5},
        )

        response = TimeInvestmentResponse(
            total_minutes=120.5,
            periods=[period],
            top_topics=[("ml", 60.0), ("web", 30.5)],
            daily_average=15.0,
            trend="stable",
        )

        assert response.total_minutes == 120.5
        assert len(response.periods) == 1
        assert response.periods[0].by_topic["ml"] == 30.0
        assert response.top_topics[0] == ("ml", 60.0)
        assert response.daily_average == 15.0
        assert response.trend == "stable"

    @pytest.mark.parametrize(
        "trend",
        [
            pytest.param("stable", id="stable"),
            pytest.param("increasing", id="increasing"),
            pytest.param("decreasing", id="decreasing"),
        ],
    )
    def test_valid_trend_values(self, trend: str) -> None:
        """TimeInvestmentResponse accepts all valid trend values."""
        response = TimeInvestmentResponse(
            total_minutes=0,
            periods=[],
            top_topics=[],
            daily_average=0,
            trend=trend,
        )
        assert response.trend == trend
