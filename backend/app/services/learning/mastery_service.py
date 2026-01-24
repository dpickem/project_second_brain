"""
Mastery Tracking Service

Tracks and calculates mastery scores per topic based on:
- Spaced repetition card performance
- Exercise attempt results
- Practice frequency and recency

Mastery Calculation:
- 60% from success rate (correct_reviews / total_reviews)
- 40% from average stability (normalized: avg_stability / 30 days)

Usage:
    from app.services.learning.mastery_service import MasteryService

    service = MasteryService(db)

    # Get mastery for a topic
    state = await service.get_mastery_state("ml/transformers")

    # Get weak spots
    weak_spots = await service.get_weak_spots(limit=5)

    # Take daily snapshot
    await service.take_daily_snapshot()
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlalchemy import select, func, and_, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models_learning import (
    SpacedRepCard,
    MasterySnapshot,
    PracticeSession,
    LearningTimeLog,
    ExerciseAttempt,
    Exercise,
    CardReviewHistory,
)
from app.enums.learning import (
    MasteryTrend,
    ExerciseType,
    CardState,
    TimePeriod,
    GroupBy,
)
from app.services.learning.exercise_generator import get_suggested_exercise_types
from app.services.tag_service import TagService
from app.models.learning import (
    DailyStatsResponse,
    LearningCurveDataPoint,
    LearningCurveResponse,
    LogTimeRequest,
    LogTimeResponse,
    MasteryOverview,
    MasteryState,
    PracticeHistoryDay,
    PracticeHistoryResponse,
    StreakData,
    TimeInvestmentPeriod,
    TimeInvestmentResponse,
    WeakSpot,
)

logger = logging.getLogger(__name__)


def _calculate_activity_level(count: int, max_count: int) -> int:
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


def _calculate_trend(current_score: float, previous_score: float) -> MasteryTrend:
    """
    Calculate mastery trend based on score delta.

    Args:
        current_score: Current mastery score (0-1).
        previous_score: Previous mastery score (0-1).

    Returns:
        IMPROVING if delta > threshold, DECLINING if < -threshold, else STABLE.
    """
    delta = current_score - previous_score
    threshold = settings.MASTERY_TREND_THRESHOLD

    if delta > threshold:
        return MasteryTrend.IMPROVING
    elif delta < -threshold:
        return MasteryTrend.DECLINING

    return MasteryTrend.STABLE


class MasteryService:
    """
    Mastery tracking and analytics service.

    Provides per-topic mastery calculation, weak spot detection,
    daily snapshot generation, and learning curve data.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize mastery service.

        Args:
            db: Async database session for queries.
        """
        self.db = db

    async def get_mastery_state(self, topic: str) -> MasteryState:
        """
        Get mastery state for a topic.

        Returns cached snapshot if available, otherwise calculates fresh.

        Args:
            topic: Topic path (e.g., "ml/transformers").

        Returns:
            MasteryState with score, trend, and practice statistics.
        """
        # Check for recent snapshot first
        recent_snapshot = await self._get_recent_snapshot(topic)

        if recent_snapshot:
            return self._snapshot_to_state(recent_snapshot)

        # Calculate fresh
        return await self._calculate_mastery(topic)

    async def get_weak_spots(self, limit: int = 10) -> list[WeakSpot]:
        """
        Get topics identified as weak spots needing practice.

        Finds topics with mastery < WEAK_SPOT_THRESHOLD and sufficient practice
        attempts. Results sorted by declining trends first, then lowest mastery.

        Args:
            limit: Maximum number of weak spots to return.

        Returns:
            List of WeakSpot objects with recommendations and suggested exercises.
        """
        # Get all topics and calculate mastery in batch (2 queries instead of N)
        topics = await self._get_all_topics()
        all_states = await self._calculate_mastery_batch(topics)

        # Filter to weak spots
        weak_spots = []
        for state in all_states:
            if (
                state.practice_count >= settings.MASTERY_MIN_ATTEMPTS
                and state.mastery_score < settings.MASTERY_WEAK_SPOT_THRESHOLD
            ):
                weak_spots.append(
                    WeakSpot(
                        topic=state.topic_path,
                        mastery_score=state.mastery_score,
                        success_rate=state.success_rate,
                        trend=state.trend,
                        recommendation=self._generate_recommendation(state),
                        suggested_exercise_types=self._suggest_exercise_types(state),
                    )
                )

        # Sort: declining trend first, then lowest mastery
        weak_spots.sort(
            key=lambda w: (
                w.trend != MasteryTrend.DECLINING,  # Declining first
                w.mastery_score,  # Then lowest mastery
            )
        )

        return weak_spots[:limit]

    async def get_overview(self) -> MasteryOverview:
        """
        Get overall mastery statistics.

        Aggregates card/exercise counts, topic mastery states,
        overall mastery average, and current practice streak.

        Returns:
            MasteryOverview with comprehensive learning statistics including
            separate breakdowns for spaced repetition cards and exercises.
        """
        # ==== SPACED REPETITION CARDS STATS ====

        # Total spaced rep cards
        total_spaced_cards_result = await self.db.execute(
            select(func.count(SpacedRepCard.id))
        )
        spaced_rep_cards_total = total_spaced_cards_result.scalar() or 0

        # Mastered cards (stability >= threshold)
        spaced_mastered_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                SpacedRepCard.stability >= settings.MASTERY_MASTERED_STABILITY_DAYS
            )
        )
        spaced_rep_cards_mastered = spaced_mastered_result.scalar() or 0

        # Learning cards (in learning/relearning/review but not yet mastered)
        spaced_learning_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                and_(
                    SpacedRepCard.state.in_(
                        [CardState.LEARNING, CardState.RELEARNING, CardState.REVIEW]
                    ),
                    SpacedRepCard.stability < settings.MASTERY_MASTERED_STABILITY_DAYS,
                )
            )
        )
        spaced_rep_cards_learning = spaced_learning_result.scalar() or 0

        # New cards (never reviewed)
        spaced_new_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                SpacedRepCard.state == CardState.NEW
            )
        )
        spaced_rep_cards_new = spaced_new_result.scalar() or 0

        # Total reviews on spaced rep cards
        spaced_reviews_result = await self.db.execute(
            select(func.sum(SpacedRepCard.total_reviews))
        )
        spaced_rep_reviews_total = spaced_reviews_result.scalar() or 0

        # ==== EXERCISES STATS ====

        # Total exercises
        exercises_total_result = await self.db.execute(select(func.count(Exercise.id)))
        exercises_total = exercises_total_result.scalar() or 0

        # Exercises with at least one attempt (completed)
        exercises_completed_result = await self.db.execute(
            select(func.count(distinct(ExerciseAttempt.exercise_id)))
        )
        exercises_completed = exercises_completed_result.scalar() or 0

        # Exercises with avg score >= threshold (mastered)
        exercises_mastered_result = await self.db.execute(
            select(func.count(distinct(ExerciseAttempt.exercise_id))).where(
                ExerciseAttempt.score >= settings.EXERCISE_MASTERY_SCORE_THRESHOLD
            )
        )
        exercises_mastered = exercises_mastered_result.scalar() or 0

        # Total exercise attempts
        exercises_attempts_result = await self.db.execute(
            select(func.count(ExerciseAttempt.id))
        )
        exercises_attempts_total = exercises_attempts_result.scalar() or 0

        # Average score across all exercise attempts
        exercises_avg_result = await self.db.execute(
            select(func.avg(ExerciseAttempt.score))
        )
        exercises_avg_score = exercises_avg_result.scalar() or 0.0

        # ==== TOPIC MASTERY STATES ====

        topics = await self._get_all_topics()
        topics_to_calculate = topics[: settings.MASTERY_MAX_TOPICS_IN_OVERVIEW]
        topic_states = await self._calculate_mastery_batch(topics_to_calculate)

        # Enhance topic states with exercise attempt data
        topic_states = await self._enhance_with_exercise_data(topic_states)

        # Compute overall mastery as average across all topics
        if topic_states:
            overall_mastery = sum(s.mastery_score for s in topic_states) / len(
                topic_states
            )
        else:
            overall_mastery = 0.0

        # ==== PRACTICE STREAK & TIME ====

        streak_days = await self._calculate_streak()

        # Get time from practice sessions
        practice_time_result = await self.db.execute(
            select(func.sum(PracticeSession.duration_minutes)).where(
                PracticeSession.ended_at.isnot(None)
            )
        )
        total_practice_minutes = practice_time_result.scalar() or 0

        # Also include time from card reviews (CardReviewHistory.time_spent_seconds)
        card_review_time_result = await self.db.execute(
            select(func.sum(CardReviewHistory.time_spent_seconds))
        )
        total_card_review_seconds = card_review_time_result.scalar() or 0
        total_card_review_minutes = total_card_review_seconds / 60.0

        # Combined total
        total_practice_time_hours = (total_practice_minutes + total_card_review_minutes) / 60.0

        # ==== RETURN COMPLETE OVERVIEW ====

        return MasteryOverview(
            overall_mastery=overall_mastery,
            topics=topic_states,
            # Spaced rep card stats
            spaced_rep_cards_total=spaced_rep_cards_total,
            spaced_rep_cards_mastered=spaced_rep_cards_mastered,
            spaced_rep_cards_learning=spaced_rep_cards_learning,
            spaced_rep_cards_new=spaced_rep_cards_new,
            spaced_rep_reviews_total=spaced_rep_reviews_total,
            # Exercise stats
            exercises_total=exercises_total,
            exercises_completed=exercises_completed,
            exercises_mastered=exercises_mastered,
            exercises_attempts_total=exercises_attempts_total,
            exercises_avg_score=exercises_avg_score,
            # General stats
            streak_days=streak_days,
            total_practice_time_hours=total_practice_time_hours,
        )

    async def _enhance_with_exercise_data(
        self, topic_states: list[MasteryState]
    ) -> list[MasteryState]:
        """
        Enhance topic mastery states with data from exercise attempts.

        For topics that have exercise attempts, compute mastery based on
        exercise performance.
        """
        if not topic_states:
            return topic_states

        # Get exercise attempt stats by topic
        topic_paths = [s.topic_path for s in topic_states]

        # Query exercise attempts grouped by topic
        exercise_stats = await self.db.execute(
            select(
                Exercise.topic,
                func.count(ExerciseAttempt.id).label("practice_count"),
                func.avg(ExerciseAttempt.score).label("avg_score"),
                func.sum(case((ExerciseAttempt.is_correct == True, 1), else_=0)).label(
                    "correct_count"
                ),
                func.max(ExerciseAttempt.attempted_at).label("last_practiced"),
            )
            .join(ExerciseAttempt, Exercise.id == ExerciseAttempt.exercise_id)
            .where(Exercise.topic.in_(topic_paths))
            .group_by(Exercise.topic)
        )

        stats_by_topic = {
            row.topic: {
                "practice_count": row.practice_count or 0,
                "avg_score": row.avg_score or 0.0,
                "correct_count": row.correct_count or 0,
                "last_practiced": row.last_practiced,
            }
            for row in exercise_stats.fetchall()
        }

        # Get exercise counts per topic
        exercise_count_query = (
            select(
                Exercise.topic,
                func.count(Exercise.id).label("exercise_count"),
            )
            .where(Exercise.topic.in_(topic_paths))
            .group_by(Exercise.topic)
        )
        exercise_count_result = await self.db.execute(exercise_count_query)
        exercise_counts = {
            row.topic: row.exercise_count for row in exercise_count_result.fetchall()
        }

        # Get card counts per topic using unnest to properly handle the tags array
        # For cards, we count cards that have the topic in their tags array
        card_counts = {}
        for topic_path in topic_paths:
            card_count_query = (
                select(func.count(SpacedRepCard.id))
                .where(SpacedRepCard.tags.any(topic_path))
            )
            result = await self.db.execute(card_count_query)
            count = result.scalar() or 0
            if count > 0:
                card_counts[topic_path] = count

        # Enhance each topic state
        enhanced_states = []
        now = datetime.now(timezone.utc)

        for state in topic_states:
            topic_data = stats_by_topic.get(state.topic_path)
            exercise_count = exercise_counts.get(state.topic_path, 0)
            card_count = card_counts.get(state.topic_path, 0)

            # Card mastery is the original state's mastery score
            card_mastery = state.mastery_score

            if topic_data and topic_data["practice_count"] > 0:
                # Compute exercise mastery from exercise scores
                exercise_mastery = topic_data["avg_score"]
                practice_count = topic_data["practice_count"]
                success_rate = (
                    topic_data["correct_count"] / practice_count
                    if practice_count > 0
                    else None
                )
                last_practiced = topic_data["last_practiced"]

                # Calculate days since last practice
                days_since = None
                if last_practiced:
                    delta = now - last_practiced
                    days_since = delta.days

                # Combined mastery is the max of card and exercise mastery
                combined_mastery = max(card_mastery, exercise_mastery)

                # Create enhanced state with separate scores
                enhanced_states.append(
                    MasteryState(
                        topic_path=state.topic_path,
                        mastery_score=combined_mastery,
                        card_mastery_score=card_mastery if card_count > 0 else None,
                        exercise_mastery_score=exercise_mastery,
                        card_count=card_count,
                        exercise_count=exercise_count,
                        practice_count=state.practice_count + practice_count,
                        success_rate=(
                            success_rate
                            if success_rate is not None
                            else state.success_rate
                        ),
                        trend=state.trend,
                        last_practiced=last_practiced or state.last_practiced,
                        days_since_review=(
                            days_since
                            if days_since is not None
                            else state.days_since_review
                        ),
                    )
                )
            else:
                # No exercise data, keep original state with card data
                enhanced_states.append(
                    MasteryState(
                        topic_path=state.topic_path,
                        mastery_score=state.mastery_score,
                        card_mastery_score=card_mastery if card_count > 0 else None,
                        exercise_mastery_score=None,
                        card_count=card_count,
                        exercise_count=exercise_count,
                        practice_count=state.practice_count,
                        success_rate=state.success_rate,
                        trend=state.trend,
                        last_practiced=state.last_practiced,
                        days_since_review=state.days_since_review,
                        retention_estimate=state.retention_estimate,
                        confidence_avg=state.confidence_avg,
                    )
                )

        return enhanced_states

    async def get_learning_curve(
        self,
        topic: Optional[str] = None,
        days: Optional[int] = None,
    ) -> LearningCurveResponse:
        """
        Get learning curve data for visualization.

        Retrieves card review activity, exercise activity, and time logs,
        calculating trend direction and 30-day projection using linear extrapolation.

        Args:
            topic: Topic path to filter by, or None for all topics.
            days: Number of days of history (defaults to MASTERY_LEARNING_CURVE_DAYS).

        Returns:
            LearningCurveResponse with data points including card and exercise activity,
            trend, and projection.
        """
        if days is None:
            days = settings.MASTERY_LEARNING_CURVE_DAYS
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Query card reviews from CardReviewHistory for accurate historical data
        # This tracks each individual review, not just the most recent per card
        card_query = select(
            func.date(CardReviewHistory.reviewed_at).label("review_date"),
            func.count(CardReviewHistory.id).label("cards_reviewed"),
        ).where(CardReviewHistory.reviewed_at >= start_date)

        if topic:
            # Filter by topic tag via join to SpacedRepCard
            card_query = card_query.join(
                SpacedRepCard, SpacedRepCard.id == CardReviewHistory.card_id
            ).where(SpacedRepCard.tags.contains([topic]))

        card_query = card_query.group_by(func.date(CardReviewHistory.reviewed_at))

        card_result = await self.db.execute(card_query)
        cards_by_date = {
            row.review_date: row.cards_reviewed or 0 for row in card_result.fetchall()
        }

        # TODO: Remove this fallback mechanism after we clear the DB next time.
        # Fallback: also check SpacedRepCard.last_reviewed for reviews before history tracking
        # This ensures we show data for cards reviewed before the history table existed
        fallback_query = select(
            func.date(SpacedRepCard.last_reviewed).label("review_date"),
            func.count(SpacedRepCard.id).label("cards_count"),
        ).where(SpacedRepCard.last_reviewed >= start_date)

        if topic:
            fallback_query = fallback_query.where(SpacedRepCard.tags.contains([topic]))

        fallback_query = fallback_query.group_by(func.date(SpacedRepCard.last_reviewed))

        fallback_result = await self.db.execute(fallback_query)
        for row in fallback_result.fetchall():
            # Only add if not already in cards_by_date (history takes precedence)
            if row.review_date not in cards_by_date:
                cards_by_date[row.review_date] = row.cards_count or 0

        # Get exercise activity data grouped by date
        exercise_query = select(
            func.date(ExerciseAttempt.attempted_at).label("attempt_date"),
            func.count(ExerciseAttempt.id).label("attempt_count"),
            func.avg(ExerciseAttempt.score).label("avg_score"),
        ).where(ExerciseAttempt.attempted_at >= start_date)

        if topic:
            exercise_query = exercise_query.join(
                Exercise, Exercise.id == ExerciseAttempt.exercise_id
            ).where(Exercise.topic == topic)

        exercise_query = exercise_query.group_by(
            func.date(ExerciseAttempt.attempted_at)
        )

        exercise_result = await self.db.execute(exercise_query)
        exercise_by_date = {
            row.attempt_date: {
                "count": row.attempt_count or 0,
                "avg_score": (row.avg_score or 0) * 100,  # Convert to percentage
            }
            for row in exercise_result.fetchall()
        }

        # Get time from card review history (CardReviewHistory.time_spent_seconds)
        card_time_query = (
            select(
                func.date(CardReviewHistory.reviewed_at).label("review_date"),
                func.sum(CardReviewHistory.time_spent_seconds / 60.0).label(
                    "total_minutes"
                ),
            )
            .where(CardReviewHistory.reviewed_at >= start_date)
            .group_by(func.date(CardReviewHistory.reviewed_at))
        )

        card_time_result = await self.db.execute(card_time_query)
        card_time_by_date = {
            row.review_date: int(row.total_minutes or 0)
            for row in card_time_result.fetchall()
        }

        # Get time from exercise attempts (ExerciseAttempt.time_spent_seconds)
        exercise_time_query = (
            select(
                func.date(ExerciseAttempt.attempted_at).label("attempt_date"),
                func.sum(ExerciseAttempt.time_spent_seconds / 60.0).label(
                    "total_minutes"
                ),
            )
            .where(ExerciseAttempt.attempted_at >= start_date)
            .group_by(func.date(ExerciseAttempt.attempted_at))
        )

        exercise_time_result = await self.db.execute(exercise_time_query)
        exercise_time_by_date = {
            row.attempt_date: int(row.total_minutes or 0)
            for row in exercise_time_result.fetchall()
        }

        # Combined time for the time_by_date (also include LearningTimeLog for backwards compat)
        time_query = (
            select(
                func.date(LearningTimeLog.started_at).label("log_date"),
                func.sum(
                    func.extract(
                        "epoch", LearningTimeLog.ended_at - LearningTimeLog.started_at
                    )
                    / 60
                ).label("total_minutes"),
            )
            .where(LearningTimeLog.started_at >= start_date)
            .group_by(func.date(LearningTimeLog.started_at))
        )

        time_result = await self.db.execute(time_query)
        time_by_date = {
            row.log_date: int(row.total_minutes or 0) for row in time_result.fetchall()
        }

        # Add card time and exercise time to combined total
        for d, minutes in card_time_by_date.items():
            time_by_date[d] = time_by_date.get(d, 0) + minutes
        for d, minutes in exercise_time_by_date.items():
            time_by_date[d] = time_by_date.get(d, 0) + minutes

        # Get mastery snapshots for mastery_score data (if available)
        snapshot_query = select(MasterySnapshot).where(
            MasterySnapshot.snapshot_date >= start_date
        )
        if topic:
            snapshot_query = snapshot_query.where(MasterySnapshot.topic_path == topic)
        snapshot_query = snapshot_query.order_by(MasterySnapshot.snapshot_date.asc())

        snapshot_result = await self.db.execute(snapshot_query)
        snapshots = snapshot_result.scalars().all()
        snapshot_by_date = {
            (
                s.snapshot_date.date()
                if hasattr(s.snapshot_date, "date")
                else s.snapshot_date
            ): s
            for s in snapshots
        }

        # Collect all unique dates from cards, exercises, and time logs
        all_dates = (
            set(cards_by_date.keys())
            | set(exercise_by_date.keys())
            | set(time_by_date.keys())
            | set(card_time_by_date.keys())
            | set(exercise_time_by_date.keys())
        )

        # Build data points for each date with activity
        data_points = []
        for activity_date in sorted(all_dates):
            cards_reviewed = cards_by_date.get(activity_date, 0)
            exercise_data = exercise_by_date.get(
                activity_date, {"count": 0, "avg_score": None}
            )
            card_time = card_time_by_date.get(activity_date, 0)
            exercise_time = exercise_time_by_date.get(activity_date, 0)
            total_time = time_by_date.get(activity_date, 0)

            # Get mastery score from snapshot if available
            snapshot = snapshot_by_date.get(activity_date)
            mastery_score = snapshot.mastery_score if snapshot else 0.0
            retention_estimate = snapshot.retention_estimate if snapshot else None

            data_points.append(
                LearningCurveDataPoint(
                    date=datetime.combine(
                        activity_date, datetime.min.time(), tzinfo=timezone.utc
                    ),
                    mastery_score=mastery_score or 0.0,
                    retention_estimate=retention_estimate,
                    cards_reviewed=cards_reviewed,
                    card_time_minutes=card_time,
                    exercises_attempted=exercise_data["count"],
                    exercise_score=(
                        exercise_data["avg_score"]
                        if exercise_data["avg_score"]
                        else None
                    ),
                    exercise_time_minutes=exercise_time,
                    time_minutes=total_time,
                )
            )

        # Calculate trend from mastery scores (if available)
        mastery_points = [dp for dp in data_points if dp.mastery_score > 0]
        if len(mastery_points) >= 2:
            trend = _calculate_trend(
                mastery_points[-1].mastery_score, mastery_points[0].mastery_score
            )
        else:
            trend = MasteryTrend.STABLE

        # Simple projection (linear extrapolation)
        projected_mastery = None
        window = settings.MASTERY_PROJECTION_WINDOW_DAYS
        horizon = settings.MASTERY_PROJECTION_HORIZON_DAYS
        if len(mastery_points) >= window:
            recent_points = mastery_points[-window:]
            avg_delta = (
                recent_points[-1].mastery_score - recent_points[0].mastery_score
            ) / window
            projected_mastery = min(
                1.0,
                max(0.0, mastery_points[-1].mastery_score + (avg_delta * horizon)),
            )

        return LearningCurveResponse(
            topic=topic,
            data_points=data_points,
            trend=trend,
            projected_mastery_30d=projected_mastery,
        )

    async def take_daily_snapshot(self) -> int:
        """
        Take daily mastery snapshots for all topics.

        Creates MasterySnapshot records for analytics and learning curve data.
        Should be called by scheduler at midnight.

        Returns:
            Number of snapshots successfully created.
        """
        topics = await self._get_all_topics()
        if not topics:
            return 0

        # Calculate mastery for all topics using batched pandas approach
        all_states = await self._calculate_mastery_batch(topics)
        prev_snapshots = await self._get_recent_snapshots_batch(
            topics, days=settings.MASTERY_SNAPSHOT_LOOKBACK_DAYS
        )

        # Create snapshots for all topics
        count = 0
        snapshot_time = datetime.now(timezone.utc)

        for state in all_states:
            try:
                prev_snapshot = prev_snapshots.get(state.topic_path)
                prev_score = prev_snapshot.mastery_score or 0 if prev_snapshot else 0
                trend = _calculate_trend(state.mastery_score, prev_score).value

                snapshot = MasterySnapshot(
                    snapshot_date=snapshot_time,
                    topic_path=state.topic_path,
                    total_cards=state.practice_count,
                    mastery_score=state.mastery_score,
                    practice_count=state.practice_count,
                    success_rate=state.success_rate,
                    trend=trend,
                    last_practiced=state.last_practiced,
                    retention_estimate=state.retention_estimate,
                    days_since_review=state.days_since_review,
                )

                self.db.add(snapshot)
                count += 1

            except Exception as e:
                logger.warning(f"Failed to snapshot topic {state.topic_path}: {e}")

        await self.db.commit()
        logger.info(f"Created {count} mastery snapshots")

        return count

    async def _calculate_mastery(self, topic: str) -> MasteryState:
        """
        Calculate mastery state for a single topic.

        For single-topic queries, uses pandas DataFrame internally.
        For batch operations, use _calculate_mastery_batch instead.

        Args:
            topic: Topic path to calculate mastery for.

        Returns:
            MasteryState with calculated score, trend, and statistics.
        """
        # Use batch method for consistency (still efficient for single topic)
        states = await self._calculate_mastery_batch([topic])
        return (
            states[0]
            if states
            else MasteryState(
                topic_path=topic,
                mastery_score=0.0,
                practice_count=0,
            )
        )

    async def _fetch_cards_dataframe(self) -> pd.DataFrame:
        """
        Fetch all cards and return as a pandas DataFrame.

        Returns:
            DataFrame with columns: id, tags, state, stability, total_reviews,
            correct_reviews, last_reviewed.
        """
        result = await self.db.execute(select(SpacedRepCard))
        cards = result.scalars().all()

        if not cards:
            return pd.DataFrame(
                columns=[
                    "id",
                    "tags",
                    "state",
                    "stability",
                    "total_reviews",
                    "correct_reviews",
                    "last_reviewed",
                ]
            )

        return pd.DataFrame(
            [
                {
                    "id": c.id,
                    "tags": c.tags or [],
                    "state": c.state,
                    "stability": c.stability or 0.0,
                    "total_reviews": c.total_reviews or 0,
                    "correct_reviews": c.correct_reviews or 0,
                    "last_reviewed": c.last_reviewed,
                }
                for c in cards
            ]
        )

    async def _get_recent_snapshots_batch(
        self, topics: list[str], days: int = 1
    ) -> dict[str, MasterySnapshot]:
        """
        Fetch most recent snapshots for multiple topics in a single query.

        Args:
            topics: List of topic paths to look up.
            days: Maximum age of snapshot in days.

        Returns:
            Dict mapping topic -> most recent MasterySnapshot (if exists).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(MasterySnapshot)
            .where(
                and_(
                    MasterySnapshot.topic_path.in_(topics),
                    MasterySnapshot.snapshot_date >= cutoff,
                )
            )
            .order_by(MasterySnapshot.snapshot_date.desc())
        )
        snapshots = result.scalars().all()

        # Keep only the most recent snapshot per topic
        snapshot_by_topic: dict[str, MasterySnapshot] = {}
        for snapshot in snapshots:
            if snapshot.topic_path and snapshot.topic_path not in snapshot_by_topic:
                snapshot_by_topic[snapshot.topic_path] = snapshot

        return snapshot_by_topic

    async def _calculate_mastery_batch(self, topics: list[str]) -> list[MasteryState]:
        """
        Calculate mastery states for multiple topics using batched queries.

        Fetches all cards and snapshots in bulk, then delegates to
        _compute_mastery_dataframe for pandas-based aggregation.

        Args:
            topics: List of topic paths to calculate mastery for.

        Returns:
            List of MasteryState objects for each topic.
        """
        if not topics:
            return []

        # Fetch all data
        cards_df = await self._fetch_cards_dataframe()
        snapshots_by_topic = await self._get_recent_snapshots_batch(
            topics, days=settings.MASTERY_SNAPSHOT_LOOKBACK_DAYS
        )

        # If no cards, return empty states for all topics
        if cards_df.empty:
            return [
                MasteryState(topic_path=topic, mastery_score=0.0, practice_count=0)
                for topic in topics
            ]

        # Compute mastery using pandas
        mastery_df = self._compute_mastery_dataframe(cards_df, topics)

        # Convert to MasteryState objects with trend from snapshots
        states = []
        for topic in topics:
            if topic in mastery_df.index:
                row = mastery_df.loc[topic]
                prev_snapshot = snapshots_by_topic.get(topic)

                # Calculate trend
                if prev_snapshot and prev_snapshot.mastery_score is not None:
                    trend = _calculate_trend(
                        row["mastery_score"], prev_snapshot.mastery_score
                    )
                else:
                    trend = MasteryTrend.STABLE

                states.append(
                    MasteryState(
                        topic_path=topic,
                        mastery_score=row["mastery_score"],
                        practice_count=int(row["total_reviews"]),
                        success_rate=(
                            row["success_rate"]
                            if pd.notna(row["success_rate"])
                            else None
                        ),
                        trend=trend,
                        last_practiced=(
                            row["last_practiced"]
                            if pd.notna(row["last_practiced"])
                            else None
                        ),
                        days_since_review=(
                            int(row["days_since_review"])
                            if pd.notna(row["days_since_review"])
                            else None
                        ),
                    )
                )
            else:
                states.append(
                    MasteryState(
                        topic_path=topic,
                        mastery_score=0.0,
                        practice_count=0,
                    )
                )

        return states

    def _compute_mastery_dataframe(
        self, cards_df: pd.DataFrame, topics: list[str]
    ) -> pd.DataFrame:
        """
        Compute mastery statistics per topic using vectorized pandas operations.

        Args:
            cards_df: DataFrame with card data.
            topics: List of topics to compute mastery for.

        Returns:
            DataFrame indexed by topic with mastery statistics.
        """
        # Explode tags so each card-topic pair is a row
        exploded = cards_df.explode("tags").copy()
        exploded = exploded[exploded["tags"].isin(topics)]

        if exploded.empty:
            return pd.DataFrame()

        # Add helper column for review-state stability (0 for non-review cards)
        exploded["review_stability"] = exploded.apply(
            lambda r: r["stability"] if r["state"] == CardState.REVIEW else 0.0, axis=1
        )
        exploded["is_review"] = (exploded["state"] == CardState.REVIEW).astype(int)

        # Group by topic and aggregate
        grouped = exploded.groupby("tags").agg(
            total_reviews=("total_reviews", "sum"),
            correct_reviews=("correct_reviews", "sum"),
            last_practiced=("last_reviewed", "max"),
            review_cards=("is_review", "sum"),
            review_stability_sum=("review_stability", "sum"),
        )

        # Compute derived metrics
        # Use naive UTC for days_since_review to handle both naive/aware timestamps from DB
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        # Success rate (None if no reviews)
        grouped["success_rate"] = grouped.apply(
            lambda r: (
                r["correct_reviews"] / r["total_reviews"]
                if r["total_reviews"] > 0
                else None
            ),
            axis=1,
        )

        # Stability factor (average stability of review cards, normalized)
        grouped["stability_factor"] = grouped.apply(
            lambda r: (
                min(
                    1.0,
                    (r["review_stability_sum"] / r["review_cards"])
                    / settings.MASTERY_STABILITY_NORMALIZATION_DAYS,
                )
                if r["review_cards"] > 0
                else 0.0
            ),
            axis=1,
        )

        # Mastery score (requires MIN_ATTEMPTS)
        grouped["mastery_score"] = grouped.apply(
            lambda r: (
                (
                    (r["success_rate"] * settings.MASTERY_SUCCESS_RATE_WEIGHT)
                    + (r["stability_factor"] * settings.MASTERY_STABILITY_WEIGHT)
                )
                if r["total_reviews"] >= settings.MASTERY_MIN_ATTEMPTS
                and r["success_rate"] is not None
                else 0.0
            ),
            axis=1,
        )

        # Days since review (strip tz from timestamp if present for consistent comparison)
        grouped["days_since_review"] = grouped["last_practiced"].apply(
            lambda x: (
                (
                    now_naive
                    - (
                        x.replace(tzinfo=None)
                        if hasattr(x, "tzinfo") and x.tzinfo
                        else x
                    )
                ).days
                if pd.notna(x)
                else None
            )
        )

        return grouped

    async def _get_recent_snapshot(
        self,
        topic: str,
        days: int = 1,
    ) -> Optional[MasterySnapshot]:
        """
        Get most recent mastery snapshot for a topic.

        Args:
            topic: Topic path to look up.
            days: Maximum age of snapshot in days (default 1).

        Returns:
            Most recent MasterySnapshot within cutoff, or None if not found.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(MasterySnapshot)
            .where(
                and_(
                    MasterySnapshot.topic_path == topic,
                    MasterySnapshot.snapshot_date >= cutoff,
                )
            )
            .order_by(MasterySnapshot.snapshot_date.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def _get_all_topics(self) -> list[str]:
        """
        Get all topics from the Tag table.

        Uses TagService to query the canonical Tag table.

        Returns:
            List of topic path strings.
        """
        tag_service = TagService(self.db)
        tags = await tag_service.get_all_tags()
        return [tag.name for tag in tags]

    async def _calculate_streak(self) -> int:
        """
        Calculate consecutive practice days.

        Counts consecutive days with reviews starting from today,
        looking back up to STREAK_WINDOW_DAYS.

        Returns:
            Number of consecutive practice days.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.MASTERY_STREAK_WINDOW_DAYS
        )

        result = await self.db.execute(
            select(distinct(func.date(SpacedRepCard.last_reviewed)))
            .where(SpacedRepCard.last_reviewed >= cutoff)
            .order_by(func.date(SpacedRepCard.last_reviewed).desc())
        )

        review_dates = [row[0] for row in result.fetchall()]

        if not review_dates:
            return 0

        # Count consecutive days from today
        today = datetime.now(timezone.utc).date()
        streak = 0

        for i, review_date in enumerate(review_dates):
            expected_date = today - timedelta(days=i)
            if review_date == expected_date:
                streak += 1
            else:
                break

        return streak

    def _snapshot_to_state(self, snapshot: MasterySnapshot) -> MasteryState:
        """
        Convert a MasterySnapshot to MasteryState.

        Args:
            snapshot: MasterySnapshot database record.

        Returns:
            MasteryState Pydantic model with snapshot data.
        """
        return MasteryState(
            topic_path=snapshot.topic_path or "",
            mastery_score=snapshot.mastery_score or 0.0,
            practice_count=snapshot.practice_count or 0,
            success_rate=snapshot.success_rate,
            trend=(
                MasteryTrend(snapshot.trend) if snapshot.trend else MasteryTrend.STABLE
            ),
            last_practiced=snapshot.last_practiced,
            retention_estimate=snapshot.retention_estimate,
            days_since_review=snapshot.days_since_review,
        )

    @staticmethod
    def _generate_recommendation(state: MasteryState) -> str:
        """
        Generate a personalized recommendation based on mastery state.

        Considers trend direction, success rate, and days since last review
        to provide actionable advice.

        Args:
            state: Current MasteryState for a topic.

        Returns:
            Human-readable recommendation string.
        """
        if state.trend == MasteryTrend.DECLINING:
            return f"Your mastery of {state.topic_path} is declining. Schedule a focused review session."

        if (
            state.success_rate
            and state.success_rate < settings.MASTERY_LOW_SUCCESS_RATE
        ):
            return f"Low success rate ({state.success_rate:.0%}). Try easier exercises or review foundational concepts."

        if (
            state.days_since_review
            and state.days_since_review > settings.MASTERY_STALE_REVIEW_DAYS
        ):
            return f"It's been {state.days_since_review} days since you practiced this topic. Time for a review!"

        return (
            f"Continue practicing {state.topic_path} to strengthen your understanding."
        )

    @staticmethod
    def _suggest_exercise_types(state: MasteryState) -> list[ExerciseType]:
        """
        Suggest appropriate exercise types based on mastery level.

        Delegates to get_suggested_exercise_types() which maps mastery levels
        to exercise types (novice -> worked examples, intermediate -> recall, etc).

        Args:
            state: Current MasteryState for a topic.

        Returns:
            List of appropriate ExerciseType values for current mastery level.
        """
        return get_suggested_exercise_types(state.mastery_score)

    # ===========================================
    # Time Investment Methods
    # ===========================================

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

        Queries LearningTimeLog records where the activity started after start_date
        and ended before end_date.

        Args:
            start_date: Inclusive start of the date range (timezone-aware UTC).
            end_date: Inclusive end of the date range (timezone-aware UTC).

        Returns:
            list[LearningTimeLog]: List of time log records within the range.
        """
        query = select(LearningTimeLog).where(
            LearningTimeLog.started_at >= start_date,
            LearningTimeLog.ended_at <= end_date,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _fetch_practice_sessions(
        self, start_date: datetime
    ) -> list[PracticeSession]:
        """
        Fetch completed practice sessions since start date.

        Only returns sessions that have been completed (ended_at is not None).
        Used to aggregate session durations for time investment calculations.

        Args:
            start_date: Only include sessions started on or after this date (timezone-aware UTC).

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
            period_delta = timedelta(days=1)
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

    # ===========================================
    # Detailed Streak Methods
    # ===========================================

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

        # Determine the reference date: today if practiced today, else yesterday
        most_recent = practice_dates[0]
        if most_recent == today:
            reference_date = today
        elif most_recent == today - timedelta(days=1):
            # Streak still active - user hasn't practiced today but did yesterday
            reference_date = most_recent
        else:
            # No recent practice - no active streak
            return 0, None

        # Count consecutive days backwards from the reference date
        streak_count = 0
        streak_start = None

        for i, practice_date in enumerate(practice_dates):
            expected_date = reference_date - timedelta(days=i)
            if practice_date == expected_date:
                streak_count += 1
                streak_start = practice_date
            else:
                break

        return streak_count, streak_start

    @staticmethod
    def _calculate_longest_streak(practice_dates: list[date]) -> int:
        """
        Calculate the longest streak from practice dates.

        Sorts unique dates and iterates to find the longest sequence of consecutive days.
        Handles duplicate dates by using a set.

        Args:
            practice_dates: List of practice dates (any order, may contain duplicates).

        Returns:
            int: Length of the longest consecutive day streak, or 0 if no practice dates.
        """
        if not practice_dates:
            return 0

        sorted_dates = sorted(set(practice_dates))
        longest = 1
        current = 1

        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    @staticmethod
    def _count_days_in_period(practice_dates: list[date], days: int) -> int:
        """
        Count unique practice days in the last N days.

        Filters practice dates to those on or after the cutoff date (today - days),
        then counts unique dates.

        Args:
            practice_dates: List of practice dates (any order, may contain duplicates).
            days: Number of days to look back from today.

        Returns:
            int: Count of unique practice days within the period.
        """
        if not practice_dates:
            return 0
        cutoff = date.today() - timedelta(days=days)
        return len([d for d in set(practice_dates) if d >= cutoff])

    # ===========================================
    # Time Logging
    # ===========================================

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

    # ===========================================
    # Dashboard & Daily Stats
    # ===========================================

    async def get_daily_stats(self) -> DailyStatsResponse:
        """
        Get daily statistics for the dashboard.

        Provides a quick overview including streak, due cards, and today's progress.

        Returns:
            DailyStatsResponse with today's learning metrics.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get streak
        streak = await self._calculate_streak()

        # Count total cards
        total_result = await self.db.execute(select(func.count(SpacedRepCard.id)))
        total_cards = total_result.scalar() or 0

        # Count due cards (due_date <= now)
        due_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(SpacedRepCard.due_date <= now)
        )
        due_cards = due_result.scalar() or 0

        # Count cards reviewed today
        reviewed_today_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                SpacedRepCard.last_reviewed >= today_start
            )
        )
        cards_reviewed_today = reviewed_today_result.scalar() or 0

        # Get overall mastery
        overview = await self.get_overview()

        # Get last practice date
        last_review_result = await self.db.execute(
            select(func.max(SpacedRepCard.last_reviewed))
        )
        last_reviewed = last_review_result.scalar()
        last_practice_date = last_reviewed.date() if last_reviewed else None

        # Check if streak is at risk (no practice today yet)
        streak_at_risk = cards_reviewed_today == 0 and streak > 0

        # Get practice time today
        time_result = await self.db.execute(
            select(func.sum(LearningTimeLog.duration_seconds)).where(
                LearningTimeLog.started_at >= today_start
            )
        )
        practice_seconds = time_result.scalar() or 0

        return DailyStatsResponse(
            streak_days=streak,
            streak_at_risk=streak_at_risk,
            due_cards_count=due_cards,
            total_cards=total_cards,
            cards_reviewed_today=cards_reviewed_today,
            overall_mastery=overview.overall_mastery,
            practice_time_today_minutes=practice_seconds // 60,
            last_practice_date=last_practice_date,
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
            day.level = _calculate_activity_level(day.count, max_count)

        return PracticeHistoryResponse(
            days=days,
            total_practice_days=total_practice_days,
            total_items=total_items,
            max_daily_count=max_count,
        )
