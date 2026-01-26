"""
API Contract Integration Tests

These tests verify the API contract between backend and frontend is solid.
They focus on common mismatch patterns:
- Wrong field names (typos)
- Wrong HTTP methods
- Wrong parameter types
- Missing required fields
- Query vs body parameter confusion

Run with: pytest tests/integration/test_api_contract.py -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


# =============================================================================
# Knowledge API Contract Tests
# =============================================================================


class TestKnowledgeAPIContract:
    """Test knowledge API endpoint contract."""

    def test_graph_endpoint_accepts_valid_params(self, client):
        """GET /api/knowledge/graph should accept valid query params."""
        response = client.get(
            "/api/knowledge/graph",
            params={
                "limit": 50,
                "depth": 2,
                "node_types": "Content,Concept",
            },
        )
        # Should not fail validation (may fail for other reasons like DB)
        assert response.status_code != 422

    def test_graph_endpoint_rejects_invalid_limit_type(self, client):
        """GET /api/knowledge/graph should reject non-integer limit."""
        response = client.get(
            "/api/knowledge/graph",
            params={"limit": "not_a_number"},
        )
        assert response.status_code == 422

    def test_graph_endpoint_rejects_out_of_range_limit(self, client):
        """GET /api/knowledge/graph should reject limit > max (500)."""
        response = client.get(
            "/api/knowledge/graph",
            params={"limit": 1000},  # Max is 500
        )
        assert response.status_code == 422

    def test_search_endpoint_requires_query(self, client):
        """POST /api/knowledge/search requires query field."""
        response = client.post(
            "/api/knowledge/search",
            json={},  # Missing 'query'
        )
        assert response.status_code == 422
        # Error should mention 'query'
        detail = response.json()["detail"]
        assert any("query" in str(e).lower() for e in detail)

    def test_search_endpoint_accepts_valid_body(self, client):
        """POST /api/knowledge/search should accept valid body."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "transformers",
                "limit": 10,
                "node_types": ["Content", "Concept"],
                "min_score": 0.5,
                "use_vector": True,
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_search_endpoint_rejects_wrong_field_name(self, client):
        """POST /api/knowledge/search should reject typos in field names."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "test",
                "maxResults": 10,  # Wrong! Should be 'limit'
            },
        )
        assert response.status_code == 422

    def test_search_endpoint_rejects_extra_fields(self, client):
        """POST /api/knowledge/search should reject unknown fields."""
        response = client.post(
            "/api/knowledge/search",
            json={
                "query": "test",
                "foo": "bar",  # Unknown field
            },
        )
        assert response.status_code == 422

    def test_node_endpoint_requires_path_param(self, client):
        """GET /api/knowledge/node/{node_id} requires node_id in path."""
        # Missing node_id should 404 (path not found)
        response = client.get("/api/knowledge/node/")
        assert response.status_code in [404, 405]

    def test_connections_direction_enum(self, client):
        """GET /api/knowledge/connections/{node_id} validates direction."""
        response = client.get(
            "/api/knowledge/connections/test-id",
            params={"direction": "invalid_direction"},
        )
        assert response.status_code == 422


# =============================================================================
# Capture API Contract Tests
# =============================================================================


class TestCaptureAPIContract:
    """Test capture API endpoint contract."""

    @pytest.fixture
    def capture_client(self):
        """
        Test client with capture API authentication bypassed.
        
        The capture endpoints require API key auth, but these contract tests
        focus on request/response validation, not authentication.
        """
        from app.dependencies import verify_capture_api_key
        
        # Override the auth dependency to always return a valid key
        app.dependency_overrides[verify_capture_api_key] = lambda: "test-key"
        client = TestClient(app)
        yield client
        # Clean up the override after the test
        app.dependency_overrides.pop(verify_capture_api_key, None)

    def test_text_capture_requires_content(self, capture_client):
        """POST /api/capture/text requires content field."""
        response = capture_client.post(
            "/api/capture/text",
            data={},  # Missing 'content'
        )
        assert response.status_code == 422

    def test_text_capture_accepts_valid_form(self, capture_client):
        """POST /api/capture/text should accept valid form data."""
        response = capture_client.post(
            "/api/capture/text",
            data={
                "content": "Test idea content",
                "title": "Test Title",
                "tags": "test,idea",
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_url_capture_validates_url_format(self, capture_client):
        """POST /api/capture/url should validate URL format."""
        response = capture_client.post(
            "/api/capture/url",
            data={"url": "not_a_valid_url"},  # Missing http://
        )
        assert response.status_code == 400

    def test_url_capture_accepts_valid_url(self, capture_client):
        """POST /api/capture/url should accept valid URLs."""
        response = capture_client.post(
            "/api/capture/url",
            data={
                "url": "https://example.com/article",
                "notes": "Interesting article",
                "tags": "article,test",
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_photo_endpoint_is_post(self, capture_client):
        """Photo capture must be POST, not GET."""
        response = capture_client.get("/api/capture/photo")
        assert response.status_code == 405  # Method Not Allowed


# =============================================================================
# Assistant API Contract Tests
# =============================================================================


class TestAssistantAPIContract:
    """Test assistant API endpoint contract."""

    def test_chat_requires_message(self, client):
        """POST /api/assistant/chat requires message field."""
        response = client.post(
            "/api/assistant/chat",
            json={},  # Missing 'message'
        )
        assert response.status_code == 422

    def test_chat_accepts_valid_body(self, client):
        """POST /api/assistant/chat should accept valid body."""
        response = client.post(
            "/api/assistant/chat",
            json={
                "message": "Hello, assistant!",
                "conversation_id": None,
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_chat_rejects_wrong_field_name(self, client):
        """POST /api/assistant/chat should reject typos."""
        response = client.post(
            "/api/assistant/chat",
            json={
                "msg": "Hello",  # Wrong! Should be 'message'
            },
        )
        assert response.status_code == 422

    def test_chat_message_length_validation(self, client):
        """POST /api/assistant/chat validates message length."""
        # Empty message should fail (min_length=1)
        response = client.post(
            "/api/assistant/chat",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_conversation_update_requires_title(self, client):
        """PATCH /api/assistant/conversations/{id} requires title."""
        response = client.patch(
            "/api/assistant/conversations/test-id",
            json={},  # Missing 'title'
        )
        assert response.status_code == 422


# =============================================================================
# Practice API Contract Tests
# =============================================================================


class TestPracticeAPIContract:
    """Test practice API endpoint contract."""

    def test_review_requires_card_id_and_rating(self, client):
        """POST /api/review/rate requires card_id and rating."""
        # Missing both
        response = client.post(
            "/api/review/rate",
            json={},
        )
        assert response.status_code == 422

        # Missing rating
        response = client.post(
            "/api/review/rate",
            json={"card_id": 1},
        )
        assert response.status_code == 422

    def test_review_validates_rating_range(self, client):
        """POST /api/review/rate validates rating is 1-4."""
        response = client.post(
            "/api/review/rate",
            json={"card_id": 1, "rating": 5},  # Rating must be 1-4
        )
        assert response.status_code == 422

    def test_session_create_accepts_valid_body(self, client):
        """POST /api/practice/session should accept valid body."""
        response = client.post(
            "/api/practice/session",
            json={
                "duration_minutes": 15,
                "topic_filter": None,
                "session_type": "practice",
                "exercise_source": "prefer_existing",
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_session_create_validates_duration(self, client):
        """POST /api/practice/session validates duration bounds."""
        # Too short (min is 5)
        response = client.post(
            "/api/practice/session",
            json={"duration_minutes": 2},
        )
        assert response.status_code == 422

        # Too long (max is 120)
        response = client.post(
            "/api/practice/session",
            json={"duration_minutes": 200},
        )
        assert response.status_code == 422


# =============================================================================
# HTTP Method Tests
# =============================================================================


class TestHTTPMethods:
    """Test that endpoints only accept correct HTTP methods."""

    def test_search_is_post_not_get(self, client):
        """Search endpoint is POST, not GET."""
        response = client.get(
            "/api/knowledge/search",
            params={"query": "test"},
        )
        assert response.status_code == 405

    def test_chat_is_post_not_get(self, client):
        """Chat endpoint is POST, not GET."""
        response = client.get("/api/assistant/chat")
        assert response.status_code == 405

    def test_graph_is_get_not_post(self, client):
        """Graph endpoint is GET, not POST."""
        response = client.post("/api/knowledge/graph")
        assert response.status_code == 405


# =============================================================================
# Query vs Body Parameter Tests
# =============================================================================


class TestQueryVsBody:
    """Test that parameters are in the right place (query vs body)."""

    def test_search_params_in_body_not_query(self, client):
        """Search parameters must be in request body, not query string."""
        # Putting search params in query string should fail
        response = client.post(
            "/api/knowledge/search",
            params={"query": "test", "limit": 10},  # Wrong place!
        )
        # Should fail because body is missing required field
        assert response.status_code == 422

    def test_graph_params_in_query_not_body(self, client):
        """Graph parameters must be in query string, not body."""
        # GET requests with query params should work correctly
        response = client.get(
            "/api/knowledge/graph",
            params={"limit": 10},  # Correct place for GET params
        )
        # Should work (may fail for other reasons like DB connection)
        assert response.status_code != 422


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestResponseStructure:
    """Test that responses have expected structure."""

    def test_validation_error_has_detail(self, client):
        """Validation errors should have 'detail' array."""
        response = client.post(
            "/api/knowledge/search",
            json={},  # Missing required field
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    def test_validation_error_detail_structure(self, client):
        """Each validation error should have loc, msg, type."""
        response = client.post(
            "/api/knowledge/search",
            json={},
        )
        data = response.json()

        for error in data["detail"]:
            assert "loc" in error, "Error should have 'loc' (location)"
            assert "msg" in error, "Error should have 'msg' (message)"
            assert "type" in error, "Error should have 'type'"
