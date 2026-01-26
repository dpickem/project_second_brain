"""
Scheduled Job Configuration

Configures periodic sync jobs using APScheduler:
- Raindrop.io sync every 6 hours
- GitHub starred repos sync daily at 7 AM
- Task cleanup daily at 3 AM
- Tag taxonomy sync daily at 4 AM

Execution Context:
    The scheduler runs IN-PROCESS with FastAPI inside the backend Docker container.
    It is started/stopped via FastAPI's lifespan context manager in app/main.py.

    Flow:
        docker-compose up -> backend container starts -> uvicorn starts FastAPI
        -> lifespan() calls start_scheduler() -> APScheduler runs in the event loop

    The scheduler does NOT execute jobs directly. Instead, it queues Celery tasks
    to Redis (e.g., sync_raindrop.delay()). A separate Celery worker would then
    pick up and execute those tasks.

Why APScheduler (AsyncIOScheduler)?
    - Shares FastAPI's asyncio event loop (no thread overhead)
    - Cron-like syntax for scheduling
    - Lightweight for a single-instance deployment

Limitations:
    - Single instance only: If you scale to multiple backend replicas,
      each replica runs its own scheduler, causing duplicate job triggers.
    - For multi-instance deployments, use Celery Beat or add leader election.

Usage:
    # Automatic (via FastAPI lifespan in main.py):
    start_scheduler()  # On app startup
    stop_scheduler()   # On app shutdown

    # Manual trigger for testing:
    from app.services.scheduler import trigger_job_now
    trigger_job_now("raindrop_sync")
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def trigger_raindrop_sync() -> None:
    """Trigger Raindrop sync for last 24 hours."""
    # Deferred import: Celery tasks are heavy and may have circular dependencies.
    # Importing here avoids loading the full task module at scheduler initialization.
    from app.services.tasks import sync_raindrop

    since = datetime.utcnow() - timedelta(hours=24)
    sync_raindrop.delay(since.isoformat())
    logger.info(f"Triggered Raindrop sync since {since}")


async def trigger_github_sync() -> None:
    """Trigger GitHub starred repos sync."""
    # Deferred import: Celery tasks are heavy and may have circular dependencies.
    from app.services.tasks import sync_github

    sync_github.delay(limit=100)
    logger.info("Triggered GitHub sync")


async def trigger_cleanup() -> None:
    """Trigger periodic cleanup task."""
    # Deferred import: Celery tasks are heavy and may have circular dependencies.
    from app.services.tasks import cleanup_old_tasks

    cleanup_old_tasks.delay()
    logger.info("Triggered cleanup task")


async def trigger_taxonomy_sync() -> None:
    """Sync tag taxonomy from YAML to database."""
    # Deferred imports: Avoid loading DB and service modules until job execution.
    from app.db.base import async_session_maker
    from app.services.tag_service import TagService

    async with async_session_maker() as db:
        service = TagService(db)
        count = await service.sync_taxonomy_to_db()
        logger.info(f"Taxonomy sync complete: {count} tags created")


def setup_scheduled_jobs() -> None:
    """Configure all scheduled sync jobs."""

    # Raindrop sync - every 6 hours
    scheduler.add_job(
        trigger_raindrop_sync,
        CronTrigger(hour="*/6"),
        id="raindrop_sync",
        name="Raindrop.io Sync",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow 1 hour grace period
    )

    # GitHub starred sync - daily at 7 AM UTC
    scheduler.add_job(
        trigger_github_sync,
        CronTrigger(hour=7, minute=0),
        id="github_sync",
        name="GitHub Starred Sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Cleanup task - daily at 3 AM UTC
    scheduler.add_job(
        trigger_cleanup,
        CronTrigger(hour=3, minute=0),
        id="cleanup",
        name="Task Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Taxonomy sync - daily at 4 AM UTC
    scheduler.add_job(
        trigger_taxonomy_sync,
        CronTrigger(hour=4, minute=0),
        id="taxonomy_sync",
        name="Tag Taxonomy Sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info("Scheduled jobs configured:")
    logger.info("  - Raindrop sync: every 6 hours")
    logger.info("  - GitHub sync: daily at 07:00 UTC")
    logger.info("  - Cleanup: daily at 03:00 UTC")
    logger.info("  - Taxonomy sync: daily at 04:00 UTC")


def start_scheduler() -> None:
    """Start the scheduler and configure jobs."""
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    setup_scheduled_jobs()
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    if not scheduler.running:
        logger.warning("Scheduler not running")
        return

    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


def get_scheduled_jobs() -> list[dict]:
    """Get list of scheduled jobs with their next run times."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
        )
    return jobs


def trigger_job_now(job_id: str) -> bool:
    """
    Manually trigger a scheduled job immediately.

    Args:
        job_id: ID of the job to trigger

    Returns:
        True if triggered successfully
    """
    job = scheduler.get_job(job_id)
    if job:
        job.modify(next_run_time=datetime.now())
        logger.info(f"Manually triggered job: {job_id}")
        return True

    logger.warning(f"Job not found: {job_id}")
    return False
