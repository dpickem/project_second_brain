# Backend API Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: January 2026  
> **Target Phase**: Completion of Backend API (~10% remaining)  
> **Design Docs**: `design_docs/06_backend_api.md`

---

## 1. Executive Summary

This document provides an implementation plan for completing the Backend API. The backend is approximately **90% complete**, with all major routers implemented. This plan covers the remaining work:

1. **Knowledge Router Enhancements** — Semantic search, connection queries, topic hierarchy
2. **Analytics Router Additions** — Time investment tracking, practice streaks
3. **Assistant Router** — Chat interface with knowledge graph context (Phase 11)
4. **Production Hardening** — Rate limiting, observability, error handling

### Implementation Status

| Component | Status | Effort | Priority |
|-----------|--------|--------|----------|
| Knowledge Search (`/api/knowledge/search`) | ⬜ Not Started | 2-3 days | High |
| Knowledge Connections (`/api/knowledge/connections`) | ⬜ Not Started | 1 day | Medium |
| Topic Hierarchy (`/api/knowledge/topics`) | ⬜ Not Started | 1-2 days | Medium |
| Time Investment Analytics | ⬜ Not Started | 1-2 days | Low |
| Practice Streak Tracking | ⬜ Not Started | 1 day | Low |
| Assistant Router (Phase 11) | ⬜ Not Started | 5-7 days | Future |
| Rate Limiting Middleware | ⬜ Not Started | 0.5 days | Low |
| Enhanced Error Handling | 🟡 Partial | 1 day | Medium |

**Total Remaining Effort**: ~2 weeks (excluding Phase 9 Assistant)

### What's Already Implemented ✅

The following is complete and tested:

- **9 Routers**: health, capture, ingestion, processing, vault, knowledge (partial), practice, review, analytics
- **53 Endpoints**: Full CRUD operations across all domains
- **7 Service Modules**: learning/, processing/, obsidian/, knowledge_graph/, llm/, scheduler, queue
- **6 Ingestion Pipelines**: raindrop, github, pdf, book_ocr, voice, web_article
- **Full Test Coverage**: Unit tests + integration tests with DB safety checks

---

## 2. Prerequisites

### 2.1 Existing Infrastructure ✅

All infrastructure is already in place:

- [x] FastAPI application with lifespan management
- [x] PostgreSQL with SQLAlchemy async
- [x] Neo4j with async client
- [x] Redis for caching and Celery
- [x] Alembic migrations (8 versions)
- [x] LiteLLM for unified LLM access
- [x] Comprehensive test suite

### 2.2 Dependencies for New Features

```txt
# Additional requirements for semantic search
sentence-transformers>=2.2.0    # Local embeddings (optional)
# OR use existing LiteLLM for OpenAI embeddings

# For rate limiting (optional)
slowapi>=0.1.9                  # Rate limiting middleware
```

### 2.3 Knowledge Graph Schema Requirements

For semantic search and connections to work effectively, ensure Neo4j has:

```cypher
-- Vector index for semantic search (if using embeddings)
CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS
FOR (c:Concept) ON c.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS FOR (s:Source) ON (s.title)
CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)
CREATE INDEX IF NOT EXISTS FOR (t:Topic) ON (t.path)
```

---

## 3. Implementation Phases

### Phase A: Knowledge Router Completion (Days 1-5)

#### Task A.1: Semantic Search Endpoint

**Purpose**: Enable natural language search across the knowledge base using embeddings.

**File**: `backend/app/routers/knowledge.py`

```python
# Add to existing knowledge.py

from typing import Optional
from pydantic import BaseModel, Field

class SearchResult(BaseModel):
    """Search result with relevance score."""
    id: str
    node_type: str  # Source, Concept, Topic
    title: str
    summary: Optional[str] = None
    score: float = Field(ge=0, le=1)
    highlights: list[str] = []  # Matching snippets

class SearchRequest(BaseModel):
    """Search query parameters."""
    query: str = Field(min_length=1, max_length=500)
    node_types: list[str] = ["Source", "Concept"]
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0, le=1)

class SearchResponse(BaseModel):
    """Search results."""
    query: str
    results: list[SearchResult]
    total: int
    search_time_ms: float


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
) -> SearchResponse:
    """
    Semantic search across knowledge base.
    
    Uses embeddings to find semantically similar content,
    not just keyword matching. Searches across Sources,
    Concepts, and Topics.
    
    Args:
        request: Search query and filters
        
    Returns:
        Ranked search results with relevance scores
    """
    import time
    start = time.time()
    
    # Implementation options:
    # 1. Neo4j vector search (if embeddings stored)
    # 2. Full-text search with Neo4j (simpler)
    # 3. External embedding service + Neo4j lookup
    
    # Option 2: Full-text search (simplest to implement first)
    query = f"""
    CALL db.index.fulltext.queryNodes('searchIndex', $query)
    YIELD node, score
    WHERE score >= $min_score
    AND any(label IN labels(node) WHERE label IN $node_types)
    RETURN node, labels(node) as labels, score
    ORDER BY score DESC
    LIMIT $limit
    """
    
    # ... execute query and map results
    
    elapsed = (time.time() - start) * 1000
    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        search_time_ms=elapsed
    )
```

**Service Layer**: `backend/app/services/knowledge_graph/search.py`

```python
"""Knowledge graph search service."""

from typing import Optional
from app.services.llm.client import get_embedding
from app.services.knowledge_graph.client import get_neo4j_client


class KnowledgeSearchService:
    """
    Search service for the knowledge graph.
    
    Supports multiple search strategies:
    1. Full-text search (fast, keyword-based)
    2. Vector similarity search (semantic, requires embeddings)
    3. Hybrid search (combines both)
    """
    
    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client
    
    async def full_text_search(
        self,
        query: str,
        node_types: list[str],
        limit: int = 20,
        min_score: float = 0.5
    ) -> list[dict]:
        """
        Full-text search using Neo4j's built-in index.
        
        Requires fulltext index to be created:
        CREATE FULLTEXT INDEX searchIndex FOR (n:Source|Concept|Topic) 
        ON EACH [n.title, n.name, n.summary, n.content]
        """
        cypher = """
        CALL db.index.fulltext.queryNodes('searchIndex', $query)
        YIELD node, score
        WHERE score >= $min_score
        RETURN node, labels(node) as labels, score
        ORDER BY score DESC
        LIMIT $limit
        """
        return await self.neo4j.query(cypher, {
            "query": query,
            "min_score": min_score,
            "limit": limit
        })
    
    async def vector_search(
        self,
        query: str,
        node_types: list[str],
        limit: int = 20,
        min_score: float = 0.7
    ) -> list[dict]:
        """
        Vector similarity search using embeddings.
        
        Generates embedding for query and finds similar nodes.
        Requires nodes to have 'embedding' property.
        """
        # Get query embedding
        query_embedding = await get_embedding(query)
        
        cypher = """
        CALL db.index.vector.queryNodes('concept_embeddings', $limit, $embedding)
        YIELD node, score
        WHERE score >= $min_score
        RETURN node, labels(node) as labels, score
        ORDER BY score DESC
        """
        return await self.neo4j.query(cypher, {
            "embedding": query_embedding,
            "min_score": min_score,
            "limit": limit
        })
```

**Migration Required**: Create fulltext index

```python
# backend/alembic/versions/009_add_fulltext_search_index.py

"""Add fulltext search index to Neo4j

Note: This is a Neo4j operation, not PostgreSQL.
Run manually or via startup script.
"""

NEO4J_SETUP = """
-- Create fulltext index for search
CREATE FULLTEXT INDEX searchIndex IF NOT EXISTS
FOR (n:Source|Concept|Topic)
ON EACH [n.title, n.name, n.summary, n.content]
"""
```

---

#### Task A.2: Connection Queries Endpoint

**Purpose**: Find related content through graph relationships.

```python
# Add to knowledge.py

class ConnectionType(str, Enum):
    """Types of connections in the knowledge graph."""
    REFERENCES = "REFERENCES"
    RELATES_TO = "RELATES_TO"
    PREREQUISITE = "PREREQUISITE"
    BUILDS_ON = "BUILDS_ON"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"

class Connection(BaseModel):
    """A connection between two nodes."""
    source_id: str
    target_id: str
    target_title: str
    target_type: str
    relationship: str
    strength: float = Field(ge=0, le=1)
    context: Optional[str] = None  # Why they're connected

class ConnectionsResponse(BaseModel):
    """Connections for a node."""
    node_id: str
    incoming: list[Connection]
    outgoing: list[Connection]
    total: int


@router.get("/connections/{node_id}", response_model=ConnectionsResponse)
async def get_connections(
    node_id: str,
    relationship_types: Optional[list[ConnectionType]] = Query(None),
    direction: str = Query("both", regex="^(incoming|outgoing|both)$"),
    limit: int = Query(20, ge=1, le=100),
    min_strength: float = Query(0.0, ge=0, le=1),
) -> ConnectionsResponse:
    """
    Get connections for a specific node.
    
    Returns incoming and outgoing relationships,
    optionally filtered by type and strength.
    
    Args:
        node_id: The node to get connections for
        relationship_types: Filter by relationship types
        direction: incoming, outgoing, or both
        limit: Maximum connections per direction
        min_strength: Minimum relationship strength
        
    Returns:
        Lists of incoming and outgoing connections
    """
    # Build Cypher query based on direction
    incoming_query = """
    MATCH (source)-[r]->(target)
    WHERE target.id = $node_id
    AND (r.strength IS NULL OR r.strength >= $min_strength)
    RETURN source, type(r) as rel_type, r.strength as strength, r.context as context
    ORDER BY r.strength DESC NULLS LAST
    LIMIT $limit
    """
    
    outgoing_query = """
    MATCH (source)-[r]->(target)
    WHERE source.id = $node_id
    AND (r.strength IS NULL OR r.strength >= $min_strength)
    RETURN target, type(r) as rel_type, r.strength as strength, r.context as context
    ORDER BY r.strength DESC NULLS LAST
    LIMIT $limit
    """
    
    # ... execute queries and build response
```

---

#### Task A.3: Topic Hierarchy Endpoint

**Purpose**: Provide hierarchical navigation of topics.

```python
# Add to knowledge.py

class TopicNode(BaseModel):
    """A node in the topic hierarchy."""
    path: str  # e.g., "ml/deep-learning/transformers"
    name: str  # e.g., "transformers"
    depth: int
    content_count: int
    children: list["TopicNode"] = []
    mastery_score: Optional[float] = None  # If user has mastery data

class TopicHierarchyResponse(BaseModel):
    """Full topic hierarchy."""
    roots: list[TopicNode]
    total_topics: int
    max_depth: int


@router.get("/topics", response_model=TopicHierarchyResponse)
async def get_topic_hierarchy(
    include_mastery: bool = Query(False, description="Include mastery scores"),
    min_content: int = Query(0, description="Min content count to include"),
) -> TopicHierarchyResponse:
    """
    Get hierarchical topic structure.
    
    Topics are organized in a tree based on their path:
    - ml/
      - ml/deep-learning/
        - ml/deep-learning/transformers/
      - ml/reinfortic-learning/
    
    Args:
        include_mastery: Include user mastery scores per topic
        min_content: Filter out topics with fewer items
        
    Returns:
        Hierarchical topic tree with content counts
    """
    # Query all topics
    query = """
    MATCH (t:Topic)
    OPTIONAL MATCH (t)<-[:HAS_TOPIC]-(s:Source)
    WITH t, count(s) as content_count
    WHERE content_count >= $min_content
    RETURN t.path as path, t.name as name, content_count
    ORDER BY t.path
    """
    
    topics = await neo4j.query(query, {"min_content": min_content})
    
    # Build hierarchy from flat list
    hierarchy = build_topic_tree(topics)
    
    if include_mastery:
        # Enrich with mastery scores
        await enrich_with_mastery(hierarchy)
    
    return TopicHierarchyResponse(
        roots=hierarchy,
        total_topics=len(topics),
        max_depth=max(t["path"].count("/") for t in topics) if topics else 0
    )


def build_topic_tree(flat_topics: list[dict]) -> list[TopicNode]:
    """
    Build tree structure from flat topic list.
    
    Algorithm:
    1. Sort by path (ensures parents come before children)
    2. Create nodes for each topic
    3. Link children to parents based on path prefix
    """
    nodes = {}
    roots = []
    
    for t in sorted(flat_topics, key=lambda x: x["path"]):
        path = t["path"]
        parts = path.strip("/").split("/")
        depth = len(parts) - 1
        
        node = TopicNode(
            path=path,
            name=parts[-1],
            depth=depth,
            content_count=t["content_count"],
            children=[]
        )
        nodes[path] = node
        
        # Find parent
        if depth == 0:
            roots.append(node)
        else:
            parent_path = "/".join(parts[:-1])
            if parent_path in nodes:
                nodes[parent_path].children.append(node)
            else:
                # Orphan - add to roots
                roots.append(node)
    
    return roots
```

---

### Phase B: Analytics Enhancements (Days 6-8)

#### Task B.1: Time Investment Tracking

**Purpose**: Track time spent learning by topic and activity type.

**Database Schema Addition**:

```python
# Add to models_learning.py

class LearningTimeLog(Base):
    """
    Tracks time spent on learning activities.
    
    Logged automatically when:
    - Practice sessions end (session duration)
    - Review sessions end (time on cards)
    - Content is read (if frontend tracks)
    """
    __tablename__ = "learning_time_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # What was being learned
    topic: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    content_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content.id"))
    
    # Activity type
    activity_type: Mapped[str] = mapped_column(String(50))  # review, practice, reading
    
    # Time tracking
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    
    # Metadata
    items_completed: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("practice_sessions.id"))
```

**Endpoint Implementation**:

```python
# Add to analytics.py

class TimeInvestmentPeriod(BaseModel):
    """Time investment for a period."""
    period_start: datetime
    period_end: datetime
    total_minutes: float
    by_topic: dict[str, float]  # topic -> minutes
    by_activity: dict[str, float]  # activity_type -> minutes

class TimeInvestmentResponse(BaseModel):
    """Time investment summary."""
    total_minutes: float
    periods: list[TimeInvestmentPeriod]
    top_topics: list[tuple[str, float]]  # (topic, minutes)
    daily_average: float
    trend: str  # "increasing", "decreasing", "stable"


@router.get("/time-investment", response_model=TimeInvestmentResponse)
async def get_time_investment(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    group_by: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
) -> TimeInvestmentResponse:
    """
    Get time investment breakdown.
    
    Shows how much time has been spent learning,
    broken down by topic and activity type.
    
    Args:
        period: Time period to analyze
        group_by: How to group the data
        
    Returns:
        Time investment summary with trends
    """
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = calculate_start_date(period, end_date)
    
    # Query time logs
    query = select(LearningTimeLog).where(
        LearningTimeLog.started_at >= start_date,
        LearningTimeLog.ended_at <= end_date
    )
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Aggregate by period
    periods = aggregate_by_period(logs, group_by)
    
    # Calculate totals and trends
    total_minutes = sum(log.duration_seconds for log in logs) / 60
    daily_average = total_minutes / max((end_date - start_date).days, 1)
    trend = calculate_trend(periods)
    
    return TimeInvestmentResponse(
        total_minutes=total_minutes,
        periods=periods,
        top_topics=get_top_topics(logs, limit=10),
        daily_average=daily_average,
        trend=trend
    )
```

---

#### Task B.2: Practice Streak Tracking

**Purpose**: Gamification through streak tracking.

```python
# Add to analytics.py

class StreakData(BaseModel):
    """Practice streak information."""
    current_streak: int  # Days
    longest_streak: int
    streak_start: Optional[date]
    last_practice: Optional[date]
    is_active_today: bool
    days_this_week: int
    days_this_month: int
    # Milestones
    milestones_reached: list[int]  # e.g., [7, 30, 100]
    next_milestone: Optional[int]


@router.get("/streak", response_model=StreakData)
async def get_streak_data(
    db: AsyncSession = Depends(get_db),
) -> StreakData:
    """
    Get practice streak information.
    
    A streak is maintained by practicing at least once per day.
    Streaks reset if a day is missed.
    
    Returns:
        Current streak, history, and milestones
    """
    # Get all practice days
    query = select(
        func.date(PracticeSession.started_at).label("practice_date")
    ).distinct().order_by(
        func.date(PracticeSession.started_at).desc()
    )
    
    result = await db.execute(query)
    practice_dates = [row.practice_date for row in result]
    
    if not practice_dates:
        return StreakData(
            current_streak=0,
            longest_streak=0,
            streak_start=None,
            last_practice=None,
            is_active_today=False,
            days_this_week=0,
            days_this_month=0,
            milestones_reached=[],
            next_milestone=7
        )
    
    today = date.today()
    
    # Calculate current streak
    current_streak = 0
    streak_start = None
    
    for i, d in enumerate(practice_dates):
        expected_date = today - timedelta(days=i)
        if d == expected_date:
            current_streak += 1
            streak_start = d
        elif d == expected_date - timedelta(days=1) and i == 0:
            # Yesterday counts if today not done yet
            current_streak += 1
            streak_start = d
        else:
            break
    
    # Calculate longest streak (similar logic, full scan)
    longest_streak = calculate_longest_streak(practice_dates)
    
    # Milestones
    milestones = [7, 14, 30, 60, 90, 180, 365]
    reached = [m for m in milestones if longest_streak >= m]
    next_milestone = next((m for m in milestones if m > current_streak), None)
    
    return StreakData(
        current_streak=current_streak,
        longest_streak=longest_streak,
        streak_start=streak_start,
        last_practice=practice_dates[0] if practice_dates else None,
        is_active_today=practice_dates[0] == today if practice_dates else False,
        days_this_week=count_days_in_period(practice_dates, 7),
        days_this_month=count_days_in_period(practice_dates, 30),
        milestones_reached=reached,
        next_milestone=next_milestone
    )
```

---

### Phase C: Production Hardening (Days 9-10)

#### Task C.1: Rate Limiting Middleware

**Purpose**: Prevent abuse and ensure fair resource usage.

```python
# backend/app/middleware/rate_limit.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations by endpoint type
RATE_LIMITS = {
    "default": "100/minute",
    "llm_heavy": "10/minute",      # Endpoints that call LLMs
    "search": "30/minute",          # Search endpoints
    "capture": "20/minute",         # File upload endpoints
    "auth": "5/minute",             # Login attempts (future)
}


def setup_rate_limiting(app):
    """Configure rate limiting on the FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Usage in routers:
# @router.post("/exercise/generate")
# @limiter.limit(RATE_LIMITS["llm_heavy"])
# async def generate_exercise(request: Request, ...):
```

---

#### Task C.2: Enhanced Error Handling

**Purpose**: Consistent, informative error responses.

```python
# backend/app/middleware/error_handling.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from uuid import uuid4

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    message: str
    error_id: str  # For log correlation
    details: Optional[dict] = None
    timestamp: datetime


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    - Catches unhandled exceptions
    - Logs with correlation ID
    - Returns consistent error format
    - Hides internal details in production
    """
    
    async def dispatch(self, request: Request, call_next):
        error_id = str(uuid4())[:8]
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
            
        except Exception as e:
            # Log full traceback
            logger.error(
                f"[{error_id}] Unhandled error: {type(e).__name__}: {e}",
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc()
                }
            )
            
            # Return sanitized response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "error_id": error_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )


# Custom exceptions for better error handling
class ServiceError(Exception):
    """Base exception for service errors."""
    status_code: int = 500
    error_code: str = "service_error"
    
class LLMError(ServiceError):
    """LLM provider error."""
    status_code = 502
    error_code = "llm_error"

class GraphQueryError(ServiceError):
    """Neo4j query error."""
    status_code = 500
    error_code = "graph_error"

class ValidationError(ServiceError):
    """Data validation error."""
    status_code = 422
    error_code = "validation_error"
```

---

### Phase D: Assistant Router (Phase 11 - Future)

> **Note**: This is planned for Phase 11 of the overall roadmap. Including here for completeness.
> The assistant leverages the existing Neo4j knowledge graph with vector embeddings for context retrieval.

#### Task D.1: Chat Endpoint with Knowledge Graph Context

**Purpose**: Conversational interface that queries the knowledge graph for relevant context.

```python
# backend/app/routers/assistant.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.services.assistant.chat import ChatService

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str = Field(regex="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context_mode: str = "auto"  # auto, knowledge, none
    stream: bool = False

class ChatResponse(BaseModel):
    message: ChatMessage
    sources: list[dict] = []  # Referenced knowledge from graph
    suggestions: list[str] = []  # Follow-up questions


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Chat with the learning assistant.
    
    The assistant queries the Neo4j knowledge graph (with vector embeddings)
    to find relevant context for answering questions. It can:
    - Answer questions about your notes
    - Explain connections between concepts
    - Suggest related topics to explore
    - Generate practice questions
    
    Args:
        request: Chat messages and configuration
        
    Returns:
        Assistant response with sources from knowledge graph
    """
    if request.stream:
        return EventSourceResponse(
            chat_service.stream_response(request.messages)
        )
    
    response = await chat_service.generate_response(
        messages=request.messages,
        context_mode=request.context_mode
    )
    
    return response


@router.get("/suggestions")
async def get_suggestions(
    context: Optional[str] = Query(None),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Get proactive learning suggestions.
    
    Based on:
    - Recent activity
    - Weak spots in mastery
    - Unexplored connections in the graph
    - Upcoming review items
    """
    suggestions = await chat_service.generate_suggestions(context)
    return {"suggestions": suggestions}


@router.post("/explain-connection")
async def explain_connection(
    source_id: str,
    target_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Get LLM explanation of connection between two items.
    
    Queries the knowledge graph for the relationship path
    and generates a natural language explanation.
    """
    explanation = await chat_service.explain_connection(source_id, target_id)
    return {"explanation": explanation}
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

```python
# tests/unit/test_knowledge_search.py

import pytest
from app.services.knowledge_graph.search import KnowledgeSearchService


class TestKnowledgeSearch:
    """Tests for knowledge search service."""
    
    @pytest.fixture
    def search_service(self, mock_neo4j):
        return KnowledgeSearchService(mock_neo4j)
    
    async def test_full_text_search_returns_results(self, search_service):
        """Full text search finds matching nodes."""
        results = await search_service.full_text_search(
            query="machine learning",
            node_types=["Source", "Concept"],
            limit=10
        )
        
        assert len(results) > 0
        assert all(r["score"] >= 0 for r in results)
    
    async def test_search_respects_min_score(self, search_service):
        """Results below min_score are filtered."""
        results = await search_service.full_text_search(
            query="transformer",
            node_types=["Concept"],
            min_score=0.8
        )
        
        assert all(r["score"] >= 0.8 for r in results)
```

### 4.2 Integration Tests

```python
# tests/integration/test_knowledge_api.py

class TestKnowledgeSearchEndpoint:
    """Integration tests for /api/knowledge/search."""
    
    async def test_search_endpoint_returns_results(self, async_test_client):
        """Search endpoint returns valid results."""
        response = await async_test_client.post(
            "/api/knowledge/search",
            json={
                "query": "neural networks",
                "node_types": ["Source", "Concept"],
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "search_time_ms" in data
    
    async def test_search_validates_query_length(self, async_test_client):
        """Search rejects empty queries."""
        response = await async_test_client.post(
            "/api/knowledge/search",
            json={"query": "", "limit": 5}
        )
        
        assert response.status_code == 422
```

---

## 5. Deployment Checklist

### Before Deploying Phase A-B:

- [ ] Neo4j fulltext index created
- [ ] Database migration for time logs applied
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] API documentation updated (OpenAPI)

### Before Deploying Phase C:

- [ ] Rate limits configured appropriately
- [ ] Error logging connected to monitoring
- [ ] Load testing performed
- [ ] Rollback plan documented

### Before Deploying Phase D (Assistant):

- [ ] Knowledge graph vector search tested
- [ ] Streaming responses verified
- [ ] Token usage monitoring in place
- [ ] Prompt injection safeguards

---

## 6. Related Documents

- `design_docs/06_backend_api.md` — API design specification
- `design_docs/09_data_models.md` — Data model reference
- `implementation_plan/05_learning_system_implementation.md` — Learning system details
- `tech_debt.md` — Technical debt tracking

