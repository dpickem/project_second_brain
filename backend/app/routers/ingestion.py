"""
Ingestion Management Router

Administrative endpoints for managing content ingestion:
- Trigger manual syncs (Raindrop, GitHub)
- Check processing status
- View queue statistics
- Manage scheduled jobs
- Sync tag taxonomy
- Browse and inspect the ingestion queue

Endpoints:
- POST /api/ingestion/raindrop/sync - Trigger Raindrop sync
- POST /api/ingestion/github/sync - Trigger GitHub starred sync
- GET /api/ingestion/status/{content_id} - Get processing status
- GET /api/ingestion/queue/stats - Get queue statistics
- GET /api/ingestion/queue/combined - List all content items with status
- GET /api/ingestion/queue/{content_uuid}/detail - Detailed item status
- GET /api/ingestion/scheduled - List scheduled jobs
- POST /api/ingestion/taxonomy/sync - Sync tag taxonomy from YAML to DB

Usage:
    # Trigger Raindrop sync for last 7 days
    curl -X POST /api/ingestion/raindrop/sync -H "Content-Type: application/json" \
         -d '{"since_days": 7}'
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import Content, ContentStatus
from app.db.models_processing import ProcessingRun
from app.services.tasks import sync_raindrop, sync_github
from app.services.storage import get_pending_content, load_content
from app.services.queue import get_queue_stats
from app.services.scheduler import get_scheduled_jobs, trigger_job_now
from app.services.tag_service import TagService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class RaindropSyncRequest(BaseModel):
    """Request body for Raindrop sync."""

    since_days: int = 1
    collection_id: Optional[int] = 0  # 0 = all collections
    limit: Optional[int] = None  # Max items to sync (default: no limit)


class GitHubSyncRequest(BaseModel):
    """Request body for GitHub sync."""

    limit: int = 50


@router.post("/raindrop/sync")
async def trigger_raindrop_sync(
    background_tasks: BackgroundTasks,
    request: RaindropSyncRequest,
) -> dict[str, Any]:
    """
    Trigger Raindrop.io sync.

    Syncs bookmarks created since the specified number of days ago.

    Args:
        background_tasks: FastAPI background task manager
        request: Sync configuration with since_days, collection_id, and limit

    Returns:
        Dict with sync status and parameters
    """
    since = datetime.now(timezone.utc) - timedelta(days=request.since_days)

    background_tasks.add_task(sync_raindrop.delay, since.isoformat(), request.limit)

    return {
        "status": "sync_started",
        "since": since.isoformat(),
        "collection_id": request.collection_id,
        "limit": request.limit,
        "message": "Raindrop sync queued",
    }


@router.post("/github/sync")
async def trigger_github_sync(
    background_tasks: BackgroundTasks,
    request: GitHubSyncRequest,
) -> dict[str, Any]:
    """
    Sync GitHub starred repositories.

    Imports recently starred repos up to the specified limit.

    Args:
        background_tasks: FastAPI background task manager
        request: Sync configuration with limit

    Returns:
        Dict with sync status and parameters
    """
    background_tasks.add_task(sync_github.delay, request.limit)

    return {
        "status": "sync_started",
        "limit": request.limit,
        "message": "GitHub sync queued",
    }


@router.get("/status/{content_id}")
async def get_processing_status(content_id: str) -> dict[str, Any]:
    """
    Get processing status for a content item.

    Returns current status and any error messages.

    Args:
        content_id: UUID of the content item to check

    Returns:
        Dict with id, title, status, error, source_type, created_at, obsidian_path

    Raises:
        HTTPException: 404 if content not found
    """
    content = await load_content(content_id)

    if not content:
        raise HTTPException(404, "Content not found")

    return {
        "id": content_id,
        "title": content.title,
        "status": (
            content.processing_status.value
            if hasattr(content.processing_status, "value")
            else content.processing_status
        ),
        "error": content.error_message,
        "source_type": content.source_type.value,
        "created_at": content.created_at.isoformat() if content.created_at else None,
        "obsidian_path": content.obsidian_path,
    }


@router.get("/queue/stats")
async def get_queue_statistics() -> dict[str, Any]:
    """
    Get processing queue statistics.

    Returns counts of active, queued, and scheduled tasks.

    Returns:
        Dict with status and queue statistics (active, queued, scheduled counts)
    """
    try:
        stats = get_queue_stats()
        return {
            "status": "ok",
            **stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Could not connect to Celery. Is the worker running?",
        }


@router.get("/scheduled")
async def list_scheduled_jobs() -> dict[str, Any]:
    """
    List all scheduled sync jobs.

    Returns job IDs, names, and next run times.

    Returns:
        Dict with jobs list and count
    """
    jobs = get_scheduled_jobs()
    return {
        "jobs": jobs,
        "count": len(jobs),
    }


@router.post("/scheduled/{job_id}/trigger")
async def trigger_scheduled_job(job_id: str) -> dict[str, str]:
    """
    Manually trigger a scheduled job immediately.

    Useful for testing or forcing an immediate sync.

    Args:
        job_id: ID of the scheduled job to trigger

    Returns:
        Dict with trigger status and job_id

    Raises:
        HTTPException: 404 if job not found
    """
    success = trigger_job_now(job_id)

    if not success:
        raise HTTPException(404, f"Job not found: {job_id}")

    return {
        "status": "triggered",
        "job_id": job_id,
        "message": f"Job {job_id} triggered for immediate execution",
    }


@router.get("/pending")
async def list_pending_content(limit: int = 20) -> dict[str, Any]:
    """
    List content items pending processing.

    Useful for monitoring the processing backlog.

    Args:
        limit: Maximum number of items to return (default: 20)

    Returns:
        Dict with count and list of pending content items
    """
    items = await get_pending_content(limit=limit)

    return {
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "source_type": item.source_type.value,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/taxonomy/sync")
async def sync_taxonomy(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Sync tag taxonomy from YAML to database.

    Creates any tags from the YAML taxonomy that don't exist in the database.
    This is also run automatically daily at 4 AM UTC.

    Returns:
        Dict with sync status and count of tags created
    """
    service = TagService(db)
    count = await service.sync_taxonomy_to_db()

    return {
        "status": "ok",
        "tags_created": count,
        "message": f"Taxonomy sync complete: {count} tags created",
    }


# =============================================================================
# Combined Queue Endpoints
# =============================================================================

# Map string filter values to ContentStatus enum members
_STATUS_MAP = {
    "pending": ContentStatus.PENDING,
    "processing": ContentStatus.PROCESSING,
    "processed": ContentStatus.PROCESSED,
    "failed": ContentStatus.FAILED,
}


@router.get("/queue/combined")
async def list_queue_items(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all content items with their ingestion and processing status.

    Provides a combined view of the ingestion queue across all statuses,
    with optional filtering by status and content type. Items are ordered
    by creation date (newest first).

    Args:
        status: Optional filter (pending, processing, processed, failed)
        content_type: Optional filter by content type (e.g., article, paper)
        limit: Maximum number of items to return (default: 50)
        offset: Number of items to skip for pagination (default: 0)
        db: Database session

    Returns:
        Dict with items, total count, and pagination metadata
    """
    # Build base query
    query = select(Content).order_by(Content.created_at.desc())

    # Apply status filter
    if status and status.lower() in _STATUS_MAP:
        query = query.where(Content.status == _STATUS_MAP[status.lower()])

    # Apply content_type filter
    if content_type:
        query = query.where(Content.content_type == content_type)

    # Get total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # For each item, fetch latest processing run status
    item_list = []
    for item in items:
        # Get latest processing run for this content
        proc_query = (
            select(ProcessingRun)
            .where(ProcessingRun.content_id == item.id)
            .order_by(ProcessingRun.started_at.desc())
            .limit(1)
        )
        proc_result = await db.execute(proc_query)
        proc_run = proc_result.scalar_one_or_none()

        # Extract error from metadata_json if present
        ingestion_error = None
        if item.metadata_json and isinstance(item.metadata_json, dict):
            ingestion_error = item.metadata_json.get("error_message")

        item_list.append({
            "id": item.id,
            "content_uuid": item.content_uuid,
            "title": item.title,
            "content_type": item.content_type,
            "source_url": item.source_url,
            "status": item.status.value if hasattr(item.status, "value") else item.status,
            "processing_status": proc_run.status if proc_run else None,
            "error_message": (
                (proc_run.error_message if proc_run and proc_run.error_message else None)
                or ingestion_error
            ),
            "vault_path": item.vault_path,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        })

    return {
        "items": item_list,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/queue/{content_uuid}/detail")
async def get_queue_item_detail(
    content_uuid: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get detailed status for a single content item in the queue.

    Returns comprehensive information including both ingestion and processing
    status, error messages, processing stages completed, and metadata.

    Args:
        content_uuid: UUID of the content item
        db: Database session

    Returns:
        Dict with full item details

    Raises:
        HTTPException: 404 if content not found
    """
    # Fetch content item
    query = select(Content).where(Content.content_uuid == content_uuid)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(404, f"Content not found: {content_uuid}")

    # Fetch all processing runs (ordered newest first)
    proc_query = (
        select(ProcessingRun)
        .where(ProcessingRun.content_id == item.id)
        .order_by(ProcessingRun.started_at.desc())
    )
    proc_result = await db.execute(proc_query)
    proc_runs = proc_result.scalars().all()

    latest_run = proc_runs[0] if proc_runs else None

    # Extract metadata
    metadata = item.metadata_json or {}
    ingestion_error = metadata.get("error_message") if isinstance(metadata, dict) else None

    # Determine which processing stages were completed
    stages_completed = []
    if latest_run:
        if latest_run.analysis:
            stages_completed.append("content_analysis")
        if latest_run.summaries:
            stages_completed.append("summarization")
        if latest_run.extraction:
            stages_completed.append("extraction")
        if latest_run.tags:
            stages_completed.append("tagging")
        if latest_run.obsidian_note_path:
            stages_completed.append("obsidian_sync")
        if latest_run.neo4j_node_id:
            stages_completed.append("neo4j_sync")

    return {
        "id": item.id,
        "content_uuid": item.content_uuid,
        "title": item.title,
        "content_type": item.content_type,
        "source_url": item.source_url,
        "source_path": item.source_path,
        "vault_path": item.vault_path,
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "summary": item.summary,
        "metadata": {
            k: v for k, v in metadata.items() if k != "error_message"
        } if isinstance(metadata, dict) else metadata,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "processed_at": item.processed_at.isoformat() if item.processed_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        # Ingestion errors
        "ingestion_error": ingestion_error,
        # Processing details (from latest run)
        "processing": {
            "status": latest_run.status if latest_run else None,
            "started_at": latest_run.started_at.isoformat() if latest_run and latest_run.started_at else None,
            "completed_at": latest_run.completed_at.isoformat() if latest_run and latest_run.completed_at else None,
            "processing_time_seconds": latest_run.processing_time_seconds if latest_run else None,
            "estimated_cost_usd": latest_run.estimated_cost_usd if latest_run else None,
            "error_message": latest_run.error_message if latest_run else None,
            "stages_completed": stages_completed,
            "models_used": latest_run.models_used if latest_run else None,
            "total_tokens": latest_run.total_tokens if latest_run else None,
        },
        "processing_runs_count": len(proc_runs),
    }
