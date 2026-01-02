#!/usr/bin/env python3
"""
Test script for extracting PDF annotations using pdfplumber.

This script demonstrates how to extract highlights, underlines, comments,
and other annotations from PDF files using pdfplumber.

IMPORTANT FINDINGS ON PDF HIGHLIGHT EXTRACTION
==============================================

The "right" approach depends on how the highlighting was created:

1. REAL PDF HIGHLIGHT ANNOTATIONS (best case)
   Most editors (Adobe, Preview, many others) create annotation objects with
   /Subtype /Highlight and a color entry. In this case you can extract:
   - The highlight color (often RGB)
   - The highlighted quadrilaterals (QuadPoints that define the region)
   - The text under those quads

2. FAKE HIGHLIGHTS (drawn rectangles) - NOT annotations
   Some PDFs don't contain highlight annotations at all. Highlighting may be
   "burned in" as graphical content (semi-transparent rectangles) or created
   during printing/export. In this case:
   - There is NO annotation color to read
   - You must detect colored shapes in the content stream
   - Options: inspect drawings or use OCR with color thresholding

PDFPLUMBER LIMITATIONS
======================
- pdfplumber provides annotation coordinates but may NOT expose the full
  PDF annotation dictionary (Subtype, QuadPoints, etc.)
- For proper highlight extraction, PyMuPDF (fitz) is recommended instead
- pdfplumber is better suited for table extraction and text layout analysis

RECOMMENDATION
==============
- For normal reviewing workflows (Adobe/Preview/etc.): Use PyMuPDF instead
- For "burned-in" highlights: Use page.get_drawings() or OCR-based detection
- pdfplumber works for basic annotation detection but lacks robust text extraction

Usage:
    python test_pdfplumber_annotations.py <pdf_path>
    python test_pdfplumber_annotations.py sample_mistral7b.pdf
    python test_pdfplumber_annotations.py sample.pdf --verbose
    python test_pdfplumber_annotations.py sample.pdf --dump-raw

Example output:
    Page 1: Found 3 annotations
      [Highlight] "machine learning models" (author: John)
      [Underline] "important concept"
      [Text] Comment: "Review this section"
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pdfplumber


def extract_annotations(pdf_path: Path, verbose: bool = False) -> list[dict[str, Any]]:
    """
    Extract all annotations from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        verbose: Whether to show detailed debug info.

    Returns:
        List of annotation dictionaries with extracted information.
    """
    annotations: list[dict[str, Any]] = []

    # Map PDF annotation subtypes to human-readable names
    subtype_names = {
        "Highlight": "Highlight",
        "Underline": "Underline",
        "StrikeOut": "Strikeout",
        "Squiggly": "Squiggly",
        "Text": "Sticky Note",
        "FreeText": "Free Text",
        "Popup": "Popup",
        "Link": "Link",
        "Stamp": "Stamp",
        "Caret": "Caret",
        "Ink": "Ink Drawing",
        "FileAttachment": "File Attachment",
        "Sound": "Sound",
        "Movie": "Movie",
        "Widget": "Widget",
        "Screen": "Screen",
        "PrinterMark": "Printer Mark",
        "TrapNet": "Trap Net",
        "Watermark": "Watermark",
        "3D": "3D",
    }

    with pdfplumber.open(pdf_path) as pdf:
        print(f"\n📄 PDF: {pdf_path.name}")
        print(f"   Pages: {len(pdf.pages)}")
        print(f"   pdfplumber version: {pdfplumber.__version__}")
        print("-" * 60)

        for page_num, page in enumerate(pdf.pages, start=1):
            # Access annotations via page.annots
            if not hasattr(page, "annots") or not page.annots:
                continue

            page_annotations = []

            for annot in page.annots:
                annot_info: dict[str, Any] = {
                    "page": page_num,
                }

                # Store ALL raw annotation data for debugging
                raw_data: dict[str, Any] = {}
                for key in annot.keys():
                    val = annot.get(key)
                    # Convert to string representation for display
                    try:
                        if hasattr(val, "__iter__") and not isinstance(val, (str, bytes)):
                            raw_data[key] = list(val)
                        else:
                            raw_data[key] = str(val) if val is not None else None
                    except Exception:
                        raw_data[key] = repr(val)
                annot_info["raw_data"] = raw_data

                # Get annotation subtype - check both Subtype and data fields
                subtype = annot.get("Subtype")
                if subtype:
                    subtype_str = str(subtype).replace("/", "")
                    annot_info["subtype"] = subtype_str
                    annot_info["type_name"] = subtype_names.get(subtype_str, subtype_str)
                else:
                    # Try to infer from 'data' field which contains PDF dict keys
                    data_keys = annot.get("data", [])
                    if "Subtype" in data_keys:
                        annot_info["subtype"] = "HasSubtype"
                        annot_info["type_name"] = "PDF Annotation"
                    else:
                        annot_info["subtype"] = "Unknown"
                        annot_info["type_name"] = "Unknown"

                # =====================================================
                # EXTRACT TEXT FROM BOUNDING BOX COORDINATES
                # pdfplumber provides x0, y0, x1, y1 directly in annot
                # =====================================================
                x0 = annot.get("x0")
                y0 = annot.get("y0")  # Note: this is PDF coords (bottom-up)
                x1 = annot.get("x1")
                y1 = annot.get("y1")
                top = annot.get("top")  # pdfplumber's top (page coords)
                bottom = annot.get("bottom")

                if x0 is not None and x1 is not None:
                    annot_info["bbox"] = {
                        "x0": float(x0),
                        "y0": float(y0) if y0 else None,
                        "x1": float(x1),
                        "y1": float(y1) if y1 else None,
                        "top": float(top) if top else None,
                        "bottom": float(bottom) if bottom else None,
                    }

                    # Use top/bottom if available (pdfplumber page coordinates)
                    # Otherwise fall back to y0/y1
                    try:
                        if top is not None and bottom is not None:
                            bbox = (float(x0), float(top), float(x1), float(bottom))
                        elif y0 is not None and y1 is not None:
                            # y0/y1 are PDF coordinates (origin at bottom)
                            # Need to use page height to convert
                            page_height = page.height
                            bbox = (
                                float(x0),
                                page_height - float(y1),  # Convert to top-down
                                float(x1),
                                page_height - float(y0),
                            )
                        else:
                            bbox = None

                        if bbox:
                            # Ensure bbox is valid
                            bx0, by0, bx1, by1 = bbox
                            if bx0 > bx1:
                                bx0, bx1 = bx1, bx0
                            if by0 > by1:
                                by0, by1 = by1, by0
                            bbox = (bx0, by0, bx1, by1)

                            # Clip to page bounds
                            bbox = (
                                max(0, bbox[0]),
                                max(0, bbox[1]),
                                min(page.width, bbox[2]),
                                min(page.height, bbox[3]),
                            )

                            # Extract text from this region
                            try:
                                cropped = page.within_bbox(bbox)
                                if cropped:
                                    text = cropped.extract_text()
                                    if text and text.strip():
                                        annot_info["text_from_bbox"] = text.strip()
                                    else:
                                        # Try extracting chars directly
                                        chars = page.chars
                                        chars_in_bbox = [
                                            c for c in chars
                                            if (bbox[0] <= c["x0"] <= bbox[2] and
                                                bbox[1] <= c["top"] <= bbox[3])
                                        ]
                                        if chars_in_bbox:
                                            text = "".join(c["text"] for c in chars_in_bbox)
                                            if text.strip():
                                                annot_info["text_from_chars"] = text.strip()
                            except Exception as e:
                                annot_info["bbox_text_error"] = str(e)
                    except Exception as e:
                        annot_info["bbox_calc_error"] = str(e)

                # Get rectangle bounds (legacy approach)
                rect = annot.get("Rect")
                if rect:
                    try:
                        rect_list = list(rect) if hasattr(rect, "__iter__") else [rect]
                        annot_info["rect"] = rect_list

                        # Always try to extract text from rect
                        if len(rect_list) >= 4 and "text_from_bbox" not in annot_info:
                            try:
                                # pdfplumber uses (x0, top, x1, bottom) format
                                bbox = (
                                    float(rect_list[0]),
                                    float(rect_list[1]),
                                    float(rect_list[2]),
                                    float(rect_list[3]),
                                )
                                # Ensure bbox is valid (x0 < x1 and top < bottom)
                                if bbox[0] > bbox[2]:
                                    bbox = (bbox[2], bbox[1], bbox[0], bbox[3])
                                if bbox[1] > bbox[3]:
                                    bbox = (bbox[0], bbox[3], bbox[2], bbox[1])

                                cropped = page.within_bbox(bbox)
                                if cropped:
                                    text = cropped.extract_text()
                                    if text and text.strip():
                                        annot_info["text_from_rect"] = text.strip()
                            except Exception as e:
                                annot_info["rect_text_error"] = str(e)
                    except Exception as e:
                        annot_info["rect_error"] = str(e)

                # Get QuadPoints (for text markup annotations like highlights)
                quad_points = annot.get("QuadPoints")
                if quad_points:
                    try:
                        quad_list = list(quad_points)
                        annot_info["quad_points"] = quad_list

                        # Try to extract the highlighted text
                        if len(quad_list) >= 8:
                            try:
                                x_coords = [quad_list[i] for i in range(0, len(quad_list), 2)]
                                y_coords = [quad_list[i] for i in range(1, len(quad_list), 2)]
                                bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

                                # Extract text within the bounding box
                                cropped = page.within_bbox(bbox)
                                text = cropped.extract_text() if cropped else None
                                if text:
                                    annot_info["highlighted_text"] = text.strip()
                            except Exception as e:
                                annot_info["quad_text_error"] = str(e)
                    except Exception as e:
                        annot_info["quad_points_error"] = str(e)

                # Get Contents (comment text)
                contents = annot.get("Contents")
                if contents:
                    annot_info["contents"] = str(contents)

                # Get author (T = Title in PDF spec, often used for author)
                author = annot.get("T")
                if author:
                    annot_info["author"] = str(author)

                # Get creation date
                creation_date = annot.get("CreationDate")
                if creation_date:
                    annot_info["creation_date"] = str(creation_date)

                # Get modification date
                mod_date = annot.get("M")
                if mod_date:
                    annot_info["modification_date"] = str(mod_date)

                # Get color
                color = annot.get("C")
                if color:
                    try:
                        annot_info["color"] = list(color) if hasattr(color, "__iter__") else color
                    except Exception:
                        annot_info["color"] = str(color)

                # Get interior color (for filled annotations)
                interior_color = annot.get("IC")
                if interior_color:
                    try:
                        annot_info["interior_color"] = (
                            list(interior_color) if hasattr(interior_color, "__iter__") else interior_color
                        )
                    except Exception:
                        annot_info["interior_color"] = str(interior_color)

                # Store raw annotation keys for debugging
                annot_info["raw_keys"] = list(annot.keys())

                page_annotations.append(annot_info)
                annotations.append(annot_info)

            if page_annotations:
                print(f"\n📑 Page {page_num}: Found {len(page_annotations)} annotation(s)")
                for ann in page_annotations:
                    display_annotation(ann, verbose=verbose)

    return annotations


def display_annotation(annot: dict[str, Any], verbose: bool = False) -> None:
    """Display a single annotation in a readable format."""
    type_name = annot.get("type_name", "Unknown")
    subtype = annot.get("subtype", "")

    # Choose emoji based on type
    emoji_map = {
        "Highlight": "🟡",
        "Underline": "➖",
        "Strikeout": "❌",
        "Sticky Note": "📝",
        "Free Text": "✏️",
        "Link": "🔗",
        "Ink Drawing": "🖊️",
        "PDF Annotation": "📎",
    }
    emoji = emoji_map.get(type_name, "📌")

    print(f"   {emoji} [{type_name}]")

    # Show extracted text - try multiple sources
    text_found = False

    if "highlighted_text" in annot:
        text = annot["highlighted_text"]
        if len(text) > 200:
            text = text[:197] + "..."
        print(f'      ✅ HIGHLIGHTED TEXT: "{text}"')
        text_found = True

    if "text_from_bbox" in annot:
        text = annot["text_from_bbox"]
        if len(text) > 200:
            text = text[:197] + "..."
        print(f'      ✅ TEXT IN REGION: "{text}"')
        text_found = True

    if "text_from_chars" in annot:
        text = annot["text_from_chars"]
        if len(text) > 200:
            text = text[:197] + "..."
        print(f'      ✅ TEXT (chars): "{text}"')
        text_found = True

    if "text_from_rect" in annot and not text_found:
        text = annot["text_from_rect"]
        if len(text) > 200:
            text = text[:197] + "..."
        print(f'      ✅ TEXT (rect): "{text}"')
        text_found = True

    if not text_found:
        print("      ⚠️  No text extracted from this annotation region")

    # Show comment contents
    if "contents" in annot:
        contents = annot["contents"]
        if len(contents) > 200:
            contents = contents[:197] + "..."
        print(f'      💬 Comment: "{contents}"')

    # Show bounding box
    if "bbox" in annot:
        bbox = annot["bbox"]
        print(f"      📐 Bbox: x0={bbox.get('x0'):.1f}, top={bbox.get('top')}, x1={bbox.get('x1'):.1f}, bottom={bbox.get('bottom')}")

    # Show author if available
    if "author" in annot:
        print(f"      👤 Author: {annot['author']}")

    # Show color if available
    if "color" in annot:
        color = annot["color"]
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            try:
                r, g, b = [int(c * 255) for c in color[:3]]
                print(f"      🎨 Color: #{r:02x}{g:02x}{b:02x}")
            except (ValueError, TypeError):
                print(f"      🎨 Color: {color}")

    # Show errors if any
    for error_key in ["bbox_text_error", "bbox_calc_error", "rect_text_error", "quad_text_error"]:
        if error_key in annot:
            print(f"      ❌ {error_key}: {annot[error_key]}")

    # Always show raw keys in verbose mode or for Unknown types
    if verbose or type_name in ["Unknown", "PDF Annotation"]:
        raw_keys = annot.get("raw_keys", [])
        if raw_keys:
            print(f"      🔑 Raw keys: {raw_keys}")
        # Show raw data
        if "raw_data" in annot and verbose:
            print(f"      📋 Raw data: {annot['raw_data']}")


def save_results(annotations: list[dict[str, Any]], output_path: Path) -> None:
    """Save annotations to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(annotations, f, indent=2, default=str)

    print(f"\n💾 Saved {len(annotations)} annotations to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract annotations from PDF files using pdfplumber",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_pdfplumber_annotations.py document.pdf
    python test_pdfplumber_annotations.py document.pdf --output annotations.json
    python test_pdfplumber_annotations.py document.pdf --verbose
        """,
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF file")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output JSON file path (default: <pdf_name>_annotations.json)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including raw annotation keys",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to JSON file",
    )
    parser.add_argument(
        "--dump-raw",
        action="store_true",
        help="Dump all raw annotation data (very verbose)",
    )

    args = parser.parse_args()

    # Validate PDF path
    if not args.pdf_path.exists():
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    if not args.pdf_path.suffix.lower() == ".pdf":
        print(f"⚠️  Warning: File may not be a PDF: {args.pdf_path}")

    # Extract annotations
    try:
        annotations = extract_annotations(args.pdf_path, verbose=args.verbose)
    except Exception as e:
        print(f"❌ Error extracting annotations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Summary: Found {len(annotations)} total annotation(s)")

    if annotations:
        # Count by type
        type_counts: dict[str, int] = {}
        for ann in annotations:
            t = ann.get("type_name", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        print("\n   By type:")
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"   - {t}: {count}")

        # Count with text
        with_text = sum(
            1 for a in annotations
            if a.get("highlighted_text") or a.get("text_from_bbox") or a.get("text_from_chars") or a.get("text_from_rect")
        )
        print(f"\n   Annotations with extracted text: {with_text} / {len(annotations)}")

    # Save results
    if not args.no_save:
        output_path = args.output or args.pdf_path.with_suffix(".annotations.json")
        save_results(annotations, output_path)

    # Verbose output
    if args.verbose and annotations:
        print("\n" + "=" * 60)
        print("🔍 Verbose: Raw annotation keys found in this PDF:")
        all_keys: set[str] = set()
        for ann in annotations:
            all_keys.update(ann.get("raw_keys", []))
        for key in sorted(all_keys):
            print(f"   - {key}")

    # Dump raw data
    if args.dump_raw and annotations:
        print("\n" + "=" * 60)
        print("📋 Raw annotation data dump:")
        for i, ann in enumerate(annotations, 1):
            print(f"\n--- Annotation {i} (Page {ann.get('page')}) ---")
            raw_data = ann.get("raw_data", {})
            for key, value in sorted(raw_data.items()):
                print(f"   {key}: {value}")


if __name__ == "__main__":
    main()

