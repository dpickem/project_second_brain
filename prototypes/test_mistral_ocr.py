#!/usr/bin/env python3
"""
Test script for Mistral OCR API.

Based on: https://docs.mistral.ai/cookbooks/mistral-ocr-data_extraction

This script demonstrates how to use Mistral's OCR model to extract text
and structured data from PDF documents.

Usage:
    python test_mistral_ocr.py <pdf_path>

    # Or use the default test PDF:
    python test_mistral_ocr.py

Requirements:
    pip install mistralai pydantic

    For annotation support (--annotate flag), you need mistralai >= 1.2.0:
    pip install --upgrade mistralai

Environment:
    Set MISTRAL_API_KEY environment variable with your Mistral API key.
"""

import argparse
import base64
import json
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    from mistralai import Mistral
    from mistralai.models import OCRResponse
except ImportError:
    print("Error: mistralai package not installed.")
    print("Install with: pip install mistralai")
    sys.exit(1)

try:
    from pydantic import BaseModel, Field
except ImportError:
    print("Error: pydantic package not installed.")
    print("Install with: pip install pydantic")
    sys.exit(1)


# ============================================================================
# Annotation Models for Structured Output
# ============================================================================


class ImageType(str, Enum):
    """Types of images that can be detected in documents."""

    GRAPH = "graph"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class ImageAnnotation(BaseModel):
    """Schema for annotating bounding box images."""

    image_type: ImageType = Field(
        ...,
        description="The type of the image. Must be one of 'graph', 'text', 'table' or 'image'.",
    )
    description: str = Field(..., description="A description of the image content.")


class DocumentAnnotation(BaseModel):
    """Schema for annotating the entire document."""

    languages: list[str] = Field(
        ...,
        description="The list of languages present in the document in ISO 639-1 code format (e.g., 'en', 'fr').",
    )
    authors: list[str] = Field(
        default_factory=list, description="Authors of the document if identifiable."
    )
    title: str = Field(
        default="", description="The title of the document if identifiable."
    )
    summary: str = Field(..., description="A comprehensive summary of the document.")


# ============================================================================
# Helper Functions
# ============================================================================


def encode_pdf(pdf_path: str) -> Optional[str]:
    """
    Encode a PDF file to base64.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Base64-encoded string of the PDF, or None if encoding failed.
    """
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: The file {pdf_path} was not found.")
        return None
    except Exception as e:
        print(f"Error encoding PDF: {e}")
        return None


def response_format_from_pydantic_model(model: type[BaseModel]) -> dict:
    """
    Convert a Pydantic model to a response format for Mistral API.

    Args:
        model: A Pydantic BaseModel class.

    Returns:
        Dictionary with JSON schema for the model.
    """
    return {
        "type": "json_schema",
        "json_schema": {"name": model.__name__, "schema": model.model_json_schema()},
    }


def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replace image placeholders in markdown with base64-encoded images.

    Args:
        markdown_str: Markdown text containing image placeholders.
        images_dict: Dictionary mapping image IDs to base64 strings.

    Returns:
        Markdown text with images replaced by base64 data.
    """
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
        )
    return markdown_str


def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images.

    Returns:
        Combined markdown string with embedded images.
    """
    markdowns: list[str] = []

    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            # Use getattr for compatibility with different SDK versions
            img_base64 = getattr(img, "image_base64", None)
            if img_base64:
                image_data[img.id] = img_base64
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))

    return "\n\n".join(markdowns)


def get_combined_markdown_annotated(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text, annotations, and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text, images, and annotations.

    Returns:
        Combined markdown string with embedded images and annotations.
    """
    markdowns: list[str] = []

    # Add document annotation at the start if available (may not exist in older SDK versions)
    doc_annotation = getattr(ocr_response, "document_annotation", None)
    if doc_annotation:
        markdowns.append(f"**Document Annotation:**\n{doc_annotation}\n")

    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            # Handle image_annotation which may not exist in older SDK versions
            img_annotation = getattr(img, "image_annotation", None) or "No annotation"
            image_data[img.id] = {
                "image": getattr(img, "image_base64", ""),
                "annotation": img_annotation,
            }

        # Replace image placeholders with images and annotations
        page_markdown = page.markdown
        for img_name, data in image_data.items():
            page_markdown = page_markdown.replace(
                f"![{img_name}]({img_name})",
                f"![{img_name}]({data['image']})\n\n**{data['annotation']}**",
            )
        markdowns.append(page_markdown)

    return "\n\n".join(markdowns)


# ============================================================================
# Main OCR Functions
# ============================================================================


def run_basic_ocr(
    client: Mistral, pdf_path: str, include_images: bool = False
) -> Optional[OCRResponse]:
    """
    Run basic OCR on a PDF file without annotations.

    Args:
        client: Mistral client instance.
        pdf_path: Path to the PDF file.
        include_images: Whether to include base64-encoded images in response.

    Returns:
        OCRResponse object or None if processing failed.
    """
    print(f"\n📄 Processing PDF: {pdf_path}")

    base64_pdf = encode_pdf(pdf_path)
    if not base64_pdf:
        return None

    print("🔄 Running OCR (basic mode)...")

    try:
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document={  # type: ignore[arg-type]
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            include_image_base64=include_images,
        )
        print("✅ OCR completed successfully!")
        return response
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return None


def run_annotated_ocr(
    client: Mistral, pdf_path: str, max_pages: int = 8, include_images: bool = True
) -> Optional[OCRResponse]:
    """
    Run OCR with annotations on a PDF file.

    Args:
        client: Mistral client instance.
        pdf_path: Path to the PDF file.
        max_pages: Maximum number of pages to process (document annotations limited to 8).
        include_images: Whether to include base64-encoded images in response.

    Returns:
        OCRResponse object or None if processing failed.
    """
    print(f"\n📄 Processing PDF: {pdf_path}")

    base64_pdf = encode_pdf(pdf_path)
    if not base64_pdf:
        return None

    print(f"🔄 Running OCR with annotations (max {max_pages} pages)...")

    document_data = {
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}",
    }

    # Try with annotation parameters first (requires mistralai >= 1.2.0)
    try:
        response = client.ocr.process(
            model="mistral-ocr-latest",
            pages=list(range(max_pages)),
            document=document_data,  # type: ignore[arg-type]
            include_image_base64=include_images,
            bbox_annotation_format=response_format_from_pydantic_model(ImageAnnotation),  # type: ignore[arg-type]
            document_annotation_format=response_format_from_pydantic_model(DocumentAnnotation),  # type: ignore[arg-type]
        )
        print("✅ OCR with annotations completed successfully!")
        return response
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            print("⚠️  Annotation parameters not supported by your mistralai version.")
            print(
                "   To enable annotations, upgrade with: pip install --upgrade mistralai"
            )
            print("   Falling back to basic OCR...")
            try:
                response = client.ocr.process(
                    model="mistral-ocr-latest",
                    pages=list(range(max_pages)),
                    document=document_data,  # type: ignore[arg-type]
                    include_image_base64=include_images,
                )
                print("✅ OCR completed (without annotations).")
                return response
            except Exception as fallback_e:
                print(f"❌ OCR failed: {fallback_e}")
                return None
        else:
            print(f"❌ OCR failed: {e}")
            return None
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return None


def save_results(
    response: OCRResponse,
    output_dir: str,
    prefix: str = "ocr_result",
    with_annotations: bool = False,
    include_images: bool = False,
) -> None:
    """
    Save OCR results to files.

    Args:
        response: OCR response to save.
        output_dir: Directory to save results.
        prefix: Prefix for output filenames.
        with_annotations: Whether to include annotations in markdown output.
        include_images: Whether to include base64 images in the output files.
    """
    import re

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save raw JSON response
    json_path = output_path / f"{prefix}.json"
    response_dict = json.loads(response.model_dump_json())

    # Remove base64 images from JSON to keep it readable (always, JSON is for structure)
    for page in response_dict.get("pages", []):
        for img in page.get("images", []):
            if "image_base64" in img:
                img["image_base64"] = (
                    "[BASE64_DATA_REMOVED - use markdown file with --include-images]"
                )

    with open(json_path, "w") as f:
        json.dump(response_dict, f, indent=2)
    print(f"📁 Saved JSON response: {json_path}")

    # Save markdown output
    md_path = output_path / f"{prefix}.md"
    if with_annotations:
        markdown_content = get_combined_markdown_annotated(response)
    else:
        markdown_content = get_combined_markdown(response)

    # Only remove base64 images if not explicitly requested
    if not include_images:
        markdown_content = re.sub(
            r"!\[([^\]]*)\]\(data:image[^)]+\)",
            r"![\1](image_removed - use --include-images to embed)",
            markdown_content,
        )
        print(f"📁 Saved Markdown output: {md_path}")
    else:
        print(f"📁 Saved Markdown output with embedded images: {md_path}")
        print(f"   ⚠️  Note: File may be large due to base64-encoded images")

    with open(md_path, "w") as f:
        f.write(markdown_content)


def print_summary(response: OCRResponse) -> None:
    """Print a summary of the OCR response."""
    print("\n" + "=" * 60)
    print("📊 OCR RESULTS SUMMARY")
    print("=" * 60)

    print(f"\n📑 Total pages processed: {len(response.pages)}")

    total_images = sum(len(page.images) for page in response.pages)
    print(f"🖼️  Total images/figures detected: {total_images}")

    # Check for document_annotation (may not exist in older SDK versions)
    doc_annotation = getattr(response, "document_annotation", None)
    if doc_annotation:
        print(f"\n📝 Document Annotation:")
        try:
            annotation = json.loads(doc_annotation)
            for key, value in annotation.items():
                print(f"   • {key}: {value}")
        except json.JSONDecodeError:
            print(f"   {doc_annotation[:500]}...")

    # Print first page preview
    if response.pages:
        print(f"\n📖 First page preview (first 500 chars):")
        print("-" * 40)
        preview = response.pages[0].markdown[:500]
        print(preview)
        if len(response.pages[0].markdown) > 500:
            print("...")

    print("\n" + "=" * 60)


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Test Mistral OCR API on PDF documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic OCR on a PDF file:
    python test_mistral_ocr.py document.pdf
    
    # OCR with annotations:
    python test_mistral_ocr.py document.pdf --annotate
    
    # Save results to a specific directory:
    python test_mistral_ocr.py document.pdf --output ./results
    
    # Download and process a sample PDF:
    python test_mistral_ocr.py --download-sample
    
    # Full example with all options (download sample, annotate, include images):
    python test_mistral_ocr.py --download-sample --annotate --include-images --output ./ocr_results --max-pages 5
        """,
    )

    parser.add_argument("pdf_path", nargs="?", help="Path to the PDF file to process.")
    parser.add_argument(
        "--annotate",
        "-a",
        action="store_true",
        help="Run OCR with annotations (structured data extraction).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./ocr_output",
        help="Output directory for results (default: ./ocr_output).",
    )
    parser.add_argument(
        "--max-pages",
        "-p",
        type=int,
        default=8,
        help="Maximum pages to process with annotations (default: 8).",
    )
    parser.add_argument(
        "--include-images",
        "-i",
        action="store_true",
        help="Include base64-encoded images in the response.",
    )
    parser.add_argument(
        "--download-sample",
        action="store_true",
        help="Download a sample PDF for testing.",
    )
    parser.add_argument(
        "--json-only", action="store_true", help="Print raw JSON response and exit."
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY environment variable not set.")
        print("   Set it with: export MISTRAL_API_KEY='your-api-key'")
        sys.exit(1)

    # Download sample PDF if requested
    if args.download_sample:
        import urllib.request

        sample_url = "https://raw.githubusercontent.com/mistralai/cookbook/refs/heads/main/mistral/ocr/mistral7b.pdf"
        sample_path = "sample_mistral7b.pdf"
        print(f"📥 Downloading sample PDF to {sample_path}...")
        try:
            urllib.request.urlretrieve(sample_url, sample_path)
            print("✅ Sample downloaded successfully!")
            if not args.pdf_path:
                args.pdf_path = sample_path
        except Exception as e:
            print(f"❌ Failed to download sample: {e}")
            sys.exit(1)

    if not args.pdf_path:
        parser.print_help()
        print("\n❌ Error: Please provide a PDF path or use --download-sample")
        sys.exit(1)

    if not Path(args.pdf_path).exists():
        print(f"❌ Error: File not found: {args.pdf_path}")
        sys.exit(1)

    # Initialize client
    print("🔐 Initializing Mistral client...")
    client = Mistral(api_key=api_key)

    # Run OCR
    if args.annotate:
        response = run_annotated_ocr(
            client,
            args.pdf_path,
            max_pages=args.max_pages,
            include_images=args.include_images,
        )
    else:
        response = run_basic_ocr(
            client, args.pdf_path, include_images=args.include_images
        )

    if not response:
        print("❌ OCR processing failed.")
        sys.exit(1)

    # Output results
    if args.json_only:
        print(json.dumps(json.loads(response.model_dump_json()), indent=2))
    else:
        print_summary(response)
        save_results(
            response,
            args.output,
            prefix=Path(args.pdf_path).stem,
            with_annotations=args.annotate,
            include_images=args.include_images,
        )
        print(f"\n✨ Done! Results saved to {args.output}/")


if __name__ == "__main__":
    main()
