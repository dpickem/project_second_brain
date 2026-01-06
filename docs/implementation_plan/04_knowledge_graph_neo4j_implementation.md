# Knowledge Graph (Neo4j) Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Updated**: January 2026  
> **Target Phase**: Phase 3-4 (Weeks 7-14, parallel with LLM Processing & Knowledge Hub)  
> **Design Doc**: `design_docs/04_knowledge_graph_neo4j.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Knowledge Graph component using Neo4j. The knowledge graph serves as the semantic backbone of the Second Brain system—storing concepts, relationships, and embeddings that power connection discovery, learning path generation, and semantic search.

### Implementation Status

**PARTIAL IMPLEMENTATION COMPLETE**

Core Neo4j infrastructure has been implemented as part of Phase 3 (LLM Processing) and Phase 4 (Knowledge Hub). Some advanced features (Knowledge API Router, advanced query service) remain for future phases.

| Component | Status | Location |
|-----------|--------|----------|
| Neo4jClient (async with pooling) | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Schema/Index Setup | ✅ Complete | `backend/app/services/knowledge_graph/queries.py` |
| Vector Search | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Content Node Operations | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Concept Node Operations | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Note Node Operations (Vault Sync) | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Relationship Operations | ✅ Complete | `backend/app/services/knowledge_graph/client.py` |
| Common Query Patterns | ✅ Complete | `backend/app/services/knowledge_graph/queries.py` |
| Schema Definitions | ✅ Complete | `backend/app/services/knowledge_graph/schemas.py` |
| Vault-to-Neo4j Sync | ✅ Complete | `backend/app/services/obsidian/sync.py` |
| Pydantic Models | ⚪ Uses existing | `backend/app/models/processing.py` |
| **Preliminary Graph UI** | 🔲 Next Up | `frontend/src/components/GraphViewer/` |
| Graph API Endpoint | 🔲 Next Up | `backend/app/routers/knowledge.py` |
| Knowledge API Router | 🔲 Not Started | Future: `backend/app/routers/knowledge.py` |
| Advanced Query Service | 🔲 Not Started | Learning paths, prerequisites |
| Graph Visualization Queries | 🔲 Not Started | Subgraph extraction |

### Architecture Overview

The Knowledge Graph integrates with the LLM Processing Layer (upstream) and supports both the Knowledge Hub (Obsidian) and Frontend (downstream):

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LLM Processing │────▶│   Neo4j Client   │────▶│  Knowledge API  │
│     Result      │     │   (✅ Complete)  │     │  (🔲 Next Up)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                        │
                        ┌───────▼────────┐        ┌──────▼───────┐
                        │     Neo4j      │        │  Graph UI    │
                        │   Database     │◀───────│ (🔲 Next Up) │
                        │  (✅ Running)  │        │ react-force  │
                        └───────┬────────┘        └──────────────┘
                                │
                        ┌───────▼────────┐
                        │  Obsidian Sync │
                        │  (✅ Complete) │
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

| In Scope (Implemented) | In Scope (Next Up) | In Scope (Future) | Out of Scope |
|------------------------|-------------------|-------------------|--------------|
| ✅ Neo4j client with pooling | 🔲 Graph API endpoint | Advanced query service | Real-time collaborative editing |
| ✅ Node types: Content, Concept, Note | 🔲 Preliminary Graph UI | Learning path generation | Multi-tenant isolation |
| ✅ Vector index creation and search | 🔲 Graph stats endpoint | Prerequisite chain queries | Neo4j cluster deployment |
| ✅ Relationship management | 🔲 Node tooltips & legend | Hybrid search (vector + text) | Graph analytics algorithms |
| ✅ Import from LLM processing pipeline | | Graph visualization queries | Custom Neo4j plugins |
| ✅ Bi-directional Obsidian sync | | | External graph federation |
| ✅ Common query patterns | | | |

---

## 2. Prerequisites

### 2.1 Infrastructure (From Phase 1) — ✅ Complete

- [x] Docker Compose environment
- [x] Neo4j container configured and running
- [x] FastAPI backend skeleton
- [x] PostgreSQL for metadata
- [x] LLM Processing Layer (Phase 3)

### 2.2 Dependencies — ✅ Installed

**Backend (in `backend/requirements.txt`):**
```txt
neo4j>=5.15.0              # Official Neo4j Python driver
numpy>=1.24.0              # Vector operations (may already be installed)
```

**Frontend (in `frontend/package.json`):**
```json
"d3": "^7.8.5",                    // Data manipulation, scales
"react-force-graph-2d": "^1.25.0", // Force-directed graph rendering
"@tanstack/react-query": "^5.20.0",// Data fetching with caching
"framer-motion": "^11.0.3",        // Animations
"tailwindcss": "^3.4.1"            // Styling
```

**Why these specific packages:**

| Package | Why This One | Alternatives Considered |
|---------|--------------|------------------------|
| `neo4j` | Official async driver with connection pooling, transaction management, and full Cypher support | `py2neo` (community, less maintained), `neomodel` (OGM, adds unnecessary abstraction) |
| `numpy` | Standard for vector operations, embedding manipulation | `torch` (overkill for vector math only) |
| `react-force-graph-2d` | High-performance force-directed graphs with React integration | `vis.js` (heavier), `cytoscape` (more complex), raw D3 (more work) |
| `d3` | Industry standard for data visualization, provides scales and utilities | `chart.js` (chart-focused, not graph) |

### 2.3 Environment Variables — ✅ Configured

```bash
# .env file
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>
NEO4J_DATABASE=neo4j
```

### 2.4 Neo4j Configuration — ✅ Complete

The Neo4j container is configured with adequate memory for vector operations:

```yaml
# docker-compose.yml neo4j service
neo4j:
  image: neo4j:5-community
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    - NEO4J_PLUGINS=["apoc"]  # Required for advanced queries
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
```

---

## 3. Implementation Phases

### Phase 3A: Foundation (Weeks 7-8) — ✅ Complete

#### Task 3A.1: Project Structure Setup

**Why this matters:** A well-organized module structure separates concerns: client management, schema operations, queries, and synchronization. This enables independent testing and clear dependency boundaries.

**Directory Structure:**

```
backend/
├── app/
│   ├── services/
│   │   ├── knowledge_graph/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Neo4j async client with connection pooling
│   │   │   ├── schemas.py          # Dataclass definitions for nodes/relationships
│   │   │   └── queries.py          # Common query patterns and index setup
│   │   └── ...
│   └── ...
```

**Deliverables:** ✅ All Complete
- [x] Directory structure created
- [x] `__init__.py` files with proper exports
- [x] Module organization

---

#### Task 3A.2: Neo4j Async Client

**Why this matters:** A robust client with connection pooling, retry logic, and proper async support is essential for production use. The driver should handle transient failures gracefully and provide clean transaction management.

**Location**: `backend/app/services/knowledge_graph/client.py`

**Key Design Decisions:**
- **Lazy initialization**: Driver connects on first use, indexes created automatically if missing
- **Dual drivers**: Async driver for FastAPI, sync driver for Celery tasks
- **Singleton pattern**: `get_neo4j_client()` returns shared instance
- **Automatic index setup**: Checks for required indexes on first connection

**Supported Operations:**
- `vector_search()` - Find similar nodes by embedding similarity
- `create_content_node()` - Create/update Content nodes with embeddings
- `create_concept_node()` - Create/merge Concept nodes
- `create_relationship()` - Generic relationship creation
- `link_content_to_concept()` - CONTAINS relationship
- `get_connected_nodes()` - Graph traversal
- `get_content_by_id()` - Lookup by UUID
- `delete_content_node()` - Delete with relationship cleanup
- `merge_note_node()` - Create/update Note nodes for Obsidian sync
- `sync_note_links()` - Sync wikilinks as LINKS_TO relationships

**Usage:**
```python
from app.services.knowledge_graph import get_neo4j_client

client = await get_neo4j_client()

# Find similar content
similar = await client.vector_search(embedding, top_k=10)

# Create a content node
node_id = await client.create_content_node(
    content_id=str(uuid4()),
    title="My Paper",
    content_type="paper",
    summary="...",
    embedding=[...],
    tags=["ml/transformers"]
)
```

**Deliverables:** ✅ All Complete
- [x] `Neo4jClient` class with async support
- [x] Connection pooling configuration
- [x] Lazy initialization
- [x] Health check method (`verify_connectivity()`)
- [x] Singleton accessor functions
- [x] Note node operations for Obsidian sync

---

#### Task 3A.3: Schema Definitions

**Why this matters:** Clear schema definitions ensure consistency between Python code and Neo4j structure. Dataclasses provide validation, serialization, and documentation of the data structures.

**Location**: `backend/app/services/knowledge_graph/schemas.py`

**Node Types:**
- `ContentNodeSchema` - Papers, articles, books, code, ideas, voice memos
- `ConceptNodeSchema` - Key concepts extracted from content
- `TagNodeSchema` - Tags from controlled taxonomy

**Relationship Types:**
- `CONTAINS` - Content → Concept
- `RELATES_TO` - Content → Content (general topical relationship)
- `EXTENDS` - Content → Content (builds on existing content)
- `CONTRADICTS` - Content → Content (challenges existing content)
- `PREREQUISITE_FOR` - Content → Content (foundational for understanding)
- `APPLIES` - Content → Content (applies concepts from another)
- `HAS_TAG` - Content → Tag
- `LINKS_TO` - Note → Note (wikilinks from Obsidian)

**Deliverables:** ✅ All Complete
- [x] Node schemas as dataclasses
- [x] Relationship schemas with properties (strength, explanation)
- [x] Enum imports from `app.enums`

---

#### Task 3A.4: Schema/Index Creation

**Why this matters:** The schema service creates indexes, constraints, and validates the database state. Running this on startup ensures the database is ready for queries and imports.

**Location**: `backend/app/services/knowledge_graph/queries.py`

**Indexes Created:**
- `content_embedding_index` - Vector index on Content.embedding (1536 dimensions, cosine)
- `concept_embedding_index` - Vector index on Concept.embedding (1536 dimensions, cosine)
- `content_id_unique` - Uniqueness constraint on Content.id
- `concept_name_unique` - Uniqueness constraint on Concept.name
- `content_type_index` - Regular index on Content.type
- `content_created_index` - Regular index on Content.created_at

**Setup Process:**
1. On first client connection, check if indexes exist
2. If missing, create all indexes via `SETUP_INDEX_QUERIES`
3. Indexes are created with `IF NOT EXISTS` for idempotency

**Deliverables:** ✅ All Complete
- [x] Vector index creation (1536 dimensions for OpenAI embeddings)
- [x] Uniqueness constraints
- [x] Type and date indexes
- [x] Automatic setup on first connection

---

### Phase 3B: Core Operations (Weeks 9-10) — ✅ Complete

#### Task 3B.1: Node CRUD Operations

**Why this matters:** Clean CRUD operations provide the foundation for all data manipulation. Using MERGE instead of CREATE ensures idempotency—running the same import twice won't create duplicates.

**Key Operations (in `client.py`):**
- `create_content_node()` - MERGE by id, SET all properties
- `create_concept_node()` - MERGE by name, conditional definition update
- `delete_content_node()` - DETACH DELETE (removes relationships too)
- `delete_content_relationships()` - Clear outgoing relationships for reprocessing

**Idempotency Pattern:**
```cypher
MERGE (c:Content {id: $id})
ON CREATE SET c.title = $title, c.created_at = datetime()
ON MATCH SET c.title = $title, c.updated_at = datetime()
```

**Deliverables:** ✅ All Complete
- [x] MERGE-based create/update operations
- [x] Get operations by ID
- [x] Delete operations with relationship cleanup
- [x] Content, Concept, and Note node types

---

#### Task 3B.2: Vector Search

**Why this matters:** Vector search enables semantic discovery—finding related content even when exact keywords don't match. This is critical for "what connects X to Y?" and "find related concepts" queries.

**Location**: `backend/app/services/knowledge_graph/client.py`

**Implementation:**
```python
async def vector_search(
    self,
    embedding: list[float],
    node_type: str = "Content",
    top_k: int = 20,
    threshold: float = 0.7,
) -> list[dict]:
    """Find similar nodes using vector similarity search."""
    index_name = f"{node_type.lower()}_embedding_index"
    # Uses VECTOR_SEARCH query from queries.py
```

**Configuration** (from `app/config/processing.py`):
- `NEO4J_VECTOR_SEARCH_TOP_K = 20` - Default number of results
- `NEO4J_VECTOR_SEARCH_THRESHOLD = 0.7` - Minimum similarity score

**Deliverables:** ✅ All Complete
- [x] Pure vector search by embedding
- [x] Configurable top_k and threshold
- [x] Index name parameterization
- [x] Results sorted by score

---

#### Task 3B.3: Common Query Patterns

**Why this matters:** Pre-built query patterns encapsulate complex Cypher logic for common use cases: content discovery, connection finding, analytics.

**Location**: `backend/app/services/knowledge_graph/queries.py`

**Query Categories:**

**Content Queries:**
- `GET_CONTENT_BY_ID` - Fetch content by UUID
- `GET_CONTENT_BY_TYPE` - Filter by content type
- `GET_RECENT_CONTENT` - Latest content by date
- `SEARCH_CONTENT_BY_TITLE` - Text search on titles

**Concept Queries:**
- `GET_CONCEPT_BY_NAME` - Lookup by name
- `GET_CONCEPTS_FOR_CONTENT` - Concepts in a content item
- `GET_CONTENT_FOR_CONCEPT` - Content explaining a concept

**Connection Queries:**
- `GET_RELATED_CONTENT` - Related content via relationships
- `GET_CONTENT_GRAPH` - 2-hop neighborhood for visualization
- `FIND_PATH_BETWEEN_CONTENT` - Shortest path

**Analytics Queries:**
- `GET_KNOWLEDGE_GRAPH_STATS` - Node and relationship counts
- `GET_MOST_CONNECTED_CONTENT` - Hub nodes
- `GET_ORPHAN_CONTENT` - Unconnected content

**Deliverables:** ✅ All Complete
- [x] Content queries (by ID, type, recent)
- [x] Concept queries
- [x] Connection queries
- [x] Tag queries
- [x] Analytics queries

---

### Phase 4A: Import & Sync (Weeks 11-12) — ✅ Complete

#### Task 4A.1: Processing Pipeline Integration

**Why this matters:** This is the primary entry point for new knowledge—taking the output of the LLM Processing Layer and creating the graph representation.

**Integration Point**: `backend/app/services/processing/output/neo4j_generator.py`

The processing pipeline calls Neo4jClient methods to:
1. Create Content node with embedding and summary
2. Create Concept nodes for extracted concepts
3. Create CONTAINS relationships (Content → Concept)
4. Create Tag relationships if applicable

**Deliverables:** ✅ All Complete
- [x] Content node creation from ProcessingResult
- [x] Concept extraction and linking
- [x] Tag relationship creation
- [x] Embedding storage

---

#### Task 4A.2: Obsidian Vault Sync

**Why this matters:** Bi-directional sync keeps the graph and vault consistent. When users edit notes in Obsidian (add links, change tags), those changes should reflect in Neo4j.

**Implementation**: `backend/app/services/obsidian/sync.py`

**Neo4j Client Extensions** (in `client.py`):
- `merge_note_node()` - Create/update Note nodes from Obsidian files
- `sync_note_links()` - Sync wikilinks as LINKS_TO relationships

**Note vs Content Nodes:**
- **Content nodes**: Have embeddings, summaries, full processing result
- **Note nodes**: Lightweight, represent Obsidian files, track wikilinks

**Sync Strategy** (see Obsidian implementation plan for full details):
1. Real-time sync via VaultWatcher
2. Startup reconciliation for offline changes
3. Manual full sync via API

**Deliverables:** ✅ All Complete
- [x] Note node operations in Neo4jClient
- [x] VaultSyncService implementation
- [x] Three-tier sync strategy
- [x] Wikilink → LINKS_TO mapping

---

### Phase 4B: Preliminary Graph Visualization UI (Week 13-14) — 🔲 Next Up

**Why this matters:** A visual representation of the knowledge graph provides immediate value—users can see their knowledge growing, discover connections, and navigate between related content. This preliminary UI provides essential feedback while the full Knowledge Explorer is developed later.

#### Task 4B.1: Graph API Endpoint

**Location**: `backend/app/routers/knowledge.py` (new file)

**Why this matters:** The frontend needs a simple API to fetch graph data for visualization. This minimal endpoint returns nodes and edges in a format ready for D3/force-graph rendering.

**Endpoint Specification:**

```python
# backend/app/routers/knowledge.py

from fastapi import APIRouter, Query
from app.services.knowledge_graph import get_neo4j_client

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

@router.get("/graph")
async def get_graph_visualization(
    center_id: str | None = Query(None, description="Center graph on this node ID"),
    node_types: str = Query("Content,Concept", description="Comma-separated node types"),
    depth: int = Query(2, ge=1, le=4, description="Traversal depth from center"),
    limit: int = Query(100, ge=10, le=500, description="Max nodes to return"),
) -> GraphResponse:
    """Get graph data for visualization.
    
    Returns nodes and edges in D3-compatible format:
    - nodes: [{id, label, type, size, color, ...}]
    - edges: [{source, target, type, strength, ...}]
    """

@router.get("/stats")
async def get_graph_stats() -> GraphStats:
    """Get summary statistics for the knowledge graph."""
```

**Response Schema:**

```python
class GraphNode(BaseModel):
    id: str
    label: str                    # Display title
    type: str                     # "Content", "Concept", "Note"
    content_type: str | None      # "paper", "article", etc. (for Content nodes)
    size: int = 1                 # Node size weight (based on connections)
    color: str | None             # Optional color hint
    metadata: dict = {}           # Additional properties

class GraphEdge(BaseModel):
    source: str                   # Source node ID
    target: str                   # Target node ID
    type: str                     # Relationship type
    strength: float = 1.0         # Edge weight
    label: str | None             # Display label

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_id: str | None
    total_nodes: int              # Total in graph (before limit)
    total_edges: int

class GraphStats(BaseModel):
    total_content: int
    total_concepts: int
    total_notes: int
    total_relationships: int
    content_by_type: dict[str, int]
```

**Neo4j Query (in `queries.py`):**

```cypher
// GET_VISUALIZATION_GRAPH query
MATCH (n)
WHERE labels(n)[0] IN $node_types
OPTIONAL MATCH (n)-[r]->(m)
WHERE labels(m)[0] IN $node_types
WITH n, r, m
LIMIT $limit
RETURN 
  collect(DISTINCT {
    id: n.id,
    label: COALESCE(n.title, n.name, n.id),
    type: labels(n)[0],
    content_type: n.type
  }) AS nodes,
  collect(DISTINCT {
    source: n.id,
    target: m.id,
    type: type(r),
    strength: COALESCE(r.strength, 1.0)
  }) AS edges
```

**Deliverables:**
- [ ] Create `backend/app/routers/knowledge.py` with `/graph` endpoint
- [ ] Add graph response schemas
- [ ] Add visualization query to `queries.py`
- [ ] Register router in `main.py`
- [ ] Add `/stats` endpoint for dashboard

---

#### Task 4B.2: Graph Viewer Component

**Location**: `frontend/src/components/GraphViewer/`

**Why this matters:** The frontend already has `react-force-graph-2d` and `d3` installed. A simple graph viewer component provides visual exploration of the knowledge graph.

**Technology Stack (Already Installed):**
- `react-force-graph-2d` v1.25.0 — Force-directed graph rendering
- `d3` v7.8.5 — Data manipulation and scales
- `@tanstack/react-query` — Data fetching with caching
- `tailwindcss` — Styling
- `framer-motion` — Animations

**Component Structure:**

```
frontend/src/
├── components/
│   └── GraphViewer/
│       ├── index.jsx              # Main export
│       ├── GraphViewer.jsx        # Core component
│       ├── GraphControls.jsx      # Zoom, filter, layout controls
│       ├── NodeTooltip.jsx        # Hover tooltip
│       ├── GraphLegend.jsx        # Node type legend
│       └── useGraphData.js        # Data fetching hook
├── pages/
│   └── KnowledgeGraph.jsx         # Full-page graph view
└── api/
    └── knowledge.js               # API client functions
```

**Core Component Implementation:**

```jsx
// frontend/src/components/GraphViewer/GraphViewer.jsx
import { useCallback, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { useGraphData } from './useGraphData'
import { GraphControls } from './GraphControls'
import { NodeTooltip } from './NodeTooltip'
import { GraphLegend } from './GraphLegend'

const NODE_COLORS = {
  Content: '#6366f1',   // Indigo for content
  Concept: '#10b981',   // Emerald for concepts
  Note: '#f59e0b',      // Amber for notes
}

const CONTENT_TYPE_COLORS = {
  paper: '#8b5cf6',     // Violet
  article: '#3b82f6',   // Blue
  book: '#ec4899',      // Pink
  code: '#14b8a6',      // Teal
  idea: '#f97316',      // Orange
}

export function GraphViewer({ centerId, onNodeClick }) {
  const graphRef = useRef()
  const { data, isLoading, error } = useGraphData(centerId)
  
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const label = node.label
    const fontSize = 12 / globalScale
    const nodeColor = node.content_type 
      ? CONTENT_TYPE_COLORS[node.content_type] || NODE_COLORS[node.type]
      : NODE_COLORS[node.type]
    
    // Draw node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI)
    ctx.fillStyle = nodeColor
    ctx.fill()
    
    // Draw label
    ctx.font = `${fontSize}px Sans-Serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = '#1f2937'
    ctx.fillText(label, node.x, node.y + 10)
  }, [])

  if (isLoading) return <GraphSkeleton />
  if (error) return <GraphError error={error} />

  return (
    <div className="relative h-full w-full bg-slate-50 rounded-lg overflow-hidden">
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        nodeCanvasObject={nodeCanvasObject}
        linkColor={() => '#cbd5e1'}
        linkWidth={link => link.strength * 2}
        onNodeClick={onNodeClick}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
      <GraphControls graphRef={graphRef} />
      <GraphLegend />
    </div>
  )
}
```

**Data Fetching Hook:**

```javascript
// frontend/src/components/GraphViewer/useGraphData.js
import { useQuery } from '@tanstack/react-query'
import { fetchGraph } from '../../api/knowledge'

export function useGraphData(centerId = null, options = {}) {
  return useQuery({
    queryKey: ['graph', centerId, options],
    queryFn: () => fetchGraph({ centerId, ...options }),
    staleTime: 30_000,  // Cache for 30 seconds
    select: (data) => ({
      nodes: data.nodes,
      links: data.edges.map(e => ({
        source: e.source,
        target: e.target,
        type: e.type,
        strength: e.strength,
      })),
    }),
  })
}
```

**API Client:**

```javascript
// frontend/src/api/knowledge.js
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchGraph({ centerId, nodeTypes, depth, limit } = {}) {
  const params = new URLSearchParams()
  if (centerId) params.set('center_id', centerId)
  if (nodeTypes) params.set('node_types', nodeTypes)
  if (depth) params.set('depth', depth)
  if (limit) params.set('limit', limit)
  
  const response = await axios.get(`${API_URL}/api/knowledge/graph?${params}`)
  return response.data
}

export async function fetchGraphStats() {
  const response = await axios.get(`${API_URL}/api/knowledge/stats`)
  return response.data
}
```

**Deliverables:**
- [ ] Create `GraphViewer` component with force-directed layout
- [ ] Implement node coloring by type
- [ ] Add zoom/pan controls
- [ ] Add node hover tooltips
- [ ] Add legend for node types
- [ ] Create data fetching hook with React Query

---

#### Task 4B.3: Knowledge Graph Page

**Location**: `frontend/src/pages/KnowledgeGraph.jsx`

**Why this matters:** A dedicated page for the graph viewer with stats sidebar provides a focused exploration experience.

**Page Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: "Knowledge Graph"                    [Refresh] [Filter]│
├────────────────────────────────────────────────┬────────────────┤
│                                                │  Stats Panel   │
│                                                │  ────────────  │
│                                                │  📄 42 Content │
│           Force-Directed Graph                 │  💡 128 Concepts│
│           (react-force-graph-2d)               │  📝 67 Notes   │
│                                                │  🔗 312 Links  │
│                                                │  ────────────  │
│                                                │  By Type:      │
│                                                │  • papers: 15  │
│                                                │  • articles: 20│
│                                                │  • books: 7    │
├────────────────────────────────────────────────┴────────────────┤
│  Node Details (when selected): Title | Type | Tags | Open Note  │
└─────────────────────────────────────────────────────────────────┘
```

**Page Component:**

```jsx
// frontend/src/pages/KnowledgeGraph.jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { GraphViewer } from '../components/GraphViewer'
import { fetchGraphStats } from '../api/knowledge'

export default function KnowledgeGraphPage() {
  const [selectedNode, setSelectedNode] = useState(null)
  const { data: stats } = useQuery({
    queryKey: ['graph-stats'],
    queryFn: fetchGraphStats,
  })

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Header */}
      <header className="px-6 py-4 bg-white border-b border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Knowledge Graph</h1>
      </header>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Area */}
        <main className="flex-1 p-4">
          <GraphViewer 
            onNodeClick={setSelectedNode}
            centerId={selectedNode?.id}
          />
        </main>
        
        {/* Stats Sidebar */}
        <aside className="w-72 bg-white border-l border-slate-200 p-4">
          <h2 className="text-lg font-semibold mb-4">Statistics</h2>
          {stats && (
            <div className="space-y-3">
              <StatItem icon="📄" label="Content" value={stats.total_content} />
              <StatItem icon="💡" label="Concepts" value={stats.total_concepts} />
              <StatItem icon="📝" label="Notes" value={stats.total_notes} />
              <StatItem icon="🔗" label="Relationships" value={stats.total_relationships} />
              
              <hr className="my-4" />
              
              <h3 className="text-sm font-medium text-slate-500">By Type</h3>
              {Object.entries(stats.content_by_type).map(([type, count]) => (
                <div key={type} className="flex justify-between text-sm">
                  <span className="capitalize">{type}</span>
                  <span className="text-slate-600">{count}</span>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
      
      {/* Selected Node Details */}
      {selectedNode && (
        <footer className="px-6 py-3 bg-white border-t border-slate-200">
          <NodeDetails node={selectedNode} onClose={() => setSelectedNode(null)} />
        </footer>
      )}
    </div>
  )
}
```

**Deliverables:**
- [ ] Create Knowledge Graph page with layout
- [ ] Integrate GraphViewer component
- [ ] Add stats sidebar with React Query
- [ ] Add selected node details panel
- [ ] Add route in React Router (`/graph`)

---

#### Task 4B.4: Integration & Navigation

**Why this matters:** The graph should be accessible from the main app navigation and integrate with existing features.

**Updates Required:**

1. **Add route** in `frontend/src/App.jsx`:
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import KnowledgeGraphPage from './pages/KnowledgeGraph'

// Add route
<Route path="/graph" element={<KnowledgeGraphPage />} />
```

2. **Add navigation link** in header/sidebar:
```jsx
<NavLink to="/graph" icon={<GraphIcon />}>Knowledge Graph</NavLink>
```

3. **Register API router** in `backend/app/main.py`:
```python
from app.routers import knowledge

app.include_router(knowledge.router)
```

**Deliverables:**
- [ ] Add `/graph` route to React Router
- [ ] Add navigation link to Knowledge Graph
- [ ] Register knowledge router in FastAPI
- [ ] Test end-to-end graph loading

---

#### Task 4B.5: Visual Design

**Why this matters:** An attractive, distinctive visual design differentiates the app from generic "AI slop" aesthetics.

**Design Principles:**
- **Dark graph background** with light nodes for focus
- **Glow effects** on nodes to suggest knowledge "illumination"
- **Organic animations** — nodes breathe and edges flow
- **High contrast** node colors for easy type differentiation

**Color Palette:**

```css
/* Graph-specific colors */
--graph-bg: #0f172a;           /* Slate 900 - deep background */
--graph-grid: #1e293b33;       /* Subtle grid overlay */
--node-content: #818cf8;       /* Indigo 400 */
--node-concept: #34d399;       /* Emerald 400 */
--node-note: #fbbf24;          /* Amber 400 */
--edge-default: #475569;       /* Slate 600 */
--edge-strong: #94a3b8;        /* Slate 400 */
--glow-color: rgba(129, 140, 248, 0.4);
```

**Node Glow Effect:**

```javascript
// In nodeCanvasObject callback
const gradient = ctx.createRadialGradient(
  node.x, node.y, 0,
  node.x, node.y, 15
)
gradient.addColorStop(0, nodeColor)
gradient.addColorStop(0.5, `${nodeColor}66`)  // Semi-transparent
gradient.addColorStop(1, 'transparent')

ctx.fillStyle = gradient
ctx.fillRect(node.x - 15, node.y - 15, 30, 30)
```

**Deliverables:**
- [ ] Apply dark theme to graph container
- [ ] Add node glow effects
- [ ] Style stats sidebar to match
- [ ] Add subtle grid background
- [ ] Ensure accessibility (color contrast)

---

## 4. Remaining Work (Future Phases)

### Knowledge API Router — 🔲 Phase 5+

**Why this matters:** Expose graph operations via REST API for frontend integration, enabling the Knowledge Explorer UI.

**Planned Endpoints:**

```python
# Future: backend/app/routers/knowledge.py

@router.get("/health")
async def knowledge_graph_health()
"""Check Neo4j connection health."""

@router.get("/stats")
async def get_graph_stats()
"""Get knowledge graph statistics (node counts, relationship counts)."""

@router.post("/search")
async def semantic_search(request: SearchRequest)
"""Perform semantic search across the knowledge graph."""

@router.get("/search/similar/{source_id}")
async def find_similar(source_id: str, top_k: int = 5)
"""Find sources similar to the given source."""

@router.get("/path")
async def find_path(concept_a: str, concept_b: str, max_hops: int = 5)
"""Find the shortest path between two concepts."""

@router.get("/prerequisites/{concept_name}")
async def get_prerequisites(concept_name: str, max_depth: int = 10)
"""Get prerequisites for understanding a concept."""

@router.get("/learning-path/{concept_name}")
async def get_learning_path(concept_name: str)
"""Generate a learning path to understand a concept."""

@router.get("/topic/{topic_name}")
async def get_topic_knowledge(topic_name: str)
"""Get all knowledge about a topic."""

@router.get("/connections/{source_id}")
async def find_connections(source_id: str)
"""Find unexpected connections to a source."""

@router.get("/graph")
async def get_graph_visualization(center_id: str = None, depth: int = 2)
"""Get graph data for visualization."""
```

---

### Advanced Query Service — 🔲 Phase 5+

**Why this matters:** Higher-level query patterns for knowledge discovery and learning support.

**Planned Features:**

```python
# Future: backend/app/services/knowledge_graph/knowledge_queries.py

class KnowledgeQueries:
    """Common query patterns for knowledge discovery."""
    
    async def find_path_between_concepts(
        self, concept_a: str, concept_b: str, max_hops: int = 5
    ) -> PathResult:
        """Find the shortest path between two concepts.
        Answers: "What connects concept A to concept B?"
        """
    
    async def get_concept_prerequisites(
        self, concept_name: str, max_depth: int = 10
    ) -> list[dict]:
        """Get all prerequisites for understanding a concept.
        Answers: "What do I need to know before learning X?"
        """
    
    async def get_learning_path(self, target_concept: str) -> list[dict]:
        """Generate a learning path to understand a concept.
        Returns concepts ordered from foundational to target.
        """
    
    async def get_topic_knowledge(self, topic_name: str) -> dict:
        """Get all knowledge about a topic.
        Answers: "What do I know about topic X?"
        """
    
    async def find_unexpected_connections(
        self, source_id: str, min_hops: int = 2, max_hops: int = 3
    ) -> list[dict]:
        """Find sources connected through indirect concept relationships.
        Surfaces non-obvious connections for serendipitous discovery.
        """
```

---

### Graph Visualization Queries — 🔲 Phase 5+

**Why this matters:** Optimized queries for rendering graph visualizations in the frontend.

```python
# Future: backend/app/services/knowledge_graph/visualization_queries.py

class GraphVisualizationQueries:
    """Queries optimized for graph visualization."""
    
    async def get_subgraph(
        self, center_id: str, center_type: str = "Content", depth: int = 2
    ) -> GraphData:
        """Get a subgraph centered on a specific node.
        Returns nodes and edges in D3-compatible format.
        """
    
    async def get_overview_graph(
        self, node_types: list[str] = None, max_nodes: int = 100
    ) -> GraphData:
        """Get an overview graph for the full knowledge base.
        Prioritizes most-connected nodes for visibility.
        """
```

---

### Hybrid Search — 🔲 Phase 5+

**Why this matters:** Combine vector and full-text search for better results when users provide both keywords and semantic intent.

```python
# Future enhancement to vector_search.py

async def hybrid_search(
    query_text: str,
    embedding: list[float],
    node_type: str = "Content",
    top_k: int = 10,
    text_weight: float = 0.3,
    vector_weight: float = 0.7
) -> list[SearchResult]:
    """Combine vector and full-text search for better results.
    
    Uses both:
    - Full-text index for keyword matching
    - Vector index for semantic similarity
    - Weighted combination of scores
    """
```

---

## 5. Testing Strategy

### 5.1 Test Structure

```
tests/
├── unit/knowledge_graph/
│   ├── test_client.py              # Neo4jClient connection, operations
│   ├── test_queries.py             # Query pattern tests
│   └── test_schemas.py             # Schema validation
├── integration/
│   ├── test_neo4j_integration.py   # Full Neo4j integration tests
│   └── test_vault_sync.py          # Vault sync integration
└── fixtures/
    └── mock_embeddings.py          # Mock embedding vectors
```

### 5.2 Key Test Cases

| Component | Test Case | Priority | Status |
|-----------|-----------|----------|--------|
| Client | Connection pooling and lazy init | High | ✅ |
| Client | Health check returns correct status | High | ✅ |
| Schema | All indexes created successfully | High | ✅ |
| Schema | Vector indexes with correct dimensions | High | ✅ |
| Operations | MERGE creates node idempotently | High | ✅ |
| Operations | Embedding set correctly | High | ✅ |
| Vector Search | Returns results sorted by score | High | ✅ |
| Vector Search | Respects threshold | High | ✅ |
| Sync | Note node created from vault file | High | ✅ |
| Sync | LINKS_TO relationships synced | High | ✅ |
| **Graph API** | `/graph` returns nodes and edges | High | 🔲 |
| **Graph API** | `/stats` returns correct counts | High | 🔲 |
| **Graph API** | Center node filtering works | Medium | 🔲 |
| **Graph UI** | Graph renders without errors | High | 🔲 |
| **Graph UI** | Nodes colored by type | Medium | 🔲 |
| **Graph UI** | Click node shows details | Medium | 🔲 |
| Queries | Path finding returns valid path | High | 🔲 |
| Queries | Prerequisites ordered by depth | Medium | 🔲 |
| API | Search returns valid SearchResult | High | 🔲 |

---

## 6. Configuration Summary

### 6.1 Settings

```python
# From app/config/settings.py
NEO4J_URI: str = "bolt://localhost:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = ""
NEO4J_DATABASE: str = "neo4j"

# From app/config/processing.py
NEO4J_VECTOR_SEARCH_TOP_K: int = 20
NEO4J_VECTOR_SEARCH_THRESHOLD: float = 0.7
NEO4J_SUMMARY_TRUNCATE: int = 500
NEO4J_GRAPH_TRAVERSAL_DEPTH: int = 2
```

---

## 7. Success Criteria

### Functional — ✅ Core Complete
- [x] Neo4j client connects reliably with connection pooling
- [x] Schema initialized with all indexes on startup
- [x] Vector search returns relevant results
- [x] Processing results import creates correct graph structure
- [x] Vault sync updates tags and links bidirectionally
- [ ] Graph API endpoint returns nodes and edges (next up)
- [ ] Preliminary Graph UI renders knowledge graph (next up)
- [ ] Knowledge API endpoints return valid responses (future)
- [ ] Path queries find connections between concepts (future)

### Non-Functional
- [x] Vector search < 100ms for 10 results
- [x] Connection pool handles concurrent requests
- [x] Import handles documents without failure
- [ ] Graph renders smoothly with 100+ nodes (next up)
- [ ] Graph API responds in < 500ms (next up)

### Integration
- [x] Integrates with LLM Processing Layer (Phase 3)
- [x] Integrates with Obsidian Knowledge Hub (Phase 4)
- [ ] Preliminary Graph UI loads from Neo4j (next up)
- [ ] Provides data for full Knowledge Explorer UI (Phase 5)
- [ ] Supports spaced repetition queries (future)

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Neo4j Enterprise required for vector indexes | Medium | Low | Community edition works with vector indexes in Neo4j 5.x |
| Large graph performance degradation | Medium | Low | Implement pagination, index optimization |
| Embedding dimension mismatch | High | Low | Validate dimensions on import |
| Sync conflicts between Obsidian and Neo4j | Medium | Medium | Last-write-wins, audit log |
| APOC plugin not available | Medium | Low | Implement fallback queries without APOC |

---

## 9. Dependencies

### Required Before This Phase — ✅ Complete
- [x] Phase 1: Foundation (Neo4j container, FastAPI)
- [x] Phase 3: LLM Processing (ProcessingResult model)

### Enables After This Phase
- **Phase 4B (Next)**: Preliminary Graph Visualization UI
- Phase 5: Full Knowledge Explorer UI (advanced features)
- Phase 6: Practice Session (mastery question queries)
- Phase 7: Spaced Repetition (learning queries)

---

## 10. Open Questions (For Future Phases)

1. **Embedding Generation**: Should we generate embeddings for concepts separately, or derive from source embeddings?
2. **Conflict Resolution**: How to handle conflicts when the same concept is extracted from multiple sources with different definitions?
3. **Graph Cleanup**: Should we implement orphan node cleanup (concepts not linked to any source)?
4. **Historical Queries**: Do we need to track historical graph state for "what did I know last month?" queries?

---

## 11. Related Documents

- `design_docs/04_knowledge_graph_neo4j.md` — Design specification
- `implementation_plan/00_foundation_implementation.md` — Infrastructure setup
- `implementation_plan/02_llm_processing_implementation.md` — ProcessingResult model
- `implementation_plan/03_knowledge_hub_obsidian_implementation.md` — Vault sync
- `design_docs/06_backend_api.md` — API design patterns
