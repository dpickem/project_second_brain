# Knowledge Hub (Obsidian) Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Target Phase**: Phase 4 (Weeks 11-14 per roadmap)  
> **Design Doc**: `design_docs/03_knowledge_hub_obsidian.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Knowledge Hub (Obsidian) component, which serves as the primary user-facing knowledge storage and interface. All processed content from the LLM Processing Layer ultimately becomes Markdown notes in the Obsidian vault, enabling local-first ownership, powerful search, and integration with the Obsidian plugin ecosystem.

### Architecture Overview

The Knowledge Hub bridges the backend processing system with the user's Obsidian vault:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LLM Processing │────▶│  Note Generator  │────▶│  Obsidian Vault │
│     Result      │     │    (Backend)     │     │   (Markdown)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                              ┌──────────────────┐        │
                              │   Vault Watcher  │◀───────┘
                              │  (Change Sync)   │
                              └──────────────────┘
                                      │
                              ┌───────▼───────┐
                              │    Neo4j      │
                              │  Knowledge    │
                              │    Graph      │
                              └───────────────┘
```

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Vault structure initialization | Obsidian plugin development |
| Note templates (Paper, Article, Book, Code, Concept) | Custom Obsidian themes |
| Frontmatter YAML generation | Third-party plugin configuration |
| Wikilink generation and extraction | Real-time collaborative editing |
| Folder index auto-generation | Mobile Obsidian sync (Obsidian Sync) |
| Daily note automation | Obsidian Publish integration |
| Tag taxonomy enforcement | Full-text search (Obsidian native) |
| Bi-directional Neo4j sync | Graph view customization |
| Vault change watcher | Plugin marketplace integration |
| Dataview query templates | |

---

## 2. Prerequisites

### 2.1 Infrastructure (From Phase 1-3)

- [x] Docker Compose environment
- [x] FastAPI backend skeleton
- [x] PostgreSQL for metadata
- [x] Neo4j for knowledge graph
- [x] Celery task queue
- [x] LLM Processing Layer (Phase 3)
- [ ] Configured vault path in environment

### 2.2 Dependencies to Install

```txt
# Add to backend/requirements.txt
jinja2>=3.1.0              # Template rendering (may already be installed)
watchdog>=4.0.0            # File system monitoring for vault changes
python-frontmatter>=1.1.0  # YAML frontmatter parsing/writing
aiofiles>=24.1.0           # Async file operations (may already be installed)
PyYAML>=6.0                # YAML processing
slugify>=0.0.1             # Safe filename generation
python-dateutil>=2.9.0     # Date parsing utilities
```

### 2.3 External Dependencies

| Dependency | Purpose | Required By |
|------------|---------|-------------|
| Obsidian (user-installed) | Note viewing/editing | End user |
| Dataview plugin | Dynamic queries | Dashboard, indices |
| Templater plugin | Template expansion | Note creation |
| Tasks plugin | Todo tracking | Follow-up tasks |

### 2.4 Environment Variables

```bash
# .env file additions
OBSIDIAN_VAULT_PATH=/path/to/vault        # Required: path to user's vault
OBSIDIAN_TEMPLATES_DIR=templates          # Template folder name
OBSIDIAN_DAILY_DIR=daily                  # Daily notes folder
OBSIDIAN_SOURCES_DIR=sources              # Source content folder
OBSIDIAN_CONCEPTS_DIR=concepts            # Concept notes folder
OBSIDIAN_EXERCISES_DIR=exercises          # Exercise folder
OBSIDIAN_REVIEWS_DIR=reviews              # Spaced repetition folder

# Sync Configuration
VAULT_WATCH_ENABLED=true                  # Enable file watcher
VAULT_SYNC_DEBOUNCE_MS=1000               # Debounce for rapid changes
VAULT_SYNC_NEO4J_ENABLED=true             # Sync changes to Neo4j

# Note Generation
NOTE_INCLUDE_DETAILED_SUMMARY=true        # Include detailed summary section
NOTE_MAX_HIGHLIGHTS=50                    # Maximum highlights to include
NOTE_MAX_CONNECTIONS=20                   # Maximum connections to show
```

---

## 3. Implementation Phases

### Phase 4A: Foundation (Week 11)

#### Task 4A.1: Project Structure Setup

**Why this matters:** A well-organized module structure separates concerns: vault management, template rendering, note generation, and synchronization. This enables independent testing and easy extension of note types.

Create the Obsidian integration module:

```
backend/
├── app/
│   ├── services/
│   │   ├── obsidian/
│   │   │   ├── __init__.py
│   │   │   ├── vault.py              # Vault management (uses ContentTypeRegistry)
│   │   │   ├── template_engine.py    # Jinja2 template loading & rendering
│   │   │   ├── generator.py          # Note generation orchestrator
│   │   │   ├── frontmatter.py        # YAML frontmatter utilities
│   │   │   ├── links.py              # Wikilink handling
│   │   │   ├── indexer.py            # Folder index generation
│   │   │   ├── watcher.py            # File change monitoring
│   │   │   └── sync.py               # Neo4j synchronization
│   │   └── ...
│   ├── routers/
│   │   └── vault.py                  # Vault API endpoints
│   ├── config/
│   │   └── obsidian.py               # Obsidian configuration
│   └── content_types.py              # ContentTypeRegistry (shared across system)
├── config/
│   ├── default.yaml                  # Single source of truth: content types, vault structure
│   ├── tag-taxonomy.yaml             # Single source of truth: tag taxonomy
│   └── templates/                    # Note templates (Jinja2)
│       ├── paper.md.j2               # Paper note template
│       ├── article.md.j2             # Article note template
│       ├── book.md.j2                # Book note template
│       ├── code.md.j2                # Code/repo note template
│       ├── concept.md.j2             # Concept note template
│       ├── daily.md.j2               # Daily note template
│       ├── exercise.md.j2            # Exercise note template
│       ├── career.md.j2              # Career note template
│       ├── personal.md.j2            # Personal development template
│       ├── project.md.j2             # Project note template
│       ├── reflection.md.j2          # Reflection template
│       ├── _index.md.j2              # Folder index template
│       └── dashboard.md.j2           # Dashboard template
```

**Single Source of Truth Principle:**
- **Content Types & Vault Structure**: Defined in `config/default.yaml` under `content_types`, loaded by `ContentTypeRegistry` (from `app/content_types.py`)
- **Tag Taxonomy**: Single source of truth in `config/tag-taxonomy.yaml`, loaded by `TagTaxonomyLoader`
- **Note Templates**: Jinja2 templates in `config/templates/*.md.j2`, loaded by `TemplateEngine`

This eliminates redundancy—no hard-coded structures, taxonomies, or template content in Python code.

> **IMPORTANT**: The `ContentTypeRegistry` class defined in `app/content_types.py` (see `00_foundation_implementation.md` Task 1A.2) is the **shared registry** used by all components: ingestion pipelines, vault management, note generation, and frontend content type selectors.

**Deliverables:**
- [ ] Directory structure created
- [ ] `__init__.py` files with proper exports
- [ ] Configuration loader for Obsidian settings

**Estimated Time:** 2 hours

---

#### Task 4A.2: Content Type Registry Integration

**Why this matters:** The content type registry defined in `config/default.yaml` serves as the single source of truth for both vault structure and content type metadata. This enables users to customize the structure and ensures consistency across ingestion, processing, and vault management.

**Content Types Config** (from `config/default.yaml` — see `00_foundation_implementation.md` Task 1A.2):

> **EXTENSIBILITY**: The `content_types` block is the single source of truth. Add new content types here and run setup script—no code changes needed. The same registry is used by ingestion pipelines, note generation, and the frontend.

```yaml
# From config/default.yaml - content_types section
# See 00_foundation_implementation.md for the full configuration

content_types:
  # ---------------------------------------------------------------------------
  # TECHNICAL CONTENT
  # ---------------------------------------------------------------------------
  paper:
    folder: "sources/papers"
    template: "templates/paper.md"      # Vault template for manual creation
    jinja_template: "paper.md.j2"       # Jinja2 template for backend generation
    description: "Academic papers, research publications"
    icon: "📄"
    file_types: ["pdf"]
    
  article:
    folder: "sources/articles"
    template: "templates/article.md"
    jinja_template: "article.md.j2"
    description: "Blog posts, news, essays, web content"
    icon: "📰"
    file_types: ["url", "html", "md"]
    
  book:
    folder: "sources/books"
    template: "templates/book.md"
    jinja_template: "book.md.j2"
    description: "Book notes and highlights"
    icon: "📚"
    file_types: ["pdf", "epub", "photo"]
    
  code:
    folder: "sources/code"
    template: "templates/code.md"
    jinja_template: "code.md.j2"
    description: "GitHub repositories, code analysis"
    icon: "💻"
    file_types: ["url", "git"]
    
  idea:
    folder: "sources/ideas"
    template: "templates/idea.md"
    jinja_template: "article.md.j2"     # Ideas use article template
    description: "Fleeting notes, quick captures"
    icon: "💡"
    file_types: ["text", "voice"]

  # ---------------------------------------------------------------------------
  # WORK & PROFESSIONAL
  # ---------------------------------------------------------------------------
  work:
    folder: "sources/work"
    template: "templates/work.md"
    jinja_template: "article.md.j2"
    description: "Work-related content"
    icon: "💼"
    subfolders:
      - meetings
      - proposals
      - projects
      
  career:
    folder: "sources/career"
    template: "templates/career.md"
    jinja_template: "career.md.j2"
    description: "Career development content"
    icon: "🎯"
    subfolders:
      - goals
      - interviews
      - networking
      - skills

  # ---------------------------------------------------------------------------
  # PERSONAL DEVELOPMENT
  # ---------------------------------------------------------------------------
  personal:
    folder: "sources/personal"
    template: "templates/personal.md"
    jinja_template: "personal.md.j2"
    description: "Personal development content"
    icon: "🌱"
    subfolders:
      - goals
      - reflections
      - habits
      - wellbeing
      
  project:
    folder: "sources/projects"
    template: "templates/project.md"
    jinja_template: "project.md.j2"
    description: "Personal project notes"
    icon: "🚀"
    subfolders:
      - active
      - ideas
      - archive
      
  reflection:
    folder: "sources/personal/reflections"
    template: "templates/reflection.md"
    jinja_template: "reflection.md.j2"
    description: "Periodic reflections, retrospectives"
    icon: "🔮"

  # ---------------------------------------------------------------------------
  # NON-TECHNICAL
  # ---------------------------------------------------------------------------
  non-tech:
    folder: "sources/non-tech"
    template: "templates/personal.md"
    jinja_template: "personal.md.j2"
    description: "Non-technical learning and interests"
    icon: "🌍"
    subfolders:
      - finance
      - hobbies
      - philosophy
      - misc

  # ---------------------------------------------------------------------------
  # SYSTEM CONTENT TYPES (used internally)
  # ---------------------------------------------------------------------------
  concept:
    folder: "concepts"
    template: "templates/concept.md"
    jinja_template: "concept.md.j2"
    description: "Atomic concept notes"
    icon: "🧩"
    system: true
    
  daily:
    folder: "daily"
    template: "templates/daily.md"
    jinja_template: "daily.md.j2"
    description: "Daily notes"
    icon: "📅"
    system: true
    
  exercise:
    folder: "exercises"
    template: "templates/exercise.md"
    jinja_template: "exercise.md.j2"
    description: "Practice problems"
    icon: "🏋️"
    system: true
```

**Key Fields:**
- `folder`: Vault folder path (used by `VaultManager` and `ContentTypeRegistry.get_folder()`)
- `template`: Obsidian template path (for manual note creation via Templater)
- `jinja_template`: Jinja2 template filename (for backend note generation)
- `subfolders`: Optional subfolders to create within the base folder
- `system`: If `true`, hidden from user content type selectors

---

#### Task 4A.3: Vault Manager

**Why this matters:** The vault manager handles all file system operations for the Obsidian vault: creating the folder structure, managing paths, validating vault health, and providing safe file operations. It uses the `ContentTypeRegistry` from `app/content_types.py` (defined in Phase 1) rather than maintaining its own configuration.

```python
# backend/app/services/obsidian/vault.py

from pathlib import Path
from datetime import datetime
from typing import Optional, Any
import aiofiles
import aiofiles.os
import logging
import re

from app.config import settings
from app.content_types import content_registry  # Uses shared ContentTypeRegistry

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages Obsidian vault structure and file operations.
    
    IMPORTANT: Uses ContentTypeRegistry from app/content_types.py as the
    single source of truth for folder mappings. See 00_foundation_implementation.md
    Task 1A.2 for the ContentTypeRegistry implementation.
    
    This ensures consistency between:
    - Ingestion pipelines (determine content type)
    - Vault management (create folders, write notes)
    - Note generation (select templates)
    - Frontend (content type dropdowns)
    """
    
    def __init__(self, vault_path: str = None):
        self.vault_path = Path(vault_path or settings.OBSIDIAN_VAULT_PATH)
        self._template_engine = None  # Lazy-loaded
        self._validate_vault_path()
    
    def _validate_vault_path(self):
        """Validate that vault path exists and is accessible."""
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault_path}")
    
    def _get_template_engine(self):
        """Lazy-load template engine."""
        if self._template_engine is None:
            from app.services.obsidian.template_engine import TemplateEngine
            self._template_engine = TemplateEngine()
        return self._template_engine
    
    async def initialize_structure(self, force: bool = False) -> dict:
        """Initialize the vault folder structure from ContentTypeRegistry.
        
        Args:
            force: If True, recreate missing folders even if vault exists
        
        Returns:
            Dict with created folders and status
        """
        created = []
        existed = []
        
        # System folders (always created)
        system_folders = [
            "topics",
            "concepts",
            "exercises/by-topic",
            "exercises/daily",
            "reviews/due",
            "reviews/archive",
            "daily",
            "templates",
            "meta",
            "assets/images",
            "assets/pdfs",
        ]
        
        # Create system folders
        for folder in system_folders:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                await aiofiles.os.makedirs(folder_path, exist_ok=True)
                created.append(folder)
            else:
                existed.append(folder)
        
        # Dynamically create folders from ContentTypeRegistry
        # This reads from config/default.yaml content_types section
        for type_key in content_registry.all_types:
            # Create base folder
            base_folder = content_registry.get_folder(type_key)
            if base_folder:
                folder_path = self.vault_path / base_folder
                if not folder_path.exists():
                    await aiofiles.os.makedirs(folder_path, exist_ok=True)
                    created.append(base_folder)
                else:
                    existed.append(base_folder)
                
                # Create subfolders if defined
                for subfolder in content_registry.get_subfolders(type_key):
                    subfolder_path = f"{base_folder}/{subfolder}"
                    full_path = self.vault_path / subfolder_path
                    if not full_path.exists():
                        await aiofiles.os.makedirs(full_path, exist_ok=True)
                        created.append(subfolder_path)
                    else:
                        existed.append(subfolder_path)
        
        logger.info(f"Vault initialized: {len(created)} created, {len(existed)} existed")
        logger.info(f"Content types loaded: {len(content_registry.all_types)}")
        return {"created": created, "existed": existed}
    
    def get_source_folder(self, content_type: str) -> Path:
        """Get the appropriate source folder for a content type.
        
        Uses ContentTypeRegistry from config/default.yaml.
        """
        folder = content_registry.get_folder(content_type)
        if folder:
            return self.vault_path / folder
        # Fallback for unknown types
        return self.vault_path / "sources/ideas"
    
    def get_jinja_template(self, content_type: str) -> Optional[str]:
        """Get the Jinja2 template name for a content type.
        
        Returns the jinja_template field from content_types config,
        or None if not found.
        """
        ct = content_registry.get(content_type)
        if ct:
            return ct.get("jinja_template")
        return None
    
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
        """Convert title to safe filename.
        
        Args:
            title: Original title
            max_length: Maximum filename length
        
        Returns:
            Safe filename without extension
        """
        # Remove/replace unsafe characters
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', ' ', safe)  # Normalize whitespace
        safe = safe.strip()
        
        # Truncate to max length
        if len(safe) > max_length:
            safe = safe[:max_length].rsplit(' ', 1)[0]  # Break at word
        
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
            path = folder / f"{filename}-{counter}.md"
            counter += 1
        
        return path
    
    async def write_note(self, path: Path, content: str) -> Path:
        """Write note content to file.
        
        Args:
            path: Full path to the note file
            content: Markdown content to write
        
        Returns:
            Path to the written file
        """
        # Ensure parent directory exists
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
- [ ] `VaultManager` class using `ContentTypeRegistry` from `app/content_types.py`
- [ ] Folder structure initialization from `content_types` config
- [ ] Path utilities for different content types (via `ContentTypeRegistry`)
- [ ] Safe filename generation
- [ ] Async file read/write operations
- [ ] Unit tests for vault operations

**Estimated Time:** 4 hours

---

#### Task 4A.3: Frontmatter Utilities

**Why this matters:** Obsidian uses YAML frontmatter for metadata. Consistent, well-structured frontmatter enables Dataview queries, filtering, and the plugin ecosystem. This utility ensures all generated notes have valid, queryable frontmatter.

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
        valid = {"unread", "reading", "read", "reviewed", "archived"}
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
    
    def set_venue(self, venue: str) -> "FrontmatterBuilder":
        """Set publication venue."""
        return self.set("venue", venue)
    
    def set_year(self, year: int | str) -> "FrontmatterBuilder":
        """Set publication year."""
        return self.set("year", int(year) if year else None)
    
    def set_domain(self, domain: str) -> "FrontmatterBuilder":
        """Set content domain."""
        return self.set("domain", domain)
    
    def set_complexity(self, complexity: str) -> "FrontmatterBuilder":
        """Set complexity level."""
        valid = {"foundational", "intermediate", "advanced"}
        if complexity in valid:
            return self.set("complexity", complexity)
        return self
    
    def set_rating(self, rating: int) -> "FrontmatterBuilder":
        """Set rating (1-5)."""
        if rating and 1 <= rating <= 5:
            return self.set("rating", rating)
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
    
    Args:
        content: Full markdown content including frontmatter
    
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


def create_paper_frontmatter(
    title: str,
    authors: list[str],
    year: int = None,
    venue: str = None,
    doi: str = None,
    tags: list[str] = None,
    domain: str = None,
    complexity: str = None,
    has_handwritten_notes: bool = False
) -> str:
    """Create frontmatter for a paper note."""
    return (
        FrontmatterBuilder()
        .set_type("paper")
        .set_title(title)
        .set_authors(authors)
        .set_year(year)
        .set_venue(venue)
        .set_source(doi=doi)
        .set_tags(tags or [])
        .set_status("unread")
        .set_domain(domain)
        .set_complexity(complexity)
        .set_custom(has_handwritten_notes=has_handwritten_notes)
        .set_created()
        .set_processed()
        .to_frontmatter()
    )


def create_article_frontmatter(
    title: str,
    source_url: str,
    author: str = None,
    published: datetime = None,
    tags: list[str] = None,
    domain: str = None
) -> str:
    """Create frontmatter for an article note."""
    return (
        FrontmatterBuilder()
        .set_type("article")
        .set_title(title)
        .set_source(url=source_url)
        .set("author", author)
        .set_date("published", published)
        .set_tags(tags or [])
        .set_domain(domain)
        .set_created()
        .set_processed()
        .to_frontmatter()
    )


def create_book_frontmatter(
    title: str,
    author: str,
    isbn: str = None,
    tags: list[str] = None,
    status: str = "reading",
    started: datetime = None,
    finished: datetime = None,
    rating: int = None
) -> str:
    """Create frontmatter for a book note."""
    return (
        FrontmatterBuilder()
        .set_type("book")
        .set_title(title)
        .set("author", author)
        .set_source(isbn=isbn)
        .set_tags(tags or [])
        .set_status(status)
        .set_date("started", started)
        .set_date("finished", finished)
        .set_rating(rating)
        .to_frontmatter()
    )


def create_code_frontmatter(
    repo: str,
    url: str,
    language: str = None,
    stars: int = None,
    tags: list[str] = None
) -> str:
    """Create frontmatter for a code repository note."""
    return (
        FrontmatterBuilder()
        .set_type("code")
        .set("repo", repo)
        .set_source(url=url)
        .set("language", language)
        .set("stars", stars)
        .set_tags(tags or [])
        .set_created()
        .to_frontmatter()
    )


def create_concept_frontmatter(
    name: str,
    domain: str,
    complexity: str = "intermediate",
    tags: list[str] = None
) -> str:
    """Create frontmatter for a concept note."""
    return (
        FrontmatterBuilder()
        .set_type("concept")
        .set("name", name)
        .set_domain(domain)
        .set_complexity(complexity)
        .set_tags(tags or [])
        .set_created()
        .to_frontmatter()
    )
```

**Deliverables:**
- [ ] `FrontmatterBuilder` fluent builder class
- [ ] Frontmatter parsing utilities
- [ ] Frontmatter update utility
- [ ] Type-specific frontmatter creators (paper, article, book, code, concept)
- [ ] Unit tests for YAML generation and parsing

**Estimated Time:** 3 hours

---

#### Task 4A.4: Wikilink Utilities

**Why this matters:** Wikilinks (`[[Note Name]]`) are the backbone of Obsidian's knowledge graph. Proper link handling ensures connections are made and maintained across notes.

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
        """Create a link to a specific header.
        
        Args:
            note: Target note name
            header: Header text (without #)
            alias: Optional display text
        
        Returns:
            Link like [[note#header]] or [[note#header|alias]]
        """
        target = f"{note}#{header}"
        return WikilinkBuilder.link(target, alias)
    
    @staticmethod
    def block_link(note: str, block_id: str, alias: str = None) -> str:
        """Create a link to a specific block.
        
        Args:
            note: Target note name
            block_id: Block identifier (without ^)
            alias: Optional display text
        
        Returns:
            Link like [[note#^block-id]]
        """
        target = f"{note}#^{block_id}"
        return WikilinkBuilder.link(target, alias)
    
    @staticmethod
    def embed(target: str) -> str:
        """Create an embedded note/image link.
        
        Args:
            target: Target note or image path
        
        Returns:
            Embed syntax like ![[target]]
        """
        return f"![[{target}]]"
    
    @staticmethod
    def embed_header(note: str, header: str) -> str:
        """Embed a specific section from another note."""
        return f"![[{note}#{header}]]"


def extract_wikilinks(content: str) -> list[str]:
    """Extract all wikilinks from markdown content.
    
    Args:
        content: Markdown content to parse
    
    Returns:
        List of linked note names (without [[]])
    """
    # Match [[link]] and [[link|alias]], extract the link part
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    matches = re.findall(pattern, content)
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for match in matches:
        # Strip header/block references for unique note names
        note_name = match.split("#")[0]
        if note_name and note_name not in seen:
            seen.add(note_name)
            unique.append(note_name)
    
    return unique


def extract_tags(content: str) -> list[str]:
    """Extract all tags from markdown content.
    
    Args:
        content: Markdown content to parse
    
    Returns:
        List of tags (with # prefix removed)
    """
    # Match #tag but not inside code blocks or links
    # Simple pattern - may need refinement
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


def generate_concept_links(concepts: list[dict]) -> str:
    """Generate links to concept notes.
    
    Args:
        concepts: List of concept dicts with name field
    
    Returns:
        Markdown with concept links
    """
    if not concepts:
        return "*No concepts*"
    
    lines = []
    for concept in concepts:
        name = concept.get("name", "")
        definition = concept.get("definition", "")
        importance = concept.get("importance", "supporting")
        
        link = WikilinkBuilder.link(name)
        
        if importance == "core":
            lines.append(f"- **{link}**: {definition}")
        else:
            lines.append(f"- {link}: {definition}")
    
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
    # Sort by length (longest first) to avoid partial matches
    concepts = sorted(known_concepts, key=len, reverse=True)
    
    for concept in concepts:
        if not concept:
            continue
        
        # Pattern to match concept not already in wikilink
        # This is simplified - production version needs more sophistication
        pattern = rf'(?<!\[\[)(?<!\|)\b({re.escape(concept)})\b(?!\]\])(?!\|)'
        
        def replace(match):
            return f"[[{match.group(1)}]]"
        
        content = re.sub(pattern, replace, content, flags=re.IGNORECASE)
    
    return content


def validate_links(content: str, vault_notes: set[str]) -> list[str]:
    """Find broken wikilinks (links to non-existent notes).
    
    Args:
        content: Markdown content to check
        vault_notes: Set of existing note names in vault
    
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

**Estimated Time:** 3 hours

---

### Phase 4B: Note Templates & Generation (Week 12)

#### Task 4B.1: Template File Format

**Why this matters:** Templates should have a **single source of truth**—Jinja2 `.md.j2` files stored in `config/templates/`. The Python code loads and renders these files rather than embedding template strings. This allows:
- Users to customize templates without touching Python code
- Templates to be version-controlled separately
- Potential future support for Obsidian Templater integration

**Example Template File** (`config/templates/paper.md.j2`):
```jinja2
---
type: paper
title: "{{ title }}"
authors: [{{ authors | join(', ') }}]
{% if year %}year: {{ year }}{% endif %}
{% if venue %}venue: "{{ venue }}"{% endif %}
{% if doi %}doi: "{{ doi }}"{% endif %}
tags: [{{ tags | join(', ') }}]
domain: {{ domain }}
complexity: {{ complexity }}
status: unread
{% if has_handwritten_notes %}has_handwritten_notes: true{% endif %}
created: {{ created | datestamp }}
processed: {{ processed | datestamp }}
---

## Summary
{{ summary }}

## Key Findings
{{ key_findings }}

## Core Concepts
{{ concepts }}

{% if highlights %}
## My Highlights
{{ highlights }}
{% endif %}

{% if handwritten_notes %}
## My Handwritten Notes
{{ handwritten_notes }}
{% endif %}

## Mastery Questions
{{ mastery_questions }}

## Follow-up Tasks
{{ followups }}

## Connections
{{ connections }}

---

## Detailed Notes
{{ detailed_summary }}
```

**Other template files follow similar patterns:**
- `config/templates/article.md.j2` — Web article format
- `config/templates/book.md.j2` — Book notes with chapter structure
- `config/templates/code.md.j2` — Repository analysis format
- `config/templates/concept.md.j2` — Atomic concept definition
- `config/templates/daily.md.j2` — Daily note structure
- `config/templates/_index.md.j2` — Folder index format
- `config/templates/dashboard.md.j2` — Main dashboard

---

#### Task 4B.2: Template Engine

**Why this matters:** A unified template engine loads `.md.j2` files from the config directory, registers custom filters, and builds context from content/processing results. No template content is hard-coded in Python.

```python
# backend/app/services/obsidian/template_engine.py

from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import logging

from app.models.content import UnifiedContent, AnnotationType
from app.models.processing import ProcessingResult, SummaryLevel
from app.services.obsidian.links import WikilinkBuilder, generate_connection_section
from app.config import settings

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Loads and renders Jinja2 templates from config/templates/.
    
    Single source of truth: Templates are .md.j2 files in config/templates/,
    NOT embedded strings in Python code.
    """
    
    _instance: Optional["TemplateEngine"] = None
    
    def __init__(self, templates_dir: str = "config/templates"):
        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(disabled_extensions=('md.j2',)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._register_filters()
        self._register_globals()
    
    def _register_filters(self):
        """Register custom Jinja2 filters for note generation."""
        self.env.filters['wikilink'] = lambda x: WikilinkBuilder.link(x)
        self.env.filters['datestamp'] = lambda x: x.strftime("%Y-%m-%d") if x else ""
        self.env.filters['truncate_smart'] = self._truncate_smart
        self.env.filters['format_highlights'] = self._format_highlights
        self.env.filters['format_concepts'] = self._format_concepts
        self.env.filters['format_questions'] = self._format_questions
        self.env.filters['format_followups'] = self._format_followups
        self.env.filters['format_connections'] = self._format_connections
    
    def _register_globals(self):
        """Register global functions available in all templates."""
        self.env.globals['now'] = datetime.now
    
    @staticmethod
    def _truncate_smart(text: str, length: int = 200) -> str:
        """Truncate text at word boundary."""
        if not text or len(text) <= length:
            return text or ""
        return text[:length].rsplit(' ', 1)[0] + "..."
    
    @staticmethod
    def _format_highlights(annotations: list, max_count: int = 50) -> str:
        """Format highlights as blockquotes."""
        highlights = [a for a in annotations if a.type == AnnotationType.DIGITAL_HIGHLIGHT][:max_count]
        if not highlights:
            return "*No highlights*"
        parts = []
        for h in highlights:
            quote = f"> {h.content}"
            if h.page_number:
                quote += f"\n> — Page {h.page_number}"
            parts.append(quote)
        return "\n\n".join(parts)
    
    @staticmethod
    def _format_concepts(concepts: list, core_only: bool = False) -> str:
        """Format extracted concepts with wikilinks."""
        if core_only:
            concepts = [c for c in concepts if c.importance == "core"]
        if not concepts:
            return "*No concepts extracted*"
        lines = []
        for c in concepts:
            link = WikilinkBuilder.link(c.name)
            if c.importance == "core":
                lines.append(f"- **{link}**: {c.definition}")
            else:
                lines.append(f"- {link}: {c.definition}")
        return "\n".join(lines)
    
    @staticmethod
    def _format_questions(questions: list) -> str:
        """Format mastery questions as checkbox list."""
        if not questions:
            return "*No mastery questions*"
        lines = []
        for q in questions:
            checkbox = f"- [ ] {q.question}"
            if q.difficulty != "intermediate":
                checkbox += f" `{q.difficulty}`"
            lines.append(checkbox)
        return "\n".join(lines)
    
    @staticmethod
    def _format_followups(followups: list) -> str:
        """Format follow-up tasks."""
        if not followups:
            return "*No follow-up tasks*"
        return "\n".join([f"- [ ] {f.task} `{f.task_type}` `{f.estimated_time}`" for f in followups])
    
    @staticmethod
    def _format_connections(connections: list) -> str:
        """Format connections with wikilinks."""
        return generate_connection_section([c.model_dump() if hasattr(c, 'model_dump') else c for c in connections])
    
    def get_template(self, template_name: str):
        """Load a template by name (without .md.j2 extension)."""
        filename = f"{template_name}.md.j2"
        return self.env.get_template(filename)
    
    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context."""
        template = self.get_template(template_name)
        return template.render(**context)
    
    async def render_note(
        self,
        template_name: str,
        content: UnifiedContent,
        result: ProcessingResult
    ) -> str:
        """Render a note template from content and processing result.
        
        Builds the full context and renders the appropriate template.
        """
        context = self._build_note_context(content, result)
        return self.render(template_name, context)
    
    async def render_meta_template(self, template_name: str, context: dict) -> str:
        """Render a meta template (dashboard, index, etc.)."""
        return self.render(template_name, context)
    
    def _build_note_context(self, content: UnifiedContent, result: ProcessingResult) -> dict[str, Any]:
        """Build template context from content and processing result."""
        return {
            # Content fields
            "title": content.title,
            "authors": content.authors or [],
            "source_url": content.source_url,
            "created_at": content.created_at,
            "annotations": content.annotations or [],
            
            # Analysis fields
            "content_type": result.analysis.content_type,
            "domain": result.analysis.domain,
            "complexity": result.analysis.complexity,
            "has_code": result.analysis.has_code,
            "has_math": result.analysis.has_math,
            
            # Summaries
            "summary": result.summaries.get(SummaryLevel.STANDARD.value, ""),
            "detailed_summary": result.summaries.get(SummaryLevel.DETAILED.value, ""),
            "brief_summary": result.summaries.get(SummaryLevel.BRIEF.value, ""),
            
            # Extraction
            "concepts": result.extraction.concepts,
            "key_findings": "\n".join([f"- {f}" for f in result.extraction.key_findings]) or "*No key findings*",
            "methodologies": result.extraction.methodologies,
            "tools_mentioned": result.extraction.tools_mentioned,
            
            # Tags
            "tags": result.tags.domain_tags + result.tags.meta_tags,
            "domain_tags": result.tags.domain_tags,
            "meta_tags": result.tags.meta_tags,
            
            # Generated content
            "connections": result.connections,
            "mastery_questions": result.mastery_questions,
            "followups": result.followups,
            
            # Formatted sections (pre-rendered for convenience)
            "highlights": self._format_highlights(content.annotations or []),
            "concepts_formatted": self._format_concepts(result.extraction.concepts, core_only=True),
            "questions_formatted": self._format_questions(result.mastery_questions),
            "followups_formatted": self._format_followups(result.followups),
            "connections_formatted": self._format_connections(result.connections),
            
            # Dates
            "created": content.created_at or datetime.now(),
            "processed": datetime.now(),
            
            # Handwritten notes detection
            "has_handwritten_notes": any(
                a.type == AnnotationType.HANDWRITTEN_NOTE 
                for a in (content.annotations or [])
            ),
        }
    
    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [p.stem.replace('.md', '') for p in self.templates_dir.glob("*.md.j2")]


# Singleton accessor
_engine: Optional[TemplateEngine] = None

def get_template_engine() -> TemplateEngine:
    """Get or create singleton template engine."""
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine
```

**Deliverables:**
- [ ] `TemplateEngine` class loading from `config/templates/`
- [ ] Custom Jinja2 filters for note formatting
- [ ] Context builder for content + processing result
- [ ] Template listing for available templates
- [ ] Unit tests for template rendering

**Estimated Time:** 4 hours

---

#### Task 4B.3: Note Generator Orchestrator

**Why this matters:** The generator orchestrates template selection (based on content type), note creation, and linked concept note generation. It uses the `TemplateEngine` with template names from `ContentTypeRegistry` rather than hard-coded mappings.

```python
# backend/app/services/obsidian/generator.py

from pathlib import Path
from typing import Optional
import logging

from app.models.content import UnifiedContent
from app.models.processing import ProcessingResult
from app.services.obsidian.vault import get_vault_manager, VaultManager
from app.services.obsidian.template_engine import get_template_engine, TemplateEngine
from app.content_types import content_registry  # Uses shared ContentTypeRegistry

logger = logging.getLogger(__name__)


class NoteGenerator:
    """Orchestrates note generation from processed content.
    
    Uses ContentTypeRegistry to determine templates for each content type.
    Template names come from the jinja_template field in config/default.yaml.
    """
    
    DEFAULT_TEMPLATE = "article.md.j2"
    
    def __init__(self, vault_manager: VaultManager = None, template_engine: TemplateEngine = None):
        self.vault = vault_manager or get_vault_manager()
        self.template_engine = template_engine or get_template_engine()
    
    def _get_template_name(self, content_type: str) -> str:
        """Get Jinja2 template name for content type.
        
        Reads from jinja_template field in content_types config.
        """
        ct = content_registry.get(content_type)
        if ct and ct.get("jinja_template"):
            # Return without .md.j2 extension for TemplateEngine
            template = ct["jinja_template"]
            return template.replace(".md.j2", "")
        return self.DEFAULT_TEMPLATE.replace(".md.j2", "")
    
    async def generate_note(
        self,
        content: UnifiedContent,
        result: ProcessingResult,
        create_concept_notes: bool = True
    ) -> dict:
        """Generate Obsidian note(s) from processed content.
        
        Args:
            content: Unified content from ingestion
            result: Processing result from LLM pipeline
            create_concept_notes: Whether to create linked concept notes
        
        Returns:
            Dict with paths to created notes
        """
        created = {"main": None, "concepts": []}
        
        # Determine template and folder
        content_type = result.analysis.content_type
        template_name = self._get_template_name(content_type)
        
        # Render note using template engine
        note_content = await self.template_engine.render_note(
            template_name, content, result
        )
        
        # Determine output folder
        folder = self.vault.get_source_folder(content_type)
        if content_type == "paper" and content.created_at:
            folder = folder / str(content.created_at.year)
        
        # Write note
        note_path = await self.vault.get_unique_path(folder, content.title)
        await self.vault.write_note(note_path, note_content)
        created["main"] = str(note_path)
        
        logger.info(f"Generated note: {note_path}")
        
        # Create concept notes for core concepts
        if create_concept_notes:
            created["concepts"] = await self._create_concept_notes(
                result, content.title, result.analysis.domain
            )
        
        return created
    
    async def _create_concept_notes(
        self,
        result: ProcessingResult,
        source_title: str,
        domain: str
    ) -> list[str]:
        """Create notes for core concepts that don't already exist."""
        created = []
        concept_folder = self.vault.get_concept_folder()
        
        core_concepts = [c for c in result.extraction.concepts if c.importance == "core"]
        
        for concept in core_concepts:
            # Skip if concept note already exists
            if await self.vault.note_exists(concept_folder, concept.name):
                logger.debug(f"Concept note already exists: {concept.name}")
                continue
            
            # Render concept note using template
            context = {
                "name": concept.name,
                "definition": concept.definition,
                "context": concept.context,
                "domain": domain,
                "complexity": result.analysis.complexity,
                "sources": [source_title],
                "related_concepts": concept.related_concepts,
            }
            note_content = self.template_engine.render("concept", context)
            
            note_path = await self.vault.get_unique_path(concept_folder, concept.name)
            await self.vault.write_note(note_path, note_content)
            created.append(str(note_path))
            
            logger.debug(f"Created concept note: {concept.name}")
        
        return created


async def generate_obsidian_note(content: UnifiedContent, result: ProcessingResult) -> str:
    """Main entry point for note generation (used by Phase 3 processing pipeline)."""
    generator = NoteGenerator()
    created = await generator.generate_note(content, result)
    return created["main"]
```

**Deliverables:**
- [ ] `NoteGenerator` using `ContentTypeRegistry` for template selection
- [ ] Template names from `jinja_template` field in `content_types` config
- [ ] Automatic concept note creation for core concepts
- [ ] Year-based subfolder organization for papers
- [ ] Duplicate note handling
- [ ] Integration tests with mock vault

**Estimated Time:** 4 hours

---

### Phase 4C: Automation & Indexing (Week 13)

#### Task 4C.1: Folder Index Generator

**Why this matters:** Auto-generated indices make vault navigation easier. Each folder gets an `_index.md` that lists its contents, grouped and sorted for quick access.

```python
# backend/app/services/obsidian/indexer.py

from pathlib import Path
from datetime import datetime
from collections import defaultdict
import frontmatter
import aiofiles
import logging

from app.services.obsidian.vault import VaultManager
from app.services.obsidian.links import WikilinkBuilder

logger = logging.getLogger(__name__)


class FolderIndexer:
    """Generates and maintains folder index notes."""
    
    def __init__(self, vault: VaultManager):
        self.vault = vault
    
    async def generate_index(self, folder: Path, recursive: bool = False) -> str:
        """Generate an index note for a folder."""
        notes = list(folder.rglob("*.md") if recursive else folder.glob("*.md"))
        notes = [n for n in notes if not n.name.startswith("_")]
        
        if not notes:
            return await self._write_empty_index(folder)
        
        entries = []
        for note_path in notes:
            try:
                async with aiofiles.open(note_path, "r") as f:
                    content = await f.read()
                post = frontmatter.loads(content)
                entries.append({
                    "path": note_path, "title": post.get("title", note_path.stem),
                    "type": post.get("type", "note"), "tags": post.get("tags", []),
                    "processed": post.get("processed")
                })
            except Exception as e:
                entries.append({"path": note_path, "title": note_path.stem, "type": "note"})
        
        entries.sort(key=lambda x: x.get("processed") or "", reverse=True)
        index_content = self._render_index(folder, entries)
        
        index_path = folder / "_index.md"
        async with aiofiles.open(index_path, "w") as f:
            await f.write(index_content)
        
        return str(index_path)
    
    def _render_index(self, folder: Path, entries: list[dict]) -> str:
        folder_name = folder.name.replace("-", " ").title()
        lines = [f"# {folder_name}\n", f"*{len(entries)} notes*\n", "## Recent\n"]
        
        for entry in entries[:10]:
            lines.append(f"- [[{entry['title']}]]")
        
        return "\n".join(lines)
```

**Deliverables:**
- [ ] `FolderIndexer` class with metadata parsing
- [ ] Index generation with grouping by type
- [ ] Scheduled regeneration support
- [ ] Unit tests

**Estimated Time:** 4 hours

---

#### Task 4C.2: Daily Note Generator

**Why this matters:** Daily notes provide a consistent entry point for captures, learning activities, and reflections. The template is loaded from `config/templates/daily.md.j2` (single source of truth).

**Daily Note Template** (`config/templates/daily.md.j2`):
```jinja2
---
type: daily
date: {{ date_iso }}
---

# {{ date_full }}

## 📥 Inbox
<!-- Quick captures -->

## 📚 Learning
- [ ] Complete review queue ([[reviews/_queue]])

## ✅ Tasks
- [ ] 

## 📝 Journal

## 🔗 Quick Links
- [[meta/dashboard|Dashboard]]
```

```python
# backend/app/services/obsidian/daily.py

from datetime import date
from pathlib import Path
import aiofiles.os
import logging

from app.services.obsidian.vault import VaultManager
from app.services.obsidian.template_engine import TemplateEngine, get_template_engine

logger = logging.getLogger(__name__)


class DailyNoteGenerator:
    """Generates daily notes using template from config/templates/daily.md.j2."""
    
    def __init__(self, vault: VaultManager, template_engine: TemplateEngine = None):
        self.vault = vault
        self.template_engine = template_engine or get_template_engine()
    
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
            return str(note_path)
        
        # Render from template (single source of truth)
        context = {
            "date_iso": target_date.strftime("%Y-%m-%d"),
            "date_full": target_date.strftime("%A, %B %d, %Y"),
            "date": target_date,
        }
        content = self.template_engine.render("daily", context)
        
        await self.vault.write_note(note_path, content)
        logger.info(f"Created daily note: {note_path}")
        
        return str(note_path)
    
    async def add_inbox_item(self, note_path: Path, item: str) -> None:
        """Add an item to the inbox section of a daily note."""
        content = await self.vault.read_note(note_path)
        
        # Find inbox section and append item
        inbox_marker = "## 📥 Inbox"
        if inbox_marker in content:
            parts = content.split(inbox_marker, 1)
            parts[1] = f"\n- {item}" + parts[1]
            content = inbox_marker.join(parts)
            await self.vault.write_note(note_path, content)
```

**Deliverables:**
- [ ] `DailyNoteGenerator` using `TemplateEngine`
- [ ] Template loaded from `config/templates/daily.md.j2`
- [ ] Inbox item addition method
- [ ] Unit tests

**Estimated Time:** 2 hours

---

#### Task 4C.3: Dataview Query Library

**Why this matters:** Pre-built Dataview queries power dynamic dashboards and help users get immediate value.

```python
# backend/app/services/obsidian/dataview.py

class DataviewLibrary:
    @staticmethod
    def recent_notes(folder: str = "sources", limit: int = 10) -> str:
        return f'''```dataview
TABLE title, tags, processed
FROM "{folder}"
SORT processed DESC
LIMIT {limit}
```'''
    
    @staticmethod
    def unread_by_type(content_type: str) -> str:
        return f'''```dataview
LIST FROM "sources" WHERE type = "{content_type}" AND status = "unread"
```'''
    
    @staticmethod
    def open_tasks() -> str:
        return '''```dataview
TASK FROM "sources" WHERE !completed GROUP BY file.link
```'''
    
    @staticmethod
    def knowledge_stats() -> str:
        return '''```dataview
TABLE length(rows) as "Count" FROM "sources" GROUP BY type
```'''
```

**Deliverables:**
- [ ] `DataviewLibrary` with common queries
- [ ] Dashboard generation function
- [ ] Documentation for customization

**Estimated Time:** 2 hours

---

### Phase 4D: Synchronization & API (Week 14)

#### Task 4D.1: Vault File Watcher

**Why this matters:** Detects user edits in Obsidian and syncs changes back to the backend and Neo4j.

```python
# backend/app/services/obsidian/watcher.py

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import logging

logger = logging.getLogger(__name__)


class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path, on_change, debounce_ms: int = 1000):
        self.vault_path = vault_path
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self._pending = {}
    
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        if "/.obsidian/" in event.src_path:
            return
        self._schedule_callback(Path(event.src_path))
    
    def _schedule_callback(self, path: Path):
        # Debounced callback implementation
        pass


class VaultWatcher:
    def __init__(self, vault_path: str, sync_callback=None):
        self.vault_path = Path(vault_path)
        self.sync_callback = sync_callback
        self._observer = None
    
    def start(self):
        handler = VaultEventHandler(self.vault_path, self.sync_callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.vault_path), recursive=True)
        self._observer.start()
    
    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
```

**Deliverables:**
- [ ] `VaultEventHandler` with debouncing
- [ ] `VaultWatcher` lifecycle management
- [ ] Ignore `.obsidian/` directory
- [ ] Unit tests

**Estimated Time:** 4 hours

---

#### Task 4D.1b: Config Watcher for Tag Taxonomy

**Why this matters:** When `config/tag-taxonomy.yaml` changes, the `meta/tag-taxonomy.md` file in the vault needs to be regenerated automatically. This ensures the human-readable reference stays in sync with the single source of truth.

```python
# backend/app/services/config_watcher.py

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import yaml

from app.services.obsidian.vault import get_vault_manager

logger = logging.getLogger(__name__)


class TaxonomyConfigHandler(FileSystemEventHandler):
    """Watches config/tag-taxonomy.yaml and regenerates meta/tag-taxonomy.md."""
    
    def __init__(self, config_path: Path, vault_path: Path):
        self.config_path = config_path
        self.vault_path = vault_path
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name == "tag-taxonomy.yaml":
            logger.info("Tag taxonomy config changed, regenerating vault reference...")
            self._regenerate_taxonomy_md()
    
    def _regenerate_taxonomy_md(self):
        """Regenerate meta/tag-taxonomy.md from YAML config."""
        try:
            from scripts.setup_vault import generate_tag_taxonomy_md
            generate_tag_taxonomy_md(self.vault_path, self.config_path)
            logger.info("✅ Regenerated meta/tag-taxonomy.md")
        except Exception as e:
            logger.error(f"Failed to regenerate tag taxonomy: {e}")


class ConfigWatcher:
    """Watches config directory for changes that require vault updates."""
    
    def __init__(self, config_dir: str = "config", vault_path: str = None):
        self.config_dir = Path(config_dir)
        self.vault_path = Path(vault_path) if vault_path else get_vault_manager().vault_path
        self._observer = None
    
    def start(self):
        taxonomy_handler = TaxonomyConfigHandler(
            self.config_dir / "tag-taxonomy.yaml",
            self.vault_path
        )
        self._observer = Observer()
        self._observer.schedule(taxonomy_handler, str(self.config_dir), recursive=False)
        self._observer.start()
        logger.info(f"Config watcher started: {self.config_dir}")
    
    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
```

**Auto-Generated File Warning:**

The generated `meta/tag-taxonomy.md` includes a prominent warning:

```markdown
> [!warning] Auto-Generated File
> This file is automatically generated from `config/tag-taxonomy.yaml`.
> **Do not edit this file directly** — your changes will be overwritten.
> To modify the tag taxonomy, edit `config/tag-taxonomy.yaml` and run:
> ```bash
> python scripts/setup_vault.py --regenerate-taxonomy
> ```
```

**Deliverables:**
- [ ] `TaxonomyConfigHandler` watching `config/tag-taxonomy.yaml`
- [ ] `ConfigWatcher` for config directory changes
- [ ] `generate_tag_taxonomy_md()` function (in `scripts/setup_vault.py`)
- [ ] Auto-generated warning in `meta/tag-taxonomy.md`
- [ ] Unit tests

**Estimated Time:** 2 hours

---

#### Task 4D.2: Neo4j Sync Service

**Why this matters:** Syncs note edits (links, tags) to the knowledge graph for consistent querying.

```python
# backend/app/services/obsidian/sync.py

from pathlib import Path
import aiofiles
import logging

from app.services.obsidian.links import extract_wikilinks, extract_tags
from app.services.obsidian.frontmatter import parse_frontmatter
from app.services.knowledge_graph.client import Neo4jClient

logger = logging.getLogger(__name__)


class VaultSyncService:
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
    
    async def sync_note(self, note_path: Path) -> dict:
        async with aiofiles.open(note_path, "r") as f:
            content = await f.read()
        
        fm, body = await parse_frontmatter(content)
        outgoing_links = extract_wikilinks(body)
        inline_tags = extract_tags(body)
        all_tags = list(set(fm.get("tags", []) + inline_tags))
        
        # Update Neo4j
        node_id = fm.get("neo4j_id") or note_path.stem
        await self.neo4j.update_note_node(
            node_id=node_id, title=fm.get("title", note_path.stem),
            note_type=fm.get("type", "note"), tags=all_tags
        )
        await self._sync_links(node_id, outgoing_links)
        
        return {"path": str(note_path), "links": len(outgoing_links)}
    
    async def _sync_links(self, source_id: str, targets: list[str]):
        await self.neo4j.clear_outgoing_links(source_id)
        for target in targets:
            await self.neo4j.create_link_relationship(source_id, target, "LINKS_TO")
```

**Deliverables:**
- [ ] `VaultSyncService` class
- [ ] Link extraction and sync
- [ ] Full vault sync method
- [ ] Integration tests

**Estimated Time:** 4 hours

---

#### Task 4D.3: Vault API Router

**Why this matters:** Exposes vault operations to frontend and external systems.

```python
# backend/app/routers/vault.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter(prefix="/api/vault", tags=["vault"])


@router.get("/status")
async def get_vault_status():
    """Get vault status and statistics."""
    vault = get_vault_manager()
    return {
        "vault_path": str(vault.vault_path),
        "exists": vault.vault_path.exists()
    }


@router.post("/initialize")
async def initialize_vault():
    """Initialize vault folder structure."""
    vault = get_vault_manager()
    result = await vault.initialize_structure()
    return {"status": "initialized", **result}


@router.post("/indices/regenerate")
async def regenerate_indices(background_tasks: BackgroundTasks):
    """Regenerate all folder indices."""
    indexer = FolderIndexer(get_vault_manager())
    background_tasks.add_task(indexer.regenerate_all_indices)
    return {"status": "regenerating"}


@router.post("/daily")
async def create_daily_note(target_date: Optional[str] = None):
    """Create today's daily note."""
    daily_gen = DailyNoteGenerator(get_vault_manager())
    dt = date.fromisoformat(target_date) if target_date else None
    path = await daily_gen.generate_daily_note(dt)
    return {"path": path}
```

**Deliverables:**
- [ ] `/status` endpoint
- [ ] `/initialize` endpoint
- [ ] `/indices/regenerate` endpoint
- [ ] `/daily` endpoint
- [ ] Unit tests for all endpoints

**Estimated Time:** 4 hours

---

## 4. Testing Strategy

### 4.1 Test Structure

```
tests/
├── unit/obsidian/
│   ├── test_vault.py              # VaultManager (uses ContentTypeRegistry)
│   ├── test_frontmatter.py        # FrontmatterBuilder, parsing
│   ├── test_links.py              # WikilinkBuilder, extraction
│   ├── test_template_engine.py    # TemplateEngine, filter tests
│   ├── test_generator.py          # NoteGenerator
│   └── test_daily.py              # DailyNoteGenerator
├── integration/
│   ├── test_vault_sync.py         # Neo4j sync
│   └── test_vault_api.py          # API endpoints
└── fixtures/
    ├── sample_vault/              # Test vault structure
    └── sample_templates/          # Test templates
```

### 4.2 Key Test Cases

| Component | Test Case | Priority |
|-----------|-----------|----------|
| Vault | Initialize creates all folders | High |
| Frontmatter | Parse and generate valid YAML | High |
| Links | Extract wikilinks correctly | High |
| Templates | Render all content types | High |
| Generator | Create notes in correct folders | High |
| Watcher | Detect file changes | High |
| Sync | Update Neo4j on change | High |

---

## 5. Configuration

### 5.1 Single Source of Truth Architecture

| Configuration | Location | Purpose |
|---------------|----------|---------|
| **Content Types & Vault Structure** | `config/default.yaml` under `content_types` | Folder paths, template mappings, subfolders, descriptions |
| **Content Type Registry** | `app/content_types.py` (`ContentTypeRegistry` class) | Python API for accessing content type config |
| **Tag Taxonomy** | `config/tag-taxonomy.yaml` | Single source of truth for valid tags |
| Note Templates (Jinja2) | `config/templates/*.md.j2` | Backend note generation |
| Note Templates (Obsidian) | Vault `templates/*.md` | Manual note creation via Templater |
| Runtime Settings | Environment variables / `ObsidianSettings` | Paths, feature flags |

> **IMPORTANT**: The `ContentTypeRegistry` from `app/content_types.py` is the **shared registry** used across all components. See `00_foundation_implementation.md` Task 1A.2 for the full implementation.

### 5.2 Runtime Settings

```python
# backend/app/config/obsidian.py

from pydantic_settings import BaseSettings

class ObsidianSettings(BaseSettings):
    # Paths
    OBSIDIAN_VAULT_PATH: str = "/path/to/vault"
    TEMPLATES_DIR: str = "config/templates"
    
    # Note Generation
    NOTE_CREATE_CONCEPTS: bool = True
    NOTE_MAX_HIGHLIGHTS: int = 50
    NOTE_DEFAULT_TEMPLATE: str = "article.md.j2"
    
    # File Watcher
    VAULT_WATCH_ENABLED: bool = True
    VAULT_SYNC_DEBOUNCE_MS: int = 1000
    
    # Neo4j Sync
    VAULT_SYNC_NEO4J_ENABLED: bool = True
    
    class Config:
        env_prefix = "OBSIDIAN_"
```

### 5.3 Config File Locations

```
project_root/
├── config/
│   ├── default.yaml               # Content types, vault structure, app settings
│   ├── tag-taxonomy.yaml          # Single source of truth: tag taxonomy
│   └── templates/                 # Jinja2 templates for backend generation
│       ├── paper.md.j2
│       ├── article.md.j2
│       ├── book.md.j2
│       ├── code.md.j2
│       ├── concept.md.j2
│       ├── daily.md.j2
│       ├── career.md.j2
│       ├── personal.md.j2
│       ├── project.md.j2
│       ├── reflection.md.j2
│       ├── _index.md.j2
│       └── dashboard.md.j2
├── backend/
│   └── app/
│       └── content_types.py       # ContentTypeRegistry class
```

### 5.4 How Components Use ContentTypeRegistry

```python
# Example: Using ContentTypeRegistry across components

from app.content_types import content_registry

# Ingestion Pipeline: Determine content type from source
content_type = determine_type(source)  # e.g., "paper"
folder = content_registry.get_folder(content_type)  # "sources/papers"

# Note Generator: Get Jinja2 template
ct = content_registry.get(content_type)
jinja_template = ct.get("jinja_template")  # "paper.md.j2"

# Frontend: Get user-selectable content types for dropdown
types = content_registry.user_types  # ['paper', 'article', 'book', ...]

# Vault Setup: Get all folders to create
all_folders = content_registry.get_all_folders()  # Dynamic list
```

---

## 6. Timeline Summary

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 11 | 4A | Foundation | Vault structure config, VaultManager, frontmatter, links |
| 12 | 4B | Templates | Template engine, `.md.j2` files, NoteGenerator |
| 13 | 4C | Automation | Indexer, daily notes, dataview library |
| 14 | 4D | Sync & API | Watcher, Neo4j sync, API endpoints |

**Total Estimated Time:** ~45-55 hours

---

## 7. Success Criteria

### Functional
- [ ] Vault initialized from `ContentTypeRegistry` (reads `config/default.yaml` content_types)
- [ ] Notes generated using Jinja2 templates from `config/templates/*.md.j2`
- [ ] Template selection uses `jinja_template` field from content_types config
- [ ] Valid frontmatter parseable by Obsidian and Dataview
- [ ] Wikilinks correctly link to concept notes
- [ ] Tag taxonomy loaded from `config/tag-taxonomy.yaml`
- [ ] Indices auto-generated with metadata from templates
- [ ] Neo4j updated on note edits

### Non-Functional
- [ ] Note generation < 1 second
- [ ] Watcher uses < 50MB memory
- [ ] API responds < 500ms

### Single Source of Truth
- [ ] Content types defined only in `config/default.yaml` (not duplicated)
- [ ] `ContentTypeRegistry` from `app/content_types.py` used by all components
- [ ] No hard-coded folder mappings in Python code
- [ ] No hard-coded template mappings in Python code
- [ ] No hard-coded tag taxonomy (uses Obsidian vault or YAML fallback)
- [ ] Adding new content type requires only YAML + template file changes

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| File permission errors | High | Medium | Validate vault path on startup |
| Concurrent file access | Medium | Medium | Debounce writes |
| Large vault performance | Medium | Low | Pagination, lazy loading |
| Neo4j sync conflicts | Medium | Medium | Last-write-wins |

---

## 9. Dependencies

### Required Before Phase 4
- [x] Phase 1: Foundation
- [x] Phase 2: Ingestion Layer
- [x] Phase 3: LLM Processing

### Enables After Phase 4
- Phase 5: Knowledge Explorer UI
- Phase 6: Spaced Repetition
- Phase 7: Mobile PWA

---

## 10. Open Questions

1. **Conflict Resolution**: How to handle conflicts between Obsidian edits and backend regeneration?
2. **Concept Deduplication**: Merge vs. separate concept notes from multiple sources?
3. **Vault Backup**: Auto-backup before regeneration?
4. **Multi-Vault Support**: Multiple vaults for different domains?
5. **Template Sync**: Should template changes in `config/templates/` trigger cache invalidation automatically?

### Resolved Questions

- ~~**Template Customization**: User-editable templates via config or Obsidian?~~
  - **Answer**: Templates are Jinja2 `.md.j2` files in `config/templates/`. Users edit these files directly.
- ~~**Tag Taxonomy Location**: Where is the source of truth for tags?~~
  - **Answer**: Single source of truth is `config/tag-taxonomy.yaml`. No fallback or duplicate sources.
- ~~**Vault Structure Configuration**: Separate vault-structure.yaml or unified config?~~
  - **Answer**: Consolidated into `config/default.yaml` under `content_types` section. Uses `ContentTypeRegistry` from `app/content_types.py` for access. See `00_foundation_implementation.md` Task 1A.2.
- ~~**Content Type to Folder Mapping**: Separate mapping or integrated with content types?~~
  - **Answer**: Integrated into `content_types` config. Each content type has a `folder` field directly in its definition.

---

## Related Documents

- `design_docs/03_knowledge_hub_obsidian.md` — Design specification
- `design_docs/04_knowledge_graph_neo4j.md` — Neo4j schema
- `implementation_plan/00_foundation_implementation.md` — **ContentTypeRegistry definition** (Task 1A.2), vault structure config
- `implementation_plan/02_llm_processing_implementation.md` — Upstream processor

