"""
Unit Tests for Vault Sync Service

Tests for the VaultSyncService class which synchronizes vault content
with the Neo4j knowledge graph.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.obsidian.sync import (
    VaultSyncService,
    SyncStatus,
    get_sync_status,
    _sync_status,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_sync_status():
    """Reset global sync status before each test."""
    global _sync_status
    _sync_status.is_running = False
    _sync_status.sync_type = None
    _sync_status.started_at = None
    _sync_status.total_notes = 0
    _sync_status.processed_notes = 0
    _sync_status.synced_notes = 0
    _sync_status.failed_notes = 0
    _sync_status.last_result = None
    _sync_status.last_completed_at = None
    _sync_status.last_error = None
    yield


@pytest.fixture
def sync_service() -> VaultSyncService:
    """Create a VaultSyncService instance."""
    return VaultSyncService()


@pytest.fixture
def mock_neo4j():
    """Create a mock Neo4j client."""
    mock = MagicMock()
    mock.merge_note_node = AsyncMock()
    mock.sync_note_links = AsyncMock()
    return mock


# ============================================================================
# SyncStatus Tests
# ============================================================================


class TestSyncStatus:
    """Tests for SyncStatus dataclass."""

    def test_default_values(self):
        """SyncStatus has sensible defaults."""
        status = SyncStatus()
        assert status.is_running is False
        assert status.sync_type is None
        assert status.total_notes == 0
        assert status.last_result is None

    def test_to_dict(self):
        """to_dict produces correct structure."""
        status = SyncStatus(
            is_running=True,
            sync_type="full",
            total_notes=100,
            processed_notes=50,
            synced_notes=48,
            failed_notes=2,
        )
        result = status.to_dict()

        assert result["is_running"] is True
        assert result["sync_type"] == "full"
        assert result["progress"]["total"] == 100
        assert result["progress"]["processed"] == 50
        assert result["progress"]["percent"] == 50.0

    def test_to_dict_percent_zero_total(self):
        """to_dict handles zero total notes."""
        status = SyncStatus(total_notes=0)
        result = status.to_dict()
        assert result["progress"]["percent"] == 0

    def test_to_dict_with_timestamps(self):
        """to_dict formats timestamps correctly."""
        now = datetime.now(timezone.utc)
        status = SyncStatus(started_at=now, last_completed_at=now)
        result = status.to_dict()

        assert result["started_at"] == now.isoformat()
        assert result["last_completed_at"] == now.isoformat()

    def test_to_dict_none_timestamps(self):
        """to_dict handles None timestamps."""
        status = SyncStatus()
        result = status.to_dict()

        assert result["started_at"] is None
        assert result["last_completed_at"] is None


class TestGetSyncStatus:
    """Tests for get_sync_status function."""

    def test_get_sync_status_returns_dict(self):
        """get_sync_status returns dictionary."""
        result = get_sync_status()
        assert isinstance(result, dict)
        assert "is_running" in result
        assert "progress" in result


# ============================================================================
# VaultSyncService Initialization Tests
# ============================================================================


class TestVaultSyncServiceInit:
    """Tests for VaultSyncService initialization."""

    def test_init(self):
        """VaultSyncService initializes correctly."""
        service = VaultSyncService()
        assert service._neo4j is None

    def test_last_sync_key_constant(self, sync_service: VaultSyncService):
        """LAST_SYNC_KEY is correct."""
        assert sync_service.LAST_SYNC_KEY == "vault_last_sync_time"


# ============================================================================
# Sync Note Tests
# ============================================================================


class TestSyncNote:
    """Tests for sync_note method."""

    @pytest.mark.asyncio
    async def test_sync_note_success(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """sync_note successfully syncs a note."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
title: Test Note
type: paper
tags:
  - ai
  - ml
---

# Content

See [[Other Note]] for more.
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="test-uuid"),
            ):
                result = await sync_service.sync_note(note_path)

        assert "error" not in result
        assert result["path"] == str(note_path)
        assert result["links_synced"] == 1
        assert "ai" in result["tags"]
        mock_neo4j.merge_note_node.assert_called_once()
        mock_neo4j.sync_note_links.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_note_uses_frontmatter_id(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """sync_note uses existing frontmatter ID."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
id: existing-id-12345
title: Test Note
type: paper
---

Content
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            result = await sync_service.sync_note(note_path)

        assert result["node_id"] == "existing-id-12345"

    @pytest.mark.asyncio
    async def test_sync_note_generates_id_if_missing(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """sync_note generates ID if not in frontmatter."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
title: Test Note
---

Content
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="generated-uuid"),
            ) as mock_gen:
                result = await sync_service.sync_note(note_path)

        mock_gen.assert_called_once_with(note_path)
        assert result["node_id"] == "generated-uuid"

    @pytest.mark.asyncio
    async def test_sync_note_extracts_inline_tags(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """sync_note extracts inline tags and merges with frontmatter."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
title: Test Note
tags:
  - frontmatter-tag
---

Content about #inline-tag and #another-tag
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                result = await sync_service.sync_note(note_path)

        assert "frontmatter-tag" in result["tags"]
        assert "inline-tag" in result["tags"]
        assert "another-tag" in result["tags"]

    @pytest.mark.asyncio
    async def test_sync_note_handles_string_tags(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """sync_note handles tags as string instead of list."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
title: Test Note
tags: single-tag
---

Content
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                result = await sync_service.sync_note(note_path)

        assert "single-tag" in result["tags"]

    @pytest.mark.asyncio
    async def test_sync_note_without_neo4j(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """sync_note completes even when Neo4j is unavailable."""
        note_path = temp_vault / "test.md"
        note_path.write_text(
            """---
title: Test Note
---

Content
"""
        )

        with patch.object(sync_service, "_ensure_neo4j", AsyncMock(return_value=None)):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                result = await sync_service.sync_note(note_path)

        # Should succeed without Neo4j
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_sync_note_error_handling(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """sync_note returns error dict on failure."""
        note_path = temp_vault / "nonexistent.md"

        result = await sync_service.sync_note(note_path)

        assert "error" in result
        assert result["path"] == str(note_path)


# ============================================================================
# Full Sync Tests
# ============================================================================


class TestFullSync:
    """Tests for full_sync method."""

    @pytest.mark.asyncio
    async def test_full_sync_success(
        self, sync_service: VaultSyncService, tmp_path: Path, mock_neo4j
    ):
        """full_sync syncs all notes in vault."""
        # Create a clean vault (not temp_vault which has templates with invalid YAML)
        vault = tmp_path / "sync_test_vault"
        vault.mkdir()
        concepts = vault / "concepts"
        concepts.mkdir()
        (concepts / "Note1.md").write_text("---\ntitle: Note 1\n---\nContent")
        (concepts / "Note2.md").write_text("---\ntitle: Note 2\n---\nContent")

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    result = await sync_service.full_sync(vault)

        assert result["synced"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_full_sync_excludes_obsidian_folder(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """full_sync excludes .obsidian directory."""
        # Create note in .obsidian (should be excluded)
        obsidian = temp_vault / ".obsidian"
        (obsidian / "config.md").write_text("---\ntype: config\n---\n")

        # Create regular note
        (temp_vault / "concepts" / "Note.md").write_text("---\ntitle: Note\n---\n")

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    result = await sync_service.full_sync(temp_vault)

        # Should not include .obsidian/config.md
        # total should not count .obsidian files
        assert ".obsidian" not in str(result.get("errors", []))

    @pytest.mark.asyncio
    async def test_full_sync_updates_status(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """full_sync updates global status during execution."""
        (temp_vault / "concepts" / "Note.md").write_text("---\ntitle: Note\n---\n")

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="uuid"),
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    await sync_service.full_sync(temp_vault)

        # After completion, status should be updated
        status = get_sync_status()
        assert status["is_running"] is False
        assert status["last_result"] is not None

    @pytest.mark.asyncio
    async def test_full_sync_prevents_concurrent_runs(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """full_sync returns error if already running."""
        global _sync_status
        _sync_status.is_running = True
        _sync_status.sync_type = "full"

        result = await sync_service.full_sync(temp_vault)

        assert "error" in result
        assert "already in progress" in result["error"]


# ============================================================================
# Reconcile on Startup Tests
# ============================================================================


class TestReconcileOnStartup:
    """Tests for reconcile_on_startup method."""

    @pytest.mark.asyncio
    async def test_reconcile_first_run(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """First run syncs all notes (no last_sync_time)."""
        (temp_vault / "concepts" / "Note1.md").write_text("---\ntitle: Note 1\n---\n")
        (temp_vault / "concepts" / "Note2.md").write_text("---\ntitle: Note 2\n---\n")

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service,
                    "_generate_and_persist_node_id",
                    AsyncMock(return_value="uuid"),
                ):
                    with patch.object(
                        sync_service, "_update_last_sync_time", AsyncMock()
                    ):
                        result = await sync_service.reconcile_on_startup(temp_vault)

        # All notes should be considered modified
        assert result["modified_since_sync"] >= 2
        assert result["last_sync"] is None

    @pytest.mark.asyncio
    async def test_reconcile_syncs_only_modified(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """Reconciliation only syncs notes modified after last_sync."""
        # Create notes
        concepts = temp_vault / "concepts"
        note1 = concepts / "Note1.md"
        note1.write_text("---\ntitle: Note 1\n---\n")

        # Set last sync to future to make all notes "old"
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=future)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    result = await sync_service.reconcile_on_startup(temp_vault)

        # No notes should be modified since last_sync is in future
        assert result["modified_since_sync"] == 0

    @pytest.mark.asyncio
    async def test_reconcile_updates_status(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j
    ):
        """Reconciliation updates global status."""
        (temp_vault / "concepts" / "Note.md").write_text("---\ntitle: Note\n---\n")

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j)
            ):
                with patch.object(
                    sync_service,
                    "_generate_and_persist_node_id",
                    AsyncMock(return_value="uuid"),
                ):
                    with patch.object(
                        sync_service, "_update_last_sync_time", AsyncMock()
                    ):
                        await sync_service.reconcile_on_startup(temp_vault)

        status = get_sync_status()
        assert status["is_running"] is False
        assert status["last_result"] is not None


# ============================================================================
# Generate Node ID Tests
# ============================================================================


class TestGenerateNodeId:
    """Tests for _generate_and_persist_node_id method."""

    @pytest.mark.asyncio
    async def test_generate_deterministic_id(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """Generated ID is deterministic based on path."""
        note_path = temp_vault / "test.md"
        note_path.write_text("---\ntitle: Test\n---\n")

        with patch("app.services.obsidian.sync.update_frontmatter", AsyncMock()):
            id1 = await sync_service._generate_and_persist_node_id(note_path)
            id2 = await sync_service._generate_and_persist_node_id(note_path)

        assert id1 == id2

    @pytest.mark.asyncio
    async def test_generate_persists_to_frontmatter(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """Generated ID is written to frontmatter."""
        note_path = temp_vault / "test.md"
        note_path.write_text("---\ntitle: Test\n---\n")

        with patch(
            "app.services.obsidian.sync.update_frontmatter", AsyncMock()
        ) as mock_update:
            node_id = await sync_service._generate_and_persist_node_id(note_path)

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == note_path
        assert call_args[0][1]["id"] == node_id


# ============================================================================
# Neo4j Client Tests
# ============================================================================


class TestEnsureNeo4j:
    """Tests for _ensure_neo4j method."""

    @pytest.mark.asyncio
    async def test_ensure_neo4j_caches_client(
        self, sync_service: VaultSyncService, mock_neo4j
    ):
        """_ensure_neo4j caches the client."""
        with patch(
            "app.services.obsidian.sync.get_neo4j_client",
            AsyncMock(return_value=mock_neo4j),
        ):
            client1 = await sync_service._ensure_neo4j()
            client2 = await sync_service._ensure_neo4j()

        assert client1 is client2
        assert client1 is mock_neo4j

    @pytest.mark.asyncio
    async def test_ensure_neo4j_handles_connection_error(
        self, sync_service: VaultSyncService
    ):
        """_ensure_neo4j returns None on connection error."""
        with patch(
            "app.services.obsidian.sync.get_neo4j_client",
            AsyncMock(side_effect=Exception("Connection refused")),
        ):
            client = await sync_service._ensure_neo4j()

        assert client is None
