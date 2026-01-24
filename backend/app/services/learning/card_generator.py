"""
Card Generator Service

Generates spaced repetition cards from extracted concepts and content.
Supports both batch generation during ingestion and on-demand generation.

===============================================================================
SPACED REPETITION CARDS vs EXERCISES - Key Distinction
===============================================================================

SPACED REP CARDS (this module):
- Purpose: Active recall & long-term memory retention
- Format: Simple front/back flashcards (question → answer)
- Scheduling: FSRS algorithm optimizes review intervals based on memory decay
- Evaluation: LLM-evaluated - user types answer, LLM grades and assigns FSRS rating
- Generation: Created during content ingestion OR on-demand from Review Queue
- UI: Appears in /review (Review Queue page)
- Use case: "I want to remember this fact/definition/concept"

EXERCISES (see exercise_generator.py):
- Purpose: Active practice & skill application
- Format: Rich prompts with worked examples, code, hints, key points
- Scheduling: Mastery-based (adapts exercise TYPE to skill level)
- Evaluation: LLM-evaluated with detailed feedback on what was correct/missing
- Generation: Created during content ingestion AND on-demand during Practice Sessions
- UI: Appears in /practice (Practice Session page)
- Use case: "I want to practice applying this concept"

===============================================================================
Card Types Generated
===============================================================================

From concepts (during ingestion):
- Definition cards: "What is X?" → concept definition
- Properties cards: "What are the key characteristics of X?" → bullet list
- Application cards: "Why is understanding X important?" → why_it_matters
- Example cards: "Give an example of X" → example content
- Misconception cards: "True or False: [wrong statement]" → correction

On-demand generation (via LLM):
- Definition cards: "What is X?"
- Comparison cards: "How does X differ from Y?"
- Application cards: "When would you use X?"
- Example cards: "Give an example of X"

===============================================================================

Usage:
    from app.services.learning.card_generator import CardGeneratorService

    generator = CardGeneratorService(db)

    # From concepts (during ingestion)
    cards = await generator.generate_from_concepts(extraction, content_id, tags)

    # On-demand for a topic
    cards = await generator.generate_for_topic(topic="ml/transformers", count=10)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models import Content
from app.db.models_learning import Exercise, SpacedRepCard
from app.enums.learning import CardState
from app.enums.pipeline import PipelineOperation
from app.models.llm_usage import LLMUsage
from app.models.processing import ExtractionResult
from app.services.llm.client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)


# Card generation prompt for on-demand generation
CARD_GENERATION_PROMPT = """Generate spaced repetition flashcards for learning about: {topic}

Context from knowledge base:
{context}

Generate {count} flashcards that test understanding of key concepts.
Each card should have:
- A clear question (front)
- A concise but complete answer (back)
- Optional hints for progressive revelation

Card types to include:
1. Definition cards - "What is X?"
2. Comparison cards - "How does X differ from Y?"
3. Application cards - "When would you use X?"
4. Example cards - "Give an example of X"

Return JSON:
{{
    "cards": [
        {{
            "card_type": "definition|comparison|application|example",
            "front": "Question text",
            "back": "Answer text",
            "hints": ["hint 1", "hint 2"]
        }}
    ]
}}

Guidelines:
- Questions should be specific and unambiguous
- Answers should be self-contained (understandable without context)
- Difficulty should vary from basic to advanced
- Include practical, real-world applications where relevant
"""


class CardGeneratorService:
    """Service for generating spaced repetition cards."""

    def __init__(self, db: AsyncSession, llm_client: LLMClient = None):
        """
        Initialize the card generator service.

        Args:
            db: Async database session for persisting cards
            llm_client: LLM client for on-demand generation (uses default if not provided)
        """
        self.db = db
        self.llm_client = llm_client or get_llm_client()

    async def generate_from_concepts(
        self,
        extraction: ExtractionResult,
        content_id: str,
        tags: list[str],
    ) -> tuple[list[SpacedRepCard], list[LLMUsage]]:
        """
        Generate cards from extracted concepts during content ingestion.

        Creates multiple card types from each concept:
        - Definition card: "What is X?" for each concept with a definition
        - Application card: "Why is understanding X important?" if why_it_matters exists
        - Example cards: "Give an example of X" (up to CARD_MAX_EXAMPLES_PER_CONCEPT)
        - Misconception cards: "True or False" style (up to CARD_MAX_MISCONCEPTIONS_PER_CONCEPT)
        - Properties card: "What are the key characteristics of X?" if >= CARD_MIN_PROPERTIES_FOR_CARD

        Args:
            extraction: Extraction result containing concepts from content processing
            content_id: UUID of source content for linking cards
            tags: Topic tags to apply to all generated cards

        Returns:
            Tuple of (persisted SpacedRepCard instances, LLM usages - empty for this method)
        """
        from sqlalchemy import select
        from app.db.models import Content

        cards = []
        usages = []

        # Look up the database PK for the ORM relationship
        result = await self.db.execute(
            select(Content.id).where(Content.content_uuid == content_id)
        )
        source_content_pk = result.scalar_one_or_none()

        for concept in extraction.concepts:
            # Skip concepts without definitions
            if not concept.definition:
                continue

            # 1. Definition card
            definition_card = SpacedRepCard(
                content_id=content_id,
                source_content_pk=source_content_pk,
                card_type="definition",
                front=f"What is {concept.name}?",
                back=concept.definition,
                hints=[concept.context] if concept.context else None,
                tags=tags,
                state=CardState.NEW.value,
                stability=0.0,
                difficulty=settings.CARD_DIFFICULTY_DEFINITION,
                due_date=datetime.now(timezone.utc),
            )
            cards.append(definition_card)

            # 2. Why it matters card (if available)
            if concept.why_it_matters:
                importance_card = SpacedRepCard(
                    content_id=content_id,
                    source_content_pk=source_content_pk,
                    card_type="application",
                    front=f"Why is understanding {concept.name} important?",
                    back=concept.why_it_matters,
                    tags=tags,
                    state=CardState.NEW.value,
                    stability=0.0,
                    difficulty=settings.CARD_DIFFICULTY_DEFINITION,
                    due_date=datetime.now(timezone.utc),
                )
                cards.append(importance_card)

            # 3. Example cards
            for i, example in enumerate(
                concept.examples[: settings.CARD_MAX_EXAMPLES_PER_CONCEPT]
            ):
                example_text = (
                    example.content if hasattr(example, "content") else str(example)
                )
                example_title = (
                    example.title if hasattr(example, "title") else f"Example {i+1}"
                )

                if example_text:
                    example_card = SpacedRepCard(
                        content_id=content_id,
                        source_content_pk=source_content_pk,
                        card_type="example",
                        front=f"Give an example of {concept.name}.",
                        back=(
                            f"{example_title}: {example_text}"
                            if example_title
                            else example_text
                        ),
                        hints=[concept.definition],
                        tags=tags,
                        state=CardState.NEW.value,
                        stability=0.0,
                        difficulty=settings.CARD_DIFFICULTY_EXAMPLE,
                        due_date=datetime.now(timezone.utc),
                    )
                    cards.append(example_card)

            # 4. Misconception cards (true/false style)
            for misconception in concept.misconceptions[
                : settings.CARD_MAX_MISCONCEPTIONS_PER_CONCEPT
            ]:
                wrong = (
                    misconception.wrong
                    if hasattr(misconception, "wrong")
                    else str(misconception)
                )
                correct = (
                    misconception.correct if hasattr(misconception, "correct") else ""
                )

                if wrong and correct:
                    misconception_card = SpacedRepCard(
                        content_id=content_id,
                        source_content_pk=source_content_pk,
                        card_type="misconception",
                        front=f"True or False: {wrong}",
                        back=f"FALSE. {correct}",
                        hints=[f"Think about {concept.name}"],
                        tags=tags,
                        state=CardState.NEW.value,
                        stability=0.0,
                        difficulty=settings.CARD_DIFFICULTY_MISCONCEPTION,
                        due_date=datetime.now(timezone.utc),
                    )
                    cards.append(misconception_card)

            # 5. Properties card (if multiple properties)
            if len(concept.properties) >= settings.CARD_MIN_PROPERTIES_FOR_CARD:
                properties_card = SpacedRepCard(
                    content_id=content_id,
                    source_content_pk=source_content_pk,
                    card_type="definition",
                    front=f"What are the key characteristics of {concept.name}?",
                    back="\n".join(f"• {p}" for p in concept.properties),
                    hints=[concept.definition],
                    tags=tags,
                    state=CardState.NEW.value,
                    stability=0.0,
                    difficulty=settings.CARD_DIFFICULTY_EXAMPLE,
                    due_date=datetime.now(timezone.utc),
                )
                cards.append(properties_card)

        # Bulk save all cards
        if cards:
            self.db.add_all(cards)
            await self.db.commit()

            # Refresh to get IDs
            for card in cards:
                await self.db.refresh(card)

            logger.info(
                f"Generated {len(cards)} cards from {len(extraction.concepts)} concepts"
            )

        return cards, usages

    async def generate_for_topic(
        self,
        topic: str,
        count: int = None,
        difficulty: str = "mixed",
    ) -> tuple[list[SpacedRepCard], list[LLMUsage]]:
        """
        Generate cards on-demand for a specific topic via LLM.

        Gathers context from existing content and exercises related to the topic,
        then uses LLM to generate contextually relevant flashcards.

        Args:
            topic: Topic path (e.g., "ml/transformers")
            count: Number of cards to generate (defaults to CARD_DEFAULT_COUNT)
            difficulty: Difficulty level ("easy", "medium", "hard", "mixed")

        Returns:
            Tuple of (persisted SpacedRepCard instances, LLM usages for cost tracking).
            Returns ([], []) if no relevant context found for the topic.
        """
        if count is None:
            count = settings.CARD_DEFAULT_COUNT

        usages = []

        # Gather context from existing content
        context = await self._gather_topic_context(topic)

        if not context:
            logger.warning(f"No context found for topic: {topic}")
            return [], []

        # Generate cards via LLM
        prompt = CARD_GENERATION_PROMPT.format(
            topic=topic,
            context=context[: settings.CARD_CONTEXT_MAX_LENGTH],
            count=count,
        )

        try:
            data, usage = await self.llm_client.complete(
                operation=PipelineOperation.CONCEPT_EXTRACTION,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.CARD_LLM_TEMPERATURE,
                max_tokens=settings.CARD_LLM_MAX_TOKENS,
                json_mode=True,
            )
            usages.append(usage)

            # Parse and create cards
            cards = []
            tags = [topic] if topic else []

            for card_data in data.get("cards", []):
                if not card_data.get("front") or not card_data.get("back"):
                    continue

                card = SpacedRepCard(
                    card_type=card_data.get("card_type", "definition"),
                    front=card_data["front"],
                    back=card_data["back"],
                    hints=card_data.get("hints"),
                    tags=tags,
                    state=CardState.NEW.value,
                    stability=0.0,
                    difficulty=self._map_difficulty(difficulty),
                    due_date=datetime.now(timezone.utc),
                )
                cards.append(card)

            # Save cards
            if cards:
                self.db.add_all(cards)
                await self.db.commit()

                for card in cards:
                    await self.db.refresh(card)

                logger.info(
                    f"Generated {len(cards)} on-demand cards for topic: {topic}"
                )

            return cards, usages

        except Exception as e:
            logger.error(f"On-demand card generation failed: {e}")
            return [], usages

    async def _gather_topic_context(self, topic: str) -> str:
        """
        Gather context from content and exercises related to a topic.

        Searches the knowledge base for relevant content to provide context
        for LLM-based card generation. Extracts keywords from the topic path
        and queries both Content summaries and Exercise prompts.

        Args:
            topic: Topic path (e.g., "ml/transformers" or "python-basics")

        Returns:
            Concatenated context string from matching content and exercises,
            or empty string if no relevant content found.
        """
        context_parts = []
        seen_content_ids = set()  # Avoid duplicates

        # Search for topic keywords in the topic path (e.g., "ml/transformers" -> "ml", "transformers")
        topic_keywords = (
            topic.replace("/", " ").replace("-", " ").replace("_", " ").split()
        )

        # Get content with matching title, summary, or raw_text
        # Use ILIKE for case-insensitive matching on any keyword
        for keyword in topic_keywords:
            if len(keyword) < settings.CARD_CONTEXT_MIN_KEYWORD_LENGTH:
                continue

            # Search by title first (most relevant)
            content_query = (
                select(Content)
                .where(Content.title.ilike(f"%{keyword}%"))
                .limit(settings.CARD_CONTEXT_CONTENT_PER_KEYWORD)
            )

            result = await self.db.execute(content_query)
            contents = result.scalars().all()

            for content in contents:
                if content.id in seen_content_ids:
                    continue
                seen_content_ids.add(content.id)

                # Use summary if available, otherwise use truncated raw_text
                text_content = content.summary if content.summary else None
                if not text_content and content.raw_text:
                    # Use first portion of raw_text as context
                    text_content = content.raw_text[
                        : settings.CARD_CONTEXT_MAX_LENGTH // 2
                    ]

                if text_content:
                    context_parts.append(f"From '{content.title}':\n{text_content}")

        # Get existing exercises for the topic
        exercise_query = (
            select(Exercise)
            .where(Exercise.topic.ilike(f"%{topic}%"))
            .limit(settings.CARD_CONTEXT_EXERCISES_LIMIT)
        )

        result = await self.db.execute(exercise_query)
        exercises = result.scalars().all()

        for exercise in exercises:
            if exercise.prompt:
                context_parts.append(
                    f"Exercise context:\n{exercise.prompt[:settings.CARD_CONTEXT_EXERCISE_PROMPT_LENGTH]}"
                )

        return "\n\n---\n\n".join(context_parts)

    def _map_difficulty(self, difficulty: str) -> float:
        """
        Map difficulty string to FSRS difficulty value.

        Args:
            difficulty: Human-readable difficulty ("easy", "medium", "hard", "mixed")

        Returns:
            FSRS difficulty float (0.0-1.0), defaults to CARD_DIFFICULTY_MIXED
        """
        mapping = {
            "easy": settings.CARD_DIFFICULTY_EASY,
            "medium": settings.CARD_DIFFICULTY_MEDIUM,
            "hard": settings.CARD_DIFFICULTY_HARD,
            "mixed": settings.CARD_DIFFICULTY_MIXED,
        }
        return mapping.get(difficulty.lower(), settings.CARD_DIFFICULTY_MIXED)

    async def ensure_minimum_cards(
        self,
        topic: str,
        minimum: int = None,
    ) -> tuple[int, list[LLMUsage]]:
        """
        Ensure a minimum number of cards exist for a topic.

        Checks existing card count and generates additional cards if below minimum.
        Used by ReviewQueue to ensure sufficient cards for a review session.

        Args:
            topic: Topic path to check/generate cards for
            minimum: Minimum cards required (defaults to CARD_MIN_FOR_TOPIC)

        Returns:
            Tuple of (total card count after generation, LLM usages for cost tracking)
        """
        if minimum is None:
            minimum = settings.CARD_MIN_FOR_TOPIC

        # Count existing cards for topic
        count_query = select(func.count(SpacedRepCard.id)).where(
            SpacedRepCard.tags.contains([topic])
        )
        result = await self.db.execute(count_query)
        existing_count = result.scalar() or 0

        if existing_count >= minimum:
            return existing_count, []

        # Generate more cards
        needed = minimum - existing_count
        cards, usages = await self.generate_for_topic(
            topic=topic,
            count=needed,
        )

        return existing_count + len(cards), usages


# Convenience function for pipeline integration
async def generate_cards_from_extraction(
    db: AsyncSession,
    extraction: ExtractionResult,
    content_id: str,
    tags: list[str],
) -> tuple[list[SpacedRepCard], list[LLMUsage]]:
    """
    Convenience function to generate cards from extraction results.

    Used by the processing pipeline after concept extraction.

    Args:
        db: Async database session
        extraction: Extraction result containing concepts from content processing
        content_id: UUID of the source content
        tags: Topic tags to apply to generated cards

    Returns:
        Tuple of (created SpacedRepCard instances, LLM usages for cost tracking)
    """
    generator = CardGeneratorService(db)
    return await generator.generate_from_concepts(extraction, content_id, tags)
