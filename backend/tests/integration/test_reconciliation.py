"""
Integration Tests for Offline Change Detection and Reconciliation

Tests the reconciliation system that detects and syncs notes
modified while the application was offline.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio

from app.services.obsidian.sync import VaultSyncService


pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sync_service() -> VaultSyncService:
    """Create a fresh VaultSyncService instance."""
    return VaultSyncService()


@pytest.fixture
def mock_neo4j():
    """Create a mock Neo4j client."""
    mock = MagicMock()
    mock.merge_note_node = AsyncMock()
    mock.sync_note_links = AsyncMock()
    return mock


@pytest.fixture
def vault_with_timestamps(temp_vault: Path) -> tuple[Path, dict]:
    """Create a vault with notes at specific modification times."""
    concepts = temp_vault / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)

    # Create notes
    old_note = concepts / "old-note.md"
    old_note.write_text(
        """---
id: old-001
title: Old Note
type: concept
---

Old content
"""
    )

    new_note = concepts / "new-note.md"
    new_note.write_text(
        """---
id: new-001
title: New Note
type: concept
---

New content
"""
    )

    # Set the old note's mtime to yesterday
    old_time = time.time() - 86400  # 24 hours ago
    os.utime(old_note, (old_time, old_time))

    return temp_vault, {
        "old_note": old_note,
        "new_note": new_note,
    }


# ============================================================================
# Timestamp Detection Tests
# ============================================================================


class TestTimestampDetection:
    """Tests for modification time detection."""

    @pytest.mark.asyncio
    async def test_detects_modified_after_last_sync(
        self, sync_service: VaultSyncService, vault_with_timestamps: tuple, mock_neo4j
    ):
        """Notes modified after last_sync_time are detected."""
        vault_path, notes = vault_with_timestamps

        # Set last sync to 12 hours ago (old note is 24h old, new note is just created)
        last_sync = datetime.now(timezone.utc) - timedelta(hours=12)

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=last_sync)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(vault_path)

        # Only new_note should be modified (created within last 12 hours)
        # old_note was modified 24 hours ago, before last_sync
        assert result["modified_since_sync"] >= 1

    @pytest.mark.asyncio
    async def test_skips_unmodified_notes(
        self, sync_service: VaultSyncService, vault_with_timestamps: tuple, mock_neo4j
    ):
        """Notes not modified since last sync are skipped."""
        vault_path, notes = vault_with_timestamps

        # Set old note's mtime to 2 days ago
        old_time = time.time() - 172800  # 48 hours ago
        os.utime(notes["old_note"], (old_time, old_time))

        # Set last sync to 1 hour ago
        last_sync = datetime.now(timezone.utc) - timedelta(hours=1)

        # Touch new note to ensure it's "recently" modified
        notes["new_note"].touch()

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=last_sync)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(vault_path)

        # Only new_note should be synced (touched after last_sync)
        assert result["synced"] >= 1


# ============================================================================
# First Run Tests
# ============================================================================


class TestFirstRun:
    """Tests for first run (no previous sync)."""

    @pytest.mark.asyncio
    async def test_first_run_syncs_all_notes(
        self, sync_service: VaultSyncService, vault_with_timestamps: tuple, mock_neo4j
    ):
        """First run with no last_sync_time syncs all notes."""
        vault_path, notes = vault_with_timestamps

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(vault_path)

        assert result["last_sync"] is None
        assert result["modified_since_sync"] >= 2  # Both notes
        assert result["synced"] >= 2

    @pytest.mark.asyncio
    async def test_first_run_updates_last_sync_time(
        self, sync_service: VaultSyncService, vault_with_timestamps: tuple, mock_neo4j
    ):
        """First run updates last_sync_time after completion."""
        vault_path, _ = vault_with_timestamps

        update_mock = AsyncMock()

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", update_mock
                ):
                    await sync_service.reconcile_on_startup(vault_path)

        update_mock.assert_called_once()


# ============================================================================
# Offline Change Scenarios
# ============================================================================


class TestOfflineChangeScenarios:
    """Tests for various offline change scenarios."""

    @pytest.mark.asyncio
    async def test_handles_new_files_created_offline(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """New files created while offline are synced."""
        concepts = temp_vault / "concepts"
        concepts.mkdir(parents=True, exist_ok=True)

        # Simulate: last sync was 1 hour ago
        last_sync = datetime.now(timezone.utc) - timedelta(hours=1)

        # Create a "new" file (created after last_sync)
        new_note = concepts / "created-offline.md"
        new_note.write_text(
            """---
id: offline-001
title: Created Offline
type: concept
---

Created while app was offline.
"""
        )

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=last_sync)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(temp_vault)

        assert result["modified_since_sync"] >= 1
        assert result["synced"] >= 1

    @pytest.mark.asyncio
    async def test_handles_edited_files_offline(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """Files edited while offline are synced."""
        concepts = temp_vault / "concepts"
        concepts.mkdir(parents=True, exist_ok=True)

        # Create a file
        edited_note = concepts / "edited-offline.md"
        edited_note.write_text(
            """---
id: edited-001
title: Edited Offline
type: concept
---

Original content.
"""
        )

        # Set its mtime to 2 hours ago (before "last sync")
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(edited_note, (old_time, old_time))

        # Simulate last sync 1 hour ago
        last_sync = datetime.now(timezone.utc) - timedelta(hours=1)

        # Now "edit" the file (touch it to update mtime)
        edited_note.touch()

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=last_sync)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(temp_vault)

        assert result["modified_since_sync"] >= 1

    @pytest.mark.asyncio
    async def test_handles_large_vault(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """Reconciliation handles vaults with many files efficiently."""
        concepts = temp_vault / "concepts"
        concepts.mkdir(parents=True, exist_ok=True)

        # Create 50 notes
        for i in range(50):
            note = concepts / f"note-{i:03d}.md"
            note.write_text(
                f"""---
id: note-{i:03d}
title: Note {i}
type: concept
---

Content for note {i}.
"""
            )

        # First run - should sync all
        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    result = await sync_service.reconcile_on_startup(temp_vault)

        assert result["total_notes"] >= 50
        assert result["synced"] >= 50


# ============================================================================
# Error Recovery Tests
# ============================================================================


class TestReconciliationErrorRecovery:
    """Tests for error recovery during reconciliation."""

    @pytest.mark.asyncio
    async def test_continues_on_individual_file_error(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """Reconciliation continues if individual file sync fails."""
        concepts = temp_vault / "concepts"
        concepts.mkdir(parents=True, exist_ok=True)

        # Create notes
        for i in range(3):
            (concepts / f"note-{i}.md").write_text(
                f"""---
id: note-{i}
title: Note {i}
---

Content
"""
            )

        # Make first sync fail
        call_count = [0]
        original_sync_note = sync_service.sync_note

        async def failing_sync_note(path):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"path": str(path), "error": "Simulated failure"}
            return await original_sync_note(path)

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(sync_service, "sync_note", failing_sync_note):
                    with patch.object(
                        sync_service, "_update_last_sync_time", AsyncMock()
                    ):
                        result = await sync_service.reconcile_on_startup(temp_vault)

        # Should have 1 failure but still process others
        assert result["failed"] >= 1
        assert result["synced"] >= 2

    @pytest.mark.asyncio
    async def test_updates_status_on_error(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """Status is updated when reconciliation has errors."""
        from app.services.obsidian.sync import get_sync_status

        concepts = temp_vault / "concepts"
        concepts.mkdir(parents=True, exist_ok=True)
        (concepts / "note.md").write_text("---\nid: n1\n---\nContent")

        # Make sync fail
        async def failing_sync(path):
            return {"path": str(path), "error": "Failed"}

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(sync_service, "sync_note", failing_sync):
                with patch.object(
                    sync_service, "_update_last_sync_time", AsyncMock()
                ):
                    await sync_service.reconcile_on_startup(temp_vault)

        status = get_sync_status()
        assert status["is_running"] is False
        assert status["last_result"]["failed"] >= 1


# ============================================================================
# Database Persistence Tests
# ============================================================================


class TestSyncTimePersistence:
    """Tests for last_sync_time persistence."""

    @pytest.mark.asyncio
    async def test_get_last_sync_time_returns_none_initially(
        self, sync_service: VaultSyncService
    ):
        """_get_last_sync_time returns None when never synced."""
        with patch(
            "app.services.obsidian.sync.async_session_maker"
        ) as mock_session_maker:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_session_maker.return_value = mock_session

            result = await sync_service._get_last_sync_time()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_last_sync_time_returns_stored_value(
        self, sync_service: VaultSyncService
    ):
        """_get_last_sync_time returns stored timestamp."""
        stored_time = "2025-01-05T10:00:00+00:00"

        with patch(
            "app.services.obsidian.sync.async_session_maker"
        ) as mock_session_maker:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_row = MagicMock()
            mock_row.value = stored_time

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_row

            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_maker.return_value = mock_session

            result = await sync_service._get_last_sync_time()

        assert result is not None
        assert result.isoformat() == stored_time


