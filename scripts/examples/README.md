# Example Scripts

This directory contains standalone example scripts that demonstrate various features and capabilities. These scripts are useful for:
- Learning how specific features work
- Testing external APIs and tools
- Debugging and exploration

## Scripts

### `mistral_ocr_example.py`

Demonstrates Mistral's OCR API for extracting text and structured data from PDF documents.

```bash
# Basic usage
python scripts/examples/mistral_ocr_example.py test_data/sample_mistral7b.pdf

# With structured annotation extraction
python scripts/examples/mistral_ocr_example.py test_data/sample_paper_async_tool_use.pdf --annotate
```

**Requirements:**
- `pip install mistralai pydantic`
- `MISTRAL_API_KEY` environment variable

### `pymupdf_annotations_example.py`

Extracts PDF annotations (highlights, underlines, comments) using PyMuPDF (fitz). This is the **recommended** approach for annotation extraction.

```bash
# Basic usage
python scripts/examples/pymupdf_annotations_example.py test_data/sample_mistral7b.pdf

# With verbose output
python scripts/examples/pymupdf_annotations_example.py document.pdf --verbose

# List all PDF elements (debugging)
python scripts/examples/pymupdf_annotations_example.py document.pdf --list-all
```

**Requirements:**
- `pip install pymupdf`

### `pdfplumber_annotations_example.py`

Demonstrates PDF annotation extraction using pdfplumber. Kept for reference; PyMuPDF is recommended for production use.

```bash
# Basic usage
python scripts/examples/pdfplumber_annotations_example.py test_data/sample_mistral7b.pdf

# Dump raw annotation data
python scripts/examples/pdfplumber_annotations_example.py document.pdf --dump-raw
```

**Requirements:**
- `pip install pdfplumber`

## Test Data

Sample PDFs are located in `test_data/`:
- `sample_mistral7b.pdf` - Sample paper for OCR testing
- `sample_paper_async_tool_use.pdf` - Sample paper with annotations

## Notes

- All scripts should be run from the project root directory
- These are example/exploration scripts, not production code
- For production PDF processing, use the pipelines in `backend/app/pipelines/`
