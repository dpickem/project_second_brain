"""
Unit tests for hash utilities.
"""

import tempfile
from pathlib import Path

import pytest

from app.pipelines.utils.hash_utils import (
    calculate_file_hash,
    calculate_content_hash,
    calculate_url_hash,
    short_hash,
)


class TestHashUtils:
    """Tests for hash utility functions."""

    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            hash_value = calculate_file_hash(temp_path)

            assert len(hash_value) == 64  # SHA-256
            # Same content should produce same hash
            hash_value2 = calculate_file_hash(temp_path)
            assert hash_value == hash_value2
        finally:
            temp_path.unlink()

    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        hash1 = calculate_content_hash("test")
        hash2 = calculate_content_hash("test")
        hash3 = calculate_content_hash("different")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64

    def test_calculate_url_hash_normalization(self):
        """Test URL hash normalization."""
        # Same URL with different formatting
        hash1 = calculate_url_hash("https://example.com/path/")
        hash2 = calculate_url_hash("https://example.com/path")
        hash3 = calculate_url_hash("HTTPS://EXAMPLE.COM/path")

        # All should produce the same hash
        assert hash1 == hash2
        assert hash1 == hash3

    def test_short_hash(self):
        """Test hash shortening."""
        full_hash = "a" * 64
        short = short_hash(full_hash, length=8)

        assert short == "aaaaaaaa"
        assert len(short) == 8
