"""
PDF annotation extraction utilities using PyMuPDF (fitz).

PyMuPDF is the RECOMMENDED library for PDF annotation extraction.
It provides direct access to highlight annotations, geometry, colors,
and robust text extraction from annotation regions.

IMPORTANT FINDINGS ON PDF HIGHLIGHT EXTRACTION
==============================================

The "right" approach depends on how the highlighting was created:

1. REAL PDF HIGHLIGHT ANNOTATIONS (best case)
   Most editors (Adobe, Preview, many others) create annotation objects with
   /Subtype /Highlight and a color entry. PyMuPDF can reliably extract:
   - The highlight color (via annot.colors - usually RGB)
   - The highlighted quadrilaterals (annot.vertices - quads defining the region)
   - The text under those quads (via page.get_text(clip=rect) or get_textbox)

   Notes/edge cases:
   - Some tools store color in slightly different fields; annot.colors usually works
   - A single highlight can span multiple lines → multiple quads
   - The vertices come in groups of 4 points per quad
   - For precise text: use page.get_textbox(rect) per quad, or intersect words

2. FAKE HIGHLIGHTS (drawn rectangles) - NOT annotations
   Some PDFs don't contain highlight annotations at all. Highlighting may be
   "burned in" as graphical content (semi-transparent rectangles) or created
   during printing/export. In this case:
   - There is NO annotation color to read
   - You must detect colored shapes via page.get_drawings()
   - Look for filled rectangles with alpha, then intersect with text positions
   - If the PDF is scanned/image-based: use OCR + color thresholding

ANNOTATION TYPES
================
- Type 8: Highlight (text markup with QuadPoints)
- Type 9: Underline (text markup with QuadPoints)
- Type 10: Squiggly (text markup with QuadPoints)
- Type 11: StrikeOut (text markup with QuadPoints)
- Type 4: Square (shape annotation - box drawn over content)
- Type 5: Circle (shape annotation)
- Type 15: Ink (freehand drawing)
- Type 2: FreeText (text box added to PDF)
- Type 0: Text (sticky note)

WHY PYMUPDF IS RECOMMENDED
==========================
- Direct access to annotation properties (type, colors, vertices, rect)
- Multiple text extraction methods (get_text, get_textbox, word intersection)
- Handles both text markup and shape annotations
- Better support for QuadPoints geometry
- Can also inspect drawings for "burned-in" highlights
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


# Annotation type constants from PyMuPDF
ANNOT_TYPES: dict[int, str] = {
    0: "Text",           # Sticky note
    1: "Link",
    2: "FreeText",
    3: "Line",
    4: "Square",
    5: "Circle",
    6: "Polygon",
    7: "PolyLine",
    8: "Highlight",
    9: "Underline",
    10: "Squiggly",
    11: "StrikeOut",
    12: "Redact",
    13: "Stamp",
    14: "Caret",
    15: "Ink",
    16: "Popup",
    17: "FileAttachment",
    18: "Sound",
    19: "Movie",
    20: "Widget",
    21: "Screen",
    22: "PrinterMark",
    23: "TrapNet",
    24: "Watermark",
    25: "3D",
}

# Emoji for each annotation type
ANNOT_EMOJI: dict[str, str] = {
    "Text": "📝",
    "Highlight": "🟡",
    "Underline": "➖",
    "Squiggly": "〰️",
    "StrikeOut": "❌",
    "FreeText": "✏️",
    "Link": "🔗",
    "Ink": "🖊️",
    "Stamp": "🔖",
    "Caret": "^",
    "Redact": "⬛",
    "Square": "⬜",
    "Circle": "⭕",
    "Line": "📏",
    "Polygon": "🔷",
    "PolyLine": "📈",
}

# Annotation type codes for text markup annotations
TEXT_MARKUP_TYPES = {8, 9, 10, 11}  # Highlight, Underline, Squiggly, StrikeOut

# Annotation type codes for shape annotations
SHAPE_ANNOTATION_TYPES = {3, 4, 5, 6, 7, 15}  # Line, Square, Circle, Polygon, PolyLine, Ink


def extract_annotation_info(
    annot: fitz.Annot,
    page: fitz.Page,
    page_num: int,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Extract information from a single annotation.

    Args:
        annot: The PyMuPDF annotation object.
        page: The page containing the annotation.
        page_num: Zero-based page number.
        verbose: Whether to include additional debug info.

    Returns:
        Dictionary containing annotation information.
    """
    annot_info: dict[str, Any] = {
        "page": page_num + 1,
        "type_code": annot.type[0],
        "type_name": ANNOT_TYPES.get(annot.type[0], f"Unknown({annot.type[0]})"),
    }

    # Get annotation rectangle (bounding box)
    rect = annot.rect
    annot_info["rect"] = {
        "x0": rect.x0,
        "y0": rect.y0,
        "x1": rect.x1,
        "y1": rect.y1,
    }

    # Get annotation info dict
    info = annot.info
    if info:
        if info.get("title"):
            annot_info["author"] = info["title"]
        if info.get("content"):
            annot_info["comment"] = info["content"]
        if info.get("subject"):
            annot_info["subject"] = info["subject"]
        if info.get("creationDate"):
            annot_info["creation_date"] = info["creationDate"]
        if info.get("modDate"):
            annot_info["modification_date"] = info["modDate"]

    # Get colors
    colors = annot.colors
    if colors:
        if colors.get("stroke"):
            annot_info["stroke_color"] = colors["stroke"]
        if colors.get("fill"):
            annot_info["fill_color"] = colors["fill"]

    # Get opacity
    opacity = annot.opacity
    if opacity is not None and opacity != 1.0:
        annot_info["opacity"] = opacity

    # Extract text based on annotation type
    type_code = annot.type[0]

    if type_code in TEXT_MARKUP_TYPES:
        _extract_text_markup_text(annot, page, annot_info)
    elif type_code in SHAPE_ANNOTATION_TYPES:
        _extract_shape_annotation_text(annot, page, annot_info)
    elif type_code == 2:  # FreeText
        _extract_freetext_text(annot, page, annot_info)

    # Fallback: try to extract text from rect for any annotation type
    if "text_from_rect" not in annot_info and "text_from_textbox" not in annot_info:
        try:
            text = page.get_text("text", clip=annot.rect).strip()
            if text:
                annot_info["text_from_rect"] = text
            textbox = page.get_textbox(annot.rect)
            if textbox and textbox.strip():
                annot_info["text_from_textbox"] = textbox.strip()
        except Exception as e:
            if "text_extraction_error" not in annot_info:
                annot_info["text_extraction_error"] = str(e)

    # Get popup content if any
    popup = annot.popup_rect
    if popup and popup.is_valid:
        annot_info["has_popup"] = True

    if verbose:
        # Include raw annotation flags
        annot_info["flags"] = annot.flags
        annot_info["has_popup_raw"] = annot.has_popup
        annot_info["is_open"] = annot.is_open

    return annot_info


def _extract_text_markup_text(
    annot: fitz.Annot,
    page: fitz.Page,
    annot_info: dict[str, Any],
) -> None:
    """Extract text for text markup annotations (Highlight, Underline, etc.)."""
    try:
        # Get the quad points (vertices of the highlight region)
        vertices = annot.vertices
        if vertices:
            annot_info["vertices_count"] = len(vertices)

            # Method 1: Use the annotation rect directly
            text = page.get_text("text", clip=annot.rect).strip()
            if text:
                annot_info["text_from_rect"] = text

            # Method 2: If vertices available, try each quad
            if len(vertices) >= 4:
                quad_texts = []
                # Vertices come in groups of 4 (quad points)
                for i in range(0, len(vertices), 4):
                    if i + 3 < len(vertices):
                        quad = vertices[i:i+4]
                        # Create rect from quad points
                        xs = [p[0] for p in quad]
                        ys = [p[1] for p in quad]
                        quad_rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                        quad_text = page.get_text("text", clip=quad_rect).strip()
                        if quad_text:
                            quad_texts.append(quad_text)
                if quad_texts:
                    annot_info["text_from_quads"] = " ".join(quad_texts)

            # Method 3: Use get_textbox on the rect
            textbox = page.get_textbox(annot.rect)
            if textbox and textbox.strip():
                annot_info["text_from_textbox"] = textbox.strip()

    except Exception as e:
        annot_info["text_extraction_error"] = str(e)


def _extract_shape_annotation_text(
    annot: fitz.Annot,
    page: fitz.Page,
    annot_info: dict[str, Any],
) -> None:
    """Extract text for shape annotations (Square, Circle, Line, etc.)."""
    try:
        # Method 1: Extract text from the annotation rectangle
        text = page.get_text("text", clip=annot.rect).strip()
        if text:
            annot_info["text_from_rect"] = text

        # Method 2: Use get_textbox on the rect
        textbox = page.get_textbox(annot.rect)
        if textbox and textbox.strip():
            annot_info["text_from_textbox"] = textbox.strip()

        # For Ink annotations, also check vertices
        if annot.type[0] == 15:  # Ink
            vertices = annot.vertices
            if vertices:
                annot_info["vertices_count"] = len(vertices)
                # Calculate bounding box of all ink strokes
                xs = [p[0] for p in vertices]
                ys = [p[1] for p in vertices]
                if xs and ys:
                    ink_rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                    ink_text = page.get_text("text", clip=ink_rect).strip()
                    if ink_text:
                        annot_info["text_from_ink_bounds"] = ink_text

    except Exception as e:
        annot_info["text_extraction_error"] = str(e)


def _extract_freetext_text(
    annot: fitz.Annot,
    page: fitz.Page,
    annot_info: dict[str, Any],
) -> None:
    """Extract text for FreeText annotations (text boxes added to PDF)."""
    try:
        # FreeText annotations contain their own text in annot.info["content"]
        # But also try to get text underneath
        text = page.get_text("text", clip=annot.rect).strip()
        if text:
            annot_info["text_from_rect"] = text
    except Exception as e:
        annot_info["text_extraction_error"] = str(e)


def extract_annotations(
    pdf_path: Path | str,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Extract all annotations from a PDF file using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.
        verbose: Whether to include additional debug info in results.

    Returns:
        List of annotation dictionaries with extracted information.
    """
    pdf_path = Path(pdf_path)
    annotations: list[dict[str, Any]] = []

    doc = fitz.open(pdf_path)

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]

            for annot in page.annots():
                if annot is None:
                    continue

                annot_info = extract_annotation_info(annot, page, page_num, verbose)
                annotations.append(annot_info)
    finally:
        doc.close()

    return annotations


def extract_annotations_with_metadata(
    pdf_path: Path | str,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Extract all annotations from a PDF file with document metadata.

    Args:
        pdf_path: Path to the PDF file.
        verbose: Whether to include additional debug info in results.

    Returns:
        Dictionary containing document metadata and list of annotations.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    result: dict[str, Any] = {
        "file": str(pdf_path),
        "page_count": doc.page_count,
        "pymupdf_version": fitz.version[0],
        "annotations": [],
    }

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]

            for annot in page.annots():
                if annot is None:
                    continue

                annot_info = extract_annotation_info(annot, page, page_num, verbose)
                result["annotations"].append(annot_info)
    finally:
        doc.close()

    return result


def get_annotation_text(annot_info: dict[str, Any]) -> str | None:
    """
    Get the best available extracted text from an annotation.

    Prefers textbox > quads > rect > ink bounds.

    Args:
        annot_info: Annotation dictionary from extract_annotations.

    Returns:
        Extracted text or None if no text was found.
    """
    return (
        annot_info.get("text_from_textbox")
        or annot_info.get("text_from_quads")
        or annot_info.get("text_from_rect")
        or annot_info.get("text_from_ink_bounds")
    )


def format_annotation_display(
    annot_info: dict[str, Any],
    verbose: bool = False,
    max_text_length: int = 200,
    max_comment_length: int = 150,
) -> str:
    """
    Format an annotation for human-readable display.

    Args:
        annot_info: Annotation dictionary from extract_annotations.
        verbose: Whether to show additional details.
        max_text_length: Maximum length for text before truncation.
        max_comment_length: Maximum length for comments before truncation.

    Returns:
        Formatted string representation of the annotation.
    """
    lines: list[str] = []

    type_name = annot_info.get("type_name", "Unknown")
    emoji = ANNOT_EMOJI.get(type_name, "📌")
    lines.append(f"   {emoji} [{type_name}]")

    # Show extracted text
    text = get_annotation_text(annot_info)
    if text:
        # Clean up whitespace
        text = " ".join(text.split())
        # Truncate long text
        if len(text) > max_text_length:
            text = text[:max_text_length - 3] + "..."
        lines.append(f'      ✅ TEXT: "{text}"')
    else:
        lines.append("      ⚠️  No text found in annotation region")

    # Show comment
    if "comment" in annot_info:
        comment = annot_info["comment"]
        if len(comment) > max_comment_length:
            comment = comment[:max_comment_length - 3] + "..."
        lines.append(f'      💬 Comment: "{comment}"')

    # Show rect coordinates
    rect = annot_info.get("rect", {})
    if rect:
        lines.append(
            f"      📐 Rect: ({rect.get('x0', 0):.1f}, {rect.get('y0', 0):.1f}) → "
            f"({rect.get('x1', 0):.1f}, {rect.get('y1', 0):.1f})"
        )

    # Show author if available
    if "author" in annot_info:
        lines.append(f"      👤 Author: {annot_info['author']}")

    # Show color
    fill = annot_info.get("fill_color") or annot_info.get("stroke_color")
    if fill and isinstance(fill, (list, tuple)) and len(fill) >= 3:
        try:
            r, g, b = [int(c * 255) for c in fill[:3]]
            lines.append(f"      🎨 Color: #{r:02x}{g:02x}{b:02x}")
        except (ValueError, TypeError):
            pass

    # Show extraction error if any
    if "text_extraction_error" in annot_info:
        lines.append(f"      ❌ Error: {annot_info['text_extraction_error']}")

    # Verbose: show additional details
    if verbose:
        if "vertices_count" in annot_info:
            lines.append(f"      📍 Vertices: {annot_info['vertices_count']}")
        if "subject" in annot_info:
            lines.append(f"      📝 Subject: {annot_info['subject']}")

    return "\n".join(lines)


def save_annotations_to_json(
    annotations: list[dict[str, Any]],
    output_path: Path | str,
) -> None:
    """
    Save annotations to a JSON file.

    Args:
        annotations: List of annotation dictionaries.
        output_path: Path to the output JSON file.
    """
    output_path = Path(output_path)
    with open(output_path, "w") as f:
        json.dump(annotations, f, indent=2, default=str)


def get_annotation_summary(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate a summary of annotations.

    Args:
        annotations: List of annotation dictionaries.

    Returns:
        Dictionary containing summary statistics.
    """
    # Count by type
    type_counts: dict[str, int] = {}
    for ann in annotations:
        t = ann.get("type_name", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Count with text
    with_text = sum(1 for a in annotations if get_annotation_text(a))

    # Count with comments
    with_comments = sum(1 for a in annotations if a.get("comment"))

    # Count by page
    pages: set[int] = {a.get("page", 0) for a in annotations}

    return {
        "total": len(annotations),
        "by_type": type_counts,
        "with_text": with_text,
        "with_comments": with_comments,
        "pages_with_annotations": len(pages),
    }


def list_pdf_elements(
    pdf_path: Path | str,
    max_pages: int = 3,
) -> dict[str, Any]:
    """
    List all elements on PDF pages (for debugging).

    Args:
        pdf_path: Path to the PDF file.
        max_pages: Maximum number of pages to inspect.

    Returns:
        Dictionary containing element counts per page.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    result: dict[str, Any] = {
        "file": str(pdf_path),
        "total_pages": doc.page_count,
        "pages_inspected": min(max_pages, doc.page_count),
        "pages": [],
    }

    try:
        for page_num in range(min(max_pages, doc.page_count)):
            page = doc[page_num]

            page_info: dict[str, Any] = {
                "page": page_num + 1,
                "annotations": len(list(page.annots())),
                "links": len(page.get_links()),
                "images": len(page.get_images()),
                "drawings": len(page.get_drawings()),
                "annotation_details": [],
            }

            # Get annotation details
            annot = page.first_annot
            while annot:
                page_info["annotation_details"].append({
                    "type": annot.type,
                    "rect": tuple(annot.rect),
                })
                annot = annot.next

            result["pages"].append(page_info)
    finally:
        doc.close()

    return result

