"""
Streak and Practice History Tracking Service

Tracks practice streaks and provides activity history for heatmap visualizations.

Responsibilities:
- Calculate current and longest practice streaks
- Track practice milestones
- Provide daily practice history for heatmaps
- Activity level calculations for visualizations

Usage:
    from app.services.learning.streak_tracking import StreakTrackingService

    service = StreakTrackingService(db)
    streak = await service.get_streak_data()
    history = await service.get_practice_history(weeks=52)
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models_learning import (
    ExerciseAttempt,
    LearningTimeLog,
    PracticeSession,
    SpacedRepCard,
)
from app.models.learning import (
    PracticeHistoryDay,
    PracticeHistoryResponse,
    StreakData,
)


def calculate_activity_level(count: int, max_count: int) -> int:
    """
    Calculate activity level (0-4) based on count relative to max.

    Used for heatmap visualizations where higher levels indicate more activity.
    Thresholds are configured in settings (ACTIVITY_LEVEL_*).

    Args:
        count: Activity count for the day.
        max_count: Maximum activity count across all days.

    Returns:
        Activity level from 0 (no activity) to 4 (high activity).
    """
    if max_count == 0 or count == 0:
        return 0

    ratio = count / max_count
    if ratio >= settings.ACTIVITY_LEVEL_HIGH:
        return 4
    elif ratio >= settings.ACTIVITY_LEVEL_MEDIUM_HIGH:
        return 3
    elif ratio >= settings.ACTIVITY_LEVEL_MEDIUM:
        return 2
    else:
        return 1  # Any activity > 0


class StreakTrackingService:
    """
    Service for tracking practice streaks and activity history.

    Provides streak calculations and practice history data for
    gamification and visualization features.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the streak tracking service.

        Args:
            db: SQLAlchemy async database session.
        """
        self.db = db

    async def get_streak_data(self) -> StreakData:
        """
        Get detailed practice streak information.

        Calculates current streak, longest streak, milestones, and activity counts
        from PracticeSession records.

        Returns:
            StreakData with comprehensive streak information.
        """
        practice_dates = await self._fetch_practice_dates()

        if not practice_dates:
            return StreakData(
                current_streak=0,
                longest_streak=0,
                streak_start=None,
                last_practice=None,
                is_active_today=False,
                days_this_week=0,
                days_this_month=0,
                milestones_reached=[],
                next_milestone=7,
            )

        today = date.today()

        # Calculate streaks
        current_streak, streak_start = self._calculate_current_streak(
            practice_dates, today
        )
        longest_streak = self._calculate_longest_streak(practice_dates)

        # Milestones
        milestones = settings.STREAK_MILESTONES
        reached = [m for m in milestones if longest_streak >= m]
        next_milestone = next((m for m in milestones if m > current_streak), None)

        # Activity counts
        days_this_week = self._count_days_in_period(practice_dates, 7)
        days_this_month = self._count_days_in_period(practice_dates, 30)

        return StreakData(
            current_streak=current_streak,
            longest_streak=longest_streak,
            streak_start=streak_start,
            last_practice=practice_dates[0] if practice_dates else None,
            is_active_today=practice_dates[0] == today if practice_dates else False,
            days_this_week=days_this_week,
            days_this_month=days_this_month,
            milestones_reached=reached,
            next_milestone=next_milestone,
        )

    async def get_practice_history(self, weeks: int = 52) -> PracticeHistoryResponse:
        """
        Get practice history for activity heatmap.

        Returns daily practice activity for the specified number of weeks,
        combining both spaced repetition card reviews and exercise attempts.

        Args:
            weeks: Number of weeks of history to return (default 52).

        Returns:
            PracticeHistoryResponse with daily activity data.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(weeks=weeks)

        # Query daily practice counts from spaced repetition cards
        card_result = await self.db.execute(
            select(
                func.date(SpacedRepCard.last_reviewed).label("practice_date"),
                func.count(SpacedRepCard.id).label("count"),
            )
            .where(SpacedRepCard.last_reviewed >= cutoff)
            .group_by(func.date(SpacedRepCard.last_reviewed))
        )

        card_rows = {row[0]: row[1] for row in card_result.fetchall()}

        # Query daily exercise attempt counts
        exercise_result = await self.db.execute(
            select(
                func.date(ExerciseAttempt.attempted_at).label("practice_date"),
                func.count(ExerciseAttempt.id).label("count"),
            )
            .where(ExerciseAttempt.attempted_at >= cutoff)
            .group_by(func.date(ExerciseAttempt.attempted_at))
        )

        exercise_rows = {row[0]: row[1] for row in exercise_result.fetchall()}

        # Query daily practice time
        time_result = await self.db.execute(
            select(
                func.date(LearningTimeLog.started_at).label("practice_date"),
                func.sum(LearningTimeLog.duration_seconds).label("total_seconds"),
            )
            .where(LearningTimeLog.started_at >= cutoff)
            .group_by(func.date(LearningTimeLog.started_at))
        )

        time_rows = {row[0]: row[1] for row in time_result.fetchall()}

        # Combine all dates from cards and exercises
        all_dates = set(card_rows.keys()) | set(exercise_rows.keys())

        # Build response
        days = []
        max_count = 0
        total_items = 0

        for practice_date in sorted(all_dates):
            card_count = card_rows.get(practice_date, 0)
            exercise_count = exercise_rows.get(practice_date, 0)
            count = card_count + exercise_count
            minutes = (time_rows.get(practice_date, 0) or 0) // 60

            max_count = max(max_count, count)
            total_items += count

            days.append(
                PracticeHistoryDay(
                    date=practice_date,
                    count=count,
                    minutes=minutes,
                    level=0,  # Will be calculated below
                )
            )

        total_practice_days = len(days)

        # Calculate activity levels (0-4 based on count relative to max)
        for day in days:
            day.level = calculate_activity_level(day.count, max_count)

        return PracticeHistoryResponse(
            days=days,
            total_practice_days=total_practice_days,
            total_items=total_items,
            max_daily_count=max_count,
        )

    async def _fetch_practice_dates(self) -> list[date]:
        """
        Fetch distinct practice dates from completed sessions.

        Queries all completed PracticeSession records and extracts unique dates,
        ordered from most recent to oldest. Used for streak calculations.

        Returns:
            list[date]: List of unique practice dates in descending order (most recent first).
        """
        query = (
            select(func.date(PracticeSession.started_at).label("practice_date"))
            .where(PracticeSession.ended_at.isnot(None))
            .distinct()
            .order_by(func.date(PracticeSession.started_at).desc())
        )
        result = await self.db.execute(query)
        return [row.practice_date for row in result]

    @staticmethod
    def _calculate_current_streak(
        practice_dates: list[date], today: date
    ) -> tuple[int, Optional[date]]:
        """
        Calculate current consecutive practice streak.

        Counts consecutive practice days starting from today (or yesterday if no
        practice today). The streak remains valid if the user practiced yesterday
        but hasn't practiced today yet.

        Args:
            practice_dates: List of practice dates in descending order (most recent first).
            today: Current date for streak calculation reference.

        Returns:
            tuple[int, Optional[date]]: Tuple containing:
                - streak_count: Number of consecutive practice days.
                - streak_start_date: Date when the current streak began, or None if no streak.
        """
        if not practice_dates:
            return 0, None

        # Check if streak is still valid (practiced today or yesterday)
        most_recent = practice_dates[0]
        yesterday = today - timedelta(days=1)

        if most_recent != today and most_recent != yesterday:
            return 0, None

        # Count consecutive days
        streak = 0
        streak_start = None
        expected_date = most_recent

        for practice_date in practice_dates:
            if practice_date == expected_date:
                streak += 1
                streak_start = practice_date
                expected_date = expected_date - timedelta(days=1)
            elif practice_date < expected_date:
                # Gap in streak
                break

        return streak, streak_start

    @staticmethod
    def _calculate_longest_streak(practice_dates: list[date]) -> int:
        """
        Calculate the longest practice streak ever achieved.

        Scans through all practice dates to find the longest consecutive run.

        Args:
            practice_dates: List of practice dates in descending order (most recent first).

        Returns:
            int: Length of the longest consecutive practice streak.
        """
        if not practice_dates:
            return 0

        # Sort ascending for easier processing
        sorted_dates = sorted(set(practice_dates))

        longest = 1
        current = 1

        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] == sorted_dates[i - 1] + timedelta(days=1):
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    @staticmethod
    def _count_days_in_period(practice_dates: list[date], days: int) -> int:
        """
        Count unique practice days within a recent period.

        Args:
            practice_dates: List of practice dates (any order).
            days: Number of days to look back from today.

        Returns:
            int: Number of unique practice days within the period.
        """
        if not practice_dates:
            return 0
        cutoff = date.today() - timedelta(days=days)
        return len([d for d in set(practice_dates) if d >= cutoff])
