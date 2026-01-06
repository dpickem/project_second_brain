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

**STATUS: ✅ PHASE 4 COMPLETE**

All Phase 4 components have been implemented. This document serves as both reference documentation and architectural context for the implemented features.

| Component | Status | Location |
|-----------|--------|----------|
| ContentTypeRegistry | ✅ Complete | `backend/app/content_types.py` |
| Jinja2 Templates | ✅ Complete | `config/templates/*.md.j2` |
| Basic Note Generator | ✅ Complete | `backend/app/services/processing/output/obsidian_generator.py` |
| Neo4j Node Generator | ✅ Complete | `backend/app/services/processing/output/neo4j_generator.py` |
| Tag Taxonomy Loader | ✅ Complete | `backend/app/services/processing/stages/taxonomy_loader.py` |
| VaultManager Service | ✅ Complete | `backend/app/services/obsidian/vault.py` |
| Frontmatter Utilities | ✅ Complete | `backend/app/services/obsidian/frontmatter.py` |
| Wikilink Utilities | ✅ Complete | `backend/app/services/obsidian/links.py` |
| Folder Indexer | ✅ Complete | `backend/app/services/obsidian/indexer.py` |
| Daily Note Generator | ✅ Complete | `backend/app/services/obsidian/daily.py` |
| Dataview Query Library | ✅ Complete | `backend/app/services/obsidian/dataview_queries.py` |
| Vault File Watcher | ✅ Complete | `backend/app/services/obsidian/watcher.py` |
| Neo4j Sync Service | ✅ Complete | `backend/app/services/obsidian/sync.py` |
| Startup Lifecycle | ✅ Complete | `backend/app/services/obsidian/lifecycle.py` |
| Vault API Endpoints | ✅ Complete | `backend/app/routers/vault.py` |
| SystemMeta Model | ✅ Complete | `backend/app/db/models.py` |

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
                            │  (✅ Complete)   │
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
│  │    - Queue Celery task for Neo4j sync                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  SHUTDOWN                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. Store last_sync_time in database (SystemMeta)        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Scope

| In Scope (All Complete) | Out of Scope |
|-------------------------|--------------|
| ✅ VaultManager service class | Obsidian plugin development |
| ✅ Frontmatter utilities module | Custom Obsidian themes |
| ✅ Wikilink utilities module | Third-party plugin configuration |
| ✅ Folder index auto-generation | Real-time collaborative editing |
| ✅ Daily note automation | Mobile Obsidian sync (Obsidian Sync) |
| ✅ Vault file change watcher | Obsidian Publish integration |
| ✅ Startup reconciliation (offline changes) | Full-text search (Obsidian native) |
| ✅ Bi-directional Neo4j sync | Graph view customization |
| ✅ Vault API endpoints | |
| ✅ Dataview query library | |

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

### 2.2 Dependencies — ✅ All Installed

These packages are in `backend/requirements.txt`:

```txt
jinja2>=3.1.0              # ✅ Template rendering (used by obsidian_generator)
aiofiles>=24.1.0           # ✅ Async file operations
PyYAML>=6.0                # ✅ YAML processing
python-frontmatter>=1.1.0  # ✅ YAML frontmatter parsing
watchdog>=4.0.0            # ✅ File system monitoring for vault changes
```

| Package | Why This One | Alternatives Considered |
|---------|--------------|------------------------|
| `watchdog` | Cross-platform file system monitoring with debouncing support | `inotify` (Linux only), polling (inefficient) |
| `python-frontmatter` | Clean API for parsing/modifying YAML frontmatter in markdown | Manual regex parsing (error-prone) |
| `aiofiles` | Async file I/O for FastAPI compatibility | Sync I/O with thread pool (more complex) |

### 2.3 Environment Variables

```bash
# Core vault configuration
OBSIDIAN_VAULT_PATH=/path/to/vault

# Sync configuration (optional, have defaults)
VAULT_WATCH_ENABLED=true                  # Enable file watcher
VAULT_SYNC_DEBOUNCE_MS=1000               # Debounce for rapid changes
VAULT_SYNC_NEO4J_ENABLED=true             # Sync changes to Neo4j
```

---

## 3. Existing Implementations (Reference)

This section documents what was built in Phase 2/3 that Phase 4 builds upon.

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

## 4. Implementation Phases

### Phase 4A: Enhanced Vault Management (Week 11) — ✅ Complete

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
│   │   │   ├── dataview_queries.py   # Dataview query templates
│   │   │   └── lifecycle.py          # Startup/shutdown lifecycle management
│   ├── routers/
│   │   └── vault.py                  # Vault API endpoints
```

**Deliverables:** ✅ All Complete
- [x] Create `backend/app/services/obsidian/` directory
- [x] Create `__init__.py` with proper exports
- [x] Obsidian settings integrated in main settings

---

#### Task 4A.2: VaultManager Service

**Why this matters:** While basic note writing exists in `obsidian_generator.py`, a comprehensive VaultManager provides vault-wide operations: structure initialization, validation, note listing, and safe file operations. This centralizes vault logic and enables features like folder indexing and daily notes.

**Location**: `backend/app/services/obsidian/vault.py`

**Key Design Decisions:**
- **Idempotent operations**: `ensure_structure()` is safe to call multiple times - existing folders are left untouched
- **Single source of truth**: Uses ContentTypeRegistry for all folder mappings (no hardcoded paths)
- **Cross-platform**: Sanitizes filenames for Windows/macOS/Linux compatibility
- **Async-first**: All I/O operations are async for FastAPI compatibility

**Folder Structure** (from `config/default.yaml`):
```
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
```

**Deliverables:** ✅ All Complete
- [x] `VaultManager` class with idempotent `ensure_structure()` method
- [x] Path utilities using `ContentTypeRegistry`
- [x] Safe file read/write operations
- [x] Vault statistics method
- [x] Singleton accessor `get_vault_manager()`
- [x] `create_vault_manager()` for setup scripts with optional validation

---

#### Task 4A.3: Frontmatter Utilities

**Why this matters:** A dedicated frontmatter module provides a fluent builder API and utilities for parsing/updating frontmatter in existing notes. This enables the vault watcher to read metadata and the sync service to update it.

**Location**: `backend/app/services/obsidian/frontmatter.py`

**Key Features:**
- `FrontmatterBuilder` - Fluent builder with type-safe methods (`set_type()`, `set_tags()`, etc.)
- `parse_frontmatter()` - Extract metadata dict and body content
- `parse_frontmatter_file()` - Async parsing from file path
- `update_frontmatter()` - Modify existing note's frontmatter without touching body
- `frontmatter_to_string()` - Convert dict + content back to markdown

**Deliverables:** ✅ All Complete
- [x] `FrontmatterBuilder` fluent builder class
- [x] Frontmatter parsing utilities
- [x] Frontmatter update utility
- [x] `frontmatter_to_string()` helper

---

#### Task 4A.4: Wikilink Utilities

**Why this matters:** Wikilinks are the backbone of Obsidian's knowledge graph. Proper link handling enables connection extraction for Neo4j sync, auto-linking concepts, and broken link detection.

**Location**: `backend/app/services/obsidian/links.py`

**Wikilink Syntax Reference:**
```
[[Note Name]]              - Basic link to a note
[[Note Name|Display Text]] - Link with custom display text (alias)
[[Note Name#Header]]       - Link to a specific header in a note
[[Note Name#^block-id]]    - Link to a specific block (paragraph)
![[Note Name]]             - Embed (transclude) another note
![[image.png]]             - Embed an image
```

**Key Components:**
- `WikilinkBuilder` - Static methods for creating properly formatted links
- `extract_wikilinks()` - Parse note content to find outgoing links
- `extract_tags()` - Find inline #tags in content
- `auto_link_concepts()` - Automatically convert known terms to wikilinks
- `validate_links()` - Find broken links (targets that don't exist)
- `create_backlink_section()` - Generate backlinks list from Neo4j data

**Integration with Neo4j:**
Extracted wikilinks are used by `VaultSyncService` to create `LINKS_TO` relationships in the knowledge graph, enabling:
- Graph traversal and visualization
- Backlink queries
- Related note suggestions
- Orphan note detection

**Deliverables:** ✅ All Complete
- [x] `WikilinkBuilder` for creating various link types
- [x] Wikilink extraction from content
- [x] Tag extraction from content
- [x] Connection section generation
- [x] Auto-linking for known concepts
- [x] Broken link validation
- [x] Backlink section generation

---

### Phase 4B: Automation Features (Week 12) — ✅ Complete

#### Task 4B.1: Folder Index Generator

**Why this matters:** Auto-generated indices make vault navigation easier. Each folder gets an `_index.md` that lists its contents, grouped and sorted for quick access.

**Location**: `backend/app/services/obsidian/indexer.py`

**Key Features:**
- Index notes use `_index.md` naming (underscore prefix) so they appear at top of folder listings
- Parses frontmatter to extract title, type, tags, processed date
- Sorts by processed date (newest first)
- Shows "Recent" section (top 10) and "All Notes" section
- Empty folders get placeholder index with "No notes yet"
- `regenerate_all_indices()` updates all content type folders

**Deliverables:** ✅ All Complete
- [x] `FolderIndexer` class with metadata parsing
- [x] Index generation with sorting by date
- [x] `regenerate_all_indices()` method
- [x] Empty folder handling

---

#### Task 4B.2: Daily Note Generator

**Why this matters:** Daily notes provide a consistent entry point for captures, learning activities, and reflections. The template is loaded from `config/templates/daily.md.j2`.

**Location**: `backend/app/services/obsidian/daily.py`

**Key Features:**
- Uses Jinja2 template from `config/templates/daily.md.j2`
- Template name comes from ContentTypeRegistry (`daily` content type)
- Won't overwrite existing daily notes (safe to call multiple times)
- `add_inbox_item()` for quick captures to today's note
- Date context variables: `date_iso`, `date_full`, `year`, `month`, `day`, `weekday`

**Deliverables:** ✅ All Complete
- [x] `DailyNoteGenerator` using Jinja2 template
- [x] Template loaded from `config/templates/daily.md.j2`
- [x] `add_inbox_item()` method for quick captures
- [x] Won't overwrite existing daily notes

---

#### Task 4B.3: Dataview Query Library

**Why this matters:** Pre-built Dataview queries power dynamic dashboards and help users get immediate value from their vault.

**Location**: `backend/app/services/obsidian/dataview_queries.py`

**Available Queries:**
- `recent_notes(folder, limit)` - Recently processed notes in a folder
- `unread_by_type(content_type)` - Unread notes of specific type
- `open_tasks()` - Incomplete tasks across vault
- `knowledge_stats()` - Note counts grouped by type
- `notes_by_domain(domain)` - Notes in a specific domain
- `mastery_questions()` - Notes with mastery questions section
- `concepts_index()` - All concept notes with domain/complexity
- `due_for_review()` - Spaced repetition queue
- `recently_created(days)` - Notes created in last N days
- `notes_with_follow_ups()` - Notes with follow-up tasks

**Deliverables:** ✅ All Complete
- [x] `DataviewLibrary` class with common queries
- [x] Dashboard query generator
- [x] Additional queries (due_for_review, recently_created, etc.)

---

### Phase 4C: Synchronization (Week 13) — ✅ Complete

#### Task 4C.1: Vault File Watcher

**Why this matters:** Detects user edits in Obsidian and syncs changes back to the backend (Neo4j graph updates, tag sync, etc.).

**Location**: `backend/app/services/obsidian/watcher.py`

**Architecture:**
```
VaultWatcher (lifecycle management)
    └── VaultEventHandler (event filtering & debouncing)
            └── watchdog.Observer (OS-level file monitoring)
```

**Key Features:**
- **Debounced callbacks**: Rapid successive saves are coalesced into single callback
- **Selective monitoring**: Only watches `.md` files, ignores `.obsidian/` config directory
- **Thread-safe**: Uses locking for safe concurrent access to pending changes
- **Graceful lifecycle**: Clean start/stop with proper thread cleanup

**Deliverables:** ✅ All Complete
- [x] `VaultEventHandler` with debouncing
- [x] `VaultWatcher` lifecycle management
- [x] Ignore `.obsidian/` directory
- [x] Thread-safe pending changes handling

---

#### Task 4C.2: Neo4j Sync Service

**Why this matters:** When users edit notes in Obsidian (add links, change tags), those changes should sync to Neo4j to keep the knowledge graph current. This service also handles **startup reconciliation** to detect changes made while the app was offline.

**Location**: `backend/app/services/obsidian/sync.py`

**Three-Tier Sync Strategy:**

| Mode | Use Case | When Called |
|------|----------|-------------|
| `sync_note(path)` | Real-time single note sync | VaultWatcher callback |
| `reconcile_on_startup(vault_path)` | Sync changes made while offline | FastAPI startup |
| `full_sync(vault_path)` | Complete vault sync | Manual API trigger |

**What Gets Synced:**
- Frontmatter metadata (title, type, tags)
- Wikilinks → `LINKS_TO` relationships in Neo4j
- Inline #tags merged with frontmatter tags

**Node ID Strategy:**
- Uses frontmatter `id` field if present
- Otherwise generates deterministic UUID5 from absolute file path
- Generated UUID is persisted back to frontmatter for stability

**Progress Tracking:**
- `SyncStatus` dataclass tracks running syncs
- `get_sync_status()` returns progress for API polling
- Prevents concurrent full syncs

**Persistence:**
- `last_sync_time` stored in PostgreSQL `SystemMeta` table
- Used by reconciliation to find files modified while offline

**Deliverables:** ✅ All Complete
- [x] `VaultSyncService` class with three sync modes
- [x] `reconcile_on_startup()` for offline change detection
- [x] `SystemMeta` model for storing last sync time
- [x] Note metadata extraction and sync
- [x] Link relationship sync via Neo4jClient
- [x] `full_sync()` method with progress tracking
- [x] `SyncStatus` dataclass for API polling
- [x] Deterministic UUID generation for notes

---

#### Task 4C.3: Startup Lifecycle Integration

**Why this matters:** Integrates the vault watcher and sync service into the FastAPI application lifecycle, ensuring offline changes are detected on startup and real-time watching begins automatically.

**Location**: `backend/app/services/obsidian/lifecycle.py`

**Startup Sequence:**
1. Validate vault path exists (via VaultManager)
2. Run reconciliation to sync notes modified while app was offline
3. Start file watcher for real-time change detection
4. Watcher calls `sync_vault_note` Celery task on file changes (debounced)

**Shutdown Sequence:**
1. Stop watcher (halts file system monitoring)
2. Update `last_sync_time` in database

**Why Celery for Watcher Callbacks:**
- Automatic retries if Neo4j is temporarily unavailable
- Task visibility and monitoring via Redis
- Decouples watcher thread from asyncio event loop
- Better handling of burst file changes

**Deliverables:** ✅ All Complete
- [x] `lifecycle.py` module with startup/shutdown functions
- [x] Integration with FastAPI lifespan context manager
- [x] Celery task queuing for watcher callbacks
- [x] Graceful shutdown with sync time update
- [x] Status endpoint integration

---

### Phase 4D: API Endpoints (Week 14) — ✅ Complete

#### Task 4D.1: Vault API Router

**Why this matters:** Exposes vault operations to the frontend and external systems via REST API.

**Location**: `backend/app/routers/vault.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vault/status` | GET | Vault health, statistics, and watcher status |
| `/api/vault/ensure-structure` | POST | Create missing folders (idempotent) |
| `/api/vault/indices/regenerate` | POST | Regenerate all folder indices (background) |
| `/api/vault/daily` | POST | Create daily note for date |
| `/api/vault/daily/inbox` | POST | Add item to daily note inbox |
| `/api/vault/sync` | POST | Full vault sync to Neo4j (background) |
| `/api/vault/folders` | GET | List all content type folders |
| `/api/vault/watcher/status` | GET | File watcher runtime status |
| `/api/vault/sync/status` | GET | Sync progress and last sync time |

**Deliverables:** ✅ All Complete
- [x] `/status` endpoint
- [x] `/ensure-structure` endpoint (idempotent)
- [x] `/indices/regenerate` endpoint
- [x] `/daily` endpoint
- [x] `/daily/inbox` endpoint
- [x] `/sync` endpoint
- [x] `/folders` endpoint
- [x] `/watcher/status` endpoint
- [x] `/sync/status` endpoint

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

### 6.1 Single Source of Truth Architecture

| Configuration | Location | Status |
|---------------|----------|--------|
| Content Types & Vault Structure | `config/default.yaml` | ✅ Complete |
| Content Type Registry | `app/content_types.py` | ✅ Complete |
| Tag Taxonomy | `config/tag-taxonomy.yaml` | ✅ Complete |
| Note Templates (Jinja2) | `config/templates/*.md.j2` | ✅ Complete |
| Vault Settings | `app/config/settings.py` | ✅ Complete |

---

## 7. Success Criteria — ✅ All Met

### Functional
- [x] Vault initialized from `ContentTypeRegistry`
- [x] Notes generated using Jinja2 templates
- [x] Template selection uses config
- [x] Valid frontmatter generated
- [x] VaultManager provides vault-wide operations
- [x] Folder indices auto-generated
- [x] Daily notes created from template
- [x] Vault watcher detects real-time changes
- [x] Startup reconciliation syncs offline changes
- [x] Neo4j updated on note edits
- [x] API endpoints functional

### Non-Functional
- [x] Note generation < 1 second
- [x] Watcher uses minimal memory (debouncing prevents buildup)
- [x] Startup reconciliation efficient (only modified files)
- [x] API responds quickly

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| File permission errors | High | Medium | Validate vault path on startup |
| Concurrent file access | Medium | Medium | Debounce writes, Celery task queue |
| Neo4j sync conflicts | Medium | Medium | Last-write-wins, log conflicts |
| Large vault performance | Medium | Low | Background processing, pagination |
| Missed offline changes | Medium | Low | Reconciliation uses mtime comparison |
| Clock skew (mtime inaccurate) | Low | Low | Full sync API as fallback |
| Startup delay (large vault) | Medium | Medium | Async reconciliation, progress logging |

---

## 9. Dependencies

### Required Before Phase 4 — ✅ All Complete
- [x] Phase 1: Foundation (ContentTypeRegistry, config structure)
- [x] Phase 2: Ingestion Layer (content models)
- [x] Phase 3: LLM Processing (note generation, Neo4j integration)

### Enables After Phase 4
- Phase 5: Knowledge Explorer UI
- Phase 6: Spaced Repetition
- Phase 7: Mobile PWA

---

## 10. Related Documents

- `design_docs/03_knowledge_hub_obsidian.md` — Design specification
- `design_docs/04_knowledge_graph_neo4j.md` — Neo4j schema
- `implementation_plan/00_foundation_implementation.md` — ContentTypeRegistry definition
- `implementation_plan/02_llm_processing_implementation.md` — Note generator implementation
- `implementation_plan/04_knowledge_graph_neo4j_implementation.md` — Neo4j implementation
