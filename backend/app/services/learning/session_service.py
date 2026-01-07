"""
Practice Session Service

Orchestrates practice sessions by combining spaced repetition cards
and exercises into balanced learning sessions.

Session composition follows learning science principles:
- 40% due spaced rep cards (consolidation)
- 30% weak spot exercises (deliberate practice)
- 30% new/interleaved content (transfer)

Usage:
    from app.services.learning.session_service import SessionService

    service = SessionService(db, spaced_rep_service, exercise_generator, mastery_service)

    session = await service.create_session(
        SessionCreateRequest(duration_minutes=15)
    )
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models_learning import ExerciseAttempt, PracticeSession
from app.enums.learning import ExerciseType

# TYPE_CHECKING to import MasteryService - this provides proper type hints for static analysis
# while avoiding circular imports at runtime.
if TYPE_CHECKING:
    from app.services.learning.mastery_service import MasteryService

from app.models.learning import (
    SessionCreateRequest,
    SessionResponse,
    SessionItem,
    SessionSummary,
    ExerciseGenerateRequest,
)
from app.services.learning.spaced_rep_service import SpacedRepService
from app.services.learning.exercise_generator import ExerciseGenerator

logger = logging.getLogger(__name__)


class SessionService:
    """
    Practice session orchestration service.

    Creates balanced practice sessions combining:
    - Due spaced repetition cards
    - Weak spot exercises
    - New/interleaved content

    Time allocation and item durations are configured in settings:
    - SESSION_TIME_RATIO_* for allocation ratios
    - SESSION_TIME_PER_CARD/EXERCISE for estimated durations
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
            spaced_rep_service: Spaced repetition service
            exercise_generator: Exercise generator
            mastery_service: Mastery tracking service (optional)
        """
        self.db = db
        self.spaced_rep = spaced_rep_service
        self.exercise_gen = exercise_generator
        self.mastery_service = mastery_service

    async def create_session(
        self,
        request: SessionCreateRequest,
    ) -> SessionResponse:
        """
        Create a new practice session with balanced content.

        Args:
            request: Session creation request

        Returns:
            Session response with items
        """
        duration = request.duration_minutes
        items: list[SessionItem] = []
        topics_covered: set[str] = set()

        # Create session record
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

        # Calculate time allocation using settings
        time_per_card = settings.SESSION_TIME_PER_CARD
        time_per_exercise = settings.SESSION_TIME_PER_EXERCISE

        spaced_rep_time = duration * settings.SESSION_TIME_RATIO_SPACED_REP
        weak_spot_time = duration * settings.SESSION_TIME_RATIO_WEAK_SPOTS
        new_content_time = duration * settings.SESSION_TIME_RATIO_NEW_CONTENT

        # Track remaining time budgets for each category
        remaining_weak_spot_time = weak_spot_time
        remaining_new_content_time = new_content_time

        # 1. Get due spaced rep cards (consolidation)
        max_cards = int(spaced_rep_time / time_per_card)
        if max_cards > 0:
            due_response = await self.spaced_rep.get_due_cards(
                limit=max_cards,
                topic_filter=request.topic_filter,
            )

            for card in due_response.cards:
                items.append(
                    SessionItem(
                        item_type="card",
                        card=card,
                        estimated_minutes=time_per_card,
                    )
                )
                # Track topics from card tags
                for tag in card.tags or []:
                    topics_covered.add(tag)

        # 2. Generate weak spot exercises (deliberate practice)
        if self.mastery_service and remaining_weak_spot_time >= time_per_exercise:
            weak_spots = await self.mastery_service.get_weak_spots(
                limit=settings.SESSION_MAX_WEAK_SPOTS
            )

            for weak_spot in weak_spots:
                if remaining_weak_spot_time < time_per_exercise:
                    break

                try:
                    exercise = await self.exercise_gen.generate_exercise(
                        request=ExerciseGenerateRequest(
                            topic=weak_spot.topic,
                            exercise_type=None,  # Auto-select based on mastery
                        ),
                        mastery_level=weak_spot.mastery_score,
                    )

                    items.append(
                        SessionItem(
                            item_type="exercise",
                            exercise=exercise,
                            estimated_minutes=exercise.estimated_time_minutes,
                        )
                    )
                    topics_covered.add(weak_spot.topic)
                    remaining_weak_spot_time -= exercise.estimated_time_minutes
                except Exception as e:
                    logger.warning(f"Failed to generate weak spot exercise: {e}")

        # 3. Generate new content exercise (interleaving/transfer)
        if request.topic_filter and remaining_new_content_time >= time_per_exercise:
            # Get mastery level for topic if available
            mastery_level = 0.5
            if self.mastery_service:
                try:
                    mastery_state = await self.mastery_service.get_mastery_state(
                        request.topic_filter
                    )
                    mastery_level = mastery_state.mastery_score
                except Exception:
                    pass

            try:
                exercise = await self.exercise_gen.generate_exercise(
                    request=ExerciseGenerateRequest(
                        topic=request.topic_filter,
                    ),
                    mastery_level=mastery_level,
                )

                items.append(
                    SessionItem(
                        item_type="exercise",
                        exercise=exercise,
                        estimated_minutes=exercise.estimated_time_minutes,
                    )
                )
                topics_covered.add(request.topic_filter)
            except Exception as e:
                logger.warning(f"Failed to generate topic exercise: {e}")

        # Interleave items (worked examples first, then shuffle rest)
        items = self._interleave_items(items)

        # Calculate total estimated duration
        estimated_duration = sum(item.estimated_minutes for item in items)

        # Update session record
        session.topics_covered = list(topics_covered)
        session.total_cards = sum(1 for i in items if i.item_type == "card")
        session.exercise_count = sum(1 for i in items if i.item_type == "exercise")
        await self.db.commit()

        logger.info(
            f"Created session {session.id}: {len(items)} items, "
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
        mastery_changes: dict[str, float] = {}
        if self.mastery_service and session.topics_covered:
            for topic in session.topics_covered:
                try:
                    # TODO: This would require before/after comparison
                    #       For now, just note the current mastery
                    state = await self.mastery_service.get_mastery_state(topic)
                    mastery_changes[topic] = state.mastery_score
                except Exception:
                    pass

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

    def _interleave_items(self, items: list[SessionItem]) -> list[SessionItem]:
        """
        Interleave session items for optimal learning.

        - Worked examples stay at the start (scaffolding for novices)
        - Other items are shuffled (interleaving benefit)
        """
        # Separate worked examples
        worked_examples = []
        other_items = []

        for item in items:
            if (
                item.item_type == "exercise"
                and item.exercise
                and item.exercise.exercise_type == ExerciseType.WORKED_EXAMPLE
            ):
                worked_examples.append(item)
            else:
                other_items.append(item)

        # Shuffle other items
        random.shuffle(other_items)

        # Worked examples first, then shuffled rest
        return worked_examples + other_items
