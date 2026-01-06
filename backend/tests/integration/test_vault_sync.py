"""
Integration Tests for Vault Sync with Neo4j

Tests the full synchronization flow between the Obsidian vault
and the Neo4j knowledge graph.

These tests require a running Neo4j instance.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.services.obsidian.sync import VaultSyncService, get_sync_status


# Skip all tests if Neo4j is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("NEO4J_URI"),
        reason="NEO4J_URI not set - Neo4j not available",
    ),
]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sync_service() -> VaultSyncService:
    """Create a fresh VaultSyncService instance."""
    return VaultSyncService()


@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client for testing without real Neo4j."""
    mock = MagicMock()
    mock.merge_note_node = AsyncMock()
    mock.sync_note_links = AsyncMock()
    mock.delete_note_links = AsyncMock()
    mock.get_note_by_id = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def vault_with_notes(temp_vault: Path) -> Path:
    """Create a temp vault with sample notes for testing."""
    # Create a paper note
    papers = temp_vault / "sources/papers"
    papers.mkdir(parents=True, exist_ok=True)
    (papers / "ml-paper.md").write_text(
        """---
id: paper-001
title: "Introduction to Machine Learning"
type: paper
tags:
  - ml
  - ai
authors:
  - John Doe
---

# Introduction to Machine Learning

This paper covers the basics of [[Neural Networks]] and [[Gradient Descent]].

## Key Concepts

- Supervised learning
- Unsupervised learning
- Reinforcement learning #reinforcement-learning

See [[Deep Learning]] for more advanced topics.
"""
    )

    # Create a concept note
    concepts = temp_vault / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)
    (concepts / "neural-networks.md").write_text(
        """---
id: concept-001
title: Neural Networks
type: concept
tags:
  - ml
  - ai
domain: machine-learning
---

# Neural Networks

Neural networks are computing systems inspired by biological neural networks.

Related: [[Backpropagation]], [[Activation Functions]]
"""
    )

    return temp_vault


# ============================================================================
# Single Note Sync Tests
# ============================================================================


class TestSingleNoteSync:
    """Tests for syncing individual notes to Neo4j."""

    @pytest.mark.asyncio
    async def test_sync_note_creates_node(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Syncing a note creates a Neo4j node with correct properties."""
        note_path = vault_with_notes / "sources/papers/ml-paper.md"

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            result = await sync_service.sync_note(note_path)

        assert "error" not in result
        assert result["node_id"] == "paper-001"

        # Verify merge_note_node was called with correct args
        mock_neo4j_client.merge_note_node.assert_called_once()
        call_kwargs = mock_neo4j_client.merge_note_node.call_args[1]
        assert call_kwargs["node_id"] == "paper-001"
        assert call_kwargs["title"] == "Introduction to Machine Learning"
        assert call_kwargs["note_type"] == "paper"
        assert "ml" in call_kwargs["tags"]

    @pytest.mark.asyncio
    async def test_sync_note_creates_links(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Syncing a note creates LINKS_TO relationships for wikilinks."""
        note_path = vault_with_notes / "sources/papers/ml-paper.md"

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            result = await sync_service.sync_note(note_path)

        # Should have extracted 4 wikilinks
        assert (
            result["links_synced"] >= 3
        )  # Neural Networks, Gradient Descent, Deep Learning (Backpropagation may or may not be linked)

        # Verify sync_note_links was called
        mock_neo4j_client.sync_note_links.assert_called_once()
        call_args = mock_neo4j_client.sync_note_links.call_args[0]
        assert call_args[0] == "paper-001"  # source_id
        # Targets should include the wikilinks
        targets = call_args[1]
        assert "Neural Networks" in targets
        assert "Gradient Descent" in targets
        assert "Deep Learning" in targets

    @pytest.mark.asyncio
    async def test_sync_note_merges_inline_tags(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Inline #tags are merged with frontmatter tags."""
        note_path = vault_with_notes / "sources/papers/ml-paper.md"

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            result = await sync_service.sync_note(note_path)

        # Should have both frontmatter tags and inline tags
        assert "ml" in result["tags"]  # from frontmatter
        assert "ai" in result["tags"]  # from frontmatter
        assert "reinforcement-learning" in result["tags"]  # inline

    @pytest.mark.asyncio
    async def test_sync_note_handles_missing_frontmatter(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j_client
    ):
        """Notes without frontmatter are handled gracefully."""
        note_path = temp_vault / "concepts" / "plain-note.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(
            """# Plain Note

This note has no frontmatter but links to [[Other Note]].
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            with patch.object(
                sync_service,
                "_generate_and_persist_node_id",
                AsyncMock(return_value="generated-id"),
            ):
                result = await sync_service.sync_note(note_path)

        assert "error" not in result
        assert result["node_id"] == "generated-id"
        assert result["links_synced"] == 1


# ============================================================================
# Full Sync Tests
# ============================================================================


class TestFullSync:
    """Tests for full vault synchronization."""

    @pytest.mark.asyncio
    async def test_full_sync_processes_all_notes(
        self, sync_service: VaultSyncService, tmp_path: Path, mock_neo4j_client
    ):
        """Full sync processes all markdown files in vault."""
        # Create a clean vault without templates (which have invalid YAML)
        vault = tmp_path / "clean_vault"
        vault.mkdir()
        (vault / "Note1.md").write_text("---\ntitle: Note 1\n---\nContent")
        (vault / "Note2.md").write_text("---\ntitle: Note 2\n---\nContent")

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                result = await sync_service.full_sync(vault)

        # Should have synced the two notes we created
        assert result["synced"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_full_sync_excludes_obsidian_config(
        self, sync_service: VaultSyncService, tmp_path: Path, mock_neo4j_client
    ):
        """Full sync excludes .obsidian configuration directory."""
        # Create a clean vault
        vault = tmp_path / "obsidian_test_vault"
        vault.mkdir()
        (vault / "Note.md").write_text("---\ntitle: Note\n---\nContent")

        # Create a markdown file in .obsidian (should be excluded)
        obsidian_dir = vault / ".obsidian"
        obsidian_dir.mkdir(exist_ok=True)
        (obsidian_dir / "config.md").write_text("---\ntype: config\n---\n")

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                result = await sync_service.full_sync(vault)

        # The .obsidian/config.md should not be in the total count
        assert result["synced"] == 1  # Only Note.md, not .obsidian/config.md
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_full_sync_continues_on_note_error(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Full sync continues processing even if a note fails."""
        # Make merge_note_node fail for first call, succeed for rest
        call_count = [0]

        async def mock_merge(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated error")

        mock_neo4j_client.merge_note_node = mock_merge

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                result = await sync_service.full_sync(vault_with_notes)

        # Should have one failure and continue with others
        assert result["failed"] >= 1
        assert result["synced"] >= 1

    @pytest.mark.asyncio
    async def test_full_sync_updates_status_progress(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Full sync updates status during processing."""
        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                await sync_service.full_sync(vault_with_notes)

        status = get_sync_status()
        assert status["is_running"] is False
        assert status["last_result"] is not None
        assert "synced" in status["last_result"]


# ============================================================================
# Reconciliation Tests
# ============================================================================


class TestReconciliation:
    """Tests for startup reconciliation."""

    @pytest.mark.asyncio
    async def test_reconcile_first_run_syncs_all(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """First run (no last_sync_time) syncs all notes."""
        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=None)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    result = await sync_service.reconcile_on_startup(vault_with_notes)

        assert result["last_sync"] is None
        assert result["modified_since_sync"] >= 2  # All notes are "new"
        assert result["synced"] >= 2

    @pytest.mark.asyncio
    async def test_reconcile_syncs_modified_only(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Reconciliation only syncs notes modified since last sync."""
        # Set last sync to now (no notes should be modified)
        recent_time = datetime.now(timezone.utc)

        with patch.object(
            sync_service, "_get_last_sync_time", AsyncMock(return_value=recent_time)
        ):
            with patch.object(
                sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
            ):
                with patch.object(sync_service, "_update_last_sync_time", AsyncMock()):
                    result = await sync_service.reconcile_on_startup(vault_with_notes)

        # Files were created before "recent_time" set, so should be 0
        assert result["modified_since_sync"] == 0
        assert result["synced"] == 0


# ============================================================================
# Link Sync Tests
# ============================================================================


class TestLinkSync:
    """Tests for wikilink relationship sync."""

    @pytest.mark.asyncio
    async def test_sync_creates_links_to_relationships(
        self, sync_service: VaultSyncService, vault_with_notes: Path, mock_neo4j_client
    ):
        """Wikilinks are converted to LINKS_TO relationships."""
        note_path = vault_with_notes / "concepts/neural-networks.md"

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            await sync_service.sync_note(note_path)

        # Check sync_note_links was called with correct targets
        call_args = mock_neo4j_client.sync_note_links.call_args[0]
        source_id = call_args[0]
        targets = call_args[1]

        assert source_id == "concept-001"
        assert "Backpropagation" in targets
        assert "Activation Functions" in targets

    @pytest.mark.asyncio
    async def test_sync_handles_notes_with_no_links(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j_client
    ):
        """Notes without wikilinks are synced correctly."""
        note_path = temp_vault / "concepts" / "no-links.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(
            """---
id: no-links-001
title: Note Without Links
type: concept
---

This note has no wikilinks at all.
"""
        )

        with patch.object(
            sync_service, "_ensure_neo4j", AsyncMock(return_value=mock_neo4j_client)
        ):
            result = await sync_service.sync_note(note_path)

        assert result["links_synced"] == 0
        # sync_note_links should still be called with empty list
        mock_neo4j_client.sync_note_links.assert_called_once_with("no-links-001", [])


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in sync operations."""

    @pytest.mark.asyncio
    async def test_sync_handles_neo4j_unavailable(
        self, sync_service: VaultSyncService, vault_with_notes: Path
    ):
        """Sync completes successfully when Neo4j is unavailable."""
        note_path = vault_with_notes / "sources/papers/ml-paper.md"

        with patch.object(sync_service, "_ensure_neo4j", AsyncMock(return_value=None)):
            result = await sync_service.sync_note(note_path)

        # Should succeed without Neo4j
        assert "error" not in result
        assert result["node_id"] == "paper-001"

    @pytest.mark.asyncio
    async def test_sync_handles_parse_error(
        self, sync_service: VaultSyncService, temp_vault: Path, mock_neo4j_client
    ):
        """Sync handles malformed frontmatter gracefully."""
        note_path = temp_vault / "concepts" / "malformed.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(
            """---
title: Malformed
tags: [unclosed list
---

Content
"""
        )

        result = await sync_service.sync_note(note_path)

        # Should return error result
        assert "error" in result
        assert result["path"] == str(note_path)

    @pytest.mark.asyncio
    async def test_sync_handles_nonexistent_file(
        self, sync_service: VaultSyncService, temp_vault: Path
    ):
        """Sync handles nonexistent file gracefully."""
        note_path = temp_vault / "nonexistent.md"

        result = await sync_service.sync_note(note_path)

        assert "error" in result
