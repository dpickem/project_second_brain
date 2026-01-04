"""
Common Neo4j Graph Queries

Pre-defined Cypher queries for common knowledge graph operations.
These can be used directly or as templates for more complex queries.
"""

# =============================================================================
# Content Queries
# =============================================================================

GET_CONTENT_BY_ID = """
MATCH (c:Content {id: $id})
RETURN c {
    .id, .title, .type, .summary, .tags,
    .source_url, .metadata, .created_at
}
"""

GET_CONTENT_BY_TYPE = """
MATCH (c:Content {type: $type})
RETURN c {.id, .title, .type, .summary, .tags}
ORDER BY c.created_at DESC
LIMIT $limit
"""

GET_RECENT_CONTENT = """
MATCH (c:Content)
RETURN c {.id, .title, .type, .summary, .tags, .created_at}
ORDER BY c.created_at DESC
LIMIT $limit
"""

SEARCH_CONTENT_BY_TITLE = """
MATCH (c:Content)
WHERE toLower(c.title) CONTAINS toLower($search_term)
RETURN c {.id, .title, .type, .summary}
LIMIT $limit
"""

# =============================================================================
# Concept Queries
# =============================================================================

GET_CONCEPT_BY_NAME = """
MATCH (c:Concept {name: $name})
RETURN c {.id, .name, .definition, .importance}
"""

GET_CONCEPTS_FOR_CONTENT = """
MATCH (content:Content {id: $content_id})-[r:CONTAINS]->(concept:Concept)
RETURN concept {.id, .name, .definition, .importance}, r.importance AS relevance
ORDER BY r.importance DESC
"""

GET_CONTENT_FOR_CONCEPT = """
MATCH (content:Content)-[r:CONTAINS]->(concept:Concept {name: $concept_name})
RETURN content {.id, .title, .type, .summary}
ORDER BY r.importance DESC
"""

# =============================================================================
# Connection Queries
# =============================================================================

GET_RELATED_CONTENT = """
MATCH (source:Content {id: $id})-[r]-(related:Content)
WHERE type(r) IN ['RELATES_TO', 'EXTENDS', 'CONTRADICTS', 'PREREQUISITE_FOR', 'APPLIES']
RETURN related {.id, .title, .type, .summary},
       type(r) AS relationship,
       r.strength AS strength,
       r.explanation AS explanation
ORDER BY r.strength DESC
"""

GET_CONTENT_GRAPH = """
MATCH (source:Content {id: $id})-[r*1..2]-(connected)
WHERE connected:Content OR connected:Concept
RETURN source, r, connected
"""

FIND_PATH_BETWEEN_CONTENT = """
MATCH path = shortestPath(
    (a:Content {id: $source_id})-[*..5]-(b:Content {id: $target_id})
)
RETURN path
"""

# =============================================================================
# Tag Queries
# =============================================================================

GET_CONTENT_BY_TAG = """
MATCH (c:Content)
WHERE $tag IN c.tags
RETURN c {.id, .title, .type, .summary, .tags}
ORDER BY c.created_at DESC
LIMIT $limit
"""

GET_TAG_STATISTICS = """
MATCH (c:Content)
UNWIND c.tags AS tag
RETURN tag, count(*) AS count
ORDER BY count DESC
"""

# =============================================================================
# Analytics Queries
# =============================================================================

GET_KNOWLEDGE_GRAPH_STATS = """
MATCH (c:Content)
WITH count(c) AS content_count
MATCH (concept:Concept)
WITH content_count, count(concept) AS concept_count
MATCH ()-[r]-()
WITH content_count, concept_count, count(r) AS relationship_count
RETURN content_count, concept_count, relationship_count
"""

GET_MOST_CONNECTED_CONTENT = """
MATCH (c:Content)-[r]-()
RETURN c.id AS id, c.title AS title, count(r) AS connections
ORDER BY connections DESC
LIMIT $limit
"""

GET_ORPHAN_CONTENT = """
MATCH (c:Content)
WHERE NOT (c)-[:RELATES_TO|EXTENDS|CONTRADICTS|PREREQUISITE_FOR|APPLIES]-()
RETURN c {.id, .title, .type, .created_at}
ORDER BY c.created_at DESC
"""

# =============================================================================
# Vector Search Queries
# =============================================================================

VECTOR_SEARCH_CONTENT = """
CALL db.index.vector.queryNodes('content_embedding_index', $top_k, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node.id AS id,
       node.title AS title,
       node.type AS type,
       node.summary AS summary,
       score
ORDER BY score DESC
"""

VECTOR_SEARCH_CONCEPTS = """
CALL db.index.vector.queryNodes('concept_embedding_index', $top_k, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node.id AS id,
       node.name AS name,
       node.definition AS definition,
       score
ORDER BY score DESC
"""

# =============================================================================
# Maintenance Queries
# =============================================================================

DELETE_CONTENT_AND_RELATIONS = """
MATCH (c:Content {id: $id})
WITH c, c.id AS deleted_id
DETACH DELETE c
RETURN deleted_id IS NOT NULL AS deleted
"""

DELETE_CONTENT_OUTGOING_RELATIONSHIPS = """
MATCH (c:Content {id: $id})-[r]->()
DELETE r
RETURN count(r) AS deleted_count
"""

CLEANUP_ORPHAN_CONCEPTS = """
MATCH (c:Concept)
WHERE NOT (c)<-[:CONTAINS]-()
DELETE c
RETURN count(*) AS deleted
"""

# =============================================================================
# Node Creation/Update Queries
# =============================================================================

MERGE_CONTENT_NODE = """
MERGE (c:Content {id: $id})
ON CREATE SET
    c.title = $title,
    c.type = $content_type,
    c.summary = $summary,
    c.embedding = $embedding,
    c.tags = $tags,
    c.source_url = $source_url,
    c.metadata = $metadata,
    c.created_at = datetime()
ON MATCH SET
    c.title = $title,
    c.type = $content_type,
    c.summary = $summary,
    c.embedding = $embedding,
    c.tags = $tags,
    c.source_url = $source_url,
    c.metadata = $metadata,
    c.updated_at = datetime()
RETURN c.id AS id
"""

MERGE_CONCEPT_NODE = """
MERGE (c:Concept {name: $name})
ON CREATE SET
    c.id = $id,
    c.definition = $definition,
    c.embedding = $embedding,
    c.importance = $importance,
    c.created_at = datetime()
ON MATCH SET
    c.definition = CASE WHEN $importance = 'core' 
                       THEN $definition ELSE c.definition END,
    c.embedding = CASE WHEN $importance = 'core'
                      THEN $embedding ELSE c.embedding END,
    c.updated_at = datetime()
RETURN c.id AS id
"""


# =============================================================================
# Query Templates (require .format() before use)
# =============================================================================
# These have placeholders for values that can't be Cypher parameters
# (e.g., relationship types, variable-length paths)
#
# Usage: query = CREATE_RELATIONSHIP.format(rel_type="RELATES_TO")

CREATE_RELATIONSHIP = """
MATCH (source {{id: $source_id}})
MATCH (target {{id: $target_id}})
MERGE (source)-[r:{rel_type}]->(target)
SET r += $properties
RETURN type(r) AS rel_type
"""

GET_CONNECTED_NODES = """
MATCH (start {{id: $node_id}})-[r{rel_filter}*1..{max_depth}]-(connected)
RETURN DISTINCT 
    connected.id AS id,
    connected.title AS title,
    connected.name AS name,
    labels(connected)[0] AS type,
    min(length(r)) AS distance
ORDER BY distance
"""

VECTOR_SEARCH = """
CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node.id AS id,
       node.title AS title,
       node.name AS name,
       node.summary AS summary,
       node.type AS type,
       score
ORDER BY score DESC
"""


# =============================================================================
# Index and Constraint Setup Queries
# =============================================================================

CREATE_CONTENT_EMBEDDING_INDEX = """
CREATE VECTOR INDEX content_embedding_index IF NOT EXISTS
FOR (c:Content)
ON (c.embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}
"""

CREATE_CONCEPT_EMBEDDING_INDEX = """
CREATE VECTOR INDEX concept_embedding_index IF NOT EXISTS
FOR (c:Concept)
ON (c.embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}
"""

CREATE_CONTENT_ID_CONSTRAINT = """
CREATE CONSTRAINT content_id_unique IF NOT EXISTS
FOR (c:Content) REQUIRE c.id IS UNIQUE
"""

CREATE_CONCEPT_NAME_CONSTRAINT = """
CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE
"""

CREATE_CONTENT_TYPE_INDEX = """
CREATE INDEX content_type_index IF NOT EXISTS
FOR (c:Content) ON (c.type)
"""

CREATE_CONTENT_CREATED_INDEX = """
CREATE INDEX content_created_index IF NOT EXISTS
FOR (c:Content) ON (c.created_at)
"""

# All setup queries in order
SETUP_INDEX_QUERIES = [
    CREATE_CONTENT_EMBEDDING_INDEX,
    CREATE_CONCEPT_EMBEDDING_INDEX,
    CREATE_CONTENT_ID_CONSTRAINT,
    CREATE_CONCEPT_NAME_CONSTRAINT,
    CREATE_CONTENT_TYPE_INDEX,
    CREATE_CONTENT_CREATED_INDEX,
]
