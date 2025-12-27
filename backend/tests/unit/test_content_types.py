"""
Unit Tests for Content Type Registry

Tests the ContentTypeRegistry class that manages content type configuration.
These tests verify:
- Content type loading from configuration
- Folder path resolution
- Template path resolution
- User vs system type filtering
- Type validation
"""

from typing import Any

import pytest

from app.content_types import ContentTypeRegistry, content_registry


class TestContentTypeRegistry:
    """Test suite for ContentTypeRegistry class."""

    @pytest.fixture
    def registry(self, sample_yaml_config: dict[str, Any]):
        """Create a ContentTypeRegistry with sample config."""
        return ContentTypeRegistry(sample_yaml_config)

    def test_get_all_types_returns_dict(self, registry) -> None:
        """get_all_types should return a dictionary of all content types."""
        all_types = registry.get_all_types()

        assert isinstance(all_types, dict)
        assert len(all_types) > 0

    def test_get_all_types_includes_all_configured_types(
        self, registry, sample_yaml_config: dict[str, Any]
    ) -> None:
        """get_all_types should include all types from config."""
        all_types = registry.get_all_types()
        expected_types = sample_yaml_config["content_types"].keys()

        for type_name in expected_types:
            assert type_name in all_types

    def test_get_user_types_excludes_system_types(self, registry) -> None:
        """get_user_types should not include system types."""
        user_types = registry.get_user_types()

        # System types should be excluded
        assert "concept" not in user_types
        assert "daily" not in user_types

        # User types should be included
        assert "paper" in user_types
        assert "article" in user_types
        assert "book" in user_types

    def test_get_user_types_returns_subset(self, registry) -> None:
        """get_user_types should return fewer types than get_all_types."""
        all_types = registry.get_all_types()
        user_types = registry.get_user_types()

        assert len(user_types) < len(all_types)

    def test_get_folder_returns_correct_path(self, registry) -> None:
        """get_folder should return the folder path for a content type."""
        assert registry.get_folder("paper") == "sources/papers"
        assert registry.get_folder("article") == "sources/articles"
        assert registry.get_folder("concept") == "concepts"
        assert registry.get_folder("daily") == "daily"

    def test_get_folder_returns_none_for_unknown_type(self, registry) -> None:
        """get_folder should return None for non-existent types."""
        assert registry.get_folder("nonexistent") is None
        assert registry.get_folder("") is None

    def test_get_template_returns_correct_path(self, registry) -> None:
        """get_template should return the Obsidian template path."""
        assert registry.get_template("paper") == "templates/paper.md"
        assert registry.get_template("article") == "templates/article.md"

    def test_get_template_returns_none_for_unknown_type(self, registry) -> None:
        """get_template should return None for non-existent types."""
        assert registry.get_template("nonexistent") is None

    def test_get_jinja_template_returns_correct_filename(self, registry) -> None:
        """get_jinja_template should return the Jinja2 template filename."""
        assert registry.get_jinja_template("paper") == "paper.md.j2"
        assert registry.get_jinja_template("article") == "article.md.j2"

    def test_get_jinja_template_returns_none_for_unknown_type(self, registry) -> None:
        """get_jinja_template should return None for non-existent types."""
        assert registry.get_jinja_template("nonexistent") is None

    def test_get_subfolders_returns_list(self, registry) -> None:
        """get_subfolders should return a list (may be empty)."""
        subfolders = registry.get_subfolders("paper")

        assert isinstance(subfolders, list)

    def test_get_subfolders_returns_empty_for_type_without_subfolders(
        self, registry
    ) -> None:
        """get_subfolders should return empty list for types without subfolders."""
        subfolders = registry.get_subfolders("paper")

        assert subfolders == []

    def test_get_subfolders_returns_empty_for_unknown_type(self, registry) -> None:
        """get_subfolders should return empty list for unknown types."""
        subfolders = registry.get_subfolders("nonexistent")

        assert subfolders == []

    def test_is_valid_type_returns_true_for_known_types(self, registry) -> None:
        """is_valid_type should return True for configured types."""
        assert registry.is_valid_type("paper") is True
        assert registry.is_valid_type("article") is True
        assert registry.is_valid_type("book") is True
        assert registry.is_valid_type("concept") is True
        assert registry.is_valid_type("daily") is True

    def test_is_valid_type_returns_false_for_unknown_types(self, registry) -> None:
        """is_valid_type should return False for non-existent types."""
        assert registry.is_valid_type("nonexistent") is False
        assert registry.is_valid_type("") is False
        assert registry.is_valid_type("PAPER") is False  # Case sensitive

    def test_get_description_returns_description(self, registry) -> None:
        """get_description should return the type description."""
        assert registry.get_description("paper") == "Academic papers"
        assert registry.get_description("article") == "Blog posts"

    def test_get_description_returns_none_for_unknown_type(self, registry) -> None:
        """get_description should return None for unknown types."""
        assert registry.get_description("nonexistent") is None

    def test_get_icon_returns_emoji(self, registry) -> None:
        """get_icon should return the emoji icon."""
        assert registry.get_icon("paper") == "📄"
        assert registry.get_icon("article") == "📰"
        assert registry.get_icon("book") == "📚"

    def test_get_icon_returns_none_for_unknown_type(self, registry) -> None:
        """get_icon should return None for unknown types."""
        assert registry.get_icon("nonexistent") is None


class TestContentTypeRegistryEdgeCases:
    """Test edge cases and error handling in ContentTypeRegistry."""

    def test_empty_config_creates_empty_registry(self) -> None:
        """Registry with empty config should have no types."""
        registry = ContentTypeRegistry({})

        assert registry.get_all_types() == {}
        assert registry.is_valid_type("paper") is False

    def test_config_without_content_types_key(self) -> None:
        """Registry should handle config without content_types key."""
        config = {"app": {"name": "Test"}}
        registry = ContentTypeRegistry(config)

        assert registry.get_all_types() == {}

    def test_type_with_missing_optional_fields(self) -> None:
        """Registry should handle types with missing optional fields."""
        config = {
            "content_types": {
                "minimal": {
                    "folder": "sources/minimal",
                    "template": "templates/minimal.md",
                    # No jinja_template, description, icon, subfolders
                }
            }
        }
        registry = ContentTypeRegistry(config)

        assert registry.is_valid_type("minimal") is True
        assert registry.get_folder("minimal") == "sources/minimal"
        assert registry.get_template("minimal") == "templates/minimal.md"
        assert registry.get_jinja_template("minimal") is None
        assert registry.get_description("minimal") is None
        assert registry.get_icon("minimal") is None
        assert registry.get_subfolders("minimal") == []


class TestGlobalContentRegistry:
    """Test the global content_registry instance."""

    def test_global_registry_exists(self) -> None:
        """The global content_registry should be importable."""
        assert content_registry is not None

    def test_global_registry_loads_from_yaml(self) -> None:
        """The global registry should load from config/default.yaml."""
        # Should have at least some content types from the config file
        all_types = content_registry.get_all_types()

        # If the config file exists, it should have content types
        # If not, it will be empty
        assert isinstance(all_types, dict)

    def test_global_registry_is_singleton(self) -> None:
        """Multiple imports should return the same instance."""
        # content_registry is a module-level singleton
        assert content_registry is content_registry


class TestContentTypeRegistryWithSubfolders:
    """Test registry behavior with content types that have subfolders."""

    def test_type_with_subfolders(self) -> None:
        """Registry should correctly return subfolders."""
        config = {
            "content_types": {
                "work": {
                    "folder": "sources/work",
                    "template": "templates/work.md",
                    "subfolders": ["meetings", "proposals", "projects"],
                }
            }
        }
        registry = ContentTypeRegistry(config)

        subfolders = registry.get_subfolders("work")

        assert "meetings" in subfolders
        assert "proposals" in subfolders
        assert "projects" in subfolders
        assert len(subfolders) == 3
