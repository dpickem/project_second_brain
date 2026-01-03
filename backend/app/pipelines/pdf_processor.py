"""
PDF Processor Pipeline

Extracts text, structure, and annotations from PDFs using a hybrid approach:
- OCR (Mistral OCR) for text extraction and handwritten note detection
- pdfplumber for PDF annotation extraction (highlights, comments, underlines)

Features:
- Full document OCR with Mistral OCR (SOTA for document AI)
- Markdown-formatted text extraction preserving structure
- Table and figure detection
- Handwritten note detection via OCR image analysis
- Highlight and comment extraction via pdfplumber
- Metadata extraction (title, authors from OCR)
- Deduplication via file hash
- LLM cost tracking

Usage:
    from app.pipelines import PDFProcessor

    processor = PDFProcessor()
    content = await processor.process(Path("paper.pdf"))
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.pipelines.utils.cost_types import LLMUsage, PipelineName, PipelineOperation
from app.pipelines.utils.mistral_ocr_client import (
    get_default_ocr_model,
    ocr_pdf_document_annotated,
    MistralOCRResult,
)
from app.pipelines.utils.pdf_utils import (
    extract_annotations as extract_pdf_annotations,
    get_annotation_text,
)
from app.pipelines.utils.text_client import (
    get_default_text_model,
    text_completion,
)
from app.services.cost_tracking import CostTracker


class PDFProcessor(BasePipeline):
    """
    PDF processing pipeline using OCR for all text extraction.

    Uses Mistral OCR (or configured OCR model) to process entire PDF documents,
    extracting text with preserved structure, tables, and figures.

    Handles:
    - Full document OCR with markdown output
    - Structure preservation (headings, lists, tables)
    - Content type classification (paper/book/article)
    - LLM cost tracking for all API calls

    Routing:
    - Content type: PipelineContentType.PDF
    - File format: .pdf
    """

    SUPPORTED_CONTENT_TYPES = {PipelineContentType.PDF}
    PIPELINE_NAME = PipelineName.PDF_PROCESSOR

    def __init__(
        self,
        ocr_model: Optional[str] = None,
        text_model: Optional[str] = None,
        max_file_size_mb: int = 50,
        include_images: bool = False,
        track_costs: bool = True,
    ) -> None:
        """
        Initialize PDF processor.

        Args:
            ocr_model: OCR model for document processing. Defaults to settings.OCR_MODEL.
            text_model: Text model for content type classification. Defaults to settings.TEXT_MODEL.
            max_file_size_mb: Maximum allowed PDF file size in megabytes. Defaults to 50.
            include_images: Whether to include extracted images in OCR response. Defaults to False.
            track_costs: Whether to log LLM costs to database. Defaults to True.
        """
        super().__init__()
        self.ocr_model = ocr_model or get_default_ocr_model()
        self.text_model = text_model or get_default_text_model()
        self.max_file_size_mb = max_file_size_mb
        self.include_images = include_images
        self.track_costs = track_costs
        self._usage_records: list[LLMUsage] = []
        self._content_id: Optional[str] = None

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Args:
            input_data: The pipeline input to validate.

        Returns:
            bool: True if this pipeline can process the input.
        """
        if not isinstance(input_data, PipelineInput):
            return False
        if input_data.content_type != PipelineContentType.PDF:
            return False
        if input_data.path is None:
            return False
        return input_data.path.suffix.lower() == ".pdf"

    async def process(
        self,
        input_data: PipelineInput,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Process a PDF file from PipelineInput.

        Args:
            input_data: PipelineInput containing the path to the PDF file.
            content_id: Optional content ID for cost attribution.

        Returns:
            UnifiedContent: Extracted text and metadata from the PDF.

        Raises:
            ValueError: If input_data.path is None.
        """
        if input_data.path is None:
            raise ValueError("PipelineInput.path is required for PDF processing")
        return await self.process_path(input_data.path, content_id)

    async def process_path(
        self,
        pdf_path: Path,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Process a PDF file using OCR.

        Performs the full PDF processing pipeline:
        1. Validates file size and existence
        2. Calculates file hash for deduplication
        3. Runs OCR on entire document
        4. Extracts metadata from OCR result
        5. Classifies content type
        6. Logs LLM costs if tracking is enabled

        Args:
            pdf_path: Path to the PDF file.
            content_id: Optional content ID for cost attribution.

        Returns:
            UnifiedContent: Complete extracted content.
        """
        pdf_path = Path(pdf_path)

        # Reset usage records
        self._usage_records = []
        self._content_id = content_id

        # Validate file
        self.validate_file(pdf_path, self.max_file_size_mb)

        # Calculate file hash for deduplication
        file_hash = self.calculate_hash(pdf_path)

        # Check for duplicate
        existing = await self.check_duplicate(file_hash)
        if existing:
            self.logger.info(f"Duplicate PDF detected: {pdf_path}")
            return existing

        self.logger.info(f"Processing PDF with OCR: {pdf_path}")

        # Run OCR on entire document
        ocr_result = await ocr_pdf_document_annotated(
            pdf_path=pdf_path,
            model=self.ocr_model,
            include_images=self.include_images,
            pipeline=self.PIPELINE_NAME,
            content_id=self._content_id,
            operation=PipelineOperation.DOCUMENT_OCR,
        )

        # Track OCR usage
        if ocr_result.usage:
            self._usage_records.append(ocr_result.usage)

        # Extract metadata from document annotation (if available)
        doc_ann = ocr_result.document_annotation
        title = (doc_ann.title if doc_ann else "") or pdf_path.stem
        authors = doc_ann.authors if doc_ann else []

        # Extract annotations from both OCR (handwritten, figures) and PDF structure (highlights)
        ocr_annotations = self._extract_ocr_annotations(ocr_result)
        pdf_annotations = self._extract_pdf_annotations(pdf_path)
        annotations = ocr_annotations + pdf_annotations

        # Classify content type
        content_type = await self._infer_content_type(title, ocr_result.full_text)

        # Count annotation types
        highlight_count = sum(
            1 for a in annotations if a.type == AnnotationType.DIGITAL_HIGHLIGHT
        )
        handwritten_count = sum(
            1 for a in annotations if a.type == AnnotationType.HANDWRITTEN_NOTE
        )
        comment_count = sum(
            1 for a in annotations if a.type == AnnotationType.TYPED_COMMENT
        )
        diagram_count = sum(
            1 for a in annotations if a.type == AnnotationType.DIAGRAM
        )
        underline_count = sum(
            1 for a in annotations if a.type == AnnotationType.UNDERLINE
        )

        self.logger.info(
            f"OCR extracted {len(ocr_result.full_text)} chars from {len(ocr_result.pages)} pages"
        )
        self.logger.info(
            f"Found {len(annotations)} annotations: "
            f"{highlight_count} highlights, {handwritten_count} handwritten, "
            f"{comment_count} comments, {diagram_count} diagrams/figures, {underline_count} underlines"
        )

        # Log accumulated costs
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"PDF processing complete - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        return UnifiedContent(
            source_type=content_type,
            source_file_path=str(pdf_path),
            title=title,
            authors=authors,
            created_at=datetime.now(),
            full_text=ocr_result.full_text,
            annotations=annotations,
            raw_file_hash=file_hash,
            asset_paths=[str(pdf_path)],
            metadata={
                "ocr_model": self.ocr_model,
                "page_count": len(ocr_result.pages),
                "summary": doc_ann.summary if doc_ann else None,
                "languages": doc_ann.languages if doc_ann else None,
                "llm_cost_usd": sum(u.cost_usd or 0 for u in self._usage_records),
                "llm_api_calls": len(self._usage_records),
                "annotation_counts": {
                    "highlights": highlight_count,
                    "handwritten_notes": handwritten_count,
                    "comments": comment_count,
                    "diagrams": diagram_count,
                    "underlines": underline_count,
                    "total": len(annotations),
                },
            },
        )

    def _extract_ocr_annotations(self, ocr_result: MistralOCRResult) -> list[Annotation]:
        """
        Extract annotations from OCR result.

        Parses image_annotation fields from OCR to identify:
        - Handwritten notes (image_type: "text" with "handwritten" in description)
        - Diagrams/figures (image_type: "graph" or other visual elements)

        Args:
            ocr_result: Result from OCR processing.

        Returns:
            List of annotations found in the document.
        """
        annotations: list[Annotation] = []

        for page in ocr_result.pages:
            for i, img in enumerate(page.images):
                image_id = img.id or f"img_{i}"
                position: dict[str, Any] = {"image_id": image_id}

                # Add bounding box if available
                if img.has_bbox:
                    position["bbox"] = {
                        "top_left_x": img.top_left_x,
                        "top_left_y": img.top_left_y,
                        "bottom_right_x": img.bottom_right_x,
                        "bottom_right_y": img.bottom_right_y,
                    }

                # Parse image annotation if present (already parsed as dict in ImageInfo)
                annotation_data = img.annotation
                if annotation_data:
                    try:
                        # annotation is already a dict in ImageInfo
                        image_type = annotation_data.get("image_type", "").lower()
                        description = annotation_data.get("description", "")

                        # Check for handwritten content
                        is_handwritten = "handwritten" in description.lower()

                        if is_handwritten:
                            # Handwritten note detected
                            annotations.append(
                                Annotation(
                                    type=AnnotationType.HANDWRITTEN_NOTE,
                                    content=description,
                                    page_number=page.index + 1,
                                    position=position,
                                )
                            )
                        elif image_type == "graph":
                            # Diagram/graph detected
                            annotations.append(
                                Annotation(
                                    type=AnnotationType.DIAGRAM,
                                    content=description
                                    or f"Diagram on page {page.index + 1}",
                                    page_number=page.index + 1,
                                    position=position,
                                )
                            )
                        else:
                            # Other image types (figures, etc.)
                            annotations.append(
                                Annotation(
                                    type=AnnotationType.DIAGRAM,
                                    content=description
                                    or f"Figure on page {page.index + 1}",
                                    page_number=page.index + 1,
                                    position=position,
                                )
                            )
                    except (TypeError, KeyError, AttributeError):
                        # Fallback if annotation parsing fails
                        annotations.append(
                            Annotation(
                                type=AnnotationType.DIAGRAM,
                                content=f"Image on page {page.index + 1}",
                                page_number=page.index + 1,
                                position=position,
                            )
                        )
                else:
                    # No annotation data, treat as generic figure
                    annotations.append(
                        Annotation(
                            type=AnnotationType.DIAGRAM,
                            content=f"Figure on page {page.index + 1}",
                            page_number=page.index + 1,
                            position=position,
                        )
                    )

        return annotations

    def _extract_pdf_annotations(self, pdf_path: Path) -> list[Annotation]:
        """
        Extract PDF annotations (highlights, underlines, comments) using PyMuPDF.

        PDF annotations are stored as annotation objects in the PDF structure,
        separate from the rendered page content. This method extracts:
        - Highlights (type 8)
        - Underlines (type 9)
        - Squiggly underlines (type 10)
        - Strikeouts (type 11)
        - Comments/sticky notes (type 0: Text)
        - Free text annotations (type 2: FreeText)

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of annotations extracted from the PDF structure.
        """
        annotations: list[Annotation] = []

        # Map PyMuPDF annotation type codes to our AnnotationType
        # See pdf_utils.py for full type code reference
        type_code_mapping: dict[int, AnnotationType | None] = {
            0: AnnotationType.TYPED_COMMENT,      # Text (sticky note)
            1: None,                               # Link - skip
            2: AnnotationType.TYPED_COMMENT,      # FreeText
            8: AnnotationType.DIGITAL_HIGHLIGHT,  # Highlight
            9: AnnotationType.UNDERLINE,          # Underline
            10: AnnotationType.UNDERLINE,         # Squiggly
            11: AnnotationType.UNDERLINE,         # StrikeOut
            16: None,                              # Popup - skip
        }

        try:
            # Use pdf_utils to extract annotations via PyMuPDF
            raw_annotations = extract_pdf_annotations(pdf_path)

            for annot_info in raw_annotations:
                type_code = annot_info.get("type_code")
                type_name = annot_info.get("type_name", "Unknown")

                # Map to our annotation type
                annotation_type = type_code_mapping.get(type_code)
                if annotation_type is None:
                    continue

                # Get text content using the helper function
                content = get_annotation_text(annot_info) or ""

                # Also check for comments (stored separately from highlighted text)
                comment = annot_info.get("comment", "")
                if comment and not content:
                    content = comment
                elif comment and content:
                    content = f"{content}\n[Comment: {comment}]"

                # Build position info
                position: dict[str, Any] = {"type_name": type_name}
                rect = annot_info.get("rect")
                if rect:
                    position["rect"] = rect
                author = annot_info.get("author")
                if author:
                    position["author"] = author
                if annot_info.get("fill_color"):
                    position["fill_color"] = annot_info["fill_color"]
                if annot_info.get("stroke_color"):
                    position["stroke_color"] = annot_info["stroke_color"]

                # Get page number (pdf_utils uses 1-based page numbers)
                page_number = annot_info.get("page", 1)

                # Create annotation if we have content or it's a markup type
                if content or type_code in {8, 9, 10, 11}:
                    annotations.append(
                        Annotation(
                            type=annotation_type,
                            content=content or f"[{type_name} annotation]",
                            page_number=page_number,
                            position=position,
                        )
                    )

            self.logger.debug(
                f"Extracted {len(annotations)} PDF annotations from {pdf_path}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract PDF annotations: {e}")

        return annotations

    async def _infer_content_type(
        self,
        title: str,
        text: str,
    ) -> ContentType:
        """
        Infer whether PDF is a paper, article, or book using LLM.

        Args:
            title: Document title.
            text: Full extracted text.

        Returns:
            ContentType: PAPER, BOOK, or ARTICLE.
        """
        text_sample = text[:3000]

        prompt = f"""Classify this PDF document into exactly one category.

Title: {title}

Text excerpt:
{text_sample}

Categories:
- paper: Academic/research papers, scientific publications, conference papers, journal articles
- book: Books, ebooks, textbooks, manuals with chapters
- article: Blog posts, news articles, general documents, reports

Respond with ONLY the category name (paper, book, or article), nothing else."""

        try:
            response, usage = await text_completion(
                model=self.text_model,
                prompt=prompt,
                max_tokens=10,
                temperature=0.0,
                pipeline=self.PIPELINE_NAME,
                content_id=self._content_id,
                operation=PipelineOperation.CONTENT_TYPE_CLASSIFICATION,
            )

            self._usage_records.append(usage)

            result = response.strip().lower()
            if "paper" in result:
                return ContentType.PAPER
            elif "book" in result:
                return ContentType.BOOK
            else:
                return ContentType.ARTICLE

        except Exception as e:
            self.logger.warning(f"Content type inference failed: {e}")
            return ContentType.ARTICLE
