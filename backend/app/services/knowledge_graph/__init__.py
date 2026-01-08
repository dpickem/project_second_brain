"""
Knowledge Graph Service Module

Provides Neo4j client wrapper for knowledge graph operations:

- Vector similarity search for connection discovery
- Content and concept node creation
- Relationship management
- Graph traversal queries
- Semantic search across knowledge base
- Graph visualization data

Usage:
    from app.services.knowledge_graph import get_neo4j_client, KnowledgeSearchService

    client = await get_neo4j_client()
    similar = await client.vector_search(embedding, top_k=10)
    
    search = KnowledgeSearchService(client)
    results = await search.semantic_search("machine learning")

    # Visualization service
    from app.services.knowledge_graph import get_visualization_service
    viz = await get_visualization_service()
    graph = await viz.get_graph(limit=100)

    # Utility functions
    from app.services.knowledge_graph import build_topic_tree
    roots, depth = build_topic_tree(flat_topics)
"""

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.services.knowledge_graph.search import KnowledgeSearchService, get_search_service
from app.services.knowledge_graph.utils import build_topic_tree
from app.services.knowledge_graph.visualization import (
    KnowledgeVisualizationService,
    get_visualization_service,
)

__all__ = [
    "Neo4jClient",
    "get_neo4j_client",
    "KnowledgeSearchService",
    "get_search_service",
    "KnowledgeVisualizationService",
    "get_visualization_service",
    "build_topic_tree",
]
