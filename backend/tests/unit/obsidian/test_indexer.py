"""
Unit Tests for Folder Indexer

Tests for the FolderIndexer class which generates _index.md files
for vault folders.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.obsidian.indexer import FolderIndexer
from app.services.obsidian.vault import VaultManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def vault_manager(temp_vault: Path) -> VaultManager:
    """Create a VaultManager with a temporary vault."""
    return VaultManager(str(temp_vault))


@pytest.fixture
def indexer(vault_manager: VaultManager) -> FolderIndexer:
    """Create a FolderIndexer with the test vault manager."""
    return FolderIndexer(vault_manager)


# ============================================================================
# FolderIndexer Initialization Tests
# ============================================================================


class TestFolderIndexerInit:
    """Tests for FolderIndexer initialization."""

    def test_init(self, vault_manager: VaultManager):
        """FolderIndexer initializes with vault manager."""
        indexer = FolderIndexer(vault_manager)
        assert indexer.vault == vault_manager

    def test_index_filename_constant(self, indexer: FolderIndexer):
        """INDEX_FILENAME is _index.md."""
        assert indexer.INDEX_FILENAME == "_index.md"


# ============================================================================
# Generate Index Tests
# ============================================================================


class TestGenerateIndex:
    """Tests for generate_index method."""

    @pytest.mark.asyncio
    async def test_generate_empty_folder(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Empty folder gets placeholder index."""
        folder = temp_vault / "empty_folder"
        folder.mkdir()

        result = await indexer.generate_index(folder)

        assert result == str(folder / "_index.md")
        assert (folder / "_index.md").exists()
        content = (folder / "_index.md").read_text()
        assert "*No notes yet*" in content

    @pytest.mark.asyncio
    async def test_generate_with_notes(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Index includes links to notes."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        # Create test notes
        (folder / "Note One.md").write_text(
            """---
title: "Note One"
type: paper
processed: "2025-01-05"
---

Content
"""
        )
        (folder / "Note Two.md").write_text(
            """---
title: "Note Two"
type: paper
processed: "2025-01-04"
---

Content
"""
        )

        result = await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        assert "[[Note One]]" in content
        assert "[[Note Two]]" in content
        assert "*2 notes*" in content

    @pytest.mark.asyncio
    async def test_generate_excludes_underscore_files(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Files starting with underscore are excluded."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        (folder / "Regular.md").write_text("---\ntitle: Regular\n---\n")
        (folder / "_hidden.md").write_text("---\ntitle: Hidden\n---\n")

        await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        assert "[[Regular]]" in content
        assert "[[_hidden]]" not in content
        assert "*1 notes*" in content

    @pytest.mark.asyncio
    async def test_generate_sorts_by_processed_date(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Notes sorted by processed date, newest first."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        (folder / "Old.md").write_text(
            """---
title: "Old Note"
processed: "2025-01-01"
---
"""
        )
        (folder / "New.md").write_text(
            """---
title: "New Note"
processed: "2025-01-05"
---
"""
        )
        (folder / "Middle.md").write_text(
            """---
title: "Middle Note"
processed: "2025-01-03"
---
"""
        )

        await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        new_pos = content.find("[[New Note]]")
        middle_pos = content.find("[[Middle Note]]")
        old_pos = content.find("[[Old Note]]")
        assert new_pos < middle_pos < old_pos

    @pytest.mark.asyncio
    async def test_generate_recent_section_limit(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Recent section shows first 10 notes only."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        # Create 15 notes
        for i in range(15):
            (folder / f"Note{i:02d}.md").write_text(
                f"""---
title: "Note {i}"
processed: "2025-01-{i+1:02d}"
---
"""
            )

        await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        # Should have Recent section with 10 and All Notes section
        assert "## Recent" in content
        assert "## All Notes" in content

    @pytest.mark.asyncio
    async def test_generate_no_all_notes_when_under_10(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """No All Notes section when 10 or fewer notes."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        for i in range(5):
            (folder / f"Note{i}.md").write_text(
                f"""---
title: "Note {i}"
---
"""
            )

        await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        assert "## Recent" in content
        assert "## All Notes" not in content

    @pytest.mark.asyncio
    async def test_generate_handles_invalid_frontmatter(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Notes with invalid frontmatter are still indexed."""
        folder = temp_vault / "test_folder"
        folder.mkdir()

        (folder / "Valid.md").write_text("---\ntitle: Valid\n---\nContent")
        (folder / "Invalid.md").write_text("No frontmatter here")

        await indexer.generate_index(folder)

        content = (folder / "_index.md").read_text()
        assert "[[Valid]]" in content
        assert "[[Invalid]]" in content  # Uses filename as title

    @pytest.mark.asyncio
    async def test_generate_recursive(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Recursive mode includes notes from subfolders."""
        folder = temp_vault / "test_folder"
        subfolder = folder / "subfolder"
        subfolder.mkdir(parents=True)

        (folder / "Root.md").write_text("---\ntitle: Root\n---\n")
        (subfolder / "Sub.md").write_text("---\ntitle: Sub\n---\n")

        await indexer.generate_index(folder, recursive=True)

        content = (folder / "_index.md").read_text()
        assert "[[Root]]" in content
        assert "[[Sub]]" in content

    @pytest.mark.asyncio
    async def test_generate_non_recursive(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Non-recursive mode excludes notes from subfolders."""
        folder = temp_vault / "test_folder"
        subfolder = folder / "subfolder"
        subfolder.mkdir(parents=True)

        (folder / "Root.md").write_text("---\ntitle: Root\n---\n")
        (subfolder / "Sub.md").write_text("---\ntitle: Sub\n---\n")

        await indexer.generate_index(folder, recursive=False)

        content = (folder / "_index.md").read_text()
        assert "[[Root]]" in content
        assert "[[Sub]]" not in content


# ============================================================================
# Render Index Tests
# ============================================================================


class TestRenderIndex:
    """Tests for _render_index method."""

    def test_render_basic(self, indexer: FolderIndexer, temp_vault: Path):
        """Basic index rendering."""
        folder = temp_vault / "papers"
        entries = [
            {"path": folder / "Paper1.md", "title": "Paper One"},
            {"path": folder / "Paper2.md", "title": "Paper Two"},
        ]

        result = indexer._render_index(folder, entries)

        assert "# Papers" in result  # Folder name formatted
        assert "*2 notes*" in result
        assert "[[Paper One]]" in result
        assert "[[Paper Two]]" in result

    def test_render_formats_folder_name(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Folder name is title-cased with hyphens replaced."""
        folder = temp_vault / "my-papers"
        folder.mkdir()
        entries = []

        result = indexer._render_index(folder, entries)

        assert "# My Papers" in result

    def test_render_has_frontmatter(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Rendered index has proper frontmatter."""
        folder = temp_vault / "test"
        entries = []

        result = indexer._render_index(folder, entries)

        assert result.startswith("---")
        assert "type: index" in result
        assert "folder: test" in result
        assert "generated:" in result


# ============================================================================
# Write Empty Index Tests
# ============================================================================


class TestWriteEmptyIndex:
    """Tests for _write_empty_index method."""

    @pytest.mark.asyncio
    async def test_write_empty_index(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Empty index has placeholder content."""
        folder = temp_vault / "empty"
        folder.mkdir()

        result = await indexer._write_empty_index(folder)

        assert result == str(folder / "_index.md")
        content = (folder / "_index.md").read_text()
        assert "---" in content
        assert "type: index" in content
        assert "*No notes yet*" in content


# ============================================================================
# Regenerate All Indices Tests
# ============================================================================


class TestRegenerateAllIndices:
    """Tests for regenerate_all_indices method."""

    @pytest.mark.asyncio
    async def test_regenerate_all_indices(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Regenerates indices for all content type folders."""
        # Create folders for content types (use exist_ok=True since fixture may create some)
        papers = temp_vault / "sources/papers"
        papers.mkdir(parents=True, exist_ok=True)
        (papers / "Paper.md").write_text("---\ntitle: Test\n---\n")

        with patch("app.services.obsidian.indexer.content_registry") as mock_registry:
            mock_registry.get_all_types.return_value = {
                "paper": {"folder": "sources/papers"},
                "article": {"folder": "sources/nonexistent"},  # Folder that doesn't exist
            }

            result = await indexer.regenerate_all_indices()

            assert "sources/papers" in result["regenerated"]
            assert "sources/nonexistent" not in result["regenerated"]
            assert result["count"] == 1
            assert (papers / "_index.md").exists()

    @pytest.mark.asyncio
    async def test_regenerate_skips_missing_folders(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Regeneration skips folders that don't exist."""
        with patch("app.services.obsidian.indexer.content_registry") as mock_registry:
            mock_registry.get_all_types.return_value = {
                "paper": {"folder": "nonexistent"},
            }

            result = await indexer.regenerate_all_indices()

            assert result["count"] == 0
            assert result["regenerated"] == []

    @pytest.mark.asyncio
    async def test_regenerate_handles_no_folder_config(
        self, indexer: FolderIndexer, temp_vault: Path
    ):
        """Regeneration handles content types without folder config."""
        with patch("app.services.obsidian.indexer.content_registry") as mock_registry:
            mock_registry.get_all_types.return_value = {
                "concept": {},  # No folder defined
            }

            result = await indexer.regenerate_all_indices()

            assert result["count"] == 0

