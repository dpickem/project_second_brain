"""
Unit tests for LLM cost tracking types.
"""

from unittest.mock import MagicMock

import pytest

from app.pipelines.utils.cost_types import (
    LLMUsage,
    extract_provider,
    extract_usage_from_response,
    create_error_usage,
)


class TestLLMUsage:
    """Tests for the LLMUsage dataclass."""

    def test_request_id_auto_generated(self):
        """Test that request_id is auto-generated as UUID."""
        usage1 = LLMUsage()
        usage2 = LLMUsage()

        # Each instance should have a unique request_id
        assert usage1.request_id != usage2.request_id
        # Should be a valid UUID format (36 chars with hyphens)
        assert len(usage1.request_id) == 36
        assert usage1.request_id.count("-") == 4

    def test_to_dict(self):
        """Test conversion to dictionary."""
        usage = LLMUsage(
            model="mistral/mistral-ocr-latest",
            provider="mistral",
            request_type="vision",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.0025,
        )

        result = usage.to_dict()

        assert isinstance(result, dict)
        assert result["model"] == "mistral/mistral-ocr-latest"
        assert result["provider"] == "mistral"
        assert result["request_type"] == "vision"
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["cost_usd"] == 0.0025

    def test_total_cost_property(self):
        """Test total_cost property."""
        # With cost set
        usage_with_cost = LLMUsage(cost_usd=0.05)
        assert usage_with_cost.total_cost == 0.05

        # Without cost (should default to 0)
        usage_no_cost = LLMUsage()
        assert usage_no_cost.total_cost == 0.0

    def test_str_representation_with_cost(self):
        """Test string representation with cost and tokens."""
        usage = LLMUsage(
            model="openai/gpt-4",
            request_type="text",
            cost_usd=0.0123,
            total_tokens=500,
        )

        result = str(usage)

        assert "openai/gpt-4" in result
        assert "text" in result
        assert "$0.0123" in result
        assert "500" in result

    def test_str_representation_without_cost(self):
        """Test string representation without cost/tokens."""
        usage = LLMUsage(
            model="unknown-model",
            request_type="vision",
        )

        result = str(usage)

        assert "unknown-model" in result
        assert "N/A" in result


class TestExtractProvider:
    """Tests for the extract_provider function."""

    def test_extract_provider_with_slash(self):
        """Test extracting provider from model with slash."""
        assert extract_provider("mistral/mistral-ocr-latest") == "mistral"
        assert extract_provider("openai/gpt-4") == "openai"
        assert extract_provider("anthropic/claude-3") == "anthropic"

    def test_extract_provider_without_slash(self):
        """Test extracting provider when no slash present."""
        assert extract_provider("gpt-4") == "unknown"
        assert extract_provider("claude-3") == "unknown"

    def test_extract_provider_multiple_slashes(self):
        """Test extracting provider with multiple slashes."""
        assert extract_provider("provider/model/variant") == "provider"


class TestExtractUsageFromResponse:
    """Tests for extract_usage_from_response function."""

    def test_extract_basic_usage(self):
        """Test extracting basic usage info."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response._hidden_params = None

        usage = extract_usage_from_response(
            response=mock_response,
            model="mistral/mistral-ocr-latest",
            request_type="vision",
            latency_ms=1234,
            pipeline="book_ocr",
            operation="page_extraction",
        )

        assert usage.model == "mistral/mistral-ocr-latest"
        assert usage.provider == "mistral"
        assert usage.request_type == "vision"
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.latency_ms == 1234
        assert usage.pipeline == "book_ocr"
        assert usage.operation == "page_extraction"
        assert usage.success is True

    def test_extract_usage_with_hidden_cost(self):
        """Test extracting cost from hidden params."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response._hidden_params = {
            "response_cost": 0.005,
            "additional_args": {
                "input_cost": 0.002,
                "output_cost": 0.003,
            },
        }

        usage = extract_usage_from_response(
            response=mock_response,
            model="openai/gpt-4",
            request_type="text",
            latency_ms=500,
        )

        assert usage.cost_usd == 0.005
        assert usage.input_cost_usd == 0.002
        assert usage.output_cost_usd == 0.003

    def test_extract_usage_no_usage_object(self):
        """Test handling response without usage object."""
        mock_response = MagicMock()
        mock_response.usage = None
        mock_response._hidden_params = None

        usage = extract_usage_from_response(
            response=mock_response,
            model="test/model",
            request_type="text",
            latency_ms=100,
        )

        assert usage.prompt_tokens is None
        assert usage.completion_tokens is None
        assert usage.total_tokens is None

    def test_extract_usage_with_content_id(self):
        """Test extracting usage with content attribution."""
        mock_response = MagicMock()
        mock_response.usage = None
        mock_response._hidden_params = None

        usage = extract_usage_from_response(
            response=mock_response,
            model="test/model",
            request_type="vision",
            latency_ms=200,
            pipeline="pdf_processor",
            content_id=42,
            operation="text_extraction",
        )

        assert usage.pipeline == "pdf_processor"
        assert usage.content_id == 42
        assert usage.operation == "text_extraction"


class TestCreateErrorUsage:
    """Tests for create_error_usage function."""

    def test_create_error_usage_basic(self):
        """Test creating error usage record."""
        usage = create_error_usage(
            model="mistral/mistral-ocr-latest",
            request_type="vision",
            latency_ms=500,
            error_message="API rate limit exceeded",
        )

        assert usage.model == "mistral/mistral-ocr-latest"
        assert usage.provider == "mistral"
        assert usage.request_type == "vision"
        assert usage.latency_ms == 500
        assert usage.success is False
        assert usage.error_message == "API rate limit exceeded"
        # Tokens and cost should be None for errors
        assert usage.prompt_tokens is None
        assert usage.cost_usd is None

    def test_create_error_usage_with_context(self):
        """Test creating error usage with pipeline context."""
        usage = create_error_usage(
            model="openai/gpt-4",
            request_type="text",
            latency_ms=1000,
            error_message="Connection timeout",
            pipeline="raindrop_sync",
            content_id=123,
            operation="summarization",
        )

        assert usage.pipeline == "raindrop_sync"
        assert usage.content_id == 123
        assert usage.operation == "summarization"
        assert usage.success is False
