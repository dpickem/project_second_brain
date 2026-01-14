"""
Processing API Router

Exposes LLM processing functionality via REST API endpoints.

Endpoints:
- POST /api/processing/trigger - Queue content for processing
- GET /api/processing/status/{content_id} - Get processing status
- GET /api/processing/result/{content_id} - Get processing result
- GET /api/processing/pending - Get all items pending processing
- POST /api/processing/reprocess - Reprocess specific stages

Usage:
    # Trigger processing
    POST /api/processing/trigger
    {"content_id": "uuid", "config": {"generate_summaries": true, ...}}

    # Check status
    GET /api/processing/status/uuid

    # Get result
    GET /api/processing/result/uuid

    # Get pending items
    GET /api/processing/pending?limit=50&include_failed=true
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.models.base import StrictRequest
from sqlalchemy.orm import selectinload

from app.db.base import async_session_maker
from app.db.models import Content
from app.db.models_processing import ProcessingRun
from app.enums.content import ProcessingStatus
from app.enums.processing import ProcessingStage, ProcessingRunStatus
from app.models.content import UnifiedContent
from app.models.processing import (
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Connection,
    FollowupTask,
    MasteryQuestion,
)
from app.services.processing.pipeline import process_content, PipelineConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/processing", tags=["processing"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ProcessingConfigRequest(StrictRequest):
    """
    Configuration options for processing request.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    generate_summaries: bool = True
    extract_concepts: bool = True
    assign_tags: bool = True
    generate_cards: bool = True  # Generate spaced repetition cards
    generate_exercises: bool = True  # Generate practice exercises
    discover_connections: bool = True
    generate_followups: bool = True
    generate_questions: bool = True
    create_obsidian_note: bool = True
    create_neo4j_nodes: bool = True
    validate_output: bool = True


class TriggerProcessingRequest(StrictRequest):
    """
    Request body for triggering processing.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    content_id: str = Field(..., description="UUID of content to process")
    config: Optional[ProcessingConfigRequest] = None


class TriggerProcessingResponse(BaseModel):
    """Response for processing trigger."""

    status: str
    content_id: str
    message: str


class ProcessingStatusResponse(BaseModel):
    """Response for processing status check."""

    status: str  # not_processed, pending, processing, completed, failed
    content_id: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    error_message: Optional[str] = None


class ProcessingResultResponse(BaseModel):
    """Response with full processing result."""

    content_id: str
    analysis: ContentAnalysis
    summaries: dict[str, str]  # level (brief/standard/detailed) -> summary text
    extraction: ExtractionResult
    tags: TagAssignment
    connections: list[Connection]
    followups: list[FollowupTask]
    questions: list[MasteryQuestion]
    obsidian_path: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    processing_time_seconds: float
    estimated_cost_usd: float


class PendingContentItem(BaseModel):
    """A content item pending processing."""

    content_id: str
    title: str
    content_type: str
    status: str
    source_url: Optional[str] = None
    created_at: str


class PendingContentResponse(BaseModel):
    """Response with list of pending content items."""

    total: int
    items: list[PendingContentItem]


# =============================================================================
# Background Task Functions
# =============================================================================


async def _run_processing(content_id: str, config_dict: Optional[dict] = None):
    """
    Background task to run the LLM processing pipeline on content.

    This function is executed asynchronously via FastAPI's BackgroundTasks.
    It orchestrates the full processing workflow:

    1. Load content from database and convert to UnifiedContent
    2. Update content status to PROCESSING
    3. Run the processing pipeline (analysis, summarization, extraction, etc.)
    4. Save ProcessingRun record with all results
    5. Update content status to PROCESSED (or FAILED on error)

    Args:
        content_id: UUID of the content to process (as string)
        config_dict: Optional configuration overrides for the pipeline.
            Keys correspond to PipelineConfig fields (e.g., generate_summaries,
            extract_concepts, assign_tags, discover_connections, etc.)

    Side Effects:
        - Updates Content.status in database (PROCESSING → PROCESSED/FAILED)
        - Creates ProcessingRun record with results
        - Updates Content.summary and Content.vault_path on success
        - Logs progress and errors

    Note:
        This function catches all exceptions to ensure content status is
        updated to FAILED rather than leaving it stuck in PROCESSING.
    """
    logger.info(f"Starting background processing for content {content_id}")

    try:
        # Load content from database
        async with async_session_maker() as session:
            result = await session.execute(
                select(Content).where(Content.content_uuid == content_id)
            )
            db_content = result.scalar_one_or_none()

            if not db_content:
                logger.error(f"Content {content_id} not found")
                return

            # Convert to UnifiedContent
            content = UnifiedContent.from_db_content(db_content)

            # Update status to processing
            db_content.status = ProcessingStatus.PROCESSING
            await session.commit()

        # Build config
        # Explicitly enable cards/exercises to avoid relying on defaults.
        # (Defaults may change over time; we always want these generated during processing.)
        config = PipelineConfig(generate_cards=True, generate_exercises=True)
        if config_dict:
            for key, value in config_dict.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Run pipeline with database session for card generation
        async with async_session_maker() as db_session:
            processing_result = await process_content(content, config, db=db_session)

        # Save result to database
        async with async_session_maker() as session:
            # Get content record again
            result = await session.execute(
                select(Content).where(Content.content_uuid == content_id)
            )
            db_content = result.scalar_one_or_none()

            if db_content:
                # Create processing run record
                run = ProcessingRun.from_processing_result(
                    content_id=db_content.id,
                    status=ProcessingRunStatus.COMPLETED.value,
                    processing_result=processing_result,
                )
                session.add(run)

                # Update content status and metadata
                db_content.status = ProcessingStatus.PROCESSED
                db_content.processed_at = datetime.utcnow()
                db_content.summary = processing_result.summaries.get("standard", "")
                if processing_result.obsidian_note_path:
                    db_content.vault_path = processing_result.obsidian_note_path

                await session.commit()

        logger.info(f"Processing completed for content {content_id}")

    except Exception as e:
        logger.error(f"Processing failed for content {content_id}: {e}")

        # Update status to failed
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Content).where(Content.content_uuid == content_id)
                )
                db_content = result.scalar_one_or_none()
                if db_content:
                    db_content.status = ProcessingStatus.FAILED

                    # Create failed processing run record
                    run = ProcessingRun.from_processing_result(
                        content_id=db_content.id,
                        status=ProcessingRunStatus.FAILED.value,
                        error_message=str(e),
                    )
                    session.add(run)
                    await session.commit()
        except Exception as save_error:
            logger.error(f"Failed to save error status: {save_error}")


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/trigger", response_model=TriggerProcessingResponse)
async def trigger_processing(
    request: TriggerProcessingRequest, background_tasks: BackgroundTasks
):
    """
    Trigger LLM processing for a content item.

    Processing runs asynchronously in the background. Use the status
    endpoint to check progress.

    Args:
        request: Processing request with content_id and optional config

    Returns:
        TriggerProcessingResponse with queued status
    """
    # Verify content exists
    async with async_session_maker() as session:
        result = await session.execute(
            select(Content).where(Content.content_uuid == request.content_id)
        )
        db_content = result.scalar_one_or_none()

        if not db_content:
            raise HTTPException(404, f"Content {request.content_id} not found")

        # Check if already processing
        if db_content.status == ProcessingStatus.PROCESSING:
            return TriggerProcessingResponse(
                status="already_processing",
                content_id=request.content_id,
                message="Content is already being processed",
            )

    # Queue background task
    config_dict = request.config.model_dump() if request.config else None
    background_tasks.add_task(_run_processing, request.content_id, config_dict)

    return TriggerProcessingResponse(
        status="queued",
        content_id=request.content_id,
        message="Processing queued successfully",
    )


@router.get("/status/{content_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(content_id: str):
    """
    Get processing status for a content item.

    Returns the current status and metadata about the most recent
    processing run.

    Args:
        content_id: UUID of the content

    Returns:
        ProcessingStatusResponse with status and timing info
    """
    async with async_session_maker() as session:
        # Get content
        result = await session.execute(
            select(Content).where(Content.content_uuid == content_id)
        )
        db_content = result.scalar_one_or_none()

        if not db_content:
            raise HTTPException(404, f"Content {content_id} not found")

        # Get most recent processing run
        run_result = await session.execute(
            select(ProcessingRun)
            .where(ProcessingRun.content_id == db_content.id)
            .order_by(ProcessingRun.started_at.desc())
            .limit(1)
        )
        run = run_result.scalar_one_or_none()

        if not run:
            return ProcessingStatusResponse(
                status="not_processed", content_id=content_id
            )

        return ProcessingStatusResponse(
            status=run.status,
            content_id=content_id,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            processing_time_seconds=run.processing_time_seconds,
            estimated_cost_usd=run.estimated_cost_usd,
            error_message=run.error_message,
        )


@router.get("/result/{content_id}", response_model=ProcessingResultResponse)
async def get_processing_result(content_id: str):
    """
    Get full processing result for a content item.

    Returns the complete processing result including analysis,
    summaries, concepts, tags, connections, and more.

    Args:
        content_id: UUID of the content

    Returns:
        ProcessingResultResponse with all processing outputs

    Raises:
        HTTPException 404: If content or processing result not found
    """
    async with async_session_maker() as session:
        # Get content
        result = await session.execute(
            select(Content).where(Content.content_uuid == content_id)
        )
        db_content = result.scalar_one_or_none()

        if not db_content:
            raise HTTPException(404, f"Content {content_id} not found")

        # Get most recent completed processing run with relationships
        run_result = await session.execute(
            select(ProcessingRun)
            .where(ProcessingRun.content_id == db_content.id)
            .where(ProcessingRun.status == ProcessingRunStatus.COMPLETED.value)
            .order_by(ProcessingRun.started_at.desc())
            .options(
                selectinload(ProcessingRun.connections),
                selectinload(ProcessingRun.followups),
                selectinload(ProcessingRun.questions),
            )
            .limit(1)
        )
        run = run_result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                404, f"No completed processing found for content {content_id}"
            )

        # Convert SQLAlchemy records to Pydantic models
        connections = [
            Connection(
                id=str(c.id),
                target_id=str(c.target_content_id),
                target_title=c.target_title or "",
                relationship_type=c.relationship_type,
                strength=c.strength,
                explanation=c.explanation or "",
                verified_by_user=c.verified_by_user,
            )
            for c in run.connections
        ]

        followups = [
            FollowupTask(
                id=str(f.id),
                task=f.task,
                task_type=f.task_type,
                priority=f.priority,
                estimated_time=f.estimated_time,
                completed=f.completed,
                completed_at=f.completed_at,
                created_at=f.created_at,
            )
            for f in run.followups
        ]

        questions = [
            MasteryQuestion(
                id=str(q.id),
                question=q.question,
                question_type=q.question_type,
                difficulty=q.difficulty,
                hints=q.hints or [],
                key_points=q.key_points or [],
                next_review_at=q.next_review_at,
                review_count=q.review_count,
                ease_factor=q.ease_factor,
                created_at=q.created_at,
            )
            for q in run.questions
        ]

        # Build response from stored JSON and loaded relationships
        return ProcessingResultResponse(
            content_id=content_id,
            analysis=run.analysis or {},
            summaries=run.summaries or {},
            extraction=run.extraction or {},
            tags=run.tags or {},
            connections=connections,
            followups=followups,
            questions=questions,
            obsidian_path=run.obsidian_note_path,
            neo4j_node_id=run.neo4j_node_id,
            processing_time_seconds=run.processing_time_seconds or 0,
            estimated_cost_usd=run.estimated_cost_usd or 0,
        )


@router.get("/pending", response_model=PendingContentResponse)
async def get_pending_content(limit: int = 100, include_failed: bool = False):
    """
    Get all content items pending processing.

    Returns content that has been ingested but not yet processed,
    optionally including items that failed processing.

    Args:
        limit: Maximum number of items to return (default 100)
        include_failed: Whether to include failed items (default False)

    Returns:
        PendingContentResponse with list of pending items
    """
    async with async_session_maker() as session:
        # Build status filter
        # Note: ProcessingStatus only has PENDING, PROCESSING, PROCESSED, FAILED
        statuses = [ProcessingStatus.PENDING]
        if include_failed:
            statuses.append(ProcessingStatus.FAILED)

        # Query pending content
        result = await session.execute(
            select(Content)
            .where(Content.status.in_(statuses))
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        pending_items = result.scalars().all()

        # Build response
        items = [
            PendingContentItem(
                content_id=item.content_uuid,
                title=item.title or "Untitled",
                content_type=item.content_type,
                status=(
                    item.status.value
                    if hasattr(item.status, "value")
                    else str(item.status)
                ),
                source_url=item.source_url,
                created_at=item.created_at.isoformat() if item.created_at else "",
            )
            for item in pending_items
        ]

        return PendingContentResponse(total=len(items), items=items)


@router.post("/reprocess")
async def reprocess_content(
    content_id: str,
    background_tasks: BackgroundTasks,
    stages: Optional[list[ProcessingStage]] = None,
):
    """
    Reprocess specific stages for existing content.

    Useful when prompts are updated or specific stages need to be re-run.

    Args:
        content_id: UUID of content to reprocess
        stages: List of stages to run (e.g., [ProcessingStage.SUMMARIZATION])

    Returns:
        Status indicating reprocessing was queued
    """
    # Build config with only specified stages
    stage_values = [s.value for s in stages] if stages else []
    config = ProcessingConfigRequest(
        generate_summaries=ProcessingStage.SUMMARIZATION.value in stage_values
        or not stages,
        extract_concepts=ProcessingStage.EXTRACTION.value in stage_values or not stages,
        assign_tags=ProcessingStage.TAGGING.value in stage_values or not stages,
        discover_connections=ProcessingStage.CONNECTIONS.value in stage_values
        or not stages,
        generate_followups=ProcessingStage.FOLLOWUPS.value in stage_values
        or not stages,
        generate_questions=ProcessingStage.QUESTIONS.value in stage_values
        or not stages,
    )

    request = TriggerProcessingRequest(content_id=content_id, config=config)
    return await trigger_processing(request, background_tasks)
