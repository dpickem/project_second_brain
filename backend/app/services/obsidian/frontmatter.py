"""
Frontmatter Utilities

Provides utilities for creating and parsing YAML frontmatter in Obsidian notes:
- FrontmatterBuilder: Fluent builder API for frontmatter creation
- Parsing utilities for reading existing frontmatter
- Update utilities for modifying frontmatter in existing notes
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any
import yaml
import frontmatter
from pathlib import Path
import aiofiles
import logging

logger = logging.getLogger(__name__)


class FrontmatterBuilder:
    """Builder for Obsidian-compatible YAML frontmatter."""

    def __init__(self):
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> FrontmatterBuilder:
        """Set a frontmatter field."""
        if value is not None:
            self._data[key] = value
        return self

    def set_type(self, content_type: str) -> FrontmatterBuilder:
        """Set the note type."""
        return self.set("type", content_type)

    def set_title(self, title: str) -> FrontmatterBuilder:
        """Set the note title."""
        return self.set("title", title)

    def set_authors(self, authors: list[str]) -> FrontmatterBuilder:
        """Set authors list."""
        if authors:
            return self.set("authors", authors)
        return self

    def set_tags(self, tags: list[str]) -> FrontmatterBuilder:
        """Set tags list."""
        if tags:
            return self.set("tags", tags)
        return self

    def set_date(
        self, key: str, dt: datetime | date | str | None
    ) -> FrontmatterBuilder:
        """Set a date field."""
        if dt is None:
            return self
        if isinstance(dt, datetime):
            return self.set(key, dt.strftime("%Y-%m-%d"))
        if isinstance(dt, date):
            return self.set(key, dt.strftime("%Y-%m-%d"))
        return self.set(key, str(dt))

    def set_created(self, dt: datetime | None = None) -> FrontmatterBuilder:
        """Set created date."""
        return self.set_date("created", dt or datetime.now())

    def set_processed(self, dt: datetime | None = None) -> FrontmatterBuilder:
        """Set processed date."""
        return self.set_date("processed", dt or datetime.now())

    def set_status(self, status: str) -> FrontmatterBuilder:
        """Set note status."""
        valid = {"unread", "reading", "read", "reviewed", "archived", "processed"}
        if status in valid:
            return self.set("status", status)
        return self.set("status", "unread")

    def set_source(
        self,
        url: str | None = None,
        doi: str | None = None,
        isbn: str | None = None,
    ) -> FrontmatterBuilder:
        """Set source information."""
        if url:
            self.set("source", url)
        if doi:
            self.set("doi", doi)
        if isbn:
            self.set("isbn", isbn)
        return self

    def set_domain(self, domain: str) -> FrontmatterBuilder:
        """Set content domain."""
        return self.set("domain", domain)

    def set_complexity(self, complexity: str) -> FrontmatterBuilder:
        """Set complexity level."""
        valid = {"foundational", "intermediate", "advanced"}
        if complexity in valid:
            return self.set("complexity", complexity)
        return self

    def set_custom(self, **kwargs) -> FrontmatterBuilder:
        """Set custom fields."""
        for key, value in kwargs.items():
            if value is not None:
                self._data[key] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the frontmatter dictionary."""
        return self._data.copy()

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        return yaml.dump(
            self._data, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

    def to_frontmatter(self) -> str:
        """Convert to complete frontmatter block with delimiters."""
        if not self._data:
            return ""
        return f"---\n{self.to_yaml()}---\n"


async def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


async def parse_frontmatter_file(path: Path) -> tuple[dict, str]:
    """Parse frontmatter from a markdown file."""
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    return await parse_frontmatter(content)


async def update_frontmatter(
    path: Path, updates: dict[str, Any], remove_keys: list[str] | None = None
) -> None:
    """Update frontmatter in an existing note.

    Args:
        path: Path to the note file
        updates: Dictionary of fields to update
        remove_keys: List of keys to remove
    """
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()

    post = frontmatter.loads(content)

    # Apply updates
    for key, value in updates.items():
        if value is not None:
            post.metadata[key] = value

    # Remove keys
    if remove_keys:
        for key in remove_keys:
            post.metadata.pop(key, None)

    # Write back
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(frontmatter.dumps(post))


def frontmatter_to_string(metadata: dict, content: str) -> str:
    """Convert frontmatter dict and content to full markdown string."""
    post = frontmatter.Post(content=content, **metadata)
    return frontmatter.dumps(post)
