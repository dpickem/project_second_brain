"""
Knowledge Graph Visualization Service

Provides graph visualization data for the frontend knowledge graph viewer.
Handles data retrieval and transformation for D3.js force-directed rendering.

Main capabilities:
- Graph data retrieval (nodes and edges for D3 rendering)
- Graph statistics aggregation
- Node detail lookups
- Connection exploration (incoming/outgoing)
- Topic hierarchy building
- Health checks

Architecture:
    This service acts as a thin query layer over Neo4j, transforming
    raw Cypher query results into frontend-ready data structures.
    It does NOT handle search functionality (see KnowledgeSearchService).

Usage:
    service = KnowledgeVisualizationService(neo4j_client)
    graph = await service.get_graph(node_types=["Content", "Concept"], limit=100)
    stats = await service.get_stats()

    # Or use the singleton getter:
    from app.services.knowledge_graph import get_visualization_service
    service = await get_visualization_service()
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional

from app.config.settings import settings
from app.enums.knowledge import ConnectionDirection
from app.services.knowledge_graph.queries import (
    GET_INCOMING_CONNECTIONS,
    GET_NODE_COUNT_BY_TYPES,
    GET_NODE_DETAILS_BY_ID,
    GET_OUTGOING_CONNECTIONS,
    GET_TOPICS_WITH_COUNTS,
    GET_VISUALIZATION_GRAPH,
    GET_VISUALIZATION_STATS,
    get_centered_visualization_query,
)
from app.services.knowledge_graph.utils import build_topic_tree

if TYPE_CHECKING:
    from neo4j import AsyncSession

    from app.services.knowledge_graph.client import Neo4jClient

logger = logging.getLogger(__name__)


# =============================================================================
# Type Aliases for Result Structures
# =============================================================================

# Graph data types
GraphNodeDict = dict[str, Any]
GraphEdgeDict = dict[str, Any]
GraphResponseDict = dict[str, Any]
StatsResponseDict = dict[str, Any]
NodeDetailsDict = dict[str, Any]
ConnectionsResponseDict = dict[str, Any]
TopicHierarchyDict = dict[str, Any]
HealthCheckDict = dict[str, Any]


class KnowledgeVisualizationService:
    """
    Service for knowledge graph visualization and exploration.

    Provides methods for retrieving graph data in formats suitable
    for D3.js force-directed graph rendering. All methods are async
    and designed for use in FastAPI request handlers.

    Attributes:
        neo4j: The Neo4j client used for executing graph queries.
        DEFAULT_NODE_TYPES: Default node types to include in visualization.

    Example:
        >>> service = KnowledgeVisualizationService(neo4j_client)
        >>> graph = await service.get_graph(limit=100)
        >>> print(f"Got {len(graph['nodes'])} nodes")
    """

    DEFAULT_NODE_TYPES: list[str] = ["Content", "Concept", "Note"]

    def __init__(self, neo4j_client: Neo4jClient) -> None:
        """
        Initialize the visualization service.

        Args:
            neo4j_client: Initialized Neo4j client for executing graph queries.
        """
        self.neo4j = neo4j_client

    # =========================================================================
    # Internal Query Helpers
    # =========================================================================

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        """
        Async context manager for Neo4j session access.

        Ensures the client is initialized before yielding a session.
        Sessions are automatically closed when the context exits.

        Yields:
            Neo4j AsyncSession configured for the target database.

        Example:
            async with self._session() as session:
                result = await session.run(query, **params)
        """
        await self.neo4j._ensure_initialized()
        async with self.neo4j._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            yield session

    async def _run_query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return all results as dicts.

        Use this for queries that return multiple records (e.g., connections,
        topic lists).

        Args:
            cypher: The Cypher query string to execute.
            **params: Named parameters to pass to the query.

        Returns:
            List of dictionaries, one per result record.

        Example:
            >>> results = await self._run_query(
            ...     "MATCH (n:Content) RETURN n.title AS title LIMIT $limit",
            ...     limit=10
            ... )
        """
        async with self._session() as session:
            result = await session.run(cypher, **params)
            return [dict(record) async for record in result]

    async def _run_single_query(
        self, cypher: str, **params: Any
    ) -> Optional[dict[str, Any]]:
        """
        Execute a Cypher query and return a single result.

        Use this for queries that return exactly one row (e.g., stats,
        node details, aggregations).

        Args:
            cypher: The Cypher query string to execute.
            **params: Named parameters to pass to the query.

        Returns:
            Single result dictionary, or None if no results.

        Example:
            >>> result = await self._run_single_query(
            ...     "MATCH (n {id: $id}) RETURN n",
            ...     id="node-123"
            ... )
        """
        async with self._session() as session:
            result = await session.run(cypher, **params)
            record = await result.single()
            return dict(record) if record else None

    # =========================================================================
    # Graph Visualization
    # =========================================================================

    async def get_graph(
        self,
        center_id: Optional[str] = None,
        node_types: Optional[list[str]] = None,
        depth: int = 2,
        limit: int = 100,
    ) -> GraphResponseDict:
        """
        Get graph data for visualization.

        Returns nodes and edges in D3-compatible format for force-directed graphs.
        Can optionally center on a specific node and expand outward to a given depth.

        Args:
            center_id: Optional node ID to center the graph on. If provided,
                returns the ego-network around this node.
            node_types: List of node types to include (default: Content, Concept, Note).
            depth: How many hops from center to traverse (only used with center_id).
                Range: 1-4 recommended for performance.
            limit: Maximum number of nodes to return (default: 100).

        Returns:
            Dict containing:
                - nodes: List of node dicts with id, label, type, content_type, metadata
                - edges: List of edge dicts with source, target, type, strength
                - center_id: The center node ID (None if not centered)
                - total_nodes: Total matching nodes in the graph (before limiting)
                - total_edges: Number of edges in the returned subgraph

        Example:
            >>> graph = await service.get_graph(limit=50)
            >>> print(f"Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}")

            >>> # Centered on a specific node
            >>> graph = await service.get_graph(center_id="paper-123", depth=2)
        """
        node_type_list = node_types or self.DEFAULT_NODE_TYPES

        # Get total count for stats (separate from limit)
        count_record = await self._run_single_query(
            GET_NODE_COUNT_BY_TYPES, node_types=node_type_list
        )
        total_nodes = count_record["total"] if count_record else 0

        # Execute appropriate query based on whether we have a center node
        if center_id:
            query = get_centered_visualization_query(depth)
            record = await self._run_single_query(
                query,
                center_id=center_id,
                node_types=node_type_list,
                limit=limit,
            )
        else:
            record = await self._run_single_query(
                GET_VISUALIZATION_GRAPH,
                node_types=node_type_list,
                limit=limit,
            )

        # Handle empty result
        if not record:
            return self._empty_graph_response(center_id, total_nodes)

        # Transform raw query results into frontend-ready format
        nodes = self._transform_nodes(record.get("nodes") or [])
        node_ids = {n["id"] for n in nodes}
        edges = self._transform_edges(record.get("edges") or [], node_ids)

        return {
            "nodes": nodes,
            "edges": edges,
            "center_id": center_id,
            "total_nodes": total_nodes,
            "total_edges": len(edges),
        }

    def _empty_graph_response(
        self, center_id: Optional[str], total_nodes: int
    ) -> GraphResponseDict:
        """Return an empty graph response structure."""
        return {
            "nodes": [],
            "edges": [],
            "center_id": center_id,
            "total_nodes": total_nodes,
            "total_edges": 0,
        }

    def _transform_nodes(self, raw_nodes: list[Any]) -> list[GraphNodeDict]:
        """
        Transform raw Neo4j node records into frontend-ready format.

        Filters out None values and nodes without IDs.

        Args:
            raw_nodes: Raw node records from Cypher query.

        Returns:
            List of node dicts ready for D3 visualization.
        """
        nodes: list[GraphNodeDict] = []
        for n in raw_nodes:
            if not n or not n.get("id"):
                continue
            nodes.append(
                {
                    "id": n["id"],
                    "label": n.get("label", n["id"]),
                    "type": n.get("type", "Unknown"),
                    "content_type": n.get("content_type"),
                    "metadata": {"tags": n.get("tags", [])},
                }
            )
        return nodes

    def _transform_edges(
        self, raw_edges: list[Any], valid_node_ids: set[str]
    ) -> list[GraphEdgeDict]:
        """
        Transform and filter raw Neo4j edge records.

        Only includes edges where both source and target nodes exist
        in the returned node set (handles subgraph boundary).

        Args:
            raw_edges: Raw edge records from Cypher query.
            valid_node_ids: Set of node IDs present in the subgraph.

        Returns:
            List of edge dicts ready for D3 visualization.
        """
        edges: list[GraphEdgeDict] = []
        for e in raw_edges:
            # Skip invalid edges or edges crossing subgraph boundary
            if not e or not e.get("source") or not e.get("target"):
                continue
            if e["source"] not in valid_node_ids or e["target"] not in valid_node_ids:
                continue

            edges.append(
                {
                    "source": e["source"],
                    "target": e["target"],
                    "type": e.get("type", "RELATED"),
                    "strength": e.get("strength", 1.0),
                }
            )
        return edges

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> StatsResponseDict:
        """
        Get summary statistics for the knowledge graph.

        Aggregates counts of content, concepts, notes, and relationships.
        Also provides a breakdown of content by type (paper, article, etc.).

        Returns:
            Dict containing:
                - total_content: Count of Content nodes
                - total_concepts: Count of Concept nodes
                - total_notes: Count of Note nodes
                - total_relationships: Count of all relationships
                - content_by_type: Dict mapping content type to count

        Example:
            >>> stats = await service.get_stats()
            >>> print(f"Total content: {stats['total_content']}")
            >>> print(f"Papers: {stats['content_by_type'].get('paper', 0)}")
        """
        record = await self._run_single_query(GET_VISUALIZATION_STATS)

        if not record:
            return self._empty_stats_response()

        # Count content by type (filter out None values)
        type_counts = self._count_types(record.get("types") or [])

        return {
            "total_content": record.get("content_count") or 0,
            "total_concepts": record.get("concept_count") or 0,
            "total_notes": record.get("note_count") or 0,
            "total_relationships": record.get("rel_count") or 0,
            "content_by_type": type_counts,
        }

    def _empty_stats_response(self) -> StatsResponseDict:
        """Return an empty stats response structure."""
        return {
            "total_content": 0,
            "total_concepts": 0,
            "total_notes": 0,
            "total_relationships": 0,
            "content_by_type": {},
        }

    def _count_types(self, types: list[Any]) -> dict[str, int]:
        """
        Count occurrences of each content type.

        Filters out None values from the types list.

        Args:
            types: List of type strings (may contain None values).

        Returns:
            Dict mapping type name to count.
        """
        type_counts: dict[str, int] = {}
        for t in types:
            if t:  # Skip None values
                type_counts[t] = type_counts.get(t, 0) + 1
        return type_counts

    # =========================================================================
    # Node Details
    # =========================================================================

    async def get_node_details(self, node_id: str) -> Optional[NodeDetailsDict]:
        """
        Get detailed information about a specific node.

        Returns comprehensive metadata for node detail views including
        summary, tags, connection count, and source information.

        Args:
            node_id: The node's unique identifier.

        Returns:
            Dict with node details, or None if not found. Contains:
                - id: Node identifier
                - label: Display title
                - type: Node type (Content, Concept, Note)
                - content_type: Specific content type if applicable
                - summary: Brief summary text
                - tags: List of associated tags
                - source_url: Original source URL if applicable
                - created_at: Creation timestamp
                - connections: Count of connected nodes
                - file_path: Obsidian vault file path if applicable
                - name: Alternative name field (for Concepts)

        Example:
            >>> details = await service.get_node_details("paper-123")
            >>> if details:
            ...     print(f"Title: {details['label']}")
            ...     print(f"Connections: {details['connections']}")
        """
        record = await self._run_single_query(GET_NODE_DETAILS_BY_ID, node_id=node_id)

        if not record or not record.get("node"):
            return None

        node = record["node"]
        return {
            "id": node["id"],
            "label": node.get("label", node["id"]),
            "type": node.get("type", "Unknown"),
            "content_type": node.get("content_type"),
            "summary": node.get("summary"),
            "tags": node.get("tags", []),
            "source_url": node.get("source_url"),
            "created_at": node.get("created_at"),
            "connections": node.get("connections", 0),
            "file_path": node.get("file_path"),
            "name": node.get("name"),
        }

    # =========================================================================
    # Health Check
    # =========================================================================

    async def check_health(self) -> HealthCheckDict:
        """
        Check Neo4j connection health.

        Verifies that the Neo4j database is reachable and responding.
        Used by health check endpoints for monitoring.

        Returns:
            Dict containing:
                - status: "healthy" or "unhealthy"
                - neo4j_connected: Boolean indicating connection status
                - error: Error message (only present if unhealthy)

        Example:
            >>> health = await service.check_health()
            >>> if health["status"] == "healthy":
            ...     print("Database is operational")
        """
        try:
            is_connected = await self.neo4j.verify_connectivity()
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "neo4j_connected": is_connected,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "neo4j_connected": False,
                "error": str(e),
            }

    # =========================================================================
    # Connections
    # =========================================================================

    async def get_connections(
        self,
        node_id: str,
        direction: ConnectionDirection = ConnectionDirection.BOTH,
        limit: int = 20,
    ) -> ConnectionsResponseDict:
        """
        Get connections for a specific node.

        Returns detailed information about connected nodes, suitable
        for displaying in a connections list view.

        Args:
            node_id: The node to get connections for.
            direction: Which connections to return:
                - INCOMING: Only relationships pointing to this node
                - OUTGOING: Only relationships pointing from this node
                - BOTH: All relationships (default)
            limit: Maximum connections per direction (default: 20).

        Returns:
            Dict containing:
                - node_id: The queried node's ID
                - incoming: List of incoming connection dicts
                - outgoing: List of outgoing connection dicts
                - total: Total connection count

            Each connection dict contains:
                - source_id / target_id: Connected node ID
                - target_title: Display title of connected node
                - target_type: Type of connected node
                - relationship: Relationship type (REFERENCES, RELATES_TO, etc.)
                - strength: Connection strength (0.0-1.0)
                - context: Optional explanation of the connection

        Example:
            >>> connections = await service.get_connections(
            ...     "paper-123",
            ...     direction=ConnectionDirection.OUTGOING
            ... )
            >>> for conn in connections["outgoing"]:
            ...     print(f"{conn['relationship']} -> {conn['target_title']}")
        """
        incoming: list[dict[str, Any]] = []
        outgoing: list[dict[str, Any]] = []

        # Fetch incoming connections if requested
        if direction in (ConnectionDirection.INCOMING, ConnectionDirection.BOTH):
            records = await self._run_query(
                GET_INCOMING_CONNECTIONS,
                node_id=node_id,
                limit=limit,
            )
            incoming = self._transform_incoming_connections(node_id, records)

        # Fetch outgoing connections if requested
        if direction in (ConnectionDirection.OUTGOING, ConnectionDirection.BOTH):
            records = await self._run_query(
                GET_OUTGOING_CONNECTIONS,
                node_id=node_id,
                limit=limit,
            )
            outgoing = self._transform_outgoing_connections(node_id, records)

        return {
            "node_id": node_id,
            "incoming": incoming,
            "outgoing": outgoing,
            "total": len(incoming) + len(outgoing),
        }

    def _transform_incoming_connections(
        self, node_id: str, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform raw incoming connection records."""
        return [
            {
                "source_id": r["source_id"],
                "target_id": node_id,
                "target_title": r["source_title"],
                "target_type": r["source_type"],
                "relationship": r["rel_type"],
                "strength": r.get("strength", 1.0),
                "context": r.get("context"),
            }
            for r in records
            if r.get("source_id")  # Filter out records with null source_id
        ]

    def _transform_outgoing_connections(
        self, node_id: str, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform raw outgoing connection records."""
        return [
            {
                "source_id": node_id,
                "target_id": r["target_id"],
                "target_title": r["target_title"],
                "target_type": r["target_type"],
                "relationship": r["rel_type"],
                "strength": r.get("strength", 1.0),
                "context": r.get("context"),
            }
            for r in records
            if r.get("target_id")  # Filter out records with null target_id
        ]

    # =========================================================================
    # Topic Hierarchy
    # =========================================================================

    async def get_topic_hierarchy(self, min_content: int = 0) -> TopicHierarchyDict:
        """
        Get hierarchical topic structure.

        Topics are organized in a tree based on their tag paths
        (e.g., "ml/deep-learning/transformers" becomes a nested structure).

        Args:
            min_content: Filter out topics with fewer items (default: 0).
                Useful for hiding sparse topic branches.

        Returns:
            Dict containing:
                - roots: List of root-level TopicNode objects
                - total_topics: Total number of topics
                - max_depth: Maximum depth of the tree

        Example:
            >>> hierarchy = await service.get_topic_hierarchy(min_content=5)
            >>> for root in hierarchy["roots"]:
            ...     print(f"{root.name}: {root.content_count} items")
        """
        records = await self._run_query(
            GET_TOPICS_WITH_COUNTS,
            min_content=min_content,
        )

        # Extract path and content_count from each record
        topics = [
            {"path": record["path"], "content_count": record["content_count"]}
            for record in records
        ]

        if not topics:
            return {
                "roots": [],
                "total_topics": 0,
                "max_depth": 0,
            }

        # Build hierarchical tree from flat list
        roots, max_depth = build_topic_tree(topics)

        return {
            "roots": roots,
            "total_topics": len(topics),
            "max_depth": max_depth,
        }


# =============================================================================
# Singleton Instance Management
# =============================================================================

_visualization_service: Optional[KnowledgeVisualizationService] = None


async def get_visualization_service() -> KnowledgeVisualizationService:
    """
    Get or create the singleton visualization service.

    Lazily initializes the service on first call. Subsequent calls
    return the same instance.

    Returns:
        Configured KnowledgeVisualizationService instance.

    Example:
        >>> service = await get_visualization_service()
        >>> graph = await service.get_graph()

    Note:
        Import of get_neo4j_client is done inside the function to avoid
        circular imports between the knowledge_graph module files.
    """
    global _visualization_service
    if _visualization_service is None:
        # Deferred import to avoid circular dependency
        from app.services.knowledge_graph import get_neo4j_client

        client = await get_neo4j_client()
        _visualization_service = KnowledgeVisualizationService(client)
    return _visualization_service
