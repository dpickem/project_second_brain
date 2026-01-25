# Backend API Implementation Plan

> **Document Status**: Implementation Plan (Updated January 2026)  
> **Created**: January 2026  
> **Last Updated**: January 7, 2026  
> **Target Phase**: ✅ Backend API Core Complete  
> **Design Docs**: `design_docs/06_backend_api.md`

---

## 1. Executive Summary

This document provides an implementation plan for the Backend API. The backend core is now **~98% complete**, with all major routers and production hardening implemented. Only the Assistant Router (Phase 11) remains for future work.

### Completed Work ✅

1. **Knowledge Router Enhancements** — Semantic search, connection queries, topic hierarchy
2. **Analytics Router Additions** — Time investment tracking, practice streaks
3. **Production Hardening** — Rate limiting, observability, error handling

### Remaining Work

1. **Assistant Router** — Chat interface with knowledge graph context (Phase 11 - Future)

### Implementation Status

| Component | Status | Effort | Priority |
|-----------|--------|--------|----------|
| Knowledge Search (`/api/knowledge/search`) | ✅ Complete | — | — |
| Knowledge Connections (`/api/knowledge/connections`) | ✅ Complete | — | — |
| Topic Hierarchy (`/api/knowledge/topics`) | ✅ Complete | — | — |
| Time Investment Analytics | ✅ Complete | — | — |
| Practice Streak Tracking | ✅ Complete | — | — |
| Rate Limiting Middleware | ✅ Complete | — | — |
| Enhanced Error Handling | ✅ Complete | — | — |
| Assistant Router (Phase 11) | ⬜ Not Started | 5-7 days | Future |

**Remaining Effort**: ~1 week (Assistant Router only, planned for Phase 11)

### What's Already Implemented ✅

The following is complete and tested:

- **10 Routers**: health, capture, ingestion, processing, vault, knowledge, practice, review, analytics (all complete)
- **60+ Endpoints**: Full CRUD operations across all domains including:
  - Knowledge search (keyword, full-text, vector, hybrid)
  - Graph connections and topic hierarchy
  - Time investment analytics with trends
  - Practice streak tracking with milestones
- **7 Service Modules**: learning/, processing/, obsidian/, knowledge_graph/, llm/, scheduler, queue
- **6 Ingestion Pipelines**: raindrop, github, pdf, book_ocr, voice, web_article
- **Production Middleware**: Rate limiting (SlowAPI), enhanced error handling with correlation IDs
- **Full Test Coverage**: Unit tests + integration tests with DB safety checks
- **Database Migrations**: 9 Alembic migrations including learning_time_logs table

---

## 2. Prerequisites

### 2.1 Infrastructure ✅ COMPLETE

All infrastructure is in place and operational:

- [x] FastAPI application with lifespan management
- [x] PostgreSQL with SQLAlchemy async
- [x] Neo4j with async client
- [x] Redis for caching and Celery
- [x] Alembic migrations (9 versions including learning_time_logs)
- [x] LiteLLM for unified LLM access
- [x] Comprehensive test suite
- [x] Rate limiting middleware (SlowAPI)
- [x] Error handling middleware

### 2.2 Dependencies ✅ COMPLETE

All required dependencies are in `backend/requirements.txt`:

```txt
# Rate limiting
slowapi>=0.1.9                  # Rate limiting middleware

# LLM embeddings (for vector search)
# Uses existing LiteLLM integration for OpenAI/Anthropic embeddings

# For future Assistant Router (Phase 11)
sse-starlette>=1.6.0            # Server-Sent Events for streaming (to be added)
```

### 2.3 Knowledge Graph Schema

Neo4j indexes are managed by the knowledge graph service. The search service gracefully handles missing indexes:

```cypher
-- Fulltext index for text search (optional, falls back to CONTAINS)
CREATE FULLTEXT INDEX searchIndex IF NOT EXISTS
FOR (n:Content|Concept|Note)
ON EACH [n.title, n.name, n.summary, n.content]

-- Vector index for semantic search (optional, per node type)
CREATE VECTOR INDEX content_embedding_index IF NOT EXISTS
FOR (c:Content) ON c.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}

CREATE VECTOR INDEX concept_embedding_index IF NOT EXISTS
FOR (c:Concept) ON c.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
```

**Graceful Degradation**: The `KnowledgeSearchService` automatically falls back:
1. Vector search → Full-text search → Keyword search
2. Missing fulltext index → Keyword (CONTAINS) matching

---

## 3. Implementation Phases

### Phase A: Knowledge Router Completion ✅ COMPLETE

#### Task A.1: Semantic Search Endpoint ✅

**Status**: Complete  
**File**: `backend/app/routers/knowledge.py`  
**Service**: `backend/app/services/knowledge_graph/search.py`

The semantic search implementation supports multiple search strategies with automatic fallback:

1. **Vector Search** — Uses LLM embeddings for semantic similarity (requires LLM client)
2. **Full-text Search** — Uses Neo4j's Lucene-based fulltext index
3. **Keyword Search** — CONTAINS matching fallback when fulltext index unavailable
4. **Hybrid Search** — Combines text and vector results with weighted scoring

**Endpoint**: `POST /api/knowledge/search`

```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    node_types: list[str] = Field(default=["Content", "Concept"])
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0, le=1)
    use_vector: bool = Field(default=True, description="Use vector search when available")

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    search_time_ms: float
```

**Search Service Implementation** (`KnowledgeSearchService`):

- `keyword_search()` — Basic CONTAINS matching on title, name, summary
- `full_text_search()` — Lucene fulltext with automatic fallback to keyword
- `vector_search()` — Embedding-based similarity (requires LLM client)
- `semantic_search()` — Unified search with automatic fallback chain
- `hybrid_search()` — Weighted combination of text + vector results

**Unit Tests**: `backend/tests/unit/test_knowledge_search.py`

---

#### Task A.2: Connection Queries Endpoint ✅

**Status**: Complete  
**File**: `backend/app/routers/knowledge.py`

**Endpoint**: `GET /api/knowledge/connections/{node_id}`

Returns both incoming and outgoing relationships for a node with direction filtering.

```python
class NodeConnection(BaseModel):
    source_id: str
    target_id: str
    target_title: str
    target_type: str
    relationship: str
    strength: float = Field(default=1.0, ge=0, le=1)
    context: Optional[str] = None

class ConnectionsResponse(BaseModel):
    node_id: str
    incoming: list[NodeConnection]
    outgoing: list[NodeConnection]
    total: int
```

**Query Parameters**:
- `direction`: Filter by `incoming`, `outgoing`, or `both` (default)
- `limit`: Maximum connections per direction (1-100, default 20)

**Enum**: `ConnectionDirection` in `app/enums/knowledge.py`

---

#### Task A.3: Topic Hierarchy Endpoint ✅

**Status**: Complete  
**File**: `backend/app/routers/knowledge.py`

**Endpoint**: `GET /api/knowledge/topics`

Provides hierarchical navigation of topics organized in a tree based on slash-separated paths.

```python
class TopicNode(BaseModel):
    path: str           # e.g., "ml/deep-learning/transformers"
    name: str           # e.g., "transformers"
    depth: int
    content_count: int
    children: list["TopicNode"] = Field(default_factory=list)
    mastery_score: Optional[float] = None

class TopicHierarchyResponse(BaseModel):
    roots: list[TopicNode]
    total_topics: int
    max_depth: int
```

**Helper Function**: `build_topic_tree()` in `app/services/knowledge_graph/__init__.py`
- Builds tree structure from flat topic list
- Handles orphan topics (missing parents)
- Unit tested in `test_knowledge_search.py`

---

### Phase B: Analytics Enhancements ✅ COMPLETE

#### Task B.1: Time Investment Tracking ✅

**Status**: Complete  
**Database Model**: `backend/app/db/models_learning.py` (`LearningTimeLog`)  
**Migration**: `backend/alembic/versions/009_add_learning_time_logs.py`  
**Endpoint**: `GET /api/analytics/time-investment`  
**Service**: `backend/app/services/learning/mastery_service.py`

The `LearningTimeLog` model tracks time spent on learning activities:

```python
class LearningTimeLog(Base):
    __tablename__ = "learning_time_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    content_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content.id"))
    activity_type: Mapped[str] = mapped_column(String(50), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    items_completed: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("practice_sessions.id"))
```

**API Response Models** (in `app/models/learning.py`):

```python
class TimeInvestmentPeriod(BaseModel):
    period_start: datetime
    period_end: datetime
    total_minutes: float
    by_topic: dict[str, float] = Field(default_factory=dict)
    by_activity: dict[str, float] = Field(default_factory=dict)

class TimeInvestmentResponse(BaseModel):
    total_minutes: float
    periods: list[TimeInvestmentPeriod]
    top_topics: list[tuple[str, float]]
    daily_average: float
    trend: str  # "increasing", "decreasing", "stable"
```

**Query Parameters**:
- `period`: `TimePeriod` enum (WEEK, MONTH, QUARTER, YEAR, ALL)
- `group_by`: `GroupBy` enum (DAY, WEEK, MONTH)

**Additional Endpoint**: `POST /api/analytics/time-log` — Log time spent on learning

**Unit Tests**: `backend/tests/unit/test_analytics_endpoints.py`

---

#### Task B.2: Practice Streak Tracking ✅

**Status**: Complete  
**Endpoint**: `GET /api/analytics/streak`  
**Service**: `backend/app/services/learning/mastery_service.py`

```python
class StreakData(BaseModel):
    current_streak: int
    longest_streak: int
    streak_start: Optional[date] = None
    last_practice: Optional[date] = None
    is_active_today: bool
    days_this_week: int
    days_this_month: int
    milestones_reached: list[int] = Field(default_factory=list)
    next_milestone: Optional[int] = None
```

**Service Static Methods** (in `MasteryService`):
- `_calculate_longest_streak()` — Find longest consecutive day sequence
- `_count_days_in_period()` — Count practice days within a time window
- `_calculate_time_trend()` — Determine trend (stable, increasing, decreasing)
- `_calculate_period_start()` — Map TimePeriod enum to start date

**Milestones**: 7, 14, 30, 60, 90, 180, 365 days

**Unit Tests**: `backend/tests/unit/test_analytics_endpoints.py`

---

### Phase C: Production Hardening ✅ COMPLETE

#### Task C.1: Rate Limiting Middleware ✅

**Status**: Complete  
**File**: `backend/app/middleware/rate_limit.py`

Rate limiting implemented using SlowAPI with configurable limits per endpoint type:

#### Task C.3: API Contract Enforcement ✅

**Status**: Complete (January 2026)  
**Files**:
- `backend/app/models/base.py` — Strict Pydantic base classes
- `backend/tests/unit/test_openapi_contract.py` — OpenAPI schema tests
- `backend/tests/integration/test_api_contract.py` — Integration contract tests
- `frontend/src/api/typed-client.js` — OpenAPI-typed frontend client
- `frontend/scripts/generate-api-types.js` — Type generation script

**Problem Solved**: Frontend/backend parameter mismatches (typos, wrong types) discovered only at runtime.

**Solution**: Multi-layer API contract enforcement:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API CONTRACT ENFORCEMENT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPILE-TIME (Frontend)          RUNTIME (Backend)        CI/CD            │
│  ─────────────────────────        ─────────────────        ──────           │
│  TypeScript types from            StrictRequest base       OpenAPI          │
│  OpenAPI schema                   (extra="forbid")         snapshot tests   │
│                                                                              │
│  npm run generate:api-types       422 on unknown fields    Contract tests   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Backend: Strict Pydantic Models**

Base classes in `app/models/base.py`:

```python
from app.models.base import StrictRequest, StrictResponse

class SearchRequest(StrictRequest):  # Rejects unknown fields (422)
    query: str
    limit: int = 20

class SearchResponse(StrictResponse):  # Lenient for responses
    results: list[SearchResult]
```

Models updated to use `StrictRequest`:
- `SearchRequest` (knowledge)
- `ChatRequest`, `ConversationUpdateRequest`, `QuizRequest` (assistant)
- `CardReviewRequest`, `SessionCreateRequest`, `LogTimeRequest` (learning)
- `TriggerProcessingRequest`, `ProcessingConfigRequest` (processing)

**Frontend: OpenAPI Type Generation**

```bash
# Generate TypeScript types from backend
npm run generate:api-types

# Check if schema changed (fails CI if unexpected)
npm run api:check
```

Typed API client (`frontend/src/api/typed-client.js`):

```javascript
import { api } from './api'

// Type-safe - catches typos at dev time
const { data } = await api.knowledge.search({ query: 'transformers' })
```

**Contract Tests (62 tests, all passing)**

Unit tests (`test_openapi_contract.py`):
- Schema structure validation
- Critical endpoint existence (22 endpoints verified)
- Parameter type validation
- Strict validation tests (extra field rejection)
- Response model verification
- Schema snapshot comparison (for breaking change detection)

Integration tests (`test_api_contract.py`):
- Wrong field name rejection (`maxResults` vs `limit`)
- Wrong HTTP method tests (POST vs GET)
- Query vs body parameter tests
- Missing required field tests
- Out-of-range validation tests
- Consistent error format tests

**Test Results**:
```
======================== 62 passed, 2 skipped in 17.87s ========================
```

**CI Integration Recommendation**:

```yaml
# .github/workflows/api-contract.yml
- name: Run contract tests
  run: pytest tests/unit/test_openapi_contract.py tests/integration/test_api_contract.py -v

- name: Check API types up to date
  run: npm run api:check
```

---

```python
# Rate limit types (from app/enums/api.py - RateLimitType enum)
RATE_LIMITS = {
    "DEFAULT": "100/minute",      # General API endpoints
    "LLM_HEAVY": "10/minute",     # Endpoints that call LLMs
    "SEARCH": "30/minute",        # Search endpoints
    "CAPTURE": "20/minute",       # File upload endpoints
    "AUTH": "5/minute",           # Login attempts (future)
    "GRAPH": "60/minute",         # Graph queries
    "ANALYTICS": "30/minute",     # Analytics endpoints
    "BATCH": "5/minute",          # Batch operations
}
```

**Features**:
- Uses `X-Forwarded-For` header when behind proxy/load balancer
- Falls back to direct IP address
- Configurable enable/disable via settings
- Convenience decorators: `@limit_llm`, `@limit_search`, `@limit_capture`

**Setup**:
```python
from app.middleware.rate_limit import setup_rate_limiting
setup_rate_limiting(app, enabled=True)
```

---

#### Task C.2: Enhanced Error Handling ✅

**Status**: Complete  
**File**: `backend/app/middleware/error_handling.py`

Comprehensive error handling with correlation IDs and custom exception classes:

```python
class ErrorResponse(BaseModel):
    error: str           # Error code (e.g., "internal_server_error")
    message: str         # Human-readable message
    error_id: str        # 8-char UUID for log correlation
    details: Optional[dict] = None  # Additional context (debug mode only)
    timestamp: datetime
```

**Custom Exception Classes**:
- `ServiceError` — Base exception with status_code and error_code
- `LLMError` — LLM provider errors (502)
- `GraphQueryError` — Neo4j query errors (500)
- `ValidationError` — Data validation errors (422)
- `NotFoundError` — Resource not found (404)
- `RateLimitError` — Rate limit exceeded (429)
- `AuthorizationError` — Permission denied (403)

**Middleware Features**:
- Catches unhandled exceptions with correlation ID
- Logs full traceback for debugging
- Returns sanitized responses in production
- Debug mode includes stack traces in response
- Uses ASGI middleware architecture (BaseHTTPMiddleware)

**Setup**:
```python
from app.middleware.error_handling import setup_error_handling
setup_error_handling(app, debug=settings.DEBUG)
```

**Helper Function**:
```python
from app.middleware.error_handling import create_error_response
response = create_error_response("custom_error", "Something went wrong", 400)
```

---

### Phase D: Assistant Router (Phase 11 - Future) ⬜ NOT STARTED

> **Note**: This is planned for Phase 11 of the overall roadmap. Including here for completeness.
> The assistant will leverage the existing Neo4j knowledge graph with vector embeddings for context retrieval.

**Status**: Not Started (Future Phase 11)  
**Estimated Effort**: 5-7 days  
**Prerequisites**:
- ✅ Knowledge graph with vector search (complete)
- ✅ LLM client integration (complete)
- ⬜ Streaming response infrastructure

#### Task D.1: Chat Endpoint with Knowledge Graph Context

**Purpose**: Conversational interface that queries the knowledge graph for relevant context.

**Planned Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/assistant/chat` | POST | Chat with knowledge-augmented assistant |
| `/api/assistant/suggestions` | GET | Proactive learning suggestions |
| `/api/assistant/explain-connection` | POST | Explain relationship between concepts |

**Planned Models**:

```python
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context_mode: str = "auto"  # auto, knowledge, none
    stream: bool = False

class ChatResponse(BaseModel):
    message: ChatMessage
    sources: list[dict] = []      # Referenced knowledge from graph
    suggestions: list[str] = []   # Follow-up questions
```

**Planned Features**:
- Answer questions about user's notes
- Explain connections between concepts
- Suggest related topics to explore
- Generate practice questions on demand
- Stream responses using SSE (Server-Sent Events)

**Dependencies to Add**:
```txt
sse-starlette>=1.6.0    # Server-Sent Events for streaming
```

---

## 4. Testing Strategy

### 4.1 Unit Tests ✅ COMPLETE

Tests are located in `backend/tests/unit/`:

**Knowledge Search Tests** (`test_knowledge_search.py`):
- `TestKnowledgeSearchService` — Tests for keyword, vector, and semantic search
  - `test_keyword_search_returns_results`
  - `test_keyword_search_empty_results`
  - `test_vector_search_requires_llm_client`
  - `test_semantic_search_prefers_vector`
  - `test_semantic_search_falls_back_to_text`
- `TestBuildTopicTree` — Tests for topic hierarchy building
  - Parametrized tests for single-level, nested, and orphan topics
  - Parent-child relationship verification

**Analytics Tests** (`test_analytics_endpoints.py`):
- `TestCalculateLongestStreak` — Streak calculation edge cases
- `TestCountDaysInPeriod` — Period windowing logic
- `TestCalculateTimeTrend` — Trend detection (stable/increasing/decreasing)
- `TestCalculatePeriodStart` — TimePeriod enum mapping
- `TestStreakDataModel` — Pydantic model validation
- `TestTimeInvestmentResponseModel` — Response model validation

**Test Helpers**:
- `AsyncIteratorMock` — Mock async iterator for Neo4j results
- `make_search_result()` — Factory for search result fixtures
- `make_time_period()` — Factory for time investment test data

### 4.2 Integration Tests

Integration tests in `backend/tests/integration/`:

**Knowledge API** (`test_knowledge_api.py`):
- Knowledge search endpoint validation
- Connection queries with real Neo4j
- Topic hierarchy responses

**API Contract Tests** (`test_api_contract.py`):
- `TestKnowledgeAPIContract` — Graph params, search body validation
- `TestCaptureAPIContract` — Form data, URL validation
- `TestAssistantAPIContract` — Chat message validation
- `TestPracticeAPIContract` — Review rating, session duration bounds
- `TestHTTPMethods` — Correct HTTP method enforcement
- `TestQueryVsBody` — Parameter location validation
- `TestResponseStructure` — Validation error format consistency

### 4.3 Contract Tests

Contract tests ensure API stability between frontend and backend:

**OpenAPI Contract Tests** (`tests/unit/test_openapi_contract.py`):
- `TestOpenAPIStructure` — Schema has required sections
- `TestCriticalEndpoints` — 22 critical endpoints exist
- `TestParameterTypes` — Request/response schemas correct
- `TestStrictValidation` — Unknown fields rejected (422)
- `TestValidationErrors` — Consistent error format
- `TestSchemaSnapshot` — Breaking change detection
- `TestResponseModels` — Endpoints have response_model

**Running Contract Tests**:
```bash
# Run all contract tests (62 tests)
pytest tests/unit/test_openapi_contract.py tests/integration/test_api_contract.py -v

# Create OpenAPI snapshot for CI
curl http://localhost:8000/openapi.json > tests/snapshots/openapi.json
```

---

## 5. Deployment Checklist

### Phase A-B (Knowledge & Analytics) ✅ COMPLETE

- [x] Neo4j fulltext index support (auto-fallback to keyword search if unavailable)
- [x] Database migration for time logs applied (migration 009)
- [x] Unit tests passing
- [x] Integration tests passing
- [x] API documentation updated (OpenAPI auto-generated)
- [x] Pydantic models with validation constraints

### Phase C (Production Hardening) ✅ COMPLETE

- [x] Rate limits configured via `RateLimitType` enum and settings
- [x] Error handling middleware with correlation IDs
- [x] Custom exception classes for different error types
- [x] Debug mode for development (includes stack traces)
- [x] Production mode sanitizes error responses

### Before Deploying Phase D (Assistant) ⬜ FUTURE

- [ ] Knowledge graph vector search tested at scale
- [ ] Streaming responses verified (SSE)
- [ ] Token usage monitoring in place
- [ ] Prompt injection safeguards implemented
- [ ] Rate limiting configured for chat endpoints
- [ ] Context window management for long conversations

---

## 6. Implementation Summary

### Completed (January 2026)

| Phase | Component | Files |
|-------|-----------|-------|
| A.1 | Semantic Search | `routers/knowledge.py`, `services/knowledge_graph/search.py` |
| A.2 | Connections API | `routers/knowledge.py`, `models/knowledge.py` |
| A.3 | Topic Hierarchy | `routers/knowledge.py`, `services/knowledge_graph/__init__.py` |
| B.1 | Time Investment | `routers/analytics.py`, `db/models_learning.py`, `alembic/versions/009_*.py` |
| B.2 | Streak Tracking | `routers/analytics.py`, `services/learning/mastery_service.py` |
| C.1 | Rate Limiting | `middleware/rate_limit.py`, `enums/api.py` |
| C.2 | Error Handling | `middleware/error_handling.py` |
| C.3 | API Contract | `models/base.py`, `tests/unit/test_openapi_contract.py`, `tests/integration/test_api_contract.py` |

### Key Design Decisions

1. **Search Fallback Chain**: Vector → Full-text → Keyword ensures search always works regardless of Neo4j index availability
2. **Static Service Methods**: Streak and trend calculations are static methods for easy unit testing
3. **Enum-based Rate Limits**: `RateLimitType` enum centralizes rate limit configuration
4. **Correlation IDs**: 8-character UUIDs in error responses enable log tracing
5. **Graceful Degradation**: Missing LLM client disables vector search but doesn't break the API
6. **Strict Request Validation**: `StrictRequest` base class with `extra="forbid"` catches frontend typos at request time
7. **OpenAPI Contract Testing**: Snapshot tests detect breaking changes; integration tests verify validation behavior

### Remaining Work

- **Phase D: Assistant Router** (Phase 11) — Conversational interface with knowledge graph context

---

## 7. Related Documents

- `design_docs/06_backend_api.md` — API design specification
- `implementation_plan/05_learning_system_implementation.md` — Learning system details
- `tech_debt.md` — Technical debt tracking

