"""
Content Lineage Service

Provides utilities for querying the relationships between content, cards, and exercises.
This enables:
- Finding what cards/exercises were generated from a piece of content
- Checking if content already has cards/exercises for specific concepts
- Getting lineage statistics for analytics

Usage:
    from app.services.learning.lineage import LineageService

    lineage = LineageService(db)

    # Check if content has any cards/exercises
    has_cards = await lineage.has_cards_for_content(content_uuid)
    has_exercises = await lineage.has_exercises_for_content(content_uuid)

    # Get all cards/exercises for a content item
    cards = await lineage.get_cards_for_content(content_uuid)
    exercises = await lineage.get_exercises_for_content(content_uuid)

    # Get lineage summary
    summary = await lineage.get_content_lineage_summary(content_uuid)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Content
from app.db.models_learning import SpacedRepCard, Exercise, ExerciseContent

logger = logging.getLogger(__name__)


@dataclass
class ContentLineageSummary:
    """Summary of cards and exercises generated from a content item."""

    content_uuid: str
    content_title: Optional[str]
    total_cards: int
    total_exercises: int
    card_concepts: list[str]  # Unique concepts that have cards
    exercise_concepts: list[str]  # Unique concepts that have exercises
    card_types: dict[str, int]  # Count by card type
    exercise_types: dict[str, int]  # Count by exercise type


class LineageService:
    """Service for querying content lineage relationships."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the lineage service.

        Args:
            db: Async database session
        """
        self.db = db

    async def has_cards_for_content(self, content_uuid: str) -> bool:
        """
        Check if any cards exist for a content item.

        Args:
            content_uuid: UUID of the content

        Returns:
            True if at least one card exists for this content
        """
        result = await self.db.execute(
            select(func.count(SpacedRepCard.id))
            .where(SpacedRepCard.content_id == content_uuid)
        )
        count = result.scalar() or 0
        return count > 0

    async def has_exercises_for_content(self, content_uuid: str) -> bool:
        """
        Check if any exercises exist for a content item.

        Args:
            content_uuid: UUID of the content

        Returns:
            True if at least one exercise exists for this content
        """
        result = await self.db.execute(
            select(func.count(ExerciseContent.id))
            .where(ExerciseContent.content_uuid == content_uuid)
        )
        count = result.scalar() or 0
        return count > 0

    async def get_cards_for_content(
        self, content_uuid: str
    ) -> list[SpacedRepCard]:
        """
        Get all cards generated from a content item.

        Args:
            content_uuid: UUID of the content

        Returns:
            List of SpacedRepCard instances
        """
        result = await self.db.execute(
            select(SpacedRepCard)
            .where(SpacedRepCard.content_id == content_uuid)
            .order_by(SpacedRepCard.created_at)
        )
        return list(result.scalars().all())

    async def get_exercises_for_content(
        self, content_uuid: str
    ) -> list[Exercise]:
        """
        Get all exercises generated from a content item.

        Uses the junction table for the query.

        Args:
            content_uuid: UUID of the content

        Returns:
            List of Exercise instances
        """
        result = await self.db.execute(
            select(Exercise)
            .join(ExerciseContent, Exercise.id == ExerciseContent.exercise_id)
            .where(ExerciseContent.content_uuid == content_uuid)
            .order_by(Exercise.created_at)
        )
        return list(result.scalars().all())

    async def get_card_concepts_for_content(
        self, content_uuid: str
    ) -> set[str]:
        """
        Get the set of concept names that have cards for this content.

        Args:
            content_uuid: UUID of the content

        Returns:
            Set of concept names (lowercase)
        """
        result = await self.db.execute(
            select(SpacedRepCard.source_concept)
            .where(SpacedRepCard.content_id == content_uuid)
            .where(SpacedRepCard.source_concept.isnot(None))
            .distinct()
        )
        return {row[0].lower() for row in result.fetchall() if row[0]}

    async def get_exercise_concepts_for_content(
        self, content_uuid: str
    ) -> set[str]:
        """
        Get the set of concept names that have exercises for this content.

        Args:
            content_uuid: UUID of the content

        Returns:
            Set of concept names (lowercase)
        """
        result = await self.db.execute(
            select(Exercise.source_concept)
            .join(ExerciseContent, Exercise.id == ExerciseContent.exercise_id)
            .where(ExerciseContent.content_uuid == content_uuid)
            .where(Exercise.source_concept.isnot(None))
            .distinct()
        )
        return {row[0].lower() for row in result.fetchall() if row[0]}

    async def get_content_lineage_summary(
        self, content_uuid: str
    ) -> ContentLineageSummary:
        """
        Get a comprehensive summary of all cards and exercises for a content item.

        Args:
            content_uuid: UUID of the content

        Returns:
            ContentLineageSummary with counts and details
        """
        # Get content title
        result = await self.db.execute(
            select(Content.title).where(Content.content_uuid == content_uuid)
        )
        content_title = result.scalar_one_or_none()

        # Get cards
        cards = await self.get_cards_for_content(content_uuid)

        # Get exercises
        exercises = await self.get_exercises_for_content(content_uuid)

        # Collect unique concepts
        card_concepts = {
            c.source_concept.lower()
            for c in cards
            if c.source_concept
        }
        exercise_concepts = {
            e.source_concept.lower()
            for e in exercises
            if e.source_concept
        }

        # Count by type
        card_types: dict[str, int] = {}
        for card in cards:
            card_types[card.card_type] = card_types.get(card.card_type, 0) + 1

        exercise_types: dict[str, int] = {}
        for exercise in exercises:
            exercise_types[exercise.exercise_type] = (
                exercise_types.get(exercise.exercise_type, 0) + 1
            )

        return ContentLineageSummary(
            content_uuid=content_uuid,
            content_title=content_title,
            total_cards=len(cards),
            total_exercises=len(exercises),
            card_concepts=sorted(card_concepts),
            exercise_concepts=sorted(exercise_concepts),
            card_types=card_types,
            exercise_types=exercise_types,
        )

    async def get_source_content_for_card(
        self, card_id: int
    ) -> Optional[Content]:
        """
        Get the source content for a card.

        Args:
            card_id: Database ID of the card

        Returns:
            Content instance or None if not linked
        """
        result = await self.db.execute(
            select(Content)
            .join(SpacedRepCard, Content.id == SpacedRepCard.source_content_pk)
            .where(SpacedRepCard.id == card_id)
        )
        return result.scalar_one_or_none()

    async def get_source_contents_for_exercise(
        self, exercise_id: int
    ) -> list[Content]:
        """
        Get all source content items for an exercise.

        An exercise can be generated from multiple content items.

        Args:
            exercise_id: Database ID of the exercise

        Returns:
            List of Content instances
        """
        result = await self.db.execute(
            select(Content)
            .join(ExerciseContent, Content.id == ExerciseContent.content_id)
            .where(ExerciseContent.exercise_id == exercise_id)
        )
        return list(result.scalars().all())

    async def delete_cards_for_content(
        self, content_uuid: str
    ) -> int:
        """
        Delete all cards for a content item.

        Useful for re-processing content with fresh card generation.

        Args:
            content_uuid: UUID of the content

        Returns:
            Number of cards deleted
        """
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(SpacedRepCard)
            .where(SpacedRepCard.content_id == content_uuid)
        )
        await self.db.commit()
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} cards for content {content_uuid}")
        return deleted_count

    async def delete_exercises_for_content(
        self, content_uuid: str
    ) -> int:
        """
        Delete all exercises linked to a content item.

        Note: This only deletes exercises that are ONLY linked to this content.
        Exercises linked to multiple contents are preserved.

        Useful for re-processing content with fresh exercise generation.

        Args:
            content_uuid: UUID of the content

        Returns:
            Number of exercises deleted
        """
        from sqlalchemy import delete

        # First, get exercises that are ONLY linked to this content
        # (to avoid deleting exercises that are shared)
        result = await self.db.execute(
            select(ExerciseContent.exercise_id)
            .where(ExerciseContent.content_uuid == content_uuid)
        )
        exercise_ids = [row[0] for row in result.fetchall()]

        if not exercise_ids:
            return 0

        # Check which exercises are only linked to this content
        exercises_to_delete = []
        for exercise_id in exercise_ids:
            count_result = await self.db.execute(
                select(func.count(ExerciseContent.id))
                .where(ExerciseContent.exercise_id == exercise_id)
            )
            link_count = count_result.scalar() or 0
            if link_count == 1:
                # Only linked to this content, safe to delete
                exercises_to_delete.append(exercise_id)

        # Delete the junction table entries first (cascade should handle this)
        await self.db.execute(
            delete(ExerciseContent)
            .where(ExerciseContent.content_uuid == content_uuid)
        )

        # Delete exercises that were only linked to this content
        deleted_count = 0
        if exercises_to_delete:
            result = await self.db.execute(
                delete(Exercise)
                .where(Exercise.id.in_(exercises_to_delete))
            )
            deleted_count = result.rowcount

        await self.db.commit()
        logger.info(
            f"Deleted {deleted_count} exercises for content {content_uuid}"
        )
        return deleted_count
