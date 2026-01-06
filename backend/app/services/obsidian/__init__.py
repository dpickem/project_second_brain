"""
Obsidian Vault Services

This module provides services for managing the Obsidian vault:
- VaultManager: Vault structure and file operations
- FrontmatterBuilder: YAML frontmatter creation and parsing
- WikilinkBuilder: Wikilink creation and extraction
- FolderIndexer: Auto-generated folder indices
- DailyNoteGenerator: Daily note creation
- VaultWatcher: File change monitoring
- VaultSyncService: Neo4j synchronization

Usage:
    from app.services.obsidian import (
        get_vault_manager,
        FrontmatterBuilder,
        WikilinkBuilder,
        VaultSyncService,
    )
"""

from app.services.obsidian.vault import VaultManager, get_vault_manager, create_vault_manager
from app.services.obsidian.frontmatter import (
    FrontmatterBuilder,
    parse_frontmatter,
    parse_frontmatter_file,
    update_frontmatter,
)
from app.services.obsidian.links import (
    WikilinkBuilder,
    extract_wikilinks,
    extract_tags,
    generate_connection_section,
    auto_link_concepts,
    validate_links,
)
from app.services.obsidian.indexer import FolderIndexer
from app.services.obsidian.daily import DailyNoteGenerator
from app.services.obsidian.dataview_queries import DataviewLibrary, generate_dashboard_queries
from app.services.obsidian.watcher import VaultWatcher, VaultEventHandler
from app.services.obsidian.sync import VaultSyncService, get_sync_status
from app.services.obsidian.lifecycle import (
    startup_vault_services,
    shutdown_vault_services,
    get_watcher_status,
)

__all__ = [
    # Vault management
    "VaultManager",
    "get_vault_manager",
    "create_vault_manager",
    # Frontmatter
    "FrontmatterBuilder",
    "parse_frontmatter",
    "parse_frontmatter_file",
    "update_frontmatter",
    # Links
    "WikilinkBuilder",
    "extract_wikilinks",
    "extract_tags",
    "generate_connection_section",
    "auto_link_concepts",
    "validate_links",
    # Automation
    "FolderIndexer",
    "DailyNoteGenerator",
    "DataviewLibrary",
    "generate_dashboard_queries",
    # Sync
    "VaultWatcher",
    "VaultEventHandler",
    "VaultSyncService",
    "get_sync_status",
    # Lifecycle
    "startup_vault_services",
    "shutdown_vault_services",
    "get_watcher_status",
]

