"""
Unit tests for Celery tasks configuration.

Tests the PipelineConfig flags that control learning material generation.
The actual task tests are lightweight to avoid Celery broker connections.
"""

import pytest

from app.services.processing.pipeline import PipelineConfig


# =============================================================================
# Test PipelineConfig Creation
# =============================================================================


class TestPipelineConfig:
    """Tests for PipelineConfig with generate_cards/generate_exercises flags."""

    def test_config_defaults_cards_and_exercises_true(self):
        """Test that PipelineConfig defaults have cards/exercises enabled."""
        config = PipelineConfig()
        assert config.generate_cards is True
        assert config.generate_exercises is True

    def test_config_cards_false(self):
        """Test PipelineConfig with cards disabled."""
        config = PipelineConfig(generate_cards=False, generate_exercises=True)
        assert config.generate_cards is False
        assert config.generate_exercises is True

    def test_config_exercises_false(self):
        """Test PipelineConfig with exercises disabled."""
        config = PipelineConfig(generate_cards=True, generate_exercises=False)
        assert config.generate_cards is True
        assert config.generate_exercises is False

    def test_config_both_disabled(self):
        """Test PipelineConfig with both cards and exercises disabled."""
        config = PipelineConfig(generate_cards=False, generate_exercises=False)
        assert config.generate_cards is False
        assert config.generate_exercises is False

    def test_config_is_dataclass(self):
        """Test that PipelineConfig is a proper dataclass."""
        config = PipelineConfig(generate_cards=True, generate_exercises=False)

        # Should have the expected attributes
        assert hasattr(config, "generate_cards")
        assert hasattr(config, "generate_exercises")


# =============================================================================
# Test process_content Task Signature (without importing Celery)
# =============================================================================


class TestProcessContentTaskSignature:
    """Tests for the process_content task function signature.

    These tests use lazy imports to avoid triggering Celery broker connections
    during test collection.
    """

    def test_process_content_accepts_config_dict(self):
        """Test that process_content task accepts config_dict parameter."""
        import inspect

        # Lazy import to avoid Celery initialization at module level
        from app.services.tasks import process_content

        sig = inspect.signature(process_content)
        params = list(sig.parameters.keys())

        assert "content_id" in params
        assert "config_dict" in params

    def test_process_content_config_dict_default_is_none(self):
        """Test that config_dict defaults to None (uses PipelineConfig defaults)."""
        import inspect
        from app.services.tasks import process_content

        sig = inspect.signature(process_content)

        assert sig.parameters["config_dict"].default is None

    def test_process_content_has_content_id_required(self):
        """Test that content_id is a required parameter."""
        import inspect
        from app.services.tasks import process_content

        sig = inspect.signature(process_content)

        # content_id should have no default (required)
        assert sig.parameters["content_id"].default is inspect.Parameter.empty


# =============================================================================
# Test Capture Router Integration (without Celery)
# =============================================================================


class TestCaptureRouterTaskIntegration:
    """Tests that verify the capture router correctly passes flags to tasks."""

    def test_capture_endpoint_has_create_flags_params(self):
        """Test that capture_text endpoint has create_cards/create_exercises params."""
        import inspect
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)
        params = list(sig.parameters.keys())

        assert "create_cards" in params
        assert "create_exercises" in params

    def test_capture_endpoint_default_flags_are_false(self):
        """Test that default values for create flags are False."""
        import inspect
        from app.routers.capture import capture_text

        sig = inspect.signature(capture_text)

        # FastAPI wraps defaults in Form() objects
        create_cards_default = sig.parameters["create_cards"].default
        create_exercises_default = sig.parameters["create_exercises"].default

        # Extract the actual default value from Form()
        assert create_cards_default.default is False
        assert create_exercises_default.default is False
