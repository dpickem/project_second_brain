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
            processing_status=ProcessingStatus.PROCESSED,
            obsidian_path="sources/papers/test-paper.md",
            tags=["ml", "transformers"],
            metadata={"doi": "10.1234/test"},
        )

        assert content.id == "test-content-id"
        assert content.source_type == ContentType.PAPER
        assert content.source_url == "https://arxiv.org/abs/1234.5678"
        assert len(content.authors) == 2
        assert len(content.annotations) == 1
        assert content.processing_status == ProcessingStatus.PROCESSED
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


class TestUnifiedContentFromDBContent:
    """Tests for UnifiedContent.from_db_content with annotations."""

    def _make_mock_db_content(
        self,
        content_uuid: str = "test-uuid-123",
        title: str = "Test Content",
        content_type: str = "paper",
        annotations: list = None,
    ):
        """Create a mock DB content object for testing."""
        from unittest.mock import MagicMock
        
        mock = MagicMock()
        mock.content_uuid = content_uuid
        mock.title = title
        mock.content_type = content_type
        mock.source_url = "https://example.com"
        mock.source_path = "/path/to/file.pdf"
        mock.raw_text = "Test content text"
        mock.metadata_json = {"authors": ["Author One"]}
        mock.annotations = annotations or []
        return mock

    def _make_mock_db_annotation(
        self,
        annotation_id: int = 1,
        annotation_type: str = "DIGITAL_HIGHLIGHT",
        text: str = "Highlighted text",
        page_number: int = 1,
        context: str = None,
        ocr_confidence: float = None,
    ):
        """Create a mock DB annotation object for testing."""
        from unittest.mock import MagicMock
        
        mock = MagicMock()
        mock.id = annotation_id
        mock.annotation_type = annotation_type
        mock.text = text
        mock.page_number = page_number
        mock.context = context
        mock.ocr_confidence = ocr_confidence
        return mock

    def test_from_db_content_basic(self):
        """Test basic conversion from DB content without annotations."""
        mock_db = self._make_mock_db_content()
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert content.id == "test-uuid-123"
        assert content.title == "Test Content"
        assert content.source_type == ContentType.PAPER
        assert len(content.annotations) == 0

    def test_from_db_content_with_single_annotation(self):
        """Test conversion with a single digital highlight annotation."""
        mock_annot = self._make_mock_db_annotation(
            annotation_id=1,
            annotation_type="DIGITAL_HIGHLIGHT",
            text="Important finding",
            page_number=5,
        )
        mock_db = self._make_mock_db_content(annotations=[mock_annot])
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 1
        assert content.annotations[0].type == AnnotationType.DIGITAL_HIGHLIGHT
        assert content.annotations[0].content == "Important finding"
        assert content.annotations[0].page_number == 5
        assert content.annotations[0].id == "1"

    def test_from_db_content_with_multiple_annotations(self):
        """Test conversion with multiple annotations of different types."""
        mock_annots = [
            self._make_mock_db_annotation(
                annotation_id=1,
                annotation_type="DIGITAL_HIGHLIGHT",
                text="Highlight 1",
                page_number=1,
            ),
            self._make_mock_db_annotation(
                annotation_id=2,
                annotation_type="HANDWRITTEN_NOTE",
                text="Note 1",
                page_number=2,
                context="Near figure 3",
            ),
            self._make_mock_db_annotation(
                annotation_id=3,
                annotation_type="DIAGRAM",
                text="Figure description",
                page_number=3,
            ),
        ]
        mock_db = self._make_mock_db_content(annotations=mock_annots)
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 3
        
        # Check types are correctly mapped
        types = [a.type for a in content.annotations]
        assert AnnotationType.DIGITAL_HIGHLIGHT in types
        assert AnnotationType.HANDWRITTEN_NOTE in types
        assert AnnotationType.DIAGRAM in types
        
        # Check context is preserved for handwritten notes
        note = next(a for a in content.annotations if a.type == AnnotationType.HANDWRITTEN_NOTE)
        assert note.context == "Near figure 3"

    def test_from_db_content_preserves_ocr_confidence(self):
        """Test that OCR confidence is preserved for annotations."""
        mock_annot = self._make_mock_db_annotation(
            annotation_type="HANDWRITTEN_NOTE",
            text="Handwritten text",
            ocr_confidence=0.85,
        )
        mock_db = self._make_mock_db_content(annotations=[mock_annot])
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert content.annotations[0].confidence == 0.85

    def test_from_db_content_handles_none_annotations(self):
        """Test graceful handling when annotations attribute is None."""
        mock_db = self._make_mock_db_content()
        mock_db.annotations = None
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 0

    def test_from_db_content_handles_empty_text(self):
        """Test handling of annotations with empty text."""
        mock_annot = self._make_mock_db_annotation(
            text="",  # Empty text
        )
        mock_db = self._make_mock_db_content(annotations=[mock_annot])
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 1
        assert content.annotations[0].content == ""

    def test_from_db_content_annotation_type_case_insensitive(self):
        """Test that annotation type conversion handles case variations."""
        # DB stores uppercase by convention
        mock_annot = self._make_mock_db_annotation(
            annotation_type="digital_highlight",  # lowercase
        )
        mock_db = self._make_mock_db_content(annotations=[mock_annot])
        
        content = UnifiedContent.from_db_content(mock_db)
        
        # Should still map correctly (converts to uppercase)
        assert content.annotations[0].type == AnnotationType.DIGITAL_HIGHLIGHT

    def test_from_db_content_preserves_authors_from_metadata(self):
        """Test that authors are extracted from metadata_json."""
        mock_db = self._make_mock_db_content()
        mock_db.metadata_json = {"authors": ["Alice", "Bob", "Charlie"]}
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert content.authors == ["Alice", "Bob", "Charlie"]

    def test_from_db_content_handles_missing_metadata(self):
        """Test handling when metadata_json is None."""
        mock_db = self._make_mock_db_content()
        mock_db.metadata_json = None
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert content.authors == []
        assert content.metadata == {}

    def test_from_db_content_all_annotation_types(self):
        """Test that all annotation types can be loaded."""
        annot_types = [
            "DIGITAL_HIGHLIGHT",
            "HANDWRITTEN_NOTE",
            "TYPED_COMMENT",
            "DIAGRAM",
            "UNDERLINE",
        ]
        mock_annots = [
            self._make_mock_db_annotation(
                annotation_id=i,
                annotation_type=at,
                text=f"Text for {at}",
            )
            for i, at in enumerate(annot_types)
        ]
        mock_db = self._make_mock_db_content(annotations=mock_annots)
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 5
        loaded_types = {a.type for a in content.annotations}
        assert loaded_types == {
            AnnotationType.DIGITAL_HIGHLIGHT,
            AnnotationType.HANDWRITTEN_NOTE,
            AnnotationType.TYPED_COMMENT,
            AnnotationType.DIAGRAM,
            AnnotationType.UNDERLINE,
        }

    def test_from_db_content_many_annotations_performance(self):
        """Test that loading many annotations works correctly."""
        # Create 100 annotations
        mock_annots = [
            self._make_mock_db_annotation(
                annotation_id=i,
                annotation_type="DIGITAL_HIGHLIGHT",
                text=f"Highlight {i}",
                page_number=i % 20 + 1,
            )
            for i in range(100)
        ]
        mock_db = self._make_mock_db_content(annotations=mock_annots)
        
        content = UnifiedContent.from_db_content(mock_db)
        
        assert len(content.annotations) == 100
        # Verify ordering is preserved
        assert content.annotations[0].content == "Highlight 0"
        assert content.annotations[99].content == "Highlight 99"
