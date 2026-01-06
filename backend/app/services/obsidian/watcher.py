"""
Vault File Watcher

Monitors the Obsidian vault for real-time file changes using the watchdog library.
Detects when users create or modify markdown notes in Obsidian, enabling automatic
synchronization with Neo4j and other downstream processing.

Key Features:
- Debounced callbacks: Rapid successive saves (e.g., during typing) are coalesced
  into a single callback, preventing unnecessary processing overhead
- Selective monitoring: Only watches .md files, ignores .obsidian/ config directory
- Thread-safe: Uses locking for safe concurrent access to pending changes
- Graceful lifecycle: Clean start/stop with proper thread cleanup

Architecture:
    VaultWatcher (lifecycle management)
        └── VaultEventHandler (event filtering & debouncing)
                └── watchdog.Observer (OS-level file monitoring)

The watcher is designed to run continuously while the backend is active.
For changes made while the app was stopped, use VaultSyncService.reconcile_on_startup().

Usage:
    from app.services.obsidian.watcher import VaultWatcher

    def handle_change(path: Path):
        print(f"Note changed: {path}")

    watcher = VaultWatcher("/path/to/vault", on_change=handle_change)
    watcher.start()
    # ... application runs ...
    watcher.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class VaultEventHandler(FileSystemEventHandler):
    """
    Handles and debounces file system events from the Obsidian vault.

    This handler filters events to only process markdown file changes,
    ignoring directories, non-.md files, and the .obsidian/ config folder.

    Debouncing Strategy:
        When a file change is detected, it's added to a pending dict with a timestamp.
        A timer is started/reset to process all pending changes after debounce_ms.
        This means if a user saves a file multiple times in quick succession,
        only one callback fires after they stop typing.

    Thread Safety:
        Uses a threading.Lock to protect the pending dict and timer from
        concurrent access, as watchdog events come from a background thread.

    Attributes:
        vault_path: Root path of the Obsidian vault
        on_change: Callback function invoked with the changed file's Path
        debounce_ms: Milliseconds to wait before processing accumulated changes
    """

    def __init__(
        self,
        vault_path: Path,
        on_change: Callable[[Path], None],
        debounce_ms: int = 1000,
    ):
        """
        Initialize the event handler.

        Args:
            vault_path: Root path of the Obsidian vault being watched
            on_change: Callback invoked for each changed file after debouncing
            debounce_ms: Delay in ms before processing changes (default: 1000ms)
        """
        self.vault_path = vault_path
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self._pending: dict[str, float] = {}
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _handle_event(self, event):
        """
        Common handler for file creation and modification events.

        Filters out directories, non-markdown files, and .obsidian/ config files
        before scheduling the callback.
        """
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        # Ignore .obsidian directory (Obsidian's internal config)
        if "/.obsidian/" in event.src_path or "\\.obsidian\\" in event.src_path:
            return

        self._schedule_callback(Path(event.src_path))

    def on_modified(self, event):
        """Handle file modification events (user saves an existing note)."""
        self._handle_event(event)

    def on_created(self, event):
        """Handle file creation events (user creates a new note)."""
        self._handle_event(event)

    def _schedule_callback(self, path: Path):
        """
        Schedule a debounced callback for a file change.

        Adds the path to pending changes and resets the debounce timer.
        If the timer was already running, it's cancelled and restarted,
        effectively extending the debounce window.

        Args:
            path: Path to the changed markdown file
        """
        with self._lock:
            self._pending[str(path)] = time.time()

            # Cancel existing timer
            if self._timer:
                self._timer.cancel()

            # Schedule new timer
            self._timer = threading.Timer(
                self.debounce_ms / 1000.0, self._process_pending
            )
            self._timer.start()

    def _process_pending(self):
        """
        Process all accumulated pending file changes.

        Called by the debounce timer after debounce_ms of inactivity.
        Invokes on_change callback for each pending path, catching and
        logging any exceptions to prevent one bad file from blocking others.
        """
        with self._lock:
            paths = list(self._pending.keys())
            self._pending.clear()

        for path_str in paths:
            try:
                self.on_change(Path(path_str))
            except Exception as e:
                logger.error(f"Error processing change for {path_str}: {e}")


class VaultWatcher:
    """
    High-level interface for watching the Obsidian vault for file changes.

    Manages the lifecycle of the watchdog Observer and provides a simple
    start/stop interface. Typically instantiated once at application startup
    and stopped at shutdown.

    The watcher monitors the entire vault recursively, but the VaultEventHandler
    filters to only process relevant markdown file changes.

    Integration with VaultSyncService:
        The typical pattern is to pass VaultSyncService.sync_note as the on_change
        callback, so detected changes are automatically synced to Neo4j.

    Attributes:
        vault_path: Root path of the Obsidian vault
        on_change: Callback invoked for each changed file
        debounce_ms: Debounce delay in milliseconds
        is_running: Whether the watcher is currently active

    Example:
        watcher = VaultWatcher(
            vault_path="/path/to/vault",
            on_change=sync_service.sync_note,
            debounce_ms=1000
        )
        watcher.start()
        # ... app runs ...
        watcher.stop()
    """

    def __init__(
        self,
        vault_path: str,
        on_change: Callable[[Path], None] | None = None,
        debounce_ms: int = 1000,
    ):
        """
        Initialize the vault watcher.

        Args:
            vault_path: Path to the Obsidian vault root directory
            on_change: Callback function invoked with Path of each changed file.
                      If None, defaults to logging the change.
            debounce_ms: Milliseconds to wait after last change before invoking
                        callback (default: 1000ms). Higher values reduce processing
                        during rapid edits but increase latency.
        """
        self.vault_path = Path(vault_path)
        self.on_change = on_change or self._default_handler
        self.debounce_ms = debounce_ms
        self._observer: Optional[Observer] = None
        self._running = False

    def _default_handler(self, path: Path):
        """Default change handler that simply logs the changed path."""
        logger.info(f"File changed: {path}")

    def start(self):
        """
        Start watching the vault for file changes.

        Creates a watchdog Observer with recursive monitoring enabled.
        Safe to call multiple times; subsequent calls are no-ops if already running.

        Note:
            This method returns immediately; monitoring happens in a background thread.
        """
        if self._running:
            logger.warning("Vault watcher already running")
            return

        handler = VaultEventHandler(
            self.vault_path, self.on_change, self.debounce_ms
        )

        self._observer = Observer()
        self._observer.schedule(handler, str(self.vault_path), recursive=True)
        self._observer.start()
        self._running = True

        logger.info(f"Started vault watcher: {self.vault_path}")

    def stop(self):
        """
        Stop watching the vault and clean up resources.

        Stops the watchdog Observer and waits up to 5 seconds for the
        background thread to terminate. Safe to call even if not running.
        """
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._running = False
        logger.info("Stopped vault watcher")

    @property
    def is_running(self) -> bool:
        """Whether the watcher is currently monitoring the vault."""
        return self._running

