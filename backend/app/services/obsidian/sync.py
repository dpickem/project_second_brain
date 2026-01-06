"""
Neo4j Sync Service

Synchronizes Obsidian vault content to the Neo4j knowledge graph, enabling
graph-based queries, visualization, and relationship discovery across notes.

Three-Tier Sync Strategy:
    1. Real-time sync (sync_note): Called by VaultWatcher when user edits a note.
       Low latency, handles single notes. Best for active editing sessions.

    2. Startup reconciliation (reconcile_on_startup): Runs during FastAPI startup.
       Compares file mtimes against last_sync_time stored in PostgreSQL (SystemMeta).
       Efficiently syncs only notes modified while the app was not running.

    3. Manual full sync (full_sync): Triggered via API for bulk operations.
       Syncs entire vault. Useful after imports, migrations, or recovery.

Neo4j Data Model:
    - Node: (Note {id, title, type, tags[], updated_at})
    - Relationship: (Note)-[:LINKS_TO]->(Note) for wikilinks

What Gets Synced:
    - Frontmatter metadata (title, type, tags, custom fields)
    - Wikilinks extracted from note body → LINKS_TO relationships
    - Inline #tags merged with frontmatter tags

Persistence:
    - last_sync_time stored in PostgreSQL SystemMeta table (key: vault_last_sync_time)
    - Survives app restarts for accurate reconciliation

Status Tracking:
    - Module-level SyncStatus tracks progress of long-running syncs
    - Exposed via get_sync_status() for API polling

Usage:
    from app.services.obsidian.sync import VaultSyncService, get_sync_status

    sync_service = VaultSyncService()

    # Single note (from watcher callback)
    await sync_service.sync_note(Path("/vault/sources/papers/my-paper.md"))

    # Startup reconciliation
    await sync_service.reconcile_on_startup(Path("/vault"))

    # Full sync (API endpoint)
    result = await sync_service.full_sync(Path("/vault"))

    # Check progress
    status = get_sync_status()
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from app.db.base import async_session_maker
from app.db.models import SystemMeta
from app.services.knowledge_graph.client import get_neo4j_client
from app.services.obsidian.frontmatter import parse_frontmatter_file, update_frontmatter
from app.services.obsidian.links import extract_tags, extract_wikilinks

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Sync Status Tracking (module-level state)
# ─────────────────────────────────────────────────────────────


@dataclass
class SyncStatus:
    """
    Tracks the current state of vault sync operations.

    This is module-level state that allows API endpoints to poll for progress
    during long-running sync operations (full_sync or reconciliation).

    Attributes:
        is_running: True if a sync operation is currently in progress
        sync_type: Type of current sync ("full", "reconciliation", or None)
        started_at: UTC timestamp when current sync started
        total_notes: Total notes to process in current operation
        processed_notes: Number of notes processed so far
        synced_notes: Notes successfully synced to Neo4j
        failed_notes: Notes that failed to sync (errors logged)
        last_result: Summary dict from most recent completed sync
        last_completed_at: UTC timestamp of last completed sync
        last_error: Error message if last sync failed
    """

    is_running: bool = False
    sync_type: Optional[str] = None  # "full", "reconciliation", or None
    started_at: Optional[datetime] = None
    total_notes: int = 0
    processed_notes: int = 0
    synced_notes: int = 0
    failed_notes: int = 0
    last_result: Optional[dict] = None
    last_completed_at: Optional[datetime] = None
    last_error: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API response.

        Returns:
            Dict with is_running, sync_type, started_at, progress (nested),
            last_result, last_completed_at, and last_error fields.
        """
        return {
            "is_running": self.is_running,
            "sync_type": self.sync_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "progress": {
                "total": self.total_notes,
                "processed": self.processed_notes,
                "synced": self.synced_notes,
                "failed": self.failed_notes,
                "percent": (
                    round(self.processed_notes / self.total_notes * 100, 1)
                    if self.total_notes > 0
                    else 0
                ),
            },
            "last_result": self.last_result,
            "last_completed_at": (
                self.last_completed_at.isoformat() if self.last_completed_at else None
            ),
            "last_error": self.last_error,
        }


# Global sync status instance (singleton pattern for cross-request state)
_sync_status = SyncStatus()


def get_sync_status() -> dict:
    """
    Get the current sync status as a dictionary.

    This function is the public interface for checking sync progress.
    Called by API endpoints to provide real-time feedback to users.

    Returns:
        Dict with sync state, progress metrics, and last operation results.
    """
    return _sync_status.to_dict()


class VaultSyncService:
    """
    Synchronizes Obsidian vault content to Neo4j knowledge graph.

    This service bridges the file-based Obsidian vault with the graph database,
    enabling powerful relationship queries and knowledge discovery. It handles
    the complexity of parsing markdown, extracting metadata, and maintaining
    graph consistency.

    Key Responsibilities:
        - Parse frontmatter and extract metadata from notes
        - Extract wikilinks to build LINKS_TO relationships
        - Merge inline #tags with frontmatter tags
        - Create/update Note nodes in Neo4j
        - Track sync timestamps for efficient reconciliation

    Thread Safety:
        - Uses module-level _sync_status for progress tracking
        - Prevents concurrent full syncs (returns error if already running)
        - Individual sync_note() calls are safe for concurrent use

    Error Handling:
        - Individual note failures don't stop batch operations
        - Errors are logged and counted in results
        - Neo4j unavailability is handled gracefully (syncs become no-ops)

    Attributes:
        LAST_SYNC_KEY: PostgreSQL SystemMeta key for storing last sync timestamp
    """

    LAST_SYNC_KEY = "vault_last_sync_time"

    def __init__(self):
        """Initialize the sync service with lazy-loaded Neo4j client."""
        self._neo4j = None

    async def _ensure_neo4j(self):
        """
        Ensure Neo4j client is initialized (async).

        Lazily loads the client on first call. Returns None if Neo4j is
        unavailable, allowing sync operations to proceed without the
        graph database (useful for testing or when Neo4j is temporarily down).

        Returns:
            Neo4jClient instance or None
        """
        if self._neo4j is None:
            try:
                self._neo4j = await get_neo4j_client()
            except Exception as e:
                logger.warning(f"Failed to get Neo4j client: {e}")
        return self._neo4j

    # Namespace UUID for generating deterministic node IDs from file paths
    _NODE_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # UUID namespace for URLs

    async def _generate_and_persist_node_id(self, note_path: Path) -> str:
        """
        Generate a deterministic UUID for a note and persist it to frontmatter.

        Uses UUID5 (SHA-1 based) to create a consistent ID from the absolute path.
        The generated ID is written back to the note's frontmatter so subsequent
        syncs will use the stored ID rather than regenerating.

        Args:
            note_path: Absolute path to the note file

        Returns:
            UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")

        Note:
            Writing to the file may trigger the VaultWatcher, but the debounce
            mechanism will coalesce rapid changes.
        """
        node_id = str(uuid.uuid5(self._NODE_ID_NAMESPACE, str(note_path)))

        # Persist the ID to frontmatter so it's stable across renames
        try:
            await update_frontmatter(note_path, {"id": node_id})
            logger.debug(f"Persisted node ID {node_id} to {note_path.name}")
        except Exception as e:
            logger.warning(f"Failed to persist node ID to {note_path}: {e}")

        return node_id

    # ─────────────────────────────────────────────────────────────
    # Startup Reconciliation - Handle offline changes
    # ─────────────────────────────────────────────────────────────

    async def reconcile_on_startup(self, vault_path: Path) -> dict:
        """
        Detect and sync changes made while the application was offline.

        This is the key mechanism for handling the "offline gap" - when users
        edit notes in Obsidian while the backend isn't running. By comparing
        file modification times (mtime) against the stored last_sync_time,
        we can efficiently identify and sync only the changed files.

        Algorithm:
            1. Retrieve last_sync_time from PostgreSQL SystemMeta
            2. Scan all .md files in vault (excluding .obsidian/)
            3. Filter to files with mtime > last_sync_time
            4. Sync each modified file to Neo4j
            5. Update last_sync_time to now

        This should be called during FastAPI startup (via lifespan handler)
        before the VaultWatcher starts, ensuring consistency.

        Args:
            vault_path: Absolute path to the Obsidian vault root

        Returns:
            Dict with:
                - total_notes: Total markdown files in vault
                - modified_since_sync: Files needing sync
                - synced: Successfully synced count
                - failed: Failed sync count
                - last_sync: Previous sync timestamp (or None if first run)

        Note:
            On first run (no last_sync_time), ALL notes are synced.
            This may take a while for large vaults.
        """
        global _sync_status

        # Update status
        _sync_status.is_running = True
        _sync_status.sync_type = "reconciliation"
        _sync_status.started_at = datetime.now(timezone.utc)
        _sync_status.processed_notes = 0
        _sync_status.synced_notes = 0
        _sync_status.failed_notes = 0
        _sync_status.last_error = None

        try:
            last_sync = await self._get_last_sync_time()

            notes = list(vault_path.rglob("*.md"))
            notes = [n for n in notes if ".obsidian" not in str(n)]

            # Find notes modified since last sync
            modified_since_sync = []
            for note_path in notes:
                try:
                    mtime = datetime.fromtimestamp(
                        note_path.stat().st_mtime, tz=timezone.utc
                    )
                    if last_sync is None or mtime > last_sync:
                        modified_since_sync.append(note_path)
                except OSError as e:
                    logger.warning(f"Could not stat {note_path}: {e}")

            _sync_status.total_notes = len(modified_since_sync)

            results = {
                "total_notes": len(notes),
                "modified_since_sync": len(modified_since_sync),
                "synced": 0,
                "failed": 0,
                "last_sync": last_sync.isoformat() if last_sync else None,
            }

            # Sync only the changed files
            for note_path in modified_since_sync:
                result = await self.sync_note(note_path)
                _sync_status.processed_notes += 1
                if "error" in result:
                    results["failed"] += 1
                    _sync_status.failed_notes += 1
                else:
                    results["synced"] += 1
                    _sync_status.synced_notes += 1

            # Update last sync time
            await self._update_last_sync_time()

            logger.info(
                f"Startup reconciliation: {results['synced']}/{results['modified_since_sync']} "
                f"modified notes synced (checked {results['total_notes']} total)"
            )

            # Update status with result
            _sync_status.last_result = results
            _sync_status.last_completed_at = datetime.now(timezone.utc)

            return results

        except Exception as e:
            _sync_status.last_error = str(e)
            raise
        finally:
            _sync_status.is_running = False
            _sync_status.sync_type = None

    async def _get_last_sync_time(self) -> Optional[datetime]:
        """
        Retrieve the last vault sync timestamp from PostgreSQL.

        Queries the SystemMeta table for the vault_last_sync_time key.
        This timestamp is used to determine which files have changed
        since the last sync operation.

        Returns:
            UTC datetime of last sync, or None if never synced
        """
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(SystemMeta).where(SystemMeta.key == self.LAST_SYNC_KEY)
                )
                row = result.scalar_one_or_none()
                if row and row.value:
                    return datetime.fromisoformat(row.value)
        except Exception as e:
            logger.warning(f"Failed to get last sync time: {e}")

        return None

    async def _update_last_sync_time(self) -> None:
        """
        Update the last vault sync timestamp in PostgreSQL.

        Called after successful sync operations to record the sync time.
        Uses upsert logic (update if exists, insert if not).

        Note:
            This timestamp should only be updated after a successful sync
            to avoid missing changes if a sync fails partway through.
        """
        now = datetime.now(timezone.utc)
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(SystemMeta).where(SystemMeta.key == self.LAST_SYNC_KEY)
                )
                row = result.scalar_one_or_none()
                if row:
                    row.value = now.isoformat()
                else:
                    session.add(
                        SystemMeta(key=self.LAST_SYNC_KEY, value=now.isoformat())
                    )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update last sync time: {e}")

    # ─────────────────────────────────────────────────────────────
    # Single Note Sync - Used by watcher for real-time updates
    # ─────────────────────────────────────────────────────────────

    async def sync_note(self, note_path: Path) -> dict:
        """
        Sync a single note to Neo4j knowledge graph.

        This is the core sync operation, used by both the real-time watcher
        and batch operations. It's designed to be fast and idempotent.

        Processing Steps:
            1. Parse frontmatter using python-frontmatter
            2. Extract wikilinks from body using regex ([[target]])
            3. Extract inline #tags from body
            4. Merge inline tags with frontmatter tags (deduplicated)
            5. MERGE Note node in Neo4j (create or update)
            6. Clear and recreate LINKS_TO relationships

        Node ID Strategy:
            - Uses frontmatter 'id' field if present
            - Otherwise generates deterministic UUID5 from absolute file path
            - Generated UUID is persisted back to frontmatter for stability
            - UUID ensures uniqueness even for same-named files in different folders

        Args:
            note_path: Absolute path to the markdown note file

        Returns:
            Success: {"path": str, "node_id": str, "links_synced": int, "tags": list}
            Failure: {"path": str, "error": str}

        Note:
            If Neo4j is unavailable, the sync completes successfully but
            no graph updates occur. This allows the system to continue
            operating in degraded mode.
        """
        try:
            # Parse note
            fm, body = await parse_frontmatter_file(note_path)

            # Extract links and tags
            outgoing_links = extract_wikilinks(body)
            inline_tags = extract_tags(body)

            # Combine frontmatter tags with inline tags
            fm_tags = fm.get("tags", [])
            if isinstance(fm_tags, str):
                fm_tags = [fm_tags]
            all_tags = list(set(fm_tags + inline_tags))

            # Determine node ID (use frontmatter id, or generate and persist a deterministic UUID)
            node_id = fm.get("id") or await self._generate_and_persist_node_id(note_path)
            title = fm.get("title", note_path.stem)
            note_type = fm.get("type", "note")

            # Update Neo4j node if client is available
            neo4j = await self._ensure_neo4j()
            if neo4j:
                await self._update_neo4j_node(
                    node_id=node_id,
                    title=title,
                    note_type=note_type,
                    tags=all_tags,
                    metadata=fm,
                )

                # Sync outgoing links
                await self._sync_links(node_id, outgoing_links)

            logger.debug(f"Synced note to Neo4j: {note_path.name}")

            return {
                "path": str(note_path),
                "node_id": node_id,
                "links_synced": len(outgoing_links),
                "tags": all_tags,
            }

        except Exception as e:
            logger.error(f"Failed to sync note {note_path}: {e}")
            return {
                "path": str(note_path),
                "error": str(e),
            }

    async def _update_neo4j_node(
        self,
        node_id: str,
        title: str,
        note_type: str,
        tags: list[str],
        metadata: dict,
    ):
        """
        Create or update a Note node in Neo4j via the client.

        Delegates to Neo4jClient.merge_note_node() which uses MERGE for
        idempotent updates. See client.py for implementation details.

        Args:
            node_id: Unique identifier for the note (from frontmatter or generated)
            title: Display title for the note
            note_type: Content type (paper, article, concept, etc.)
            tags: List of all tags (frontmatter + inline)
            metadata: Full frontmatter dict (reserved for future use)
        """
        neo4j = await self._ensure_neo4j()
        if not neo4j:
            return

        try:
            await neo4j.merge_note_node(
                node_id=node_id,
                title=title,
                note_type=note_type,
                tags=tags,
            )
        except Exception as e:
            logger.error(f"Failed to update Neo4j node {node_id}: {e}")

    async def _sync_links(self, source_id: str, targets: list[str]):
        """
        Synchronize outgoing wikilinks via the Neo4j client.

        Delegates to Neo4jClient.sync_note_links() which implements
        delete-and-recreate strategy. See client.py for details.

        Args:
            source_id: Node ID of the source note
            targets: List of target node IDs (extracted wikilink texts)
        """
        neo4j = await self._ensure_neo4j()
        if not neo4j:
            return

        try:
            await neo4j.sync_note_links(source_id, targets)
        except Exception as e:
            logger.error(f"Failed to sync links for {source_id}: {e}")

    # ─────────────────────────────────────────────────────────────
    # Full Sync - Manual trigger via API
    # ─────────────────────────────────────────────────────────────

    async def full_sync(self, vault_path: Path) -> dict:
        """
        Sync all notes in the vault to Neo4j.

        This is a heavyweight operation that processes every markdown file
        in the vault. Use sparingly - typically only for:
            - Initial setup / migration
            - Recovery after Neo4j data loss
            - Debugging / verification

        For routine operations, use:
            - sync_note() for real-time changes (via VaultWatcher)
            - reconcile_on_startup() for offline changes

        Concurrency Protection:
            Only one full_sync can run at a time. If called while another
            is in progress, returns immediately with an error status.

        Progress Tracking:
            Updates module-level _sync_status throughout execution.
            Poll via get_sync_status() for real-time progress.

        Args:
            vault_path: Absolute path to the Obsidian vault root

        Returns:
            Success: {"synced": int, "failed": int, "errors": list, "total": int}
            Already running: {"error": str, "status": dict}

        Warning:
            Can be slow for large vaults (1000+ notes). Consider running
            during off-peak hours or with user notification.
        """
        global _sync_status

        # Check if sync is already running
        if _sync_status.is_running:
            return {
                "error": "Sync already in progress",
                "status": _sync_status.to_dict(),
            }

        # Update status
        _sync_status.is_running = True
        _sync_status.sync_type = "full"
        _sync_status.started_at = datetime.now(timezone.utc)
        _sync_status.processed_notes = 0
        _sync_status.synced_notes = 0
        _sync_status.failed_notes = 0
        _sync_status.last_error = None

        try:
            notes = list(vault_path.rglob("*.md"))
            notes = [n for n in notes if ".obsidian" not in str(n)]

            _sync_status.total_notes = len(notes)

            results = {"synced": 0, "failed": 0, "errors": [], "total": len(notes)}

            for note_path in notes:
                result = await self.sync_note(note_path)
                _sync_status.processed_notes += 1
                if "error" in result:
                    results["failed"] += 1
                    results["errors"].append(result)
                    _sync_status.failed_notes += 1
                else:
                    results["synced"] += 1
                    _sync_status.synced_notes += 1

            # Update last sync time after full sync
            await self._update_last_sync_time()

            logger.info(
                f"Full sync complete: {results['synced']} synced, {results['failed']} failed"
            )

            # Update status with result (exclude errors list for cleaner status)
            _sync_status.last_result = {
                "synced": results["synced"],
                "failed": results["failed"],
                "total": results["total"],
            }
            _sync_status.last_completed_at = datetime.now(timezone.utc)

            return results

        except Exception as e:
            _sync_status.last_error = str(e)
            logger.error(f"Full sync failed: {e}")
            raise
        finally:
            _sync_status.is_running = False
            _sync_status.sync_type = None

