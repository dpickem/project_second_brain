"""
Vault Manager Service

Central service for managing the Obsidian vault filesystem structure and operations.
Acts as the single point of access for all vault-related file operations, ensuring
consistent path handling, safe file operations, and proper folder structure.

Key Responsibilities:
    - Vault structure initialization (idempotent ensure_structure())
    - Path resolution using ContentTypeRegistry for folder mappings
    - Safe filename sanitization for cross-platform compatibility
    - Async file I/O for reading and writing notes
    - Vault statistics and discovery

Design Principles:
    - Idempotent operations: ensure_structure() is safe to call multiple times
    - Single source of truth: Uses ContentTypeRegistry for all folder mappings
    - Cross-platform: Sanitizes filenames for Windows/macOS/Linux compatibility
    - Async-first: All I/O operations are async for FastAPI compatibility

Folder Structure (from config/default.yaml):
    vault/
    ├── sources/           # Ingested content by type
    │   ├── papers/
    │   ├── articles/
    │   ├── books/
    │   └── ...
    ├── concepts/          # Extracted concepts (atomic notes)
    ├── daily/             # Daily notes
    ├── topics/            # Topic index notes
    ├── exercises/         # Practice problems
    ├── reviews/           # Spaced repetition queue
    ├── templates/         # Obsidian templates
    ├── meta/              # Dashboards, config
    └── assets/            # Images, PDFs

Usage:
    from app.services.obsidian.vault import get_vault_manager

    vault = get_vault_manager()

    # Ensure structure exists (idempotent)
    await vault.ensure_structure()

    # Get folder for a content type
    papers_folder = vault.get_source_folder("paper")

    # Write a note
    path = await vault.get_unique_path(papers_folder, "My Paper Title")
    await vault.write_note(path, content)

    # Get vault statistics
    stats = await vault.get_vault_stats()
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, TypedDict

import aiofiles
import aiofiles.os

from app.config.settings import settings, yaml_config
from app.content_types import content_registry

logger = logging.getLogger(__name__)


class VaultStructureResult(TypedDict):
    """Return type for ensure_structure() method."""

    created: list[str]
    """Folder paths that were created."""
    existed: list[str]
    """Folder paths that already existed."""
    total: int
    """Total folder count (created + existed)."""


class VaultManager:
    """
    Central manager for Obsidian vault structure and file operations.

    This class provides a unified interface for all vault filesystem operations,
    ensuring consistent handling of paths, filenames, and folder structures.
    It's designed to be used as a singleton via get_vault_manager().

    Key Features:
        - Idempotent structure initialization (safe to call repeatedly)
        - ContentTypeRegistry integration for folder mappings
        - Cross-platform filename sanitization
        - Async file I/O operations
        - Vault discovery and statistics

    Thread Safety:
        File operations are async but not locked. For concurrent writes to the
        same file, external coordination is required. The VaultWatcher handles
        this by debouncing rapid changes.

    Attributes:
        vault_path: Absolute Path to the Obsidian vault root directory

    Raises:
        ValueError: If vault_path doesn't exist or isn't a directory
    """

    def __init__(self, vault_path: str | None = None):
        """
        Initialize the vault manager.

        Args:
            vault_path: Path to Obsidian vault. If None, uses settings.OBSIDIAN_VAULT_PATH.
                       Supports ~ expansion for home directory.

        Raises:
            ValueError: If the vault path doesn't exist or isn't a directory
        """
        self.vault_path = Path(vault_path or settings.OBSIDIAN_VAULT_PATH).expanduser()
        self._validate_vault_path()

    def _validate_vault_path(self):
        """
        Validate that vault path exists and is accessible.

        Called during __init__ to fail fast if the vault is misconfigured.

        Raises:
            ValueError: If path doesn't exist or isn't a directory
        """
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault_path}")

    async def ensure_structure(self) -> VaultStructureResult:
        """
        Ensure the vault folder structure exists (idempotent).

        Creates the complete folder hierarchy needed for the knowledge system:
        1. System folders from config/default.yaml (obsidian.system_folders)
        2. Content type folders from ContentTypeRegistry (sources/papers, etc.)
        3. Subfolders defined per content type

        All folder definitions come from config - no hardcoded paths.

        This method is idempotent - safe to call multiple times. Existing folders
        are left untouched; only missing folders are created.

        Typical usage:
            - Called during app startup to ensure vault is ready
            - Called via API endpoint to repair vault structure
            - Safe to call after adding new content types to config

        Returns:
            Dict with:
                - created: List of folder paths that were created
                - existed: List of folder paths that already existed
                - total: Total folder count
        """
        created = []
        existed = []

        # Get system folders from config (obsidian.system_folders in default.yaml)
        obsidian_config = yaml_config.get("obsidian", {})
        system_folders = obsidian_config.get("system_folders", [])

        # Ensure system folders exist
        for folder in system_folders:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                await aiofiles.os.makedirs(folder_path, exist_ok=True)
                created.append(folder)
            else:
                existed.append(folder)

        # Ensure content type folders from ContentTypeRegistry exist
        all_types = content_registry.get_all_types()
        for type_key, type_config in all_types.items():
            # Ensure base folder exists
            base_folder = type_config.get("folder")
            if base_folder:
                folder_path = self.vault_path / base_folder
                if not folder_path.exists():
                    await aiofiles.os.makedirs(folder_path, exist_ok=True)
                    created.append(base_folder)
                else:
                    existed.append(base_folder)

                # Ensure subfolders exist if defined
                for subfolder in type_config.get("subfolders", []):
                    subfolder_path = f"{base_folder}/{subfolder}"
                    full_path = self.vault_path / subfolder_path
                    if not full_path.exists():
                        await aiofiles.os.makedirs(full_path, exist_ok=True)
                        created.append(subfolder_path)
                    else:
                        existed.append(subfolder_path)

        logger.info(
            f"Vault structure check: {len(created)} folders created, "
            f"{len(existed)} already existed"
        )
        return {
            "created": created,
            "existed": existed,
            "total": len(created) + len(existed),
        }

    def get_source_folder(self, content_type: str) -> Path:
        """
        Get the appropriate source folder for a content type.

        Looks up the folder mapping from ContentTypeRegistry. Falls back to
        sources/ideas for unknown types (fleeting notes).

        Args:
            content_type: Type key (e.g., "paper", "article", "book")

        Returns:
            Absolute Path to the content type's folder
        """
        folder = content_registry.get_folder(content_type)
        if folder:
            return self.vault_path / folder
        return self.vault_path / "sources/ideas"

    def get_concept_folder(self) -> Path:
        """
        Get the concepts folder path.

        Concepts are atomic knowledge notes extracted from source content.
        Defaults to "concepts" if not configured.

        Returns:
            Absolute Path to the concepts folder
        """
        folder = content_registry.get_folder("concept")
        return self.vault_path / (folder or "concepts")

    def get_daily_folder(self) -> Path:
        """
        Get the daily notes folder path.

        Daily notes provide a date-based journal and inbox for quick captures.
        Defaults to "daily" if not configured.

        Returns:
            Absolute Path to the daily notes folder
        """
        folder = content_registry.get_folder("daily")
        return self.vault_path / (folder or "daily")

    def get_template_folder(self) -> Path:
        """
        Get the Obsidian templates folder path.

        Templates are used by both Obsidian's Templater plugin and the
        backend's Jinja2 rendering for note generation.
        Folder path from config/default.yaml: obsidian.templates.folder

        Returns:
            Absolute Path to the templates folder
        """
        obsidian_config = yaml_config.get("obsidian", {})
        templates_config = obsidian_config.get("templates", {})
        folder = templates_config.get("folder", "templates")
        return self.vault_path / folder

    def sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """
        Convert a title to a safe cross-platform filename.

        Removes characters that are invalid on Windows (<>:"/\\|?*),
        collapses whitespace, and truncates to max_length while preserving
        word boundaries.

        Args:
            title: The title to convert
            max_length: Maximum filename length (default 100 for path safety)

        Returns:
            Sanitized filename (without .md extension)

        Examples:
            "My Paper: A Study" → "My Paper A Study"
            "What is AI?" → "What is AI"
        """
        safe = re.sub(r'[<>:"/\\|?*]', "", title)
        safe = re.sub(r"\s+", " ", safe).strip()
        if len(safe) > max_length:
            safe = safe[:max_length].rsplit(" ", 1)[0]
        return safe or "Untitled"

    async def note_exists(self, folder: Path, title: str) -> bool:
        """
        Check if a note with this title already exists.

        Uses sanitize_filename() to match the actual filename that would
        be created for the given title.

        Args:
            folder: Folder to check in
            title: Note title (will be sanitized)

        Returns:
            True if a note with this title exists, False otherwise
        """
        filename = self.sanitize_filename(title)
        path = folder / f"{filename}.md"
        return path.exists()

    async def get_unique_path(self, folder: Path, title: str) -> Path:
        """
        Get a unique file path, adding a counter suffix if needed.

        If "My Paper.md" exists, returns "My Paper_1.md", then "My Paper_2.md", etc.
        Useful for avoiding overwrites when ingesting content with duplicate titles.

        Args:
            folder: Target folder for the note
            title: Desired title (will be sanitized)

        Returns:
            Path that doesn't already exist
        """
        filename = self.sanitize_filename(title)
        path = folder / f"{filename}.md"

        counter = 1
        while path.exists():
            path = folder / f"{filename}_{counter}.md"
            counter += 1

        return path

    def get_path_for_update(
        self, folder: Path, title: str, existing_path: Optional[str] = None
    ) -> Path:
        """
        Get the path to use for updating/creating a note.

        Unlike get_unique_path(), this method is designed for reprocessing scenarios
        where we want to UPDATE an existing note rather than create a new one.

        Priority:
        1. If existing_path is provided, use it (for reprocessing the same content)
        2. If a note with this title already exists (no suffix), return that path
        3. Otherwise, return the base path (no suffix) for new notes

        This prevents creating duplicate files like "Paper_1.md", "Paper_2.md" etc.
        when reprocessing the same content multiple times.

        Args:
            folder: Target folder for the note
            title: Desired title (will be sanitized)
            existing_path: Optional existing vault path from database

        Returns:
            Path to write to (may or may not already exist)
        """
        # If we have an existing path from DB, use it (preserves location on reprocess)
        if existing_path:
            full_existing = self.vault_path / existing_path
            if full_existing.exists():
                logger.debug(f"Using existing path for update: {full_existing}")
                return full_existing

        # Check for base filename (without suffix)
        filename = self.sanitize_filename(title)
        base_path = folder / f"{filename}.md"

        if base_path.exists():
            logger.debug(f"Found existing note to update: {base_path}")
            return base_path

        # New note - use base path
        logger.debug(f"Creating new note at: {base_path}")
        return base_path

    async def write_note(self, path: Path, content: str) -> Path:
        """
        Write note content to file.

        Creates parent directories if they don't exist.
        Overwrites existing file without warning.

        Args:
            path: Full path including filename
            content: Complete markdown content (including frontmatter)

        Returns:
            The path that was written to
        """
        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)
        logger.debug(f"Wrote note: {path}")
        return path

    async def read_note(self, path: Path) -> str:
        """
        Read note content from file.

        Args:
            path: Full path to the note

        Returns:
            Complete file content as string

        Raises:
            FileNotFoundError: If the note doesn't exist
        """
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()

    async def list_notes(self, folder: Path, recursive: bool = False) -> list[Path]:
        """
        List all markdown notes in a folder.

        Args:
            folder: Folder to search
            recursive: If True, includes notes in subfolders

        Returns:
            List of absolute Paths to .md files
        """
        if recursive:
            return list(folder.rglob("*.md"))
        return list(folder.glob("*.md"))

    async def get_vault_stats(self) -> dict:
        """
        Get statistics about the vault.

        Counts notes by content type using the folder mappings from
        ContentTypeRegistry. Useful for dashboard displays and health checks.

        Returns:
            Dict with:
                - total_notes: Total count across all types
                - by_type: Dict mapping content type → note count
        """
        stats = {"total_notes": 0, "by_type": {}}

        all_types = content_registry.get_all_types()
        for type_key, type_config in all_types.items():
            folder = type_config.get("folder")
            if folder:
                folder_path = self.vault_path / folder
                if folder_path.exists():
                    notes = list(folder_path.rglob("*.md"))
                    count = len(notes)
                    stats["by_type"][type_key] = count
                    stats["total_notes"] += count

        return stats


# ─────────────────────────────────────────────────────────────
# Singleton Access
# ─────────────────────────────────────────────────────────────

_vault_manager: Optional[VaultManager] = None


def get_vault_manager() -> VaultManager:
    """
    Get or create the singleton VaultManager instance.

    The singleton pattern ensures all code uses the same vault configuration
    and avoids repeatedly validating the vault path.

    Returns:
        Shared VaultManager instance

    Raises:
        ValueError: If OBSIDIAN_VAULT_PATH is not configured or invalid
    """
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultManager()
    return _vault_manager


def create_vault_manager(vault_path: str, validate: bool = True) -> VaultManager:
    """
    Create a VaultManager for a specific path with optional validation.

    Unlike get_vault_manager(), this creates a new instance (not singleton)
    and allows disabling validation for setup scripts that create the vault.

    Args:
        vault_path: Path to the vault (supports ~ expansion)
        validate: If True, raises ValueError if path doesn't exist.
                 If False, skips validation (for initial setup).

    Returns:
        New VaultManager instance

    Usage (setup script):
        # Create vault directory first
        Path(vault_path).mkdir(parents=True, exist_ok=True)
        vault = create_vault_manager(vault_path, validate=True)
        await vault.ensure_structure()
    """
    if validate:
        return VaultManager(vault_path)

    # Create without validation for setup scripts
    manager = object.__new__(VaultManager)
    manager.vault_path = Path(vault_path).expanduser()
    return manager


def reset_vault_manager() -> None:
    """
    Reset the singleton vault manager.

    Used primarily for testing to ensure a fresh instance.
    Also useful if vault path changes at runtime.
    """
    global _vault_manager
    _vault_manager = None
