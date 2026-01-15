"""
Practice Session Service

Orchestrates practice sessions by combining spaced repetition cards
and exercises into balanced learning sessions.

Session composition is fully configurable:
- Content mode: exercises only, cards only, or both
- Source preference: use existing, generate new, or prefer existing
- Time allocation ratios for exercises vs cards
- Interleaving strategy for optimal learning

Configuration hierarchy:
1. Request parameters (highest priority)
2. Settings defaults (configurable in frontend settings page)
3. Hardcoded fallbacks (lowest priority)

Usage:
    from app.services.learning.session_service import SessionService

    service = SessionService(db, spaced_rep_service, exercise_generator, mastery_service)

    session = await service.create_session(
        SessionCreateRequest(
            duration_minutes=15,
            content_mode=SessionContentMode.BOTH,
            exercise_source=ContentSourcePreference.PREFER_EXISTING,
        )
    )
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from itertools import zip_longest
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models_learning import ExerciseAttempt, PracticeSession, Exercise
from app.enums.learning import (
    ExerciseType,
    ExerciseDifficulty,
    SessionContentMode,
    ContentSourcePreference,
)

# TYPE_CHECKING to import MasteryService - provides type hints for static analysis
# while avoiding circular imports at runtime.
if TYPE_CHECKING:
    from app.services.learning.mastery_service import MasteryService

from app.models.learning import (
    SessionCreateRequest,
    SessionResponse,
    SessionItem,
    SessionSummary,
    ExerciseGenerateRequest,
    ExerciseResponse,
    CardResponse,
)
from app.services.learning.spaced_rep_service import SpacedRepService
from app.services.learning.exercise_generator import ExerciseGenerator
from app.services.learning.session_budget import (
    SessionTimeBudget,
    resolve_content_mode,
    resolve_exercise_source,
    resolve_card_source,
)

logger = logging.getLogger(__name__)


class SessionService:
    """
    Practice session orchestration service.

    Creates balanced practice sessions combining:
    - Due spaced repetition cards (consolidation)
    - Weak spot exercises (deliberate practice)
    - New/interleaved content (transfer)

    Configuration is controlled by:
    - SessionCreateRequest parameters
    - Settings defaults (SESSION_* settings)
    - SessionTimeBudget for time allocation
    """

    def __init__(
        self,
        db: AsyncSession,
        spaced_rep_service: SpacedRepService,
        exercise_generator: ExerciseGenerator,
        mastery_service: Optional[MasteryService] = None,
    ):
        """
        Initialize session service.

        Args:
            db: Database session
            spaced_rep_service: Spaced repetition service for cards
            exercise_generator: Exercise generator for creating exercises
            mastery_service: Mastery tracking service (optional)
        """
        self.db = db
        self.spaced_rep = spaced_rep_service
        self.exercise_gen = exercise_generator
        self.mastery_service = mastery_service

    # =========================================================================
    # Main Entry Points
    # =========================================================================

    async def create_session(
        self,
        request: SessionCreateRequest,
    ) -> SessionResponse:
        """
        Create a new practice session with configurable content.

        Session content is determined by:
        1. content_mode: What to include (exercises, cards, or both)
        2. exercise_source/card_source: How to source content
        3. topic_filter: Focus on a specific topic (optional)
        4. duration_minutes: Target session duration

        Args:
            request: Session creation request with configuration

        Returns:
            Session response with items ready for practice

        Raises:
            RuntimeError: If no content could be generated for the session
        """
        # Resolve configuration from request + settings defaults
        config = self._resolve_configuration(request)

        # Create time budget manager
        budget = SessionTimeBudget(
            total_minutes=request.duration_minutes,
            content_mode=config["content_mode"],
            exercise_ratio=request.exercise_ratio,
            topic_selected=request.topic_filter is not None,
        )

        logger.info(
            f"Creating session: duration={request.duration_minutes}min, "
            f"mode={config['content_mode'].value}, topic={request.topic_filter}"
        )

        # Create session record
        session = await self._create_session_record(request)

        # Collect items and topics
        items: list[SessionItem] = []
        topics_covered: set[str] = set()

        # Get mastery level for topic (used for exercise selection)
        mastery_level = await self._get_topic_mastery(request.topic_filter)

        # Step 1: Add exercises (if enabled)
        if config["content_mode"] != SessionContentMode.CARDS_ONLY:
            exercise_items, exercise_topics = await self._collect_exercises(
                topic=request.topic_filter,
                mastery_level=mastery_level,
                budget=budget,
                source_preference=config["exercise_source"],
            )
            items.extend(exercise_items)
            topics_covered.update(exercise_topics)

        # Step 2: Add cards (if enabled)
        if config["content_mode"] != SessionContentMode.EXERCISES_ONLY:
            card_items, card_topics = await self._collect_cards(
                topic=request.topic_filter,
                budget=budget,
                source_preference=config["card_source"],
            )
            items.extend(card_items)
            topics_covered.update(card_topics)

        # Step 3: Fill remaining time if possible
        items, topics_covered = await self._fill_remaining_time(
            items=items,
            topics_covered=topics_covered,
            topic=request.topic_filter,
            mastery_level=mastery_level,
            budget=budget,
            config=config,
        )

        # Validate we have content
        if not items:
            self._handle_empty_session(request, session)

        # Apply interleaving for optimal learning
        items = self._interleave_items(items)

        # Calculate final session stats
        estimated_duration = sum(item.estimated_minutes for item in items)

        # Update session record with results
        await self._update_session_record(session, items, topics_covered)

        logger.info(
            f"Created session {session.id}: {len(items)} items "
            f"({budget.exercise_count} exercises, {budget.card_count} cards), "
            f"~{estimated_duration:.0f}min, topics={topics_covered}"
        )

        return SessionResponse(
            session_id=session.id,
            items=items,
            estimated_duration_minutes=estimated_duration,
            topics_covered=list(topics_covered),
            session_type=request.session_type,
        )

    async def end_session(self, session_id: int) -> SessionSummary:
        """
        End a practice session and calculate summary.

        Args:
            session_id: Session ID to end

        Returns:
            Session summary with statistics

        Raises:
            ValueError: If session not found
        """
        # Load session
        result = await self.db.execute(
            select(PracticeSession).where(PracticeSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Update end time (timezone-aware UTC)
        session.ended_at = datetime.now(timezone.utc)

        # Calculate duration
        duration_minutes = 0.0
        if session.started_at:
            delta = session.ended_at - session.started_at
            duration_minutes = delta.total_seconds() / 60

        session.duration_minutes = int(duration_minutes)

        # Calculate average score from exercise attempts
        score_result = await self.db.execute(
            select(func.avg(ExerciseAttempt.score)).where(
                ExerciseAttempt.session_id == session_id
            )
        )
        avg_score = score_result.scalar() or 0.0
        session.average_score = avg_score

        await self.db.commit()

        # Calculate mastery changes if available
        mastery_changes = await self._calculate_mastery_changes(session)

        return SessionSummary(
            session_id=session.id,
            duration_minutes=duration_minutes,
            cards_reviewed=session.total_cards or 0,
            exercises_completed=session.exercise_count or 0,
            correct_count=session.correct_count or 0,
            total_count=(session.total_cards or 0) + (session.exercise_count or 0),
            average_score=avg_score,
            mastery_changes=mastery_changes,
        )

    # =========================================================================
    # Configuration Resolution
    # =========================================================================

    def _resolve_configuration(
        self,
        request: SessionCreateRequest,
    ) -> dict:
        """
        Resolve all configuration options from request and settings.

        Merges request parameters with settings defaults, handling:
        - Content mode (exercises, cards, both)
        - Exercise source preference
        - Card source preference

        Args:
            request: Session creation request

        Returns:
            Dict with resolved configuration values
        """
        return {
            "content_mode": resolve_content_mode(request.content_mode),
            "exercise_source": resolve_exercise_source(request.exercise_source),
            "card_source": resolve_card_source(request.card_source),
        }

    # =========================================================================
    # Exercise Collection
    # =========================================================================

    async def _collect_exercises(
        self,
        topic: Optional[str],
        mastery_level: float,
        budget: SessionTimeBudget,
        source_preference: ContentSourcePreference,
    ) -> tuple[list[SessionItem], set[str]]:
        """
        Collect exercises for the session based on budget and preferences.

        Args:
            topic: Optional topic filter
            mastery_level: Current mastery level (0-1)
            budget: Time budget manager
            source_preference: How to source exercises

        Returns:
            Tuple of (exercise items, topics covered)
        """
        items: list[SessionItem] = []
        topics_covered: set[str] = set()
        max_exercises = budget.max_exercises()

        if max_exercises <= 0:
            return items, topics_covered

        logger.debug(
            f"Collecting exercises: topic={topic}, max={max_exercises}, "
            f"source={source_preference.value}"
        )

        # Get existing exercises if allowed
        existing_exercises: list[ExerciseResponse] = []
        if source_preference != ContentSourcePreference.GENERATE_NEW:
            existing_exercises = await self._get_existing_exercises(
                topic=topic,
                limit=max_exercises,
                mastery_level=mastery_level,
            )
            logger.debug(f"Found {len(existing_exercises)} existing exercises")

        # Add existing exercises
        for exercise in existing_exercises:
            if not budget.can_fit_exercise(exercise.estimated_time_minutes)[0]:
                break
            items.append(self._create_exercise_item(exercise))
            budget.add_exercise(exercise.estimated_time_minutes)
            if topic:
                topics_covered.add(topic)
            elif exercise.topic:
                topics_covered.add(exercise.topic)

        # Generate more if needed and allowed
        if source_preference != ContentSourcePreference.EXISTING_ONLY:
            generated = await self._generate_exercises(
                topic=topic,
                mastery_level=mastery_level,
                budget=budget,
                existing_count=len(items),
            )
            for exercise in generated:
                if not budget.can_fit_exercise(exercise.estimated_time_minutes)[0]:
                    break
                items.append(self._create_exercise_item(exercise))
                budget.add_exercise(exercise.estimated_time_minutes)
                if exercise.topic:
                    topics_covered.add(exercise.topic)

        logger.info(f"Collected {len(items)} exercises")
        return items, topics_covered

    async def _get_existing_exercises(
        self,
        topic: Optional[str],
        limit: int = 10,
        mastery_level: float = 0.5,
    ) -> list[ExerciseResponse]:
        """
        Fetch existing exercises from the database.

        Exercises are selected based on mastery level to match appropriate
        difficulty. Results are randomized to provide variety across sessions.

        Args:
            topic: Topic path to filter by (or None for any)
            limit: Maximum number of exercises to return
            mastery_level: Current mastery level (0-1) for difficulty selection

        Returns:
            List of existing exercises
        """
        if not topic:
            return []

        logger.debug(
            f"Looking for existing exercises: topic='{topic}', "
            f"limit={limit}, mastery={mastery_level}"
        )

        # Map mastery to appropriate difficulties
        difficulties = self._get_difficulties_for_mastery(mastery_level)
        logger.debug(f"Filtering by difficulties: {difficulties}")

        # Query with difficulty filter
        query = (
            select(Exercise)
            .where(Exercise.topic.ilike(f"%{topic}%"))
            .where(Exercise.difficulty.in_(difficulties))
            .order_by(func.random())
            .limit(limit)
        )

        result = await self.db.execute(query)
        exercises = result.scalars().all()
        logger.debug(f"Found {len(exercises)} exercises with difficulty filter")

        # Fallback: try without difficulty filter
        if not exercises:
            logger.debug("Trying without difficulty filter...")
            query = (
                select(Exercise)
                .where(Exercise.topic.ilike(f"%{topic}%"))
                .order_by(func.random())
                .limit(limit)
            )
            result = await self.db.execute(query)
            exercises = result.scalars().all()
            logger.debug(f"Found {len(exercises)} exercises without filter")

        return [self._exercise_to_response(ex) for ex in exercises]

    async def _generate_exercises(
        self,
        topic: Optional[str],
        mastery_level: float,
        budget: SessionTimeBudget,
        existing_count: int,
    ) -> list[ExerciseResponse]:
        """
        Generate new exercises via LLM.

        Args:
            topic: Topic to generate for
            mastery_level: Current mastery level
            budget: Time budget manager
            existing_count: Number of existing exercises already added

        Returns:
            List of generated exercises
        """
        if not topic:
            return []

        exercises: list[ExerciseResponse] = []
        max_to_generate = budget.max_exercises() - existing_count

        if max_to_generate <= 0:
            return exercises

        logger.debug(f"Generating up to {max_to_generate} new exercises")

        for i in range(max_to_generate):
            if not budget.can_fit_exercise(settings.SESSION_TIME_PER_EXERCISE)[0]:
                break

            try:
                exercise, _usages = await self.exercise_gen.generate_exercise(
                    request=ExerciseGenerateRequest(topic=topic),
                    mastery_level=mastery_level,
                    ensure_topic=True,
                )
                exercises.append(exercise)
                logger.debug(f"Generated exercise {i+1}/{max_to_generate}")
            except Exception as e:
                logger.warning(f"Failed to generate exercise: {e}")
                # If we have no exercises at all and this is the first one, re-raise
                if existing_count == 0 and len(exercises) == 0:
                    raise RuntimeError(
                        f"Failed to generate exercise for topic '{topic}'. "
                        f"Please try again or select a different topic. Error: {e}"
                    ) from e
                break

        return exercises

    def _get_difficulties_for_mastery(
        self,
        mastery_level: float,
    ) -> list[str]:
        """
        Map mastery level to appropriate exercise difficulties.

        Args:
            mastery_level: Current mastery (0-1)

        Returns:
            List of difficulty values to filter by
        """
        if mastery_level < 0.3:
            return [ExerciseDifficulty.FOUNDATIONAL.value]
        elif mastery_level < 0.7:
            return [
                ExerciseDifficulty.FOUNDATIONAL.value,
                ExerciseDifficulty.INTERMEDIATE.value,
            ]
        else:
            return [
                ExerciseDifficulty.INTERMEDIATE.value,
                ExerciseDifficulty.ADVANCED.value,
            ]

    def _create_exercise_item(self, exercise: ExerciseResponse) -> SessionItem:
        """Create a SessionItem from an exercise."""
        return SessionItem(
            item_type="exercise",
            exercise=exercise,
            estimated_minutes=exercise.estimated_time_minutes,
        )

    def _exercise_to_response(self, exercise: Exercise) -> ExerciseResponse:
        """Convert Exercise DB model to ExerciseResponse."""
        return ExerciseResponse(
            id=exercise.id,
            exercise_uuid=exercise.exercise_uuid,
            exercise_type=ExerciseType(exercise.exercise_type),
            topic=exercise.topic,
            difficulty=ExerciseDifficulty(exercise.difficulty),
            prompt=exercise.prompt,
            hints=exercise.hints or [],
            expected_key_points=exercise.expected_key_points or [],
            worked_example=exercise.worked_example,
            follow_up_problem=exercise.follow_up_problem,
            language=exercise.language,
            starter_code=exercise.starter_code,
            buggy_code=exercise.buggy_code,
            estimated_time_minutes=exercise.estimated_time_minutes or 10,
            tags=exercise.tags or [],
        )

    # =========================================================================
    # Card Collection
    # =========================================================================

    async def _collect_cards(
        self,
        topic: Optional[str],
        budget: SessionTimeBudget,
        source_preference: ContentSourcePreference,
    ) -> tuple[list[SessionItem], set[str]]:
        """
        Collect spaced repetition cards for the session.

        Args:
            topic: Optional topic filter
            budget: Time budget manager
            source_preference: How to source cards (currently only due cards supported)

        Returns:
            Tuple of (card items, topics covered)
        """
        items: list[SessionItem] = []
        topics_covered: set[str] = set()
        max_cards = budget.max_cards()

        if max_cards <= 0:
            return items, topics_covered

        logger.debug(f"Collecting cards: topic={topic}, max={max_cards}")

        # Get due cards (existing_only and prefer_existing both use due cards)
        # generate_new for cards would mean creating new cards, which we don't support yet
        due_response = await self.spaced_rep.get_due_cards(
            limit=max_cards,
            topic_filter=topic,
        )

        for card in due_response.cards:
            if not budget.can_fit_card(settings.SESSION_TIME_PER_CARD)[0]:
                break

            items.append(self._create_card_item(card))
            budget.add_card(settings.SESSION_TIME_PER_CARD)

            # Collect topics from card tags
            for tag in card.tags or []:
                topics_covered.add(tag)

        logger.info(f"Collected {len(items)} cards")
        return items, topics_covered

    def _create_card_item(self, card: CardResponse) -> SessionItem:
        """Create a SessionItem from a card."""
        return SessionItem(
            item_type="card",
            card=card,
            estimated_minutes=settings.SESSION_TIME_PER_CARD,
        )

    # =========================================================================
    # Fill Remaining Time
    # =========================================================================

    async def _fill_remaining_time(
        self,
        items: list[SessionItem],
        topics_covered: set[str],
        topic: Optional[str],
        mastery_level: float,
        budget: SessionTimeBudget,
        config: dict,
    ) -> tuple[list[SessionItem], set[str]]:
        """
        Fill any remaining time budget with additional content.

        Tries to add more content if there's significant time remaining.
        Prioritizes based on what's already in the session.

        Note: This is a "best effort" phase - failures are logged but don't
        raise errors since we already have items in the session.

        Args:
            items: Current session items
            topics_covered: Topics already covered
            topic: Topic filter (if any)
            mastery_level: Current mastery level
            budget: Time budget manager
            config: Resolved configuration

        Returns:
            Updated (items, topics_covered)
        """
        remaining = budget.total_remaining

        # Only fill if we have meaningful time remaining
        if remaining < settings.SESSION_MIN_TIME_FOR_EXERCISE:
            return items, topics_covered

        logger.debug(f"Filling remaining {remaining:.1f}min")

        content_mode = config["content_mode"]

        # Try to add more exercises if we have room and it's allowed
        if content_mode != SessionContentMode.CARDS_ONLY:
            if budget.can_fit_exercise(settings.SESSION_TIME_PER_EXERCISE)[0]:
                try:
                    more_exercises, more_topics = await self._collect_exercises(
                        topic=topic,
                        mastery_level=mastery_level,
                        budget=budget,
                        source_preference=config["exercise_source"],
                    )
                    # Filter to avoid duplicates
                    existing_ids = {
                        item.exercise.id
                        for item in items
                        if item.item_type == "exercise" and item.exercise
                    }
                    for ex_item in more_exercises:
                        if ex_item.exercise and ex_item.exercise.id not in existing_ids:
                            items.append(ex_item)
                            existing_ids.add(ex_item.exercise.id)
                    topics_covered.update(more_topics)
                except RuntimeError as e:
                    # Best effort - log and continue if we already have items
                    logger.debug(f"Could not add more exercises during fill: {e}")

        # Try to add more cards if we have room and it's allowed
        if content_mode != SessionContentMode.EXERCISES_ONLY:
            if budget.can_fit_card(settings.SESSION_TIME_PER_CARD)[0]:
                more_cards, more_topics = await self._collect_cards(
                    topic=topic,
                    budget=budget,
                    source_preference=config["card_source"],
                )
                # Filter to avoid duplicates
                existing_ids = {
                    item.card.id
                    for item in items
                    if item.item_type == "card" and item.card
                }
                for card_item in more_cards:
                    if card_item.card and card_item.card.id not in existing_ids:
                        items.append(card_item)
                        existing_ids.add(card_item.card.id)
                topics_covered.update(more_topics)

        return items, topics_covered

    # =========================================================================
    # Interleaving
    # =========================================================================

    def _interleave_items(self, items: list[SessionItem]) -> list[SessionItem]:
        """
        Interleave session items by content type for optimal learning.

        This method handles CONTENT-TYPE interleaving: mixing cards with exercises
        within a practice session. It operates on SessionItem objects which can
        be either cards or exercises.

        Strategy:
        1. Worked examples placed first (scaffolding for novices)
        2. Remaining items shuffled (interleaving benefit)
        3. Cards and exercises mixed throughout (spaced practice)

        This follows learning science research showing:
        - Worked examples help novices build initial schemas
        - Interleaving improves transfer and discrimination
        - Mixing content types prevents blocking effects

        Note:
            This is complementary to SpacedRepService._interleave_by_topic(),
            which handles TOPIC interleaving (mixing cards from different topics).
            When cards come from get_due_cards(), they are already topic-interleaved;
            this method then mixes those cards with exercises.

        See Also:
            SpacedRepService._interleave_by_topic: Topic-based card interleaving

        Args:
            items: Session items to interleave

        Returns:
            Interleaved items list
        """
        if not settings.SESSION_INTERLEAVE_ENABLED:
            return items

        # Separate by type
        worked_examples: list[SessionItem] = []
        cards: list[SessionItem] = []
        other_exercises: list[SessionItem] = []

        for item in items:
            if item.item_type == "card":
                cards.append(item)
            elif (
                item.item_type == "exercise"
                and item.exercise
                and item.exercise.exercise_type == ExerciseType.WORKED_EXAMPLE
            ):
                worked_examples.append(item)
            else:
                other_exercises.append(item)

        # Build interleaved list
        result: list[SessionItem] = []

        # Worked examples first (if setting enabled)
        if settings.SESSION_WORKED_EXAMPLES_FIRST:
            result.extend(worked_examples)
        else:
            other_exercises.extend(worked_examples)

        # Shuffle and interleave remaining items
        # Create alternating pattern of cards and exercises
        random.shuffle(cards)
        random.shuffle(other_exercises)

        # Interleave cards and exercises
        interleaved = self._alternate_merge(cards, other_exercises)
        result.extend(interleaved)

        return result

    def _alternate_merge(
        self,
        list_a: list[SessionItem],
        list_b: list[SessionItem],
    ) -> list[SessionItem]:
        """
        Merge two lists in an alternating pattern.

        Creates a mixed sequence that alternates between the two lists,
        distributing items as evenly as possible. Uses itertools.zip_longest
        to handle unequal list lengths gracefully.

        Args:
            list_a: First list (e.g., cards)
            list_b: Second list (e.g., exercises)

        Returns:
            Merged list with alternating items
        """
        # Sentinel to detect fill values from zip_longest
        sentinel = object()
        return [
            item
            for pair in zip_longest(list_a, list_b, fillvalue=sentinel)
            for item in pair
            if item is not sentinel
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_topic_mastery(self, topic: Optional[str]) -> float:
        """
        Get mastery level for a topic.

        Args:
            topic: Topic path to check

        Returns:
            Mastery level (0-1), defaults to 0.5 if unknown
        """
        if not topic or not self.mastery_service:
            return 0.5

        try:
            mastery_state = await self.mastery_service.get_mastery_state(topic)
            return mastery_state.mastery_score
        except Exception:
            return 0.5

    async def _create_session_record(
        self,
        request: SessionCreateRequest,
    ) -> PracticeSession:
        """Create initial session record in database."""
        session = PracticeSession(
            session_type=request.session_type.value,
            started_at=datetime.utcnow(),
            total_cards=0,
            correct_count=0,
            topics_covered=[],
            exercise_count=0,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def _update_session_record(
        self,
        session: PracticeSession,
        items: list[SessionItem],
        topics_covered: set[str],
    ):
        """Update session record with final stats."""
        session.topics_covered = list(topics_covered)
        session.total_cards = sum(1 for i in items if i.item_type == "card")
        session.exercise_count = sum(1 for i in items if i.item_type == "exercise")
        await self.db.commit()

    def _handle_empty_session(
        self,
        request: SessionCreateRequest,
        session: PracticeSession,
    ):
        """Handle case where no items could be collected."""
        if request.topic_filter:
            raise RuntimeError(
                f"No content available for topic '{request.topic_filter}'. "
                "Please try a different topic or add more content."
            )
        else:
            # No topic filter and no items - user has no content to practice
            logger.info(
                f"Session {session.id} created with no items - "
                "user has no content to practice"
            )

    async def _calculate_mastery_changes(
        self,
        session: PracticeSession,
    ) -> dict[str, float]:
        """Calculate mastery changes for session topics."""
        mastery_changes: dict[str, float] = {}

        if not self.mastery_service or not session.topics_covered:
            return mastery_changes

        for topic in session.topics_covered:
            try:
                state = await self.mastery_service.get_mastery_state(topic)
                mastery_changes[topic] = state.mastery_score
            except Exception:
                pass

        return mastery_changes
