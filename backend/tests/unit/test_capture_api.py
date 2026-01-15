"""
Unit tests for the Capture API endpoints.

Tests the text capture endpoint including the create_cards/create_exercises
toggles that control learning material generation.
"""

import inspect
import pytest

from app.enums import ContentType


# =============================================================================
# Test Capture Endpoint Signature
# =============================================================================


class TestCaptureTextEndpointSignature:
    """Tests for the capture_text endpoint function signature."""

    def test_capture_endpoint_accepts_create_cards(self):
        """Test that capture_text endpoint accepts create_cards parameter."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)
        params = list(sig.parameters.keys())

        assert "create_cards" in params

    def test_capture_endpoint_accepts_create_exercises(self):
        """Test that capture_text endpoint accepts create_exercises parameter."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)
        params = list(sig.parameters.keys())

        assert "create_exercises" in params

    def test_capture_endpoint_default_cards_is_false(self):
        """Test that create_cards defaults to False."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)

        # FastAPI wraps defaults in Form() objects
        create_cards_default = sig.parameters["create_cards"].default
        assert create_cards_default.default is False

    def test_capture_endpoint_default_exercises_is_false(self):
        """Test that create_exercises defaults to False."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)

        # FastAPI wraps defaults in Form() objects
        create_exercises_default = sig.parameters["create_exercises"].default
        assert create_exercises_default.default is False

    def test_capture_endpoint_has_content_param(self):
        """Test that capture_text has content as required parameter."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)
        params = list(sig.parameters.keys())

        assert "content" in params

    def test_capture_endpoint_has_background_tasks(self):
        """Test that capture_text has background_tasks parameter for async processing."""
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)
        params = list(sig.parameters.keys())

        assert "background_tasks" in params


# =============================================================================
# Test UnifiedContent Creation
# =============================================================================


class TestUnifiedContentCreation:
    """Tests for UnifiedContent model used in capture."""

    def test_unified_content_accepts_idea_type(self):
        """Test that UnifiedContent can be created with IDEA type."""
        from app.models.content import UnifiedContent

        content = UnifiedContent(
            source_type=ContentType.IDEA,
            title="Test Idea",
            full_text="Test content",
        )

        assert content.source_type == ContentType.IDEA
        assert content.title == "Test Idea"
        assert content.full_text == "Test content"

    def test_unified_content_accepts_tags(self):
        """Test that UnifiedContent can have tags assigned."""
        from app.models.content import UnifiedContent

        content = UnifiedContent(
            source_type=ContentType.IDEA,
            title="Test",
            tags=["tag1", "tag2"],
        )

        assert content.tags == ["tag1", "tag2"]

    def test_unified_content_id_generated(self):
        """Test that UnifiedContent generates an ID if not provided."""
        from app.models.content import UnifiedContent

        content = UnifiedContent(
            source_type=ContentType.IDEA,
            title="Test",
        )

        # Should have an ID generated
        assert content.id is not None
        assert len(content.id) > 0


# =============================================================================
# Test Title Generation Helper
# =============================================================================


class TestTitleGeneration:
    """Tests for title generation from content."""

    def test_title_generation_function_exists(self):
        """Test that _generate_title helper function exists."""
        from app.routers.capture import _generate_title

        assert callable(_generate_title)

    def test_generate_title_short_content(self):
        """Test title generation for short content."""
        from app.routers.capture import _generate_title

        result = _generate_title("Short note")
        assert result == "Short note"

    def test_generate_title_long_content_truncates(self):
        """Test title generation truncates long content."""
        from app.routers.capture import _generate_title

        long_content = "A" * 200
        result = _generate_title(long_content)

        # Should truncate to max 100 chars (97 + "...")
        assert len(result) <= 100
        assert len(result) < len(long_content)

    def test_generate_title_with_newlines_uses_first_line(self):
        """Test title generation uses first line when content has newlines."""
        from app.routers.capture import _generate_title

        result = _generate_title("First line\nSecond line\nThird line")
        assert result == "First line"

    def test_generate_title_strips_whitespace(self):
        """Test title generation strips leading/trailing whitespace."""
        from app.routers.capture import _generate_title

        result = _generate_title("  Padded content  ")
        assert result == "Padded content"

    def test_generate_title_empty_first_line_uses_next(self):
        """Test title generation skips empty first line."""
        from app.routers.capture import _generate_title

        result = _generate_title("\n\nActual content")
        assert "Actual content" in result


# =============================================================================
# Test Router Registration
# =============================================================================


class TestCaptureRouterRegistration:
    """Tests that capture router is properly configured."""

    def test_capture_router_has_text_endpoint(self):
        """Test that capture router has /text endpoint."""
        from app.routers.capture import router

        routes = [r.path for r in router.routes]
        # Routes include the router prefix
        assert any("/text" in route for route in routes)

    def test_capture_text_is_post_method(self):
        """Test that capture_text uses POST method."""
        from app.routers.capture import router

        for route in router.routes:
            if "/text" in route.path:
                assert "POST" in route.methods
                break
        else:
            pytest.fail("/text route not found")
