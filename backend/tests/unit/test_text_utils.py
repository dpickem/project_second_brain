"""
Unit tests for text utilities.
"""

import pytest

from app.pipelines.utils.text_utils import (
    clean_text,
    extract_json_from_response,
    normalize_llm_json_response,
    unwrap_llm_single_object_response,
    truncate_text,
    extract_title_from_text,
    split_into_chunks,
)


class TestTextUtils:
    """Tests for text utility functions."""

    def test_clean_text_whitespace(self):
        """Test cleaning excessive whitespace."""
        dirty = "Hello    world\n\n\n\ntest"
        clean = clean_text(dirty)

        assert "    " not in clean
        assert "\n\n\n" not in clean
        assert "Hello" in clean
        assert "world" in clean

    def test_clean_text_null_chars(self):
        """Test removing null characters."""
        dirty = "Hello\x00World"
        clean = clean_text(dirty)

        assert "\x00" not in clean
        assert "HelloWorld" in clean

    def test_extract_json_raw(self):
        """Test extracting raw JSON."""
        response = '{"key": "value"}'
        result = extract_json_from_response(response)

        assert result == {"key": "value"}

    def test_extract_json_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        response = """Here is the result:
```json
{"page_number": 42, "text": "Hello"}
```
"""
        result = extract_json_from_response(response)

        assert result["page_number"] == 42
        assert result["text"] == "Hello"

    def test_extract_json_array(self):
        """Test extracting JSON array."""
        response = """
```json
[{"item": 1}, {"item": 2}]
```
"""
        result = extract_json_from_response(response)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_extract_json_invalid(self):
        """Test handling invalid JSON."""
        response = "This is not JSON at all"
        result = extract_json_from_response(response)

        assert result is None

    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long sentence that needs to be truncated"
        truncated = truncate_text(text, max_length=20)

        assert len(truncated) <= 20
        assert truncated.endswith("...")

    def test_truncate_text_no_truncation(self):
        """Test that short text isn't truncated."""
        text = "Short"
        truncated = truncate_text(text, max_length=100)

        assert truncated == "Short"

    def test_extract_title_from_text(self):
        """Test title extraction."""
        text = "# Main Title\n\nSome content here..."
        title = extract_title_from_text(text)

        assert title == "Main Title"

    def test_extract_title_plain_text(self):
        """Test title extraction from plain text."""
        text = "First line is the title\nSecond line is content"
        title = extract_title_from_text(text)

        assert title == "First line is the title"

    def test_split_into_chunks(self):
        """Test splitting text into chunks."""
        text = "A" * 10000  # 10k characters
        chunks = split_into_chunks(text, chunk_size=4000, chunk_overlap=200)

        assert len(chunks) > 1
        # Each chunk should be around the target size
        for chunk in chunks:
            assert len(chunk) <= 4000 + 200  # Allow for overlap

    def test_normalize_llm_json_response_dict(self):
        """Test normalizing a dict response (pass-through)."""
        data = {"concepts": [{"name": "foo"}]}
        result = normalize_llm_json_response(data, "concepts")

        assert result == data

    def test_normalize_llm_json_response_list(self):
        """Test normalizing a list response into a dict."""
        data = [{"name": "foo"}, {"name": "bar"}]
        result = normalize_llm_json_response(data, "concepts")

        assert result == {"concepts": [{"name": "foo"}, {"name": "bar"}]}

    def test_normalize_llm_json_response_empty_list(self):
        """Test normalizing an empty list."""
        data = []
        result = normalize_llm_json_response(data, "questions")

        assert result == {"questions": []}

    def test_normalize_llm_json_response_invalid_type(self):
        """Test handling invalid types."""
        result = normalize_llm_json_response("string", "concepts")
        assert result == {}

        result = normalize_llm_json_response(None, "concepts")
        assert result == {}

        result = normalize_llm_json_response(123, "concepts")
        assert result == {}

    def test_unwrap_llm_single_object_response_dict(self):
        """Test unwrapping a dict response (pass-through)."""
        data = {"content_type": "paper", "domain": "ml"}
        result = unwrap_llm_single_object_response(data)

        assert result == data

    def test_unwrap_llm_single_object_response_list(self):
        """Test unwrapping a list with one item."""
        data = [{"content_type": "paper", "domain": "ml"}]
        result = unwrap_llm_single_object_response(data)

        assert result == {"content_type": "paper", "domain": "ml"}

    def test_unwrap_llm_single_object_response_empty_list(self):
        """Test handling an empty list."""
        result = unwrap_llm_single_object_response([])
        assert result == {}

    def test_unwrap_llm_single_object_response_invalid_type(self):
        """Test handling invalid types."""
        assert unwrap_llm_single_object_response("string") == {}
        assert unwrap_llm_single_object_response(None) == {}
        assert unwrap_llm_single_object_response(123) == {}
        assert unwrap_llm_single_object_response(["not", "a", "dict"]) == {}
