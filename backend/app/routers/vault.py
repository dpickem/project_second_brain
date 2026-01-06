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
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pathlib import Path
import logging

from app.services.obsidian.vault import get_vault_manager, VaultManager
from app.services.obsidian.indexer import FolderIndexer
from app.services.obsidian.daily import DailyNoteGenerator
from app.services.obsidian.sync import VaultSyncService, get_sync_status
from app.services.obsidian.lifecycle import get_watcher_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault"])


class DailyNoteRequest(BaseModel):
    date: Optional[str] = None  # ISO format: YYYY-MM-DD


class InboxItemRequest(BaseModel):
    item: str
    date: Optional[str] = None


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

        all_types = content_registry.get_all_types()
        for type_key, type_config in all_types.items():
            folder = type_config.get("folder")
            if folder:
                folder_path = vault.vault_path / folder
                folders.append(
                    {
                        "type": type_key,
                        "folder": folder,
                        "exists": folder_path.exists(),
                        "icon": type_config.get("icon", "📄"),
                    }
                )

        return {"folders": folders}
    except ValueError as e:
        return {"folders": [], "error": str(e)}
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

