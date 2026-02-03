"""
Exercise Generator Service

LLM-powered exercise generation that creates adaptive exercises based on
content and mastery level. Implements learning science principles:

- Novice (mastery < 0.3): Worked examples, code completions
- Intermediate (mastery 0.3-0.7): Free recall, self-explain, implementations
- Advanced (mastery > 0.7): Applications, teach-back, refactoring

===============================================================================
EXERCISES vs SPACED REPETITION CARDS - Key Distinction
===============================================================================

EXERCISES (this module):
- Purpose: Active practice & deep skill application
- Format: Rich, structured problems with:
  * Detailed prompts requiring thought and composition
  * Worked examples (for novices) with follow-up problems
  * Code templates, test cases, buggy code (for programming topics)
  * Progressive hints and expected key points
- Scheduling: Mastery-based adaptive selection
  * Exercise TYPE changes based on skill level
  * Novices get worked examples, experts get teach-back exercises
- Evaluation: LLM-powered evaluation providing:
  * Score (0-100%)
  * Detailed feedback on strengths/weaknesses
  * Key points covered vs missed
  * Identified misconceptions with corrections
- Generation: Created on-demand during Practice Sessions
- UI: Appears in /practice (Practice Session page)
- Database: exercises table, exercise_attempts table
- Use case: "I want to PRACTICE and get feedback on my understanding"

SPACED REP CARDS (see card_generator.py):
- Purpose: Passive recall & long-term memory retention
- Format: Simple front/back flashcards
- Scheduling: FSRS algorithm (optimizes for memory retention)
- Evaluation: Self-rated (Again/Hard/Good/Easy)
- Generation: During content ingestion OR on-demand from Review Queue
- UI: Appears in /review (Review Queue page)
- Database: spaced_rep_cards table, practice_attempts table
- Use case: "I want to REMEMBER facts and definitions"

WHY BOTH?
Learning science shows optimal retention requires:
1. Initial understanding (Exercises - active engagement)
2. Long-term retention (Cards - spaced repetition)

The Practice Session combines both: cards for review + exercises for practice.

===============================================================================

Usage:
    from app.services.learning.exercise_generator import ExerciseGenerator

    generator = ExerciseGenerator(llm_client, db_session)

    exercise, usages = await generator.generate_exercise(
        request=ExerciseGenerateRequest(topic="ml/transformers/attention"),
        mastery_level=0.5,
    )
    # usages contains LLMUsage objects for cost tracking
"""

import json
import logging
import random
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Content
from app.db.models_learning import Exercise, ExerciseContent
from app.enums.learning import ExerciseType, ExerciseDifficulty
from app.enums.pipeline import PipelineOperation
from app.models.learning import (
    ExerciseGenerateRequest,
    ExerciseResponse,
)
from app.models.processing import ExtractionResult
from app.models.llm_usage import LLMUsage
from app.services.llm.client import LLMClient, build_messages, get_default_text_model
from app.services.tag_service import TagService
from app.config import settings

logger = logging.getLogger(__name__)


# ===========================================
# Prompt Templates for Exercise Generation
# ===========================================

# Context block inserted into prompts when concept details are available
CONCEPT_CONTEXT_BLOCK = """
=== Source Concept Details ===
Concept: {concept_name}
Definition: {concept_definition}
{concept_context}
{concept_why_it_matters}
{concept_examples}
==============================

Use these specific details from the source material to create a targeted exercise.
"""

# Context block for full content-based exercises
CONTENT_CONTEXT_BLOCK = """
=== Source Content ===
Title: {content_title}
Type: {content_type}

Summary:
{content_summary}

Key Topics: {key_topics}
==============================

Create an exercise that tests understanding of this specific content.
"""

EXERCISE_PROMPTS = {
    ExerciseType.FREE_RECALL: """Generate a free recall exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}).
{context_block}
Create an exercise that asks the learner to explain the concept from memory without looking at notes.

Return a JSON object with:
{{
    "prompt": "The exercise prompt asking to explain the concept",
    "hints": ["hint1", "hint2", "hint3"],
    "expected_key_points": ["point1", "point2", "point3", "point4"],
    "estimated_time_minutes": 5
}}

Make the prompt specific and actionable. The key points should cover the essential aspects a good explanation should include.""",
    ExerciseType.SELF_EXPLAIN: """Generate a self-explanation exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}).
{context_block}
Create an exercise that asks the learner to explain WHY or HOW something works, not just WHAT it is.

Return a JSON object with:
{{
    "prompt": "The exercise prompt asking why/how something works",
    "hints": ["hint1", "hint2", "hint3"],
    "expected_key_points": ["point1", "point2", "point3", "point4"],
    "estimated_time_minutes": 7
}}

Focus on causal understanding and mechanisms rather than definitions.""",
    ExerciseType.WORKED_EXAMPLE: """Generate a worked example exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}), so they are still learning the basics.
{context_block}
Create a step-by-step worked example followed by a similar practice problem.

Return a JSON object with:
{{
    "prompt": "Brief introduction to the concept",
    "worked_example": "Step 1: ...\\nStep 2: ...\\nStep 3: ...\\nResult: ...",
    "follow_up_problem": "Now try this similar problem: ...",
    "hints": ["hint for the follow-up problem"],
    "expected_key_points": ["key understanding points"],
    "estimated_time_minutes": 10
}}

The worked example should be clear and numbered. The follow-up problem should test the same concept.""",
    ExerciseType.APPLICATION: """Generate an application exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}), indicating solid understanding.
{context_block}
Create an exercise that requires applying the concept to a novel situation or real-world scenario.

Return a JSON object with:
{{
    "prompt": "A scenario requiring application of the concept",
    "hints": ["hint1", "hint2", "hint3"],
    "expected_key_points": ["point1", "point2", "point3", "point4"],
    "estimated_time_minutes": 10
}}

The scenario should be realistic and require creative problem-solving.""",
    ExerciseType.TEACH_BACK: """Generate a teach-back exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}), indicating advanced understanding.
{context_block}
Create an exercise asking the learner to explain the concept as if teaching it to someone else (Feynman technique).

Return a JSON object with:
{{
    "prompt": "Explain this concept as if teaching it to [specific audience]",
    "hints": ["hint1", "hint2", "hint3"],
    "expected_key_points": ["point1", "point2", "point3", "point4", "point5"],
    "estimated_time_minutes": 10
}}

Specify an appropriate audience (beginner, colleague, etc.) and expect comprehensive coverage.""",
    ExerciseType.CODE_IMPLEMENT: """Generate a code implementation exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}).
Target language: {language}
{context_block}
Create an exercise that requires writing code from scratch to solve a problem.

Return a JSON object with:
{{
    "prompt": "Problem statement and requirements",
    "language": "{language}",
    "starter_code": "# Starting template with function signature\\ndef solution():\\n    pass",
    "solution_code": "# Complete working solution\\ndef solution():\\n    # implementation",
    "test_cases": [
        {{"input": "example input", "expected": "expected output"}},
        {{"input": "another input", "expected": "another output"}}
    ],
    "hints": ["hint1", "hint2"],
    "expected_key_points": ["code understanding points"],
    "estimated_time_minutes": 15
}}

Include at least 3 test cases covering normal and edge cases.""",
    ExerciseType.CODE_DEBUG: """Generate a debugging exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}).
Target language: {language}
{context_block}
Create an exercise with buggy code that the learner must fix.

Return a JSON object with:
{{
    "prompt": "Find and fix the bug(s) in this code",
    "language": "{language}",
    "buggy_code": "# Code with intentional bugs\\ndef buggy_function():\\n    # buggy implementation",
    "solution_code": "# Corrected code\\ndef buggy_function():\\n    # fixed implementation",
    "test_cases": [
        {{"input": "test input", "expected": "expected output"}}
    ],
    "hints": ["hint about where the bug might be"],
    "expected_key_points": ["understanding of what the bug was and why"],
    "estimated_time_minutes": 10
}}

Include 1-3 realistic bugs that relate to the topic.""",
    ExerciseType.COMPARE_CONTRAST: """Generate a compare/contrast exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}).
{context_block}
Create an exercise that requires comparing and contrasting related concepts or approaches.

Return a JSON object with:
{{
    "prompt": "Compare and contrast [concept A] with [concept B]",
    "hints": ["hint1", "hint2"],
    "expected_key_points": ["similarity1", "similarity2", "difference1", "difference2", "when_to_use_each"],
    "estimated_time_minutes": 8
}}

Choose concepts that are commonly confused or have subtle differences.""",
    ExerciseType.CODE_COMPLETE: """Generate a code completion exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}), so they are still building foundational skills.
Target language: {language}
{context_block}
Create an exercise with partially written code that the learner must complete. This helps novices
learn patterns by filling in the blanks rather than writing everything from scratch.

Return a JSON object with:
{{
    "prompt": "Complete the missing parts of this code to make it work correctly",
    "language": "{language}",
    "starter_code": "# Code with strategic gaps marked with TODO or ___\\ndef function_name(params):\\n    # TODO: Initialize variables\\n    ___\\n    \\n    # Given: loop structure\\n    for item in items:\\n        # TODO: Process each item\\n        ___\\n    \\n    return result",
    "solution_code": "# Complete working solution\\ndef function_name(params):\\n    # Full implementation",
    "test_cases": [
        {{"input": "example input", "expected": "expected output"}},
        {{"input": "another input", "expected": "another output"}}
    ],
    "hints": ["hint about what the first blank should do", "hint about the second blank"],
    "expected_key_points": ["understanding of what each completed section does"],
    "estimated_time_minutes": 10
}}

Leave 2-4 strategic blanks that test understanding of the core concept. Provide enough context that learners can deduce the solution.""",
    ExerciseType.CODE_REFACTOR: """Generate a code refactoring exercise for the topic: {topic}

The learner's mastery level is {mastery_level:.0%} ({difficulty}), indicating advanced understanding.
Target language: {language}
{context_block}
Create an exercise with working but poorly written code that the learner must refactor to improve.
This tests deep understanding of best practices, design patterns, and code quality.

Return a JSON object with:
{{
    "prompt": "Refactor this working code to improve [specific aspect: readability/performance/maintainability/design]",
    "language": "{language}",
    "starter_code": "# Working but suboptimal code\\ndef messy_function():\\n    # Code that works but has clear improvement opportunities\\n    # e.g., code duplication, poor naming, inefficient algorithms, lack of abstraction",
    "solution_code": "# Refactored version demonstrating best practices\\ndef clean_function():\\n    # Improved implementation",
    "test_cases": [
        {{"input": "test input", "expected": "expected output"}}
    ],
    "hints": ["hint about what could be improved", "hint about a design pattern or technique to apply"],
    "expected_key_points": ["understanding of why the refactoring improves the code", "specific technique applied"],
    "estimated_time_minutes": 15
}}

The original code should work correctly but have obvious improvement opportunities related to the topic.
Focus on one main refactoring goal (performance, readability, design patterns, etc.).""",
}


# ===========================================
# Exercise Type Selection Constants
# ===========================================

# Exercise type selection by mastery level
# These are the canonical lists used by both ExerciseGenerator and MasteryService
NOVICE_EXERCISES: list[ExerciseType] = [
    ExerciseType.WORKED_EXAMPLE,
    ExerciseType.CODE_COMPLETE,
]
INTERMEDIATE_EXERCISES: list[ExerciseType] = [
    ExerciseType.FREE_RECALL,
    ExerciseType.SELF_EXPLAIN,
    ExerciseType.CODE_IMPLEMENT,
    ExerciseType.CODE_DEBUG,
]
ADVANCED_EXERCISES: list[ExerciseType] = [
    ExerciseType.APPLICATION,
    ExerciseType.TEACH_BACK,
    ExerciseType.COMPARE_CONTRAST,
    ExerciseType.CODE_REFACTOR,
]

# Code-based exercise types (vs text-based)
CODE_EXERCISE_TYPES: set[ExerciseType] = {
    ExerciseType.CODE_IMPLEMENT,
    ExerciseType.CODE_COMPLETE,
    ExerciseType.CODE_DEBUG,
    ExerciseType.CODE_REFACTOR,
    ExerciseType.CODE_EXPLAIN,
}


def get_suggested_exercise_types(
    mastery_score: float,
    is_code_topic: bool = False,
) -> list[ExerciseType]:
    """
    Get suggested exercise types based on mastery level.

    This is the canonical function for mapping mastery → exercise types.
    Used by both ExerciseGenerator and MasteryService.

    Args:
        mastery_score: Current mastery score (0-1)
        is_code_topic: Whether the topic is code-related

    Returns:
        List of appropriate exercise types for this mastery level
    """
    if mastery_score < settings.MASTERY_NOVICE_THRESHOLD:
        candidates = NOVICE_EXERCISES
    elif mastery_score < settings.MASTERY_INTERMEDIATE_THRESHOLD:
        candidates = INTERMEDIATE_EXERCISES
    else:
        candidates = ADVANCED_EXERCISES

    if is_code_topic:
        # Filter to code exercises for code topics
        code_candidates = [t for t in candidates if t in CODE_EXERCISE_TYPES]
        return code_candidates if code_candidates else candidates
    else:
        # Filter to text exercises for non-code topics
        text_candidates = [t for t in candidates if t not in CODE_EXERCISE_TYPES]
        return text_candidates if text_candidates else candidates


class ExerciseGenerator:
    """
    LLM-powered exercise generation service.

    Generates adaptive exercises based on topic and mastery level,
    implementing research-backed learning strategies.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        db: AsyncSession,
        model: str | None = None,
    ):
        """
        Initialize exercise generator.

        Args:
            llm_client: LLM client for generation
            db: Database session
            model: Model to use for generation (defaults to TEXT_MODEL from settings)
        """
        self.llm = llm_client
        self.db = db
        self.model = model or get_default_text_model()

    async def _get_existing_concepts_for_content(
        self, content_uuid: str
    ) -> set[str]:
        """
        Get the set of concept names that already have exercises for this content.

        Used for deduplication: skip generating exercises for concepts that already
        have exercises from this content.

        Args:
            content_uuid: UUID of the source content

        Returns:
            Set of concept names (lowercase) that have existing exercises
        """
        # Query via the junction table for exercises linked to this content
        result = await self.db.execute(
            select(Exercise.source_concept)
            .join(ExerciseContent, Exercise.id == ExerciseContent.exercise_id)
            .where(ExerciseContent.content_uuid == content_uuid)
            .where(Exercise.source_concept.isnot(None))
        )
        return {row[0].lower() for row in result.fetchall() if row[0]}

    async def _link_exercise_to_content(
        self, exercise_id: int, content_uuid: str
    ) -> None:
        """
        Create a link between an exercise and its source content.

        Creates an entry in the exercise_content junction table.

        Args:
            exercise_id: Database ID of the exercise
            content_uuid: UUID of the source content
        """
        # Look up the content's database PK
        result = await self.db.execute(
            select(Content.id).where(Content.content_uuid == content_uuid)
        )
        content_pk = result.scalar_one_or_none()

        if content_pk:
            link = ExerciseContent(
                exercise_id=exercise_id,
                content_id=content_pk,
                content_uuid=content_uuid,
            )
            self.db.add(link)
            # Note: caller should commit

    def _build_concept_context(self, concept) -> str:
        """
        Build a context block from a Concept object.

        This context is inserted into the LLM prompt to generate exercises
        that are specific to the source material, not generic.

        Args:
            concept: A Concept object from ExtractionResult

        Returns:
            Formatted context block string
        """
        # Format optional fields
        context_line = f"Context: {concept.context}" if concept.context else ""
        why_line = f"Why it matters: {concept.why_it_matters}" if concept.why_it_matters else ""

        # Format examples
        examples_text = ""
        if concept.examples:
            example_lines = []
            max_examples = settings.EXERCISE_CONTEXT_MAX_EXAMPLES
            for i, ex in enumerate(concept.examples[:max_examples], 1):
                if hasattr(ex, "content"):
                    example_lines.append(f"  {i}. {ex.content}")
                else:
                    example_lines.append(f"  {i}. {ex}")
            if example_lines:
                examples_text = "Examples:\n" + "\n".join(example_lines)

        # Format properties if available
        properties_text = ""
        if concept.properties:
            max_props = settings.EXERCISE_CONTEXT_MAX_PROPERTIES
            properties_text = "Properties: " + ", ".join(concept.properties[:max_props])

        return CONCEPT_CONTEXT_BLOCK.format(
            concept_name=concept.name,
            concept_definition=concept.definition,
            concept_context=context_line,
            concept_why_it_matters=why_line,
            concept_examples=examples_text + ("\n" + properties_text if properties_text else ""),
        )

    def _build_content_context(
        self,
        content_title: str,
        content_type: str,
        content_summary: str,
        key_topics: list[str] = None,
    ) -> str:
        """
        Build a context block from full content details.

        This context is inserted into the LLM prompt to generate exercises
        based on the full content, not just extracted concepts.

        Args:
            content_title: Title of the content
            content_type: Type of content (paper, article, book, etc.)
            content_summary: Summary of the content
            key_topics: List of key topics from the content

        Returns:
            Formatted context block string
        """
        topics_str = ", ".join(key_topics) if key_topics else "N/A"
        max_summary_len = settings.EXERCISE_CONTEXT_MAX_SUMMARY_LENGTH

        return CONTENT_CONTEXT_BLOCK.format(
            content_title=content_title,
            content_type=content_type,
            content_summary=content_summary[:max_summary_len] if content_summary else "N/A",
            key_topics=topics_str,
        )

    async def generate_exercise(
        self,
        request: ExerciseGenerateRequest,
        mastery_level: float | None = None,
        ensure_topic: bool = True,
        source_concept: str | None = None,
        context_block: str = "",
    ) -> tuple[ExerciseResponse, list[LLMUsage]]:
        """
        Generate an exercise for a topic.

        Args:
            request: Exercise generation request
            mastery_level: Current mastery level (0-1)
            ensure_topic: If True, ensure topic exists in database (default True).
                         Missing topics are auto-created to keep Tag table in sync.
            source_concept: Name of the concept this exercise was generated from.
                          Used for lineage tracking and deduplication.
            context_block: Optional context string to include in the prompt.
                          Use _build_concept_context() or _build_content_context()
                          to generate this from source material.

        Returns:
            Tuple of (generated exercise, LLM usages for cost tracking)
        """
        usages: list[LLMUsage] = []

        # Use default mastery level if not provided
        if mastery_level is None:
            mastery_level = settings.EXERCISE_DEFAULT_MASTERY_LEVEL

        # Ensure topic exists in database (auto-creates if missing)
        if ensure_topic:
            tag_service = TagService(self.db)
            await tag_service.ensure_topic_exists(request.topic)

        # Select difficulty based on mastery
        difficulty = self._select_difficulty(mastery_level)
        if request.difficulty:
            difficulty = request.difficulty

        # Select exercise type based on mastery and topic
        is_code_topic, classify_usage = await self._is_code_topic(
            request.topic, request.language
        )
        if classify_usage:
            usages.append(classify_usage)
        exercise_type = self._select_exercise_type(
            mastery_level,
            is_code_topic,
            request.exercise_type,
        )

        # Get prompt template
        template = EXERCISE_PROMPTS.get(exercise_type)
        if not template:
            # Fallback to free recall for unsupported types
            template = EXERCISE_PROMPTS[ExerciseType.FREE_RECALL]
            exercise_type = ExerciseType.FREE_RECALL

        # Format prompt (default language only for code exercises)
        is_code_exercise = exercise_type in CODE_EXERCISE_TYPES
        default_lang = settings.EXERCISE_DEFAULT_CODE_LANGUAGE
        language = request.language or (default_lang if is_code_exercise else None)
        prompt = template.format(
            topic=request.topic,
            mastery_level=mastery_level,
            difficulty=difficulty.value,
            language=language,
            context_block=context_block,
        )

        # Generate with LLM
        logger.info(f"Generating {exercise_type.value} exercise for {request.topic}")

        messages = build_messages(
            prompt=prompt,
            system_prompt="You are an expert educational content creator. Generate exercises in JSON format.",
        )

        response, usage = await self.llm.complete(
            operation=PipelineOperation.CONCEPT_EXTRACTION,
            messages=messages,
            model=self.model,
            temperature=settings.EXERCISE_LLM_TEMPERATURE,
            json_mode=True,
        )
        if usage:
            usages.append(usage)

        # Response is already parsed when json_mode=True
        exercise_data = response if isinstance(response, dict) else json.loads(response)

        # Create exercise record
        exercise = Exercise(
            exercise_uuid=str(uuid.uuid4()),
            exercise_type=exercise_type.value,
            topic=request.topic,
            difficulty=difficulty.value,
            prompt=exercise_data.get("prompt", f"Explain {request.topic}"),
            hints=exercise_data.get("hints", []),
            expected_key_points=exercise_data.get("expected_key_points", []),
            worked_example=exercise_data.get("worked_example"),
            follow_up_problem=exercise_data.get("follow_up_problem"),
            language=exercise_data.get("language"),
            starter_code=exercise_data.get("starter_code"),
            solution_code=exercise_data.get("solution_code"),
            test_cases=exercise_data.get("test_cases"),
            buggy_code=exercise_data.get("buggy_code"),
            source_content_ids=request.source_content_ids,
            source_concept=source_concept,  # Lineage tracking
            estimated_time_minutes=exercise_data.get(
                "estimated_time_minutes", settings.EXERCISE_DEFAULT_ESTIMATED_TIME
            ),
            tags=[request.topic],
        )

        self.db.add(exercise)
        await self.db.commit()
        await self.db.refresh(exercise)

        # Create junction table entries for content lineage
        if request.source_content_ids:
            for content_uuid in request.source_content_ids:
                await self._link_exercise_to_content(exercise.id, content_uuid)
            await self.db.commit()

        logger.info(
            f"Created exercise {exercise.id}: {exercise_type.value} for {request.topic}"
        )

        return self._to_response(exercise), usages

    def _select_difficulty(self, mastery_level: float) -> ExerciseDifficulty:
        """Select difficulty based on mastery level."""
        if mastery_level < settings.MASTERY_NOVICE_THRESHOLD:
            return ExerciseDifficulty.FOUNDATIONAL
        elif mastery_level < settings.MASTERY_INTERMEDIATE_THRESHOLD:
            return ExerciseDifficulty.INTERMEDIATE
        else:
            return ExerciseDifficulty.ADVANCED

    def _select_exercise_type(
        self,
        mastery_level: float,
        is_code: bool,
        requested_type: Optional[ExerciseType],
    ) -> ExerciseType:
        """Select appropriate exercise type based on mastery."""
        # Use requested type if provided
        if requested_type:
            return requested_type

        # Get candidates using the shared function
        candidates = get_suggested_exercise_types(mastery_level, is_code)

        # Pick one randomly from the candidates
        return random.choice(candidates) if candidates else ExerciseType.FREE_RECALL

    async def _is_code_topic(
        self, topic: str, language: Optional[str]
    ) -> tuple[bool, Optional[LLMUsage]]:
        """
        Determine if a topic is code-related using LLM classification.

        Uses the LLM to intelligently classify whether a topic would benefit
        from code-based exercises (implementation, debugging, refactoring) or
        text-based exercises (recall, explanation, comparison).

        Args:
            topic: The topic string to classify
            language: If a programming language is explicitly specified, returns True

        Returns:
            Tuple of (is_code_topic, LLM usage if LLM was called)
        """
        # If language is explicitly specified, it's definitely a code topic
        if language:
            return True, None

        prompt = f"""Classify whether this learning topic is primarily about programming/coding or is a conceptual/theoretical topic.

Topic: "{topic}"

A topic is CODE-RELATED if learning it would primarily involve:
- Writing, reading, or understanding code
- Implementing algorithms or data structures
- Using programming languages, frameworks, or libraries
- Debugging, testing, or refactoring code
- API design or system implementation

A topic is NOT code-related if it's primarily about:
- Conceptual understanding or theory
- Mathematical concepts (without implementation focus)
- Architecture or design principles (at a high level)
- General knowledge or domain expertise

Respond with ONLY a JSON object:
{{"is_code_topic": true}} or {{"is_code_topic": false}}"""

        try:
            messages = build_messages(
                prompt=prompt,
                system_prompt="You are a classifier. Respond only with the requested JSON.",
            )

            response, usage = await self.llm.complete(
                operation=PipelineOperation.CONCEPT_EXTRACTION,
                messages=messages,
                model=self.model,
                temperature=settings.EXERCISE_LLM_CLASSIFY_TEMPERATURE,
                json_mode=True,
            )

            result = response if isinstance(response, dict) else json.loads(response)
            return result.get("is_code_topic", False), usage

        except Exception as e:
            logger.warning(
                f"Failed to classify topic '{topic}': {e}, defaulting to False"
            )
            return False, None

    def _to_response(self, exercise: Exercise) -> ExerciseResponse:
        """Convert database model to response (hiding solution)."""
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
            estimated_time_minutes=(
                exercise.estimated_time_minutes
                or settings.EXERCISE_DEFAULT_ESTIMATED_TIME
            ),
            tags=exercise.tags or [],
        )

    async def generate_from_concepts(
        self,
        extraction: ExtractionResult,
        content_id: str,
        tags: list[str],
        max_exercises: int | None = None,
        skip_existing: bool = True,
    ) -> tuple[list[ExerciseResponse], list[LLMUsage]]:
        """
        Generate exercises from extracted concepts during content processing.

        Focuses on CORE concepts to generate practice exercises that reinforce
        the main ideas from the processed content. Uses FOUNDATIONAL difficulty
        since this is initial learning, not review.

        Deduplication: By default, skips concepts that already have exercises
        for this content. This prevents duplicate exercise generation on re-processing.

        Args:
            extraction: Extraction result containing concepts
            content_id: UUID of the source content
            tags: Tags to apply to generated exercises
            max_exercises: Maximum exercises to generate (default: EXERCISE_MAX_FROM_CONCEPTS)
            skip_existing: If True (default), skip concepts that already have exercises

        Returns:
            Tuple of (generated exercises, LLM usages for cost tracking)
        """
        exercises: list[ExerciseResponse] = []
        usages: list[LLMUsage] = []

        # Use default from settings if not provided
        if max_exercises is None:
            max_exercises = settings.EXERCISE_MAX_FROM_CONCEPTS

        if not extraction.concepts:
            logger.debug("No concepts found, skipping exercise generation")
            return exercises, usages

        # Get existing concepts to skip (deduplication)
        existing_concepts: set[str] = set()
        if skip_existing:
            existing_concepts = await self._get_existing_concepts_for_content(content_id)
            if existing_concepts:
                logger.info(
                    f"Skipping {len(existing_concepts)} concepts that already have exercises"
                )

        # Focus on CORE concepts only
        core_concepts = [c for c in extraction.concepts if c.importance == "CORE"]
        if not core_concepts:
            # Fallback to first few concepts if no CORE concepts
            core_concepts = extraction.concepts[:max_exercises]
        else:
            core_concepts = core_concepts[:max_exercises]

        # Filter out existing concepts
        if skip_existing:
            core_concepts = [
                c for c in core_concepts if c.name.lower() not in existing_concepts
            ]

        if not core_concepts:
            logger.info("All core concepts already have exercises for this content")
            return exercises, usages

        logger.info(f"Generating exercises for {len(core_concepts)} core concepts")

        for concept in core_concepts:
            try:
                # Build topic from concept name (use first tag as domain if available)
                topic = (
                    tags[0] + "/" + concept.name.lower().replace(" ", "-")
                    if tags
                    else concept.name.lower().replace(" ", "-")
                )

                # Build rich context from concept details
                context_block = self._build_concept_context(concept)

                request = ExerciseGenerateRequest(
                    topic=topic,
                    exercise_type=None,  # Auto-select based on mastery (will be novice)
                    difficulty=ExerciseDifficulty.FOUNDATIONAL,  # Start easy
                    source_content_ids=[content_id],
                )

                # Generate exercise (novice mastery = gets worked examples/free recall)
                exercise, exercise_usages = await self.generate_exercise(
                    request=request,
                    mastery_level=settings.EXERCISE_NOVICE_MASTERY_LEVEL,
                    ensure_topic=True,
                    source_concept=concept.name,  # Lineage tracking
                    context_block=context_block,  # Pass concept details to LLM
                )
                usages.extend(exercise_usages)

                # Update tags to include content tags
                if exercise:
                    exercises.append(exercise)
                    logger.debug(f"Generated exercise for concept: {concept.name}")

            except Exception as e:
                logger.warning(
                    f"Failed to generate exercise for concept '{concept.name}': {e}"
                )
                continue

        logger.info(f"Generated {len(exercises)} exercises from extraction")
        return exercises, usages

    async def generate_from_content(
        self,
        content_uuid: str,
        content_title: str,
        content_type: str,
        content_summary: str,
        key_topics: list[str] = None,
        tags: list[str] = None,
        max_exercises: int | None = None,
        skip_existing: bool = True,
    ) -> tuple[list[ExerciseResponse], list[LLMUsage]]:
        """
        Generate exercises from full content (not just concepts).

        Creates exercises that test comprehension of the entire content,
        not just individual extracted concepts. Good for:
        - Application exercises based on the content's main ideas
        - Compare/contrast exercises with related topics
        - Teach-back exercises to explain the content's thesis

        Deduplication: By default, skips if exercises already exist for this
        content with source_concept='__CONTENT__' marker.

        Args:
            content_uuid: UUID of the source content
            content_title: Title of the content
            content_type: Type of content (paper, article, book, etc.)
            content_summary: Summary or abstract of the content
            key_topics: List of key topics from content analysis
            tags: Tags to apply to generated exercises
            max_exercises: Maximum exercises to generate (default: EXERCISE_MAX_FROM_CONTENT)
            skip_existing: If True (default), skip if content already has exercises

        Returns:
            Tuple of (generated exercises, LLM usages for cost tracking)
        """
        exercises: list[ExerciseResponse] = []
        usages: list[LLMUsage] = []

        # Use defaults from settings if not provided
        if max_exercises is None:
            max_exercises = settings.EXERCISE_MAX_FROM_CONTENT
        content_marker = settings.EXERCISE_CONTENT_SOURCE_MARKER

        if not content_summary:
            logger.debug("No content summary, skipping content-based exercise generation")
            return exercises, usages

        # Check for existing content-based exercises (marked with content marker)
        if skip_existing:
            existing_concepts = await self._get_existing_concepts_for_content(content_uuid)
            if content_marker.lower() in existing_concepts:
                logger.info("Content already has content-based exercises, skipping")
                return exercises, usages

        # Build context from content
        context_block = self._build_content_context(
            content_title=content_title,
            content_type=content_type,
            content_summary=content_summary,
            key_topics=key_topics,
        )

        # Build topic from content title
        max_topic_len = settings.EXERCISE_TOPIC_NAME_MAX_LENGTH
        topic = (
            tags[0] + "/" + content_title.lower().replace(" ", "-")[:max_topic_len]
            if tags
            else content_title.lower().replace(" ", "-")[:max_topic_len]
        )

        # Generate different exercise types based on content
        exercise_types_to_try = [
            ExerciseType.APPLICATION,  # Apply content concepts
            ExerciseType.TEACH_BACK,   # Explain content as if teaching
        ]

        for exercise_type in exercise_types_to_try[:max_exercises]:
            try:
                request = ExerciseGenerateRequest(
                    topic=topic,
                    exercise_type=exercise_type,
                    difficulty=ExerciseDifficulty.INTERMEDIATE,
                    source_content_ids=[content_uuid],
                )

                exercise, exercise_usages = await self.generate_exercise(
                    request=request,
                    mastery_level=settings.EXERCISE_INTERMEDIATE_MASTERY_LEVEL,
                    ensure_topic=True,
                    source_concept=content_marker,  # Special marker for content-based
                    context_block=context_block,
                )
                usages.extend(exercise_usages)

                if exercise:
                    exercises.append(exercise)
                    logger.debug(
                        f"Generated {exercise_type.value} exercise from content: {content_title}"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to generate {exercise_type.value} exercise from content: {e}"
                )
                continue

        logger.info(f"Generated {len(exercises)} exercises from content summary")
        return exercises, usages


# ===========================================
# Convenience function for pipeline integration
# ===========================================


async def generate_exercises_from_extraction(
    db: AsyncSession,
    llm_client: LLMClient,
    extraction: ExtractionResult,
    content_id: str,
    tags: list[str],
    max_exercises: int | None = None,
) -> tuple[list[ExerciseResponse], list[LLMUsage]]:
    """
    Convenience function to generate exercises from extraction results.

    Used by the processing pipeline after concept extraction to create
    practice exercises for the main concepts.

    Args:
        db: Database session
        llm_client: LLM client for generation
        extraction: Extraction result with concepts
        content_id: UUID of the source content
        tags: Tags to apply to exercises
        max_exercises: Maximum exercises (default: EXERCISE_MAX_FROM_CONCEPTS setting)

    Returns:
        Tuple of (generated exercises, LLM usages for cost tracking)
    """
    generator = ExerciseGenerator(llm_client, db)
    return await generator.generate_from_concepts(
        extraction=extraction,
        content_id=content_id,
        tags=tags,
        max_exercises=max_exercises,
    )


async def generate_exercises_from_content(
    db: AsyncSession,
    llm_client: LLMClient,
    content_uuid: str,
    content_title: str,
    content_type: str,
    content_summary: str,
    key_topics: list[str] = None,
    tags: list[str] = None,
    max_exercises: int | None = None,
) -> tuple[list[ExerciseResponse], list[LLMUsage]]:
    """
    Convenience function to generate exercises from full content.

    Used by the processing pipeline to create exercises based on the
    content's summary and main ideas, complementing concept-based exercises.

    Args:
        db: Database session
        llm_client: LLM client for generation
        content_uuid: UUID of the source content
        content_title: Title of the content
        content_type: Type of content (paper, article, etc.)
        content_summary: Summary or abstract of the content
        key_topics: List of key topics from content analysis
        tags: Tags to apply to exercises
        max_exercises: Maximum exercises (default: EXERCISE_MAX_FROM_CONTENT setting)

    Returns:
        Tuple of (generated exercises, LLM usages for cost tracking)
    """
    generator = ExerciseGenerator(llm_client, db)
    return await generator.generate_from_content(
        content_uuid=content_uuid,
        content_title=content_title,
        content_type=content_type,
        content_summary=content_summary,
        key_topics=key_topics,
        tags=tags,
        max_exercises=max_exercises,
    )
