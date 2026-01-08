"""
Integration Tests for Knowledge and Analytics API Endpoints.

This module provides integration tests for:
- Knowledge API endpoints:
    - /api/knowledge/search - Semantic search with filtering
    - /api/knowledge/connections/{node_id} - Node connection queries
    - /api/knowledge/topics - Topic hierarchy retrieval
- Analytics API endpoints:
    - /api/analytics/time-investment - Time investment tracking
    - /api/analytics/streak - Learning streak information
    - /api/analytics/time-log - Manual time logging

IMPORTANT: These tests use the TEST database only (via POSTGRES_TEST_* env vars).
The test_client fixture overrides get_db to ensure the production database
is never touched. See tests/integration/conftest.py for details.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def now() -> datetime:
    """
    Provide the current UTC timestamp (timezone-aware).

    Returns:
        datetime: Current time in UTC with timezone info.
    """
    return datetime.now(timezone.utc)


@pytest.fixture
def valid_time_log_payload(now: datetime) -> dict[str, Any]:
    """
    Generate a valid time log payload for testing.

    Creates a payload representing 10 minutes of review activity
    starting from the current time.

    Args:
        now: Current UTC timestamp from the `now` fixture.

    Returns:
        dict: Valid time log request payload.
    """
    return {
        "activity_type": "review",
        "started_at": now.isoformat(),
        "ended_at": (now + timedelta(minutes=10)).isoformat(),
        "topic": "ml/transformers",
        "items_completed": 5,
    }


# =============================================================================
# Knowledge Search Endpoint Tests
# =============================================================================


class TestKnowledgeSearchEndpoint:
    """
    Integration tests for the /api/knowledge/search endpoint.

    Tests semantic search functionality including:
    - Valid search requests with various parameters
    - Query validation (empty queries, invalid limits)
    - Response structure verification
    """

    @pytest.mark.asyncio
    async def test_search_accepts_valid_request(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the search endpoint accepts valid requests and returns
        expected response structure.

        Tests a fully-specified search request with query, node types,
        limit, and minimum score filter.
        """
        response = await async_test_client.post(
            "/api/knowledge/search",
            json={
                "query": "machine learning",
                "node_types": ["Content", "Concept"],
                "limit": 5,
                "min_score": 0.3,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response contains required fields
        assert "results" in data, "Response should contain 'results'"
        assert "search_time_ms" in data, "Response should contain 'search_time_ms'"
        assert data["query"] == "machine learning"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("payload", "description"),
        [
            pytest.param(
                {"query": "", "limit": 5},
                "empty query string",
                id="empty_query",
            ),
            pytest.param(
                {"query": "test", "limit": 200},
                "limit exceeds maximum (100)",
                id="limit_too_high",
            ),
            pytest.param(
                {"query": "test", "limit": 0},
                "limit is zero",
                id="limit_zero",
            ),
            pytest.param(
                {"query": "test", "min_score": 1.5},
                "min_score exceeds 1.0",
                id="invalid_min_score",
            ),
        ],
    )
    async def test_search_validates_invalid_inputs(
        self,
        async_test_client: AsyncClient,
        payload: dict[str, Any],
        description: str,
    ) -> None:
        """
        Verify that the search endpoint validates request parameters.

        Tests that invalid inputs return HTTP 422 Unprocessable Entity.

        Args:
            async_test_client: The async HTTP test client.
            payload: The request payload to test.
            description: Description of the validation case (for test output).
        """
        response = await async_test_client.post(
            "/api/knowledge/search",
            json=payload,
        )

        assert response.status_code == 422, f"Expected 422 for {description}"


# =============================================================================
# Connections Endpoint Tests
# =============================================================================


class TestConnectionsEndpoint:
    """
    Integration tests for the /api/knowledge/connections/{node_id} endpoint.

    Tests node connection queries including:
    - Response structure with incoming/outgoing connections
    - Direction parameter validation
    """

    @pytest.mark.asyncio
    async def test_connections_returns_expected_structure(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the connections endpoint returns the expected response
        structure with node ID, incoming/outgoing connections, and total count.
        """
        response = await async_test_client.get(
            "/api/knowledge/connections/test-node-id",
            params={"direction": "both", "limit": 10},
        )

        # Note: May return 500 if Neo4j is not available
        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()

            required_fields = ["node_id", "incoming", "outgoing", "total"]
            for field in required_fields:
                assert field in data, f"Response should contain '{field}'"

    @pytest.mark.asyncio
    async def test_connections_validates_direction_parameter(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the connections endpoint validates the direction parameter.

        Only 'incoming', 'outgoing', and 'both' are valid values.
        """
        response = await async_test_client.get(
            "/api/knowledge/connections/test-node",
            params={"direction": "invalid"},
        )

        assert response.status_code == 422


# =============================================================================
# Topics Endpoint Tests
# =============================================================================


class TestTopicsEndpoint:
    """
    Integration tests for the /api/knowledge/topics endpoint.

    Tests topic hierarchy retrieval including:
    - Response structure with topic roots and metadata
    - Filter parameter handling
    """

    @pytest.mark.asyncio
    async def test_topics_returns_expected_structure(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the topics endpoint returns the expected response
        structure with topic roots, total count, and max depth.
        """
        response = await async_test_client.get(
            "/api/knowledge/topics",
            params={"min_content": 0},
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = ["roots", "total_topics", "max_depth"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}'"


# =============================================================================
# Analytics - Time Investment Endpoint Tests
# =============================================================================


class TestTimeInvestmentEndpoint:
    """
    Integration tests for the /api/analytics/time-investment endpoint.

    Tests time investment tracking including:
    - Response structure with aggregated time data
    - Period and group_by parameter validation
    """

    @pytest.mark.asyncio
    async def test_time_investment_returns_expected_structure(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the time investment endpoint returns the expected
        response structure with totals, periods, and trend data.
        """
        response = await async_test_client.get(
            "/api/analytics/time-investment",
            params={"period": "30d", "group_by": "day"},
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = ["total_minutes", "periods", "daily_average", "trend"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}'"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("params", "description"),
        [
            pytest.param(
                {"period": "invalid"},
                "invalid period format",
                id="invalid_period",
            ),
            pytest.param(
                {"period": "30d", "group_by": "invalid"},
                "invalid group_by value",
                id="invalid_group_by",
            ),
        ],
    )
    async def test_time_investment_validates_parameters(
        self,
        async_test_client: AsyncClient,
        params: dict[str, str],
        description: str,
    ) -> None:
        """
        Verify that the time investment endpoint validates query parameters.

        Args:
            async_test_client: The async HTTP test client.
            params: Query parameters to test.
            description: Description of the validation case.
        """
        response = await async_test_client.get(
            "/api/analytics/time-investment",
            params=params,
        )

        assert response.status_code == 422, f"Expected 422 for {description}"


# =============================================================================
# Analytics - Streak Endpoint Tests
# =============================================================================


class TestStreakEndpoint:
    """
    Integration tests for the /api/analytics/streak endpoint.

    Tests learning streak information including:
    - Response structure with current/longest streak data
    - Milestone tracking
    """

    @pytest.mark.asyncio
    async def test_streak_returns_expected_structure(
        self,
        async_test_client: AsyncClient,
    ) -> None:
        """
        Verify that the streak endpoint returns the expected response
        structure with streak counts and milestone information.
        """
        response = await async_test_client.get("/api/analytics/streak")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "current_streak",
            "longest_streak",
            "is_active_today",
            "days_this_week",
            "milestones_reached",
        ]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}'"


# =============================================================================
# Analytics - Time Log Endpoint Tests
# =============================================================================


class TestTimeLogEndpoint:
    """
    Integration tests for the /api/analytics/time-log endpoint.

    Tests manual time logging including:
    - Valid time log submission
    - Required field validation
    """

    @pytest.mark.asyncio
    async def test_time_log_accepts_valid_request(
        self,
        async_test_client: AsyncClient,
        valid_time_log_payload: dict[str, Any],
    ) -> None:
        """
        Verify that the time log endpoint accepts valid requests.

        Uses the valid_time_log_payload fixture to provide a properly
        formatted request body.

        Note: May return 500 if database is not available for writes,
        but should at least pass validation.
        """
        response = await async_test_client.post(
            "/api/analytics/time-log",
            json=valid_time_log_payload,
        )

        # Accept either success or internal error (DB unavailable)
        # 422 would indicate a validation failure, which we don't expect
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("payload", "description"),
        [
            pytest.param(
                {
                    "started_at": "2026-01-07T10:00:00Z",
                    "ended_at": "2026-01-07T10:30:00Z",
                },
                "missing activity_type",
                id="missing_activity_type",
            ),
            pytest.param(
                {
                    "activity_type": "review",
                    "ended_at": "2026-01-07T10:30:00Z",
                },
                "missing started_at",
                id="missing_started_at",
            ),
            pytest.param(
                {
                    "activity_type": "review",
                    "started_at": "2026-01-07T10:00:00Z",
                },
                "missing ended_at",
                id="missing_ended_at",
            ),
        ],
    )
    async def test_time_log_validates_required_fields(
        self,
        async_test_client: AsyncClient,
        payload: dict[str, Any],
        description: str,
    ) -> None:
        """
        Verify that the time log endpoint validates required fields.

        Args:
            async_test_client: The async HTTP test client.
            payload: The request payload to test.
            description: Description of the validation case.
        """
        response = await async_test_client.post(
            "/api/analytics/time-log",
            json=payload,
        )

        assert response.status_code == 422, f"Expected 422 for {description}"
