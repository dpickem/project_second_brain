"""
Knowledge Graph API Models (Pydantic)

Request/response schemas for the Knowledge Graph API including:
- Graph visualization (nodes, edges, responses)
- Graph statistics
- Semantic search
- Node connections and relationships
- Topic hierarchy

ARCHITECTURE NOTE:
    This file contains PYDANTIC models for API validation.
    The actual graph storage is in Neo4j, managed by app/services/knowledge_graph/.

    Data flows: API Request → Pydantic → Service → Neo4j

API Contract:
    Request models use StrictRequest (extra="forbid") to reject unknown fields.
    This catches frontend/backend mismatches early with clear 422 errors.

Usage:
    from app.models.knowledge import (
        GraphNode,
        GraphResponse,
        SearchRequest,
        SearchResponse,
    )
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import StrictRequest, StrictResponse


# =============================================================================
# Graph Visualization Models
# =============================================================================


class GraphNode(BaseModel):
    """
    Node in the knowledge graph visualization.

    Represents a single entity (Content, Concept, or Note) in the graph
    with properties needed for D3.js force-directed rendering.

    Attributes:
        id: Unique node identifier (UUID or Neo4j ID)
        label: Display title for the node
        type: Node type - "Content", "Concept", or "Note"
        content_type: For Content nodes, the specific type (paper, article, etc.)
        size: Visual weight based on connection count (for node sizing)
        color: Optional hex color code for custom styling
        metadata: Additional properties (tags, etc.)
    """

    id: str
    label: str
    type: str  # "Content", "Concept", "Note"
    content_type: Optional[str] = None  # "paper", "article", etc.
    size: int = Field(default=1, description="Node size weight based on connections")
    color: Optional[str] = Field(default=None, description="Optional hex color code")
    metadata: dict = Field(default_factory=dict, description="Additional properties")


class GraphEdge(BaseModel):
    """
    Lightweight edge for graph visualization.

    Designed for bulk transfer in graph visualization responses where
    hundreds of edges may be returned. Contains only IDs and visual
    properties - no display metadata to minimize payload size.

    For detailed connection information with titles and context,
    see NodeConnection which is used by the /connections endpoint.

    Attributes:
        source: Source node ID
        target: Target node ID
        type: Relationship type (REFERENCES, RELATES_TO, etc.)
        strength: Edge weight from 0.0 to 1.0 for visual thickness
        label: Optional display label for the edge

    See Also:
        NodeConnection: Rich connection model with display metadata
        GraphResponse: Uses GraphEdge for visualization data
    """

    source: str
    target: str
    type: str
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    label: Optional[str] = None


class GraphResponse(BaseModel):
    """
    Response containing graph data for visualization.

    Returns a subgraph suitable for rendering with D3.js or similar
    visualization libraries. Includes metadata about the full graph size.

    Attributes:
        nodes: List of nodes in the subgraph
        edges: List of edges connecting the nodes
        center_id: ID of the center node (if centered query)
        total_nodes: Total nodes in the full graph (before limiting)
        total_edges: Total edges in the returned subgraph
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_id: Optional[str] = None
    total_nodes: int
    total_edges: int


class GraphStats(BaseModel):
    """
    Summary statistics for the knowledge graph.

    Provides aggregate metrics about the graph contents
    for dashboard displays and health monitoring.

    Attributes:
        total_content: Count of Content nodes
        total_concepts: Count of Concept nodes
        total_notes: Count of Note nodes
        total_relationships: Count of all relationships
        content_by_type: Breakdown of content by type (paper, article, etc.)
    """

    total_content: int
    total_concepts: int
    total_notes: int
    total_relationships: int
    content_by_type: dict[str, int] = Field(default_factory=dict)


class NodeDetails(BaseModel):
    """
    Detailed information about a single node.

    Returns comprehensive metadata for a node detail view,
    including content summary, tags, and connection count.

    Attributes:
        id: Node identifier
        label: Display title
        type: Node type (Content, Concept, Note)
        content_type: Specific content type if applicable
        summary: Brief summary text
        tags: List of associated tags
        source_url: Original source URL if applicable
        created_at: Creation timestamp (ISO 8601)
        connections: Count of connected nodes
        file_path: Obsidian vault file path if applicable
        name: Alternative name field (for Concepts)
    """

    id: str
    label: str
    type: str
    content_type: Optional[str] = None
    summary: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    created_at: Optional[str] = None
    connections: int = 0
    file_path: Optional[str] = None
    name: Optional[str] = None


# =============================================================================
# Search Models
# =============================================================================


class SearchResult(BaseModel):
    """
    Single search result with relevance score.

    Represents a matched node from semantic or keyword search
    with scoring and optional highlight snippets.

    Attributes:
        id: Node identifier
        node_type: Type of matched node (Content, Concept, Note)
        title: Display title
        summary: Brief summary or excerpt
        score: Relevance score from 0.0 to 1.0
        highlights: Matching text snippets (for keyword search)
    """

    id: str
    node_type: str  # Content, Concept, Note
    title: str
    summary: Optional[str] = None
    score: float = Field(ge=0, le=1)
    highlights: list[str] = Field(default_factory=list)


class SearchRequest(StrictRequest):
    """
    Search query parameters.

    Configures semantic search across the knowledge graph
    with filtering and scoring options.

    Attributes:
        query: Search query text (1-500 characters)
        node_types: Types to search (default: Content, Concept)
        limit: Maximum results to return (1-100, default: 20)
        min_score: Minimum relevance score threshold (0-1, default: 0.5)
        use_vector: Whether to use vector/embedding search when available

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    query: str = Field(..., min_length=1, max_length=500)
    node_types: list[str] = Field(default=["Content", "Concept"])
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0, le=1)
    use_vector: bool = Field(
        default=True, description="Use vector search when available"
    )


class SearchResponse(BaseModel):
    """
    Search results response.

    Contains ranked search results with query echo
    and performance metrics.

    Attributes:
        query: Original search query
        results: List of matching results, ranked by score
        total: Total number of results returned
        search_time_ms: Search execution time in milliseconds
    """

    query: str
    results: list[SearchResult]
    total: int
    search_time_ms: float


# =============================================================================
# Connection Models
# =============================================================================


class NodeConnection(BaseModel):
    """
    Rich connection model with display metadata.

    Used by the /connections/{node_id} endpoint to return detailed
    information about a node's relationships. Includes display-ready
    metadata (titles, types, context) so the UI can render connection
    lists without additional lookups.

    For bulk graph visualization where payload size matters,
    see GraphEdge which contains only IDs and visual properties.

    Note: Named NodeConnection to distinguish from app.models.processing.Connection
    which represents LLM-discovered connections during content processing.

    Attributes:
        source_id: Source node ID
        target_id: Target node ID
        target_title: Title of the connected node (for display)
        target_type: Type of the connected node (Content, Concept, Note)
        relationship: Relationship type (REFERENCES, RELATES_TO, etc.)
        strength: Connection strength from 0.0 to 1.0
        context: Optional explanation of why they're connected

    See Also:
        GraphEdge: Lightweight edge for visualization (IDs only)
        ConnectionsResponse: Uses NodeConnection for detailed queries
    """

    source_id: str
    target_id: str
    target_title: str
    target_type: str
    relationship: str
    strength: float = Field(default=1.0, ge=0, le=1)
    context: Optional[str] = None


class ConnectionsResponse(BaseModel):
    """
    Response containing connections for a node.

    Returns both incoming and outgoing relationships,
    enabling bidirectional graph exploration.

    Attributes:
        node_id: The queried node's ID
        incoming: Connections pointing to this node
        outgoing: Connections pointing from this node
        total: Total connection count
    """

    node_id: str
    incoming: list[NodeConnection]
    outgoing: list[NodeConnection]
    total: int


# =============================================================================
# Topic Hierarchy Models
# =============================================================================


class TopicNode(BaseModel):
    """
    A node in the topic hierarchy tree.

    Topics are organized hierarchically using slash-separated paths
    (e.g., "ml/deep-learning/transformers"). This model supports
    recursive tree structures for navigation UIs.

    Attributes:
        path: Full topic path (e.g., "ml/deep-learning/transformers")
        name: Leaf name (e.g., "transformers")
        depth: Depth in tree (0 = root)
        content_count: Number of content items with this topic
        children: Child topic nodes
        mastery_score: Optional mastery score if user has learning data
    """

    path: str
    name: str
    depth: int
    content_count: int
    children: list["TopicNode"] = Field(default_factory=list)
    mastery_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="User mastery score for this topic"
    )


class TopicHierarchyResponse(BaseModel):
    """
    Full topic hierarchy response.

    Returns the complete topic tree for navigation
    with aggregate statistics.

    Attributes:
        roots: Root-level topic nodes
        total_topics: Total number of topics in the tree
        max_depth: Maximum depth of the tree
    """

    roots: list[TopicNode]
    total_topics: int
    max_depth: int
