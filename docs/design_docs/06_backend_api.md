# Backend API Design

> **Document Status**: Design Specification (Largely Implemented)  
> **Last Updated**: January 2026  
> **Implementation Status**: ~90% Complete  
> **Related Docs**: `07_frontend_application.md`, `09_data_models.md`

---

## Implementation Status Summary

| Router | Status | Notes |
|--------|--------|-------|
| `/api/health/*` | ✅ Implemented | Health checks, readiness probes |
| `/api/capture/*` | ✅ Implemented | Text, URL, photo, voice, PDF, book capture |
| `/api/ingest/*` | ✅ Implemented | Raindrop sync, GitHub sync, queue management |
| `/api/processing/*` | ✅ Implemented | LLM processing pipeline triggers |
| `/api/vault/*` | ✅ Implemented | Obsidian vault operations, sync |
| `/api/knowledge/*` | ✅ Implemented | Graph visualization, node queries |
| `/api/practice/*` | ✅ Implemented | Practice sessions, exercises, attempts |
| `/api/review/*` | ✅ Implemented | Spaced rep cards, FSRS scheduling |
| `/api/analytics/*` | ✅ Implemented | Mastery tracking, weak spots, learning curves |
| `/api/assistant/*` | ⬜ Not Started | Chat interface, suggestions (Phase 9) |

---

## 1. Overview

The FastAPI backend provides REST APIs for all system operations including content ingestion, knowledge queries, practice sessions, and analytics. It orchestrates communication between the frontend, databases, and LLM services.

### Design Goals

1. **Type Safety**: Full Pydantic validation on all endpoints ✅
2. **Async First**: Non-blocking I/O for LLM and database calls ✅
3. **Modular Routers**: Separate routers for each domain ✅
4. **Observable**: Structured logging, metrics, and tracing ✅
5. **Testable**: Dependency injection for all services ✅

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           ROUTERS                                     │   │
│  │  /api/capture/*  /api/ingest/*   /api/processing/*  /api/vault/*     │   │
│  │  /api/knowledge/* /api/practice/* /api/review/*     /api/analytics/* │   │
│  │  /api/health/*   /api/assistant/* (planned)                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          MIDDLEWARE                                   │   │
│  │  CORS │ Request Logging │ Error Handling                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          SERVICES                                     │   │
│  │  learning/         │  processing/         │  obsidian/               │   │
│  │   ├─ fsrs          │   ├─ pipeline        │   ├─ vault               │   │
│  │   ├─ spaced_rep    │   ├─ summarization   │   ├─ sync                │   │
│  │   ├─ mastery       │   ├─ extraction      │   ├─ watcher             │   │
│  │   ├─ session       │   ├─ tagging         │   └─ frontmatter         │   │
│  │   ├─ exercise_gen  │   └─ connections     │                          │   │
│  │   ├─ evaluator     │                      │  knowledge_graph/        │   │
│  │   └─ code_sandbox  │  llm/                │   ├─ client              │   │
│  │                    │   └─ client          │   ├─ queries             │   │
│  │  pipelines/        │     (LiteLLM)        │   └─ schemas             │   │
│  │   ├─ raindrop      │                      │                          │   │
│  │   ├─ github        │  scheduler           │  queue (Celery)          │   │
│  │   ├─ pdf           │  cost_tracking       │  tag_service             │   │
│  │   ├─ book_ocr      │  storage             │                          │   │
│  │   └─ voice         │                      │                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA ACCESS                                   │   │
│  │        PostgreSQL        │        Neo4j        │        Redis         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure (Current)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app creation ✅
│   ├── config/
│   │   └── settings.py         # Pydantic Settings ✅
│   │
│   ├── routers/                # API route modules ✅
│   │   ├── health.py           # Health checks ✅
│   │   ├── capture.py          # Quick capture endpoints ✅
│   │   ├── ingestion.py        # Sync triggers, queue ✅
│   │   ├── processing.py       # LLM processing ✅
│   │   ├── vault.py            # Obsidian operations ✅
│   │   ├── knowledge.py        # Knowledge graph queries ✅
│   │   ├── practice.py         # Practice sessions ✅
│   │   ├── review.py           # Spaced repetition ✅
│   │   ├── analytics.py        # Learning analytics ✅
│   │   └── assistant.py        # LLM chat (planned) ⬜
│   │
│   ├── services/               # Business logic ✅
│   │   ├── learning/           # Learning system ✅
│   │   │   ├── fsrs.py         # FSRS algorithm ✅
│   │   │   ├── spaced_rep_service.py ✅
│   │   │   ├── mastery_service.py ✅
│   │   │   ├── session_service.py ✅
│   │   │   ├── exercise_generator.py ✅
│   │   │   ├── evaluator.py    ✅
│   │   │   └── code_sandbox.py ✅
│   │   ├── processing/         # LLM pipeline ✅
│   │   │   ├── pipeline.py     ✅
│   │   │   └── stages/         # summarization, extraction, etc. ✅
│   │   ├── obsidian/           # Vault management ✅
│   │   │   ├── vault.py        ✅
│   │   │   ├── sync.py         ✅
│   │   │   ├── watcher.py      ✅
│   │   │   └── frontmatter.py  ✅
│   │   ├── knowledge_graph/    # Neo4j client ✅
│   │   ├── llm/                # LiteLLM client ✅
│   │   ├── scheduler.py        # APScheduler ✅
│   │   ├── queue.py            # Celery tasks ✅
│   │   └── tag_service.py      # Tag taxonomy ✅
│   │
│   ├── pipelines/              # Ingestion pipelines ✅
│   │   ├── raindrop_sync.py    ✅
│   │   ├── github_importer.py  ✅
│   │   ├── pdf_processor.py    ✅
│   │   ├── book_ocr.py         ✅
│   │   ├── voice_transcribe.py ✅
│   │   └── web_article.py      ✅
│   │
│   ├── models/                 # Pydantic models ✅
│   │   ├── content.py          ✅
│   │   ├── learning.py         ✅
│   │   ├── llm_usage.py        ✅
│   │   └── processing.py       ✅
│   │
│   ├── db/                     # Database ✅
│   │   ├── base.py             # SQLAlchemy base ✅
│   │   ├── models.py           # Content models ✅
│   │   ├── models_learning.py  # Learning models ✅
│   │   ├── models_processing.py # Processing models ✅
│   │   └── redis.py            ✅
│   │
│   └── enums/                  # Enumerations ✅
│       ├── content.py          ✅
│       ├── learning.py         ✅
│       └── processing.py       ✅
│
├── alembic/                    # Database migrations ✅
│   └── versions/
│       ├── 001-007...          # Foundation migrations ✅
│       └── 008_timestamps_with_timezone.py ✅
│
├── tests/
│   ├── unit/                   # Unit tests ✅
│   └── integration/            # API integration tests ✅
│
├── Dockerfile                  ✅
├── requirements.txt            ✅
└── alembic.ini                 ✅
```

---

## 4. Main Application ✅

```python
# backend/app/main.py (IMPLEMENTED)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import (
    health_router, capture_router, ingestion_router,
    processing_router, vault_router, knowledge_router,
    practice_router, review_router, analytics_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: scheduler, vault services
    yield
    # Shutdown: cleanup

app = FastAPI(
    title="Second Brain API",
    description="Knowledge management and learning system API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS, router registration, Neo4j driver initialization
```

---

## 5. API Endpoints

### 5.1 Capture Router ✅

**Prefix**: `/api/capture`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/text` | POST | ✅ | Quick text capture for ideas/notes |
| `/url` | POST | ✅ | Capture URL for processing |
| `/photo` | POST | ✅ | Photo capture for OCR |
| `/voice` | POST | ✅ | Voice memo transcription |
| `/pdf` | POST | ✅ | PDF document ingestion |
| `/book` | POST | ✅ | Multi-image book OCR |

### 5.2 Ingestion Router ✅

**Prefix**: `/api/ingest`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/raindrop/sync` | POST | ✅ | Sync Raindrop.io bookmarks |
| `/github/sync` | POST | ✅ | Import GitHub starred repos |
| `/status/{content_id}` | GET | ✅ | Get processing status |
| `/queue/stats` | GET | ✅ | Queue statistics |
| `/scheduled` | GET | ✅ | List scheduled jobs |
| `/scheduled/{job_id}/trigger` | POST | ✅ | Manually trigger job |
| `/pending` | GET | ✅ | List pending content |
| `/taxonomy/sync` | POST | ✅ | Sync tag taxonomy |

### 5.3 Processing Router ✅

**Prefix**: `/api/processing`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/trigger` | POST | ✅ | Trigger LLM processing |
| `/status/{content_id}` | GET | ✅ | Processing status |
| `/result/{content_id}` | GET | ✅ | Get processing results |
| `/pending` | GET | ✅ | List pending items |
| `/reprocess` | POST | ✅ | Reprocess failed content |

### 5.4 Vault Router ✅

**Prefix**: `/api/vault`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/status` | GET | ✅ | Vault status & statistics |
| `/ensure-structure` | POST | ✅ | Ensure folder structure |
| `/indices/regenerate` | POST | ✅ | Regenerate folder indices |
| `/daily` | POST | ✅ | Create daily note |
| `/daily/inbox` | POST | ✅ | Add item to inbox |
| `/sync` | POST | ✅ | Sync vault to Neo4j |
| `/folders` | GET | ✅ | List content folders |
| `/watcher/status` | GET | ✅ | Watcher status |
| `/sync/status` | GET | ✅ | Sync status |
| `/notes` | GET | ✅ | List notes |
| `/notes/{path}` | GET | ✅ | Get note content |

### 5.5 Knowledge Router ✅

**Prefix**: `/api/knowledge`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/graph` | GET | ✅ | Graph data for visualization |
| `/stats` | GET | ✅ | Graph statistics |
| `/node/{node_id}` | GET | ✅ | Node details |
| `/health` | GET | ✅ | Neo4j health check |
| `/search` | GET | ⬜ | Semantic search (planned) |
| `/connections/{id}` | GET | ⬜ | Get connections (planned) |
| `/topics` | GET | ⬜ | Topic hierarchy (planned) |

### 5.6 Practice Router ✅

**Prefix**: `/api/practice`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/session` | POST | ✅ | Create practice session |
| `/session/{id}/end` | POST | ✅ | End session, get summary |
| `/exercise/generate` | POST | ✅ | Generate single exercise |
| `/exercise/{id}` | GET | ✅ | Get exercise details |
| `/submit` | POST | ✅ | Submit exercise attempt |
| `/attempt/{id}/confidence` | PATCH | ✅ | Update confidence rating |

### 5.7 Review Router ✅

**Prefix**: `/api/review`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/cards` | POST | ✅ | Create spaced rep card |
| `/cards/{id}` | GET | ✅ | Get card details |
| `/due` | GET | ✅ | Get due cards |
| `/rate` | POST | ✅ | Submit card rating (FSRS) |
| `/stats` | GET | ✅ | Review statistics |

### 5.8 Analytics Router ✅

**Prefix**: `/api/analytics`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/overview` | GET | ✅ | Mastery overview |
| `/mastery/{topic}` | GET | ✅ | Topic-specific mastery |
| `/weak-spots` | GET | ✅ | Topics needing attention |
| `/learning-curve` | GET | ✅ | Learning curve data |
| `/snapshot` | POST | ✅ | Take mastery snapshot |
| `/time-investment` | GET | ⬜ | Time by topic (planned) |
| `/streak` | GET | ⬜ | Practice streak (planned) |

### 5.9 Assistant Router ⬜ (Planned - Phase 9)

**Prefix**: `/api/assistant`

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/chat` | POST | ⬜ | Chat with assistant |
| `/chat/stream` | POST | ⬜ | Streaming chat |
| `/suggestions` | GET | ⬜ | Learning suggestions |
| `/explain-connection` | POST | ⬜ | Explain graph connections |

---

## 6. Configuration ✅

Settings are managed via Pydantic BaseSettings in `app/config/settings.py`:

```python
class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Second Brain"
    DEBUG: bool = False
    
    # Database
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    
    # Neo4j
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    
    # Redis
    REDIS_URL
    
    # LLM (via LiteLLM)
    OPENAI_API_KEY, MISTRAL_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
    
    # Obsidian
    OBSIDIAN_VAULT_PATH
    
    # External Services
    RAINDROP_ACCESS_TOKEN, GITHUB_ACCESS_TOKEN
    
    # Learning System
    SESSION_TIME_RATIO_SPACED_REP: float = 0.4
    SESSION_TIME_RATIO_WEAK_SPOTS: float = 0.3
    SESSION_TIME_RATIO_NEW_CONTENT: float = 0.3
    SESSION_TIME_PER_CARD: float = 2.0
    SESSION_TIME_PER_EXERCISE: float = 7.0
    SESSION_MAX_WEAK_SPOTS: int = 3
    MASTERY_WEAK_SPOT_THRESHOLD: float = 0.6
```

---

## 7. Background Tasks ✅

Using Celery with Redis broker:

```python
# backend/app/services/queue.py

celery_app = Celery(
    "second_brain",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Task queues: high_priority, default, low_priority
```

APScheduler for periodic tasks:

```python
# backend/app/services/scheduler.py

scheduler = BackgroundScheduler()
# Scheduled: Raindrop sync, GitHub sync
```

---

## 8. Testing ✅

- **Unit tests**: `tests/unit/` - Comprehensive coverage for services
- **Integration tests**: `tests/integration/` - API endpoint testing
- **Test database safety**: Automatic check to prevent production DB access
- **Fixtures**: Shared fixtures in `conftest.py`

---

## 9. Remaining Work

### High Priority (for feature completeness)
1. **Knowledge Search** - Semantic search endpoint (`/api/knowledge/search`)
2. **Connection queries** - Related content lookup
3. **Topic hierarchy** - Hierarchical topic browsing

### Phase 9 (Learning Assistant)
1. **Assistant Router** - Full chat interface
2. **RAG Pipeline** - Query knowledge graph for context
3. **Suggestions** - Proactive learning recommendations

### Nice to Have
1. Rate limiting middleware
2. Authentication middleware (if multi-user)
3. Time investment analytics
4. Practice streak tracking

---

## 10. Related Documents

- `07_frontend_application.md` — Frontend consuming these APIs
- `09_data_models.md` — Full Pydantic and database models
- `05_learning_system.md` — Practice and review logic
- `implementation_plan/OVERVIEW.md` — Implementation roadmap
