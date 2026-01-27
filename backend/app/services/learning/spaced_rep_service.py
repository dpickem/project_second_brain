"""
Spaced Repetition Service

Service layer that integrates FSRS scheduling with the database.
Handles card CRUD (Create, Read, Update, Delete) operations, review processing,
and statistics.

Usage:
    from app.services.learning import SpacedRepService

    service = SpacedRepService(db_session)

    # Get due cards
    due_response = await service.get_due_cards(limit=50)

    # Process a review
    result = await service.review_card(CardReviewRequest(
        card_id=123,
        rating=Rating.GOOD
    ))
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import random
from typing import Optional
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_learning import SpacedRepCard, CardReviewHistory
from app.enums.learning import CardState as CardStateEnum, Rating
from app.models.learning import (
    CardCreate,
    CardResponse,
    CardReviewRequest,
    CardReviewResponse,
    DueCardsResponse,
    ReviewForecast,
    CardStats,
)
from app.services.learning.fsrs import CardState, create_scheduler
from app.services.tag_service import TagService
from app.config.settings import settings

# Import fsrs State enum for conversion from DB string states
from fsrs import State as FSRSState

# Map our string states to fsrs State enum
# Note: fsrs v6+ has no "New" state - new cards are State.Learning with last_review=None
_STATE_MAP = {
    "new": FSRSState.Learning,  # New cards use Learning state
    "learning": FSRSState.Learning,
    "review": FSRSState.Review,
    "relearning": FSRSState.Relearning,
}

logger = logging.getLogger(__name__)


class SpacedRepService:
    """
    Service for managing spaced repetition cards with FSRS.

    Provides:
    - Card CRUD operations
    - Review processing with FSRS algorithm
    - Due card queries with topic filtering
    - Card statistics and forecasts
    """

    def __init__(
        self,
        db: AsyncSession,
        target_retention_probability: float = None,
        max_interval: int = None,
    ):
        """
        Initialize the spaced repetition service.

        Args:
            db: Async database session
            target_retention_probability: Target retention probability
                (defaults to settings.FSRS_DEFAULT_RETENTION)
            max_interval: Maximum interval in days
                (defaults to settings.FSRS_MAX_INTERVAL_DAYS)
        """
        self.db = db
        self.scheduler = create_scheduler(
            retention=target_retention_probability or settings.FSRS_DEFAULT_RETENTION,
            max_interval=max_interval or settings.FSRS_MAX_INTERVAL_DAYS,
        )

    async def create_card(self, card_data: CardCreate) -> CardResponse:
        """
        Create a new spaced repetition card.

        Card is created in NEW state with FSRS initial parameters.

        Args:
            card_data: Card creation data

        Returns:
            Created card response

        Raises:
            InvalidTagError: If any tags don't exist in the database
        """
        # Validate tags against database
        if card_data.tags:
            tag_service = TagService(self.db)
            await tag_service.validate_tags(card_data.tags)

        card = SpacedRepCard(
            content_id=card_data.content_id,
            card_type=card_data.card_type,
            front=card_data.front,
            back=card_data.back,
            hints=card_data.hints,
            tags=card_data.tags,
            concept_id=card_data.concept_id,
            # Code fields
            language=card_data.language,
            starter_code=card_data.starter_code,
            solution_code=card_data.solution_code,
            test_cases=card_data.test_cases,
            # FSRS initial state
            state=CardStateEnum.NEW.value,
            stability=settings.FSRS_INITIAL_STABILITY,
            difficulty=settings.FSRS_INITIAL_DIFFICULTY,
            due_date=datetime.now(timezone.utc),
            lapses=0,
            scheduled_days=0,
        )

        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)

        logger.info(f"Created card {card.id} of type {card.card_type}")

        return self._to_response(card)

    async def get_card(self, card_id: int) -> Optional[CardResponse]:
        """Get a card by ID."""
        result = await self.db.execute(
            select(SpacedRepCard).where(SpacedRepCard.id == card_id)
        )
        card = result.scalar_one_or_none()

        if card is None:
            return None

        return self._to_response(card)

    async def list_cards(
        self,
        topic_filter: Optional[str] = None,
        card_type: Optional[str] = None,
        state_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CardResponse]:
        """
        List all cards with optional filters.

        Args:
            topic_filter: Filter by topic tag (partial match)
            card_type: Filter by card type
            state_filter: Filter by state (new, learning, review, mastered)
            limit: Maximum cards to return
            offset: Pagination offset

        Returns:
            List of card responses
        """
        query = select(SpacedRepCard)

        # Apply filters
        if topic_filter:
            # Match any tag that contains the topic filter
            query = query.where(SpacedRepCard.tags.any(topic_filter))

        if card_type:
            query = query.where(SpacedRepCard.card_type == card_type)

        if state_filter:
            query = query.where(SpacedRepCard.state == state_filter)

        # Order by created date (newest first) and apply pagination
        query = query.order_by(SpacedRepCard.id.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        cards = result.scalars().all()

        return [self._to_response(card) for card in cards]

    async def get_due_cards(
        self,
        limit: int = None,
        topic_filter: Optional[str] = None,
    ) -> DueCardsResponse:
        """
        Get cards due for review with topic interleaving.

        Cards are returned in an interleaved order to prevent reviewing
        multiple cards from the same topic consecutively. This improves
        learning by forcing context switches between topics.

        Interleaving is performed by _interleave_by_topic() which:
        1. Fetches due cards (up to 2x limit for better interleaving options)
        2. Groups cards by their primary topic (first tag)
        3. Shuffles cards within each topic group
        4. Round-robin interleaves across topic groups
        5. Returns the requested limit

        Note:
            This topic interleaving is separate from content-type interleaving
            done by SessionService._interleave_items(), which mixes cards with
            exercises. Both work together for optimal learning.

        Args:
            limit: Maximum number of cards to return
                (defaults to settings.REVIEW_DEFAULT_LIMIT)
            topic_filter: Optional topic to filter by (matches tags)

        Returns:
            Due cards response with forecast
        """
        if limit is None:
            limit = settings.REVIEW_DEFAULT_LIMIT

        now = datetime.now(timezone.utc)

        # Build query for due cards
        # Fetch more than limit to have better interleaving options
        query = select(SpacedRepCard).where(SpacedRepCard.due_date <= now)

        # Apply topic filter if provided
        if topic_filter:
            # PostgreSQL array contains operator
            query = query.where(SpacedRepCard.tags.any(topic_filter))

        # Get cards ordered by due date first (prioritize overdue cards)
        # but fetch more than needed for interleaving
        fetch_limit = min(
            limit * settings.REVIEW_INTERLEAVE_FETCH_MULTIPLIER,
            settings.REVIEW_INTERLEAVE_MAX_FETCH,
        )
        query = query.order_by(SpacedRepCard.due_date.asc()).limit(fetch_limit)

        result = await self.db.execute(query)
        cards = list(result.scalars().all())

        # Interleave cards by topic
        interleaved_cards = self._interleave_by_topic(cards, limit)

        # Get total count of due cards
        count_query = select(func.count(SpacedRepCard.id)).where(
            SpacedRepCard.due_date <= now
        )
        if topic_filter:
            count_query = count_query.where(SpacedRepCard.tags.any(topic_filter))

        total_result = await self.db.execute(count_query)
        total_due = total_result.scalar() or 0

        # Get forecast
        forecast = await self._get_review_forecast(topic_filter)

        return DueCardsResponse(
            cards=[self._to_response(c) for c in interleaved_cards],
            total_due=total_due,
            review_forecast=forecast,
        )

    def _interleave_by_topic(
        self,
        cards: list[SpacedRepCard],
        limit: int,
    ) -> list[SpacedRepCard]:
        """
        Interleave cards by topic to prevent same-topic clustering.

        This method handles TOPIC interleaving: ensuring cards from the same
        topic (e.g., ML, Databases) don't appear consecutively. It operates
        on SpacedRepCard objects and uses the first tag as the primary topic.

        Algorithm:
        1. Group cards by their primary topic (first tag)
        2. Shuffle cards within each topic group
        3. Round-robin pick from each topic group

        This improves learning by forcing context switches between topics,
        which research shows enhances long-term retention and discrimination.

        Note:
            This is complementary to SessionService._interleave_items(),
            which handles CONTENT-TYPE interleaving (mixing cards with exercises).
            Topic interleaving happens first at the card retrieval level;
            content-type interleaving happens later when building sessions.

        See Also:
            SessionService._interleave_items: Content-type session interleaving

        Args:
            cards: List of cards to interleave
            limit: Maximum number of cards to return

        Returns:
            Interleaved list of cards
        """
        if len(cards) <= 1:
            return cards[:limit]

        # Group cards by primary topic (first tag, or 'no-topic' if no tags)
        topic_groups: dict[str, list[SpacedRepCard]] = defaultdict(list)
        for card in cards:
            primary_topic = card.tags[0] if card.tags else "_no_topic"
            topic_groups[primary_topic].append(card)

        # Shuffle cards within each topic group
        for topic_cards in topic_groups.values():
            random.shuffle(topic_cards)

        # Round-robin interleave across topic groups
        # Shuffle the order of topics too for variety
        topics = list(topic_groups.keys())
        random.shuffle(topics)

        interleaved: list[SpacedRepCard] = []
        topic_indices = {topic: 0 for topic in topics}

        while len(interleaved) < limit:
            added_any = False
            for topic in topics:
                if topic_indices[topic] < len(topic_groups[topic]):
                    interleaved.append(topic_groups[topic][topic_indices[topic]])
                    topic_indices[topic] += 1
                    added_any = True
                    if len(interleaved) >= limit:
                        break
            if not added_any:
                break  # All groups exhausted

        return interleaved

    async def review_card(
        self,
        request: CardReviewRequest,
    ) -> CardReviewResponse:
        """
        Process a card review with FSRS.

        Args:
            request: Review request with card_id and rating

        Returns:
            Review response with new scheduling info

        Raises:
            ValueError: If card not found
        """
        # Load card
        result = await self.db.execute(
            select(SpacedRepCard).where(SpacedRepCard.id == request.card_id)
        )
        card = result.scalar_one_or_none()

        if card is None:
            raise ValueError(f"Card {request.card_id} not found")

        # Convert to FSRS CardState
        # Map our string state to fsrs State enum
        db_state = card.state or CardStateEnum.NEW.value
        fsrs_state = _STATE_MAP.get(db_state, FSRSState.Learning)

        # Create FSRS CardState from database card (both use timezone-aware UTC)
        # For new cards (never reviewed), stability and difficulty should be None
        # to let FSRS initialize them properly on first review
        is_new_card = card.last_reviewed is None
        card_state = CardState(
            state=fsrs_state,
            difficulty=(
                None
                if is_new_card
                else (card.difficulty or settings.FSRS_FALLBACK_DIFFICULTY)
            ),
            stability=(
                None
                if is_new_card
                else (card.stability or settings.FSRS_FALLBACK_STABILITY)
            ),
            due=card.due_date,
            last_review=card.last_reviewed,
            reps=card.repetitions or 0,
            lapses=card.lapses or 0,
            scheduled_days=card.scheduled_days or 0,
        )

        # Process review with FSRS
        new_state, log = self.scheduler.review(card_state, request.rating)

        # Update card in database (FSRS returns timezone-aware UTC datetimes)
        card.state = new_state.state.name.lower()
        card.difficulty = new_state.difficulty
        card.stability = new_state.stability
        card.due_date = new_state.due
        card.last_reviewed = new_state.last_review
        card.repetitions = new_state.reps
        card.lapses = new_state.lapses
        card.scheduled_days = new_state.scheduled_days

        # Update stats
        card.total_reviews = (card.total_reviews or 0) + 1
        if request.rating != Rating.AGAIN:
            card.correct_reviews = (card.correct_reviews or 0) + 1

        # Create review history record for analytics
        history_record = CardReviewHistory(
            card_id=card.id,
            rating=request.rating.value,
            reviewed_at=new_state.last_review,
            time_spent_seconds=request.time_spent_seconds,
            state_before=log.state_before.name.lower() if log.state_before else None,
            state_after=log.state_after.name.lower() if log.state_after else None,
            stability_after=new_state.stability,
            scheduled_days=new_state.scheduled_days,
        )
        self.db.add(history_record)

        await self.db.commit()
        await self.db.refresh(card)

        logger.info(
            f"Reviewed card {card.id}: {log.state_before} -> {log.state_after}, "
            f"next due in {new_state.scheduled_days} days"
        )

        return CardReviewResponse(
            card_id=card.id,
            new_state=CardStateEnum(new_state.state.name.lower()),
            new_stability=new_state.stability,
            new_difficulty=new_state.difficulty,
            next_due_date=new_state.due,
            scheduled_days=new_state.scheduled_days,
            was_correct=request.rating != Rating.AGAIN,
        )

    async def get_card_stats(
        self,
        topic_filter: Optional[str] = None,
    ) -> CardStats:
        """
        Get aggregate statistics about spaced repetition cards.

        Provides a snapshot of the card collection's health and review workload.
        Used by dashboards and the session service to understand learning progress.

        Statistics include:
        - Total card count (overall collection size)
        - Cards grouped by FSRS state (new/learning/review/relearning)
        - Average stability and difficulty (only for review-state cards,
          as new/learning cards don't have meaningful FSRS metrics yet)
        - Due today count (cards needing review within the current day)
        - Overdue count (cards past their due date - indicates review backlog)

        Args:
            topic_filter: Optional topic tag to filter stats by. When provided,
                only cards containing this tag in their tags array are counted.
                Useful for topic-specific progress tracking.

        Returns:
            CardStats with aggregated metrics for the card collection.

        Note:
            - Stability represents memory strength (higher = longer retention)
            - Difficulty represents how hard a card is to learn (0-1 scale)
            - Overdue cards should be prioritized in review sessions
        """
        # Build filter conditions (reused across all queries for consistency)
        conditions = []
        if topic_filter:
            # PostgreSQL array 'any' operator: matches if tag is in the tags array
            conditions.append(SpacedRepCard.tags.any(topic_filter))

        # --- Total card count ---
        total_query = select(func.count(SpacedRepCard.id))
        if conditions:
            total_query = total_query.where(*conditions)
        total_result = await self.db.execute(total_query)
        total_cards = total_result.scalar() or 0

        # --- Cards grouped by FSRS state ---
        # States: new (never reviewed), learning (initial phase), review (graduated),
        # relearning (lapsed and re-entering learning)
        state_query = select(
            SpacedRepCard.state, func.count(SpacedRepCard.id)
        ).group_by(SpacedRepCard.state)
        if conditions:
            state_query = state_query.where(*conditions)
        state_result = await self.db.execute(state_query)
        cards_by_state = {state: count for state, count in state_result.fetchall()}

        # --- Average FSRS metrics (review cards only) ---
        # Only review-state cards have meaningful stability/difficulty values.
        # New and learning cards have initial/partial values that would skew averages.
        avg_query = select(
            func.avg(SpacedRepCard.stability), func.avg(SpacedRepCard.difficulty)
        ).where(SpacedRepCard.state == CardStateEnum.REVIEW.value)
        if conditions:
            avg_query = avg_query.where(*conditions)
        avg_result = await self.db.execute(avg_query)
        avg_row = avg_result.fetchone()
        avg_stability = avg_row[0] or 0.0  # Days until 90% retention drops to ~90%
        avg_difficulty = avg_row[1] or 0.0  # 0 = easy, 1 = hard

        # --- Time boundaries for due/overdue calculations ---
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        # --- Cards due today (between start of today and start of tomorrow) ---
        due_today_query = select(func.count(SpacedRepCard.id)).where(
            and_(
                SpacedRepCard.due_date >= today_start,
                SpacedRepCard.due_date < tomorrow_start,
            )
        )
        if conditions:
            due_today_query = due_today_query.where(*conditions)
        due_today_result = await self.db.execute(due_today_query)
        due_today = due_today_result.scalar() or 0

        # --- Overdue cards (due before start of today) ---
        # These represent a review backlog and should be prioritized
        overdue_query = select(func.count(SpacedRepCard.id)).where(
            SpacedRepCard.due_date < today_start
        )
        if conditions:
            overdue_query = overdue_query.where(*conditions)
        overdue_result = await self.db.execute(overdue_query)
        overdue = overdue_result.scalar() or 0

        return CardStats(
            total_cards=total_cards,
            cards_by_state=cards_by_state,
            avg_stability=avg_stability,
            avg_difficulty=avg_difficulty,
            due_today=due_today,
            overdue=overdue,
        )

    async def _count_cards_in_date_range(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
        extra_conditions: Optional[list] = None,
    ) -> int:
        """
        Count cards with due_date in a given range.

        Args:
            start: Inclusive lower bound (None = no lower bound)
            end: Exclusive upper bound (None = no upper bound)
            extra_conditions: Additional SQLAlchemy filter conditions (e.g., topic filter)

        Returns:
            Count of cards matching the date range and conditions.
        """
        query = select(func.count(SpacedRepCard.id))

        # Build date range filter
        if start is not None and end is not None:
            query = query.where(
                and_(SpacedRepCard.due_date >= start, SpacedRepCard.due_date < end)
            )
        elif start is not None:
            query = query.where(SpacedRepCard.due_date >= start)
        elif end is not None:
            query = query.where(SpacedRepCard.due_date < end)

        # Apply extra conditions (e.g., topic filter)
        if extra_conditions:
            query = query.where(*extra_conditions)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_review_forecast(
        self,
        topic_filter: Optional[str] = None,
    ) -> ReviewForecast:
        """
        Calculate review workload forecast for upcoming time periods.

        Provides a breakdown of how many cards are due across different time
        horizons. Used by the UI to help users plan their study sessions and
        visualize upcoming workload.

        Time buckets (mutually exclusive, no overlap):
        - overdue: Cards due before today (review backlog)
        - today: Cards due within the current calendar day
        - tomorrow: Cards due within the next calendar day
        - this_week: Cards due in days 3-7 (excludes today/tomorrow)
        - later: Cards due beyond the 7-day window

        This forecast helps users:
        - See if they have a backlog to catch up on (overdue)
        - Plan today's session (today + overdue = immediate workload)
        - Anticipate upcoming busy days (tomorrow, this_week)
        - Understand long-term card distribution (later)

        Args:
            topic_filter: Optional topic tag to filter forecast by.
                When provided, only cards with this tag are counted.

        Returns:
            ReviewForecast with card counts for each time bucket.

        Note:
            All time calculations use UTC and calendar day boundaries
            (midnight to midnight) for consistency.
        """
        # Define time boundaries (all calculations use UTC)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        day_after_tomorrow = tomorrow_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)

        # Build topic filter condition (reused across all queries)
        conditions = [SpacedRepCard.tags.any(topic_filter)] if topic_filter else None

        # Count cards in each time bucket using date range helper
        # Ranges use [start, end) notation: inclusive start, exclusive end
        return ReviewForecast(
            overdue=await self._count_cards_in_date_range(
                None, today_start, conditions
            ),
            today=await self._count_cards_in_date_range(
                today_start, tomorrow_start, conditions
            ),
            tomorrow=await self._count_cards_in_date_range(
                tomorrow_start, day_after_tomorrow, conditions
            ),
            this_week=await self._count_cards_in_date_range(
                day_after_tomorrow, week_end, conditions
            ),
            later=await self._count_cards_in_date_range(week_end, None, conditions),
        )

    def _to_response(self, card: SpacedRepCard) -> CardResponse:
        """Convert database model to response model."""
        return CardResponse(
            id=card.id,
            content_id=card.content_id,
            concept_id=card.concept_id,
            card_type=card.card_type,
            front=card.front,
            back=card.back,
            hints=card.hints or [],
            tags=card.tags or [],
            state=CardStateEnum(card.state or CardStateEnum.NEW.value),
            stability=card.stability or settings.FSRS_INITIAL_STABILITY,
            difficulty=card.difficulty or settings.FSRS_INITIAL_DIFFICULTY,
            due_date=card.due_date,
            last_reviewed=card.last_reviewed,
            repetitions=card.repetitions or 0,
            lapses=card.lapses or 0,
            total_reviews=card.total_reviews or 0,
            correct_reviews=card.correct_reviews or 0,
            language=card.language,
        )
