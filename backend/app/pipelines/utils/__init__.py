"""Pipeline utilities for image processing, OCR, text handling, and cost tracking."""

from app.pipelines.utils.image_utils import (
    image_to_base64,
    preprocess_for_ocr,
    resize_for_api,
    get_image_dimensions,
)
from app.pipelines.utils.ocr_client import (
    vision_completion,
    vision_completion_sync,
    vision_completion_multi_image,
    get_default_ocr_model,
)
from app.pipelines.utils.text_client import (
    text_completion,
    text_completion_sync,
    text_completion_with_context,
    text_completion_chat,
    get_default_text_model,
)
from app.pipelines.utils.cost_types import (
    LLMUsage,
    extract_provider,
    extract_usage_from_response,
    create_error_usage,
)
from app.pipelines.utils.hash_utils import (
    calculate_file_hash,
    calculate_content_hash,
)
from app.pipelines.utils.text_utils import (
    clean_text,
    extract_json_from_response,
    truncate_text,
    extract_title_from_text,
    normalize_whitespace,
    remove_markdown_formatting,
    split_into_chunks,
    split_markdown_into_chunks,
    split_by_tokens,
)

__all__ = [
    # Image utilities
    "image_to_base64",
    "preprocess_for_ocr",
    "resize_for_api",
    "get_image_dimensions",
    # OCR client (vision completion functions)
    "vision_completion",
    "vision_completion_sync",
    "vision_completion_multi_image",
    "get_default_ocr_model",
    # Text client (text completion functions)
    "text_completion",
    "text_completion_sync",
    "text_completion_with_context",
    "text_completion_chat",
    "get_default_text_model",
    # Cost tracking types
    "LLMUsage",
    "extract_provider",
    "extract_usage_from_response",
    "create_error_usage",
    # Hash utilities
    "calculate_file_hash",
    "calculate_content_hash",
    # Text utilities
    "clean_text",
    "extract_json_from_response",
    "truncate_text",
    "extract_title_from_text",
    "normalize_whitespace",
    "remove_markdown_formatting",
    # Text chunking (LangChain-based)
    "split_into_chunks",
    "split_markdown_into_chunks",
    "split_by_tokens",
]
