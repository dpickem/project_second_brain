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
- [ ] PostgreSQL service added to docker-compose.yml
- [ ] Redis service added to docker-compose.yml
- [ ] Health checks configured for all services
- [ ] Volume persistence configured
- [ ] Backend dependencies updated

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

# Obsidian vault configuration
# These settings tell the ingestion pipelines WHERE to write notes
# and WHICH template to use for each content type
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
    
  # Subfolders within sources/ - one for each content type
  # Maps directly to ContentType enum in the data models
  subfolders:
    sources:
      - papers               # Academic papers, research (PDFs)
      - articles             # Blog posts, news, essays (web)
      - books                # Book notes and highlights (photos/OCR)
      - code                 # Repository analyses (GitHub)
      - ideas                # Fleeting notes, quick captures
      - work                 # Work-specific content (meetings, proposals)
      
  # Template file paths for each content type
  # When ingesting a paper, use templates/paper.md
  # These templates define the frontmatter schema and section structure
  templates:
    paper: "templates/paper.md"
    article: "templates/article.md"
    book: "templates/book.md"
    code: "templates/code.md"
    concept: "templates/concept.md"
    idea: "templates/idea.md"
    daily: "templates/daily.md"
    exercise: "templates/exercise.md"

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

**Deliverables:**
- [ ] Pydantic settings class
- [ ] YAML configuration file
- [ ] Environment variable validation
- [ ] Configuration loading utilities

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
- [ ] Async SQLAlchemy engine setup
- [ ] Session management with dependency injection
- [ ] Core database models (Content, Annotation, Tag)
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
- [ ] Alembic configuration
- [ ] Initial migration script
- [ ] Migration commands documented

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
- [ ] Redis connection pool
- [ ] Caching utilities
- [ ] Session store implementation

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
|   +-- work/             # Work-specific content
|       |-- meetings/     # Meeting notes
|       |-- proposals/    # Proposals, design docs
|       +-- projects/     # Project-specific notes
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
# scripts/setup_vault.py

from pathlib import Path
import yaml

def create_vault_structure(vault_path: Path, config: dict):
    """Create the Obsidian vault folder structure."""
    
    vault_path.mkdir(parents=True, exist_ok=True)
    
    # Core folders
    folders = [
        "sources/papers",
        "sources/articles", 
        "sources/books",
        "sources/code",
        "sources/ideas",
        "sources/work/meetings",
        "sources/work/proposals",
        "sources/work/projects",
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
    
    for folder in folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)
        print(f"Created: {folder}")
    
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


if __name__ == "__main__":
    import json
    import os
    
    vault_path = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "./vault"))
    
    with open("config/default.yaml") as f:
        config = yaml.safe_load(f)
    
    create_vault_structure(vault_path, config)
    create_obsidian_config(vault_path)
```

**Deliverables:**
- [ ] Vault folder structure created
- [ ] Obsidian configuration files
- [ ] Vault setup script

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

**Deliverables:**
- [ ] Paper template
- [ ] Article template
- [ ] Book template
- [ ] Code repository template
- [ ] Concept template
- [ ] Idea template
- [ ] Daily note template
- [ ] Exercise template

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
<!-- meta/tag-taxonomy.md -->
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

### Personal

#### personal/wellbeing/ — Health & Wellbeing
- `personal/wellbeing/health` — Physical health, fitness
- `personal/wellbeing/mental` — Mental health, mindfulness

#### personal/growth/ — Personal Growth
- `personal/growth/finance` — Personal finance
- `personal/growth/philosophy` — Philosophy, thinking
- `personal/growth/creativity` — Creative pursuits

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
- [ ] Tag taxonomy document
- [ ] Domain tag hierarchy
- [ ] Status tag definitions
- [ ] Quality tag definitions
- [ ] Source tag mappings
- [ ] Tag usage guidelines

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
- [ ] Plugin setup documentation
- [ ] Dataview query examples
- [ ] Templater configuration
- [ ] Hotkey recommendations

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
| `tag-taxonomy.md` | Tag definitions and rules | When adding new tags, resolving confusion |
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
- [ ] Main dashboard with Dataview queries
- [ ] Workflows documentation
- [ ] Review queue note
- [ ] Folder index templates

**Estimated Time:** 3 hours

---

### Phase 1C: Integration & Testing (Days 8-10)

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
- [ ] Basic health endpoint
- [ ] Detailed health with service checks
- [ ] Readiness probe endpoint

**Estimated Time:** 2 hours

---

#### Task 1C.2: Database Migration Test

**Purpose**: Verify the database is correctly set up and basic CRUD operations work.

**Why Test Scripts (Not Just Unit Tests)?**

Test scripts are **runnable verification tools** that:
1. Can be run manually during development
2. Serve as documentation ("this is how you verify the DB works")
3. Are simpler than pytest fixtures for quick checks
4. Work in the Docker environment

Create test script to verify database setup:

```python
# scripts/test_database.py

import asyncio
from app.db.base import engine, async_session_maker, init_db
from app.db.models import Content, Tag, PracticeSession
from sqlalchemy import select
import uuid
from datetime import datetime

async def test_database():
    """Test database connectivity and basic operations."""
    
    print("🔄 Testing database connection...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    async with async_session_maker() as session:
        # Test insert
        test_tag = Tag(
            id=uuid.uuid4(),
            name="test/tag",
            category="test",
            description="Test tag for verification"
        )
        session.add(test_tag)
        await session.commit()
        print("✅ Insert successful")
        
        # Test query
        result = await session.execute(
            select(Tag).where(Tag.name == "test/tag")
        )
        tag = result.scalar_one_or_none()
        assert tag is not None
        print("✅ Query successful")
        
        # Test delete
        await session.delete(tag)
        await session.commit()
        print("✅ Delete successful")
    
    print("\n✅ All database tests passed!")


if __name__ == "__main__":
    asyncio.run(test_database())
```

**Deliverables:**
- [ ] Database test script
- [ ] CRUD operation verification

**Estimated Time:** 1 hour

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
# scripts/validate_vault.py

from pathlib import Path
import frontmatter
import yaml
import sys

def validate_vault(vault_path: Path) -> bool:
    """Validate Obsidian vault structure and configuration."""
    
    errors = []
    warnings = []
    
    print(f"🔍 Validating vault at: {vault_path}\n")
    
    # Check folder structure
    required_folders = [
        "sources/papers",
        "sources/articles",
        "sources/books",
        "sources/code",
        "sources/ideas",
        "topics",
        "concepts",
        "exercises",
        "reviews",
        "daily",
        "templates",
        "meta",
    ]
    
    for folder in required_folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            print(f"  ✅ {folder}")
        else:
            errors.append(f"Missing folder: {folder}")
            print(f"  ❌ {folder} (missing)")
    
    print()
    
    # Check templates
    required_templates = [
        "templates/paper.md",
        "templates/article.md",
        "templates/book.md",
        "templates/code.md",
        "templates/concept.md",
        "templates/daily.md",
    ]
    
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
- [ ] Vault validation script
- [ ] Folder structure checks
- [ ] Template validation
- [ ] Meta file checks

**Estimated Time:** 1 hour

---

#### Task 1C.4: Integration Test Suite

**Purpose**: Automated tests that verify the entire stack works together.

**Why Integration Tests (Not Just Unit Tests)?**

| Unit Tests | Integration Tests |
|------------|------------------|
| Test code in isolation | Test components together |
| Mock all dependencies | Use real PostgreSQL, Redis |
| Fast (milliseconds) | Slower but realistic |
| "Function returns correct value" | "API can save to DB and cache" |

**Test Categories for Phase 1:**

```text
INTEGRATION TEST COVERAGE
=========================

1. DATABASE CONNECTIVITY
   - Can connect to PostgreSQL
   - All tables exist (from migrations)
   - Basic CRUD operations work

2. REDIS CONNECTIVITY
   - Can connect to Redis
   - Set/get operations work
   - TTL expiration works

3. VAULT STRUCTURE
   - Required folders exist
   - Templates present and valid
   - Meta files have correct structure

4. API ENDPOINTS
   - Health endpoints return correct status
   - Service degradation is detected
```

Create integration tests for Phase 1:

```python
# tests/integration/test_foundation.py

import pytest
import asyncio
from pathlib import Path
from sqlalchemy import text

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    from app.db.base import async_session_maker
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def redis_client():
    from app.db.redis import get_redis
    client = await get_redis()
    yield client


class TestPostgreSQLConnection:
    """Test PostgreSQL connectivity and operations."""
    
    @pytest.mark.asyncio
    async def test_connection(self, db_session):
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_tables_exist(self, db_session):
        """Verify all required tables exist."""
        tables = [
            "content",
            "annotations", 
            "tags",
            "practice_sessions",
            "practice_attempts",
            "spaced_rep_cards",
            "mastery_snapshots"
        ]
        
        for table in tables:
            result = await db_session.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            )
            assert result.scalar() is True, f"Table {table} does not exist"


class TestRedisConnection:
    """Test Redis connectivity and operations."""
    
    @pytest.mark.asyncio
    async def test_connection(self, redis_client):
        assert await redis_client.ping()
    
    @pytest.mark.asyncio
    async def test_set_get(self, redis_client):
        await redis_client.set("test_key", "test_value", ex=60)
        value = await redis_client.get("test_key")
        assert value == "test_value"
        await redis_client.delete("test_key")


class TestVaultStructure:
    """Test Obsidian vault setup."""
    
    @pytest.fixture
    def vault_path(self):
        from app.config import settings
        return Path(settings.OBSIDIAN_VAULT_PATH)
    
    def test_vault_exists(self, vault_path):
        assert vault_path.exists()
        assert vault_path.is_dir()
    
    def test_required_folders(self, vault_path):
        required = [
            "sources/papers",
            "sources/articles",
            "templates",
            "meta"
        ]
        for folder in required:
            assert (vault_path / folder).exists(), f"Missing: {folder}"
    
    def test_templates_exist(self, vault_path):
        templates = [
            "templates/paper.md",
            "templates/article.md",
            "templates/book.md"
        ]
        for template in templates:
            assert (vault_path / template).exists(), f"Missing: {template}"


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_detailed_health(self, client):
        response = client.get("/api/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "postgres" in data["services"]
        assert "redis" in data["services"]
```

**Deliverables:**
- [ ] PostgreSQL connection tests
- [ ] Redis connection tests
- [ ] Vault structure tests
- [ ] Health endpoint tests

**Estimated Time:** 3 hours

---

## 4. Testing Strategy

### 4.1 Test Structure

```text
tests/
|-- unit/
|   |-- test_config.py         # Configuration loading
|   |-- test_redis_cache.py    # Redis utilities
|   +-- test_vault_utils.py    # Vault helper functions
|-- integration/
|   +-- test_foundation.py     # Full integration tests
+-- fixtures/
    +-- sample_vault/          # Test vault structure
```

### 4.2 Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only integration tests
pytest tests/integration/ -v

# Run specific test class
pytest tests/integration/test_foundation.py::TestPostgreSQLConnection -v
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
- [ ] All Docker services start successfully
- [ ] PostgreSQL accepts connections and migrations run
- [ ] Redis responds to ping
- [ ] Health endpoints return healthy status
- [ ] Backend can read/write to all databases

### Knowledge Hub
- [ ] Vault folder structure matches design
- [ ] All templates have valid frontmatter
- [ ] Tag taxonomy is documented
- [ ] Dashboard displays correctly with Dataview
- [ ] Daily note template works with Templater

### Integration
- [ ] All integration tests pass
- [ ] Vault validation script succeeds
- [ ] Configuration loads from environment

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
- [ ] Review design docs
- [ ] Verify Docker installed
- [ ] Install Obsidian
- [ ] Create `.env` file with credentials

### Phase 1A: Infrastructure
- [ ] Update docker-compose.yml
- [ ] Create configuration module
- [ ] Set up PostgreSQL models
- [ ] Configure Alembic migrations
- [ ] Implement Redis utilities

### Phase 1B: Knowledge Hub
- [ ] Run vault setup script
- [ ] Create all templates
- [ ] Define tag taxonomy
- [ ] Configure plugins
- [ ] Create dashboard and meta notes

### Phase 1C: Integration
- [ ] Add health check endpoints
- [ ] Write integration tests
- [ ] Run validation scripts
- [ ] Document any issues

### Post-Implementation
- [ ] Update OVERVIEW.md progress
- [ ] Document any deviations from plan
- [ ] Create issues for Phase 2 blockers

---

## 10. Frequently Asked Questions

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

---

## 11. Related Documents

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `design_docs/00_system_overview.md` | High-level architecture | Understanding the big picture |
| `design_docs/03_knowledge_hub_obsidian.md` | Detailed Obsidian design | Deep dive on vault structure, templates |
| `design_docs/09_data_models.md` | Complete data model reference | Understanding all entity relationships |
| `implementation_plan/OVERVIEW.md` | Master roadmap | Seeing how this phase fits |
| `implementation_plan/01_ingestion_layer_implementation.md` | Next phase plan | Planning ahead |

