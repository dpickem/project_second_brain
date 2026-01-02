"""
Image Processing Utilities

Provides utilities for image preprocessing, conversion, and optimization
for OCR and Vision LLM processing.

Supports HEIC/HEIF images (common on iOS) via pillow-heif package.

Usage:
    from app.pipelines.utils.image_utils import image_to_base64, preprocess_for_ocr

    image = Image.open("page.png")
    processed = preprocess_for_ocr(image)
    base64_data = image_to_base64(processed)
"""

from pathlib import Path
from typing import Union
import base64
import io

import pillow_heif
from PIL import Image, ImageEnhance, ImageFilter

# Register HEIC/HEIF support (iOS photos)
pillow_heif.register_heif_opener()


def image_to_base64(image: Union[Image.Image, str, Path], format: str = "PNG") -> str:
    """
    Convert PIL Image to base64 string for API transmission.

    Args:
        image: PIL Image, file path string, or Path object
        format: Output format (PNG, JPEG, etc.)

    Returns:
        Base64-encoded image string
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    buffered = io.BytesIO()

    # Convert to RGB if saving as JPEG and image has alpha channel
    if format.upper() == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGB")

    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def base64_to_image(base64_string: str) -> Image.Image:
    """
    Convert base64 string back to PIL Image.

    Args:
        base64_string: Base64-encoded image data

    Returns:
        PIL Image object
    """
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))


def preprocess_for_ocr(
    image: Union[Image.Image, str, Path],
    enhance_contrast: float = 1.5,
    sharpen: bool = True,
) -> Image.Image:
    """
    Enhance image quality for better OCR results.

    Applies contrast enhancement and sharpening to improve text recognition,
    especially for photos of printed documents or handwritten notes.

    Args:
        image: Input image (PIL Image, file path, or Path)
        enhance_contrast: Contrast enhancement factor (1.0 = no change)
        sharpen: Whether to apply sharpening filter

    Returns:
        Preprocessed PIL Image
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    # Convert to RGB if necessary
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Enhance contrast
    if enhance_contrast != 1.0:
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(enhance_contrast)

    # Sharpen for clearer text
    if sharpen:
        image = image.filter(ImageFilter.SHARPEN)

    return image


def resize_for_api(
    image: Union[Image.Image, str, Path], max_dimension: int = 2048
) -> Image.Image:
    """
    Resize image to fit within API limits while preserving aspect ratio.

    Most Vision APIs have size limits. This ensures images are within bounds
    while maintaining quality and aspect ratio.

    Args:
        image: Input image
        max_dimension: Maximum width or height in pixels

    Returns:
        Resized image (or original if already within limits)
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    width, height = image.size

    # Check if resizing is needed
    if max(width, height) <= max_dimension:
        return image

    # Calculate new dimensions preserving aspect ratio
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))

    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def auto_rotate(image: Union[Image.Image, str, Path]) -> Image.Image:
    """
    Auto-rotate image based on EXIF orientation data.

    Mobile photos often have EXIF orientation that needs to be applied.

    Args:
        image: Input image

    Returns:
        Correctly rotated image
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    try:
        from PIL import ExifTags

        # Get EXIF data
        exif = image._getexif()
        if exif is None:
            return image

        # Find orientation tag
        orientation_key = None
        for key, value in ExifTags.TAGS.items():
            if value == "Orientation":
                orientation_key = key
                break

        if orientation_key is None or orientation_key not in exif:
            return image

        orientation = exif[orientation_key]

        # Apply rotation based on orientation
        rotations = {
            3: 180,
            6: 270,
            8: 90,
        }

        if orientation in rotations:
            image = image.rotate(rotations[orientation], expand=True)
    except (AttributeError, KeyError, IndexError):
        # No EXIF data or orientation, return as-is
        pass

    return image


def get_image_dimensions(image: Union[Image.Image, str, Path]) -> tuple[int, int]:
    """
    Get image dimensions without loading full image into memory.

    Args:
        image: Image or path to image

    Returns:
        Tuple of (width, height)
    """
    if isinstance(image, Image.Image):
        return image.size

    with Image.open(image) as img:
        return img.size


def split_two_page_spread(
    image: Union[Image.Image, str, Path],
) -> tuple[Image.Image, Image.Image]:
    """
    Split a two-page book spread into left and right pages.

    ASSUMPTION: This function assumes the two pages are perfectly centered
    in the image, splitting exactly at the horizontal midpoint. It does NOT
    detect the actual spine/gutter location. For best results, ensure the
    book spread is photographed with both pages equally visible and the
    spine aligned with the image center.

    Args:
        image: Image of two-page spread

    Returns:
        Tuple of (left_page, right_page) images
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    width, height = image.size
    mid = width // 2

    left_page = image.crop((0, 0, mid, height))
    right_page = image.crop((mid, 0, width, height))

    return left_page, right_page
