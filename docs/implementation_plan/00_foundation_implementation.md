# Foundation & Knowledge Hub Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Target Phase**: Phase 1 (Weeks 1-2 per roadmap)  
> **Design Docs**: `design_docs/00_system_overview.md`, `design_docs/03_knowledge_hub_obsidian.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for Phase 1: Foundation, which establishes the core infrastructure and knowledge hub that all subsequent phases build upon. This phase has two main tracks:

1. **Knowledge Hub Setup** — Configure Obsidian vault with folder structure, templates, plugins, and tagging taxonomy
2. **Infrastructure Completion** — Add PostgreSQL, Redis, and database migrations to the existing Docker stack

### Why This Phase Matters

Phase 1 is the **critical foundation** that enables everything else:

| Foundation Component | What It Enables |
|---------------------|-----------------|
| **PostgreSQL** | Persistent storage for content metadata, learning records, practice history, and spaced repetition scheduling. Unlike Neo4j (which stores knowledge *relationships*), PostgreSQL stores *transactional data* that needs ACID guarantees. |
| **Redis** | Fast session caching for the web app, temporary storage during processing, and task queue backend for async operations. Without Redis, every page load would hit the database. |
| **Obsidian Vault Structure** | Consistent organization means ingestion pipelines know exactly where to write notes, and the LLM processing layer knows what format to generate. |
| **Note Templates** | Templates ensure every ingested piece of content has the same structure, making it queryable via Dataview and enabling automated processing. |
| **Tagging Taxonomy** | A controlled vocabulary prevents tag sprawl. Without it, you'd end up with `ml`, `ML`, `machine-learning`, `machine_learning` all meaning the same thing. |
| **Alembic Migrations** | Database schema changes are inevitable. Migrations let us evolve the schema safely without losing data. |

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Obsidian vault folder structure | Content ingestion pipelines |
| Note templates for all content types | LLM processing |
| Tagging taxonomy definition | Frontend UI components |
| Essential plugin configuration | Mobile capture |
| PostgreSQL container & schema | Multi-user authentication |
| Redis container for caching | Production deployment |
| Alembic database migrations | Knowledge graph queries |
| Configuration management | External API integrations |

---

## 2. Prerequisites

### 2.1 Infrastructure (Already Complete)

- [x] Docker & Docker Compose installed
- [x] Neo4j container configured
- [x] FastAPI backend skeleton
- [x] React/Vite frontend skeleton

### 2.2 Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Obsidian | Latest | Knowledge hub application |
| Python | 3.11+ | Backend services |
| Node.js | 18+ | Frontend build |
| Docker | 24+ | Container orchestration |
| PostgreSQL | 16 | Learning records database |
| Redis | 7 | Session caching & queues |

### 2.3 Dependencies to Install

```txt
# Add to backend/requirements.txt
sqlalchemy[asyncio]>=2.0.0    # Async ORM
asyncpg>=0.29.0               # PostgreSQL async driver
alembic>=1.13.0               # Database migrations
redis>=5.0.0                  # Redis client
python-dotenv>=1.0.0          # Environment management
pydantic-settings>=2.0.0      # Settings management
pyyaml>=6.0.0                 # YAML configuration
```

**Why these specific packages:**

| Package | Why This One | Alternatives Considered |
|---------|--------------|------------------------|
| `sqlalchemy[asyncio]` | Industry standard ORM with excellent async support. The `[asyncio]` extra installs `greenlet` for async operations. | Django ORM (too heavyweight), raw SQL (too verbose) |
| `asyncpg` | Fastest PostgreSQL driver for Python. Uses binary protocol instead of text, 3x faster than psycopg2. | `psycopg3` (good but asyncpg is more mature for async) |
| `alembic` | The standard migration tool for SQLAlchemy. Auto-generates migrations from model changes. | `yoyo` (simpler but less integrated) |
| `redis` | Official Redis client with native async support (redis-py 5.0+). | `aioredis` (deprecated, merged into redis-py) |
| `pydantic-settings` | Type-safe configuration with automatic env variable loading. Validates config at startup, fails fast if misconfigured. | `python-decouple` (simpler but no validation) |
| `pyyaml` | Standard YAML parser. Used for application config that doesn't contain secrets. | `ruamel.yaml` (preserves comments, overkill here) |

### 2.4 Environment Variables

```bash
# .env file additions
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=secondbrain

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# Obsidian
OBSIDIAN_VAULT_PATH=/path/to/vault

# Existing (already configured)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
OPENAI_API_KEY=<api_key>
```

---

## 3. Implementation Phases

### Phase 1A: Infrastructure Completion (Days 1-3)

#### Task 1A.1: Docker Compose Update

**Purpose**: Add PostgreSQL and Redis to the existing Docker stack to provide persistent storage and caching.

**Why Docker Compose?** All services run in isolated containers with defined dependencies. The `depends_on` with `condition: service_healthy` ensures the backend doesn't start until databases are ready—preventing connection errors on startup.

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| **Alpine images** for PostgreSQL/Redis | Smaller image size (~50MB vs ~150MB), faster pulls, smaller attack surface |
| **Health checks** on all services | Backend waits for databases to be truly ready, not just "container started" |
| **Named volumes** | Data persists across container restarts. Without volumes, you'd lose all data when containers stop. |
| **Append-only Redis** (`--appendonly yes`) | Redis writes every operation to disk. Survives restarts without data loss. |
| **Vault mounted read-write** | Backend needs to write notes to the Obsidian vault |

Extend `docker-compose.yml` with PostgreSQL and Redis services:

```yaml
# docker-compose.yml

version: '3.8'

services:
  neo4j:
    image: neo4j:5
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH}
    depends_on:
      neo4j:
        condition: service_healthy
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ${OBSIDIAN_VAULT_PATH}:/vault:rw

  frontend:
    build: ./frontend
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    ports:
      - "3000:3000"

volumes:
  neo4j_data:
  postgres_data:
  redis_data:
```

**Deliverables:**
- [x] PostgreSQL service added to docker-compose.yml
- [x] Redis service added to docker-compose.yml
- [x] Health checks configured for all services
- [x] Volume persistence configured
- [x] Backend dependencies updated

**Estimated Time:** 2 hours

---

#### Task 1A.2: Configuration Management

**Purpose**: Centralize all application configuration in one place with validation, making it easy to change settings without modifying code.

**The Two-Layer Configuration Strategy:**

We use TWO configuration mechanisms that serve different purposes:

| Layer | File | Contains | Changes How Often | Who Changes It |
|-------|------|----------|-------------------|----------------|
| **Environment Variables** | `.env` | **Secrets & deployment-specific settings** (passwords, API keys, database hosts) | Per deployment | DevOps/Admin |
| **YAML Configuration** | `config/default.yaml` | **Application behavior settings** (folder names, TTLs, pool sizes, template mappings) | Rarely, by developers | Developer |

**Why Not Put Everything in Environment Variables?**

1. **Readability**: Complex nested config (like folder structures) is unreadable as env vars
2. **Type Safety**: YAML naturally represents lists, dicts, nested structures
3. **Documentation**: YAML allows comments explaining each setting
4. **Defaults**: Code shouldn't hardcode defaults—they belong in config files

**Why Not Put Everything in YAML?**

1. **Secrets**: Never commit secrets to version control
2. **Deployment Variance**: Database hosts differ per environment (local vs staging vs prod)
3. **12-Factor App**: Environment variables are the standard for deployment config

**How They Work Together:**

```text
APPLICATION STARTUP
===================

1. Pydantic Settings loads from:
   - .env file (secrets, hosts, credentials)
   - Environment variables (override .env)

2. YAML config loads from:
   - config/default.yaml (app behavior)
   - config/{ENV}.yaml if exists (env-specific overrides)

3. Both are validated at startup
   - Missing required values -> app fails to start
   - Invalid types -> app fails to start
```

Create centralized configuration with Pydantic settings:

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Second Brain"
    DEBUG: bool = False
    
    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "secondbrain"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "secondbrain"
    
    @property
    def POSTGRES_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def POSTGRES_URL_SYNC(self) -> str:
        """Sync URL for Alembic migrations."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    
    # Obsidian
    OBSIDIAN_VAULT_PATH: Path = Path("/vault")
    
    # OpenAI
    OPENAI_API_KEY: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
```

```yaml
# config/default.yaml
#
# PURPOSE: Application behavior configuration (NOT secrets)
# 
# This file defines HOW the application behaves:
# - Folder structure for the Obsidian vault
# - Template mappings for each content type  
# - Database connection pool sizing
# - Cache TTL values
#
# WHEN TO EDIT THIS FILE:
# - Adding a new content type (new template, new folder)
# - Tuning performance (pool sizes, TTLs)
# - Changing organizational structure
#
# WHEN NOT TO EDIT THIS FILE:
# - Changing database passwords -> use .env
# - Changing hostnames for different environments -> use .env
# - Changing API keys -> use .env

app:
  name: "Second Brain"        # Display name in logs and UI
  debug: false                # Set via DEBUG env var in production

# =============================================================================
# OBSIDIAN VAULT CONFIGURATION
# =============================================================================
# These settings tell the ingestion pipelines WHERE to write notes
# and WHICH template to use for each content type.
#
# EXTENSIBILITY: This configuration is designed to be extended without code changes.
# To add a new content type:
#   1. Add entry to content_types below
#   2. Create the template file in templates/
#   3. (Optional) Add subfolder structure
#   4. (Optional) Add tags to tag taxonomy
# The system will automatically recognize and handle the new type.

obsidian:
  vault_path: "/vault"        # Overridden by OBSIDIAN_VAULT_PATH env var
  
  # Top-level folder names in the vault
  # Changing these changes where notes are stored
  folders:
    sources: "sources"        # Raw ingested content organized by type
    topics: "topics"          # Topic-based index notes (auto-generated)
    concepts: "concepts"      # Standalone concept definitions (atomic notes)
    exercises: "exercises"    # Generated practice problems
    reviews: "reviews"        # Spaced repetition cards and queue
    daily: "daily"            # Daily notes (YYYY-MM-DD.md)
    templates: "templates"    # Note templates (not shown in Obsidian)
    meta: "meta"              # System config, dashboards, documentation

# =============================================================================
# CONTENT TYPE REGISTRY
# =============================================================================
# This is the single source of truth for all content types in the system.
# Each content type defines:
#   - folder: Where notes are stored in the vault
#   - template: Obsidian template path (for manual creation via Templater)
#   - jinja_template: Jinja2 template filename (for backend note generation)
#   - subfolders: Optional subfolders for organization
#   - description: Human-readable description
#   - icon: Optional emoji for UI display
#   - file_types: What file types this content type accepts
#   - system: If true, hidden from user content type selectors
#
# TWO TYPES OF TEMPLATES:
#   - template: Plain Markdown in vault's templates/ folder, used by Templater
#               plugin when user manually creates notes in Obsidian
#   - jinja_template: Jinja2 template in config/templates/, used by backend
#               when generating notes programmatically
#
# TO ADD A NEW CONTENT TYPE:
# 1. Add a new entry below with unique key
# 2. Create Obsidian template file in vault's templates/ folder
# 3. Create Jinja2 template file in config/templates/
# 4. Run `python scripts/setup/setup_vault.py` to create folders
# 5. The system will automatically handle ingestion, queries, and display

content_types:
  # ---------------------------------------------------------------------------
  # TECHNICAL CONTENT
  # ---------------------------------------------------------------------------
  paper:
    folder: "sources/papers"
    template: "templates/paper.md"           # Obsidian template (for Templater)
    jinja_template: "paper.md.j2"            # Backend Jinja2 template
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
    jinja_template: "article.md.j2"          # Ideas use article Jinja2 template
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
    template: "templates/personal.md"        # Reuse personal template
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
    system: true  # Not shown in content type selector
    
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

# PostgreSQL connection pool configuration
# These settings prevent overwhelming the database with connections
database:
  pool_size: 5               # Number of persistent connections to maintain
                             # Higher = more concurrent queries, more memory
  max_overflow: 10           # Extra connections allowed during spikes
                             # pool_size + max_overflow = max total connections
  pool_timeout: 30           # Seconds to wait for a connection before erroring

# Redis cache configuration  
redis:
  session_ttl: 3600          # Session expiration: 1 hour (seconds)
                             # User must re-login after this
  cache_ttl: 300             # Default cache TTL: 5 minutes
                             # Balance between freshness and performance
```

**Configuration Usage Example:**

```python
# In code, access configuration like this:
from app.config import settings, load_yaml_config

# Environment-based settings (from .env)
db_url = settings.POSTGRES_URL       # "postgresql+asyncpg://user:pass@host/db"
api_key = settings.OPENAI_API_KEY    # Never logged, never in YAML

# YAML-based settings (from config/default.yaml)
config = load_yaml_config()
template_path = config["obsidian"]["templates"]["paper"]  # "templates/paper.md"
pool_size = config["database"]["pool_size"]                # 5
```

**Content Type Registry Helper:**

```python
# backend/app/content_types.py
#
# PURPOSE: Provides a dynamic registry of content types loaded from config.
# This allows adding new content types WITHOUT code changes - just update YAML.

from functools import lru_cache
from pathlib import Path
from typing import Optional
import yaml

@lru_cache()
def load_content_types() -> dict:
    """Load content types from configuration."""
    with open("config/default.yaml") as f:
        config = yaml.safe_load(f)
    return config.get("content_types", {})


class ContentTypeRegistry:
    """
    Dynamic registry of content types.
    
    EXTENSIBILITY: This class reads content types from config/default.yaml.
    To add a new content type:
    1. Add entry to content_types in config/default.yaml
    2. Create template file
    3. The system automatically recognizes the new type
    
    No code changes required!
    """
    
    def __init__(self):
        self._types = load_content_types()
    
    @property
    def all_types(self) -> list[str]:
        """Get all content type keys."""
        return list(self._types.keys())
    
    @property
    def user_types(self) -> list[str]:
        """Get content types available for user selection (excludes system types)."""
        return [k for k, v in self._types.items() if not v.get("system", False)]
    
    def get(self, type_key: str) -> Optional[dict]:
        """Get content type configuration by key."""
        return self._types.get(type_key)
    
    def get_folder(self, type_key: str) -> Optional[str]:
        """Get folder path for a content type."""
        ct = self.get(type_key)
        return ct["folder"] if ct else None
    
    def get_template(self, type_key: str) -> Optional[str]:
        """Get Obsidian template path for a content type (for Templater)."""
        ct = self.get(type_key)
        return ct["template"] if ct else None
    
    def get_jinja_template(self, type_key: str) -> Optional[str]:
        """Get Jinja2 template name for a content type (for backend generation)."""
        ct = self.get(type_key)
        return ct.get("jinja_template") if ct else None
    
    def get_subfolders(self, type_key: str) -> list[str]:
        """Get subfolders for a content type."""
        ct = self.get(type_key)
        return ct.get("subfolders", []) if ct else []
    
    def get_all_folders(self) -> list[str]:
        """Get all folders that should be created (for vault setup)."""
        folders = []
        for type_key, config in self._types.items():
            base_folder = config["folder"]
            folders.append(base_folder)
            for subfolder in config.get("subfolders", []):
                folders.append(f"{base_folder}/{subfolder}")
        return folders
    
    def type_for_folder(self, folder_path: str) -> Optional[str]:
        """Reverse lookup: get content type from folder path."""
        for type_key, config in self._types.items():
            if folder_path.startswith(config["folder"]):
                return type_key
        return None
    
    def validate_type(self, type_key: str) -> bool:
        """Check if a content type exists."""
        return type_key in self._types


# Global singleton
content_registry = ContentTypeRegistry()


# Usage examples:
# 
# from app.content_types import content_registry
#
# # Get all user-selectable content types for dropdown
# types = content_registry.user_types  # ['paper', 'article', 'book', ...]
#
# # Get folder for a content type
# folder = content_registry.get_folder("paper")  # "sources/papers"
#
# # Get Obsidian template for a content type (for Templater plugin)
# template = content_registry.get_template("career")  # "templates/career.md"
#
# # Get Jinja2 template for backend note generation
# jinja = content_registry.get_jinja_template("career")  # "career.md.j2"
#
# # Determine content type from file path
# type_key = content_registry.type_for_folder("sources/papers/attention.md")  # "paper"
#
# # Get all folders for vault setup
# all_folders = content_registry.get_all_folders()  # Dynamic list based on config
```

**Deliverables:**
- [x] Pydantic settings class
- [x] YAML configuration file
- [x] Content type registry with dynamic loading
- [x] Environment variable validation
- [x] Configuration loading utilities

**Estimated Time:** 2 hours

---

#### Task 1A.3: PostgreSQL Database Setup

**Purpose**: Define the database schema for storing content metadata, learning records, and practice history.

**Why PostgreSQL (Not Just Neo4j)?**

We use BOTH databases, each for what it does best:

| Database | Use Case | Why |
|----------|----------|-----|
| **Neo4j** | Knowledge relationships | "What concepts are related to transformers?" "What papers cite this one?" Graph queries are natural for traversing relationships. |
| **PostgreSQL** | Transactional data | ACID compliance for practice sessions, spaced repetition scheduling, content ingestion status. Row-level locking prevents double-processing. |

**Data Model Overview:**

```text
POSTGRESQL SCHEMA
=================

Content Pipeline                     Learning System
+------------+                       +------------------+
| Content    | 1 --------------- * | Annotation       |
| - id       |                       | - content_id     |
| - title    |                       | - text           |
| - type     |                       | - page_number    |
| - status   |                       +------------------+
+------------+
      |                              +------------------+
      |                              | PracticeSession  | 1
      |                              | - started_at     |----+
      |                              | - topics         |    |
      |                              +------------------+    | *
      |                                               +------------+
      +---------------------------------------------->| Attempt    |
                                                      | - correct  |
Taxonomy              Spaced Repetition              +------------+
+----------+         +------------------+
| Tag      |         | SpacedRepCard    |
| - name   |         | - front/back     |
| - cat    |         | - due_date       |
| - parent |         | - stability      |  (FSRS algorithm)
+----------+         +------------------+

Analytics
+-------------------+
| MasterySnapshot   |  Daily snapshots of mastery scores by topic
|                   |  Powers the analytics dashboard and trends
+-------------------+
```

Create database connection management and base models:

```python
# backend/app/db/base.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

```python
# backend/app/db/models.py
#
# PURPOSE: SQLAlchemy models defining the PostgreSQL schema
# 
# These models are the single source of truth for the database structure.
# Alembic reads these models to auto-generate migrations.

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, backref
from app.db.base import Base
import uuid
from datetime import datetime


class Content(Base):
    """
    Tracks ALL ingested content regardless of source type.
    
    This is the central registry of everything in the Second Brain.
    One row = one piece of content (paper, article, book, etc.)
    
    The processing pipeline:
    1. Content ingested -> status='pending'
    2. Text extracted -> status='extracted'
    3. LLM processing -> status='processed'
    4. Note written -> status='complete', obsidian_path populated
    5. If error -> status='error', error_message populated
    """
    __tablename__ = "content"
    
    # Primary key: UUID prevents enumeration attacks, works for distributed systems
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content type: 'paper', 'article', 'book', 'code', 'idea', etc.
    # Maps to subfolders in config/default.yaml and determines which template to use
    source_type = Column(String(50), nullable=False, index=True)
    
    # Where the content came from (for deduplication and back-reference)
    source_url = Column(Text)          # Web URL, DOI, GitHub URL
    source_file_path = Column(Text)    # Local path to uploaded file
    
    # Basic metadata
    title = Column(String(500), nullable=False)
    authors = Column(ARRAY(String))    # PostgreSQL array type for multiple authors
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)       # When content was originally created/published
    ingested_at = Column(DateTime, default=datetime.utcnow)  # When we imported it
    
    # Extracted content
    full_text = Column(Text)           # Full extracted text (for search, embeddings)
    
    # Deduplication: SHA-256 hash of the raw file
    # If same hash exists, we've already ingested this content
    raw_file_hash = Column(String(64), index=True, unique=True)
    
    # Processing state machine
    processing_status = Column(String(20), default="pending", index=True)
    error_message = Column(Text)       # Detailed error for debugging
    
    # Output location
    obsidian_path = Column(Text)       # Path to generated note: "sources/papers/2024-attention.md"
    
    # Flexible storage for source-specific metadata
    # Paper: { "doi": "...", "venue": "NeurIPS 2024", "citations": 150 }
    # Book: { "isbn": "...", "publisher": "...", "pages": 450 }
    metadata = Column(JSON, default=dict)
    
    # Relationship: one content -> many annotations
    annotations = relationship("Annotation", back_populates="content", cascade="all, delete-orphan")


class Annotation(Base):
    """
    Extracted annotations from content (highlights, handwritten notes, etc.)
    
    Annotations are the raw pieces of insight extracted from content BEFORE
    they're processed by LLMs. Each annotation might become:
    - A highlight block in the Obsidian note
    - A concept extracted for the knowledge graph  
    - A flashcard for spaced repetition
    """
    __tablename__ = "annotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    
    # Type of annotation
    # 'highlight' = yellow marker in PDF
    # 'handwritten' = handwritten note (OCR'd)
    # 'comment' = typed annotation in Kindle/Reader
    # 'bookmark' = marked section without text
    type = Column(String(50), nullable=False)
    
    text = Column(Text, nullable=False)        # The annotation text itself
    page_number = Column(Integer)              # Page number (PDFs, books)
    
    # Position within the content (for linking back to source)
    # { "start": 1024, "end": 1156, "rect": [x1, y1, x2, y2] }
    position = Column(JSON)
    
    # Surrounding text for context (helps LLM understand the annotation)
    context = Column(Text)
    
    # OCR confidence score (0.0-1.0) for handwritten annotations
    # High confidence = can process automatically
    # Low confidence = flag for human review
    confidence = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    content = relationship("Content", back_populates="annotations")


class Tag(Base):
    """
    Central tag registry for the taxonomy.
    
    Tags are stored here (not just in Obsidian notes) for:
    1. Validation: reject unknown tags, suggest alternatives
    2. Hierarchy: know that 'ml/transformers' is under 'ml'
    3. Analytics: count usage, find underused tags
    4. Sync: push tag changes to Obsidian via Tag Wrangler
    
    HIERARCHY DESIGN:
    Tags form a 3-level tree structure via self-referential FK.
    
        ml (parent_id=NULL)                          <- domain
        |-- ml/architecture (parent_id -> ml.id)     <- category
        |   |-- ml/architecture/transformers         <- topic
        |   |-- ml/architecture/llms
        |   +-- ml/architecture/diffusion
        +-- ml/technique (parent_id -> ml.id)
            |-- ml/technique/fine-tuning
            +-- ml/technique/rlhf
    
    Using FK instead of storing parent name as string because:
    - Referential integrity: DB rejects invalid parent references
    - Rename-safe: renaming "ml" to "machine-learning" doesn't break children
    - ORM navigation: tag.parent.name, tag.children work automatically
    """
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Full tag path including hierarchy: "ml/transformers"
    # This is the display name used in Obsidian notes
    name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Tag category for grouping:
    # 'domain' = topic tags (ml, systems, engineering)
    # 'status' = workflow state (actionable, reference, archive)  
    # 'quality' = content type (foundational, deep-dive, overview)
    # 'source' = auto-applied by content type (paper, article, book)
    category = Column(String(50))
    
    # Self-referential FK for hierarchy
    # "ml/transformers" -> parent_id points to "ml" tag's UUID
    # NULL = root-level tag (no parent)
    parent_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("tags.id", ondelete="SET NULL"),  # If parent deleted, children become roots
        nullable=True,
        index=True
    )
    
    # ORM relationships for easy navigation
    # tag.parent -> get parent Tag object
    # tag.children -> get list of child Tag objects
    parent = relationship(
        "Tag", 
        remote_side=[id],  # Points to the 'id' column of the parent
        backref=backref("children", lazy="selectin")  # Efficient loading of children
    )
    
    # Human description for documentation
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PracticeSession(Base):
    """
    A single practice/study session.
    
    Sessions track engagement over time. Each session contains multiple
    practice attempts across different topics. Used for:
    - Streak tracking ("You've practiced 7 days in a row!")
    - Session analytics ("Average 23 minutes per session")
    - Topic coverage ("You haven't practiced ML in 2 weeks")
    """
    __tablename__ = "practice_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime)              # NULL = session in progress
    
    # Topics covered in this session (denormalized for fast queries)
    # ["ml/transformers", "systems/distributed"]
    topics = Column(JSON)
    
    # Session summary stats (updated after each attempt)
    exercise_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    
    attempts = relationship("PracticeAttempt", back_populates="session", cascade="all, delete-orphan")


class PracticeAttempt(Base):
    """
    A single practice question attempt.
    
    Records EVERY attempt at EVERY question for detailed analytics:
    - Which concepts are struggling? (low is_correct rate)
    - Is confidence calibrated? (high confidence but wrong answers)
    - How does time spent correlate with correctness?
    """
    __tablename__ = "practice_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id"), nullable=False)
    
    # Links to Neo4j concept node (not FK because different database)
    concept_id = Column(UUID(as_uuid=True))
    
    # Exercise type from learning science research:
    # 'free-recall' = "Explain X without looking at notes"
    # 'self-explain' = "Why does this work?"
    # 'worked-example' = "Walk through this solution"
    # 'elaborative-interrogation' = "How does X relate to Y?"
    exercise_type = Column(String(50))
    
    prompt = Column(Text, nullable=False)     # The question asked
    response = Column(Text)                   # User's answer (for review)
    is_correct = Column(Boolean)              # Did they get it right?
    
    # Confidence tracking (calibration metric)
    confidence_before = Column(Float)         # "How confident are you?" (1-5)
    confidence_after = Column(Float)          # "After seeing answer, how confident?" (1-5)
    
    time_spent_seconds = Column(Integer)      # Response time
    feedback = Column(Text)                   # LLM-generated feedback on their answer
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("PracticeSession", back_populates="attempts")


class SpacedRepCard(Base):
    """
    Spaced repetition cards using the FSRS algorithm.
    
    FSRS (Free Spaced Repetition Scheduler) is a modern algorithm that
    outperforms SM-2 (Anki's default) by using a more accurate memory model.
    
    Key FSRS concepts:
    - Stability: days until 90% recall probability
    - Difficulty: how hard the card is (0-1, higher = harder)
    - State: new -> learning -> review (-> relearning if lapsed)
    
    Reference: https://github.com/open-spaced-repetition/fsrs4anki
    """
    __tablename__ = "spaced_rep_cards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Links to knowledge graph and source content
    concept_id = Column(UUID(as_uuid=True))   # Neo4j concept node
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"))  # Source material
    
    # Card content
    front = Column(Text, nullable=False)      # Question/prompt
    back = Column(Text, nullable=False)       # Answer/explanation
    
    # FSRS algorithm parameters
    difficulty = Column(Float, default=0.3)   # Initial difficulty (0-1)
    stability = Column(Float, default=1.0)    # Days until 90% recall
    due_date = Column(DateTime)               # When to show next
    last_review = Column(DateTime)            # Last review timestamp
    review_count = Column(Integer, default=0) # Total reviews
    lapses = Column(Integer, default=0)       # Times forgotten (relearning)
    
    # Card state machine:
    # 'new' -> never reviewed
    # 'learning' -> being learned (short intervals)
    # 'review' -> graduated to review queue (longer intervals)
    # 'relearning' -> forgot and re-learning
    state = Column(String(20), default="new")
    
    created_at = Column(DateTime, default=datetime.utcnow)


class MasterySnapshot(Base):
    """
    Daily snapshots of mastery scores by topic.
    
    Mastery scores are computed from:
    - Spaced rep card stability
    - Practice attempt accuracy
    - Time since last practice
    
    Daily snapshots enable:
    - Progress graphs over time
    - "You've improved 15% in ML this month"
    - Identifying skill decay
    """
    __tablename__ = "mastery_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    concept_id = Column(UUID(as_uuid=True))   # Specific concept (optional)
    topic_path = Column(String(255), index=True)  # "ml/transformers" or just "ml"
    
    # Computed metrics (0.0 - 1.0)
    mastery_score = Column(Float)             # Overall mastery
    confidence_avg = Column(Float)            # Average confidence rating
    
    # Activity metrics
    practice_count = Column(Integer)          # Total practices for this topic
    last_practiced = Column(DateTime)         # Most recent practice
    
    # Indexed for time-series queries: "mastery over last 30 days"
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
```

**Deliverables:**
- [x] Async SQLAlchemy engine setup
- [x] Session management with dependency injection
- [x] Core database models (Content, Annotation, Tag)
- [ ] Learning system models (PracticeSession, SpacedRepCard, MasterySnapshot)

**Estimated Time:** 3 hours

---

#### Task 1A.4: Alembic Migrations Setup

**Purpose**: Enable safe, versioned changes to the database schema over time.

**Why Migrations Matter:**

Without migrations, schema changes require:
1. Manually writing ALTER TABLE statements
2. Hoping you remember what changed
3. Praying you can replicate in production

With Alembic:
1. Change the SQLAlchemy model
2. Run `alembic revision --autogenerate` -> migration script created
3. Run `alembic upgrade head` -> schema updated
4. Commit migration to git -> teammates get the same change

**Migration Workflow:**

```text
ALEMBIC MIGRATION FLOW
======================

1. Developer modifies models.py
   - Add column: SpacedRepCard.ease_factor

2. Generate migration
   $ alembic revision --autogenerate -m "add ease_factor"
   - Creates: alembic/versions/abc123_add_ease_factor.py

3. Review generated migration
   - Check upgrade() and downgrade() are correct
   - Alembic auto-detection isn't perfect for all changes

4. Apply migration
   $ alembic upgrade head
   - Database schema now matches models

5. Rollback if needed
   $ alembic downgrade -1
   - Reverts the last migration
```

Configure Alembic for database migrations:

```bash
# Initialize Alembic
cd backend
alembic init alembic
```

```python
# backend/alembic/env.py

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db import models  # Import all models
from app.config import settings

config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.POSTGRES_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Run migration
alembic upgrade head
```

**Deliverables:**
- [x] Alembic configuration
- [x] Initial migration script
- [x] Migration commands documented

**Estimated Time:** 1 hour

---

#### Task 1A.5: Redis Connection Setup

**Purpose**: Provide fast in-memory caching and session storage to reduce database load.

**What Redis Is Used For:**

| Use Case | Why Redis | Alternative Without Redis |
|----------|-----------|---------------------------|
| **Session Storage** | User sessions in memory. Sub-millisecond reads. | Store in PostgreSQL: slower, more DB load |
| **Cache Layer** | Cache expensive queries (concept lookups, user stats) | Re-query database every time: slow |
| **Rate Limiting** | Track API requests per user with TTL | Manual expiration logic: complex |
| **Task Queues** (future) | Background job processing | Polling database: inefficient |

**Redis Data Patterns:**

```text
REDIS KEY PATTERNS
==================

Sessions (TTL: 1 hour)
  session:{session_id} -> { user_id, started_at, topics }

Cache (TTL: 5 minutes)
  secondbrain:user:{user_id}:stats -> { mastery, streak, ... }
  secondbrain:concept:{id} -> { name, connections, ... }

Processing Locks (TTL: 5 minutes)
  lock:content:{content_id} -> "processing"
  (Prevents duplicate processing of same content)

Rate Limits (TTL: 1 minute)
  rate:{user_id}:{endpoint} -> count
```

Create Redis client utilities:

```python
# backend/app/db/redis.py

import redis.asyncio as redis
from app.config import settings
from contextlib import asynccontextmanager
import json
from typing import Optional, Any
from datetime import timedelta

# Create connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=10
)


async def get_redis() -> redis.Redis:
    """Get Redis connection from pool."""
    return redis.Redis(connection_pool=redis_pool)


class RedisCache:
    """Redis caching utilities."""
    
    def __init__(self, prefix: str = "secondbrain"):
        self.prefix = prefix
    
    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with redis.Redis(connection_pool=redis_pool) as r:
            value = await r.get(self._key(key))
            if value:
                return json.loads(value)
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 300
    ) -> None:
        """Set value in cache with optional TTL."""
        async with redis.Redis(connection_pool=redis_pool) as r:
            await r.set(
                self._key(key),
                json.dumps(value),
                ex=ttl
            )
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with redis.Redis(connection_pool=redis_pool) as r:
            await r.delete(self._key(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        async with redis.Redis(connection_pool=redis_pool) as r:
            return await r.exists(self._key(key)) > 0


class SessionStore:
    """Redis-backed session storage."""
    
    def __init__(self, ttl: int = 3600):
        self.cache = RedisCache(prefix="session")
        self.ttl = ttl
    
    async def create_session(self, session_id: str, data: dict) -> None:
        """Create a new session."""
        await self.cache.set(session_id, data, ttl=self.ttl)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return await self.cache.get(session_id)
    
    async def update_session(self, session_id: str, data: dict) -> None:
        """Update session data."""
        await self.cache.set(session_id, data, ttl=self.ttl)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session."""
        await self.cache.delete(session_id)


# Global instances
cache = RedisCache()
session_store = SessionStore()
```

**Deliverables:**
- [x] Redis connection pool
- [x] Caching utilities
- [x] Session store implementation

**Estimated Time:** 2 hours

---

### Phase 1B: Knowledge Hub Setup (Days 4-7)

#### Task 1B.1: Obsidian Vault Structure Creation

**Purpose**: Create a consistent folder structure that supports both human navigation AND automated processing.

**Why This Specific Structure?**

The folder structure serves TWO audiences:

| Audience | Need | How Structure Helps |
|----------|------|---------------------|
| **Human (you)** | Find notes quickly, browse by topic | Intuitive hierarchy: `sources/papers/`, `concepts/` |
| **Backend (pipelines)** | Know where to write notes, which template to use | Deterministic paths: content type -> folder mapping |

**Folder-by-Folder Explanation:**

```text
vault/
|-- sources/              # RAW INGESTED CONTENT (organized by source type)
|   |-- papers/           # Academic papers -> use paper.md template
|   |-- articles/         # Web articles, blog posts -> article.md template
|   |-- books/            # Book notes -> book.md template
|   |-- code/             # GitHub repos analyzed -> code.md template
|   |-- ideas/            # Quick captures, fleeting notes -> idea.md template
|   |-- work/             # Work-specific content
|   |   |-- meetings/     # Meeting notes
|   |   |-- proposals/    # Proposals, design docs
|   |   +-- projects/     # Work project-specific notes
|   |-- career/           # Career development content
|   |   |-- goals/        # Career goals and planning
|   |   |-- interviews/   # Interview prep, experiences
|   |   |-- networking/   # Networking notes, contacts
|   |   +-- skills/       # Skill development tracking
|   |-- personal/         # Personal development content
|   |   |-- goals/        # Personal goals, life planning
|   |   |-- reflections/  # Journal entries, retrospectives
|   |   |-- habits/       # Habit tracking, routines
|   |   +-- wellbeing/    # Health, fitness, mental wellness
|   |-- projects/         # Personal project notes
|   |   |-- active/       # Currently active projects
|   |   |-- ideas/        # Project ideas, brainstorms
|   |   +-- archive/      # Completed/paused projects
|   +-- non-tech/         # Non-technical learning
|       |-- finance/      # Personal finance, investing
|       |-- hobbies/      # Hobbies, creative pursuits
|       |-- philosophy/   # Philosophy, thinking frameworks
|       +-- misc/         # Miscellaneous topics
|
|-- topics/               # TOPIC INDEX NOTES (auto-generated)
|                         # "Machine Learning.md" links to all ML-tagged notes
|
|-- concepts/             # ATOMIC CONCEPT NOTES (Zettelkasten style)
|                         # One concept = one note
|
|-- exercises/            # PRACTICE PROBLEMS
|   |-- by-topic/         # Exercises organized by topic
|   +-- daily/            # Daily generated practice sets
|
|-- reviews/              # SPACED REPETITION
|   |-- due/              # Cards due for review
|   +-- archive/          # Completed/retired cards
|
|-- daily/                # DAILY NOTES (YYYY-MM-DD.md)
|
|-- templates/            # NOTE TEMPLATES (used by Templater plugin)
|
|-- meta/                 # SYSTEM DOCUMENTATION
|   |-- dashboard.md      # Main entry point with Dataview queries
|   |-- tag-taxonomy.md   # Tag definitions and rules
|   +-- workflows.md      # How to use the system
|
+-- assets/               # BINARY ATTACHMENTS
    |-- images/           # Screenshots, diagrams
    +-- pdfs/             # Original PDFs (if stored locally)
```

Create the vault folder structure and initialize with placeholder files:

```python
# scripts/setup/setup_vault.py

from pathlib import Path
import yaml

def create_vault_structure(vault_path: Path, config: dict):
    """
    Create the Obsidian vault folder structure.
    
    EXTENSIBILITY: This function dynamically reads content types from config.
    To add new content types, just update config/default.yaml - no code changes needed.
    """
    
    vault_path.mkdir(parents=True, exist_ok=True)
    
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
        (vault_path / folder).mkdir(parents=True, exist_ok=True)
        print(f"Created: {folder}")
    
    # Dynamically create folders from content_types registry
    # This reads from config/default.yaml, so adding a new content type
    # there will automatically create the folder here
    content_types = config.get("content_types", {})
    
    for type_key, type_config in content_types.items():
        # Create base folder
        base_folder = type_config.get("folder", f"sources/{type_key}")
        (vault_path / base_folder).mkdir(parents=True, exist_ok=True)
        print(f"Created: {base_folder}")
        
        # Create subfolders if defined
        for subfolder in type_config.get("subfolders", []):
            subfolder_path = f"{base_folder}/{subfolder}"
            (vault_path / subfolder_path).mkdir(parents=True, exist_ok=True)
            print(f"Created: {subfolder_path}")
    
    print(f"\n✅ Vault structure created at: {vault_path}")
    print(f"   Content types loaded: {len(content_types)}")
    
    # Create .gitkeep files for empty folders
    for folder in folders:
        folder_path = vault_path / folder
        if not any(folder_path.iterdir()):
            (folder_path / ".gitkeep").touch()
    
    print(f"\n✅ Vault structure created at: {vault_path}")


def create_obsidian_config(vault_path: Path):
    """Create Obsidian app configuration."""
    
    obsidian_dir = vault_path / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    
    # App settings
    app_settings = {
        "alwaysUpdateLinks": True,
        "newFileLocation": "folder",
        "newFileFolderPath": "sources/ideas",
        "attachmentFolderPath": "assets",
        "showUnsupportedFiles": False,
        "strictLineBreaks": False,
        "useMarkdownLinks": False,
        "promptDelete": True,
    }
    
    with open(obsidian_dir / "app.json", "w") as f:
        json.dump(app_settings, f, indent=2)
    
    # Core plugins to enable
    core_plugins = [
        "file-explorer",
        "global-search", 
        "switcher",
        "graph",
        "backlink",
        "outgoing-link",
        "tag-pane",
        "page-preview",
        "daily-notes",
        "templates",
        "note-composer",
        "command-palette",
        "editor-status",
        "starred",
        "outline",
        "word-count",
    ]
    
    with open(obsidian_dir / "core-plugins.json", "w") as f:
        json.dump(core_plugins, f, indent=2)
    
    # Daily notes settings
    daily_notes_settings = {
        "folder": "daily",
        "format": "YYYY-MM-DD",
        "template": "templates/daily.md"
    }
    
    with open(obsidian_dir / "daily-notes.json", "w") as f:
        json.dump(daily_notes_settings, f, indent=2)
    
    # Templates settings
    templates_settings = {
        "folder": "templates",
        "dateFormat": "YYYY-MM-DD",
        "timeFormat": "HH:mm"
    }
    
    with open(obsidian_dir / "templates.json", "w") as f:
        json.dump(templates_settings, f, indent=2)
    
    print("✅ Obsidian configuration created")


def generate_tag_taxonomy_md(vault_path: Path, taxonomy_config_path: Path = None):
    """
    Generate meta/tag-taxonomy.md from config/tag-taxonomy.yaml.
    
    The YAML config is the single source of truth. This function generates
    a human-readable markdown reference for use within Obsidian.
    
    The generated file includes a warning that it's auto-generated.
    """
    taxonomy_config_path = taxonomy_config_path or Path("config/tag-taxonomy.yaml")
    
    if not taxonomy_config_path.exists():
        print(f"⚠️  Tag taxonomy config not found: {taxonomy_config_path}")
        return
    
    with open(taxonomy_config_path) as f:
        taxonomy = yaml.safe_load(f)
    
    # Build markdown content
    lines = [
        "---",
        "type: meta",
        "title: Tag Taxonomy",
        "---",
        "",
        "> [!warning] Auto-Generated File",
        "> This file is automatically generated from `config/tag-taxonomy.yaml`.",
        "> **Do not edit this file directly** — your changes will be overwritten.",
        "> To modify the tag taxonomy, edit `config/tag-taxonomy.yaml` and run:",
        "> ```bash",
        "> python scripts/setup/setup_vault.py --regenerate-taxonomy",
        "> ```",
        "",
        "# Tag Taxonomy",
        "",
        "This document defines the valid tags for the knowledge base.",
        "Tags follow the `domain/category/topic` hierarchy (up to 3 levels).",
        "",
        "---",
        "",
        "## Domain Tags",
        "",
    ]
    
    # Add domain tags
    domains = taxonomy.get("domains", [])
    if isinstance(domains, list):
        # Simple list format
        for tag in domains:
            lines.append(f"- `{tag}`")
    elif isinstance(domains, dict):
        # Hierarchical format
        for domain, categories in domains.items():
            lines.append(f"### {domain.replace('-', ' ').title()}")
            lines.append("")
            if isinstance(categories, dict):
                for category, topics in categories.items():
                    if isinstance(topics, list):
                        for topic in topics:
                            lines.append(f"- `{domain}/{category}/{topic}`")
                    else:
                        lines.append(f"- `{domain}/{category}`")
            elif isinstance(categories, list):
                for cat in categories:
                    lines.append(f"- `{domain}/{cat}`")
            lines.append("")
    
    lines.extend([
        "",
        "---",
        "",
        "## Status Tags",
        "",
    ])
    
    # Add status tags
    for tag in taxonomy.get("status", []):
        lines.append(f"- `{tag}`")
    
    lines.extend([
        "",
        "## Quality Tags",
        "",
    ])
    
    # Add quality tags
    for tag in taxonomy.get("quality", []):
        lines.append(f"- `{tag}`")
    
    lines.extend([
        "",
        "---",
        "",
        "## Usage Guidelines",
        "",
        "1. **Always use existing tags** when possible",
        "2. **Create new tags** by adding them to `config/tag-taxonomy.yaml`",
        "3. **Follow the hierarchy**: `domain/category/topic`",
        "4. **Use lowercase** with hyphens for multi-word tags",
        "",
        "---",
        "",
        f"*Generated from `config/tag-taxonomy.yaml`*",
    ])
    
    # Write to meta/tag-taxonomy.md
    output_path = vault_path / "meta" / "tag-taxonomy.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"✅ Generated: meta/tag-taxonomy.md (from config/tag-taxonomy.yaml)")


if __name__ == "__main__":
    import json
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Obsidian vault structure")
    parser.add_argument("--regenerate-taxonomy", action="store_true",
                        help="Only regenerate meta/tag-taxonomy.md from YAML config")
    args = parser.parse_args()
    
    vault_path = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "./vault"))
    
    if args.regenerate_taxonomy:
        # Only regenerate the tag taxonomy markdown
        generate_tag_taxonomy_md(vault_path)
    else:
        # Full vault setup
        with open("config/default.yaml") as f:
            config = yaml.safe_load(f)
        
        create_vault_structure(vault_path, config)
        create_obsidian_config(vault_path)
        generate_tag_taxonomy_md(vault_path)  # Also generate tag taxonomy
```

**Deliverables:**
- [x] Vault folder structure created
- [x] Obsidian configuration files
- [x] Vault setup script

**Estimated Time:** 2 hours

---

#### Task 1B.2: Note Templates

**Purpose**: Define consistent structures for each content type so notes are queryable and processable.

**Why Templates Are Critical:**

| Without Templates | With Templates |
|-------------------|----------------|
| Every note has different frontmatter | All papers have `type: paper`, `status: unread`, etc. |
| Can't query "unread papers" | `WHERE status = "unread" AND type = "paper"` works |
| LLM output varies wildly | LLM fills in predefined sections |
| Hard to know what's missing | Clear sections: Summary, Key Findings, My Notes |

**Template Design Principles:**

1. **Frontmatter first**: YAML metadata enables Dataview queries
2. **LLM-fillable sections**: Marked with `<!-- LLM-generated -->` comments
3. **Human sections**: Space for your own thoughts (never auto-overwritten)
4. **Consistent structure**: Same sections across content types where applicable
5. **Templater syntax**: `{{date:YYYY-MM-DD}}` for dynamic content

**Frontmatter Schema (Required Fields):**

```yaml
# Every note MUST have these fields for system compatibility
type: string          # Content type: paper, article, book, code, concept, idea
title: string         # Human-readable title
tags: string[]        # Array of tags from taxonomy
status: string        # Processing status: unread, processing, processed
created: date         # When the note was created (YYYY-MM-DD)
```

Create templates for each content type:

```markdown
<!-- templates/paper.md -->
---
type: paper
title: "{{title}}"
authors: []
year: {{date:YYYY}}
venue: ""
doi: ""
tags: []
status: unread
has_handwritten_notes: false
created: {{date:YYYY-MM-DD}}
processed: 
---

## Summary
<!-- LLM-generated summary will be inserted here -->

## Key Findings
- 

## Core Concepts
- **Concept**: Definition

## My Highlights
> Highlight text
> — Page X

## My Handwritten Notes
> [!note] Page X
> Transcription
> *Context: "surrounding text"*

## Mastery Questions
- [ ] Question 1
- [ ] Question 2

## Follow-up Tasks
- [ ] Task #research

## Connections
- [[Related Note]] — Relationship explanation

---

## Detailed Notes
```

```markdown
<!-- templates/article.md -->
---
type: article
title: "{{title}}"
source: ""
author: ""
published: 
tags: []
status: unread
created: {{date:YYYY-MM-DD}}
processed:
---

## Summary
<!-- LLM-generated summary -->

## Key Takeaways
1. 
2. 

## Highlights
> Highlight text

## My Notes


## Action Items
- [ ] 

## Related
- [[Related Note]]
```

```markdown
<!-- templates/book.md -->
---
type: book
title: "{{title}}"
author: ""
isbn: ""
tags: []
status: reading
started: {{date:YYYY-MM-DD}}
finished: 
rating: 
---

## Overview


## Key Themes
### Theme 1


## Highlights by Chapter

### Chapter 1: Title
> Highlight
> — Page X



## Favorite Quotes
> "Quote"
> — Author, p. X

## How This Changed My Thinking


## Action Items
- [ ] 

## Related Books
- [[Other Book]]
```

```markdown
<!-- templates/code.md -->
---
type: code
repo: "{{title}}"
url: ""
language: ""
stars: 
tags: []
created: {{date:YYYY-MM-DD}}
---

## Purpose


## Why I Saved This


## Architecture Overview


## Tech Stack
- **Language**: 
- **Framework**: 
- **Dependencies**: 

## Notable Patterns
### Pattern Name


## Key Learnings
1. 
2. 

## Ideas to Apply
- [ ] 

## Related
- [[Related Repo]]
```

```markdown
<!-- templates/concept.md -->
---
type: concept
name: "{{title}}"
domain: ""
complexity: foundational
tags: []
created: {{date:YYYY-MM-DD}}
---

## Definition


## Why It Matters


## Key Properties
- 

## Examples
### Example 1


## Common Misconceptions
- ❌ Misconception
- ✅ Correction

## Prerequisites
- [[Prerequisite Concept]]

## Related Concepts
- [[Related]] — Relationship

## Sources
- [[Source Paper]]
```

```markdown
<!-- templates/idea.md -->
---
type: idea
title: "{{title}}"
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Idea


## Context


## Why It Matters


## Next Steps
- [ ] 

## Related
- [[Related Note]]
```

```markdown
<!-- templates/daily.md -->
---
type: daily
date: {{date:YYYY-MM-DD}}
---

# {{date:dddd, MMMM D, YYYY}}

## 📥 Inbox
<!-- Quick captures, ideas, todos that need processing -->


## 📚 Learning
### Today's Practice
- [ ] Complete review queue ([[reviews/_queue]])

### Notes Processed
<!-- Links to notes processed today -->


## ✅ Tasks
### Must Do
- [ ] 

### Should Do
- [ ] 

### Could Do
- [ ] 

## 📝 Journal
<!-- Reflection, thoughts, learnings -->


## 🔗 Quick Links
- [[meta/dashboard|Dashboard]]
- [[reviews/_queue|Review Queue]]
```

```markdown
<!-- templates/exercise.md -->
---
type: exercise
topic: ""
difficulty: intermediate
exercise_type: free-recall
source_concept: ""
tags: []
created: {{date:YYYY-MM-DD}}
---

## Question


## Expected Answer


## Hints
1. 
2. 

## Related Concepts
- [[Concept]]

## Source Material
- [[Source Note]]
```

```markdown
<!-- templates/career.md -->
---
type: career
title: "{{title}}"
category: ""
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Overview


## Why This Matters


## Current State
<!-- Where am I now? -->


## Target State
<!-- Where do I want to be? -->


## Action Plan
- [ ] 

## Resources Needed
- 

## Timeline
| Milestone | Target Date | Status |
|-----------|-------------|--------|
|           |             |        |

## Progress Notes


## Related
- [[Related Note]]
```

```markdown
<!-- templates/personal.md -->
---
type: personal
title: "{{title}}"
area: ""
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Summary


## Why This Matters to Me


## Key Insights
1. 
2. 
3. 

## How This Applies to My Life


## Action Items
- [ ] 

## Reflections


## Related
- [[Related Note]]
```

```markdown
<!-- templates/project.md -->
---
type: project
title: "{{title}}"
status: planning
priority: medium
started: {{date:YYYY-MM-DD}}
target_completion: 
completed: 
tags: []
---

## Vision
<!-- What does success look like? -->


## Motivation
<!-- Why am I doing this? -->


## Goals
- [ ] Primary goal
- [ ] Secondary goal

## Scope
### In Scope
- 

### Out of Scope
- 

## Milestones
| Milestone | Target | Status |
|-----------|--------|--------|
|           |        |        |

## Tasks
### To Do
- [ ] 

### In Progress
- [ ] 

### Done
- [x] 

## Resources
- **Time**: 
- **Budget**: 
- **Tools**: 

## Progress Log
### {{date:YYYY-MM-DD}}
- 

## Lessons Learned


## Related
- [[Related Project]]
```

```markdown
<!-- templates/reflection.md -->
---
type: reflection
title: "{{title}}"
period: ""
tags: []
created: {{date:YYYY-MM-DD}}
---

## What Went Well
1. 
2. 
3. 

## What Could Be Better
1. 
2. 
3. 

## Key Learnings
- 

## Surprises
<!-- What unexpected things happened? -->


## Gratitude
<!-- What am I thankful for? -->
1. 
2. 
3. 

## Energy & Mood
<!-- How did I feel during this period? -->


## Priorities for Next Period
1. 
2. 
3. 

## Adjustments to Make
- [ ] 

## Questions to Explore
- 
```

**Deliverables:**
- [x] Paper template
- [x] Article template
- [x] Book template
- [x] Code repository template
- [x] Concept template
- [x] Idea template
- [x] Daily note template
- [x] Exercise template
- [x] Career template
- [x] Personal development template
- [x] Project template
- [x] Reflection template

**Estimated Time:** 3 hours

---

#### Task 1B.3: Tagging Taxonomy

**Purpose**: Define a controlled vocabulary that prevents tag chaos and enables meaningful queries.

**The Tag Sprawl Problem:**

Without a taxonomy, you'll inevitably end up with:
- `ml`, `ML`, `machine-learning`, `machine_learning`, `MachineLearning`
- `todo`, `TODO`, `to-do`, `action-item`, `task`
- Tags that mean nothing: `important`, `interesting`, `good`

**Taxonomy Design:**

The tagging system uses **hierarchical namespaced tags** with clear categories:

```text
TAG HIERARCHY (3 Levels)
========================

DOMAIN TAGS: domain/category/topic

TECHNICAL DOMAINS:
ml/                                     (domain)
|-- ml/architecture/                    (category)
|   |-- ml/architecture/transformers    (topic)
|   |-- ml/architecture/llms
|   +-- ml/architecture/diffusion
|-- ml/technique/
|   |-- ml/technique/fine-tuning
|   +-- ml/technique/rlhf
+-- ml/application/
    |-- ml/application/agents
    +-- ml/application/rag

systems/
|-- systems/distributed/consensus
+-- systems/storage/databases

CAREER & PERSONAL DOMAINS:
career/
|-- career/growth/goals
|-- career/skills/technical
+-- career/networking/mentorship

personal/
|-- personal/goals/life
|-- personal/growth/habits
+-- personal/wellbeing/physical

projects/
|-- projects/active/side-project
+-- projects/planning/ideas

non-tech/
|-- non-tech/finance/investing
|-- non-tech/philosophy/mental-models
+-- non-tech/hobbies/reading

STATUS TAGS (workflow state) - flat, no hierarchy
  status/actionable     Has tasks I need to do
  status/reference      Evergreen reference material
  status/archive        No longer actively used

QUALITY TAGS (content depth) - flat, no hierarchy
  quality/foundational  Core concepts, must know
  quality/deep-dive     Comprehensive treatment
  quality/overview      Surface level introduction
```

QUERY EXAMPLES:
- All ML notes:           startswith(tag, "ml/")
- All ML architectures:   startswith(tag, "ml/architecture/")
- Specific topic:         contains(tags, "ml/architecture/transformers")

NOTE: Source tags (source/paper, source/article) are NOT used.
The folder structure (sources/papers/, sources/articles/) already
encodes this information. Tags should add NEW information, not
duplicate what the file path already tells you.
```

**Tag Rules:**

| Rule | Example | Why |
|------|---------|-----|
| **1-3 domain tags per note** | `ml/transformers`, `ml/nlp` | Too many = meaningless |
| **Exactly 1 status tag** | `status/actionable` | Every note has a state |
| **Use most specific tag** | `ml/transformers` not just `ml` | Enables precise queries |
| **No source tags** | Folder path = source type | Avoid redundant information |

Create the controlled vocabulary for tags:

```markdown
<!-- meta/tag-taxonomy.md - AUTO-GENERATED from config/tag-taxonomy.yaml -->
---
type: meta
title: "Tag Taxonomy"
created: {{date:YYYY-MM-DD}}
---

# Tag Taxonomy

This document defines the controlled vocabulary for tags in the Second Brain vault.

## Usage Rules

1. **1-3 domain tags** per note (use most specific that applies)
2. **1 status tag** (required for all notes)
3. **1 quality tag** (recommended)
4. **NO source tags** — folder path already indicates source type
5. Prefer existing tags over creating new ones
6. Review suggested new tags monthly

---

## Domain Tags (Hierarchical)

> **Tag Structure**: `domain/category/topic`
> - Query all ML: `startswith(tag, "ml/")`
> - Query category: `startswith(tag, "ml/architecture/")`
> - Query specific: `contains(tags, "ml/architecture/transformers")`

### Machine Learning

#### ml/architecture/ — Model Architectures
- `ml/architecture/transformers` — Transformer architectures, attention mechanisms
- `ml/architecture/llms` — Large language models (GPT, Claude, Llama)
- `ml/architecture/diffusion` — Diffusion models, image/video generation
- `ml/architecture/rnns` — Recurrent architectures (LSTM, GRU)
- `ml/architecture/cnns` — Convolutional networks
- `ml/architecture/gnns` — Graph neural networks
- `ml/architecture/ssms` — State space models (Mamba, S4)
- `ml/architecture/moe` — Mixture of experts, sparse models

#### ml/modality/ — Input/Output Modalities
- `ml/modality/nlp` — Natural language processing
- `ml/modality/vision` — Computer vision, image understanding
- `ml/modality/multimodal` — Vision-language, audio-visual
- `ml/modality/speech` — Speech recognition, TTS
- `ml/modality/audio` — Audio processing, music
- `ml/modality/video` — Video understanding, generation
- `ml/modality/3d` — 3D vision, point clouds, NeRF
- `ml/modality/robotics` — Robot learning, embodied AI

#### ml/technique/ — Methods & Techniques
- `ml/technique/attention` — Attention mechanisms, efficient attention
- `ml/technique/embeddings` — Vector representations, similarity
- `ml/technique/fine-tuning` — Adaptation, transfer learning, LoRA, PEFT
- `ml/technique/rlhf` — Reinforcement learning from human feedback
- `ml/technique/distillation` — Knowledge distillation, compression
- `ml/technique/quantization` — Model quantization, low-bit inference
- `ml/technique/pruning` — Network pruning, sparsity
- `ml/technique/pretraining` — Self-supervised learning, foundation models

#### ml/training/ — Training & Optimization
- `ml/training/optimization` — Optimizers, loss functions, regularization
- `ml/training/scaling` — Scaling laws, compute-optimal training
- `ml/training/distributed` — Distributed training, parallelism
- `ml/training/data` — Datasets, data curation, synthetic data
- `ml/training/augmentation` — Data augmentation techniques
- `ml/training/curriculum` — Curriculum learning, data ordering

#### ml/inference/ — Inference & Deployment
- `ml/inference/efficiency` — Efficient inference, batching, caching
- `ml/inference/serving` — Model serving, APIs, latency
- `ml/inference/mlops` — ML operations, experiment tracking
- `ml/inference/edge` — Edge deployment, mobile ML

#### ml/application/ — Applications
- `ml/application/agents` — AI agents, tool use, planning
- `ml/application/rag` — Retrieval-augmented generation
- `ml/application/code` — Code generation, program synthesis
- `ml/application/reasoning` — Chain-of-thought, math reasoning
- `ml/application/generation` — Text/image generation
- `ml/application/search` — Semantic search, reranking
- `ml/application/recommendation` — Recommender systems

#### ml/safety/ — Evaluation & Safety
- `ml/safety/evaluation` — Benchmarks, metrics, leaderboards
- `ml/safety/interpretability` — Explainability, mechanistic interp
- `ml/safety/alignment` — AI alignment, RLHF safety
- `ml/safety/robustness` — Adversarial robustness, OOD detection
- `ml/safety/fairness` — Bias mitigation, fairness

#### ml/theory/ — Theory & Foundations
- `ml/theory/learning` — Learning theory, generalization
- `ml/theory/information` — Information-theoretic ML
- `ml/theory/bayesian` — Bayesian methods, uncertainty
- `ml/theory/optimization` — Optimization theory, convergence

### Systems

#### systems/distributed/ — Distributed Systems
- `systems/distributed/consensus` — Consensus algorithms, Raft, Paxos
- `systems/distributed/replication` — Data replication, consistency
- `systems/distributed/sharding` — Partitioning, sharding strategies

#### systems/storage/ — Storage & Databases
- `systems/storage/databases` — Database design, SQL/NoSQL
- `systems/storage/caching` — Caching strategies, Redis
- `systems/storage/filesystems` — File systems, object storage

#### systems/infrastructure/ — Infrastructure
- `systems/infrastructure/networking` — Network protocols, TCP/IP
- `systems/infrastructure/cloud` — Cloud platforms, AWS/GCP/Azure
- `systems/infrastructure/containers` — Docker, Kubernetes

#### systems/reliability/ — Reliability & Performance
- `systems/reliability/performance` — Optimization, profiling
- `systems/reliability/observability` — Monitoring, logging, tracing
- `systems/reliability/security` — Security, cryptography

### Engineering

#### engineering/design/ — Software Design
- `engineering/design/architecture` — System design, patterns
- `engineering/design/api` — API design, REST, GraphQL
- `engineering/design/data-modeling` — Data modeling, schemas

#### engineering/practices/ — Development Practices
- `engineering/practices/testing` — Testing strategies, TDD
- `engineering/practices/devops` — CI/CD, infrastructure as code
- `engineering/practices/code-review` — Code review, collaboration

#### engineering/languages/ — Languages & Frameworks
- `engineering/languages/python` — Python ecosystem
- `engineering/languages/typescript` — TypeScript/JavaScript
- `engineering/languages/rust` — Rust, systems programming

### Leadership

#### leadership/management/ — Team Management
- `leadership/management/teams` — Team dynamics, structure
- `leadership/management/hiring` — Recruitment, interviewing
- `leadership/management/feedback` — Feedback, performance

#### leadership/skills/ — Leadership Skills
- `leadership/skills/communication` — Communication, presenting
- `leadership/skills/strategy` — Strategic thinking, planning
- `leadership/skills/decision-making` — Decision frameworks

### Productivity

#### productivity/learning/ — Learning & Growth
- `productivity/learning/techniques` — Learning methods, retention
- `productivity/learning/reading` — Reading strategies
- `productivity/learning/writing` — Writing skills

#### productivity/systems/ — Personal Systems
- `productivity/systems/habits` — Habit formation
- `productivity/systems/time` — Time management
- `productivity/systems/tools` — Productivity tools

### Career

#### career/growth/ — Career Growth
- `career/growth/goals` — Career goals, planning, vision
- `career/growth/strategy` — Career strategy, positioning
- `career/growth/transitions` — Role changes, pivots, promotions

#### career/skills/ — Professional Skills
- `career/skills/technical` — Technical skill development
- `career/skills/soft` — Soft skills, interpersonal skills
- `career/skills/domain` — Domain expertise, industry knowledge

#### career/networking/ — Professional Networking
- `career/networking/relationships` — Professional relationships
- `career/networking/mentorship` — Mentoring, being mentored
- `career/networking/community` — Communities, conferences, events

#### career/job-search/ — Job Search & Interviews
- `career/job-search/interviews` — Interview preparation, experiences
- `career/job-search/negotiation` — Salary, offer negotiation
- `career/job-search/applications` — Resume, applications, portfolio

### Personal Development

#### personal/goals/ — Goals & Planning
- `personal/goals/life` — Life goals, vision, values
- `personal/goals/annual` — Annual goals, yearly planning
- `personal/goals/quarterly` — Quarterly objectives, OKRs

#### personal/growth/ — Personal Growth
- `personal/growth/mindset` — Mindset, mental models, beliefs
- `personal/growth/habits` — Habit formation, routines, systems
- `personal/growth/reflection` — Self-reflection, journaling
- `personal/growth/creativity` — Creative pursuits, artistic expression

#### personal/wellbeing/ — Health & Wellbeing
- `personal/wellbeing/physical` — Physical health, fitness, exercise
- `personal/wellbeing/mental` — Mental health, mindfulness, meditation
- `personal/wellbeing/sleep` — Sleep, rest, recovery
- `personal/wellbeing/nutrition` — Nutrition, diet, eating habits

#### personal/relationships/ — Relationships
- `personal/relationships/family` — Family relationships
- `personal/relationships/friends` — Friendships, social life
- `personal/relationships/communication` — Communication skills

### Projects

#### projects/active/ — Active Projects
- `projects/active/side-project` — Side projects, personal ventures
- `projects/active/learning` — Learning projects, courses
- `projects/active/creative` — Creative projects, art, writing

#### projects/planning/ — Project Planning
- `projects/planning/ideas` — Project ideas, brainstorms
- `projects/planning/roadmap` — Project roadmaps, milestones
- `projects/planning/resources` — Resources, tools, requirements

### Non-Technical

#### non-tech/finance/ — Personal Finance
- `non-tech/finance/investing` — Investing, portfolio management
- `non-tech/finance/budgeting` — Budgeting, saving, spending
- `non-tech/finance/planning` — Financial planning, retirement

#### non-tech/philosophy/ — Philosophy & Thinking
- `non-tech/philosophy/ethics` — Ethics, moral philosophy
- `non-tech/philosophy/wisdom` — Wisdom traditions, stoicism
- `non-tech/philosophy/mental-models` — Mental models, decision frameworks

#### non-tech/hobbies/ — Hobbies & Interests
- `non-tech/hobbies/reading` — Non-technical reading, fiction
- `non-tech/hobbies/sports` — Sports, outdoor activities
- `non-tech/hobbies/arts` — Arts, music, entertainment
- `non-tech/hobbies/travel` — Travel, exploration

#### non-tech/learning/ — General Learning
- `non-tech/learning/history` — History, historical events
- `non-tech/learning/science` — Non-CS science (physics, biology, etc.)
- `non-tech/learning/language` — Language learning

---

## Status Tags

| Tag | Description | When to Use |
|-----|-------------|-------------|
| `status/actionable` | Has pending tasks | Notes with uncompleted todos |
| `status/reference` | Useful for lookup | Evergreen reference material |
| `status/archive` | Historical only | Old, rarely accessed content |
| `status/review` | Needs review | Content that needs updating |
| `status/processing` | Being processed | Currently being ingested/summarized |

---

## Quality Tags

| Tag | Description | When to Use |
|-----|-------------|-------------|
| `quality/foundational` | Must-know content | Core concepts, essential knowledge |
| `quality/deep-dive` | Comprehensive | Detailed treatments of topics |
| `quality/overview` | Surface-level | Introductory material |
| `quality/practical` | Hands-on | Applied, actionable content |
| `quality/theoretical` | Academic | Research-focused content |

---

## Source Tags — NOT USED

> **Why no source tags?** The folder structure already encodes source type:
> - `sources/papers/` = it's a paper
> - `sources/articles/` = it's an article
> - `sources/books/` = it's a book
>
> Tags should add **new information**, not duplicate what the file path tells you.
> Use domain tags (`ml/transformers`) and status tags (`status/actionable`) instead.

---

## Adding New Tags

Before adding a new tag:

1. Check if an existing tag covers the concept
2. Consider if it fits the hierarchical structure
3. Ensure it will be used for 3+ notes
4. Add to this taxonomy document

### Proposed Tags Queue
<!-- Add proposed new tags here for monthly review -->

- 

---

## Tag Maintenance

### Monthly Review Checklist
- [ ] Review unused tags (< 3 uses)
- [ ] Merge similar tags
- [ ] Update taxonomy document
- [ ] Check for inconsistent usage
```

**Deliverables:**
- [x] Tag taxonomy document
- [x] Domain tag hierarchy
- [x] Status tag definitions
- [x] Quality tag definitions
- [x] Source tag mappings
- [x] Tag usage guidelines

**Estimated Time:** 2 hours

---

#### Task 1B.4: Essential Plugin Configuration

**Purpose**: Install and configure Obsidian plugins that transform it from a note editor into a queryable knowledge base.

**Why These Plugins?**

| Plugin | What It Does | Why It's Essential |
|--------|--------------|-------------------|
| **Dataview** | Query notes like a database using SQL-like syntax | Powers the dashboard, "show all unread papers", "find notes by tag" |
| **Templater** | Advanced templates with dynamic content, folder-specific defaults | Auto-applies paper.md when creating note in sources/papers/ |
| **Tasks** | Track todos across the entire vault, query incomplete tasks | "Show all tasks tagged #research from last week" |
| **Tag Wrangler** | Bulk rename, merge, delete tags | Fix taxonomy mistakes, merge duplicates |
| **Linter** | Enforce consistent Markdown formatting | Clean YAML frontmatter, consistent heading styles |
| **Calendar** | Visual calendar for daily notes | Navigate to any day's note with one click |

**Plugin Interaction Map:**

```text
PLUGIN INTERACTION FLOW
=======================

1. CREATE NOTE
   - User creates note in sources/papers/
   - Templater detects folder -> applies paper.md template
   - Template inserts {{date:YYYY-MM-DD}} -> "2024-12-21"

2. ADD CONTENT
   - User writes "- [ ] Read related paper #research"
   - Tasks plugin detects todo syntax
   - Task appears in global task queries

3. SAVE NOTE
   - Linter auto-formats on save
   - Sorts YAML frontmatter alphabetically
   - Fixes heading inconsistencies

4. QUERY DATA
   - Dashboard uses Dataview to query vault
   - "TABLE title FROM sources/papers WHERE status = 'unread'"
   - Results update automatically as notes change

5. MANAGE TAGS
   - Realize "ML" and "ml" both exist
   - Tag Wrangler: right-click -> merge "ML" into "ml"
   - All notes updated automatically
```

Document and configure essential Obsidian plugins:

```markdown
<!-- meta/plugin-setup.md -->
---
type: meta
title: "Plugin Setup Guide"
created: {{date:YYYY-MM-DD}}
---

# Obsidian Plugin Setup

## Essential Plugins (Install First)

### 1. Dataview
**Purpose**: Query notes as a database

**Installation**: Community Plugins > Browse > "Dataview" > Install > Enable

**Settings**:
- Enable JavaScript Queries: ON
- Enable Inline Queries: ON

### 2. Templater
**Purpose**: Advanced templates with dynamic content

**Installation**: Community Plugins > Browse > "Templater" > Install > Enable

**Settings**:
- Template folder location: `templates`
- Enable Folder Templates: ON
- Add folder templates:
  - `sources/papers` -> `templates/paper.md`
  - `sources/articles` -> `templates/article.md`
  - `sources/books` -> `templates/book.md`
  - `sources/code` -> `templates/code.md`
  - `sources/ideas` -> `templates/idea.md`
  - `sources/career` -> `templates/career.md`
  - `sources/personal` -> `templates/personal.md`
  - `sources/personal/reflections` -> `templates/reflection.md`
  - `sources/projects` -> `templates/project.md`
  - `concepts` -> `templates/concept.md`
  - `daily` -> `templates/daily.md`

### 3. Tasks
**Purpose**: Track todos across the vault

**Installation**: Community Plugins > Browse > "Tasks" > Install > Enable

**Settings**:
- Global task filter: Leave empty (search all)
- Set done date on completion: ON

### 4. Tag Wrangler
**Purpose**: Bulk tag management

**Installation**: Community Plugins > Browse > "Tag Wrangler" > Install > Enable

### 5. Linter
**Purpose**: Enforce formatting consistency

**Installation**: Community Plugins > Browse > "Linter" > Install > Enable

**Settings**:
- YAML Title: ON
- YAML Sort: ON
- Heading blank lines: ON

---

## Recommended Plugins

### 6. Calendar
**Purpose**: Visual daily notes navigation

### 7. Periodic Notes
**Purpose**: Weekly/monthly review notes

### 8. Smart Connections
**Purpose**: AI-powered related notes

### 9. Waypoint
**Purpose**: Auto-generate folder index notes

### 10. Kanban
**Purpose**: Visual project boards

---

## Dataview Query Examples

### Dashboard Queries

Save these in `meta/dashboard.md`:

#### Recently Processed Notes
```dataview
TABLE title as "Title", tags as "Tags", processed as "Processed"
FROM "sources"
WHERE processed
SORT processed DESC
LIMIT 10
```

#### Unread Papers
```dataview
LIST
FROM "sources/papers"
WHERE status = "unread"
SORT created DESC
```

#### All Open Tasks
```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
GROUP BY file.link
```

#### Notes by Topic
```dataview
TABLE length(rows) as "Count"
FROM "sources"
FLATTEN tags as tag
WHERE startswith(tag, "ml/") OR startswith(tag, "systems/")
GROUP BY tag
SORT length(rows) DESC
```

#### Notes Needing Review
```dataview
LIST
FROM "sources"
WHERE contains(tags, "status/review")
SORT file.mtime ASC
```

---

## Hotkeys to Configure

| Action | Suggested Hotkey |
|--------|------------------|
| Open daily note | Cmd/Ctrl + D |
| New note from template | Cmd/Ctrl + Shift + N |
| Search tags | Cmd/Ctrl + Shift + T |
| Toggle task complete | Cmd/Ctrl + Enter |
| Insert template | Alt + T |

**Deliverables:**
- [x] Plugin setup documentation
- [x] Dataview query examples
- [x] Templater configuration
- [x] Hotkey recommendations

**Estimated Time:** 2 hours

---

#### Task 1B.5: System Dashboard & Meta Notes

**Purpose**: Create the "home base" notes that make the vault navigable and self-documenting.

**The Dashboard Pattern:**

The dashboard (`meta/dashboard.md`) is the **entry point** to your Second Brain:

```text
                    +------------------+
                    |    DASHBOARD     |
                    |   (Home Base)    |
                    +--------+---------+
                             |
       +---------------------+---------------------+
       |                     |                     |
       v                     v                     v
+-------------+       +-------------+       +-------------+
|   Inbox     |       |  Learning   |       |  Recently   |
| (5 items)   |       |   Queue     |       |  Modified   |
+-------------+       +-------------+       +-------------+

Dashboard sections (powered by Dataview queries):
- Quick Stats: content counts by type
- Inbox: unprocessed content
- Reading: currently reading
- Tasks: open todos across vault

       +---------------------+---------------------+
       |                     |                     |
       v                     v                     v
+-------------+       +-------------+       +-------------+
|    Tag      |       | Workflows   |       |   Review    |
|  Taxonomy   |       |   Guide     |       |   Queue     |
+-------------+       +-------------+       +-------------+
```

**Meta Notes Explained:**

| Note | Purpose | When You'd Use It |
|------|---------|-------------------|
| `dashboard.md` | Central hub with live queries | Daily: check inbox, see what's due |
| `tag-taxonomy.md` | **Auto-generated** from `config/tag-taxonomy.yaml` | Browsing available tags (do not edit directly) |
| `workflows.md` | How-to documentation | Onboarding, remembering processes |
| `plugin-setup.md` | Plugin configuration | Troubleshooting, setup on new machine |
| `reviews/_queue.md` | Spaced repetition queue | Practice sessions |

Create the main dashboard and system documentation:

```markdown
<!-- meta/dashboard.md -->
---
type: meta
title: "Second Brain Dashboard"
created: {{date:YYYY-MM-DD}}
---

# 🧠 Second Brain Dashboard

## 📊 Quick Stats

```dataview
TABLE WITHOUT ID
  length(filter(rows, (r) => r.type = "paper")) as "📄 Papers",
  length(filter(rows, (r) => r.type = "article")) as "📰 Articles",
  length(filter(rows, (r) => r.type = "book")) as "📚 Books",
  length(filter(rows, (r) => r.type = "code")) as "💻 Code",
  length(filter(rows, (r) => r.type = "idea")) as "💡 Ideas"
FROM "sources"
FLATTEN type
GROUP BY true
```

---

## 📥 Inbox (Needs Processing)

```dataview
TABLE title as "Title", source_type as "Type", created as "Captured"
FROM "sources"
WHERE status = "processing" OR !processed
SORT created DESC
LIMIT 10
```

---

## 📚 Currently Reading

```dataview
LIST
FROM "sources/books"
WHERE status = "reading"
SORT file.mtime DESC
```

---

## ✅ Open Tasks

```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
LIMIT 15
```

---

## 🏷️ Top Topics

```dataview
TABLE length(rows) as "Notes"
FROM "sources"
FLATTEN tags
WHERE !startswith(tags, "status/") AND !startswith(tags, "quality/") AND !startswith(tags, "source/")
GROUP BY tags
SORT length(rows) DESC
LIMIT 10
```

---

## 🔗 Quick Links

- [[meta/tag-taxonomy|Tag Taxonomy]]
- [[meta/plugin-setup|Plugin Setup]]
- [[meta/workflows|Workflows]]
- [[reviews/_queue|Review Queue]]
- [[daily/{{date:YYYY-MM-DD}}|Today's Note]]

---

## 📅 Recent Activity

```dataview
TABLE file.mtime as "Modified", type as "Type"
FROM "sources" OR "concepts"
SORT file.mtime DESC
LIMIT 10
```
```

```markdown
<!-- meta/workflows.md -->
---
type: meta
title: "Workflows"
created: {{date:YYYY-MM-DD}}
---

# Workflows

## Daily Workflow

### Morning (5-10 min)
1. Open [[daily/{{date:YYYY-MM-DD}}|today's daily note]]
2. Review inbox items
3. Check [[reviews/_queue|review queue]]
4. Plan learning focus for the day

### Throughout Day
1. Capture ideas immediately (quick capture)
2. Tag with `status/actionable` if needs follow-up
3. Link to related notes when relevant

### Evening (5-10 min)
1. Process inbox items
2. Update task status
3. Journal reflection

---

## Content Processing Workflow

### 1. Capture
- Quick capture via API/CLI
- Auto-placed in `sources/ideas` or appropriate folder

### 2. Process
- LLM generates summary
- Extracts key concepts
- Suggests tags and connections

### 3. Review
- Verify accuracy of summary
- Add personal notes
- Create manual connections
- Update status tag

### 4. Learn
- Generate mastery questions
- Schedule for spaced repetition
- Practice via exercises

---

## Paper Processing

1. **Upload PDF** -> `/api/ingest/pdf`
2. **Extract text & highlights** -> Automated
3. **OCR handwritten notes** -> Vision LLM
4. **Generate summary** -> LLM
5. **Review & enhance** -> Manual
6. **Create concept notes** -> For key ideas
7. **Add to review queue** -> Mastery questions

---

## Weekly Review

Every Sunday:

1. [ ] Process remaining inbox items
2. [ ] Review notes marked `status/review`
3. [ ] Check for orphan notes (no links)
4. [ ] Update tag taxonomy if needed
5. [ ] Archive completed items
6. [ ] Plan next week's learning focus
```

```markdown
<!-- reviews/_queue.md -->
---
type: meta
title: "Review Queue"
created: {{date:YYYY-MM-DD}}
---

# 📋 Review Queue

## Due Today

```dataview
LIST
FROM "sources" OR "concepts"
WHERE due_date = date(today)
SORT file.mtime ASC
```

## Overdue

```dataview
LIST
FROM "sources" OR "concepts"
WHERE due_date < date(today)
SORT due_date ASC
```

## Coming Up (Next 7 Days)

```dataview
TABLE due_date as "Due", difficulty as "Difficulty"
FROM "sources" OR "concepts"
WHERE due_date > date(today) AND due_date <= date(today) + dur(7 days)
SORT due_date ASC
```

---

## Stats

- **Total cards**: `$= dv.pages('"sources" OR "concepts"').where(p => p.type == "concept").length`
- **Due today**: Count from query above
- **Streak**: Track manually or via backend

---

## Quick Actions

- [[Start Practice Session]] (link to web app)
- [[Generate New Cards]] (link to web app)

**Deliverables:**
- [x] Main dashboard with Dataview queries
- [x] Workflows documentation
- [x] Review queue note
- [x] Folder index templates

**Estimated Time:** 3 hours

---

### Phase 1C: Integration & Verification (Days 8-10)

#### Task 1C.1: Backend Health Checks

**Purpose**: Provide endpoints for monitoring service health and diagnosing connection issues.

**Why Health Checks Matter:**

| Without Health Checks | With Health Checks |
|----------------------|-------------------|
| "Is it down?" SSH in, check logs | Hit `/api/health` -> instant status |
| Kubernetes kills healthy pods | Readiness probe prevents premature traffic |
| Silent database disconnections | Detailed check shows exactly what's broken |

**Health Check Levels:**

```text
HEALTH CHECK HIERARCHY
======================

GET /api/health                    (Basic - for load balancers)
  - Returns: { "status": "healthy" }
  - Fast: no database calls
  - Use: load balancer health checks (every 5 seconds)

GET /api/health/detailed           (Comprehensive - for debugging)
  - Checks: PostgreSQL, Redis, Neo4j, Vault
  - Returns status of each service
  - Use: debugging, monitoring dashboards

GET /api/health/ready              (Kubernetes readiness probe)
  - Returns 200 if ready to serve traffic
  - Returns 503 if dependencies not ready
  - Use: Kubernetes won't send traffic until ready
```

Add health check endpoints to verify infrastructure:

```python
# backend/app/routers/health.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.base import get_db
from app.db.redis import get_redis
from app.config import settings
from pathlib import Path
import redis.asyncio as redis

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "second-brain"}


@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
):
    """Detailed health check for all services."""
    health = {
        "status": "healthy",
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["postgres"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
        health["services"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Neo4j
    try:
        from app.db.neo4j import get_neo4j_driver
        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run("RETURN 1")
        health["services"]["neo4j"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["neo4j"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Obsidian vault
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    if vault_path.exists() and vault_path.is_dir():
        health["services"]["vault"] = {
            "status": "healthy",
            "path": str(vault_path)
        }
    else:
        health["services"]["vault"] = {
            "status": "unhealthy",
            "error": f"Vault not found at {vault_path}"
        }
        health["status"] = "degraded"
    
    return health


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        return {"ready": True}
    except:
        return {"ready": False}, 503
```

**Deliverables:**
- [x] Basic health endpoint
- [x] Detailed health with service checks
- [x] Readiness probe endpoint

**Estimated Time:** 2 hours

---

#### Task 1C.2: Database Verification

**Purpose**: Verify the database is correctly set up and migrations have run.

After running Alembic migrations, verify the database:

```bash
# Check tables exist
docker-compose exec postgres psql -U secondbrain -d secondbrain -c "\dt"

# Run pytest database tests (see Section 4 for details)
cd backend
pytest tests/integration/test_database.py -v
```

> **📋 See Section 4 (Testing Strategy)** for comprehensive database test implementation, including CRUD operations, relationship tests, and transaction handling.

**Deliverables:**
- [x] Database tables verified
- [x] Integration tests pass (`pytest tests/integration/test_database.py`)

**Estimated Time:** 30 minutes

---

#### Task 1C.3: Vault Validation

**Purpose**: Verify the Obsidian vault is correctly structured before ingestion pipelines start writing to it.

**What Gets Validated:**

| Check | Why It Matters |
|-------|---------------|
| **Folder structure** | Ingestion pipelines expect `sources/papers/` to exist |
| **Templates present** | Templater fails silently if template is missing |
| **Frontmatter valid** | Dataview queries break on malformed YAML |
| **Required meta files** | Dashboard won't work without tag-taxonomy.md |
| **Obsidian config** | Plugin settings need to be present |

Create script to validate vault structure:

```python
# scripts/setup/validate_vault.py

from pathlib import Path
import frontmatter
import yaml
import sys

def validate_vault(vault_path: Path) -> bool:
    """
    Validate Obsidian vault structure and configuration.
    
    EXTENSIBILITY: This function dynamically reads expected folders and templates
    from config/default.yaml. When you add a new content type to the config,
    validation will automatically check for it.
    """
    
    errors = []
    warnings = []
    
    print(f"🔍 Validating vault at: {vault_path}\n")
    
    # Load content types from configuration
    with open("config/default.yaml") as f:
        config = yaml.safe_load(f)
    
    content_types = config.get("content_types", {})
    
    # Build list of required folders from content types
    required_folders = [
        # System folders (always required)
        "topics",
        "concepts",
        "exercises",
        "reviews",
        "daily",
        "templates",
        "meta",
    ]
    
    # Add folders from content type registry
    for type_key, type_config in content_types.items():
        folder = type_config.get("folder")
        if folder:
            required_folders.append(folder)
    
    print("📁 Checking folder structure:")
    for folder in required_folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            print(f"  ✅ {folder}")
        else:
            errors.append(f"Missing folder: {folder}")
            print(f"  ❌ {folder} (missing)")
    
    print()
    
    # Build list of required templates from content types
    required_templates = set()
    for type_key, type_config in content_types.items():
        template = type_config.get("template")
        if template:
            required_templates.add(template)
    
    print("📄 Checking templates:")
    for template in required_templates:
        template_path = vault_path / template
        if template_path.exists():
            # Validate frontmatter
            try:
                fm = frontmatter.load(template_path)
                if "type" in fm.metadata:
                    print(f"  ✅ {template}")
                else:
                    warnings.append(f"Template missing 'type' field: {template}")
                    print(f"  ⚠️  {template} (missing type field)")
            except Exception as e:
                errors.append(f"Invalid template: {template} - {e}")
                print(f"  ❌ {template} (invalid)")
        else:
            errors.append(f"Missing template: {template}")
            print(f"  ❌ {template} (missing)")
    
    print()
    
    # Check meta files
    required_meta = [
        "meta/tag-taxonomy.md",
        "meta/dashboard.md",
    ]
    
    print("📋 Checking meta files:")
    for meta_file in required_meta:
        meta_path = vault_path / meta_file
        if meta_path.exists():
            print(f"  ✅ {meta_file}")
        else:
            warnings.append(f"Missing meta file: {meta_file}")
            print(f"  ⚠️  {meta_file} (missing)")
    
    print()
    
    # Check Obsidian config
    obsidian_config = vault_path / ".obsidian"
    if obsidian_config.exists():
        print("⚙️  Obsidian configuration: ✅")
    else:
        warnings.append("Obsidian configuration folder not found")
        print("⚙️  Obsidian configuration: ⚠️  (not configured)")
    
    print()
    
    # Summary
    print("=" * 50)
    if errors:
        print(f"❌ Validation FAILED with {len(errors)} error(s):")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Validation PASSED")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"   - {warning}")
    
    return len(errors) == 0


if __name__ == "__main__":
    import os
    vault_path = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "./vault"))
    success = validate_vault(vault_path)
    sys.exit(0 if success else 1)
```

**Deliverables:**
- [x] Vault validation script
- [x] Folder structure checks
- [x] Template validation
- [x] Meta file checks

**Estimated Time:** 1 hour

---

#### Task 1C.4: Run Test Suite

**Purpose**: Execute the automated test suite to verify all Phase 1 components work together.

The complete test suite is documented in **Section 4 (Testing Strategy)**. This task involves running those tests.

**Quick Start:**

```bash
# Start services (required for integration tests)
docker-compose up -d postgres redis neo4j

# Run all tests
cd backend
pytest tests/ -v

# Or run unit tests only (no services needed)
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
```

**Test Coverage for Phase 1:**

| Test File | What It Tests |
|-----------|--------------|
| `tests/unit/test_config.py` | Settings, environment variables, YAML config |
| `tests/unit/test_content_types.py` | Content type registry |
| `tests/unit/test_redis.py` | Cache, session store, task queue |
| `tests/integration/test_database.py` | PostgreSQL models, CRUD, relationships |
| `tests/integration/test_health.py` | Health check endpoints |
| `tests/integration/test_vault.py` | Vault structure validation |

> **📋 See Section 4 (Testing Strategy)** for complete test implementation details, fixtures, and test-writing guidelines.

**Deliverables:**
- [x] All unit tests pass (`pytest tests/unit/`)
- [x] All integration tests pass (`pytest tests/integration/`)
- [x] Coverage meets targets (see Section 4.7)

**Estimated Time:** 1 hour (to run and verify)

---

## 4. Testing Strategy

This section provides a comprehensive testing strategy for Phase 1, covering unit tests, integration tests, fixtures, and best practices.

### 4.1 Test Philosophy

| Test Type | Purpose | Dependencies | Speed |
|-----------|---------|--------------|-------|
| **Unit Tests** | Test individual functions/classes in isolation | None (all mocked) | Fast (< 1s each) |
| **Integration Tests** | Test component interactions with real services | Docker services running | Medium (1-5s each) |

**Key Principles:**
1. **Fast feedback**: Unit tests run without Docker, enabling quick iteration
2. **Realistic validation**: Integration tests verify actual service interactions
3. **Isolation**: Each test is independent—no shared state between tests
4. **Maintainability**: Clear test organization and naming conventions

### 4.2 Test Directory Structure

```text
backend/tests/
├── __init__.py                    # Package marker with test documentation
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
│
├── unit/                          # Unit tests (no external dependencies)
│   ├── __init__.py
│   ├── test_config.py             # Settings and YAML config loading
│   ├── test_content_types.py      # Content type registry
│   └── test_redis.py              # Redis utilities (cache, session, queue)
│
└── integration/                   # Integration tests (require services)
    ├── __init__.py
    ├── conftest.py                # Integration-specific fixtures
    ├── test_database.py           # PostgreSQL models and CRUD
    ├── test_health.py             # Health check endpoints
    └── test_vault.py              # Vault structure validation
```

### 4.3 Test Categories

#### 4.3.1 Unit Tests

**Configuration Tests (`test_config.py`)**
- Settings default values
- Environment variable overrides
- POSTGRES_URL property construction
- YAML configuration loading
- Content type structure validation

```python
# Example: Test POSTGRES_URL construction
def test_postgres_url_construction(self) -> None:
    """POSTGRES_URL property should build correct connection string."""
    settings = Settings(
        POSTGRES_HOST="testhost",
        POSTGRES_PORT=5433,
        POSTGRES_USER="testuser",
        POSTGRES_PASSWORD="testpass",
        POSTGRES_DB="testdb",
        ...
    )
    
    expected = "postgresql+asyncpg://testuser:testpass@testhost:5433/testdb"
    assert settings.POSTGRES_URL == expected
```

**Content Type Registry Tests (`test_content_types.py`)**
- All content types loaded
- User types vs system types filtering
- Folder path resolution
- Template path resolution
- Type validation

```python
# Example: Test user types exclude system types
def test_get_user_types_excludes_system_types(self, registry) -> None:
    """get_user_types should not include system types."""
    user_types = registry.get_user_types()
    
    # System types should be excluded
    assert "concept" not in user_types
    assert "daily" not in user_types
    
    # User types should be included
    assert "paper" in user_types
    assert "article" in user_types
```

**Redis Utilities Tests (`test_redis.py`)**
- Cache key generation
- Cache get/set/delete operations
- Session store lifecycle
- Task queue enqueue/dequeue
- TTL handling

```python
# Example: Test session store with mock Redis
@pytest.mark.asyncio
async def test_create_session(self, session_store, mock_redis) -> None:
    """create_session should store session data with TTL."""
    with patch("app.db.redis.get_redis", return_value=mock_redis):
        session_data = {"user_id": "123", "email": "test@example.com"}
        
        result = await session_store.create_session("session_id", session_data)
        
        assert result == "session_id"
        mock_redis.setex.assert_called_once()
```

#### 4.3.2 Integration Tests

**Database Tests (`test_database.py`)**
- PostgreSQL connection
- Table existence verification
- Content CRUD operations
- Annotation relationships
- Tag uniqueness constraints
- Practice session models
- Spaced repetition cards
- Transaction rollback behavior

```python
# Example: Test Content model creation
@pytest.mark.asyncio
async def test_create_content(self, clean_db: AsyncSession) -> None:
    """Should create a content record."""
    content = Content(
        content_type="paper",
        title="Test Paper: Neural Networks",
        source_url="https://example.com/paper.pdf",
        status=ContentStatus.PENDING,
    )
    
    clean_db.add(content)
    await clean_db.commit()
    await clean_db.refresh(content)
    
    assert content.id is not None
    assert content.title == "Test Paper: Neural Networks"
```

**Health Endpoint Tests (`test_health.py`)**
- Basic health check (200 response)
- Detailed health with dependencies
- Readiness probe
- Degraded status on failures
- Response time validation

```python
# Example: Test detailed health endpoint
def test_detailed_health_has_dependencies(self, test_client) -> None:
    """Detailed health should include dependency statuses."""
    response = test_client.get("/api/health/detailed")
    data = response.json()
    
    assert "dependencies" in data
    expected_deps = ["postgres", "redis", "neo4j", "obsidian_vault"]
    for dep in expected_deps:
        assert dep in data["dependencies"]
```

**Vault Validation Tests (`test_vault.py`)**
- Valid vault passes validation
- Missing folders fail validation
- Template frontmatter validation
- Obsidian configuration files
- Meta files existence

```python
# Example: Test vault validation
def test_valid_vault_passes_validation(
    self, temp_vault: Path, sample_yaml_config: dict
) -> None:
    """A complete vault should pass validation."""
    from validate_vault import validate_vault
    
    result = validate_vault(temp_vault, sample_yaml_config)
    
    assert result is True
```

### 4.4 Fixtures

#### Shared Fixtures (`conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `event_loop` | session | Async event loop for pytest-asyncio |
| `setup_test_environment` | session | Set test environment variables |
| `sample_yaml_config` | function | Sample YAML config for testing |
| `mock_redis` | function | Mocked Redis client |
| `mock_db_session` | function | Mocked database session |
| `temp_vault` | function | Complete temporary vault |
| `incomplete_vault` | function | Incomplete vault for failure tests |

```python
# Example: temp_vault fixture creates a complete test vault
@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault directory structure for testing."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    
    # Create system folders
    folders = [
        "topics", "concepts", "templates", "meta",
        "sources/papers", "sources/articles", ...
    ]
    for folder in folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)
    
    # Create .obsidian configuration
    # Create sample templates
    # Create meta files
    
    return vault_path
```

#### Integration Fixtures (`integration/conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `db_session` | function | Real database session (rolled back) |
| `clean_db` | function | Database session with cleaned tables |
| `redis_client` | function | Real Redis client with test prefix |
| `test_client` | function | FastAPI TestClient |

### 4.5 Test Commands

```bash
# ============================================
# Running Tests
# ============================================

# Run all tests
pytest tests/ -v

# Run only unit tests (fast, no services needed)
pytest tests/unit/ -v

# Run only integration tests (requires Docker services)
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_config.py -v

# Run specific test class
pytest tests/unit/test_config.py::TestSettings -v

# Run specific test method
pytest tests/unit/test_config.py::TestSettings::test_default_values -v

# Run tests matching a pattern
pytest tests/ -v -k "test_content"

# ============================================
# Coverage Reports
# ============================================

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Coverage with specific module
pytest tests/ --cov=app.config --cov-report=term-missing

# Generate XML coverage for CI
pytest tests/ --cov=app --cov-report=xml

# ============================================
# Debugging & Development
# ============================================

# Run with verbose output and print statements
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -v -x

# Run last failed tests
pytest tests/ --lf

# Run with pdb on failures
pytest tests/ --pdb

# Show local variables in tracebacks
pytest tests/ -l

# ============================================
# Markers
# ============================================

# Run only tests marked as 'database'
pytest tests/ -v -m database

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### 4.6 Test Configuration (`pytest.ini`)

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Markers for test categorization
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (requires running services)
    slow: Tests that take a long time to run
    database: Tests that require PostgreSQL
    redis: Tests that require Redis
    vault: Tests that require a vault directory

# Output configuration
addopts = 
    -v
    --strict-markers
    --tb=short
    -ra

# Warning filters
filterwarnings =
    ignore::DeprecationWarning
```

### 4.7 Test Coverage Goals

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `app/config.py` | 90% | High |
| `app/content_types.py` | 95% | High |
| `app/db/redis.py` | 85% | High |
| `app/db/models.py` | 80% | Medium |
| `app/routers/health.py` | 90% | High |

### 4.8 Running Integration Tests

Integration tests require a running PostgreSQL database with a dedicated test user and database. **Do not run integration tests against your production database!**

#### 4.8.1 Test Database Setup (One-Time)

The integration tests expect specific credentials defined in your `.env` file. Add these variables to your `.env`:

```bash
# Test Database Credentials (add to .env)
POSTGRES_TEST_USER=testuser
POSTGRES_TEST_PASSWORD="your-secure-test-password"
POSTGRES_TEST_DB=testdb
```

Then create the test user and database in PostgreSQL:

```bash
# Option 1: Using docker-compose exec (if PostgreSQL is running in Docker)
docker-compose up -d postgres

# Connect to PostgreSQL as the admin user
docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Inside psql, create the test user and database using your chosen password:
CREATE USER testuser WITH PASSWORD 'your-secure-test-password';
CREATE DATABASE testdb OWNER testuser;
GRANT ALL PRIVILEGES ON DATABASE testdb TO testuser;
\q

# Option 2: Using local psql (if PostgreSQL is running locally)
psql -U postgres -c "CREATE USER testuser WITH PASSWORD 'your-secure-test-password';"
psql -U postgres -c "CREATE DATABASE testdb OWNER testuser;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE testdb TO testuser;"
```

**Note:** The test fixtures in `conftest.py` read credentials from `POSTGRES_TEST_*` environment variables, falling back to defaults (`testuser`/`testpass`) for CI environments.

#### 4.8.2 Test Environment Variables

The test fixtures read credentials from environment variables (see `tests/conftest.py`). Add these to your `.env` file:

| Environment Variable | Default Value | Purpose |
|---------------------|---------------|---------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_TEST_USER` | `testuser` | Test database user |
| `POSTGRES_TEST_PASSWORD` | `testpass` | Test database password |
| `POSTGRES_TEST_DB` | `testdb` | Test database name |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis (database 1 for isolation) |

**Security Note:** Store your actual test credentials in `.env` (which is gitignored). The defaults are only used for CI environments where `.env` may not exist.

#### 4.8.3 Running Integration Tests

```bash
# 1. Start required services
docker-compose up -d postgres redis

# 2. Wait for services to be healthy
docker-compose ps  # Ensure postgres and redis show "healthy"

# 3. Create test database (first time only - see section 4.8.1)

# 4. Run integration tests
cd backend
pytest tests/integration/ -v

# 5. Or run all tests (unit + integration)
pytest tests/ -v

# 6. Stop services when done (optional)
docker-compose down
```

#### 4.8.4 Troubleshooting

**"Connection refused" errors:**
- Ensure PostgreSQL and Redis are running: `docker-compose ps`
- Check that ports 5432 (PostgreSQL) and 6379 (Redis) are not blocked

**"Role 'testuser' does not exist" errors:**
- Create the test user and database (see section 4.8.1)

**"Database 'testdb' does not exist" errors:**
- Create the test database (see section 4.8.1)

**"Permission denied" errors:**
- Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE testdb TO testuser;`

**Running tests against wrong database:**
- Tests use hardcoded `testuser/testpass/testdb` credentials
- This is intentional to prevent accidentally modifying production data
- Do NOT change conftest.py to use your production credentials

### 4.9 CI/CD Integration

For GitHub Actions or similar CI systems:

```yaml
# .github/workflows/test.yml (example)
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=app --cov-report=xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          # CI uses default test credentials (no .env file available)
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run integration tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          # Use POSTGRES_TEST_* variables (conftest.py reads these)
          POSTGRES_TEST_USER: testuser
          POSTGRES_TEST_PASSWORD: testpass
          POSTGRES_TEST_DB: testdb
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd backend
          pytest tests/integration/ -v
```

### 4.10 Writing New Tests

When adding new functionality, follow these guidelines:

1. **Create unit tests first**: They're faster to write and run
2. **Use descriptive names**: `test_cache_get_returns_none_for_missing_key`
3. **One assertion per test** (when practical)
4. **Use fixtures**: Don't repeat setup code
5. **Mock external dependencies**: Unit tests shouldn't hit real services
6. **Test edge cases**: Empty inputs, None values, error conditions

**Test Naming Convention:**
```
test_<method_name>_<scenario>_<expected_result>

Examples:
- test_get_folder_returns_correct_path
- test_get_folder_returns_none_for_unknown_type
- test_create_session_stores_data_with_ttl
```

---

## 5. Timeline Summary

| Day | Phase | Tasks | Deliverables |
|-----|-------|-------|--------------|
| 1-3 | 1A | Infrastructure | Docker Compose, PostgreSQL, Redis, Alembic |
| 4-7 | 1B | Knowledge Hub | Vault structure, templates, tags, plugins |
| 8-10 | 1C | Integration | Health checks, validation, testing |

**Total Estimated Time:** ~35-40 hours

---

## 6. Success Criteria

### Infrastructure
- [x] All Docker services start successfully
- [x] PostgreSQL accepts connections and migrations run
- [x] Redis responds to ping
- [x] Health endpoints return healthy status
- [x] Backend can read/write to all databases

### Knowledge Hub
- [x] Vault folder structure matches design
- [x] All templates have valid frontmatter
- [x] Tag taxonomy is documented
- [x] Dashboard displays correctly with Dataview
- [x] Daily note template works with Templater

### Integration
- [x] All integration tests pass
- [x] Vault validation script succeeds
- [x] Configuration loads from environment

---

## 7. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Database connection issues | High | Medium | Health checks, connection pooling |
| Plugin compatibility | Medium | Low | Document tested versions |
| Vault sync conflicts | Medium | Medium | Clear ownership (backend writes, user reads) |
| Configuration complexity | Low | Medium | Centralized config, documentation |

---

## 8. Dependencies

### Enables After Phase 1

```text
PHASE DEPENDENCY GRAPH
======================

PHASE 1: FOUNDATION (this phase)
|
|-- PostgreSQL --------+----------+-----------+
|                      |          |           |
|                      v          v           v
|   +--------------------------------------------------+
|   |  PHASE 2: INGESTION                              |
|   |  - Store content metadata in PostgreSQL          |
|   |  - Write notes to Obsidian vault                 |
|   |  - Use templates from config/default.yaml        |
|   +------------------------+-------------------------+
|                            |
|-- Redis -------------------)----------+
|                            |          |
|                            v          v
|   +--------------------------------------------------+
|   |  PHASE 3: LLM PROCESSING                         |
|   |  - Cache embeddings in Redis                     |
|   |  - Store processing status in PostgreSQL         |
|   |  - Output to Obsidian using templates            |
|   +------------------------+-------------------------+
|                            |
|-- Tag Taxonomy ------------)----------+
|                            |          |
|                            v          v
|   +--------------------------------------------------+
|   |  PHASE 4+: FRONTEND & LEARNING                   |
|   |  - Query PostgreSQL for learning records         |
|   |  - Session storage in Redis                      |
|   |  - Health endpoints for monitoring               |
|   |  - Dataview queries use tag taxonomy             |
|   +--------------------------------------------------+
```

**Specific Dependencies:**

| Future Phase | Depends On From Phase 1 |
|--------------|------------------------|
| **Phase 2 (Ingestion)** | `Content` table for metadata, vault folder structure for output, templates for note format |
| **Phase 3 (LLM Processing)** | Redis for embedding cache, `Annotation` table for extracted highlights, templates for LLM output format |
| **Phase 4 (Knowledge Explorer)** | Health endpoints for status, vault structure for note loading |
| **Phase 5 (Practice Sessions)** | `PracticeSession` and `PracticeAttempt` tables, Redis for session state |
| **Phase 6 (Spaced Repetition)** | `SpacedRepCard` table, `MasterySnapshot` for analytics |
| **Phase 7 (Analytics)** | All PostgreSQL tables for querying, `MasterySnapshot` for trends |

---

## 9. Checklist

### Pre-Implementation
- [x] Review design docs
- [x] Verify Docker installed
- [x] Install Obsidian
- [x] Create `.env` file with credentials

### Phase 1A: Infrastructure
- [x] Update docker-compose.yml
- [x] Create configuration module
- [x] Set up PostgreSQL models
- [x] Configure Alembic migrations
- [x] Implement Redis utilities

### Phase 1B: Knowledge Hub
- [x] Run vault setup script
- [x] Create all templates
- [x] Define tag taxonomy
- [x] Configure plugins
- [x] Create dashboard and meta notes

### Phase 1C: Integration & Verification
- [x] Add health check endpoints
- [x] Run vault validation script
- [x] Execute test suite (see Section 4)
- [x] Run validation scripts
- [x] Document any issues

### Post-Implementation
- [x] Update OVERVIEW.md progress
- [x] Document any deviations from plan
- [x] Create issues for Phase 2 blockers

---

## 10. Extensibility Guide

The system is designed to be extended without code changes. This section documents how to add new content types, tags, and customize the system for your needs.

### 10.1 Adding a New Content Type

**Time required**: ~15-20 minutes

To add a new content type (e.g., "podcast" for podcast notes):

#### Step 1: Add to Configuration

Edit `config/default.yaml` and add an entry to `content_types`:

```yaml
content_types:
  # ... existing types ...
  
  podcast:
    folder: "sources/podcasts"
    template: "templates/podcast.md"        # Obsidian template (for Templater)
    jinja_template: "podcast.md.j2"         # Backend Jinja2 template
    description: "Podcast episode notes and takeaways"
    icon: "🎙️"
    file_types: ["url", "audio"]
    subfolders:
      - episodes
      - series
```

#### Step 2: Create the Obsidian Template

Create `templates/podcast.md` in your vault (for manual note creation via Templater):

```markdown
---
type: podcast
title: "{{title}}"
podcast_name: ""
episode: ""
host: ""
guests: []
duration: ""
tags: []
status: unread
listened: {{date:YYYY-MM-DD}}
---

## Summary


## Key Takeaways
1. 
2. 
3. 

## Notable Quotes
> "Quote"
> — Speaker, timestamp

## My Notes


## Action Items
- [ ] 

## Related
- [[Related Note]]
```

#### Step 3: Create the Jinja2 Template (for Backend)

Create `config/templates/podcast.md.j2` (for backend note generation):

```jinja2
---
type: podcast
title: "{{ title }}"
podcast_name: "{{ podcast_name }}"
episode: "{{ episode }}"
host: "{{ host }}"
guests: [{{ guests | join(', ') }}]
duration: "{{ duration }}"
tags: [{{ tags | join(', ') }}]
status: unread
listened: {{ listened | datestamp }}
created: {{ created | datestamp }}
processed: {{ processed | datestamp }}
---

## Summary
{{ summary }}

## Key Takeaways
{{ key_takeaways }}

## Notable Quotes
{{ quotes }}

## My Notes
{{ notes }}

## Action Items
{{ action_items }}

## Related
{{ connections }}
```

#### Step 4: Regenerate Vault Structure

```bash
python scripts/setup/setup_vault.py
```

**That's it!** The system will now:
- ✅ Create the `sources/podcasts/` folder structure
- ✅ Recognize "podcast" as a valid content type
- ✅ Use the Obsidian template for manual note creation (via Templater)
- ✅ Use the Jinja2 template for backend-generated notes
- ✅ Include podcasts in Dataview queries
- ✅ Show podcasts in the frontend content type selector

### 10.2 Adding New Tags

**Time required**: ~5 minutes

Tags are defined in `config/tag-taxonomy.yaml` (the single source of truth) and synced to the PostgreSQL `tags` table for validation.

#### Step 1: Add to Taxonomy Configuration

Edit `config/tag-taxonomy.yaml`:

```markdown
### Audio & Podcasts

#### audio/podcasts/ — Podcast Content
- `audio/podcasts/tech` — Technology podcasts
- `audio/podcasts/business` — Business & entrepreneurship
- `audio/podcasts/interview` — Interview format shows
```

#### Step 2: (Optional) Add to Database

For strict tag validation, add to the `tags` table:

```python
# Via API or direct DB insert
Tag(
    name="audio/podcasts/tech",
    category="domain",
    description="Technology podcasts",
    parent_id=<parent_tag_uuid>  # Optional
)
```

### 10.3 Customizing Existing Content Types

You can modify existing content types by editing `config/default.yaml`:

```yaml
content_types:
  paper:
    folder: "sources/papers"
    template: "templates/paper.md"
    # Add new subfolders
    subfolders:
      - ml
      - systems
      - security
      - economics  # New category!
```

Re-run `python scripts/setup/setup_vault.py` to create new folders.

### 10.4 Creating Custom Templates

Templates support Templater syntax for dynamic content:

| Syntax | Output | Use Case |
|--------|--------|----------|
| `{{date:YYYY-MM-DD}}` | `2024-12-21` | Current date |
| `{{date:dddd}}` | `Saturday` | Day of week |
| `{{title}}` | User input | Note title |
| `{{time:HH:mm}}` | `14:30` | Current time |

**Template Best Practices:**
1. Always include `type` in frontmatter
2. Include `tags: []` for queryability
3. Include `status` for workflow tracking
4. Use `<!-- LLM-generated -->` comments for sections filled by AI
5. Include `## Related` section for linking

### 10.5 Extending the Tag Hierarchy

The tag system uses a 3-level hierarchy: `domain/category/topic`

**Adding a New Domain:**

```yaml
# In config/tag-taxonomy.yaml

new-domain:
  description: "New Domain Name"
  categories:
    category1:
      description: "Category description"
      topics:
        - topic1: "Topic description"
        - topic2: "Topic description"
    category2:
      description: "Another category"
      topics:
        - topic1: "Topic description"
```

After updating the YAML, regenerate the vault reference file:

```bash
python scripts/setup/setup_vault.py --regenerate-taxonomy
```

This will update `meta/tag-taxonomy.md` with the new tags. The generated file looks like:

```markdown
### New Domain Name

#### newdomain/category1/ — Description
- `newdomain/category1/topic1` — Topic description
- `newdomain/category1/topic2` — Topic description

#### newdomain/category2/ — Description
- `newdomain/category2/topic1` — Topic description
```

**Rules for New Tags:**
1. Use lowercase with hyphens
2. Follow the 3-level hierarchy
3. Keep tag names concise (< 30 chars total)
4. Add description for discoverability
5. Ensure it's meaningfully different from existing tags

### 10.6 API Extension Points

For programmatic extensions, the system provides these hooks:

```python
# Register a custom content type handler
from app.content_types import content_registry

# Check if a type exists before processing
if content_registry.validate_type("podcast"):
    folder = content_registry.get_folder("podcast")
    template = content_registry.get_template("podcast")

# Get all user-selectable types for UI dropdowns
types = content_registry.user_types  # Excludes system types

# Reverse lookup: determine type from file path
content_type = content_registry.type_for_folder("sources/podcasts/episode1.md")
```

### 10.7 Configuration Validation

The system validates configuration at startup. If you add invalid configuration:

```yaml
content_types:
  invalid_type:
    # Missing required 'folder' field!
    template: "templates/invalid.md"
```

The system will fail fast with a clear error:

```
ConfigurationError: Content type 'invalid_type' missing required field 'folder'
```

### 10.8 Extensibility Checklist

When extending the system, verify:

- [x] Configuration added to `config/default.yaml` (with both `template` and `jinja_template` fields)
- [x] Obsidian template created in vault's `templates/` folder (for manual creation)
- [x] Jinja2 template created in `config/templates/` folder (for backend generation)
- [x] Both templates have required frontmatter (`type`, `tags`, `status`)
- [x] Vault setup script run to create folders (`python scripts/setup/setup_vault.py`)
- [x] Tag taxonomy updated (if new tags needed)
- [ ] (Optional) Templater folder mapping configured in Obsidian

---

## 11. Frequently Asked Questions

### Infrastructure Questions

**Q: Why do we need both Neo4j AND PostgreSQL?**

A: They serve different purposes. PostgreSQL stores **transactional data** (who practiced when, what's due for review, processing status). Neo4j stores **relationships** (how concepts connect, citation graphs). You could force everything into PostgreSQL, but graph queries ("find all concepts within 3 hops of Transformers") are orders of magnitude slower in SQL.

**Q: What happens if Redis goes down?**

A: The system degrades gracefully. Session data is lost (users need to re-login), caches become cache misses (slower but functional). Redis is not the source of truth for anything critical—it's an optimization layer.

**Q: Can I skip Docker and run services locally?**

A: Yes, but not recommended. You'd need to install PostgreSQL, Redis, and Neo4j manually, configure connection strings, and ensure versions match. Docker makes the entire stack reproducible with `docker-compose up`.

### Obsidian Questions

**Q: Why Obsidian instead of Notion/Roam/Logseq?**

A: Three reasons:
1. **Local files**: Plain Markdown files you own, not locked in a proprietary database
2. **Plugin ecosystem**: Dataview enables database-like queries impossible in most tools
3. **Backend integration**: Easy for code to read/write Markdown files

**Q: What if I don't use Obsidian?**

A: The backend writes Markdown files—they're usable in any editor. You'd lose Dataview queries and Templater features, but the files themselves are portable.

**Q: Why are templates separate from the backend code?**

A: Templates live in the vault because:
1. Users can customize them without touching code
2. Obsidian's Templater plugin needs them in the vault
3. Separation of concerns: backend writes content, templates define format

### Configuration Questions

**Q: Why both `.env` and `config/default.yaml`?**

A: **Secrets vs. behavior**. `.env` holds secrets (passwords, API keys) that should never be in git. `default.yaml` holds application settings (folder names, TTLs) that should be version-controlled and documented.

**Q: How do I override config for different environments?**

A: Environment variables override `.env` values. For YAML, create `config/production.yaml` that overrides specific values from `config/default.yaml`. The config loader merges them.

**Q: What's the minimum configuration to get started?**

A: Create a `.env` file with:
```bash
NEO4J_PASSWORD=your_neo4j_password
POSTGRES_PASSWORD=your_postgres_password
OPENAI_API_KEY=your_openai_key
OBSIDIAN_VAULT_PATH=/path/to/your/vault
```
Everything else has sensible defaults.

### Extensibility Questions

**Q: How do I add a new content type (e.g., for podcasts or courses)?**

A: Just two steps, no code changes needed:
1. Add entry to `content_types` in `config/default.yaml`
2. Create the template file in `templates/`
Run `python scripts/setup/setup_vault.py` to create folders. See Section 10.1 for details.

**Q: Can I customize the folder structure?**

A: Yes! The folder structure is entirely defined in `config/default.yaml`. Change folder paths, add subfolders, or reorganize as needed. The system reads this dynamically at runtime.

**Q: What if I need a content type that doesn't fit the existing templates?**

A: Create a custom template with whatever frontmatter and sections you need. The only requirements are:
- `type: your_type_name` in frontmatter (for Dataview queries)
- `tags: []` field (for tagging)
The system handles everything else dynamically.

**Q: Can I add my own tag domains beyond what's predefined?**

A: Absolutely. Tags are not hardcoded. Add new domains to `config/tag-taxonomy.yaml` (the single source of truth) following the `domain/category/topic` convention. The tags will be synced to the PostgreSQL `tags` table for validation. The `meta/tag-taxonomy.md` file in the vault is auto-generated from this YAML config—run `python scripts/setup/setup_vault.py --regenerate-taxonomy` after changes.

---

## 12. Related Documents

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `design_docs/00_system_overview.md` | High-level architecture | Understanding the big picture |
| `design_docs/03_knowledge_hub_obsidian.md` | Detailed Obsidian design | Deep dive on vault structure, templates |
| `design_docs/09_data_models.md` | Complete data model reference | Understanding all entity relationships |
| `implementation_plan/OVERVIEW.md` | Master roadmap | Seeing how this phase fits |
| `implementation_plan/01_ingestion_layer_implementation.md` | Next phase plan | Planning ahead |

