"""
Celery Task Definitions

Defines async tasks for content processing, including:
- ingest_content: Main task for ingestion (extracting raw text/annotations) via PipelineRegistry
- ingest_book: Specialized ingestion task for batch book OCR processing
- sync_raindrop: Periodic sync of Raindrop.io bookmarks
- sync_github: Periodic sync of GitHub starred repos

Pipeline Routing:
    Tasks use PipelineContentType to route content to the appropriate pipeline:
    - "pdf" → PDFProcessor
    - "book" → BookOCRPipeline (batch via ingest_book task)
    - "voice_memo" → VoiceTranscriber
    - "code" → GitHubImporter
    - "article" → WebArticlePipeline

    Note: RaindropSync is NOT used via registry. It's a batch sync pipeline
    used directly via sync_raindrop task → RaindropSync.sync_collection().

Retry Strategy:
    Uses tenacity for retry logic with exponential backoff:
    - content_retry: 3 attempts, 1-4 min backoff (for content processing)
    - sync_retry: 3 attempts, 5-20 min backoff (for external API syncs)

Queue Routing:
    Task-to-queue assignment is configured centrally in queue.py via `task_routes`,
    NOT in the task decorators. The routing maps task names to queues:
    - ingest_content        → ingestion_default queue
    - ingest_content_high   → ingestion_high queue (voice memos, user waiting)
    - ingest_content_low    → ingestion_low queue (batch imports, syncs)
    - ingest_book           → ingestion_default queue (60 min timeout)
    - process_content       → llm_processing queue (LLM pipeline)
    - sync_raindrop         → ingestion_low queue
    - sync_github           → ingestion_low queue

    To run workers for specific queues:
        celery -A app.services.queue worker -Q ingestion_high,ingestion_default,ingestion_low,llm_processing -l info

Usage:
    from app.services.tasks import ingest_content, ingest_book
    from app.pipelines import PipelineContentType

    # Queue PDF for processing
    ingest_content.delay(
        content_id="uuid",
        content_type=PipelineContentType.PDF.value,
        source_path="/path/to/file.pdf",
    )

    # Queue voice memo (high priority)
    ingest_content_high.delay(
        content_id="uuid",
        content_type=PipelineContentType.VOICE_MEMO.value,
        source_path="/path/to/memo.mp3",
    )

    # Queue book for batch OCR
    ingest_book.delay(
        content_id="uuid",
        image_paths=["/path/to/page1.jpg", "/path/to/page2.jpg"],
        book_metadata={"title": "My Book"},
    )

    # Check task status
    result = ingest_content.AsyncResult(task_id)
    print(result.status)
"""

# =============================================================================
# Standard library imports
# =============================================================================
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Third-party imports
# =============================================================================
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# =============================================================================
# Internal imports
# =============================================================================
from app.config import settings
from app.pipelines import (
    BookOCRPipeline,
    GitHubImporter,
    PipelineContentType,
    PipelineInput,
    RaindropSync,
    get_registry,
)
from app.db.base import task_session_maker
from app.db.models import Content, ContentStatus
from app.enums import ProcessingRunStatus
from app.enums.content import ProcessingStatus
from app.models.content import UnifiedContent
from app.services.obsidian.sync import VaultSyncService
from app.services.queue import celery_app
from app.services.storage import (
    load_content,
    save_content,
    update_content,
    update_status,
)
from app.services.processing.pipeline import (
    process_content as run_llm_pipeline,
    PipelineConfig,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Retry configurations using tenacity
# =============================================================================

# For content processing: 3 attempts, 1-4 min exponential backoff
# Don't retry validation errors (file size limits, missing files, invalid content types)
content_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=60, min=60, max=240),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    retry=retry_if_not_exception_type((ValueError, FileNotFoundError)),
    reraise=True,
)

# For external API syncs: 3 attempts, 5-20 min exponential backoff
sync_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=300, min=300, max=1200),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

# For LLM processing: 2 attempts, 2-5 min exponential backoff
# Fewer retries than ingestion since LLM processing is expensive.
llm_processing_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=120, min=120, max=300),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# =============================================================================
# Content processing tasks
# =============================================================================


async def _run_llm_processing_impl(
    content_id: str,
    config: PipelineConfig,
) -> dict[str, Any]:
    """
    Internal async implementation of LLM processing.

    Runs the full LLM processing pipeline to generate:
    - Summaries (brief, standard, detailed)
    - Concepts and key findings
    - Spaced repetition cards (if config.generate_cards=True)
    - Practice exercises (if config.generate_exercises=True)
    - Tags, connections, follow-ups, mastery questions
    - Obsidian notes and Neo4j nodes

    Args:
        content_id: UUID of the content to process
        config: Pipeline configuration controlling which stages to run

    Returns:
        Dictionary with processing results including card/exercise counts
    """
    from sqlalchemy import select
    from app.db.models_processing import ProcessingRun
    from app.enums.processing import ProcessingRunStatus as PRunStatus

    logger.info(f"Starting LLM processing for content {content_id}")

    async with task_session_maker() as session:
        # Load content from database
        result = await session.execute(
            select(Content).where(Content.content_uuid == content_id)
        )
        db_content = result.scalar_one_or_none()

        if not db_content:
            logger.error(f"Content {content_id} not found for LLM processing")
            return {"status": "error", "error": "Content not found"}

        # Convert to UnifiedContent for processing pipeline
        unified_content = UnifiedContent.from_db_content(db_content)

        # Update status to processing
        db_content.status = ProcessingStatus.PROCESSING
        await session.commit()

    # Run LLM processing pipeline with a new database session for card/exercise generation
    try:
        async with task_session_maker() as db_session:
            processing_result = await run_llm_pipeline(
                unified_content, config, db=db_session
            )

        # Save processing results
        async with task_session_maker() as session:
            result = await session.execute(
                select(Content).where(Content.content_uuid == content_id)
            )
            db_content = result.scalar_one_or_none()

            if db_content:
                # Create processing run record
                run = ProcessingRun.from_processing_result(
                    content_id=db_content.id,
                    status=PRunStatus.COMPLETED.value,
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

        logger.info(
            f"LLM processing completed for {content_id}: "
            f"{processing_result.processing_time_seconds:.2f}s, "
            f"${processing_result.estimated_cost_usd:.4f}"
        )

        return {
            "status": ProcessingRunStatus.COMPLETED.value,
            "content_id": content_id,
            "processing_time_seconds": processing_result.processing_time_seconds,
            "estimated_cost_usd": processing_result.estimated_cost_usd,
            "concepts_extracted": len(processing_result.extraction.concepts),
            "cards_generated": len(getattr(processing_result, "cards", [])),
            "exercises_generated": len(getattr(processing_result, "exercises", [])),
        }

    except Exception as e:
        logger.error(f"LLM processing failed for {content_id}: {e}")

        # Update status to failed
        async with task_session_maker() as session:
            result = await session.execute(
                select(Content).where(Content.content_uuid == content_id)
            )
            db_content = result.scalar_one_or_none()
            if db_content:
                db_content.status = ProcessingStatus.FAILED

                # Create failed processing run record
                run = ProcessingRun.from_processing_result(
                    content_id=db_content.id,
                    status=PRunStatus.FAILED.value,
                    error_message=str(e),
                )
                session.add(run)
                await session.commit()

        return {
            "status": ProcessingRunStatus.FAILED.value,
            "content_id": content_id,
            "error": str(e),
        }


@llm_processing_retry
def _process_content_with_retry(
    content_id: str,
    config: PipelineConfig,
) -> dict[str, Any]:
    """Run LLM processing (pipeline) with tenacity retry logic."""
    return asyncio.run(_run_llm_processing_impl(content_id, config))


@celery_app.task(name="app.services.tasks.process_content")
def process_content(
    content_id: str,
    config_dict: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Celery task to run the LLM processing pipeline on already-ingested content.

    This task runs the full LLM processing pipeline to generate:
    - Summaries (brief, standard, detailed)
    - Concepts and key findings
    - Spaced repetition cards (if config.generate_cards=True)
    - Practice exercises (if config.generate_exercises=True)
    - Tags, connections, follow-ups, mastery questions
    - Obsidian notes and Neo4j nodes

    This task is automatically queued after content ingestion when
    auto_process=True (the default).

    Retry behavior: 2 attempts with exponential backoff (2-5 min).

    Args:
        content_id: UUID of the content to process
        config_dict: Optional dictionary of PipelineConfig fields to override defaults.
            Common fields:
            - generate_cards (bool): Generate spaced repetition cards
            - generate_exercises (bool): Generate practice exercises
            - generate_summaries (bool): Generate summaries
            - extract_concepts (bool): Extract concepts
            - create_obsidian_note (bool): Create Obsidian note
            - create_neo4j_nodes (bool): Create Neo4j nodes
            If None, uses PipelineConfig defaults (all stages enabled).

    Returns:
        Dictionary with processing results
    """
    # Build PipelineConfig from dict (Celery requires serializable args)
    config = PipelineConfig(**(config_dict or {}))

    try:
        return _process_content_with_retry(content_id, config)
    except RetryError as e:
        logger.error(f"LLM processing failed for {content_id} after all retries: {e}")
        # Status already updated to FAILED in _run_llm_processing_impl
        raise


@content_retry
def _ingest_content_impl(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    Internal implementation of content ingestion with tenacity retry.

    Uses PipelineRegistry to ingest content (extract raw text/annotations/metadata),
    then optionally queues the LLM processing pipeline to generate cards, exercises,
    summaries, and other learning materials.

    Args:
        content_id: UUID of the content to process
        content_type: PipelineContentType value (e.g., "pdf", "book", "voice_memo")
        source_path: File path for file-based content
        source_url: URL for web-based content
        source_text: Text for direct text input
        auto_process: If True, automatically run LLM processing after ingestion
                     to generate cards, exercises, summaries, etc. (default: True)

    Raises:
        Exception: Re-raised after retry attempts exhausted.
    """
    logger.info(f"Ingesting content {content_id} (type: {content_type})")

    # Parse content type
    try:
        pipeline_content_type = PipelineContentType(content_type)
    except ValueError:
        logger.error(f"Unknown content type: {content_type}")
        raise ValueError(f"Unknown content type: {content_type}")

    # Build PipelineInput
    pipeline_input = PipelineInput(
        content_type=pipeline_content_type,
        path=Path(source_path) if source_path else None,
        url=source_url,
        text=source_text,
        content_id=content_id,
    )

    async def run_pipeline_and_update():
        # Get the pre-configured singleton registry
        registry = get_registry()

        # Route to appropriate pipeline
        result = await registry.process(pipeline_input)

        if result is None:
            return None

        # Update database with results
        # Use task_context=True because we're in a Celery task with a new event loop
        await update_content(
            content_id,
            title=result.title,
            full_text=result.full_text,
            annotations=result.annotations,
            metadata=result.metadata,
            task_context=True,
        )

        return result

    # Run the async pipeline and DB update in a single event loop
    result = asyncio.run(run_pipeline_and_update())

    if result is None:
        logger.warning(f"No pipeline found for content type: {content_type}")
        return {
            "status": ProcessingRunStatus.FAILED.value,
            "content_id": content_id,
            "error": f"No pipeline found for content type: {content_type}",
        }

    logger.info(f"Content {content_id} ingestion completed")

    # Auto-queue LLM processing if enabled
    if auto_process:
        logger.info(f"Queuing {content_id} for LLM processing...")
        # Ingested content (PDFs, articles, etc.) should generate cards and exercises by default
        process_content.delay(
            content_id,
            config_dict={"generate_cards": True, "generate_exercises": True},
        )

        return {
            "status": ProcessingRunStatus.INGESTED.value,
            "content_id": content_id,
            "content_type": content_type,
            "title": result.title,
            "ingested_at": datetime.utcnow().isoformat(),
            "processing_queued": True,
        }

    return {
        "status": ProcessingRunStatus.INGESTED.value,
        "content_id": content_id,
        "content_type": content_type,
        "title": result.title,
        "ingested_at": datetime.utcnow().isoformat(),
        "processing_queued": False,
    }


@celery_app.task(name="app.services.tasks.ingest_content")
def ingest_content(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    Ingest content through the appropriate ingestion pipeline (raw extraction).

    IMPORTANT: Content must already exist in the database before calling this task.
    This task calls update_content() to update fields after pipeline processing,
    which assumes the Content record already exists. If content doesn't exist,
    use save_content() first (see sync_raindrop and sync_github for examples).

    Uses PipelineRegistry to route content based on content_type:
    - "pdf" → PDFProcessor
    - "book" → BookOCRPipeline
    - "voice_memo" → VoiceTranscriber
    - "code" → GitHubImporter
    - "article" → WebArticlePipeline

    After ingestion, if auto_process=True (default), the content is automatically
    processed through the LLM pipeline to generate:
    - Summaries, concepts, and tags
    - Spaced repetition cards for review
    - Practice exercises
    - Obsidian notes and Neo4j nodes

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 1-4 min).

    Args:
        content_id: UUID of the content to process (must already exist in DB)
        content_type: PipelineContentType value for routing (e.g., "pdf", "book")
        source_path: File path for file-based content
        source_url: URL for web-based content (GitHub, articles)
        source_text: Text for direct text input
        auto_process: If True, automatically run LLM processing after ingestion
                     to generate cards, exercises, summaries, etc. (default: True)

    Returns:
        Dictionary with processing results
    """
    try:
        return _ingest_content_impl(
            content_id, content_type, source_path, source_url, source_text, auto_process
        )
    except RetryError as e:
        logger.error(f"Processing failed for {content_id} after all retries: {e}")
        asyncio.run(
            update_status(
                content_id, ContentStatus.FAILED.value, str(e), task_context=True
            )
        )
        raise


@celery_app.task(name="app.services.tasks.ingest_content_high")
def ingest_content_high(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    High-priority content processing (e.g., voice memos).

    Same as ingest_content but routed to ingestion_high queue.
    Retry behavior inherited from _process_content_impl via tenacity.

    Note: Content must already exist in DB before calling. See ingest_content docstring.
    """
    return ingest_content(
        content_id, content_type, source_path, source_url, source_text, auto_process
    )


@celery_app.task(name="app.services.tasks.ingest_content_low")
def ingest_content_low(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    Low-priority content processing (e.g., batch imports).

    Same as ingest_content but routed to ingestion_low queue.
    Retry behavior inherited from _process_content_impl via tenacity.

    Note: Content must already exist in DB before calling. See ingest_content docstring.
    """
    return ingest_content(
        content_id, content_type, source_path, source_url, source_text, auto_process
    )


@content_retry
def _process_book_impl(
    content_id: str,
    image_paths: list[str],
    book_metadata: dict[str, Any],
    max_concurrency: int = 5,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    Internal implementation of book OCR processing with tenacity retry.

    Uses BookOCRPipeline to process multiple page images into a single
    unified book content item. Pages are processed in parallel for speed.

    Note: This task uses BookOCRPipeline directly rather than PipelineRegistry
    because it requires special handling for multi-file batch processing.
    The PipelineInput pattern is still used for the pipeline call.
    """
    logger.info(
        f"Processing book {content_id} with {len(image_paths)} pages "
        f"(concurrency: {max_concurrency})"
    )

    async def run_pipeline_and_update():
        pipeline = BookOCRPipeline(
            track_costs=True,
            max_concurrency=max_concurrency,
        )
        paths = [Path(p) for p in image_paths]

        # Use direct path interface (process_paths) for batch processing
        # Note: For single-file processing, use PipelineInput instead
        result = await pipeline.process_paths(
            image_paths=paths,
            book_metadata=book_metadata,
            content_id=content_id,
        )

        # Update database with results
        # Use task_context=True because we're in a Celery task with a new event loop
        await update_content(
            content_id,
            title=result.title,
            authors=result.authors,
            full_text=result.full_text,
            annotations=result.annotations,
            metadata=result.metadata,
            task_context=True,
        )

        return result

    # Run the async pipeline and DB update in a single event loop
    result = asyncio.run(run_pipeline_and_update())

    logger.info(
        f"Book {content_id} ingestion complete: "
        f"{result.metadata.get('total_pages_processed', 0)} pages, "
        f"${result.metadata.get('llm_cost_usd', 0):.4f} LLM cost"
    )

    # Auto-queue LLM processing if enabled
    if auto_process:
        logger.info(f"Queuing book {content_id} for LLM processing...")
        # Book content should generate cards and exercises by default
        process_content.delay(
            content_id,
            config_dict={"generate_cards": True, "generate_exercises": True},
        )

        return {
            "status": ProcessingRunStatus.INGESTED.value,
            "content_id": content_id,
            "title": result.title,
            "pages_processed": result.metadata.get("total_pages_processed", 0),
            "llm_cost_usd": result.metadata.get("llm_cost_usd", 0),
            "ingested_at": datetime.utcnow().isoformat(),
            "processing_queued": True,
        }

    return {
        "status": ProcessingRunStatus.INGESTED.value,
        "content_id": content_id,
        "title": result.title,
        "pages_processed": result.metadata.get("total_pages_processed", 0),
        "llm_cost_usd": result.metadata.get("llm_cost_usd", 0),
        "ingested_at": datetime.utcnow().isoformat(),
        "processing_queued": False,
    }


@celery_app.task(name="app.services.tasks.ingest_book")
def ingest_book(
    content_id: str,
    image_paths: list[str],
    book_metadata: Optional[dict[str, Any]] = None,
    max_concurrency: int = 5,
    auto_process: bool = True,
) -> dict[str, Any]:
    """
    Process batch of book page images through BookOCRPipeline.

    This task uses PipelineContentType.BOOK but bypasses the registry
    for direct batch processing of multiple images.

    This task:
    1. Loads all page images
    2. Runs OCR on each page in PARALLEL (limited by max_concurrency)
    3. Aggregates into a single book content item
    4. Updates the database with extracted content
    5. Tracks LLM costs
    6. Optionally runs LLM processing to generate cards, exercises, etc.

    Time limit: 60 minutes (configured in queue.py)

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 1-4 min).

    Args:
        content_id: UUID of the book content item
        image_paths: List of paths to page image files
        book_metadata: Optional dict with title, authors, isbn
        max_concurrency: Max parallel OCR calls (default 5, increase for faster processing)
        auto_process: If True, automatically run LLM processing after ingestion
                     to generate cards, exercises, summaries, etc. (default: True)

    Returns:
        Dictionary with processing results
    """
    book_metadata = book_metadata or {}

    try:
        return _process_book_impl(
            content_id, image_paths, book_metadata, max_concurrency, auto_process
        )
    except RetryError as e:
        logger.error(f"Book processing failed for {content_id} after all retries: {e}")
        # Update status to failed
        asyncio.run(
            update_status(
                content_id, ContentStatus.FAILED.value, str(e), task_context=True
            )
        )
        raise


# =============================================================================
# External sync tasks
# =============================================================================


@sync_retry
def _sync_raindrop_impl(since_dt: datetime, limit: Optional[int] = None) -> list[Any]:
    """
    Internal implementation of Raindrop sync with tenacity retry.

    Args:
        since_dt: Datetime to sync items from.
        limit: Maximum number of items to sync (default: no limit).

    Returns:
        List of synced items.
    """
    if not settings.RAINDROP_ACCESS_TOKEN:
        raise ValueError("RAINDROP_ACCESS_TOKEN not set")

    async def run_sync():
        sync = RaindropSync(access_token=settings.RAINDROP_ACCESS_TOKEN)
        try:
            items = await sync.sync_collection(since=since_dt, limit=limit)
            return items
        finally:
            await sync.close()

    return asyncio.run(run_sync())


@celery_app.task(name="app.services.tasks.sync_raindrop")
def sync_raindrop(
    since: Optional[str] = None, limit: Optional[int] = None
) -> dict[str, Any]:
    """
    Sync bookmarks from Raindrop.io.

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 5-20 min).

    Args:
        since: ISO format datetime string. If provided, only sync items
               created after this date. Defaults to last 24 hours.
        limit: Maximum number of items to sync (default: no limit).

    Returns:
        Dictionary with sync results
    """
    logger.info(f"Starting Raindrop sync since {since}, limit={limit}")

    # Parse since date
    if since:
        since_dt = datetime.fromisoformat(since)
    else:
        since_dt = datetime.utcnow() - timedelta(hours=24)

    # Check for API token early (skip without retry)
    if not settings.RAINDROP_ACCESS_TOKEN:
        logger.warning("RAINDROP_ACCESS_TOKEN not set, skipping sync")
        return {"status": ProcessingRunStatus.SKIPPED.value, "reason": "No API token"}

    try:
        items = _sync_raindrop_impl(since_dt, limit=limit)
    except RetryError as e:
        logger.error(f"Raindrop sync failed after all retries: {e}")
        raise

    # Save each item to database and queue for processing
    async def save_and_queue():
        saved_count = 0
        for item in items:
            try:
                # Save content to database first
                await save_content(item)
                saved_count += 1
                # Then queue for processing
                ingest_content_low.delay(
                    content_id=item.id,
                    content_type=PipelineContentType.ARTICLE.value,
                    source_url=item.source_url,
                )
            except Exception as e:
                logger.error(f"Failed to save/queue content {item.id}: {e}")
        return saved_count

    saved_count = asyncio.run(save_and_queue())
    logger.info(f"Raindrop sync complete: {saved_count} items saved and queued")

    return {
        "status": ProcessingRunStatus.COMPLETED.value,
        "items_synced": saved_count,
        "synced_at": datetime.utcnow().isoformat(),
    }


@sync_retry
def _sync_github_impl(limit: int) -> list[Any]:
    """
    Internal implementation of GitHub sync with tenacity retry.

    Args:
        limit: Maximum number of repos to sync.

    Returns:
        List of synced items.
    """
    if not settings.GITHUB_ACCESS_TOKEN:
        raise ValueError("GITHUB_ACCESS_TOKEN not set")

    async def run_sync():
        importer = GitHubImporter(access_token=settings.GITHUB_ACCESS_TOKEN)
        try:
            items = await importer.import_starred_repos(limit=limit)
            return items
        finally:
            await importer.close()

    return asyncio.run(run_sync())


@celery_app.task(name="app.services.tasks.sync_github")
def sync_github(limit: int = 50) -> dict[str, Any]:
    """
    Sync starred repositories from GitHub.

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 5-20 min).

    Args:
        limit: Maximum number of repos to sync

    Returns:
        Dictionary with sync results
    """
    logger.info(f"Starting GitHub sync with limit {limit}")

    # Check for API token early (skip without retry)
    if not settings.GITHUB_ACCESS_TOKEN:
        logger.warning("GITHUB_ACCESS_TOKEN not set, skipping sync")
        return {"status": ProcessingRunStatus.SKIPPED.value, "reason": "No API token"}

    try:
        items = _sync_github_impl(limit)
    except RetryError as e:
        logger.error(f"GitHub sync failed after all retries: {e}")
        raise

    # Save each item to database and queue for processing
    async def save_and_queue():
        saved_count = 0
        for item in items:
            try:
                # Save content to database first
                await save_content(item)
                saved_count += 1
                # Then queue for processing
                ingest_content_low.delay(
                    content_id=item.id,
                    content_type=PipelineContentType.CODE.value,
                    source_url=item.source_url,
                )
            except Exception as e:
                logger.error(f"Failed to save/queue repo {item.id}: {e}")
        return saved_count

    saved_count = asyncio.run(save_and_queue())
    logger.info(f"GitHub sync complete: {saved_count} repos saved and queued")

    return {
        "status": ProcessingRunStatus.COMPLETED.value,
        "repos_synced": saved_count,
        "synced_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Vault sync tasks
# =============================================================================


@celery_app.task(name="app.services.tasks.sync_vault_note")
def sync_vault_note(note_path: str) -> dict[str, Any]:
    """
    Sync a single vault note to Neo4j knowledge graph.

    Called by VaultWatcher when a note is created or modified in Obsidian.
    Uses VaultSyncService to:
    1. Parse frontmatter and extract metadata
    2. Extract wikilinks and tags from content
    3. Create/update Note node in Neo4j
    4. Sync LINKS_TO relationships

    Retry behavior: 3 attempts with exponential backoff (handled by Celery).
    This is appropriate because Neo4j might be temporarily unavailable.

    Args:
        note_path: Absolute path to the markdown note file

    Returns:
        Dictionary with sync results (node_id, links_synced, tags)
    """
    logger.info(f"Syncing vault note: {note_path}")

    async def run_sync():
        sync_service = VaultSyncService()
        result = await sync_service.sync_note(Path(note_path))
        return result

    try:
        result = asyncio.run(run_sync())
        logger.info(f"Vault note synced: {note_path}")
        return result
    except Exception as e:
        logger.error(f"Failed to sync vault note {note_path}: {e}")
        return {
            "path": note_path,
            "error": str(e),
            "status": ProcessingRunStatus.FAILED.value,
        }


# =============================================================================
# Maintenance tasks
# =============================================================================


@celery_app.task(name="app.services.tasks.cleanup_old_tasks")
def cleanup_old_tasks() -> dict[str, str]:
    """
    Periodic task to clean up old task results and failed items.

    Scheduling:
        This task is triggered by APScheduler in app/services/scheduler.py.
        The scheduler calls cleanup_old_tasks.delay() daily at 3 AM UTC,
        which queues this task to Redis for execution by a Celery worker.

        See scheduler.py:trigger_cleanup() and setup_scheduled_jobs().
    """
    logger.info("Running task cleanup")

    # TODO: Implement cleanup logic
    # - Remove old task results from Redis
    # - Retry or mark as failed any stuck processing items

    return {
        "status": ProcessingRunStatus.COMPLETED.value,
        "cleaned_at": datetime.utcnow().isoformat(),
    }
