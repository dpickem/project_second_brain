"""
Startup Lifecycle Integration

Manages the lifecycle of vault services within the FastAPI application,
ensuring proper initialization on startup and cleanup on shutdown.

Architecture:
    FastAPI Lifespan (main.py)
            |
            V
    startup_vault_services()
            |
            +---> VaultManager (validates vault path)
            +---> VaultSyncService.reconcile_on_startup() (sync offline changes)
            +---> VaultWatcher.start() (begin real-time monitoring)
            |
    [Application Running - watcher syncs changes to Neo4j]
            |
            V
    shutdown_vault_services()
            |
            +---> VaultWatcher.stop()
            +---> VaultSyncService._update_last_sync_time()

Startup Sequence:
    1. Validate vault path exists (via VaultManager)
    2. Run reconciliation to sync notes modified while app was offline
    3. Start file watcher for real-time change detection
    4. Watcher calls sync_note() on file changes (debounced)

Configuration (from settings):
    - VAULT_WATCH_ENABLED: Enable/disable file system monitoring
    - VAULT_SYNC_NEO4J_ENABLED: Enable/disable Neo4j synchronization
    - VAULT_SYNC_DEBOUNCE_MS: Debounce delay for rapid file changes

Thread Safety:
    Module-level state (_vault_watcher, _sync_service) is managed by
    FastAPI's lifespan context, which runs startup/shutdown sequentially.
    The watcher runs in a background thread but schedules async work
    via asyncio.create_task() in the main event loop.

Usage:
    # In main.py lifespan context manager:
    from app.services.obsidian.lifecycle import (
        startup_vault_services,
        shutdown_vault_services,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await startup_vault_services()
        yield
        await shutdown_vault_services()
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config.settings import settings

if TYPE_CHECKING:
    from app.services.obsidian.sync import VaultSyncService
    from app.services.obsidian.watcher import VaultWatcher

logger = logging.getLogger(__name__)

# Module-level state for watcher and sync service
# Managed by FastAPI lifespan - initialized on startup, cleaned up on shutdown
_vault_watcher: VaultWatcher | None = None
_sync_service: VaultSyncService | None = None


async def startup_vault_services() -> dict:
    """
    Initialize vault services on application startup.

    This function is called during FastAPI startup to establish the connection
    between the Obsidian vault and the Neo4j knowledge graph. It performs:

    1. **Reconciliation**: Syncs notes that were modified while the app was
       offline. Compares file modification times against the last sync time
       stored in PostgreSQL (SystemMeta table).

    2. **Watcher Start**: Begins real-time file system monitoring. When users
       edit notes in Obsidian, changes are automatically synced to Neo4j.

    The function is designed to fail gracefully:
    - If the vault path doesn't exist, it logs a warning and returns
    - If Neo4j is unavailable, sync operations are skipped
    - Individual note sync failures don't stop the startup process

    Returns:
        Dict containing:
            - reconciliation: Result dict from reconcile_on_startup() or None
            - watcher_started: Boolean indicating if watcher is running
            - vault_path: String path to the vault or None if not configured

    Raises:
        Exception: Only for unexpected errors; vault/Neo4j unavailability
                   is handled gracefully with warnings.
    """
    global _vault_watcher, _sync_service

    # Import here to avoid circular imports
    from app.services.obsidian.vault import get_vault_manager
    from app.services.obsidian.sync import VaultSyncService
    from app.services.obsidian.watcher import VaultWatcher

    results = {
        "reconciliation": None,
        "watcher_started": False,
        "vault_path": None,
    }

    # Check if vault sync is enabled
    vault_sync_enabled = getattr(settings, "VAULT_SYNC_NEO4J_ENABLED", True)
    vault_watch_enabled = getattr(settings, "VAULT_WATCH_ENABLED", True)
    debounce_ms = getattr(settings, "VAULT_SYNC_DEBOUNCE_MS", 1000)

    try:
        vault = get_vault_manager()
        results["vault_path"] = str(vault.vault_path)
        _sync_service = VaultSyncService()

        # Step 1: Reconcile offline changes
        if vault_sync_enabled:
            logger.info("Starting vault reconciliation...")
            results["reconciliation"] = await _sync_service.reconcile_on_startup(
                vault.vault_path
            )
            logger.info(
                f"Reconciliation complete: {results['reconciliation']['synced']} notes synced"
            )

        # Step 2: Start real-time watcher
        if vault_watch_enabled:
            # Import Celery task here to avoid circular imports
            from app.services.tasks import sync_vault_note

            def on_file_change(path):
                """Handle file changes by queuing Celery task.

                Using Celery instead of direct async provides:
                - Automatic retries if Neo4j is temporarily unavailable
                - Task visibility and monitoring via Redis
                - Decouples watcher thread from asyncio event loop
                - Better handling of burst file changes
                """
                if vault_sync_enabled:
                    try:
                        sync_vault_note.delay(str(path))
                        logger.debug(f"Queued vault sync task for: {path}")
                    except Exception as e:
                        logger.error(f"Failed to queue sync task for {path}: {e}")

            _vault_watcher = VaultWatcher(
                vault_path=str(vault.vault_path),
                on_change=on_file_change,
                debounce_ms=debounce_ms,
            )
            _vault_watcher.start()
            results["watcher_started"] = True
            logger.info(f"Vault watcher started: {vault.vault_path}")

        return results

    except ValueError as e:
        # Vault path doesn't exist - this is expected in some environments
        logger.warning(f"Vault services not started: {e}")
        return results
    except Exception as e:
        logger.error(f"Failed to start vault services: {e}")
        raise


async def shutdown_vault_services() -> None:
    """
    Clean up vault services on application shutdown.

    Performs orderly shutdown of vault-related services:

    1. **Stop Watcher**: Halts file system monitoring. The watchdog observer
       thread is stopped, and no new file events will be processed.

    2. **Update Last Sync Time**: Persists the current timestamp to PostgreSQL
       (SystemMeta table). This timestamp is used by reconcile_on_startup()
       to determine which notes need syncing after the next restart.

    This function is idempotent - safe to call even if startup failed or
    services weren't fully initialized.

    Called automatically by FastAPI's lifespan context manager on shutdown.
    """
    global _vault_watcher, _sync_service

    vault_sync_enabled = getattr(settings, "VAULT_SYNC_NEO4J_ENABLED", True)

    if _vault_watcher:
        _vault_watcher.stop()
        _vault_watcher = None
        logger.info("Vault watcher stopped")

    # Update last sync time on shutdown
    if _sync_service and vault_sync_enabled:
        await _sync_service._update_last_sync_time()
        logger.info("Updated last sync time")

    _sync_service = None


def get_watcher_status() -> dict:
    """
    Get current status of vault watcher and sync configuration.

    Returns the runtime state of vault services, useful for:
    - Health check endpoints
    - Dashboard status displays
    - Debugging sync issues

    Returns:
        Dict containing:
            - watcher_running: True if file watcher is actively monitoring
            - sync_enabled: True if Neo4j sync is configured on
            - watch_enabled: True if file watching is configured on

    Note:
        watcher_running can be False even when watch_enabled is True if:
        - The vault path doesn't exist
        - Startup failed for another reason
        - The app is still starting up
    """
    vault_sync_enabled = getattr(settings, "VAULT_SYNC_NEO4J_ENABLED", True)
    vault_watch_enabled = getattr(settings, "VAULT_WATCH_ENABLED", True)

    return {
        "watcher_running": _vault_watcher.is_running if _vault_watcher else False,
        "sync_enabled": vault_sync_enabled,
        "watch_enabled": vault_watch_enabled,
    }

