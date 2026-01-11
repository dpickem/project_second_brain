"""
OpenAPI Contract Tests

These tests ensure the API contract is stable and changes are intentional.
They serve as a safety net to catch accidental breaking changes.

Contract testing strategy:
1. Snapshot test: Detect any schema changes (parameter names, types, etc.)
2. Structural tests: Verify critical endpoints exist with expected params
3. Breaking change detection: Compare against committed baseline

Run with: pytest tests/unit/test_openapi_contract.py -v
"""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def openapi_schema(client) -> dict[str, Any]:
    """Get the current OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


# =============================================================================
# Schema Structural Tests
# =============================================================================


class TestOpenAPIStructure:
    """Verify the OpenAPI schema structure is correct."""

    def test_schema_has_info(self, openapi_schema):
        """Schema should have info section."""
        assert "info" in openapi_schema
        assert "title" in openapi_schema["info"]
        assert "version" in openapi_schema["info"]

    def test_schema_has_paths(self, openapi_schema):
        """Schema should have paths section."""
        assert "paths" in openapi_schema
        assert len(openapi_schema["paths"]) > 0

    def test_schema_has_components(self, openapi_schema):
        """Schema should have components/schemas for Pydantic models."""
        assert "components" in openapi_schema
        assert "schemas" in openapi_schema["components"]


# =============================================================================
# Critical Endpoint Existence Tests
# =============================================================================


class TestCriticalEndpoints:
    """Verify critical endpoints exist in the schema."""

    CRITICAL_ENDPOINTS = [
        # Health
        ("GET", "/api/health"),
        # Capture
        ("POST", "/api/capture/text"),
        ("POST", "/api/capture/url"),
        ("POST", "/api/capture/photo"),
        ("POST", "/api/capture/voice"),
        ("POST", "/api/capture/pdf"),
        ("POST", "/api/capture/book"),
        # Knowledge
        ("GET", "/api/knowledge/graph"),
        ("GET", "/api/knowledge/stats"),
        ("GET", "/api/knowledge/node/{node_id}"),
        ("POST", "/api/knowledge/search"),
        ("GET", "/api/knowledge/connections/{node_id}"),
        ("GET", "/api/knowledge/topics"),
        # Review (spaced repetition)
        ("GET", "/api/review/due"),
        ("POST", "/api/review/rate"),
        # Practice (sessions, exercises)
        ("POST", "/api/practice/session"),
        # Analytics
        ("GET", "/api/analytics/overview"),
        ("GET", "/api/analytics/time-investment"),
        # Assistant
        ("POST", "/api/assistant/chat"),
        ("GET", "/api/assistant/conversations"),
    ]

    @pytest.mark.parametrize("method,path", CRITICAL_ENDPOINTS)
    def test_endpoint_exists(self, openapi_schema, method, path):
        """Verify critical endpoint exists in schema."""
        paths = openapi_schema.get("paths", {})
        assert path in paths, f"Missing endpoint: {path}"

        endpoint = paths[path]
        method_lower = method.lower()
        assert method_lower in endpoint, f"Missing method {method} on {path}"


# =============================================================================
# Parameter Type Tests
# =============================================================================


class TestParameterTypes:
    """Verify important parameters have correct types."""

    def test_knowledge_search_request_body(self, openapi_schema):
        """Search request should have required fields with correct types."""
        search_schema = openapi_schema["components"]["schemas"].get("SearchRequest")
        assert search_schema is not None, "SearchRequest schema missing"

        properties = search_schema.get("properties", {})

        # query is required string
        assert "query" in properties
        assert properties["query"]["type"] == "string"

        # limit should be integer with bounds
        assert "limit" in properties
        assert properties["limit"]["type"] == "integer"

        # node_types should be array
        assert "node_types" in properties
        assert properties["node_types"]["type"] == "array"

    def test_chat_request_body(self, openapi_schema):
        """Chat request should have message field."""
        chat_schema = openapi_schema["components"]["schemas"].get("ChatRequest")
        assert chat_schema is not None, "ChatRequest schema missing"

        properties = chat_schema.get("properties", {})

        # message is required string
        assert "message" in properties
        assert properties["message"]["type"] == "string"

        # conversation_id is optional
        assert "conversation_id" in properties

    def test_graph_response_structure(self, openapi_schema):
        """Graph response should have nodes and edges."""
        graph_schema = openapi_schema["components"]["schemas"].get("GraphResponse")
        assert graph_schema is not None, "GraphResponse schema missing"

        properties = graph_schema.get("properties", {})

        assert "nodes" in properties
        assert "edges" in properties
        assert "total_nodes" in properties
        assert "total_edges" in properties


# =============================================================================
# Strict Validation Tests
# =============================================================================


class TestStrictValidation:
    """Test that strict request models reject unknown fields."""

    def test_search_request_rejects_unknown_fields(self, client):
        """SearchRequest should reject unknown fields with 422."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "test",
                "unknown_field": "should_fail",  # Extra field
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        # Should mention the extra field
        assert any(
            "unknown_field" in str(err) or "extra" in str(err).lower() for err in detail
        )

    def test_chat_request_rejects_unknown_fields(self, client):
        """ChatRequest should reject unknown fields with 422."""
        response = client.post(
            "/api/assistant/chat",
            json={
                "message": "Hello",
                "typo_field": "should_fail",  # Extra field
            },
        )
        assert response.status_code == 422


# =============================================================================
# Validation Error Format Tests
# =============================================================================


class TestValidationErrors:
    """Test that validation errors are consistent and informative."""

    def test_missing_required_field_error(self, client):
        """Missing required field should return 422 with field name."""
        response = client.post(
            "/api/knowledge/search",
            json={},  # Missing required 'query'
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert len(detail) > 0
        # Should mention 'query' as missing
        assert any("query" in str(err) for err in detail)

    def test_wrong_type_error(self, client):
        """Wrong type should return 422 with type info."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "test",
                "limit": "not_a_number",  # Should be int
            },
        )
        assert response.status_code == 422

    def test_validation_error_format(self, client):
        """Validation errors should have consistent format."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "",  # Too short (min_length=1)
            },
        )
        assert response.status_code == 422
        data = response.json()

        # Should have 'detail' with list of errors
        assert "detail" in data
        assert isinstance(data["detail"], list)

        # Each error should have standard Pydantic fields
        for error in data["detail"]:
            assert "loc" in error  # Location of error
            assert "msg" in error  # Human-readable message
            assert "type" in error  # Error type


# =============================================================================
# Schema Snapshot Test
# =============================================================================


class TestSchemaSnapshot:
    """
    Schema snapshot test for detecting breaking changes.

    This test compares the current schema against a committed baseline.
    If it fails, either:
    1. You made an intentional change → update the snapshot
    2. You made an accidental change → fix the code

    To update the snapshot:
        pytest tests/unit/test_openapi_contract.py -k test_schema_snapshot --snapshot-update

    Or manually:
        curl http://localhost:8000/openapi.json > tests/snapshots/openapi.json
    """

    SNAPSHOT_PATH = Path(__file__).parent.parent / "snapshots" / "openapi.json"

    @pytest.fixture
    def snapshot_schema(self) -> dict[str, Any] | None:
        """Load the committed snapshot schema."""
        if not self.SNAPSHOT_PATH.exists():
            return None
        with open(self.SNAPSHOT_PATH) as f:
            return json.load(f)

    def test_schema_paths_unchanged(self, openapi_schema, snapshot_schema):
        """Endpoint paths should match snapshot."""
        if snapshot_schema is None:
            pytest.skip("No snapshot file - run 'make snapshot' to create")

        current_paths = set(openapi_schema.get("paths", {}).keys())
        snapshot_paths = set(snapshot_schema.get("paths", {}).keys())

        added = current_paths - snapshot_paths
        removed = snapshot_paths - current_paths

        if added:
            pytest.fail(f"New endpoints added (update snapshot): {added}")
        if removed:
            pytest.fail(f"Endpoints removed (breaking change!): {removed}")

    def test_schema_components_unchanged(self, openapi_schema, snapshot_schema):
        """Schema component names should match snapshot."""
        if snapshot_schema is None:
            pytest.skip("No snapshot file - run 'make snapshot' to create")

        current_schemas = set(
            openapi_schema.get("components", {}).get("schemas", {}).keys()
        )
        snapshot_schemas = set(
            snapshot_schema.get("components", {}).get("schemas", {}).keys()
        )

        added = current_schemas - snapshot_schemas
        removed = snapshot_schemas - current_schemas

        if added:
            pytest.fail(f"New schemas added (update snapshot): {added}")
        if removed:
            pytest.fail(f"Schemas removed (breaking change!): {removed}")


# =============================================================================
# Response Model Tests
# =============================================================================


class TestResponseModels:
    """Test that endpoints have response_model set."""

    def test_endpoints_have_response_models(self, openapi_schema):
        """Important endpoints should declare response schemas."""
        paths = openapi_schema.get("paths", {})

        # Endpoints that should have response models
        should_have_response = [
            ("/api/knowledge/graph", "get"),
            ("/api/knowledge/stats", "get"),
            ("/api/knowledge/search", "post"),
            ("/api/assistant/chat", "post"),
            ("/api/assistant/conversations", "get"),
        ]

        for path, method in should_have_response:
            if path not in paths:
                continue

            endpoint = paths[path].get(method, {})
            responses = endpoint.get("responses", {})

            # Should have 200 response
            assert "200" in responses, f"{method.upper()} {path} missing 200 response"

            # 200 response should have content schema
            success = responses["200"]
            if "content" in success:
                content = success["content"]
                assert (
                    "application/json" in content
                ), f"{method.upper()} {path} should return JSON"
