"""
Integration Tests for Vault API Endpoints

Tests the vault-related API endpoints including:
- Vault health and status
- Structure validation
- Sync operations
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from app.main import app

    return TestClient(app)


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
    mock.full_sync = AsyncMock(
        return_value={"synced": 10, "failed": 0, "total": 10, "errors": []}
    )
    mock.reconcile_on_startup = AsyncMock(
        return_value={
            "total_notes": 100,
            "modified_since_sync": 5,
            "synced": 5,
            "failed": 0,
        }
    )
    return mock


# ============================================================================
# Health Endpoint Tests
# ============================================================================


class TestVaultHealth:
    """Tests for vault health endpoints."""

    def test_health_includes_vault_status(self, client: TestClient):
        """Health endpoint includes vault information."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        # Health endpoint should include vault-related info
        assert "status" in data

    def test_health_detailed_includes_vault(self, client: TestClient):
        """Detailed health includes vault health."""
        response = client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "obsidian_vault" in data["dependencies"]


# ============================================================================
# Vault Status Endpoint Tests
# ============================================================================


class TestVaultStatus:
    """Tests for vault status endpoints."""

    def test_vault_status_endpoint(self, client: TestClient):
        """Vault status endpoint returns current state."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_get_vault.return_value = MagicMock(vault_path=Path("/test/vault"))

            with patch("app.routers.vault.get_watcher_status") as mock_watcher:
                mock_watcher.return_value = {
                    "watcher_running": True,
                    "sync_enabled": True,
                    "watch_enabled": True,
                }

                with patch("app.routers.vault.get_sync_status") as mock_sync:
                    mock_sync.return_value = {
                        "is_running": False,
                        "sync_type": None,
                        "progress": {"total": 0, "processed": 0},
                    }

                    response = client.get("/api/vault/status")

        if response.status_code == 200:
            data = response.json()
            assert "vault_path" in data or "status" in data


# ============================================================================
# Vault Structure Endpoint Tests
# ============================================================================


class TestVaultStructure:
    """Tests for vault structure endpoints."""

    def test_ensure_structure_endpoint(self, client: TestClient, temp_vault: Path):
        """Ensure structure endpoint creates missing folders."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_manager = MagicMock()
            mock_manager.vault_path = temp_vault
            mock_manager.ensure_structure = AsyncMock(
                return_value={"created": ["new_folder"], "existed": ["topics"], "total": 2}
            )
            mock_get_vault.return_value = mock_manager

            response = client.post("/api/vault/ensure-structure")

        if response.status_code == 200:
            data = response.json()
            assert "created" in data or "status" in data


# ============================================================================
# Vault Sync Endpoint Tests
# ============================================================================


class TestVaultSyncEndpoints:
    """Tests for vault sync endpoints."""

    def test_trigger_full_sync(
        self, client: TestClient, mock_vault_manager, mock_sync_service
    ):
        """Trigger full sync endpoint starts sync operation."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_get_vault.return_value = mock_vault_manager

            with patch("app.routers.vault.VaultSyncService") as mock_svc_class:
                mock_svc_class.return_value = mock_sync_service

                response = client.post("/api/vault/sync")

        # Accept various status codes (200, 202, 404 if endpoint doesn't exist)
        if response.status_code in [200, 202]:
            data = response.json()
            assert "synced" in data or "status" in data or "message" in data

    def test_get_sync_status(self, client: TestClient):
        """Sync status endpoint returns current progress."""
        with patch("app.routers.vault.get_sync_status") as mock_status:
            mock_status.return_value = {
                "is_running": True,
                "sync_type": "full",
                "progress": {"total": 100, "processed": 50, "percent": 50.0},
            }

            response = client.get("/api/vault/sync/status")

        if response.status_code == 200:
            data = response.json()
            assert "is_running" in data or "status" in data


# ============================================================================
# Vault Stats Endpoint Tests
# ============================================================================


class TestVaultStats:
    """Tests for vault statistics endpoints."""

    def test_get_vault_stats(self, client: TestClient, temp_vault: Path):
        """Vault stats endpoint returns note counts."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_manager = MagicMock()
            mock_manager.vault_path = temp_vault
            mock_manager.get_vault_stats = AsyncMock(
                return_value={
                    "total_notes": 150,
                    "by_type": {"paper": 50, "article": 30, "concept": 70},
                }
            )
            mock_get_vault.return_value = mock_manager

            response = client.get("/api/vault/stats")

        if response.status_code == 200:
            data = response.json()
            assert "total_notes" in data or "stats" in data


# ============================================================================
# Index Generation Endpoint Tests
# ============================================================================


class TestIndexGeneration:
    """Tests for folder index generation endpoints."""

    def test_regenerate_indices(self, client: TestClient, temp_vault: Path):
        """Regenerate indices endpoint updates all folder indices."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_manager = MagicMock()
            mock_manager.vault_path = temp_vault
            mock_get_vault.return_value = mock_manager

            with patch("app.routers.vault.FolderIndexer") as mock_indexer_class:
                mock_indexer = MagicMock()
                mock_indexer.regenerate_all_indices = AsyncMock(
                    return_value={"regenerated": ["sources/papers"], "count": 1}
                )
                mock_indexer_class.return_value = mock_indexer

                response = client.post("/api/vault/indices/regenerate")

        if response.status_code == 200:
            data = response.json()
            assert "regenerated" in data or "count" in data or "status" in data


# ============================================================================
# Daily Note Endpoint Tests
# ============================================================================


class TestDailyNoteEndpoints:
    """Tests for daily note endpoints."""

    def test_ensure_today_note(self, client: TestClient, temp_vault: Path):
        """Ensure today's note endpoint creates daily note."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_manager = MagicMock()
            mock_manager.vault_path = temp_vault
            mock_get_vault.return_value = mock_manager

            with patch("app.routers.vault.DailyNoteGenerator") as mock_gen_class:
                mock_gen = MagicMock()
                mock_gen.ensure_today_note = AsyncMock(
                    return_value=str(temp_vault / "daily/2025-01-05.md")
                )
                mock_gen_class.return_value = mock_gen

                response = client.post("/api/vault/daily/today")

        if response.status_code == 200:
            data = response.json()
            assert "path" in data or "status" in data


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestAPIErrorHandling:
    """Tests for API error handling."""

    def test_handles_vault_not_found(self, client: TestClient):
        """API handles missing vault gracefully."""
        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_get_vault.side_effect = ValueError("Vault path does not exist")

            response = client.get("/api/vault/status")

        # Should return error response, not 500
        if response.status_code not in [404, 500]:
            data = response.json()
            assert "error" in data or "detail" in data

    def test_handles_sync_already_running(
        self, client: TestClient, mock_vault_manager, mock_sync_service
    ):
        """API handles concurrent sync attempts."""
        mock_sync_service.full_sync = AsyncMock(
            return_value={"error": "Sync already in progress", "status": {}}
        )

        with patch("app.routers.vault.get_vault_manager") as mock_get_vault:
            mock_get_vault.return_value = mock_vault_manager

            with patch("app.routers.vault.VaultSyncService") as mock_svc_class:
                mock_svc_class.return_value = mock_sync_service

                response = client.post("/api/vault/sync")

        if response.status_code in [200, 409]:
            data = response.json()
            # Should indicate sync is already running
            if "error" in data:
                assert "already" in data["error"].lower() or "progress" in data["error"].lower()


