"""
Knowledge Graph Service Module

Provides Neo4j client wrapper for knowledge graph operations:

- Vector similarity search for connection discovery
- Content and concept node creation
- Relationship management
- Graph traversal queries

Usage:
    from app.services.knowledge_graph import get_neo4j_client

    client = await get_neo4j_client()
    similar = await client.vector_search(embedding, top_k=10)
"""

from app.services.knowledge_graph.client import Neo4jClient, get_neo4j_client

__all__ = ["Neo4jClient", "get_neo4j_client"]
