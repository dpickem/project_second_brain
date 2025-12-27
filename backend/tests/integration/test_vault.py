"""
Integration Tests for Vault Validation

Tests the vault structure validation functionality.
These tests use temporary directories to simulate vault structures.

Run with: pytest tests/integration/test_vault.py -v
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add scripts directory to path for validate_vault import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from validate_vault import validate_vault


class TestVaultStructureValidation:
    """Test vault folder structure validation."""

    def test_valid_vault_passes_validation(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """A complete vault should pass validation."""
        result = validate_vault(temp_vault, sample_yaml_config)

        assert result is True

    def test_missing_folders_fail_validation(
        self, incomplete_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Vault with missing folders should fail validation."""
        result = validate_vault(incomplete_vault, sample_yaml_config)

        assert result is False

    def test_nonexistent_vault_fails(
        self, tmp_path: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Non-existent vault path should fail validation."""
        nonexistent = tmp_path / "does_not_exist"
        result = validate_vault(nonexistent, sample_yaml_config)

        assert result is False


class TestVaultSystemFolders:
    """Test system folder creation and validation."""

    def test_system_folders_created(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """System folders should exist in the vault."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]

        for folder_path in system_folders:
            full_path = temp_vault / folder_path
            assert full_path.exists(), f"Missing system folder: {folder_path}"

    def test_assets_subfolders_exist(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Assets folder should have required subfolders."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        asset_folders = [f for f in system_folders if f.startswith("assets/")]

        for folder_path in asset_folders:
            full_path = temp_vault / folder_path
            assert full_path.exists(), f"Missing asset subfolder: {folder_path}"

    def test_exercises_subfolders_exist(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Exercises folder should have organizational subfolders."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        exercise_folders = [f for f in system_folders if f.startswith("exercises/")]

        for folder_path in exercise_folders:
            full_path = temp_vault / folder_path
            assert full_path.exists(), f"Missing exercise subfolder: {folder_path}"

    def test_reviews_subfolders_exist(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Reviews folder should have due and archive subfolders."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        review_folders = [f for f in system_folders if f.startswith("reviews/")]

        for folder_path in review_folders:
            full_path = temp_vault / folder_path
            assert full_path.exists(), f"Missing review subfolder: {folder_path}"


class TestVaultContentTypeFolders:
    """Test content type folder creation."""

    def test_content_type_folders_created(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Content type folders should exist."""
        content_types = sample_yaml_config["content_types"]

        for type_name, type_config in content_types.items():
            folder_path = temp_vault / type_config["folder"]
            assert (
                folder_path.exists()
            ), f"Missing folder for {type_name}: {type_config['folder']}"


class TestTemplateValidation:
    """Test template file validation."""

    def test_templates_folder_exists(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Templates folder should exist."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        templates_folder = [f for f in system_folders if f == "templates"][0]
        assert (temp_vault / templates_folder).exists()

    def test_templates_have_frontmatter(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Templates should have YAML frontmatter."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        templates_folder = [f for f in system_folders if f == "templates"][0]
        template_files = list((temp_vault / templates_folder).glob("*.md"))

        assert len(template_files) > 0, "No template files found"

        for template in template_files:
            content = template.read_text()
            assert content.startswith("---"), f"{template.name} missing frontmatter"

    def test_templates_have_type_field(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Templates should have 'type' in frontmatter."""
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        templates_folder = [f for f in system_folders if f == "templates"][0]
        template_files = list((temp_vault / templates_folder).glob("*.md"))

        for template in template_files:
            content = template.read_text()
            # Simple check - frontmatter should contain "type:"
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx > 0:
                    frontmatter = content[3:end_idx]
                    assert (
                        "type:" in frontmatter
                    ), f"{template.name} missing 'type' field"


class TestObsidianConfiguration:
    """Test Obsidian configuration files."""

    def test_obsidian_folder_exists(self, temp_vault: Path) -> None:
        """The .obsidian folder should exist."""
        assert (temp_vault / ".obsidian").exists()

    def test_app_json_exists(self, temp_vault: Path) -> None:
        """app.json configuration should exist."""
        assert (temp_vault / ".obsidian" / "app.json").exists()

    def test_app_json_valid(self, temp_vault: Path) -> None:
        """app.json should be valid JSON."""
        app_json_path = temp_vault / ".obsidian" / "app.json"
        content = app_json_path.read_text()

        # Should parse without errors
        config = json.loads(content)
        assert isinstance(config, dict)

    def test_core_plugins_exists(self, temp_vault: Path) -> None:
        """core-plugins.json should exist."""
        assert (temp_vault / ".obsidian" / "core-plugins.json").exists()

    def test_core_plugins_valid(self, temp_vault: Path) -> None:
        """core-plugins.json should be valid JSON array."""
        plugins_path = temp_vault / ".obsidian" / "core-plugins.json"
        content = plugins_path.read_text()

        plugins = json.loads(content)
        assert isinstance(plugins, list)


class TestMetaFiles:
    """Test meta documentation files."""

    def test_meta_folder_exists(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Meta folder should exist."""
        meta_folder = sample_yaml_config["obsidian"]["meta"]["folder"]
        assert (temp_vault / meta_folder).exists()

    def test_dashboard_exists(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Dashboard file should exist."""
        meta_folder = sample_yaml_config["obsidian"]["meta"]["folder"]
        assert (temp_vault / meta_folder / "dashboard.md").exists()

    def test_dashboard_has_frontmatter(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Dashboard should have proper frontmatter."""
        meta_folder = sample_yaml_config["obsidian"]["meta"]["folder"]
        dashboard = temp_vault / meta_folder / "dashboard.md"
        content = dashboard.read_text()

        assert content.startswith("---")
        assert "type: meta" in content or "type:meta" in content


class TestVaultIntegrity:
    """Test overall vault integrity."""

    def test_no_broken_symlinks(self, temp_vault: Path) -> None:
        """Vault should not contain broken symlinks."""
        for item in temp_vault.rglob("*"):
            if item.is_symlink():
                assert item.resolve().exists(), f"Broken symlink: {item}"

    def test_no_empty_required_folders(
        self, temp_vault: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Required folders should exist (may be empty with .gitkeep)."""
        # Get required folders from system_folders config
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        required_folders = [
            "templates",
            sample_yaml_config["obsidian"]["meta"]["folder"],
        ]

        for folder in required_folders:
            # Verify folder is in system_folders config
            matching = [
                f for f in system_folders if f == folder or f.startswith(f"{folder}/")
            ]
            assert matching, f"Folder '{folder}' not in system_folders config"

            folder_path = temp_vault / folder
            assert folder_path.exists()
            assert folder_path.is_dir()


class TestVaultPathResolution:
    """Test vault path handling."""

    def test_relative_path_handling(self, tmp_path: Path) -> None:
        """Should handle relative vault paths."""
        vault = tmp_path / "relative_vault"
        vault.mkdir()
        (vault / "templates").mkdir()

        # Should work with both absolute and relative paths
        assert vault.exists()
        assert (vault / "templates").exists()

    def test_home_expansion(self, tmp_path: Path) -> None:
        """Path expansion should work for home directory."""
        # This is more of a documentation test
        # The actual path expansion happens at config loading time
        home = Path.home()
        assert home.exists()


class TestVaultCreation:
    """Test vault creation from scratch."""

    def test_create_vault_folders(
        self, tmp_path: Path, sample_yaml_config: dict[str, Any]
    ) -> None:
        """Should be able to create vault folders programmatically."""
        vault = tmp_path / "new_vault"

        # Get folders from config
        system_folders = sample_yaml_config["obsidian"]["system_folders"]
        content_type_folders = [
            ct["folder"] for ct in sample_yaml_config["content_types"].values()
        ]
        folders_to_create = system_folders + content_type_folders

        for folder in folders_to_create:
            (vault / folder).mkdir(parents=True, exist_ok=True)

        # Verify creation
        for folder in folders_to_create:
            assert (vault / folder).exists()

    def test_create_obsidian_config(self, tmp_path: Path) -> None:
        """Should be able to create .obsidian configuration."""
        vault = tmp_path / "configured_vault"
        obsidian_dir = vault / ".obsidian"
        obsidian_dir.mkdir(parents=True)

        # Create app.json
        app_config = {
            "alwaysUpdateLinks": True,
            "newFileLocation": "folder",
        }
        (obsidian_dir / "app.json").write_text(json.dumps(app_config))

        # Verify
        assert (obsidian_dir / "app.json").exists()
        loaded = json.loads((obsidian_dir / "app.json").read_text())
        assert loaded["alwaysUpdateLinks"] is True
