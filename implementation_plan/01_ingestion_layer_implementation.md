# Ingestion Layer Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: December 2025  
> **Target Phase**: Phase 2 (Weeks 3-6 per roadmap)  
> **Design Doc**: `design_docs/01_ingestion_layer.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Ingestion Layer, which captures content from diverse sources (PDFs, web articles, book photos, code repos, voice memos, and quick notes) and normalizes them into the Unified Content Format (UCF) for downstream LLM processing.

### OCR Strategy

**Model-Agnostic Design** — The OCR pipeline is designed to work with any vision-capable LLM via a unified interface. The default configuration uses **Mistral OCR** for its state-of-the-art performance:
- Native structured output (Markdown, JSON) ideal for RAG pipelines
- High multilingual support and benchmark-leading accuracy on complex layouts
- Batch inference support for large document processing

The model can be swapped via configuration (e.g., to GPT-4V, Gemini, Claude) without code changes.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| PDF text/annotation extraction | LLM processing of content |
| Handwritten note OCR via Vision LLM | Obsidian note generation |
| Raindrop.io API integration | Knowledge graph population |
| Book photo OCR pipeline | Learning system integration |
| GitHub repository analysis | Frontend UI components |
| Voice memo transcription | Mobile PWA (separate plan) |
| Quick capture REST API | Multi-user authentication |
| Processing queue (Celery/Redis) | Production deployment |

---

## 2. Prerequisites

### 2.1 Infrastructure (Already Configured)

- [x] Docker Compose environment
- [x] Redis container for queue backend
- [x] PostgreSQL container for metadata
- [x] FastAPI backend skeleton

### 2.2 Dependencies to Install

```txt
# Add to backend/requirements.txt
pymupdf>=1.24.0           # PDF text extraction
pdfplumber>=0.11.0        # PDF annotation extraction  
pdf2image>=1.17.0         # PDF to image conversion
Pillow>=10.0.0            # Image processing
trafilatura>=1.6.0        # Web article extraction
httpx>=0.27.0             # Async HTTP client
celery>=5.4.0             # Distributed task queue for async processing
python-magic>=0.4.27      # File type detection
openai>=1.40.0            # Whisper API for voice transcription
litellm>=1.40.0           # Model-agnostic LLM interface with spend tracking & rate limiting
```

### 2.3 External Services Required

| Service | Purpose | Required By |
|---------|---------|-------------|
| OpenAI API | Whisper transcription | Voice pipeline |
| Vision LLM Provider | OCR (configurable via `OCR_MODEL`) | Book/PDF OCR, handwriting extraction |
| Raindrop.io API | Bookmark sync | Raindrop pipeline |
| GitHub API | Repository analysis | GitHub pipeline |

> **Model-Agnostic OCR**: The system uses [LiteLLM](https://docs.litellm.ai/) to provide a unified interface to 100+ LLM providers. Set `OCR_MODEL` to any vision-capable model (e.g., `mistral/pixtral-large-latest`, `openai/gpt-4o`, `anthropic/claude-3-5-sonnet-20241022`, `gemini/gemini-2.0-flash`). Default is Mistral OCR for best structured extraction performance.

### LLM Abstraction Layer: LiteLLM vs AISuite

We evaluated two model-agnostic frameworks for our OCR pipeline:

| Feature | [LiteLLM](https://docs.litellm.ai/) | [AISuite](https://github.com/andrewyng/aisuite) |
|---------|---------|---------|
| **Provider Support** | 100+ providers | ~10 major providers |
| **Spend Tracking** | ✅ Built-in cost tracking per request | ❌ Not available |
| **Budget Limits** | ✅ Set max budget, alerts on threshold | ❌ Not available |
| **Rate Limiting** | ✅ TPM/RPM limits, queuing | ❌ Not available |
| **Fallbacks** | ✅ Automatic failover to backup models | ❌ Manual implementation |
| **Caching** | ✅ Redis/in-memory response caching | ❌ Not available |
| **Load Balancing** | ✅ Round-robin across deployments | ❌ Not available |
| **Async Support** | ✅ Native `acompletion()` | ⚠️ Sync only, needs wrapper |
| **Complexity** | Medium (more config options) | Low (minimal API) |
| **Model Format** | `provider/model-name` | `provider:model-name` |

**Our Choice: LiteLLM**

We chose LiteLLM because:
1. **Spend Tracking**: Vision API calls are expensive ($0.01-0.03 per image). Built-in cost tracking helps monitor and optimize usage.
2. **Rate Limiting**: Prevents runaway costs from bugs or batch processing spikes.
3. **Budget Alerts**: Set monthly limits and get notified before overspending.
4. **Fallbacks**: If Mistral is rate-limited, automatically try GPT-4V without code changes.
5. **Native Async**: Better performance in our async FastAPI/Celery architecture.

> **Note**: AISuite (by Andrew Ng) is excellent for simpler use cases where you just need provider abstraction without operational features. Consider it if you want minimal dependencies and don't need spend management.

### 2.4 Environment Variables

```bash
# .env file additions
OPENAI_API_KEY=sk-...            # For Whisper + optional GPT-4V OCR
MISTRAL_API_KEY=...              # For Mistral OCR (default)
ANTHROPIC_API_KEY=...            # Optional: for Claude vision
RAINDROP_ACCESS_TOKEN=...
GITHUB_ACCESS_TOKEN=ghp_...
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
OBSIDIAN_VAULT_PATH=/path/to/vault
UPLOAD_DIR=/path/to/uploads

# OCR Configuration (model-agnostic via LiteLLM)
OCR_MODEL=mistral/pixtral-large-latest  # Format: provider/model-name
                                         # Alternatives: openai/gpt-4o, anthropic/claude-3-5-sonnet-20241022
                                         #               gemini/gemini-2.0-flash, azure/gpt-4-vision
OCR_MAX_TOKENS=4000
OCR_USE_JSON_MODE=true           # Request structured JSON output

# LiteLLM Operational Controls (optional but recommended)
LITELLM_BUDGET_MAX=100.0         # Monthly budget limit in USD
LITELLM_BUDGET_ALERT=80.0        # Alert when 80% of budget used
LITELLM_LOG_COSTS=true           # Log cost per request
```

---

## 3. Implementation Phases

### Phase 2A: Foundation (Week 3)

#### Task 2A.1: Project Structure Setup

**Why this matters:** A well-organized directory structure is essential for maintainability as the ingestion layer grows. Separating pipelines, utilities, routers, and services ensures each component has a clear responsibility and can be developed/tested independently. This structure follows Python best practices and enables easy addition of new content sources.

Create the ingestion module directory structure:

```
backend/
├── app/
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract base pipeline
│   │   ├── pdf_processor.py     # PDF pipeline
│   │   ├── raindrop_sync.py     # Raindrop pipeline
│   │   ├── book_ocr.py          # Book photo pipeline
│   │   ├── github_importer.py   # GitHub pipeline
│   │   ├── voice_transcribe.py  # Voice memo pipeline
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── image_utils.py   # Image preprocessing
│   │       ├── text_utils.py    # Text cleaning
│   │       └── hash_utils.py    # Deduplication
│   ├── routers/
│   │   ├── capture.py           # Quick capture endpoints
│   │   └── ingestion.py         # Pipeline trigger endpoints
│   ├── services/
│   │   ├── queue.py             # Celery task definitions
│   │   └── storage.py           # File storage handling
│   └── config/
│       └── pipelines.py         # Pipeline configuration
```

**Deliverables:**
- [ ] Directory structure created
- [ ] `__init__.py` files with proper exports
- [ ] Configuration loader for pipeline settings

**Estimated Time:** 2 hours

---

#### Task 2A.2: Unified Content Format (UCF) Models

**Why this matters:** The Unified Content Format (UCF) is the cornerstone of our ingestion architecture. Regardless of source (PDF, web article, book photo, voice memo), all content is normalized into this common format. This enables:
- **Downstream processing consistency**: LLM processors and knowledge extractors work with one format
- **Source-agnostic storage**: PostgreSQL stores all content uniformly
- **Annotation preservation**: Highlights, handwritten notes, and comments travel with content
- **Validation**: Pydantic ensures data integrity before storage

Implement the core Pydantic models from `09_data_models.md`:

```python
# backend/app/models/content.py

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class ContentType(str, Enum):
    PAPER = "paper"
    ARTICLE = "article"
    BOOK = "book"
    CODE = "code"
    IDEA = "idea"
    VOICE_MEMO = "voice_memo"

class AnnotationType(str, Enum):
    DIGITAL_HIGHLIGHT = "digital_highlight"
    HANDWRITTEN_NOTE = "handwritten_note"
    TYPED_COMMENT = "typed_comment"
    DIAGRAM = "diagram"

class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: AnnotationType
    content: str
    page_number: Optional[int] = None
    position: Optional[dict] = None
    context: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)

class UnifiedContent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: ContentType
    source_url: Optional[str] = None
    source_file_path: Optional[str] = None
    title: str
    authors: list[str] = []
    created_at: datetime
    ingested_at: datetime = Field(default_factory=datetime.now)
    full_text: str
    annotations: list[Annotation] = []
    raw_file_hash: Optional[str] = None
    asset_paths: list[str] = []
    processing_status: str = "pending"
    error_message: Optional[str] = None
    obsidian_path: Optional[str] = None
```

**Deliverables:**
- [ ] `ContentType` enum
- [ ] `AnnotationType` enum
- [ ] `Annotation` model with validation
- [ ] `UnifiedContent` model with defaults
- [ ] Unit tests for model validation

**Estimated Time:** 3 hours

---

#### Task 2A.3: Abstract Base Pipeline

**Why this matters:** The abstract base pipeline enforces a consistent interface across all content sources. Every pipeline (PDF, Raindrop, Book OCR, Voice, GitHub) must implement the same `process()` and `supports()` methods. This enables:
- **Polymorphism**: The system can route content to the appropriate pipeline dynamically
- **Shared utilities**: Hash calculation, duplicate detection, and logging are inherited
- **Testability**: Each pipeline can be tested against the same interface contract
- **Extensibility**: Adding a new content source only requires implementing the base interface

Create the base class that all pipelines inherit from:

```python
# backend/app/pipelines/base.py

from abc import ABC, abstractmethod
from app.models.content import UnifiedContent
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)

class BasePipeline(ABC):
    """Abstract base class for all ingestion pipelines."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process(self, input_data) -> UnifiedContent:
        """Process input and return UnifiedContent."""
        pass
    
    @abstractmethod
    def supports(self, input_data) -> bool:
        """Check if this pipeline can handle the input."""
        pass
    
    def calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def check_duplicate(self, file_hash: str) -> Optional[UnifiedContent]:
        """Check if content with this hash already exists."""
        # Will query PostgreSQL content table
        pass
```

**Deliverables:**
- [ ] `BasePipeline` abstract class
- [ ] Hash calculation utility
- [ ] Duplicate checking interface
- [ ] Logging setup

**Estimated Time:** 2 hours

---

#### Task 2A.4: Celery Queue Configuration

**Why Celery?** Content ingestion involves time-consuming operations: OCR API calls (2-10s per page), voice transcription (30s+ for long memos), and article fetching. Running these synchronously would block the API and create poor user experience. Celery provides:
- **Async processing**: User uploads content → immediate response → background processing
- **Retry logic**: Transient API failures automatically retry with exponential backoff
- **Priority queues**: Voice memos (user waiting) process before batch PDF imports
- **Scalability**: Add more workers as content volume grows
- **Observability**: Track job status, failures, and processing times

**Why Redis as broker?** Redis is already in our stack (for caching), is lightweight, and handles Celery's message queue needs well for single-server deployments.

Set up the async processing queue:

```python
# backend/app/services/queue.py

from celery import Celery
from app.config import settings

celery_app = Celery(
    "second_brain",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.services.tasks.process_content": {"queue": "default"},
        "app.services.tasks.process_content_high": {"queue": "high_priority"},
        "app.services.tasks.process_content_low": {"queue": "low_priority"},
    },
    task_default_retry_delay=60,
    task_max_retries=3,
)
```

```python
# backend/app/services/tasks.py

from app.services.queue import celery_app
from app.models.content import UnifiedContent
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_content(self, content_id: str, metadata: dict = None):
    """Process ingested content through LLM pipeline."""
    try:
        logger.info(f"Processing content {content_id}")
        # Load content from database
        # Run through LLM processing (Phase 3)
        # Update status to completed
        return {"status": "completed", "content_id": content_id}
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

**Deliverables:**
- [ ] Celery app configuration
- [ ] Task routing for priorities
- [ ] Retry configuration
- [ ] Basic task structure

**Estimated Time:** 3 hours

---

#### Task 2A.5: Database Schema & Migrations

**Why PostgreSQL for content storage?** While Obsidian files are the user-facing knowledge base, we need a relational database for:
- **Processing state**: Track what's pending, completed, or failed
- **Deduplication**: Hash-based lookup prevents re-processing the same file
- **Querying**: Find content by source type, date range, or processing status
- **Annotations**: Store structured annotation data with foreign key relationships
- **Full-text search**: PostgreSQL's `tsvector` enables searching across all ingested content

**Why Alembic?** Database migrations ensure schema changes are versioned, reversible, and can be applied consistently across development, staging, and production environments.

Create PostgreSQL tables for content storage:

```python
# backend/app/db/models.py

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from datetime import datetime

class Content(Base):
    __tablename__ = "content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False, index=True)
    source_url = Column(Text)
    source_file_path = Column(Text)
    title = Column(String(500), nullable=False)
    authors = Column(ARRAY(String))
    created_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    full_text = Column(Text)
    raw_file_hash = Column(String(64), index=True)
    processing_status = Column(String(20), default="pending", index=True)
    error_message = Column(Text)
    obsidian_path = Column(Text)
    
    annotations = relationship("Annotation", back_populates="content", cascade="all, delete-orphan")

class Annotation(Base):
    __tablename__ = "annotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    type = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    page_number = Column(Integer)
    position = Column(JSON)
    context = Column(Text)
    confidence = Column(Float)
    
    content = relationship("Content", back_populates="annotations")
```

```bash
# Alembic migration
alembic revision --autogenerate -m "Create content and annotations tables"
alembic upgrade head
```

**Deliverables:**
- [ ] Content SQLAlchemy model
- [ ] Annotation SQLAlchemy model
- [ ] Alembic migration for tables
- [ ] Indexes on frequently queried columns

**Estimated Time:** 2 hours

---

### Phase 2B: PDF Pipeline (Week 4)

**Why PDFs first?** Academic papers, research documents, and ebooks are primary knowledge sources. PDFs are complex—they contain text, embedded images, annotations, and sometimes handwritten notes. Solving PDF ingestion covers ~60% of typical knowledge worker content.

#### Task 2B.1: PDF Text Extraction

**Why PyMuPDF?** We evaluated multiple PDF libraries:
- **PyMuPDF (fitz)**: Fast, handles most PDFs well, extracts text with layout awareness
- **pdfplumber**: Better for extracting annotations and structured elements like tables
- **pdfminer**: Slower, lower-level, better for edge cases

We use PyMuPDF for text extraction and pdfplumber for annotations—combining their strengths.

Implement basic PDF text extraction with PyMuPDF:

```python
# backend/app/pipelines/pdf_processor.py

import fitz  # PyMuPDF
from pathlib import Path
from app.pipelines.base import BasePipeline
from app.models.content import UnifiedContent, ContentType, Annotation, AnnotationType
from datetime import datetime
import re

class PDFProcessor(BasePipeline):
    def __init__(
        self, 
        ocr_model: str = "mistral:pixtral-large-latest",
        ocr_max_tokens: int = 4000,
        use_json_mode: bool = True
    ):
        super().__init__()
        self.ocr_model = ocr_model
        self.ocr_max_tokens = ocr_max_tokens
        self.use_json_mode = use_json_mode
    
    def supports(self, input_data) -> bool:
        if isinstance(input_data, Path):
            return input_data.suffix.lower() == ".pdf"
        return False
    
    async def process(self, pdf_path: Path) -> UnifiedContent:
        file_hash = self.calculate_hash(pdf_path)
        
        # Check for duplicate
        existing = await self.check_duplicate(file_hash)
        if existing:
            self.logger.info(f"Duplicate detected: {pdf_path}")
            return existing
        
        # Extract metadata
        metadata = self._extract_metadata(pdf_path)
        
        # Extract text
        full_text = self._extract_text(pdf_path)
        
        # Extract digital annotations
        annotations = self._extract_annotations(pdf_path)
        
        return UnifiedContent(
            source_type=ContentType.PAPER,
            source_file_path=str(pdf_path),
            title=metadata.get("title", pdf_path.stem),
            authors=metadata.get("authors", []),
            created_at=metadata.get("created", datetime.now()),
            full_text=full_text,
            annotations=annotations,
            raw_file_hash=file_hash,
            processing_status="pending"
        )
    
    def _extract_metadata(self, pdf_path: Path) -> dict:
        doc = fitz.open(pdf_path)
        meta = doc.metadata
        
        result = {
            "title": meta.get("title") or pdf_path.stem,
            "authors": [],
            "created": None
        }
        
        # Parse author field
        if meta.get("author"):
            authors = re.split(r'[,;&]', meta["author"])
            result["authors"] = [a.strip() for a in authors if a.strip()]
        
        # Parse creation date
        if meta.get("creationDate"):
            try:
                date_str = meta["creationDate"].replace("D:", "")[:8]
                result["created"] = datetime.strptime(date_str, "%Y%m%d")
            except:
                result["created"] = datetime.now()
        
        doc.close()
        return result
    
    def _extract_text(self, pdf_path: Path) -> str:
        doc = fitz.open(pdf_path)
        text_parts = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"[Page {page_num}]\n{text}")
        
        doc.close()
        return "\n\n".join(text_parts)
```

**Deliverables:**
- [ ] PDF metadata extraction
- [ ] Full text extraction with page markers
- [ ] Author name parsing
- [ ] Date parsing with fallbacks

**Estimated Time:** 4 hours

---

#### Task 2B.2: PDF Annotation Extraction

**Why extract annotations?** Highlights and comments represent the user's *engagement* with content—they're often more valuable than the source text itself. A highlighted passage indicates "this is important," and a comment captures thinking in context. Preserving these annotations ensures the knowledge graph reflects not just *what* was read, but *what mattered*.

Extract digital highlights and comments:

```python
# Add to pdf_processor.py

import pdfplumber

def _extract_annotations(self, pdf_path: Path) -> list[Annotation]:
    annotations = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_annots = page.annots or []
            
            for annot in page_annots:
                annot_type = annot.get("subtype", "").lower()
                
                if annot_type == "highlight":
                    # Extract highlighted text
                    text = self._get_text_in_rect(page, annot.get("rect"))
                    if text:
                        annotations.append(Annotation(
                            type=AnnotationType.DIGITAL_HIGHLIGHT,
                            content=text,
                            page_number=page_num,
                            position={"rect": annot.get("rect")}
                        ))
                
                elif annot_type in ("text", "freetext", "popup"):
                    # Extract text comments
                    content = annot.get("contents") or annot.get("text", "")
                    if content:
                        annotations.append(Annotation(
                            type=AnnotationType.TYPED_COMMENT,
                            content=content,
                            page_number=page_num,
                            position={"rect": annot.get("rect")}
                        ))
                
                elif annot_type == "underline":
                    text = self._get_text_in_rect(page, annot.get("rect"))
                    if text:
                        annotations.append(Annotation(
                            type=AnnotationType.DIGITAL_HIGHLIGHT,
                            content=text,
                            page_number=page_num,
                            position={"rect": annot.get("rect"), "style": "underline"}
                        ))
    
    return annotations

def _get_text_in_rect(self, page, rect) -> str:
    if not rect:
        return ""
    try:
        crop = page.within_bbox(rect)
        chars = crop.chars
        return "".join(c.get("text", "") for c in chars).strip()
    except:
        return ""
```

**Deliverables:**
- [ ] Highlight text extraction
- [ ] Comment/popup extraction
- [ ] Underline detection
- [ ] Bounding box handling

**Estimated Time:** 4 hours

---

#### Task 2B.3: Handwritten Annotation OCR

**Why Vision LLM for handwriting?** Traditional OCR (Tesseract, etc.) fails on handwritten text, especially margin notes in varied handwriting styles. Modern Vision LLMs like Mistral's Pixtral, GPT-4V, and Claude can:
- Recognize diverse handwriting styles
- Understand context (a "?" near text means "question about this")
- Distinguish printed text from handwritten annotations
- Extract meaning from diagrams and arrows

This is a key differentiator—most note systems ignore handwritten annotations entirely.

Implement Vision LLM-based handwriting detection and transcription using a **model-agnostic** approach via LiteLLM:

> **Model-Agnostic Design**: The OCR pipeline uses [LiteLLM](https://docs.litellm.ai/) to support 100+ vision-capable models. Configure via `OCR_MODEL` environment variable using format `provider/model-name`. Default is Mistral for best structured extraction performance.

```python
# Add to pdf_processor.py

from pdf2image import convert_from_path
from app.pipelines.utils.image_utils import image_to_base64
from app.pipelines.utils.ocr_client import vision_completion
import json

async def _extract_handwritten_annotations(self, pdf_path: Path) -> list[Annotation]:
    annotations = []
    images = convert_from_path(pdf_path, dpi=300)
    
    for page_num, image in enumerate(images, 1):
        # Quick detection pass
        has_handwriting = await self._detect_handwriting(image)
        
        if has_handwriting:
            self.logger.info(f"Handwriting detected on page {page_num}")
            page_annotations = await self._transcribe_handwriting(image, page_num)
            annotations.extend(page_annotations)
    
    return annotations

async def _detect_handwriting(self, image) -> bool:
    """Detect if page contains handwritten annotations."""
    image_data = image_to_base64(image)
    
    response = await vision_completion(
        model=self.ocr_model,
        prompt="Does this document page contain any handwritten annotations, notes, or markings? Respond only with 'yes' or 'no'.",
        image_data=image_data,
        max_tokens=10
    )
    
    return "yes" in response.lower()

async def _transcribe_handwriting(self, image, page_num: int) -> list[Annotation]:
    """Transcribe handwritten content from image."""
    image_data = image_to_base64(image)
    
    prompt = """Analyze this document page and extract ALL handwritten annotations.

For each handwritten element, provide:
1. The transcribed text (use [unclear] for illegible parts)
2. Its location on the page
3. Any nearby printed text it relates to

Return as JSON array:
[
  {
    "text": "transcribed handwritten text",
    "location": "top-right margin",
    "context": "nearby printed text or null",
    "type": "note|question|arrow|underline|circle"
  }
]

If no handwritten content, return: []"""
    
    response = await vision_completion(
        model=self.ocr_model,
        prompt=prompt,
        image_data=image_data,
        max_tokens=self.ocr_max_tokens,
        json_mode=self.use_json_mode
    )
    
    return self._parse_handwriting_response(response, page_num)

def _parse_handwriting_response(self, response_text: str, page_num: int) -> list[Annotation]:
    # Extract JSON from response
    try:
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text
        
        items = json.loads(json_str.strip())
        
        return [
            Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content=item.get("text", ""),
                page_number=page_num,
                context=item.get("context"),
                position={"location": item.get("location"), "mark_type": item.get("type")}
            )
            for item in items
            if item.get("text")
        ]
    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to parse handwriting response: {e}")
        return []
```

**Deliverables:**
- [ ] PDF to image conversion
- [ ] Model-agnostic vision completion wrapper
- [ ] Handwriting detection via configurable model
- [ ] Handwriting transcription with optional JSON mode
- [ ] JSON response parsing with error handling
- [ ] Integration tests with sample PDFs

**Estimated Time:** 5 hours

---

#### Task 2B.4: Image Utilities & Model-Agnostic OCR Client

**Why centralize OCR in a utility module?** Multiple pipelines need vision capabilities (PDF handwriting, book photos, quick photo capture). A shared `ocr_client.py` ensures:
- **Consistency**: Same model configuration and error handling everywhere
- **Swappability**: Change `OCR_MODEL` once, affects all pipelines
- **Testability**: Mock the OCR client to test pipelines without API calls
- **Cost tracking**: Single point to log API usage

**Why LiteLLM?** [LiteLLM](https://docs.litellm.ai/) provides a unified interface to 100+ LLM providers with production-ready features. Key benefits:
- **Spend Tracking**: Vision API calls are expensive ($0.01-0.03/image). Built-in cost tracking helps monitor usage.
- **Rate Limiting**: Prevents runaway costs from batch processing spikes or bugs.
- **Budget Alerts**: Set monthly limits and get notified before overspending.
- **Automatic Fallbacks**: If primary model is rate-limited, fallback to backup without code changes.
- **Native Async**: Better performance in our async FastAPI/Celery architecture.

Create shared image processing utilities and a model-agnostic vision completion wrapper:

```python
# backend/app/pipelines/utils/image_utils.py

from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import base64
import io

def image_to_base64(image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    if isinstance(image, (str, Path)):
        image = Image.open(image)
    
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def preprocess_for_ocr(image) -> Image.Image:
    """Enhance image for better OCR results."""
    if isinstance(image, (str, Path)):
        image = Image.open(image)
    
    # Convert to RGB if necessary
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)
    
    return image

def resize_for_api(image, max_dimension: int = 2048) -> Image.Image:
    """Resize image to fit within API limits while preserving aspect ratio."""
    if isinstance(image, (str, Path)):
        image = Image.open(image)
    
    width, height = image.size
    
    if max(width, height) <= max_dimension:
        return image
    
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
```

```python
# backend/app/pipelines/utils/ocr_client.py

"""
Model-agnostic vision completion wrapper using LiteLLM.

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name". Supported providers include:
- Mistral: mistral/pixtral-large-latest
- OpenAI: openai/gpt-4o, openai/gpt-4o-mini
- Anthropic: anthropic/claude-3-5-sonnet-20241022
- Google: gemini/gemini-2.0-flash
- Azure: azure/gpt-4-vision

Key features over simpler abstractions (e.g., AISuite):
- Built-in spend tracking and cost logging
- Rate limiting (TPM/RPM) to prevent runaway costs
- Budget limits with alerts
- Automatic fallbacks to backup models
- Native async support (acompletion)

See: https://docs.litellm.ai/
"""

import litellm
from litellm import completion, acompletion
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure LiteLLM settings
litellm.success_callback = ["langfuse"] if settings.LANGFUSE_ENABLED else []
litellm.set_verbose = settings.DEBUG  # Enable detailed logging in debug mode

def vision_completion_sync(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1
) -> str:
    """Execute vision completion with any LiteLLM-supported model.
    
    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
               e.g., "mistral/pixtral-large-latest", "openai/gpt-4o"
        prompt: Text prompt for the vision model
        image_data: Base64-encoded image data
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        image_format: Image MIME type suffix (png, jpeg, etc.)
        temperature: Sampling temperature (lower = more deterministic)
    
    Returns:
        Model response text/JSON string
    
    Example:
        >>> response = vision_completion_sync(
        ...     model="mistral/pixtral-large-latest",
        ...     prompt="Extract all text from this image",
        ...     image_data=base64_image,
        ...     json_mode=True
        ... )
    """
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{image_data}"
                }
            }
        ]
    }]
    
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    # Add JSON mode if supported by model
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    try:
        response = completion(**kwargs)
        
        # Log cost for spend tracking
        if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
            logger.info(f"Vision completion cost: ${response._hidden_params['response_cost']:.4f}")
        
        logger.debug(f"Vision completion successful with {model}")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision completion failed with {model}: {e}")
        raise

async def vision_completion(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1
) -> str:
    """Async version of vision_completion using LiteLLM's native acompletion."""
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{image_data}"
                }
            }
        ]
    }]
    
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    try:
        response = await acompletion(**kwargs)
        logger.debug(f"Vision completion successful with {model}")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision completion failed with {model}: {e}")
        raise

def text_completion_sync(
    model: str,
    prompt: str,
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.1
) -> str:
    """Execute text-only completion (for metadata inference, etc.)."""
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = completion(**kwargs)
    return response.choices[0].message.content

async def text_completion(
    model: str,
    prompt: str,
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.1
) -> str:
    """Async version of text_completion using LiteLLM's native acompletion."""
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = await acompletion(**kwargs)
    return response.choices[0].message.content
```

**Deliverables:**
- [ ] Base64 encoding function
- [ ] OCR preprocessing (contrast, sharpen)
- [ ] Image resizing for API limits
- [ ] Model-agnostic `vision_completion()` wrapper via LiteLLM
- [ ] Sync version `vision_completion_sync()` for Celery tasks
- [ ] `text_completion()` helper for metadata inference
- [ ] Unit tests for utilities

**Estimated Time:** 3 hours

---

### Phase 2C: Additional Pipelines (Week 5)

**Why multiple pipelines?** Knowledge workers consume information from many sources. A Second Brain that only handles PDFs misses most of the content people actually engage with—web articles, podcasts, code repositories, and fleeting ideas captured in voice memos.

#### Task 2C.1: Raindrop.io Sync Pipeline

**Why Raindrop.io?** Raindrop.io is a popular bookmark manager that captures web content with highlights and tags. Unlike browser bookmarks, Raindrop stores the actual content (not just URLs) and allows highlighting passages. By syncing Raindrop:
- **Capture reading habits**: Every saved article enters the knowledge graph
- **Preserve highlights**: User highlights become annotations in UCF
- **Leverage existing workflow**: No need to change how users save articles

**Why Trafilatura?** Web article extraction is hard—ads, navigation, footers, cookie banners. Trafilatura is the best-in-class library for extracting main article content while filtering noise.

```python
# backend/app/pipelines/raindrop_sync.py

import httpx
from datetime import datetime, timedelta
from app.pipelines.base import BasePipeline
from app.models.content import UnifiedContent, ContentType, Annotation, AnnotationType
from trafilatura import fetch_url, extract
import asyncio

class RaindropSync(BasePipeline):
    BASE_URL = "https://api.raindrop.io/rest/v1"
    
    def __init__(self, access_token: str, llm_client=None):
        super().__init__(llm_client)
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0
        )
    
    def supports(self, input_data) -> bool:
        return input_data == "raindrop_sync"
    
    async def sync_collection(
        self,
        collection_id: int = 0,
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
            response.raise_for_status()
            data = response.json()
            
            if not data.get("items"):
                break
            
            # Process items concurrently (with limit)
            tasks = [self._process_raindrop(item) for item in data["items"]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, UnifiedContent):
                    all_items.append(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Failed to process raindrop: {result}")
            
            params["page"] += 1
            if params["page"] * 50 >= data.get("count", 0):
                break
        
        return all_items
    
    async def _process_raindrop(self, item: dict) -> UnifiedContent:
        # Fetch article content
        article_content = await self._fetch_article_content(item["link"])
        
        # Get highlights
        highlights = await self._get_highlights(item["_id"])
        
        annotations = [
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=h.get("text", ""),
                context=h.get("note")
            )
            for h in highlights
            if h.get("text")
        ]
        
        return UnifiedContent(
            source_type=ContentType.ARTICLE,
            source_url=item["link"],
            title=item.get("title", "Untitled"),
            authors=[item.get("creator", "Unknown")],
            created_at=datetime.fromisoformat(item["created"].replace("Z", "+00:00")),
            full_text=article_content or f"[Content could not be fetched from {item['link']}]",
            annotations=annotations,
            processing_status="pending"
        )
    
    async def _fetch_article_content(self, url: str) -> str:
        """Extract main content from URL using trafilatura."""
        try:
            downloaded = fetch_url(url)
            if downloaded:
                content = extract(downloaded, include_comments=False)
                return content or ""
        except Exception as e:
            self.logger.warning(f"Failed to fetch {url}: {e}")
        return ""
    
    async def _get_highlights(self, raindrop_id: int) -> list[dict]:
        """Get highlights for a specific raindrop."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/raindrop/{raindrop_id}"
            )
            response.raise_for_status()
            return response.json().get("item", {}).get("highlights", [])
        except Exception as e:
            self.logger.warning(f"Failed to get highlights for {raindrop_id}: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()
```

**Deliverables:**
- [ ] Raindrop API client
- [ ] Collection sync with pagination
- [ ] Highlight extraction
- [ ] Article content fetching
- [ ] Rate limiting handling

**Estimated Time:** 5 hours

---

#### Task 2C.2: Book Photo OCR Pipeline

**Why book photos?** Physical books remain a major knowledge source, especially for technical and non-fiction readers. Users highlight passages, write margin notes, and annotate diagrams. These annotations are *trapped* in physical form unless digitized.

**The challenge**: Unlike PDFs, book photos have:
- Variable lighting and angles
- Two-page spreads requiring page number extraction
- Mix of printed text and handwritten notes
- No guaranteed page order (users photograph random pages)

This pipeline solves all of these by using Vision LLM to extract page numbers from the image itself, not assuming image order equals page order.

> **Note**: This pipeline uses a **model-agnostic** approach via LiteLLM. Configure the vision model via `OCR_MODEL` (format: `provider/model-name`). Default is Mistral for best performance on complex document layouts.

```python
# backend/app/pipelines/book_ocr.py

from pathlib import Path
from app.pipelines.base import BasePipeline
from app.pipelines.utils.image_utils import image_to_base64, preprocess_for_ocr
from app.pipelines.utils.ocr_client import vision_completion
from app.models.content import UnifiedContent, ContentType, Annotation, AnnotationType
from datetime import datetime
from PIL import Image
import json

class BookOCRPipeline(BasePipeline):
    def __init__(
        self, 
        ocr_model: str = "mistral:pixtral-large-latest",
        ocr_max_tokens: int = 4000,
        use_json_mode: bool = True,
        text_model: str = "openai:gpt-4o-mini"  # For metadata inference
    ):
        super().__init__()
        self.ocr_model = ocr_model
        self.ocr_max_tokens = ocr_max_tokens
        self.use_json_mode = use_json_mode
        self.text_model = text_model
    
    def supports(self, input_data) -> bool:
        if isinstance(input_data, list):
            return all(
                isinstance(p, Path) and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic")
                for p in input_data
            )
        return False
    
    async def process(
        self,
        image_paths: list[Path],
        book_metadata: dict = None
    ) -> UnifiedContent:
        """Process batch of book page photos.
        
        Note: Page numbers are extracted via OCR from the images themselves,
        NOT assumed from image order. Images may contain multiple pages,
        page numbers may be missing, or pages may be out of order.
        """
        page_results = []
        
        for idx, image_path in enumerate(image_paths):
            self.logger.info(f"Processing image {idx + 1}/{len(image_paths)}: {image_path}")
            
            # Preprocess image
            processed = preprocess_for_ocr(image_path)
            
            # Extract content including page number from OCR
            page_result = await self._process_page(processed, image_path)
            page_result["source_image"] = str(image_path)
            page_results.append(page_result)
        
        # Sort by extracted page number (pages without numbers go to end)
        page_results.sort(key=lambda x: (
            x.get("page_number") is None,  # None values last
            x.get("page_number") or 0
        ))
        
        # Aggregate annotations with correct page numbers and chapter info
        all_annotations = []
        full_text_parts = []
        chapters_found = {}  # Track unique chapters: {chapter_num: chapter_title}
        
        for result in page_results:
            page_num = result.get("page_number")
            chapter = result.get("chapter")
            
            # Build page label with chapter context if available
            if page_num and chapter:
                chapter_str = f"Ch. {chapter['number']}" if chapter.get('number') else ""
                if chapter.get('title'):
                    chapter_str = f"{chapter_str}: {chapter['title']}" if chapter_str else chapter['title']
                page_label = f"Page {page_num} ({chapter_str})" if chapter_str else f"Page {page_num}"
            elif page_num:
                page_label = f"Page {page_num}"
            else:
                page_label = f"[Image: {result['source_image']}]"
            
            full_text_parts.append(f"[{page_label}]\n{result['full_text']}")
            
            # Track chapters for metadata
            if chapter and chapter.get('number'):
                chapters_found[chapter['number']] = chapter.get('title')
            
            # Update annotations with extracted page number and chapter
            for annot in result.get("annotations", []):
                annot.page_number = page_num
                # Store chapter context in annotation position metadata
                if chapter:
                    if annot.position is None:
                        annot.position = {}
                    annot.position["chapter"] = chapter
                all_annotations.append(annot)
        
        # Infer metadata if not provided
        if not book_metadata and full_text_parts:
            book_metadata = await self._infer_metadata(full_text_parts[0])
        
        book_metadata = book_metadata or {}
        
        return UnifiedContent(
            source_type=ContentType.BOOK,
            title=book_metadata.get("title", "Unknown Book"),
            authors=book_metadata.get("authors", []),
            created_at=datetime.now(),
            full_text="\n\n---\n\n".join(full_text_parts),
            annotations=all_annotations,
            asset_paths=[str(p) for p in image_paths],
            processing_status="pending"
        )
    
    async def _process_page(self, image: Image.Image, source_path: Path) -> dict:
        """Process a single book page photo using configured vision model.
        
        The page number is extracted via OCR from the image itself, not assumed.
        Images may contain:
        - A single page with visible page number
        - A single page without visible page number
        - A two-page spread (both pages extracted)
        """
        image_data = image_to_base64(image)
        
        prompt = """Analyze this book page photo and extract:

1. PAGE NUMBER: Look for printed page numbers (usually at top or bottom corners).
   - If visible, extract the number(s)
   - If this is a two-page spread, extract both page numbers
   - If no page number is visible, use null

2. CHAPTER INFO: Look in headers/footers for chapter information.
   - Chapter number (e.g., "Chapter 5", "Part II", "Section 3.2")
   - Chapter title (e.g., "The Nature of Memory")
   - Running headers often show: "Chapter X" on left pages, chapter title on right pages

3. ALL printed text (complete transcription)

4. HIGHLIGHTED or MARKED passages (underlined, circled, highlighted)

5. HANDWRITTEN MARGIN NOTES (in margins, whitespace, between lines)

Return JSON:
{
  "page_number": 42,
  "page_number_location": "bottom-right",
  "chapter": {
    "number": "5",
    "title": "The Nature of Memory",
    "location": "header-left"
  },
  "is_two_page_spread": false,
  "spread_pages": null,
  "full_text": "complete printed text...",
  "highlights": [
    {"text": "highlighted passage", "type": "highlight|underline|circle", "location": "top|middle|bottom"}
  ],
  "margin_notes": [
    {"text": "handwritten note", "location": "left-margin|right-margin|top|bottom", "related_text": "nearby printed text or null", "type": "note|question|definition"}
  ]
}

For two-page spreads, use:
{
  "page_number": null,
  "is_two_page_spread": true,
  "spread_pages": [42, 43],
  ...
}

If no chapter info visible, use: "chapter": null

Important:
- Page number extraction is critical - check all corners and headers/footers
- Chapter info often appears in running headers/footers - check both top and bottom
- Use null for page_number or chapter only if truly not visible
- Distinguish printed text from handwritten annotations
- Use [unclear] for illegible parts
- Include ALL handwritten content including brief marks like "!" or "?""""
        
        response = await vision_completion(
            model=self.ocr_model,
            prompt=prompt,
            image_data=image_data,
            max_tokens=self.ocr_max_tokens,
            json_mode=self.use_json_mode
        )
        
        return self._parse_page_response(response)
    
    def _parse_page_response(self, response_text: str) -> dict:
        """Parse OCR response including extracted page number and chapter info."""
        try:
            # Extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text
            
            data = json.loads(json_str.strip())
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse OCR response")
            return {"full_text": "", "annotations": [], "page_number": None, "chapter": None}
        
        # Extract page number from OCR result
        page_number = data.get("page_number")
        is_spread = data.get("is_two_page_spread", False)
        spread_pages = data.get("spread_pages")
        
        # Extract chapter info from headers/footers
        chapter_data = data.get("chapter")
        chapter_info = None
        if chapter_data:
            chapter_info = {
                "number": chapter_data.get("number"),
                "title": chapter_data.get("title"),
                "location": chapter_data.get("location")
            }
            self.logger.info(f"Chapter detected: {chapter_info.get('number')} - {chapter_info.get('title')}")
        
        # For two-page spreads, use first page number
        if is_spread and spread_pages:
            page_number = spread_pages[0] if spread_pages else None
            self.logger.info(f"Two-page spread detected: pages {spread_pages}")
        
        annotations = []
        
        # Process highlights (page_number will be set by caller after sorting)
        for h in data.get("highlights", []):
            annotations.append(Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=h.get("text", ""),
                page_number=None,  # Set later after page ordering
                position={"location": h.get("location"), "style": h.get("type")}
            ))
        
        # Process margin notes
        for note in data.get("margin_notes", []):
            annotations.append(Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content=note.get("text", ""),
                page_number=None,  # Set later after page ordering
                context=note.get("related_text"),
                position={"location": note.get("location"), "note_type": note.get("type")}
            ))
        
        return {
            "page_number": page_number,
            "page_number_location": data.get("page_number_location"),
            "chapter": chapter_info,
            "is_two_page_spread": is_spread,
            "spread_pages": spread_pages,
            "full_text": data.get("full_text", ""),
            "annotations": annotations
        }
    
    async def _infer_metadata(self, first_page_text: str) -> dict:
        """Use LLM to infer book title and author from first page."""
        if not first_page_text:
            return {}
        
        prompt = f"""Based on this book page text, identify:
1. Book title
2. Author name(s)

Text:
{first_page_text[:2000]}

Return JSON: {{"title": "...", "authors": ["..."]}}
If unsure, use null for that field."""
        
        response = await text_completion(
            model=self.text_model,
            prompt=prompt,
            max_tokens=200,
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except:
            return {}
```

**Deliverables:**
- [ ] Book photo batch processing (no assumption of image order = page order)
- [ ] Page number extraction via OCR (from image corners/headers/footers)
- [ ] Chapter extraction from running headers/footers (number and title)
- [ ] Two-page spread detection and handling
- [ ] Model-agnostic OCR integration via LiteLLM
- [ ] Page OCR with highlights/notes separation
- [ ] Automatic page ordering based on extracted page numbers
- [ ] Book metadata inference
- [ ] Multi-page aggregation with proper page labels (including chapter context)
- [ ] Chapter metadata attached to annotations for better context

**Estimated Time:** 6 hours

---

#### Task 2C.3: Voice Memo Transcription

**Why voice memos?** Ideas often strike when typing isn't convenient—during walks, commutes, or while reading physical books. Voice capture is 3-5x faster than typing and captures the *tone* and *context* of a thought.

**Why Whisper?** OpenAI's Whisper is the gold standard for speech-to-text:
- Handles accents, background noise, and technical vocabulary
- Supports 99 languages
- Produces punctuated, paragraph-separated text
- API-based means no local GPU required

**Why expand notes?** Raw transcripts are messy—"um"s, incomplete sentences, rambling. The LLM expansion step transforms stream-of-consciousness speech into structured, readable notes while preserving original meaning.

```python
# backend/app/pipelines/voice_transcribe.py

from pathlib import Path
from openai import OpenAI
from app.pipelines.base import BasePipeline
from app.models.content import UnifiedContent, ContentType, Annotation, AnnotationType
from datetime import datetime

class VoiceTranscriber(BasePipeline):
    SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
    
    def __init__(self, llm_client, openai_api_key: str = None):
        super().__init__(llm_client)
        self.whisper_client = OpenAI(api_key=openai_api_key)
    
    def supports(self, input_data) -> bool:
        if isinstance(input_data, Path):
            return input_data.suffix.lower() in self.SUPPORTED_FORMATS
        return False
    
    async def process(self, audio_path: Path, expand: bool = True) -> UnifiedContent:
        # Transcribe with Whisper
        with open(audio_path, "rb") as audio_file:
            transcript = self.whisper_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        self.logger.info(f"Transcribed {audio_path}: {len(transcript)} chars")
        
        # Optionally expand into structured note
        if expand and self.llm_client:
            expanded = await self._expand_note(transcript)
        else:
            expanded = transcript
        
        return UnifiedContent(
            source_type=ContentType.VOICE_MEMO,
            source_file_path=str(audio_path),
            title=self._generate_title(expanded),
            created_at=datetime.fromtimestamp(audio_path.stat().st_mtime),
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
        prompt = f"""Transform this voice memo transcript into a well-structured note.

Transcript:
{transcript}

Instructions:
- Fix transcription errors
- Organize into logical sections if appropriate
- Add implicit context
- Keep original meaning and intent
- Format in Markdown

Return only the expanded note."""
        
        response = await self.llm_client.chat.completions.create(
            model="openai:gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def _generate_title(self, content: str) -> str:
        """Generate title from first meaningful line."""
        lines = content.strip().split("\n")
        for line in lines:
            clean = line.strip().lstrip("#").strip()
            if clean and len(clean) > 5:
                return clean[:100]
        return f"Voice memo - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
```

**Deliverables:**
- [ ] Whisper API integration
- [ ] Audio format detection
- [ ] Note expansion with LLM
- [ ] Title generation

**Estimated Time:** 3 hours

---

#### Task 2C.4: GitHub Repository Importer

**Why GitHub repos?** For developers, GitHub stars represent "interesting code I want to learn from." Most starred repos are never revisited because there's no system to extract and organize learnings. This pipeline:
- **Fetches README content**: The primary documentation
- **Analyzes file structure**: Reveals architecture patterns
- **Generates LLM summary**: Purpose, tech stack, key learnings
- **Creates knowledge nodes**: Links to related concepts in the graph

**Why analyze starred repos?** Stars are an *intent signal*—the user wanted to learn something from this repo. By surfacing that intent and extracting structured knowledge, we convert dormant stars into active learning.

```python
# backend/app/pipelines/github_importer.py

import httpx
from app.pipelines.base import BasePipeline
from app.models.content import UnifiedContent, ContentType
from datetime import datetime

class GitHubImporter(BasePipeline):
    BASE_URL = "https://api.github.com"
    
    def __init__(self, access_token: str, llm_client=None):
        super().__init__(llm_client)
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=30.0
        )
    
    def supports(self, input_data) -> bool:
        if isinstance(input_data, str):
            return input_data.startswith("https://github.com/") or input_data == "github_starred"
        return False
    
    async def import_starred_repos(self, limit: int = 50) -> list[UnifiedContent]:
        """Import user's starred repositories."""
        response = await self.client.get(
            f"{self.BASE_URL}/user/starred",
            params={"per_page": limit, "sort": "created", "direction": "desc"}
        )
        response.raise_for_status()
        
        results = []
        for repo in response.json():
            content = await self._analyze_repo(repo)
            results.append(content)
        
        return results
    
    async def import_repo(self, repo_url: str) -> UnifiedContent:
        """Import a specific repository."""
        # Parse owner/repo from URL
        parts = repo_url.replace("https://github.com/", "").split("/")
        owner, repo = parts[0], parts[1].split("#")[0].split("?")[0]
        
        response = await self.client.get(f"{self.BASE_URL}/repos/{owner}/{repo}")
        response.raise_for_status()
        
        return await self._analyze_repo(response.json())
    
    async def _analyze_repo(self, repo: dict) -> UnifiedContent:
        full_name = repo["full_name"]
        
        # Fetch README
        readme = await self._get_readme(full_name)
        
        # Get file tree
        tree = await self._get_tree(full_name)
        
        # Generate analysis
        analysis = await self._generate_analysis(repo, readme, tree)
        
        return UnifiedContent(
            source_type=ContentType.CODE,
            source_url=repo["html_url"],
            title=full_name,
            authors=[repo["owner"]["login"]],
            created_at=datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")),
            full_text=analysis,
            processing_status="pending"
        )
    
    async def _get_readme(self, full_name: str) -> str:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/repos/{full_name}/readme",
                headers={"Accept": "application/vnd.github.raw"}
            )
            if response.status_code == 200:
                return response.text
        except:
            pass
        return ""
    
    async def _get_tree(self, full_name: str) -> list[str]:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/repos/{full_name}/git/trees/HEAD",
                params={"recursive": 1}
            )
            if response.status_code == 200:
                tree = response.json().get("tree", [])
                return [item["path"] for item in tree[:100]]
        except:
            pass
        return []
    
    async def _generate_analysis(self, repo: dict, readme: str, tree: list[str]) -> str:
        if not self.llm_client:
            return f"# {repo['full_name']}\n\n{repo.get('description', '')}\n\n## README\n\n{readme}"
        
        prompt = f"""Analyze this GitHub repository:

Repository: {repo['full_name']}
Description: {repo.get('description', 'No description')}
Stars: {repo['stargazers_count']}
Language: {repo.get('language', 'Unknown')}

README:
{readme[:5000]}

File Structure:
{chr(10).join(tree[:50])}

Provide:
1. **Purpose**: What does this repository do?
2. **Architecture**: Key design patterns
3. **Tech Stack**: Languages, frameworks, dependencies
4. **Key Learnings**: What can be learned from this codebase?
5. **Notable Patterns**: Interesting implementations"""
        
        response = await self.llm_client.chat.completions.create(
            model="anthropic:claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    async def close(self):
        await self.client.aclose()
```

**Deliverables:**
- [ ] GitHub API client
- [ ] Starred repos sync
- [ ] README fetching
- [ ] File tree analysis
- [ ] LLM-powered repo analysis

**Estimated Time:** 5 hours

---

### Phase 2D: Quick Capture API (Week 6)

**Why a Quick Capture API?** The best Second Brain is one that gets used. Friction kills capture—if it takes more than a few seconds, users won't do it. The Quick Capture API enables:
- **Mobile PWA capture**: Snap a photo, record a voice note, paste a URL
- **Browser extension**: Highlight text → send to Second Brain
- **CLI tools**: `capture "interesting thought"` from terminal
- **Zapier/automation**: Trigger captures from other apps

#### Task 2D.1: Capture Router

**Why FastAPI routers?** FastAPI's router pattern organizes endpoints logically. The capture router handles all "throw content at the system" interactions—text, URLs, photos, voice, and PDFs. Each endpoint validates input, saves files, creates a UCF skeleton, and queues background processing.

**Why background tasks?** Users expect immediate response. The API returns within milliseconds (file saved, queued for processing) while OCR/transcription happens asynchronously.

```python
# backend/app/routers/capture.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
from app.models.content import UnifiedContent, ContentType, Annotation, AnnotationType
from app.services.storage import save_upload, save_content
from app.services.tasks import process_content
from datetime import datetime
import uuid
import httpx

router = APIRouter(prefix="/api/capture", tags=["capture"])

@router.post("/text")
async def capture_text(
    background_tasks: BackgroundTasks,
    content: str = Form(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """Quick text capture for ideas, notes, thoughts."""
    ucf = UnifiedContent(
        source_type=ContentType.IDEA,
        title=title or _generate_title(content),
        created_at=datetime.now(),
        full_text=content,
        processing_status="pending"
    )
    
    await save_content(ucf)
    background_tasks.add_task(process_content.delay, ucf.id, {"tags": tags})
    
    return {"status": "captured", "id": ucf.id}

@router.post("/url")
async def capture_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Capture a URL for later processing."""
    title = await _fetch_page_title(url)
    
    annotations = []
    if notes:
        annotations.append(Annotation(
            type=AnnotationType.TYPED_COMMENT,
            content=notes
        ))
    
    ucf = UnifiedContent(
        source_type=ContentType.ARTICLE,
        source_url=url,
        title=title,
        created_at=datetime.now(),
        full_text="",  # Fetched during processing
        annotations=annotations,
        processing_status="pending"
    )
    
    await save_content(ucf)
    background_tasks.add_task(process_content.delay, ucf.id, {"fetch_content": True})
    
    return {"status": "captured", "id": ucf.id, "title": title}

@router.post("/photo")
async def capture_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    capture_type: str = Form("general"),
    notes: Optional[str] = Form(None)
):
    """Capture a photo for OCR processing."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    file_path = await save_upload(file, directory="photos")
    
    ucf = UnifiedContent(
        source_type=ContentType.IDEA,
        source_file_path=str(file_path),
        title=f"Photo capture - {capture_type}",
        created_at=datetime.now(),
        full_text="",  # Extracted during processing
        asset_paths=[str(file_path)],
        processing_status="pending"
    )
    
    await save_content(ucf)
    background_tasks.add_task(process_content.delay, ucf.id, {"capture_type": capture_type})
    
    return {"status": "captured", "id": ucf.id}

@router.post("/voice")
async def capture_voice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Capture a voice memo for transcription."""
    valid_types = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/webm", "audio/m4a"}
    if file.content_type not in valid_types:
        raise HTTPException(400, f"Unsupported audio format: {file.content_type}")
    
    file_path = await save_upload(file, directory="voice_memos")
    
    ucf = UnifiedContent(
        source_type=ContentType.VOICE_MEMO,
        source_file_path=str(file_path),
        title=f"Voice memo - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        created_at=datetime.now(),
        full_text="",  # Transcribed during processing
        processing_status="pending"
    )
    
    await save_content(ucf)
    background_tasks.add_task(process_content.delay, ucf.id, {"priority": "high"})
    
    return {"status": "captured", "id": ucf.id}

@router.post("/pdf")
async def capture_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    content_type_hint: Optional[str] = Form(None)
):
    """Upload a PDF for processing."""
    if file.content_type != "application/pdf":
        raise HTTPException(400, "File must be a PDF")
    
    file_path = await save_upload(file, directory="pdfs")
    
    ucf = UnifiedContent(
        source_type=ContentType.PAPER,
        source_file_path=str(file_path),
        title=file.filename or "Untitled PDF",
        created_at=datetime.now(),
        full_text="",  # Extracted during processing
        processing_status="pending"
    )
    
    await save_content(ucf)
    background_tasks.add_task(process_content.delay, ucf.id, {"content_type_hint": content_type_hint})
    
    return {"status": "captured", "id": ucf.id}

def _generate_title(content: str) -> str:
    """Generate title from content."""
    first_line = content.strip().split("\n")[0]
    return first_line[:100] if first_line else f"Note - {datetime.now().strftime('%Y-%m-%d')}"

async def _fetch_page_title(url: str) -> str:
    """Fetch page title from URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                import re
                match = re.search(r"<title[^>]*>([^<]+)</title>", response.text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
    except:
        pass
    return url
```

**Deliverables:**
- [ ] Text capture endpoint
- [ ] URL capture endpoint
- [ ] Photo capture endpoint
- [ ] Voice capture endpoint
- [ ] PDF capture endpoint
- [ ] Input validation
- [ ] Background task queueing

**Estimated Time:** 5 hours

---

#### Task 2D.2: Storage Service

**Why a dedicated storage service?** File handling has many concerns:
- **Unique filenames**: Avoid collisions with UUID-based naming
- **Directory organization**: Separate PDFs, photos, voice memos
- **Database persistence**: Store UCF objects with proper relationships
- **Async file I/O**: Non-blocking writes with `aiofiles`

Centralizing this logic prevents duplication across routers and ensures consistent file handling.

```python
# backend/app/services/storage.py

from pathlib import Path
from fastapi import UploadFile
from app.config import settings
from app.models.content import UnifiedContent
from app.db.session import get_db
from app.db.models import Content, Annotation
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import uuid

async def save_upload(file: UploadFile, directory: str = "uploads") -> Path:
    """Save uploaded file and return path."""
    upload_dir = Path(settings.UPLOAD_DIR) / directory
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    ext = Path(file.filename).suffix if file.filename else ""
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename
    
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    
    return file_path

async def save_content(content: UnifiedContent, db: AsyncSession = None):
    """Save UnifiedContent to PostgreSQL."""
    if db is None:
        async with get_db() as db:
            return await _save_content_impl(content, db)
    return await _save_content_impl(content, db)

async def _save_content_impl(content: UnifiedContent, db: AsyncSession):
    db_content = Content(
        id=uuid.UUID(content.id),
        source_type=content.source_type.value,
        source_url=content.source_url,
        source_file_path=content.source_file_path,
        title=content.title,
        authors=content.authors,
        created_at=content.created_at,
        ingested_at=content.ingested_at,
        full_text=content.full_text,
        raw_file_hash=content.raw_file_hash,
        processing_status=content.processing_status,
        obsidian_path=content.obsidian_path
    )
    
    db.add(db_content)
    
    for annot in content.annotations:
        db_annot = Annotation(
            id=uuid.UUID(annot.id),
            content_id=db_content.id,
            type=annot.type.value,
            text=annot.content,
            page_number=annot.page_number,
            position=annot.position,
            context=annot.context,
            confidence=annot.confidence
        )
        db.add(db_annot)
    
    await db.commit()
    return db_content

async def load_content(content_id: str, db: AsyncSession = None) -> UnifiedContent:
    """Load UnifiedContent from PostgreSQL."""
    # Implementation for loading back from database
    pass

async def update_status(content_id: str, status: str, error: str = None, db: AsyncSession = None):
    """Update processing status of content."""
    # Implementation for status updates
    pass
```

**Deliverables:**
- [ ] File upload handling
- [ ] Content persistence to PostgreSQL
- [ ] Content loading from PostgreSQL
- [ ] Status update functions

**Estimated Time:** 4 hours

---

#### Task 2D.3: Ingestion Router

**Why separate from capture router?** The ingestion router handles *bulk operations* and *administrative triggers*:
- Manually trigger Raindrop sync
- Force GitHub starred repos refresh
- Check processing queue status
- Retry failed items

These are different from quick capture—they're intentional, scheduled, or administrative actions rather than user-initiated content throws.

```python
# backend/app/routers/ingestion.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

class SyncRequest(BaseModel):
    since_days: int = 1

@router.post("/raindrop/sync")
async def sync_raindrop(
    background_tasks: BackgroundTasks,
    request: SyncRequest
):
    """Trigger Raindrop.io sync."""
    from app.services.tasks import sync_raindrop_task
    
    since = datetime.now() - timedelta(days=request.since_days)
    background_tasks.add_task(sync_raindrop_task.delay, since.isoformat())
    
    return {"status": "sync_started", "since": since.isoformat()}

@router.post("/github/sync")
async def sync_github_starred(
    background_tasks: BackgroundTasks,
    limit: int = 50
):
    """Sync GitHub starred repositories."""
    from app.services.tasks import sync_github_task
    
    background_tasks.add_task(sync_github_task.delay, limit)
    
    return {"status": "sync_started", "limit": limit}

@router.get("/status/{content_id}")
async def get_processing_status(content_id: str):
    """Get processing status for a content item."""
    from app.services.storage import load_content
    
    content = await load_content(content_id)
    if not content:
        raise HTTPException(404, "Content not found")
    
    return {
        "id": content_id,
        "status": content.processing_status,
        "error": content.error_message
    }

@router.get("/queue/stats")
async def get_queue_stats():
    """Get processing queue statistics."""
    from app.services.queue import celery_app
    
    inspect = celery_app.control.inspect()
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    
    return {
        "active_tasks": sum(len(v) for v in active.values()),
        "queued_tasks": sum(len(v) for v in reserved.values())
    }
```

**Deliverables:**
- [ ] Raindrop sync trigger endpoint
- [ ] GitHub sync trigger endpoint
- [ ] Processing status endpoint
- [ ] Queue statistics endpoint

**Estimated Time:** 3 hours

---

#### Task 2D.4: Scheduled Sync Jobs

**Why scheduled syncs?** Some content sources should sync automatically:
- **Raindrop every 6 hours**: Capture articles saved during the day
- **GitHub daily at 7 AM**: Process newly starred repos overnight
- **Future**: Email digests, RSS feeds, calendar events

**Why APScheduler?** It's the standard Python scheduler with cron-like syntax, timezone support, and job persistence. It runs within the FastAPI process, avoiding the complexity of external cron jobs.

```python
# backend/app/services/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.tasks import sync_raindrop_task, sync_github_task
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

def setup_scheduled_jobs():
    """Configure scheduled sync jobs."""
    
    # Raindrop sync - every 6 hours
    scheduler.add_job(
        trigger_raindrop_sync,
        CronTrigger(hour="*/6"),
        id="raindrop_sync",
        replace_existing=True
    )
    
    # GitHub starred sync - daily at 7 AM
    scheduler.add_job(
        trigger_github_sync,
        CronTrigger(hour=7, minute=0),
        id="github_sync",
        replace_existing=True
    )
    
    logger.info("Scheduled jobs configured")

async def trigger_raindrop_sync():
    """Trigger Raindrop sync for last 24 hours."""
    since = datetime.now() - timedelta(hours=24)
    sync_raindrop_task.delay(since.isoformat())
    logger.info(f"Triggered Raindrop sync since {since}")

async def trigger_github_sync():
    """Trigger GitHub starred repos sync."""
    sync_github_task.delay(limit=100)
    logger.info("Triggered GitHub sync")

def start_scheduler():
    setup_scheduled_jobs()
    scheduler.start()
    logger.info("Scheduler started")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

**Deliverables:**
- [ ] APScheduler configuration
- [ ] Raindrop periodic sync
- [ ] GitHub periodic sync
- [ ] Startup/shutdown hooks

**Estimated Time:** 2 hours

---

## 4. Testing Strategy

### 4.1 Unit Tests

```
tests/
├── unit/
│   ├── test_models.py          # Pydantic model validation
│   ├── test_pdf_processor.py   # PDF extraction logic
│   ├── test_image_utils.py     # Image processing utilities
│   └── test_storage.py         # Storage service
├── integration/
│   ├── test_pdf_pipeline.py    # Full PDF pipeline
│   ├── test_raindrop_sync.py   # Raindrop API integration
│   └── test_capture_api.py     # REST API endpoints
└── fixtures/
    ├── sample.pdf              # Test PDF with annotations
    ├── sample_highlighted.pdf  # PDF with highlights
    └── sample_handwritten.pdf  # PDF with handwriting
```

### 4.2 Test Cases

| Pipeline | Test Case | Priority |
|----------|-----------|----------|
| PDF | Extract text from multi-page PDF | High |
| PDF | Extract digital highlights | High |
| PDF | Detect handwritten annotations | High |
| PDF | Handle encrypted PDF (graceful failure) | Medium |
| OCR | Vision completion with default model | High |
| OCR | Structured JSON output mode | High |
| OCR | Model switching via configuration | Medium |
| OCR | Rate limit/timeout handling | Medium |
| Raindrop | Sync with pagination | High |
| Raindrop | Handle rate limits | Medium |
| Book OCR | Process multiple page photos | High |
| Book OCR | Extract page numbers via OCR | High |
| Book OCR | Extract chapter info from headers/footers | High |
| Book OCR | Handle missing page numbers gracefully | Medium |
| Book OCR | Handle missing chapter info gracefully | Medium |
| Book OCR | Detect two-page spreads | Medium |
| Book OCR | Sort pages by extracted page number | High |
| Book OCR | Extract margin notes with confidence | High |
| Book OCR | Attach chapter context to annotations | Medium |
| Voice | Transcribe MP3 file | High |
| Voice | Expand transcript to note | Medium |
| Capture API | Upload PDF | High |
| Capture API | Capture text note | High |
| Capture API | Invalid file type rejection | High |

### 4.3 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific pipeline tests
pytest tests/unit/test_pdf_processor.py -v
```

---

## 5. Configuration

### 5.1 Pipeline Configuration

```python
# backend/app/config/pipelines.py

from pydantic_settings import BaseSettings

class PipelineSettings(BaseSettings):
    # PDF Processing
    PDF_TEXT_ENGINE: str = "pymupdf"
    PDF_HANDWRITING_DETECTION: bool = True
    PDF_IMAGE_DPI: int = 300
    PDF_MAX_FILE_SIZE_MB: int = 50
    
    # Vision OCR - Model-agnostic via LiteLLM (format: provider/model-name)
    # Supported models include:
    #   - mistral/pixtral-large-latest (default - best for structured docs)
    #   - openai/gpt-4o, openai/gpt-4o-mini
    #   - anthropic/claude-3-5-sonnet-20241022
    #   - gemini/gemini-2.0-flash
    OCR_MODEL: str = "mistral/pixtral-large-latest"
    OCR_MAX_TOKENS: int = 4000
    OCR_USE_JSON_MODE: bool = True
    OCR_TIMEOUT_SECONDS: int = 60
    OCR_MAX_RETRIES: int = 3
    
    # LiteLLM spend management (optional but recommended)
    LITELLM_BUDGET_MAX: float = 100.0  # Monthly budget in USD
    LITELLM_BUDGET_ALERT: float = 80.0  # Alert at 80% usage
    
    # Text model for metadata inference, note expansion, etc.
    TEXT_MODEL: str = "openai/gpt-4o-mini"
    
    # Raindrop
    RAINDROP_SYNC_INTERVAL_HOURS: int = 6
    RAINDROP_FETCH_FULL_CONTENT: bool = True
    
    # GitHub
    GITHUB_SYNC_STARRED: bool = True
    GITHUB_MAX_REPOS: int = 100
    GITHUB_ANALYZE_STRUCTURE: bool = True
    
    # Voice
    VOICE_TRANSCRIPTION_MODEL: str = "whisper-1"
    VOICE_EXPAND_NOTES: bool = True
    
    # Deduplication
    DEDUP_ENABLED: bool = True
    DEDUP_WINDOW_DAYS: int = 30
    
    class Config:
        env_prefix = "PIPELINE_"
```

> **Model-Agnostic Design**: The OCR pipeline uses [LiteLLM](https://docs.litellm.ai/) to support 100+ vision-capable models with the format `provider/model-name`. Change `OCR_MODEL` to switch providers without code changes. Default is Mistral for best structured extraction performance on complex documents.

---

## 6. Timeline Summary

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 3 | 2A | Foundation | Models, base pipeline, queue, database |
| 4 | 2B | PDF Pipeline | Text extraction, annotations, model-agnostic OCR via LiteLLM |
| 5 | 2C | Additional Pipelines | Raindrop, Book OCR, Voice, GitHub |
| 6 | 2D | Quick Capture | REST API, storage, scheduling |

**Total Estimated Time:** ~55-65 hours

> **Note:** Model-agnostic design via LiteLLM provides enterprise features (spend tracking, rate limiting, budgets) while keeping provider-switching simple via configuration.

---

## 7. Success Criteria

### Functional Requirements

- [ ] PDF text extraction accuracy > 95% on standard documents
- [ ] Digital highlight extraction works on major PDF readers (Adobe, Preview, Foxit)
- [ ] Handwritten note OCR achieves readable transcriptions on clear handwriting
- [ ] Vision completion produces valid structured JSON output for 95%+ of requests
- [ ] Raindrop sync captures all highlights and tags
- [ ] Voice transcription produces accurate text for clear audio
- [ ] All capture endpoints respond in < 3 seconds
- [ ] Processing queue handles 100+ items without failure

### Non-Functional Requirements

- [ ] Graceful degradation when external APIs unavailable
- [ ] Idempotent operations (re-running doesn't create duplicates)
- [ ] Logging sufficient for debugging failed ingestions (including model used)
- [ ] Configuration allows disabling individual pipelines
- [ ] OCR model configurable without code changes (via `OCR_MODEL`)
- [ ] OCR usage metrics tracked for cost monitoring

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Vision API rate limits | High | Medium | Implement batching, request queuing, configurable model switching |
| API provider outages | Medium | Low | Model-agnostic design allows quick config change to alternate provider |
| PDF format variations | Medium | High | Test with diverse PDFs, graceful error handling |
| Raindrop API changes | Medium | Low | Version pin API, monitor for deprecations |
| Large file processing timeouts | Medium | Medium | Implement chunking, async streaming, batch processing |
| OCR accuracy on poor images | Medium | Medium | Image preprocessing, confidence thresholds |
| LiteLLM compatibility | Low | Low | Pin LiteLLM version, test model updates in staging |

> **Model-Agnostic Advantage**: The LiteLLM abstraction allows switching OCR providers via configuration without code changes. If one provider has issues, simply update `OCR_MODEL` to use an alternative (e.g., switch from `mistral/pixtral-large-latest` to `openai/gpt-4o` or `anthropic/claude-3-5-sonnet-20241022`). LiteLLM also supports automatic fallbacks if configured.

---

## 9. Dependencies on Other Phases

### Required Before Phase 2

- [x] Phase 1: Foundation & Infrastructure (Docker, FastAPI, databases)

### Enables After Phase 2

- Phase 3: LLM Processing Layer (processes UCF output)
- Phase 4: Knowledge Explorer UI (displays processed content)

---

## 10. Open Questions

1. ~~**Handwriting OCR Model Selection**: Should we default to Gemini (cheaper) or GPT-4V (potentially more accurate)?~~ **RESOLVED**: Model-agnostic design via LiteLLM. Default is `mistral/pixtral-large-latest` for best accuracy; configurable via `OCR_MODEL`.
1. ~~**Model Cost Tracking**: How should we track and alert on OCR usage costs across different providers?~~ **RESOLVED**: LiteLLM provides built-in spend tracking and budget alerts. Configure via `LITELLM_BUDGET_MAX` and `LITELLM_BUDGET_ALERT`.
2. **Raindrop Collections**: Sync all collections or allow user to specify?
3. **File Size Limits**: What's the maximum PDF/audio file size to accept?
4. **Processing Priority**: Should voice memos always be high priority?
5. **Duplicate Handling**: Alert user or silently skip duplicates?

---

## Related Documents

- `design_docs/01_ingestion_layer.md` — Original design specification
- `design_docs/02_llm_processing_layer.md` — Downstream processing
- `design_docs/09_data_models.md` — Data model definitions
- `implementation_plan/02_llm_processing_implementation.md` — Next phase plan (to be created)
