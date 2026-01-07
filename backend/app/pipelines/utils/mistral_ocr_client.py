"""
Mistral OCR Client for PDF Document Processing

A dedicated client for Mistral's OCR API that provides thorough PDF document
processing with support for:
- Full document OCR with markdown output
- Document-level annotations (title, authors, summary, languages)
- Image-level annotations (type classification, descriptions)
- Base64 image extraction from documents
- Cost tracking and usage metrics

This client uses the Mistral SDK directly for full control over the OCR API,
unlike the generic VLM client which uses LiteLLM for vision chat models.

Usage:
    from app.pipelines.utils.mistral_ocr_client import (
        ocr_pdf_document,
        ocr_pdf_document_annotated,
        MistralOCRResult,
    )

    # Basic OCR
    result = await ocr_pdf_document(Path("document.pdf"))
    print(result.full_text)

    # OCR with annotations (handles any number of pages)
    result = await ocr_pdf_document_annotated(
        Path("document.pdf"),
        include_images=True,
    )
    print(result.document_annotation)
    for page in result.pages:
        for img in page.images:
            print(img.annotation)

Requirements:
    pip install mistralai>=1.2.0  # For annotation support
"""

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
from mistralai import Mistral
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.models.llm_usage import LLMUsage, create_error_usage

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MODEL = "mistral-ocr-latest"
MAX_ANNOTATED_PAGES = 8  # Document annotations limited to 8 pages by Mistral API


def _normalize_model_name(model: str) -> str:
    """
    Normalize model name for Mistral SDK.

    Strips 'mistral/' prefix if present since the Mistral SDK expects
    just 'mistral-ocr-latest', not 'mistral/mistral-ocr-latest'
    (the prefix is a LiteLLM convention).
    """
    if model.startswith("mistral/"):
        return model[len("mistral/") :]
    return model


# Mistral OCR pricing (as of 2024) - USD per 1000 pages
# Note: Mistral API does not return cost directly, so we calculate it
MISTRAL_OCR_COST_PER_1000_PAGES = 1.00  # $1.00 per 1000 pages


# =============================================================================
# Annotation Schema Models (for structured output)
# =============================================================================


class ImageType(str, Enum):
    """Types of images that can be detected in documents."""

    GRAPH = "graph"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class ImageAnnotationSchema(BaseModel):
    """Schema for annotating bounding box images in OCR output."""

    image_type: ImageType = Field(
        ...,
        description="The type of the image. Must be one of 'graph', 'text', 'table' or 'image'.",
    )
    description: str = Field(
        ...,
        description="A detailed description of the image content.",
    )


class DocumentAnnotationSchema(BaseModel):
    """Schema for annotating the entire document in OCR output."""

    languages: list[str] = Field(
        ...,
        description="The list of languages present in the document in ISO 639-1 code format (e.g., 'en', 'fr').",
    )
    authors: list[str] = Field(
        default_factory=list,
        description="Authors of the document if identifiable.",
    )
    title: str = Field(
        default="",
        description="The title of the document if identifiable.",
    )
    summary: str = Field(
        ...,
        description="A comprehensive summary of the document content.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Main topics or keywords extracted from the document.",
    )


# =============================================================================
# Result Data Classes
# =============================================================================


@dataclass
class ImageInfo:
    """Information about an image detected in a page."""

    id: str
    top_left_x: Optional[float] = None
    top_left_y: Optional[float] = None
    bottom_right_x: Optional[float] = None
    bottom_right_y: Optional[float] = None
    image_base64: Optional[str] = None
    annotation: Optional[dict[str, Any]] = None

    @property
    def has_bbox(self) -> bool:
        """Check if bounding box coordinates are available."""
        return all(
            v is not None
            for v in [
                self.top_left_x,
                self.top_left_y,
                self.bottom_right_x,
                self.bottom_right_y,
            ]
        )

    @property
    def bbox(self) -> Optional[tuple[float, float, float, float]]:
        """Get bounding box as tuple (x1, y1, x2, y2)."""
        if self.has_bbox:
            return (
                self.top_left_x,
                self.top_left_y,
                self.bottom_right_x,
                self.bottom_right_y,
            )
        return None


@dataclass
class OCRPage:
    """Represents a single page from OCR processing."""

    index: int
    markdown: str
    images: list[ImageInfo] = field(default_factory=list)

    @property
    def image_count(self) -> int:
        """Number of images detected on this page."""
        return len(self.images)

    @property
    def char_count(self) -> int:
        """Number of characters in the markdown text."""
        return len(self.markdown)


@dataclass
class DocumentAnnotation:
    """Parsed document-level annotation."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    summary: str = ""
    topics: list[str] = field(default_factory=list)
    raw: Optional[str] = None  # Original JSON string if parsing failed

    @classmethod
    def from_json(cls, json_str: str) -> "DocumentAnnotation":
        """Parse document annotation from JSON string."""
        try:
            data = json.loads(json_str)
            return cls(
                title=data.get("title", ""),
                authors=data.get("authors", []),
                languages=data.get("languages", []),
                summary=data.get("summary", ""),
                topics=data.get("topics", []),
            )
        except (json.JSONDecodeError, TypeError):
            return cls(raw=json_str)


@dataclass
class MistralOCRResult:
    """Complete result from Mistral OCR processing."""

    pages: list[OCRPage]
    full_text: str
    full_markdown: str  # Markdown with page separators
    document_annotation: Optional[DocumentAnnotation] = None
    usage: Optional[LLMUsage] = None
    model: str = DEFAULT_MODEL
    processing_time_ms: int = 0

    @property
    def page_count(self) -> int:
        """Number of pages processed."""
        return len(self.pages)

    @property
    def total_images(self) -> int:
        """Total number of images across all pages."""
        return sum(page.image_count for page in self.pages)

    @property
    def total_chars(self) -> int:
        """Total character count across all pages."""
        return sum(page.char_count for page in self.pages)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "page_count": self.page_count,
            "total_images": self.total_images,
            "total_chars": self.total_chars,
            "processing_time_ms": self.processing_time_ms,
            "document_annotation": (
                {
                    "title": self.document_annotation.title,
                    "authors": self.document_annotation.authors,
                    "languages": self.document_annotation.languages,
                    "summary": self.document_annotation.summary,
                    "topics": self.document_annotation.topics,
                }
                if self.document_annotation
                else None
            ),
            "pages": [
                {
                    "index": page.index,
                    "char_count": page.char_count,
                    "image_count": page.image_count,
                    "images": [
                        {
                            "id": img.id,
                            "bbox": img.bbox,
                            "annotation": img.annotation,
                            "has_image_data": img.image_base64 is not None,
                        }
                        for img in page.images
                    ],
                }
                for page in self.pages
            ],
            "usage": (
                {
                    "cost_usd": self.usage.cost_usd,
                    "latency_ms": self.usage.latency_ms,
                    "pages_processed": self.usage.prompt_tokens,
                }
                if self.usage
                else None
            ),
        }

    def save_json(self, output_path: Path) -> None:
        """Save result metadata to JSON file (without base64 images)."""
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def save_markdown(self, output_path: Path, include_images: bool = False) -> None:
        """
        Save result to markdown file.

        Args:
            output_path: Path to save the markdown file.
            include_images: If True, embed base64 images in markdown.
        """
        import re

        content = self.full_markdown

        # Add document annotation header if available
        if self.document_annotation and self.document_annotation.title:
            header = f"# {self.document_annotation.title}\n\n"
            if self.document_annotation.authors:
                header += (
                    f"**Authors:** {', '.join(self.document_annotation.authors)}\n\n"
                )
            if self.document_annotation.summary:
                header += f"**Summary:** {self.document_annotation.summary}\n\n"
            if self.document_annotation.languages:
                header += f"**Languages:** {', '.join(self.document_annotation.languages)}\n\n"
            header += "---\n\n"
            content = header + content

        # Remove base64 images if not requested
        if not include_images:
            content = re.sub(
                r"!\[([^\]]*)\]\(data:image[^)]+\)",
                r"![\1](image_removed)",
                content,
            )

        with open(output_path, "w") as f:
            f.write(content)


# =============================================================================
# Helper Functions
# =============================================================================


def _response_format_from_pydantic_model(model: type[BaseModel]) -> dict:
    """Convert a Pydantic model to a response format for Mistral API."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "schema": model.model_json_schema(),
        },
    }


def _encode_pdf_to_base64(pdf_path: Path) -> str:
    """Encode a PDF file to base64 string."""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _replace_images_in_markdown(markdown: str, images: list[ImageInfo]) -> str:
    """Replace image placeholders with base64 data URLs."""
    for img in images:
        if img.image_base64:
            markdown = markdown.replace(
                f"![{img.id}]({img.id})",
                f"![{img.id}](data:image/png;base64,{img.image_base64})",
            )
    return markdown


def _calculate_cost(pages_processed: int) -> float:
    """Calculate cost based on pages processed."""
    return (pages_processed / 1000) * MISTRAL_OCR_COST_PER_1000_PAGES


def _extract_usage(
    response: Any,
    model: str,
    latency_ms: int,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> LLMUsage:
    """
    Extract usage information from Mistral OCR response.

    Note: Mistral OCR API returns usage_info with pages_processed but does not
    return cost directly. Cost is calculated based on published pricing.
    """
    pages_processed = 0

    # Extract pages processed from usage_info
    if hasattr(response, "usage_info") and response.usage_info:
        usage_info = response.usage_info
        if hasattr(usage_info, "pages_processed"):
            pages_processed = usage_info.pages_processed

    # Calculate cost based on pages
    cost_usd = _calculate_cost(pages_processed) if pages_processed > 0 else None

    return LLMUsage(
        model=model,
        request_type="ocr",
        latency_ms=latency_ms,
        prompt_tokens=pages_processed,  # Store pages_processed in prompt_tokens
        cost_usd=cost_usd,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )


def _parse_ocr_response(
    response: Any,
    include_images: bool = False,
) -> tuple[list[OCRPage], Optional[DocumentAnnotation]]:
    """Parse Mistral OCR response into structured data."""
    pages: list[OCRPage] = []
    doc_annotation: Optional[DocumentAnnotation] = None

    # Parse pages
    if hasattr(response, "pages") and response.pages:
        for page in response.pages:
            page_index = getattr(page, "index", len(pages))
            page_markdown = getattr(page, "markdown", "") or ""

            # Parse images
            page_images: list[ImageInfo] = []
            if hasattr(page, "images") and page.images:
                for img in page.images:
                    img_info = ImageInfo(id=getattr(img, "id", ""))

                    # Extract bounding box
                    for coord in [
                        "top_left_x",
                        "top_left_y",
                        "bottom_right_x",
                        "bottom_right_y",
                    ]:
                        if hasattr(img, coord):
                            setattr(img_info, coord, getattr(img, coord))

                    # Extract image annotation
                    if hasattr(img, "image_annotation") and img.image_annotation:
                        try:
                            if isinstance(img.image_annotation, str):
                                img_info.annotation = json.loads(img.image_annotation)
                            else:
                                img_info.annotation = img.image_annotation
                        except (json.JSONDecodeError, TypeError):
                            img_info.annotation = {"raw": str(img.image_annotation)}

                    # Include base64 image data if requested
                    if include_images and hasattr(img, "image_base64"):
                        img_info.image_base64 = img.image_base64

                    page_images.append(img_info)

            pages.append(
                OCRPage(
                    index=page_index,
                    markdown=page_markdown,
                    images=page_images,
                )
            )

    # Parse document annotation
    if hasattr(response, "document_annotation") and response.document_annotation:
        doc_annotation = DocumentAnnotation.from_json(response.document_annotation)

    return pages, doc_annotation


def _get_pdf_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF using PyMuPDF."""
    with fitz.open(pdf_path) as doc:
        return len(doc)


def get_mistral_client() -> Mistral:
    """Get or create Mistral client instance using API key from settings."""
    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY not configured in settings. "
            "Set it in your .env file: MISTRAL_API_KEY='your-api-key'"
        )
    return Mistral(api_key=api_key)


# =============================================================================
# Public API - Basic OCR
# =============================================================================


async def ocr_pdf_document(
    pdf_path: Path,
    model: str = DEFAULT_MODEL,
    pages: Optional[list[int]] = None,
    include_images: bool = False,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> MistralOCRResult:
    """
    Process a PDF document using Mistral OCR (basic mode).

    Extracts text from all pages with markdown formatting. Does not include
    document-level or image-level annotations (for that use
    ocr_pdf_document_annotated instead).

    Args:
        pdf_path: Path to the PDF file.
        model: Mistral OCR model to use. Defaults to "mistral-ocr-latest".
        pages: Optional list of 0-indexed page numbers to process.
               If None, processes all pages.
        include_images: Whether to include base64-encoded images in response.
        pipeline: Name of calling pipeline for cost attribution.
        content_id: Associated content ID for cost attribution.
        operation: Specific operation name for tracking.

    Returns:
        MistralOCRResult containing pages, full text, and usage info.

    Example:
        >>> result = await ocr_pdf_document(Path("paper.pdf"))
        >>> print(f"Extracted {result.page_count} pages, {result.total_chars} chars")
        >>> print(result.full_text)
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Normalize model name (strip mistral/ prefix for native SDK)
    model = _normalize_model_name(model)

    client = get_mistral_client()
    base64_pdf = _encode_pdf_to_base64(pdf_path)

    document = {
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}",
    }

    # Build kwargs
    kwargs: dict[str, Any] = {
        "model": model,
        "document": document,
        "include_image_base64": include_images,
    }
    if pages is not None:
        kwargs["pages"] = pages

    logger.info(f"Starting Mistral OCR (basic) on {pdf_path.name}")
    start_time = time.perf_counter()

    try:
        # Run OCR in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.ocr.process(**kwargs),
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response
        ocr_pages, _ = _parse_ocr_response(response, include_images)

        # Build full text with page markers
        text_parts = []
        markdown_parts = []
        for page in ocr_pages:
            if page.markdown:
                text_parts.append(page.markdown)
                markdown_parts.append(f"[Page {page.index + 1}]\n\n{page.markdown}")

                # Replace image placeholders if images included
                if include_images:
                    markdown_parts[-1] = _replace_images_in_markdown(
                        markdown_parts[-1], page.images
                    )

        # Extract usage
        usage = _extract_usage(
            response=response,
            model=model,
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        logger.info(
            f"Mistral OCR complete: {len(ocr_pages)} pages, "
            f"{sum(p.char_count for p in ocr_pages)} chars, "
            f"{latency_ms}ms"
        )

        return MistralOCRResult(
            pages=ocr_pages,
            full_text="\n\n".join(text_parts),
            full_markdown="\n\n---\n\n".join(markdown_parts),
            document_annotation=None,
            usage=usage,
            model=model,
            processing_time_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        create_error_usage(
            model=model,
            request_type="ocr",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Mistral OCR failed: {e}")
        raise


# =============================================================================
# Public API - Annotated OCR
# =============================================================================


async def ocr_pdf_document_annotated(
    pdf_path: Path,
    model: str = DEFAULT_MODEL,
    include_images: bool = True,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> MistralOCRResult:
    """
    Process a PDF document using Mistral OCR with full annotations.

    Extracts text with:
    - Document-level annotations (title, authors, summary, languages, topics)
    - Image-level annotations (type classification, descriptions) on ALL pages
    - Base64-encoded images (optional)

    For documents with more than 8 pages:
    - First 8 pages: document annotation + image annotations
    - Remaining pages: image annotations only (Mistral API limits document
      annotation to 8 pages, but image annotations work on all pages)
    - Results are combined into a single MistralOCRResult

    Args:
        pdf_path: Path to the PDF file.
        model: Mistral OCR model to use. Defaults to "mistral-ocr-latest".
        include_images: Whether to include base64-encoded images.
        pipeline: Name of calling pipeline for cost attribution.
        content_id: Associated content ID for cost attribution.
        operation: Specific operation name for tracking.

    Returns:
        MistralOCRResult with full annotations including document metadata.

    Example:
        >>> result = await ocr_pdf_document_annotated(Path("paper.pdf"))
        >>> print(f"Title: {result.document_annotation.title}")
        >>> print(f"Authors: {result.document_annotation.authors}")
        >>> print(f"Summary: {result.document_annotation.summary}")
        >>> print(f"Total pages: {result.page_count}")
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Determine total page count
    total_pages = _get_pdf_page_count(pdf_path)

    # If document has <= 8 pages, process all with annotations
    if total_pages <= MAX_ANNOTATED_PAGES:
        return await _ocr_with_annotations(
            pdf_path=pdf_path,
            model=model,
            page_indices=None,  # Process all pages
            include_images=include_images,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

    # For documents > 8 pages, process in two batches
    logger.info(
        f"Document has {total_pages} pages. Processing first {MAX_ANNOTATED_PAGES} "
        f"with full annotations, remaining {total_pages - MAX_ANNOTATED_PAGES} with image annotations only."
    )

    start_time = time.perf_counter()

    # Process first 8 pages with annotations
    annotated_result = await _ocr_with_annotations(
        pdf_path=pdf_path,
        model=model,
        page_indices=list(range(MAX_ANNOTATED_PAGES)),
        include_images=include_images,
        pipeline=pipeline,
        content_id=content_id,
        operation=f"{operation}_annotated" if operation else "annotated_pages",
    )

    # Process remaining pages with image annotations only (no document annotation)
    remaining_pages = list(range(MAX_ANNOTATED_PAGES, total_pages))
    remaining_result = await _ocr_basic(
        pdf_path=pdf_path,
        model=model,
        page_indices=remaining_pages,
        include_images=include_images,
        pipeline=pipeline,
        content_id=content_id,
        operation=f"{operation}_remaining" if operation else "remaining_pages",
    )

    total_latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Combine results
    all_pages = annotated_result.pages + remaining_result.pages

    # Build combined text
    text_parts = []
    markdown_parts = []
    for page in all_pages:
        if page.markdown:
            text_parts.append(page.markdown)
            page_md = f"[Page {page.index + 1}]\n\n{page.markdown}"

            # Add image annotations for annotated pages
            if page.index < MAX_ANNOTATED_PAGES:
                for img in page.images:
                    if img.annotation:
                        img_type = img.annotation.get("image_type", "unknown")
                        img_desc = img.annotation.get("description", "")
                        page_md = page_md.replace(
                            f"![{img.id}]({img.id})",
                            f"![{img.id}]({img.id})\n\n"
                            f"**[{img_type.upper()}]** {img_desc}",
                        )

            # Replace image placeholders with base64 if available
            if include_images:
                page_md = _replace_images_in_markdown(page_md, page.images)

            markdown_parts.append(page_md)

    # Combine usage
    combined_usage = LLMUsage(
        model=model,
        request_type="ocr",
        latency_ms=total_latency_ms,
        prompt_tokens=(
            (annotated_result.usage.prompt_tokens or 0)
            + (remaining_result.usage.prompt_tokens or 0)
            if annotated_result.usage and remaining_result.usage
            else None
        ),
        cost_usd=(
            (annotated_result.usage.cost_usd or 0)
            + (remaining_result.usage.cost_usd or 0)
            if annotated_result.usage and remaining_result.usage
            else None
        ),
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )

    logger.info(
        f"Mistral OCR (annotated) complete: "
        f"Title='{annotated_result.document_annotation.title if annotated_result.document_annotation else 'N/A'}', "
        f"{len(all_pages)} pages total, {total_latency_ms}ms"
    )

    return MistralOCRResult(
        pages=all_pages,
        full_text="\n\n".join(text_parts),
        full_markdown="\n\n---\n\n".join(markdown_parts),
        document_annotation=annotated_result.document_annotation,
        usage=combined_usage,
        model=model,
        processing_time_ms=total_latency_ms,
    )


async def _ocr_with_annotations(
    pdf_path: Path,
    model: str,
    page_indices: Optional[list[int]],
    include_images: bool,
    pipeline: Optional[str],
    content_id: Optional[int],
    operation: Optional[str],
) -> MistralOCRResult:
    """Internal: Process PDF pages with annotation support."""
    # Normalize model name (strip mistral/ prefix for native SDK)
    model = _normalize_model_name(model)

    client = get_mistral_client()
    base64_pdf = _encode_pdf_to_base64(pdf_path)

    document = {
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}",
    }

    logger.info(
        f"Starting Mistral OCR (annotated) on {pdf_path.name} "
        f"(pages: {page_indices if page_indices else 'all'})"
    )
    start_time = time.perf_counter()

    try:
        loop = asyncio.get_event_loop()

        # Build base kwargs
        # Note: bbox_annotation_format and document_annotation_format were removed
        # in mistralai SDK 1.5.x. Annotations are no longer supported via the SDK.
        base_kwargs: dict[str, Any] = {
            "model": model,
            "document": document,
            "include_image_base64": include_images,
        }
        if page_indices is not None:
            base_kwargs["pages"] = page_indices

        response = await loop.run_in_executor(
            None,
            lambda: client.ocr.process(**base_kwargs),
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response
        ocr_pages, doc_annotation = _parse_ocr_response(response, include_images)

        # Build full text with page markers
        text_parts = []
        markdown_parts = []

        for page in ocr_pages:
            if page.markdown:
                text_parts.append(page.markdown)
                page_md = f"[Page {page.index + 1}]\n\n{page.markdown}"

                # Add image annotations as markdown
                for img in page.images:
                    if img.annotation:
                        img_type = img.annotation.get("image_type", "unknown")
                        img_desc = img.annotation.get("description", "")
                        page_md = page_md.replace(
                            f"![{img.id}]({img.id})",
                            f"![{img.id}]({img.id})\n\n"
                            f"**[{img_type.upper()}]** {img_desc}",
                        )

                # Replace image placeholders with base64 if available
                if include_images:
                    page_md = _replace_images_in_markdown(page_md, page.images)

                markdown_parts.append(page_md)

        # Extract usage
        usage = _extract_usage(
            response=response,
            model=model,
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        if doc_annotation:
            logger.info(
                f"Mistral OCR (annotated) batch complete: "
                f"Title='{doc_annotation.title}', "
                f"Authors={doc_annotation.authors}, "
                f"{len(ocr_pages)} pages, {latency_ms}ms"
            )
        else:
            logger.info(
                f"Mistral OCR (annotated) batch complete: "
                f"{len(ocr_pages)} pages, {latency_ms}ms (no doc annotation)"
            )

        return MistralOCRResult(
            pages=ocr_pages,
            full_text="\n\n".join(text_parts),
            full_markdown="\n\n---\n\n".join(markdown_parts),
            document_annotation=doc_annotation,
            usage=usage,
            model=model,
            processing_time_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        create_error_usage(
            model=model,
            request_type="ocr",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Mistral OCR (annotated) failed: {e}")
        raise


async def _ocr_basic(
    pdf_path: Path,
    model: str,
    page_indices: list[int],
    include_images: bool,
    pipeline: Optional[str],
    content_id: Optional[int],
    operation: Optional[str],
) -> MistralOCRResult:
    """Internal: Process PDF pages with image annotations (no document annotation)."""
    # Normalize model name (strip mistral/ prefix for native SDK)
    model = _normalize_model_name(model)

    client = get_mistral_client()
    base64_pdf = _encode_pdf_to_base64(pdf_path)

    document = {
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}",
    }

    logger.info(
        f"Starting Mistral OCR (basic) on {pdf_path.name} "
        f"(pages: {page_indices[0]}-{page_indices[-1]})"
    )
    start_time = time.perf_counter()

    try:
        loop = asyncio.get_event_loop()

        # Note: bbox_annotation_format was removed in mistralai SDK 1.5.x
        response = await loop.run_in_executor(
            None,
            lambda: client.ocr.process(
                model=model,
                document=document,
                pages=page_indices,
                include_image_base64=include_images,
            ),
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response
        ocr_pages, _ = _parse_ocr_response(response, include_images)

        # Build full text with page markers
        text_parts = []
        markdown_parts = []
        for page in ocr_pages:
            if page.markdown:
                text_parts.append(page.markdown)
                page_md = f"[Page {page.index + 1}]\n\n{page.markdown}"

                # Add image annotations as markdown
                for img in page.images:
                    if img.annotation:
                        img_type = img.annotation.get("image_type", "unknown")
                        img_desc = img.annotation.get("description", "")
                        page_md = page_md.replace(
                            f"![{img.id}]({img.id})",
                            f"![{img.id}]({img.id})\n\n"
                            f"**[{img_type.upper()}]** {img_desc}",
                        )

                # Replace image placeholders with base64 if available
                if include_images:
                    page_md = _replace_images_in_markdown(page_md, page.images)

                markdown_parts.append(page_md)

        # Extract usage
        usage = _extract_usage(
            response=response,
            model=model,
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        logger.info(
            f"Mistral OCR (basic) batch complete: "
            f"{len(ocr_pages)} pages, {latency_ms}ms"
        )

        return MistralOCRResult(
            pages=ocr_pages,
            full_text="\n\n".join(text_parts),
            full_markdown="\n\n---\n\n".join(markdown_parts),
            document_annotation=None,
            usage=usage,
            model=model,
            processing_time_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        create_error_usage(
            model=model,
            request_type="ocr",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Mistral OCR (basic) failed: {e}")
        raise


# =============================================================================
# Public API - Synchronous Wrappers
# =============================================================================


def ocr_pdf_document_sync(
    pdf_path: Path,
    model: str = DEFAULT_MODEL,
    pages: Optional[list[int]] = None,
    include_images: bool = False,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> MistralOCRResult:
    """
    Synchronous wrapper for ocr_pdf_document.

    See ocr_pdf_document for full documentation.
    """
    return asyncio.get_event_loop().run_until_complete(
        ocr_pdf_document(
            pdf_path=pdf_path,
            model=model,
            pages=pages,
            include_images=include_images,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
    )


def ocr_pdf_document_annotated_sync(
    pdf_path: Path,
    model: str = DEFAULT_MODEL,
    include_images: bool = True,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> MistralOCRResult:
    """
    Synchronous wrapper for ocr_pdf_document_annotated.

    See ocr_pdf_document_annotated for full documentation.
    """
    return asyncio.get_event_loop().run_until_complete(
        ocr_pdf_document_annotated(
            pdf_path=pdf_path,
            model=model,
            include_images=include_images,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def get_default_ocr_model() -> str:
    """Get the default Mistral OCR model from settings."""
    return settings.OCR_MODEL or DEFAULT_MODEL


async def ocr_image(
    image_path: Path,
    model: str = DEFAULT_MODEL,
    include_annotation: bool = True,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, Optional[dict[str, Any]], LLMUsage]:
    """
    Process a single image using Mistral OCR.

    Args:
        image_path: Path to the image file.
        model: Mistral OCR model to use.
        include_annotation: Whether to request image annotation.
        pipeline: Pipeline name for cost tracking.
        content_id: Content ID for cost tracking.
        operation: Operation name for cost tracking.

    Returns:
        Tuple of (markdown_text, annotation_dict, usage).
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Normalize model name (strip mistral/ prefix for native SDK)
    model = _normalize_model_name(model)

    # Determine MIME type
    suffix = image_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    mime_type = mime_types.get(suffix, "image/png")

    # Encode image
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    client = get_mistral_client()

    document = {
        "type": "image_url",
        "image_url": f"data:{mime_type};base64,{image_base64}",
    }

    # Note: bbox_annotation_format was removed in mistralai SDK 1.5.x
    # Annotations are no longer supported via the SDK
    kwargs: dict[str, Any] = {
        "model": model,
        "document": document,
    }

    start_time = time.perf_counter()

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.ocr.process(**kwargs),
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract text and annotation
        markdown = ""
        annotation = None

        if hasattr(response, "pages") and response.pages:
            page = response.pages[0]
            markdown = getattr(page, "markdown", "") or ""

            if hasattr(page, "images") and page.images:
                for img in page.images:
                    if hasattr(img, "image_annotation") and img.image_annotation:
                        try:
                            if isinstance(img.image_annotation, str):
                                annotation = json.loads(img.image_annotation)
                            else:
                                annotation = img.image_annotation
                        except (json.JSONDecodeError, TypeError):
                            annotation = {"raw": str(img.image_annotation)}
                        break

        usage = _extract_usage(
            response=response,
            model=model,
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        return markdown, annotation, usage

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        create_error_usage(
            model=model,
            request_type="ocr",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        raise
