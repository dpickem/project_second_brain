"""
Unit Tests for Vault Lifecycle Management

Tests for startup_vault_services, shutdown_vault_services, and
get_watcher_status functions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.obsidian.lifecycle import (
    startup_vault_services,
    shutdown_vault_services,
    get_watcher_status,
    _vault_watcher,
    _sync_service,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module-level state before each test."""
    import app.services.obsidian.lifecycle as lifecycle

    lifecycle._vault_watcher = None
    lifecycle._sync_service = None
    yield
    lifecycle._vault_watcher = None
    lifecycle._sync_service = None


@pytest.fixture
def mock_vault_manager():
    """Create a mock VaultManager."""
    mock = MagicMock()
    mock.vault_path = Path("/mock/vault")
    return mock


@pytest.fixture
def mock_sync_service():
    """Create a mock VaultSyncService."""
    mock = MagicMock()
    mock.reconcile_on_startup = AsyncMock(
        return_value={
            "total_notes": 100,
            "modified_since_sync": 5,
            "synced": 5,
            "failed": 0,
            "last_sync": None,
        }
    )
    mock._update_last_sync_time = AsyncMock()
    return mock


@pytest.fixture
def mock_vault_watcher():
    """Create a mock VaultWatcher."""
    mock = MagicMock()
    mock.start = MagicMock()
    mock.stop = MagicMock()
    mock.is_running = True
    return mock


# ============================================================================
# Startup Tests
# ============================================================================


class TestStartupVaultServices:
    """Tests for startup_vault_services function."""

    @pytest.mark.asyncio
    async def test_startup_full_success(
        self, mock_vault_manager, mock_sync_service, mock_vault_watcher, temp_vault: Path
    ):
        """Startup with all services enabled succeeds."""
        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = True
            mock_settings.VAULT_SYNC_DEBOUNCE_MS = 1000

            # Patch the imports inside the function
            with patch(
                "app.services.obsidian.vault.get_vault_manager",
                return_value=mock_vault_manager,
            ):
                with patch(
                    "app.services.obsidian.sync.VaultSyncService",
                    return_value=mock_sync_service,
                ):
                    with patch(
                        "app.services.obsidian.watcher.VaultWatcher",
                        return_value=mock_vault_watcher,
                    ):
                        with patch(
                            "app.services.tasks.sync_vault_note"
                        ):
                            result = await startup_vault_services()

        assert result["vault_path"] == str(mock_vault_manager.vault_path)
        assert result["reconciliation"] is not None
        assert result["watcher_started"] is True
        mock_sync_service.reconcile_on_startup.assert_called_once()
        mock_vault_watcher.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_sync_disabled(
        self, mock_vault_manager, mock_sync_service, mock_vault_watcher
    ):
        """Startup with sync disabled skips reconciliation."""
        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = False
            mock_settings.VAULT_WATCH_ENABLED = True
            mock_settings.VAULT_SYNC_DEBOUNCE_MS = 1000

            with patch(
                "app.services.obsidian.vault.get_vault_manager",
                return_value=mock_vault_manager,
            ):
                with patch(
                    "app.services.obsidian.sync.VaultSyncService",
                    return_value=mock_sync_service,
                ):
                    with patch(
                        "app.services.obsidian.watcher.VaultWatcher",
                        return_value=mock_vault_watcher,
                    ):
                        with patch(
                            "app.services.tasks.sync_vault_note"
                        ):
                            result = await startup_vault_services()

        assert result["reconciliation"] is None
        mock_sync_service.reconcile_on_startup.assert_not_called()

    @pytest.mark.asyncio
    async def test_startup_watcher_disabled(
        self, mock_vault_manager, mock_sync_service
    ):
        """Startup with watcher disabled doesn't start watcher."""
        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = False
            mock_settings.VAULT_SYNC_DEBOUNCE_MS = 1000

            with patch(
                "app.services.obsidian.vault.get_vault_manager",
                return_value=mock_vault_manager,
            ):
                with patch(
                    "app.services.obsidian.sync.VaultSyncService",
                    return_value=mock_sync_service,
                ):
                    result = await startup_vault_services()

        assert result["watcher_started"] is False

    @pytest.mark.asyncio
    async def test_startup_vault_not_found(self):
        """Startup handles missing vault gracefully."""
        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = True

            with patch(
                "app.services.obsidian.vault.get_vault_manager",
                side_effect=ValueError("Vault path does not exist"),
            ):
                result = await startup_vault_services()

        assert result["vault_path"] is None
        assert result["reconciliation"] is None
        assert result["watcher_started"] is False

    @pytest.mark.asyncio
    async def test_startup_uses_celery_task(
        self, mock_vault_manager, mock_sync_service, mock_vault_watcher
    ):
        """Startup configures watcher to use Celery task."""
        captured_callback = None

        def capture_watcher_init(vault_path, on_change, debounce_ms):
            nonlocal captured_callback
            captured_callback = on_change
            return mock_vault_watcher

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = True
            mock_settings.VAULT_SYNC_DEBOUNCE_MS = 1000

            with patch(
                "app.services.obsidian.vault.get_vault_manager",
                return_value=mock_vault_manager,
            ):
                with patch(
                    "app.services.obsidian.sync.VaultSyncService",
                    return_value=mock_sync_service,
                ):
                    with patch(
                        "app.services.obsidian.watcher.VaultWatcher",
                        side_effect=capture_watcher_init,
                    ):
                        with patch(
                            "app.services.tasks.sync_vault_note"
                        ) as mock_task:
                            mock_task.delay = MagicMock()
                            await startup_vault_services()

                            # Call the captured callback
                            assert captured_callback is not None
                            captured_callback("/path/to/note.md")

                            mock_task.delay.assert_called_once_with("/path/to/note.md")


# ============================================================================
# Shutdown Tests
# ============================================================================


class TestShutdownVaultServices:
    """Tests for shutdown_vault_services function."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_watcher(self, mock_vault_watcher, mock_sync_service):
        """Shutdown stops the vault watcher."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = mock_vault_watcher
        lifecycle._sync_service = mock_sync_service

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True

            await shutdown_vault_services()

        mock_vault_watcher.stop.assert_called_once()
        assert lifecycle._vault_watcher is None

    @pytest.mark.asyncio
    async def test_shutdown_updates_sync_time(self, mock_sync_service):
        """Shutdown updates last sync time."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._sync_service = mock_sync_service

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True

            await shutdown_vault_services()

        mock_sync_service._update_last_sync_time.assert_called_once()
        assert lifecycle._sync_service is None

    @pytest.mark.asyncio
    async def test_shutdown_sync_disabled(self, mock_sync_service):
        """Shutdown skips sync update when disabled."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._sync_service = mock_sync_service

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = False

            await shutdown_vault_services()

        mock_sync_service._update_last_sync_time.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self):
        """Shutdown is safe to call when services not started."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = None
        lifecycle._sync_service = None

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True

            # Should not raise
            await shutdown_vault_services()

        assert lifecycle._vault_watcher is None
        assert lifecycle._sync_service is None


# ============================================================================
# Get Watcher Status Tests
# ============================================================================


class TestGetWatcherStatus:
    """Tests for get_watcher_status function."""

    def test_status_watcher_running(self, mock_vault_watcher):
        """Status shows watcher running."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = mock_vault_watcher
        mock_vault_watcher.is_running = True

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = True

            result = get_watcher_status()

        assert result["watcher_running"] is True
        assert result["sync_enabled"] is True
        assert result["watch_enabled"] is True

    def test_status_watcher_not_started(self):
        """Status shows watcher not running when not started."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = None

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = True
            mock_settings.VAULT_WATCH_ENABLED = True

            result = get_watcher_status()

        assert result["watcher_running"] is False

    def test_status_reflects_settings(self):
        """Status reflects current settings."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = None

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            mock_settings.VAULT_SYNC_NEO4J_ENABLED = False
            mock_settings.VAULT_WATCH_ENABLED = False

            result = get_watcher_status()

        assert result["sync_enabled"] is False
        assert result["watch_enabled"] is False

    def test_status_missing_settings_attributes(self):
        """Status handles missing settings attributes gracefully."""
        import app.services.obsidian.lifecycle as lifecycle

        lifecycle._vault_watcher = None

        with patch("app.services.obsidian.lifecycle.settings") as mock_settings:
            # Simulate missing attributes
            del mock_settings.VAULT_SYNC_NEO4J_ENABLED
            del mock_settings.VAULT_WATCH_ENABLED

            result = get_watcher_status()

        # Should use defaults (True)
        assert result["sync_enabled"] is True
        assert result["watch_enabled"] is True

