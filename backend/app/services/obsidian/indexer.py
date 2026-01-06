"""
Folder Index Generator

Auto-generates index notes (_index.md) for content folders in the Obsidian vault.
These index notes improve vault navigation by providing:
- A summary of notes in each folder
- Quick links to recent notes (sorted by processed date)
- An overview of all notes when the folder contains many items

Index files use the "_index.md" naming convention (underscore prefix) so they
appear at the top of folder listings in Obsidian and are excluded from
content searches and other index generations.

Usage:
    from app.services.obsidian import FolderIndexer, get_vault_manager

    vault = get_vault_manager()
    indexer = FolderIndexer(vault)

    # Generate index for a specific folder
    await indexer.generate_index(vault.vault_path / "sources/papers")

    # Regenerate all indices for content type folders
    result = await indexer.regenerate_all_indices()
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import logging

import aiofiles
import frontmatter

from app.content_types import content_registry
from app.services.obsidian.links import WikilinkBuilder
from app.services.obsidian.vault import VaultManager

logger = logging.getLogger(__name__)


class FolderIndexer:
    """
    Generates and maintains folder index notes for Obsidian vault navigation.

    Index notes (_index.md) are auto-generated markdown files that provide:
    - A count of notes in the folder
    - "Recent" section: wikilinks to the 10 most recently processed notes
    - "All Notes" section: wikilinks to remaining notes (if > 10 total)

    The generated index includes YAML frontmatter with:
    - type: "index" (for Dataview queries)
    - folder: the folder name
    - generated: date when the index was created/updated

    Notes are sorted by their "processed" frontmatter field (newest first).
    Notes without frontmatter or with parsing errors are still included
    using the filename as the title.

    Attributes:
        INDEX_FILENAME: The standard filename for index notes ("_index.md")
        vault: Reference to the VaultManager for path resolution
    """

    INDEX_FILENAME = "_index.md"

    def __init__(self, vault: VaultManager):
        """
        Initialize the indexer with a vault reference.

        Args:
            vault: VaultManager instance for vault path resolution
        """
        self.vault = vault

    async def generate_index(self, folder: Path, recursive: bool = False) -> str:
        """
        Generate an index note (_index.md) for a folder.

        Scans the folder for markdown files, extracts frontmatter metadata,
        and creates a navigable index with wikilinks. Files starting with
        underscore (like _index.md itself) are excluded.

        Args:
            folder: Absolute path to the folder to index
            recursive: If True, includes notes from all subfolders;
                      if False (default), only indexes direct children

        Returns:
            Absolute path to the created/updated index file

        Note:
            - Notes with invalid frontmatter are still indexed using filename as title
            - Empty folders get a placeholder index with "No notes yet" message
            - Existing index files are overwritten without warning
        """
        notes = list(folder.rglob("*.md") if recursive else folder.glob("*.md"))
        notes = [n for n in notes if not n.name.startswith("_")]

        if not notes:
            return await self._write_empty_index(folder)

        entries = []
        for note_path in notes:
            try:
                async with aiofiles.open(note_path, "r", encoding="utf-8") as f:
                    content = await f.read()

                post = frontmatter.loads(content)
                entries.append(
                    {
                        "path": note_path,
                        "title": post.get("title", note_path.stem),
                        "type": post.get("type", "note"),
                        "tags": post.get("tags", []),
                        "processed": post.get("processed"),
                        "created": post.get("created"),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to parse {note_path}: {e}")
                entries.append(
                    {
                        "path": note_path,
                        "title": note_path.stem,
                        "type": "note",
                    }
                )

        # Sort by processed date (newest first)
        entries.sort(key=lambda x: x.get("processed") or "", reverse=True)

        index_content = self._render_index(folder, entries)

        index_path = folder / self.INDEX_FILENAME
        async with aiofiles.open(index_path, "w", encoding="utf-8") as f:
            await f.write(index_content)

        logger.info(f"Generated index: {index_path} ({len(entries)} notes)")
        return str(index_path)

    def _render_index(self, folder: Path, entries: list[dict]) -> str:
        """
        Render the index markdown content from parsed entries.

        Args:
            folder: The folder being indexed (used for header/metadata)
            entries: List of dicts with keys: path, title, type, tags, processed, created

        Returns:
            Complete markdown string with frontmatter and wikilinks
        """
        folder_name = folder.name.replace("-", " ").title()

        lines = [
            "---",
            "type: index",
            f"folder: {folder.name}",
            f"generated: {datetime.now().strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {folder_name}",
            "",
            f"*{len(entries)} notes*",
            "",
            "## Recent",
            "",
        ]

        # Add recent notes
        for entry in entries[:10]:
            link = WikilinkBuilder.link(entry["title"])
            lines.append(f"- {link}")

        if len(entries) > 10:
            lines.extend(["", "## All Notes", ""])
            for entry in entries[10:]:
                link = WikilinkBuilder.link(entry["title"])
                lines.append(f"- {link}")

        return "\n".join(lines)

    async def _write_empty_index(self, folder: Path) -> str:
        """
        Write a placeholder index for a folder with no markdown files.

        Args:
            folder: The empty folder to create an index for

        Returns:
            Absolute path to the created index file
        """
        folder_name = folder.name.replace("-", " ").title()

        content = f"""---
type: index
folder: {folder.name}
generated: {datetime.now().strftime('%Y-%m-%d')}
---

# {folder_name}

*No notes yet*
"""

        index_path = folder / self.INDEX_FILENAME
        async with aiofiles.open(index_path, "w", encoding="utf-8") as f:
            await f.write(content)

        return str(index_path)

    async def regenerate_all_indices(self) -> dict:
        """
        Regenerate index notes for all content type folders defined in config.

        Iterates through all content types from ContentTypeRegistry and
        generates an index for each folder that exists in the vault.
        Useful for bulk updates after imports or vault restructuring.

        Returns:
            Dict with:
                - regenerated: list of folder paths that were indexed
                - count: total number of indices regenerated
        """
        regenerated = []
        all_types = content_registry.get_all_types()

        for type_key, type_config in all_types.items():
            folder_name = type_config.get("folder")
            if folder_name:
                folder_path = self.vault.vault_path / folder_name
                if folder_path.exists():
                    await self.generate_index(folder_path)
                    regenerated.append(folder_name)

        logger.info(f"Regenerated {len(regenerated)} folder indices")
        return {"regenerated": regenerated, "count": len(regenerated)}

