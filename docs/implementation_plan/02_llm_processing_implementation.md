# LLM Processing Layer Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Target Phase**: Phase 3 (Weeks 7-10 per roadmap)  
> **Design Doc**: `design_docs/02_llm_processing_layer.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the LLM Processing Layer, which transforms raw ingested content (from the Ingestion Layer) into structured, connected knowledge. The pipeline performs seven processing stages: content analysis, summarization, concept extraction, tagging, connection discovery, follow-up task generation, and mastery question generation.

### LLM Strategy

**Provider-Agnostic Design via LiteLLM** — The processing pipeline uses [LiteLLM](https://docs.litellm.ai/) to provide a unified interface to 100+ LLM providers. Each processing stage can use a different model optimized for its task:

| Task | Default Model | Rationale |
|------|---------------|-----------|
| Classification/Analysis | `openai/gpt-4o-mini` | Cost-efficient for structured output |
| Summarization | `anthropic/claude-3-5-sonnet-20241022` | Excellent long-form understanding |
| Extraction | `openai/gpt-4o` | Strong structured JSON output |
| Connection Discovery | `anthropic/claude-3-5-sonnet-20241022` | Nuanced reasoning |
| Question Generation | `openai/gpt-4o` | Creative yet precise |
| Embeddings | `openai/text-embedding-3-small` | Cost-effective, high quality |

Models can be swapped via configuration without code changes.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Multi-provider LLM client | Frontend UI components |
| Content analysis & classification | Ingestion pipelines (Phase 2) |
| Multi-level summarization | Mobile PWA (separate plan) |
| Concept/entity extraction | Multi-user authentication |
| Hierarchical tagging from taxonomy | Production deployment |
| Embedding-based connection discovery | Real-time processing |
| Follow-up task generation | User feedback UI |
| Mastery question generation | |
| Obsidian note generation | |
| Neo4j knowledge graph population | |
| Processing queue integration | |

---

## 2. Prerequisites

### 2.1 Infrastructure (From Phase 1 & 2)

- [x] Docker Compose environment
- [x] Redis container for queue backend & caching
- [x] PostgreSQL container for metadata
- [x] FastAPI backend skeleton
- [x] Celery task queue (from Phase 2)
- [x] Neo4j container for knowledge graph
- [ ] Alembic migrations for processing tables

### 2.2 Dependencies to Install

```txt
# Add to backend/requirements.txt
litellm>=1.40.0            # Model-agnostic LLM interface
pydantic>=2.0              # Data validation (already installed)
jinja2>=3.1.0              # Template rendering for Obsidian notes
neo4j>=5.0.0               # Neo4j driver
tiktoken>=0.7.0            # Token counting for OpenAI models
tenacity>=8.2.0            # Retry logic with exponential backoff
structlog>=24.1.0          # Structured logging
```

### 2.3 External Services Required

| Service | Purpose | Required By |
|---------|---------|-------------|
| OpenAI API | GPT-4o, GPT-4o-mini, embeddings | Most stages |
| Anthropic API | Claude for summarization, connections | Summarization, connections |
| Neo4j | Knowledge graph storage | Connection discovery |
| Redis | Embedding cache, rate limiting | All stages |

### 2.4 Environment Variables

```bash
# .env file additions
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...               # Optional: for Gemini fallback

# LLM Configuration (model-agnostic via LiteLLM)
LLM_MODEL_CLASSIFICATION=openai/gpt-4o-mini
LLM_MODEL_SUMMARIZATION=anthropic/claude-3-5-sonnet-20241022
LLM_MODEL_EXTRACTION=openai/gpt-4o
LLM_MODEL_CONNECTIONS=anthropic/claude-3-5-sonnet-20241022
LLM_MODEL_QUESTIONS=openai/gpt-4o
LLM_MODEL_EMBEDDINGS=openai/text-embedding-3-small

# LiteLLM Operational Controls
LITELLM_BUDGET_MAX=200.0         # Monthly budget limit in USD
LITELLM_BUDGET_ALERT=150.0       # Alert when budget threshold reached
LITELLM_LOG_COSTS=true           # Log cost per request

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Processing Configuration
PROCESSING_MAX_CONTENT_LENGTH=100000
PROCESSING_MAX_RETRIES=3
PROCESSING_TIMEOUT_SECONDS=300
OBSIDIAN_VAULT_PATH=/path/to/vault
```

---

## 3. Implementation Phases

### Phase 3A: Foundation (Week 7)

#### Task 3A.1: Project Structure Setup

**Why this matters:** A well-organized directory structure separates concerns: LLM client configuration, processing stages, pipeline orchestration, and output generation. This enables independent testing of each stage and easy addition of new processing capabilities.

Create the processing module directory structure:

```
backend/
├── app/
│   ├── services/
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Unified LLM client
│   │   │   ├── models.py           # Model configuration
│   │   │   └── cost_tracker.py     # Cost estimation & tracking
│   │   ├── processing/
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py         # Main orchestrator
│   │   │   ├── stages/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── content_analysis.py
│   │   │   │   ├── summarization.py
│   │   │   │   ├── extraction.py
│   │   │   │   ├── tagging.py
│   │   │   │   ├── connections.py
│   │   │   │   ├── followups.py
│   │   │   │   └── questions.py
│   │   │   ├── output/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── obsidian_generator.py
│   │   │   │   └── neo4j_generator.py
│   │   │   └── validation.py       # Output quality checks
│   │   └── knowledge_graph/
│   │       ├── __init__.py
│   │       ├── client.py           # Neo4j client wrapper
│   │       ├── schemas.py          # Node/edge definitions
│   │       └── queries.py          # Common graph queries
│   ├── routers/
│   │   └── processing.py           # Processing API endpoints
│   └── config/
│       └── processing.py           # Processing configuration
```

**Deliverables:**
- [ ] Directory structure created
- [ ] `__init__.py` files with proper exports
- [ ] Configuration loader for processing settings

**Estimated Time:** 2 hours

---

#### Task 3A.2: Processing Data Models

**Why this matters:** Well-defined Pydantic models ensure type safety and validation throughout the processing pipeline. Each processing stage produces structured output that downstream stages and output generators can rely on.

```python
# backend/app/models/processing.py

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class ContentAnalysis(BaseModel):
    """Result of initial content analysis."""
    content_type: str           # paper, article, book, code, idea
    domain: str                 # ml, systems, leadership, etc.
    complexity: str             # foundational, intermediate, advanced
    estimated_length: str       # short, medium, long
    has_code: bool
    has_math: bool
    has_diagrams: bool
    key_topics: list[str]
    language: str = "en"

class SummaryLevel(str, Enum):
    BRIEF = "brief"           # 1-2 sentences
    STANDARD = "standard"     # 1-2 paragraphs
    DETAILED = "detailed"     # Full summary with sections

class Concept(BaseModel):
    """Extracted concept with context."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    definition: str
    context: str                    # How it's used in this content
    importance: str                 # core, supporting, tangential
    related_concepts: list[str] = []

class ExtractionResult(BaseModel):
    """Result of concept extraction."""
    concepts: list[Concept] = []
    key_findings: list[str] = []
    methodologies: list[str] = []
    tools_mentioned: list[str] = []
    people_mentioned: list[str] = []

class TagAssignment(BaseModel):
    """Result of tag classification."""
    domain_tags: list[str] = []
    meta_tags: list[str] = []
    suggested_new_tags: list[str] = []
    reasoning: str = ""

class Connection(BaseModel):
    """Connection to existing knowledge."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str
    target_title: str
    relationship_type: str      # RELATES_TO, EXTENDS, CONTRADICTS, PREREQUISITE_FOR
    strength: float = Field(ge=0.0, le=1.0)
    explanation: str

class FollowupTask(BaseModel):
    """Generated follow-up task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    task_type: str              # research, practice, connect, apply, review
    priority: str               # high, medium, low
    estimated_time: str         # 15min, 30min, 1hr, 2hr+

class MasteryQuestion(BaseModel):
    """Generated mastery question."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    question_type: str          # conceptual, application, analysis, synthesis
    difficulty: str             # foundational, intermediate, advanced
    hints: list[str] = []
    key_points: list[str] = []

class ProcessingResult(BaseModel):
    """Complete result of processing pipeline."""
    content_id: str
    analysis: ContentAnalysis
    summaries: dict[str, str] = {}  # level -> summary
    extraction: ExtractionResult
    tags: TagAssignment
    connections: list[Connection] = []
    followups: list[FollowupTask] = []
    mastery_questions: list[MasteryQuestion] = []
    obsidian_note_path: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    processing_time_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    processed_at: datetime = Field(default_factory=datetime.now)
```

**Deliverables:**
- [ ] `ContentAnalysis` model
- [ ] `SummaryLevel` enum and summaries dict
- [ ] `Concept` and `ExtractionResult` models
- [ ] `TagAssignment` model
- [ ] `Connection` model
- [ ] `FollowupTask` model
- [ ] `MasteryQuestion` model
- [ ] `ProcessingResult` aggregate model
- [ ] Unit tests for model validation

**Estimated Time:** 3 hours

---

#### Task 3A.3: Unified LLM Client

**Why this matters:** A unified LLM client abstracts provider differences, enables task-specific model selection, automatic fallbacks, cost tracking, and retry logic. Using LiteLLM provides these enterprise features out of the box.

```python
# backend/app/services/llm/client.py

"""
Unified LLM client supporting multiple providers via LiteLLM.

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name". Key features:
- Automatic fallbacks to backup models
- Built-in cost tracking and budget alerts
- Rate limiting (TPM/RPM)
- Native async support

See: https://docs.litellm.ai/
"""

import litellm
from litellm import completion, acompletion, embedding, aembedding
from app.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = settings.DEBUG
litellm.drop_params = True  # Drop unsupported params instead of erroring

class LLMClient:
    """Unified LLM client with task-based model selection."""
    
    # Model mapping by task (configurable via environment)
    MODELS = {
        "classification": settings.LLM_MODEL_CLASSIFICATION,
        "summarization": settings.LLM_MODEL_SUMMARIZATION,
        "extraction": settings.LLM_MODEL_EXTRACTION,
        "connection_discovery": settings.LLM_MODEL_CONNECTIONS,
        "question_generation": settings.LLM_MODEL_QUESTIONS,
        "embeddings": settings.LLM_MODEL_EMBEDDINGS,
    }
    
    # Fallback models for each primary model
    FALLBACKS = {
        "anthropic/claude-3-5-sonnet-20241022": "openai/gpt-4o",
        "openai/gpt-4o": "anthropic/claude-3-5-sonnet-20241022",
        "openai/gpt-4o-mini": "anthropic/claude-3-5-haiku-20241022",
    }
    
    def __init__(self):
        self._validate_api_keys()
        self._total_cost = 0.0
    
    def _validate_api_keys(self):
        """Verify required API keys are set."""
        required = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        import os
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise ValueError(f"Missing API keys: {missing}")
    
    def get_model_for_task(self, task: str) -> str:
        """Get the configured model for a specific task."""
        return self.MODELS.get(task, "openai/gpt-4o")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True
    )
    async def complete(
        self,
        task: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        retry_with_fallback: bool = True
    ) -> str:
        """Generate a completion using the appropriate model for the task.
        
        Args:
            task: Task type (classification, summarization, etc.)
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
            json_mode: Request structured JSON output
            retry_with_fallback: Use fallback model on failure
        
        Returns:
            Model response text
        """
        model = self.get_model_for_task(task)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        try:
            response = await acompletion(**kwargs)
            
            # Track cost
            if hasattr(response, '_hidden_params'):
                cost = response._hidden_params.get('response_cost', 0)
                self._total_cost += cost
                if settings.LITELLM_LOG_COSTS:
                    logger.info(f"LLM completion cost: ${cost:.4f} (task={task}, model={model})")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM completion failed: {e} (model={model})")
            
            if retry_with_fallback and model in self.FALLBACKS:
                fallback = self.FALLBACKS[model]
                logger.info(f"Retrying with fallback model: {fallback}")
                kwargs["model"] = fallback
                response = await acompletion(**kwargs)
                return response.choices[0].message.content
            raise
    
    def complete_sync(
        self,
        task: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        """Synchronous version for Celery tasks."""
        model = self.get_model_for_task(task)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = completion(**kwargs)
        return response.choices[0].message.content
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        model = self.get_model_for_task("embeddings")
        
        response = await aembedding(
            model=model,
            input=texts
        )
        
        return [item["embedding"] for item in response.data]
    
    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous embedding for Celery tasks."""
        model = self.get_model_for_task("embeddings")
        
        response = embedding(
            model=model,
            input=texts
        )
        
        return [item["embedding"] for item in response.data]
    
    @property
    def total_cost(self) -> float:
        """Get total cost accumulated by this client instance."""
        return self._total_cost


# Singleton instance
_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    """Get or create singleton LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
```

**Deliverables:**
- [ ] `LLMClient` class with task-based model selection
- [ ] Async and sync completion methods
- [ ] Async and sync embedding methods
- [ ] Automatic fallback on failure
- [ ] Cost tracking per request
- [ ] Retry logic with exponential backoff
- [ ] Singleton accessor function
- [ ] Unit tests with mocked LLM responses

**Estimated Time:** 4 hours

---

#### Task 3A.4: Neo4j Knowledge Graph Client

**Why this matters:** The knowledge graph stores concepts, content nodes, and their relationships. The client provides a clean interface for vector similarity search (connection discovery), node creation, and relationship management.

```python
# backend/app/services/knowledge_graph/client.py

from neo4j import AsyncGraphDatabase, GraphDatabase
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    """Client for Neo4j knowledge graph operations."""
    
    def __init__(self):
        self._async_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self._sync_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    async def close(self):
        await self._async_driver.close()
        self._sync_driver.close()
    
    async def vector_search(
        self,
        embedding: list[float],
        node_type: str = "Content",
        top_k: int = 10,
        threshold: float = 0.7
    ) -> list[dict]:
        """Find similar nodes using vector similarity search.
        
        Args:
            embedding: Query embedding vector
            node_type: Type of node to search (Content, Concept)
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
        
        Returns:
            List of matching nodes with similarity scores
        """
        query = """
        CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
        YIELD node, score
        WHERE score >= $threshold
        RETURN node.id AS id,
               node.title AS title,
               node.summary AS summary,
               node.type AS type,
               score
        ORDER BY score DESC
        """
        
        index_name = f"{node_type.lower()}_embedding_index"
        
        async with self._async_driver.session() as session:
            result = await session.run(
                query,
                index_name=index_name,
                top_k=top_k,
                embedding=embedding,
                threshold=threshold
            )
            return [dict(record) async for record in result]
    
    async def create_content_node(
        self,
        content_id: str,
        title: str,
        content_type: str,
        summary: str,
        embedding: list[float],
        tags: list[str],
        source_url: Optional[str] = None
    ) -> str:
        """Create a Content node in the knowledge graph.
        
        Returns:
            The created node's ID
        """
        query = """
        CREATE (c:Content {
            id: $id,
            title: $title,
            type: $content_type,
            summary: $summary,
            embedding: $embedding,
            tags: $tags,
            source_url: $source_url,
            created_at: datetime()
        })
        RETURN c.id AS id
        """
        
        async with self._async_driver.session() as session:
            result = await session.run(
                query,
                id=content_id,
                title=title,
                content_type=content_type,
                summary=summary,
                embedding=embedding,
                tags=tags,
                source_url=source_url
            )
            record = await result.single()
            return record["id"]
    
    async def create_concept_node(
        self,
        concept_id: str,
        name: str,
        definition: str,
        embedding: list[float],
        importance: str
    ) -> str:
        """Create or merge a Concept node."""
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET
            c.id = $id,
            c.definition = $definition,
            c.embedding = $embedding,
            c.importance = $importance,
            c.created_at = datetime()
        ON MATCH SET
            c.definition = CASE WHEN $importance = 'core' 
                               THEN $definition ELSE c.definition END
        RETURN c.id AS id
        """
        
        async with self._async_driver.session() as session:
            result = await session.run(
                query,
                id=concept_id,
                name=name,
                definition=definition,
                embedding=embedding,
                importance=importance
            )
            record = await result.single()
            return record["id"]
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict = None
    ):
        """Create a relationship between two nodes."""
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{relationship_type}]->(target)
        SET r += $properties
        RETURN type(r) AS rel_type
        """
        
        async with self._async_driver.session() as session:
            await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                properties=properties or {}
            )
    
    async def get_connected_nodes(
        self,
        node_id: str,
        relationship_types: list[str] = None,
        max_depth: int = 2
    ) -> list[dict]:
        """Get nodes connected to a given node."""
        rel_filter = ""
        if relationship_types:
            rel_filter = ":" + "|".join(relationship_types)
        
        query = f"""
        MATCH (start {{id: $node_id}})-[r{rel_filter}*1..{max_depth}]-(connected)
        RETURN DISTINCT connected.id AS id,
               connected.title AS title,
               connected.name AS name,
               labels(connected)[0] AS type
        """
        
        async with self._async_driver.session() as session:
            result = await session.run(query, node_id=node_id)
            return [dict(record) async for record in result]


# Singleton instance
_client: Optional[Neo4jClient] = None

async def get_neo4j_client() -> Neo4jClient:
    """Get or create singleton Neo4j client."""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
```

**Deliverables:**
- [ ] `Neo4jClient` class
- [ ] Vector similarity search method
- [ ] Content node creation
- [ ] Concept node creation/merge
- [ ] Relationship creation
- [ ] Connected nodes query
- [ ] Async and sync support
- [ ] Unit tests with test database

**Estimated Time:** 4 hours

---

#### Task 3A.5: Database Schema for Processing

**Why this matters:** Processing results need to be persisted for audit trails, reprocessing, and feedback loops. The schema extends Phase 2's content table with processing-specific fields and adds new tables for concepts, connections, and questions.

```python
# backend/app/db/models_processing.py

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from datetime import datetime

class ProcessingRun(Base):
    """Record of a processing pipeline execution."""
    __tablename__ = "processing_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Analysis results
    analysis = Column(JSONB)         # ContentAnalysis as JSON
    summaries = Column(JSONB)        # {level: summary} dict
    extraction = Column(JSONB)       # ExtractionResult as JSON
    tags = Column(JSONB)             # TagAssignment as JSON
    
    # Processing metadata
    models_used = Column(JSONB)      # {stage: model} mapping
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    processing_time_seconds = Column(Float)
    error_message = Column(Text)
    
    # Outputs
    obsidian_note_path = Column(Text)
    neo4j_node_id = Column(String(64))
    
    content = relationship("Content", back_populates="processing_runs")
    concepts = relationship("ConceptRecord", back_populates="processing_run", cascade="all, delete-orphan")
    connections = relationship("ConnectionRecord", back_populates="processing_run", cascade="all, delete-orphan")
    questions = relationship("QuestionRecord", back_populates="processing_run", cascade="all, delete-orphan")
    followups = relationship("FollowupRecord", back_populates="processing_run", cascade="all, delete-orphan")


class ConceptRecord(Base):
    """Extracted concept stored for reference and linking."""
    __tablename__ = "concepts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_run_id = Column(UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False)
    
    name = Column(String(200), nullable=False, index=True)
    definition = Column(Text)
    context = Column(Text)
    importance = Column(String(20))  # core, supporting, tangential
    related_concepts = Column(ARRAY(String))
    embedding = Column(ARRAY(Float))  # For similarity search
    neo4j_node_id = Column(String(64))
    
    processing_run = relationship("ProcessingRun", back_populates="concepts")


class ConnectionRecord(Base):
    """Discovered connection to existing knowledge."""
    __tablename__ = "connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_run_id = Column(UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False)
    
    source_content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    target_content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # RELATES_TO, EXTENDS, etc.
    strength = Column(Float)
    explanation = Column(Text)
    verified_by_user = Column(Boolean, default=False)
    
    processing_run = relationship("ProcessingRun", back_populates="connections")


class QuestionRecord(Base):
    """Generated mastery question."""
    __tablename__ = "mastery_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_run_id = Column(UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    
    question = Column(Text, nullable=False)
    question_type = Column(String(30))  # conceptual, application, analysis, synthesis
    difficulty = Column(String(20))     # foundational, intermediate, advanced
    hints = Column(ARRAY(String))
    key_points = Column(ARRAY(String))
    
    # For spaced repetition integration
    next_review_at = Column(DateTime)
    review_count = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    
    processing_run = relationship("ProcessingRun", back_populates="questions")


class FollowupRecord(Base):
    """Generated follow-up task."""
    __tablename__ = "followup_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_run_id = Column(UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    
    task = Column(Text, nullable=False)
    task_type = Column(String(30))      # research, practice, connect, apply, review
    priority = Column(String(10))       # high, medium, low
    estimated_time = Column(String(20)) # 15min, 30min, 1hr, 2hr+
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    processing_run = relationship("ProcessingRun", back_populates="followups")
```

```bash
# Alembic migration
alembic revision --autogenerate -m "Add processing tables"
alembic upgrade head
```

**Deliverables:**
- [ ] `ProcessingRun` model
- [ ] `ConceptRecord` model
- [ ] `ConnectionRecord` model
- [ ] `QuestionRecord` model with spaced repetition fields
- [ ] `FollowupRecord` model
- [ ] Alembic migration
- [ ] Proper indexes on frequently queried columns

**Estimated Time:** 3 hours

---

### Phase 3B: Processing Stages (Weeks 8-9)

#### Task 3B.1: Content Analysis Stage

**Why this matters:** Content analysis is the first processing stage that determines how subsequent stages behave. Identifying content type, domain, complexity, and key topics allows the pipeline to use appropriate prompts and model configurations for each piece of content.

```python
# backend/app/services/processing/stages/content_analysis.py

from app.models.processing import ContentAnalysis
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze this content and provide structured metadata.

Content Title: {title}
Content Type Hint: {source_type}
Content (first 8000 chars):
{content}

Provide analysis in JSON format:
{{
  "content_type": "paper|article|book|code|idea|voice_memo",
  "domain": "primary domain (e.g., ml, systems, leadership, productivity, science, business)",
  "complexity": "foundational|intermediate|advanced",
  "estimated_length": "short|medium|long",
  "has_code": true|false,
  "has_math": true|false,
  "has_diagrams": true|false,
  "key_topics": ["topic1", "topic2", "topic3"],
  "language": "en|de|fr|es|..."
}}

Guidelines:
- "paper" for academic/research papers with citations
- "article" for blog posts, news, essays
- "book" for book excerpts or full books
- "code" for code repositories or technical documentation
- "idea" for quick notes or thoughts
- "voice_memo" for transcribed audio

Complexity levels:
- "foundational": Introductory, suitable for beginners
- "intermediate": Assumes some background knowledge
- "advanced": Requires deep domain expertise
"""


async def analyze_content(
    content: UnifiedContent,
    llm_client: LLMClient
) -> ContentAnalysis:
    """Perform initial content analysis to guide downstream processing.
    
    Args:
        content: Unified content from ingestion
        llm_client: LLM client for completion
    
    Returns:
        ContentAnalysis with type, domain, complexity, etc.
    """
    # Use first ~8000 chars for analysis (cost-efficient)
    text_sample = content.full_text[:8000] if content.full_text else ""
    
    if not text_sample.strip():
        logger.warning(f"Content {content.id} has no text, using defaults")
        return ContentAnalysis(
            content_type=content.source_type.value,
            domain="general",
            complexity="intermediate",
            estimated_length="short",
            has_code=False,
            has_math=False,
            has_diagrams=False,
            key_topics=[],
            language="en"
        )
    
    prompt = ANALYSIS_PROMPT.format(
        title=content.title,
        source_type=content.source_type.value,
        content=text_sample
    )
    
    response = await llm_client.complete(
        task="classification",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        return ContentAnalysis(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse analysis response: {e}")
        # Return sensible defaults
        return ContentAnalysis(
            content_type=content.source_type.value,
            domain="general",
            complexity="intermediate",
            estimated_length="medium",
            has_code=False,
            has_math=False,
            has_diagrams=False,
            key_topics=[],
            language="en"
        )
```

**Deliverables:**
- [ ] `analyze_content()` function
- [ ] Analysis prompt with clear guidelines
- [ ] JSON parsing with fallback defaults
- [ ] Unit tests with various content types

**Estimated Time:** 3 hours

---

#### Task 3B.2: Summarization Stage

**Why this matters:** Multi-level summaries serve different use cases: brief summaries for quick reference in the knowledge graph, standard summaries for Obsidian note frontmatter, and detailed summaries for deep comprehension. Content-type-specific prompts ensure relevant information is prioritized.

```python
# backend/app/services/processing/stages/summarization.py

from app.models.processing import ContentAnalysis, SummaryLevel
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
import logging

logger = logging.getLogger(__name__)

SUMMARY_PROMPTS = {
    "paper": """Summarize this academic paper at {level} level.

Paper Title: {title}
Authors: {authors}

Paper content:
{content}

Annotations/highlights from the reader (these indicate what they found important):
{annotations}

Summary levels:
- BRIEF: Core contribution in 1-2 sentences. What is the paper's main claim?
- STANDARD: 2-3 paragraphs covering: Problem addressed, Approach taken, Key findings, Implications
- DETAILED: Full structured summary including: Abstract, Introduction context, Methodology, Results, Discussion, Limitations, Future work

Provide a {level} summary:""",
    
    "article": """Summarize this article at {level} level.

Title: {title}
Source: {source}

Article:
{content}

Reader's highlights (what they found important):
{annotations}

Summary levels:
- BRIEF: Main point in 1-2 sentences
- STANDARD: 2-3 paragraphs with key takeaways and actionable insights
- DETAILED: Comprehensive summary with all major points, examples, and implications

Focus on practical takeaways and actionable insights.

Provide a {level} summary:""",
    
    "book": """Summarize these book notes/highlights at {level} level.

Book: {title}
Authors: {authors}

Content (highlights, notes, or chapter text):
{content}

The reader highlighted these passages as important - use them to inform the summary.

Summary levels:
- BRIEF: Core theme in 1-2 sentences
- STANDARD: Key ideas and their implications
- DETAILED: Chapter-by-chapter or section-by-section breakdown

Provide a {level} summary:""",
    
    "code": """Summarize this code repository analysis at {level} level.

Repository: {title}

Analysis:
{content}

Summary levels:
- BRIEF: What the code does in 1-2 sentences
- STANDARD: Purpose, architecture, key patterns
- DETAILED: Full breakdown including: Purpose, Architecture, Tech stack, Notable patterns, Key learnings

Provide a {level} summary:""",
    
    "idea": """Summarize this idea/note at {level} level.

Title: {title}

Content:
{content}

Summary levels:
- BRIEF: Core idea in 1 sentence
- STANDARD: Main point with context and implications
- DETAILED: Full exploration of the idea with connections

Provide a {level} summary:""",
    
    "voice_memo": """Summarize this voice memo transcription at {level} level.

Title: {title}

Transcription:
{content}

Summary levels:
- BRIEF: Main point in 1 sentence
- STANDARD: Key points organized logically
- DETAILED: Full summary with all points, ideas, and action items

Provide a {level} summary:"""
}


async def generate_summary(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    level: SummaryLevel,
    llm_client: LLMClient
) -> str:
    """Generate a summary at the specified level."""
    # Select appropriate prompt template
    prompt_template = SUMMARY_PROMPTS.get(
        analysis.content_type,
        SUMMARY_PROMPTS["article"]
    )
    
    # Format annotations
    annotations_text = "\n".join([
        f"- [{a.type.value}] {a.content[:300]}"
        for a in content.annotations[:20]
    ]) if content.annotations else "None provided"
    
    # Adjust content length based on level
    content_limits = {
        SummaryLevel.BRIEF: 10000,
        SummaryLevel.STANDARD: 25000,
        SummaryLevel.DETAILED: 40000
    }
    max_content = content_limits.get(level, 25000)
    
    prompt = prompt_template.format(
        title=content.title,
        authors=", ".join(content.authors) if content.authors else "Unknown",
        source=content.source_url or "Unknown",
        content=content.full_text[:max_content] if content.full_text else "",
        annotations=annotations_text,
        level=level.value.upper()
    )
    
    # Adjust max tokens based on level
    token_limits = {
        SummaryLevel.BRIEF: 200,
        SummaryLevel.STANDARD: 800,
        SummaryLevel.DETAILED: 2000
    }
    max_tokens = token_limits.get(level, 800)
    
    return await llm_client.complete(
        task="summarization",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens
    )


async def generate_all_summaries(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    llm_client: LLMClient
) -> dict[str, str]:
    """Generate summaries at all levels."""
    summaries = {}
    
    for level in SummaryLevel:
        try:
            summaries[level.value] = await generate_summary(
                content, analysis, level, llm_client
            )
        except Exception as e:
            logger.error(f"Failed to generate {level.value} summary: {e}")
            summaries[level.value] = f"[Summary generation failed: {e}]"
    
    return summaries
```

**Deliverables:**
- [ ] Content-type-specific prompt templates
- [ ] `generate_summary()` for single level
- [ ] `generate_all_summaries()` for all levels
- [ ] Annotation inclusion in prompts
- [ ] Token limit configuration per level
- [ ] Unit tests with sample content

**Estimated Time:** 4 hours

---

#### Task 3B.3: Concept Extraction Stage

**Why this matters:** Concepts are the atomic units of knowledge in the graph. Extracting concepts with definitions, importance levels, and relationships enables rich querying, connection discovery, and knowledge gap identification.

```python
# backend/app/services/processing/stages/extraction.py

from app.models.processing import Concept, ExtractionResult
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract structured information from this content.

Title: {title}
Domain: {domain}
Complexity: {complexity}

Content:
{content}

Extract the following:

1. **CONCEPTS**: Key ideas, terms, frameworks, theories mentioned
   - Name: The concept name
   - Definition: A clear, concise definition
   - Context: How this concept is used/discussed in THIS content
   - Importance: 
     * "core" - Central to understanding this content
     * "supporting" - Helps understand core concepts
     * "tangential" - Mentioned but not essential
   - Related concepts: Other concepts in this content it connects to

2. **KEY FINDINGS**: Main insights, conclusions, claims, or arguments made

3. **METHODOLOGIES**: Approaches, techniques, algorithms, or processes described

4. **TOOLS**: Software, frameworks, libraries, or technologies mentioned

5. **PEOPLE**: Authors, researchers, practitioners, or thought leaders referenced

Return as JSON:
{{
  "concepts": [
    {{
      "name": "concept name",
      "definition": "clear definition in 1-2 sentences",
      "context": "how it's used in this specific content",
      "importance": "core|supporting|tangential",
      "related_concepts": ["concept1", "concept2"]
    }}
  ],
  "key_findings": ["finding or insight 1", "finding or insight 2"],
  "methodologies": ["methodology or technique 1"],
  "tools_mentioned": ["tool or technology 1"],
  "people_mentioned": ["person name 1"]
}}

Extract 5-15 concepts depending on content length and density.
"""


async def extract_concepts(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    llm_client: LLMClient
) -> ExtractionResult:
    """Extract concepts, findings, and entities from content."""
    text_content = content.full_text[:20000] if content.full_text else ""
    
    if not text_content.strip():
        logger.warning(f"Content {content.id} has no text for extraction")
        return ExtractionResult()
    
    prompt = EXTRACTION_PROMPT.format(
        title=content.title,
        domain=analysis.domain,
        complexity=analysis.complexity,
        content=text_content
    )
    
    response = await llm_client.complete(
        task="extraction",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=3000,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        concepts = [
            Concept(
                name=c.get("name", ""),
                definition=c.get("definition", ""),
                context=c.get("context", ""),
                importance=c.get("importance", "supporting"),
                related_concepts=c.get("related_concepts", [])
            )
            for c in data.get("concepts", [])
            if c.get("name")
        ]
        
        return ExtractionResult(
            concepts=concepts,
            key_findings=data.get("key_findings", []),
            methodologies=data.get("methodologies", []),
            tools_mentioned=data.get("tools_mentioned", []),
            people_mentioned=data.get("people_mentioned", [])
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse extraction response: {e}")
        return ExtractionResult()
```

**Deliverables:**
- [ ] `extract_concepts()` function
- [ ] Comprehensive extraction prompt
- [ ] Concept model mapping
- [ ] Error handling with empty result fallback
- [ ] Unit tests with diverse content

**Estimated Time:** 4 hours

---

#### Task 3B.4: Tagging & Classification Stage

**Why this matters:** A controlled tag vocabulary ensures consistency across the knowledge base. Tags enable filtering, grouping, and discovering content by domain, status, or quality level.

```python
# backend/app/services/processing/stages/tagging.py

from app.models.processing import ContentAnalysis, TagAssignment
from app.services.llm.client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)

TAG_TAXONOMY = {
    "domains": [
        "ml/deep-learning", "ml/nlp", "ml/computer-vision", 
        "ml/reinforcement-learning", "ml/mlops", "ml/transformers",
        "systems/distributed", "systems/databases", "systems/performance",
        "engineering/architecture", "engineering/testing", "engineering/devops",
        "leadership/management", "leadership/communication", "leadership/strategy",
        "productivity/habits", "productivity/tools", "productivity/workflows",
        "learning/techniques", "learning/note-taking",
    ],
    "meta": [
        "status/actionable", "status/reference", "status/archive",
        "quality/foundational", "quality/deep-dive", "quality/overview",
    ]
}

TAGGING_PROMPT = """Assign tags to this content from the provided taxonomy.

Content Analysis:
- Title: {title}
- Type: {content_type}
- Domain: {domain}
- Complexity: {complexity}
- Key Topics: {key_topics}

Summary: {summary}

Available Tags (select from these ONLY):
DOMAIN TAGS: {domain_tags}
META TAGS: {meta_tags}

Rules:
1. Assign 1-3 domain tags (most specific that applies)
2. Assign 1-2 meta tags
3. ONLY use tags from the provided taxonomy

Return as JSON:
{{
  "domain_tags": ["domain/tag1", "domain/tag2"],
  "meta_tags": ["meta/tag1"],
  "suggested_new_tags": ["domain/new-tag if taxonomy has clear gap"],
  "reasoning": "Brief explanation of tag choices"
}}
"""


async def assign_tags(
    content_title: str,
    analysis: ContentAnalysis,
    summary: str,
    llm_client: LLMClient
) -> TagAssignment:
    """Assign tags from controlled vocabulary."""
    prompt = TAGGING_PROMPT.format(
        title=content_title,
        content_type=analysis.content_type,
        domain=analysis.domain,
        complexity=analysis.complexity,
        key_topics=", ".join(analysis.key_topics[:10]),
        summary=summary[:2000] if summary else "No summary available",
        domain_tags=", ".join(TAG_TAXONOMY["domains"]),
        meta_tags=", ".join(TAG_TAXONOMY["meta"])
    )
    
    response = await llm_client.complete(
        task="classification",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        valid_domain_tags = [t for t in data.get("domain_tags", []) if t in TAG_TAXONOMY["domains"]]
        valid_meta_tags = [t for t in data.get("meta_tags", []) if t in TAG_TAXONOMY["meta"]]
        
        return TagAssignment(
            domain_tags=valid_domain_tags,
            meta_tags=valid_meta_tags,
            suggested_new_tags=data.get("suggested_new_tags", []),
            reasoning=data.get("reasoning", "")
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse tagging response: {e}")
        return TagAssignment(meta_tags=["status/to-review"])
```

**Deliverables:**
- [ ] `TAG_TAXONOMY` controlled vocabulary
- [ ] `assign_tags()` function
- [ ] Tag validation against taxonomy
- [ ] Unit tests for tag validation

**Estimated Time:** 3 hours

---

#### Task 3B.5: Connection Discovery Stage

**Why this matters:** Connection discovery creates the "web" in the knowledge graph. By finding semantic relationships between new content and existing knowledge, the system surfaces non-obvious connections.

```python
# backend/app/services/processing/stages/connections.py

from app.models.processing import Connection, ExtractionResult
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
from app.services.knowledge_graph.client import Neo4jClient
import json
import logging

logger = logging.getLogger(__name__)

CONNECTION_EVALUATION_PROMPT = """Evaluate the relationship between new content and a potential connection.

NEW CONTENT:
Title: {new_title}
Summary: {new_summary}
Key Concepts: {new_concepts}

POTENTIAL CONNECTION:
Title: {candidate_title}
Summary: {candidate_summary}

Connection Types:
- RELATES_TO: General topical relationship
- EXTENDS: New content builds on existing content
- CONTRADICTS: New content challenges existing content
- PREREQUISITE_FOR: Existing is foundational for new
- APPLIES: New content applies concepts from existing

Return JSON:
{{
  "has_connection": true|false,
  "relationship_type": "RELATES_TO|EXTENDS|CONTRADICTS|PREREQUISITE_FOR|APPLIES",
  "strength": 0.0-1.0,
  "explanation": "1-2 sentence explanation"
}}
"""


async def discover_connections(
    content: UnifiedContent,
    summary: str,
    concepts: ExtractionResult,
    analysis: ContentAnalysis,
    llm_client: LLMClient,
    neo4j_client: Neo4jClient,
    top_k: int = 10,
    similarity_threshold: float = 0.7,
    connection_threshold: float = 0.4
) -> list[Connection]:
    """Discover connections to existing knowledge in the graph."""
    connections = []
    
    # Generate embedding for new content
    embedding_text = f"{content.title}\n\n{summary[:2000]}"
    embeddings = await llm_client.embed([embedding_text])
    if not embeddings:
        return []
    
    # Find similar content via vector search
    candidates = await neo4j_client.vector_search(
        embedding=embeddings[0],
        node_type="Content",
        top_k=top_k * 2,
        threshold=similarity_threshold
    )
    
    concept_names = [c.name for c in concepts.concepts[:10]]
    
    for candidate in candidates:
        if candidate.get("id") == content.id:
            continue
        
        connection = await _evaluate_connection(
            new_title=content.title,
            new_summary=summary,
            new_concepts=concept_names,
            candidate=candidate,
            llm_client=llm_client,
            threshold=connection_threshold
        )
        if connection:
            connections.append(connection)
    
    connections.sort(key=lambda c: c.strength, reverse=True)
    return connections[:top_k]


async def _evaluate_connection(
    new_title: str,
    new_summary: str,
    new_concepts: list[str],
    candidate: dict,
    llm_client: LLMClient,
    threshold: float
) -> Connection | None:
    """Evaluate a single potential connection using LLM."""
    prompt = CONNECTION_EVALUATION_PROMPT.format(
        new_title=new_title,
        new_summary=new_summary[:1500],
        new_concepts=", ".join(new_concepts),
        candidate_title=candidate.get("title", "Unknown"),
        candidate_summary=candidate.get("summary", "")[:1000]
    )
    
    response = await llm_client.complete(
        task="connection_discovery",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        if not data.get("has_connection"):
            return None
        strength = float(data.get("strength", 0))
        if strength < threshold:
            return None
        
        return Connection(
            target_id=candidate["id"],
            target_title=candidate.get("title", "Unknown"),
            relationship_type=data.get("relationship_type", "RELATES_TO"),
            strength=strength,
            explanation=data.get("explanation", "")
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse connection evaluation: {e}")
        return None
```

**Deliverables:**
- [ ] `discover_connections()` main function
- [ ] Embedding generation for new content
- [ ] Vector similarity search via Neo4j
- [ ] LLM-based connection evaluation
- [ ] Multiple relationship types
- [ ] Unit tests with mock graph

**Estimated Time:** 5 hours

---

#### Task 3B.6: Follow-up Task Generation Stage

**Why this matters:** Follow-up tasks transform passive reading into active learning. By generating specific, actionable tasks based on content and reader highlights, the system helps users engage more deeply.

```python
# backend/app/services/processing/stages/followups.py

from app.models.processing import FollowupTask, ContentAnalysis, ExtractionResult
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)

FOLLOWUP_PROMPT = """Generate actionable follow-up tasks based on this content.

Content:
- Title: {title}
- Type: {content_type}
- Domain: {domain}

Summary: {summary}
Key Concepts: {concepts}
Reader's Highlights: {annotations}

Generate 3-5 follow-up tasks that are:
1. Actionable: Can be completed in a single session
2. Deepening: Go beyond surface understanding
3. Connected: Relate to other knowledge areas

Task Types:
- research: "Look up X to understand Y better"
- practice: "Try implementing X"
- connect: "Explore how this relates to Z"
- apply: "Use this on project W"
- review: "Revisit X after applying this"

Return as JSON:
{{
  "tasks": [
    {{
      "task": "Specific, actionable task description",
      "type": "research|practice|connect|apply|review",
      "priority": "high|medium|low",
      "estimated_time": "15min|30min|1hr|2hr+"
    }}
  ]
}}
"""


async def generate_followups(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    concepts: ExtractionResult,
    llm_client: LLMClient
) -> list[FollowupTask]:
    """Generate follow-up tasks for deeper engagement."""
    annotations_text = "\n".join([
        f"- {a.content[:200]}" for a in content.annotations[:10]
    ]) if content.annotations else "None"
    
    prompt = FOLLOWUP_PROMPT.format(
        title=content.title,
        content_type=analysis.content_type,
        domain=analysis.domain,
        summary=summary[:2000] if summary else "",
        concepts=", ".join([c.name for c in concepts.concepts[:10]]),
        annotations=annotations_text
    )
    
    response = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1000,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        return [
            FollowupTask(
                task=t.get("task", ""),
                task_type=t.get("type", "research"),
                priority=t.get("priority", "medium"),
                estimated_time=t.get("estimated_time", "30min")
            )
            for t in data.get("tasks", []) if t.get("task")
        ]
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse followups response: {e}")
        return []
```

**Deliverables:**
- [ ] `generate_followups()` function
- [ ] Comprehensive prompt with task types
- [ ] Priority and time estimation
- [ ] Unit tests for various content

**Estimated Time:** 3 hours

---

#### Task 3B.7: Mastery Question Generation Stage

**Why this matters:** Mastery questions enable active recall and self-testing. If a user can answer these questions from memory, they truly understand the material.

```python
# backend/app/services/processing/stages/questions.py

from app.models.processing import MasteryQuestion, ContentAnalysis, ExtractionResult
from app.models.content import UnifiedContent
from app.services.llm.client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)

MASTERY_QUESTIONS_PROMPT = """Generate mastery questions for this content.

A mastery question is one where:
- If you can answer it from memory, you truly understand the material
- It tests UNDERSTANDING, not just recall of facts
- Answering requires integrating multiple concepts

Content:
- Title: {title}
- Domain: {domain}
- Complexity: {complexity}

Summary: {summary}
Key Concepts: {concepts}
Key Findings: {findings}

Question Types:
- conceptual: "What is X and why does it matter?"
- application: "How would you use X to solve Y?"
- analysis: "Why does X lead to Y?"
- synthesis: "How does X connect to Z?"

Difficulty for {complexity} content:
- foundational: "what" and "how" questions
- intermediate: "why" and "when to use" questions
- advanced: "edge cases" and "trade-offs" questions

Return as JSON:
{{
  "questions": [
    {{
      "question": "Clear, specific question",
      "type": "conceptual|application|analysis|synthesis",
      "difficulty": "foundational|intermediate|advanced",
      "hints": ["Hint 1", "Hint 2"],
      "key_points": ["Key point for good answer"]
    }}
  ]
}}
"""


async def generate_mastery_questions(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    concepts: ExtractionResult,
    llm_client: LLMClient
) -> list[MasteryQuestion]:
    """Generate questions that test true understanding."""
    concepts_text = "\n".join([
        f"- {c.name}: {c.definition}" for c in concepts.concepts[:10]
    ]) if concepts.concepts else "No concepts"
    
    findings_text = "\n".join([
        f"- {f}" for f in concepts.key_findings[:10]
    ]) if concepts.key_findings else "No findings"
    
    prompt = MASTERY_QUESTIONS_PROMPT.format(
        title=content.title,
        domain=analysis.domain,
        complexity=analysis.complexity,
        summary=summary[:3000] if summary else "",
        concepts=concepts_text,
        findings=findings_text
    )
    
    response = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1500,
        json_mode=True
    )
    
    try:
        data = json.loads(response)
        return [
            MasteryQuestion(
                question=q.get("question", ""),
                question_type=q.get("type", "conceptual"),
                difficulty=q.get("difficulty", analysis.complexity),
                hints=q.get("hints", []),
                key_points=q.get("key_points", [])
            )
            for q in data.get("questions", []) if q.get("question")
        ]
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse questions response: {e}")
        return []
```

**Deliverables:**
- [ ] `generate_mastery_questions()` function
- [ ] Question type and difficulty calibration
- [ ] Hints and key points for each question
- [ ] Unit tests with various complexity levels

**Estimated Time:** 4 hours

---

### Phase 3C: Pipeline Orchestration (Week 9-10)

#### Task 3C.1: Main Processing Pipeline

**Why this matters:** The pipeline orchestrator coordinates all processing stages, manages dependencies between stages, handles errors gracefully, and tracks processing time and costs.

```python
# backend/app/services/processing/pipeline.py

from dataclasses import dataclass
from datetime import datetime
import time
import logging

from app.models.content import UnifiedContent
from app.models.processing import (
    ProcessingResult, ContentAnalysis, ExtractionResult,
    TagAssignment, Connection, FollowupTask, MasteryQuestion, SummaryLevel
)
from app.services.llm.client import get_llm_client
from app.services.knowledge_graph.client import get_neo4j_client
from app.services.processing.stages.content_analysis import analyze_content
from app.services.processing.stages.summarization import generate_all_summaries
from app.services.processing.stages.extraction import extract_concepts
from app.services.processing.stages.tagging import assign_tags
from app.services.processing.stages.connections import discover_connections
from app.services.processing.stages.followups import generate_followups
from app.services.processing.stages.questions import generate_mastery_questions
from app.services.processing.output.obsidian_generator import generate_obsidian_note
from app.services.processing.output.neo4j_generator import create_knowledge_nodes
from app.services.processing.validation import validate_processing_result

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    generate_summaries: bool = True
    extract_concepts: bool = True
    assign_tags: bool = True
    discover_connections: bool = True
    generate_followups: bool = True
    generate_questions: bool = True
    create_obsidian_note: bool = True
    create_neo4j_nodes: bool = True
    validate_output: bool = True
    max_connection_candidates: int = 10


async def process_content(
    content: UnifiedContent,
    config: PipelineConfig = None
) -> ProcessingResult:
    """Run the full LLM processing pipeline on ingested content.
    
    Pipeline stages:
    1. Content Analysis - Determine type, domain, complexity
    2. Summarization - Generate brief, standard, and detailed summaries
    3. Concept Extraction - Extract key concepts, findings, entities
    4. Tagging - Assign tags from controlled vocabulary
    5. Connection Discovery - Find relationships to existing knowledge
    6. Follow-up Generation - Create actionable learning tasks
    7. Question Generation - Create mastery questions
    """
    config = config or PipelineConfig()
    start_time = time.time()
    
    llm_client = get_llm_client()
    neo4j_client = await get_neo4j_client()
    
    logger.info(f"Starting processing pipeline for: {content.title}")
    
    # Stage 1: Content Analysis
    analysis = await analyze_content(content, llm_client)
    logger.info(f"Analysis: {analysis.content_type}, {analysis.domain}, {analysis.complexity}")
    
    # Stage 2: Generate Summaries
    summaries = {}
    if config.generate_summaries:
        summaries = await generate_all_summaries(content, analysis, llm_client)
    
    # Stage 3: Extract Concepts
    extraction = ExtractionResult()
    if config.extract_concepts:
        extraction = await extract_concepts(content, analysis, llm_client)
    
    # Stage 4: Assign Tags
    tags = TagAssignment()
    if config.assign_tags:
        standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
        tags = await assign_tags(content.title, analysis, standard_summary, llm_client)
    
    # Stage 5: Discover Connections
    connections = []
    if config.discover_connections:
        standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
        connections = await discover_connections(
            content, standard_summary, extraction, analysis,
            llm_client, neo4j_client, top_k=config.max_connection_candidates
        )
    
    # Stage 6: Generate Follow-ups
    followups = []
    if config.generate_followups:
        standard_summary = summaries.get(SummaryLevel.STANDARD.value, "")
        followups = await generate_followups(
            content, analysis, standard_summary, extraction, llm_client
        )
    
    # Stage 7: Generate Mastery Questions
    questions = []
    if config.generate_questions:
        detailed_summary = summaries.get(SummaryLevel.DETAILED.value, "")
        questions = await generate_mastery_questions(
            content, analysis, detailed_summary, extraction, llm_client
        )
    
    processing_time = time.time() - start_time
    estimated_cost = llm_client.total_cost
    
    result = ProcessingResult(
        content_id=content.id,
        analysis=analysis,
        summaries=summaries,
        extraction=extraction,
        tags=tags,
        connections=connections,
        followups=followups,
        mastery_questions=questions,
        processing_time_seconds=processing_time,
        estimated_cost_usd=estimated_cost
    )
    
    # Validate output
    if config.validate_output:
        issues = await validate_processing_result(result)
        if issues:
            logger.warning(f"Validation issues: {issues}")
    
    # Generate outputs
    if config.create_obsidian_note:
        result.obsidian_note_path = await generate_obsidian_note(content, result)
    
    if config.create_neo4j_nodes:
        result.neo4j_node_id = await create_knowledge_nodes(
            content, result, llm_client, neo4j_client
        )
    
    logger.info(f"Processing complete in {processing_time:.2f}s, cost: ${estimated_cost:.4f}")
    
    return result
```

**Deliverables:**
- [ ] `PipelineConfig` dataclass
- [ ] `process_content()` orchestration function
- [ ] Sequential stage execution with logging
- [ ] Time and cost tracking
- [ ] Configurable stage skipping
- [ ] Integration tests for full pipeline

**Estimated Time:** 5 hours

---

#### Task 3C.2: Celery Task Integration

**Why this matters:** Processing is API-intensive. Running it synchronously would block the API. Celery tasks enable background processing with retry logic and progress tracking.

```python
# backend/app/services/tasks_processing.py

from celery import shared_task
from app.services.queue import celery_app
from app.services.processing.pipeline import process_content, PipelineConfig
from app.services.storage import load_content, update_processing_status
from app.db.models_processing import ProcessingRun
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_content_task(self, content_id: str, config_dict: dict = None):
    """Celery task to process content through LLM pipeline."""
    logger.info(f"Starting processing task for content {content_id}")
    
    try:
        content = asyncio.run(load_content(content_id))
        if not content:
            raise ValueError(f"Content {content_id} not found")
        
        asyncio.run(update_processing_status(content_id, "processing"))
        
        config = PipelineConfig()
        if config_dict:
            for key, value in config_dict.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        result = asyncio.run(process_content(content, config))
        asyncio.run(_save_processing_result(content_id, result))
        asyncio.run(update_processing_status(content_id, "completed"))
        
        return {
            "status": "completed",
            "content_id": content_id,
            "concepts": len(result.extraction.concepts),
            "connections": len(result.connections),
            "questions": len(result.mastery_questions),
            "time": result.processing_time_seconds,
            "cost": result.estimated_cost_usd
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        asyncio.run(update_processing_status(content_id, "failed", str(e)))
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True)
def reprocess_content_task(self, content_id: str, stages: list[str] = None):
    """Re-run specific processing stages on existing content."""
    config = PipelineConfig(
        generate_summaries="summarization" in (stages or []),
        extract_concepts="extraction" in (stages or []),
        assign_tags="tagging" in (stages or []),
        discover_connections="connections" in (stages or []),
        generate_followups="followups" in (stages or []),
        generate_questions="questions" in (stages or [])
    )
    return process_content_task(content_id, config.__dict__)
```

**Deliverables:**
- [ ] `process_content_task` Celery task
- [ ] `reprocess_content_task` for partial re-processing
- [ ] Status updates during processing
- [ ] Retry logic with exponential backoff
- [ ] Integration with Phase 2 ingestion

**Estimated Time:** 4 hours

---

#### Task 3C.3: Output Validation

**Why this matters:** LLM outputs can be inconsistent. Validation catches quality issues early.

```python
# backend/app/services/processing/validation.py

from app.models.processing import ProcessingResult, SummaryLevel
import logging

logger = logging.getLogger(__name__)


async def validate_processing_result(result: ProcessingResult) -> list[str]:
    """Validate processing outputs for quality issues."""
    issues = []
    
    # Check summaries
    standard = result.summaries.get(SummaryLevel.STANDARD.value, "")
    if len(standard) < 100:
        issues.append(f"Standard summary too short ({len(standard)} chars)")
    
    # Check concepts
    if not result.extraction.concepts:
        issues.append("No concepts extracted")
    else:
        core = [c for c in result.extraction.concepts if c.importance == "core"]
        if not core:
            issues.append("No core concepts identified")
    
    # Check tags
    if not result.tags.domain_tags:
        issues.append("No domain tags assigned")
    
    # Check questions
    if len(result.mastery_questions) < 2:
        issues.append(f"Insufficient questions ({len(result.mastery_questions)})")
    
    return issues
```

**Deliverables:**
- [ ] `validate_processing_result()` function
- [ ] Summary, concept, tag, question validation
- [ ] Configurable validation thresholds

**Estimated Time:** 2 hours

---

### Phase 3D: Output Generation (Week 10)

#### Task 3D.1: Obsidian Note Generator

**Why this matters:** Obsidian notes are the user-facing output. Well-formatted notes with proper frontmatter integrate into the user's knowledge vault.

```python
# backend/app/services/processing/output/obsidian_generator.py

from pathlib import Path
from datetime import datetime
from jinja2 import Environment, BaseLoader
from app.models.content import UnifiedContent, AnnotationType
from app.models.processing import ProcessingResult, SummaryLevel
from app.config import settings
import aiofiles
import logging

logger = logging.getLogger(__name__)

PAPER_TEMPLATE = '''---
type: paper
title: "{{ title }}"
authors: [{{ authors }}]
tags: [{{ tags }}]
domain: {{ domain }}
complexity: {{ complexity }}
processed: {{ processed }}
---

## Summary
{{ summary_standard }}

## Key Findings
{{ key_findings }}

## Core Concepts
{{ concepts }}

## Highlights
{{ highlights }}

## Mastery Questions
{{ questions }}

## Follow-ups
{{ followups }}

## Connections
{{ connections }}
'''


async def generate_obsidian_note(
    content: UnifiedContent,
    result: ProcessingResult
) -> str:
    """Generate an Obsidian-compatible markdown note."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(PAPER_TEMPLATE)
    
    all_tags = result.tags.domain_tags + result.tags.meta_tags
    
    # Format highlights
    highlights = [a for a in content.annotations if a.type == AnnotationType.DIGITAL_HIGHLIGHT]
    highlights_text = "\n\n".join([
        f"> {h.content}" + (f"\n> — Page {h.page_number}" if h.page_number else "")
        for h in highlights
    ]) or "*No highlights*"
    
    # Format concepts
    core_concepts = [c for c in result.extraction.concepts if c.importance == "core"]
    concepts_text = "\n".join([
        f"- **{c.name}**: {c.definition}" for c in core_concepts
    ]) or "*No concepts*"
    
    # Format other sections
    findings_text = "\n".join([f"- {f}" for f in result.extraction.key_findings]) or "*None*"
    questions_text = "\n".join([f"- [ ] {q.question}" for q in result.mastery_questions]) or "*None*"
    followups_text = "\n".join([
        f"- [ ] {f.task} `{f.task_type}` `{f.estimated_time}`" for f in result.followups
    ]) or "*None*"
    connections_text = "\n".join([
        f"- [[{c.target_title}]] — {c.explanation}" for c in result.connections
    ]) or "*None*"
    
    note_content = template.render(
        title=content.title,
        authors=", ".join(content.authors) if content.authors else "",
        tags=", ".join(all_tags),
        domain=result.analysis.domain,
        complexity=result.analysis.complexity,
        processed=datetime.now().strftime("%Y-%m-%d"),
        summary_standard=result.summaries.get(SummaryLevel.STANDARD.value, ""),
        key_findings=findings_text,
        concepts=concepts_text,
        highlights=highlights_text,
        questions=questions_text,
        followups=followups_text,
        connections=connections_text
    )
    
    # Write to vault
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    subfolder = {"paper": "Papers", "article": "Articles", "book": "Books"}.get(
        result.analysis.content_type, "Notes"
    )
    output_dir = vault_path / subfolder
    output_dir.mkdir(parents=True, exist_ok=True)
    
    safe_title = "".join(c for c in content.title if c.isalnum() or c in " -_")[:100]
    output_path = output_dir / f"{safe_title}.md"
    
    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        await f.write(note_content)
    
    return str(output_path)
```

**Deliverables:**
- [ ] Jinja2 templates for note types
- [ ] Frontmatter YAML generation
- [ ] Section formatting (highlights, concepts, etc.)
- [ ] Wiki-links for connections
- [ ] Subfolder organization
- [ ] Async file writing

**Estimated Time:** 5 hours

---

#### Task 3D.2: Neo4j Knowledge Graph Generator

**Why this matters:** The knowledge graph enables semantic search and connection discovery. Properly structured nodes and relationships ensure the graph remains useful.

```python
# backend/app/services/processing/output/neo4j_generator.py

from app.models.content import UnifiedContent
from app.models.processing import ProcessingResult, SummaryLevel
from app.services.llm.client import LLMClient
from app.services.knowledge_graph.client import Neo4jClient
import logging

logger = logging.getLogger(__name__)


async def create_knowledge_nodes(
    content: UnifiedContent,
    result: ProcessingResult,
    llm_client: LLMClient,
    neo4j_client: Neo4jClient
) -> str:
    """Create knowledge graph nodes and relationships."""
    # Generate embedding
    summary = result.summaries.get(SummaryLevel.STANDARD.value, content.title)
    embeddings = await llm_client.embed([f"{content.title}\n\n{summary}"])
    embedding = embeddings[0] if embeddings else []
    
    # Create content node
    all_tags = result.tags.domain_tags + result.tags.meta_tags
    content_node_id = await neo4j_client.create_content_node(
        content_id=content.id,
        title=content.title,
        content_type=result.analysis.content_type,
        summary=summary[:2000],
        embedding=embedding,
        tags=all_tags,
        source_url=content.source_url
    )
    
    # Create concept nodes
    core_concepts = [c for c in result.extraction.concepts if c.importance == "core"]
    for concept in core_concepts:
        concept_emb = await llm_client.embed([f"{concept.name}: {concept.definition}"])
        await neo4j_client.create_concept_node(
            concept_id=concept.id,
            name=concept.name,
            definition=concept.definition,
            embedding=concept_emb[0] if concept_emb else [],
            importance=concept.importance
        )
        await neo4j_client.create_relationship(
            source_id=content.id,
            target_id=concept.id,
            relationship_type="CONTAINS",
            properties={"importance": concept.importance}
        )
    
    # Create content connections
    for conn in result.connections:
        await neo4j_client.create_relationship(
            source_id=content.id,
            target_id=conn.target_id,
            relationship_type=conn.relationship_type,
            properties={"strength": conn.strength, "explanation": conn.explanation}
        )
    
    return content_node_id
```

**Deliverables:**
- [ ] Content node creation with embedding
- [ ] Concept node creation
- [ ] CONTAINS relationships
- [ ] Cross-content relationships
- [ ] Integration tests

**Estimated Time:** 4 hours

---

#### Task 3D.3: Processing API Router

**Why this matters:** The API exposes processing to frontend and external systems.

```python
# backend/app/routers/processing.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.tasks_processing import process_content_task
from app.services.storage import load_content
from app.db.session import get_db
from app.db.models_processing import ProcessingRun
from sqlalchemy import select

router = APIRouter(prefix="/api/processing", tags=["processing"])


class ProcessRequest(BaseModel):
    content_id: str
    config: Optional[dict] = None


@router.post("/trigger")
async def trigger_processing(request: ProcessRequest):
    """Trigger LLM processing for a content item."""
    content = await load_content(request.content_id)
    if not content:
        raise HTTPException(404, f"Content not found")
    
    task = process_content_task.delay(request.content_id, request.config)
    return {"status": "queued", "task_id": task.id}


@router.get("/status/{content_id}")
async def get_processing_status(content_id: str):
    """Get processing status for a content item."""
    async with get_db() as db:
        result = await db.execute(
            select(ProcessingRun)
            .where(ProcessingRun.content_id == content_id)
            .order_by(ProcessingRun.started_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()
        
        if not run:
            return {"status": "not_processed"}
        
        return {
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "processing_time": run.processing_time_seconds,
            "cost": run.estimated_cost_usd
        }


@router.get("/result/{content_id}")
async def get_processing_result(content_id: str):
    """Get full processing result."""
    async with get_db() as db:
        result = await db.execute(
            select(ProcessingRun)
            .where(ProcessingRun.content_id == content_id)
            .where(ProcessingRun.status == "completed")
            .order_by(ProcessingRun.started_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()
        
        if not run:
            raise HTTPException(404, "No completed processing found")
        
        return {
            "analysis": run.analysis,
            "summaries": run.summaries,
            "extraction": run.extraction,
            "tags": run.tags,
            "obsidian_path": run.obsidian_note_path
        }
```

**Deliverables:**
- [ ] `/trigger` endpoint
- [ ] `/status/{content_id}` endpoint
- [ ] `/result/{content_id}` endpoint
- [ ] Input validation and error handling

**Estimated Time:** 3 hours

---

## 4. Testing Strategy

### 4.1 Unit Tests

```
tests/
├── unit/
│   ├── test_llm_client.py         # LLM client with mocks
│   ├── test_content_analysis.py   # Analysis stage
│   ├── test_summarization.py      # Summary generation
│   ├── test_extraction.py         # Concept extraction
│   ├── test_tagging.py            # Tag assignment
│   ├── test_connections.py        # Connection discovery
│   ├── test_questions.py          # Question generation
│   ├── test_obsidian_generator.py # Note generation
│   └── test_validation.py         # Output validation
├── integration/
│   ├── test_pipeline.py           # Full pipeline
│   ├── test_neo4j_generator.py    # Graph operations
│   └── test_processing_api.py     # API endpoints
└── fixtures/
    ├── sample_paper.json          # Sample UnifiedContent
    ├── sample_article.json
    └── mock_llm_responses.json
```

### 4.2 Test Cases

| Stage | Test Case | Priority |
|-------|-----------|----------|
| LLM Client | Complete with task-specific model | High |
| LLM Client | Fallback on primary model failure | High |
| LLM Client | Cost tracking accumulation | Medium |
| Analysis | Classify paper vs article | High |
| Analysis | Extract key topics | High |
| Summarization | Generate all three levels | High |
| Summarization | Handle empty content gracefully | Medium |
| Extraction | Extract core concepts with definitions | High |
| Extraction | Parse JSON response correctly | High |
| Tagging | Validate tags against taxonomy | High |
| Tagging | Reject invalid tags | Medium |
| Connections | Find similar content via embedding | High |
| Connections | Evaluate connection strength | High |
| Questions | Generate difficulty-appropriate questions | High |
| Questions | Include hints and key points | Medium |
| Obsidian | Generate valid frontmatter YAML | High |
| Obsidian | Format wiki-links correctly | High |
| Neo4j | Create content node with embedding | High |
| Neo4j | Create relationships | High |
| Pipeline | Complete all stages | High |
| Pipeline | Handle stage failures gracefully | High |
| API | Trigger processing returns task ID | High |
| API | Status endpoint returns correct state | High |

### 4.3 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific stage tests
pytest tests/unit/test_extraction.py -v

# Run integration tests (requires Neo4j)
pytest tests/integration/ -v --neo4j-url=bolt://localhost:7687
```

---

## 5. Configuration

### 5.1 Processing Configuration

```python
# backend/app/config/processing.py

from pydantic_settings import BaseSettings

class ProcessingSettings(BaseSettings):
    # LLM Models (format: provider/model-name)
    LLM_MODEL_CLASSIFICATION: str = "openai/gpt-4o-mini"
    LLM_MODEL_SUMMARIZATION: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_MODEL_EXTRACTION: str = "openai/gpt-4o"
    LLM_MODEL_CONNECTIONS: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_MODEL_QUESTIONS: str = "openai/gpt-4o"
    LLM_MODEL_EMBEDDINGS: str = "openai/text-embedding-3-small"
    
    # Content Limits
    MAX_CONTENT_LENGTH: int = 100000
    MAX_ANNOTATIONS: int = 100
    SUMMARY_TRUNCATE_BRIEF: int = 10000
    SUMMARY_TRUNCATE_STANDARD: int = 25000
    SUMMARY_TRUNCATE_DETAILED: int = 40000
    EXTRACTION_TRUNCATE: int = 20000
    
    # Connection Discovery
    CONNECTION_SIMILARITY_THRESHOLD: float = 0.7
    CONNECTION_STRENGTH_THRESHOLD: float = 0.4
    MAX_CONNECTION_CANDIDATES: int = 10
    
    # Output Settings
    OBSIDIAN_VAULT_PATH: str = "/path/to/vault"
    NOTE_SUBFOLDER_BY_TYPE: bool = True
    GENERATE_NEO4J_NODES: bool = True
    
    # Quality Settings
    VALIDATE_OUTPUTS: bool = True
    MIN_SUMMARY_LENGTH: int = 100
    MIN_CONCEPTS: int = 1
    MIN_QUESTIONS: int = 2
    
    # Cost Management
    LITELLM_BUDGET_MAX: float = 200.0
    LITELLM_BUDGET_ALERT: float = 150.0
    LITELLM_LOG_COSTS: bool = True
    
    class Config:
        env_prefix = "PROCESSING_"
```

---

## 6. Timeline Summary

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 7 | 3A | Foundation | LLM client, Neo4j client, models, database schema |
| 8 | 3B | Processing Stages (1-4) | Analysis, summarization, extraction, tagging |
| 9 | 3B/3C | Processing Stages (5-7) + Orchestration | Connections, followups, questions, pipeline |
| 10 | 3D | Output Generation | Obsidian notes, Neo4j nodes, API, validation |

**Total Estimated Time:** ~65-75 hours

---

## 7. Success Criteria

### Functional Requirements

- [ ] Content analysis correctly classifies paper vs article vs book
- [ ] Summaries generated at all three levels (brief, standard, detailed)
- [ ] At least 3 core concepts extracted from typical academic paper
- [ ] Tags assigned from controlled vocabulary with 95% accuracy
- [ ] Connection discovery finds relevant existing content (when present)
- [ ] 3-5 mastery questions generated per content item
- [ ] Obsidian notes render correctly with valid frontmatter
- [ ] Neo4j nodes created with proper relationships
- [ ] Processing completes within 5 minutes for typical content

### Non-Functional Requirements

- [ ] Graceful degradation when LLM API unavailable (use fallback)
- [ ] Cost tracking accurate to within 10%
- [ ] Processing queue handles 50+ items without failure
- [ ] Logging sufficient for debugging failed processing
- [ ] Model selection configurable without code changes
- [ ] Retry logic handles transient API failures

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API rate limits | High | Medium | Implement request queuing, use fallback models |
| Inconsistent LLM outputs | Medium | High | JSON mode, validation, retry failed stages |
| High API costs | High | Medium | Cost tracking, budget alerts, model selection by task |
| Neo4j performance at scale | Medium | Low | Index optimization, batch operations |
| Prompt quality issues | Medium | Medium | Version prompts, A/B testing, user feedback |
| Embedding dimension mismatch | Low | Low | Validate embedding dimensions, use consistent model |

---

## 9. Dependencies on Other Phases

### Required Before Phase 3

- [x] Phase 1: Foundation & Infrastructure (Docker, FastAPI, databases)
- [x] Phase 2: Ingestion Layer (UnifiedContent, processing queue)

### Enables After Phase 3

- Phase 4: Knowledge Explorer UI (displays processed content)
- Phase 5: Practice Session UI (uses mastery questions)
- Phase 6: Spaced Repetition (uses questions for review)
- Phase 8: Learning Assistant (RAG over knowledge graph)

---

## 10. Open Questions

1. **Model Cost Optimization**: Should we use GPT-4o-mini for all stages during development and upgrade for production?
2. **Batch Processing**: Should multiple content items be processed in parallel or sequentially to manage costs?
3. **Tag Taxonomy Updates**: How should users propose new tags when the taxonomy has gaps?
4. **Connection Thresholds**: What similarity/strength thresholds produce the best connections without noise?
5. **Question Difficulty Calibration**: Should difficulty be based on content complexity or user's demonstrated mastery?
6. **Obsidian Template Customization**: Should users be able to customize note templates?
7. **Reprocessing Policy**: When prompts are updated, should all content be reprocessed automatically?

---

## Related Documents

- `design_docs/02_llm_processing_layer.md` — Original design specification
- `design_docs/01_ingestion_layer.md` — Upstream content source
- `design_docs/04_knowledge_graph_neo4j.md` — Neo4j schema details
- `design_docs/03_knowledge_hub_obsidian.md` — Obsidian note format
- `implementation_plan/01_ingestion_layer_implementation.md` — Previous phase

