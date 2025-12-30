"""
PDF Processor Pipeline

Extracts text, highlights, comments, and handwritten annotations from PDFs.
Supports academic papers, ebooks, and annotated documents.

Features:
- Text extraction with PyMuPDF (fast, layout-aware)
- Digital annotation extraction with pdfplumber (highlights, comments)
- Handwritten annotation OCR with Vision LLM
- Metadata extraction (title, authors, date)
- Deduplication via file hash

Usage:
    from app.pipelines import PDFProcessor

    processor = PDFProcessor()
    content = await processor.process(Path("paper.pdf"))
"""

from PIL.Image import Image
import re
from datetime import datetime
from itertools import batched
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
from PIL import Image

from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.pipelines.utils.cost_types import LLMUsage
from app.pipelines.utils.image_utils import image_to_base64
from app.pipelines.utils.ocr_client import (
    get_default_ocr_model,
    vision_completion_multi_image,
)
from app.pipelines.utils.text_client import (
    get_default_text_model,
    text_completion,
)
from app.pipelines.utils.text_utils import extract_json_from_response
from app.services.cost_tracking import CostTracker


class PDFProcessor(BasePipeline):
    """
    PDF processing pipeline for extracting text and annotations.

    Handles:
    - Printed text extraction
    - Digital highlights and comments
    - Handwritten margin notes (via Vision LLM)
    - PDF metadata (title, authors, date)
    - LLM cost tracking for all API calls

    Routing:
    - Content type: PipelineContentType.PDF
    - File format: .pdf
    """

    SUPPORTED_CONTENT_TYPES = {PipelineContentType.PDF}
    PIPELINE_NAME = "pdf_processor"

    def __init__(
        self,
        ocr_model: Optional[str] = None,
        text_model: Optional[str] = None,
        ocr_max_tokens: int = 4000,
        use_json_mode: bool = True,
        enable_handwriting_detection: bool = True,
        max_file_size_mb: int = 50,
        image_dpi: int = 300,
        handwriting_batch_size: int = 5,
        track_costs: bool = True,
    ) -> None:
        """
        Initialize PDF processor.

        Args:
            ocr_model: Vision model for handwriting OCR. Defaults to value from
                environment variable via get_default_ocr_model().
            text_model: Text model for content type classification. Defaults to value
                from environment variable via get_default_text_model().
            ocr_max_tokens: Maximum tokens for OCR responses. Defaults to 4000.
            use_json_mode: Whether to request structured JSON from OCR. Defaults to True.
            enable_handwriting_detection: Whether to detect handwritten notes. Defaults to True.
            max_file_size_mb: Maximum allowed PDF file size in megabytes. Defaults to 50.
            image_dpi: DPI resolution for page-to-image conversion. Defaults to 300.
            handwriting_batch_size: Number of pages to process per VLM call. Higher values
                reduce API calls but may hit token limits. Defaults to 5.
            track_costs: Whether to log LLM costs to database. Defaults to True.

        Returns:
            None
        """
        super().__init__()
        self.ocr_model = ocr_model or get_default_ocr_model()
        self.text_model = text_model or get_default_text_model()
        self.ocr_max_tokens = ocr_max_tokens
        self.use_json_mode = use_json_mode
        self.enable_handwriting_detection = enable_handwriting_detection
        self.max_file_size_mb = max_file_size_mb
        self.image_dpi = image_dpi
        self.handwriting_batch_size = handwriting_batch_size
        self.track_costs = track_costs
        self._usage_records: list[LLMUsage] = []
        self._content_id: Optional[str] = None

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Validates that the input is a PipelineInput with content_type PDF
        and a path ending with .pdf extension.

        Args:
            input_data: The pipeline input to validate.

        Returns:
            bool: True if this pipeline can process the input, False otherwise.
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
            content_id: Optional content ID for cost attribution and tracking.

        Returns:
            UnifiedContent: Extracted text, metadata, and annotations from the PDF.

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
        Process a PDF file (direct path interface).

        Performs the full PDF processing pipeline:
        1. Validates file size and existence
        2. Calculates file hash for deduplication
        3. Extracts PDF metadata (title, authors, date)
        4. Extracts printed text content
        5. Extracts digital annotations (highlights, comments)
        6. Optionally detects and transcribes handwritten annotations
        7. Logs LLM costs if tracking is enabled

        Args:
            pdf_path: Path to the PDF file to process.
            content_id: Optional content ID for cost attribution and tracking.

        Returns:
            UnifiedContent: Complete extracted content including text, metadata,
                and all annotations (digital and handwritten).
        """
        pdf_path = Path(pdf_path)

        # Reset usage records for this processing run
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

        self.logger.info(f"Processing PDF: {pdf_path}")

        # Step 1: Extract metadata
        metadata = self._extract_metadata(pdf_path)

        # Step 2: Extract text
        full_text = self._extract_text(pdf_path)

        # Step 3: Extract digital annotations
        digital_annotations = self._extract_digital_annotations(pdf_path)

        # Step 4: Detect handwritten annotations (if enabled)
        handwritten_annotations: list[Annotation] = []
        if self.enable_handwriting_detection:
            handwritten_annotations = await self._extract_handwritten_annotations(
                pdf_path
            )

        # Combine all annotations
        all_annotations = digital_annotations + handwritten_annotations

        # Determine content type (paper vs article vs book)
        content_type = await self._infer_content_type(metadata, full_text)

        self.logger.info(
            f"Extracted {len(full_text)} chars, "
            f"{len(digital_annotations)} digital annotations, "
            f"{len(handwritten_annotations)} handwritten annotations"
        )

        # Log all accumulated LLM costs to database
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
            title=metadata.get("title", pdf_path.stem),
            authors=metadata.get("authors", []),
            created_at=metadata.get("created", datetime.now()),
            full_text=full_text,
            annotations=all_annotations,
            raw_file_hash=file_hash,
            asset_paths=[str(pdf_path)],
            metadata={
                "llm_cost_usd": sum(u.cost_usd or 0 for u in self._usage_records),
                "llm_api_calls": len(self._usage_records),
            },
        )

    def _extract_metadata(self, pdf_path: Path) -> dict[str, Any]:
        """
        Extract PDF metadata including title, authors, and creation date.

        Uses PyMuPDF to read embedded PDF metadata. Parses author fields
        that may be separated by commas, semicolons, or ampersands.
        Handles PDF date format (D:YYYYMMDDHHmmSS+TZ) for creation dates.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            dict[str, Any]: Dictionary containing:
                - "title" (str): Document title or filename stem if not available.
                - "authors" (list[str]): List of author names, empty if not available.
                - "created" (datetime | None): Creation date or current time if not parseable.
        """
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}

        result: dict[str, Any] = {
            "title": meta.get("title") or pdf_path.stem,
            "authors": [],
            "created": None,
        }

        # Parse author field (may be comma, semicolon, or & separated)
        if meta.get("author"):
            authors = re.split(r"[,;&]", meta["author"])
            result["authors"] = [a.strip() for a in authors if a.strip()]

        # Parse creation date
        if meta.get("creationDate"):
            try:
                # PDF date format: D:YYYYMMDDHHmmSS+TZ
                date_str = meta["creationDate"].replace("D:", "")[:8]
                result["created"] = datetime.strptime(date_str, "%Y%m%d")
            except (ValueError, IndexError):
                result["created"] = datetime.now()
        else:
            result["created"] = datetime.now()

        doc.close()
        return result

    def _extract_text(self, pdf_path: Path) -> str:
        """
        Extract all printed text from PDF with page markers.

        Uses PyMuPDF for fast, layout-aware text extraction. Each page's
        content is prefixed with a page marker in the format "[Page N]".

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            str: Concatenated text from all pages with page markers,
                separated by double newlines.
        """
        doc = fitz.open(pdf_path)
        text_parts: list[str] = []

        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"[Page {page_num}]\n{text}")

        doc.close()
        return "\n\n".join(text_parts)

    def _extract_digital_annotations(self, pdf_path: Path) -> list[Annotation]:
        """
        Extract digital highlights, underlines, and comments from PDF.

        Uses pdfplumber to read PDF annotation objects. Supports:
        - Highlights: Extracts highlighted text
        - Text/FreeText/Popup/Note: Extracts comment content
        - Underlines: Extracts underlined text

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            list[Annotation]: List of Annotation objects for each digital
                annotation found, with type, content, page number, and position.
        """
        annotations: list[Annotation] = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_annots = page.annots or []

                    for annot in page_annots:
                        annot_type = annot.get("subtype", "").lower()

                        if annot_type == "highlight":
                            text = self._get_text_in_rect(page, annot.get("rect"))
                            if text:
                                annotations.append(
                                    Annotation(
                                        type=AnnotationType.DIGITAL_HIGHLIGHT,
                                        content=text,
                                        page_number=page_num,
                                        position={"rect": annot.get("rect")},
                                    )
                                )

                        elif annot_type in ("text", "freetext", "popup", "note"):
                            content = annot.get("contents") or annot.get("text", "")
                            if content:
                                annotations.append(
                                    Annotation(
                                        type=AnnotationType.TYPED_COMMENT,
                                        content=content,
                                        page_number=page_num,
                                        position={"rect": annot.get("rect")},
                                    )
                                )

                        elif annot_type == "underline":
                            text = self._get_text_in_rect(page, annot.get("rect"))
                            if text:
                                annotations.append(
                                    Annotation(
                                        type=AnnotationType.UNDERLINE,
                                        content=text,
                                        page_number=page_num,
                                        position={
                                            "rect": annot.get("rect"),
                                            "style": "underline",
                                        },
                                    )
                                )
        except Exception as e:
            self.logger.warning(f"Error extracting digital annotations: {e}")

        return annotations

    def _get_text_in_rect(
        self,
        page: pdfplumber.page.Page,
        rect: Optional[tuple[float, float, float, float]],
    ) -> str:
        """
        Extract text within a bounding rectangle on a page.

        Args:
            page: A pdfplumber Page object to extract text from.
            rect: Bounding box as (x0, y0, x1, y1) tuple, or None.

        Returns:
            str: Extracted text within the rectangle, or empty string if
                rect is None or extraction fails.
        """
        if not rect:
            return ""
        try:
            crop = page.within_bbox(rect)
            chars = crop.chars
            return "".join(c.get("text", "") for c in chars).strip()
        except Exception:
            return ""

    async def _extract_handwritten_annotations(
        self,
        pdf_path: Path,
    ) -> list[Annotation]:
        """
        Transcribe handwritten annotations from PDF pages using Vision LLM.

        Converts PDF pages to images and processes them in batches to reduce
        API calls. Each batch sends multiple page images in a single VLM request.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            list[Annotation]: List of Annotation objects for each handwritten
                annotation found, including transcribed text and location.
        """
        annotations: list[Annotation] = []

        try:
            # Convert PDF pages to images, pair with 1-indexed page numbers
            images = convert_from_path(pdf_path, dpi=self.image_dpi)
            numbered_pages = list[tuple[int, Image]](enumerate(images, start=1))

            # Process in batches
            for batch in batched(numbered_pages, self.handwriting_batch_size):
                page_numbers, batch_images = zip(*batch)
                page_numbers = list(page_numbers)

                self.logger.debug(
                    f"Processing handwriting batch: pages {page_numbers[0]}-{page_numbers[-1]}"
                )

                batch_annotations = await self._transcribe_handwriting_batch(
                    list(batch_images), page_numbers
                )

                if batch_annotations:
                    self.logger.info(
                        f"Found {len(batch_annotations)} handwritten annotations "
                        f"in pages {page_numbers[0]}-{page_numbers[-1]}"
                    )
                    annotations.extend(batch_annotations)

        except Exception as e:
            self.logger.error(f"Handwriting extraction failed: {e}")

        return annotations

    async def _transcribe_handwriting_batch(
        self,
        images: list[Image.Image],
        page_numbers: list[int],
    ) -> list[Annotation]:
        """
        Transcribe handwritten content from multiple page images in a single API call.

        Sends multiple page images to the Vision LLM together, with a prompt that
        instructs the model to identify which page each annotation comes from.

        Args:
            images: List of PIL Images of PDF pages to analyze.
            page_numbers: List of 1-indexed page numbers corresponding to each image.

        Returns:
            list[Annotation]: List of Annotation objects with transcribed
                handwritten content, or empty list on error.
        """
        # Convert images to base64
        images_b64 = [image_to_base64(img) for img in images]

        # Build page reference string
        page_refs = ", ".join(
            f"Image {i + 1} = Page {pn}" for i, pn in enumerate(page_numbers)
        )

        prompt = f"""Analyze these document pages and extract ALL handwritten annotations.

Page mapping: {page_refs}

For each handwritten element, provide:
1. The page number it appears on
2. The transcribed text (use [unclear] for illegible parts)
3. Its location on the page
4. Any nearby printed text it relates to

Return as JSON array:
[
  {{
    "page": 1,
    "text": "transcribed handwritten text",
    "location": "top-right margin",
    "context": "nearby printed text or null",
    "type": "note|question|arrow|underline|circle"
  }}
]

If no handwritten content exists on any page, return: []"""

        try:
            response, usage = await vision_completion_multi_image(
                model=self.ocr_model,
                prompt=prompt,
                images=images_b64,
                max_tokens=self.ocr_max_tokens,
                json_mode=self.use_json_mode,
                pipeline=self.PIPELINE_NAME,
                content_id=self._content_id,
                operation="handwriting_transcription_batch",
            )

            # Track usage for batch logging
            self._usage_records.append(usage)

            return self._parse_handwriting_batch_response(response, page_numbers)

        except Exception as e:
            self.logger.error(f"Handwriting transcription batch failed: {e}")
            return []

    def _parse_handwriting_batch_response(
        self,
        response_text: str,
        valid_page_numbers: list[int],
    ) -> list[Annotation]:
        """
        Parse batched LLM response into Annotation objects.

        Extracts JSON array from the LLM response and converts each item
        into an Annotation with HANDWRITTEN_NOTE type. Each item must include
        a page number field.

        Args:
            response_text: Raw text response from the Vision LLM.
            valid_page_numbers: List of valid page numbers for this batch,
                used to validate and default page assignments.

        Returns:
            list[Annotation]: List of Annotation objects parsed from the response,
                or empty list if parsing fails or response is invalid.
        """
        items = extract_json_from_response(response_text)

        if not items or not isinstance(items, list):
            return []

        annotations: list[Annotation] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            text = item.get("text", "").strip()
            if not text:
                continue

            # Get page number from response, default to first page in batch if missing
            page_num = item.get("page")
            if page_num is None or page_num not in valid_page_numbers:
                page_num = valid_page_numbers[0]

            annotations.append(
                Annotation(
                    type=AnnotationType.HANDWRITTEN_NOTE,
                    content=text,
                    page_number=page_num,
                    context=item.get("context"),
                    position={
                        "location": item.get("location"),
                        "mark_type": item.get("type"),
                    },
                )
            )

        return annotations

    async def _infer_content_type(
        self,
        metadata: dict[str, Any],
        text: str,
    ) -> ContentType:
        """
        Infer whether PDF is a paper, article, or book using LLM classification.

        Sends the document title and initial text to an LLM for classification.
        Falls back to ARTICLE if classification fails.

        Args:
            metadata: Extracted PDF metadata including title.
            text: Full extracted text from the PDF.

        Returns:
            ContentType: PAPER for academic/research papers, BOOK for books/ebooks,
                or ARTICLE for general articles and other documents.
        """
        # Extract title from metadata
        title = metadata.get("title", "Unknown")

        # Use first ~3000 chars to stay well within token limits
        text_sample = text[:3000]

        # Construct prompt for content type classification
        prompt = f"""Classify this PDF document into exactly one category.

Title: {title}

Text excerpt:
{text_sample}

Categories:
- paper: Academic/research papers, scientific publications, conference papers, journal articles, preprints (arXiv, etc.)
- book: Books, ebooks, textbooks, manuals with chapters
- article: Blog posts, news articles, general web articles, reports, other documents

Respond with ONLY the category name (paper, book, or article), nothing else."""

        try:
            response, usage = await text_completion(
                model=self.text_model,
                prompt=prompt,
                max_tokens=10,
                temperature=0.0,
                pipeline=self.PIPELINE_NAME,
                content_id=self._content_id,
                operation="content_type_classification",
            )

            # Track usage for batch logging
            self._usage_records.append(usage)

            # Parse response
            result = response.strip().lower()
            if "paper" in result:
                return ContentType.PAPER
            elif "book" in result:
                return ContentType.BOOK
            else:
                return ContentType.ARTICLE

        except Exception as e:
            self.logger.warning(
                f"Content type inference failed, defaulting to ARTICLE: {e}"
            )
            return ContentType.ARTICLE
