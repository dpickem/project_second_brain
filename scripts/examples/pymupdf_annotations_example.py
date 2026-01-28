#!/usr/bin/env python3
"""
Example script for extracting PDF annotations using PyMuPDF (fitz).

This script uses the pdf_utils module from backend/app/pipelines/utils
to extract and display PDF annotations.

Usage:
    # From project root:
    python scripts/examples/pymupdf_annotations_example.py <pdf_path>
    python scripts/examples/pymupdf_annotations_example.py test_data/sample_mistral7b.pdf
    python scripts/examples/pymupdf_annotations_example.py test_data/sample_paper_async_tool_use.pdf --verbose
    python scripts/examples/pymupdf_annotations_example.py document.pdf --list-all

Requirements:
    pip install pymupdf
"""

import argparse
import sys
from pathlib import Path

# Add backend/app/pipelines/utils to path for direct module import
# This avoids triggering the full backend initialization chain
_project_root = Path(__file__).parent.parent.parent
_utils_path = _project_root / "backend" / "app" / "pipelines" / "utils"
sys.path.insert(0, str(_utils_path))

from pdf_utils import (
    ANNOT_EMOJI,
    extract_annotations,
    format_annotation_display,
    get_annotation_summary,
    list_pdf_elements,
    save_annotations_to_json,
)

try:
    import fitz  # PyMuPDF - for version info
except ImportError:
    print("❌ PyMuPDF not installed. Install with: pip install pymupdf")
    sys.exit(1)


def display_annotations(
    pdf_path: Path,
    annotations: list[dict],
    verbose: bool = False,
) -> None:
    """Display extracted annotations grouped by page."""
    print(f"\n📄 PDF: {pdf_path.name}")

    # Open doc just for metadata
    doc = fitz.open(pdf_path)
    print(f"   Pages: {doc.page_count}")
    print(f"   PyMuPDF version: {fitz.version[0]}")
    doc.close()
    print("-" * 60)

    # Group by page
    pages: dict[int, list[dict]] = {}
    for ann in annotations:
        page = ann.get("page", 0)
        if page not in pages:
            pages[page] = []
        pages[page].append(ann)

    # Display by page
    for page_num in sorted(pages.keys()):
        page_anns = pages[page_num]
        print(f"\n📑 Page {page_num}: Found {len(page_anns)} annotation(s)")
        for ann in page_anns:
            print(format_annotation_display(ann, verbose=verbose))


def display_summary(annotations: list[dict]) -> None:
    """Display summary statistics for annotations."""
    print("\n" + "=" * 60)
    print(f"📊 Summary: Found {len(annotations)} total annotation(s)")

    if annotations:
        summary = get_annotation_summary(annotations)

        print("\n   By type:")
        for t, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
            emoji = ANNOT_EMOJI.get(t, "📌")
            print(f"   {emoji} {t}: {count}")

        print(
            f"\n   Annotations with extracted text: {summary['with_text']} / {summary['total']}"
        )

        if summary["with_comments"]:
            print(f"   Annotations with comments: {summary['with_comments']}")
    else:
        print("\n   ⚠️  No annotations found in this PDF.")
        print("   This could mean:")
        print("   - The PDF has no annotations")
        print("   - Highlights were made in a viewer that doesn't save to PDF")
        print("   - The annotations are stored in a non-standard format")
        print("\n   Try: --list-all to see what elements exist in the PDF")


def display_pdf_elements(pdf_path: Path) -> None:
    """Display all elements in the PDF for debugging."""
    print("\n🔍 Debug: Listing all page elements...")

    elements = list_pdf_elements(pdf_path, max_pages=3)

    for page_info in elements["pages"]:
        print(f"\nPage {page_info['page']}:")
        print(f"  - Annotations: {page_info['annotations']}")
        print(f"  - Links: {page_info['links']}")
        print(f"  - Images: {page_info['images']}")
        print(f"  - Drawings: {page_info['drawings']}")

        for i, annot_detail in enumerate(page_info["annotation_details"], 1):
            print(
                f"    Annot {i}: type={annot_detail['type']}, rect={annot_detail['rect']}"
            )

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Extract annotations from PDF files using PyMuPDF (fitz)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/examples/pymupdf_annotations_example.py document.pdf
    python scripts/examples/pymupdf_annotations_example.py test_data/sample_mistral7b.pdf --output annotations.json
    python scripts/examples/pymupdf_annotations_example.py document.pdf --verbose
        """,
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file path (default: <pdf_name>_pymupdf_annotations.json)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output including raw annotation data",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to JSON file",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List ALL elements on each page (for debugging)",
    )

    args = parser.parse_args()

    # Validate PDF path
    if not args.pdf_path.exists():
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    if not args.pdf_path.suffix.lower() == ".pdf":
        print(f"⚠️  Warning: File may not be a PDF: {args.pdf_path}")

    # Debug: list all elements if requested
    if args.list_all:
        display_pdf_elements(args.pdf_path)

    # Extract annotations
    try:
        annotations = extract_annotations(args.pdf_path, verbose=args.verbose)
    except Exception as e:
        print(f"❌ Error extracting annotations: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Display annotations
    display_annotations(args.pdf_path, annotations, verbose=args.verbose)

    # Display summary
    display_summary(annotations)

    # Save results
    if not args.no_save and annotations:
        output_path = args.output or args.pdf_path.with_suffix(
            ".pymupdf_annotations.json"
        )
        save_annotations_to_json(annotations, output_path)
        print(f"\n💾 Saved {len(annotations)} annotations to {output_path}")


if __name__ == "__main__":
    main()
