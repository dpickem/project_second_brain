"""
Unit Tests for Knowledge Visualization Service

Tests for:
- KnowledgeVisualizationService: graph data retrieval, stats, node details, connections
- Health check functionality
- Topic hierarchy building

Test organization:
- TestVisualizationGraph: get_graph method tests
- TestVisualizationStats: get_stats method tests
- TestNodeDetails: get_node_details method tests
- TestHealthCheck: check_health method tests
- TestConnections: get_connections method tests
- TestTopicHierarchy: get_topic_hierarchy method tests
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.enums.knowledge import ConnectionDirection
from app.services.knowledge_graph.visualization import KnowledgeVisualizationService


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


class SingleResultMock:
    """
    Mock for Neo4j single result queries.

    Wraps a single record or None for queries that use `result.single()`.
    """

    def __init__(self, record: dict[str, Any] | None) -> None:
        self._record = record

    async def single(self) -> dict[str, Any] | None:
        return self._record


def make_graph_node(
    id: str = "node-1",
    label: str = "Test Node",
    type: str = "Content",
    content_type: str | None = "paper",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Factory for creating mock graph node data."""
    return {
        "id": id,
        "label": label,
        "type": type,
        "content_type": content_type,
        "tags": tags or [],
    }


def make_graph_edge(
    source: str = "node-1",
    target: str = "node-2",
    type: str = "RELATES_TO",
    strength: float = 1.0,
) -> dict[str, Any]:
    """Factory for creating mock graph edge data."""
    return {
        "source": source,
        "target": target,
        "type": type,
        "strength": strength,
    }


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client with async driver."""
    client = MagicMock()
    client._ensure_initialized = AsyncMock()
    client._async_driver = MagicMock()
    client.verify_connectivity = AsyncMock(return_value=True)
    return client


@pytest.fixture
def visualization_service(mock_neo4j_client: MagicMock) -> KnowledgeVisualizationService:
    """Create a KnowledgeVisualizationService with mocked dependencies."""
    return KnowledgeVisualizationService(mock_neo4j_client)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock Neo4j session."""
    return AsyncMock()


@pytest.fixture
def configured_session(
    mock_neo4j_client: MagicMock, mock_session: AsyncMock
) -> AsyncMock:
    """
    Configure mock_neo4j_client to return mock_session as context manager.

    Returns:
        The mock_session, ready for configuring .run() return values.
    """
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_neo4j_client._async_driver.session.return_value = mock_context
    return mock_session


# =============================================================================
# TestVisualizationGraph
# =============================================================================


class TestVisualizationGraph:
    """Tests for get_graph method."""

    async def test_get_graph_returns_nodes_and_edges(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_graph returns nodes and edges in D3-compatible format."""
        # Arrange
        nodes = [
            make_graph_node("n1", "Node 1", "Content", "paper"),
            make_graph_node("n2", "Node 2", "Concept", None),
        ]
        edges = [make_graph_edge("n1", "n2", "RELATES_TO", 0.8)]

        # First query: node count
        count_result = SingleResultMock({"total": 2})
        # Second query: graph data
        graph_result = SingleResultMock({"nodes": nodes, "edges": edges})

        configured_session.run = AsyncMock(side_effect=[count_result, graph_result])

        # Act
        result = await visualization_service.get_graph(limit=100)

        # Assert
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["total_nodes"] == 2
        assert result["center_id"] is None

    async def test_get_graph_with_center_id(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_graph with center_id uses centered query."""
        # Arrange
        center_node = make_graph_node("center-1", "Center Node")
        count_result = SingleResultMock({"total": 1})
        graph_result = SingleResultMock({"nodes": [center_node], "edges": []})

        configured_session.run = AsyncMock(side_effect=[count_result, graph_result])

        # Act
        result = await visualization_service.get_graph(
            center_id="center-1", depth=2, limit=50
        )

        # Assert
        assert result["center_id"] == "center-1"
        assert len(result["nodes"]) == 1

    async def test_get_graph_filters_invalid_edges(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_graph excludes edges that reference non-existent nodes."""
        # Arrange
        nodes = [make_graph_node("n1", "Node 1")]
        # Edge references n2 which doesn't exist in nodes
        edges = [make_graph_edge("n1", "n2")]

        count_result = SingleResultMock({"total": 1})
        graph_result = SingleResultMock({"nodes": nodes, "edges": edges})

        configured_session.run = AsyncMock(side_effect=[count_result, graph_result])

        # Act
        result = await visualization_service.get_graph(limit=100)

        # Assert - edge should be filtered out
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 0

    async def test_get_graph_empty_result(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_graph handles empty graph gracefully."""
        count_result = SingleResultMock({"total": 0})
        graph_result = SingleResultMock(None)

        configured_session.run = AsyncMock(side_effect=[count_result, graph_result])

        # Act
        result = await visualization_service.get_graph()

        # Assert
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["total_nodes"] == 0

    @pytest.mark.parametrize(
        "node_types,expected_types",
        [
            (None, ["Content", "Concept", "Note"]),  # default
            (["Content"], ["Content"]),
            (["Content", "Concept"], ["Content", "Concept"]),
        ],
        ids=["default_types", "single_type", "multiple_types"],
    )
    async def test_get_graph_uses_correct_node_types(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
        node_types: list[str] | None,
        expected_types: list[str],
    ) -> None:
        """get_graph passes correct node_types to query."""
        count_result = SingleResultMock({"total": 0})
        graph_result = SingleResultMock({"nodes": [], "edges": []})
        configured_session.run = AsyncMock(side_effect=[count_result, graph_result])

        # Act
        await visualization_service.get_graph(node_types=node_types)

        # Assert - verify node_types parameter passed to query
        call_args = configured_session.run.call_args_list[0]
        assert call_args.kwargs.get("node_types") == expected_types


# =============================================================================
# TestVisualizationStats
# =============================================================================


class TestVisualizationStats:
    """Tests for get_stats method."""

    async def test_get_stats_returns_counts(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_stats returns proper statistics."""
        # Arrange
        stats_result = SingleResultMock({
            "content_count": 50,
            "concept_count": 25,
            "note_count": 100,
            "rel_count": 200,
            "types": ["paper", "article", "paper", "book"],
        })
        configured_session.run = AsyncMock(return_value=stats_result)

        # Act
        result = await visualization_service.get_stats()

        # Assert
        assert result["total_content"] == 50
        assert result["total_concepts"] == 25
        assert result["total_notes"] == 100
        assert result["total_relationships"] == 200
        assert result["content_by_type"] == {"paper": 2, "article": 1, "book": 1}

    async def test_get_stats_handles_empty_graph(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_stats handles empty graph gracefully."""
        configured_session.run = AsyncMock(return_value=SingleResultMock(None))

        # Act
        result = await visualization_service.get_stats()

        # Assert
        assert result["total_content"] == 0
        assert result["total_concepts"] == 0
        assert result["total_notes"] == 0
        assert result["total_relationships"] == 0
        assert result["content_by_type"] == {}

    async def test_get_stats_handles_null_types(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_stats handles None values in types list."""
        stats_result = SingleResultMock({
            "content_count": 10,
            "concept_count": 5,
            "note_count": 3,
            "rel_count": 15,
            "types": ["paper", None, "article", None],
        })
        configured_session.run = AsyncMock(return_value=stats_result)

        # Act
        result = await visualization_service.get_stats()

        # Assert - None values should be filtered out
        assert result["content_by_type"] == {"paper": 1, "article": 1}


# =============================================================================
# TestNodeDetails
# =============================================================================


class TestNodeDetails:
    """Tests for get_node_details method."""

    async def test_get_node_details_returns_full_info(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_node_details returns complete node information."""
        # Arrange
        node_data = {
            "id": "test-node-1",
            "label": "Machine Learning Basics",
            "type": "Content",
            "content_type": "paper",
            "summary": "An introduction to ML",
            "tags": ["ml", "basics"],
            "source_url": "https://example.com/paper.pdf",
            "created_at": "2024-01-01T00:00:00",
            "connections": 5,
            "file_path": "/vault/sources/papers/ml-basics.md",
            "name": None,
        }
        configured_session.run = AsyncMock(
            return_value=SingleResultMock({"node": node_data})
        )

        # Act
        result = await visualization_service.get_node_details("test-node-1")

        # Assert
        assert result is not None
        assert result["id"] == "test-node-1"
        assert result["label"] == "Machine Learning Basics"
        assert result["type"] == "Content"
        assert result["content_type"] == "paper"
        assert result["summary"] == "An introduction to ML"
        assert result["tags"] == ["ml", "basics"]
        assert result["connections"] == 5

    async def test_get_node_details_not_found(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_node_details returns None for non-existent node."""
        configured_session.run = AsyncMock(
            return_value=SingleResultMock({"node": None})
        )

        # Act
        result = await visualization_service.get_node_details("non-existent")

        # Assert
        assert result is None

    async def test_get_node_details_missing_optional_fields(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_node_details handles missing optional fields."""
        node_data = {
            "id": "concept-1",
            "type": "Concept",
            "name": "Neural Network",
        }
        configured_session.run = AsyncMock(
            return_value=SingleResultMock({"node": node_data})
        )

        # Act
        result = await visualization_service.get_node_details("concept-1")

        # Assert
        assert result is not None
        assert result["id"] == "concept-1"
        assert result["label"] == "concept-1"  # Falls back to id
        assert result["tags"] == []  # Default empty list


# =============================================================================
# TestHealthCheck
# =============================================================================


class TestHealthCheck:
    """Tests for check_health method."""

    async def test_health_check_healthy(
        self,
        visualization_service: KnowledgeVisualizationService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """check_health returns healthy status when connected."""
        mock_neo4j_client.verify_connectivity = AsyncMock(return_value=True)

        # Act
        result = await visualization_service.check_health()

        # Assert
        assert result["status"] == "healthy"
        assert result["neo4j_connected"] is True

    async def test_health_check_unhealthy(
        self,
        visualization_service: KnowledgeVisualizationService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """check_health returns unhealthy status when disconnected."""
        mock_neo4j_client.verify_connectivity = AsyncMock(return_value=False)

        # Act
        result = await visualization_service.check_health()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["neo4j_connected"] is False

    async def test_health_check_handles_exception(
        self,
        visualization_service: KnowledgeVisualizationService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """check_health returns error info when exception occurs."""
        mock_neo4j_client.verify_connectivity = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        # Act
        result = await visualization_service.check_health()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["neo4j_connected"] is False
        assert "Connection refused" in result["error"]


# =============================================================================
# TestConnections
# =============================================================================


class TestConnections:
    """Tests for get_connections method."""

    @pytest.fixture
    def incoming_connection(self) -> dict[str, Any]:
        """Sample incoming connection data."""
        return {
            "source_id": "source-1",
            "source_title": "Source Node",
            "source_type": "Content",
            "rel_type": "REFERENCES",
            "strength": 0.9,
            "context": "Source references this node",
        }

    @pytest.fixture
    def outgoing_connection(self) -> dict[str, Any]:
        """Sample outgoing connection data."""
        return {
            "target_id": "target-1",
            "target_title": "Target Node",
            "target_type": "Concept",
            "rel_type": "CONTAINS",
            "strength": 1.0,
            "context": "Contains this concept",
        }

    async def test_get_connections_both_directions(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
        incoming_connection: dict[str, Any],
        outgoing_connection: dict[str, Any],
    ) -> None:
        """get_connections returns both incoming and outgoing."""
        # First call: incoming
        incoming_result = AsyncIteratorMock([incoming_connection])
        # Second call: outgoing
        outgoing_result = AsyncIteratorMock([outgoing_connection])

        configured_session.run = AsyncMock(
            side_effect=[incoming_result, outgoing_result]
        )

        # Act
        result = await visualization_service.get_connections(
            node_id="test-node", direction=ConnectionDirection.BOTH
        )

        # Assert
        assert result["node_id"] == "test-node"
        assert len(result["incoming"]) == 1
        assert len(result["outgoing"]) == 1
        assert result["total"] == 2

    async def test_get_connections_incoming_only(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
        incoming_connection: dict[str, Any],
    ) -> None:
        """get_connections with INCOMING direction only queries incoming."""
        configured_session.run = AsyncMock(
            return_value=AsyncIteratorMock([incoming_connection])
        )

        # Act
        result = await visualization_service.get_connections(
            node_id="test-node", direction=ConnectionDirection.INCOMING
        )

        # Assert
        assert len(result["incoming"]) == 1
        assert len(result["outgoing"]) == 0
        assert result["total"] == 1

    async def test_get_connections_outgoing_only(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
        outgoing_connection: dict[str, Any],
    ) -> None:
        """get_connections with OUTGOING direction only queries outgoing."""
        configured_session.run = AsyncMock(
            return_value=AsyncIteratorMock([outgoing_connection])
        )

        # Act
        result = await visualization_service.get_connections(
            node_id="test-node", direction=ConnectionDirection.OUTGOING
        )

        # Assert
        assert len(result["incoming"]) == 0
        assert len(result["outgoing"]) == 1
        assert result["total"] == 1

    async def test_get_connections_filters_null_ids(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_connections filters out records with null source/target ids."""
        invalid_connection = {"source_id": None, "source_title": "Bad"}
        valid_connection = {
            "target_id": "t1",
            "target_title": "Good",
            "target_type": "Content",
            "rel_type": "RELATES_TO",
        }

        configured_session.run = AsyncMock(
            side_effect=[
                AsyncIteratorMock([invalid_connection]),
                AsyncIteratorMock([valid_connection]),
            ]
        )

        # Act
        result = await visualization_service.get_connections(
            node_id="test", direction=ConnectionDirection.BOTH
        )

        # Assert
        assert len(result["incoming"]) == 0  # Filtered out
        assert len(result["outgoing"]) == 1


# =============================================================================
# TestTopicHierarchy
# =============================================================================


class TestTopicHierarchy:
    """Tests for get_topic_hierarchy method."""

    async def test_get_topic_hierarchy_returns_tree(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_topic_hierarchy returns hierarchical structure."""
        # Arrange
        topics = [
            {"path": "ml", "content_count": 10},
            {"path": "ml/deep-learning", "content_count": 5},
            {"path": "web", "content_count": 3},
        ]
        configured_session.run = AsyncMock(return_value=AsyncIteratorMock(topics))

        # Act
        result = await visualization_service.get_topic_hierarchy()

        # Assert
        assert result["total_topics"] == 3
        assert result["max_depth"] == 1
        assert len(result["roots"]) == 2  # ml and web

    async def test_get_topic_hierarchy_empty(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_topic_hierarchy handles empty topic list."""
        configured_session.run = AsyncMock(return_value=AsyncIteratorMock([]))

        # Act
        result = await visualization_service.get_topic_hierarchy()

        # Assert
        assert result["roots"] == []
        assert result["total_topics"] == 0
        assert result["max_depth"] == 0

    async def test_get_topic_hierarchy_respects_min_content(
        self,
        visualization_service: KnowledgeVisualizationService,
        configured_session: AsyncMock,
    ) -> None:
        """get_topic_hierarchy passes min_content filter to query."""
        configured_session.run = AsyncMock(return_value=AsyncIteratorMock([]))

        # Act
        await visualization_service.get_topic_hierarchy(min_content=5)

        # Assert - verify min_content parameter was passed
        call_args = configured_session.run.call_args
        assert call_args.kwargs.get("min_content") == 5

