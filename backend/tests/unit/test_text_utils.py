"""
Unit tests for text utilities.
"""

import pytest

from app.pipelines.utils.text_utils import (
    clean_text,
    extract_json_from_response,
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
