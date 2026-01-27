"""
Storage Service

Handles file uploads and content persistence to PostgreSQL.

Responsibilities:
- Save uploaded files with unique names
- Persist UnifiedContent to database
- Load content from database
- Update processing status

ID System (IMPORTANT):
    This service works with TWO different ID types internally:

    1. content_id (UUID string) - PUBLIC API:
       - Generated at ingestion time via uuid.uuid4()
       - Stored in DBContent.content_uuid column (indexed, unique constraint)
       - Also stored in UnifiedContent.id for application use
       - The ONLY identifier exposed in function signatures
       - Stable across systems (can be shared externally, used in URLs, etc.)
       - Example: "550e8400-e29b-41d4-a716-446655440000"

    2. db_id (integer) - INTERNAL ONLY:
       - Auto-incrementing PostgreSQL primary key (DBContent.id)
       - NEVER exposed in function signatures or APIs
       - Used internally for foreign key relationships (annotations, cards, etc.)
       - Stored in content.metadata["db_id"] after save for internal joins only
       - Example: 42

    Why two IDs?
       - UUIDs provide globally unique, collision-free identifiers suitable for
         distributed systems and external references
       - Integer PKs are efficient for database joins and foreign keys
       - The UUID is the "logical" ID; the integer is the "physical" ID

    Lookup behavior:
       - All functions use DBContent.content_uuid column for lookups
       - Integer db_id is NEVER accepted as input - use UUID only

Usage:
    from app.services.storage import save_upload, save_content

    # Save uploaded file
    file_path = await save_upload(upload_file, directory="pdfs")

    # Save content to database
    await save_content(unified_content)
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.base import async_session_maker, task_session_maker
from app.db.models import Annotation as DBAnnotation
from app.db.models import Content as DBContent
from app.db.models import ContentStatus
from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    ProcessingStatus,
    UnifiedContent,
)

logger = logging.getLogger(__name__)

# Upload directory from config
#
# UPLOAD_DIR is a temporary staging area for raw uploaded files, NOT the Obsidian
# vault's assets folder. This separation exists because:
#
# 1. Staging vs. Permanent: Uploaded files land here before processing. They may
#    fail validation, duplicate detection, or LLM processing - we don't want
#    failed/rejected content polluting the vault.
#
# 2. Processing Pipeline: Files here are inputs to the ingestion pipeline. After
#    successful processing, relevant assets (images, PDFs) are copied to the
#    vault's assets/ folder (configured in default.yaml: obsidian.app_config.attachment_folder).
#
# 3. Cleanup: This directory can be periodically cleaned (e.g., delete files older
#    than 7 days) without affecting the vault. The vault's assets are permanent.
#
# Flow: Upload → UPLOAD_DIR → Pipeline Processing → Vault assets/ (if successful)
#
UPLOAD_DIR = Path(settings.UPLOAD_DIR)


async def save_upload(file: UploadFile, directory: str = "uploads") -> Path:
    """
    Save uploaded file and return path.

    Creates a unique filename using UUID to prevent collisions.

    Args:
        file: FastAPI UploadFile object
        directory: Subdirectory under UPLOAD_DIR (e.g., "pdfs", "photos")

    Returns:
        Path to the saved file
    """
    # Create upload directory if it doesn't exist
    upload_dir = UPLOAD_DIR / directory
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename preserving extension
    ext = Path(file.filename).suffix if file.filename else ""
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename

    # Save file asynchronously
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    logger.info(f"Saved upload: {file_path} ({len(content)} bytes)")
    return file_path


async def save_content(
    content: UnifiedContent,
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Save UnifiedContent to PostgreSQL.

    Args:
        content: UnifiedContent object to save. Must have content.id (UUID) set.
        db: Optional database session (creates new if not provided)

    Returns:
        content_id (UUID string) - the logical identifier for subsequent lookups.
        Note: The database integer PK is stored in content.metadata["db_id"].
    """
    if db is None:
        async with async_session_maker() as db:
            return await _save_content_impl(content, db)
    return await _save_content_impl(content, db)


async def _save_content_impl(content: UnifiedContent, db: AsyncSession) -> str:
    """
    Internal implementation of content saving to PostgreSQL.

    This method performs the actual database operations for save_content().
    It is separated to allow the public function to handle session management
    (creating a new session if none provided) while keeping the core logic clean.

    ID Handling:
        - content.id (UUID string): Stored in DBContent.content_uuid column.
          This is the PRIMARY identifier used throughout the application.
          Has a unique index for efficient lookups.
        - db_content.id (integer): Auto-generated PostgreSQL primary key.
          Used internally for foreign key relationships (e.g., annotations).
          Stored back in content.metadata["db_id"] for reference.

    Operations performed:
        1. Creates a DBContent record from UnifiedContent fields
        2. Stores content_id (UUID) in content_uuid column (indexed, unique)
        3. Stores additional metadata (authors, hash, tags, timestamps) in metadata_json
        4. Flushes to obtain the database-generated integer PK (db_id)
        5. Creates DBAnnotation records linked via db_id foreign key
        6. Commits the transaction
        7. Stores db_id back in content.metadata["db_id"] for internal reference

    Args:
        content: UnifiedContent object to persist. content.id must be a valid UUID string.
        db: Active database session (caller manages lifecycle)

    Returns:
        content_id (UUID string) - NOT the database integer PK.
        Use this for all subsequent load/update operations.
    """
    # ---------------------------------------------------------------------
    # Deduplication (best-effort)
    #
    # We dedupe on:
    # - raw_file_hash (for file-based content) if present
    # - source_url (for URL-based content) if present
    #
    # Important: capture endpoints should compute raw_file_hash at upload time
    # so we can avoid inserting duplicate Content rows *before* Celery ingestion.
    # ---------------------------------------------------------------------
    try:
        existing: Optional[DBContent] = None

        if content.raw_file_hash:
            result = await db.execute(
                select(DBContent).where(
                    DBContent.metadata_json["raw_file_hash"].as_string()
                    == content.raw_file_hash
                )
            )
            existing = result.scalar_one_or_none()

        if existing is None and content.source_url:
            result = await db.execute(
                select(DBContent).where(DBContent.source_url == content.source_url)
            )
            existing = result.scalar_one_or_none()

        if existing is not None:
            # Mutate the incoming object so callers (capture routes) can skip enqueueing.
            content.metadata["_deduped"] = True
            content.metadata["_dedupe_existing_id"] = existing.content_uuid
            content.id = existing.content_uuid

            logger.info(
                f"Deduped content '{content.title}' -> existing content_id={existing.content_uuid}"
            )
            return existing.content_uuid
    except Exception as e:
        # Never fail ingestion due to dedupe query issues
        logger.warning(f"Deduplication check failed (continuing without dedupe): {e}")

    # Create database content record
    # Note: db_content.id (integer PK) is auto-generated by PostgreSQL
    db_content = DBContent(
        # content_uuid is the PRIMARY external identifier (indexed, unique)
        content_uuid=content.id,
        content_type=content.source_type.value,
        title=content.title,
        source_url=content.source_url,
        source_path=content.source_file_path,
        # Handle both enum and string status values (ProcessingStatus enum vs raw string)
        status=(
            content.processing_status.value
            if hasattr(content.processing_status, "value")
            else content.processing_status
        ),
        raw_text=content.full_text,
        metadata_json={
            # Keep UUID in metadata for backwards compatibility during migration
            "id": content.id,
            "authors": content.authors,
            "raw_file_hash": content.raw_file_hash,
            "asset_paths": content.asset_paths,
            "tags": content.tags,
            "created_at": (
                content.created_at.isoformat() if content.created_at else None
            ),
            "ingested_at": (
                content.ingested_at.isoformat() if content.ingested_at else None
            ),
            **content.metadata,
        },
        vault_path=content.obsidian_path,
    )

    db.add(db_content)
    await db.flush()  # Generates db_content.id (integer PK)

    # Create annotation records linked via db_id (integer FK)
    # Note: Annotations use db_content.id (integer) as foreign key, not the UUID
    for annot in content.annotations:
        db_annot = DBAnnotation(
            content_id=db_content.id,  # Integer FK to DBContent.id (not UUID!)
            annotation_type=annot.type.value,
            text=annot.content,
            page_number=annot.page_number,
            context=annot.context,
            is_handwritten=annot.type.value == "handwritten_note",
            ocr_confidence=annot.confidence,
        )
        db.add(db_annot)

    await db.commit()

    # Store the integer db_id for internal reference (e.g., direct DB queries)
    content.metadata["db_id"] = db_content.id

    logger.info(
        f"Saved content: {content.title} (content_id={content.id}, db_id={db_content.id})"
    )
    return content.id  # Return UUID, not integer PK


async def load_content(
    content_id: str,
    db: Optional[AsyncSession] = None,
) -> Optional[UnifiedContent]:
    """
    Load UnifiedContent from PostgreSQL by content_id (UUID).

    Args:
        content_id: UUID string identifier (e.g., "550e8400-e29b-41d4-a716-446655440000").
            Must be a valid UUID that was returned from save_content().
        db: Optional database session

    Returns:
        UnifiedContent object or None if not found
    """
    if db is None:
        async with async_session_maker() as db:
            return await _load_content_impl(content_id, db)
    return await _load_content_impl(content_id, db)


async def _load_content_impl(
    content_id: str,
    db: AsyncSession,
) -> Optional[UnifiedContent]:
    """
    Internal implementation of content loading from PostgreSQL.

    This method performs the actual database query and object reconstruction
    for load_content(). Separated to allow the public function to handle
    session management.

    Lookup:
        Uses the indexed content_uuid column for efficient lookup.
        Example: content_id="550e8400-e29b-41d4-a716-446655440000"

    Reconstruction:
        - Loads the DBContent record by content_uuid
        - Converts related DBAnnotation records to Annotation objects
        - Rebuilds UnifiedContent from database fields and stored metadata
        - Restores datetime fields from ISO format strings in metadata

    Args:
        content_id: UUID string identifier (must be valid UUID from save_content)
        db: Active database session (caller manages lifecycle)

    Returns:
        Reconstructed UnifiedContent object, or None if not found
    """
    # Lookup by content_uuid column (indexed, fast)
    # Use selectinload to eagerly load annotations (required for async SQLAlchemy)
    result = await db.execute(
        select(DBContent)
        .where(DBContent.content_uuid == content_id)
        .options(selectinload(DBContent.annotations))
    )
    db_content = result.scalar_one_or_none()

    if not db_content:
        return None

    # Load annotations (already eagerly loaded via selectinload)
    annotations = []
    if db_content.annotations:
        for db_annot in db_content.annotations:
            annotations.append(
                Annotation(
                    id=str(db_annot.id),  # Annotation's own db_id as string
                    type=AnnotationType(db_annot.annotation_type.upper()),
                    content=db_annot.text,
                    page_number=db_annot.page_number,
                    context=db_annot.context,
                    confidence=db_annot.ocr_confidence,
                )
            )

    # Reconstruct UnifiedContent
    metadata = db_content.metadata_json or {}

    return UnifiedContent(
        # content_uuid is the primary identifier (NOT NULL, unique)
        id=db_content.content_uuid,
        source_type=ContentType(db_content.content_type.upper()),
        source_url=db_content.source_url,
        source_file_path=db_content.source_path,
        title=db_content.title,
        authors=metadata.get("authors", []),
        created_at=(
            datetime.fromisoformat(metadata["created_at"])
            if metadata.get("created_at")
            else db_content.created_at
        ),
        ingested_at=(
            datetime.fromisoformat(metadata["ingested_at"])
            if metadata.get("ingested_at")
            else db_content.created_at
        ),
        full_text=db_content.raw_text or "",
        annotations=annotations,
        raw_file_hash=metadata.get("raw_file_hash"),
        asset_paths=metadata.get("asset_paths", []),
        processing_status=ProcessingStatus(
            db_content.status.value
            if hasattr(db_content.status, "value")
            else db_content.status
        ),
        error_message=None,
        obsidian_path=db_content.vault_path,
        tags=metadata.get("tags", []),
        metadata=metadata,  # Includes "db_id" if previously saved
    )


async def get_db_id_by_uuid(
    content_id: str,
    db: Optional[AsyncSession] = None,
) -> Optional[int]:
    """
    Get the integer database ID for a content UUID.

    This is useful when you need the integer FK for database operations
    (e.g., llm_usage_logs.content_id) but only have the UUID.

    Args:
        content_id: UUID string of the content
        db: Optional database session

    Returns:
        Integer database ID (content.id) or None if not found
    """
    if db is None:
        async with async_session_maker() as db:
            result = await db.execute(
                select(DBContent.id).where(DBContent.content_uuid == content_id)
            )
            row = result.scalar_one_or_none()
            return row
    result = await db.execute(
        select(DBContent.id).where(DBContent.content_uuid == content_id)
    )
    return result.scalar_one_or_none()


async def update_status(
    content_id: str,
    status: str,
    error: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    task_context: bool = False,
) -> bool:
    """
    Update processing status of content by content_id (UUID).

    Args:
        content_id: UUID string of the content (e.g., "550e8400-e29b-41d4-a716-446655440000").
        status: New status value (must match ContentStatus enum: "pending", "processing",
            "processed", "failed")
        error: Optional error message if status is 'failed'
        db: Optional database session
        task_context: If True, use task_session_maker (safe for Celery tasks with
            new event loops). If False, use async_session_maker (FastAPI routes).

    Returns:
        True if update succeeded, False if content not found
    """
    if db is None:
        session_maker = task_session_maker if task_context else async_session_maker
        async with session_maker() as db:
            return await _update_status_impl(content_id, status, error, db)
    return await _update_status_impl(content_id, status, error, db)


async def _update_status_impl(
    content_id: str,
    status: str,
    error: Optional[str],
    db: AsyncSession,
) -> bool:
    """
    Internal implementation of status update in PostgreSQL.

    This method performs the actual database update for update_status().
    Separated to allow the public function to handle session management.

    ID Handling:
        This function looks up by content_uuid column (indexed, fast).
        It does NOT support fallback to integer db_id. If you have a db_id, you must
        first load the content to get its UUID.

    Operations performed:
        1. Queries for content by content_uuid column (UUID lookup only)
        2. Updates the status field to the new ContentStatus enum value
        3. If status is "completed", sets processed_at timestamp
        4. If error is provided, stores it in metadata_json["error_message"]
        5. Commits the transaction

    Args:
        content_id: UUID string of the content to update (e.g., "550e8400-...").
            Integer db_id is NOT supported here.
        status: New status value (must be valid ContentStatus enum value:
            "pending", "processing", "processed", "failed")
        error: Optional error message to store in metadata
        db: Active database session (caller manages lifecycle)

    Returns:
        True if content was found and updated, False if not found
    """
    # Lookup by content_uuid column (indexed, fast)
    # Note: No fallback to db_id here - UUID is required
    result = await db.execute(
        select(DBContent).where(DBContent.content_uuid == content_id)
    )
    db_content = result.scalar_one_or_none()

    if not db_content:
        logger.warning(f"Content not found for status update (content_id={content_id})")
        return False

    # Update status
    db_content.status = ContentStatus(status)

    # Update processed_at if processed
    if status == ContentStatus.PROCESSED.value:
        db_content.processed_at = datetime.now(timezone.utc)

    # Store error in metadata if provided
    if error:
        metadata = db_content.metadata_json or {}
        metadata["error_message"] = error
        db_content.metadata_json = metadata

    await db.commit()

    logger.info(
        f"Updated status: content_id={content_id}, db_id={db_content.id}, status={status}"
    )
    return True


async def update_content(
    content_id: str,
    title: Optional[str] = None,
    authors: Optional[list[str]] = None,
    full_text: Optional[str] = None,
    annotations: Optional[list] = None,
    metadata: Optional[dict] = None,
    db: Optional[AsyncSession] = None,
    task_context: bool = False,
) -> bool:
    """
    Update content fields after processing (e.g., after OCR pipeline completes).

    Args:
        content_id: UUID string of the content to update.
        title: New title (optional).
        authors: List of author names (optional).
        full_text: Extracted/processed full text (optional).
        annotations: List of Annotation objects to add (optional).
        metadata: Additional metadata to merge (optional).
        db: Optional database session.
        task_context: If True, use task_session_maker (safe for Celery tasks with
            new event loops). If False, use async_session_maker (FastAPI routes).

    Returns:
        True if update succeeded, False if content not found.
    """
    if db is None:
        session_maker = task_session_maker if task_context else async_session_maker
        async with session_maker() as db:
            return await _update_content_impl(
                content_id, title, authors, full_text, annotations, metadata, db
            )
    return await _update_content_impl(
        content_id, title, authors, full_text, annotations, metadata, db
    )


async def _update_content_impl(
    content_id: str,
    title: Optional[str],
    authors: Optional[list[str]],
    full_text: Optional[str],
    annotations: Optional[list],
    metadata: Optional[dict],
    db: AsyncSession,
) -> bool:
    """
    Internal implementation of content update.

    Updates the specified fields on an existing content record. Only non-None
    fields are updated. Annotations are appended (not replaced).
    """
    # Lookup by content_uuid
    result = await db.execute(
        select(DBContent).where(DBContent.content_uuid == content_id)
    )
    db_content = result.scalar_one_or_none()

    if not db_content:
        logger.warning(f"Content not found for update (content_id={content_id})")
        return False

    # Update fields if provided
    if title is not None:
        db_content.title = title

    if full_text is not None:
        db_content.raw_text = full_text

    # Update metadata_json (merge)
    existing_metadata = db_content.metadata_json or {}

    if authors is not None:
        existing_metadata["authors"] = authors

    if metadata is not None:
        existing_metadata.update(metadata)

    db_content.metadata_json = existing_metadata

    # Add new annotations
    if annotations:
        for annot in annotations:
            db_annot = DBAnnotation(
                content_id=db_content.id,  # Integer FK
                annotation_type=(
                    annot.type.value if hasattr(annot.type, "value") else annot.type
                ),
                text=annot.content,
                page_number=annot.page_number,
                context=annot.context,
                is_handwritten=(
                    annot.type.value == "handwritten_note"
                    if hasattr(annot.type, "value")
                    else annot.type == "handwritten_note"
                ),
                ocr_confidence=(
                    annot.confidence if hasattr(annot, "confidence") else None
                ),
            )
            db.add(db_annot)

    await db.commit()

    logger.info(f"Updated content: content_id={content_id}, db_id={db_content.id}")
    return True


async def get_pending_content(
    limit: int = 100,
    db: Optional[AsyncSession] = None,
) -> list[UnifiedContent]:
    """
    Get content items that are pending processing.

    Args:
        limit: Maximum number of items to return
        db: Optional database session

    Returns:
        List of UnifiedContent objects. Each object's .id is the UUID (content_id).
    """
    if db is None:
        async with async_session_maker() as db:
            return await _get_pending_impl(limit, db)
    return await _get_pending_impl(limit, db)


async def _get_pending_impl(limit: int, db: AsyncSession) -> list[UnifiedContent]:
    """
    Internal implementation of pending content retrieval from PostgreSQL.

    This method performs the actual database query for get_pending_content().
    Separated to allow the public function to handle session management.

    Query logic:
        1. Selects DBContent records where status == ContentStatus.PENDING
        2. Orders by created_at ascending (oldest first = FIFO processing)
        3. Limits results to prevent memory issues with large backlogs
        4. Reconstructs each record into UnifiedContent via _load_content_impl

    Args:
        limit: Maximum number of pending items to return
        db: Active database session (caller manages lifecycle)

    Returns:
        List of UnifiedContent objects ready for processing.
        Each object's .id is the UUID (content_uuid).
    """
    # Query pending content, oldest first (FIFO)
    # Use selectinload to eagerly load annotations (required for async SQLAlchemy)
    result = await db.execute(
        select(DBContent)
        .where(DBContent.status == ContentStatus.PENDING)
        .options(selectinload(DBContent.annotations))
        .order_by(DBContent.created_at.asc())  # Explicit ascending = oldest first
        .limit(limit)
    )

    items = []
    for db_content in result.scalars():
        content = await _load_content_impl(db_content.content_uuid, db)
        if content:
            items.append(content)

    return items
