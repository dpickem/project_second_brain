"""
Book Photo OCR Pipeline

Extracts text, highlights, and margin notes from photos of physical book pages.
Uses Vision LLM for OCR with intelligent page number and chapter detection.

Features:
- Page number extraction via OCR (not assumed from image order)
- Chapter detection from running headers/footers
- Handwritten margin note transcription
- Highlight/underline detection
- Two-page spread handling
- Book metadata inference
- Parallel OCR processing for faster batch handling

Usage:
    from app.pipelines import BookOCRPipeline
    from app.pipelines.base import PipelineInput, PipelineContentType

    pipeline = BookOCRPipeline()

    # Using PipelineInput (registry pattern)
    input_data = PipelineInput(
        path=Path("pages/"),  # Directory or will be set from asset_paths
        content_type=PipelineContentType.BOOK,
    )
    content = await pipeline.process(input_data)

    # Direct call with paths (legacy)
    content = await pipeline.process_paths(
        [Path("page1.jpg"), Path("page2.jpg")],
        book_metadata={"title": "Deep Work"}
    )

    # For large books, increase concurrency:
    pipeline = BookOCRPipeline(max_concurrency=10)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.pipelines.utils.image_utils import (
    image_to_base64,
    preprocess_for_ocr,
    auto_rotate,
)
from app.pipelines.utils.vlm_client import (
    vision_completion,
    get_default_ocr_model,
)
from app.enums.pipeline import PipelineName
from app.pipelines.utils.cost_types import LLMUsage
from app.pipelines.utils.text_utils import extract_json_from_response
from app.enums.pipeline import PipelineOperation
from app.services.llm import (
    get_llm_client,
    get_default_text_model,
    build_messages,
)
from app.services.cost_tracking import CostTracker

# =============================================================================
# Constants
# =============================================================================

# OCR processing defaults
DEFAULT_OCR_MAX_TOKENS = (
    8000  # Max tokens for OCR responses (dense pages may need more)
)
DEFAULT_MAX_CONCURRENCY = (
    5  # Concurrent OCR API calls (5-10 recommended, up to 20 for large batches)
)

# Output formatting
DEFAULT_BOOK_TITLE = "Unknown Book"
PAGE_SEPARATOR = "\n\n---\n\n"  # Separator between pages in full_text output

# Metadata inference
METADATA_MAX_TOKENS = 500  # Max tokens for metadata inference (small output)
METADATA_TEMPERATURE = 0.2  # Low temp for factual extraction
METADATA_TEXT_LIMIT = 4000  # Max chars of page text to send for inference
METADATA_PAGES_TO_USE = 3  # Number of pages to use for metadata inference

# Retry configuration for JSON parsing failures
MAX_JSON_PARSE_RETRIES = 2  # Number of retries when JSON parsing fails


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ChapterInfo:
    """Chapter information extracted from page headers/footers."""

    number: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None


@dataclass
class PageResult:
    """Result from processing a single book page."""

    full_text: str = ""
    annotations: list[Annotation] = field(default_factory=list)
    page_number: Optional[int] = None
    page_number_location: Optional[str] = None
    chapter: Optional[ChapterInfo] = None
    is_two_page_spread: bool = False
    spread_pages: Optional[list[int]] = None
    source_image: str = ""
    # Error tracking
    error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    @classmethod
    def from_error(cls, error: str, source_image: str = "") -> PageResult:
        """Create a PageResult representing an error."""
        return cls(error=error, source_image=source_image)


@dataclass
class BookMetadata:
    """Book metadata (provided or inferred)."""

    title: str = DEFAULT_BOOK_TITLE
    authors: list[str] = field(default_factory=list)
    isbn: Optional[str] = None
    # Inference tracking
    inferred: bool = False
    inference_error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        """Check if metadata inference failed."""
        return self.inference_error is not None


class BookOCRPipeline(BasePipeline):
    """
    Book photo OCR pipeline for extracting content from physical books.

    Key features:
    - Page numbers extracted via OCR, not assumed from image order
    - Chapter info extracted from running headers/footers
    - Distinguishes printed text from handwritten annotations
    - Handles two-page spreads
    - Tracks LLM costs for all API calls

    Routing:
    - Content type: PipelineContentType.BOOK
    - File formats: .jpg, .jpeg, .png, .heic, .webp, .tiff
    """

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff"}
    SUPPORTED_CONTENT_TYPES = {PipelineContentType.BOOK}
    PIPELINE_NAME = PipelineName.BOOK_OCR

    def __init__(
        self,
        ocr_model: Optional[str] = None,
        text_model: Optional[str] = None,
        ocr_max_tokens: int = DEFAULT_OCR_MAX_TOKENS,
        use_json_mode: bool = True,
        track_costs: bool = True,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        """
        Initialize Book OCR pipeline.

        Args:
            ocr_model: Vision model for OCR (e.g., "gemini/gemini-3-flash-preview").
                       Defaults to settings.OCR_MODEL.
            text_model: Text model for metadata inference (e.g., "gemini/gemini-3-flash-preview").
                       Defaults to settings.TEXT_MODEL.
            ocr_max_tokens: Maximum tokens for OCR responses.
            use_json_mode: Request structured JSON output from vision model.
            track_costs: Whether to log LLM costs to database.
            max_concurrency: Maximum concurrent OCR API calls.
                Recommended: 5-10 for most use cases, up to 20 for large batches.
        """
        super().__init__()
        self.ocr_model = ocr_model or get_default_ocr_model()
        self.text_model = text_model or get_default_text_model()
        self.ocr_max_tokens = ocr_max_tokens
        self.use_json_mode = use_json_mode
        self.track_costs = track_costs
        self.max_concurrency = max_concurrency
        self._usage_records: list[LLMUsage] = []
        self._usage_lock: Optional[asyncio.Lock] = None
        self._content_id: Optional[str] = None

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Requires:
        - content_type == BOOK
        - path is set (file or directory of images)
        """
        if not isinstance(input_data, PipelineInput):
            return False

        if input_data.content_type != PipelineContentType.BOOK:
            return False

        if input_data.path is None:
            return False

        # Check if it's a supported image file
        if input_data.path.is_file():
            return input_data.path.suffix.lower() in self.SUPPORTED_FORMATS

        # For directories, we'll check files during processing
        return True

    async def process(
        self,
        input_data: PipelineInput,
        book_metadata: Optional[BookMetadata] = None,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Process book page photos from PipelineInput.

        Args:
            input_data: PipelineInput with path to image file or directory of images.
            book_metadata: Optional metadata dict with title, authors, isbn.
                          If not provided, will attempt to infer from page text.
            content_id: Optional content ID for cost attribution in database.

        Returns:
            UnifiedContent with extracted text, annotations, and metadata.

        Raises:
            ValueError: If input_data.path is neither a file nor directory.
        """
        # Extract image paths from input
        if input_data.path.is_file():
            image_paths = [input_data.path]
        elif input_data.path.is_dir():
            image_paths = [
                p
                for p in input_data.path.iterdir()
                if p.suffix.lower() in self.SUPPORTED_FORMATS
            ]
        else:
            raise ValueError(f"Invalid path: {input_data.path}")

        return await self.process_paths(image_paths, book_metadata, content_id)

    async def process_paths(
        self,
        image_paths: list[Path],
        book_metadata: Optional[BookMetadata] = None,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Process batch of book page photos.

        Page numbers are extracted via OCR from the images themselves,
        NOT assumed from image order. Images may contain two-page spreads,
        page numbers may be missing, or pages may be out of order.

        Args:
            image_paths: List of paths to page images (.jpg, .png, etc.).
            book_metadata: Optional metadata with title, authors, isbn.
                          If not provided, will attempt to infer from first page.
            content_id: Optional content UUID for cost attribution.

        Returns:
            UnifiedContent with:
            - full_text: All pages joined with separators
            - annotations: Highlights and margin notes with page numbers
            - metadata: Chapters found, processing stats, LLM costs
        """
        if isinstance(image_paths, Path):
            image_paths = [image_paths]

        image_paths = [Path(p) for p in image_paths]

        # Convert dict to BookMetadata if needed (tasks.py passes dict)
        if isinstance(book_metadata, dict):
            book_metadata = BookMetadata(
                title=book_metadata.get("title", DEFAULT_BOOK_TITLE),
                authors=book_metadata.get("authors", []),
                isbn=book_metadata.get("isbn"),
            )

        # Reset usage records for this processing run
        self._usage_records = []
        self._usage_lock = asyncio.Lock()  # Create lock in async context
        self._content_id = content_id

        self.logger.info(
            f"Processing {len(image_paths)} book page images "
            f"(max {self.max_concurrency} concurrent)"
        )

        # Process pages in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_with_semaphore(idx: int, image_path: Path) -> dict:
            async with semaphore:
                self.logger.info(
                    f"Processing image {idx + 1}/{len(image_paths)}: {image_path.name}"
                )

                # Preprocess image (CPU-bound, but fast)
                image = auto_rotate(image_path)
                processed = preprocess_for_ocr(image)

                # Extract content including page number from OCR
                page_result = await self._process_page(processed)
                page_result.source_image = str(image_path)
                return page_result

        # Create tasks for all pages
        tasks = [
            process_with_semaphore(idx, path) for idx, path in enumerate(image_paths)
        ]

        # Execute all tasks concurrently (limited by semaphore)
        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        valid_results: list[PageResult] = []
        for idx, result in enumerate(page_results):
            if isinstance(result, Exception):
                self.logger.error(f"Page {idx + 1} failed: {result}")
                valid_results.append(
                    PageResult.from_error(
                        error=str(result),
                        source_image=str(image_paths[idx]),
                    )
                )
            else:
                valid_results.append(result)

        page_results = valid_results

        # Infer metadata BEFORE sorting - use original photo order
        # Copyright/ISBN pages often have no page number and would sort to the end
        if not book_metadata and page_results:
            # Build text from first few pages in ORIGINAL order (as photographed)
            metadata_texts = []
            for result in page_results[:METADATA_PAGES_TO_USE]:
                if result.full_text and not result.has_error:
                    metadata_texts.append(result.full_text)
            if metadata_texts:
                combined_text = "\n\n---\n\n".join(metadata_texts)
                book_metadata = await self._infer_metadata(combined_text)

        # Sort by extracted page number for final output
        # Tuple key: (is_none, page_num) ensures None values sort last
        page_results.sort(
            key=lambda x: (
                x.page_number is None,  # None values last
                x.page_number or 0,
            )
        )

        # Aggregate results
        all_annotations = []
        full_text_parts = []
        chapters_found = {}

        for result in page_results:
            page_num = result.page_number
            chapter = result.chapter

            # Build page label with chapter context
            page_label = self._build_page_label(page_num, chapter, result.source_image)
            full_text_parts.append(f"[{page_label}]\n{result.full_text}")

            # Track chapters
            if chapter and chapter.number:
                chapters_found[chapter.number] = chapter.title

            # Update annotations with extracted page number and chapter
            for annot in result.annotations:
                annot.page_number = page_num
                if chapter:
                    if annot.position is None:
                        annot.position = {}
                    annot.position["chapter"] = {
                        "number": chapter.number,
                        "title": chapter.title,
                    }
                all_annotations.append(annot)

        if not book_metadata:
            book_metadata = BookMetadata()

        # Log all accumulated LLM costs to database
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"Book OCR complete - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        # Count errors
        page_errors = [r for r in page_results if r.has_error]

        return UnifiedContent(
            source_type=ContentType.BOOK,
            title=book_metadata.title,
            authors=book_metadata.authors,
            created_at=datetime.now(),
            full_text=PAGE_SEPARATOR.join(full_text_parts),
            annotations=all_annotations,
            asset_paths=[str(p) for p in image_paths],
            metadata={
                "chapters": chapters_found,
                "isbn": book_metadata.isbn,
                "total_pages_processed": len(page_results),
                "pages_with_errors": len(page_errors),
                "page_errors": (
                    [{"source": r.source_image, "error": r.error} for r in page_errors]
                    if page_errors
                    else None
                ),
                "metadata_inferred": book_metadata.inferred,
                "metadata_inference_error": book_metadata.inference_error,
                "llm_cost_usd": sum(u.cost_usd or 0 for u in self._usage_records),
                "llm_api_calls": len(self._usage_records),
            },
        )

    def _build_page_label(
        self,
        page_num: Optional[int],
        chapter: Optional[ChapterInfo],
        source_image: str,
    ) -> str:
        """
        Build a descriptive label for a page.

        Args:
            page_num: Extracted page number, or None if not found.
            chapter: Chapter info, or None if not detected.
            source_image: Path to source image file (used as fallback label).

        Returns:
            Label like "Page 42 (Ch. 5: Memory)" or "[Image: photo.jpg]".
        """
        if page_num and chapter:
            chapter_str = ""
            if chapter.number:
                chapter_str = f"Ch. {chapter.number}"
            if chapter.title:
                chapter_str = (
                    f"{chapter_str}: {chapter.title}" if chapter_str else chapter.title
                )
            return (
                f"Page {page_num} ({chapter_str})"
                if chapter_str
                else f"Page {page_num}"
            )
        elif page_num:
            return f"Page {page_num}"
        else:
            return f"[Image: {Path(source_image).name}]"

    async def _process_page(self, image: Image.Image) -> PageResult:
        """
        Process a book page using a vision chat model (Gemini, GPT-4o, Claude).

        These models can follow structured prompts to extract page numbers,
        chapters, highlights, and margin notes in addition to the text.

        Args:
            image: PIL Image to process.

        Returns:
            PageResult with structured extraction.
        """
        image_data = image_to_base64(image)

        prompt = """Analyze this book page photo and extract:

1. PAGE NUMBER: Look for printed page numbers (usually at top or bottom corners).
   - If visible, extract the number(s)
   - If this is a two-page spread, extract both page numbers
   - If no page number is visible, use null

2. CHAPTER INFO: Look in headers/footers for chapter information.
   - Chapter number (e.g., "Chapter 5", "Part II", "Section 3.2")
   - Chapter title (e.g., "The Nature of Memory")
   - Running headers often show: "Chapter X" on left pages, chapter title on right pages

3. ALL printed text (complete transcription)

4. UNDERLINED TEXT - CRITICAL: Carefully scan EVERY line of text for underlines.
   Underlines indicate important passages the reader wanted to remember.
   Look for:
   - Straight lines drawn beneath text (pen, pencil, or ruler-drawn)
   - Wavy or irregular underlines
   - Single underlines or double underlines
   - Partial underlines (even a few words underlined matter)
   - Faint or light pencil underlines (look closely!)
   
   For EACH underlined passage, extract the COMPLETE text that is underlined.
   Do not skip any underlined text, even if it seems minor.

5. OTHER MARKINGS: Highlighted text (color), circled words, bracketed passages, 
   vertical lines in margins next to text, asterisks or stars next to text.

6. HANDWRITTEN MARGIN NOTES (in margins, whitespace, between lines)

Return JSON:
{
  "page_number": 42,
  "page_number_location": "bottom-right",
  "chapter": {
    "number": "5",
    "title": "The Nature of Memory",
    "location": "header-left"
  },
  "is_two_page_spread": false,
  "spread_pages": null,
  "full_text": "complete printed text...",
  "highlights": [
    {"text": "the exact underlined or highlighted passage", "type": "underline|highlight|circle|bracket|vertical_line|star", "location": "top|middle|bottom", "style": "pen|pencil|marker|ruler"}
  ],
  "margin_notes": [
    {"text": "handwritten note", "location": "left-margin|right-margin|top|bottom", "related_text": "nearby printed text or null", "type": "note|question|definition"}
  ]
}

For two-page spreads, use:
{
  "page_number": null,
  "is_two_page_spread": true,
  "spread_pages": [42, 43],
  ...
}

If no chapter info visible, use: "chapter": null

CRITICAL INSTRUCTIONS:
- UNDERLINES ARE HIGH PRIORITY: Scan every paragraph carefully for any lines drawn under text
- Even faint pencil marks count - look closely at the space just below each line of text
- Capture the FULL underlined phrase, not just partial words
- Page number extraction is critical - check all corners and headers/footers
- Chapter info often appears in running headers/footers - check both top and bottom
- Use null for page_number or chapter only if truly not visible
- Distinguish printed text from handwritten annotations
- Use [unclear] for illegible parts
- Include ALL handwritten content including brief marks like "!" or "?"
"""

        last_error: Optional[str] = None

        for attempt in range(1, MAX_JSON_PARSE_RETRIES + 2):  # +2 for initial + retries
            try:
                response, usage = await vision_completion(
                    model=self.ocr_model,
                    prompt=prompt,
                    image_data=image_data,
                    max_tokens=self.ocr_max_tokens,
                    json_mode=self.use_json_mode,
                    pipeline=self.PIPELINE_NAME,
                    content_id=getattr(self, "_content_id", None),
                    operation=PipelineOperation.PAGE_EXTRACTION,
                )

                # Track usage for batch logging (thread-safe)
                async with self._usage_lock:
                    self._usage_records.append(usage)

                # Try to parse the response
                result = self._parse_page_response(response)

                # Check if parsing succeeded
                if not result.has_error:
                    return result

                # JSON parsing failed - retry if we have attempts left
                last_error = result.error
                if attempt <= MAX_JSON_PARSE_RETRIES:
                    self.logger.warning(
                        f"JSON parse failed (attempt {attempt}/{MAX_JSON_PARSE_RETRIES + 1}), "
                        f"retrying..."
                    )
                    continue

                # No more retries, return the error
                return result

            except Exception as e:
                self.logger.error(f"Page OCR failed: {e}")
                return PageResult.from_error(error=f"OCR failed: {e}")

        # Should not reach here, but just in case
        return PageResult.from_error(error=last_error or "Unknown error")

    def _parse_page_response(self, response_text: str) -> PageResult:
        """
        Parse OCR JSON response into structured PageResult.

        Args:
            response_text: Raw JSON response from vision model.

        Returns:
            PageResult with page_number, chapter, full_text, and annotations.
        """
        data = extract_json_from_response(response_text)

        if not data or not isinstance(data, dict):
            self.logger.error("Failed to parse OCR response as JSON")
            return PageResult.from_error(error="Failed to parse OCR response as JSON")

        # Extract page number
        page_number = data.get("page_number")
        is_spread = data.get("is_two_page_spread", False)
        spread_pages = data.get("spread_pages")

        # For two-page spreads, use first page number
        if is_spread and spread_pages:
            page_number = spread_pages[0] if spread_pages else None
            self.logger.info(f"Two-page spread detected: pages {spread_pages}")

        # Extract chapter info
        chapter_data = data.get("chapter")
        chapter_info: Optional[ChapterInfo] = None
        if chapter_data and isinstance(chapter_data, dict):
            chapter_info = ChapterInfo(
                number=chapter_data.get("number"),
                title=chapter_data.get("title"),
                location=chapter_data.get("location"),
            )
            self.logger.info(
                f"Chapter detected: {chapter_info.number} - {chapter_info.title}"
            )

        # Process annotations
        annotations = []

        # Process highlights
        for h in data.get("highlights", []):
            if not isinstance(h, dict):
                continue
            text = h.get("text", "").strip()
            if text:
                annotations.append(
                    Annotation(
                        type=AnnotationType.DIGITAL_HIGHLIGHT,  # Physical highlight in book
                        content=text,
                        page_number=None,  # Set later after page ordering
                        position={
                            "location": h.get("location"),
                            "style": h.get("type"),
                        },
                    )
                )

        # Process margin notes
        for note in data.get("margin_notes", []):
            if not isinstance(note, dict):
                continue
            text = note.get("text", "").strip()
            if text:
                annotations.append(
                    Annotation(
                        type=AnnotationType.HANDWRITTEN_NOTE,
                        content=text,
                        page_number=None,  # Set later after page ordering
                        context=note.get("related_text"),
                        position={
                            "location": note.get("location"),
                            "note_type": note.get("type"),
                        },
                    )
                )

        return PageResult(
            page_number=page_number,
            page_number_location=data.get("page_number_location"),
            chapter=chapter_info,
            is_two_page_spread=is_spread,
            spread_pages=spread_pages,
            full_text=data.get("full_text", ""),
            annotations=annotations,
        )

    async def _infer_metadata(self, first_page_text: str) -> BookMetadata:
        """
        Infer book metadata from page text using LLM.

        Analyzes the first page(s) to extract:
        - Book title (from headers, title pages, running headers)
        - Author name(s) (from title pages or headers)
        - ISBN (if visible on copyright pages)

        Args:
            first_page_text: Text from the first page(s) of the book.

        Returns:
            BookMetadata with title, authors, and optionally isbn.
            Returns default BookMetadata if text_model is not configured or extraction fails.
        """
        if not first_page_text or not self.text_model:
            self.logger.debug("Metadata inference skipped - no text or model")
            return BookMetadata()  # Not an error, just no inference attempted

        # Limit text length to avoid excessive token usage
        page_text = first_page_text[:METADATA_TEXT_LIMIT]
        if len(first_page_text) > METADATA_TEXT_LIMIT:
            page_text += "\n[...truncated...]"

        system_prompt = """You are a librarian assistant that identifies books from page text.

Your task is to extract book metadata from the provided text, which comes from scanned book pages.

Look for:
1. Book title - often in headers, title pages, or running headers
2. Author name(s) - may appear on title pages or in headers
3. ISBN - if visible (usually on copyright pages)

You MUST respond with valid JSON in this exact format:
{
  "title": "The Book Title" or null if not found,
  "authors": ["Author Name"] or [] if not found,
  "isbn": "978-0-123456-78-9" or null if not found,
  "confidence": "high" | "medium" | "low"
}

Only include information you can actually see in the text. Do NOT guess or make up information.
If you cannot determine a field with reasonable confidence, use null or empty array."""

        user_prompt = f"""Extract book metadata from this page text:

---
{page_text}
---

Respond with JSON containing title, authors, isbn, and confidence level."""

        try:
            self.logger.debug(f"Inferring book metadata with {self.text_model}")

            client = get_llm_client()
            messages = build_messages(user_prompt, system_prompt)
            response_text, usage = await client.complete(
                operation=PipelineOperation.METADATA_INFERENCE,
                messages=messages,
                model=self.text_model,
                max_tokens=METADATA_MAX_TOKENS,
                temperature=METADATA_TEMPERATURE,
                json_mode=True,
                pipeline=self.PIPELINE_NAME,
                content_id=getattr(self, "_content_id", None),
            )

            # Track usage (thread-safe)
            async with self._usage_lock:
                self._usage_records.append(usage)

            # Parse the JSON response
            try:
                result = json.loads(response_text)

                # Extract title
                title = DEFAULT_BOOK_TITLE
                raw_title = result.get("title")
                if raw_title and isinstance(raw_title, str) and raw_title.strip():
                    title = raw_title.strip()

                # Extract authors
                authors: list[str] = []
                raw_authors = result.get("authors", [])
                if raw_authors and isinstance(raw_authors, list):
                    authors = [
                        a.strip()
                        for a in raw_authors
                        if isinstance(a, str) and a.strip()
                    ]

                # Extract ISBN
                isbn: Optional[str] = None
                raw_isbn = result.get("isbn")
                if raw_isbn and isinstance(raw_isbn, str) and raw_isbn.strip():
                    isbn = raw_isbn.strip()

                confidence = result.get("confidence", "unknown")
                self.logger.info(
                    f"Metadata inferred (confidence: {confidence}): "
                    f"title='{title}', authors={authors}"
                )

                return BookMetadata(
                    title=title,
                    authors=authors,
                    isbn=isbn,
                    inferred=True,
                )

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse metadata JSON: {e}")
                return BookMetadata(inference_error=f"JSON parse error: {e}")

        except Exception as e:
            self.logger.warning(f"Metadata inference failed: {e}")
            return BookMetadata(inference_error=str(e))
