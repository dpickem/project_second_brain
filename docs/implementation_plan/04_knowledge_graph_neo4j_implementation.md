# Knowledge Graph (Neo4j) Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Target Phase**: Phase 3-4 (Weeks 7-14, parallel with LLM Processing & Knowledge Hub)  
> **Design Doc**: `design_docs/04_knowledge_graph_neo4j.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Knowledge Graph component using Neo4j. The knowledge graph serves as the semantic backbone of the Second Brain system—storing concepts, relationships, and embeddings that power connection discovery, learning path generation, and semantic search.

### Architecture Overview

The Knowledge Graph integrates with the LLM Processing Layer (upstream) and supports both the Knowledge Hub (Obsidian) and Frontend (downstream):

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LLM Processing │────▶│   Neo4j Client   │────▶│  Knowledge API  │
│     Result      │     │   (Backend)      │     │   (FastAPI)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                        │
                        ┌───────▼────────┐        ┌──────▼───────┐
                        │     Neo4j      │        │   Frontend   │
                        │   Database     │        │   Graph UI   │
                        └───────┬────────┘        └──────────────┘
                                │
                        ┌───────▼────────┐
                        │  Obsidian Sync │
                        │   (Watcher)    │
                        └────────────────┘
```

### Why Neo4j?

| Requirement | Why Neo4j Fits |
|-------------|----------------|
| **Relationship queries** | Native graph traversal is 100-1000x faster than SQL JOINs for multi-hop queries |
| **Semantic search** | Built-in vector indexes for embedding similarity queries |
| **Schema flexibility** | Property graph model adapts as we discover new entity types |
| **Visualization** | Native export formats for D3/graph visualization libraries |

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Neo4j client service with connection pooling | Graph visualization UI (Phase 5) |
| Node types: Source, Concept, Topic, Person, Tag | Real-time collaborative editing |
| Relationship types per design doc | Multi-tenant isolation |
| Vector index creation and search | Neo4j cluster deployment |
| Hybrid search (vector + full-text) | Graph analytics algorithms (PageRank, etc.) |
| Import from LLM processing pipeline | Custom Neo4j plugins |
| Bi-directional Obsidian sync | External graph federation |
| Common query patterns | |
| API endpoints for graph operations | |

---

## 2. Prerequisites

### 2.1 Infrastructure (From Phase 1)

- [x] Docker Compose environment
- [x] Neo4j container configured and running
- [x] FastAPI backend skeleton
- [x] PostgreSQL for metadata
- [ ] LLM Processing Layer (Phase 3 - parallel implementation)

### 2.2 Dependencies to Install

```txt
# Add to backend/requirements.txt
neo4j>=5.15.0              # Official Neo4j Python driver
neo4j-graphrag>=0.3.0      # RAG utilities for Neo4j (optional, for future RAG pipeline)
numpy>=1.24.0              # Vector operations (may already be installed)
```

**Why these specific packages:**

| Package | Why This One | Alternatives Considered |
|---------|--------------|------------------------|
| `neo4j` | Official async driver with connection pooling, transaction management, and full Cypher support | `py2neo` (community, less maintained), `neomodel` (OGM, adds unnecessary abstraction) |
| `neo4j-graphrag` | Official utilities for vector search and RAG patterns. Provides `VectorRetriever` for semantic search | Building from scratch (more work, less tested) |
| `numpy` | Standard for vector operations, embedding manipulation | `torch` (overkill for vector math only) |

### 2.3 Environment Variables

```bash
# .env file additions (some may already exist from Phase 1)
# Neo4j Connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>
NEO4J_DATABASE=secondbrain

# Vector Search Configuration
NEO4J_VECTOR_DIMENSIONS=1536      # OpenAI ada-002 embedding size
NEO4J_VECTOR_SIMILARITY=cosine    # cosine | euclidean

# Sync Configuration
NEO4J_SYNC_BATCH_SIZE=100         # Batch size for bulk imports
NEO4J_SYNC_ENABLED=true           # Enable Obsidian sync
```

### 2.4 Neo4j Configuration

The Neo4j container should be configured with adequate memory for vector operations:

```yaml
# docker-compose.yml neo4j service additions
neo4j:
  image: neo4j:5-enterprise  # Enterprise for vector indexes (or 5-community with plugins)
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    - NEO4J_PLUGINS=["apoc"]  # Required for advanced queries
    - NEO4J_dbms_memory_heap_initial__size=512m
    - NEO4J_dbms_memory_heap_max__size=1G
    - NEO4J_dbms_memory_pagecache_size=512m
```

---

## 3. Implementation Phases

### Phase 3A: Foundation (Week 7-8)

#### Task 3A.1: Project Structure Setup

**Why this matters:** A well-organized module structure separates concerns: client management, schema operations, queries, and synchronization. This enables independent testing and clear dependency boundaries.

Create the Neo4j service module:

```
backend/
├── app/
│   ├── services/
│   │   ├── knowledge_graph/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Neo4j async client with connection pooling
│   │   │   ├── schema.py           # Schema creation and validation
│   │   │   ├── models.py           # Pydantic models for nodes/relationships
│   │   │   ├── queries.py          # Common query patterns
│   │   │   ├── vector_search.py    # Vector and hybrid search
│   │   │   ├── import_service.py   # Import from processing pipeline
│   │   │   └── sync.py             # Obsidian sync operations
│   │   └── ...
│   ├── routers/
│   │   └── knowledge.py            # Knowledge graph API endpoints
│   └── ...
```

**Deliverables:**
- [ ] Directory structure created
- [ ] `__init__.py` files with proper exports
- [ ] Type stubs and base classes defined

**Estimated Time:** 2 hours

---

#### Task 3A.2: Neo4j Async Client

**Why this matters:** A robust client with connection pooling, retry logic, and proper async support is essential for production use. The driver should handle transient failures gracefully and provide clean transaction management.

```python
# backend/app/services/knowledge_graph/client.py

from contextlib import asynccontextmanager
from typing import Any, Optional
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client with connection pooling and retry logic.
    
    Usage:
        async with neo4j_client.session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            records = [record async for record in result]
    """
    
    _instance: Optional["Neo4jClient"] = None
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: float = 60.0
    ):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or getattr(settings, 'NEO4J_DATABASE', 'neo4j')
        
        self._driver: Optional[AsyncDriver] = None
        self._max_pool_size = max_connection_pool_size
        self._acquisition_timeout = connection_acquisition_timeout
    
    async def connect(self) -> None:
        """Initialize the Neo4j driver connection."""
        if self._driver is not None:
            return
        
        self._driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_pool_size=self._max_pool_size,
            connection_acquisition_timeout=self._acquisition_timeout
        )
        
        # Verify connectivity
        await self._driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {self.uri}")
    
    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    @asynccontextmanager
    async def session(self, **kwargs):
        """Get a session from the connection pool.
        
        Usage:
            async with client.session() as session:
                await session.run(...)
        """
        if self._driver is None:
            await self.connect()
        
        session = self._driver.session(database=self.database, **kwargs)
        try:
            yield session
        finally:
            await session.close()
    
    async def run(
        self,
        query: str,
        parameters: dict[str, Any] = None,
        **kwargs
    ) -> list[dict]:
        """Execute a query and return results as list of dicts.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        async with self.session() as session:
            result = await session.run(query, parameters or {}, **kwargs)
            records = [dict(record) async for record in result]
            return records
    
    async def run_single(
        self,
        query: str,
        parameters: dict[str, Any] = None
    ) -> Optional[dict]:
        """Execute a query expecting a single result."""
        results = await self.run(query, parameters)
        return results[0] if results else None
    
    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] = None
    ) -> dict:
        """Execute a write transaction with automatic retry.
        
        Returns:
            Summary of the write operation
        """
        async def _write_tx(tx):
            result = await tx.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }
        
        async with self.session() as session:
            return await session.execute_write(_write_tx)
    
    async def health_check(self) -> dict:
        """Check Neo4j connection health."""
        try:
            if self._driver is None:
                await self.connect()
            
            result = await self.run_single("RETURN 1 as ping")
            return {
                "status": "healthy",
                "connected": True,
                "uri": self.uri,
                "database": self.database
            }
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Singleton instance
_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create singleton Neo4j client."""
    global _client
    if _client is None:
        _client = Neo4jClient()
        await _client.connect()
    return _client


async def close_neo4j_client() -> None:
    """Close the singleton Neo4j client."""
    global _client
    if _client:
        await _client.close()
        _client = None
```

**Deliverables:**
- [ ] `Neo4jClient` class with async support
- [ ] Connection pooling configuration
- [ ] Session context manager
- [ ] Write transaction with retry
- [ ] Health check method
- [ ] Singleton accessor functions
- [ ] Unit tests for client operations

**Estimated Time:** 4 hours

---

#### Task 3A.3: Pydantic Models for Graph Entities

**Why this matters:** Type-safe models ensure consistency between Python code and Neo4j schema. Pydantic provides validation, serialization, and clear documentation of the data structures.

```python
# backend/app/services/knowledge_graph/models.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Node types in the knowledge graph."""
    SOURCE = "Source"
    CONCEPT = "Concept"
    TOPIC = "Topic"
    PERSON = "Person"
    TAG = "Tag"
    MASTERY_QUESTION = "MasteryQuestion"


class RelationshipType(str, Enum):
    """Relationship types between nodes."""
    # Document relationships
    CITES = "CITES"
    EXTENDS = "EXTENDS"
    CONTRADICTS = "CONTRADICTS"
    RELATES_TO = "RELATES_TO"
    
    # Concept relationships
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    SUBCLASS_OF = "SUBCLASS_OF"
    USED_IN = "USED_IN"
    
    # Source-Concept relationships
    INTRODUCES = "INTRODUCES"
    EXPLAINS = "EXPLAINS"
    APPLIES = "APPLIES"
    
    # Person relationships
    AUTHORED = "AUTHORED"
    WORKS_ON = "WORKS_ON"
    
    # Tag relationships
    TAGGED_WITH = "TAGGED_WITH"
    
    # Topic relationships
    SUBTOPIC_OF = "SUBTOPIC_OF"
    BELONGS_TO = "BELONGS_TO"
    
    # Learning relationships
    TESTS = "TESTS"
    FROM_SOURCE = "FROM_SOURCE"
    
    # Generic
    LINKS_TO = "LINKS_TO"


class ContentType(str, Enum):
    """Content types for Source nodes."""
    PAPER = "paper"
    ARTICLE = "article"
    BOOK = "book"
    CODE = "code"
    IDEA = "idea"


class ComplexityLevel(str, Enum):
    """Complexity levels for concepts."""
    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# --- Node Models ---

class SourceNode(BaseModel):
    """Source document node (paper, article, book, etc.)."""
    id: str = Field(..., description="Unique identifier (UUID)")
    type: ContentType = Field(..., description="Content type")
    title: str = Field(..., description="Document title")
    authors: list[str] = Field(default_factory=list, description="Author names")
    source_url: Optional[str] = Field(None, description="Original URL")
    created_at: Optional[datetime] = Field(None, description="Original creation date")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    summary: Optional[str] = Field(None, description="Document summary")
    embedding: Optional[list[float]] = Field(None, description="1536-dim embedding vector")
    obsidian_path: Optional[str] = Field(None, description="Path in Obsidian vault")
    
    class Config:
        use_enum_values = True


class ConceptNode(BaseModel):
    """Extracted concept node."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Concept name")
    definition: Optional[str] = Field(None, description="Concept definition")
    domain: Optional[str] = Field(None, description="Domain (ml, systems, etc.)")
    complexity: ComplexityLevel = Field(
        ComplexityLevel.INTERMEDIATE, description="Complexity level"
    )
    embedding: Optional[list[float]] = Field(None, description="Embedding vector")
    obsidian_path: Optional[str] = Field(None, description="Path in vault")
    
    class Config:
        use_enum_values = True


class TopicNode(BaseModel):
    """Topic category node for hierarchical organization."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Topic name (e.g., 'machine-learning')")
    path: str = Field(..., description="Hierarchical path (e.g., 'ml/deep-learning')")
    description: Optional[str] = Field(None, description="Topic description")
    parent_path: Optional[str] = Field(None, description="Parent topic path")


class PersonNode(BaseModel):
    """Person node (author, researcher)."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Full name")
    affiliation: Optional[str] = Field(None, description="Organization")
    homepage: Optional[str] = Field(None, description="Personal website")


class TagNode(BaseModel):
    """Tag from controlled vocabulary."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Tag name (e.g., 'ml/transformers')")
    category: Optional[str] = Field(None, description="Tag category")


class MasteryQuestionNode(BaseModel):
    """Learning/mastery question node."""
    id: str = Field(..., description="Unique identifier")
    question: str = Field(..., description="Question text")
    source_id: str = Field(..., description="ID of source document")
    difficulty: str = Field("intermediate", description="Question difficulty")
    hints: list[str] = Field(default_factory=list, description="Hints")
    key_points: list[str] = Field(default_factory=list, description="Key points for answer")


# --- Relationship Models ---

class Relationship(BaseModel):
    """Base relationship model."""
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    type: RelationshipType = Field(..., description="Relationship type")
    properties: dict = Field(default_factory=dict, description="Additional properties")
    
    class Config:
        use_enum_values = True


class ConnectionRelationship(Relationship):
    """Connection between sources with explanation."""
    strength: float = Field(0.5, ge=0.0, le=1.0, description="Connection strength")
    explanation: Optional[str] = Field(None, description="Why these are connected")


# --- Query Result Models ---

class SearchResult(BaseModel):
    """Vector/hybrid search result."""
    id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    node_type: NodeType
    score: float = Field(..., description="Similarity score")
    
    class Config:
        use_enum_values = True


class PathResult(BaseModel):
    """Path query result (e.g., shortest path between concepts)."""
    nodes: list[dict] = Field(..., description="Nodes in path")
    relationships: list[dict] = Field(..., description="Relationships in path")
    length: int = Field(..., description="Path length")


class GraphData(BaseModel):
    """Graph data for visualization."""
    nodes: list[dict] = Field(..., description="Graph nodes")
    edges: list[dict] = Field(..., description="Graph edges")
    node_count: int = Field(..., description="Total node count")
    edge_count: int = Field(..., description="Total edge count")
```

**Deliverables:**
- [ ] Node type models (Source, Concept, Topic, Person, Tag, MasteryQuestion)
- [ ] Relationship type enums
- [ ] Relationship models with properties
- [ ] Search result models
- [ ] Path result models
- [ ] Graph data model for visualization
- [ ] Unit tests for model validation

**Estimated Time:** 3 hours

---

#### Task 3A.4: Schema Creation Service

**Why this matters:** The schema service creates indexes, constraints, and validates the database state. Running this on startup ensures the database is ready for queries and imports.

```python
# backend/app/services/knowledge_graph/schema.py

from typing import Optional
import logging

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages Neo4j schema: constraints, indexes, and vector indexes.
    
    Run on application startup to ensure schema is initialized.
    """
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    async def initialize_schema(self) -> dict:
        """Initialize all schema elements.
        
        Returns:
            Summary of created schema elements
        """
        results = {
            "constraints": [],
            "indexes": [],
            "vector_indexes": [],
            "fulltext_indexes": []
        }
        
        # Create constraints
        constraints = await self._create_constraints()
        results["constraints"] = constraints
        
        # Create regular indexes
        indexes = await self._create_indexes()
        results["indexes"] = indexes
        
        # Create vector indexes
        vector_indexes = await self._create_vector_indexes()
        results["vector_indexes"] = vector_indexes
        
        # Create full-text indexes
        fulltext_indexes = await self._create_fulltext_indexes()
        results["fulltext_indexes"] = fulltext_indexes
        
        logger.info(f"Schema initialized: {results}")
        return results
    
    async def _create_constraints(self) -> list[str]:
        """Create uniqueness constraints."""
        client = await self._get_client()
        created = []
        
        constraints = [
            ("source_id", "Source", "id"),
            ("concept_name", "Concept", "name"),
            ("topic_id", "Topic", "id"),
            ("person_id", "Person", "id"),
            ("tag_name", "Tag", "name"),
            ("question_id", "MasteryQuestion", "id"),
        ]
        
        for name, label, property in constraints:
            try:
                await client.run(f"""
                    CREATE CONSTRAINT {name} IF NOT EXISTS
                    FOR (n:{label}) REQUIRE n.{property} IS UNIQUE
                """)
                created.append(name)
                logger.debug(f"Created constraint: {name}")
            except Exception as e:
                logger.warning(f"Constraint {name} may already exist: {e}")
        
        return created
    
    async def _create_indexes(self) -> list[str]:
        """Create regular lookup indexes."""
        client = await self._get_client()
        created = []
        
        indexes = [
            ("source_type", "Source", "type"),
            ("source_obsidian_path", "Source", "obsidian_path"),
            ("concept_domain", "Concept", "domain"),
            ("concept_complexity", "Concept", "complexity"),
            ("topic_path", "Topic", "path"),
            ("tag_category", "Tag", "category"),
        ]
        
        for name, label, property in indexes:
            try:
                await client.run(f"""
                    CREATE INDEX {name} IF NOT EXISTS
                    FOR (n:{label}) ON (n.{property})
                """)
                created.append(name)
                logger.debug(f"Created index: {name}")
            except Exception as e:
                logger.warning(f"Index {name} may already exist: {e}")
        
        return created
    
    async def _create_vector_indexes(self) -> list[str]:
        """Create vector indexes for semantic search."""
        client = await self._get_client()
        created = []
        
        vector_indexes = [
            ("source_embedding", "Source", "embedding", 1536),
            ("concept_embedding", "Concept", "embedding", 1536),
        ]
        
        for name, label, property, dimensions in vector_indexes:
            try:
                await client.run(f"""
                    CREATE VECTOR INDEX {name} IF NOT EXISTS
                    FOR (n:{label})
                    ON (n.{property})
                    OPTIONS {{
                        indexConfig: {{
                            `vector.dimensions`: {dimensions},
                            `vector.similarity_function`: 'cosine'
                        }}
                    }}
                """)
                created.append(name)
                logger.info(f"Created vector index: {name}")
            except Exception as e:
                logger.warning(f"Vector index {name} creation failed: {e}")
        
        return created
    
    async def _create_fulltext_indexes(self) -> list[str]:
        """Create full-text search indexes."""
        client = await self._get_client()
        created = []
        
        fulltext_indexes = [
            ("source_text", "Source", ["title", "summary"]),
            ("concept_text", "Concept", ["name", "definition"]),
        ]
        
        for name, label, properties in fulltext_indexes:
            props_str = ", ".join([f"n.{p}" for p in properties])
            try:
                await client.run(f"""
                    CREATE FULLTEXT INDEX {name} IF NOT EXISTS
                    FOR (n:{label})
                    ON EACH [{props_str}]
                """)
                created.append(name)
                logger.info(f"Created fulltext index: {name}")
            except Exception as e:
                logger.warning(f"Fulltext index {name} creation failed: {e}")
        
        return created
    
    async def verify_schema(self) -> dict:
        """Verify schema is correctly set up."""
        client = await self._get_client()
        
        # Get existing indexes
        indexes = await client.run("SHOW INDEXES")
        
        # Get existing constraints
        constraints = await client.run("SHOW CONSTRAINTS")
        
        return {
            "indexes": [idx.get("name") for idx in indexes],
            "constraints": [c.get("name") for c in constraints],
            "status": "verified"
        }
    
    async def drop_all(self, confirm: bool = False) -> dict:
        """Drop all schema elements. Use with caution!
        
        Args:
            confirm: Must be True to actually drop
        """
        if not confirm:
            return {"status": "aborted", "message": "confirm=True required"}
        
        client = await self._get_client()
        
        # Drop all indexes
        await client.run("CALL apoc.schema.assert({}, {})")
        
        return {"status": "dropped", "message": "All schema elements removed"}


async def initialize_neo4j_schema() -> dict:
    """Initialize Neo4j schema on application startup."""
    manager = SchemaManager()
    return await manager.initialize_schema()
```

**Deliverables:**
- [ ] `SchemaManager` class
- [ ] Constraint creation for unique IDs
- [ ] Regular index creation for lookups
- [ ] Vector index creation (1536 dimensions for OpenAI embeddings)
- [ ] Full-text index creation for search
- [ ] Schema verification method
- [ ] Startup initialization function
- [ ] Unit tests for schema operations

**Estimated Time:** 4 hours

---

### Phase 3B: Core Operations (Week 9-10)

#### Task 3B.1: Node CRUD Operations

**Why this matters:** Clean CRUD operations provide the foundation for all data manipulation. Using MERGE instead of CREATE ensures idempotency—running the same import twice won't create duplicates.

```python
# backend/app/services/knowledge_graph/operations.py

from typing import Optional, Any
from datetime import datetime
import logging

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.services.knowledge_graph.models import (
    SourceNode, ConceptNode, TopicNode, PersonNode, TagNode,
    MasteryQuestionNode, NodeType, RelationshipType
)

logger = logging.getLogger(__name__)


class NodeOperations:
    """CRUD operations for graph nodes."""
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    # --- Source Node Operations ---
    
    async def create_source(self, source: SourceNode) -> dict:
        """Create or update a Source node."""
        client = await self._get_client()
        
        query = """
        MERGE (s:Source {id: $id})
        SET s.type = $type,
            s.title = $title,
            s.authors = $authors,
            s.source_url = $source_url,
            s.created_at = $created_at,
            s.processed_at = $processed_at,
            s.summary = $summary,
            s.obsidian_path = $obsidian_path
        RETURN s
        """
        
        # Handle embedding separately (large property)
        params = source.model_dump(exclude={"embedding"})
        params["created_at"] = params["created_at"].isoformat() if params.get("created_at") else None
        params["processed_at"] = params["processed_at"].isoformat() if params.get("processed_at") else None
        
        result = await client.run_single(query, params)
        
        # Set embedding if provided
        if source.embedding:
            await self._set_embedding("Source", source.id, source.embedding)
        
        logger.debug(f"Created/updated Source: {source.id}")
        return result
    
    async def get_source(self, source_id: str) -> Optional[dict]:
        """Get a Source node by ID."""
        client = await self._get_client()
        return await client.run_single(
            "MATCH (s:Source {id: $id}) RETURN s",
            {"id": source_id}
        )
    
    async def delete_source(self, source_id: str) -> bool:
        """Delete a Source node and its relationships."""
        client = await self._get_client()
        result = await client.execute_write(
            "MATCH (s:Source {id: $id}) DETACH DELETE s",
            {"id": source_id}
        )
        return result.get("nodes_deleted", 0) > 0
    
    # --- Concept Node Operations ---
    
    async def create_concept(self, concept: ConceptNode) -> dict:
        """Create or update a Concept node."""
        client = await self._get_client()
        
        query = """
        MERGE (c:Concept {name: $name})
        SET c.id = $id,
            c.definition = $definition,
            c.domain = $domain,
            c.complexity = $complexity,
            c.obsidian_path = $obsidian_path
        RETURN c
        """
        
        params = concept.model_dump(exclude={"embedding"})
        result = await client.run_single(query, params)
        
        if concept.embedding:
            await self._set_embedding("Concept", concept.name, concept.embedding, "name")
        
        logger.debug(f"Created/updated Concept: {concept.name}")
        return result
    
    async def get_concept(self, name: str) -> Optional[dict]:
        """Get a Concept node by name."""
        client = await self._get_client()
        return await client.run_single(
            "MATCH (c:Concept {name: $name}) RETURN c",
            {"name": name}
        )
    
    # --- Topic Node Operations ---
    
    async def create_topic(self, topic: TopicNode) -> dict:
        """Create or update a Topic node."""
        client = await self._get_client()
        
        query = """
        MERGE (t:Topic {id: $id})
        SET t.name = $name,
            t.path = $path,
            t.description = $description,
            t.parent_path = $parent_path
        RETURN t
        """
        
        result = await client.run_single(query, topic.model_dump())
        
        # Create SUBTOPIC_OF relationship if parent exists
        if topic.parent_path:
            await client.run("""
                MATCH (child:Topic {id: $child_id})
                MATCH (parent:Topic {path: $parent_path})
                MERGE (child)-[:SUBTOPIC_OF]->(parent)
            """, {"child_id": topic.id, "parent_path": topic.parent_path})
        
        return result
    
    # --- Person Node Operations ---
    
    async def get_or_create_person_by_name(self, name: str) -> dict:
        """Get or create a Person node by name."""
        client = await self._get_client()
        person_id = name.lower().replace(" ", "_")
        
        return await client.run_single("""
            MERGE (p:Person {name: $name})
            ON CREATE SET p.id = $id
            RETURN p
        """, {"name": name, "id": person_id})
    
    # --- Tag Node Operations ---
    
    async def get_or_create_tag(self, tag_name: str, category: str = None) -> dict:
        """Get or create a Tag node by name."""
        client = await self._get_client()
        
        return await client.run_single("""
            MERGE (t:Tag {name: $name})
            ON CREATE SET t.id = $id, t.category = $category
            RETURN t
        """, {
            "name": tag_name,
            "id": tag_name.lower().replace("/", "_"),
            "category": category
        })
    
    # --- Helper Methods ---
    
    async def _set_embedding(
        self, label: str, identifier: str, 
        embedding: list[float], id_property: str = "id"
    ) -> None:
        """Set embedding vector on a node."""
        client = await self._get_client()
        await client.run(f"""
            MATCH (n:{label} {{{id_property}: $identifier}})
            SET n.embedding = $embedding
        """, {"identifier": identifier, "embedding": embedding})
    
    async def node_exists(self, label: str, identifier: str, id_property: str = "id") -> bool:
        """Check if a node exists."""
        client = await self._get_client()
        result = await client.run_single(f"""
            MATCH (n:{label} {{{id_property}: $identifier}})
            RETURN count(n) as count
        """, {"identifier": identifier})
        return result.get("count", 0) > 0


class RelationshipOperations:
    """Operations for creating and managing relationships."""
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    async def create_relationship(
        self, source_label: str, source_id: str,
        target_label: str, target_id: str,
        rel_type: RelationshipType,
        properties: dict = None,
        source_id_prop: str = "id",
        target_id_prop: str = "id"
    ) -> dict:
        """Create a relationship between two nodes."""
        client = await self._get_client()
        
        props_clause = ""
        if properties:
            props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
            props_clause = f" {{{props_str}}}"
        
        query = f"""
        MATCH (source:{source_label} {{{source_id_prop}: $source_id}})
        MATCH (target:{target_label} {{{target_id_prop}: $target_id}})
        MERGE (source)-[r:{rel_type.value}{props_clause}]->(target)
        RETURN r
        """
        
        params = {"source_id": source_id, "target_id": target_id}
        if properties:
            params.update(properties)
        
        return await client.run_single(query, params)
    
    async def source_explains_concept(self, source_id: str, concept_name: str) -> dict:
        """Create EXPLAINS relationship between Source and Concept."""
        return await self.create_relationship(
            "Source", source_id, "Concept", concept_name,
            RelationshipType.EXPLAINS, target_id_prop="name"
        )
    
    async def concept_prerequisite_for(self, prereq_name: str, concept_name: str) -> dict:
        """Create PREREQUISITE_FOR relationship between concepts."""
        return await self.create_relationship(
            "Concept", prereq_name, "Concept", concept_name,
            RelationshipType.PREREQUISITE_FOR,
            source_id_prop="name", target_id_prop="name"
        )
    
    async def person_authored_source(self, person_name: str, source_id: str) -> dict:
        """Create AUTHORED relationship."""
        return await self.create_relationship(
            "Person", person_name, "Source", source_id,
            RelationshipType.AUTHORED, source_id_prop="name"
        )
    
    async def source_tagged_with(self, source_id: str, tag_name: str) -> dict:
        """Create TAGGED_WITH relationship."""
        return await self.create_relationship(
            "Source", source_id, "Tag", tag_name,
            RelationshipType.TAGGED_WITH, target_id_prop="name"
        )
    
    async def clear_outgoing_relationships(
        self, label: str, node_id: str, 
        rel_type: RelationshipType = None, id_prop: str = "id"
    ) -> int:
        """Remove all outgoing relationships of a type from a node."""
        client = await self._get_client()
        rel_clause = f"[r:{rel_type.value}]" if rel_type else "[r]"
        
        result = await client.execute_write(f"""
            MATCH (n:{label} {{{id_prop}: $node_id}})-{rel_clause}->()
            DELETE r
        """, {"node_id": node_id})
        
        return result.get("relationships_deleted", 0)
```

**Deliverables:**
- [ ] `NodeOperations` class for all node types
- [ ] MERGE-based create/update operations
- [ ] Get operations by ID and name
- [ ] Delete operations with relationship cleanup
- [ ] `RelationshipOperations` class
- [ ] Type-specific relationship helpers
- [ ] Relationship clearing for sync operations
- [ ] Unit tests for all CRUD operations

**Estimated Time:** 5 hours

---

#### Task 3B.2: Vector Search Service

**Why this matters:** Vector search enables semantic discovery—finding related content even when exact keywords don't match. This is critical for "what connects X to Y?" and "find related concepts" queries.

```python
# backend/app/services/knowledge_graph/vector_search.py

from typing import Optional
import logging

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.services.knowledge_graph.models import SearchResult, NodeType

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Vector and hybrid search operations for the knowledge graph."""
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    async def vector_search(
        self, embedding: list[float],
        node_type: NodeType = NodeType.SOURCE,
        top_k: int = 10, min_score: float = 0.7
    ) -> list[SearchResult]:
        """Find similar nodes by embedding vector.
        
        Args:
            embedding: Query embedding vector (1536 dimensions)
            node_type: Type of nodes to search (Source or Concept)
            top_k: Maximum number of results
            min_score: Minimum similarity score (0-1)
        """
        client = await self._get_client()
        index_name = f"{node_type.value.lower()}_embedding"
        
        query = """
        CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
        YIELD node, score
        WHERE score >= $min_score
        RETURN 
            node.id as id,
            node.title as title,
            node.name as name,
            node.summary as summary,
            node.definition as definition,
            labels(node)[0] as node_type,
            score
        ORDER BY score DESC
        """
        
        results = await client.run(query, {
            "index_name": index_name, "top_k": top_k,
            "embedding": embedding, "min_score": min_score
        })
        
        return [
            SearchResult(
                id=r["id"],
                title=r.get("title") or r.get("name"),
                summary=r.get("summary") or r.get("definition"),
                node_type=NodeType(r["node_type"]),
                score=r["score"]
            )
            for r in results
        ]
    
    async def hybrid_search(
        self, query_text: str, embedding: list[float],
        node_type: NodeType = NodeType.SOURCE,
        top_k: int = 10,
        text_weight: float = 0.3, vector_weight: float = 0.7
    ) -> list[SearchResult]:
        """Combine vector and full-text search for better results."""
        client = await self._get_client()
        
        index_name = f"{node_type.value.lower()}_embedding"
        text_index = f"{node_type.value.lower()}_text"
        
        query = """
        // Full-text search
        CALL db.index.fulltext.queryNodes($text_index, $query_text)
        YIELD node as textNode, score as textScore
        WITH collect({node: textNode, score: textScore}) as textResults
        
        // Vector search
        CALL db.index.vector.queryNodes($vector_index, $top_k, $embedding)
        YIELD node as vectorNode, score as vectorScore
        WITH textResults, collect({node: vectorNode, score: vectorScore}) as vectorResults
        
        // Combine and deduplicate
        WITH textResults + vectorResults as allResults
        UNWIND allResults as result
        WITH result.node as node, 
             CASE WHEN result.score < 1 THEN result.score * $vector_weight 
                  ELSE result.score * $text_weight END as weightedScore
        WITH node, max(weightedScore) as score
        RETURN 
            node.id as id, node.title as title, node.name as name,
            node.summary as summary, node.definition as definition,
            labels(node)[0] as node_type, score
        ORDER BY score DESC
        LIMIT $top_k
        """
        
        results = await client.run(query, {
            "text_index": text_index, "vector_index": index_name,
            "query_text": query_text, "embedding": embedding,
            "top_k": top_k, "text_weight": text_weight, "vector_weight": vector_weight
        })
        
        return [
            SearchResult(
                id=r["id"], title=r.get("title") or r.get("name"),
                summary=r.get("summary") or r.get("definition"),
                node_type=NodeType(r["node_type"]), score=r["score"]
            )
            for r in results
        ]
    
    async def find_similar_sources(
        self, source_id: str, top_k: int = 5, min_score: float = 0.75
    ) -> list[SearchResult]:
        """Find sources similar to a given source using its embedding."""
        client = await self._get_client()
        
        source = await client.run_single(
            "MATCH (s:Source {id: $id}) RETURN s.embedding as embedding",
            {"id": source_id}
        )
        
        if not source or not source.get("embedding"):
            return []
        
        results = await self.vector_search(
            embedding=source["embedding"],
            node_type=NodeType.SOURCE,
            top_k=top_k + 1, min_score=min_score
        )
        
        return [r for r in results if r.id != source_id][:top_k]
    
    async def semantic_search(
        self, query_embedding: list[float], top_k: int = 10,
        min_score: float = 0.7,
        include_sources: bool = True, include_concepts: bool = True
    ) -> list[SearchResult]:
        """Search across both Sources and Concepts."""
        results = []
        
        if include_sources:
            results.extend(await self.vector_search(
                query_embedding, NodeType.SOURCE, top_k, min_score
            ))
        
        if include_concepts:
            results.extend(await self.vector_search(
                query_embedding, NodeType.CONCEPT, top_k, min_score
            ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
```

**Deliverables:**
- [ ] `VectorSearchService` class
- [ ] Pure vector search by embedding
- [ ] Hybrid search combining vector and full-text
- [ ] Similar source discovery
- [ ] Cross-type semantic search
- [ ] Unit tests with mock embeddings

**Estimated Time:** 4 hours

---

#### Task 3B.3: Common Query Patterns

**Why this matters:** Pre-built query patterns encapsulate complex Cypher logic for common use cases: learning paths, connection discovery, knowledge exploration.

```python
# backend/app/services/knowledge_graph/queries.py

from typing import Optional
import logging

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.services.knowledge_graph.models import PathResult, GraphData

logger = logging.getLogger(__name__)


class KnowledgeQueries:
    """Common query patterns for knowledge discovery."""
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    async def find_path_between_concepts(
        self, concept_a: str, concept_b: str, max_hops: int = 5
    ) -> Optional[PathResult]:
        """Find the shortest path between two concepts.
        
        Answers: "What connects concept A to concept B?"
        """
        client = await self._get_client()
        
        result = await client.run_single(f"""
            MATCH path = shortestPath(
                (a:Concept {{name: $concept_a}})-[*..{max_hops}]-(b:Concept {{name: $concept_b}})
            )
            RETURN 
                [n IN nodes(path) | {{id: n.id, name: n.name, labels: labels(n)}}] as nodes,
                [r IN relationships(path) | {{type: type(r), properties: properties(r)}}] as relationships,
                length(path) as length
        """, {"concept_a": concept_a, "concept_b": concept_b})
        
        if not result:
            return None
        
        return PathResult(
            nodes=result["nodes"],
            relationships=result["relationships"],
            length=result["length"]
        )
    
    async def get_concept_prerequisites(
        self, concept_name: str, max_depth: int = 10
    ) -> list[dict]:
        """Get all prerequisites for understanding a concept.
        
        Answers: "What do I need to know before learning X?"
        """
        client = await self._get_client()
        
        return await client.run(f"""
            MATCH path = (prereq:Concept)-[:PREREQUISITE_FOR*1..{max_depth}]->(target:Concept {{name: $concept}})
            WITH prereq, min(length(path)) as depth
            RETURN 
                prereq.name as name, prereq.definition as definition,
                prereq.complexity as complexity, prereq.domain as domain, depth
            ORDER BY depth ASC
        """, {"concept": concept_name})
    
    async def get_learning_path(self, target_concept: str) -> list[dict]:
        """Generate a learning path to understand a concept."""
        client = await self._get_client()
        
        return await client.run("""
            MATCH path = (start:Concept)-[:PREREQUISITE_FOR*]->(end:Concept {name: $target})
            WITH nodes(path) as pathNodes, length(path) as depth
            UNWIND pathNodes as concept
            WITH DISTINCT concept, min(depth) as minDepth
            RETURN 
                concept.name as name, concept.definition as definition,
                concept.complexity as complexity, minDepth as order
            ORDER BY order DESC
        """, {"target": target_concept})
    
    async def get_topic_knowledge(self, topic_name: str, limit: int = 50) -> dict:
        """Get all knowledge about a topic.
        
        Answers: "What do I know about topic X?"
        """
        client = await self._get_client()
        
        sources = await client.run("""
            MATCH (t:Topic {name: $topic})<-[:BELONGS_TO]-(s:Source)
            RETURN s.id as id, s.title as title, s.type as type, s.processed_at as processed_at
            ORDER BY s.processed_at DESC
            LIMIT $limit
        """, {"topic": topic_name, "limit": limit})
        
        concepts = await client.run("""
            MATCH (t:Topic {name: $topic})<-[:BELONGS_TO]-(s:Source)-[:EXPLAINS]->(c:Concept)
            RETURN DISTINCT c.name as name, c.definition as definition,
                c.complexity as complexity, count(s) as source_count
            ORDER BY source_count DESC
            LIMIT $limit
        """, {"topic": topic_name, "limit": limit})
        
        return {
            "topic": topic_name, "sources": sources, "concepts": concepts,
            "source_count": len(sources), "concept_count": len(concepts)
        }
    
    async def find_unexpected_connections(
        self, source_id: str, min_hops: int = 2, max_hops: int = 3, limit: int = 5
    ) -> list[dict]:
        """Find sources connected through indirect concept relationships."""
        client = await self._get_client()
        
        return await client.run(f"""
            MATCH (s1:Source {{id: $source_id}})-[:EXPLAINS]->(c1:Concept)
            MATCH (c1)-[:RELATES_TO*{min_hops}..{max_hops}]-(c2:Concept)<-[:EXPLAINS]-(s2:Source)
            WHERE s1 <> s2
            WITH s2, collect(DISTINCT c2.name) as shared_concepts
            RETURN s2.id as id, s2.title as title, s2.type as type,
                shared_concepts, size(shared_concepts) as connection_count
            ORDER BY connection_count DESC
            LIMIT $limit
        """, {"source_id": source_id, "limit": limit})
    
    async def get_graph_stats(self) -> dict:
        """Get overall graph statistics."""
        client = await self._get_client()
        
        result = await client.run_single("""
            MATCH (n)
            WITH labels(n)[0] as label, count(n) as count
            RETURN collect({label: label, count: count}) as node_counts
        """)
        
        rel_result = await client.run_single("""
            MATCH ()-[r]->()
            WITH type(r) as type, count(r) as count
            RETURN collect({type: type, count: count}) as rel_counts
        """)
        
        return {
            "nodes": {item["label"]: item["count"] for item in result.get("node_counts", [])},
            "relationships": {item["type"]: item["count"] for item in rel_result.get("rel_counts", [])}
        }


class GraphVisualizationQueries:
    """Queries optimized for graph visualization."""
    
    def __init__(self, client: Neo4jClient = None):
        self._client = client
    
    async def _get_client(self) -> Neo4jClient:
        if self._client is None:
            self._client = await get_neo4j_client()
        return self._client
    
    async def get_subgraph(
        self, center_id: str, center_type: str = "Source",
        depth: int = 2, max_nodes: int = 100
    ) -> GraphData:
        """Get a subgraph centered on a specific node."""
        client = await self._get_client()
        
        result = await client.run_single(f"""
            MATCH (center:{center_type} {{id: $center_id}})
            CALL apoc.path.subgraphAll(center, {{maxLevel: $depth, limit: $max_nodes}})
            YIELD nodes, relationships
            RETURN 
                [n IN nodes | {{
                    id: n.id, label: coalesce(n.title, n.name),
                    type: labels(n)[0], properties: properties(n)
                }}] as nodes,
                [r IN relationships | {{
                    source: startNode(r).id, target: endNode(r).id,
                    type: type(r), properties: properties(r)
                }}] as edges
        """, {"center_id": center_id, "depth": depth, "max_nodes": max_nodes})
        
        if not result:
            return GraphData(nodes=[], edges=[], node_count=0, edge_count=0)
        
        return GraphData(
            nodes=result["nodes"], edges=result["edges"],
            node_count=len(result["nodes"]), edge_count=len(result["edges"])
        )
    
    async def get_overview_graph(
        self, node_types: list[str] = None, max_nodes: int = 100
    ) -> GraphData:
        """Get an overview graph for the full knowledge base."""
        client = await self._get_client()
        
        if node_types is None:
            node_types = ["Source", "Concept", "Topic"]
        
        type_filter = " OR ".join([f"n:{t}" for t in node_types])
        
        result = await client.run_single(f"""
            MATCH (n) WHERE {type_filter}
            WITH n ORDER BY size((n)--()) DESC LIMIT $max_nodes
            WITH collect(n) as nodes
            UNWIND nodes as n
            MATCH (n)-[r]-(m) WHERE m IN nodes
            WITH nodes, collect(DISTINCT r) as relationships
            RETURN 
                [n IN nodes | {{
                    id: n.id, label: coalesce(n.title, n.name),
                    type: labels(n)[0], connectionCount: size((n)--())
                }}] as nodes,
                [r IN relationships | {{
                    source: startNode(r).id, target: endNode(r).id, type: type(r)
                }}] as edges
        """, {"max_nodes": max_nodes})
        
        if not result:
            return GraphData(nodes=[], edges=[], node_count=0, edge_count=0)
        
        return GraphData(
            nodes=result["nodes"], edges=result["edges"],
            node_count=len(result["nodes"]), edge_count=len(result["edges"])
        )
```

**Deliverables:**
- [ ] `KnowledgeQueries` class with discovery patterns
- [ ] Path finding between concepts
- [ ] Prerequisite chain queries
- [ ] Learning path generation
- [ ] Topic knowledge aggregation
- [ ] Unexpected connection discovery
- [ ] `GraphVisualizationQueries` for UI
- [ ] Subgraph extraction
- [ ] Overview graph generation
- [ ] Unit tests for all query patterns

**Estimated Time:** 6 hours

---

### Phase 4A: Import & Sync (Weeks 11-12)

#### Task 4A.1: Processing Pipeline Import Service

**Why this matters:** This is the primary entry point for new knowledge—taking the output of the LLM Processing Layer and creating the graph representation. Proper batching and error handling ensure reliable imports.

```python
# backend/app/services/knowledge_graph/import_service.py

from typing import Optional
from datetime import datetime
import logging
import uuid

from app.services.knowledge_graph.client import get_neo4j_client
from app.services.knowledge_graph.operations import NodeOperations, RelationshipOperations
from app.services.knowledge_graph.models import (
    SourceNode, ConceptNode, TagNode, PersonNode,
    MasteryQuestionNode, ContentType, ComplexityLevel
)
from app.models.processing import ProcessingResult  # From Phase 3
from app.models.content import UnifiedContent  # From Phase 2

logger = logging.getLogger(__name__)


class ProcessingResultImporter:
    """Import LLM processing results into the knowledge graph.
    
    This is the bridge between Phase 3 (LLM Processing) and the knowledge graph.
    Called after content is processed to persist the extracted knowledge.
    """
    
    def __init__(self):
        self.nodes = NodeOperations()
        self.relationships = RelationshipOperations()
    
    async def import_result(
        self,
        content: UnifiedContent,
        result: ProcessingResult,
        obsidian_path: str = None
    ) -> dict:
        """Import a processing result into the knowledge graph.
        
        Args:
            content: Original unified content
            result: Processing result from LLM pipeline
            obsidian_path: Path to the generated Obsidian note
        
        Returns:
            Summary of created nodes and relationships
        """
        summary = {
            "source_id": None,
            "concepts_created": 0,
            "tags_created": 0,
            "authors_created": 0,
            "relationships_created": 0,
            "errors": []
        }
        
        try:
            # 1. Create Source node
            source_id = str(uuid.uuid4())
            source = SourceNode(
                id=source_id,
                type=ContentType(result.analysis.content_type),
                title=content.title,
                authors=content.authors or [],
                source_url=content.source_url,
                created_at=content.created_at,
                processed_at=datetime.now(),
                summary=result.summaries.get("standard", ""),
                embedding=result.embedding,
                obsidian_path=obsidian_path
            )
            
            await self.nodes.create_source(source)
            summary["source_id"] = source_id
            logger.info(f"Created Source node: {source_id}")
            
            # 2. Create Concept nodes and EXPLAINS relationships
            for concept in result.extraction.concepts:
                try:
                    concept_node = ConceptNode(
                        id=str(uuid.uuid4()),
                        name=concept.name,
                        definition=concept.definition,
                        domain=result.analysis.domain,
                        complexity=self._map_complexity(concept.importance),
                        embedding=None  # Could generate concept embedding separately
                    )
                    
                    await self.nodes.create_concept(concept_node)
                    
                    # Create relationship based on importance
                    if concept.importance == "core":
                        await self.relationships.create_relationship(
                            "Source", source_id, "Concept", concept.name,
                            "INTRODUCES", target_id_prop="name"
                        )
                    else:
                        await self.relationships.source_explains_concept(source_id, concept.name)
                    
                    summary["concepts_created"] += 1
                    summary["relationships_created"] += 1
                    
                except Exception as e:
                    logger.error(f"Error creating concept {concept.name}: {e}")
                    summary["errors"].append(f"Concept {concept.name}: {str(e)}")
            
            # 3. Create Tag nodes and relationships
            all_tags = result.tags.domain_tags + result.tags.meta_tags
            for tag in all_tags:
                try:
                    await self.nodes.get_or_create_tag(tag)
                    await self.relationships.source_tagged_with(source_id, tag)
                    summary["tags_created"] += 1
                    summary["relationships_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating tag {tag}: {e}")
                    summary["errors"].append(f"Tag {tag}: {str(e)}")
            
            # 4. Create Person nodes for authors
            for author in content.authors or []:
                try:
                    await self.nodes.get_or_create_person_by_name(author)
                    await self.relationships.person_authored_source(author, source_id)
                    summary["authors_created"] += 1
                    summary["relationships_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating author {author}: {e}")
                    summary["errors"].append(f"Author {author}: {str(e)}")
            
            # 5. Create MasteryQuestion nodes
            for question in result.mastery_questions:
                try:
                    q_node = MasteryQuestionNode(
                        id=str(uuid.uuid4()),
                        question=question.question,
                        source_id=source_id,
                        difficulty=question.difficulty,
                        hints=question.hints or [],
                        key_points=question.key_points or []
                    )
                    await self.nodes.create_mastery_question(q_node)
                    
                    # Link to source
                    await self.relationships.create_relationship(
                        "MasteryQuestion", q_node.id,
                        "Source", source_id,
                        "FROM_SOURCE"
                    )
                except Exception as e:
                    logger.error(f"Error creating mastery question: {e}")
            
            # 6. Create connections to other sources
            for connection in result.connections:
                try:
                    # Check if target exists
                    if await self.nodes.node_exists("Source", connection.target_id):
                        await self.relationships.create_relationship(
                            "Source", source_id,
                            "Source", connection.target_id,
                            connection.relationship_type,
                            properties={
                                "strength": connection.strength,
                                "explanation": connection.explanation
                            }
                        )
                        summary["relationships_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating connection: {e}")
            
            logger.info(f"Import complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            summary["errors"].append(f"Import failed: {str(e)}")
            return summary
    
    def _map_complexity(self, importance: str) -> ComplexityLevel:
        """Map concept importance to complexity level."""
        mapping = {
            "core": ComplexityLevel.FOUNDATIONAL,
            "important": ComplexityLevel.INTERMEDIATE,
            "supporting": ComplexityLevel.ADVANCED
        }
        return mapping.get(importance, ComplexityLevel.INTERMEDIATE)


class BatchImporter:
    """Batch import operations for bulk data migration."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.importer = ProcessingResultImporter()
    
    async def import_batch(
        self,
        items: list[tuple[UnifiedContent, ProcessingResult, str]]
    ) -> dict:
        """Import multiple items in batches.
        
        Args:
            items: List of (content, result, obsidian_path) tuples
        """
        total = len(items)
        success = 0
        failures = []
        
        for i, (content, result, path) in enumerate(items):
            try:
                await self.importer.import_result(content, result, path)
                success += 1
                
                if (i + 1) % self.batch_size == 0:
                    logger.info(f"Processed {i + 1}/{total} items")
                    
            except Exception as e:
                logger.error(f"Failed to import {content.title}: {e}")
                failures.append({"title": content.title, "error": str(e)})
        
        return {
            "total": total,
            "success": success,
            "failures": len(failures),
            "failure_details": failures
        }


# Convenience function for Phase 3 integration
async def import_processing_result(
    content: UnifiedContent,
    result: ProcessingResult,
    obsidian_path: str = None
) -> dict:
    """Import a single processing result into the knowledge graph.
    
    Called from the LLM Processing Layer after content is processed.
    """
    importer = ProcessingResultImporter()
    return await importer.import_result(content, result, obsidian_path)
```

**Deliverables:**
- [ ] `ProcessingResultImporter` class
- [ ] Source node creation with embedding
- [ ] Concept extraction and relationship creation
- [ ] Tag and author handling
- [ ] MasteryQuestion node creation
- [ ] Connection relationship creation
- [ ] `BatchImporter` for bulk operations
- [ ] Integration tests with mock processing results

**Estimated Time:** 5 hours

---

#### Task 4A.2: Obsidian Vault Sync Service

**Why this matters:** Bi-directional sync keeps the graph and vault consistent. When users edit notes in Obsidian (add links, change tags), those changes should reflect in Neo4j.

```python
# backend/app/services/knowledge_graph/sync.py

from pathlib import Path
from typing import Optional
import logging
import frontmatter
import aiofiles

from app.services.knowledge_graph.client import get_neo4j_client
from app.services.knowledge_graph.operations import NodeOperations, RelationshipOperations
from app.services.obsidian.links import extract_wikilinks, extract_tags

logger = logging.getLogger(__name__)


class VaultToGraphSync:
    """Sync Obsidian vault changes to Neo4j knowledge graph."""
    
    def __init__(self):
        self.nodes = NodeOperations()
        self.relationships = RelationshipOperations()
    
    async def sync_note(self, note_path: Path) -> dict:
        """Sync a single note's changes to the graph.
        
        Called by the vault file watcher when a note is modified.
        """
        try:
            async with aiofiles.open(note_path, "r", encoding="utf-8") as f:
                content = await f.read()
            
            post = frontmatter.loads(content)
            fm = dict(post.metadata)
            body = post.content
            
            # Extract current state
            outgoing_links = extract_wikilinks(body)
            inline_tags = extract_tags(body)
            all_tags = list(set(fm.get("tags", []) + inline_tags))
            
            # Determine node identity
            node_id = fm.get("id") or fm.get("neo4j_id") or note_path.stem
            note_type = fm.get("type", "note")
            
            client = await get_neo4j_client()
            
            # Update node properties
            if note_type in ["paper", "article", "book", "code", "idea"]:
                await client.run("""
                    MATCH (s:Source {obsidian_path: $path})
                    SET s.title = $title,
                        s.type = $type
                    RETURN s
                """, {
                    "path": str(note_path),
                    "title": fm.get("title", note_path.stem),
                    "type": note_type
                })
            elif note_type == "concept":
                await client.run("""
                    MATCH (c:Concept {obsidian_path: $path})
                    SET c.name = $name,
                        c.definition = $definition
                    RETURN c
                """, {
                    "path": str(note_path),
                    "name": fm.get("name", note_path.stem),
                    "definition": fm.get("definition", "")
                })
            
            # Sync tags
            await self._sync_tags(node_id, note_type, all_tags)
            
            # Sync outgoing links
            await self._sync_links(node_id, note_type, outgoing_links)
            
            return {
                "path": str(note_path),
                "node_id": node_id,
                "tags_synced": len(all_tags),
                "links_synced": len(outgoing_links)
            }
            
        except Exception as e:
            logger.error(f"Failed to sync note {note_path}: {e}")
            return {"path": str(note_path), "error": str(e)}
    
    async def _sync_tags(self, node_id: str, note_type: str, tags: list[str]):
        """Sync tags from note to graph."""
        label = "Source" if note_type != "concept" else "Concept"
        
        # Clear existing tag relationships
        await self.relationships.clear_outgoing_relationships(
            label, node_id, "TAGGED_WITH"
        )
        
        # Create new tag relationships
        for tag in tags:
            await self.nodes.get_or_create_tag(tag)
            await self.relationships.source_tagged_with(node_id, tag)
    
    async def _sync_links(self, node_id: str, note_type: str, links: list[str]):
        """Sync wikilinks from note to graph."""
        label = "Source" if note_type != "concept" else "Concept"
        client = await get_neo4j_client()
        
        # Clear existing LINKS_TO relationships
        await self.relationships.clear_outgoing_relationships(
            label, node_id, "LINKS_TO"
        )
        
        # Create new link relationships
        for target_title in links:
            # Try to find target by title or name
            await client.run("""
                MATCH (source {id: $source_id})
                OPTIONAL MATCH (target)
                WHERE target.title = $target_title OR target.name = $target_title
                FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (source)-[:LINKS_TO]->(target)
                )
            """, {"source_id": node_id, "target_title": target_title})
    
    async def full_vault_sync(self, vault_path: Path) -> dict:
        """Perform a full sync of the entire vault.
        
        Used for initial import or recovery.
        """
        results = {"synced": 0, "errors": []}
        
        for note_path in vault_path.rglob("*.md"):
            # Skip system files
            if note_path.name.startswith("_") or ".obsidian" in str(note_path):
                continue
            
            result = await self.sync_note(note_path)
            if "error" in result:
                results["errors"].append(result)
            else:
                results["synced"] += 1
        
        logger.info(f"Full vault sync complete: {results['synced']} notes synced")
        return results


class GraphToVaultSync:
    """Sync Neo4j changes back to Obsidian vault (if needed)."""
    
    async def update_note_connections(self, note_path: Path, source_id: str):
        """Update a note's connections section based on graph data.
        
        Called when new connections are discovered in the graph.
        """
        client = await get_neo4j_client()
        
        # Get connections from graph
        connections = await client.run("""
            MATCH (s:Source {id: $id})-[r:RELATES_TO|CITES|EXTENDS]->(target:Source)
            RETURN target.title as title, type(r) as rel_type, r.explanation as explanation
            ORDER BY r.strength DESC
            LIMIT 10
        """, {"id": source_id})
        
        if not connections:
            return
        
        # Generate connections section
        lines = ["## Connections", ""]
        for conn in connections:
            link = f"[[{conn['title']}]]"
            if conn.get("explanation"):
                lines.append(f"- {link} — {conn['explanation']}")
            else:
                lines.append(f"- {link} ({conn['rel_type']})")
        
        # TODO: Update the note file with new connections section
        # This requires careful parsing to avoid overwriting user content
        logger.info(f"Would update connections in {note_path}")
```

**Deliverables:**
- [ ] `VaultToGraphSync` class
- [ ] Single note sync method
- [ ] Tag synchronization
- [ ] Link synchronization
- [ ] Full vault sync for initial import
- [ ] `GraphToVaultSync` for reverse sync (optional)
- [ ] Integration tests with test vault

**Estimated Time:** 4 hours

---

#### Task 4A.3: Knowledge Graph API Router

**Why this matters:** The API layer exposes graph operations to the frontend and external systems. Clean endpoints enable the Knowledge Explorer UI (Phase 5).

```python
# backend/app/routers/knowledge.py

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional

from app.services.knowledge_graph.client import get_neo4j_client
from app.services.knowledge_graph.queries import KnowledgeQueries, GraphVisualizationQueries
from app.services.knowledge_graph.vector_search import VectorSearchService
from app.services.knowledge_graph.schema import initialize_neo4j_schema
from app.services.knowledge_graph.models import SearchResult, GraphData, PathResult

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# --- Health & Status ---

@router.get("/health")
async def knowledge_graph_health():
    """Check Neo4j connection health."""
    client = await get_neo4j_client()
    return await client.health_check()


@router.post("/schema/initialize")
async def initialize_schema():
    """Initialize Neo4j schema (indexes, constraints)."""
    result = await initialize_neo4j_schema()
    return {"status": "initialized", **result}


@router.get("/stats")
async def get_graph_stats():
    """Get knowledge graph statistics."""
    queries = KnowledgeQueries()
    return await queries.get_graph_stats()


# --- Search ---

class SearchRequest(BaseModel):
    query: str
    embedding: Optional[list[float]] = None
    top_k: int = 10
    include_sources: bool = True
    include_concepts: bool = True


@router.post("/search", response_model=list[SearchResult])
async def semantic_search(request: SearchRequest):
    """Perform semantic search across the knowledge graph.
    
    If embedding is not provided, only full-text search is performed.
    """
    search = VectorSearchService()
    
    if request.embedding:
        return await search.semantic_search(
            query_embedding=request.embedding,
            top_k=request.top_k,
            include_sources=request.include_sources,
            include_concepts=request.include_concepts
        )
    else:
        # Fall back to full-text search
        client = await get_neo4j_client()
        results = await client.run("""
            CALL db.index.fulltext.queryNodes('source_text', $query)
            YIELD node, score
            RETURN node.id as id, node.title as title, node.summary as summary,
                   labels(node)[0] as node_type, score
            LIMIT $top_k
        """, {"query": request.query, "top_k": request.top_k})
        
        return [SearchResult(**r) for r in results]


@router.get("/search/similar/{source_id}", response_model=list[SearchResult])
async def find_similar(
    source_id: str,
    top_k: int = Query(5, ge=1, le=20)
):
    """Find sources similar to the given source."""
    search = VectorSearchService()
    return await search.find_similar_sources(source_id, top_k)


# --- Knowledge Discovery ---

@router.get("/path")
async def find_path(
    concept_a: str = Query(..., description="First concept name"),
    concept_b: str = Query(..., description="Second concept name"),
    max_hops: int = Query(5, ge=1, le=10)
) -> Optional[PathResult]:
    """Find the shortest path between two concepts."""
    queries = KnowledgeQueries()
    result = await queries.find_path_between_concepts(concept_a, concept_b, max_hops)
    
    if not result:
        raise HTTPException(404, f"No path found between {concept_a} and {concept_b}")
    
    return result


@router.get("/prerequisites/{concept_name}")
async def get_prerequisites(
    concept_name: str,
    max_depth: int = Query(10, ge=1, le=20)
):
    """Get prerequisites for understanding a concept."""
    queries = KnowledgeQueries()
    return await queries.get_concept_prerequisites(concept_name, max_depth)


@router.get("/learning-path/{concept_name}")
async def get_learning_path(concept_name: str):
    """Generate a learning path to understand a concept."""
    queries = KnowledgeQueries()
    path = await queries.get_learning_path(concept_name)
    
    if not path:
        raise HTTPException(404, f"No learning path found for {concept_name}")
    
    return {"target": concept_name, "path": path}


@router.get("/topic/{topic_name}")
async def get_topic_knowledge(
    topic_name: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get all knowledge about a topic."""
    queries = KnowledgeQueries()
    return await queries.get_topic_knowledge(topic_name, limit)


@router.get("/connections/{source_id}")
async def find_connections(
    source_id: str,
    min_hops: int = Query(2, ge=1, le=5),
    max_hops: int = Query(3, ge=1, le=5),
    limit: int = Query(5, ge=1, le=20)
):
    """Find unexpected connections to a source."""
    queries = KnowledgeQueries()
    return await queries.find_unexpected_connections(source_id, min_hops, max_hops, limit)


# --- Graph Visualization ---

@router.get("/graph", response_model=GraphData)
async def get_graph(
    center_id: Optional[str] = None,
    center_type: str = Query("Source", regex="^(Source|Concept|Topic)$"),
    depth: int = Query(2, ge=1, le=4),
    max_nodes: int = Query(100, ge=10, le=500)
):
    """Get graph data for visualization.
    
    If center_id is provided, returns a subgraph centered on that node.
    Otherwise, returns an overview of the most connected nodes.
    """
    viz = GraphVisualizationQueries()
    
    if center_id:
        return await viz.get_subgraph(center_id, center_type, depth, max_nodes)
    else:
        return await viz.get_overview_graph(max_nodes=max_nodes)


@router.get("/graph/topic/{topic_name}", response_model=GraphData)
async def get_topic_graph(
    topic_name: str,
    include_concepts: bool = True,
    max_nodes: int = Query(50, ge=10, le=200)
):
    """Get graph for a specific topic."""
    viz = GraphVisualizationQueries()
    return await viz.get_topic_graph(topic_name, include_concepts, max_nodes)


# --- Topics ---

@router.get("/topics")
async def list_topics():
    """List all topics in the knowledge graph."""
    client = await get_neo4j_client()
    return await client.run("""
        MATCH (t:Topic)
        OPTIONAL MATCH (t)<-[:BELONGS_TO]-(s:Source)
        RETURN t.id as id, t.name as name, t.path as path, count(s) as source_count
        ORDER BY source_count DESC
    """)


@router.get("/topics/{topic_id}/subtopics")
async def get_subtopics(topic_id: str):
    """Get subtopics of a topic."""
    client = await get_neo4j_client()
    return await client.run("""
        MATCH (parent:Topic {id: $id})<-[:SUBTOPIC_OF]-(child:Topic)
        RETURN child.id as id, child.name as name, child.path as path
    """, {"id": topic_id})
```

**Deliverables:**
- [ ] `/health` endpoint for Neo4j status
- [ ] `/schema/initialize` endpoint
- [ ] `/stats` endpoint for graph statistics
- [ ] `/search` semantic search endpoint
- [ ] `/search/similar/{id}` similar source discovery
- [ ] `/path` path finding between concepts
- [ ] `/prerequisites/{concept}` prerequisite chain
- [ ] `/learning-path/{concept}` learning path generation
- [ ] `/topic/{name}` topic knowledge
- [ ] `/connections/{id}` connection discovery
- [ ] `/graph` visualization data endpoint
- [ ] `/topics` listing endpoint
- [ ] OpenAPI documentation
- [ ] Integration tests for all endpoints

**Estimated Time:** 5 hours

---

## 4. Testing Strategy

### 4.1 Test Structure

```
tests/
├── unit/knowledge_graph/
│   ├── test_client.py              # Neo4jClient connection, retry logic
│   ├── test_models.py              # Pydantic model validation
│   ├── test_schema.py              # Schema creation/verification
│   ├── test_operations.py          # Node/relationship CRUD
│   ├── test_vector_search.py       # Vector search with mock embeddings
│   ├── test_queries.py             # Query patterns with test data
│   └── test_import_service.py      # Import from processing results
├── integration/
│   ├── test_neo4j_integration.py   # Full Neo4j integration tests
│   ├── test_knowledge_api.py       # API endpoint tests
│   └── test_vault_sync.py          # Obsidian sync integration
└── fixtures/
    ├── sample_graph/               # Test graph data
    ├── mock_embeddings.py          # Mock embedding vectors
    └── mock_processing_results.py  # Mock ProcessingResult objects
```

### 4.2 Key Test Cases

| Component | Test Case | Priority |
|-----------|-----------|----------|
| Client | Connection pooling and retry | High |
| Client | Health check returns correct status | High |
| Schema | All indexes created successfully | High |
| Schema | Vector indexes with correct dimensions | High |
| Operations | MERGE creates node idempotently | High |
| Operations | Embedding set correctly | High |
| Vector Search | Returns results sorted by score | High |
| Vector Search | Respects min_score threshold | High |
| Queries | Path finding returns valid path | High |
| Queries | Prerequisites ordered by depth | Medium |
| Import | Full processing result imported | High |
| Import | Handles missing optional fields | Medium |
| Sync | Tags updated on note edit | High |
| API | Search returns valid SearchResult | High |
| API | Graph endpoint returns valid GraphData | High |

### 4.3 Test Data Setup

```python
# tests/fixtures/sample_graph.py

import pytest
from app.services.knowledge_graph.models import SourceNode, ConceptNode

@pytest.fixture
async def sample_sources():
    return [
        SourceNode(
            id="source-1",
            type="paper",
            title="Attention Is All You Need",
            authors=["Vaswani et al."],
            summary="Introduces the Transformer architecture",
            embedding=[0.1] * 1536  # Mock embedding
        ),
        SourceNode(
            id="source-2",
            type="paper",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin et al."],
            summary="Pre-trained language model using transformers",
            embedding=[0.2] * 1536
        ),
    ]

@pytest.fixture
async def sample_concepts():
    return [
        ConceptNode(
            id="concept-1",
            name="Transformer",
            definition="Neural network architecture using self-attention",
            domain="ml",
            complexity="intermediate"
        ),
        ConceptNode(
            id="concept-2",
            name="Self-Attention",
            definition="Mechanism for computing weighted representations",
            domain="ml",
            complexity="intermediate"
        ),
    ]
```

---

## 5. Configuration

### 5.1 Environment Variables

```bash
# .env - Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=secondbrain

# Connection Pool
NEO4J_MAX_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=60

# Vector Search
NEO4J_VECTOR_DIMENSIONS=1536
NEO4J_VECTOR_SIMILARITY=cosine

# Sync
NEO4J_SYNC_ENABLED=true
NEO4J_SYNC_BATCH_SIZE=100
```

### 5.2 Settings Class

```python
# backend/app/config/neo4j.py

from pydantic_settings import BaseSettings


class Neo4jSettings(BaseSettings):
    # Connection
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"
    
    # Pool
    NEO4J_MAX_POOL_SIZE: int = 50
    NEO4J_CONNECTION_TIMEOUT: float = 60.0
    
    # Vector
    NEO4J_VECTOR_DIMENSIONS: int = 1536
    NEO4J_VECTOR_SIMILARITY: str = "cosine"
    
    # Sync
    NEO4J_SYNC_ENABLED: bool = True
    NEO4J_SYNC_BATCH_SIZE: int = 100
    
    class Config:
        env_prefix = ""
        case_sensitive = True
```

### 5.3 Docker Compose Integration

```yaml
# docker-compose.yml additions
services:
  neo4j:
    image: neo4j:5-enterprise
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
      - NEO4J_dbms_memory_pagecache_size=512m
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  neo4j_data:
  neo4j_logs:
```

---

## 6. Timeline Summary

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 7-8 | 3A | Foundation | Project structure, Neo4j client, models, schema |
| 9-10 | 3B | Core Operations | Node CRUD, vector search, query patterns |
| 11-12 | 4A | Import & Sync | Processing import, vault sync, API endpoints |
| 13-14 | - | Testing & Polish | Integration tests, documentation, bug fixes |

**Total Estimated Time:** ~50-60 hours

---

## 7. Success Criteria

### Functional
- [ ] Neo4j client connects reliably with connection pooling
- [ ] Schema initialized with all indexes on startup
- [ ] Vector search returns relevant results (>0.7 similarity)
- [ ] Path queries find connections between concepts
- [ ] Processing results import creates correct graph structure
- [ ] Vault sync updates tags and links bidirectionally
- [ ] All API endpoints return valid responses

### Non-Functional
- [ ] Vector search < 100ms for 10 results
- [ ] Path queries < 500ms for depth 5
- [ ] API endpoints < 200ms average response
- [ ] Connection pool handles 50 concurrent requests
- [ ] Import handles 1000 documents without failure

### Integration
- [ ] Integrates with LLM Processing Layer (Phase 3)
- [ ] Integrates with Obsidian Knowledge Hub (Phase 4)
- [ ] Provides data for Knowledge Explorer UI (Phase 5)
- [ ] Supports spaced repetition queries (Phase 7)

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Neo4j Enterprise required for vector indexes | High | Medium | Use Community + external vector DB fallback |
| Large graph performance degradation | Medium | Low | Implement pagination, index optimization |
| Embedding dimension mismatch | High | Low | Validate dimensions on import |
| Sync conflicts between Obsidian and Neo4j | Medium | Medium | Last-write-wins, audit log |
| APOC plugin not available | Medium | Low | Implement fallback queries without APOC |

---

## 9. Dependencies

### Required Before This Phase
- [x] Phase 1: Foundation (Neo4j container, FastAPI)
- [ ] Phase 3: LLM Processing (ProcessingResult model)

### Enables After This Phase
- Phase 4: Knowledge Hub Obsidian (bi-directional sync)
- Phase 5: Knowledge Explorer UI (graph visualization)
- Phase 6: Practice Session (mastery question queries)
- Phase 7: Spaced Repetition (learning queries)

---

## 10. Open Questions

1. **Enterprise vs Community**: Do we require Neo4j Enterprise for vector indexes, or can we use Community with external vector search?
2. **Embedding Generation**: Should we generate embeddings for concepts separately, or derive from source embeddings?
3. **Conflict Resolution**: How to handle conflicts when the same concept is extracted from multiple sources with different definitions?
4. **Graph Cleanup**: Should we implement orphan node cleanup (concepts not linked to any source)?
5. **Historical Queries**: Do we need to track historical graph state for "what did I know last month?" queries?

---

## 11. Related Documents

- `design_docs/04_knowledge_graph_neo4j.md` — Design specification
- `implementation_plan/00_foundation_implementation.md` — Infrastructure setup
- `implementation_plan/02_llm_processing_implementation.md` — ProcessingResult model
- `implementation_plan/03_knowledge_hub_obsidian_implementation.md` — Vault sync
- `design_docs/06_backend_api.md` — API design patterns
