"""
Unit Tests for Knowledge Search Service

Tests for:
- KnowledgeSearchService: keyword, full-text, vector, and semantic search
- build_topic_tree: hierarchical topic organization for the knowledge router
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.knowledge_graph import build_topic_tree
from app.services.knowledge_graph.search import KnowledgeSearchService


# =============================================================================
# Test Helpers
# =============================================================================


class AsyncIteratorMock:
    """
    Mock async iterator for simulating Neo4j query results.

    Neo4j's async driver returns results that can be iterated with `async for`.
    This helper creates an async iterator from a list of items.

    Args:
        items: List of dictionaries representing query result records.

    Example:
        mock_result = AsyncIteratorMock([{"id": "1", "title": "Test"}])
        async for record in mock_result:
            print(record)  # {"id": "1", "title": "Test"}
    """

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.index = 0

    def __aiter__(self) -> "AsyncIteratorMock":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.index < len(self.items):
            item = self.items[self.index]
            self.index += 1
            return item
        raise StopAsyncIteration


def make_search_result(
    id: str = "test-1",
    node_type: str = "Content",
    title: str = "Test Result",
    summary: str = "Test summary",
    score: float = 0.9,
) -> dict[str, Any]:
    """
    Factory function to create a mock search result.

    Args:
        id: Unique identifier for the node.
        node_type: Node label (Content, Concept, Note).
        title: Display title of the node.
        summary: Brief description of the node.
        score: Relevance score (0.0-1.0).

    Returns:
        Dictionary matching the search result schema.
    """
    return {
        "id": id,
        "node_type": node_type,
        "title": title,
        "summary": summary,
        "score": score,
    }


# =============================================================================
# KnowledgeSearchService Tests
# =============================================================================


class TestKnowledgeSearchService:
    """
    Tests for KnowledgeSearchService search methods.

    Tests cover:
    - keyword_search: basic CONTAINS matching
    - vector_search: embedding-based similarity search
    - semantic_search: unified search with fallback
    """

    @pytest.fixture
    def mock_neo4j_client(self) -> MagicMock:
        """Create a mock Neo4j client with async driver."""
        client = MagicMock()
        client._ensure_initialized = AsyncMock()
        client._async_driver = MagicMock()
        return client

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create a mock LLM client that returns 1536-dim embeddings."""
        client = MagicMock()
        # Return a list of embeddings and metadata (matching real signature)
        client.embed = AsyncMock(return_value=([[0.1] * 1536], MagicMock()))
        return client

    @pytest.fixture
    def search_service(
        self, mock_neo4j_client: MagicMock, mock_llm_client: MagicMock
    ) -> KnowledgeSearchService:
        """Create a KnowledgeSearchService with mocked dependencies."""
        return KnowledgeSearchService(mock_neo4j_client, mock_llm_client)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock Neo4j session."""
        return AsyncMock()

    @pytest.fixture
    def configured_session(
        self, mock_neo4j_client: MagicMock, mock_session: AsyncMock
    ) -> AsyncMock:
        """
        Configure mock_neo4j_client to return mock_session as context manager.

        This eliminates the repetitive setup of:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_neo4j_client._async_driver.session.return_value = mock_context

        Returns:
            The mock_session, ready for configuring .run() return values.
        """
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_neo4j_client._async_driver.session.return_value = mock_context
        return mock_session

    # -------------------------------------------------------------------------
    # keyword_search tests
    # -------------------------------------------------------------------------

    async def test_keyword_search_returns_results(
        self,
        search_service: KnowledgeSearchService,
        configured_session: AsyncMock,
    ) -> None:
        """keyword_search returns matching nodes with scores."""
        # Arrange
        expected_result = make_search_result(
            id="test-1",
            title="Machine Learning Basics",
            summary="Introduction to ML",
            score=0.9,
        )
        configured_session.run = AsyncMock(
            return_value=AsyncIteratorMock([expected_result])
        )

        # Act
        results, elapsed_ms = await search_service.keyword_search(
            query="machine learning",
            node_types=["Content", "Concept"],
            limit=10,
        )

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "test-1"
        assert results[0]["title"] == "Machine Learning Basics"
        assert elapsed_ms >= 0

    async def test_keyword_search_empty_results(
        self,
        search_service: KnowledgeSearchService,
        configured_session: AsyncMock,
    ) -> None:
        """keyword_search returns empty list when no matches found."""
        # Arrange
        configured_session.run = AsyncMock(return_value=AsyncIteratorMock([]))

        # Act
        results, elapsed_ms = await search_service.keyword_search(
            query="nonexistent",
            limit=10,
        )

        # Assert
        assert len(results) == 0
        assert elapsed_ms >= 0

    # -------------------------------------------------------------------------
    # vector_search tests
    # -------------------------------------------------------------------------

    async def test_vector_search_requires_llm_client(
        self, mock_neo4j_client: MagicMock
    ) -> None:
        """vector_search raises ValueError when LLM client is not configured."""
        service = KnowledgeSearchService(mock_neo4j_client, llm_client=None)

        with pytest.raises(ValueError, match="LLM client required"):
            await service.vector_search("test query")

    # -------------------------------------------------------------------------
    # semantic_search tests
    # -------------------------------------------------------------------------

    async def test_semantic_search_prefers_vector(
        self,
        search_service: KnowledgeSearchService,
        mock_llm_client: MagicMock,
        configured_session: AsyncMock,
    ) -> None:
        """semantic_search uses vector search when LLM client is available."""
        # Arrange
        expected_result = make_search_result(
            id="test-vec-1",
            title="Vector Result",
            summary="Found via embeddings",
            score=0.85,
        )
        configured_session.run = AsyncMock(
            return_value=AsyncIteratorMock([expected_result])
        )

        # Act
        await search_service.semantic_search(
            query="deep learning",
            use_vector=True,
        )

        # Assert - verify LLM was called for embeddings
        mock_llm_client.embed.assert_called_once_with(["deep learning"])

    async def test_semantic_search_falls_back_to_text(
        self, mock_neo4j_client: MagicMock, mock_session: AsyncMock
    ) -> None:
        """semantic_search falls back to text search when use_vector=False."""
        service = KnowledgeSearchService(mock_neo4j_client, llm_client=None)

        # Setup mock context manager manually (no LLM client in this test)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_neo4j_client._async_driver.session.return_value = mock_context

        # First call: fulltext index check (returns False -> triggers keyword fallback)
        mock_result_check = AsyncIteratorMock([{"exists": False}])
        # Second call: keyword search results
        mock_result_search = AsyncIteratorMock(
            [make_search_result(id="test-text-1", title="Text Result", score=0.7)]
        )
        mock_session.run = AsyncMock(
            side_effect=[mock_result_check, mock_result_search]
        )

        # Act
        results, _ = await service.semantic_search(
            query="neural networks",
            use_vector=False,
        )

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "test-text-1"


# =============================================================================
# build_topic_tree Tests
# =============================================================================


class TestBuildTopicTree:
    """
    Tests for the build_topic_tree helper in the knowledge router.

    This function builds a hierarchical tree structure from flat topic paths
    (e.g., "ml/deep-learning/transformers" -> nested tree).
    """

    @pytest.mark.parametrize(
        "topics,expected_roots,expected_max_depth,expected_first_name",
        [
            # Single-level topics
            pytest.param(
                [{"path": "ml", "content_count": 5}, {"path": "web", "content_count": 3}],
                2,  # expected_roots
                0,  # expected_max_depth
                "ml",  # expected_first_name
                id="single_level_topics",
            ),
            # Nested tree
            pytest.param(
                [
                    {"path": "ml", "content_count": 10},
                    {"path": "ml/deep-learning", "content_count": 5},
                    {"path": "ml/deep-learning/transformers", "content_count": 3},
                ],
                1,
                2,
                "ml",
                id="nested_tree",
            ),
            # Orphan topics (parent missing - path has depth but orphan becomes root)
            pytest.param(
                [{"path": "ml/transformers", "content_count": 3}],
                1,
                1,  # Path has 2 segments, max_depth reflects original path depth
                "transformers",  # Last segment becomes name when orphaned
                id="orphan_topic",
            ),
            # Empty list
            pytest.param(
                [],
                0,
                0,
                None,  # No first name for empty list
                id="empty_list",
            ),
        ],
    )
    def test_build_topic_tree(
        self,
        topics: list[dict[str, Any]],
        expected_roots: int,
        expected_max_depth: int,
        expected_first_name: str | None,
    ) -> None:
        """
        build_topic_tree correctly builds hierarchical structure from paths.

        Args:
            topics: Input topic list with path and content_count.
            expected_roots: Expected number of root nodes.
            expected_max_depth: Expected maximum tree depth.
            expected_first_name: Expected name of first root (None if empty).
        """
        roots, max_depth = build_topic_tree(topics)

        assert len(roots) == expected_roots
        assert max_depth == expected_max_depth
        if expected_first_name is not None:
            assert roots[0].name == expected_first_name

    def test_build_nested_tree_structure(self) -> None:
        """Verify nested tree has correct parent-child relationships."""
        topics = [
            {"path": "ml", "content_count": 10},
            {"path": "ml/deep-learning", "content_count": 5},
            {"path": "ml/deep-learning/transformers", "content_count": 3},
        ]

        roots, _ = build_topic_tree(topics)

        # Verify structure: ml -> deep-learning -> transformers
        assert roots[0].name == "ml"
        assert roots[0].content_count == 10
        assert len(roots[0].children) == 1
        assert roots[0].children[0].name == "deep-learning"
        assert roots[0].children[0].content_count == 5
        assert len(roots[0].children[0].children) == 1
        assert roots[0].children[0].children[0].name == "transformers"
