"""
Knowledge Graph Search Service

Search capabilities for the knowledge graph:
- Keyword search (CONTAINS matching)
- Full-text search (requires fulltext index)
- Vector similarity search (requires embeddings)
- Hybrid search (combines text + vector)

Usage:
    service = KnowledgeSearchService(neo4j_client, llm_client)
    results, ms = await service.semantic_search("machine learning", limit=20)
"""

import logging
import time
from typing import Optional

from app.services.knowledge_graph.client import Neo4jClient
from app.services.knowledge_graph.queries import (
    CHECK_FULLTEXT_INDEX,
    FULLTEXT_SEARCH_QUERY,
    KEYWORD_SEARCH_QUERY,
    SEARCH_VECTOR_QUERY,
)
from app.services.llm.client import LLMClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeSearchService:
    """
    Search service supporting keyword, full-text, vector, and hybrid search.

    Attributes:
        DEFAULT_NODE_TYPES: Node types for text-based searches.
        VECTOR_NODE_TYPES: Node types for vector searches (excludes Note).
    """

    DEFAULT_NODE_TYPES = ["Content", "Concept", "Note"]
    VECTOR_NODE_TYPES = ["Content", "Concept"]

    def __init__(
        self, neo4j_client: Neo4jClient, llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize the search service.

        Args:
            neo4j_client: Neo4j client for executing graph queries.
            llm_client: Optional LLM client for generating embeddings.
                Required for vector_search and hybrid_search.
        """
        self.neo4j = neo4j_client
        self.llm = llm_client
        self._fulltext_index_exists: Optional[bool] = None

    async def _run_query(self, cypher: str, **params) -> list[dict]:
        """
        Execute a Cypher query and return results as dicts.

        Args:
            cypher: The Cypher query string to execute.
            **params: Named parameters to pass to the query.

        Returns:
            List of dictionaries, one per result record.
        """
        await self.neo4j._ensure_initialized()
        async with self.neo4j._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(cypher, **params)
            return [dict(record) async for record in result]

    async def _check_fulltext_index(self) -> bool:
        """
        Check if the fulltext search index exists (result is cached).

        Returns:
            True if 'searchIndex' fulltext index exists, False otherwise.
        """
        if self._fulltext_index_exists is not None:
            return self._fulltext_index_exists

        try:
            records = await self._run_query(CHECK_FULLTEXT_INDEX)
            self._fulltext_index_exists = records[0]["exists"] if records else False
        except Exception as e:
            logger.debug(f"Could not check fulltext index: {e}")
            self._fulltext_index_exists = False

        return self._fulltext_index_exists

    async def keyword_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 20,
    ) -> tuple[list[dict], float]:
        """
        Keyword search using CONTAINS matching on title, name, and summary.

        This is the most basic search method, performing case-insensitive
        substring matching. Scoring is based on which field matched:
        title (1.0), name (0.9), summary (0.7).

        Args:
            query: Search string to match against node properties.
            node_types: Node labels to search. Defaults to DEFAULT_NODE_TYPES.
            limit: Maximum number of results to return.

        Returns:
            Tuple of (results, elapsed_ms) where results is a list of dicts
            with keys: id, node_type, title, summary, score.
        """
        start = time.perf_counter()
        records = await self._run_query(
            KEYWORD_SEARCH_QUERY,
            query=query,
            node_types=node_types or self.DEFAULT_NODE_TYPES,
            limit=limit,
        )
        return records, (time.perf_counter() - start) * 1000

    async def full_text_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 20,
        min_score: float = 0.5,
    ) -> tuple[list[dict], float]:
        """
        Full-text search using Neo4j's fulltext index.

        Uses Lucene-based fulltext search for better relevance ranking.
        Automatically falls back to keyword_search if the fulltext index
        doesn't exist.

        Args:
            query: Search string (supports Lucene query syntax).
            node_types: Node labels to search. Defaults to DEFAULT_NODE_TYPES.
            limit: Maximum number of results to return.
            min_score: Minimum relevance score threshold (0.0-1.0).

        Returns:
            Tuple of (results, elapsed_ms) where results is a list of dicts
            with keys: id, node_type, title, summary, score.

        Example:
            Lucene query syntax examples::

                "machine learning"     # exact phrase
                machine AND learning   # both terms required
                machine OR neural      # either term
                machin*                # wildcard (matches machine, machining)
                learning~              # fuzzy match (matches learning typos)
                "neural network"~3     # terms within 3 words of each other
        """
        if not await self._check_fulltext_index():
            logger.debug("Fulltext index not found, falling back to keyword search")
            return await self.keyword_search(query, node_types, limit)

        start = time.perf_counter()
        records = await self._run_query(
            FULLTEXT_SEARCH_QUERY,
            query=query,
            node_types=node_types or self.DEFAULT_NODE_TYPES,
            limit=limit,
            min_score=min_score,
        )
        return records, (time.perf_counter() - start) * 1000

    async def vector_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 20,
        min_score: float = 0.7,
    ) -> tuple[list[dict], float]:
        """
        Vector similarity search using embeddings.

        Generates an embedding for the query and finds semantically similar
        nodes using cosine similarity. Searches each node type's vector
        index separately and merges results.

        Args:
            query: Natural language search query.
            node_types: Node labels to search. Defaults to VECTOR_NODE_TYPES.
            limit: Maximum number of results to return.
            min_score: Minimum cosine similarity threshold (0.0-1.0).

        Returns:
            Tuple of (results, elapsed_ms) where results is a list of dicts
            with keys: id, node_type, title, summary, score.

        Raises:
            ValueError: If LLM client was not provided during initialization.
        """
        if not self.llm:
            raise ValueError("LLM client required for vector search")

        await self.neo4j._ensure_initialized()
        start = time.perf_counter()
        node_types = node_types or self.VECTOR_NODE_TYPES

        # Generate query embedding
        embeddings, _ = await self.llm.embed([query])
        if not embeddings:
            logger.error("Failed to generate embedding for query")
            return [], 0

        # Search each node type's vector index
        all_results = []
        for node_type in node_types:
            index_name = f"{node_type.lower()}_embedding_index"
            try:
                records = await self._run_query(
                    SEARCH_VECTOR_QUERY,
                    index_name=index_name,
                    embedding=embeddings[0],
                    node_types=[node_type],
                    limit=limit,
                    min_score=min_score,
                )
                all_results.extend(records)
            except Exception as e:
                logger.debug(f"Vector search failed for {node_type}: {e}")

        # Sort by score and limit
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:limit], (time.perf_counter() - start) * 1000

    async def semantic_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 20,
        min_score: float = 0.5,
        use_vector: bool = True,
    ) -> tuple[list[dict], float]:
        """
        Unified semantic search with automatic fallback.

        Attempts vector search first (if LLM client available and use_vector=True),
        falling back to full-text search on failure or if vector search is disabled.

        Args:
            query: Search string or natural language query.
            node_types: Node labels to search. Defaults vary by search method.
            limit: Maximum number of results to return.
            min_score: Minimum relevance/similarity threshold (0.0-1.0).
            use_vector: Whether to attempt vector search first.

        Returns:
            Tuple of (results, elapsed_ms) where results is a list of dicts
            with keys: id, node_type, title, summary, score.
        """
        if use_vector and self.llm:
            try:
                return await self.vector_search(query, node_types, limit, min_score)
            except Exception as e:
                logger.warning(f"Vector search failed, falling back to text: {e}")

        return await self.full_text_search(query, node_types, limit, min_score)

    async def hybrid_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 20,
        min_score: float = 0.5,
        text_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> tuple[list[dict], float]:
        """
        Hybrid search combining text and vector results with weighted scoring.

        Runs both full-text and vector searches, then merges results using
        weighted combination of scores. This often provides the best results
        by capturing both keyword matches and semantic similarity.

        Args:
            query: Search string or natural language query.
            node_types: Node labels to search. Defaults vary by search method.
            limit: Maximum number of results to return.
            min_score: Minimum score threshold for individual searches.
            text_weight: Weight for full-text search scores (0.0-1.0).
            vector_weight: Weight for vector search scores (0.0-1.0).

        Returns:
            Tuple of (results, elapsed_ms) where results is a list of dicts
            with keys: id, node_type, title, summary, score, text_score,
            vector_score.

        Note:
            Falls back to full_text_search if LLM client is not available.
        """
        if not self.llm:
            return await self.full_text_search(query, node_types, limit, min_score)

        start = time.perf_counter()

        # Run both searches
        text_results, _ = await self.full_text_search(
            query, node_types, limit * 2, min_score
        )
        vector_results, _ = await self.vector_search(
            query, node_types, limit * 2, min_score
        )

        # Merge results by node id
        merged: dict[str, dict] = {}
        for r in text_results:
            merged[r["id"]] = {**r, "text_score": r.get("score", 0), "vector_score": 0}
        for r in vector_results:
            if r["id"] in merged:
                merged[r["id"]]["vector_score"] = r.get("score", 0)
            else:
                merged[r["id"]] = {
                    **r,
                    "text_score": 0,
                    "vector_score": r.get("score", 0),
                }

        # Calculate combined scores
        for result in merged.values():
            result["score"] = (
                result["text_score"] * text_weight
                + result["vector_score"] * vector_weight
            )

        # Sort and limit
        results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[
            :limit
        ]
        return results, (time.perf_counter() - start) * 1000


async def get_search_service(
    neo4j_client: Neo4jClient,
    llm_client: Optional[LLMClient] = None,
) -> KnowledgeSearchService:
    """
    Factory function to create a KnowledgeSearchService.

    Args:
        neo4j_client: Neo4j client for executing graph queries.
        llm_client: Optional LLM client for generating embeddings.

    Returns:
        Configured KnowledgeSearchService instance.
    """
    return KnowledgeSearchService(neo4j_client, llm_client)
