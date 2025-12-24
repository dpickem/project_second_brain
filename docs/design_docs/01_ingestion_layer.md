# Ingestion Layer Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `02_llm_processing_layer.md`, `09_data_models.md`

---

## 1. Overview

The Ingestion Layer captures content from diverse sources and normalizes it for processing. Each pipeline handles source-specific extraction logic while outputting a unified content format.

### Design Goals

1. **Source Diversity**: Support PDFs, web articles, book photos, code repos, quick notes
2. **Annotation Preservation**: Capture highlights, handwritten notes, and margin comments
3. **Minimal Friction**: Automated sync where possible; < 3 second manual capture
4. **Graceful Degradation**: Continue processing if individual items fail
5. **Idempotent Operations**: Re-running pipelines doesn't create duplicates

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├───────────┬───────────┬───────────┬───────────┬───────────┬─────────────────┤
│   PDFs    │ Raindrop  │   Book    │   GitHub  │   Voice   │  Quick Notes    │
│           │    API    │  Photos   │    API    │   Memos   │   (Text/URL)    │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴────────┬────────┘
      │           │           │           │           │              │
      ▼           ▼           ▼           ▼           ▼              ▼
┌───────────┐┌───────────┐┌───────────┐┌───────────┐┌───────────┐┌───────────┐
│    PDF    ││ Raindrop  ││   OCR     ││  GitHub   ││   Voice   ││   Quick   │
│ Processor ││   Sync    ││ Pipeline  ││ Importer  ││Transcribe ││  Capture  │
└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘
      │           │           │           │           │              │
      └───────────┴───────────┴───────────┼───────────┴──────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────┐
                            │   Unified Content       │
                            │   Format (UCF)          │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │   Processing Queue      │
                            │   (Redis/Celery)        │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                              To LLM Processing Layer
```

---

## 3. Unified Content Format (UCF)

All pipelines output content in this standardized format:

> **EXTENSIBILITY**: Content types are defined in `config/default.yaml`. New types can be added without code changes—just add the type to config and create a template.

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class ContentType(str, Enum):
    """
    Built-in content types. Additional types can be added via config.
    See config/default.yaml content_types section.
    """
    # Technical content
    PAPER = "paper"
    ARTICLE = "article"
    BOOK = "book"
    CODE = "code"
    IDEA = "idea"
    VOICE_MEMO = "voice_memo"
    
    # Career & personal (extensible via config)
    CAREER = "career"
    PERSONAL = "personal"
    PROJECT = "project"
    REFLECTION = "reflection"
    NON_TECH = "non-tech"

class AnnotationType(str, Enum):
    DIGITAL_HIGHLIGHT = "digital_highlight"
    HANDWRITTEN_NOTE = "handwritten_note"
    TYPED_COMMENT = "typed_comment"
    DIAGRAM = "diagram"

class Annotation(BaseModel):
    type: AnnotationType
    content: str
    page_number: Optional[int] = None
    position: Optional[dict] = None  # {x, y, width, height} for page coords
    context: Optional[str] = None    # Surrounding text for context
    confidence: Optional[float] = None  # OCR confidence score

class UnifiedContent(BaseModel):
    # Core identity
    id: str                          # UUID generated on ingestion
    source_type: ContentType
    source_url: Optional[str] = None
    source_file_path: Optional[str] = None
    
    # Metadata
    title: str
    authors: list[str] = []
    created_at: datetime
    ingested_at: datetime
    
    # Content
    full_text: str                   # Complete extracted text
    annotations: list[Annotation] = []
    
    # Raw storage
    raw_file_hash: Optional[str] = None  # SHA256 of original file
    asset_paths: list[str] = []          # Paths to images, diagrams, etc.
    
    # Processing status
    processing_status: str = "pending"   # pending | processing | completed | failed
    error_message: Optional[str] = None
```

---

## 4. Pipeline Specifications

### 4.1 PDF Processor

**Purpose**: Extract text, highlights, and handwritten annotations from academic papers and documents.

#### Input
- PDF file (local path or uploaded)
- Optional: Expected content type hint

#### Processing Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                         PDF INPUT                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      1. Metadata Extraction    │
              │   (title, authors, DOI, date) │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      2. Text Extraction        │
              │   (PyMuPDF for printed text)  │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      3. Annotation Detection   │
              │   (pdfplumber for highlights) │
              └───────────────┬───────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
   ┌─────────────────┐               ┌─────────────────┐
   │ Digital Annots  │               │ Handwritten?    │
   │ (highlights,    │               │ (check each     │
   │  typed notes)   │               │  page region)   │
   └────────┬────────┘               └────────┬────────┘
            │                                 │
            │                                 ▼
            │                        ┌─────────────────┐
            │                        │ Page → Image    │
            │                        │ (300 DPI)       │
            │                        └────────┬────────┘
            │                                 │
            │                                 ▼
            │                        ┌─────────────────┐
            │                        │ Vision LLM OCR  │
            │                        │ (Handwriting)   │
            │                        └────────┬────────┘
            │                                 │
            └─────────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    4. Content Association      │
              │  (link annotations to context)│
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    5. Output UCF              │
              └───────────────────────────────┘
```

#### Implementation

```python
# pipelines/pdf_processor.py

import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
from pathlib import Path
import hashlib

class PDFProcessor:
    def __init__(self, llm_client, vision_model: str = "google:gemini-2.0-flash"):
        self.llm_client = llm_client
        self.vision_model = vision_model
    
    async def process(self, pdf_path: Path) -> UnifiedContent:
        """Process a PDF file and extract all content."""
        
        # Calculate file hash for deduplication
        file_hash = self._calculate_hash(pdf_path)
        
        # Check if already processed
        existing = await self._check_existing(file_hash)
        if existing:
            return existing
        
        # Step 1: Extract metadata
        metadata = self._extract_metadata(pdf_path)
        
        # Step 2: Extract full text
        full_text = self._extract_text(pdf_path)
        
        # Step 3: Extract digital annotations
        digital_annotations = self._extract_digital_annotations(pdf_path)
        
        # Step 4: Check for handwritten annotations
        handwritten_annotations = await self._extract_handwritten_annotations(pdf_path)
        
        # Step 5: Build UCF
        return UnifiedContent(
            id=str(uuid.uuid4()),
            source_type=ContentType.PAPER,
            source_file_path=str(pdf_path),
            title=metadata.get("title", pdf_path.stem),
            authors=metadata.get("authors", []),
            created_at=metadata.get("created", datetime.now()),
            ingested_at=datetime.now(),
            full_text=full_text,
            annotations=digital_annotations + handwritten_annotations,
            raw_file_hash=file_hash,
            processing_status="pending"
        )
    
    def _extract_text(self, pdf_path: Path) -> str:
        """Extract all printed text from PDF."""
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n\n".join(text_parts)
    
    def _extract_digital_annotations(self, pdf_path: Path) -> list[Annotation]:
        """Extract highlights and typed comments."""
        annotations = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract highlighted text
                for annot in page.annots or []:
                    if annot.get("subtype") == "Highlight":
                        # Get the highlighted text
                        rect = annot.get("rect")
                        chars = page.within_bbox(rect).chars
                        text = "".join(c["text"] for c in chars)
                        
                        annotations.append(Annotation(
                            type=AnnotationType.DIGITAL_HIGHLIGHT,
                            content=text,
                            page_number=page_num,
                            position={"rect": rect}
                        ))
        
        return annotations
    
    async def _extract_handwritten_annotations(self, pdf_path: Path) -> list[Annotation]:
        """Use Vision LLM to detect and transcribe handwritten notes."""
        annotations = []
        
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=300)
        
        for page_num, image in enumerate(images, 1):
            # First pass: detect if page has handwriting
            has_handwriting = await self._detect_handwriting(image)
            
            if has_handwriting:
                # Second pass: transcribe handwritten content
                transcription = await self._transcribe_handwriting(image, page_num)
                annotations.extend(transcription)
        
        return annotations
    
    async def _detect_handwriting(self, image) -> bool:
        """Quick check if page contains handwritten annotations."""
        # Convert PIL image to base64
        image_data = self._image_to_base64(image)
        
        response = await self.llm_client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Does this page contain any handwritten annotations, notes, or markings? Answer only 'yes' or 'no'."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }]
        )
        
        return "yes" in response.choices[0].message.content.lower()
    
    async def _transcribe_handwriting(self, image, page_num: int) -> list[Annotation]:
        """Transcribe all handwritten content on a page."""
        image_data = self._image_to_base64(image)
        
        prompt = """Analyze this document page and extract ALL handwritten annotations.
        
For each handwritten element, provide:
1. The transcribed text
2. Its approximate location (top/middle/bottom, left/margin/right)
3. Any nearby printed text it relates to

Format as JSON array:
[
  {
    "text": "transcribed handwritten text",
    "location": "top-right margin",
    "context": "nearby printed text or null",
    "type": "note|underline|arrow|diagram"
  }
]

If no handwritten content exists, return empty array: []
"""
        
        response = await self.llm_client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }]
        )
        
        # Parse response and convert to Annotation objects
        handwritten_items = self._parse_handwriting_response(response.choices[0].message.content)
        
        return [
            Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content=item["text"],
                page_number=page_num,
                context=item.get("context"),
                position={"location": item.get("location")}
            )
            for item in handwritten_items
        ]
```

#### Configuration

```yaml
# config/pipelines/pdf.yaml
pdf_processor:
  text_extraction:
    engine: "pymupdf"  # or "pdfplumber"
    
  annotation_extraction:
    highlight_engine: "pdfplumber"
    include_comments: true
    include_underlines: true
    
  handwriting_detection:
    enabled: true
    vision_model: "google:gemini-2.0-flash"
    image_dpi: 300
    batch_size: 5  # Pages to process in parallel
    
  deduplication:
    enabled: true
    hash_algorithm: "sha256"
```

---

### 4.2 Raindrop.io Sync

**Purpose**: Automatically sync bookmarked web articles with highlights and tags.

#### API Integration

```python
# pipelines/raindrop_sync.py

import httpx
from datetime import datetime, timedelta

class RaindropSync:
    BASE_URL = "https://api.raindrop.io/rest/v1"
    
    def __init__(self, access_token: str, llm_client):
        self.access_token = access_token
        self.llm_client = llm_client
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    async def sync_collection(
        self, 
        collection_id: int = 0,  # 0 = all items
        since: datetime = None
    ) -> list[UnifiedContent]:
        """Sync raindrops from a collection."""
        
        params = {"perpage": 50, "page": 0}
        if since:
            params["search"] = f"created:>{since.strftime('%Y-%m-%d')}"
        
        all_items = []
        while True:
            response = await self.client.get(
                f"{self.BASE_URL}/raindrops/{collection_id}",
                params=params
            )
            data = response.json()
            
            if not data.get("items"):
                break
                
            for item in data["items"]:
                content = await self._process_raindrop(item)
                if content:
                    all_items.append(content)
            
            params["page"] += 1
            if params["page"] * 50 >= data.get("count", 0):
                break
        
        return all_items
    
    async def _process_raindrop(self, item: dict) -> UnifiedContent:
        """Convert a raindrop to UCF."""
        
        # Fetch full article content
        article_content = await self._fetch_article_content(item["link"])
        
        # Extract highlights from raindrop
        highlights = await self._get_highlights(item["_id"])
        
        annotations = [
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=h["text"],
                context=h.get("note")
            )
            for h in highlights
        ]
        
        return UnifiedContent(
            id=str(uuid.uuid4()),
            source_type=ContentType.ARTICLE,
            source_url=item["link"],
            title=item.get("title", "Untitled"),
            authors=[item.get("creator", "Unknown")],
            created_at=datetime.fromisoformat(item["created"].replace("Z", "+00:00")),
            ingested_at=datetime.now(),
            full_text=article_content,
            annotations=annotations,
            processing_status="pending"
        )
    
    async def _fetch_article_content(self, url: str) -> str:
        """Fetch and extract main content from article URL."""
        # Use readability/trafilatura for content extraction
        from trafilatura import fetch_url, extract
        
        downloaded = fetch_url(url)
        if downloaded:
            return extract(downloaded, include_comments=False) or ""
        return ""
    
    async def _get_highlights(self, raindrop_id: int) -> list[dict]:
        """Get highlights for a specific raindrop."""
        response = await self.client.get(
            f"{self.BASE_URL}/raindrop/{raindrop_id}"
        )
        data = response.json()
        return data.get("item", {}).get("highlights", [])
```

#### Sync Scheduling

```python
# scripts/daily_sync.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pipelines.raindrop_sync import RaindropSync

async def run_raindrop_sync():
    """Daily sync job for Raindrop.io."""
    sync = RaindropSync(
        access_token=os.environ["RAINDROP_ACCESS_TOKEN"],
        llm_client=get_llm_client()
    )
    
    # Get items from last 24 hours
    since = datetime.now() - timedelta(days=1)
    items = await sync.sync_collection(since=since)
    
    # Queue for processing
    for item in items:
        await queue_for_processing(item)
    
    logger.info(f"Synced {len(items)} items from Raindrop")

scheduler = AsyncIOScheduler()
scheduler.add_job(run_raindrop_sync, 'cron', hour=6)  # Run at 6 AM daily
```

---

### 4.3 Book Photo OCR Pipeline

**Purpose**: Extract highlighted text and handwritten margin notes from photos of physical book pages.

#### Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     BOOK PHOTOS INPUT                            │
│        (multiple images of highlighted/annotated pages)          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    1. Image Preprocessing      │
              │  (rotation, deskew, contrast) │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    2. Vision OCR              │
              │  (full page text extraction)  │
              └───────────────┬───────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│  3a. Highlight Detection │     │  3b. Margin Note OCR    │
│  (marked/underlined     │     │  (handwritten notes in  │
│   passages in text)     │     │   margins & whitespace) │
└───────────────┬─────────┘     └───────────────┬─────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    4. Context Association     │
              │  (link margin notes to nearby │
              │   highlighted/printed text)   │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    5. Book Metadata           │
              │  (title, author from user     │
              │   or ISBN lookup)             │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    6. Aggregate by Chapter    │
              │  (group annotations logically)│
              └───────────────────────────────┘
```

#### Implementation

```python
# pipelines/book_ocr.py

class BookOCRPipeline:
    def __init__(self, llm_client, vision_model: str = "google:gemini-2.0-flash"):
        self.llm_client = llm_client
        self.vision_model = vision_model
    
    async def process_book_photos(
        self,
        image_paths: list[Path],
        book_metadata: dict = None  # Optional: title, author, isbn
    ) -> UnifiedContent:
        """Process a batch of book page photos."""
        
        all_annotations = []
        full_text_parts = []
        
        for page_num, image_path in enumerate(sorted(image_paths), 1):
            # Preprocess image
            processed_image = self._preprocess_image(image_path)
            
            # Extract text, highlights, and margin notes
            page_result = await self._process_page(processed_image, page_num)
            
            full_text_parts.append(page_result["full_text"])
            all_annotations.extend(page_result["annotations"])
        
        # Get or infer book metadata
        if not book_metadata:
            book_metadata = await self._infer_metadata(full_text_parts[0])
        
        return UnifiedContent(
            id=str(uuid.uuid4()),
            source_type=ContentType.BOOK,
            title=book_metadata.get("title", "Unknown Book"),
            authors=book_metadata.get("authors", []),
            created_at=datetime.now(),
            ingested_at=datetime.now(),
            full_text="\n\n---\n\n".join(full_text_parts),
            annotations=all_annotations,
            asset_paths=[str(p) for p in image_paths],
            processing_status="pending"
        )
    
    async def _process_page(self, image, page_num: int) -> dict:
        """Extract text, highlights, and handwritten margin notes from a page."""
        image_data = self._image_to_base64(image)
        
        prompt = """Analyze this book page photo and extract:

1. ALL printed text on the page (full transcription)
2. Any HIGHLIGHTED or MARKED passages (underlined, circled, or highlighted text)
3. Any HANDWRITTEN MARGIN NOTES (notes written in margins, whitespace, or between lines)

Return as JSON:
{
  "full_text": "complete printed page text...",
  "highlights": [
    {
      "text": "highlighted passage from printed text",
      "type": "highlight|underline|circle",
      "location": "top|middle|bottom of page"
    }
  ],
  "margin_notes": [
    {
      "text": "transcribed handwritten note",
      "location": "left-margin|right-margin|top-margin|bottom-margin|interline",
      "related_text": "nearby printed text this note refers to, or null",
      "type": "note|question|definition|summary|connection"
    }
  ]
}

Important:
- Distinguish between printed book text and handwritten annotations
- For margin notes, identify what printed text they relate to if possible
- Preserve the meaning even if handwriting is partially unclear (use [unclear] for illegible parts)
- Include ALL handwritten content, even brief marks like "!" or "?"
"""
        
        response = await self.llm_client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }]
        )
        
        return self._parse_page_response(response.choices[0].message.content, page_num)
    
    def _parse_page_response(self, response_text: str, page_num: int) -> dict:
        """Parse LLM response into structured annotations."""
        import json
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        data = json.loads(response_text.strip())
        
        annotations = []
        
        # Process highlights
        for h in data.get("highlights", []):
            annotations.append(Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=h["text"],
                page_number=page_num,
                position={"location": h.get("location")},
                context=None
            ))
        
        # Process handwritten margin notes
        for note in data.get("margin_notes", []):
            annotations.append(Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content=note["text"],
                page_number=page_num,
                position={
                    "location": note.get("location"),
                    "note_type": note.get("type")
                },
                context=note.get("related_text")
            ))
        
        return {
            "full_text": data.get("full_text", ""),
            "annotations": annotations
        }
    
    def _preprocess_image(self, image_path: Path):
        """Enhance image quality for OCR."""
        from PIL import Image, ImageEnhance, ImageFilter
        
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        
        return img
```

---

### 4.4 GitHub Repository Importer

**Purpose**: Analyze starred repositories and extract learnings.

```python
# pipelines/github_importer.py

import httpx
from pathlib import Path

class GitHubImporter:
    BASE_URL = "https://api.github.com"
    
    def __init__(self, access_token: str, llm_client):
        self.access_token = access_token
        self.llm_client = llm_client
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
    
    async def import_starred_repos(self, limit: int = 50) -> list[UnifiedContent]:
        """Import recently starred repositories."""
        response = await self.client.get(
            f"{self.BASE_URL}/user/starred",
            params={"per_page": limit, "sort": "created", "direction": "desc"}
        )
        
        repos = response.json()
        results = []
        
        for repo in repos:
            content = await self._analyze_repo(repo)
            results.append(content)
        
        return results
    
    async def _analyze_repo(self, repo: dict) -> UnifiedContent:
        """Analyze a repository and extract key information."""
        
        # Get README content
        readme = await self._get_readme(repo["full_name"])
        
        # Get repository structure
        tree = await self._get_tree(repo["full_name"])
        
        # Get key files (package.json, requirements.txt, etc.)
        key_files = await self._get_key_files(repo["full_name"], tree)
        
        # Generate analysis
        analysis = await self._generate_analysis(repo, readme, tree, key_files)
        
        return UnifiedContent(
            id=str(uuid.uuid4()),
            source_type=ContentType.CODE,
            source_url=repo["html_url"],
            title=repo["full_name"],
            authors=[repo["owner"]["login"]],
            created_at=datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")),
            ingested_at=datetime.now(),
            full_text=analysis,
            annotations=[],
            processing_status="pending"
        )
    
    async def _generate_analysis(
        self, 
        repo: dict, 
        readme: str, 
        tree: list,
        key_files: dict
    ) -> str:
        """Use LLM to generate repository analysis."""
        
        prompt = f"""Analyze this GitHub repository and provide a structured summary.

Repository: {repo['full_name']}
Description: {repo.get('description', 'No description')}
Stars: {repo['stargazers_count']}
Language: {repo.get('language', 'Unknown')}

README:
{readme[:5000]}

File Structure:
{self._format_tree(tree[:50])}

Key Configuration Files:
{self._format_key_files(key_files)}

Provide:
1. **Purpose**: What does this repository do?
2. **Architecture**: Key design patterns and structure
3. **Tech Stack**: Languages, frameworks, dependencies
4. **Key Learnings**: What can be learned from this codebase?
5. **Notable Code**: Any interesting patterns or implementations
"""
        
        response = await self.llm_client.chat.completions.create(
            model="anthropic:claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
```

---

### 4.5 Voice Memo Transcription

**Purpose**: Convert voice recordings to text notes.

```python
# pipelines/voice_transcribe.py

import openai
from pathlib import Path

class VoiceTranscriber:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.whisper_client = openai.OpenAI()
    
    async def transcribe(self, audio_path: Path) -> UnifiedContent:
        """Transcribe audio file and optionally expand the note."""
        
        # Transcribe with Whisper
        with open(audio_path, "rb") as audio_file:
            transcript = self.whisper_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Expand fleeting note into structured content
        expanded = await self._expand_note(transcript)
        
        return UnifiedContent(
            id=str(uuid.uuid4()),
            source_type=ContentType.VOICE_MEMO,
            source_file_path=str(audio_path),
            title=self._generate_title(expanded),
            authors=[],
            created_at=datetime.now(),
            ingested_at=datetime.now(),
            full_text=expanded,
            annotations=[
                Annotation(
                    type=AnnotationType.TYPED_COMMENT,
                    content=f"Original transcript: {transcript}"
                )
            ],
            processing_status="pending"
        )
    
    async def _expand_note(self, transcript: str) -> str:
        """Expand a voice memo into a proper note."""
        
        prompt = f"""Transform this voice memo transcript into a well-structured note.
        
Transcript:
{transcript}

Instructions:
- Fix any transcription errors
- Organize into logical sections if appropriate
- Add any implicit context
- Keep the original meaning and intent
- Format in Markdown

Return only the expanded note, no commentary."""
        
        response = await self.llm_client.chat.completions.create(
            model="openai:gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
```

---

### 4.6 Quick Capture API

**Purpose**: Low-friction capture for ideas and URLs.

```python
# backend/app/routers/capture.py

from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

router = APIRouter(prefix="/api/capture", tags=["capture"])

@router.post("/text")
async def capture_text(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)  # Comma-separated
) -> dict:
    """Quick text capture - ideas, notes, thoughts."""
    
    ucf = UnifiedContent(
        id=str(uuid.uuid4()),
        source_type=ContentType.IDEA,
        title=title or _generate_title(content),
        authors=[],
        created_at=datetime.now(),
        ingested_at=datetime.now(),
        full_text=content,
        processing_status="pending"
    )
    
    # Queue for processing
    await queue_for_processing(ucf, priority="high")
    
    return {"status": "captured", "id": ucf.id}

@router.post("/url")
async def capture_url(
    url: str = Form(...),
    notes: Optional[str] = Form(None)
) -> dict:
    """Capture a URL for later processing."""
    
    # Quick fetch for title
    title = await _fetch_page_title(url)
    
    ucf = UnifiedContent(
        id=str(uuid.uuid4()),
        source_type=ContentType.ARTICLE,
        source_url=url,
        title=title,
        authors=[],
        created_at=datetime.now(),
        ingested_at=datetime.now(),
        full_text="",  # Will be fetched during processing
        annotations=[
            Annotation(
                type=AnnotationType.TYPED_COMMENT,
                content=notes
            )
        ] if notes else [],
        processing_status="pending"
    )
    
    await queue_for_processing(ucf)
    
    return {"status": "captured", "id": ucf.id, "title": title}

@router.post("/photo")
async def capture_photo(
    file: UploadFile = File(...),
    capture_type: str = Form("general"),  # book_page | whiteboard | general
    notes: Optional[str] = Form(None)
) -> dict:
    """Capture a photo for OCR processing."""
    
    # Save file
    file_path = await _save_upload(file)
    
    ucf = UnifiedContent(
        id=str(uuid.uuid4()),
        source_type=ContentType.IDEA,
        source_file_path=str(file_path),
        title=f"Photo capture - {capture_type}",
        authors=[],
        created_at=datetime.now(),
        ingested_at=datetime.now(),
        full_text="",  # Will be extracted during processing
        asset_paths=[str(file_path)],
        processing_status="pending"
    )
    
    await queue_for_processing(ucf, metadata={"capture_type": capture_type})
    
    return {"status": "captured", "id": ucf.id}

@router.post("/voice")
async def capture_voice(
    file: UploadFile = File(...)
) -> dict:
    """Capture a voice memo for transcription."""
    
    file_path = await _save_upload(file, directory="voice_memos")
    
    ucf = UnifiedContent(
        id=str(uuid.uuid4()),
        source_type=ContentType.VOICE_MEMO,
        source_file_path=str(file_path),
        title=f"Voice memo - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        authors=[],
        created_at=datetime.now(),
        ingested_at=datetime.now(),
        full_text="",  # Will be transcribed
        processing_status="pending"
    )
    
    await queue_for_processing(ucf, priority="high")
    
    return {"status": "captured", "id": ucf.id}
```

---

## 5. Processing Queue

All ingested content goes through a centralized queue for async processing.

```python
# backend/app/services/queue.py

from celery import Celery
from redis import Redis

celery_app = Celery(
    "second_brain",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task(bind=True, max_retries=3)
def process_content(self, content_id: str, metadata: dict = None):
    """Process ingested content through LLM pipeline."""
    try:
        # Load content from database
        content = load_content(content_id)
        
        # Run through LLM processing pipeline
        processed = await llm_processing_pipeline(content, metadata)
        
        # Store results
        await save_processed_content(processed)
        
        # Update status
        await update_status(content_id, "completed")
        
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

async def queue_for_processing(
    content: UnifiedContent, 
    priority: str = "normal",
    metadata: dict = None
):
    """Add content to processing queue."""
    
    # Save to database first
    await save_content(content)
    
    # Queue task
    task_options = {
        "high": {"queue": "high_priority"},
        "normal": {"queue": "default"},
        "low": {"queue": "low_priority"}
    }
    
    process_content.apply_async(
        args=[content.id, metadata],
        **task_options.get(priority, {})
    )
```

---

## 6. Error Handling & Monitoring

### Retry Strategy

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "retry_delays": [60, 300, 900],  # 1 min, 5 min, 15 min
    "retry_on": [
        "RateLimitError",
        "APIConnectionError",
        "TimeoutError"
    ]
}
```

### Monitoring Metrics

| Metric | Description |
|--------|-------------|
| `ingestion_total` | Total items ingested by source type |
| `ingestion_errors` | Failed ingestions by error type |
| `ingestion_latency` | Time from capture to queued |
| `processing_queue_size` | Items waiting for processing |
| `ocr_confidence` | Average OCR confidence scores |

---

## 7. Configuration

```yaml
# config/ingestion.yaml
ingestion:
  # Global settings
  deduplication:
    enabled: true
    window_days: 30
    
  # Pipeline-specific settings
  pdf:
    max_file_size_mb: 50
    extract_images: true
    handwriting_detection: true
    
  raindrop:
    sync_interval_hours: 6
    collections: []  # Empty = all collections
    fetch_full_content: true
    
  github:
    sync_starred: true
    max_repos: 100
    analyze_structure: true
    
  ocr:
    default_model: "google:gemini-2.0-flash"
    fallback_model: "openai:gpt-4o"
    image_dpi: 300
    
  voice:
    transcription_model: "whisper-1"
    expand_notes: true
```

---

## 8. Related Documents

- `02_llm_processing_layer.md` — How content is processed after ingestion
- `09_data_models.md` — Database schemas for storing ingested content
- `08_mobile_capture.md` — Mobile-specific capture workflows

