# Knowledge Graph (Neo4j) Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `02_llm_processing_layer.md`, `03_knowledge_hub_obsidian.md`

---

## 1. Overview

Neo4j provides graph-based storage for concepts, relationships, and semantic connections. It enables queries that would be difficult in traditional databases: "What connects X to Y?", "What are the prerequisites for learning Z?", "What do I know about topic T?"

### Design Goals

1. **Relationship-First**: Model knowledge as connected concepts
2. **Semantic Search**: Vector embeddings for similarity queries
3. **Bi-Directional Sync**: Stay in sync with Obsidian vault
4. **Query Performance**: Fast traversal for common patterns
5. **Extensibility**: Easy to add new node/edge types

---

## 2. Graph Schema

### 2.1 Node Types

```cypher
// Core node types

// Source documents (papers, articles, books, etc.)
(:Source {
  id: string,           // UUID
  type: string,         // paper, article, book, code, idea
  title: string,
  authors: [string],
  source_url: string,
  created_at: datetime,
  processed_at: datetime,
  summary: string,
  embedding: [float],   // 1536-dim vector
  obsidian_path: string // Path in vault
})

// Extracted concepts
(:Concept {
  id: string,
  name: string,
  definition: string,
  domain: string,       // ml, systems, leadership, etc.
  complexity: string,   // foundational, intermediate, advanced
  embedding: [float],
  obsidian_path: string
})

// Topic categories
(:Topic {
  id: string,
  name: string,         // e.g., "machine-learning"
  path: string,         // e.g., "ml/deep-learning/transformers"
  description: string,
  parent_path: string   // For hierarchy
})

// People (authors, researchers)
(:Person {
  id: string,
  name: string,
  affiliation: string,
  homepage: string
})

// Tags from controlled vocabulary
(:Tag {
  id: string,
  name: string,         // e.g., "ml/transformers"
  category: string      // domain, status, quality
})

// Learning records
(:MasteryQuestion {
  id: string,
  question: string,
  source_id: string,
  difficulty: string,
  hints: [string],
  key_points: [string]
})
```

### 2.2 Relationship Types

```cypher
// Document relationships
(:Source)-[:CITES]->(:Source)           // Paper cites another paper
(:Source)-[:EXTENDS]->(:Source)         // Builds upon prior work
(:Source)-[:CONTRADICTS]->(:Source)     // Challenges prior work
(:Source)-[:RELATES_TO]->(:Source)      // General relationship

// Concept relationships
(:Concept)-[:PREREQUISITE_FOR]->(:Concept)  // Must understand A before B
(:Concept)-[:RELATES_TO]->(:Concept)        // General connection
(:Concept)-[:SUBCLASS_OF]->(:Concept)       // Hierarchy (e.g., CNN subclass of Neural Network)
(:Concept)-[:USED_IN]->(:Concept)           // Technique used in another

// Source-Concept relationships
(:Source)-[:INTRODUCES]->(:Concept)     // First to define concept
(:Source)-[:EXPLAINS]->(:Concept)       // Contains explanation of concept
(:Source)-[:APPLIES]->(:Concept)        // Uses concept in practice

// Person relationships
(:Person)-[:AUTHORED]->(:Source)
(:Person)-[:WORKS_ON]->(:Concept)

// Tag relationships
(:Source)-[:TAGGED_WITH]->(:Tag)
(:Concept)-[:TAGGED_WITH]->(:Tag)

// Topic hierarchy
(:Topic)-[:SUBTOPIC_OF]->(:Topic)
(:Source)-[:BELONGS_TO]->(:Topic)
(:Concept)-[:BELONGS_TO]->(:Topic)

// Learning relationships
(:MasteryQuestion)-[:TESTS]->(:Concept)
(:MasteryQuestion)-[:FROM_SOURCE]->(:Source)
```

### 2.3 Schema Visualization

```
                    ┌──────────┐
                    │  Person  │
                    └────┬─────┘
                         │ AUTHORED
                         ▼
    ┌───────┐      ┌──────────┐      ┌─────────┐
    │  Tag  │◀─────│  Source  │─────▶│ Concept │
    └───────┘      └────┬─────┘      └────┬────┘
         ▲              │                 │
         │              │ BELONGS_TO      │ PREREQUISITE_FOR
         │              ▼                 ▼
         │         ┌─────────┐      ┌─────────┐
         └─────────│  Topic  │◀─────│ Concept │
                   └─────────┘      └─────────┘
                        │
                        │ SUBTOPIC_OF
                        ▼
                   ┌─────────┐
                   │  Topic  │
                   └─────────┘
```

---

## 3. Vector Search Configuration

### 3.1 Index Creation

```cypher
// Create vector index for semantic search on Sources
CREATE VECTOR INDEX source_embedding IF NOT EXISTS
FOR (s:Source)
ON (s.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}

// Create vector index for Concepts
CREATE VECTOR INDEX concept_embedding IF NOT EXISTS
FOR (c:Concept)
ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}

// Full-text search indices
CREATE FULLTEXT INDEX source_text IF NOT EXISTS
FOR (s:Source)
ON EACH [s.title, s.summary]

CREATE FULLTEXT INDEX concept_text IF NOT EXISTS
FOR (c:Concept)
ON EACH [c.name, c.definition]
```

### 3.2 Vector Search Queries

```python
# backend/app/services/neo4j_client.py

from neo4j import AsyncGraphDatabase

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async def vector_search(
        self,
        embedding: list[float],
        node_type: str = "Source",
        top_k: int = 10,
        min_score: float = 0.7
    ) -> list[dict]:
        """Find similar nodes by embedding."""
        
        query = f"""
        CALL db.index.vector.queryNodes(
          '{node_type.lower()}_embedding',
          $top_k,
          $embedding
        ) YIELD node, score
        WHERE score >= $min_score
        RETURN node {{
          .id, .title, .summary, .type,
          score: score
        }} as result
        ORDER BY score DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                embedding=embedding,
                top_k=top_k,
                min_score=min_score
            )
            return [record["result"] async for record in result]
    
    async def hybrid_search(
        self,
        query_text: str,
        embedding: list[float],
        top_k: int = 10
    ) -> list[dict]:
        """Combine vector and full-text search."""
        
        query = """
        // Full-text search
        CALL db.index.fulltext.queryNodes('source_text', $query_text)
        YIELD node as textNode, score as textScore
        
        // Vector search
        CALL db.index.vector.queryNodes('source_embedding', $top_k, $embedding)
        YIELD node as vectorNode, score as vectorScore
        
        // Combine results
        WITH collect({node: textNode, score: textScore * 0.3}) as textResults,
             collect({node: vectorNode, score: vectorScore * 0.7}) as vectorResults
        UNWIND textResults + vectorResults as result
        WITH result.node as node, max(result.score) as combinedScore
        RETURN node {.id, .title, .summary, score: combinedScore}
        ORDER BY combinedScore DESC
        LIMIT $top_k
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                query_text=query_text,
                embedding=embedding,
                top_k=top_k
            )
            return [record async for record in result]
```

---

## 4. Common Query Patterns

### 4.1 Knowledge Discovery

```cypher
// What connects concept A to concept B?
MATCH path = shortestPath(
  (a:Concept {name: $concept_a})-[*..5]-(b:Concept {name: $concept_b})
)
RETURN path

// What are the prerequisites for understanding concept X?
MATCH path = (prereq:Concept)-[:PREREQUISITE_FOR*]->(target:Concept {name: $concept})
RETURN prereq, path
ORDER BY length(path)

// What do I know about topic X?
MATCH (t:Topic {name: $topic})<-[:BELONGS_TO]-(s:Source)
OPTIONAL MATCH (s)-[:EXPLAINS]->(c:Concept)
RETURN s.title as source, collect(c.name) as concepts
ORDER BY s.processed_at DESC
```

### 4.2 Learning Queries

```cypher
// Find concepts I haven't practiced recently
MATCH (c:Concept)<-[:TESTS]-(q:MasteryQuestion)
WHERE NOT exists((q)<-[:ATTEMPTED]-(:PracticeAttempt {date: date()}))
RETURN c.name, c.complexity, count(q) as question_count
ORDER BY c.complexity, question_count DESC
LIMIT 10

// Get learning path for a topic
MATCH path = (start:Concept)-[:PREREQUISITE_FOR*]->(end:Concept)
WHERE end.name = $target_concept
WITH nodes(path) as concepts, length(path) as depth
UNWIND concepts as c
RETURN DISTINCT c.name, c.complexity, depth
ORDER BY depth
```

### 4.3 Connection Discovery

```cypher
// Find unexpected connections (2+ hops)
MATCH (s1:Source {id: $source_id})-[:EXPLAINS]->(c1:Concept)
MATCH (c1)-[:RELATES_TO*2..3]-(c2:Concept)<-[:EXPLAINS]-(s2:Source)
WHERE s1 <> s2
RETURN s2.title, collect(DISTINCT c2.name) as shared_concepts
ORDER BY size(shared_concepts) DESC
LIMIT 5

// Find sources that bridge topics
MATCH (s:Source)-[:BELONGS_TO]->(t1:Topic)
MATCH (s)-[:BELONGS_TO]->(t2:Topic)
WHERE t1 <> t2
RETURN s.title, collect(DISTINCT t1.name) as topics
ORDER BY size(topics) DESC
LIMIT 10
```

---

## 5. Data Import/Export

### 5.1 Import from Processing Pipeline

```python
async def import_processed_content(
    result: ProcessingResult,
    neo4j_client: Neo4jClient
):
    """Import processing results into Neo4j."""
    
    # Create Source node
    await neo4j_client.run("""
        MERGE (s:Source {id: $id})
        SET s.title = $title,
            s.type = $type,
            s.summary = $summary,
            s.embedding = $embedding,
            s.processed_at = datetime(),
            s.obsidian_path = $obsidian_path
    """, {
        "id": result.content_id,
        "title": result.content.title,
        "type": result.analysis.content_type,
        "summary": result.summaries[SummaryLevel.STANDARD],
        "embedding": result.embedding,
        "obsidian_path": result.obsidian_path
    })
    
    # Create Concept nodes
    for concept in result.concepts.concepts:
        await neo4j_client.run("""
            MERGE (c:Concept {name: $name})
            SET c.definition = $definition,
                c.domain = $domain,
                c.complexity = $complexity
            
            WITH c
            MATCH (s:Source {id: $source_id})
            MERGE (s)-[:EXPLAINS]->(c)
        """, {
            "name": concept.name,
            "definition": concept.definition,
            "domain": result.analysis.domain,
            "complexity": concept.importance,
            "source_id": result.content_id
        })
    
    # Create connections
    for conn in result.connections:
        await neo4j_client.run("""
            MATCH (s1:Source {id: $source_id})
            MATCH (s2:Source {id: $target_id})
            MERGE (s1)-[r:$rel_type]->(s2)
            SET r.strength = $strength,
                r.explanation = $explanation
        """, {
            "source_id": result.content_id,
            "target_id": conn.target_id,
            "rel_type": conn.relationship_type,
            "strength": conn.strength,
            "explanation": conn.explanation
        })
    
    # Create tags
    for tag in result.tags.get("domain_tags", []):
        await neo4j_client.run("""
            MERGE (t:Tag {name: $tag})
            WITH t
            MATCH (s:Source {id: $source_id})
            MERGE (s)-[:TAGGED_WITH]->(t)
        """, {
            "tag": tag,
            "source_id": result.content_id
        })
```

### 5.2 Sync with Obsidian

```python
async def sync_obsidian_to_neo4j(vault_path: Path, neo4j_client: Neo4jClient):
    """Full sync from Obsidian vault to Neo4j."""
    
    for note_path in vault_path.rglob("*.md"):
        fm = frontmatter.load(note_path)
        
        # Determine node type
        note_type = fm.get("type", "note")
        
        if note_type in ["paper", "article", "book", "code", "idea"]:
            await neo4j_client.run("""
                MERGE (s:Source {obsidian_path: $path})
                SET s.title = $title,
                    s.type = $type,
                    s.tags = $tags
            """, {
                "path": str(note_path),
                "title": fm.get("title", note_path.stem),
                "type": note_type,
                "tags": fm.get("tags", [])
            })
        
        elif note_type == "concept":
            await neo4j_client.run("""
                MERGE (c:Concept {obsidian_path: $path})
                SET c.name = $name,
                    c.definition = $definition
            """, {
                "path": str(note_path),
                "name": fm.get("name", note_path.stem),
                "definition": fm.get("definition", "")
            })
        
        # Extract and create links
        content = note_path.read_text()
        links = extract_wikilinks(content)
        
        for link_title in links:
            await neo4j_client.run("""
                MATCH (source {obsidian_path: $source_path})
                MERGE (target {title: $target_title})
                MERGE (source)-[:LINKS_TO]->(target)
            """, {
                "source_path": str(note_path),
                "target_title": link_title
            })
```

---

## 6. Graph Visualization

### 6.1 Frontend Integration

```typescript
// frontend/src/components/KnowledgeGraph/GraphVisualization.tsx

interface GraphNode {
  id: string;
  label: string;
  type: 'Source' | 'Concept' | 'Topic';
  properties: Record<string, any>;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// D3-force simulation configuration
const forceConfig = {
  charge: -300,
  linkDistance: 100,
  centerStrength: 0.1,
};

// Color by node type
const nodeColors = {
  Source: '#4f46e5',   // Indigo
  Concept: '#10b981',  // Green
  Topic: '#f59e0b',    // Amber
};

// Node size by importance
const getNodeSize = (node: GraphNode): number => {
  const connectionCount = node.properties.connectionCount || 1;
  return Math.min(20 + Math.log(connectionCount) * 5, 50);
};
```

### 6.2 Graph Export for Visualization

```python
@router.get("/api/knowledge/graph")
async def get_graph_data(
    center_id: str = None,
    depth: int = 2,
    node_types: list[str] = ["Source", "Concept"],
    max_nodes: int = 100
):
    """Get graph data for visualization."""
    
    if center_id:
        # Get subgraph centered on node
        query = """
        MATCH (center {id: $center_id})
        CALL apoc.path.subgraphAll(center, {
          maxLevel: $depth,
          labelFilter: $label_filter
        })
        YIELD nodes, relationships
        RETURN nodes, relationships
        LIMIT $max_nodes
        """
    else:
        # Get overview graph
        query = """
        MATCH (n)
        WHERE any(label in labels(n) WHERE label IN $node_types)
        WITH n LIMIT $max_nodes
        MATCH (n)-[r]-(m)
        WHERE any(label in labels(m) WHERE label IN $node_types)
        RETURN collect(DISTINCT n) + collect(DISTINCT m) as nodes,
               collect(DISTINCT r) as relationships
        """
    
    result = await neo4j_client.run(query, {
        "center_id": center_id,
        "depth": depth,
        "node_types": node_types,
        "max_nodes": max_nodes,
        "label_filter": "|".join(node_types)
    })
    
    return format_graph_response(result)
```

---

## 7. Performance Optimization

### 7.1 Indexes

```cypher
// Unique constraints
CREATE CONSTRAINT source_id IF NOT EXISTS
FOR (s:Source) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT concept_name IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE;

// Lookup indexes
CREATE INDEX source_type IF NOT EXISTS
FOR (s:Source) ON (s.type);

CREATE INDEX source_obsidian_path IF NOT EXISTS
FOR (s:Source) ON (s.obsidian_path);

CREATE INDEX concept_domain IF NOT EXISTS
FOR (c:Concept) ON (c.domain);

CREATE INDEX tag_name IF NOT EXISTS
FOR (t:Tag) ON (t.name);
```

### 7.2 Query Optimization Tips

```cypher
// Use parameters, not string concatenation
// ✅ Good
MATCH (s:Source {type: $type}) RETURN s

// ❌ Bad
MATCH (s:Source {type: 'paper'}) RETURN s

// Use LIMIT early
// ✅ Good
MATCH (s:Source)
WITH s LIMIT 100
MATCH (s)-[:EXPLAINS]->(c:Concept)
RETURN s, c

// ❌ Bad
MATCH (s:Source)-[:EXPLAINS]->(c:Concept)
RETURN s, c
LIMIT 100
```

---

## 8. Configuration

```yaml
# config/neo4j.yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "${NEO4J_PASSWORD}"
  database: "secondbrain"
  
  connection_pool:
    max_size: 50
    acquisition_timeout: 60
    
  vector_search:
    dimensions: 1536
    similarity: "cosine"
    
  sync:
    obsidian_enabled: true
    watch_changes: true
    batch_size: 100
```

---

## 9. Related Documents

- `02_llm_processing_layer.md` — Content processing and embedding generation
- `03_knowledge_hub_obsidian.md` — Bi-directional sync
- `06_backend_api.md` — API endpoints for graph queries

