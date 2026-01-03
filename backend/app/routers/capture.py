"""
Quick Capture API Router

Low-friction capture endpoints for ideas, URLs, photos, voice memos, PDFs, and books.
All endpoints return immediately after queueing for background processing.

Endpoints:
- POST /api/capture/text - Quick text/idea capture
- POST /api/capture/url - URL/article capture
- POST /api/capture/photo - Photo capture for OCR (single image)
- POST /api/capture/voice - Voice memo capture
- POST /api/capture/pdf - PDF document upload
- POST /api/capture/book - Batch book page capture (multiple images)

Usage:
    # Text capture
    curl -X POST /api/capture/text -F "content=My idea" -F "title=Optional title"

    # URL capture
    curl -X POST /api/capture/url -F "url=https://example.com" -F "notes=Why I saved this"

    # Photo capture (single)
    curl -X POST /api/capture/photo -F "file=@page.jpg" -F "capture_type=book_page"

    # Book capture (batch)
    curl -X POST /api/capture/book -F "files=@p1.jpg" -F "files=@p2.jpg" -F "title=Deep Work"
"""

from datetime import datetime
from typing import Optional
import re

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
import httpx

from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.pipelines.base import PipelineContentType
from app.services.storage import save_upload, save_content
from app.services.tasks import process_book, process_content, process_content_high

router = APIRouter(prefix="/api/capture", tags=["capture"])


@router.post("/text")
async def capture_text(
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="Text content to capture"),
    title: Optional[str] = Form(None, description="Optional title"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """
    Quick text capture for ideas, notes, and thoughts.

    Immediately queues content for processing and returns.
    Processing includes: LLM tagging, Obsidian note creation, knowledge graph.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        content: The text content to capture (required).
        title: Optional title for the note. If not provided, generated from content.
        tags: Optional comma-separated list of tags (e.g., "idea,work,urgent").

    Returns:
        dict: Response containing status, content ID, title, and processing message.
    """
    # Generate title if not provided
    if not title:
        title = _generate_title(content)

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    ucf = UnifiedContent(
        source_type=ContentType.IDEA,
        title=title,
        created_at=datetime.now(),
        full_text=content,
        tags=tag_list,
    )

    # Save to database
    await save_content(ucf)

    # For text/idea capture, no pipeline processing needed - content is already saved
    # Future: could queue for LLM tagging task here

    return {
        "status": "captured",
        "id": ucf.id,
        "title": title,
        "message": "Content saved successfully",
    }


@router.post("/url")
async def capture_url(
    background_tasks: BackgroundTasks,
    url: str = Form(..., description="URL to capture"),
    notes: Optional[str] = Form(None, description="Optional notes about this URL"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """
    Capture a URL for later processing.

    Fetches page title immediately, then queues full content
    extraction for background processing.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        url: The URL to capture (must start with http:// or https://).
        notes: Optional notes about why this URL was saved or key takeaways.
        tags: Optional comma-separated list of tags (e.g., "article,ai,research").

    Returns:
        dict: Response containing status, content ID, title, URL, and processing message.

    Raises:
        HTTPException: 400 if URL doesn't start with http:// or https://.
    """
    # Validate URL
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Invalid URL - must start with http:// or https://")

    # Fetch page title
    title = await _fetch_page_title(url)

    # Create annotations from notes
    annotations = []
    if notes:
        annotations.append(
            Annotation(
                type=AnnotationType.TYPED_COMMENT,
                content=notes,
            )
        )

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    ucf = UnifiedContent(
        source_type=ContentType.ARTICLE,
        source_url=url,
        title=title,
        created_at=datetime.now(),
        full_text="",  # Will be fetched during processing
        annotations=annotations,
        tags=tag_list,
    )

    await save_content(ucf)

    # Queue for article extraction pipeline
    background_tasks.add_task(
        process_content.delay,
        ucf.id,
        PipelineContentType.ARTICLE.value,
        None,       # source_path
        url,        # source_url
    )

    return {
        "status": "captured",
        "id": ucf.id,
        "title": title,
        "url": url,
        "message": "URL queued for content extraction",
    }


@router.post("/photo")
async def capture_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Photo file"),
    capture_type: str = Form(
        "general", description="Type: book_page, whiteboard, document, or general"
    ),
    notes: Optional[str] = Form(None, description="Optional notes"),
    book_title: Optional[str] = Form(None, description="Book title if known"),
):
    """
    Capture a photo for OCR processing.

    Supports book pages, whiteboards, documents, and general photos.
    Uses Vision LLM for text and handwriting extraction.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        file: The image file to process (JPEG, PNG, etc.).
        capture_type: Type of photo being captured. Options:
            - "book_page": Page from a physical book with potential margin notes.
            - "whiteboard": Whiteboard or blackboard photo.
            - "document": Printed document or form.
            - "general": General photo with text (default).
        notes: Optional notes or context about the photo.
        book_title: Book title if capture_type is "book_page".

    Returns:
        dict: Response containing status, content ID, file path, capture type,
              and processing message.

    Raises:
        HTTPException: 400 if file is not an image.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    # Save file
    file_path = await save_upload(file, directory="photos")

    # Determine content type based on capture type
    content_type = ContentType.IDEA
    if capture_type == "book_page":
        content_type = ContentType.BOOK

    # Create annotations from notes
    annotations = []
    if notes:
        annotations.append(
            Annotation(
                type=AnnotationType.TYPED_COMMENT,
                content=notes,
            )
        )

    title = book_title or f"Photo capture - {capture_type}"

    ucf = UnifiedContent(
        source_type=content_type,
        source_file_path=str(file_path),
        title=title,
        created_at=datetime.now(),
        full_text="",  # Will be extracted during processing
        annotations=annotations,
        asset_paths=[str(file_path)],
        metadata={"capture_type": capture_type},
    )

    await save_content(ucf)

    # Map capture_type to PipelineContentType
    pipeline_type_map = {
        "book_page": PipelineContentType.BOOK,
        "whiteboard": PipelineContentType.WHITEBOARD,
        "document": PipelineContentType.DOCUMENT,
        "general": PipelineContentType.PHOTO,
    }
    pipeline_type = pipeline_type_map.get(capture_type, PipelineContentType.PHOTO)

    background_tasks.add_task(
        process_content.delay,
        ucf.id,
        pipeline_type.value,
        str(file_path),   # source_path
    )

    return {
        "status": "captured",
        "id": ucf.id,
        "file_path": str(file_path),
        "capture_type": capture_type,
        "message": "Photo queued for OCR processing",
    }


@router.post("/voice")
async def capture_voice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file"),
    expand: bool = Form(True, description="Expand transcript into structured note"),
):
    """
    Capture a voice memo for transcription.

    Uses Whisper for transcription and optionally expands the
    raw transcript into a well-structured note.

    High-priority processing for quick turnaround.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        file: Audio file to transcribe. Supported formats: MP3, MP4, WAV, WebM,
              M4A, OGG, FLAC.
        expand: If True (default), uses LLM to expand raw transcript into a
                structured, well-formatted note. If False, keeps raw transcript.

    Returns:
        dict: Response containing status, content ID, file path, and processing
              message indicating high-priority queue.

    Raises:
        HTTPException: 400 if audio format is not supported.
    """
    # Validate audio format
    valid_types = {
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/webm",
        "audio/m4a",
        "audio/x-m4a",
        "audio/ogg",
        "audio/flac",
    }

    if file.content_type and file.content_type not in valid_types:
        # Also check by extension
        ext = file.filename.split(".")[-1].lower() if file.filename else ""
        if ext not in {"mp3", "mp4", "wav", "webm", "m4a", "ogg", "flac"}:
            raise HTTPException(400, f"Unsupported audio format: {file.content_type}")

    # Save file
    file_path = await save_upload(file, directory="voice_memos")

    ucf = UnifiedContent(
        source_type=ContentType.VOICE_MEMO,
        source_file_path=str(file_path),
        title=f"Voice memo - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        created_at=datetime.now(),
        full_text="",  # Will be transcribed
        asset_paths=[str(file_path)],
        metadata={"expand": expand},
    )

    await save_content(ucf)

    # Use high-priority queue for voice memos (user is waiting)
    background_tasks.add_task(
        process_content_high.delay,
        ucf.id,
        PipelineContentType.VOICE_MEMO.value,
        str(file_path),   # source_path
    )

    return {
        "status": "captured",
        "id": ucf.id,
        "file_path": str(file_path),
        "message": "Voice memo queued for transcription (high priority)",
    }


@router.post("/pdf")
async def capture_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file"),
    content_type_hint: Optional[str] = Form(
        None, description="Hint: paper, article, book, or general"
    ),
    detect_handwriting: bool = Form(True, description="Detect handwritten annotations"),
):
    """
    Upload a PDF for processing.

    Extracts text, digital highlights/comments, and optionally
    handwritten annotations using Vision LLM.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        file: The PDF file to process.
        content_type_hint: Optional hint about the PDF content type to optimize
                          processing. Options:
            - "paper": Academic paper with citations and abstract.
            - "article": Web article or blog post.
            - "book": Book chapter or full book.
            - "general": General document (default).
        detect_handwriting: If True (default), uses Vision LLM to detect and
                           extract handwritten annotations in margins.

    Returns:
        dict: Response containing status, content ID, file path, filename,
              and processing message.

    Raises:
        HTTPException: 400 if file is not a PDF.
    """
    # Validate PDF
    if file.content_type != "application/pdf":
        ext = file.filename.split(".")[-1].lower() if file.filename else ""
        if ext != "pdf":
            raise HTTPException(400, "File must be a PDF")

    # Save file
    file_path = await save_upload(file, directory="pdfs")

    ucf = UnifiedContent(
        source_type=ContentType.PAPER,
        source_file_path=str(file_path),
        title=file.filename or "Untitled PDF",
        created_at=datetime.now(),
        full_text="",  # Will be extracted
        asset_paths=[str(file_path)],
        metadata={
            "content_type_hint": content_type_hint,
            "detect_handwriting": detect_handwriting,
        },
    )

    await save_content(ucf)

    # Queue PDF for processing
    background_tasks.add_task(
        process_content.delay,
        ucf.id,
        PipelineContentType.PDF.value,
        str(file_path),   # source_path
    )

    return {
        "status": "captured",
        "id": ucf.id,
        "file_path": str(file_path),
        "filename": file.filename,
        "message": "PDF queued for processing",
    }


@router.post("/book")
async def capture_book(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Multiple book page images"),
    title: Optional[str] = Form(None, description="Book title"),
    authors: Optional[str] = Form(None, description="Comma-separated author names"),
    isbn: Optional[str] = Form(None, description="ISBN if known"),
    notes: Optional[str] = Form(None, description="Optional notes about this book"),
    max_concurrency: int = Form(
        5, description="Max parallel OCR calls (5-20 recommended)"
    ),
):
    """
    Capture multiple book page photos as a single book.

    Uploads all images and processes them together using BookOCRPipeline.
    Pages are processed in PARALLEL for faster results.

    Note: This endpoint requires individual file uploads rather than a directory path
    because the backend runs inside Docker and doesn't have access to the host
    filesystem. Files are uploaded via multipart form data and saved to the
    container's /uploads volume.

    The pipeline:
    - Extracts page numbers via OCR (doesn't assume order from upload)
    - Detects chapters from running headers
    - Extracts printed text and handwritten margin notes
    - Aggregates all pages into a single Obsidian note

    Performance:
    - 10 pages @ concurrency 5: ~30 seconds
    - 50 pages @ concurrency 10: ~75 seconds
    - 100 pages @ concurrency 10: ~150 seconds

    Best for: Capturing highlights and margin notes from physical books.

    Args:
        background_tasks: FastAPI background tasks handler for async processing.
        files: List of image files (JPG, PNG, HEIC, WebP, TIFF) representing
               book pages. Order doesn't matter; pages are sorted by detected
               page numbers during OCR processing.
        title: Optional book title. If not provided, the pipeline will attempt
               to infer it from page headers or generate a timestamped title.
        authors: Optional comma-separated list of author names
                 (e.g., "Cal Newport, James Clear").
        isbn: Optional ISBN for metadata lookup and book identification.
        notes: Optional notes about the book or why it was captured.

    Returns:
        dict: Response containing status, content ID, title, page count,
              file paths, and processing message.

    Raises:
        HTTPException: 400 if no files provided or if any file is not a
                      supported image format.
    """
    if not files:
        raise HTTPException(400, "At least one image file is required")

    # Validate all files are images by extension (content_type is unreliable for
    # formats like HEIC which curl sends as application/octet-stream)
    valid_extensions = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff"}
    saved_paths = []

    for file in files:
        # Check extension (primary validation - more reliable than content_type)
        ext = ""
        if file.filename:
            ext = "." + file.filename.split(".")[-1].lower()
            if ext not in valid_extensions:
                raise HTTPException(
                    400,
                    f"Unsupported image format: {ext}. Supported: {valid_extensions}",
                )

        # Save file
        file_path = await save_upload(file, directory="book_pages")
        saved_paths.append(str(file_path))

    # Parse authors
    author_list = []
    if authors:
        author_list = [a.strip() for a in authors.split(",") if a.strip()]

    # Create annotations from notes
    annotations = []
    if notes:
        annotations.append(
            Annotation(
                type=AnnotationType.TYPED_COMMENT,
                content=notes,
            )
        )

    # Generate title if not provided
    book_title = title or f"Book capture - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Create content entry (will be updated after processing)
    ucf = UnifiedContent(
        source_type=ContentType.BOOK,
        title=book_title,
        authors=author_list,
        created_at=datetime.now(),
        full_text="",  # Will be populated by pipeline
        annotations=annotations,
        asset_paths=saved_paths,
        metadata={
            "isbn": isbn,
            "page_count": len(files),
            "processing_type": "batch_ocr",
        },
    )

    await save_content(ucf)

    # Build metadata for the task
    book_metadata = {
        "title": title,  # May be None - pipeline will infer
        "authors": author_list,
        "isbn": isbn,
    }

    # Queue for batch book processing (parallel OCR)
    background_tasks.add_task(
        process_book.delay,
        ucf.id,
        saved_paths,
        book_metadata,
        max_concurrency,
    )

    return {
        "status": "captured",
        "id": ucf.id,
        "title": book_title,
        "page_count": len(files),
        "file_paths": saved_paths,
        "max_concurrency": max_concurrency,
        "message": f"Book with {len(files)} pages queued for parallel OCR processing",
    }


def _generate_title(content: str) -> str:
    """
    Generate a title from content by extracting the first line.

    Args:
        content: The text content to generate a title from.

    Returns:
        str: A title derived from the first line of content (max 100 chars),
             or a date-based fallback title if content is empty.
    """
    if not content:
        return f"Note - {datetime.now().strftime('%Y-%m-%d')}"

    # Use first line as title
    first_line = content.strip().split("\n")[0]
    first_line = first_line.lstrip("#").strip()

    if len(first_line) > 100:
        first_line = first_line[:97] + "..."

    return first_line or f"Note - {datetime.now().strftime('%Y-%m-%d')}"


async def _fetch_page_title(url: str) -> str:
    """
    Fetch page title from URL by parsing the HTML <title> tag.

    Args:
        url: The URL to fetch the title from.

    Returns:
        str: The page title if found, otherwise returns the URL as fallback.
             Uses a 10-second timeout and follows redirects.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Second Brain Bot 1.0"},
            )

            if response.status_code == 200:
                # Extract title from HTML
                match = re.search(
                    r"<title[^>]*>([^<]+)</title>", response.text, re.IGNORECASE
                )
                if match:
                    return match.group(1).strip()
    except Exception:
        pass

    # Fallback to URL
    return url
