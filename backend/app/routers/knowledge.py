"""
Knowledge Graph API Router

Exposes knowledge graph visualization and query operations via REST API.

Endpoints:
    GET  /api/knowledge/graph           - Get graph data for visualization
    GET  /api/knowledge/stats           - Get graph statistics
    GET  /api/knowledge/node/{node_id}  - Get node details
    GET  /api/knowledge/health          - Check Neo4j connection health
    POST /api/knowledge/search          - Semantic search across knowledge base
    GET  /api/knowledge/connections/{node_id} - Get node connections
    GET  /api/knowledge/topics          - Get topic hierarchy

Models are defined in app.models.knowledge.
Enums are defined in app.enums.knowledge.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.enums.knowledge import ConnectionDirection
from app.models.knowledge import (
    ConnectionsResponse,
    GraphNode,
    GraphEdge,
    GraphResponse,
    GraphStats,
    NodeConnection,
    NodeDetails,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TopicHierarchyResponse,
)
from app.services.knowledge_graph import (
    get_neo4j_client,
    get_visualization_service,
    KnowledgeSearchService,
)
from app.services.llm import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# =============================================================================
# Graph Visualization Endpoints
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

    Returns nodes and edges in D3-compatible format for force-directed graphs.

    Args:
        center_id: Optional node ID to center the graph on
        node_types: Comma-separated list of node types to include
        depth: How many hops from center to traverse (only used with center_id)
        limit: Maximum number of nodes to return

    Returns:
        GraphResponse with nodes, edges, and metadata
    """
    try:
        service = await get_visualization_service()
        node_type_list = [t.strip() for t in node_types.split(",")]

        result = await service.get_graph(
            center_id=center_id,
            node_types=node_type_list,
            depth=depth,
            limit=limit,
        )

        # Convert to response models
        nodes = [
            GraphNode(
                id=n["id"],
                label=n["label"],
                type=n["type"],
                content_type=n.get("content_type"),
                metadata=n.get("metadata", {}),
            )
            for n in result["nodes"]
        ]

        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                type=e["type"],
                strength=e["strength"],
            )
            for e in result["edges"]
        ]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            center_id=result["center_id"],
            total_nodes=result["total_nodes"],
            total_edges=result["total_edges"],
        )

    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph: {str(e)}")


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats() -> GraphStats:
    """
    Get summary statistics for the knowledge graph.

    Returns:
        GraphStats with node and relationship counts
    """
    try:
        service = await get_visualization_service()
        result = await service.get_stats()

        return GraphStats(
            total_content=result["total_content"],
            total_concepts=result["total_concepts"],
            total_notes=result["total_notes"],
            total_relationships=result["total_relationships"],
            content_by_type=result["content_by_type"],
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

    Returns:
        NodeDetails with full node information

    Raises:
        HTTPException 404: If node not found
    """
    try:
        service = await get_visualization_service()
        result = await service.get_node_details(node_id)

        if not result:
            raise HTTPException(status_code=404, detail="Node not found")

        return NodeDetails(
            id=result["id"],
            label=result["label"],
            type=result["type"],
            content_type=result.get("content_type"),
            summary=result.get("summary"),
            tags=result.get("tags", []),
            source_url=result.get("source_url"),
            created_at=result.get("created_at"),
            connections=result.get("connections", 0),
            file_path=result.get("file_path"),
            name=result.get("name"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching node details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch node: {str(e)}")


@router.get("/health")
async def knowledge_graph_health() -> dict:
    """
    Check Neo4j connection health.

    Returns:
        Health status dict with neo4j_connected boolean
    """
    service = await get_visualization_service()
    return await service.check_health()


# =============================================================================
# Search Endpoint
# =============================================================================


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest) -> SearchResponse:
    """
    Semantic search across knowledge base.

    Uses embeddings to find semantically similar content when available,
    otherwise falls back to keyword/fulltext matching. Searches across
    Content, Concepts, and Notes.

    Args:
        request: Search query and filters

    Returns:
        SearchResponse with ranked results
    """
    try:
        neo4j_client = await get_neo4j_client()
        await neo4j_client._ensure_initialized()

        # Get LLM client for vector search (optional)
        llm_client = None
        if request.use_vector:
            try:
                llm_client = get_llm_client()
            except Exception:
                logger.debug("LLM client not available, using text search only")

        search_service = KnowledgeSearchService(neo4j_client, llm_client)

        results, search_time_ms = await search_service.semantic_search(
            query=request.query,
            node_types=request.node_types,
            limit=request.limit,
            min_score=request.min_score,
            use_vector=request.use_vector and llm_client is not None,
        )

        # Convert to response format
        search_results = [
            SearchResult(
                id=r.get("id", ""),
                node_type=r.get("node_type", "Unknown"),
                title=r.get("title", "Untitled"),
                summary=r.get("summary"),
                score=min(r.get("score", 0), 1.0),  # Cap at 1.0
                highlights=[],  # Could extract snippets in future
            )
            for r in results
            if r.get("id")
        ]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results),
            search_time_ms=search_time_ms,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# =============================================================================
# Connection Endpoints
# =============================================================================


@router.get("/connections/{node_id}", response_model=ConnectionsResponse)
async def get_connections(
    node_id: str,
    direction: ConnectionDirection = Query(
        ConnectionDirection.BOTH, description="Filter by direction"
    ),
    limit: int = Query(20, ge=1, le=100, description="Max connections per direction"),
) -> ConnectionsResponse:
    """
    Get connections for a specific node.

    Returns incoming and outgoing relationships, optionally filtered by direction.

    Args:
        node_id: The node to get connections for
        direction: incoming, outgoing, or both
        limit: Maximum connections per direction

    Returns:
        ConnectionsResponse with incoming and outgoing lists
    """
    try:
        service = await get_visualization_service()
        result = await service.get_connections(
            node_id=node_id,
            direction=direction,
            limit=limit,
        )

        incoming = [
            NodeConnection(
                source_id=c["source_id"],
                target_id=c["target_id"],
                target_title=c["target_title"],
                target_type=c["target_type"],
                relationship=c["relationship"],
                strength=c.get("strength", 1.0),
                context=c.get("context"),
            )
            for c in result["incoming"]
        ]

        outgoing = [
            NodeConnection(
                source_id=c["source_id"],
                target_id=c["target_id"],
                target_title=c["target_title"],
                target_type=c["target_type"],
                relationship=c["relationship"],
                strength=c.get("strength", 1.0),
                context=c.get("context"),
            )
            for c in result["outgoing"]
        ]

        return ConnectionsResponse(
            node_id=result["node_id"],
            incoming=incoming,
            outgoing=outgoing,
            total=result["total"],
        )

    except Exception as e:
        logger.error(f"Error fetching connections: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch connections: {str(e)}"
        )


# =============================================================================
# Topic Hierarchy Endpoints
# =============================================================================


@router.get("/topics", response_model=TopicHierarchyResponse)
async def get_topic_hierarchy(
    min_content: int = Query(0, ge=0, description="Min content count to include"),
) -> TopicHierarchyResponse:
    """
    Get hierarchical topic structure.

    Topics are organized in a tree based on their tag paths:
    - ml/
      - ml/deep-learning/
        - ml/deep-learning/transformers/

    Args:
        min_content: Filter out topics with fewer items

    Returns:
        TopicHierarchyResponse with tree structure
    """
    try:
        service = await get_visualization_service()
        result = await service.get_topic_hierarchy(min_content=min_content)

        return TopicHierarchyResponse(
            roots=result["roots"],
            total_topics=result["total_topics"],
            max_depth=result["max_depth"],
        )

    except Exception as e:
        logger.error(f"Error fetching topic hierarchy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch topics: {str(e)}")


# =============================================================================
# Maintenance Endpoints
# =============================================================================


@router.post("/link-content-notes")
async def link_content_to_notes() -> dict:
    """
    Create REPRESENTS relationships between Content and Note nodes.

    Content nodes (from LLM processing) and Note nodes (from vault sync) may
    represent the same file but aren't automatically linked. This endpoint
    creates REPRESENTS relationships for all Content/Note pairs that share
    the same file_path.

    This is a backfill operation for existing data. New Content and Note nodes
    are automatically linked during creation.

    Returns:
        Dict with count of newly created links
    """
    try:
        neo4j_client = await get_neo4j_client()
        linked_count = await neo4j_client.link_all_content_to_notes()

        logger.info(f"Linked {linked_count} Content-Note pairs")

        return {
            "status": "success",
            "linked_count": linked_count,
            "message": f"Created {linked_count} REPRESENTS relationships",
        }

    except Exception as e:
        logger.error(f"Error linking content to notes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to link content to notes: {str(e)}"
        )
