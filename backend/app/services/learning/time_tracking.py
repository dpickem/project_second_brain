"""
Time Investment Tracking Service

Tracks time spent on learning activities and provides aggregated
time investment analytics.

Responsibilities:
- Log learning time entries
- Aggregate time by topic and activity type
- Group time into configurable periods (day/week/month)
- Calculate time investment trends

Usage:
    from app.services.learning.time_tracking import TimeTrackingService

    service = TimeTrackingService(db)
    investment = await service.get_time_investment(TimePeriod.MONTH)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_learning import LearningTimeLog, PracticeSession
from app.enums.learning import TimePeriod, GroupBy
from app.models.learning import (
    LogTimeRequest,
    LogTimeResponse,
    TimeInvestmentPeriod,
    TimeInvestmentResponse,
)


class TimeTrackingService:
    """
    Service for tracking and analyzing learning time investment.

    Handles time logging and provides analytics on time spent across
    topics and activity types.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the time tracking service.

        Args:
            db: SQLAlchemy async database session.
        """
        self.db = db

    async def get_time_investment(
        self,
        period: TimePeriod = TimePeriod.MONTH,
        group_by: GroupBy = GroupBy.DAY,
    ) -> TimeInvestmentResponse:
        """
        Get time investment breakdown for learning activities.

        Aggregates time from LearningTimeLog and PracticeSession records,
        grouped by topic and activity type.

        Args:
            period: Time period to analyze.
            group_by: How to group the data.

        Returns:
            TimeInvestmentResponse with aggregated time data and trends.
        """
        end_date = datetime.now(timezone.utc)
        start_date = self._calculate_period_start(period, end_date)

        # Fetch time logs and sessions
        logs = await self._fetch_time_logs(start_date, end_date)
        sessions = await self._fetch_practice_sessions(start_date)

        # Calculate totals from logs
        total_seconds = sum(log.duration_seconds for log in logs)

        # Add session durations not already tracked in logs
        logged_session_ids = {log.session_id for log in logs if log.session_id}
        for session in sessions:
            if session.id not in logged_session_ids and session.duration_minutes:
                total_seconds += session.duration_minutes * 60

        total_minutes = total_seconds / 60

        # Aggregate by topic for top_topics
        topic_minutes = self._aggregate_by_topic(logs)

        # Group into periods
        periods = self._group_into_periods(logs, start_date, end_date, group_by)

        # Calculate daily average
        days = max((end_date - start_date).days, 1)
        daily_average = total_minutes / days

        # Get top topics
        top_topics = sorted(topic_minutes.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        # Calculate trend
        trend = self._calculate_time_trend(periods)

        return TimeInvestmentResponse(
            total_minutes=total_minutes,
            periods=periods,
            top_topics=top_topics,
            daily_average=daily_average,
            trend=trend,
        )

    async def log_learning_time(self, request: LogTimeRequest) -> LogTimeResponse:
        """
        Log time spent on a learning activity.

        Creates a LearningTimeLog record for time investment tracking.

        Args:
            request: Time log details including activity type, timestamps, etc.

        Returns:
            LogTimeResponse with created log ID and duration.

        Raises:
            ValueError: If ended_at is before started_at.
        """
        duration_seconds = int((request.ended_at - request.started_at).total_seconds())

        if duration_seconds < 0:
            raise ValueError("ended_at must be after started_at")

        log = LearningTimeLog(
            topic=request.topic,
            content_id=request.content_id,
            activity_type=request.activity_type,
            started_at=request.started_at,
            ended_at=request.ended_at,
            duration_seconds=duration_seconds,
            items_completed=request.items_completed,
            session_id=request.session_id,
        )

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return LogTimeResponse(
            id=log.id,
            duration_seconds=duration_seconds,
            message=f"Logged {duration_seconds // 60} minutes of {request.activity_type}",
        )

    @staticmethod
    def _calculate_period_start(period: TimePeriod, end_date: datetime) -> datetime:
        """
        Calculate start date based on time period.

        Maps TimePeriod enum values to timedelta offsets from the end date.
        For TimePeriod.ALL, returns a date far in the past (2020-01-01).

        Args:
            period: Time period enum specifying the range (WEEK, MONTH, QUARTER, YEAR, ALL).
            end_date: End date of the period (typically now).

        Returns:
            datetime: Start date for the specified period, timezone-aware (UTC).
        """
        period_map = {
            TimePeriod.WEEK: timedelta(days=7),
            TimePeriod.MONTH: timedelta(days=30),
            TimePeriod.QUARTER: timedelta(days=90),
            TimePeriod.YEAR: timedelta(days=365),
        }
        delta = period_map.get(period)
        if delta:
            return end_date - delta

        # TimePeriod.ALL - return very old date
        return datetime(2020, 1, 1, tzinfo=timezone.utc)

    async def _fetch_time_logs(
        self, start_date: datetime, end_date: datetime
    ) -> list[LearningTimeLog]:
        """
        Fetch learning time logs within date range.

        Queries LearningTimeLog records where the activity started after start_date.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (for reference, not used in query).

        Returns:
            list[LearningTimeLog]: List of time log records.
        """
        query = select(LearningTimeLog).where(LearningTimeLog.started_at >= start_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _fetch_practice_sessions(
        self, start_date: datetime
    ) -> list[PracticeSession]:
        """
        Fetch completed practice sessions after start date.

        Queries PracticeSession records that have an ended_at timestamp
        (i.e., completed sessions) and started after the given date.

        Args:
            start_date: Start of the date range (inclusive).

        Returns:
            list[PracticeSession]: List of completed practice session records.
        """
        query = select(PracticeSession).where(
            PracticeSession.started_at >= start_date,
            PracticeSession.ended_at.isnot(None),
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _aggregate_by_topic(logs: list[LearningTimeLog]) -> dict[str, float]:
        """
        Aggregate time logs by topic.

        Sums duration_seconds for each unique topic and converts to minutes.
        Logs without a topic are excluded from aggregation.

        Args:
            logs: List of LearningTimeLog records to aggregate.

        Returns:
            dict[str, float]: Mapping of topic path to total minutes spent.
        """
        topic_minutes: dict[str, float] = {}
        for log in logs:
            if log.topic:
                topic_minutes[log.topic] = (
                    topic_minutes.get(log.topic, 0) + log.duration_seconds / 60
                )
        return topic_minutes

    @staticmethod
    def _aggregate_by_activity(logs: list[LearningTimeLog]) -> dict[str, float]:
        """
        Aggregate time logs by activity type.

        Sums duration_seconds for each activity type (review, practice, reading, exercise)
        and converts to minutes.

        Args:
            logs: List of LearningTimeLog records to aggregate.

        Returns:
            dict[str, float]: Mapping of activity type to total minutes spent.
        """
        activity_minutes: dict[str, float] = {}
        for log in logs:
            activity_minutes[log.activity_type] = (
                activity_minutes.get(log.activity_type, 0) + log.duration_seconds / 60
            )
        return activity_minutes

    def _group_into_periods(
        self,
        logs: list[LearningTimeLog],
        start_date: datetime,
        end_date: datetime,
        group_by: GroupBy,
    ) -> list[TimeInvestmentPeriod]:
        """
        Group time logs into periods based on grouping strategy.

        For GroupBy.DAY, creates one TimeInvestmentPeriod per day in the range.
        For GroupBy.WEEK, creates one TimeInvestmentPeriod per 7-day period.
        For GroupBy.MONTH, creates one TimeInvestmentPeriod per calendar month.

        Args:
            logs: List of LearningTimeLog records to group.
            start_date: Start of the date range (timezone-aware UTC).
            end_date: End of the date range (timezone-aware UTC).
            group_by: Grouping strategy (DAY, WEEK, or MONTH).

        Returns:
            list[TimeInvestmentPeriod]: List of period objects with time breakdowns.
        """
        periods: list[TimeInvestmentPeriod] = []

        if group_by == GroupBy.DAY:
            period_delta: Optional[timedelta] = timedelta(days=1)
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif group_by == GroupBy.WEEK:
            period_delta = timedelta(days=7)
            # Align to start of week (Monday)
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days_since_monday = current.weekday()
            current = current - timedelta(days=days_since_monday)
        else:  # GroupBy.MONTH
            # Start at first day of the start_date's month
            current = start_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            period_delta = None  # Handled specially for months

        while current < end_date:
            if group_by == GroupBy.MONTH:
                # Calculate end of current month
                if current.month == 12:
                    period_end = current.replace(year=current.year + 1, month=1)
                else:
                    period_end = current.replace(month=current.month + 1)
            else:
                assert period_delta is not None
                period_end = current + period_delta

            # Cap period_end at end_date
            effective_end = min(period_end, end_date)

            # Filter logs for this period
            period_logs = [
                log for log in logs if current <= log.started_at < effective_end
            ]

            # Aggregate by topic and activity for this period
            period_topic_mins = self._aggregate_by_topic(period_logs)
            period_activity_mins = self._aggregate_by_activity(period_logs)
            period_total = sum(log.duration_seconds for log in period_logs) / 60

            periods.append(
                TimeInvestmentPeriod(
                    period_start=current,
                    period_end=effective_end,
                    total_minutes=period_total,
                    by_topic=period_topic_mins,
                    by_activity=period_activity_mins,
                )
            )

            current = period_end

        return periods

    @staticmethod
    def _calculate_time_trend(periods: list[TimeInvestmentPeriod]) -> str:
        """
        Calculate trend from time investment periods.

        Compares average time investment between first half and second half of periods.
        Returns "increasing" if second half is >10% higher, "decreasing" if >10% lower,
        otherwise "stable".

        Args:
            periods: List of TimeInvestmentPeriod objects ordered chronologically.

        Returns:
            str: Trend indicator - "increasing", "decreasing", or "stable".
        """
        if len(periods) < 2:
            return "stable"

        mid = len(periods) // 2
        first_half_avg = sum(p.total_minutes for p in periods[:mid]) / max(mid, 1)
        second_half_avg = sum(p.total_minutes for p in periods[mid:]) / max(
            len(periods) - mid, 1
        )

        if second_half_avg > first_half_avg * 1.1:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            return "decreasing"

        return "stable"
