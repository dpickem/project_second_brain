"""
Image Storage Service for Extracted PDF/Book Images

Saves images extracted during OCR processing to the Obsidian vault's assets folder
AND to the database for proper relational tracking.

Provides utilities for:
- Saving base64-encoded images to files
- Storing image metadata in the database with content FK
- Generating consistent filenames (content_id_page_N_img_M.format)
- Optimizing images for web display
- Tracking image metadata for template rendering

Images are stored in: vault/assets/images/{content_id}/
Image metadata is stored in: database.images table

Usage:
    from app.services.processing.output.image_storage import (
        save_extracted_images,
        ImageInfo,
    )

    # Save images from OCR result (saves to disk AND database)
    saved_images = await save_extracted_images(
        content_id="abc123",
        content_pk=57,  # Database primary key of content
        ocr_result=ocr_result,
    )

    # Returns list of ImageInfo with paths and metadata
    for img in saved_images:
        print(f"Saved: {img.vault_path} - {img.description}")
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import aiofiles
import aiofiles.os
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.config import settings
from app.db.base import task_session_maker
from app.db.models import Image as DBImage, Content as DBContent
from app.services.obsidian.vault import get_vault_manager

if TYPE_CHECKING:
    from app.pipelines.utils.mistral_ocr_client import MistralOCRResult, OCRPage

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """
    Information about an extracted and saved image.

    Attributes:
        vault_path: Relative path within the vault (e.g., "assets/images/abc123/page_1_img_0.png")
        absolute_path: Absolute path on the filesystem
        page_number: Page number in the source document (1-indexed)
        image_index: Index of the image on its page (0-indexed)
        image_type: Type of image (e.g., "graph", "table", "image", "text")
        description: LLM-generated description of the image content
        has_bbox: Whether bounding box coordinates are available
        width: Image width in pixels
        height: Image height in pixels
    """

    vault_path: str
    absolute_path: Path
    page_number: int
    image_index: int
    image_type: str = "image"
    description: str = ""
    has_bbox: bool = False
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "vault_path": self.vault_path,
            "page_number": self.page_number,
            "image_index": self.image_index,
            "image_type": self.image_type,
            "description": self.description,
            "width": self.width,
            "height": self.height,
        }


async def save_extracted_images(
    content_id: str,
    ocr_result: "MistralOCRResult",
    content_pk: Optional[int] = None,
    optimize: bool = True,
    db: Optional[AsyncSession] = None,
) -> list[ExtractedImage]:
    """
    Save all extracted images from an OCR result to the vault AND database.

    Creates a content-specific folder in the vault's assets directory
    and saves each image with a consistent naming scheme. Also creates
    database records in the images table for proper relational tracking.

    Args:
        content_id: UUID of the content these images belong to
        ocr_result: OCR result containing pages with images
        content_pk: Primary key (integer ID) of the content record in the database.
            Required for database insertion. If not provided, images are only saved
            to disk (backwards compatibility).
        optimize: Whether to optimize images (resize, compress). Defaults to True.
        db: Optional database session. If not provided, creates a new session.

    Returns:
        List of ExtractedImage objects with paths and metadata

    Example:
        >>> result = await ocr_pdf_document_annotated(pdf_path, include_images=True)
        >>> images = await save_extracted_images("abc123", result, content_pk=57)
        >>> for img in images:
        ...     print(f"Page {img.page_number}: {img.vault_path}")
    """
    saved_images: list[ExtractedImage] = []

    # Get vault manager and determine output directory
    vault = get_vault_manager()
    assets_folder = vault.vault_path / "assets" / settings.IMAGE_ASSETS_FOLDER / content_id

    # Ensure directory exists
    await aiofiles.os.makedirs(assets_folder, exist_ok=True)

    # Process each page
    for page in ocr_result.pages:
        page_images = await _save_page_images(
            page=page,
            content_id=content_id,
            assets_folder=assets_folder,
            vault_root=vault.vault_path,
            optimize=optimize,
        )
        saved_images.extend(page_images)

    if saved_images:
        logger.info(
            f"Saved {len(saved_images)} images for content {content_id} "
            f"to {assets_folder}"
        )

        # Save to database - look up content_pk if not provided
        effective_pk = content_pk
        if effective_pk is None:
            effective_pk = await _get_content_pk(content_id, db)

        if effective_pk is not None:
            await _save_images_to_db(
                saved_images=saved_images,
                content_id=content_id,
                content_pk=effective_pk,
                db=db,
            )
        else:
            logger.warning(f"Could not find content_pk for {content_id}, images not saved to DB")
    else:
        logger.debug(f"No images to save for content {content_id}")

    return saved_images


async def _get_content_pk(
    content_id: str,
    db: Optional[AsyncSession] = None,
) -> Optional[int]:
    """
    Look up the database primary key for a content UUID.

    Args:
        content_id: UUID of the content
        db: Optional database session

    Returns:
        Integer primary key or None if not found
    """
    async def _query(session: AsyncSession) -> Optional[int]:
        result = await session.execute(
            select(DBContent.id).where(DBContent.content_uuid == content_id)
        )
        return result.scalar_one_or_none()

    try:
        if db is not None:
            return await _query(db)
        else:
            async with task_session_maker() as session:
                return await _query(session)
    except Exception as e:
        logger.error(f"Failed to get content_pk for {content_id}: {e}")
        return None


async def _save_images_to_db(
    saved_images: list[ExtractedImage],
    content_id: str,
    content_pk: int,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Save image records to the database.

    Args:
        saved_images: List of ExtractedImage objects to save
        content_id: UUID of the content
        content_pk: Primary key of the content record
        db: Optional database session
    """
    async def _do_save(session: AsyncSession) -> None:
        for img in saved_images:
            # Get file size
            file_size = None
            if img.absolute_path.exists():
                file_size = img.absolute_path.stat().st_size

            db_image = DBImage(
                content_id=content_pk,
                content_uuid=content_id,
                filename=img.absolute_path.name,
                vault_path=img.vault_path,
                page_number=img.page_number,
                image_index=img.image_index,
                width=img.width if img.width > 0 else None,
                height=img.height if img.height > 0 else None,
                file_size=file_size,
                description=img.description or None,
            )
            session.add(db_image)

        await session.commit()
        logger.info(f"Saved {len(saved_images)} image records to database for content {content_id}")

    try:
        if db is not None:
            await _do_save(db)
        else:
            async with task_session_maker() as session:
                await _do_save(session)
    except Exception as e:
        logger.error(f"Failed to save images to database for content {content_id}: {e}")


async def _save_page_images(
    page: "OCRPage",
    content_id: str,
    assets_folder: Path,
    vault_root: Path,
    optimize: bool,
) -> list[ExtractedImage]:
    """
    Save all images from a single page.

    Args:
        page: OCR page containing images
        content_id: Content UUID for filename generation
        assets_folder: Absolute path to output folder
        vault_root: Root path of the vault (for relative path calculation)
        optimize: Whether to optimize images

    Returns:
        List of ExtractedImage objects for this page
    """
    saved: list[ExtractedImage] = []
    page_number = page.index + 1  # Convert to 1-indexed

    for img_idx, img_info in enumerate(page.images):
        # Skip if no image data
        if not img_info.image_base64:
            logger.debug(
                f"Skipping image {img_idx} on page {page_number}: no base64 data"
            )
            continue

        try:
            # Generate filename
            filename = f"page_{page_number}_img_{img_idx}.{settings.IMAGE_DEFAULT_FORMAT}"
            output_path = assets_folder / filename

            # Log base64 data info for debugging
            b64_data = img_info.image_base64
            b64_preview = b64_data[:100] if len(b64_data) > 100 else b64_data
            logger.debug(
                f"Processing image {img_idx} on page {page_number}: "
                f"{len(b64_data)} chars, preview: {b64_preview[:50]}..."
            )

            # Decode and optionally optimize image
            image_bytes, width, height = await _process_image(
                b64_data,
                optimize=optimize,
            )

            # Save to file
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(image_bytes)

            # Calculate relative vault path
            relative_path = output_path.relative_to(vault_root)

            # Extract annotation info
            image_type = "image"
            description = ""
            if img_info.annotation:
                image_type = img_info.annotation.get("image_type", "image")
                description = img_info.annotation.get("description", "")

            saved.append(
                ExtractedImage(
                    vault_path=str(relative_path),
                    absolute_path=output_path,
                    page_number=page_number,
                    image_index=img_idx,
                    image_type=image_type,
                    description=description,
                    has_bbox=img_info.has_bbox,
                    width=width,
                    height=height,
                )
            )

            logger.debug(f"Saved image: {output_path}")

        except Exception as e:
            logger.warning(
                f"Failed to save image {img_idx} on page {page_number}: {e}"
            )

    return saved


async def _process_image(
    base64_data: str,
    optimize: bool = True,
) -> tuple[bytes, int, int]:
    """
    Process and optionally optimize a base64-encoded image.

    Args:
        base64_data: Base64-encoded image data (may include data URI prefix)
        optimize: Whether to resize and compress

    Returns:
        Tuple of (image_bytes, width, height)
    """
    # Handle data URI prefix if present (e.g., "data:image/png;base64,...")
    if base64_data.startswith("data:"):
        # Extract the base64 part after the comma
        try:
            base64_data = base64_data.split(",", 1)[1]
        except IndexError:
            raise ValueError("Invalid data URI format")

    # Decode base64
    try:
        image_data = base64.b64decode(base64_data)
    except Exception as e:
        raise ValueError(f"Failed to decode base64: {e}")

    if len(image_data) < 100:
        raise ValueError(f"Image data too small ({len(image_data)} bytes), likely invalid")

    # Try to open the image
    try:
        image = Image.open(BytesIO(image_data))
    except Exception as e:
        # Log first few bytes for debugging
        preview = image_data[:50].hex() if len(image_data) >= 50 else image_data.hex()
        raise ValueError(f"Cannot identify image format. First bytes: {preview}. Error: {e}")

    # Get original dimensions
    width, height = image.size

    # Convert to RGB if necessary (for JPEG/consistent output)
    if image.mode in ("RGBA", "LA", "P"):
        # Create white background for transparency
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(image, mask=image.split()[-1] if "A" in image.mode else None)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    if optimize:
        # Resize if too large
        if max(width, height) > settings.IMAGE_MAX_DIMENSION:
            ratio = settings.IMAGE_MAX_DIMENSION / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            width, height = new_width, new_height

    # Save to bytes buffer
    buffer = BytesIO()
    if settings.IMAGE_DEFAULT_FORMAT == "png":
        image.save(buffer, format="PNG", compress_level=settings.IMAGE_PNG_COMPRESSION)
    else:
        image.save(buffer, format="JPEG", quality=settings.IMAGE_JPEG_QUALITY, optimize=True)

    return buffer.getvalue(), width, height


async def delete_content_images(
    content_id: str,
    db: Optional[AsyncSession] = None,
) -> int:
    """
    Delete all images for a content item (used during reprocessing).
    Deletes from both the filesystem AND the database.

    Args:
        content_id: UUID of the content
        db: Optional database session

    Returns:
        Number of images deleted from disk
    """
    # Delete from database first
    async def _delete_from_db(session: AsyncSession) -> int:
        result = await session.execute(
            delete(DBImage).where(DBImage.content_uuid == content_id)
        )
        await session.commit()
        return result.rowcount  # type: ignore

    try:
        if db is not None:
            db_deleted = await _delete_from_db(db)
        else:
            async with task_session_maker() as session:
                db_deleted = await _delete_from_db(session)
        logger.info(f"Deleted {db_deleted} image records from database for content {content_id}")
    except Exception as e:
        logger.warning(f"Error deleting images from database for {content_id}: {e}")

    # Delete from filesystem
    vault = get_vault_manager()
    images_folder = vault.vault_path / "assets" / settings.IMAGE_ASSETS_FOLDER / content_id

    if not images_folder.exists():
        return 0

    deleted_count = 0
    try:
        # Delete all files in the folder
        for file in images_folder.iterdir():
            if file.is_file():
                file.unlink()
                deleted_count += 1

        # Remove the folder if empty
        if not any(images_folder.iterdir()):
            images_folder.rmdir()

        logger.info(f"Deleted {deleted_count} images from disk for content {content_id}")
    except Exception as e:
        logger.warning(f"Error deleting images from disk for {content_id}: {e}")

    return deleted_count


def get_obsidian_image_embed(
    image: ExtractedImage,
    use_wikilink: bool = True,
) -> str:
    """
    Generate Obsidian markdown embed syntax for an image.

    Args:
        image: ExtractedImage to embed
        use_wikilink: If True, use Obsidian wikilink syntax (![[path]])
                     If False, use standard markdown (![alt](path))

    Returns:
        Markdown string to embed the image
    """
    if use_wikilink:
        return f"![[{image.vault_path}]]"
    else:
        alt_text = image.description or f"Figure from page {image.page_number}"
        return f"![{alt_text}]({image.vault_path})"
