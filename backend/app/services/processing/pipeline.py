"""
Processing Pipeline Orchestrator

Coordinates all processing stages, manages dependencies between stages,
handles errors gracefully, and tracks processing time and costs.

Pipeline stages:
1. Content Analysis - Determine type, domain, complexity
2. Summarization - Generate brief, standard, and detailed summaries
3. Concept Extraction - Extract key concepts, findings, entities
4. Tagging - Assign tags from controlled vocabulary
5. Connection Discovery - Find relationships to existing knowledge
6. Follow-up Generation - Create actionable learning tasks
7. Question Generation - Create mastery questions

Cost Tracking:
    Each LLM call returns an LLMUsage object. These are collected throughout
    the pipeline and persisted to the database via CostTracker at the end.
    This enables per-operation cost attribution and historical analysis.

Usage:
    from app.services.processing import process_content, PipelineConfig

    result = await process_content(content, config=PipelineConfig())
    print(f"Processed in {result.processing_time_seconds}s")
    print(f"Estimated cost: ${result.estimated_cost_usd:.4f}")
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import UnifiedContent
from app.models.processing import (
    ProcessingResult,
    ExtractionResult,
    TagAssignment,
)
from app.enums.processing import ProcessingStage, SummaryLevel
from app.models.llm_usage import LLMUsage
from app.services.llm.client import get_llm_client, LLMClient
from app.services.knowledge_graph.client import get_neo4j_client, Neo4jClient
from app.services.processing.stages.content_analysis import analyze_content
from app.services.processing.stages.summarization import generate_all_summaries
from app.services.processing.stages.extraction import extract_concepts
from app.services.processing.stages.tagging import assign_tags
from app.services.processing.stages.connections import discover_connections
from app.services.processing.stages.followups import generate_followups
from app.services.processing.stages.questions import generate_mastery_questions
from app.services.processing.validation import validate_processing_result
from app.services.processing.output.obsidian_generator import (
    generate_obsidian_note,
    generate_exercise_notes_for_content,
    get_best_title,
)
from app.services.processing.output.neo4j_generator import create_knowledge_nodes
from app.services.cost_tracking import CostTracker
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Stage Dependencies
# =============================================================================
# Maps each pipeline stage to its required dependencies.
# ANALYSIS has no dependencies and always runs first.
# When a stage is enabled, all its dependencies are automatically enabled.
STAGE_DEPENDENCIES: dict[ProcessingStage, list[ProcessingStage]] = {
    ProcessingStage.ANALYSIS: [],
    ProcessingStage.SUMMARIZATION: [],
    ProcessingStage.EXTRACTION: [],
    ProcessingStage.TAGGING: [ProcessingStage.SUMMARIZATION],
    ProcessingStage.CONNECTIONS: [
        ProcessingStage.SUMMARIZATION,
        ProcessingStage.EXTRACTION,
    ],
    ProcessingStage.FOLLOWUPS: [
        ProcessingStage.SUMMARIZATION,
        ProcessingStage.EXTRACTION,
    ],
    ProcessingStage.QUESTIONS: [
        ProcessingStage.SUMMARIZATION,
        ProcessingStage.EXTRACTION,
    ],
}

# Maps PipelineConfig attribute names to ProcessingStage enum values
CONFIG_FIELD_TO_STAGE: dict[str, ProcessingStage] = {
    "generate_summaries": ProcessingStage.SUMMARIZATION,
    "extract_concepts": ProcessingStage.EXTRACTION,
    "assign_tags": ProcessingStage.TAGGING,
    "discover_connections": ProcessingStage.CONNECTIONS,
    "generate_followups": ProcessingStage.FOLLOWUPS,
    "generate_questions": ProcessingStage.QUESTIONS,
}

# Reverse mapping: ProcessingStage -> config field name
STAGE_TO_CONFIG_FIELD: dict[ProcessingStage, str] = {
    v: k for k, v in CONFIG_FIELD_TO_STAGE.items()
}


@dataclass
class PipelineConfig:
    """
    Configuration for pipeline execution.

    Allows selective enabling/disabling of stages and customization
    of processing parameters.

    Stage Dependencies (defined in STAGE_DEPENDENCIES):
        - TAGGING: requires SUMMARIZATION
        - CONNECTIONS: requires SUMMARIZATION, EXTRACTION
        - FOLLOWUPS: requires SUMMARIZATION, EXTRACTION
        - QUESTIONS: requires SUMMARIZATION, EXTRACTION

    When a stage is enabled, its dependencies are automatically enabled.
    A log message is emitted when dependencies are auto-enabled.

    Exercise Generation Options:
        When generate_exercises=True, you can control which types are generated:
        - generate_exercises_from_concepts: Creates exercises based on extracted concepts
          (targeted, tests specific terminology and definitions)
        - generate_exercises_from_content: Creates exercises based on full content summary
          (broader, tests comprehension and application of main ideas)
        Both default to True. Set either to False to disable that type.
    """

    # Stage toggles
    generate_summaries: bool = True
    extract_concepts: bool = True
    assign_tags: bool = True
    generate_cards: bool = False  # Generate spaced repetition cards (disabled by default, use on-demand generation)
    generate_exercises: bool = False  # Generate practice exercises (disabled by default, use on-demand generation)
    generate_exercises_from_concepts: bool = True  # When generate_exercises=True, generate from extracted concepts
    generate_exercises_from_content: bool = True  # When generate_exercises=True, generate from content summary
    discover_connections: bool = True
    generate_followups: bool = True
    generate_questions: bool = True

    # Output toggles
    create_obsidian_note: bool = True
    create_neo4j_nodes: bool = True

    # Validation
    validate_output: bool = True

    # Connection discovery parameters
    max_connection_candidates: int = field(
        default_factory=lambda: processing_settings.MAX_CONNECTION_CANDIDATES
    )

    def __post_init__(self):
        """Auto-enable dependencies for enabled stages."""
        auto_enabled = []

        # Check each stage and enable its dependencies
        for config_field, stage in CONFIG_FIELD_TO_STAGE.items():
            if not getattr(self, config_field):
                continue

            for dependency in STAGE_DEPENDENCIES[stage]:
                dep_field = STAGE_TO_CONFIG_FIELD.get(dependency)
                if dep_field and not getattr(self, dep_field):
                    setattr(self, dep_field, True)
                    auto_enabled.append(f"{dep_field} (required by {config_field})")

        if auto_enabled:
            logger.info(f"Auto-enabled pipeline stages: {', '.join(auto_enabled)}")


async def process_content(
    content: UnifiedContent,
    config: PipelineConfig = None,
    llm_client: LLMClient = None,
    neo4j_client: Neo4jClient = None,
    db: AsyncSession = None,
) -> ProcessingResult:
    """
    Run the full LLM processing pipeline on ingested content.

    This is the main entry point for processing content through the
    LLM pipeline. It orchestrates all stages and handles errors.

    Args:
        content: UnifiedContent from ingestion
        config: Pipeline configuration (uses defaults if not provided)
        llm_client: LLM client (creates new one if not provided)
        neo4j_client: Neo4j client (creates new one if not provided)

    Returns:
        ProcessingResult with all stage outputs

    Raises:
        Exception: If critical stages fail
    """
    config = config or PipelineConfig()
    start_time = time.time()

    # Collect LLMUsage objects from all stages for cost tracking
    all_usages: list[LLMUsage] = []

    # Initialize clients
    if llm_client is None:
        llm_client = get_llm_client()

    if neo4j_client is None and config.discover_connections:
        neo4j_client = await get_neo4j_client()

    logger.info(f"Starting processing pipeline for: {content.title}")

    # =========================================================================
    # Stage 1: Content Analysis (always runs)
    # =========================================================================
    logger.debug("Stage 1: Content Analysis")
    analysis, analysis_usages = await analyze_content(
        content=content, llm_client=llm_client
    )
    all_usages.extend(analysis_usages)
    logger.info(
        f"Analysis: type={analysis.content_type}, "
        f"domain={analysis.domain}, "
        f"complexity={analysis.complexity}"
    )

    # =========================================================================
    # Stage 2: Generate Summaries
    # =========================================================================
    summaries = {}
    if config.generate_summaries:
        logger.debug("Stage 2: Summarization")
        try:
            summaries, summary_usages = await generate_all_summaries(
                content=content, analysis=analysis, llm_client=llm_client
            )
            all_usages.extend(summary_usages)
            logger.info(f"Generated {len(summaries)} summaries")
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            summaries = {"standard": f"[Summarization failed: {e}]"}

    # =========================================================================
    # Stage 3: Extract Concepts
    # =========================================================================
    extraction = ExtractionResult()
    if config.extract_concepts:
        logger.debug("Stage 3: Concept Extraction")
        try:
            extraction, extraction_usages = await extract_concepts(
                content=content, analysis=analysis, llm_client=llm_client
            )
            all_usages.extend(extraction_usages)
            logger.info(
                f"Extracted {len(extraction.concepts)} concepts, "
                f"{len(extraction.key_findings)} findings"
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")

    # =========================================================================
    # Stage 4: Assign Tags
    # =========================================================================
    tags = TagAssignment()
    if config.assign_tags:
        logger.debug("Stage 4: Tagging")
        try:
            standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
            tags, tagging_usages = await assign_tags(
                content_title=content.title,
                analysis=analysis,
                summary=standard_summary,
                llm_client=llm_client,
                content_id=content.id,
            )
            all_usages.extend(tagging_usages)
            logger.info(
                f"Assigned {len(tags.domain_tags)} domain tags, "
                f"{len(tags.meta_tags)} meta tags"
            )
        except Exception as e:
            logger.error(f"Tagging failed: {e}")

    # =========================================================================
    # Stage 4b: Generate Spaced Repetition Cards
    # =========================================================================
    generated_cards = []
    if config.generate_cards and extraction.concepts and db is not None:
        logger.debug("Stage 4b: Card Generation")
        try:
            # Deferred import to avoid circular dependency
            from app.services.learning.card_generator import (
                generate_cards_from_extraction,
            )

            # Combine domain and meta tags for cards
            card_tags = tags.domain_tags + tags.meta_tags if tags else []
            generated_cards, card_usages = await generate_cards_from_extraction(
                db=db,
                extraction=extraction,
                content_id=content.id,  # content_id = UUID throughout the app
                tags=card_tags,
            )
            all_usages.extend(card_usages)
            logger.info(f"Generated {len(generated_cards)} spaced repetition cards")
        except Exception as e:
            logger.error(f"Card generation failed: {e}")
    elif config.generate_cards and db is None:
        logger.warning("Card generation skipped: no database session provided")

    # =========================================================================
    # Stage 4c: Exercise Generation (from concepts + from content)
    # =========================================================================
    generated_exercises = []
    if config.generate_exercises and db is not None:
        logger.debug("Stage 4c: Exercise Generation")
        try:
            # Deferred import to avoid circular dependency
            from app.services.learning.exercise_generator import (
                generate_exercises_from_extraction,
                generate_exercises_from_content,
            )

            # Combine domain and meta tags for exercises
            exercise_tags = tags.domain_tags + tags.meta_tags if tags else []

            # 4c.1: Generate exercises from extracted concepts
            if config.generate_exercises_from_concepts and extraction.concepts:
                concept_exercises, concept_usages = (
                    await generate_exercises_from_extraction(
                        db=db,
                        llm_client=llm_client,
                        extraction=extraction,
                        content_id=content.id,
                        tags=exercise_tags,
                    )
                )
                generated_exercises.extend(concept_exercises)
                all_usages.extend(concept_usages)
                logger.info(
                    f"Generated {len(concept_exercises)} exercises from concepts"
                )

            # 4c.2: Generate exercises from full content summary
            if config.generate_exercises_from_content:
                standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
                if standard_summary:
                    content_exercises, content_usages = (
                        await generate_exercises_from_content(
                            db=db,
                            llm_client=llm_client,
                            content_uuid=content.id,
                            content_title=content.title,
                            content_type=analysis.content_type if analysis else "article",
                            content_summary=standard_summary,
                            key_topics=analysis.key_topics if analysis else [],
                            tags=exercise_tags,
                        )
                    )
                    generated_exercises.extend(content_exercises)
                    all_usages.extend(content_usages)
                    logger.info(
                        f"Generated {len(content_exercises)} exercises from content"
                    )

            logger.info(
                f"Total: {len(generated_exercises)} practice exercises generated"
            )
        except Exception as e:
            logger.error(f"Exercise generation failed: {e}")
    elif config.generate_exercises and db is None:
        logger.warning("Exercise generation skipped: no database session provided")

    # =========================================================================
    # Stage 5: Discover Connections
    # =========================================================================
    connections = []
    if config.discover_connections and neo4j_client:
        logger.debug("Stage 5: Connection Discovery")
        try:
            standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
            connections, connection_usages = await discover_connections(
                content=content,
                summary=standard_summary,
                extraction=extraction,
                analysis=analysis,
                llm_client=llm_client,
                neo4j_client=neo4j_client,
                top_k=config.max_connection_candidates,
            )
            all_usages.extend(connection_usages)
            logger.info(f"Discovered {len(connections)} connections")
        except Exception as e:
            logger.error(f"Connection discovery failed: {e}")

    # =========================================================================
    # Stage 6: Generate Follow-ups
    # =========================================================================
    followups = []
    if config.generate_followups:
        logger.debug("Stage 6: Follow-up Generation")
        try:
            standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
            followups, followup_usages = await generate_followups(
                content=content,
                analysis=analysis,
                summary=standard_summary,
                extraction=extraction,
                llm_client=llm_client,
            )
            all_usages.extend(followup_usages)
            logger.info(f"Generated {len(followups)} follow-up tasks")
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")

    # =========================================================================
    # Stage 7: Generate Mastery Questions
    # =========================================================================
    questions = []
    if config.generate_questions:
        logger.debug("Stage 7: Question Generation")
        try:
            detailed_summary = summaries.get(SummaryLevel.DETAILED.value, "")
            questions, question_usages = await generate_mastery_questions(
                content=content,
                analysis=analysis,
                summary=detailed_summary,
                extraction=extraction,
                llm_client=llm_client,
            )
            all_usages.extend(question_usages)
            logger.info(f"Generated {len(questions)} mastery questions")
        except Exception as e:
            logger.error(f"Question generation failed: {e}")

    # =========================================================================
    # Persist LLM Usage to Database
    # =========================================================================
    if all_usages:
        try:
            await CostTracker.log_usages_batch(all_usages)
            logger.debug(f"Persisted {len(all_usages)} LLM usage records")
        except Exception as e:
            logger.error(f"Failed to persist LLM usage records: {e}")

    # =========================================================================
    # Build Result
    # =========================================================================
    processing_time = time.time() - start_time
    estimated_cost = sum(u.cost_usd or 0 for u in all_usages)

    result = ProcessingResult(
        content_id=content.id,
        analysis=analysis,
        summaries=summaries,
        extraction=extraction,
        tags=tags,
        connections=connections,
        followups=followups,
        mastery_questions=questions,
        processing_time_seconds=processing_time,
        estimated_cost_usd=estimated_cost,
    )

    # =========================================================================
    # Validate Output
    # =========================================================================
    if config.validate_output:
        issues = validate_processing_result(result)
        if issues:
            logger.warning(f"Validation issues: {issues}")

    # =========================================================================
    # Generate Outputs (Obsidian, Neo4j)
    # =========================================================================
    if config.create_obsidian_note and processing_settings.GENERATE_OBSIDIAN_NOTES:
        try:
            result.obsidian_note_path = await generate_obsidian_note(content, result)
            logger.info(f"Generated Obsidian note: {result.obsidian_note_path}")
        except Exception as e:
            logger.error(f"Obsidian note generation failed: {e}")

        # Generate Obsidian notes for exercises (if any were created)
        if generated_exercises:
            try:
                # Use the best title (extracted from processing) rather than raw content.title
                # which may be a UUID if the original file didn't have a proper title
                best_title = get_best_title(content, result)
                exercise_notes = await generate_exercise_notes_for_content(
                    exercises=generated_exercises,
                    source_content_titles=[best_title],
                    source_content_ids=[content.id],
                )
                logger.info(f"Generated {len(exercise_notes)} exercise notes")
            except Exception as e:
                logger.error(f"Exercise note generation failed: {e}")

    if (
        config.create_neo4j_nodes
        and processing_settings.GENERATE_NEO4J_NODES
        and neo4j_client
    ):
        try:
            result.neo4j_node_id = await create_knowledge_nodes(
                content, result, llm_client, neo4j_client
            )
            logger.info(f"Created Neo4j node: {result.neo4j_node_id}")
        except Exception as e:
            logger.error(f"Neo4j node creation failed: {e}")

    logger.info(
        f"Processing complete: {content.title} in {processing_time:.2f}s, "
        f"cost: ${estimated_cost:.4f}"
    )

    return result
