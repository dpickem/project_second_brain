# Ingestion Pipelines

This package contains all content ingestion pipelines that convert diverse source formats into the **Unified Content Format (UCF)**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PipelineRegistry                              │
│  • Automatic routing based on (file_format, content_type) tuple     │
│  • Uses PipelineInput for context-aware routing                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ PDFProcessor  │  │ BookOCRPipeline │  │ VoiceTranscriber│
│  (PDF type)   │  │  (BOOK type)    │  │ (VOICE_MEMO)    │
└───────────────┘  └─────────────────┘  └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ UnifiedContent  │
                    │    (UCF)        │
                    └─────────────────┘
```

## Routing with PipelineInput

The registry routes inputs based on a **tuple of (file_format, content_type)**, not just file extension. This allows different pipelines to handle the same file format based on context:

| File Format | Content Type | Pipeline |
|-------------|--------------|----------|
| `.jpg/.png` | `BOOK` | BookOCRPipeline |
| `.jpg/.png` | `WHITEBOARD` | WhiteboardOCRPipeline (future) |
| `.pdf` | `PDF` | PDFProcessor |
| `.mp3/.wav` | `VOICE_MEMO` | VoiceTranscriber |
| URL | `CODE` | GitHubImporter |
| URL | `ARTICLE` | WebArticlePipeline |

**Batch Sync (not via registry):**
| Service | Pipeline | Usage |
|---------|----------|-------|
| Raindrop.io | RaindropSync | `sync.sync_collection(since=...)` |

### PipelineInput

All pipelines accept a `PipelineInput` object that wraps the actual input with routing context:

```python
from app.pipelines.base import PipelineInput, PipelineContentType

# File input (book page image)
input_data = PipelineInput(
    path=Path("page.jpg"),
    content_type=PipelineContentType.BOOK,
)

# URL input (GitHub repo)
input_data = PipelineInput(
    url="https://github.com/user/repo",
    content_type=PipelineContentType.CODE,
)

# Text input (quick idea)
input_data = PipelineInput(
    text="My brilliant idea...",
    content_type=PipelineContentType.IDEA,
)
```

### PipelineContentType Enum

```python
class PipelineContentType(str, Enum):
    # Image-based (requires context to route)
    BOOK = "book"              # Book page photos → BookOCRPipeline
    WHITEBOARD = "whiteboard"  # Whiteboard photos (future)
    DOCUMENT = "document"      # Document scans (future)
    PHOTO = "photo"            # General photos (future)
    
    # File-based (extension is sufficient)
    PDF = "pdf"                # PDF files → PDFProcessor
    VOICE_MEMO = "voice_memo"  # Audio files → VoiceTranscriber
    
    # URL-based
    CODE = "code"              # GitHub repos → GitHubImporter
    ARTICLE = "article"        # Web articles → RaindropSync
    
    # Text-based
    IDEA = "idea"              # Quick text captures
    NOTE = "note"              # Longer notes
```

---

## Pipelines

### PDFProcessor
Extracts text, highlights, comments, and handwritten annotations from PDFs.

**Supported content types:** `PipelineContentType.PDF`  
**Supported formats:** `.pdf`

**Features:**
- Text extraction with PyMuPDF (fast, layout-aware)
- Digital annotation extraction (highlights, comments, underlines)
- Handwritten annotation OCR via Vision LLM
- Metadata extraction (title, authors, date)
- Deduplication via file hash

```python
from app.pipelines import PDFProcessor
from app.pipelines.base import PipelineInput, PipelineContentType

processor = PDFProcessor()
input_data = PipelineInput(
    path=Path("paper.pdf"),
    content_type=PipelineContentType.PDF,
)
content = await processor.process(input_data)
```

---

### BookOCRPipeline
Extracts text and margin notes from photos of physical book pages.

**Supported content types:** `PipelineContentType.BOOK`  
**Supported formats:** `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, `.tiff`

**Features:**
- Page number extraction via OCR (not assumed from image order)
- Chapter detection from running headers/footers
- Handwritten margin note transcription
- Highlight/underline detection
- Two-page spread handling
- Parallel OCR processing for faster batch handling

```python
from app.pipelines import BookOCRPipeline
from app.pipelines.base import PipelineInput, PipelineContentType

pipeline = BookOCRPipeline(max_concurrency=10)
input_data = PipelineInput(
    path=Path("page1.jpg"),  # Or list of paths for batch
    content_type=PipelineContentType.BOOK,
)
content = await pipeline.process(input_data)
```

---

### VoiceTranscriber
Transcribes voice recordings using OpenAI Whisper.

**Supported content types:** `PipelineContentType.VOICE_MEMO`  
**Supported formats:** `.mp3`, `.mp4`, `.m4a`, `.wav`, `.webm`, `.ogg`, `.flac`

**Features:**
- Whisper API transcription (handles accents, noise, technical vocabulary)
- Optional LLM expansion (fixes transcription errors, adds structure)
- Automatic title generation
- Original transcript preserved as annotation

```python
from app.pipelines import VoiceTranscriber
from app.pipelines.base import PipelineInput, PipelineContentType

transcriber = VoiceTranscriber()
input_data = PipelineInput(
    path=Path("voice_memo.mp3"),
    content_type=PipelineContentType.VOICE_MEMO,
)
content = await transcriber.process(input_data)
```

---

### GitHubImporter
Analyzes starred repositories and extracts learnings.

**Supported content types:** `PipelineContentType.CODE`  
**Input:** GitHub URLs

**Features:**
- Starred repos sync with pagination
- Individual repo import by URL
- README content extraction
- File tree analysis
- LLM-powered analysis (purpose, architecture, tech stack, learnings)

```python
from app.pipelines import GitHubImporter
from app.pipelines.base import PipelineInput, PipelineContentType

importer = GitHubImporter(access_token="ghp_...")
input_data = PipelineInput(
    url="https://github.com/user/repo",
    content_type=PipelineContentType.CODE,
)
content = await importer.process(input_data)
```

---

### WebArticlePipeline
Extracts content from web article URLs using Trafilatura.

**Supported content types:** `PipelineContentType.ARTICLE`  
**Input:** Any web article URL

**Features:**
- Article content extraction via Trafilatura
- Title extraction from HTML
- Metadata extraction (author, date, site name)
- Clean text output

```python
from app.pipelines import WebArticlePipeline
from app.pipelines.base import PipelineInput, PipelineContentType

pipeline = WebArticlePipeline()
input_data = PipelineInput(
    url="https://example.com/blog/article",
    content_type=PipelineContentType.ARTICLE,
)
content = await pipeline.process(input_data)
```

---

### RaindropSync (Batch Sync Only)
Syncs bookmarked web articles with highlights from Raindrop.io.

**Note:** This pipeline is NOT used via PipelineRegistry. Use `sync_collection()` directly.

For generic article URL processing, use `WebArticlePipeline` instead.

**Features:**
- Collection sync with pagination
- Highlight extraction from Raindrop.io
- Full article content fetching (via WebArticlePipeline)
- Rate limit handling
- Concurrent processing

```python
from app.pipelines import RaindropSync
from datetime import datetime, timedelta

# Direct batch sync (NOT via registry)
sync = RaindropSync(access_token="...")
items = await sync.sync_collection(
    collection_id=0,  # 0 = all collections
    since=datetime.now() - timedelta(days=7),
    limit=100,
)
await sync.close()
```

---

## Base Pipeline

All pipelines inherit from `BasePipeline`, which provides:

```python
class BasePipeline(ABC):
    # Content types this pipeline handles
    SUPPORTED_CONTENT_TYPES: set[PipelineContentType] = set()
    
    @abstractmethod
    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        """Process input and return UnifiedContent."""
        pass

    @abstractmethod
    def supports(self, input_data: PipelineInput) -> bool:
        """Check if this pipeline can handle the input."""
        pass

    def calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash for deduplication."""

    def validate_file(self, file_path: Path, max_size_mb: int = 50) -> bool:
        """Validate file exists and is within size limits."""
```

### Creating a New Pipeline

```python
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.models.content import UnifiedContent, ContentType

class MyPipeline(BasePipeline):
    PIPELINE_NAME = "my_pipeline"
    SUPPORTED_CONTENT_TYPES = {PipelineContentType.DOCUMENT}
    SUPPORTED_FORMATS = {".doc", ".docx"}
    
    def supports(self, input_data: PipelineInput) -> bool:
        if input_data.content_type not in self.SUPPORTED_CONTENT_TYPES:
            return False
        if input_data.path is None:
            return False
        return input_data.path.suffix.lower() in self.SUPPORTED_FORMATS
    
    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        # Your processing logic here
        return UnifiedContent(
            content_type=ContentType.ARTICLE,
            title="...",
            body="...",
            source_path=str(input_data.path),
        )
```

---

## Pipeline Registry

The registry manages pipelines and routes inputs automatically. Use `get_registry()` to access the pre-configured singleton:

```python
from app.pipelines import get_registry, PipelineInput, PipelineContentType

# Get the pre-configured singleton registry
registry = get_registry()

# Route automatically based on content type
input_data = PipelineInput(
    path=Path("page.jpg"),
    content_type=PipelineContentType.BOOK,
)
content = await registry.process(input_data)  # Uses BookOCRPipeline

# List registered pipelines
pipelines = registry.list_pipelines()
# [
#   {"name": "PDFProcessor", "content_types": ["pdf"]},
#   {"name": "BookOCRPipeline", "content_types": ["book"]},
#   {"name": "VoiceTranscriber", "content_types": ["voice_memo"]},
#   {"name": "GitHubImporter", "content_types": ["code"]},      # if token configured
#   {"name": "RaindropSync", "content_types": ["article"]},     # if token configured
# ]
```

### Registry Configuration

The singleton registry is lazily initialized by `get_registry()` with:
- All file-based pipelines (PDFProcessor, BookOCRPipeline, VoiceTranscriber)
- URL-based pipelines only if API tokens are configured in settings

For testing, use `reset_registry()` to clear the singleton:

```python
from app.pipelines import reset_registry

reset_registry()  # Next get_registry() creates a fresh instance
```

---

## Utility Modules

Located in `app/pipelines/utils/`:

| Module | Purpose |
|--------|---------|
| `vlm_client.py` | Vision Language Model completion via LiteLLM (supports OpenAI, Gemini, Anthropic) |
| `mistral_ocr_client.py` | Dedicated Mistral OCR for PDF document processing with annotations |
| `cost_types.py` | LLM usage tracking types (`LLMUsage`, cost extraction) |
| `hash_utils.py` | File and content hashing for deduplication |
| `image_utils.py` | Image preprocessing, base64 encoding, rotation |
| `text_utils.py` | Text chunking, JSON extraction, title extraction |

### OCR Client Example

```python
from app.pipelines.utils.vlm_client import vision_completion

response, usage = await vision_completion(
    model="mistral/mistral-ocr-latest",
    prompt="Extract all text from this image",
    image_data=base64_image,
    json_mode=True,
    pipeline="book_ocr",
    operation="page_extraction"
)

print(f"Cost: ${usage.cost_usd:.4f}")
```

---

## Design Principles

### One Pipeline Per (file_format, content_type) Pair

The routing key is a **tuple**, not just file extension. This solves the ambiguity problem where the same file format can represent different content:

```
Same file format, different content types:
  .jpg + BOOK        → BookOCRPipeline
  .jpg + WHITEBOARD  → WhiteboardOCRPipeline
  .jpg + DOCUMENT    → DocumentOCRPipeline
```

The `PipelineInput` wrapper provides the necessary context for the registry to route correctly.

### Cost Tracking
All pipelines that use LLM APIs track costs via `CostTracker`:

```python
from app.services.cost_tracking import CostTracker

# Log usage after LLM call
await CostTracker.log_usage(usage)
```

### Unified Content Format
All pipelines output `UnifiedContent`, ensuring consistent downstream processing:

```python
UnifiedContent(
    content_type=ContentType.PAPER,
    title="Deep Learning Fundamentals",
    body="Full extracted text...",
    annotations=[
        Annotation(type=AnnotationType.HIGHLIGHT, content="key passage"),
        Annotation(type=AnnotationType.NOTE, content="margin note"),
    ],
    metadata={"authors": ["Alice", "Bob"], "year": 2024},
    source_path="/path/to/paper.pdf",
    source_hash="sha256:abc123...",
)
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_MODEL` | `mistral/mistral-ocr-latest` | Vision model for OCR |
| `TEXT_MODEL` | `openai/gpt-4o-mini` | Text model for inference |
| `OPENAI_API_KEY` | - | Required for Whisper transcription |
| `MISTRAL_API_KEY` | - | Required for Mistral OCR |
| `GITHUB_ACCESS_TOKEN` | - | Required for GitHub imports |
| `RAINDROP_ACCESS_TOKEN` | - | Required for Raindrop sync |
