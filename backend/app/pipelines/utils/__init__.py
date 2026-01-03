"""Pipeline utilities for image processing, VLM/OCR, text handling, and cost tracking."""

from app.pipelines.utils.image_utils import (
    image_to_base64,
    preprocess_for_ocr,
    resize_for_api,
    get_image_dimensions,
)
from app.pipelines.utils.vlm_client import (
    vision_completion,
    vision_completion_sync,
    vision_completion_multi_image,
    get_default_vlm_model,
    get_default_ocr_model,  # Backwards compatibility alias
)
from app.pipelines.utils.mistral_ocr_client import (
    ocr_pdf_document,
    ocr_pdf_document_annotated,
    ocr_pdf_document_sync,
    ocr_pdf_document_annotated_sync,
    ocr_image,
    OCRPage,
    MistralOCRResult,
    DocumentAnnotation,
    ImageInfo,
    ImageType,
    ImageAnnotationSchema,
    DocumentAnnotationSchema,
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
    PipelineName,
    PipelineOperation,
    extract_provider,
    extract_usage_from_response,
    create_error_usage,
)
from app.pipelines.utils.api_utils import (
    adjust_temperature_for_model,
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
from app.pipelines.utils.pdf_utils import (
    ANNOT_TYPES,
    ANNOT_EMOJI,
    TEXT_MARKUP_TYPES,
    SHAPE_ANNOTATION_TYPES,
    extract_annotations,
    extract_annotations_with_metadata,
    extract_annotation_info,
    get_annotation_text,
    format_annotation_display,
    save_annotations_to_json,
    get_annotation_summary,
    list_pdf_elements,
)

__all__ = [
    # Image utilities
    "image_to_base64",
    "preprocess_for_ocr",
    "resize_for_api",
    "get_image_dimensions",
    # VLM client (vision completion functions)
    "vision_completion",
    "vision_completion_sync",
    "vision_completion_multi_image",
    "get_default_vlm_model",
    "get_default_ocr_model",  # Backwards compatibility
    # Mistral OCR client (PDF document OCR)
    "ocr_pdf_document",
    "ocr_pdf_document_annotated",
    "ocr_pdf_document_sync",
    "ocr_pdf_document_annotated_sync",
    "ocr_image",
    "OCRPage",
    "MistralOCRResult",
    "DocumentAnnotation",
    "ImageInfo",
    "ImageType",
    "ImageAnnotationSchema",
    "DocumentAnnotationSchema",
    # Text client (text completion functions)
    "text_completion",
    "text_completion_sync",
    "text_completion_with_context",
    "text_completion_chat",
    "get_default_text_model",
    # Cost tracking types and enums
    "LLMUsage",
    "PipelineName",
    "PipelineOperation",
    "extract_provider",
    "extract_usage_from_response",
    "create_error_usage",
    "adjust_temperature_for_model",
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
    # PDF annotation utilities (PyMuPDF-based)
    "ANNOT_TYPES",
    "ANNOT_EMOJI",
    "TEXT_MARKUP_TYPES",
    "SHAPE_ANNOTATION_TYPES",
    "extract_annotations",
    "extract_annotations_with_metadata",
    "extract_annotation_info",
    "get_annotation_text",
    "format_annotation_display",
    "save_annotations_to_json",
    "get_annotation_summary",
    "list_pdf_elements",
]
