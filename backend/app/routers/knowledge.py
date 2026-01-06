"""
Knowledge Graph API Router

Exposes knowledge graph visualization and query operations via REST API.
Provides endpoints for:
- Graph data for visualization (nodes and edges)
- Graph statistics
- Node details
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.knowledge_graph import get_neo4j_client
from app.services.knowledge_graph.queries import (
    GET_VISUALIZATION_GRAPH,
    GET_VISUALIZATION_STATS,
    GET_NODE_DETAILS_BY_ID,
    GET_NODE_COUNT_BY_TYPES,
    get_centered_visualization_query,
)
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# =============================================================================
# Response Schemas
# =============================================================================


class GraphNode(BaseModel):
    """Node in the graph visualization."""

    id: str
    label: str  # Display title
    type: str  # "Content", "Concept", "Note"
    content_type: Optional[str] = None  # "paper", "article", etc. (for Content nodes)
    size: int = 1  # Node size weight (based on connections)
    color: Optional[str] = None  # Optional color hint
    metadata: dict = {}  # Additional properties


class GraphEdge(BaseModel):
    """Edge in the graph visualization."""

    source: str  # Source node ID
    target: str  # Target node ID
    type: str  # Relationship type
    strength: float = 1.0  # Edge weight
    label: Optional[str] = None  # Display label


class GraphResponse(BaseModel):
    """Response containing graph data for visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_id: Optional[str] = None
    total_nodes: int  # Total in graph (before limit)
    total_edges: int


class GraphStats(BaseModel):
    """Summary statistics for the knowledge graph."""

    total_content: int
    total_concepts: int
    total_notes: int
    total_relationships: int
    content_by_type: dict[str, int]


class NodeDetails(BaseModel):
    """Detailed information about a single node."""

    id: str
    label: str
    type: str
    content_type: Optional[str] = None
    summary: Optional[str] = None
    tags: list[str] = []
    source_url: Optional[str] = None
    created_at: Optional[str] = None
    connections: int = 0
    file_path: Optional[str] = None
    name: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/graph", response_model=GraphResponse)
async def get_graph_visualization(
    center_id: Optional[str] = Query(None, description="Center graph on this node ID"),
    node_types: str = Query(
        "Content,Concept,Note", description="Comma-separated node types"
    ),
    depth: int = Query(2, ge=1, le=4, description="Traversal depth from center"),
    limit: int = Query(100, ge=10, le=500, description="Max nodes to return"),
) -> GraphResponse:
    """
    Get graph data for visualization.

    Returns nodes and edges in D3-compatible format:
    - nodes: [{id, label, type, size, color, ...}]
    - edges: [{source, target, type, strength, ...}]

    Args:
        center_id: Optional node ID to center the graph on
        node_types: Comma-separated list of node types to include
        depth: How many hops from center to traverse (only used with center_id)
        limit: Maximum number of nodes to return
    """
    try:
        client = await get_neo4j_client()
        await client._ensure_initialized()

        node_type_list = [t.strip() for t in node_types.split(",")]

        async with client._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            # Get total count for stats
            count_result = await session.run(
                GET_NODE_COUNT_BY_TYPES, node_types=node_type_list
            )
            count_record = await count_result.single()
            total_nodes = count_record["total"] if count_record else 0

            # Get graph data
            if center_id:
                result = await session.run(
                    get_centered_visualization_query(depth),
                    center_id=center_id,
                    node_types=node_type_list,
                    limit=limit,
                )
            else:
                result = await session.run(
                    GET_VISUALIZATION_GRAPH,
                    node_types=node_type_list,
                    limit=limit,
                )

            record = await result.single()

            if not record:
                return GraphResponse(
                    nodes=[],
                    edges=[],
                    center_id=center_id,
                    total_nodes=0,
                    total_edges=0,
                )

            raw_nodes = record["nodes"] or []
            raw_edges = record["edges"] or []

            # Convert to response models
            nodes = []
            node_ids = set()
            for n in raw_nodes:
                if n and n.get("id"):
                    node_ids.add(n["id"])
                    nodes.append(
                        GraphNode(
                            id=n["id"],
                            label=n.get("label", n["id"]),
                            type=n.get("type", "Unknown"),
                            content_type=n.get("content_type"),
                            metadata={"tags": n.get("tags", [])},
                        )
                    )

            # Filter edges to only include nodes we have
            edges = []
            for e in raw_edges:
                if (
                    e
                    and e.get("source")
                    and e.get("target")
                    and e["source"] in node_ids
                    and e["target"] in node_ids
                ):
                    edges.append(
                        GraphEdge(
                            source=e["source"],
                            target=e["target"],
                            type=e.get("type", "RELATED"),
                            strength=e.get("strength", 1.0),
                        )
                    )

            return GraphResponse(
                nodes=nodes,
                edges=edges,
                center_id=center_id,
                total_nodes=total_nodes,
                total_edges=len(edges),
            )

    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph: {str(e)}")


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats() -> GraphStats:
    """
    Get summary statistics for the knowledge graph.

    Returns:
        - total_content: Number of Content nodes
        - total_concepts: Number of Concept nodes
        - total_notes: Number of Note nodes
        - total_relationships: Number of relationships
        - content_by_type: Breakdown of content by type
    """
    try:
        client = await get_neo4j_client()
        await client._ensure_initialized()

        async with client._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(GET_VISUALIZATION_STATS)
            record = await result.single()

            if not record:
                return GraphStats(
                    total_content=0,
                    total_concepts=0,
                    total_notes=0,
                    total_relationships=0,
                    content_by_type={},
                )

            # Count content by type
            types = record["types"] or []
            type_counts = {}
            for t in types:
                if t:
                    type_counts[t] = type_counts.get(t, 0) + 1

            return GraphStats(
                total_content=record["content_count"] or 0,
                total_concepts=record["concept_count"] or 0,
                total_notes=record["note_count"] or 0,
                total_relationships=record["rel_count"] or 0,
                content_by_type=type_counts,
            )

    except Exception as e:
        logger.error(f"Error fetching graph stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/node/{node_id}", response_model=NodeDetails)
async def get_node_details(node_id: str) -> NodeDetails:
    """
    Get detailed information about a specific node.

    Args:
        node_id: The node's unique identifier
    """
    try:
        client = await get_neo4j_client()
        await client._ensure_initialized()

        async with client._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(GET_NODE_DETAILS_BY_ID, node_id=node_id)
            record = await result.single()

            if not record or not record["node"]:
                raise HTTPException(status_code=404, detail="Node not found")

            node = record["node"]
            return NodeDetails(
                id=node["id"],
                label=node.get("label", node["id"]),
                type=node.get("type", "Unknown"),
                content_type=node.get("content_type"),
                summary=node.get("summary"),
                tags=node.get("tags", []),
                source_url=node.get("source_url"),
                created_at=node.get("created_at"),
                connections=node.get("connections", 0),
                file_path=node.get("file_path"),
                name=node.get("name"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching node details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch node: {str(e)}")


@router.get("/health")
async def knowledge_graph_health():
    """Check Neo4j connection health."""
    try:
        client = await get_neo4j_client()
        is_connected = await client.verify_connectivity()
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
