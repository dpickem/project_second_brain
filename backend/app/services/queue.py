"""
Celery Queue Configuration

Provides async task processing for content ingestion. Tasks are routed to
different queues based on priority:
- high_priority: Voice memos (user waiting)
- default: Normal content processing, book OCR
- low_priority: Batch imports, background syncs

Why Celery?
- Async processing: User uploads → immediate response → background processing
- Retry logic: Transient API failures automatically retry with exponential backoff
- Priority queues: Voice memos process before batch PDF imports
- Scalability: Add more workers as content volume grows
- Observability: Track job status, failures, and processing times

Task Time Limits:
- Default tasks: 10 minutes
- Book OCR (process_book): 60 minutes (parallel processing of many pages)

Usage:
    from app.services.queue import celery_app
    from app.services.tasks import process_content

    # Queue a task
    process_content.delay(content_id, {"priority": "high"})

    # Run worker: celery -A app.services.queue worker -l info
"""

import logging

import litellm
from celery import Celery
from celery.signals import worker_process_init
from litellm.litellm_core_utils import logging_worker as litellm_logging_worker

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "second_brain",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.services.tasks.process_content": {"queue": "default"},
        "app.services.tasks.process_content_high": {"queue": "high_priority"},
        "app.services.tasks.process_content_low": {"queue": "low_priority"},
        "app.services.tasks.process_book": {"queue": "default"},
        "app.services.tasks.sync_raindrop": {"queue": "low_priority"},
        "app.services.tasks.sync_github": {"queue": "low_priority"},
    },
    # Task-specific time limits (override defaults for long-running tasks)
    task_annotations={
        "app.services.tasks.process_book": {
            "soft_time_limit": 1800,  # 30 minutes soft limit
            "time_limit": 3600,  # 60 minutes hard limit
        },
    },
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    # Result expiration (24 hours)
    result_expires=86400,
    # Default task time limits (overridden by task_annotations for specific tasks)
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Concurrency
    worker_prefetch_multiplier=1,  # For fair task distribution
    # Task acknowledgment
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


# =============================================================================
# Worker Process Initialization
# =============================================================================
# LiteLLM's LoggingWorker creates an asyncio Queue at module import time.
# When Celery forks workers (prefork pool), each worker gets a new event loop
# but the queue is still bound to the parent's loop, causing:
#   RuntimeError: <Queue ...> is bound to a different event loop
#
# This signal handler resets LiteLLM's internal state after each worker fork.


@worker_process_init.connect
def reset_litellm_on_worker_init(**kwargs):
    """
    Reset LiteLLM's async logging state after Celery worker fork.
    
    This prevents the 'Queue bound to different event loop' error that occurs
    when LiteLLM's LoggingWorker is initialized before Celery forks workers.
    
    The issue: LiteLLM's LoggingWorker creates an asyncio.Queue at module import,
    which binds to the parent process's event loop. After Celery forks, each worker
    has a new event loop but the queue is still bound to the old one.
    """
    try:
        # Reset top-level litellm attributes that may hold event loop references
        if hasattr(litellm, "_logging_worker"):
            litellm._logging_worker = None
        
        # Reset async callbacks that might hold event loop refs
        if hasattr(litellm, "_async_success_callback"):
            litellm._async_success_callback = []
        if hasattr(litellm, "_async_failure_callback"):
            litellm._async_failure_callback = []
        
        # Reset the LoggingWorker singleton in the core utils module
        if hasattr(litellm_logging_worker, "_logging_worker_instance"):
            litellm_logging_worker._logging_worker_instance = None
        if hasattr(litellm_logging_worker, "logging_worker"):
            litellm_logging_worker.logging_worker = None
            
        logger.debug("Reset LiteLLM logging state for new worker process")
        
    except Exception as e:
        # Log but don't fail worker startup
        logger.warning(f"Failed to reset LiteLLM state on worker init: {e}")


def get_queue_stats() -> dict:
    """
    Get statistics about the task queues.

    Returns:
        Dictionary with queue statistics
    """
    inspect = celery_app.control.inspect()

    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    scheduled = inspect.scheduled() or {}

    return {
        "active_tasks": sum(len(v) for v in active.values()),
        "queued_tasks": sum(len(v) for v in reserved.values()),
        "scheduled_tasks": sum(len(v) for v in scheduled.values()),
        "workers": list(active.keys()),
    }
