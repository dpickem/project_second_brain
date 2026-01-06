"""
Unit Tests for Daily Note Generator

Tests for the DailyNoteGenerator class which creates and manages
daily notes from Jinja2 templates.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.obsidian.daily import DailyNoteGenerator
from app.services.obsidian.vault import VaultManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def vault_manager(temp_vault: Path) -> VaultManager:
    """Create a VaultManager with a temporary vault."""
    return VaultManager(str(temp_vault))


@pytest.fixture
def daily_generator(vault_manager: VaultManager) -> DailyNoteGenerator:
    """Create a DailyNoteGenerator with the test vault manager."""
    return DailyNoteGenerator(vault_manager)


@pytest.fixture
def mock_template_env(tmp_path: Path):
    """Create a mock Jinja2 environment with test templates."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Create a test daily template
    (templates_dir / "daily.md.j2").write_text(
        """---
type: daily
date: {{ date_iso }}
---

# {{ date_full }}

## 📥 Inbox

## ✅ Tasks

## 📝 Notes
"""
    )
    return templates_dir


# ============================================================================
# DailyNoteGenerator Initialization Tests
# ============================================================================


class TestDailyNoteGeneratorInit:
    """Tests for DailyNoteGenerator initialization."""

    def test_init(self, vault_manager: VaultManager):
        """DailyNoteGenerator initializes with vault manager."""
        generator = DailyNoteGenerator(vault_manager)
        assert generator.vault == vault_manager
        assert generator._env is not None


# ============================================================================
# Generate Daily Note Tests
# ============================================================================


class TestGenerateDailyNote:
    """Tests for generate_daily_note method."""

    @pytest.mark.asyncio
    async def test_generate_creates_new_note(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """New daily note is created from template."""
        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                target_date = date(2025, 1, 15)

                result = await generator.generate_daily_note(target_date)

                expected_path = temp_vault / "daily" / "2025-01-15.md"
                assert result == str(expected_path)
                assert expected_path.exists()
                content = expected_path.read_text()
                assert "date: 2025-01-15" in content
                assert "Wednesday, January 15, 2025" in content

    @pytest.mark.asyncio
    async def test_generate_uses_today_by_default(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """generate_daily_note defaults to today's date."""
        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                result = await generator.generate_daily_note()

                today = date.today()
                expected_path = (
                    temp_vault / "daily" / f"{today.strftime('%Y-%m-%d')}.md"
                )
                assert result == str(expected_path)

    @pytest.mark.asyncio
    async def test_generate_does_not_overwrite_existing(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """Existing daily notes are not overwritten."""
        target_date = date(2025, 1, 15)
        daily_folder = temp_vault / "daily"
        daily_folder.mkdir(parents=True, exist_ok=True)
        existing_note = daily_folder / "2025-01-15.md"
        existing_note.write_text("Original content - should not change")

        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                result = await generator.generate_daily_note(target_date)

                assert result == str(existing_note)
                content = existing_note.read_text()
                assert content == "Original content - should not change"

    @pytest.mark.asyncio
    async def test_generate_creates_daily_folder(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """Daily folder is created if it doesn't exist."""
        # Remove the daily folder if it exists
        daily_folder = temp_vault / "daily"
        if daily_folder.exists():
            import shutil

            shutil.rmtree(daily_folder)

        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                target_date = date(2025, 1, 15)
                await generator.generate_daily_note(target_date)

                assert daily_folder.exists()

    @pytest.mark.asyncio
    async def test_generate_raises_without_template(
        self, vault_manager: VaultManager, mock_template_env: Path
    ):
        """ValueError raised when no template configured."""
        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = None

                generator = DailyNoteGenerator(vault_manager)

                with pytest.raises(ValueError, match="No jinja_template configured"):
                    await generator.generate_daily_note()

    @pytest.mark.asyncio
    async def test_generate_template_context(
        self, vault_manager: VaultManager, temp_vault: Path
    ):
        """Template receives correct context variables."""
        # Create a template that uses all context variables
        templates_dir = temp_vault / "test_templates"
        templates_dir.mkdir()
        (templates_dir / "daily.md.j2").write_text(
            """---
date: {{ date_iso }}
year: {{ year }}
month: {{ month }}
day: {{ day }}
weekday: {{ weekday }}
full: {{ date_full }}
---
"""
        )

        with patch("app.services.obsidian.daily.TEMPLATES_DIR", templates_dir):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                target_date = date(2025, 6, 20)  # Friday
                await generator.generate_daily_note(target_date)

                note_path = temp_vault / "daily" / "2025-06-20.md"
                content = note_path.read_text()
                assert "date: 2025-06-20" in content
                assert "year: 2025" in content
                assert "month: June" in content
                assert "day: 20" in content
                assert "weekday: Friday" in content


# ============================================================================
# Add Inbox Item Tests
# ============================================================================


class TestAddInboxItem:
    """Tests for add_inbox_item method."""

    @pytest.mark.asyncio
    async def test_add_inbox_item(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """Item is added to inbox section."""
        target_date = date(2025, 1, 15)
        daily_folder = temp_vault / "daily"
        daily_folder.mkdir(parents=True, exist_ok=True)

        # Create note with inbox section
        note_path = daily_folder / "2025-01-15.md"
        note_path.write_text(
            """---
type: daily
---

## 📥 Inbox

## Tasks
"""
        )

        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                await generator.add_inbox_item(target_date, "New task to review")

                content = note_path.read_text()
                assert "- New task to review" in content

    @pytest.mark.asyncio
    async def test_add_inbox_creates_note_if_missing(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """Daily note is created if it doesn't exist."""
        target_date = date(2025, 1, 15)
        daily_folder = temp_vault / "daily"
        daily_folder.mkdir(parents=True, exist_ok=True)

        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                await generator.add_inbox_item(target_date, "New item")

                note_path = daily_folder / "2025-01-15.md"
                assert note_path.exists()


# ============================================================================
# Get Today Note Path Tests
# ============================================================================


class TestGetTodayNotePath:
    """Tests for get_today_note_path method."""

    @pytest.mark.asyncio
    async def test_get_today_note_path(
        self, daily_generator: DailyNoteGenerator, temp_vault: Path
    ):
        """Returns correct path for today's note."""
        result = await daily_generator.get_today_note_path()

        today = date.today()
        expected = temp_vault / "daily" / f"{today.strftime('%Y-%m-%d')}.md"
        assert result == expected


# ============================================================================
# Ensure Today Note Tests
# ============================================================================


class TestEnsureTodayNote:
    """Tests for ensure_today_note method."""

    @pytest.mark.asyncio
    async def test_ensure_today_note(
        self, vault_manager: VaultManager, temp_vault: Path, mock_template_env: Path
    ):
        """ensure_today_note creates today's note."""
        with patch("app.services.obsidian.daily.TEMPLATES_DIR", mock_template_env):
            with patch("app.services.obsidian.daily.content_registry") as mock_registry:
                mock_registry.get_jinja_template.return_value = "daily.md.j2"

                generator = DailyNoteGenerator(vault_manager)
                result = await generator.ensure_today_note()

                today = date.today()
                expected = temp_vault / "daily" / f"{today.strftime('%Y-%m-%d')}.md"
                assert result == str(expected)
                assert expected.exists()
