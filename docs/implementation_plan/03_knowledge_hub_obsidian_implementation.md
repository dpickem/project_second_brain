# Knowledge Hub (Obsidian) Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Updated**: January 2026  
> **Target Phase**: Phase 4 (Weeks 11-14 per roadmap)  
> **Design Doc**: `design_docs/03_knowledge_hub_obsidian.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Knowledge Hub (Obsidian) component, which serves as the primary user-facing knowledge storage and interface. All processed content from the LLM Processing Layer ultimately becomes Markdown notes in the Obsidian vault, enabling local-first ownership, powerful search, and integration with the Obsidian plugin ecosystem.

### Implementation Status

**IMPORTANT**: Significant portions of this phase were implemented as part of Phase 2 (Ingestion) and Phase 3 (LLM Processing). This updated plan reflects what's already complete and what remains.

| Component | Status | Location |
|-----------|--------|----------|
| ContentTypeRegistry | ✅ Complete | `backend/app/content_types.py` |
| Jinja2 Templates | ✅ Complete | `config/templates/*.md.j2` |
| Basic Note Generator | ✅ Complete | `backend/app/services/processing/output/obsidian_generator.py` |
| Neo4j Node Generator | ✅ Complete | `backend/app/services/processing/output/neo4j_generator.py` |
| Tag Taxonomy Loader | ✅ Complete | `backend/app/services/processing/stages/taxonomy_loader.py` |
| VaultManager Service | 🔲 Not Started | `backend/app/services/obsidian/vault.py` |
| Frontmatter Utilities | 🔲 Not Started | `backend/app/services/obsidian/frontmatter.py` |
| Wikilink Utilities | 🔲 Not Started | `backend/app/services/obsidian/links.py` |
| Folder Indexer | 🔲 Not Started | `backend/app/services/obsidian/indexer.py` |
| Daily Note Generator | 🔲 Not Started | `backend/app/services/obsidian/daily.py` |
| Vault File Watcher | 🔲 Not Started | `backend/app/services/obsidian/watcher.py` |
| Neo4j Sync Service | 🔲 Not Started | `backend/app/services/obsidian/sync.py` |
| Startup Lifecycle | 🔲 Not Started | `backend/app/services/obsidian/lifecycle.py` |
| Vault API Endpoints | 🔲 Not Started | `backend/app/routers/vault.py` |

### Architecture Overview

The Knowledge Hub bridges the backend processing system with the user's Obsidian vault:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LLM Processing │────▶│  Note Generator  │────▶│  Obsidian Vault │
│     Result      │     │  (✅ Complete)   │     │   (Markdown)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                            ┌──────────────────┐        │
                            │   Vault Watcher  │◀───────┘
                            │  (🔲 Phase 4)    │
                            └──────────────────┘
                                    │
                            ┌───────▼───────┐
                            │    Neo4j      │
                            │  Knowledge    │
                            │    Graph      │
                            └───────────────┘
```

### Sync Strategy

**Important**: The vault watcher only detects changes made while the app is running. To handle changes made while offline (e.g., user edits in Obsidian when the backend is not running), we implement a **three-tier sync strategy**:

| Scenario | Mechanism | When Triggered |
|----------|-----------|----------------|
| App is running | `VaultWatcher` (real-time events) | File system events |
| App just started | `reconcile_on_startup()` (compare mtimes) | FastAPI startup hook |
| Manual trigger | `full_sync()` (sync everything) | API endpoint call |

```
┌─────────────────────────────────────────────────────────────────┐
│                        App Lifecycle                            │
├─────────────────────────────────────────────────────────────────┤
│  STARTUP                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. reconcile_on_startup()                               │   │
│  │    - Compare file mtimes vs last_sync_time              │   │
│  │    - Sync only changed files to Neo4j                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  RUNNING                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. VaultWatcher (real-time)                             │   │
│  │    - Detect file changes via OS events                  │   │
│  │    - Debounce rapid changes                             │   │
│  │    - Sync each changed file to Neo4j                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  SHUTDOWN                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. Store last_sync_time in database                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Scope (Updated)

| In Scope (Phase 4 Remaining) | Already Complete (Phase 2/3) |
|------------------------------|------------------------------|
| VaultManager service class | ContentTypeRegistry |
| Frontmatter utilities module | Jinja2 templates (all 13 types) |
| Wikilink utilities module | Basic note generation |
| Folder index auto-generation | Neo4j node creation |
| Daily note automation | Tag taxonomy loading |
| Vault file change watcher | Processing pipeline integration |
| Startup reconciliation (offline changes) | Template rendering |
| Bi-directional Neo4j sync | Filename sanitization |
| Vault API endpoints | |
| Dataview query library | |

| Out of Scope |
|--------------|
| Obsidian plugin development |
| Custom Obsidian themes |
| Third-party plugin configuration |
| Real-time collaborative editing |
| Mobile Obsidian sync (Obsidian Sync) |
| Obsidian Publish integration |
| Full-text search (Obsidian native) |
| Graph view customization |

---

## 2. Prerequisites

### 2.1 Infrastructure (From Phase 1-3) — ✅ Complete

- [x] Docker Compose environment
- [x] FastAPI backend skeleton
- [x] PostgreSQL for metadata
- [x] Neo4j for knowledge graph
- [x] Celery task queue
- [x] LLM Processing Layer (Phase 3)
- [x] Configured vault path in environment
- [x] ContentTypeRegistry loaded from `config/default.yaml`
- [x] Tag taxonomy loaded from `config/tag-taxonomy.yaml`

### 2.2 Already Implemented Dependencies

These packages are already in `backend/requirements.txt`:

```txt
jinja2>=3.1.0              # ✅ Template rendering (used by obsidian_generator)
aiofiles>=24.1.0           # ✅ Async file operations
PyYAML>=6.0                # ✅ YAML processing
python-frontmatter>=1.1.0  # ✅ YAML frontmatter parsing
```

### 2.3 New Dependencies for Phase 4

```txt
# Add to backend/requirements.txt
watchdog>=4.0.0            # File system monitoring for vault changes
python-slugify>=8.0.0      # Safe filename generation (replaces manual sanitization)
python-dateutil>=2.9.0     # Date parsing utilities
```

### 2.4 Environment Variables (Already Configured)

```bash
# These are already in .env from Phase 1-3
OBSIDIAN_VAULT_PATH=/path/to/vault

# New variables for Phase 4
VAULT_WATCH_ENABLED=true                  # Enable file watcher
VAULT_SYNC_DEBOUNCE_MS=1000               # Debounce for rapid changes
VAULT_SYNC_NEO4J_ENABLED=true             # Sync changes to Neo4j
```

---

## 3. Existing Implementations (Reference)

This section documents what's already been built in Phase 2/3 that Phase 4 builds upon.

### 3.1 ContentTypeRegistry (✅ Complete)

**Location**: `backend/app/content_types.py`

The ContentTypeRegistry loads content types from `config/default.yaml` and provides methods for folder lookup, template mapping, and validation.

```python
# Usage example
from app.content_types import content_registry

folder = content_registry.get_folder("paper")  # "sources/papers"
template = content_registry.get_jinja_template("paper")  # "paper.md.j2"
is_valid = content_registry.is_valid_type("paper")  # True
```

### 3.2 Obsidian Note Generator (✅ Complete)

**Location**: `backend/app/services/processing/output/obsidian_generator.py`

The note generator:
- Loads Jinja2 templates from `config/templates/`
- Selects template based on content type
- Prepares template data from `ProcessingResult`
- Writes notes to vault with duplicate handling
- Uses ContentTypeRegistry for folder mapping

```python
# Usage
from app.services.processing.output.obsidian_generator import generate_obsidian_note

path = await generate_obsidian_note(content, result)
```

### 3.3 Jinja2 Templates (✅ Complete)

**Location**: `config/templates/`

All 13 content type templates exist:
- `article.md.j2`, `book.md.j2`, `career.md.j2`, `code.md.j2`
- `concept.md.j2`, `daily.md.j2`, `exercise.md.j2`, `idea.md.j2`
- `paper.md.j2`, `personal.md.j2`, `project.md.j2`, `reflection.md.j2`, `work.md.j2`

### 3.4 Tag Taxonomy Loader (✅ Complete)

**Location**: `backend/app/services/processing/stages/taxonomy_loader.py`

Loads tag taxonomy from `config/tag-taxonomy.yaml` with caching.

---

## 4. Implementation Phases (Remaining Work)

### Phase 4A: Enhanced Vault Management (Week 11)

#### Task 4A.1: Project Structure Setup

Create the dedicated Obsidian services module:

```
backend/
├── app/
│   ├── services/
│   │   ├── obsidian/                 # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── vault.py              # VaultManager class
│   │   │   ├── frontmatter.py        # FrontmatterBuilder utilities
│   │   │   ├── links.py              # Wikilink handling
│   │   │   ├── indexer.py            # Folder index generation
│   │   │   ├── daily.py              # Daily note generation
│   │   │   ├── watcher.py            # File change monitoring
│   │   │   ├── sync.py               # Neo4j synchronization + reconciliation
│   │   │   └── lifecycle.py          # Startup/shutdown lifecycle management
│   │   ├── processing/
│   │   │   └── output/
│   │   │       ├── obsidian_generator.py  # ✅ EXISTS
│   │   │       └── neo4j_generator.py     # ✅ EXISTS
│   ├── routers/
│   │   └── vault.py                  # NEW: Vault API endpoints
│   ├── config/
│   │   └── obsidian.py               # NEW: Obsidian-specific settings
│   ├── models/
│   │   └── system.py                 # NEW: SystemMeta for last_sync_time
```

**Deliverables:**
- [ ] Create `backend/app/services/obsidian/` directory
- [ ] Create `__init__.py` with proper exports
- [ ] Create `backend/app/config/obsidian.py` for settings

**Estimated Time:** 1 hour

---

#### Task 4A.2: VaultManager Service

**Why this matters:** While basic note writing exists in `obsidian_generator.py`, a comprehensive VaultManager provides vault-wide operations: structure initialization, validation, note listing, and safe file operations. This centralizes vault logic and enables features like folder indexing and daily notes.

```python
# backend/app/services/obsidian/vault.py

from pathlib import Path
from typing import Optional
import aiofiles
import aiofiles.os
import logging
import re

from app.config.settings import settings
from app.content_types import content_registry

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages Obsidian vault structure and file operations.
    
    Complements the existing obsidian_generator.py by providing:
    - Vault structure initialization
    - Vault validation
    - Note listing and discovery
    - Safe file operations
    - Path utilities
    
    Uses ContentTypeRegistry for folder mappings.
    """
    
    def __init__(self, vault_path: str = None):
        self.vault_path = Path(vault_path or settings.OBSIDIAN_VAULT_PATH)
        self._validate_vault_path()
    
    def _validate_vault_path(self):
        """Validate that vault path exists and is accessible."""
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault_path}")
    
    async def ensure_structure(self) -> dict:
        """Ensure the vault folder structure exists (idempotent).
        
        Creates only missing folders defined in config/default.yaml content_types.
        Safe to call multiple times - existing folders are left untouched.
        
        This is a no-op for folders that already exist.
        
        Returns:
            Dict with created and existing folder counts
        """
        created = []
        existed = []
        
        # System folders (ensure they exist)
        system_folders = [
            "topics",
            "exercises/by-topic",
            "exercises/daily",
            "reviews/due",
            "reviews/archive",
            "templates",
            "meta",
            "assets/images",
            "assets/pdfs",
        ]
        
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
        
        logger.info(f"Vault structure check: {len(created)} folders created, {len(existed)} already existed")
        return {"created": created, "existed": existed, "total": len(created) + len(existed)}
    
    def get_source_folder(self, content_type: str) -> Path:
        """Get the appropriate source folder for a content type."""
        folder = content_registry.get_folder(content_type)
        if folder:
            return self.vault_path / folder
        return self.vault_path / "sources/ideas"
    
    def get_concept_folder(self) -> Path:
        """Get the concepts folder path."""
        folder = content_registry.get_folder("concept")
        return self.vault_path / (folder or "concepts")
    
    def get_daily_folder(self) -> Path:
        """Get the daily notes folder path."""
        folder = content_registry.get_folder("daily")
        return self.vault_path / (folder or "daily")
    
    def get_template_folder(self) -> Path:
        """Get the templates folder path."""
        return self.vault_path / "templates"
    
    def sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """Convert title to safe filename."""
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', ' ', safe).strip()
        if len(safe) > max_length:
            safe = safe[:max_length].rsplit(' ', 1)[0]
        return safe or "Untitled"
    
    async def note_exists(self, folder: Path, title: str) -> bool:
        """Check if a note with this title already exists."""
        filename = self.sanitize_filename(title)
        path = folder / f"{filename}.md"
        return path.exists()
    
    async def get_unique_path(self, folder: Path, title: str) -> Path:
        """Get a unique file path, adding counter if needed."""
        filename = self.sanitize_filename(title)
        path = folder / f"{filename}.md"
        
        counter = 1
        while path.exists():
            path = folder / f"{filename}_{counter}.md"
            counter += 1
        
        return path
    
    async def write_note(self, path: Path, content: str) -> Path:
        """Write note content to file."""
        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)
        logger.debug(f"Wrote note: {path}")
        return path
    
    async def read_note(self, path: Path) -> str:
        """Read note content from file."""
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()
    
    async def list_notes(self, folder: Path, recursive: bool = False) -> list[Path]:
        """List all markdown notes in a folder."""
        if recursive:
            return list(folder.rglob("*.md"))
        return list(folder.glob("*.md"))
    
    async def get_vault_stats(self) -> dict:
        """Get statistics about the vault."""
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


# Singleton instance
_vault_manager: Optional[VaultManager] = None


def get_vault_manager() -> VaultManager:
    """Get or create singleton vault manager."""
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultManager()
    return _vault_manager
```

**Deliverables:**
- [ ] `VaultManager` class with idempotent `ensure_structure()` method
- [ ] Path utilities using `ContentTypeRegistry`
- [ ] Safe file read/write operations
- [ ] Vault statistics method
- [ ] Unit tests for vault operations

**Estimated Time:** 3 hours

---

#### Task 4A.3: Frontmatter Utilities

**Why this matters:** A dedicated frontmatter module provides a fluent builder API and utilities for parsing/updating frontmatter in existing notes. This enables the vault watcher to read metadata and the sync service to update it.

```python
# backend/app/services/obsidian/frontmatter.py

from datetime import datetime, date
from typing import Any, Optional
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
    
    def set(self, key: str, value: Any) -> "FrontmatterBuilder":
        """Set a frontmatter field."""
        if value is not None:
            self._data[key] = value
        return self
    
    def set_type(self, content_type: str) -> "FrontmatterBuilder":
        """Set the note type."""
        return self.set("type", content_type)
    
    def set_title(self, title: str) -> "FrontmatterBuilder":
        """Set the note title."""
        return self.set("title", title)
    
    def set_authors(self, authors: list[str]) -> "FrontmatterBuilder":
        """Set authors list."""
        if authors:
            return self.set("authors", authors)
        return self
    
    def set_tags(self, tags: list[str]) -> "FrontmatterBuilder":
        """Set tags list."""
        if tags:
            return self.set("tags", tags)
        return self
    
    def set_date(self, key: str, dt: datetime | date | str) -> "FrontmatterBuilder":
        """Set a date field."""
        if dt is None:
            return self
        if isinstance(dt, datetime):
            return self.set(key, dt.strftime("%Y-%m-%d"))
        if isinstance(dt, date):
            return self.set(key, dt.strftime("%Y-%m-%d"))
        return self.set(key, str(dt))
    
    def set_created(self, dt: datetime = None) -> "FrontmatterBuilder":
        """Set created date."""
        return self.set_date("created", dt or datetime.now())
    
    def set_processed(self, dt: datetime = None) -> "FrontmatterBuilder":
        """Set processed date."""
        return self.set_date("processed", dt or datetime.now())
    
    def set_status(self, status: str) -> "FrontmatterBuilder":
        """Set note status."""
        valid = {"unread", "reading", "read", "reviewed", "archived", "processed"}
        if status in valid:
            return self.set("status", status)
        return self.set("status", "unread")
    
    def set_source(self, url: str = None, doi: str = None, isbn: str = None) -> "FrontmatterBuilder":
        """Set source information."""
        if url:
            self.set("source", url)
        if doi:
            self.set("doi", doi)
        if isbn:
            self.set("isbn", isbn)
        return self
    
    def set_domain(self, domain: str) -> "FrontmatterBuilder":
        """Set content domain."""
        return self.set("domain", domain)
    
    def set_complexity(self, complexity: str) -> "FrontmatterBuilder":
        """Set complexity level."""
        valid = {"foundational", "intermediate", "advanced"}
        if complexity in valid:
            return self.set("complexity", complexity)
        return self
    
    def set_custom(self, **kwargs) -> "FrontmatterBuilder":
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
            self._data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
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
    path: Path,
    updates: dict[str, Any],
    remove_keys: list[str] = None
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
```

**Deliverables:**
- [ ] `FrontmatterBuilder` fluent builder class
- [ ] Frontmatter parsing utilities
- [ ] Frontmatter update utility
- [ ] Unit tests for YAML generation and parsing

**Estimated Time:** 2 hours

---

#### Task 4A.4: Wikilink Utilities

**Why this matters:** Wikilinks are the backbone of Obsidian's knowledge graph. Proper link handling enables connection extraction for Neo4j sync, auto-linking concepts, and broken link detection.

```python
# backend/app/services/obsidian/links.py

import re
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WikilinkBuilder:
    """Builder for Obsidian wikilinks."""
    
    @staticmethod
    def link(target: str, alias: str = None) -> str:
        """Create a standard wikilink.
        
        Args:
            target: Target note name or path
            alias: Optional display text
        
        Returns:
            Wikilink string like [[target]] or [[target|alias]]
        """
        if alias:
            return f"[[{target}|{alias}]]"
        return f"[[{target}]]"
    
    @staticmethod
    def header_link(note: str, header: str, alias: str = None) -> str:
        """Create a link to a specific header."""
        target = f"{note}#{header}"
        return WikilinkBuilder.link(target, alias)
    
    @staticmethod
    def block_link(note: str, block_id: str, alias: str = None) -> str:
        """Create a link to a specific block."""
        target = f"{note}#^{block_id}"
        return WikilinkBuilder.link(target, alias)
    
    @staticmethod
    def embed(target: str) -> str:
        """Create an embedded note/image link."""
        return f"![[{target}]]"


def extract_wikilinks(content: str) -> list[str]:
    """Extract all wikilinks from markdown content.
    
    Returns:
        List of linked note names (without [[]])
    """
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    matches = re.findall(pattern, content)
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for match in matches:
        note_name = match.split("#")[0]  # Strip header/block references
        if note_name and note_name not in seen:
            seen.add(note_name)
            unique.append(note_name)
    
    return unique


def extract_tags(content: str) -> list[str]:
    """Extract all inline tags from markdown content."""
    pattern = r'(?<!\[)#([a-zA-Z][\w/-]*)'
    matches = re.findall(pattern, content)
    return list(set(matches))


def generate_connection_section(connections: list[dict]) -> str:
    """Generate a connections section with wikilinks.
    
    Args:
        connections: List of connection dicts with target_title and explanation
    
    Returns:
        Markdown section with wikilinks
    """
    if not connections:
        return "*No connections found*"
    
    lines = []
    for conn in connections:
        target = conn.get("target_title", "Unknown")
        explanation = conn.get("explanation", "")
        relationship = conn.get("relationship_type", "RELATES_TO")
        
        link = WikilinkBuilder.link(target)
        
        if explanation:
            lines.append(f"- {link} — {explanation}")
        else:
            lines.append(f"- {link} ({relationship})")
    
    return "\n".join(lines)


def auto_link_concepts(
    content: str,
    known_concepts: list[str],
    exclude_in_links: bool = True
) -> str:
    """Auto-link known concepts in content.
    
    Args:
        content: Markdown content to process
        known_concepts: List of concept names to link
        exclude_in_links: Don't link text that's already in a wikilink
    
    Returns:
        Content with concepts converted to wikilinks
    """
    concepts = sorted(known_concepts, key=len, reverse=True)
    
    for concept in concepts:
        if not concept:
            continue
        
        pattern = rf'(?<!\[\[)(?<!\|)\b({re.escape(concept)})\b(?!\]\])(?!\|)'
        
        def replace(match):
            return f"[[{match.group(1)}]]"
        
        content = re.sub(pattern, replace, content, flags=re.IGNORECASE)
    
    return content


def validate_links(content: str, vault_notes: set[str]) -> list[str]:
    """Find broken wikilinks (links to non-existent notes).
    
    Returns:
        List of broken link targets
    """
    links = extract_wikilinks(content)
    broken = [link for link in links if link not in vault_notes]
    return broken
```

**Deliverables:**
- [ ] `WikilinkBuilder` for creating various link types
- [ ] Wikilink extraction from content
- [ ] Tag extraction from content
- [ ] Connection section generation
- [ ] Auto-linking for known concepts
- [ ] Broken link validation
- [ ] Unit tests for link operations

**Estimated Time:** 2 hours

---

### Phase 4B: Automation Features (Week 12)

#### Task 4B.1: Folder Index Generator

**Why this matters:** Auto-generated indices make vault navigation easier. Each folder gets an `_index.md` that lists its contents, grouped and sorted for quick access.

```python
# backend/app/services/obsidian/indexer.py

from pathlib import Path
from datetime import datetime
import frontmatter
import aiofiles
import logging

from app.services.obsidian.vault import VaultManager
from app.services.obsidian.links import WikilinkBuilder

logger = logging.getLogger(__name__)


class FolderIndexer:
    """Generates and maintains folder index notes."""
    
    INDEX_FILENAME = "_index.md"
    
    def __init__(self, vault: VaultManager):
        self.vault = vault
    
    async def generate_index(self, folder: Path, recursive: bool = False) -> str:
        """Generate an index note for a folder.
        
        Args:
            folder: Folder to index
            recursive: Whether to include notes from subfolders
        
        Returns:
            Path to created index file
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
                entries.append({
                    "path": note_path,
                    "title": post.get("title", note_path.stem),
                    "type": post.get("type", "note"),
                    "tags": post.get("tags", []),
                    "processed": post.get("processed"),
                    "created": post.get("created"),
                })
            except Exception as e:
                logger.warning(f"Failed to parse {note_path}: {e}")
                entries.append({
                    "path": note_path,
                    "title": note_path.stem,
                    "type": "note",
                })
        
        # Sort by processed date (newest first)
        entries.sort(key=lambda x: x.get("processed") or "", reverse=True)
        
        index_content = self._render_index(folder, entries)
        
        index_path = folder / self.INDEX_FILENAME
        async with aiofiles.open(index_path, "w", encoding="utf-8") as f:
            await f.write(index_content)
        
        logger.info(f"Generated index: {index_path} ({len(entries)} notes)")
        return str(index_path)
    
    def _render_index(self, folder: Path, entries: list[dict]) -> str:
        """Render the index content."""
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
            link = WikilinkBuilder.link(entry['title'])
            lines.append(f"- {link}")
        
        if len(entries) > 10:
            lines.extend(["", "## All Notes", ""])
            for entry in entries[10:]:
                link = WikilinkBuilder.link(entry['title'])
                lines.append(f"- {link}")
        
        return "\n".join(lines)
    
    async def _write_empty_index(self, folder: Path) -> str:
        """Write an empty index for a folder with no notes."""
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
        """Regenerate indices for all content type folders."""
        regenerated = []
        
        from app.content_types import content_registry
        all_types = content_registry.get_all_types()
        
        for type_key, type_config in all_types.items():
            folder_name = type_config.get("folder")
            if folder_name:
                folder_path = self.vault.vault_path / folder_name
                if folder_path.exists():
                    await self.generate_index(folder_path)
                    regenerated.append(folder_name)
        
        return {"regenerated": regenerated, "count": len(regenerated)}
```

**Deliverables:**
- [ ] `FolderIndexer` class with metadata parsing
- [ ] Index generation with sorting by date
- [ ] `regenerate_all_indices` method
- [ ] Unit tests

**Estimated Time:** 3 hours

---

#### Task 4B.2: Daily Note Generator

**Why this matters:** Daily notes provide a consistent entry point for captures, learning activities, and reflections. The template is loaded from `config/templates/daily.md.j2`.

```python
# backend/app/services/obsidian/daily.py

from datetime import date, datetime
from pathlib import Path
import aiofiles
import aiofiles.os
import logging

from jinja2 import Environment, FileSystemLoader

from app.services.obsidian.vault import VaultManager
from app.config.settings import TEMPLATES_DIR

logger = logging.getLogger(__name__)


class DailyNoteGenerator:
    """Generates daily notes using template from config/templates/daily.md.j2."""
    
    def __init__(self, vault: VaultManager):
        self.vault = vault
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )
    
    async def generate_daily_note(self, target_date: date = None) -> str:
        """Generate a daily note for the given date.
        
        Args:
            target_date: Date for the note (defaults to today)
        
        Returns:
            Path to the created/existing note
        """
        target_date = target_date or date.today()
        daily_folder = self.vault.get_daily_folder()
        await aiofiles.os.makedirs(daily_folder, exist_ok=True)
        
        filename = target_date.strftime("%Y-%m-%d.md")
        note_path = daily_folder / filename
        
        # Don't overwrite existing daily notes
        if note_path.exists():
            logger.debug(f"Daily note already exists: {note_path}")
            return str(note_path)
        
        # Render from template
        try:
            template = self._env.get_template("daily.md.j2")
            context = {
                "date_iso": target_date.strftime("%Y-%m-%d"),
                "date_full": target_date.strftime("%A, %B %d, %Y"),
                "date": target_date,
                "year": target_date.year,
                "month": target_date.strftime("%B"),
                "day": target_date.day,
                "weekday": target_date.strftime("%A"),
            }
            content = template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render daily template: {e}")
            # Fallback to basic template
            content = self._basic_daily_template(target_date)
        
        async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
            await f.write(content)
        
        logger.info(f"Created daily note: {note_path}")
        return str(note_path)
    
    def _basic_daily_template(self, target_date: date) -> str:
        """Fallback basic daily template."""
        return f"""---
type: daily
date: {target_date.strftime("%Y-%m-%d")}
---

# {target_date.strftime("%A, %B %d, %Y")}

## 📥 Inbox


## 📚 Learning
- [ ] Complete review queue

## ✅ Tasks
- [ ] 

## 📝 Journal

"""
    
    async def add_inbox_item(self, target_date: date, item: str) -> None:
        """Add an item to the inbox section of a daily note.
        
        Creates the daily note if it doesn't exist.
        """
        note_path = Path(await self.generate_daily_note(target_date))
        
        content = await self.vault.read_note(note_path)
        
        # Find inbox section and append item
        inbox_marker = "## 📥 Inbox"
        if inbox_marker in content:
            parts = content.split(inbox_marker, 1)
            if len(parts) == 2:
                parts[1] = f"\n- {item}" + parts[1]
                content = inbox_marker.join(parts)
                await self.vault.write_note(note_path, content)
                logger.debug(f"Added inbox item to {note_path}")
```

**Deliverables:**
- [ ] `DailyNoteGenerator` using Jinja2 template
- [ ] Fallback template if `daily.md.j2` fails
- [ ] `add_inbox_item` method for quick captures
- [ ] Unit tests

**Estimated Time:** 2 hours

---

#### Task 4B.3: Dataview Query Library

**Why this matters:** Pre-built Dataview queries power dynamic dashboards and help users get immediate value from their vault.

```python
# backend/app/services/obsidian/dataview.py

"""
Library of Dataview query snippets for Obsidian notes.

These queries are designed to be embedded in generated notes
(dashboards, indexes) to create dynamic content.
"""


class DataviewLibrary:
    """Collection of useful Dataview queries."""
    
    @staticmethod
    def recent_notes(folder: str = "sources", limit: int = 10) -> str:
        """Query for recent notes in a folder."""
        return f'''```dataview
TABLE title as "Title", tags as "Tags", processed as "Processed"
FROM "{folder}"
WHERE processed
SORT processed DESC
LIMIT {limit}
```'''
    
    @staticmethod
    def unread_by_type(content_type: str) -> str:
        """Query for unread notes of a specific type."""
        return f'''```dataview
LIST
FROM "sources"
WHERE type = "{content_type}" AND (status = "unread" OR !status)
SORT created DESC
```'''
    
    @staticmethod
    def open_tasks() -> str:
        """Query for all incomplete tasks across vault."""
        return '''```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
GROUP BY file.link
LIMIT 50
```'''
    
    @staticmethod
    def knowledge_stats() -> str:
        """Query for note counts by type."""
        return '''```dataview
TABLE WITHOUT ID
  type as "Type",
  length(rows) as "Count"
FROM "sources"
GROUP BY type
SORT length(rows) DESC
```'''
    
    @staticmethod
    def notes_by_domain(domain: str) -> str:
        """Query for notes in a specific domain."""
        return f'''```dataview
TABLE title as "Title", complexity as "Level", processed as "Date"
FROM "sources"
WHERE domain = "{domain}"
SORT processed DESC
```'''
    
    @staticmethod
    def mastery_questions() -> str:
        """Query for notes with mastery questions."""
        return '''```dataview
LIST
FROM "sources"
WHERE contains(file.content, "## Mastery Questions")
SORT processed DESC
LIMIT 20
```'''
    
    @staticmethod
    def concepts_index() -> str:
        """Query for all concept notes."""
        return '''```dataview
TABLE WITHOUT ID
  file.link as "Concept",
  domain as "Domain",
  complexity as "Level"
FROM "concepts"
SORT file.name ASC
```'''


def generate_dashboard_queries() -> dict[str, str]:
    """Generate all queries needed for the main dashboard."""
    return {
        "recent": DataviewLibrary.recent_notes(limit=10),
        "unread_papers": DataviewLibrary.unread_by_type("paper"),
        "unread_articles": DataviewLibrary.unread_by_type("article"),
        "tasks": DataviewLibrary.open_tasks(),
        "stats": DataviewLibrary.knowledge_stats(),
        "concepts": DataviewLibrary.concepts_index(),
    }
```

**Deliverables:**
- [ ] `DataviewLibrary` class with common queries
- [ ] Dashboard query generator
- [ ] Documentation of query patterns

**Estimated Time:** 1 hour

---

### Phase 4C: Synchronization (Week 13)

#### Task 4C.1: Vault File Watcher

**Why this matters:** Detects user edits in Obsidian and syncs changes back to the backend (Neo4j graph updates, tag sync, etc.).

```python
# backend/app/services/obsidian/watcher.py

from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
import asyncio
import logging
import threading
import time

logger = logging.getLogger(__name__)


class VaultEventHandler(FileSystemEventHandler):
    """Handles file system events in the vault."""
    
    def __init__(
        self,
        vault_path: Path,
        on_change: Callable[[Path], None],
        debounce_ms: int = 1000
    ):
        self.vault_path = vault_path
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self._pending: dict[str, float] = {}
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        # Ignore .obsidian directory
        if "/.obsidian/" in event.src_path or "\\.obsidian\\" in event.src_path:
            return
        
        self._schedule_callback(Path(event.src_path))
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        if "/.obsidian/" in event.src_path or "\\.obsidian\\" in event.src_path:
            return
        
        self._schedule_callback(Path(event.src_path))
    
    def _schedule_callback(self, path: Path):
        """Schedule a debounced callback for a file change."""
        with self._lock:
            self._pending[str(path)] = time.time()
            
            # Cancel existing timer
            if self._timer:
                self._timer.cancel()
            
            # Schedule new timer
            self._timer = threading.Timer(
                self.debounce_ms / 1000.0,
                self._process_pending
            )
            self._timer.start()
    
    def _process_pending(self):
        """Process all pending file changes."""
        with self._lock:
            paths = list(self._pending.keys())
            self._pending.clear()
        
        for path_str in paths:
            try:
                self.on_change(Path(path_str))
            except Exception as e:
                logger.error(f"Error processing change for {path_str}: {e}")


class VaultWatcher:
    """Watches the Obsidian vault for file changes."""
    
    def __init__(
        self,
        vault_path: str,
        on_change: Callable[[Path], None] = None,
        debounce_ms: int = 1000
    ):
        self.vault_path = Path(vault_path)
        self.on_change = on_change or self._default_handler
        self.debounce_ms = debounce_ms
        self._observer: Optional[Observer] = None
        self._running = False
    
    def _default_handler(self, path: Path):
        """Default change handler that logs changes."""
        logger.info(f"File changed: {path}")
    
    def start(self):
        """Start watching the vault."""
        if self._running:
            logger.warning("Vault watcher already running")
            return
        
        handler = VaultEventHandler(
            self.vault_path,
            self.on_change,
            self.debounce_ms
        )
        
        self._observer = Observer()
        self._observer.schedule(handler, str(self.vault_path), recursive=True)
        self._observer.start()
        self._running = True
        
        logger.info(f"Started vault watcher: {self.vault_path}")
    
    def stop(self):
        """Stop watching the vault."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._running = False
        logger.info("Stopped vault watcher")
    
    @property
    def is_running(self) -> bool:
        return self._running
```

**Deliverables:**
- [ ] `VaultEventHandler` with debouncing
- [ ] `VaultWatcher` lifecycle management
- [ ] Ignore `.obsidian/` directory
- [ ] Unit tests

**Estimated Time:** 3 hours

---

#### Task 4C.2: Neo4j Sync Service

**Why this matters:** When users edit notes in Obsidian (add links, change tags), those changes should sync to Neo4j to keep the knowledge graph current. This service also handles **startup reconciliation** to detect changes made while the app was offline.

```python
# backend/app/services/obsidian/sync.py

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import aiofiles
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.obsidian.links import extract_wikilinks, extract_tags
from app.services.obsidian.frontmatter import parse_frontmatter_file
from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.db.session import get_async_session
from app.models.system import SystemMeta  # Stores last_sync_time

logger = logging.getLogger(__name__)


class VaultSyncService:
    """Syncs vault changes to Neo4j knowledge graph.
    
    Implements three sync modes:
    1. sync_note() - Single note sync (used by watcher)
    2. reconcile_on_startup() - Sync changes made while offline
    3. full_sync() - Complete vault sync (manual trigger)
    """
    
    LAST_SYNC_KEY = "vault_last_sync_time"
    
    def __init__(self, neo4j_client: Neo4jClient = None):
        self._neo4j = neo4j_client
    
    @property
    def neo4j(self) -> Neo4jClient:
        if self._neo4j is None:
            self._neo4j = get_neo4j_client()
        return self._neo4j
    
    # ─────────────────────────────────────────────────────────────
    # Startup Reconciliation - Handle offline changes
    # ─────────────────────────────────────────────────────────────
    
    async def reconcile_on_startup(self, vault_path: Path) -> dict:
        """Detect and sync changes made while app was offline.
        
        Compares file modification times against last known sync time.
        This should be called during FastAPI startup.
        
        Args:
            vault_path: Path to the Obsidian vault
        
        Returns:
            Dict with reconciliation results
        """
        last_sync = await self._get_last_sync_time()
        
        notes = list(vault_path.rglob("*.md"))
        notes = [n for n in notes if ".obsidian" not in str(n)]
        
        # Find notes modified since last sync
        modified_since_sync = []
        for note_path in notes:
            try:
                mtime = datetime.fromtimestamp(
                    note_path.stat().st_mtime,
                    tz=timezone.utc
                )
                if last_sync is None or mtime > last_sync:
                    modified_since_sync.append(note_path)
            except OSError as e:
                logger.warning(f"Could not stat {note_path}: {e}")
        
        results = {
            "total_notes": len(notes),
            "modified_since_sync": len(modified_since_sync),
            "synced": 0,
            "failed": 0,
            "last_sync": last_sync.isoformat() if last_sync else None,
        }
        
        # Sync only the changed files
        for note_path in modified_since_sync:
            result = await self.sync_note(note_path)
            if "error" in result:
                results["failed"] += 1
            else:
                results["synced"] += 1
        
        # Update last sync time
        await self._update_last_sync_time()
        
        logger.info(
            f"Startup reconciliation: {results['synced']}/{results['modified_since_sync']} "
            f"modified notes synced (checked {results['total_notes']} total)"
        )
        
        return results
    
    async def _get_last_sync_time(self) -> Optional[datetime]:
        """Get the last vault sync timestamp from database."""
        async with get_async_session() as session:
            result = await session.execute(
                select(SystemMeta).where(SystemMeta.key == self.LAST_SYNC_KEY)
            )
            row = result.scalar_one_or_none()
            if row and row.value:
                return datetime.fromisoformat(row.value)
        return None
    
    async def _update_last_sync_time(self) -> None:
        """Update the last vault sync timestamp in database."""
        now = datetime.now(timezone.utc)
        async with get_async_session() as session:
            result = await session.execute(
                select(SystemMeta).where(SystemMeta.key == self.LAST_SYNC_KEY)
            )
            row = result.scalar_one_or_none()
            if row:
                row.value = now.isoformat()
            else:
                session.add(SystemMeta(key=self.LAST_SYNC_KEY, value=now.isoformat()))
            await session.commit()
    
    # ─────────────────────────────────────────────────────────────
    # Single Note Sync - Used by watcher for real-time updates
    # ─────────────────────────────────────────────────────────────
    
    async def sync_note(self, note_path: Path) -> dict:
        """Sync a single note to Neo4j.
        
        Extracts:
        - Frontmatter metadata (title, type, tags)
        - Outgoing wikilinks
        - Inline tags
        
        Updates the corresponding node in Neo4j.
        
        Args:
            note_path: Path to the note file
        
        Returns:
            Dict with sync results
        """
        try:
            # Parse note
            fm, body = await parse_frontmatter_file(note_path)
            
            # Extract links and tags
            outgoing_links = extract_wikilinks(body)
            inline_tags = extract_tags(body)
            
            # Combine frontmatter tags with inline tags
            all_tags = list(set(fm.get("tags", []) + inline_tags))
            
            # Determine node ID (use title or filename)
            node_id = fm.get("id") or note_path.stem
            title = fm.get("title", note_path.stem)
            note_type = fm.get("type", "note")
            
            # Update Neo4j node
            await self._update_neo4j_node(
                node_id=node_id,
                title=title,
                note_type=note_type,
                tags=all_tags,
                metadata=fm
            )
            
            # Sync outgoing links
            await self._sync_links(node_id, outgoing_links)
            
            logger.info(f"Synced note to Neo4j: {note_path.name}")
            
            return {
                "path": str(note_path),
                "node_id": node_id,
                "links_synced": len(outgoing_links),
                "tags": all_tags,
            }
            
        except Exception as e:
            logger.error(f"Failed to sync note {note_path}: {e}")
            return {
                "path": str(note_path),
                "error": str(e),
            }
    
    async def _update_neo4j_node(
        self,
        node_id: str,
        title: str,
        note_type: str,
        tags: list[str],
        metadata: dict
    ):
        """Update or create a node in Neo4j."""
        query = """
        MERGE (n:Note {id: $node_id})
        SET n.title = $title,
            n.type = $note_type,
            n.tags = $tags,
            n.updated_at = datetime()
        RETURN n.id
        """
        
        async with self.neo4j.get_session() as session:
            await session.run(
                query,
                node_id=node_id,
                title=title,
                note_type=note_type,
                tags=tags
            )
    
    async def _sync_links(self, source_id: str, targets: list[str]):
        """Sync outgoing links for a note.
        
        Creates LINKS_TO relationships for each wikilink.
        """
        # First, clear existing LINKS_TO relationships
        clear_query = """
        MATCH (source:Note {id: $source_id})-[r:LINKS_TO]->()
        DELETE r
        """
        
        # Then create new relationships
        create_query = """
        MATCH (source:Note {id: $source_id})
        MERGE (target:Note {id: $target_id})
        ON CREATE SET target.title = $target_id
        MERGE (source)-[r:LINKS_TO]->(target)
        SET r.synced_at = datetime()
        """
        
        async with self.neo4j.get_session() as session:
            await session.run(clear_query, source_id=source_id)
            
            for target in targets:
                await session.run(
                    create_query,
                    source_id=source_id,
                    target_id=target
                )
    
    # ─────────────────────────────────────────────────────────────
    # Full Sync - Manual trigger via API
    # ─────────────────────────────────────────────────────────────
    
    async def full_sync(self, vault_path: Path) -> dict:
        """Sync all notes in the vault to Neo4j.
        
        Warning: This can be slow for large vaults.
        Use reconcile_on_startup() for routine syncing.
        """
        notes = list(vault_path.rglob("*.md"))
        notes = [n for n in notes if ".obsidian" not in str(n)]
        
        results = {"synced": 0, "failed": 0, "errors": []}
        
        for note_path in notes:
            result = await self.sync_note(note_path)
            if "error" in result:
                results["failed"] += 1
                results["errors"].append(result)
            else:
                results["synced"] += 1
        
        # Update last sync time after full sync
        await self._update_last_sync_time()
        
        logger.info(f"Full sync complete: {results['synced']} synced, {results['failed']} failed")
        return results
```

**Deliverables:**
- [ ] `VaultSyncService` class with three sync modes
- [ ] `reconcile_on_startup()` for offline change detection
- [ ] `SystemMeta` model for storing last sync time (or reuse existing)
- [ ] Note metadata extraction and sync
- [ ] Link relationship sync
- [ ] Full vault sync method
- [ ] Integration tests

**Estimated Time:** 5 hours

---

#### Task 4C.3: Startup Lifecycle Integration

**Why this matters:** Integrates the vault watcher and sync service into the FastAPI application lifecycle, ensuring offline changes are detected on startup and real-time watching begins automatically.

```python
# backend/app/services/obsidian/lifecycle.py

import asyncio
import logging
from typing import Optional

from app.config.settings import settings
from app.services.obsidian.vault import get_vault_manager
from app.services.obsidian.sync import VaultSyncService
from app.services.obsidian.watcher import VaultWatcher

logger = logging.getLogger(__name__)

# Module-level state for watcher
_vault_watcher: Optional[VaultWatcher] = None
_sync_service: Optional[VaultSyncService] = None


async def startup_vault_services() -> dict:
    """Initialize vault services on application startup.
    
    1. Reconcile changes made while app was offline
    2. Start real-time file watcher
    
    Returns:
        Dict with startup results
    """
    global _vault_watcher, _sync_service
    
    results = {
        "reconciliation": None,
        "watcher_started": False,
    }
    
    try:
        vault = get_vault_manager()
        _sync_service = VaultSyncService()
        
        # Step 1: Reconcile offline changes
        if settings.VAULT_SYNC_NEO4J_ENABLED:
            logger.info("Starting vault reconciliation...")
            results["reconciliation"] = await _sync_service.reconcile_on_startup(
                vault.vault_path
            )
            logger.info(
                f"Reconciliation complete: {results['reconciliation']['synced']} notes synced"
            )
        
        # Step 2: Start real-time watcher
        if settings.VAULT_WATCH_ENABLED:
            def on_file_change(path):
                """Handle file changes by scheduling async sync."""
                if _sync_service and settings.VAULT_SYNC_NEO4J_ENABLED:
                    # Schedule the async sync in the event loop
                    asyncio.create_task(_sync_service.sync_note(path))
            
            _vault_watcher = VaultWatcher(
                vault_path=str(vault.vault_path),
                on_change=on_file_change,
                debounce_ms=settings.VAULT_SYNC_DEBOUNCE_MS
            )
            _vault_watcher.start()
            results["watcher_started"] = True
            logger.info(f"Vault watcher started: {vault.vault_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to start vault services: {e}")
        raise


async def shutdown_vault_services() -> None:
    """Clean up vault services on application shutdown."""
    global _vault_watcher, _sync_service
    
    if _vault_watcher:
        _vault_watcher.stop()
        _vault_watcher = None
        logger.info("Vault watcher stopped")
    
    # Update last sync time on shutdown
    if _sync_service and settings.VAULT_SYNC_NEO4J_ENABLED:
        await _sync_service._update_last_sync_time()
        logger.info("Updated last sync time")
    
    _sync_service = None


def get_watcher_status() -> dict:
    """Get current status of vault watcher."""
    return {
        "watcher_running": _vault_watcher.is_running if _vault_watcher else False,
        "sync_enabled": settings.VAULT_SYNC_NEO4J_ENABLED,
        "watch_enabled": settings.VAULT_WATCH_ENABLED,
    }
```

**Integration with FastAPI main.py:**

```python
# backend/app/main.py (add to existing file)

from contextlib import asynccontextmanager
from app.services.obsidian.lifecycle import (
    startup_vault_services,
    shutdown_vault_services
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    
    # Initialize vault services (watcher + sync)
    try:
        vault_results = await startup_vault_services()
        logger.info(f"Vault services initialized: {vault_results}")
    except Exception as e:
        logger.warning(f"Vault services failed to start: {e}")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")
    await shutdown_vault_services()


# Update FastAPI app initialization
app = FastAPI(
    title="Second Brain API",
    lifespan=lifespan,  # Use lifespan instead of on_event
)
```

**Deliverables:**
- [ ] `lifecycle.py` module with startup/shutdown functions
- [ ] Integration with FastAPI lifespan context manager
- [ ] Proper async handling for watcher callbacks
- [ ] Graceful shutdown with sync time update
- [ ] Status endpoint integration

**Estimated Time:** 2 hours

---

### Phase 4D: API Endpoints (Week 14)

#### Task 4D.1: Vault API Router

**Why this matters:** Exposes vault operations to the frontend and external systems via REST API.

```python
# backend/app/routers/vault.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pathlib import Path

from app.services.obsidian.vault import get_vault_manager, VaultManager
from app.services.obsidian.indexer import FolderIndexer
from app.services.obsidian.daily import DailyNoteGenerator
from app.services.obsidian.sync import VaultSyncService

router = APIRouter(prefix="/api/vault", tags=["vault"])


class DailyNoteRequest(BaseModel):
    date: Optional[str] = None  # ISO format: YYYY-MM-DD


class InboxItemRequest(BaseModel):
    item: str
    date: Optional[str] = None


@router.get("/status")
async def get_vault_status():
    """Get vault status and statistics."""
    try:
        vault = get_vault_manager()
        stats = await vault.get_vault_stats()
        return {
            "status": "healthy",
            "vault_path": str(vault.vault_path),
            "exists": vault.vault_path.exists(),
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-structure")
async def ensure_vault_structure():
    """Ensure vault folder structure exists (idempotent).
    
    Creates any missing folders. Safe to call multiple times.
    """
    try:
        vault = get_vault_manager()
        result = await vault.ensure_structure()
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indices/regenerate")
async def regenerate_indices(background_tasks: BackgroundTasks):
    """Regenerate all folder indices."""
    vault = get_vault_manager()
    indexer = FolderIndexer(vault)
    
    # Run in background for large vaults
    background_tasks.add_task(indexer.regenerate_all_indices)
    
    return {"status": "regenerating", "message": "Index regeneration started"}


@router.post("/daily")
async def create_daily_note(request: DailyNoteRequest = None):
    """Create a daily note."""
    vault = get_vault_manager()
    daily_gen = DailyNoteGenerator(vault)
    
    target_date = None
    if request and request.date:
        try:
            target_date = date.fromisoformat(request.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    path = await daily_gen.generate_daily_note(target_date)
    return {"status": "created", "path": path}


@router.post("/daily/inbox")
async def add_inbox_item(request: InboxItemRequest):
    """Add an item to today's daily note inbox."""
    if not request.item:
        raise HTTPException(status_code=400, detail="Item cannot be empty")
    
    vault = get_vault_manager()
    daily_gen = DailyNoteGenerator(vault)
    
    target_date = date.today()
    if request.date:
        try:
            target_date = date.fromisoformat(request.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    await daily_gen.add_inbox_item(target_date, request.item)
    return {"status": "added", "date": target_date.isoformat()}


@router.post("/sync")
async def sync_vault_to_neo4j(background_tasks: BackgroundTasks):
    """Sync entire vault to Neo4j (runs in background)."""
    vault = get_vault_manager()
    sync_service = VaultSyncService()
    
    background_tasks.add_task(sync_service.full_sync, vault.vault_path)
    
    return {"status": "syncing", "message": "Full vault sync started"}


@router.get("/folders")
async def list_folders():
    """List all content type folders in the vault."""
    from app.content_types import content_registry
    
    vault = get_vault_manager()
    folders = []
    
    all_types = content_registry.get_all_types()
    for type_key, type_config in all_types.items():
        folder = type_config.get("folder")
        if folder:
            folder_path = vault.vault_path / folder
            folders.append({
                "type": type_key,
                "folder": folder,
                "exists": folder_path.exists(),
                "icon": type_config.get("icon", "📄"),
            })
    
    return {"folders": folders}
```

**Deliverables:**
- [ ] `/status` endpoint
- [ ] `/ensure-structure` endpoint (idempotent)
- [ ] `/indices/regenerate` endpoint
- [ ] `/daily` endpoint
- [ ] `/daily/inbox` endpoint
- [ ] `/sync` endpoint
- [ ] `/folders` endpoint
- [ ] Unit tests for all endpoints

**Estimated Time:** 3 hours

---

#### Task 4D.2: Obsidian Settings Module

**Why this matters:** Centralized settings for all Obsidian-related configuration.

```python
# backend/app/config/obsidian.py

from pydantic_settings import BaseSettings
from typing import Optional


class ObsidianSettings(BaseSettings):
    """Settings for Obsidian vault integration."""
    
    # Paths
    OBSIDIAN_VAULT_PATH: str = "/path/to/vault"
    
    # Note Generation (used by existing obsidian_generator.py)
    NOTE_CREATE_CONCEPTS: bool = True
    NOTE_MAX_HIGHLIGHTS: int = 50
    NOTE_DEFAULT_TEMPLATE: str = "article"
    
    # File Watcher
    VAULT_WATCH_ENABLED: bool = True
    VAULT_SYNC_DEBOUNCE_MS: int = 1000
    
    # Neo4j Sync
    VAULT_SYNC_NEO4J_ENABLED: bool = True
    
    class Config:
        env_prefix = ""  # Use exact env var names
        extra = "ignore"
```

**Deliverables:**
- [ ] `ObsidianSettings` Pydantic settings class
- [ ] Integration with main settings

**Estimated Time:** 30 minutes

---

## 5. Testing Strategy

### 5.1 Test Structure

```
tests/
├── unit/
│   └── obsidian/
│       ├── test_vault.py              # VaultManager tests
│       ├── test_frontmatter.py        # FrontmatterBuilder tests
│       ├── test_links.py              # WikilinkBuilder tests
│       ├── test_indexer.py            # FolderIndexer tests
│       ├── test_daily.py              # DailyNoteGenerator tests
│       ├── test_dataview.py           # DataviewLibrary tests
│       ├── test_sync.py               # VaultSyncService tests
│       └── test_lifecycle.py          # Startup/shutdown tests
├── integration/
│   ├── test_vault_sync.py             # Neo4j sync integration tests
│   ├── test_vault_api.py              # API endpoint tests
│   └── test_reconciliation.py         # Offline change detection tests
└── fixtures/
    └── sample_vault/                  # Test vault structure
```

### 5.2 Key Test Cases

| Component | Test Case | Priority |
|-----------|-----------|----------|
| VaultManager | `ensure_structure()` creates missing folders | High |
| VaultManager | `ensure_structure()` is idempotent (no-op for existing) | High |
| VaultManager | Get folder uses ContentTypeRegistry | High |
| Frontmatter | Builder produces valid YAML | High |
| Frontmatter | Parse and update existing notes | High |
| Links | Extract wikilinks correctly | High |
| Links | Auto-link known concepts | Medium |
| Indexer | Generate index with metadata | High |
| Daily | Create daily note from template | High |
| Watcher | Detect file changes with debounce | High |
| Sync | Update Neo4j on note change | High |
| Sync | Reconcile offline changes by mtime | High |
| Sync | Store/retrieve last_sync_time | High |
| Lifecycle | Startup runs reconciliation first | High |
| Lifecycle | Startup then starts watcher | High |
| Lifecycle | Shutdown stops watcher cleanly | High |
| Lifecycle | Shutdown updates last_sync_time | High |
| API | All endpoints return correct status | High |

---

## 6. Configuration Summary

### 6.1 Single Source of Truth Architecture (Updated)

| Configuration | Location | Status |
|---------------|----------|--------|
| Content Types & Vault Structure | `config/default.yaml` | ✅ Complete |
| Content Type Registry | `app/content_types.py` | ✅ Complete |
| Tag Taxonomy | `config/tag-taxonomy.yaml` | ✅ Complete |
| Note Templates (Jinja2) | `config/templates/*.md.j2` | ✅ Complete |
| Obsidian Settings | `app/config/obsidian.py` | 🔲 New |

---

## 7. Timeline Summary (Updated)

| Week | Phase | Tasks | Status |
|------|-------|-------|--------|
| 11 | 4A | VaultManager, Frontmatter, Links | 🔲 Not Started |
| 12 | 4B | Indexer, Daily Notes, Dataview | 🔲 Not Started |
| 13 | 4C | Vault Watcher, Neo4j Sync, Startup Lifecycle | 🔲 Not Started |
| 14 | 4D | API Endpoints | 🔲 Not Started |

**Previously Completed (Phase 2/3):**
- ✅ ContentTypeRegistry
- ✅ Jinja2 Templates (13 types)
- ✅ Basic Note Generator (`obsidian_generator.py`)
- ✅ Neo4j Node Generator (`neo4j_generator.py`)
- ✅ Tag Taxonomy Loader

**Estimated Remaining Time:** ~27-32 hours (reduced from 45-55 hours)

---

## 8. Success Criteria (Updated)

### Functional
- [x] ~~Vault initialized from `ContentTypeRegistry`~~ (done in vault setup)
- [x] ~~Notes generated using Jinja2 templates~~ (done in Phase 3)
- [x] ~~Template selection uses config~~ (done in Phase 3)
- [x] ~~Valid frontmatter generated~~ (done in Phase 3)
- [ ] VaultManager provides vault-wide operations
- [ ] Folder indices auto-generated
- [ ] Daily notes created from template
- [ ] Vault watcher detects real-time changes
- [ ] Startup reconciliation syncs offline changes
- [ ] Neo4j updated on note edits
- [ ] API endpoints functional

### Non-Functional
- [ ] Note generation < 1 second (verify existing)
- [ ] Watcher uses < 50MB memory
- [ ] Startup reconciliation < 30 seconds for 1000 notes
- [ ] API responds < 500ms

---

## 9. Risk Assessment (Updated)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| File permission errors | High | Medium | Validate vault path on startup |
| Concurrent file access | Medium | Medium | Debounce writes |
| Neo4j sync conflicts | Medium | Medium | Last-write-wins, log conflicts |
| Large vault performance | Medium | Low | Background processing, pagination |
| Missed offline changes | Medium | Low | Reconciliation uses mtime comparison |
| Clock skew (mtime inaccurate) | Low | Low | Full sync API as fallback |
| Startup delay (large vault) | Medium | Medium | Async reconciliation, progress logging |

---

## 10. Dependencies

### Required Before Phase 4
- [x] Phase 1: Foundation (ContentTypeRegistry, config structure)
- [x] Phase 2: Ingestion Layer (content models)
- [x] Phase 3: LLM Processing (note generation, Neo4j integration)

### Enables After Phase 4
- Phase 5: Knowledge Explorer UI
- Phase 6: Spaced Repetition
- Phase 7: Mobile PWA

---

## 11. Related Documents

- `design_docs/03_knowledge_hub_obsidian.md` — Design specification
- `design_docs/04_knowledge_graph_neo4j.md` — Neo4j schema
- `implementation_plan/00_foundation_implementation.md` — ContentTypeRegistry definition
- `implementation_plan/02_llm_processing_implementation.md` — Note generator implementation
