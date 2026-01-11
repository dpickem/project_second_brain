"""
Vault API Router

Exposes vault operations to the frontend and external systems via REST API.
Provides endpoints for:
- Vault status and statistics
- Structure initialization (idempotent)
- Folder index regeneration
- Daily note creation
- Quick inbox capture
- Full vault sync to Neo4j
- Note browsing and content retrieval
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from pathlib import Path
import logging
import os

from app.services.obsidian.vault import get_vault_manager, VaultManager
from app.services.obsidian.indexer import FolderIndexer
from app.services.obsidian.daily import DailyNoteGenerator
from app.services.obsidian.sync import VaultSyncService, get_sync_status
from app.services.obsidian.lifecycle import get_watcher_status
from app.services.obsidian.frontmatter import parse_frontmatter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault"])


class DailyNoteRequest(BaseModel):
    date: Optional[str] = None  # ISO format: YYYY-MM-DD


class InboxItemRequest(BaseModel):
    item: str
    date: Optional[str] = None


class NoteInfo(BaseModel):
    """Summary info for a note in the vault."""

    path: str  # Relative path from vault root
    name: str  # File name without extension
    folder: str  # Parent folder
    modified: datetime  # Last modified time
    size: int  # File size in bytes
    title: Optional[str] = None  # Title from frontmatter
    tags: List[str] = []  # Tags from frontmatter
    content_type: Optional[str] = None  # Content type if detected


class NoteContent(BaseModel):
    """Full note content with metadata."""

    path: str
    name: str
    content: str  # Full markdown content
    frontmatter: dict = {}  # Parsed frontmatter
    modified: datetime
    size: int


class NotesListResponse(BaseModel):
    """Paginated list of notes."""

    notes: List[NoteInfo]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("/status")
async def get_vault_status():
    """Get vault status and statistics."""
    try:
        vault = get_vault_manager()
        stats = await vault.get_vault_stats()
        watcher_status = get_watcher_status()
        return {
            "status": "healthy",
            "vault_path": str(vault.vault_path),
            "exists": vault.vault_path.exists(),
            **stats,
            **watcher_status,
        }
    except ValueError as e:
        # Vault path doesn't exist
        return {
            "status": "not_configured",
            "error": str(e),
            "vault_path": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-structure")
async def ensure_vault_structure():
    """Ensure vault folder structure exists (idempotent).

    Creates any missing folders. Safe to call multiple times.
    """
    try:
        vault = get_vault_manager()
        result = await vault.ensure_structure()
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indices/regenerate")
async def regenerate_indices(background_tasks: BackgroundTasks):
    """Regenerate all folder indices."""
    try:
        vault = get_vault_manager()
        indexer = FolderIndexer(vault)

        # Run in background for large vaults
        background_tasks.add_task(indexer.regenerate_all_indices)

        return {"status": "regenerating", "message": "Index regeneration started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily")
async def create_daily_note(request: DailyNoteRequest = None):
    """Create a daily note."""
    try:
        vault = get_vault_manager()
        daily_gen = DailyNoteGenerator(vault)

        target_date = None
        if request and request.date:
            try:
                target_date = date.fromisoformat(request.date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )

        path = await daily_gen.generate_daily_note(target_date)
        return {"status": "created", "path": path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/inbox")
async def add_inbox_item(request: InboxItemRequest):
    """Add an item to today's daily note inbox."""
    if not request.item:
        raise HTTPException(status_code=400, detail="Item cannot be empty")

    try:
        vault = get_vault_manager()
        daily_gen = DailyNoteGenerator(vault)

        target_date = date.today()
        if request.date:
            try:
                target_date = date.fromisoformat(request.date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )

        await daily_gen.add_inbox_item(target_date, request.item)
        return {"status": "added", "date": target_date.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_vault_to_neo4j(background_tasks: BackgroundTasks):
    """Sync entire vault to Neo4j (runs in background)."""
    try:
        vault = get_vault_manager()
        sync_service = VaultSyncService()

        background_tasks.add_task(sync_service.full_sync, vault.vault_path)

        return {"status": "syncing", "message": "Full vault sync started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders")
async def list_folders():
    """List all content type folders in the vault."""
    from app.content_types import content_registry

    try:
        vault = get_vault_manager()
        folders = []
        total_notes = 0

        all_types = content_registry.get_all_types()
        for type_key, type_config in all_types.items():
            folder = type_config.get("folder")
            if folder:
                folder_path = vault.vault_path / folder
                # Count markdown files in this folder
                note_count = 0
                if folder_path.exists():
                    note_count = sum(
                        1
                        for f in folder_path.rglob("*.md")
                        if not any(part.startswith(".") for part in f.parts)
                    )
                total_notes += note_count
                folders.append(
                    {
                        "type": type_key,
                        "folder": folder,
                        "exists": folder_path.exists(),
                        "icon": type_config.get("icon", "📄"),
                        "note_count": note_count,
                    }
                )

        return {"folders": folders, "total_notes": total_notes}
    except ValueError as e:
        return {"folders": [], "total_notes": 0, "error": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watcher/status")
async def get_vault_watcher_status():
    """Get the current status of the vault file watcher."""
    return get_watcher_status()


@router.get("/sync/status")
async def get_vault_sync_status():
    """Get the current status of vault-to-Neo4j sync.

    Returns:
        - is_running: Whether a sync is currently in progress
        - sync_type: Type of sync ("full" or "reconciliation")
        - progress: Current progress (total, processed, synced, failed, percent)
        - last_result: Result of the last completed sync
        - last_completed_at: When the last sync completed
        - last_error: Error message if the last sync failed
    """
    sync_status = get_sync_status()

    # Also get last sync time from database
    sync_service = VaultSyncService()
    last_sync_time = await sync_service._get_last_sync_time()

    return {
        **sync_status,
        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
    }


# =============================================================================
# Note Browsing Endpoints
# =============================================================================


@router.get("/notes", response_model=NotesListResponse)
async def list_notes(
    folder: Optional[str] = Query(None, description="Filter by folder path"),
    search: Optional[str] = Query(None, description="Search in file names"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Notes per page"),
    sort_by: str = Query("modified", description="Sort by: modified, name, size"),
    sort_desc: bool = Query(True, description="Sort descending"),
):
    """List notes in the vault with filtering and pagination.

    Scans the vault for markdown files and returns metadata.
    Supports filtering by folder, search term, tag, and content type.
    """
    try:
        vault = get_vault_manager()
        vault_path = vault.vault_path

        if not vault_path.exists():
            raise HTTPException(status_code=404, detail="Vault not found")

        # Collect all markdown files
        notes = []
        search_path = vault_path / folder if folder else vault_path

        if not search_path.exists():
            return NotesListResponse(
                notes=[], total=0, page=page, page_size=page_size, has_more=False
            )

        for md_file in search_path.rglob("*.md"):
            # Skip hidden files and folders
            if any(part.startswith(".") for part in md_file.parts):
                continue

            rel_path = md_file.relative_to(vault_path)

            # Get file stats
            stat = md_file.stat()

            # Try to parse frontmatter for metadata
            note_title = None
            note_tags = []
            note_content_type = None

            try:
                content = md_file.read_text(encoding="utf-8")
                fm, _ = parse_frontmatter(content)
                if fm:
                    note_title = fm.get("title")
                    note_tags = fm.get("tags", [])
                    if isinstance(note_tags, str):
                        note_tags = [note_tags]
                    note_content_type = fm.get("type") or fm.get("content_type")
            except Exception:
                pass  # Skip frontmatter parsing errors

            # Apply search filter - check file name, title, and path
            # Match if ANY significant search word appears in the searchable text
            if search:
                search_lower = search.lower()
                searchable_text = (
                    f"{md_file.stem} {note_title or ''} {str(rel_path)}".lower()
                )

                # Check if the full search term matches anywhere
                full_match = search_lower in searchable_text

                # Also check if ANY significant word matches (for fuzzy matching)
                search_words = [w for w in search_lower.split() if len(w) > 2]
                any_word_match = search_words and any(
                    word in searchable_text for word in search_words
                )

                if not (full_match or any_word_match):
                    continue

            # Apply tag filter
            if tag and tag not in note_tags:
                continue

            # Apply content type filter
            if content_type and note_content_type != content_type:
                continue

            notes.append(
                NoteInfo(
                    path=str(rel_path),
                    name=md_file.stem,
                    folder=str(rel_path.parent) if rel_path.parent != Path(".") else "",
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    size=stat.st_size,
                    title=note_title,
                    tags=note_tags,
                    content_type=note_content_type,
                )
            )

        # Sort notes
        if sort_by == "modified":
            notes.sort(key=lambda n: n.modified, reverse=sort_desc)
        elif sort_by == "name":
            notes.sort(key=lambda n: n.name.lower(), reverse=sort_desc)
        elif sort_by == "size":
            notes.sort(key=lambda n: n.size, reverse=sort_desc)

        # Paginate
        total = len(notes)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_notes = notes[start:end]

        return NotesListResponse(
            notes=paginated_notes,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{note_path:path}", response_model=NoteContent)
async def get_note(note_path: str):
    """Get the full content of a specific note.

    Args:
        note_path: Relative path to the note from vault root (e.g., "papers/my-paper.md")

    Returns:
        Full note content with parsed frontmatter.
    """
    try:
        vault = get_vault_manager()
        vault_path = vault.vault_path

        # Ensure path ends with .md
        if not note_path.endswith(".md"):
            note_path = note_path + ".md"

        file_path = vault_path / note_path

        # Security: Ensure path is within vault
        try:
            file_path.resolve().relative_to(vault_path.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Note not found")

        # Read file
        content = file_path.read_text(encoding="utf-8")
        stat = file_path.stat()

        # Parse frontmatter and extract body content (without frontmatter)
        body_content = content
        frontmatter = {}
        try:
            fm, body = await parse_frontmatter(content)
            if fm:
                frontmatter = fm
                body_content = body
        except Exception:
            pass

        return NoteContent(
            path=note_path,
            name=file_path.stem,
            content=body_content,
            frontmatter=frontmatter,
            modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading note {note_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
