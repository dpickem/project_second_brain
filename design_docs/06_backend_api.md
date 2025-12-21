# Backend API Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `07_frontend_application.md`, `09_data_models.md`

---

## 1. Overview

The FastAPI backend provides REST APIs for all system operations including content ingestion, knowledge queries, practice sessions, and analytics. It orchestrates communication between the frontend, databases, and LLM services.

### Design Goals

1. **Type Safety**: Full Pydantic validation on all endpoints
2. **Async First**: Non-blocking I/O for LLM and database calls
3. **Modular Routers**: Separate routers for each domain
4. **Observable**: Structured logging, metrics, and tracing
5. **Testable**: Dependency injection for all services

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           ROUTERS                                     │   │
│  │  /api/ingest/*   /api/knowledge/*   /api/practice/*   /api/capture/*  │   │
│  │  /api/review/*   /api/analytics/*   /api/assistant/*  /api/health/*   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          MIDDLEWARE                                   │   │
│  │  Authentication │ Rate Limiting │ Request Logging │ Error Handling   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          SERVICES                                     │   │
│  │  LLMClient │ Neo4jClient │ ProcessingPipeline │ SpacedRepScheduler   │   │
│  │  ExerciseGenerator │ MasteryTracker │ ObsidianSync │ QueueManager    │   │
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

## 3. Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app creation
│   ├── config.py               # Settings and configuration
│   │
│   ├── routers/                # API route modules
│   │   ├── __init__.py
│   │   ├── capture.py          # Quick capture endpoints
│   │   ├── ingest.py           # Content ingestion
│   │   ├── knowledge.py        # Knowledge graph queries
│   │   ├── practice.py         # Practice sessions
│   │   ├── review.py           # Spaced repetition
│   │   ├── analytics.py        # Learning analytics
│   │   ├── assistant.py        # LLM chat assistant
│   │   └── health.py           # Health checks
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── llm_client.py       # Unified LLM interface
│   │   ├── neo4j_client.py     # Graph database client
│   │   ├── exercise_generator.py
│   │   ├── spaced_rep.py       # FSRS algorithm
│   │   ├── mastery_tracker.py
│   │   ├── obsidian_sync.py
│   │   └── processing/         # LLM processing pipeline
│   │       ├── pipeline.py
│   │       ├── summarization.py
│   │       ├── extraction.py
│   │       └── connections.py
│   │
│   ├── models/                 # Pydantic models
│   │   ├── __init__.py
│   │   ├── content.py          # Content models
│   │   ├── practice.py         # Practice/learning models
│   │   ├── graph.py            # Graph data models
│   │   └── responses.py        # API response models
│   │
│   ├── db/                     # Database
│   │   ├── __init__.py
│   │   ├── postgres.py         # SQLAlchemy setup
│   │   ├── redis.py            # Redis client
│   │   └── migrations/         # Alembic migrations
│   │
│   └── middleware/             # Custom middleware
│       ├── __init__.py
│       ├── auth.py
│       ├── rate_limit.py
│       └── logging.py
│
├── tests/
│   ├── conftest.py
│   ├── test_routers/
│   └── test_services/
│
├── Dockerfile
├── requirements.txt
└── alembic.ini
```

---

## 4. Main Application

```python
# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.postgres import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.services.neo4j_client import init_neo4j, close_neo4j

from app.routers import (
    capture, ingest, knowledge, practice, 
    review, analytics, assistant, health
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    await init_redis()
    await init_neo4j()
    
    yield
    
    # Shutdown
    await close_db()
    await close_redis()
    await close_neo4j()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Second Brain API",
        description="Knowledge management and active learning system",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(capture.router, prefix="/api/capture", tags=["capture"])
    app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
    app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
    app.include_router(practice.router, prefix="/api/practice", tags=["practice"])
    app.include_router(review.router, prefix="/api/review", tags=["review"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
    
    return app

app = create_app()
```

---

## 5. API Endpoints

### 5.1 Capture Router

```python
# backend/app/routers/capture.py

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from app.models.content import CaptureResponse, ContentType

router = APIRouter()

@router.post("/text", response_model=CaptureResponse)
async def capture_text(
    background_tasks: BackgroundTasks,
    content: str = Form(...),
    title: str = Form(None),
    tags: str = Form(None)
):
    """Quick text capture for ideas and notes."""
    pass

@router.post("/url", response_model=CaptureResponse)
async def capture_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    notes: str = Form(None)
):
    """Capture a URL for processing."""
    pass

@router.post("/photo", response_model=CaptureResponse)
async def capture_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    capture_type: str = Form("general"),
    notes: str = Form(None)
):
    """Capture photo for OCR processing."""
    pass

@router.post("/voice", response_model=CaptureResponse)
async def capture_voice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Capture voice memo for transcription."""
    pass
```

### 5.2 Ingest Router

```python
# backend/app/routers/ingest.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.content import IngestResponse, ProcessingStatus

router = APIRouter()

@router.post("/pdf", response_model=IngestResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    process_immediately: bool = True
):
    """Ingest a PDF document."""
    pass

@router.post("/raindrop/sync", response_model=IngestResponse)
async def sync_raindrop(
    collection_id: int = None,
    since_days: int = 7
):
    """Sync bookmarks from Raindrop.io."""
    pass

@router.post("/github/import", response_model=IngestResponse)
async def import_github(
    repos: list[str] = None,
    import_starred: bool = True,
    limit: int = 50
):
    """Import GitHub repositories."""
    pass

@router.get("/status/{content_id}", response_model=ProcessingStatus)
async def get_processing_status(content_id: str):
    """Get processing status for ingested content."""
    pass

@router.get("/queue", response_model=list[ProcessingStatus])
async def get_queue_status():
    """Get current processing queue status."""
    pass
```

### 5.3 Knowledge Router

```python
# backend/app/routers/knowledge.py

from fastapi import APIRouter, Query
from app.models.graph import GraphData, SearchResult, ConnectionResult

router = APIRouter()

@router.get("/search", response_model=list[SearchResult])
async def search_knowledge(
    query: str,
    types: list[str] = Query(["Source", "Concept"]),
    limit: int = 20
):
    """Semantic search across knowledge base."""
    pass

@router.get("/graph", response_model=GraphData)
async def get_graph(
    center_id: str = None,
    depth: int = 2,
    node_types: list[str] = Query(["Source", "Concept"]),
    max_nodes: int = 100
):
    """Get graph data for visualization."""
    pass

@router.get("/connections/{content_id}", response_model=list[ConnectionResult])
async def get_connections(
    content_id: str,
    relationship_types: list[str] = None,
    limit: int = 10
):
    """Get connections for a specific piece of content."""
    pass

@router.get("/topics", response_model=list[dict])
async def get_topic_hierarchy():
    """Get hierarchical topic structure."""
    pass

@router.get("/topic/{topic_path}", response_model=dict)
async def get_topic_details(
    topic_path: str
):
    """Get details and content for a topic."""
    pass
```

### 5.4 Practice Router

```python
# backend/app/routers/practice.py

from fastapi import APIRouter, Depends
from app.models.practice import (
    PracticeSession, Exercise, ExerciseResponse,
    EvaluationResult, SessionSummary
)

router = APIRouter()

@router.post("/session", response_model=PracticeSession)
async def create_practice_session(
    duration_minutes: int = 15,
    topic: str = None,
    exercise_types: list[str] = None
):
    """Generate a new practice session."""
    pass

@router.get("/session/{session_id}", response_model=PracticeSession)
async def get_session(session_id: str):
    """Get an existing practice session."""
    pass

@router.post("/exercise/generate", response_model=Exercise)
async def generate_exercise(
    topic: str,
    exercise_type: str = "free_recall",
    difficulty: str = None
):
    """Generate a single exercise."""
    pass

@router.post("/exercise/{exercise_id}/submit", response_model=EvaluationResult)
async def submit_exercise_response(
    exercise_id: str,
    response: ExerciseResponse
):
    """Submit response to an exercise and get feedback."""
    pass

@router.post("/session/{session_id}/complete", response_model=SessionSummary)
async def complete_session(session_id: str):
    """Mark session as complete and get summary."""
    pass
```

### 5.5 Review Router

```python
# backend/app/routers/review.py

from fastapi import APIRouter
from app.models.practice import SpacedRepCard, CardReview, ReviewSummary

router = APIRouter()

@router.get("/due", response_model=list[SpacedRepCard])
async def get_due_cards(
    limit: int = 20,
    topic: str = None
):
    """Get cards due for review."""
    pass

@router.post("/rate/{card_id}", response_model=SpacedRepCard)
async def rate_card(
    card_id: str,
    review: CardReview
):
    """Submit rating for a reviewed card."""
    pass

@router.get("/stats", response_model=dict)
async def get_review_stats():
    """Get spaced repetition statistics."""
    pass

@router.post("/batch", response_model=ReviewSummary)
async def batch_review(
    reviews: list[CardReview]
):
    """Submit multiple card reviews at once."""
    pass
```

### 5.6 Analytics Router

```python
# backend/app/routers/analytics.py

from fastapi import APIRouter, Query
from datetime import date
from app.models.analytics import (
    MasteryOverview, WeakSpot, LearningCurve, 
    TimeInvestment, StreakData
)

router = APIRouter()

@router.get("/mastery", response_model=MasteryOverview)
async def get_mastery_overview(
    topic: str = None
):
    """Get mastery scores by topic."""
    pass

@router.get("/weak-spots", response_model=list[WeakSpot])
async def get_weak_spots(
    threshold: float = 0.6,
    limit: int = 10
):
    """Get topics that need attention."""
    pass

@router.get("/learning-curve", response_model=LearningCurve)
async def get_learning_curve(
    topic: str = None,
    start_date: date = None,
    end_date: date = None,
    metrics: list[str] = Query(["accuracy", "confidence"])
):
    """Get learning curve data over time."""
    pass

@router.get("/time-investment", response_model=TimeInvestment)
async def get_time_investment(
    period: str = "30d",
    group_by: str = "topic"
):
    """Get time spent by topic/activity."""
    pass

@router.get("/streak", response_model=StreakData)
async def get_streak_data():
    """Get practice streak information."""
    pass
```

### 5.7 Assistant Router

```python
# backend/app/routers/assistant.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.assistant import ChatMessage, ChatResponse, SuggestionResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    messages: list[ChatMessage],
    stream: bool = False
):
    """Chat with the learning assistant."""
    if stream:
        return StreamingResponse(
            stream_chat_response(messages),
            media_type="text/event-stream"
        )
    pass

@router.post("/chat/stream")
async def chat_stream(messages: list[ChatMessage]):
    """Streaming chat endpoint."""
    return StreamingResponse(
        stream_chat_response(messages),
        media_type="text/event-stream"
    )

@router.get("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    context: str = None
):
    """Get learning suggestions based on current context."""
    pass

@router.post("/explain-connection")
async def explain_connection(
    source_id: str,
    target_id: str
):
    """Get LLM explanation of connection between two items."""
    pass
```

---

## 6. Configuration

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Second Brain API"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "secondbrain"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "secondbrain"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM Providers
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    GOOGLE_API_KEY: str = None
    
    # Obsidian
    OBSIDIAN_VAULT_PATH: str
    
    # External Services
    RAINDROP_ACCESS_TOKEN: str = None
    GITHUB_ACCESS_TOKEN: str = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## 7. Error Handling

```python
# backend/app/middleware/error_handling.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(e) if settings.DEBUG else None
                }
            )

# Custom exceptions
class ProcessingError(Exception):
    """Error during content processing."""
    pass

class LLMError(Exception):
    """Error from LLM provider."""
    pass

class GraphQueryError(Exception):
    """Error querying Neo4j."""
    pass
```

---

## 8. Background Tasks

```python
# backend/app/services/queue.py

from celery import Celery
from app.config import settings

celery_app = Celery(
    "second_brain",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "process_content": {"queue": "processing"},
        "sync_raindrop": {"queue": "sync"},
        "generate_cards": {"queue": "cards"},
    }
)

@celery_app.task(bind=True, max_retries=3)
def process_content_task(self, content_id: str):
    """Background task for content processing."""
    try:
        # Run processing pipeline
        result = asyncio.run(process_content(content_id))
        return {"status": "success", "content_id": content_id}
    except Exception as e:
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

---

## 9. Testing

```python
# backend/tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from app.config import settings
from app.db.postgres import get_db

# Test database
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_secondbrain"

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with AsyncSession(engine) as session:
        yield session

# backend/tests/test_routers/test_practice.py

def test_create_session(client):
    response = client.post(
        "/api/practice/session",
        params={"duration_minutes": 15}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "items" in data
```

---

## 10. Related Documents

- `07_frontend_application.md` — Frontend consuming these APIs
- `09_data_models.md` — Full Pydantic and database models
- `05_learning_system.md` — Practice and review logic

