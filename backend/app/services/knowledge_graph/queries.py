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
# Search Service Queries
# =============================================================================

FULLTEXT_SEARCH_QUERY = """
CALL db.index.fulltext.queryNodes('searchIndex', $query)
YIELD node, score
WHERE score >= $min_score
AND any(label IN labels(node) WHERE label IN $node_types)
RETURN 
    node.id AS id,
    labels(node)[0] AS node_type,
    COALESCE(node.title, node.name, node.id) AS title,
    node.summary AS summary,
    score
ORDER BY score DESC
LIMIT $limit
"""

KEYWORD_SEARCH_QUERY = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $node_types)
AND (
    toLower(n.title) CONTAINS toLower($query)
    OR toLower(n.name) CONTAINS toLower($query)
    OR toLower(n.summary) CONTAINS toLower($query)
)
WITH n, 
    CASE 
        WHEN toLower(n.title) CONTAINS toLower($query) THEN 1.0
        WHEN toLower(n.name) CONTAINS toLower($query) THEN 0.9
        ELSE 0.7
    END AS score
RETURN 
    n.id AS id,
    labels(n)[0] AS node_type,
    COALESCE(n.title, n.name, n.id) AS title,
    n.summary AS summary,
    score
ORDER BY score DESC
LIMIT $limit
"""

SEARCH_VECTOR_QUERY = """
CALL db.index.vector.queryNodes($index_name, $limit, $embedding)
YIELD node, score
WHERE score >= $min_score
AND any(label IN labels(node) WHERE label IN $node_types)
RETURN 
    node.id AS id,
    labels(node)[0] AS node_type,
    COALESCE(node.title, node.name, node.id) AS title,
    node.summary AS summary,
    score
ORDER BY score DESC
"""

CHECK_FULLTEXT_INDEX = """
SHOW INDEXES YIELD name WHERE name = 'searchIndex' RETURN count(*) > 0 AS exists
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
    c.file_path = $file_path,
    c.metadata = $metadata,
    c.created_at = datetime()
ON MATCH SET
    c.title = $title,
    c.type = $content_type,
    c.summary = $summary,
    c.embedding = $embedding,
    c.tags = $tags,
    c.source_url = $source_url,
    c.file_path = $file_path,
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
    c.file_path = $file_path,
    c.created_at = datetime()
ON MATCH SET
    c.definition = CASE WHEN $importance = 'core' 
                       THEN $definition ELSE c.definition END,
    c.embedding = CASE WHEN $importance = 'core'
                      THEN $embedding ELSE c.embedding END,
    c.file_path = CASE WHEN $file_path IS NOT NULL 
                       THEN $file_path ELSE c.file_path END,
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

# Link concepts by name (concepts are merged by name, not ID)
LINK_CONCEPTS_BY_NAME = """
MATCH (source:Concept {{name: $source_name}})
MATCH (target:Concept {{name: $target_name}})
WHERE source <> target
MERGE (source)-[r:{rel_type}]->(target)
SET r += $properties
RETURN type(r) AS rel_type, source.name AS source, target.name AS target
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


# =============================================================================
# Obsidian Vault Sync Queries (Note nodes for vault representation)
# =============================================================================
# Note nodes are distinct from Content nodes - they represent Obsidian vault
# files for graph visualization and link tracking, not processed content.

MERGE_NOTE_NODE = """
MERGE (n:Note {id: $node_id})
SET n.title = $title,
    n.type = $note_type,
    n.tags = $tags,
    n.file_path = $file_path,
    n.source_url = $source_url,
    n.updated_at = datetime()
RETURN n.id AS id
"""

DELETE_NOTE_OUTGOING_LINKS = """
MATCH (source:Note {id: $source_id})-[r:LINKS_TO]->()
DELETE r
RETURN count(r) AS deleted_count
"""

CREATE_NOTE_LINK = """
MATCH (source:Note {id: $source_id})
MERGE (target:Note {id: $target_id})
ON CREATE SET target.title = $target_id
MERGE (source)-[r:LINKS_TO]->(target)
SET r.synced_at = datetime()
RETURN type(r) AS rel_type
"""


# =============================================================================
# Content-Note Linking Queries (bridge processed content with vault notes)
# =============================================================================
# Content nodes (from LLM processing) and Note nodes (from vault sync) can
# represent the same file. These queries create REPRESENTS relationships
# to connect them, unifying the graph visualization.

LINK_CONTENT_TO_NOTE_BY_FILE_PATH = """
MATCH (c:Content {file_path: $file_path})
MATCH (n:Note {file_path: $file_path})
MERGE (c)-[r:REPRESENTS]->(n)
SET r.linked_at = datetime()
RETURN c.id AS content_id, n.id AS note_id
"""

FIND_NOTE_BY_FILE_PATH = """
MATCH (n:Note {file_path: $file_path})
RETURN n.id AS id, n.title AS title
"""

FIND_CONTENT_BY_FILE_PATH = """
MATCH (c:Content {file_path: $file_path})
RETURN c.id AS id, c.title AS title
"""

LINK_ALL_CONTENT_TO_NOTES = """
MATCH (c:Content)
WHERE c.file_path IS NOT NULL
MATCH (n:Note {file_path: c.file_path})
WHERE NOT (c)-[:REPRESENTS]->(n)
MERGE (c)-[r:REPRESENTS]->(n)
SET r.linked_at = datetime()
RETURN count(r) AS linked_count
"""


# =============================================================================
# Graph Visualization Queries
# =============================================================================
# Queries for the Graph Viewer UI - returning nodes and edges for D3/force-graph

GET_VISUALIZATION_GRAPH = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $node_types)
WITH n
LIMIT $limit
WITH collect(n) AS nodes_list
UNWIND nodes_list AS n
OPTIONAL MATCH (n)-[r]-(m)
WHERE m IN nodes_list
WITH n, r, m
RETURN 
    collect(DISTINCT {
        id: COALESCE(n.id, toString(id(n))),
        label: COALESCE(n.title, n.name, n.id, 'Unnamed'),
        type: [label IN labels(n) WHERE label IN $node_types][0],
        content_type: n.type,
        tags: COALESCE(n.tags, [])
    }) AS nodes,
    collect(DISTINCT CASE WHEN r IS NOT NULL THEN {
        source: COALESCE(startNode(r).id, toString(id(startNode(r)))),
        target: COALESCE(endNode(r).id, toString(id(endNode(r)))),
        type: type(r),
        strength: COALESCE(r.strength, 1.0)
    } END) AS edges
"""


def get_centered_visualization_query(depth: int) -> str:
    """Generate centered graph query with literal depth value.

    Neo4j doesn't allow parameters in relationship path lengths,
    so we interpolate the depth value directly into the query.

    Args:
        depth: Number of hops from center node to traverse (1-4)

    Returns:
        Cypher query string with depth interpolated
    """
    return f"""
MATCH (center {{id: $center_id}})
CALL {{
    WITH center
    MATCH (center)-[r*1..{depth}]-(connected)
    WHERE any(label IN labels(connected) WHERE label IN $node_types)
    RETURN connected AS n, 2 AS priority
    UNION
    WITH center
    RETURN center AS n, 1 AS priority
}}
WITH DISTINCT n, min(priority) AS p
ORDER BY p
LIMIT $limit
WITH collect(n) AS nodes_list
UNWIND nodes_list AS n
OPTIONAL MATCH (n)-[r]-(m)
WHERE m IN nodes_list
WITH n, r, m
RETURN 
    collect(DISTINCT {{
        id: COALESCE(n.id, toString(id(n))),
        label: COALESCE(n.title, n.name, n.id, 'Unnamed'),
        type: [label IN labels(n) WHERE label IN $node_types][0],
        content_type: n.type,
        tags: COALESCE(n.tags, [])
    }}) AS nodes,
    collect(DISTINCT CASE WHEN r IS NOT NULL THEN {{
        source: COALESCE(startNode(r).id, toString(id(startNode(r)))),
        target: COALESCE(endNode(r).id, toString(id(endNode(r)))),
        type: type(r),
        strength: COALESCE(r.strength, 1.0)
    }} END) AS edges
"""


GET_VISUALIZATION_STATS = """
OPTIONAL MATCH (content:Content)
WITH count(content) AS content_count
OPTIONAL MATCH (concept:Concept)
WITH content_count, count(concept) AS concept_count
OPTIONAL MATCH (note:Note)
WITH content_count, concept_count, count(note) AS note_count
OPTIONAL MATCH ()-[r]->()
WITH content_count, concept_count, note_count, count(r) AS rel_count
OPTIONAL MATCH (c:Content)
WITH content_count, concept_count, note_count, rel_count,
     collect(COALESCE(c.type, 'unknown')) AS types
RETURN 
    content_count,
    concept_count,
    note_count,
    rel_count,
    types
"""


GET_NODE_DETAILS_BY_ID = """
MATCH (n {id: $node_id})
OPTIONAL MATCH (n)-[r]-()
WITH n, count(r) AS connections
RETURN {
    id: n.id,
    label: COALESCE(n.title, n.name, n.id),
    type: labels(n)[0],
    content_type: n.type,
    summary: n.summary,
    tags: COALESCE(n.tags, []),
    source_url: n.source_url,
    created_at: toString(n.created_at),
    connections: connections,
    file_path: n.file_path,
    name: n.name
} AS node
"""


GET_NODE_COUNT_BY_TYPES = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $node_types)
RETURN count(n) AS total
"""


# =============================================================================
# Connection Queries (for /connections/{node_id} endpoint)
# =============================================================================

GET_INCOMING_CONNECTIONS = """
MATCH (source)-[r]->(target {id: $node_id})
RETURN 
    source.id AS source_id,
    COALESCE(source.title, source.name, source.id) AS source_title,
    labels(source)[0] AS source_type,
    type(r) AS rel_type,
    COALESCE(r.strength, 1.0) AS strength,
    r.context AS context
ORDER BY r.strength DESC NULLS LAST
LIMIT $limit
"""

GET_OUTGOING_CONNECTIONS = """
MATCH (source {id: $node_id})-[r]->(target)
RETURN 
    target.id AS target_id,
    COALESCE(target.title, target.name, target.id) AS target_title,
    labels(target)[0] AS target_type,
    type(r) AS rel_type,
    COALESCE(r.strength, 1.0) AS strength,
    r.context AS context
ORDER BY r.strength DESC NULLS LAST
LIMIT $limit
"""


# =============================================================================
# Topic Hierarchy Queries
# =============================================================================

GET_TOPICS_WITH_COUNTS = """
MATCH (c:Content)
WHERE c.tags IS NOT NULL
UNWIND c.tags AS tag
WITH tag, count(DISTINCT c) AS content_count
WHERE content_count >= $min_content
RETURN tag AS path, content_count
ORDER BY tag
"""


# =============================================================================
# Utility Queries (connectivity, index checks)
# =============================================================================

VERIFY_CONNECTIVITY = """
RETURN 1 AS test
"""

LIST_INDEX_NAMES = """
SHOW INDEXES YIELD name
"""

# Debug query - returns entire graph structure
GET_ALL_GRAPH_DATA = """
MATCH (n)-[r]->(m) RETURN n,r,m
"""
