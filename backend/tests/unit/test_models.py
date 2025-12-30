"""
Unit tests for Pydantic models.

Tests the UnifiedContent, Annotation, and related models
for proper validation and serialization.
"""

from datetime import datetime
import pytest
import uuid

from app.models.content import (
    ContentType,
    AnnotationType,
    Annotation,
    UnifiedContent,
    ProcessingStatus,
    ContentBatch,
)


class TestAnnotation:
    """Tests for the Annotation model."""

    def test_annotation_with_required_fields(self):
        """Test creating annotation with only required fields."""
        annot = Annotation(
            type=AnnotationType.DIGITAL_HIGHLIGHT,
            content="Test highlight",
        )

        assert annot.type == AnnotationType.DIGITAL_HIGHLIGHT
        assert annot.content == "Test highlight"
        assert annot.id is not None  # Auto-generated
        assert annot.page_number is None
        assert annot.confidence is None

    def test_annotation_with_all_fields(self):
        """Test creating annotation with all fields."""
        annot = Annotation(
            id="test-id",
            type=AnnotationType.HANDWRITTEN_NOTE,
            content="Margin note",
            page_number=42,
            position={"location": "right-margin"},
            context="Nearby printed text",
            confidence=0.95,
        )

        assert annot.id == "test-id"
        assert annot.type == AnnotationType.HANDWRITTEN_NOTE
        assert annot.content == "Margin note"
        assert annot.page_number == 42
        assert annot.position["location"] == "right-margin"
        assert annot.context == "Nearby printed text"
        assert annot.confidence == 0.95

    def test_annotation_confidence_bounds(self):
        """Test that confidence must be between 0 and 1."""
        # Valid confidence
        annot = Annotation(
            type=AnnotationType.DIGITAL_HIGHLIGHT,
            content="Test",
            confidence=0.5,
        )
        assert annot.confidence == 0.5

        # Boundary values
        annot_zero = Annotation(
            type=AnnotationType.DIGITAL_HIGHLIGHT,
            content="Test",
            confidence=0.0,
        )
        assert annot_zero.confidence == 0.0

        annot_one = Annotation(
            type=AnnotationType.DIGITAL_HIGHLIGHT,
            content="Test",
            confidence=1.0,
        )
        assert annot_one.confidence == 1.0

    def test_annotation_types(self):
        """Test all annotation types can be created."""
        for annot_type in AnnotationType:
            annot = Annotation(
                type=annot_type,
                content=f"Test {annot_type.value}",
            )
            assert annot.type == annot_type


class TestUnifiedContent:
    """Tests for the UnifiedContent model."""

    def test_unified_content_minimal(self):
        """Test creating content with minimal required fields."""
        content = UnifiedContent(
            source_type=ContentType.IDEA,
            title="Test idea",
        )

        assert content.source_type == ContentType.IDEA
        assert content.title == "Test idea"
        assert content.id is not None
        assert content.full_text == ""
        assert content.annotations == []
        assert content.processing_status == ProcessingStatus.PENDING

    def test_unified_content_full(self):
        """Test creating content with all fields."""
        created = datetime(2025, 1, 1, 12, 0, 0)

        content = UnifiedContent(
            id="test-content-id",
            source_type=ContentType.PAPER,
            source_url="https://arxiv.org/abs/1234.5678",
            source_file_path="/path/to/paper.pdf",
            title="Test Paper",
            authors=["Alice", "Bob"],
            created_at=created,
            full_text="Abstract: This is a test paper...",
            annotations=[
                Annotation(
                    type=AnnotationType.DIGITAL_HIGHLIGHT,
                    content="Important finding",
                )
            ],
            raw_file_hash="abc123",
            asset_paths=["/path/to/paper.pdf"],
            processing_status=ProcessingStatus.COMPLETED,
            obsidian_path="sources/papers/test-paper.md",
            tags=["ml", "transformers"],
            metadata={"doi": "10.1234/test"},
        )

        assert content.id == "test-content-id"
        assert content.source_type == ContentType.PAPER
        assert content.source_url == "https://arxiv.org/abs/1234.5678"
        assert len(content.authors) == 2
        assert len(content.annotations) == 1
        assert content.processing_status == ProcessingStatus.COMPLETED
        assert "ml" in content.tags

    def test_content_types(self):
        """Test all content types can be used."""
        for content_type in ContentType:
            content = UnifiedContent(
                source_type=content_type,
                title=f"Test {content_type.value}",
            )
            assert content.source_type == content_type

    def test_content_serialization(self):
        """Test content can be serialized to JSON."""
        content = UnifiedContent(
            source_type=ContentType.ARTICLE,
            title="Test article",
            full_text="Article content...",
        )

        json_data = content.model_dump_json()
        assert "Test article" in json_data
        assert "article" in json_data

    def test_content_with_annotations(self):
        """Test content with multiple annotations."""
        content = UnifiedContent(
            source_type=ContentType.BOOK,
            title="Test book",
            annotations=[
                Annotation(
                    type=AnnotationType.DIGITAL_HIGHLIGHT,
                    content="Highlight 1",
                    page_number=10,
                ),
                Annotation(
                    type=AnnotationType.HANDWRITTEN_NOTE,
                    content="Note 1",
                    page_number=10,
                    context="Near highlight",
                ),
                Annotation(
                    type=AnnotationType.TYPED_COMMENT,
                    content="Comment 1",
                ),
            ],
        )

        assert len(content.annotations) == 3
        assert content.annotations[0].type == AnnotationType.DIGITAL_HIGHLIGHT
        assert content.annotations[1].type == AnnotationType.HANDWRITTEN_NOTE
        assert content.annotations[2].type == AnnotationType.TYPED_COMMENT


class TestContentBatch:
    """Tests for the ContentBatch model."""

    def test_content_batch(self):
        """Test creating a batch of content items."""
        items = [
            UnifiedContent(
                source_type=ContentType.IDEA,
                title=f"Idea {i}",
            )
            for i in range(3)
        ]

        batch = ContentBatch(items=items)

        assert len(batch.items) == 3
        assert batch.batch_id is not None
        assert batch.created_at is not None

    def test_empty_batch(self):
        """Test creating an empty batch."""
        batch = ContentBatch(items=[])

        assert len(batch.items) == 0
        assert batch.batch_id is not None
