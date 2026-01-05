"""
Celery Task Definitions

Defines async tasks for content processing, including:
- process_content: Main task for processing ingested content through PipelineRegistry
- process_book: Specialized task for batch book OCR processing
- sync_raindrop: Periodic sync of Raindrop.io bookmarks
- sync_github: Periodic sync of GitHub starred repos

Pipeline Routing:
    Tasks use PipelineContentType to route content to the appropriate pipeline:
    - "pdf" → PDFProcessor
    - "book" → BookOCRPipeline (batch via process_book task)
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
    - process_content       → default queue
    - process_content_high  → high_priority queue (voice memos, user waiting)
    - process_content_low   → low_priority queue (batch imports, syncs)
    - process_book          → default queue (60 min timeout)
    - sync_raindrop         → low_priority queue
    - sync_github           → low_priority queue

    To run workers for specific queues:
        celery -A app.services.queue worker -Q high_priority,default,low_priority -l info

Usage:
    from app.services.tasks import process_content, process_book
    from app.pipelines import PipelineContentType

    # Queue PDF for processing
    process_content.delay(
        content_id="uuid",
        content_type=PipelineContentType.PDF.value,
        source_path="/path/to/file.pdf",
    )

    # Queue voice memo (high priority)
    process_content_high.delay(
        content_id="uuid",
        content_type=PipelineContentType.VOICE_MEMO.value,
        source_path="/path/to/memo.mp3",
    )

    # Queue book for batch OCR
    process_book.delay(
        content_id="uuid",
        image_paths=["/path/to/page1.jpg", "/path/to/page2.jpg"],
        book_metadata={"title": "My Book"},
    )

    # Check task status
    result = process_content.AsyncResult(task_id)
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
from app.db.models import ContentStatus
from app.enums import ProcessingRunStatus
from app.services.queue import celery_app
from app.services.storage import load_content, update_content, update_status

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


# =============================================================================
# Content processing tasks
# =============================================================================


@content_retry
def _process_content_impl(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
) -> dict[str, Any]:
    """
    Internal implementation of content processing with tenacity retry.

    Uses PipelineRegistry to route content to the appropriate pipeline
    based on the content type.

    Args:
        content_id: UUID of the content to process
        content_type: PipelineContentType value (e.g., "pdf", "book", "voice_memo")
        source_path: File path for file-based content
        source_url: URL for web-based content
        source_text: Text for direct text input

    Raises:
        Exception: Re-raised after retry attempts exhausted.
    """
    logger.info(f"Processing content {content_id} (type: {content_type})")

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
        # Note: Status remains PENDING after ingestion.
        # Status changes to PROCESSED only after LLM processing pipeline runs.
        # See: app/services/processing/pipeline.py

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

    return {
        "status": ProcessingRunStatus.INGESTED.value,
        "content_id": content_id,
        "content_type": content_type,
        "title": result.title,
        "ingested_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(name="app.services.tasks.process_content")
def process_content(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
) -> dict[str, Any]:
    """
    Process ingested content through the appropriate pipeline.

    Uses PipelineRegistry to route content based on content_type:
    - "pdf" → PDFProcessor
    - "book" → BookOCRPipeline
    - "voice_memo" → VoiceTranscriber
    - "code" → GitHubImporter
    - "article" → WebArticlePipeline

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 1-4 min).

    Args:
        content_id: UUID of the content to process
        content_type: PipelineContentType value for routing (e.g., "pdf", "book")
        source_path: File path for file-based content
        source_url: URL for web-based content (GitHub, articles)
        source_text: Text for direct text input

    Returns:
        Dictionary with processing results
    """
    try:
        return _process_content_impl(
            content_id, content_type, source_path, source_url, source_text
        )
    except RetryError as e:
        logger.error(f"Processing failed for {content_id} after all retries: {e}")
        asyncio.run(
            update_status(
                content_id, ContentStatus.FAILED.value, str(e), task_context=True
            )
        )
        raise


@celery_app.task(name="app.services.tasks.process_content_high")
def process_content_high(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
) -> dict[str, Any]:
    """
    High-priority content processing (e.g., voice memos).

    Same as process_content but routed to high_priority queue.
    Retry behavior inherited from _process_content_impl via tenacity.
    """
    return process_content(
        content_id, content_type, source_path, source_url, source_text
    )


@celery_app.task(name="app.services.tasks.process_content_low")
def process_content_low(
    content_id: str,
    content_type: str,
    source_path: Optional[str] = None,
    source_url: Optional[str] = None,
    source_text: Optional[str] = None,
) -> dict[str, Any]:
    """
    Low-priority content processing (e.g., batch imports).

    Same as process_content but routed to low_priority queue.
    Retry behavior inherited from _process_content_impl via tenacity.
    """
    return process_content(
        content_id, content_type, source_path, source_url, source_text
    )


@content_retry
def _process_book_impl(
    content_id: str,
    image_paths: list[str],
    book_metadata: dict[str, Any],
    max_concurrency: int = 5,
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
        # Note: Status remains PENDING after ingestion.
        # Status changes to PROCESSED only after LLM processing pipeline runs.
        # See: app/services/processing/pipeline.py

        return result

    # Run the async pipeline and DB update in a single event loop
    result = asyncio.run(run_pipeline_and_update())

    logger.info(
        f"Book {content_id} ingestion complete: "
        f"{result.metadata.get('total_pages_processed', 0)} pages, "
        f"${result.metadata.get('llm_cost_usd', 0):.4f} LLM cost"
    )

    return {
        "status": ProcessingRunStatus.INGESTED.value,
        "content_id": content_id,
        "title": result.title,
        "pages_processed": result.metadata.get("total_pages_processed", 0),
        "llm_cost_usd": result.metadata.get("llm_cost_usd", 0),
        "ingested_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(name="app.services.tasks.process_book")
def process_book(
    content_id: str,
    image_paths: list[str],
    book_metadata: Optional[dict[str, Any]] = None,
    max_concurrency: int = 5,
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

    Time limit: 60 minutes (configured in queue.py)

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 1-4 min).

    Args:
        content_id: UUID of the book content item
        image_paths: List of paths to page image files
        book_metadata: Optional dict with title, authors, isbn
        max_concurrency: Max parallel OCR calls (default 5, increase for faster processing)

    Returns:
        Dictionary with processing results
    """
    book_metadata = book_metadata or {}

    try:
        return _process_book_impl(
            content_id, image_paths, book_metadata, max_concurrency
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
def _sync_raindrop_impl(since_dt: datetime) -> list[Any]:
    """
    Internal implementation of Raindrop sync with tenacity retry.

    Args:
        since_dt: Datetime to sync items from.

    Returns:
        List of synced items.
    """
    if not settings.RAINDROP_ACCESS_TOKEN:
        raise ValueError("RAINDROP_ACCESS_TOKEN not set")

    async def run_sync():
        sync = RaindropSync(access_token=settings.RAINDROP_ACCESS_TOKEN)
        try:
            items = await sync.sync_collection(since=since_dt)
            return items
        finally:
            await sync.close()

    return asyncio.run(run_sync())


@celery_app.task(name="app.services.tasks.sync_raindrop")
def sync_raindrop(since: Optional[str] = None) -> dict[str, Any]:
    """
    Sync bookmarks from Raindrop.io.

    Retry behavior is handled by tenacity (3 attempts, exponential backoff 5-20 min).

    Args:
        since: ISO format datetime string. If provided, only sync items
               created after this date. Defaults to last 24 hours.

    Returns:
        Dictionary with sync results
    """
    logger.info(f"Starting Raindrop sync since {since}")

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
        items = _sync_raindrop_impl(since_dt)
    except RetryError as e:
        logger.error(f"Raindrop sync failed after all retries: {e}")
        raise

    # Queue each item for processing with ARTICLE content type
    for item in items:
        process_content_low.delay(
            content_id=item.id,
            content_type=PipelineContentType.ARTICLE.value,
            source_url=item.url if hasattr(item, "url") else None,
        )

    logger.info(f"Raindrop sync complete: {len(items)} items queued")

    return {
        "status": ProcessingRunStatus.COMPLETED.value,
        "items_synced": len(items),
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

    # Queue each item for processing with CODE content type
    for item in items:
        process_content_low.delay(
            content_id=item.id,
            content_type=PipelineContentType.CODE.value,
            source_url=item.url if hasattr(item, "url") else None,
        )

    logger.info(f"GitHub sync complete: {len(items)} repos queued")

    return {
        "status": ProcessingRunStatus.COMPLETED.value,
        "repos_synced": len(items),
        "synced_at": datetime.utcnow().isoformat(),
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
