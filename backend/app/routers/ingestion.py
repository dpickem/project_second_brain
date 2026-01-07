"""
Ingestion Management Router

Administrative endpoints for managing content ingestion:
- Trigger manual syncs (Raindrop, GitHub)
- Check processing status
- View queue statistics
- Manage scheduled jobs
- Sync tag taxonomy

Endpoints:
- POST /api/ingestion/raindrop/sync - Trigger Raindrop sync
- POST /api/ingestion/github/sync - Trigger GitHub starred sync
- GET /api/ingestion/status/{content_id} - Get processing status
- GET /api/ingestion/queue/stats - Get queue statistics
- GET /api/ingestion/scheduled - List scheduled jobs
- POST /api/ingestion/taxonomy/sync - Sync tag taxonomy from YAML to DB

Usage:
    # Trigger Raindrop sync for last 7 days
    curl -X POST /api/ingestion/raindrop/sync -H "Content-Type: application/json" \
         -d '{"since_days": 7}'
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.tasks import sync_raindrop, sync_github
from app.services.storage import get_pending_content, load_content
from app.services.queue import get_queue_stats
from app.services.scheduler import get_scheduled_jobs, trigger_job_now
from app.services.tag_service import TagService

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class RaindropSyncRequest(BaseModel):
    """Request body for Raindrop sync."""

    since_days: int = 1
    collection_id: Optional[int] = 0  # 0 = all collections


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
        request: Sync configuration with since_days and collection_id

    Returns:
        Dict with sync status and parameters
    """
    since = datetime.utcnow() - timedelta(days=request.since_days)

    background_tasks.add_task(sync_raindrop.delay, since.isoformat())

    return {
        "status": "sync_started",
        "since": since.isoformat(),
        "collection_id": request.collection_id,
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
