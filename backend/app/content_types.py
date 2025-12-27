"""
Content Type Registry

This module provides a dynamic registry for content types loaded from config/default.yaml.
It allows the ingestion system to dynamically handle any content type without code changes.

Usage:
    from app.content_types import content_registry

    # Get all content types
    all_types = content_registry.get_all_types()

    # Get folder for a type
    folder = content_registry.get_folder("paper")  # "sources/papers"

    # Validate a type exists
    if content_registry.is_valid_type("paper"):
        ...
"""

from typing import Any, Optional

from app.config import yaml_config


class ContentTypeRegistry:
    """Registry for content types loaded from configuration."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._content_types: dict[str, dict[str, Any]] = config.get("content_types", {})

    def get_all_types(self) -> dict[str, dict[str, Any]]:
        """Get all content types."""
        return self._content_types

    def get_user_types(self) -> dict[str, dict[str, Any]]:
        """Get content types that are user-selectable (not system types)."""
        return {
            key: config
            for key, config in self._content_types.items()
            if not config.get("system", False)
        }

    def get_folder(self, content_type: str) -> Optional[str]:
        """Get the vault folder for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("folder")
        return None

    def get_template(self, content_type: str) -> Optional[str]:
        """Get the Obsidian template path for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("template")
        return None

    def get_jinja_template(self, content_type: str) -> Optional[str]:
        """Get the Jinja2 template filename for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("jinja_template")
        return None

    def get_subfolders(self, content_type: str) -> list[str]:
        """Get subfolders for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("subfolders", [])
        return []

    def is_valid_type(self, content_type: str) -> bool:
        """Check if a content type exists in the registry."""
        return content_type in self._content_types

    def get_description(self, content_type: str) -> Optional[str]:
        """Get the description for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("description")
        return None

    def get_icon(self, content_type: str) -> Optional[str]:
        """Get the icon emoji for a content type."""
        type_config = self._content_types.get(content_type)
        if type_config:
            return type_config.get("icon")
        return None


# Global registry instance
content_registry = ContentTypeRegistry(yaml_config)
