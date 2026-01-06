"""
Unit Tests for VaultManager

Tests for the VaultManager class which handles vault structure, 
path resolution, file operations, and statistics.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from app.services.obsidian.vault import (
    VaultManager,
    get_vault_manager,
    create_vault_manager,
    reset_vault_manager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test."""
    reset_vault_manager()
    yield
    reset_vault_manager()


@pytest.fixture
def vault_manager(temp_vault: Path) -> VaultManager:
    """Create a VaultManager with a temporary vault."""
    return VaultManager(str(temp_vault))


# ============================================================================
# VaultManager Initialization Tests
# ============================================================================


class TestVaultManagerInit:
    """Tests for VaultManager initialization."""

    def test_init_with_valid_path(self, temp_vault: Path):
        """VaultManager initializes with a valid vault path."""
        manager = VaultManager(str(temp_vault))
        assert manager.vault_path == temp_vault

    def test_init_expands_tilde(self, temp_vault: Path):
        """VaultManager expands ~ in paths."""
        # We can't easily test actual ~ expansion without mocking
        # but we can verify the path is expanded
        manager = VaultManager(str(temp_vault))
        assert "~" not in str(manager.vault_path)

    def test_init_nonexistent_path_raises(self, tmp_path: Path):
        """VaultManager raises ValueError for nonexistent paths."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(ValueError, match="does not exist"):
            VaultManager(str(nonexistent))

    def test_init_file_path_raises(self, tmp_path: Path):
        """VaultManager raises ValueError when path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        with pytest.raises(ValueError, match="not a directory"):
            VaultManager(str(file_path))

    def test_init_uses_settings_default(self, temp_vault: Path):
        """VaultManager uses settings.OBSIDIAN_VAULT_PATH when path is None."""
        with patch("app.services.obsidian.vault.settings") as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(temp_vault)
            manager = VaultManager()
            assert manager.vault_path == temp_vault


# ============================================================================
# VaultManager Structure Tests
# ============================================================================


class TestVaultManagerStructure:
    """Tests for ensure_structure method."""

    @pytest.mark.asyncio
    async def test_ensure_structure_creates_missing_folders(self, tmp_path: Path):
        """ensure_structure creates missing system folders."""
        vault_path = tmp_path / "new_vault"
        vault_path.mkdir()

        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {
                "system_folders": ["topics", "concepts", "daily"]
            }
            with patch("app.services.obsidian.vault.content_registry") as mock_registry:
                mock_registry.get_all_types.return_value = {}

                manager = VaultManager(str(vault_path))
                result = await manager.ensure_structure()

                assert "topics" in result["created"]
                assert "concepts" in result["created"]
                assert "daily" in result["created"]
                assert (vault_path / "topics").exists()
                assert (vault_path / "concepts").exists()

    @pytest.mark.asyncio
    async def test_ensure_structure_idempotent(self, temp_vault: Path):
        """ensure_structure is idempotent - safe to call multiple times."""
        manager = VaultManager(str(temp_vault))

        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {"system_folders": ["topics"]}
            with patch("app.services.obsidian.vault.content_registry") as mock_registry:
                mock_registry.get_all_types.return_value = {}

                # First call
                result1 = await manager.ensure_structure()
                # Second call
                result2 = await manager.ensure_structure()

                # Topics already exists from fixture, should be in 'existed'
                assert result2["total"] == result1["total"]

    @pytest.mark.asyncio
    async def test_ensure_structure_creates_content_type_folders(self, tmp_path: Path):
        """ensure_structure creates content type folders from registry."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {"system_folders": []}
            with patch("app.services.obsidian.vault.content_registry") as mock_registry:
                mock_registry.get_all_types.return_value = {
                    "paper": {"folder": "sources/papers", "subfolders": []},
                    "article": {"folder": "sources/articles", "subfolders": []},
                }

                manager = VaultManager(str(vault_path))
                result = await manager.ensure_structure()

                assert "sources/papers" in result["created"]
                assert "sources/articles" in result["created"]
                assert (vault_path / "sources/papers").exists()

    @pytest.mark.asyncio
    async def test_ensure_structure_creates_subfolders(self, tmp_path: Path):
        """ensure_structure creates subfolders for content types."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {"system_folders": []}
            with patch("app.services.obsidian.vault.content_registry") as mock_registry:
                mock_registry.get_all_types.return_value = {
                    "exercise": {
                        "folder": "exercises",
                        "subfolders": ["by-topic", "daily"],
                    },
                }

                manager = VaultManager(str(vault_path))
                result = await manager.ensure_structure()

                assert "exercises/by-topic" in result["created"]
                assert "exercises/daily" in result["created"]


# ============================================================================
# VaultManager Path Resolution Tests
# ============================================================================


class TestVaultManagerPathResolution:
    """Tests for folder path resolution methods."""

    def test_get_source_folder_known_type(self, vault_manager: VaultManager):
        """get_source_folder returns correct folder for known content types."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_folder.return_value = "sources/papers"
            folder = vault_manager.get_source_folder("paper")
            assert folder == vault_manager.vault_path / "sources/papers"

    def test_get_source_folder_unknown_type(self, vault_manager: VaultManager):
        """get_source_folder returns ideas folder for unknown types."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_folder.return_value = None
            folder = vault_manager.get_source_folder("unknown_type")
            assert folder == vault_manager.vault_path / "sources/ideas"

    def test_get_concept_folder(self, vault_manager: VaultManager):
        """get_concept_folder returns correct path."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_folder.return_value = "concepts"
            folder = vault_manager.get_concept_folder()
            assert folder == vault_manager.vault_path / "concepts"

    def test_get_concept_folder_default(self, vault_manager: VaultManager):
        """get_concept_folder uses default when not configured."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_folder.return_value = None
            folder = vault_manager.get_concept_folder()
            assert folder == vault_manager.vault_path / "concepts"

    def test_get_daily_folder(self, vault_manager: VaultManager):
        """get_daily_folder returns correct path."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_folder.return_value = "daily"
            folder = vault_manager.get_daily_folder()
            assert folder == vault_manager.vault_path / "daily"

    def test_get_template_folder(self, vault_manager: VaultManager):
        """get_template_folder returns configured path."""
        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {
                "templates": {"folder": "my_templates"}
            }
            folder = vault_manager.get_template_folder()
            assert folder == vault_manager.vault_path / "my_templates"

    def test_get_template_folder_default(self, vault_manager: VaultManager):
        """get_template_folder uses default when not configured."""
        with patch("app.services.obsidian.vault.yaml_config") as mock_config:
            mock_config.get.return_value = {}
            folder = vault_manager.get_template_folder()
            assert folder == vault_manager.vault_path / "templates"


# ============================================================================
# VaultManager Filename Sanitization Tests
# ============================================================================


class TestVaultManagerSanitization:
    """Tests for filename sanitization."""

    def test_sanitize_removes_invalid_chars(self, vault_manager: VaultManager):
        """sanitize_filename removes Windows-invalid characters."""
        result = vault_manager.sanitize_filename('My Paper: A "Study" of AI?')
        assert ":" not in result
        assert '"' not in result
        assert "?" not in result

    def test_sanitize_collapses_whitespace(self, vault_manager: VaultManager):
        """sanitize_filename collapses multiple spaces."""
        result = vault_manager.sanitize_filename("My   Paper    Title")
        assert "  " not in result
        assert result == "My Paper Title"

    def test_sanitize_truncates_long_names(self, vault_manager: VaultManager):
        """sanitize_filename truncates to max_length."""
        long_title = "A" * 150
        result = vault_manager.sanitize_filename(long_title, max_length=50)
        assert len(result) <= 50

    def test_sanitize_truncates_at_word_boundary(self, vault_manager: VaultManager):
        """sanitize_filename truncates at word boundaries."""
        title = "This is a very long title that should be truncated nicely"
        result = vault_manager.sanitize_filename(title, max_length=30)
        assert len(result) <= 30
        assert not result.endswith(" ")

    def test_sanitize_returns_untitled_for_empty(self, vault_manager: VaultManager):
        """sanitize_filename returns 'Untitled' for empty/invalid input."""
        assert vault_manager.sanitize_filename("") == "Untitled"
        assert vault_manager.sanitize_filename("?:*") == "Untitled"

    def test_sanitize_preserves_valid_chars(self, vault_manager: VaultManager):
        """sanitize_filename preserves valid characters."""
        result = vault_manager.sanitize_filename("Machine Learning 101")
        assert result == "Machine Learning 101"

    def test_sanitize_handles_special_chars(self, vault_manager: VaultManager):
        """sanitize_filename handles various special characters."""
        result = vault_manager.sanitize_filename("Paper<>:/\\|?*Test")
        assert result == "PaperTest"


# ============================================================================
# VaultManager File Operations Tests
# ============================================================================


class TestVaultManagerFileOperations:
    """Tests for file I/O operations."""

    @pytest.mark.asyncio
    async def test_note_exists_true(self, vault_manager: VaultManager, temp_vault: Path):
        """note_exists returns True when note exists."""
        folder = temp_vault / "concepts"
        (folder / "Test Note.md").write_text("content")

        result = await vault_manager.note_exists(folder, "Test Note")
        assert result is True

    @pytest.mark.asyncio
    async def test_note_exists_false(self, vault_manager: VaultManager, temp_vault: Path):
        """note_exists returns False when note doesn't exist."""
        folder = temp_vault / "concepts"
        result = await vault_manager.note_exists(folder, "Nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_unique_path_simple(self, vault_manager: VaultManager, temp_vault: Path):
        """get_unique_path returns simple path when no conflict."""
        folder = temp_vault / "concepts"
        path = await vault_manager.get_unique_path(folder, "New Note")
        assert path == folder / "New Note.md"

    @pytest.mark.asyncio
    async def test_get_unique_path_with_conflict(self, vault_manager: VaultManager, temp_vault: Path):
        """get_unique_path adds counter when file exists."""
        folder = temp_vault / "concepts"
        (folder / "Existing Note.md").write_text("content")

        path = await vault_manager.get_unique_path(folder, "Existing Note")
        assert path == folder / "Existing Note_1.md"

    @pytest.mark.asyncio
    async def test_get_unique_path_multiple_conflicts(self, vault_manager: VaultManager, temp_vault: Path):
        """get_unique_path increments counter for multiple conflicts."""
        folder = temp_vault / "concepts"
        (folder / "Note.md").write_text("content")
        (folder / "Note_1.md").write_text("content")
        (folder / "Note_2.md").write_text("content")

        path = await vault_manager.get_unique_path(folder, "Note")
        assert path == folder / "Note_3.md"

    @pytest.mark.asyncio
    async def test_write_note(self, vault_manager: VaultManager, temp_vault: Path):
        """write_note creates file with content."""
        path = temp_vault / "concepts" / "New Note.md"
        content = "---\ntype: concept\n---\n\n# Content"

        result = await vault_manager.write_note(path, content)

        assert result == path
        assert path.exists()
        assert path.read_text() == content

    @pytest.mark.asyncio
    async def test_write_note_creates_parent_dirs(self, vault_manager: VaultManager, temp_vault: Path):
        """write_note creates parent directories if needed."""
        path = temp_vault / "new" / "nested" / "folder" / "Note.md"
        content = "content"

        await vault_manager.write_note(path, content)

        assert path.exists()
        assert path.read_text() == content

    @pytest.mark.asyncio
    async def test_read_note(self, vault_manager: VaultManager, temp_vault: Path):
        """read_note returns file content."""
        path = temp_vault / "concepts" / "Test.md"
        expected_content = "---\ntype: concept\n---\n\n# Test"
        path.write_text(expected_content)

        content = await vault_manager.read_note(path)

        assert content == expected_content

    @pytest.mark.asyncio
    async def test_read_note_not_found(self, vault_manager: VaultManager, temp_vault: Path):
        """read_note raises FileNotFoundError for missing files."""
        path = temp_vault / "concepts" / "Missing.md"

        with pytest.raises(FileNotFoundError):
            await vault_manager.read_note(path)

    @pytest.mark.asyncio
    async def test_list_notes_simple(self, vault_manager: VaultManager, temp_vault: Path):
        """list_notes returns markdown files in folder."""
        folder = temp_vault / "concepts"
        (folder / "Note1.md").write_text("content")
        (folder / "Note2.md").write_text("content")
        (folder / "ignore.txt").write_text("not markdown")

        notes = await vault_manager.list_notes(folder)

        assert len(notes) == 2
        assert all(n.suffix == ".md" for n in notes)

    @pytest.mark.asyncio
    async def test_list_notes_recursive(self, vault_manager: VaultManager, temp_vault: Path):
        """list_notes with recursive=True finds notes in subfolders."""
        folder = temp_vault / "sources"
        (folder / "papers").mkdir(parents=True, exist_ok=True)
        (folder / "Note1.md").write_text("content")
        (folder / "papers" / "Note2.md").write_text("content")

        notes = await vault_manager.list_notes(folder, recursive=True)

        assert len(notes) == 2

    @pytest.mark.asyncio
    async def test_list_notes_non_recursive(self, vault_manager: VaultManager, temp_vault: Path):
        """list_notes with recursive=False only finds notes in folder."""
        folder = temp_vault / "sources"
        (folder / "papers").mkdir(parents=True, exist_ok=True)
        (folder / "Note1.md").write_text("content")
        (folder / "papers" / "Note2.md").write_text("content")

        notes = await vault_manager.list_notes(folder, recursive=False)

        assert len(notes) == 1


# ============================================================================
# VaultManager Statistics Tests
# ============================================================================


class TestVaultManagerStats:
    """Tests for vault statistics."""

    @pytest.mark.asyncio
    async def test_get_vault_stats(self, vault_manager: VaultManager, temp_vault: Path):
        """get_vault_stats returns note counts by type."""
        # Create some test notes
        (temp_vault / "sources/papers").mkdir(parents=True, exist_ok=True)
        (temp_vault / "sources/papers" / "Paper1.md").write_text("content")
        (temp_vault / "sources/papers" / "Paper2.md").write_text("content")

        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_all_types.return_value = {
                "paper": {"folder": "sources/papers"},
            }

            stats = await vault_manager.get_vault_stats()

            assert stats["by_type"]["paper"] == 2
            assert stats["total_notes"] == 2

    @pytest.mark.asyncio
    async def test_get_vault_stats_empty(self, vault_manager: VaultManager):
        """get_vault_stats handles empty vault."""
        with patch("app.services.obsidian.vault.content_registry") as mock_registry:
            mock_registry.get_all_types.return_value = {
                "paper": {"folder": "sources/papers"},
            }

            stats = await vault_manager.get_vault_stats()

            assert stats["total_notes"] == 0


# ============================================================================
# Singleton Tests
# ============================================================================


class TestVaultManagerSingleton:
    """Tests for singleton pattern."""

    def test_get_vault_manager_returns_same_instance(self, temp_vault: Path):
        """get_vault_manager returns the same instance."""
        with patch("app.services.obsidian.vault.settings") as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(temp_vault)

            manager1 = get_vault_manager()
            manager2 = get_vault_manager()

            assert manager1 is manager2

    def test_reset_vault_manager(self, temp_vault: Path):
        """reset_vault_manager clears the singleton."""
        with patch("app.services.obsidian.vault.settings") as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(temp_vault)

            manager1 = get_vault_manager()
            reset_vault_manager()
            manager2 = get_vault_manager()

            assert manager1 is not manager2

    def test_create_vault_manager_not_singleton(self, temp_vault: Path):
        """create_vault_manager creates a new instance, not singleton."""
        with patch("app.services.obsidian.vault.settings") as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(temp_vault)

            singleton = get_vault_manager()
            new_instance = create_vault_manager(str(temp_vault))

            assert singleton is not new_instance

    def test_create_vault_manager_skip_validation(self, tmp_path: Path):
        """create_vault_manager can skip validation for setup."""
        nonexistent = tmp_path / "new_vault"

        # Should not raise even though path doesn't exist
        manager = create_vault_manager(str(nonexistent), validate=False)

        assert manager.vault_path == nonexistent


