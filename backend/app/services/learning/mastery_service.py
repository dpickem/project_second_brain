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
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import select, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models_learning import SpacedRepCard, MasterySnapshot
from app.enums.learning import MasteryTrend, ExerciseType, CardState
from app.services.learning.exercise_generator import get_suggested_exercise_types
from app.services.tag_service import TagService
from app.models.learning import (
    MasteryState,
    MasteryOverview,
    WeakSpot,
    LearningCurveDataPoint,
    LearningCurveResponse,
)

logger = logging.getLogger(__name__)


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

        Aggregates card counts (mastered, learning, new), topic mastery states,
        overall mastery average, and current practice streak.

        Returns:
            MasteryOverview with comprehensive learning statistics.
        """
        # 1. Count total cards in the system
        total_cards_result = await self.db.execute(select(func.count(SpacedRepCard.id)))
        total_cards = total_cards_result.scalar() or 0

        # 2. Count cards by learning state
        # Mastered: cards with stability above threshold (retained long-term)
        mastered_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                SpacedRepCard.stability >= settings.MASTERY_MASTERED_STABILITY_DAYS
            )
        )
        cards_mastered = mastered_result.scalar() or 0

        # Learning: cards actively being studied but not yet mastered
        # Includes learning, relearning, and review states with low stability
        learning_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                and_(
                    SpacedRepCard.state.in_(
                        [CardState.LEARNING, CardState.RELEARNING, CardState.REVIEW]
                    ),
                    SpacedRepCard.stability < settings.MASTERY_MASTERED_STABILITY_DAYS,
                )
            )
        )
        cards_learning = learning_result.scalar() or 0

        # New: cards that have never been reviewed
        new_result = await self.db.execute(
            select(func.count(SpacedRepCard.id)).where(
                SpacedRepCard.state == CardState.NEW
            )
        )
        cards_new = new_result.scalar() or 0

        # 3. Calculate per-topic mastery states (batch query instead of N queries)
        topics = await self._get_all_topics()
        topics_to_calculate = topics[: settings.MASTERY_MAX_TOPICS_IN_OVERVIEW]
        topic_states = await self._calculate_mastery_batch(topics_to_calculate)

        # 4. Compute overall mastery as average across all topics
        if topic_states:
            overall_mastery = sum(s.mastery_score for s in topic_states) / len(
                topic_states
            )
        else:
            overall_mastery = 0.0

        # 5. Calculate practice streak (consecutive days with reviews)
        streak_days = await self._calculate_streak()

        # 6. Return aggregated overview
        return MasteryOverview(
            overall_mastery=overall_mastery,
            topics=topic_states,
            total_cards=total_cards,
            cards_mastered=cards_mastered,
            cards_learning=cards_learning,
            cards_new=cards_new,
            streak_days=streak_days,
        )

    async def get_learning_curve(
        self,
        topic: Optional[str] = None,
        days: Optional[int] = None,
    ) -> LearningCurveResponse:
        """
        Get learning curve data for visualization.

        Retrieves historical mastery snapshots and calculates trend direction
        and 30-day projection using linear extrapolation.

        Args:
            topic: Topic path to filter by, or None for all topics.
            days: Number of days of history (defaults to MASTERY_LEARNING_CURVE_DAYS).

        Returns:
            LearningCurveResponse with data points, trend, and projection.
        """
        if days is None:
            days = settings.MASTERY_LEARNING_CURVE_DAYS
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get snapshots for the period
        query = select(MasterySnapshot).where(
            MasterySnapshot.snapshot_date >= start_date
        )

        if topic:
            query = query.where(MasterySnapshot.topic_path == topic)

        query = query.order_by(MasterySnapshot.snapshot_date.asc())

        result = await self.db.execute(query)
        snapshots = result.scalars().all()

        # Convert to data points
        data_points = []
        for snapshot in snapshots:
            data_points.append(
                LearningCurveDataPoint(
                    date=snapshot.snapshot_date,
                    mastery_score=snapshot.mastery_score or 0.0,
                    retention_estimate=snapshot.retention_estimate,
                    cards_reviewed=(
                        (snapshot.mastered_cards or 0) + (snapshot.learning_cards or 0)
                    ),
                )
            )

        # Calculate trend
        if len(data_points) >= 2:
            trend = _calculate_trend(
                data_points[-1].mastery_score, data_points[0].mastery_score
            )
        else:
            trend = MasteryTrend.STABLE

        # Simple projection (linear extrapolation)
        projected_mastery = None
        window = settings.MASTERY_PROJECTION_WINDOW_DAYS
        horizon = settings.MASTERY_PROJECTION_HORIZON_DAYS
        if len(data_points) >= window:
            recent_points = data_points[-window:]
            avg_delta = (
                recent_points[-1].mastery_score - recent_points[0].mastery_score
            ) / window
            projected_mastery = min(
                1.0,
                max(0.0, data_points[-1].mastery_score + (avg_delta * horizon)),
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
        snapshot_time = datetime.utcnow()

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
        cutoff = datetime.utcnow() - timedelta(days=days)

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
        now = datetime.utcnow()

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

        # Days since review
        grouped["days_since_review"] = grouped["last_practiced"].apply(
            lambda x: (now - x).days if pd.notna(x) else None
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
        cutoff = datetime.utcnow() - timedelta(days=days)

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
        cutoff = datetime.utcnow() - timedelta(days=settings.MASTERY_STREAK_WINDOW_DAYS)

        result = await self.db.execute(
            select(distinct(func.date(SpacedRepCard.last_reviewed)))
            .where(SpacedRepCard.last_reviewed >= cutoff)
            .order_by(func.date(SpacedRepCard.last_reviewed).desc())
        )

        review_dates = [row[0] for row in result.fetchall()]

        if not review_dates:
            return 0

        # Count consecutive days from today
        today = datetime.utcnow().date()
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
