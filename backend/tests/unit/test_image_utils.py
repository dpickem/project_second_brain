"""
Unit tests for image utilities.
"""

import base64
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.pipelines.utils.image_utils import (
    image_to_base64,
    preprocess_for_ocr,
    resize_for_api,
    get_image_dimensions,
)


class TestImageUtils:
    """Tests for image utility functions."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        img = Image.new("RGB", (100, 100), color="red")
        return img

    @pytest.fixture
    def sample_image_file(self, sample_image):
        """Create a sample image file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            sample_image.save(f, format="PNG")
            return Path(f.name)

    def test_image_to_base64(self, sample_image):
        """Test converting image to base64."""
        b64 = image_to_base64(sample_image)

        # Should be valid base64
        assert isinstance(b64, str)
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    def test_image_to_base64_from_path(self, sample_image_file):
        """Test converting image file to base64."""
        try:
            b64 = image_to_base64(sample_image_file)
            assert isinstance(b64, str)
            assert len(b64) > 0
        finally:
            sample_image_file.unlink()

    def test_preprocess_for_ocr(self, sample_image):
        """Test image preprocessing for OCR."""
        processed = preprocess_for_ocr(sample_image)

        assert isinstance(processed, Image.Image)
        assert processed.mode == "RGB"

    def test_resize_for_api_no_resize_needed(self, sample_image):
        """Test that small images aren't resized."""
        resized = resize_for_api(sample_image, max_dimension=500)

        assert resized.size == (100, 100)

    def test_resize_for_api_resize_needed(self):
        """Test that large images are resized."""
        large_img = Image.new("RGB", (4000, 3000), color="blue")
        resized = resize_for_api(large_img, max_dimension=2048)

        assert max(resized.size) <= 2048
        # Aspect ratio preserved
        assert resized.size[0] == 2048 or resized.size[1] == 2048

    def test_get_image_dimensions(self, sample_image):
        """Test getting image dimensions."""
        width, height = get_image_dimensions(sample_image)

        assert width == 100
        assert height == 100
